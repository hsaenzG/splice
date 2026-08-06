#!/usr/bin/env python3
"""Splice CLI — shared by Kiro, Cursor, and Claude Code hooks."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from shared.orchestrator import check_ollama, orchestrate_context, resolve_orchestrator  # noqa: E402
from shared.collect import capture_stdin_as_error, items_from_prompt, parse_hook_stdin  # noqa: E402
from shared.store import (  # noqa: E402
    add_context_items,
    bundle_path,
    ensure_session,
    load_session,
    save_orchestration,
    write_bundle_markdown,
)


def cmd_doctor(_: argparse.Namespace) -> int:
    mode = resolve_orchestrator(ROOT)
    print(f"Orchestrator: {mode}")
    print(f"Config: {ROOT / '.splice/config.json'}")
    if mode == "ollama":
        status = check_ollama(ROOT)
        print(json.dumps(status, indent=2))
        if not status.get("reachable"):
            print("\nInstall: https://ollama.com — then: ollama pull llama3.2", file=sys.stderr)
            return 1
        if not status.get("modelAvailable"):
            model = status.get("model")
            print(f"\nModel '{model}' not found. Run: ollama pull {model}", file=sys.stderr)
            return 1
    elif mode == "bedrock":
        print("Bedrock mode — requires AWS credentials and model access in your region.")
    else:
        print("Mock mode — no external model required.")
    return 0


def cmd_capture_error(_: argparse.Namespace) -> int:
    path = capture_stdin_as_error(ROOT)
    print(f"Saved to {path}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    session = ensure_session(args.assistant, args.project, ROOT)
    print(json.dumps(session, indent=2))
    print(f"\nSession ready: {session['sessionId']} ({args.assistant})", file=sys.stderr)
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    session = load_session(ROOT)
    if not session:
        print("No active session. Run: splice-cli.py init --assistant cursor|kiro|claude")
        return 1
    print(json.dumps(session, indent=2))
    return 0


def cmd_orchestrate(args: argparse.Namespace) -> int:
    session = ensure_session(args.assistant, root=ROOT)
    prompt = args.prompt or ""
    attachments = []

    if args.hook_mode and not sys.stdin.isatty():
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            hook_input = parse_hook_stdin(sys.stdin.read())
            prompt = hook_input.get("prompt", prompt)
            attachments = hook_input.get("attachments", [])

    if args.hook_mode and not _should_orchestrate(prompt, args.always):
        if args.assistant == "cursor":
            print(json.dumps({"continue": True}))
        return 0

    items = items_from_prompt(prompt, args.assistant, attachments, root=ROOT)

    if args.extra_file:
        from shared.collect import read_file_snippet

        items.append(
            {
                "type": "file",
                "content": read_file_snippet(args.extra_file),
                "metadata": {"path": args.extra_file, "assistant": args.assistant},
            }
        )

    if args.fresh:
        # Per-submit capture for IDE hooks — avoid unbounded session growth
        all_items = items
        session = ensure_session(args.assistant, root=ROOT)
        session["contextItems"] = items
        from shared.store import save_session

        save_session(session, ROOT)
    else:
        session = add_context_items(items, ROOT)
        all_items = session.get("contextItems", [])
    result = orchestrate_context(
        session["sessionId"],
        all_items,
        assistant=args.assistant,
        assistants_used=session.get("assistantsUsed", [args.assistant]),
        root=ROOT,
    )
    save_orchestration(result, ROOT)

    if args.format == "json":
        out = json.dumps(result, indent=2)
    elif args.format == "markdown":
        out = bundle_path(ROOT).read_text()
    elif args.format == "claude":
        out = _claude_hook_output(result, ROOT)
    else:
        out = _compact_stdout(result)

    if args.assistant == "cursor" and args.hook_mode:
        print(json.dumps({"continue": True, "user_message": ""}))
        return 0

    if args.assistant == "claude" and args.hook_mode:
        print(out)
        return 0

    print(out)
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    """Simulate switching from one IDE to another with shared session."""
    from_assistant = args.from_assistant
    to_assistant = args.to_assistant

    session = load_session(ROOT)
    if not session:
        session = ensure_session(from_assistant, root=ROOT)

    session["assistant"] = to_assistant
    used = session.setdefault("assistantsUsed", [])
    if to_assistant not in used:
        used.append(to_assistant)

    items = session.get("contextItems", [])
    if not items:
        from shared.collect import items_from_prompt

        items = items_from_prompt(
            args.prompt or "Handoff: continue the current task using the orchestrated bundle",
            to_assistant,
            root=ROOT,
        )
        session = add_context_items(items, ROOT)
        items = session.get("contextItems", [])

    result = orchestrate_context(
        session["sessionId"],
        items,
        assistant=to_assistant,
        assistants_used=session.get("assistantsUsed", []),
        root=ROOT,
    )
    save_orchestration(result, ROOT)
    print(json.dumps(result, indent=2))
    print(f"\n→ Handoff {from_assistant} → {to_assistant}", file=sys.stderr)
    print(f"→ Bundle: {bundle_path(ROOT)}", file=sys.stderr)
    return 0


def _should_orchestrate(prompt: str, always: bool) -> bool:
    if always:
        return True
    p = prompt.lower()
    return "/harness" in p or "@harness" in p or "splice" in p


def _claude_hook_output(result: dict, root: Path) -> str:
    bundle_file = bundle_path(root)
    body = _compact_stdout(result)
    if bundle_file.exists():
        body += f"\n\nFull bundle: {bundle_file.relative_to(root)}"
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": body,
            }
        }
    )


def _compact_stdout(result: dict) -> str:
    metrics = result.get("metrics", {})
    lines = [
        "[Splice]",
        f"orchestrator={result.get('orchestrator', result.get('source', 'mock'))} "
        f"agent={result.get('recommendedAgent')} workflow={result.get('workflow')} "
        f"reduction={metrics.get('contextReductionPct')}% latency={result.get('latencyMs')}ms",
        result.get("handoffRecommendation", ""),
        "",
    ]
    for item in result.get("contextBundle", [])[:4]:
        path = item.get("metadata", {}).get("path", item.get("type"))
        lines.append(f"[{item.get('type')}] {path}:")
        lines.append(str(item.get("content", ""))[:500])
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Splice CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create or resume local session")
    p_init.add_argument("--assistant", required=True, choices=["cursor", "kiro", "claude"])
    p_init.add_argument("--project", default=None)
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status", help="Show active session")
    p_status.set_defaults(func=cmd_status)

    p_orch = sub.add_parser("orchestrate", help="Ingest + orchestrate context")
    p_orch.add_argument("--assistant", required=True, choices=["cursor", "kiro", "claude"])
    p_orch.add_argument("--prompt", default="")
    p_orch.add_argument("--extra-file", default=None)
    p_orch.add_argument(
        "--format",
        choices=["compact", "markdown", "json", "claude"],
        default="compact",
    )
    p_orch.add_argument("--hook-mode", action="store_true", help="IDE hook output format")
    p_orch.add_argument("--always", action="store_true", help="Orchestrate even without /harness")
    p_orch.add_argument(
        "--fresh",
        action="store_true",
        help="Hook mode: orchestrate current capture only, do not accumulate history",
    )
    p_orch.set_defaults(func=cmd_orchestrate)

    p_handoff = sub.add_parser("handoff", help="Switch assistant in shared session")
    p_handoff.add_argument(
        "--from",
        dest="from_assistant",
        required=True,
        choices=["cursor", "kiro", "claude"],
    )
    p_handoff.add_argument(
        "--to",
        dest="to_assistant",
        required=True,
        choices=["cursor", "kiro", "claude"],
    )
    p_handoff.set_defaults(func=cmd_handoff)

    p_err = sub.add_parser("capture-error", help="Pipe stderr/stdout into last-error.log for /harness")
    p_err.set_defaults(func=cmd_capture_error)

    p_doc = sub.add_parser("doctor", help="Check orchestrator config and Ollama connectivity")
    p_doc.set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
