import { defineConfig } from "@trigger.dev/sdk";

// The CLI evaluates this file before it reads .env, so load it here (does not override existing env vars).
try {
  process.loadEnvFile(".env");
} catch {
  // No .env file (for example on CI): fall back to variables already in the environment.
}

const project = process.env.TRIGGER_PROJECT_REF;
if (!project) {
  throw new Error(
    "Missing TRIGGER_PROJECT_REF. Add it to .env (Trigger.dev dashboard -> Project settings -> Project ref, starts with proj_)."
  );
}

export default defineConfig({
  project,
  dirs: ["./src/trigger"],
  maxDuration: 3600,
  retries: {
    enabledInDev: false,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 2000,
      maxTimeoutInMs: 30_000,
      factor: 2,
      randomize: true,
    },
  },
});
