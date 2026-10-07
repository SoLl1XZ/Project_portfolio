import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scan import (detect_technologies, last_updated, parse_markdown, read_overrides, read_text_metadata,
                  scan_project, strip_inline_markdown, title_from_folder_name)


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


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class ReadTextMetadataTest(TempDirTestCase):
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


class DetectTechnologiesTest(TempDirTestCase):
    def test_orders_by_file_count_then_name(self):
        project = make_project(self.root, "p", {
            "a.py": "", "b.py": "", "src/c.py": "", "index.html": "", "app.js": "", "notes.md": "",
        })
        self.assertEqual(detect_technologies(project), ["Python", "HTML", "JavaScript"])

    def test_ignores_hidden_dependency_and_data_folders(self):
        project = make_project(self.root, "p", {
            "main.ml": "", ".venv/lib/x.py": "", "node_modules/y.js": "", "data/data.js": "", ".git/hook.sh": "",
        })
        self.assertEqual(detect_technologies(project), ["OCaml"])

    def test_empty_project_has_no_technologies(self):
        self.assertEqual(detect_technologies(make_project(self.root, "p", {})), [])


class LastUpdatedTest(TempDirTestCase):
    def test_uses_newest_file_without_git(self):
        project = make_project(self.root, "p", {"old.py": "", "new.py": ""})
        os.utime(project / "old.py", (datetime(2024, 1, 5, 12).timestamp(),) * 2)
        os.utime(project / "new.py", (datetime(2025, 3, 14, 12).timestamp(),) * 2)
        self.assertEqual(last_updated(project), "2025-03-14")

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_uses_last_commit_date_in_git_repo(self):
        project = make_project(self.root, "p", {"main.py": ""})
        commit_time = "2023-06-01T12:00:00"
        env = {**os.environ, "GIT_AUTHOR_DATE": commit_time, "GIT_COMMITTER_DATE": commit_time}
        git = ["git", "-C", str(project), "-c", "user.name=Test", "-c", "user.email=test@example.com",
               "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "init"], check=True, env=env)
        self.assertEqual(last_updated(project), "2023-06-01")

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_git_repo_without_commits_falls_back_to_files(self):
        project = make_project(self.root, "p", {"main.py": ""})
        os.utime(project / "main.py", (datetime(2025, 3, 14, 12).timestamp(),) * 2)
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        self.assertEqual(last_updated(project), "2025-03-14")


class ReadOverridesTest(TempDirTestCase):
    def test_missing_file_gives_empty_dict(self):
        self.assertEqual(read_overrides(make_project(self.root, "p", {})), {})

    def test_invalid_json_raises_with_file_name(self):
        project = make_project(self.root, "p", {"portfolio.json": "{not json"})
        with self.assertRaisesRegex(ValueError, "portfolio.json"):
            read_overrides(project)

    def test_wrong_field_type_raises(self):
        project = make_project(self.root, "p", {"portfolio.json": json.dumps({"tags": "Python"})})
        with self.assertRaisesRegex(ValueError, "'tags' should be list"):
            read_overrides(project)

    def test_non_object_raises(self):
        project = make_project(self.root, "p", {"portfolio.json": "[]"})
        with self.assertRaises(ValueError):
            read_overrides(project)


class ScanProjectTest(TempDirTestCase):
    def test_overrides_win_over_detected_values(self):
        project = make_project(self.root, "p", {
            "README.md": "# Dansk titel\n\nDansk tekst.\n",
            "main.py": "",
            "portfolio.json": json.dumps({"title": "English title", "tags": ["Python", "Chart.js"]}),
        })
        result = scan_project(project)
        self.assertEqual(result["title"], "English title")
        self.assertEqual(result["description"], "Dansk tekst.")
        self.assertEqual(result["tags"], ["Python", "Chart.js"])

    def test_hidden_project_is_skipped(self):
        project = make_project(self.root, "p", {"portfolio.json": json.dumps({"hidden": True})})
        self.assertIsNone(scan_project(project))

    def test_only_web_and_mail_links_are_kept(self):
        links = {"GitHub": "https://github.com/x", "Mail": "mailto:a@b.dk", "Bad": "javascript:alert(1)"}
        project = make_project(self.root, "p", {"portfolio.json": json.dumps({"links": links})})
        self.assertEqual(scan_project(project)["links"], {"GitHub": "https://github.com/x", "Mail": "mailto:a@b.dk"})

    def test_empty_folder_still_gives_a_complete_card(self):
        result = scan_project(make_project(self.root, "empty_project", {}))
        self.assertEqual(result["title"], "Empty Project")
        self.assertEqual((result["description"], result["tags"], result["links"]), ("", [], {}))
        self.assertRegex(result["updated"], r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
