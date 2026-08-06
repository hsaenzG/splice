# Splice — Install in your project

Add shared Kiro + Cursor + Claude Code context orchestration to **any** repo in under a minute.

## One-line install

From this repo:

```bash
bash /path/to/splice/scripts/install-splice.sh /path/to/your-project
```

Or from your project (clone Splice first):

```bash
git clone https://github.com/hsaenzG/splice.git /tmp/splice
bash /tmp/splice/scripts/install-splice.sh .
```

## What gets installed

| Path | Purpose |
|------|---------|
| `scripts/splice-cli.py` | CLI: init, orchestrate, handoff, capture-error |
| `src/shared/` | Orchestration, config, collection logic |
| `integrations/hooks/` | Kiro + Cursor + Claude Code hook scripts |
| `.splice/config.json` | Per-project capture rules |
| `.cursor/hooks.json` + rules | Cursor integration |
| `.kiro/hooks/` + steering | Kiro integration |
| `.claude/settings.json` + `CLAUDE.md` | Claude Code integration |

## Configure your project

Edit `.splice/config.json`:

```json
{
  "project": "my-app",
  "captureGitDiff": true,
  "includePaths": ["src/**/*.ts"],
  "errorSources": [".splice/last-error.log"],
  "extraFiles": ["README.md"],
  "promptPathPatterns": true
}
```

| Field | What it does |
|-------|----------------|
| `includePaths` | Glob patterns — files to include on every `/harness` |
| `errorSources` | Log files treated as `error` context |
| `extraFiles` | Always include these paths |
| `promptPathPatterns` | Extract `src/foo.ts` from your prompt automatically |
| `captureGitDiff` | Include `git diff` (scoped to detected files when possible) |

## Daily workflow

### 1. Capture an error (optional)

```bash
npm test 2>&1 | python3 scripts/splice-cli.py capture-error
# or
pytest 2>&1 | python3 scripts/splice-cli.py capture-error
```

### 2. Triage in Kiro or Claude Code

```
/harness debug the failing test — focus on auth module
```

### 3. Implement in Cursor or Claude Code (same repo, same session)

```
/harness apply the fix using the orchestrated bundle
```

### 4. Check metrics

```bash
python3 scripts/splice-cli.py status
cat .splice/active-bundle.md
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SPLICE_FILES` | Comma-separated extra files: `src/a.ts,src/b.ts` |
| `SPLICE_ORCHESTRATOR` | `mock` · `ollama` · `bedrock` |
| `OLLAMA_MODEL` | Override Ollama model (default `llama3.2`) |
| `OLLAMA_BASE_URL` | Default `http://localhost:11434` |

## Orchestrator modes

See **[ORCHESTRATORS.md](../ORCHESTRATORS.md)** for full guide.

```json
{ "orchestrator": "mock" }
{ "orchestrator": "ollama", "ollama": { "model": "llama3.2" } }
{ "orchestrator": "bedrock" }
```

```bash
ollama pull llama3.2
python3 scripts/splice-cli.py doctor
```

## What is NOT tied to a specific bug

- Session sharing (`.splice/session.json`)
- `/harness` trigger in Kiro, Cursor, and Claude Code
- Handoff between any combination of the three
- Mock orchestration routing (debugger / architect / implementer)
- Git diff + prompt path detection + error log capture

## Optional: sample demo in this repo

The `demo-app/` folder is an **optional example** (UserList bug). Enable it in config:

```json
{
  "errorSources": [".splice/last-error.log", "demo-app/UserList.tsx.error.log"],
  "extraFiles": ["demo-app/UserList.tsx"]
}
```

## AWS deploy (optional)

See root `README.md` for CDK/API Gateway path — not required for local IDE hooks.

## Uninstall

Remove: `scripts/splice-cli.py`, `src/shared/`, `integrations/hooks/`, `.splice/`, and Splice entries in `.cursor/`, `.kiro/`, and `.claude/`.
