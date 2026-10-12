import subprocess
from pathlib import Path

from helpers import TempDirTestCase
from publish import COMMIT_MESSAGE, DATA_FILE, publish

OLD_DATA = 'window.PORTFOLIO_DATA = {\n  "generated": "2026-10-05T09:00",\n  "projects": ["a"]\n};\n'
NEW_TIMESTAMP_ONLY = OLD_DATA.replace("2026-10-05T09:00", "2026-10-12T09:00")
NEW_PROJECT = NEW_TIMESTAMP_ONLY.replace('["a"]', '["a", "b"]')


def run_git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


class PublishTest(TempDirTestCase):
    """Each test gets a clone whose 'origin' is a local bare repository standing in for GitHub."""

    def setUp(self):
        super().setUp()
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        run_git(self.root, "init", "-q", "--bare", "-b", "main", str(self.remote))
        run_git(self.root, "init", "-q", "-b", "main", str(self.repo))
        run_git(self.repo, "config", "user.name", "Test")
        run_git(self.repo, "config", "user.email", "test@example.com")
        self.write_data(OLD_DATA)
        run_git(self.repo, "add", DATA_FILE)
        run_git(self.repo, "commit", "-q", "-m", "Initial data")
        run_git(self.repo, "remote", "add", "origin", str(self.remote))
        run_git(self.repo, "push", "-q", "-u", "origin", "main")

    def write_data(self, content: str) -> None:
        path = self.repo / DATA_FILE
        path.parent.mkdir(exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def remote_messages(self) -> list[str]:
        return run_git(self.remote, "log", "--format=%s", "main").splitlines()

    def test_new_timestamp_alone_is_not_committed_and_file_is_restored(self):
        self.write_data(NEW_TIMESTAMP_ONLY)
        self.assertEqual(publish(self.repo), "no project changes; nothing to push")
        self.assertEqual(self.remote_messages(), ["Initial data"])
        self.assertEqual(run_git(self.repo, "status", "--porcelain"), "")

    def test_changed_project_is_committed_and_pushed(self):
        self.write_data(NEW_PROJECT)
        self.assertEqual(publish(self.repo), "committed new data; pushed 1 commit(s)")
        self.assertEqual(self.remote_messages(), [COMMIT_MESSAGE, "Initial data"])

    def test_other_uncommitted_files_are_left_alone(self):
        (self.repo / "notes.md").write_text("work in progress", encoding="utf-8")
        run_git(self.repo, "add", "notes.md")
        self.write_data(NEW_PROJECT)
        publish(self.repo)
        committed_files = run_git(self.remote, "show", "--name-only", "--format=", "main").split()
        self.assertEqual(committed_files, [DATA_FILE])
        self.assertIn("A  notes.md", run_git(self.repo, "status", "--porcelain"))

    def test_commit_left_behind_by_an_offline_run_is_pushed_next_time(self):
        self.write_data(NEW_PROJECT)
        run_git(self.repo, "commit", "-q", "-m", COMMIT_MESSAGE, "--", DATA_FILE)
        self.assertEqual(publish(self.repo), "no project changes; pushed 1 commit(s)")
        self.assertEqual(self.remote_messages(), [COMMIT_MESSAGE, "Initial data"])

    def test_failed_push_raises_so_launchd_logs_an_error(self):
        run_git(self.repo, "remote", "set-url", "origin", str(self.root / "missing.git"))
        self.write_data(NEW_PROJECT)
        with self.assertRaises(subprocess.CalledProcessError):
            publish(self.repo)
