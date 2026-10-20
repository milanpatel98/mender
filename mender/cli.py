"""Command line: `mender fix`, `mender bench`, `mender tasks`."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .agent import Agent, Budget
from .evals import load_tasks, run_benchmark, unified_diff
from .policy import Mode, Policy
from .providers import ProviderError, make_provider
from .sandbox import Workspace
from .trace import Trace

RUNS = Path.cwd() / "runs"


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def cmd_bench(args: argparse.Namespace) -> int:
    print(f"mender {__version__} · benchmark · provider={args.provider} model={args.model or 'default'}\n")
    budget = Budget(max_steps=args.max_steps)
    try:
        run_dir = run_benchmark(args.provider, args.model, Path(args.out), args.task or None, budget)
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = json.loads((run_dir / "report.json").read_text())
    s = report["summary"]
    lo, hi = s["solve_rate_ci95"]
    v = s["verdicts"]
    print(
        f"\nsolved {v['solved']}/{s['tasks']} ({_pct(s['solve_rate'])}, 95% CI {_pct(lo)}–{_pct(hi)})"
        f"  ·  overfit {v['overfit']}  ·  tampered {v['tampered']}  ·  unsolved {v['unsolved']}  ·  error {v['error']}"
    )
    print(f"median steps {s['median_steps']}  ·  tokens {s['tokens_in']:,} in / {s['tokens_out']:,} out")
    print(f"\nreport: {run_dir / 'report.json'}")
    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    source = Path(args.repo).resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory", file=sys.stderr)
        return 2
    try:
        provider = make_provider("anthropic", args.model)
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    trace = Trace(task=source.name, provider=provider.name, model=provider.model)
    policy = Policy(mode=Mode.READ_ONLY if args.dry_run else Mode.EDIT)
    with Workspace.copy_of(source) as ws:
        before = ws.snapshot()
        Agent(provider, ws, policy, Budget(max_steps=args.max_steps)).run(args.issue, trace)
        after = ws.snapshot()
        trace.diff = unified_diff(before, after)
        out = trace.save(RUNS / "adhoc" / f"{trace.id}.json")
        print(trace.diff or "(no changes)")
        print(f"\noutcome: {trace.outcome}\nsummary: {trace.summary or '-'}\ntrace:   {out}")
        if args.apply and trace.diff and not args.dry_run:
            for path, content in after.items():
                if before.get(path) != content:
                    (source / path).parent.mkdir(parents=True, exist_ok=True)
                    (source / path).write_text(content)
            print("applied to", source)
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    for t in load_tasks():
        print(f"{t.id:<24} {t.category:<14} {t.difficulty:<7} {t.title}")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    shutil.rmtree(Path(args.out), ignore_errors=True)
    print("removed", args.out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mender", description="A code-repair agent with an honest benchmark.")
    parser.add_argument("--version", action="version", version=f"mender {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    bench = sub.add_parser("bench", help="run the benchmark and write a report")
    bench.add_argument("--provider", choices=["anthropic", "reference", "adversary"], default="anthropic")
    bench.add_argument("--model", help="model id, e.g. claude-sonnet-5-5")
    bench.add_argument("--task", action="append", help="run only this task (repeatable)")
    bench.add_argument("--max-steps", type=int, default=24)
    bench.add_argument("--out", default="runs")
    bench.set_defaults(func=cmd_bench)

    fix = sub.add_parser("fix", help="fix a bug in your own repository")
    fix.add_argument("repo")
    fix.add_argument("--issue", required=True, help="the bug report, in plain words")
    fix.add_argument("--model")
    fix.add_argument("--max-steps", type=int, default=24)
    fix.add_argument("--dry-run", action="store_true", help="read-only: diagnose without editing")
    fix.add_argument("--apply", action="store_true", help="write the fix back to your repository")
    fix.set_defaults(func=cmd_fix)

    tasks = sub.add_parser("tasks", help="list benchmark tasks")
    tasks.set_defaults(func=cmd_tasks)

    clean = sub.add_parser("clean", help="delete saved runs")
    clean.add_argument("--out", default="runs")
    clean.set_defaults(func=cmd_clean)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
