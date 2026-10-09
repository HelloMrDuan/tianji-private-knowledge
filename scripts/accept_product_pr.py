"""Run new product regressions with actual PRIVATE knowledge in an isolated backend.

Use only a trusted checked-out owner code commit in this PRIVATE repository.
It never modifies the tracked data, manifest, or code checkout and never
downloads a public or fabricated knowledge fallback.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PRIVATE_REPO = "HelloMrDuan/tianji-private-knowledge"
TEST_MODULES = {
    "career": "test_career_interpretation",
    "romance": "test_romance_spouse_year_structure",
    "periods": "test_daily_period_branch_relations",
}
BASELINE_TEST = "test_scenario_engine"


def _run(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    """Fixed argv only; never use a shell or execute caller-supplied commands."""
    subprocess.run(argv, cwd=cwd, env=env, check=True)


def _private_manifest(repo: Path) -> dict:
    path = repo / "scripts" / "import_public_snapshot.py"
    spec = importlib.util.spec_from_file_location("private_snapshot_import", path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load private manifest verifier")
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    return importer.verify(repo)


def _assert_public_checkout(code: Path, expected_sha: str) -> None:
    if code.is_symlink() or not code.is_dir():
        raise ValueError("Public code checkout is missing or unsafe")
    if (code / "data").exists() or (code / "data").is_symlink():
        raise ValueError("Public code checkout must not contain private data")
    if len(expected_sha) != 40 or any(c not in "0123456789abcdef" for c in expected_sha):
        raise ValueError("Expected exact 40-character public commit SHA")
    origin = subprocess.check_output(
        ["git", "-C", str(code), "remote", "get-url", "origin"], text=True,
    ).strip()
    trusted_origins = {
        "https://github.com/HelloMrDuan/tianji-knowledge-base",
        "https://github.com/HelloMrDuan/tianji-knowledge-base.git",
        "git@github.com:HelloMrDuan/tianji-knowledge-base.git",
    }
    if origin not in trusted_origins:
        raise ValueError("Only the owner's public repository is accepted")
    observed = subprocess.check_output(
        ["git", "-C", str(code), "rev-parse", "HEAD"], text=True,
    ).strip()
    if observed != expected_sha:
        raise ValueError("Public code checkout does not match expected pinned SHA")
    # No local edits or untracked scripts from an uncontrolled workspace.
    changes = subprocess.check_output(
        ["git", "-C", str(code), "status", "--porcelain", "--untracked-files=all",
         "--", "config", "src", "scripts", "tests", "schemas", "evals", "docs",
         "pyproject.toml"], text=True,
    ).strip()
    if changes:
        raise ValueError("Public code checkout has unreviewed local files or edits")


def modules_for(suite: str) -> list[str]:
    if suite == "all":
        return [*TEST_MODULES.values(), BASELINE_TEST]
    if suite not in TEST_MODULES:
        raise ValueError("Unknown real-data product suite")
    return [TEST_MODULES[suite], BASELINE_TEST]


def run_acceptance(private: Path, code: Path, expected_sha: str, suite: str) -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        if os.environ.get("GITHUB_REPOSITORY", "").lower() != PRIVATE_REPO.lower():
            raise ValueError("CI acceptance may run only in the private repository")
    private = private.resolve(strict=True)
    code = code.resolve(strict=True)
    _assert_public_checkout(code, expected_sha)
    inventory = _private_manifest(private)
    if inventory["source_commit"] != "da3aef06ad03a02c94770689f7cc1510b0d4593e":
        raise ValueError("Unexpected pinned private source history")

    modules = modules_for(suite)
    for name in modules:
        if not (code / "tests" / (name + ".py")).is_file():
            raise ValueError("Requested real test is missing: " + name)

    temp_base = Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
    temp_base = temp_base.resolve(strict=True)
    if (temp_base / ".git").exists() or temp_base.is_relative_to(private) or temp_base.is_relative_to(code):
        raise ValueError("Private verification needs a non-Git external runner directory")
    with tempfile.TemporaryDirectory(prefix="tianji-private-product-", dir=temp_base) as temporary:
        stage = Path(temporary)
        stage.chmod(0o700)
        snapshot = stage / "snapshot"
        snapshot.mkdir(mode=0o700)
        shutil.copytree(private / "data", snapshot / "data", symlinks=False)
        shutil.copy2(private / "private-data-manifest.json", snapshot / "private-data-manifest.json")
        sys.path.insert(0, str(code))
        try:
            from scripts.assemble_private_backend import assemble_private_backend
            assembled = stage / "backend"
            details = assemble_private_backend(code, snapshot, assembled)
        finally:
            sys.path.remove(str(code))
        if details["knowledge_files"] != inventory["file_count"]:
            raise ValueError("Assembled knowledge asset count differs from private manifest")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join((str(assembled / "src"), str(assembled / "tests")))
        # This is a mutable EPHEMERAL runtime, never the tracked private HEAD.
        # Rebuild derived data from new code, then independently check it for drift.
        _run([sys.executable, "scripts/validate_kb.py"], cwd=assembled, env=env)
        _run([sys.executable, "scripts/validate_knowledge.py"], cwd=assembled, env=env)
        _run([sys.executable, "scripts/build_production_runtime.py"], cwd=assembled, env=env)
        _run([sys.executable, "scripts/validate_phase2.py"], cwd=assembled, env=env)
        _run([sys.executable, "scripts/build_product_coverage.py"], cwd=assembled, env=env)
        _run([sys.executable, "scripts/build_product_coverage.py", "--check"], cwd=assembled, env=env)
        _run([sys.executable, "-m", "unittest", "-v", *modules], cwd=assembled, env=env)
        print(json.dumps({
            "status": "pass", "public_sha": expected_sha, "suite": suite,
            "private_files_verified": inventory["file_count"],
            "real_unittest_modules": modules,
            "source_manifest_preserved": True,
        }))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-code", type=Path, required=True)
    parser.add_argument("--expected-sha", type=str, required=True)
    parser.add_argument("--suite", choices=(*TEST_MODULES, "all"), required=True)
    args = parser.parse_args()
    run_acceptance(Path(__file__).resolve().parents[1],
                   args.public_code, args.expected_sha, args.suite)


if __name__ == "__main__":
    main()
