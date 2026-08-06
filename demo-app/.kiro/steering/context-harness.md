# Splice steering

When the user includes `/harness` or `@harness`, Splice injects an orchestrated bundle into the conversation.

## Your job

1. Use the orchestrated bundle as primary context.
2. Follow `recommendedAgent` and `workflow` from the bundle.
3. Suggest handoff to the other IDE when appropriate (Kiro triage → Cursor implement, or reverse).

## Shared session

State lives in `.splice/session.json` — same repo, both IDEs.

## Optional error capture

```bash
<command> 2>&1 | python3 scripts/splice-cli.py capture-error
```

Then `/harness` picks up `.splice/last-error.log` automatically.
