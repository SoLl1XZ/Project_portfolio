"""Extract portfolio metadata from a single project folder."""

import json
import os
import re
import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

OVERRIDE_FILE = "portfolio.json"
OVERRIDE_TYPES = {"title": str, "description": str, "tags": list, "links": dict, "hidden": bool}

# Only these schemes may reach an href, so a "javascript:" URL in portfolio.json can never run.
ALLOWED_LINK_SCHEMES = ("https://", "http://", "mailto:")

# Priority order: a README is written for human readers, CLAUDE.md for Claude.
TEXT_SOURCES = ("README.md", "CLAUDE.md")

# Folders with dependencies, caches or generated output rather than the project's own code.
IGNORED_DIRS = {"node_modules", "__pycache__", "venv", "data", "output", "build", "dist", "_build"}

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".ipynb": "Jupyter",
    ".ml": "OCaml",
    ".mli": "OCaml",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".r": "R",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".rs": "Rust",
    ".go": "Go",
    ".sh": "Shell",
}

# CLAUDE.md files often start with "# CLAUDE.md – <project>"; the prefix says nothing about the project.
CLAUDE_TITLE_PREFIX = re.compile(r"^CLAUDE\.md\s*[–—:-]\s*", re.IGNORECASE)

CODE_FENCES = ("```", "~~~")
NON_PROSE_LINE = re.compile(r"^(#|[-*+]\s|\d+\.\s|>|\||<|---|\*\*\*)")
LIST_ITEM = re.compile(r"^([-*+]|\d+\.)\s+")
MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
EMPHASIS_MARKERS = re.compile(r"[*`]")


def strip_inline_markdown(text: str) -> str:
    """Turn inline markdown into plain text: links keep their label, emphasis and code markers are dropped."""
    text = MARKDOWN_LINK.sub(r"\1", text)
    return EMPHASIS_MARKERS.sub("", text).strip()


def is_prose(line: str) -> bool:
    return bool(line) and not NON_PROSE_LINE.match(line)


def lines_outside_code_blocks(text: str) -> list[str]:
    """Stripped lines with fenced code removed; each fence becomes a blank line so it ends a paragraph."""
    lines: list[str] = []
    in_code_block = False
    for line in (raw.strip() for raw in text.splitlines()):
        if line.startswith(CODE_FENCES):
            in_code_block = not in_code_block
            lines.append("")
        elif not in_code_block:
            lines.append(line)
    return lines


def list_items_from(lines: list[str], index: int) -> list[str]:
    """Text of the list that starts at `index` (after any blank lines), without bullets or numbers."""
    while index < len(lines) and not lines[index]:
        index += 1
    items: list[str] = []
    while index < len(lines) and LIST_ITEM.match(lines[index]):
        items.append(LIST_ITEM.sub("", lines[index]))
        index += 1
    return items


def first_paragraph(lines: list[str]) -> str | None:
    """The first run of prose lines. If it ends with ':', the sentence continues in a list, so include it."""
    start = next((i for i, line in enumerate(lines) if is_prose(line)), None)
    if start is None:
        return None
    end = start
    while end < len(lines) and is_prose(lines[end]):
        end += 1
    parts = lines[start:end]
    if parts[-1].endswith(":"):
        parts += list_items_from(lines, end)
    return strip_inline_markdown(" ".join(parts))


def parse_markdown(text: str) -> tuple[str | None, str | None]:
    """Return the first level-1 heading and the first prose paragraph of a markdown document."""
    lines = lines_outside_code_blocks(text)
    heading = next((line[2:] for line in lines if line.startswith("# ")), None)
    title = strip_inline_markdown(heading) if heading else None
    return title or None, first_paragraph(lines)


def title_from_folder_name(folder_name: str) -> str:
    """'macro_dashboard' -> 'Macro Dashboard'. Only the first letter is raised, so 'OCaml' survives."""
    words = re.split(r"[_\-\s]+", folder_name)
    return " ".join(word[0].upper() + word[1:] for word in words if word)


def read_text_metadata(project_dir: Path) -> dict[str, str]:
    """Title and description from README.md / CLAUDE.md; each field comes from the first file that has it."""
    title: str | None = None
    description: str | None = None
    for filename in TEXT_SOURCES:
        path = project_dir / filename
        if not path.is_file():
            continue
        file_title, file_description = parse_markdown(path.read_text(encoding="utf-8", errors="replace"))
        if filename == "CLAUDE.md" and file_title:
            file_title = CLAUDE_TITLE_PREFIX.sub("", file_title)
        title = title or file_title
        description = description or file_description
    return {
        "title": title or title_from_folder_name(project_dir.name),
        "description": description or "",
    }


def iter_project_files(project_dir: Path) -> Iterator[Path]:
    """Yield the project's own files, skipping hidden entries (.git, .venv, .env, ...) and IGNORED_DIRS."""
    for current_dir, dirnames, filenames in os.walk(project_dir):
        # Pruning dirnames in place stops os.walk from descending into those folders at all.
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and name not in IGNORED_DIRS]
        for filename in filenames:
            if not filename.startswith("."):
                yield Path(current_dir) / filename


def detect_technologies(project_dir: Path) -> list[str]:
    """Languages found in the project, most files first; ties are broken alphabetically."""
    counts: dict[str, int] = {}
    for path in iter_project_files(project_dir):
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return sorted(counts, key=lambda language: (-counts[language], language))


def git_last_commit_date(project_dir: Path) -> str | None:
    """Date (YYYY-MM-DD) of the newest commit, if the folder is its own git repo with at least one commit."""
    # Only the folder's own repo counts; asking git from a plain subfolder would report a parent repo.
    if not (project_dir / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), "log", "-1", "--format=%cs"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def modification_time(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:  # e.g. a broken symlink
        return None


def newest_file_date(project_dir: Path) -> str:
    """Date of the most recently modified file; the folder's own date when it has no files."""
    timestamps = [t for t in map(modification_time, iter_project_files(project_dir)) if t is not None]
    newest = max(timestamps, default=project_dir.stat().st_mtime)
    return date.fromtimestamp(newest).isoformat()


def last_updated(project_dir: Path) -> str:
    return git_last_commit_date(project_dir) or newest_file_date(project_dir)


def read_overrides(project_dir: Path) -> dict:
    """Contents of portfolio.json, or {} when there is none. Raises ValueError if the file is malformed."""
    path = project_dir / OVERRIDE_FILE
    if not path.is_file():
        return {}
    try:
        overrides = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON ({error})") from error
    if not isinstance(overrides, dict):
        raise ValueError(f"{path}: expected a JSON object, got {type(overrides).__name__}")
    for key, expected_type in OVERRIDE_TYPES.items():
        if key in overrides and not isinstance(overrides[key], expected_type):
            actual = type(overrides[key]).__name__
            raise ValueError(f"{path}: '{key}' should be {expected_type.__name__}, got {actual}")
    return overrides


def safe_links(links: dict) -> dict[str, str]:
    return {label: url for label, url in links.items() if isinstance(url, str) and url.startswith(ALLOWED_LINK_SCHEMES)}


def scan_project(project_dir: Path) -> dict | None:
    """Everything the website shows about one project, or None when portfolio.json hides it."""
    overrides = read_overrides(project_dir)
    if overrides.get("hidden"):
        return None
    text = read_text_metadata(project_dir)
    return {
        "folder": project_dir.name,
        "title": overrides.get("title") or text["title"],
        "description": overrides.get("description") or text["description"],
        "tags": overrides.get("tags") or detect_technologies(project_dir),
        "links": safe_links(overrides.get("links") or {}),
        "updated": last_updated(project_dir),
    }
