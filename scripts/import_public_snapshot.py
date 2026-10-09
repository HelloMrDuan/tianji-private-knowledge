"""Import the pinned public HEAD data into the owner's PRIVATE GitHub repository.

Runs exclusively in the authenticated private GitHub Actions environment.
No data is displayed in the logs. Never auto-refreshes to a moving source HEAD.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCE_REPO = "HelloMrDuan/tianji-knowledge-base"
SOURCE_COMMIT = "da3aef06ad03a02c94770689f7cc1510b0d4593e"
PRIVATE_REPO = "HelloMrDuan/tianji-private-knowledge"
EXPECTED_FILES = 235
EXPECTED_BYTES = 13518179
AREAS = (
    "audit", "canonical", "coverage", "index", "product", "quarantine",
    "reference", "registry", "research", "state", "upstream",
)
MANIFEST_NAME = "private-data-manifest.json"
SCHEMA = "private-data-snapshot-v2"


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[dict]:
    data = root / "data"
    if data.is_symlink() or not data.is_dir():
        raise ValueError("Missing or unsafe private data directory")
    if {item.name for item in data.iterdir()} != set(AREAS):
        raise ValueError("Unexpected or missing knowledge asset area")
    rows: list[dict] = []
    for area in AREAS:
        directory = data / area
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Unsafe asset area")
        count = 0
        for current, directories, files in os.walk(directory, followlinks=False):
            current = Path(current)
            for name in directories:
                node = current / name
                if node.is_symlink() or not node.is_dir():
                    raise ValueError("Unsafe knowledge subdirectory")
            for name in sorted(files):
                path = current / name
                if path.is_symlink() or not path.is_file():
                    raise ValueError("Unsafe knowledge file")
                rows.append({
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash(path),
                })
                count += 1
        if not count:
            raise ValueError("Empty knowledge area")
    return sorted(rows, key=lambda row: row["path"])


def manifest_for(rows: list[dict]) -> dict:
    if (len(rows) != EXPECTED_FILES or
            sum(row["bytes"] for row in rows) != EXPECTED_BYTES):
        raise ValueError("Pinned upstream snapshot file count or size changed")
    return {
        "schema_version": SCHEMA,
        "areas": list(AREAS),
        "file_count": len(rows),
        "total_bytes": EXPECTED_BYTES,
        "files": rows,
        "source_repository": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "warning": "RESTRICTED PRIVATE ASSETS; historical public disclosure remains",
    }


def verify(root: Path) -> dict:
    path = root / MANIFEST_NAME
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing private data manifest")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    rows = inventory(root)
    if manifest != manifest_for(rows):
        raise ValueError("Private manifest or copied knowledge bytes do not match")
    return manifest


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.DEVNULL)


def main() -> None:
    if (os.getenv("GITHUB_ACTIONS", "").lower() != "true" or
            os.getenv("GITHUB_REPOSITORY", "").lower() != PRIVATE_REPO.lower()):
        raise SystemExit("Run only in the provisioned private GitHub Actions repository")

    root = Path.cwd().resolve(strict=True)
    if not (root / ".git").exists():
        raise SystemExit("Missing authenticated private Git checkout")

    if (root / "data").exists() or (root / MANIFEST_NAME).exists():
        result = verify(root)
        print("Existing private snapshot verified:",
              result["file_count"], "files;", result["total_bytes"], "bytes")
        return

    with tempfile.TemporaryDirectory(prefix="tianji-source-") as temporary:
        source = Path(temporary) / "source"
        run("git", "clone", "--quiet", "--no-checkout", "--depth", "1",
            f"https://github.com/{SOURCE_REPO}.git", str(source))
        run("git", "fetch", "--quiet", "--depth", "1", "origin", SOURCE_COMMIT, cwd=source)
        run("git", "checkout", "--quiet", "--detach", SOURCE_COMMIT, cwd=source)
        observed_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True
        ).strip()
        if observed_commit != SOURCE_COMMIT:
            raise ValueError("Source commit pin mismatch")

        upstream = manifest_for(inventory(source))
        # Copy into a separate verification root; do not read from or merge
        # with any existing private HEAD data.
        data_temp = root / ".private-import-verify"
        if data_temp.exists() or data_temp.is_symlink():
            raise ValueError("Existing private verification stage")
        data_temp.mkdir(mode=0o700)
        try:
            shutil.copytree(source / "data", data_temp / "data", symlinks=False)
            actual = manifest_for(inventory(data_temp))
            if actual != upstream:
                raise ValueError("Private snapshot copy mismatched pinned source")
            (data_temp / MANIFEST_NAME).write_text(
                json.dumps(actual, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            # Verify after disk copy, before making data visible in repo HEAD.
            verify(data_temp)
            (data_temp / "data").rename(root / "data")
            (data_temp / MANIFEST_NAME).rename(root / MANIFEST_NAME)
        finally:
            shutil.rmtree(data_temp, ignore_errors=True)

    result = verify(root)
    print("Restricted snapshot imported and verified:",
          result["file_count"], "files;", result["total_bytes"], "bytes")


if __name__ == "__main__":
    main()
