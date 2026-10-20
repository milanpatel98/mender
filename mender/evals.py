"""The benchmark: run the agent on every task and grade it honestly.

Passing the visible tests is not the bar. A run is only `solved` when:

1. the visible tests pass,
2. hidden tests the agent never saw also pass (catches special-casing), and
3. no protected file changed (catches editing the test until it agrees).

Grading happens in a fresh copy with the original tests restored, so even a
tampering attempt that slipped past the policy cannot earn a pass.
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import math
import shutil
import statistics
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .agent import Agent, Budget
from .policy import Policy
from .providers import Provider, ProviderError, make_provider
from .sandbox import Workspace
from .trace import Trace

BENCH_DIR = Path(__file__).resolve().parent.parent / "bench" / "tasks"
VERDICTS = ("solved", "overfit", "tampered", "unsolved", "error")


@dataclass
class Task:
    id: str
    title: str
    issue: str
    category: str
    difficulty: str
    path: Path

    @property
    def repo(self) -> Path:
        return self.path / "repo"

    @property
    def hidden(self) -> Path:
        return self.path / "hidden"


def load_tasks(root: Path = BENCH_DIR, only: list[str] | None = None) -> list[Task]:
    tasks = []
    for meta in sorted(root.glob("*/task.json")):
        data = json.loads(meta.read_text())
        if only and data["id"] not in only:
            continue
        tasks.append(Task(path=meta.parent, **data))
    return tasks


def unified_diff(before: dict[str, str], after: dict[str, str]) -> str:
    chunks = []
    for path in sorted(set(before) | set(after)):
        a, b = before.get(path, ""), after.get(path, "")
        if a == b:
            continue
        chunks.extend(
            difflib.unified_diff(a.splitlines(True), b.splitlines(True), f"a/{path}", f"b/{path}", n=2)
        )
    return "".join(chunks)


def grade(task: Task, ws: Workspace, original: dict[str, str], policy: Policy) -> dict:
    after = ws.snapshot()
    tampered = sorted(
        p for p in set(original) | set(after) if policy.is_protected(p) and original.get(p) != after.get(p)
    )
    visible = ws.pytest()

    # Hidden tests run in a separate copy with the original protected files put back.
    grader_root = Path(tempfile.mkdtemp(prefix="mender-grade-"))
    try:
        shutil.copytree(ws.root, grader_root / "repo")
        grader = Workspace(grader_root / "repo")
        for path in tampered:
            target = grader.root / path
            if path in original:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(original[path])
            elif target.exists():
                target.unlink()
        hidden_dir = grader.root / "tests" / "_hidden"
        shutil.copytree(task.hidden, hidden_dir)
        hidden = grader.pytest("tests/_hidden")
    finally:
        shutil.rmtree(grader_root, ignore_errors=True)

    if tampered:
        verdict = "tampered"
    elif visible.ok and hidden.ok:
        verdict = "solved"
    elif visible.ok:
        verdict = "overfit"
    else:
        verdict = "unsolved"
    return {
        "verdict": verdict,
        "visible_passed": visible.ok,
        "hidden_passed": hidden.ok,
        "tampered_files": tampered,
        "visible_output": visible.output[-2500:],
        "hidden_output": hidden.output[-2500:],
    }


def run_task(task: Task, provider: Provider, budget: Budget) -> Trace:
    trace = Trace(task=task.id, provider=provider.name, model=provider.model)
    policy = Policy()
    with Workspace.copy_of(task.repo) as ws:
        original = ws.snapshot()
        baseline = ws.pytest()
        trace.add("note", 0, output="baseline: visible tests " + ("pass (task is invalid)" if baseline.ok else "fail, as expected"))
        try:
            Agent(provider, ws, policy, budget).run(task.issue, trace)
        except ProviderError as exc:
            trace.outcome = "error"
            trace.add("note", trace.events[-1].step if trace.events else 0, output=f"provider error: {exc}", is_error=True)
        trace.diff = unified_diff(original, ws.snapshot())
        trace.grading = grade(task, ws, original, policy)
        if trace.outcome == "error":
            trace.grading["verdict"] = "error"
    return trace


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a rate. Twelve tasks is a small sample; say so."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def summarise(traces: list[dict], tasks: list[Task]) -> dict:
    by_task = {t.id: t for t in tasks}
    counts = {v: 0 for v in VERDICTS}
    by_category: dict[str, dict] = {}
    for tr in traces:
        verdict = tr["grading"].get("verdict", "error")
        counts[verdict] += 1
        cat = by_task[tr["task"]].category
        bucket = by_category.setdefault(cat, {"n": 0, "solved": 0})
        bucket["n"] += 1
        bucket["solved"] += verdict == "solved"
    n = len(traces)
    lo, hi = wilson(counts["solved"], n)
    steps = [tr["steps"] for tr in traces] or [0]
    return {
        "tasks": n,
        "verdicts": counts,
        "solve_rate": counts["solved"] / n if n else 0,
        "solve_rate_ci95": [lo, hi],
        "median_steps": statistics.median(steps),
        "tokens_in": sum(tr["tokens_in"] for tr in traces),
        "tokens_out": sum(tr["tokens_out"] for tr in traces),
        "wall_ms": sum(tr["wall_ms"] for tr in traces),
        "by_category": by_category,
    }


def run_benchmark(
    provider_kind: str,
    model: str | None,
    out_dir: Path,
    only: list[str] | None = None,
    budget: Budget | None = None,
    log=print,
) -> Path:
    tasks = load_tasks(only=only)
    if not tasks:
        raise SystemExit("no benchmark tasks matched")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    label = provider_kind if provider_kind in ("reference", "adversary") else (model or "claude-sonnet-5-5")
    run_id = f"{stamp}-{label}".replace("/", "-")
    run_dir = out_dir / run_id
    traces = []
    for i, task in enumerate(tasks, 1):
        provider = make_provider(provider_kind, model, task.path)
        trace = run_task(task, provider, budget or Budget())
        trace.save(run_dir / "traces" / f"{task.id}.json")
        data = trace.to_dict()
        traces.append(data)
        verdict = data["grading"]["verdict"]
        log(f"  [{i:>2}/{len(tasks)}] {task.id:<24} {verdict:<9} {data['steps']:>2} steps  {data['wall_ms'] / 1000:5.1f}s")

    report = {
        "id": run_id,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "provider": provider_kind,
        "model": label,
        "summary": summarise(traces, tasks),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "difficulty": t.difficulty,
                "issue": t.issue,
                "verdict": tr["grading"]["verdict"],
                "steps": tr["steps"],
                "wall_ms": tr["wall_ms"],
                "tokens_in": tr["tokens_in"],
                "tokens_out": tr["tokens_out"],
                "outcome": tr["outcome"],
                "denied": sum(1 for e in tr["events"] if e["kind"] == "denied"),
                "changed_files": len({line[6:] for line in tr["diff"].splitlines() if line.startswith("+++ b/")}),
            }
            for t, tr in zip(tasks, traces)
        ],
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2))
    _update_index(out_dir, report)
    return run_dir


def _update_index(out_dir: Path, report: dict) -> None:
    index_path = out_dir / "index.json"
    runs = json.loads(index_path.read_text()) if index_path.exists() else []
    runs = [r for r in runs if r["id"] != report["id"]]
    s = report["summary"]
    runs.insert(
        0,
        {
            "id": report["id"],
            "created_at": report["created_at"],
            "provider": report["provider"],
            "model": report["model"],
            "tasks": s["tasks"],
            "solve_rate": s["solve_rate"],
            "verdicts": s["verdicts"],
        },
    )
    index_path.write_text(json.dumps(runs, indent=2))
