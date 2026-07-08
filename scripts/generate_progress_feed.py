from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "site" / "public" / "generated"


def _git_lines(args: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> None:
    commits = []
    for line in _git_lines(["log", "-8", "--date=short", "--pretty=format:%h%x09%ad%x09%s"]):
        sha, date, subject = line.split("\t", 2)
        commits.append({"sha": sha, "date": date, "subject": subject})

    feed = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "commits": commits,
        "pullRequests": [],
        "issues": [],
        "note": "CI may replace this with GitHub API data during release builds.",
    }

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / "progress.json").write_text(json.dumps(feed, indent=2) + "\n")


if __name__ == "__main__":
    main()
