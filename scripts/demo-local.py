#!/usr/bin/env python3
"""
Local demo runner — no AWS required.
Simulates the full Splice flow using in-memory storage and mock orchestration.
"""

import json
import sys
import uuid
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shared.bedrock import orchestrate_context  # noqa: E402

SAMPLE_ITEMS = [
    {
        "type": "error",
        "content": "TypeError: Cannot read property 'map' of undefined at UserList.tsx:42",
        "metadata": {"path": "src/UserList.tsx", "line": 42},
    },
    {
        "type": "diff",
        "content": "- const users = data\n+ const users = data?.items ?? []",
        "metadata": {"path": "src/UserList.tsx"},
    },
    {
        "type": "file",
        "content": "export function UserList({ data }) { return data.map(u => <li>{u.name}</li>) }",
        "metadata": {"path": "src/UserList.tsx"},
    },
    {
        "type": "file",
        "content": "README.md — project setup instructions (unrelated to bug)",
        "metadata": {"path": "README.md"},
    },
    {
        "type": "note",
        "content": "User reported crash after API schema change",
        "metadata": {},
    },
]


def main():
    session_id = str(uuid.uuid4())
    print("=" * 60)
    print("Splice — Local Demo")
    print("=" * 60)
    print(f"\n1. Session created: {session_id}")
    print(f"   Project: demo-local | Assistant: cursor\n")

    print(f"2. Ingested {len(SAMPLE_ITEMS)} context items:")
    for item in SAMPLE_ITEMS:
        print(f"   - [{item['type']}] {item['metadata'].get('path', 'note')}")

    print("\n3. Orchestrating context…")
    result = orchestrate_context(session_id, SAMPLE_ITEMS)

    metrics = result.get("metrics", {})
    print(f"\n4. Orchestration complete ({result.get('latencyMs')}ms)")
    print(f"   Agent:    {result.get('recommendedAgent')}")
    print(f"   Workflow: {result.get('workflow')}")
    print(f"   Reduction: {metrics.get('contextReductionPct')}% context filtered")
    print(f"\n   Reasoning: {result.get('reasoning')}")

    print("\n5. Context bundle (what downstream assistant receives):")
    for i, item in enumerate(result.get("contextBundle", []), 1):
        score = item.get("relevanceScore", 0)
        path = item.get("metadata", {}).get("path", item.get("type"))
        print(f"   {i}. [{item.get('type')}] {path} (relevance: {score})")

    print("\n" + "=" * 60)
    print("SUCCESS METRIC: orchestration latency < 3000ms")
    latency = result.get("latencyMs", 9999)
    status = "PASS" if latency < 3000 else "FAIL"
    print(f"  latencyMs={latency} → {status}")
    print("=" * 60)

    out = Path(__file__).parent.parent / "demo-output.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\nFull output written to {out}")


if __name__ == "__main__":
    main()
