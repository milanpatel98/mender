"""The agent's tools: small, precise, and hard to misuse.

Design choices worth calling out:

* `edit_file` is search-and-replace on an exact, unique snippet, not a whole-
  file rewrite. Rewrites invite the model to silently drop code it did not
  read; a unique-match edit fails loudly instead.
* `read_file` returns line numbers, so the model can cite and target lines.
* `run_tests` is the only way to execute code. There is no general shell.
* Every tool returns plain text plus an `is_error` flag. Errors are feedback
  for the model, not exceptions that crash the run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .sandbox import SandboxError, Workspace, truncate

SCHEMAS = [
    {
        "name": "list_files",
        "description": "List every file in the repository.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Read a file with line numbers. Optionally pass start/end lines (1-based, inclusive).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer"},
                "end": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "search",
        "description": "Search all files for a regular expression. Returns path:line: text for each match.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace an exact snippet in a file. `old` must appear exactly once; include enough "
            "surrounding lines to make it unique. Preserve indentation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
    },
    {
        "name": "create_file",
        "description": "Create a new file. Fails if the file already exists; use edit_file for changes.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run the test suite with pytest. Optionally pass a test path or node id to run a subset.",
        "input_schema": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
        },
    },
    {
        "name": "finish",
        "description": "Call once the tests pass. Summarise the root cause and the fix in two or three sentences.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
]


@dataclass
class ToolResult:
    output: str
    is_error: bool = False


class Toolbox:
    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def call(self, name: str, args: dict) -> ToolResult:
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            return ToolResult(f"unknown tool '{name}'", True)
        try:
            return handler(**args)
        except TypeError as exc:
            return ToolResult(f"bad arguments for {name}: {exc}", True)
        except SandboxError as exc:
            return ToolResult(str(exc), True)

    # ---- handlers -------------------------------------------------------

    def _list_files(self) -> ToolResult:
        return ToolResult("\n".join(self.ws.files()) or "(empty repository)")

    def _read_file(self, path: str, start: int | None = None, end: int | None = None) -> ToolResult:
        lines = self.ws.read(path).splitlines()
        lo = max(1, start or 1)
        hi = min(len(lines), end or len(lines))
        width = len(str(hi))
        body = "\n".join(f"{n:>{width}}  {lines[n - 1]}" for n in range(lo, hi + 1))
        return ToolResult(truncate(body or "(empty file)", 12000))

    def _search(self, pattern: str) -> ToolResult:
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return ToolResult(f"invalid regex: {exc}", True)
        hits = []
        for rel in self.ws.files():
            try:
                text = self.ws.read(rel)
            except SandboxError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{rel}:{n}: {line.strip()}")
                    if len(hits) >= 80:
                        return ToolResult("\n".join(hits) + "\n... (stopped at 80 matches)")
        return ToolResult("\n".join(hits) or "no matches")

    def _edit_file(self, path: str, old: str, new: str) -> ToolResult:
        text = self.ws.read(path)
        count = text.count(old)
        if count == 0:
            near = _closest_line(text, old)
            hint = f" The closest line is: {near!r}" if near else ""
            return ToolResult(f"`old` was not found in {path}. Read the file again and copy the text exactly.{hint}", True)
        if count > 1:
            return ToolResult(f"`old` appears {count} times in {path}; include more surrounding lines.", True)
        self.ws.write(path, text.replace(old, new, 1))
        return ToolResult(f"edited {path}")

    def _create_file(self, path: str, content: str) -> ToolResult:
        if self.ws.resolve(path).exists():
            return ToolResult(f"{path} already exists; use edit_file", True)
        self.ws.write(path, content)
        return ToolResult(f"created {path}")

    def _run_tests(self, target: str | None = None) -> ToolResult:
        args = [target] if target else []
        if target:
            self.ws.resolve(target.split("::")[0])  # refuse paths outside the repo
        result = self.ws.pytest(*args)
        status = "PASSED" if result.ok else ("TIMED OUT" if result.timed_out else "FAILED")
        return ToolResult(f"{status} (exit {result.exit_code}, {result.duration_ms} ms)\n\n{truncate(result.output)}")

    def _finish(self, summary: str) -> ToolResult:
        return ToolResult("done")


def _closest_line(text: str, snippet: str) -> str | None:
    first = snippet.strip().splitlines()[0].strip() if snippet.strip() else ""
    if not first:
        return None
    best, score = None, 0
    for line in text.splitlines():
        common = len(set(first.split()) & set(line.split()))
        if common > score:
            best, score = line, common
    return best
