#!/usr/bin/env python3
"""Fetch the declared reference archive without changing existing artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import build_reference_manifest as inventory


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"


def download(url: str, relative_path: str) -> str:
    destination = REFERENCE / relative_path
    if destination.is_file() and destination.stat().st_size:
        return f"SKIP {relative_path}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    result = subprocess.run(
        [
            "curl",
            "-L",
            "--fail",
            "--retry",
            "3",
            "--retry-all-errors",
            "--connect-timeout",
            "20",
            "--max-time",
            "180",
            "--silent",
            "--show-error",
            "--user-agent",
            "Mozilla/5.0 (ACFQP reference archival; research use)",
            "--output",
            str(temporary),
            url,
        ],
        check=False,
    )
    if result.returncode:
        if temporary.exists():
            temporary.unlink()
        raise RuntimeError(f"download failed ({result.returncode}): {url}")
    temporary.replace(destination)
    return f"FETCH {relative_path}"


def clone(origin: str, relative_path: str) -> str:
    destination = REFERENCE / relative_path
    if (destination / ".git").is_dir():
        return f"SKIP {relative_path}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", origin, str(destination)],
        check=True,
    )
    return f"CLONE {relative_path}"


def main() -> int:
    actions = []
    for paper in inventory.PAPERS:
        actions.append(download(paper["download_url"], paper["pdf"]))
        page_url = paper.get("page_download_url", paper["source_url"])
        actions.append(download(page_url, paper["page"]))
    for page in inventory.PAGES:
        actions.append(download(page["source_url"], page["page"]))
    actions.append(
        download(
            "https://github.com/chrisvander/2048-Expectimax",
            "pages/github_chrisvander_2048-Expectimax.html",
        )
    )
    actions.append(
        download(
            "https://github.com/erzhu419/Laplace-semi-MDP",
            "pages/github_erzhu419_Laplace-semi-MDP.html",
        )
    )
    for _, origin, relative_path, _, _ in inventory.REPOSITORIES:
        actions.append(clone(origin, relative_path))
    print("\n".join(actions))
    return inventory.main()


if __name__ == "__main__":
    sys.exit(main())
