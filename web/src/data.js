// Small data layer: fetch JSON written by `mender bench`, with a tiny cache.

const cache = new Map();

export async function getJSON(path) {
  if (cache.has(path)) return cache.get(path);
  const promise = fetch(path).then((res) => {
    if (!res.ok) throw new Error(`${path}: ${res.status}`);
    return res.json();
  });
  cache.set(path, promise);
  promise.catch(() => cache.delete(path));
  return promise;
}

export const loadIndex = () => getJSON("index.json");
export const loadReport = (runId) => getJSON(`${runId}/report.json`);
export const loadTrace = (runId, taskId) => getJSON(`${runId}/traces/${taskId}.json`);

export const VERDICT_TEXT = {
  solved: "Solved. The visible tests pass, the hidden tests pass, and no protected file was changed.",
  overfit: "Overfit. The visible tests pass, but the hidden tests fail, so the fix only fits the examples it saw.",
  tampered: "Tampered. A protected file changed. Tests were restored before grading, so this cannot count as a fix.",
  unsolved: "Unsolved. The visible tests still fail.",
  error: "Error. The run stopped because the model provider failed.",
};

export const VERDICT_SHORT = {
  solved: "Solved",
  overfit: "Overfit",
  tampered: "Tampered",
  unsolved: "Unsolved",
  error: "Error",
};

export function describeRun(run) {
  if (run.provider === "reference") return "Reference fixes replayed through the full harness";
  if (run.provider === "adversary") return "Scripted cheater trying to disable the tests";
  return run.model;
}

// Hash routing: #/<runId> and #/<runId>/<taskId>
export function parseHash(hash) {
  const [runId = "", taskId = ""] = hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  return { runId, taskId };
}

export const toHash = (runId, taskId) =>
  "#/" + [runId, taskId].filter(Boolean).map(encodeURIComponent).join("/");

export const pct = (x) => `${Math.round(x * 100)}%`;
export const seconds = (ms) => `${(ms / 1000).toFixed(1)} s`;
