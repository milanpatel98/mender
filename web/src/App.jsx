import { useEffect, useMemo, useState } from "react";
import Swatch from "./Swatch.jsx";
import TaskView from "./TaskView.jsx";
import { Bar, Footer } from "./Chrome.jsx";
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
      .catch(() => setError("No runs found. Run “mender bench --provider reference” in the project folder, then refresh."));
  }, []);

  const runId = route.runId || runs?.[0]?.id || "";

  useEffect(() => {
    if (!runId) return;
    setReport(null);
    loadReport(runId)
      .then(setReport)
      .catch(() => setError(`Could not load run ${runId}. It may have been deleted with “mender clean”.`));
  }, [runId]);

  const dark = Boolean(route.taskId);
  useEffect(() => {
    document.documentElement.dataset.view = dark ? "task" : "run";
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#111111" : "#F4EE7B");
  }, [dark]);

  if (error) {
    return (
      <div className="shell">
        <Bar />
        <p className="notice">{error}</p>
      </div>
    );
  }
  if (!report) return <div className="shell loading" aria-busy="true" />;
  if (route.taskId) return <TaskView report={report} taskId={route.taskId} />;
  return <RunView report={report} runs={runs || []} />;
}

function Mark() {
  // A needle and one thread that ends in a checkmark: sewn up, tests passing.
  return (
    <svg className="mark" viewBox="0 -24 320 140" aria-hidden="true">
      <path className="mark-thread" pathLength="100" d="M8 66 C 30 58, 50 52, 78 62 L 122 104 L 226 26" />
      <g className="mark-needle">
        <line x1="231" y1="22.2" x2="284" y2="-17.8" className="mark-shaft" />
        <line x1="284" y1="-17.8" x2="296" y2="-26.8" className="mark-tip" />
        <ellipse cx="240" cy="15.4" rx="5" ry="1.7" transform="rotate(-37 240 15.4)" className="mark-eye" />
      </g>
    </svg>
  );
}

function RunView({ report, runs }) {
  const s = report.summary;
  const v = s.verdicts;
  const [lo, hi] = s.solve_rate_ci95;
  const [animate] = useState(() => !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const order = { solved: 0, overfit: 1, tampered: 2, unsolved: 3, error: 4 };
  const tasks = useMemo(
    () => [...report.tasks].sort((a, b) => order[a.verdict] - order[b.verdict] || a.id.localeCompare(b.id)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [report],
  );
  const denied = report.tasks.reduce((n, t) => n + (t.denied || 0), 0);
  const adversary = report.provider === "adversary";

  return (
    <div className="shell">
      <section className="hero" aria-labelledby="title">
        <div className="hero-grid" aria-hidden="true" />
        <Bar />
        <h1 id="title" className="word">
          Mender
        </h1>
        {/* Hero mark: Milan is designing it. Drop the SVG into src/mark.svg and render it here. */}
        <div className="hero-foot">
          <span className="numeral" aria-hidden="true">
            {v.solved}
          </span>
          <p className="hero-caption">
            {adversary ? (
              <>
                Tasks a cheating agent got past the grader.
                <br />
                {denied} attempts to rewrite the tests, all blocked.
              </>
            ) : (
              <>
                Bugs fixed out of {s.tasks}, checked against
                <br />
                hidden tests the agent never saw.
              </>
            )}
          </p>
        </div>
      </section>

      <nav className="runs" aria-label="Benchmark runs">
        {runs.map((run) => (
          <a key={run.id} href={toHash(run.id)} aria-current={run.id === report.id ? "page" : undefined}>
            <span className="run-name">{run.provider === "reference" ? "Reference fixes" : run.provider === "adversary" ? "Cheating agent" : run.model}</span>
            <span className="run-score">
              {run.verdicts.solved}/{run.tasks}
            </span>
          </a>
        ))}
      </nav>

      <section className="intro">
        <h2 className="intro-title">An agent that fixes bugs, graded so it cannot cheat.</h2>
        <div className="intro-body">
          <p>
            Mender reads a bug report, runs the tests, finds the cause and makes the smallest fix. Passing the tests it can see is not enough. Every
            task also has hidden tests, and any change to a test file fails the task outright.
          </p>
          <p className="intro-meta">
            This run: {describeRun(report)}. Solve rate {pct(s.solve_rate)}, and with only {s.tasks} tasks the honest range is {pct(lo)}
            –{pct(hi)}. Median {s.median_steps} steps per task.
          </p>
        </div>
      </section>

      <section className="work" aria-labelledby="work-title">
        <div className="work-head">
          <h2 id="work-title">Tasks</h2>
          <details className="legend">
            <summary>How to read these</summary>
            <p>
              Each task is a torn piece of cloth and every step the agent took is a stitch. Black thread closes a real fix. Half-closed means the
              visible tests passed but the hidden ones failed. Red crosses are attempts to edit tests that the permission layer blocked.
            </p>
          </details>
        </div>
        <ul className="cards">
          {tasks.map((task, i) => (
            <li key={task.id}>
              <a className={`card verdict-${task.verdict}`} href={toHash(report.id, task.id)}>
                <span className="card-art">
                  <Swatch task={task} animate={animate && i < 8} />
                </span>
                <span className="card-title">{task.title}</span>
                <span className="card-meta">
                  {VERDICT_SHORT[task.verdict]} · {task.steps} steps
                </span>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <Footer />
    </div>
  );
}
