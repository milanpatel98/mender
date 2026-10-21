import { useEffect, useState } from "react";
import Swatch from "./Swatch.jsx";
import { Bar, Footer } from "./Chrome.jsx";
import { VERDICT_SHORT, VERDICT_TEXT, loadTrace, seconds, toHash } from "./data.js";

export default function TaskView({ report, taskId }) {
  const task = report.tasks.find((t) => t.id === taskId);
  const [trace, setTrace] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setTrace(null);
    setError("");
    loadTrace(report.id, taskId).then(setTrace).catch(() => setError("This trace file is missing."));
    window.scrollTo({ top: 0 });
  }, [report.id, taskId]);

  if (!task) {
    return (
      <div className="shell shell-dark">
        <Bar dark />
        <p className="notice">
          There is no task called “{taskId}” in this run. <a href={toHash(report.id)}>See all tasks</a>.
        </p>
      </div>
    );
  }

  const index = report.tasks.findIndex((t) => t.id === taskId);
  const prev = report.tasks[index - 1];
  const next = report.tasks[index + 1];

  return (
    <div className="shell shell-dark">
      <Bar dark />
      <main className="task">
        <a className="back" href={toHash(report.id)}>
          <span aria-hidden="true">←</span> Back
        </a>

        <h1 className="task-title">
          <span className="task-title-lead">{VERDICT_SHORT[task.verdict]}.</span>
          <span>{task.title}.</span>
        </h1>

        <div className={`plate plate-${task.verdict}`}>
          <Swatch task={task} animate={false} />
          <p className="plate-caption">
            {task.category} · {task.difficulty} · {task.steps} steps · {seconds(task.wall_ms)}
          </p>
        </div>

        <p className={`verdict verdict-${task.verdict}`}>{VERDICT_TEXT[task.verdict]}</p>

        <section className="issue" aria-labelledby="issue-title">
          <h2 id="issue-title">The bug report</h2>
          <blockquote>{task.issue.replace(/\n(?!\n)/g, " ")}</blockquote>
        </section>

        {error && <p className="notice">{error}</p>}
        {trace && (
          <>
            {trace.summary && (
              <section aria-labelledby="summary-title">
                <h2 id="summary-title">The agent’s explanation</h2>
                <p className="agent-summary">{trace.summary}</p>
              </section>
            )}
            <Steps events={trace.events} />
            <Diff diff={trace.diff} />
            <Grading grading={trace.grading} />
          </>
        )}

        <nav className="pager" aria-label="Other tasks">
          {prev ? (
            <a href={toHash(report.id, prev.id)}>
              <span className="pager-dir">Previous</span>
              {prev.title}
            </a>
          ) : (
            <span />
          )}
          {next ? (
            <a href={toHash(report.id, next.id)} className="pager-next">
              <span className="pager-dir">Next</span>
              {next.title}
            </a>
          ) : (
            <span />
          )}
        </nav>
      </main>
      <Footer dark />
    </div>
  );
}

function describeCall(event) {
  const input = event.input || {};
  switch (event.tool) {
    case "read_file":
      return input.start ? `${input.path}, lines ${input.start}–${input.end ?? "end"}` : input.path;
    case "edit_file":
    case "create_file":
      return input.path;
    case "search":
      return `/${input.pattern}/`;
    case "run_tests":
      return input.target || "full suite";
    default:
      return "";
  }
}

function Steps({ events }) {
  // Group events by step: a thought plus the tool calls it produced.
  const steps = [];
  for (const event of events) {
    if (event.step === 0) continue;
    let step = steps.find((s) => s.n === event.step);
    if (!step) steps.push((step = { n: event.step, thought: "", calls: [], notes: [] }));
    if (event.kind === "thought") step.thought = event.output;
    else if (event.kind === "note") step.notes.push(event.output);
    else step.calls.push(event);
  }

  return (
    <section aria-labelledby="steps-title">
      <h2 id="steps-title">What the agent did</h2>
      <ol className="steps">
        {steps.map((step) => (
          <li key={step.n} className="step">
            {step.thought && <p className="thought">{step.thought}</p>}
            {step.calls.map((call, i) => (
              <Call key={i} event={call} />
            ))}
            {step.notes.map((note, i) => (
              <p key={i} className="note">
                {note}
              </p>
            ))}
          </li>
        ))}
      </ol>
    </section>
  );
}

function Call({ event }) {
  const status = event.kind === "denied" ? "Blocked" : event.is_error ? "Failed" : event.kind === "final" ? "Finished" : null;
  const isEdit = event.tool === "edit_file" && event.input?.old !== undefined;
  return (
    <details className={`call call-${event.kind} ${event.is_error ? "call-error" : ""}`}>
      <summary>
        <code className="call-tool">{event.tool}</code>
        <span className="call-target">{describeCall(event)}</span>
        {status && <span className="call-status">{status}</span>}
        {event.duration_ms > 0 && <span className="call-time">{event.duration_ms} ms</span>}
      </summary>
      {isEdit && (
        <pre className="code diff">
          {event.input.old.split("\n").map((l, i) => (
            <span key={`o${i}`} className="del">{`- ${l}\n`}</span>
          ))}
          {event.input.new.split("\n").map((l, i) => (
            <span key={`n${i}`} className="add">{`+ ${l}\n`}</span>
          ))}
        </pre>
      )}
      {event.output && event.kind !== "final" && <pre className="code">{event.output}</pre>}
    </details>
  );
}

function Diff({ diff }) {
  if (!diff) {
    return (
      <section aria-labelledby="diff-title">
        <h2 id="diff-title">Changes to the code</h2>
        <p className="muted">The agent changed nothing.</p>
      </section>
    );
  }
  return (
    <section aria-labelledby="diff-title">
      <h2 id="diff-title">Changes to the code</h2>
      <pre className="code diff">
        {diff.split("\n").map((line, i) => {
          const cls = line.startsWith("+++") || line.startsWith("---") ? "file" : line.startsWith("@@") ? "hunk" : line.startsWith("+") ? "add" : line.startsWith("-") ? "del" : "";
          return (
            <span key={i} className={cls}>
              {line + "\n"}
            </span>
          );
        })}
      </pre>
    </section>
  );
}

function Grading({ grading }) {
  if (!grading?.verdict) return null;
  const checks = [
    ["Visible tests", grading.visible_passed],
    ["Hidden tests the agent never saw", grading.hidden_passed],
    ["Protected files untouched", (grading.tampered_files || []).length === 0],
  ];
  return (
    <section aria-labelledby="grading-title">
      <h2 id="grading-title">How it was graded</h2>
      <ul className="checks">
        {checks.map(([label, ok]) => (
          <li key={label} className={ok ? "pass" : "fail"}>
            <span className="check-mark" aria-hidden="true">{ok ? "✓" : "✕"}</span>
            {label}: {ok ? "pass" : "fail"}
          </li>
        ))}
      </ul>
      <details className="call">
        <summary>Hidden test output</summary>
        <pre className="code">{grading.hidden_output}</pre>
      </details>
    </section>
  );
}
