"""Upload the web app to a Hugging Face Space (Docker SDK).

Only what the app needs is uploaded: Dockerfile, pyproject, src/, app/, data/skills/ and
.streamlit/. Never .env, data/raw, evaluation data or resumes. The Space gets its own README
with the settings Hugging Face needs (sdk: docker, port 7860).

    HF_TOKEN=... python scripts/deploy_space.py <user>/<space-name>

Secrets the app needs (DATABASE_URL, GEMINI_API_KEY) are NOT uploaded: add them in the
Space's Settings -> Variables and secrets.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["Dockerfile", "pyproject.toml", "src", "app", "data/skills", ".streamlit"]
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info", ".env*", "*.pdf",
                              "labeler.py")   # labeller is a local dev tool

SPACE_README = """---
title: SkillPulse
emoji: 📈
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Live Indian job-skill demand + private resume gap analysis
---

# SkillPulse

What skills do Indian employers ask for right now, and how close is your resume?
Live job data (Jobs by Adzuna), refreshed nightly. Your resume is never stored.

Source code and methodology: https://github.com/nightcrawler2608/skillpulse
"""


def stage(dest: Path) -> None:
    for item in INCLUDE:
        src = ROOT / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=SKIP)
        else:
            (dest / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / item)
    (dest / "README.md").write_text(SPACE_README, encoding="utf-8")
    leaked = [p for p in dest.rglob("*") if p.name.startswith(".env")]
    if leaked:
        raise SystemExit(f"Refusing to upload secrets: {leaked}")


def main() -> int:
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        print(__doc__)
        return 2
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set.")
        return 2
    from huggingface_hub import HfApi

    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "local"
    with tempfile.TemporaryDirectory() as tmp:
        stage(Path(tmp))
        files = sum(1 for p in Path(tmp).rglob("*") if p.is_file())
        HfApi(token=token).upload_folder(
            repo_id=sys.argv[1], repo_type="space", folder_path=tmp,
            commit_message=f"Deploy {sha} from GitHub",
            delete_patterns=["*", "**/*"],   # remove files that no longer exist in the app
        )
    print(f"Uploaded {files} files to https://huggingface.co/spaces/{sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
