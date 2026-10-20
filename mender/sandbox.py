"""The sandbox: an isolated copy of a repository the agent is allowed to touch.

Three layers keep the agent contained:

1. Filesystem: every path is resolved and must stay inside the workspace root.
   Symlinks that point outside are refused, so `../../etc/passwd` and a planted
   link both fail the same check.
2. Process: commands come from an allowlist, run with a scrubbed environment
   (no API keys or tokens leak into child processes), a wall-clock timeout,
   and, on POSIX, kernel resource limits on CPU time, memory and file size.
3. Output: everything returned to the model is truncated, so a runaway test
   cannot flood the context window.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

IGNORED = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}

# Environment variables a child process is allowed to inherit. Everything
# else (ANTHROPIC_API_KEY, GH_TOKEN, AWS_*, ...) is dropped.
SAFE_ENV = {"PATH", "LANG", "LC_ALL", "HOME", "TMPDIR", "SYSTEMROOT", "TZ"}


class SandboxError(Exception):
    """Raised when an action would escape or abuse the sandbox."""


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    output: str
    duration_ms: int
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def truncate(text: str, limit: int = 6000) -> str:
    """Keep the head and tail of long output; the middle is rarely the clue."""
    if len(text) <= limit:
        return text
    head = text[: limit * 2 // 3]
    tail = text[-limit // 3 :]
    dropped = len(text) - len(head) - len(tail)
    return f"{head}\n\n... [{dropped} characters truncated] ...\n\n{tail}"


def _limit_resources(cpu_seconds: int, memory_mb: int) -> None:  # pragma: no cover - runs in child
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    mem = memory_mb * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    except (ValueError, OSError):
        pass  # macOS does not support RLIMIT_AS; CPU and file limits still apply
    resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
    os.setsid()  # own process group, so a timeout can kill grandchildren too


class Workspace:
    """A throwaway copy of a repository, plus safe file and process access."""

    def __init__(self, root: Path, *, owned: bool = False):
        self.root = root.resolve()
        self._owned = owned

    @classmethod
    def copy_of(cls, source: Path) -> "Workspace":
        tmp = Path(tempfile.mkdtemp(prefix="mender-"))
        dest = tmp / "repo"
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns(*IGNORED), symlinks=True)
        return cls(dest, owned=True)

    def cleanup(self) -> None:
        if self._owned:
            shutil.rmtree(self.root.parent, ignore_errors=True)

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()

    # ---- filesystem -----------------------------------------------------

    def resolve(self, relative: str) -> Path:
        if not relative or "\x00" in relative:
            raise SandboxError("empty or invalid path")
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise SandboxError(f"path escapes the workspace: {relative}")
        return candidate

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def files(self) -> list[str]:
        out = []
        for path in sorted(self.root.rglob("*")):
            if any(part in IGNORED for part in path.relative_to(self.root).parts):
                continue
            if path.is_file():
                out.append(path.relative_to(self.root).as_posix())
        return out

    def read(self, relative: str) -> str:
        path = self.resolve(relative)
        if not path.is_file():
            raise SandboxError(f"no such file: {relative}")
        return path.read_text(encoding="utf-8", errors="replace")

    def write(self, relative: str, content: str) -> None:
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def snapshot(self) -> dict[str, str]:
        """Path -> content for every text file; used for diffs and tamper checks."""
        snap = {}
        for rel in self.files():
            try:
                snap[rel] = (self.root / rel).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        return snap

    # ---- processes ------------------------------------------------------

    def run(
        self,
        argv: list[str],
        *,
        timeout: float = 60,
        cpu_seconds: int = 60,
        memory_mb: int = 1024,
    ) -> CommandResult:
        env = {k: v for k, v in os.environ.items() if k in SAFE_ENV}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONHASHSEED"] = "0"
        preexec = None
        if os.name == "posix":
            preexec = lambda: _limit_resources(cpu_seconds, memory_mb)  # noqa: E731

        started = time.monotonic()
        proc = subprocess.Popen(
            argv,
            cwd=self.root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            preexec_fn=preexec,
        )
        try:
            out, _ = proc.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            self._kill(proc)
            out, _ = proc.communicate()
            timed_out = True
        elapsed = int((time.monotonic() - started) * 1000)
        return CommandResult(argv, proc.returncode if not timed_out else -9, out or "", elapsed, timed_out)

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        if os.name == "posix":
            import signal

            try:
                os.killpg(proc.pid, signal.SIGKILL)
                return
            except ProcessLookupError:
                return
        proc.kill()

    def pytest(self, *args: str, timeout: float = 60) -> CommandResult:
        return self.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args], timeout=timeout)
