# Next Iterations — Splice

Roadmap oriented toward a healthy open-source project. Community adoption is the north star.

---

## Milestone 2 — Community Foundation (current focus)

The prerequisite for accepting contributions. Without this, PRs break things and contributors get frustrated.

1. **Test suite** — pytest coverage for `orchestrator.py`, `collect.py`, `store.py`, `config.py`; CI runs on every PR
2. **GitHub Actions** — lint (ruff), type-check (mypy), test on push/PR; badge in README
3. **CONTRIBUTING.md** — dev setup, how to add an IDE adapter, how to add an orchestrator backend, PR checklist
4. **Semantic versioning + CHANGELOG.md** — so the community can depend on the project and track what changed
5. ~~**IDE hooks (Kiro + Cursor + Claude Code)**~~ — done
6. ~~**Project config**~~ — `.splice/config.json` per project

---

## Milestone 3 — IDE Ecosystem

The community is already asking about Windsurf, Zed, Cline, and Continue. This milestone makes Splice extensible so adapters can be contributed without touching core.

7. **Adapter interface** — define a clean contract for IDE adapters (hook scripts + bundle reader); document in CONTRIBUTING.md
8. **Windsurf adapter** — high demand; follows same hook pattern as Cursor
9. **Zed adapter** — growing community, LSP-based hook integration
10. **MCP server mode** — expose Splice as an MCP tool so any MCP-compatible IDE (Claude Code, Zed, Continue) can use it natively without per-IDE hook scripts

---

## Milestone 4 — Distribution & Documentation

Makes the tool usable without cloning the repo.

11. ~~**`pip install splice-cli`**~~ — done; `splice setup` installs hooks, `splice doctor/orchestrate/handoff/status` work globally
12. **Publish to PyPI** — `twine upload` so `pip install splice-cli` works for everyone
13. **Docs site** — mkdocs or Docusaurus; covers install, config reference, IDE adapters, orchestrator backends
14. **GitHub Discussions** — replace issues-as-support with a structured forum for Q&A and ideas
15. **`npm install -g @splice/cli`** — thin JS wrapper that delegates to the Python CLI; for developers who prefer npm. Deferred until PyPI distribution is stable and there is community demand.

---

## Milestone 5 — Intelligence

Smarter orchestration once the foundation and community are solid.

15. **Embedding-based dedup** — vector fingerprints to collapse duplicate file contexts across sessions
16. **Multi-agent routing** — return a *sequence* of agent handoffs (debugger → implementer → reviewer)
17. **Prompt-aware file scoring** — rank files by semantic relevance to the current prompt, not just by type

---

## Milestone 6 — Platform (optional, for teams)

For organizations running Splice across multiple repos and contributors. Community-driven; only if there is demand.

18. **Cross-session memory** — session summaries with TTL; pick up context across days
19. **Webhook outbound** — push bundle to external agents or CI pipelines
20. **Policy layer** — redact secrets/PII before orchestration; audit log

---

## Explicitly deferred

- Multi-tenant billing
- Custom model fine-tuning
- Full agent execution (Splice orchestrates context; assistants execute)
- AWS-specific cost dashboard (too opinionated for a cross-platform OSS tool)
- "Build vs. buy" scorecard (was internal framing, not relevant for the community)
