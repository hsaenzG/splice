"""Local file store for IDE-integrated demos (no AWS required)."""

import json
import uuid
from pathlib import Path
from typing import Any

from shared.db import utc_now

DEFAULT_DIR = Path(".splice")


def harness_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".splice"


def session_path(root: Path | None = None) -> Path:
    return harness_dir(root) / "session.json"


def bundle_path(root: Path | None = None) -> Path:
    return harness_dir(root) / "active-bundle.md"


def load_session(root: Path | None = None) -> dict[str, Any] | None:
    path = session_path(root)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_session(session: dict[str, Any], root: Path | None = None) -> None:
    path = session_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2))


def ensure_session(assistant: str, project: str | None = None, root: Path | None = None) -> dict[str, Any]:
    from shared.config import load_config

    cfg = load_config(root)
    project = project or cfg.get("project") or (root or Path.cwd()).name
    existing = load_session(root)
    if existing:
        existing["assistant"] = assistant
        existing["updatedAt"] = utc_now()
        save_session(existing, root)
        return existing

    session = {
        "sessionId": str(uuid.uuid4()),
        "project": project,
        "assistant": assistant,
        "assistantsUsed": [assistant],
        "status": "active",
        "contextItems": [],
        "lastOrchestration": None,
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
    }
    save_session(session, root)
    return session


def add_context_items(items: list[dict], root: Path | None = None) -> dict[str, Any]:
    session = load_session(root)
    if not session:
        raise RuntimeError("No session. Run: python3 scripts/splice-cli.py init --assistant <cursor|kiro>")

    session.setdefault("contextItems", []).extend(items)
    assistant = session.get("assistant", "unknown")
    used = session.setdefault("assistantsUsed", [])
    if assistant not in used:
        used.append(assistant)
    session["updatedAt"] = utc_now()
    save_session(session, root)
    return session


def save_orchestration(result: dict[str, Any], root: Path | None = None) -> None:
    session = load_session(root)
    if not session:
        raise RuntimeError("No active session")
    session["lastOrchestration"] = result
    session["status"] = "orchestrated"
    session["updatedAt"] = utc_now()
    save_session(session, root)
    write_bundle_markdown(result, root)


def write_bundle_markdown(result: dict[str, Any], root: Path | None = None) -> Path:
    metrics = result.get("metrics", {})
    lines = [
        "# Splice — Active Bundle",
        "",
        f"- **Session:** `{result.get('sessionId', 'n/a')}`",
        f"- **Source assistant:** {result.get('sourceAssistant', 'n/a')}",
        f"- **Recommended agent:** `{result.get('recommendedAgent')}`",
        f"- **Workflow:** `{result.get('workflow')}`",
        f"- **Handoff:** {result.get('handoffRecommendation', 'none')}",
        f"- **Latency:** {result.get('latencyMs')}ms",
        f"- **Context reduction:** {metrics.get('contextReductionPct')}%",
        "",
        "## Reasoning",
        "",
        result.get("reasoning", ""),
        "",
        "## Context bundle (use this, ignore noise)",
        "",
    ]
    for i, item in enumerate(result.get("contextBundle", []), 1):
        meta = item.get("metadata") or {}
        if isinstance(meta, str):
            meta = {"path": meta}
        path = meta.get("path", item.get("type", "item")) if isinstance(meta, dict) else item.get("type", "item")
        lines.extend(
            [
                f"### {i}. [{item.get('type')}] {path} (relevance {item.get('relevanceScore', 0)})",
                "",
                "```",
                str(item.get("content", ""))[:1500],
                "```",
                "",
            ]
        )

    path = bundle_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path
