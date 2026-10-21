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
      <p>© 2026 Milan Patel</p>
      <p>
        <a href="https://github.com/milanpatel98/mender/blob/main/LICENSE">MIT License</a>
      </p>
    </footer>
  );
}
