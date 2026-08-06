# Splice (Claude Code)

This project uses **Splice** — a meta-tooling layer that shares orchestrated context between **Kiro**, **Cursor**, and **Claude Code**.

## On every turn

1. If `.splice/active-bundle.md` exists, **read it first**.
2. Do not re-paste errors or files already in the bundle.
3. Follow `recommendedAgent` and `workflow` from the bundle.

## Trigger

Type `/harness` or `@harness` in your prompt to refresh orchestration before Claude processes the task.

## Handoff

If `assistantsUsed` in the session includes another IDE, continue using the bundle — do not re-triage from scratch.

## Capture errors (optional)

```bash
npm test 2>&1 | python3 scripts/splice-cli.py capture-error
# then: /harness fix the failing test
```

## Orchestrator

Configured in `.splice/config.json`: `mock` (default) · `ollama` (local) · `bedrock` (cloud).

```bash
python3 scripts/splice-cli.py doctor
```
