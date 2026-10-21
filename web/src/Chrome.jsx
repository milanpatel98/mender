export function Bar({ dark }) {
  return (
    <header className={`bar ${dark ? "bar-dark" : ""}`}>
      <a href="#/" className="bar-name">
        Mender – 01
      </a>
      <a href="https://github.com/milanpatel98/mender" className="bar-link">
        Source
      </a>
    </header>
  );
}

export function Footer({ dark }) {
  return (
    <footer className={`foot ${dark ? "foot-dark" : ""}`}>
      <p>Built by Milan Patel. Original tasks, harness and grader. The agent loop uses no framework.</p>
      <p>
        Run your own model: <code>mender bench --model &lt;id&gt;</code>
      </p>
    </footer>
  );
}
