"""The agent loop, written by hand instead of borrowed from a framework.

    observe -> think -> act -> record, until the model calls `finish`,
    the step budget runs out, or the loop detects it is stuck.

Three safeguards matter more than the loop itself:

* Budgets. Steps and tokens are capped; an agent that never stops is a bill.
* Stuck detection. The same tool call three times in a row gets a nudge, and
  a fourth ends the run as `stuck` instead of burning the remaining budget.
* Context hygiene. Old tool outputs are compacted to a one-line stub once the
  history grows, so long runs keep the most recent evidence in view.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from .policy import Policy
from .providers import Provider
from .sandbox import Workspace
from .tools import SCHEMAS, Toolbox
from .trace import Trace

SYSTEM = """You are Mender, a careful software engineer fixing a bug in an unfamiliar repository.

How to work:
1. Reproduce first: run the tests and read the failure before changing anything.
2. Find the root cause. Read the code involved; do not guess from names alone.
3. Make the smallest change that fixes the cause, not just the symptom the test shows.
   Hidden tests will check the general behaviour, so do not special-case test inputs.
4. Never edit tests or configuration; they are protected and define correct behaviour.
5. Re-run the tests. When they pass, call `finish` with a short root-cause summary.

Be economical: read only what you need, and prefer one precise edit over many."""


@dataclass
class Budget:
    max_steps: int = 24
    max_tokens: int = 400_000
    keep_recent_tool_results: int = 6


class Agent:
    def __init__(self, provider: Provider, workspace: Workspace, policy: Policy | None = None, budget: Budget | None = None):
        self.provider = provider
        self.ws = workspace
        self.policy = policy or Policy()
        self.budget = budget or Budget()
        self.tools = Toolbox(workspace)

    def run(self, issue: str, trace: Trace) -> Trace:
        messages: list[dict] = [{"role": "user", "content": f"Issue report:\n\n{issue}\n\nThe repository is checked out. Start by running the tests."}]
        last_calls: list[str] = []
        used_tokens = 0
        nudged = False

        for step in range(1, self.budget.max_steps + 1):
            started = time.monotonic()
            reply = self.provider.complete(SYSTEM, messages, SCHEMAS)
            used_tokens += reply.input_tokens + reply.output_tokens
            thought = " ".join(b.text for b in reply.blocks if b.type == "text").strip()
            trace.add(
                "thought",
                step,
                output=thought,
                duration_ms=int((time.monotonic() - started) * 1000),
                tokens_in=reply.input_tokens,
                tokens_out=reply.output_tokens,
            )
            messages.append({"role": "assistant", "content": [b.to_api() for b in reply.blocks]})

            calls = [b for b in reply.blocks if b.type == "tool_use"]
            if not calls:
                # The model stopped talking to tools. Ask once; then give up.
                if nudged:
                    trace.add("note", step, output="still no tool call after a nudge; giving up")
                    trace.outcome = "gave_up"
                    return trace
                nudged = True
                trace.add("note", step, output="no tool call; prompting the agent to continue")
                messages.append({"role": "user", "content": "Use a tool to continue, or call finish if the tests pass."})
                continue
            nudged = False

            results = []
            for call in calls:
                if call.name == "finish":
                    trace.summary = str(call.input.get("summary", ""))
                    trace.add("final", step, tool="finish", input=call.input, output=trace.summary)
                    trace.outcome = "finished"
                    return trace

                signature = call.name + json.dumps(call.input, sort_keys=True)
                last_calls = (last_calls + [signature])[-4:]
                repeats = sum(1 for s in last_calls if s == signature)

                decision = self.policy.check(call.name, call.input)
                t0 = time.monotonic()
                if not decision.allowed:
                    output, is_error = f"Permission denied: {decision.reason}", True
                    trace.add("denied", step, tool=call.name, input=call.input, output=output, is_error=True)
                else:
                    result = self.tools.call(call.name, call.input)
                    output, is_error = result.output, result.is_error
                    trace.add(
                        "tool",
                        step,
                        tool=call.name,
                        input=call.input,
                        output=output,
                        is_error=is_error,
                        duration_ms=int((time.monotonic() - t0) * 1000),
                    )
                if repeats == 3:
                    output += "\n\nNote: you have made this exact call three times. Try a different approach."
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": output, "is_error": is_error})

            messages.append({"role": "user", "content": results})
            self._compact(messages)

            if last_calls.count(last_calls[-1]) >= 4:
                trace.add("note", step, output="same call four times in a row; stopping as stuck")
                trace.outcome = "stuck"
                return trace
            if used_tokens > self.budget.max_tokens:
                trace.add("note", step, output=f"token budget exceeded ({used_tokens})")
                trace.outcome = "over_budget"
                return trace
        else:
            trace.add("note", self.budget.max_steps, output="step budget exhausted")
            trace.outcome = "out_of_steps"
        return trace

    def _compact(self, messages: list[dict]) -> None:
        """Replace all but the most recent tool outputs with a short stub."""
        seen = 0
        for message in reversed(messages):
            if message["role"] != "user" or not isinstance(message["content"], list):
                continue
            for block in message["content"]:
                if block.get("type") != "tool_result":
                    continue
                seen += 1
                if seen > self.budget.keep_recent_tool_results and len(block["content"]) > 300:
                    first = block["content"].splitlines()[0][:120]
                    block["content"] = f"[earlier output compacted; began: {first}]"
