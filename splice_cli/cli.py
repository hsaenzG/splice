#!/usr/bin/env python3
"""Splice CLI — shared context layer for Kiro, Cursor, and Claude Code."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path

from splice_cli.shared.orchestrator import check_ollama, orchestrate_context, resolve_orchestrator
from splice_cli.shared.collect import capture_stdin_as_error, items_from_prompt, parse_hook_stdin
from splice_cli.shared.store import (
    add_context_items,
    bundle_path,
    ensure_session,
    load_session,
    save_orchestration,
    write_bundle_markdown,
)

# When installed via pip, root is always the current working directory.
ROOT = Path.cwd()


# ---------------------------------------------------------------------------
# splice setup — install IDE hooks into the current project
# ---------------------------------------------------------------------------

IDES = ("kiro", "cursor", "claude")

# Files that get copied for each IDE
_SETUP_FILES: dict[str, list[tuple[str, str]]] = {
    "kiro": [
        ("hooks/kiro-orchestrate.sh",        "integrations/hooks/kiro-orchestrate.sh"),
        ("hooks/kiro-session-init.sh",        "integrations/hooks/kiro-session-init.sh"),
        ("templates/kiro-hooks-context-harness.json",  ".kiro/hooks/splice.json"),
        ("templates/kiro-steering-context-harness.md", ".kiro/steering/splice.md"),
    ],
    "cursor": [
        ("hooks/cursor-orchestrate.sh",       "integrations/hooks/cursor-orchestrate.sh"),
        ("hooks/cursor-session-init.sh",       "integrations/hooks/cursor-session-init.sh"),
        ("templates/cursor-rules-context-harness.mdc", ".cursor/rules/splice.mdc"),
        ("templates/cursor-hooks.json",        ".cursor/hooks.json"),
    ],
    "claude": [
        ("hooks/claude-orchestrate.sh",       "integrations/hooks/claude-orchestrate.sh"),
        ("hooks/claude-session-init.sh",       "integrations/hooks/claude-session-init.sh"),
        ("templates/claude-claude.md",         ".claude/CLAUDE.md"),
        ("templates/claude-settings.json",     ".claude/settings.json"),
    ],
}

_SHARED_HOOKS = [
    ("hooks/orchestrate.sh", "integrations/hooks/orchestrate.sh"),
]

_GITIGNORE_SNIPPET = """
# splice
.splice/session.json
.splice/active-bundle.md
.splice/last-error.log
"""

_DEFAULT_CONFIG = """{
  "project": null,
  "orchestrator": "mock",
  "captureGitDiff": true,
  "includePaths": [],
  "errorSources": [".splice/last-error.log"],
  "extraFiles": [],
  "promptPathPatterns": true,
  "ollama": {
    "baseUrl": "http://localhost:11434",
    "model": "llama3.2",
    "timeoutSeconds": 60
  },
  "bedrock": {
    "modelId": "amazon.nova-lite-v1:0"
  }
}
"""


def _data_dir() -> Path:
    """Return the path to splice_cli/data/ bundled with the package."""
    try:
        # Python 3.9+ importlib.resources
        with resources.as_file(resources.files("splice_cli").joinpath("data")) as p:
            return p
    except AttributeError:
        # Fallback: resolve from this file
        return Path(__file__).parent / "data"


def _detect_ides(target: Path) -> list[str]:
    """Detect which IDEs appear to be in use in the target project."""
    detected = []
    if (target / ".kiro").exists():
        detected.append("kiro")
    if (target / ".cursor").exists():
        detected.append("cursor")
    if (target / ".claude").exists():
        detected.append("claude")
    return detected


def cmd_setup(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()
    if not target.exists():
        print(f"Error: path '{target}' does not exist.", file=sys.stderr)
        return 1

    data = _data_dir()

    # Determine which IDEs to set up
    ides_requested: list[str] = args.ides if args.ides else _detect_ides(target)
    if not ides_requested:
        ides_requested = list(IDES)
        print("No IDEs detected — installing hooks for all supported IDEs (kiro, cursor, claude).")
    else:
        print(f"Installing hooks for: {', '.join(ides_requested)}")

    installed: list[str] = []
    skipped: list[str] = []

    def _install(src_rel: str, dst_rel: str) -> None:
        src = data / src_rel
        dst = target / dst_rel
        if not src.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Don't overwrite existing IDE config files (hooks.json, settings.json)
        # unless --force is passed
        if dst.exists() and not args.force and dst_rel.endswith((".json", ".md")) and (
            ".kiro/hooks" in dst_rel or ".cursor/hooks" in dst_rel or ".claude/settings" in dst_rel
        ):
            skipped.append(dst_rel)
            return
        shutil.copy2(src, dst)
        # Make shell scripts executable
        if dst.suffix == ".sh":
            dst.chmod(dst.stat().st_mode | 0o755)
        installed.append(dst_rel)

    # Shared hooks (always installed)
    for src_rel, dst_rel in _SHARED_HOOKS:
        _install(src_rel, dst_rel)

    # Per-IDE hooks
    for ide in ides_requested:
        if ide not in _SETUP_FILES:
            print(f"  Warning: unknown IDE '{ide}', skipping.")
            continue
        for src_rel, dst_rel in _SETUP_FILES[ide]:
            _install(src_rel, dst_rel)

    # Config file
    cfg_path = target / ".splice" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if not cfg_path.exists():
        cfg_path.write_text(_DEFAULT_CONFIG)
        installed.append(".splice/config.json")
    else:
        skipped.append(".splice/config.json")

    # .gitignore
    gitignore = target / ".gitignore"
    marker = "# splice"
    if gitignore.exists():
        content = gitignore.read_text()
        if marker not in content:
            gitignore.write_text(content + _GITIGNORE_SNIPPET)
            installed.append(".gitignore (updated)")
    else:
        gitignore.write_text(_GITIGNORE_SNIPPET.strip() + "\n")
        installed.append(".gitignore (created)")

    # Summary
    print()
    if installed:
        print("Installed:")
        for f in installed:
            print(f"  + {f}")
    if skipped:
        print("Skipped (already exist — use --force to overwrite):")
        for f in skipped:
            print(f"  ~ {f}")

    print(f"""
Done. Next steps:
  1. Edit {target / '.splice/config.json'} for your project
  2. Restart Kiro, Cursor, and/or Claude Code
  3. In any assistant: /harness <your task>

Optional: pipe errors before /harness
  npm test 2>&1 | splice capture-error
""")
    return 0


# ---------------------------------------------------------------------------
# Remaining subcommands (thin wrappers over the shared library)
# ---------------------------------------------------------------------------


def cmd_doctor(_: argparse.Namespace) -> int:
    root = ROOT
    mode = resolve_orchestrator(root)
    print(f"Orchestrator: {mode}")
    print(f"Config:       {root / '.splice/config.json'}")
    if mode == "ollama":
        status = check_ollama(root)
        print(json.dumps(status, indent=2))
        if not status.get("reachable"):
            print("\nInstall Ollama: https://ollama.com — then: ollama pull llama3.2", file=sys.stderr)
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


def cmd_init(args: argparse.Namespace) -> int:
    session = ensure_session(args.assistant, args.project, ROOT)
    print(json.dumps(session, indent=2))
    print(f"\nSession ready: {session['sessionId']} ({args.assistant})", file=sys.stderr)
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    session = load_session(ROOT)
    if not session:
        print("No active session. Run: splice init --assistant cursor|kiro|claude")
        return 1
    print(json.dumps(session, indent=2))
    return 0


def cmd_capture_error(_: argparse.Namespace) -> int:
    path = capture_stdin_as_error(ROOT)
    print(f"Saved to {path}")
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
        from splice_cli.shared.collect import read_file_snippet
        items.append({
            "type": "file",
            "content": read_file_snippet(args.extra_file),
            "metadata": {"path": args.extra_file, "assistant": args.assistant},
        })

    if args.fresh:
        session = ensure_session(args.assistant, root=ROOT)
        session["contextItems"] = items
        from splice_cli.shared.store import save_session
        save_session(session, ROOT)
        all_items = items
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": body,
        }
    })


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
        p = item.get("metadata", {}).get("path", item.get("type"))
        lines.append(f"[{item.get('type')}] {p}:")
        lines.append(str(item.get("content", ""))[:500])
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="splice",
        description="Splice — shared context layer for Kiro, Cursor, and Claude Code",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    # setup — install hooks into a project
    p_setup = sub.add_parser(
        "setup",
        help="Install IDE hooks into the current (or given) project",
    )
    p_setup.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target project directory (default: current directory)",
    )
    p_setup.add_argument(
        "--ide",
        dest="ides",
        action="append",
        choices=list(IDES),
        metavar="IDE",
        help="Specific IDE to set up (kiro|cursor|claude). Repeat for multiple. Default: auto-detect.",
    )
    p_setup.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing IDE config files",
    )
    p_setup.set_defaults(func=cmd_setup)

    # init — create/resume session
    p_init = sub.add_parser("init", help="Create or resume a session")
    p_init.add_argument("--assistant", required=True, choices=["cursor", "kiro", "claude"])
    p_init.add_argument("--project", default=None)
    p_init.set_defaults(func=cmd_init)

    # status
    p_status = sub.add_parser("status", help="Show active session")
    p_status.set_defaults(func=cmd_status)

    # doctor
    p_doc = sub.add_parser("doctor", help="Check orchestrator config and connectivity")
    p_doc.set_defaults(func=cmd_doctor)

    # capture-error
    p_err = sub.add_parser("capture-error", help="Pipe stderr/stdout into last-error.log")
    p_err.set_defaults(func=cmd_capture_error)

    # orchestrate
    p_orch = sub.add_parser("orchestrate", help="Ingest + orchestrate context")
    p_orch.add_argument("--assistant", required=True, choices=["cursor", "kiro", "claude"])
    p_orch.add_argument("--prompt", default="")
    p_orch.add_argument("--extra-file", default=None)
    p_orch.add_argument(
        "--format", choices=["compact", "markdown", "json", "claude"], default="compact",
    )
    p_orch.add_argument("--hook-mode", action="store_true")
    p_orch.add_argument("--always", action="store_true")
    p_orch.add_argument("--fresh", action="store_true")
    p_orch.set_defaults(func=cmd_orchestrate)

    # handoff
    p_handoff = sub.add_parser("handoff", help="Switch assistant in shared session")
    p_handoff.add_argument("--from", dest="from_assistant", required=True, choices=["cursor", "kiro", "claude"])
    p_handoff.add_argument("--to", dest="to_assistant", required=True, choices=["cursor", "kiro", "claude"])
    p_handoff.add_argument("--prompt", default=None)
    p_handoff.set_defaults(func=cmd_handoff)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
