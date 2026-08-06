#!/usr/bin/env python3
"""
Dual-IDE demo: Kiro triages → Cursor implements (shared session).
No AWS required.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from shared.bedrock import orchestrate_context  # noqa: E402
from shared.collect import items_from_prompt  # noqa: E402
from shared.store import ensure_session, save_orchestration, session_path  # noqa: E402

PROMPT_KIRO = "/harness debug the UserList crash after API schema change"
PROMPT_CURSOR = "/harness apply the fix in UserList.tsx using the orchestrated bundle"


DEMO_CONFIG = {
    "project": "splice-demo",
    "captureGitDiff": True,
    "errorSources": [".splice/last-error.log", "demo-app/UserList.tsx.error.log"],
    "extraFiles": ["demo-app/UserList.tsx"],
    "promptPathPatterns": True,
}


def write_demo_config():
    cfg_dir = ROOT / ".splice"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.json").write_text(json.dumps(DEMO_CONFIG, indent=2) + "\n")


def run_step(assistant: str, prompt: str, session: dict) -> dict:
    print(f"\n{'=' * 60}")
    print(f"STEP — {assistant.upper()}")
    print(f"Prompt: {prompt}")
    print("=" * 60)

    items = items_from_prompt(prompt, assistant, root=ROOT)
    session.setdefault("contextItems", []).extend(items)
    session["assistant"] = assistant
    used = session.setdefault("assistantsUsed", [])
    if assistant not in used:
        used.append(assistant)

    result = orchestrate_context(
        session["sessionId"],
        session["contextItems"],
        assistant=assistant,
        assistants_used=used,
    )
    session["lastOrchestration"] = result
    save_orchestration(result, ROOT)

    metrics = result.get("metrics", {})
    print(f"Agent:     {result.get('recommendedAgent')}")
    print(f"Workflow:  {result.get('workflow')}")
    print(f"Reduction: {metrics.get('contextReductionPct')}%")
    print(f"Handoff:   {result.get('handoffRecommendation')}")
    print(f"Latency:   {result.get('latencyMs')}ms")
    return session


def main():
    if session_path(ROOT).parent.exists():
        import shutil

        shutil.rmtree(session_path(ROOT).parent, ignore_errors=True)

    write_demo_config()
    session = ensure_session("kiro", project="splice-demo", root=ROOT)
    print(f"Shared session: {session['sessionId']}")

    session = run_step("kiro", PROMPT_KIRO, session)
    session = run_step("cursor", PROMPT_CURSOR, session)

    print(f"\n{'=' * 60}")
    print("DUAL-IDE DEMO COMPLETE")
    print(f"Session file: {session_path(ROOT)}")
    print(f"Bundle file:  {ROOT / '.splice/active-bundle.md'}")
    print("=" * 60)
    print("\nNext: open this repo in Kiro and Cursor and try the same /harness prompts.")


if __name__ == "__main__":
    main()
