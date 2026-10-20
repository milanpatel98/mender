import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The viewer reads benchmark output straight from ../runs, so `mender bench`
// followed by a browser refresh is the whole workflow. No copy step.
export default defineConfig({
  plugins: [react()],
  base: "./",
  publicDir: "../runs",
  server: { port: 5178 },
});
