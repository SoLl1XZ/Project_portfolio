import tempfile
import unittest
from pathlib import Path


def make_project(root: Path, name: str, files: dict[str, str]) -> Path:
    """Create a project folder under root with the given {relative path: content} files."""
    project_dir = root / name
    project_dir.mkdir()
    for relative_path, content in files.items():
        path = project_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return project_dir


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
