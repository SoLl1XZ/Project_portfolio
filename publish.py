"""Rebuild data/projects.js and push it to GitHub when a project really changed (run weekly by launchd)."""

import subprocess
from pathlib import Path

import build

PORTFOLIO_DIR = Path(__file__).resolve().parent
DATA_FILE = "data/projects.js"
# build.py stamps every run with the time; a new timestamp alone is not worth a commit.
TIMESTAMP_LINE = '"generated":'
COMMIT_MESSAGE = "Rebuild portfolio data"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    # check=True makes a failed git command raise, so launchd logs it and records a non-zero exit code.
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


def has_real_changes(repo: Path) -> bool:
    """True when the data file differs from the last commit in more than the timestamp line."""
    result = git(repo, "diff", "--quiet", "-I", TIMESTAMP_LINE, "--", DATA_FILE, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    return result.returncode == 1


def unpushed_commit_count(repo: Path) -> int:
    return int(git(repo, "rev-list", "--count", "@{upstream}..HEAD").stdout)


def publish(repo: Path) -> str:
    """Commit the data file if it really changed, then push anything not yet on GitHub. Returns a log line."""
    if has_real_changes(repo):
        # Naming the path commits only the data file, even if other files have uncommitted edits.
        git(repo, "commit", "-m", COMMIT_MESSAGE, "--", DATA_FILE)
        action = "committed new data"
    else:
        # Drop the timestamp-only edit so the working tree stays clean.
        git(repo, "restore", "--", DATA_FILE)
        action = "no project changes"
    # Also pushes a commit left behind by an earlier run that was offline.
    unpushed = unpushed_commit_count(repo)
    if unpushed:
        git(repo, "push")
        return f"{action}; pushed {unpushed} commit(s)"
    return f"{action}; nothing to push"


def main() -> None:
    build.main()
    print(publish(PORTFOLIO_DIR))


if __name__ == "__main__":
    main()
