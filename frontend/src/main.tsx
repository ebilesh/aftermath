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
    name: "The acknowledgement gap",
    description: "Commit a credit. Crash before acknowledgement. Replay it.",
    config: { duplicates: 3, outage_steps: 1, crash: "after_commit" },
  },
  {
    name: "Offline, then back",
    description: "Hold notifications through three failed RPC attempts.",
    config: { duplicates: 2, outage_steps: 3, crash: "none" },
  },
  {
    name: "Crash before commit",
    description: "Stop before any credit is written. Recover from disk.",
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
            Failure lab<span>01</span>
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
            Break the delivery.
            <br />
            Inspect the recovery.
          </p>
          <small>Python · SQLite · React</small>
        </div>
        <a className="author" href="https://github.com/ebilesh">
          github.com/ebilesh <ArrowRight size={14} />
        </a>
      </aside>
      <main>
        <header>
          <span>
            Workspace <ChevronRight size={14} />{" "}
            {view === "lab" ? "Failure lab" : "Transaction inspector"}
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
                <h1>What survives a failure?</h1>
                <p>
                  Inject a fault. Replay the payment. Follow every state change.
                </p>
              </div>
              <span className="simulation">
                <i /> SIMULATED ACTIVITY
              </span>
            </section>
            <div className="workspace">
              <section className="controls">
                <div className="section-title">
                  <h2>Experiment setup</h2>
                  <FlaskConical size={18} />
                </div>
                <p className="muted">
                  One order. One transfer. Unreliable delivery.
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
                      Custom experiment
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
                    <label htmlFor="duplicates">Duplicate notifications</label>
                    <p>Extra deliveries of the same payment.</p>
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
                    <p>Number of RPC attempts that fail.</p>
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
                  Worker crash point
                  <select
                    value={config.crash}
                    onChange={(e) =>
                      setConfig({ ...config, crash: e.target.value })
                    }
                  >
                    <option value="after_commit">
                      After credit, before acknowledgement
                    </option>
                    <option value="before_commit">Before credit commits</option>
                    <option value="none">No crash</option>
                  </select>
                </label>
                <div className="transfer">
                  <span>SYNTHETIC TRANSFER</span>
                  <strong>0.025 SOL</strong>
                  <small>
                    Finalized · matching recipient · integer lamports
                  </small>
                </div>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => action(() => update("/runs", config))}
                >
                  <Play size={16} />
                  Create experiment
                  <ArrowRight size={16} />
                </button>
                <p className="footnote">
                  Synthetic payment inputs. Real Python worker processes and
                  SQLite commits. One attempt per logical tick.
                </p>
              </section>
              <section className="run-panel">
                <div className="section-title">
                  <h2>Recovery workbench</h2>
                  <span className={"status " + (run?.crashed ? "stopped" : "")}>
                    {run
                      ? run.crashed
                        ? "Worker stopped"
                        : run.complete
                          ? "Complete"
                          : "Ready to advance"
                      : "Awaiting experiment"}
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
                          )?.name || "Custom experiment"}
                        </h3>
                      </div>
                      <button
                        className="icon-button"
                        onClick={exportRun}
                        title="Export run JSON"
                        aria-label="Export run JSON"
                      >
                        <Download size={18} />
                      </button>
                    </div>
                    <div className="pipeline">
                      {[
                        "Notification",
                        "Verify transfer",
                        "Credit ledger",
                        "Acknowledge",
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
                          {run.credits.length} / 1 credits written
                        </strong>
                        <p>
                          {run.invariant
                            ? "Single-credit invariant holds."
                            : "Invariant violated."}{" "}
                          {run.jobs.filter((j) => j.state === "acked").length}{" "}
                          of {run.jobs.length} notifications acknowledged.
                        </p>
                      </div>
                      <Check size={20} />
                    </div>
                    <div className="timeline-head">
                      <h3>
                        Event timeline <span>{run.events.length}</span>
                      </h3>
                      <div>
                        <span>tick {String(run.tick).padStart(2, "0")}</span>
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
                          {run.crashed ? "Restart worker" : "Advance worker"}
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
                            <strong>{e.kind.replaceAll("_", " ")}</strong>
                            <p>{e.detail}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                    {run.complete && (
                      <div className="complete">
                        <Check size={17} /> All notifications acknowledged.
                        Replay recovered with one credit.
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty">
                    <FlaskConical size={40} />
                    <h3>A failure worth inspecting</h3>
                    <p>
                      Create an experiment, then advance one worker attempt at a
                      time. The timeline will show what committed and what
                      recovery repeats.
                    </p>
                  </div>
                )}
              </section>
            </div>
            <section className="history">
              <div className="section-title">
                <h2>Recent experiments</h2>
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
                      {r.config.duplicates} duplicates · {r.config.outage_steps}{" "}
                      outage steps · {r.config.crash.replaceAll("_", " ")}
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
                  Your experiments will appear here. Each run keeps its
                  configuration and audit trail.
                </p>
              )}
            </section>
          </>
        ) : (
          <>
            <section className="intro">
              <div>
                <h1>Inspect the chain.</h1>
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
                Queries the public Solana RPC. Results never enter the simulated
                credit ledger.
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
                  Cluster
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
                  Transaction signature
                  <input
                    disabled={busy}
                    required
                    value={signature}
                    onChange={(e) => {
                      setSignature(e.target.value);
                      setInspection(null);
                    }}
                    placeholder="Paste a base58 transaction signature"
                  />
                </label>
                <button className="primary" disabled={busy}>
                  {busy ? "Querying Solana…" : "Inspect transaction"}
                  <ArrowRight size={16} />
                </button>
              </form>
              <p className="footnote">
                Commitment: finalized · Transaction versions: legacy and v0.
                Public RPC may rate-limit requests. A missing result does not
                prove a transaction failed.
              </p>
              {inspection && (
                <div className="rpc-result">
                  <p>
                    Network: {inspection.cluster} · Commitment:{" "}
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
                        Slot {inspection.result.slot} · Fee{" "}
                        {inspection.result.meta?.fee ?? "unknown"} lamports ·{" "}
                        {inspection.result.meta
                          ? inspection.result.meta.err
                            ? "Execution failed"
                            : "Execution succeeded"
                          : "Execution metadata unavailable"}
                      </p>
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
          <span>Aftermath · Reproducible failure testing</span>
          <span>At-least-once delivery. At-most-one credit.</span>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
