"""Backward-compatible re-export — use shared.orchestrator."""

from shared.orchestrator import check_ollama, orchestrate_context, resolve_orchestrator

__all__ = ["orchestrate_context", "resolve_orchestrator", "check_ollama"]
