# Demo — Kiro, Cursor & Claude Code

Walkthrough to see the **same meta-tooling layer** work across the AI coding tools you use.

## What you'll see

| Tool | Role in demo | How Splice injects context |
|------|--------------|----------------------------|
| **Kiro** | Triage / debug | `UserPromptSubmit` hook → stdout appended to prompt |
| **Cursor** | Implementation | `sessionStart` + rule reads `.splice/active-bundle.md` |
| **Claude Code** | Refactor / implement | `SessionStart` + `UserPromptSubmit` → `additionalContext` |
| **Shared** | Session state | `.splice/session.json` in repo |

## 0. Pre-flight (terminal)

```bash
cd "/path/to/splice"

# Simulate Kiro → Cursor handoff (no IDE needed)
python3 scripts/demo-dual-ide.py

# Or step by step:
python3 scripts/splice-cli.py init --assistant kiro
python3 scripts/splice-cli.py orchestrate --assistant kiro --prompt "/harness debug UserList crash" --always
python3 scripts/splice-cli.py handoff --from kiro --to cursor
python3 scripts/splice-cli.py handoff --from cursor --to claude
```

Open `.splice/active-bundle.md` — that's the reduced context all tools should use.

---

## 1. Kiro — triage with `/harness`

1. Open this repo in **Kiro**
2. Confirm hooks loaded: Agent Hooks panel → `splice-orchestrate` enabled
3. Confirm steering: `.kiro/steering/splice.md`
4. In agent chat, send:

```
/harness debug the crash in demo-app/UserList.tsx — API now returns { items: [] }
```

**Expected:** Hook runs → orchestration appended → agent routes as **debugger**.

**Check:** `.splice/session.json` shows `"assistantsUsed": ["kiro"]`

---

## 2. Cursor — implement with same session

1. Open the **same repo** in **Cursor** (don't delete `.splice/`)
2. Restart Cursor if hooks don't load (`.cursor/hooks.json`)
3. New Agent chat — `sessionStart` hook initializes session
4. Send:

```
/harness fix demo-app/UserList.tsx using the orchestrated bundle — use data?.items
```

**Expected:** Bundle refreshed; rule reads `active-bundle.md`; no re-paste of error log.

**Check:** `assistantsUsed` includes `kiro` and `cursor`

---

## 3. Claude Code — continue or refactor

1. In the **same repo**, run `claude` (CLI) from project root
2. Hooks load from `.claude/settings.json` — project-level, committable
3. On session start, Splice injects instructions + current bundle via `SessionStart`
4. Send:

```
/harness refactor UserList.tsx to handle empty items gracefully using the bundle
```

**Expected:**
- `UserPromptSubmit` hook runs only when `/harness` is in the prompt (fast no-op otherwise)
- JSON `additionalContext` with orchestration summary injected into Claude's context
- `.claude/CLAUDE.md` reinforces reading `active-bundle.md`

**Check:** `assistantsUsed` includes `claude`

**Test hook without Claude Code:**

```bash
echo '{"prompt":"/harness debug"}' | bash integrations/hooks/claude-orchestrate.sh
# Should output hookSpecificOutput JSON

echo '{"prompt":"hello"}' | bash integrations/hooks/claude-orchestrate.sh
# Should exit silently in ~50ms
```

---

## 4. Compare metrics

```bash
cat .splice/session.json | python3 -m json.tool
cat .splice/active-bundle.md
```

| Metric | Target |
|--------|--------|
| `contextReductionPct` | ≥ 30% |
| `latencyMs` | < 3000 (mock) · ~7s OK (Ollama) |
| `handoffRecommendation` | Mentions cross-IDE handoff |

---

## 5. Optional — AWS API

If deployed (`./scripts/deploy.sh`):

```bash
export SPLICE_URL="https://YOUR_API.execute-api.region.amazonaws.com/prod"
```

Hooks work locally by default; API mode is Milestone 2.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Kiro chat spins forever | Reload Kiro; ensure hook uses stdin timeout (not blocking `cat`) |
| Kiro hook doesn't fire | Enable hook in Agent Hooks panel; prompt must include `/harness` |
| Cursor ignores bundle | Ensure rule `splice.mdc` is active |
| Claude Code slow on every prompt | Hook should no-op without `/harness` — update `claude-orchestrate.sh` |
| Claude hook timeout | Increase `timeout` in `.claude/settings.json` (Ollama ~90s) |
| Empty session | `python3 scripts/splice-cli.py init --assistant claude` |
| Hooks not loading | Restart IDE/CLI; `chmod +x integrations/hooks/*.sh` |

---

## Files for multi-IDE integration

```
.claude/settings.json
.claude/CLAUDE.md
.cursor/hooks.json
.cursor/rules/splice.mdc
.kiro/hooks/splice.json
.kiro/steering/splice.md
integrations/hooks/
scripts/splice-cli.py
scripts/demo-dual-ide.py
demo-app/
```
