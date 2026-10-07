import tempfile
import unittest
from pathlib import Path

from scan import parse_markdown, read_text_metadata, strip_inline_markdown, title_from_folder_name


def make_project(root: Path, name: str, files: dict[str, str]) -> Path:
    """Create a project folder under root with the given {relative path: content} files."""
    project_dir = root / name
    project_dir.mkdir()
    for relative_path, content in files.items():
        path = project_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return project_dir


class StripInlineMarkdownTest(unittest.TestCase):
    def test_removes_bold_and_code_markers(self):
        self.assertEqual(strip_inline_markdown("A **fast** `scan.py` tool"), "A fast scan.py tool")

    def test_keeps_link_label_only(self):
        self.assertEqual(strip_inline_markdown("See [the docs](https://example.com)."), "See the docs.")


class ParseMarkdownTest(unittest.TestCase):
    def test_reads_first_heading_and_first_paragraph(self):
        text = "# My Project\n\nFirst paragraph.\n\nSecond paragraph.\n"
        self.assertEqual(parse_markdown(text), ("My Project", "First paragraph."))

    def test_joins_lines_of_one_paragraph(self):
        text = "# T\n\nLine one\nline two.\n"
        self.assertEqual(parse_markdown(text)[1], "Line one line two.")

    def test_skips_headings_lists_tables_quotes_and_code(self):
        text = (
            "# T\n\n## Section\n\n- item\n1. step\n> quote\n| a | b |\n\n"
            "```bash\nnot a paragraph\n```\n\nThe real description.\n"
        )
        self.assertEqual(parse_markdown(text)[1], "The real description.")

    def test_only_level_one_heading_counts_as_title(self):
        self.assertEqual(parse_markdown("## Sub\n\nText.\n")[0], None)

    def test_empty_document_gives_nothing(self):
        self.assertEqual(parse_markdown(""), (None, None))


class TitleFromFolderNameTest(unittest.TestCase):
    def test_underscores_and_dashes_become_spaces(self):
        self.assertEqual(title_from_folder_name("macro_dashboard"), "Macro Dashboard")
        self.assertEqual(title_from_folder_name("my-cool-app"), "My Cool App")

    def test_keeps_existing_capitals(self):
        self.assertEqual(title_from_folder_name("OCaml_parser"), "OCaml Parser")


class ReadTextMetadataTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_readme_wins_over_claude_md(self):
        project = make_project(self.root, "p", {
            "README.md": "# From README\n\nReadme text.\n",
            "CLAUDE.md": "# From CLAUDE\n\nClaude text.\n",
        })
        self.assertEqual(read_text_metadata(project), {"title": "From README", "description": "Readme text."})

    def test_claude_md_prefix_is_removed_from_title(self):
        project = make_project(self.root, "p", {"CLAUDE.md": "# CLAUDE.md – Backtester\n\nTests strategies.\n"})
        self.assertEqual(read_text_metadata(project)["title"], "Backtester")

    def test_missing_field_falls_back_to_next_file(self):
        project = make_project(self.root, "p", {
            "README.md": "# Readme Title\n",
            "CLAUDE.md": "# Claude Title\n\nClaude text.\n",
        })
        self.assertEqual(read_text_metadata(project), {"title": "Readme Title", "description": "Claude text."})

    def test_folder_without_markdown_uses_folder_name(self):
        project = make_project(self.root, "ocaml_interpreter", {"main.ml": "let () = ()\n"})
        self.assertEqual(read_text_metadata(project), {"title": "Ocaml Interpreter", "description": ""})


if __name__ == "__main__":
    unittest.main()
