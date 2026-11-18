# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

This folder holds documentation only. There is no `package.json`, `src/`, `.env`, `.gitignore`, or `.github/` workflow yet. The first build will need to scaffold a Trigger.dev project (`npx trigger.dev@latest init` or equivalent) before any of the commands below will work.

Files:
- `CLAUDE (1).md`: the full workflow spec for building automations. Claude Code does not auto-load it because of the filename. The essentials are repeated below.
- `trigger-ref.md`: Trigger.dev SDK v4 code patterns (tasks, schedules, waits, triggers, debounce, retries, Zod schema tasks).
- `.mcp.json`: registers the Trigger.dev MCP server (`npx trigger.dev@latest mcp --project-ref <ref> --dev-only`). Claude Code auto-loads it after a restart and approval of the project server.

## Commands

- Start local dev server: `npx trigger.dev@latest dev`
- Add a dependency: `npm install <pkg>` (add `-D @types/<pkg>` only if the package has no bundled types)
- No build, lint, or test scripts exist yet. There is no single-test command to document.

Prefer the Trigger.dev MCP tools over the CLI when they cover the task:
`mcp__trigger__trigger_task` (fire a test run), `mcp__trigger__wait_for_run_to_complete`, `mcp__trigger__get_run_details` (logs and errors), `mcp__trigger__list_runs`, `mcp__trigger__get_current_worker` (registered tasks), `mcp__trigger__deploy`.

## Architecture

Each automation is a set of Trigger.dev tasks, one folder per automation:

```
src/trigger/{automation-name}/
```

- Simple automations: one task file.
- Polling automations: an orchestrator (`schedules.task` with a cron) checks the source and dispatches one `processTask.trigger(...)` per new item, using an `idempotencyKey` so the same item is never processed twice. A separate processor task does the heavy work (API calls, LLM, posting output). See the orchestrator+processor pattern in `trigger-ref.md`.
- Tasks run on Trigger.dev infrastructure. Never run automation code as a plain Node script.

Each automation follows the same lifecycle: understand the idea → research APIs (auth, rate limits, free tiers) → clarify with the user → plan in plain English and get approval → build → set env vars → test locally → deploy → verify with run logs.

## Rules that span files

- **Language and HTTP:** TypeScript only, no Python or shell scripts. Use native `fetch`.
- **SDK:** use `@trigger.dev/sdk` (`task`, `schedules.task`, `schemaTask`). Never use `client.defineJob`, which is v2 and breaks the project.
- **Result handling:** `triggerAndWait()` and `batchTriggerAndWait()` return a `Result`. Check `result.ok` before reading `result.output`.
- **No `Promise.all`:** never wrap `triggerAndWait`, `batchTriggerAndWait`, or `wait.*` in `Promise.all`.
- **Imports:** relative imports between task files need the `.js` extension, e.g. `import { x } from "./process-item.js"`.
- **Schedules:** always ask the user for the frequency before choosing a cron. When polling, make the lookback window slightly longer than the interval (e.g. 25h for a daily cron).
- **Secrets:** every secret, ID, and token lives in `.env` and is read with `process.env`. Validate at the top of each task and throw if missing. Never log secret values or hardcode them, even in comments.
- **New env var:** add it to `.env` with a comment saying where to get it, then tell the user to add it to the Trigger.dev dashboard (Project → Environment Variables) for both staging and prod. Missing dashboard vars are the most common production failure.
- **`.env` must be in `.gitignore`** before any commit.

## Deploying

- Never deploy or push to production without the user's explicit approval. Wait for them to say so ("deploy", "ship it", "push it").
- Before deploying: local test run succeeded, all env vars are in the dashboard, and `.env` is gitignored.
- The workflow spec says deploys happen by pushing to `master`, with GitHub Actions running `.github/workflows/deploy.yml`. That file does not exist yet. Confirm the deploy path with the user before relying on it.
- After deploying: check `mcp__trigger__list_runs` for a successful first run, and confirm scheduled tasks appear in the dashboard's Schedules tab.

## Debugging a failed run

Read the error with `mcp__trigger__get_run_details`. Common causes, in order: env var missing from the dashboard, `.js` missing from an import path, or wrong auth header or key format for the API.
