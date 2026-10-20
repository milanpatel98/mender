import { useEffect, useMemo, useState } from "react";
import Swatch from "./Swatch.jsx";
import TaskView from "./TaskView.jsx";
import { VERDICT_SHORT, describeRun, loadIndex, loadReport, parseHash, pct, toHash } from "./data.js";

function useHashRoute() {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  const [runs, setRuns] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadIndex()
      .then(setRuns)
      .catch(() => setError("No runs found. Run `mender bench --provider reference` in the project folder, then refresh."));
  }, []);

  const runId = route.runId || runs?.[0]?.id || "";

  useEffect(() => {
    if (!runId) return;
    setReport(null);
    loadReport(runId)
      .then(setReport)
      .catch(() => setError(`Could not load run ${runId}. It may have been deleted with \`mender clean\`.`));
  }, [runId]);

  useEffect(() => {
    if (!route.taskId) window.scrollTo({ top: 0 });
  }, [route.taskId, runId]);

  return (
    <div className="page">
      <header className="masthead">
        <a className="wordmark" href={toHash(runId)}>
          Mender
        </a>
        <p className="tagline">A code-repair agent, graded so it cannot cheat.</p>
        <a className="source" href="https://github.com/milanpatel98/mender">
          Source on GitHub
        </a>
      </header>

      {error && <p className="notice">{error}</p>}

      {runs && runs.length > 0 && <RunPicker runs={runs} current={runId} />}

      {report && !route.taskId && <RunView report={report} />}
      {report && route.taskId && <TaskView report={report} taskId={route.taskId} />}

      <footer className="colophon">
        <p>
          Built by Milan Patel. Tasks, harness and grader are original work; the agent loop uses no framework.
          Run your own model with <code>mender bench --model &lt;id&gt;</code>.
        </p>
      </footer>
    </div>
  );
}

function RunPicker({ runs, current }) {
  return (
    <nav className="runs" aria-label="Benchmark runs">
      <h2 className="runs-heading">Runs</h2>
      <ul>
        {runs.map((run) => (
          <li key={run.id}>
            <a href={toHash(run.id)} aria-current={run.id === current ? "page" : undefined}>
              <span className="run-name">{run.model}</span>
              <span className="run-score">
                {run.verdicts.solved}/{run.tasks}
              </span>
              <span className="run-when">{new Date(run.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function RunView({ report }) {
  const s = report.summary;
  const [lo, hi] = s.solve_rate_ci95;
  const v = s.verdicts;
  const [animate] = useState(() => !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const order = { solved: 0, overfit: 1, tampered: 2, unsolved: 3, error: 4 };
  const tasks = useMemo(() => [...report.tasks].sort((a, b) => order[a.verdict] - order[b.verdict] || a.id.localeCompare(b.id)), [report]);
  const denied = report.tasks.reduce((n, t) => n + (t.denied || 0), 0);

  const caught = [
    v.overfit && `${v.overfit} overfit to the visible tests`,
    v.tampered && `${v.tampered} changed a protected file`,
    denied && `${denied} attempts to edit tests or config were blocked`,
  ].filter(Boolean);

  return (
    <main>
      <section className="lede" aria-labelledby="run-title">
        <h1 id="run-title">{describeRun(report)}</h1>
        <p className="lede-sentence">
          Mended <strong>{v.solved} of {s.tasks}</strong> tears ({pct(s.solve_rate)}; with only {s.tasks} tasks the honest range is {pct(lo)} to {pct(hi)}), in a median of {s.median_steps} steps.
          {caught.length > 0 && <> The grader also caught: {caught.join("; ")}.</>}
        </p>
        {(s.tokens_in > 0 || s.tokens_out > 0) && (
          <p className="lede-meta">
            {s.tokens_in.toLocaleString()} input tokens and {s.tokens_out.toLocaleString()} output tokens across the run.
          </p>
        )}
      </section>

      <Legend />

      <ul className="swatches">
        {tasks.map((task) => (
          <li key={task.id}>
            <a className={`swatch-card verdict-${task.verdict}`} href={toHash(report.id, task.id)}>
              <Swatch task={task} animate={animate} />
              <span className="swatch-title">{task.title}</span>
              <span className="swatch-meta">
                {VERDICT_SHORT[task.verdict]}, {task.steps} steps
              </span>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}

function Legend() {
  return (
    <details className="legend">
      <summary>How to read the swatches</summary>
      <p>
        Each task is a torn piece of cloth. Every step the agent took is a stitch across the tear. Gold thread
        closes a tear the agent truly fixed. A tear closed only halfway passed the visible tests but failed the
        hidden ones. Red thread means a protected file changed, and a red cross is a cheat attempt the
        permission layer blocked.
      </p>
    </details>
  );
}
