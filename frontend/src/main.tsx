import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  Check,
  ChevronRight,
  FlaskConical,
  Globe,
  Play,
  RotateCcw,
  ShieldCheck,
  Terminal,
  Download,
} from "lucide-react";
import "./style.css";
type Config = { duplicates: number; outage_steps: number; crash: string };
type Run = {
  id: string;
  tick: number;
  crashed: number;
  config: Config;
  events: { id: number; tick: number; kind: string; detail: string }[];
  credits: { lamports: number }[];
  jobs: { state: string }[];
  invariant: boolean;
  complete: boolean;
};
const presets = [
  {
    name: "Crash after saving the payment",
    description: "Save the payment, stop before marking its confirmation as processed, then retry.",
    config: { duplicates: 3, outage_steps: 1, crash: "after_commit" },
  },
  {
    name: "Offline, then back",
    description: "Keep the confirmations pending while three connection attempts fail.",
    config: { duplicates: 2, outage_steps: 3, crash: "none" },
  },
  {
    name: "Crash before saving the payment",
    description: "Stop before saving the payment, then restart and try again.",
    config: { duplicates: 1, outage_steps: 0, crash: "before_commit" },
  },
];
async function api(path: string, body?: unknown) {
  const response = await fetch(
    "/api" + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}
const eventLabels: Record<string, string> = {
  created: "Payment confirmations queued",
  rpc_unavailable: "Connection unavailable; payment check will be retried",
  verified: "Payment checked",
  worker_crashed: "Payment processor stopped",
  credited: "Payment record saved",
  duplicate_ignored: "Payment already recorded; extra confirmation skipped",
  acknowledged: "Confirmation marked as processed",
  restarted: "Payment processor restarted",
};
function App() {
  const [view, setView] = useState("lab"),
    [runs, setRuns] = useState<Run[]>([]),
    [run, setRun] = useState<Run | null>(null),
    [config, setConfig] = useState<Config>(presets[0].config),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [signature, setSignature] = useState(""),
    [cluster, setCluster] = useState("devnet"),
    [inspection, setInspection] = useState<any>(null);
  useEffect(() => {
    api("/runs")
      .then((r: Run[]) => {
        setRuns(r);
        setRun(r[0] || null);
      })
      .catch((e) => setError(e.message));
  }, []);
  async function action(fn: () => Promise<any>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function update(path: string, body: unknown = {}) {
    const r = await api(path, body);
    setRun(r);
    setRuns((old) => [r, ...old.filter((x) => x.id !== r.id)]);
  }
  function exportRun() {
    if (!run) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify({ schema_version: 1, ...run }, null, 2)], {
        type: "application/json",
      }),
    );
    a.download = `aftermath-${run.id}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="/">
          <Activity size={25} />
          <span>
            aftermath<span className="brand-dot">.</span>
          </span>
        </a>
        <p className="aside-caption">SOLANA PAYMENT FAILURE LAB</p>
        <nav>
          <button
            className={view === "lab" ? "active" : ""}
            onClick={() => setView("lab")}
          >
            <FlaskConical size={18} />
            Payment simulation
          </button>
          <button
            className={view === "inspector" ? "active" : ""}
            onClick={() => setView("inspector")}
          >
            <Globe size={18} />
            Transaction inspector
            <ChevronRight size={14} />
          </button>
        </nav>
        <div className="sidebar-note">
          <Terminal size={19} />
          <p>
            One payment.
            <br />
            Repeated confirmations.
          </p>
          <small>Python, SQLite and React</small>
        </div>
        <a className="author" href="https://github.com/ebilesh">
          github.com/ebilesh <ArrowRight size={14} />
        </a>
      </aside>
      <main>
        <header>
          <span>
            Workspace <ChevronRight size={14} />{" "}
            {view === "lab" ? "Payment simulation" : "Transaction inspector"}
          </span>
          <span className="local">
            <i />
            Local environment
          </span>
        </header>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {view === "lab" ? (
          <>
            <section className="intro">
              <div>
                <h1>Test a payment system crash</h1>
                <p>
                  A payment confirmation can arrive more than once. Simulate a crash and check that restarting the software records the payment only once.
                </p>
              </div>
              <span className="simulation">
                <i /> No real money moves
              </span>
            </section>
            <section className="start-guide" aria-labelledby="example-heading">
              <h2 id="example-heading">The default example</h2>
              <p>A customer pays once, but four copies of the payment confirmation arrive. The program crashes after saving the payment. Restart it and check whether the repeated confirmations create an extra payment record.</p>
              <p>The payment-processing program is called a <strong>worker</strong>. Its payment records are stored in a <strong>ledger</strong>. The simulation uses Python workers and a SQLite database.</p>
            </section>
            <div className="workspace">
              <section className="controls">
                <div className="section-title">
                  <h2>Set up a simulation</h2>
                  <FlaskConical size={18} />
                </div>
                <p className="muted">
                  Send repeated confirmations for one payment and choose when the program stops.
                </p>
                <label>
                  Start with a scenario
                  <select
                    value={presets.findIndex(
                      (p) =>
                        JSON.stringify(p.config) === JSON.stringify(config),
                    )}
                    onChange={(e) => {
                      const p = presets[Number(e.target.value)];
                      if (p) setConfig(p.config);
                    }}
                  >
                    <option value={-1} disabled>
                      Custom simulation
                    </option>
                    {presets.map((p, i) => (
                      <option value={i} key={p.name}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="field">
                  <div>
                    <label htmlFor="duplicates">Extra payment confirmations</label>
                    <p>Copies of the same confirmation, not additional payments.</p>
                  </div>
                  <input
                    id="duplicates"
                    type="number"
                    min="0"
                    max="50"
                    value={config.duplicates}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        duplicates: Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="field">
                  <div>
                    <label htmlFor="outage">Network outage</label>
                    <p>How many attempts to check the payment fail before the connection returns.</p>
                  </div>
                  <input
                    id="outage"
                    type="number"
                    min="0"
                    max="20"
                    value={config.outage_steps}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        outage_steps: Number(e.target.value),
                      })
                    }
                  />
                </div>
                <label>
                  When the payment processor crashes
                  <select
                    value={config.crash}
                    onChange={(e) =>
                      setConfig({ ...config, crash: e.target.value })
                    }
                  >
                    <option value="after_commit">
                      After saving, before marking done
                    </option>
                    <option value="before_commit">Before saving the payment</option>
                    <option value="none">No crash</option>
                  </select>
                </label>
                <div className="transfer">
                  <span>Simulated payment</span>
                  <strong>0.025 SOL</strong>
                  <small>
                    SOL is the currency used on the Solana network.
                  </small>
                </div>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => action(() => update("/runs", config))}
                >
                  <Play size={16} />
                  Create simulation
                  <ArrowRight size={16} />
                </button>
                <p className="footnote">
                  No funds are sent. Each step runs the payment-processing program once; the saved records stay in a local database.
                </p>
              </section>
              <section className="run-panel">
                <div className="section-title">
                  <h2>Watch what happens</h2>
                  <span className={"status " + (run?.crashed ? "stopped" : "")}>
                    {run
                      ? run.crashed
                        ? "Program stopped"
                        : run.complete
                          ? "Complete"
                          : "Ready for the next step"
                      : "Create a simulation to begin"}
                  </span>
                </div>
                {run ? (
                  <>
                    <div className="run-heading">
                      <div>
                        <small>RUN / {run.id}</small>
                        <h3>
                          {presets.find(
                            (p) =>
                              JSON.stringify(p.config) ===
                              JSON.stringify(run.config),
                          )?.name || "Custom simulation"}
                        </h3>
                      </div>
                      <button
                        className="icon-button"
                        onClick={exportRun}
                        title="Download event history (JSON)"
                        aria-label="Download event history (JSON)"
                      >
                        <Download size={18} />
                      </button>
                    </div>
                    <div className="pipeline">
                      {[
                        "Receive confirmation",
                        "Check payment",
                        "Save payment",
                        "Mark processed",
                      ].map((x, i) => (
                        <React.Fragment key={x}>
                          <span
                            className={
                              (i === 2 && run.credits.length) || run.complete
                                ? "done"
                                : ""
                            }
                          >
                            {x}
                          </span>
                          {i < 3 && <ArrowRight size={14} />}
                        </React.Fragment>
                      ))}
                    </div>
                    <div className="proof">
                      <ShieldCheck size={27} />
                      <div>
                        <strong>
                          {run.credits.length} payment record{run.credits.length === 1 ? "" : "s"} saved
                        </strong>
                        <p>
                          {run.invariant
                            ? run.credits.length === 0 ? "No payment has been saved yet." : "The same payment has not been recorded twice."
                            : "The payment was recorded more than once."}{" "}
                          {run.jobs.filter((j) => j.state === "acked").length}{" "}
                          of {run.jobs.length} confirmations marked as processed. Expected final total: one payment record.
                        </p>
                      </div>
                      <Check size={20} />
                    </div>
                    <div className="timeline-head">
                      <h3>
                        What happened <span>{run.events.length}</span>
                      </h3>
                      <div>
                        <span>step {String(run.tick).padStart(2, "0")}</span>
                        <button
                          disabled={busy || run.complete}
                          onClick={() =>
                            action(() =>
                              update(
                                `/runs/${run.id}/${run.crashed ? "restart" : "step"}`,
                              ),
                            )
                          }
                        >
                          {run.crashed ? (
                            <RotateCcw size={14} />
                          ) : (
                            <Play size={14} />
                          )}{" "}
                          {run.crashed ? "Restart the processor" : "Run next step"}
                        </button>
                      </div>
                    </div>
                    <ol className="timeline">
                      {run.events.map((e) => (
                        <li
                          key={e.id}
                          className={
                            e.kind === "worker_crashed"
                              ? "fault"
                              : e.kind === "credited"
                                ? "success"
                                : ""
                          }
                        >
                          <span className="tick">
                            T+{String(e.tick).padStart(2, "0")}
                          </span>
                          <div className="event-dot" />
                          <div>
                            <strong>{eventLabels[e.kind] || e.kind.replaceAll("_", " ")}</strong>
                            <details><summary>Technical details</summary><p>{e.detail}</p></details>
                          </div>
                        </li>
                      ))}
                    </ol>
                    {run.complete && (
                      <div className="complete">
                        <Check size={17} /> All confirmations processed. {run.credits.length === 1 ? "The payment was recorded once." : "Check the payment count above."}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty">
                    <h3>Start with the crash example</h3>
                    <p>
                      Choose Create simulation, then Run next step until the program stops. Restart the processor and keep stepping until it finishes. Check that only one payment record was saved.
                    </p>
                  </div>
                )}
              </section>
            </div>
            <section className="history">
              <div className="section-title">
                <h2>Saved simulations</h2>
                <span>{runs.length} saved locally</span>
              </div>
              {runs.length ? (
                runs.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setRun(r)}
                    className={run?.id === r.id ? "selected" : ""}
                  >
                    <code>{r.id}</code>
                    <span>
                      <span className="run-fact">{r.config.duplicates} extra confirmations</span>
                      <span className="run-fact">{r.config.outage_steps} failed checks</span>
                      <span className="run-fact">{r.config.crash === "after_commit" ? "crash after saving" : r.config.crash === "before_commit" ? "crash before saving" : "no crash"}</span>
                    </span>
                    <span>
                      {r.complete
                        ? "Complete"
                        : r.crashed
                          ? "Stopped"
                          : "In progress"}
                    </span>
                    <ChevronRight size={16} />
                  </button>
                ))
              ) : (
                <p className="muted">
                  Your simulations will appear here with their settings and event history.
                </p>
              )}
            </section>
          </>
        ) : (
          <>
            <section className="intro">
              <div>
                <h1>Look up a Solana transaction</h1>
                <p>
                  Read a real finalized Solana transaction without connecting a
                  wallet.
                </p>
              </div>
              <span className="simulation real">READ-ONLY RPC</span>
            </section>
            <section className="inspector">
              <h2>Transaction lookup</h2>
              <p>
                Look up a payment by its transaction ID. This reads public network data and does not send money or change the simulation.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  action(async () => {
                    setInspection(null);
                    setInspection(
                      await api("/inspect", { signature, cluster }),
                    );
                  });
                }}
              >
                <label>
                  Network
                  <select
                    disabled={busy}
                    value={cluster}
                    onChange={(e) => {
                      setCluster(e.target.value);
                      setInspection(null);
                    }}
                  >
                    <option value="devnet">Devnet</option>
                    <option value="mainnet-beta">Mainnet beta</option>
                  </select>
                </label>
                <label>
                  Transaction ID (signature)
                  <input
                    disabled={busy}
                    required
                    value={signature}
                    onChange={(e) => {
                      setSignature(e.target.value);
                      setInspection(null);
                    }}
                    placeholder="Paste a Solana transaction ID"
                  />
                </label>
                <button className="primary" disabled={busy}>
                  {busy ? "Querying Solana…" : "Inspect transaction"}
                  <ArrowRight size={16} />
                </button>
              </form>
              <p className="footnote">
                Commitment: finalized. Transaction versions: legacy and v0.
                Public RPC may rate-limit requests. A missing result does not
                prove a transaction failed.
              </p>
              {inspection && (
                <div className="rpc-result">
                  <p>
                    Network: {inspection.cluster}. Commitment:{" "}
                    {inspection.commitment}
                  </p>
                  <p className="signature">Signature: {inspection.signature}</p>
                  <h3>
                    {inspection.result
                      ? "Finalized transaction returned"
                      : "No finalized transaction found"}
                  </h3>
                  {inspection.result && (
                    <>
                      <p>
                        Slot {inspection.result.slot}. Fee:{" "}
                        {inspection.result.meta?.fee ?? "unknown"} lamports. {" "}
                        {inspection.result.meta
                          ? !("err" in inspection.result.meta) ? "Execution metadata unavailable" : inspection.result.meta.err
                            ? "Execution failed"
                            : "Execution succeeded"
                          : "Execution metadata unavailable"}
                      </p>
                      <h3>Native SOL transfer instructions</h3>
                      <p>{inspection.evidence?.warning}</p>
                      {inspection.evidence?.transfers.length ? (
                        <div className="transfer-evidence">
                          {inspection.evidence.transfers.map((transfer: {scope:string;instruction:number;source:string;destination:string;lamports:string;applied:boolean}) => (
                            <article key={`${transfer.scope}:${transfer.instruction}`}>
                              <strong>{transfer.lamports} lamports. {transfer.applied ? "Execution succeeded" : "Not confirmed as applied"}</strong>
                              <p className="signature">From: {transfer.source}</p>
                              <p className="signature">To: {transfer.destination}</p>
                              <small>{transfer.scope} / instruction {transfer.instruction}</small>
                            </article>
                          ))}
                        </div>
                      ) : <p>No supported parsed native SOL transfer instructions returned.</p>}
                      <details open>
                        <summary>Raw RPC result</summary>
                        <pre>{JSON.stringify(inspection, null, 2)}</pre>
                      </details>
                    </>
                  )}
                </div>
              )}
            </section>
          </>
        )}
        <footer>
          <span>Aftermath payment recovery simulations</span>
          <span>One payment should leave one saved record.</span>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);

