"""Collect workspace context for IDE hooks — project-agnostic."""

import json
import re
import subprocess
from pathlib import Path

from shared.config import harness_dir, load_config

# Common path-like tokens in prompts: src/foo.ts, ./bar.py, @path
_PATH_RE = re.compile(
    r"(?<![\w./-])((?:\./|\.\./|/)?[A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,8})(?![\w./-])"
)


def git_diff(paths: list[str] | None = None, max_chars: int = 4000) -> str:
    cmd = ["git", "diff", "--no-color"]
    if paths:
        cmd.extend(paths)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=False, cwd=Path.cwd()
        )
        diff = result.stdout.strip()
        if not diff:
            result = subprocess.run(
                ["git", "diff", "--cached", "--no-color"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                cwd=Path.cwd(),
            )
            diff = result.stdout.strip()
        return diff[:max_chars]
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""


def read_file_snippet(path: str, max_chars: int = 2000) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    if not p.exists() or not p.is_file():
        return ""
    try:
        return p.read_text(errors="replace")[:max_chars]
    except OSError:
        return ""


def _paths_from_prompt(prompt: str, root: Path) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _PATH_RE.findall(prompt):
        candidate = match.strip("'\"")
        p = Path(candidate)
        if not p.is_absolute():
            p = root / candidate
        try:
            p = p.resolve()
        except OSError:
            continue
        if not p.is_file() or not str(p).startswith(str(root.resolve())):
            continue
        rel = str(p.relative_to(root.resolve()))
        if rel not in seen:
            seen.add(rel)
            found.append(rel)
    return found[:8]


def _glob_include_paths(patterns: list[str], root: Path, limit: int = 6) -> list[str]:
    files: list[str] = []
    for pattern in patterns:
        for p in root.glob(pattern):
            if p.is_file():
                try:
                    files.append(str(p.relative_to(root)))
                except ValueError:
                    files.append(str(p))
            if len(files) >= limit:
                return files
    return files


def _read_error_sources(sources: list[str], root: Path, assistant: str) -> list[dict]:
    items: list[dict] = []
    for source in sources:
        p = root / source if not Path(source).is_absolute() else Path(source)
        if not p.exists() or not p.is_file():
            continue
        content = p.read_text(errors="replace").strip()
        if not content:
            continue
        try:
            rel = str(p.relative_to(root.resolve()))
        except ValueError:
            rel = str(p)
        items.append(
            {
                "type": "error",
                "content": content[:3000],
                "metadata": {"path": rel, "assistant": assistant},
            }
        )
    return items


def items_from_prompt(
    prompt: str,
    assistant: str,
    attachments: list | None = None,
    root: Path | None = None,
) -> list[dict]:
    root = root or Path.cwd()
    cfg = load_config(root)
    items: list[dict] = []

    clean = prompt.strip()
    if clean:
        items.append(
            {
                "type": "note",
                "content": clean[:2000],
                "metadata": {"source": "user-prompt", "assistant": assistant},
            }
        )

    for att in attachments or []:
        if att.get("type") != "file":
            continue
        file_path = att.get("file_path") or att.get("path", "")
        content = read_file_snippet(file_path)
        if content:
            items.append(
                {
                    "type": "file",
                    "content": content,
                    "metadata": {"path": file_path, "assistant": assistant},
                }
            )

    items.extend(_read_error_sources(cfg.get("errorSources", []), root, assistant))

    seen_files: set[str] = set()

    def add_file(rel_path: str) -> None:
        if rel_path in seen_files:
            return
        content = read_file_snippet(str(root / rel_path))
        if content:
            seen_files.add(rel_path)
            items.append(
                {
                    "type": "file",
                    "content": content,
                    "metadata": {"path": rel_path, "assistant": assistant},
                }
            )

    for rel in cfg.get("extraFiles", []):
        add_file(rel)

    if cfg.get("promptPathPatterns", True):
        for rel in _paths_from_prompt(clean, root):
            add_file(rel)

    for rel in _glob_include_paths(cfg.get("includePaths", []), root):
        add_file(rel)

    env_files = __import__("os").environ.get("SPLICE_FILES", "")
    for rel in [f.strip() for f in env_files.split(",") if f.strip()]:
        add_file(rel)

    if cfg.get("captureGitDiff", True):
        diff_paths = list(seen_files) or None
        diff = git_diff(diff_paths, cfg.get("gitDiffMaxChars", 4000))
        if diff:
            label = ", ".join(diff_paths[:3]) if diff_paths else "workspace"
            items.append(
                {
                    "type": "diff",
                    "content": diff,
                    "metadata": {"path": label, "assistant": assistant},
                }
            )

    return items


def parse_hook_stdin(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"prompt": raw}


def capture_stdin_as_error(root: Path | None = None) -> Path:
    """Save stdin to .splice/last-error.log for next /harness run."""
    root = root or Path.cwd()
    log = harness_dir(root) / "last-error.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    import sys

    data = sys.stdin.read()
    log.write_text(data)
    return log
