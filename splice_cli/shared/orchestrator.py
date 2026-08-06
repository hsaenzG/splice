"""Context orchestration — mock, Ollama (local), or Bedrock (cloud)."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from splice_cli.shared.config import load_config

VALID_ORCHESTRATORS = ("mock", "ollama", "bedrock")


def resolve_orchestrator(root: Path | None = None) -> str:
    """Pick backend: env > legacy MOCK_BEDROCK > config.json."""
    env = os.environ.get("SPLICE_ORCHESTRATOR", "").strip().lower()
    if env in VALID_ORCHESTRATORS:
        return env
    if os.environ.get("MOCK_BEDROCK", "").lower() == "false":
        return "bedrock"
    cfg = load_config(root)
    mode = str(cfg.get("orchestrator", "mock")).lower()
    return mode if mode in VALID_ORCHESTRATORS else "mock"


def orchestrate_context(
    session_id: str,
    items: list[dict],
    assistant: str = "cursor",
    assistants_used: list | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    mode = resolve_orchestrator(root)

    if mode == "ollama":
        result = _ollama_orchestration(session_id, items, assistant, assistants_used, root)
    elif mode == "bedrock":
        result = _bedrock_orchestration(session_id, items, assistant, assistants_used, root)
    else:
        result = _mock_orchestration(session_id, items, assistant, assistants_used)

    result["orchestrator"] = mode
    result["latencyMs"] = round((time.perf_counter() - start) * 1000, 2)
    return result


def check_ollama(root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(root)
    ollama = cfg.get("ollama", {})
    base = os.environ.get("OLLAMA_BASE_URL", ollama.get("baseUrl", "http://localhost:11434")).rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", ollama.get("model", "llama3.2"))
    out: dict[str, Any] = {"baseUrl": base, "model": model, "reachable": False, "models": []}

    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        out["reachable"] = True
        out["models"] = [m.get("name") for m in data.get("models", [])]
        out["modelAvailable"] = any(model in (m or "") for m in out["models"])
    except Exception as exc:
        out["error"] = str(exc)
    return out


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------


def _mock_orchestration(
    session_id: str,
    items: list[dict],
    assistant: str = "cursor",
    assistants_used: list | None = None,
) -> dict[str, Any]:
    assistants_used = assistants_used or [assistant]
    by_type: dict[str, list] = {}
    for item in items:
        by_type.setdefault(item.get("type", "note"), []).append(item)

    has_errors = "error" in by_type
    has_diff = "diff" in by_type
    file_count = len(by_type.get("file", []))

    if has_errors and has_diff:
        primary_agent, workflow, priority = "debugger", "debug-with-context", ["error", "diff", "file"]
    elif has_errors:
        primary_agent, workflow, priority = "debugger", "error-triage", ["error", "file"]
    elif file_count > 3:
        primary_agent, workflow, priority = "architect", "scope-review", ["file", "note"]
    else:
        primary_agent, workflow, priority = "implementer", "focused-edit", ["file", "diff", "note", "error"]

    handoff = _handoff_recommendation(assistant, assistants_used)
    bundled = _build_context_bundle(items, priority)
    metrics = _compute_metrics(items, bundled)

    return {
        "sessionId": session_id,
        "sourceAssistant": assistant,
        "assistantsUsed": assistants_used,
        "recommendedAgent": primary_agent,
        "workflow": workflow,
        "handoffRecommendation": handoff,
        "contextPriority": priority,
        "contextBundle": bundled,
        "reasoning": (
            f"Detected {len(items)} context items across {len(by_type)} types from '{assistant}'. "
            f"Routing to '{primary_agent}' via '{workflow}'. "
            f"Context reduced by {metrics['contextReductionPct']}%. {handoff}"
        ),
        "metrics": metrics,
        "source": "mock",
    }


# ---------------------------------------------------------------------------
# LLM backends (Ollama + Bedrock)
# ---------------------------------------------------------------------------


def _llm_prompt(session_id: str, items: list[dict]) -> str:
    summary = [
        {"type": i.get("type"), "preview": str(i.get("content", ""))[:300]}
        for i in items[:12]
    ]
    return f"""You are a meta-tooling orchestrator above AI coding assistants (Kiro, Cursor, Claude Code).
Given session {session_id} and these context items, return JSON only with:
- recommendedAgent: one of debugger|architect|implementer|reviewer
- workflow: short snake_case workflow name
- contextPriority: ordered list of context types (error, diff, file, note)
- reasoning: 2 sentences max
- contextBundle: top 5 most relevant items with type, content (truncated), metadata (optional), relevanceScore (0-1)

Context items:
{json.dumps(summary, indent=2)}
"""


def _ollama_orchestration(
    session_id: str,
    items: list[dict],
    assistant: str,
    assistants_used: list | None,
    root: Path | None,
) -> dict[str, Any]:
    cfg = load_config(root)
    ollama = cfg.get("ollama", {})
    base = os.environ.get("OLLAMA_BASE_URL", ollama.get("baseUrl", "http://localhost:11434")).rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", ollama.get("model", "llama3.2"))
    timeout = int(ollama.get("timeoutSeconds", 60))

    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": _llm_prompt(session_id, items)}],
            "stream": False,
            "format": "json",
        }
    ).encode()

    try:
        req = urllib.request.Request(
            f"{base}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        text = data.get("message", {}).get("content", "{}")
        parsed = _parse_llm_json(text)
        return _finalize_llm_result(parsed, session_id, items, assistant, assistants_used, "ollama", model)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        fallback = _mock_orchestration(session_id, items, assistant, assistants_used)
        fallback["source"] = "ollama-fallback"
        fallback["reasoning"] = f"Ollama unavailable ({exc}). Mock routing used. " + fallback["reasoning"]
        return fallback


def _bedrock_orchestration(
    session_id: str,
    items: list[dict],
    assistant: str,
    assistants_used: list | None,
    root: Path | None,
) -> dict[str, Any]:
    import boto3

    cfg = load_config(root)
    bedrock_cfg = cfg.get("bedrock", {})
    model_id = os.environ.get(
        "BEDROCK_MODEL_ID", bedrock_cfg.get("modelId", "amazon.nova-lite-v1:0")
    )

    body = json.dumps(
        {
            "messages": [{"role": "user", "content": [{"text": _llm_prompt(session_id, items)}]}],
            "inferenceConfig": {"maxTokens": 1024, "temperature": 0.2},
        }
    )

    try:
        client = boto3.client("bedrock-runtime")
        resp = client.invoke_model(modelId=model_id, body=body)
        payload = json.loads(resp["body"].read())
        text = payload.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "{}")
        parsed = _parse_llm_json(text)
        result = _finalize_llm_result(parsed, session_id, items, assistant, assistants_used, "bedrock", model_id)
        return result
    except Exception as exc:
        fallback = _mock_orchestration(session_id, items, assistant, assistants_used)
        fallback["source"] = "bedrock-fallback"
        fallback["reasoning"] = f"Bedrock unavailable ({exc}). Mock routing used. " + fallback["reasoning"]
        return fallback


def _parse_llm_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise json.JSONDecodeError("No JSON object in LLM response", text, 0)


def _finalize_llm_result(
    parsed: dict,
    session_id: str,
    items: list[dict],
    assistant: str,
    assistants_used: list | None,
    source: str,
    model: str,
) -> dict:
    assistants_used = assistants_used or [assistant]
    priority = parsed.get("contextPriority") or ["error", "diff", "file", "note"]
    bundled = parsed.get("contextBundle") or _build_context_bundle(items, priority)
    bundled = [_normalize_bundle_item(i) for i in bundled]

    parsed["sessionId"] = session_id
    parsed["sourceAssistant"] = assistant
    parsed["assistantsUsed"] = assistants_used
    parsed["contextBundle"] = bundled
    parsed["contextPriority"] = priority
    parsed["handoffRecommendation"] = parsed.get("handoffRecommendation") or _handoff_recommendation(
        assistant, assistants_used
    )
    parsed["metrics"] = _compute_metrics(items, bundled)
    parsed["source"] = source
    parsed["model"] = model
    return parsed


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _handoff_recommendation(current: str, used: list[str]) -> str:
    others = [a for a in used if a != current]
    if not others:
        if current == "kiro":
            return "After triage in Kiro, hand off implementation to Cursor for fast inline edits."
        if current == "cursor":
            return "After implementation in Cursor, hand off architecture review to Kiro specs/steering."
        return "Single-assistant session — no handoff yet."
    if current == "cursor" and "kiro" in used:
        return "Kiro already ingested context — Cursor should implement using the bundle below."
    if current == "kiro" and "cursor" in used:
        return "Cursor made edits — Kiro should review diff + validate against steering docs."
    return f"Multi-assistant session ({', '.join(used)}) — use bundle only, avoid duplicate context."


def _build_context_bundle(items: list[dict], priority: list[str]) -> list[dict]:
    seen_paths: set[str] = set()
    bundle: list[dict] = []
    type_order = {t: i for i, t in enumerate(priority)}

    sorted_items = sorted(
        items,
        key=lambda x: (type_order.get(x.get("type", "note"), 99), x.get("timestamp", "")),
    )

    for item in sorted_items:
        meta = item.get("metadata") or {}
        if isinstance(meta, str):
            meta = {"path": meta}
        path = meta.get("path", item.get("id", ""))
        if path and path in seen_paths:
            continue
        if path:
            seen_paths.add(path)
        bundle.append(
            {
                "type": item.get("type"),
                "content": item.get("content", "")[:2000],
                "metadata": meta if isinstance(meta, dict) else {},
                "relevanceScore": _relevance(item.get("type", ""), priority),
            }
        )
    return bundle[:8]


def _relevance(item_type: str, priority: list[str]) -> float:
    try:
        return round(1.0 - (priority.index(item_type) * 0.15), 2)
    except ValueError:
        return 0.3


def _normalize_bundle_item(item: dict) -> dict:
    meta = item.get("metadata") or {}
    if isinstance(meta, str):
        meta = {"path": meta}
    elif not isinstance(meta, dict):
        meta = {}
    return {
        "type": item.get("type", "note"),
        "content": str(item.get("content", ""))[:2000],
        "metadata": meta,
        "relevanceScore": float(item.get("relevanceScore", 0.5)),
    }


def _compute_metrics(items: list[dict], bundled: list[dict]) -> dict:
    raw_tokens = sum(len(str(i.get("content", ""))) for i in items)
    bundled_tokens = sum(len(str(i.get("content", ""))) for i in bundled)
    return {
        "rawContextItems": len(items),
        "bundledContextItems": len(bundled),
        "contextReductionPct": round((1 - bundled_tokens / max(raw_tokens, 1)) * 100, 1),
        "estimatedTokenSavings": raw_tokens - bundled_tokens,
    }
