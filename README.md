# Aftermath

A Solana payment failure lab built for [ebilesh](https://github.com/ebilesh). Reproduce an acknowledgement gap, recover the worker, and inspect why an order receives one credit despite repeated delivery.

## Run locally

Requires Python 3.10+ and Node.js 20.19+.

```sh
npm ci
npm run build
python3 -m backend.server
```

Open http://127.0.0.1:8000. Python uses only the standard library. For frontend development, run `npm run dev` in a second terminal; Vite proxies `/api` to Python on port 8000.

```sh
npm test
# Isolate the real process-kill recovery test:
python3 -m unittest backend.test_subprocess -v
python3 experiments/replay.py experiments/ack-gap.json
```

## Try the failure

1. Create “The acknowledgement gap”. This queues four simulated notifications for one finalized 0.025 SOL transfer.
2. Advance once. The simulated RPC is unavailable; no credit is written.
3. Advance again. The credit commits, then the worker stops before acknowledging the notification.
4. Restart the worker. Advance until every notification is acknowledged.
5. Inspect `duplicate ignored` events and the single ledger credit. Export the full run as JSON. Create another run with the same recipe to reproduce the logical failure trace.

You can stop and restart the Python server at any point. `aftermath.sqlite3` persists runs, jobs, credits, and events. `AFTERMATH_DB` selects another path. There is no automatic worker: each Advance is one deterministic logical attempt, not elapsed wall time. Run IDs and job IDs differ between experiments; fault order and logical ticks reproduce.

## Correctness model

Notifications are at-least-once. Ledger effects are at-most-once per order and signature. Each run models one order and one synthetic finalized transfer. A SQLite primary key on order/run ID and unique signature constrain the ledger, independently of the UI. Integer lamports avoid rounding errors. `BEGIN IMMEDIATE` serializes each credit or acknowledgement transaction; concurrent attempts may reverify the same still-pending job, while constraints and conditional acknowledgement preserve safety; the ledger insert and its audit event commit atomically. Acknowledgement is deliberately a separate logical boundary. A crash after credit leaves the job pending; replay encounters the existing credit and acknowledges without crediting again.

The UI launches a real Python worker subprocess for each Advance. The configured crash boundaries persist a stopped marker and exit that worker without acknowledgement; Restart clears the marker, and the next Advance launches a fresh process. A network outage causes the real worker to skip verification and retain pending work, using a deterministic counter rather than an actual severed socket. Payment inputs and chain verification are synthetic. The separate subprocess integration test kills an OS process at the committed-credit boundary. This does not emulate arbitrary crash timing, RPC consensus behavior, fork/reorg handling, or distributed leases. There is one local SQLite writer, no external side effect, and no claim of end-to-end exactly-once delivery.

Tests cover persistence across a fresh Lab instance, before/after commit crashes, outage preservation, 31 concurrent worker attempts, direct database constraint violations, input bounds, and a recipe matrix. They assert both safety (no double credit) and liveness after recovery (every job acknowledged).

## Read-only Solana inspector

Paste a real transaction signature and choose devnet or mainnet beta. The backend calls the fixed public cluster endpoint using [`getTransaction`](https://solana.com/docs/rpc/http/gettransaction), `jsonParsed`, `finalized`, and `maxSupportedTransactionVersion: 0`. It displays slot, execution status, fee in lamports, and the raw response including parsed instructions and account balances. It never signs, submits, or credits a payment. Public RPC may return rate limits or null for a missing, unavailable, or not-yet-finalized transaction. Null is not proof of failure. Network errors remain errors, never simulated successes.

## Layout and API

- `backend/lab.py`: SQLite schema, worker transitions, durable event log.
- `backend/server.py`: local HTTP API, production static assets, fixed-endpoint RPC reader.
- `frontend/src`: React/TypeScript workbench and inspector.
- `experiments`: versionable JSON recipe and standalone replay runner.

| Endpoint | Behavior |
| --- | --- |
| GET `/api/runs` | Most recent 100 runs |
| POST `/api/runs` | Create with `duplicates`, `outage_steps`, `crash` |
| GET `/api/runs/{id}` | Configuration, queue, credits, ordered events |
| POST `/api/runs/{id}/step` | Advance one worker attempt |
| POST `/api/runs/{id}/restart` | Resume stopped worker |
| POST `/api/inspect` | Read finalized transaction by `signature` and `cluster` |

All POST requests accept JSON objects. Exported runs include `schema_version: 1` and the original recipe under `config`; use that config for another run.

## Scope

This first version focuses on inspectable failure recovery. It is not a payment gateway or reconciliation service. Synthetic verification assumes a correct recipient, amount, and finalized transaction. Live inspection does not validate merchant intent or support SPL-token settlement. The server binds to loopback and has no authentication; do not expose it as a public service. A next engineering step would introduce a devnet transfer validator with recipient, amount, reference, and finality checks before any real acceptance path, then exercise arbitrary process death and transaction contention under load.


## Replace the payment handler

`PaymentHandler.verify(order_id)` returns `VerifiedPayment(signature, lamports, evidence)` after checking merchant intent against a chain source. It must raise on unavailable, failed, unfinalized, wrong-recipient, or wrong-amount inputs. The worker owns ledger mutation and acknowledgement. Handlers must return a stable signature on replay and must not perform external credit side effects. This seam supports read/verify handlers, not arbitrary external payment mutations.

See `examples/custom_handler.py` for a merchant adapter and `backend/test_handler.py` for reusable recovery and rejection tests. The example defaults to fake chain data; replace its `lookup` with your chain reader. The first version's order amount is fixed at 25000000 lamports.

```python
from backend.lab import Lab
from examples.custom_handler import MerchantHandler

lab = Lab("custom.sqlite3", handler=MerchantHandler())
run = lab.create({"duplicates": 3, "outage_steps": 1, "crash": "after_commit"})
while not run["complete"]:
    run = lab.restart(run["id"]) if run["crashed"] else lab.step(run["id"])
assert len(run["credits"]) == 1
```

The subprocess CLI accepts `--handler examples.custom_handler:MerchantHandler` (a zero-argument factory). For your own adapter, change that import path. To isolate it in tests, inject a fake lookup and assert both rejection before credit and successful replay after a crash. Run `python3 -m unittest backend.test_handler -v`. The UI intentionally uses the default simulated handler; it does not load arbitrary modules from an HTTP request.

## Demo and architecture

In a two-minute demo, create the default experiment, advance through its outage and crash, restart, and drain the notifications. Show the single credit, pending/acknowledged counts, and ordered audit trail. Reload the page to demonstrate persistence. Export the run. Then open the inspector, select the intended network, and paste a transaction signature from that network. The result identifies the queried network and signature and exposes raw chain evidence. If RPC is unavailable, show the error as an error.

The React client sends commands to Python's HTTP handler. Advance launches `python -m backend.worker` against the same SQLite file. The worker reads a pending notification, applies configured faults, invokes its handler, commits a constrained ledger credit with an audit event, then commits acknowledgement separately. SQLite is the recovery authority; no in-memory queue is needed. The inspector is an independent fixed-endpoint read-only RPC adapter and cannot insert credits.

What runs for real: Python subprocesses, database transactions, uniqueness constraints, replay, and the event log. What is simulated: notification delivery, chain transfer data, finality/recipient verification, and outage scheduling. What remains unfinished: real merchant settlement validation, authenticated multi-user hosting, distributed workers, arbitrary crash fuzzing, SPL-token accounting, and browser automation in an unrestricted environment.

### Verification in this build environment

17 Python tests passed, including an actual subprocess kill/restart, HTTP request handling through the real subprocess worker, and mocked Solana RPC contracts and unavailable responses. TypeScript checking and the Vite production build passed. The standalone recipe runner passed. Browser verification and listening-server startup were attempted but blocked by sandbox socket permissions (EPERM); outbound npm DNS was unavailable. Dependencies were installed from the local cache, and a lockfile is included. Live Solana connectivity has not been verified here. RPC tests use explicit mocks, never fabricated live results.
