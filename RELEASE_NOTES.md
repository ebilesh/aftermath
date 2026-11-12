# Aftermath v0.1.0

First local release of the Solana payment failure lab.

## Included

- Python worker subprocesses with persisted SQLite notifications, credits, and audit events.
- Duplicate notification, verification outage, and worker stop controls.
- Separate ledger commit and acknowledgement transactions with an at-most-one credit constraint.
- A reproducible test that kills a worker after credit commit, restarts it, and verifies exactly one credit.
- React/TypeScript workbench with event timeline, saved runs, and JSON export.
- Replaceable verification handler with a tested merchant adapter example.
- Read-only Solana transaction lookup showing network, signature, finality, execution status, and raw RPC evidence.
- Deterministic JSON experiment recipe and replay CLI.

## Run locally

Requires Python 3.10+ and Node.js 20.19+.

```sh
git clone --branch v0.1.0 https://github.com/ebilesh/aftermath.git
cd aftermath
npm ci
npm test
npm run build
python3 -m backend.server
```

Open http://127.0.0.1:8000. The Python backend has no third-party dependencies.

## Verification and limits

17 Python tests and the TypeScript/Vite build passed during development. The release workflow reruns tests, the production build, and the recipe before publishing.

Payment inputs and chain verification in the failure lab are synthetic; Python processes, SQLite transactions, and recovery are real. The UI's injected crash uses a durable stop boundary; the subprocess integration test performs an actual OS process kill.

Live Solana connectivity and browser interaction were not verified in the development sandbox. RPC tests use mocks and cover null, rejected, and unavailable responses. This is a local engineering lab, not a production payment gateway. See README.md for the walkthrough, architecture, and unfinished work.
