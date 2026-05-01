"""
Snapshot helper — saves the current state of the tracker before
making destructive edits. Always run this before starting a new
feature branch or major refactor.

Usage:
    python tools/snapshot.py <tag>           # tag = a short version label
    python tools/snapshot.py "v2.1-cnh-fix"
    python tools/snapshot.py "before-rewrite"

It copies:
    web/index.html       → history/<tag>/index.html
    web/dashboard.js     → history/<tag>/dashboard.js
    web/data.json        → history/<tag>/data.json
    analytics.py         → history/<tag>/analytics.py
    data_fetcher.py      → history/<tag>/data_fetcher.py
    build.py             → history/<tag>/build.py
    config.py            → history/<tag>/config.py
    + writes a manifest.json with timestamp + git status (if git available)

After running, also append an entry to CHANGELOG.md describing what
the next edit will do and why.
"""

import shutil
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parent.parent.resolve()
HISTORY = ROOT / "history"

SNAPSHOT_FILES = [
    # Public site (renamed from web/ → docs/ for GitHub Pages, v3.0)
    "docs/index.html",
    "docs/dashboard.js",
    "docs/data.json",
    # Legacy web/ paths kept so old snapshots still work if files exist
    "web/index.html",
    "web/dashboard.js",
    "web/data.json",
    # Python pipeline
    "analytics.py",
    "data_fetcher.py",
    "build.py",
    "config.py",
    "charts.py",
    "app.py",
]


def main():
    if len(sys.argv) < 2:
        print("✗ Missing tag.")
        print("  Usage: python tools/snapshot.py <tag>")
        print("  Example: python tools/snapshot.py 'v2.1-cnh-fix'")
        sys.exit(1)

    tag = sys.argv[1].strip().replace(" ", "-")
    target = HISTORY / tag

    if target.exists():
        print(f"⚠️  history/{tag}/ already exists.")
        ans = input("Overwrite? [y/N] ")
        if ans.lower() != "y":
            print("Aborted.")
            sys.exit(0)
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    saved = []
    skipped = []
    for rel in SNAPSHOT_FILES:
        src = ROOT / rel
        if not src.exists():
            skipped.append(rel)
            continue
        # Flatten into target dir, prefixing with subdir if any
        dst_name = rel.replace("/", "__")
        shutil.copy2(src, target / dst_name)
        saved.append(rel)

    # Manifest
    manifest = {
        "tag": tag,
        "timestamp": datetime.now().isoformat(),
        "files_saved": saved,
        "files_skipped": skipped,
    }

    # Add git info if available
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
        manifest["git_sha"] = sha
        manifest["git_dirty"] = bool(status)
        manifest["git_status"] = status.splitlines()[:20]  # first 20 lines
    except (subprocess.CalledProcessError, FileNotFoundError):
        manifest["git_sha"] = None

    with open(target / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✓ Snapshot saved to history/{tag}/")
    print(f"  Files: {len(saved)} saved, {len(skipped)} skipped")
    if skipped:
        print(f"  Skipped (not present): {', '.join(skipped)}")
    print()
    print(f"→ Next: append a new entry to CHANGELOG.md describing the upcoming edit.")


if __name__ == "__main__":
    main()
