// A task drawn as a swatch of indigo cloth with a tear.
//
// Each step the agent took becomes a running stitch across the tear.
// Gold thread closes a solved tear; a tampered one is sewn in red;
// an overfit fix closes only half; denied cheat attempts are red crosses.

const SIZE = 120;

function seeded(text) {
  let h = 2166136261;
  for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

function tearPath(id) {
  const rand = seeded(id);
  const start = { x: 18 + rand() * 12, y: 28 + rand() * 18 };
  const end = { x: 90 + rand() * 12, y: 74 + rand() * 18 };
  const points = [start];
  const segments = 7;
  for (let i = 1; i < segments; i++) {
    const t = i / segments;
    points.push({
      x: start.x + (end.x - start.x) * t + (rand() - 0.5) * 8,
      y: start.y + (end.y - start.y) * t + (rand() - 0.5) * 10,
    });
  }
  points.push(end);
  return { points, start, end };
}

function pointAt(points, t) {
  const scaled = t * (points.length - 1);
  const i = Math.min(points.length - 2, Math.floor(scaled));
  const f = scaled - i;
  const a = points[i];
  const b = points[i + 1];
  return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, dx: b.x - a.x, dy: b.y - a.y };
}

export default function Swatch({ task, animate }) {
  const { points } = tearPath(task.id);
  const line = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const verdict = task.verdict;
  const closed = verdict === "solved" ? 1 : verdict === "overfit" || verdict === "tampered" ? 0.5 : 0;

  const count = Math.max(2, Math.min(12, task.steps || 2));
  const stitches = Array.from({ length: count }, (_, i) => {
    const t = (i + 0.5) / count;
    const p = pointAt(points, t);
    const len = Math.hypot(p.dx, p.dy) || 1;
    const nx = -p.dy / len;
    const ny = p.dx / len;
    const reach = 7;
    return {
      t,
      d: `M${(p.x - nx * reach).toFixed(1)} ${(p.y - ny * reach).toFixed(1)} L${(p.x + nx * reach).toFixed(1)} ${(p.y + ny * reach).toFixed(1)}`,
    };
  });

  const crosses = Array.from({ length: Math.min(3, task.denied || 0) }, (_, i) => {
    const p = pointAt(points, 0.2 + i * 0.3);
    return { x: p.x + 14, y: p.y - 12 };
  });

  const threadClass = verdict === "tampered" ? "thread thread-red" : verdict === "solved" || verdict === "overfit" ? "thread thread-gold" : "thread";

  return (
    <svg className={`swatch ${animate ? "swatch-animate" : ""}`} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={`${task.title}: ${verdict}, ${task.steps} steps`}>
      <rect className="cloth" width={SIZE} height={SIZE} rx="3" />
      <g className="weave">
        {Array.from({ length: 11 }, (_, i) => (
          <path key={i} d={`M6 ${10 + i * 10} H${SIZE - 6}`} />
        ))}
      </g>
      <path className="tear" d={line} strokeWidth={closed === 1 ? 1.5 : closed ? 3.5 : 6} />
      {closed < 1 && closed > 0 && (
        <path className="tear-mended" d={line} pathLength="1" strokeDasharray={`${closed} 1`} />
      )}
      <g className={threadClass}>
        {stitches.map((s, i) => {
          const sewn = closed === 0 ? s.t < 0.35 : s.t <= closed + 0.001;
          return (
            <path
              key={i}
              d={s.d}
              pathLength="1"
              className={sewn ? "" : "loose"}
              style={animate ? { animationDelay: `${120 + i * 45}ms` } : undefined}
            />
          );
        })}
      </g>
      <g className="denied">
        {crosses.map((c, i) => (
          <path key={i} d={`M${c.x - 3.5} ${c.y - 3.5} l7 7 M${c.x + 3.5} ${c.y - 3.5} l-7 7`} />
        ))}
      </g>
    </svg>
  );
}
