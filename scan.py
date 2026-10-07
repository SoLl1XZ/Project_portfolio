"""Extract portfolio metadata from a single project folder."""

import re
from pathlib import Path

# Priority order: a README is written for human readers, CLAUDE.md for Claude.
TEXT_SOURCES = ("README.md", "CLAUDE.md")

# CLAUDE.md files often start with "# CLAUDE.md – <project>"; the prefix says nothing about the project.
CLAUDE_TITLE_PREFIX = re.compile(r"^CLAUDE\.md\s*[–—:-]\s*", re.IGNORECASE)

CODE_FENCES = ("```", "~~~")
NON_PROSE_LINE = re.compile(r"^(#|[-*+]\s|\d+\.\s|>|\||<|---|\*\*\*)")
MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
EMPHASIS_MARKERS = re.compile(r"[*`]")


def strip_inline_markdown(text: str) -> str:
    """Turn inline markdown into plain text: links keep their label, emphasis and code markers are dropped."""
    text = MARKDOWN_LINK.sub(r"\1", text)
    return EMPHASIS_MARKERS.sub("", text).strip()


def is_prose(line: str) -> bool:
    return bool(line) and not NON_PROSE_LINE.match(line)


def parse_markdown(text: str) -> tuple[str | None, str | None]:
    """Return the first level-1 heading and the first prose paragraph of a markdown document."""
    title: str | None = None
    paragraph: list[str] = []
    paragraph_done = False
    in_code_block = False

    for line in (raw.strip() for raw in text.splitlines()):
        if line.startswith(CODE_FENCES):
            in_code_block = not in_code_block
            paragraph_done = paragraph_done or bool(paragraph)
            continue
        if in_code_block:
            continue
        if title is None and line.startswith("# "):
            title = strip_inline_markdown(line[2:]) or None
        if paragraph_done:
            continue
        if is_prose(line):
            paragraph.append(line)
        elif paragraph:
            paragraph_done = True

    description = strip_inline_markdown(" ".join(paragraph)) if paragraph else None
    return title, description


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
