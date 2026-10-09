"""Verify a source-free Tianji runtime before confidential deployment.

This command inspects a *local private* sealed bundle. It never uploads an
artifact, reads credentials, or enables publication to a web/static root.
The digest is supplied by the release build as a separate required pin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

DIGEST = re.compile(r"[0-9a-f]{64}\\Z")
BUNDLE_FILES = frozenset({"build/production_runtime.json", "build/production_rag.jsonl"})
FORBIDDEN = frozenset({"config", "schemas", "web", "docs", "tests", ".git", "node_modules", "private-data-manifest.json"})


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_bundle(bundle: Path, pin: str) -> dict:
    """Fail closed on unexpected paths, symlinks, or a mismatched external pin."""
    if not bundle.is_absolute() or bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("Bundle must be an existing absolute non-symlink directory")
    if not DIGEST.fullmatch(pin):
        raise ValueError("Expected a full external SHA256 pin")
    bundle = bundle.resolve(strict=True)
    actual = set()
    for path in bundle.rglob("*"):
        if path.is_symlink():
            raise ValueError("Sealed bundle contains a symlink")
        relative = path.relative_to(bundle).as_posix()
        if any(part in FORBIDDEN for part in path.relative_to(bundle).parts):
            raise ValueError("Unexpected source or public asset in sealed bundle")
        if path.is_file():
            actual.add(relative)
        elif not path.is_dir():
            raise ValueError("Unsupported sealed bundle node")
    if not BUNDLE_FILES <= actual:
        raise ValueError("Required sealed artifacts missing")
    code = {name for name in actual if name.startswith("src/tianji_kb/")}
    tables = {name for name in actual if name.startswith("data/")}
    if not code or any(not n.endswith(".py") for n in code):
        raise ValueError("Unexpected Python engine files")
    if any(not n.startswith(("src/tianji_kb/", "data/")) for n in actual - BUNDLE_FILES):
        raise ValueError("Unexpected sealed runtime file")
    sys.path.insert(0, str(bundle / "src"))
    try:
        from tianji_kb.sealed_bundle import RUNTIME_TABLES
    finally:
        sys.path.pop(0)
    if tables != set(RUNTIME_TABLES):
        raise ValueError("Engine table allowlist mismatch")
    if _sha(bundle / "build/production_runtime.json") != pin:
        raise ValueError("Sealed runtime SHA256 pin mismatch")
    return {"sha256_pin": pin, "engine_modules": len(code), "engine_tables": len(tables)}


CHECK_RUNTIME = """
from fastapi.testclient import TestClient
from tianji_kb.api import create_app
from tianji_kb.resolver import ROOT
from tianji_kb.runtime_catalog import load_catalog
load_catalog(ROOT)
client = TestClient(create_app(admin_read_token='private-smoke-only'))
health = client.get('/health')
assert health.status_code == 200, health.text
assert health.json().get('rag_ready') is True
bazi = client.post('/api/v1/public/execute', json={
    'domain': 'bazi', 'variant': 'ziping-structural-v1',
    'input': {'value': '2000-01-07T12:00:00+08:00'},
    'mode': 'production', 'explain': False})
assert bazi.status_code == 200, bazi.text
assert bazi.json()['chart']['day_master']['stem'] == '甲'
dream = client.post('/api/v1/dream/culture', json={'dream_text': '我梦见被蛇咬了'})
assert dream.status_code == 200, dream.text
assert dream.json()['status'] == 'reviewed_cultural_matches'
hidden = client.post('/api/v1/admin/research/dream', json={'dream_text': '我梦见被蛇咬了'})
assert hidden.status_code == 401
print('SEALED_RUNTIME_VERIFIED: private API, Bazi, dream, admin isolation')
"""


def validate_runtime(bundle: Path, pin: str) -> dict:
    report = inspect_bundle(bundle, pin)
    bundle = bundle.resolve(strict=True)
    env = os.environ.copy()
    env.update({
        "TIANJI_RUNTIME_MODE": "sealed",
        "TIANJI_RUNTIME_ROOT": str(bundle),
        "TIANJI_RUNTIME_SHA256": pin,
        "PYTHONPATH": str(bundle / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    result = subprocess.run([sys.executable, "-c", CHECK_RUNTIME], cwd=bundle,
                            env=env, text=True, capture_output=True, timeout=120)
    if result.returncode != 0:
        # No entire model responses or private file contents should reach Actions logs.
        raise ValueError("Private sealed API acceptance test failed (details withheld)")
    if "SEALED_RUNTIME_VERIFIED" not in result.stdout:
        raise ValueError("Sealed acceptance marker missing")
    report["private_api_smoke"] = "passed"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify sealed backend using an external SHA256 pin")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--pin", required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    report = validate_runtime(args.bundle, args.pin) if args.smoke else inspect_bundle(args.bundle, args.pin)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
