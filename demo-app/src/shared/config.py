"""Project-level Splice configuration."""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "project": None,
    "orchestrator": "mock",
    "captureGitDiff": True,
    "gitDiffMaxChars": 4000,
    "includePaths": [],
    "errorSources": [".splice/last-error.log"],
    "extraFiles": [],
    "promptPathPatterns": True,
    "ollama": {
        "baseUrl": "http://localhost:11434",
        "model": "llama3.2",
        "timeoutSeconds": 60,
    },
    "bedrock": {
        "modelId": "amazon.nova-lite-v1:0",
    },
}


def harness_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".splice"


def config_path(root: Path | None = None) -> Path:
    return harness_dir(root) / "config.json"


def load_config(root: Path | None = None) -> dict:
    path = config_path(root)
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(path.read_text())
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config_example(root: Path | None = None) -> Path:
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")
    return path
