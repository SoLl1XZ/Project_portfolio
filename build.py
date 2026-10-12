"""Scan every project folder next to this one and write data/projects.js for the website."""

import json
import sys
from datetime import datetime
from pathlib import Path

from scan import scan_project

PORTFOLIO_DIR = Path(__file__).resolve().parent
PROJECTS_ROOT = PORTFOLIO_DIR.parent
OUTPUT_FILE = PORTFOLIO_DIR / "data" / "projects.js"
# Screenshots live in this repo (images/<folder>.jpg), because GitHub Pages only serves the portfolio itself.
IMAGES_DIR = PORTFOLIO_DIR / "images"
IMAGE_SUFFIX = ".jpg"


def find_project_dirs(root: Path, exclude: Path) -> list[Path]:
    """Every visible subfolder of root except `exclude` (the portfolio itself), alphabetically."""
    return sorted(
        path for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.resolve() != exclude.resolve()
    )


def collect_projects(project_dirs: list[Path]) -> list[dict]:
    """Scan each folder and return the visible projects, most recently updated first."""
    projects = []
    for project_dir in project_dirs:
        try:
            project = scan_project(project_dir)
        except ValueError as error:
            # Skip instead of showing it without overrides: a typo must never un-hide a hidden project.
            print(f"warning: skipped {project_dir.name}: {error}", file=sys.stderr)
            continue
        if project is not None:
            projects.append(project)
    # sorted() is stable, so projects updated the same day keep their alphabetical order.
    return sorted(projects, key=lambda project: project["updated"], reverse=True)


def attach_images(projects: list[dict], images_dir: Path) -> list[dict]:
    """Give each project with a screenshot in images_dir an "image" path, and list those projects first."""
    for project in projects:
        screenshot = images_dir / f"{project['folder']}{IMAGE_SUFFIX}"
        if screenshot.is_file():
            # Relative to index.html, so the page works both on GitHub Pages and via file://.
            project["image"] = f"{images_dir.name}/{screenshot.name}"
    # A project with a screenshot gets the large card at the top. sorted() is stable, so the
    # newest-first order from collect_projects is kept within each group.
    return sorted(projects, key=lambda project: "image" not in project)


def render_data_file(projects: list[dict], generated: str) -> str:
    """A .js file rather than .json, because a page opened via file:// may not fetch() local files."""
    payload = {"generated": generated, "projects": projects}
    return f"window.PORTFOLIO_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n"


def main() -> None:
    projects = attach_images(collect_projects(find_project_dirs(PROJECTS_ROOT, exclude=PORTFOLIO_DIR)), IMAGES_DIR)
    generated = datetime.now().isoformat(timespec="minutes")
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(render_data_file(projects, generated), encoding="utf-8")
    # The timestamp makes logs/build.log show when the weekly launchd run last happened.
    print(f"{generated}  wrote {len(projects)} projects to {OUTPUT_FILE.relative_to(PORTFOLIO_DIR)}")


if __name__ == "__main__":
    main()
