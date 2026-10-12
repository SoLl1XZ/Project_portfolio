import contextlib
import io
import json
import os
import unittest
from datetime import datetime

from build import attach_images, collect_projects, find_project_dirs, render_data_file
from helpers import TempDirTestCase, make_project


def set_file_date(path, year: int, month: int, day: int) -> None:
    timestamp = datetime(year, month, day, 12).timestamp()
    os.utime(path, (timestamp, timestamp))


class FindProjectDirsTest(TempDirTestCase):
    def test_skips_files_hidden_folders_and_the_portfolio_itself(self):
        for name in ("beta", "alpha", ".obsidian", "portfolio"):
            (self.root / name).mkdir()
        (self.root / "notes.md").write_text("", encoding="utf-8")
        found = find_project_dirs(self.root, exclude=self.root / "portfolio")
        self.assertEqual([path.name for path in found], ["alpha", "beta"])


class CollectProjectsTest(TempDirTestCase):
    def test_newest_project_comes_first(self):
        old = make_project(self.root, "old", {"a.py": ""})
        new = make_project(self.root, "new", {"a.py": ""})
        set_file_date(old / "a.py", 2024, 1, 1)
        set_file_date(new / "a.py", 2025, 1, 1)
        projects = collect_projects([old, new])
        self.assertEqual([project["folder"] for project in projects], ["new", "old"])

    def test_hidden_project_is_left_out(self):
        visible = make_project(self.root, "visible", {})
        hidden = make_project(self.root, "hidden", {"portfolio.json": json.dumps({"hidden": True})})
        self.assertEqual([project["folder"] for project in collect_projects([visible, hidden])], ["visible"])

    def test_broken_portfolio_json_skips_only_that_project_with_a_warning(self):
        good = make_project(self.root, "good", {})
        broken = make_project(self.root, "broken", {"portfolio.json": "{oops"})
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            projects = collect_projects([good, broken])
        self.assertEqual([project["folder"] for project in projects], ["good"])
        self.assertIn("skipped broken", stderr.getvalue())


class AttachImagesTest(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.images_dir = self.root / "images"
        self.images_dir.mkdir()

    def test_project_with_screenshot_gets_a_path_relative_to_the_page(self):
        (self.images_dir / "dash.jpg").write_bytes(b"")
        projects = attach_images([{"folder": "dash"}, {"folder": "plain"}], self.images_dir)
        self.assertEqual(projects, [{"folder": "dash", "image": "images/dash.jpg"}, {"folder": "plain"}])

    def test_projects_with_screenshot_come_first_and_keep_their_order(self):
        for name in ("b", "d"):
            (self.images_dir / f"{name}.jpg").write_bytes(b"")
        projects = attach_images([{"folder": name} for name in "abcd"], self.images_dir)
        self.assertEqual([project["folder"] for project in projects], ["b", "d", "a", "c"])

    def test_other_formats_and_missing_folder_give_no_image(self):
        (self.images_dir / "dash.png").write_bytes(b"")
        self.assertEqual(attach_images([{"folder": "dash"}], self.images_dir), [{"folder": "dash"}])
        self.assertEqual(attach_images([{"folder": "dash"}], self.root / "missing"), [{"folder": "dash"}])


class RenderDataFileTest(unittest.TestCase):
    def test_is_a_js_assignment_with_valid_json(self):
        projects = [{"folder": "p", "title": "Løkke"}]
        content = render_data_file(projects, "2026-10-07T18:00")
        prefix, suffix = "window.PORTFOLIO_DATA = ", ";\n"
        self.assertTrue(content.startswith(prefix) and content.endswith(suffix))
        payload = json.loads(content[len(prefix):-len(suffix)])
        self.assertEqual(payload, {"generated": "2026-10-07T18:00", "projects": projects})
        self.assertIn("Løkke", content)  # non-ASCII kept readable, not \u-escaped


if __name__ == "__main__":
    unittest.main()
