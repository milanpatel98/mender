"""Permissions: what the agent may do, decided outside the model.

A model can be talked into anything by the text it reads (a README, a code
comment, a test docstring). So the rules live here, in code, and the model
only ever sees the verdict. Every decision is recorded in the trace.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    READ_ONLY = "read-only"  # look around, run tests, change nothing
    EDIT = "edit"            # change source files, but never protected ones


READ_TOOLS = {"list_files", "read_file", "search", "run_tests", "finish"}
WRITE_TOOLS = {"edit_file", "create_file"}


@dataclass
class Decision:
    allowed: bool
    reason: str = ""


@dataclass
class Policy:
    mode: Mode = Mode.EDIT
    # Paths the agent may read but never write. Tests are the obvious case:
    # an agent that edits the test until it passes has not fixed anything.
    protected: list[str] = field(
        default_factory=lambda: ["tests/*", "tests/**", "test_*.py", "*_test.py", "conftest.py", "pyproject.toml", "setup.cfg"]
    )
    max_file_bytes: int = 200_000

    def is_protected(self, path: str) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.protected)

    def check(self, tool: str, args: dict) -> Decision:
        if tool in READ_TOOLS:
            return Decision(True)
        if tool not in WRITE_TOOLS:
            return Decision(False, f"unknown tool '{tool}'")
        if self.mode is Mode.READ_ONLY:
            return Decision(False, "this run is read-only; describe the fix instead")
        path = str(args.get("path", ""))
        if self.is_protected(path):
            return Decision(False, f"'{path}' is protected. Tests define correct behaviour; fix the code, not the test.")
        content = args.get("content") or args.get("new") or ""
        if len(content.encode()) > self.max_file_bytes:
            return Decision(False, "write is larger than the per-file limit")
        return Decision(True)
