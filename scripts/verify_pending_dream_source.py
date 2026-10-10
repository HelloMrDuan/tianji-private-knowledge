"""Fail-closed private verifier for unreviewed historical dream candidates.

Not a production Dream retrieval adapter or a source promotion tool.
Only audits bytes from the pinned single Git blob given by the caller.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
APPENDIX = BASE / "private-reviews/dream_pending_original_v1.json"
SNAPSHOT = BASE / "data/quarantine/public_domain_snapshots/daizhigev20/zhougong_dream_candidates.json"
COMMIT = "4a6d6f2088825f132521d848c2ea86cf9c9a7620"
BLOB = "0c7b0823265c4ff00465f833e0be28f1bf0f2175"
SOURCE_SHA = "d80c42b0b8f44f5b8cf2c4e1c286b200388b65dcd321347eb7ac1011d0be5e97"
CANDIDATES = {
    "death": ("见人死自死皆吉", 5941, "direct_scene"),
    "deceased": ("死人复活主有信", 5933, "related_only"),
    "chased": (None, None, "not_found"),
    "pregnancy": ("携手上桥妻有孕", 4619, "related_only"),
    "marriage": ("夫妇宴会主相别", 4703, "related_only"),
    "work": ("受职上官财物来", 5541, "related_only"),
    "exam": ("读书文写字大吉", 5415, "related_only"),
}


def _assert(condition, message):
    if not condition:
        raise ValueError("Dream candidate source integrity: " + message)


def verify_pending_review(raw_bytes, snapshot, appendix):
    """Compare real pinned original text, D-level candidates and non-release gates."""
    _assert(type(raw_bytes) is bytes, "original UTF-8 bytes are required")
    _assert(hashlib.sha256(raw_bytes).hexdigest() == SOURCE_SHA,
            "original source digest changed")
    blob = b"blob " + str(len(raw_bytes)).encode("ascii") + b"\0" + raw_bytes
    _assert(hashlib.sha1(blob).hexdigest() == BLOB, "git blob identity changed")
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("Dream candidate source integrity: invalid UTF-8") from error
    _assert(isinstance(snapshot, dict) and isinstance(appendix, dict),
            "invalid review records")
    provenance = appendix.get("provenance", {})
    _assert(provenance == {
        "repository": "garychowcmu/daizhigev20",
        "commit": COMMIT, "path": "易藏/术数/周公解梦.txt",
        "git_blob": BLOB, "sha256": SOURCE_SHA,
        "snapshot": "data/quarantine/public_domain_snapshots/daizhigev20/zhougong_dream_candidates.json",
    }, "appendix provenance changed")
    _assert(snapshot.get("pinned_commit") == COMMIT
            and snapshot.get("blob_sha") == BLOB and snapshot.get("sha256") == SOURCE_SHA
            and snapshot.get("review_status") == "pending"
            and snapshot.get("canonical_ready") is False
            and snapshot.get("promotion") == "quarantine_only",
            "snapshot source or candidate maturity changed")
    _assert(appendix.get("id") == "dream.pending.original-source-audit.v1"
            and appendix.get("schema_version") == "1.0"
            and isinstance(appendix.get("candidates"), list)
            and len(appendix["candidates"]) == len(CANDIDATES),
            "unexpected appendix schema")
    manifest = {item.get("id"): item for item in snapshot.get("candidates", [])}
    seen = set()
    for item in appendix["candidates"]:
        _assert(isinstance(item, dict), "invalid appended candidate")
        name = item.get("id")
        _assert(name in CANDIDATES and name not in seen and name in manifest,
                "unknown, duplicate or missing candidate")
        seen.add(name)
        quote, offset, scope = CANDIDATES[name]
        actual = manifest[name]
        for row in (item, actual):
            _assert(row.get("exact_anchor") == quote
                    and row.get("raw_unicode_offset") == offset
                    and row.get("match_scope") == scope
                    and row.get("review_status") == "pending"
                    and row.get("evidence_level") == "D"
                    and row.get("production_allowed") is False,
                    "candidate claim or approval status changed")
        _assert(not actual.get("reviewed_term_id")
                and not actual.get("reviewed_rule_id"),
                "pending candidate cannot enter reviewed rule registry")
        _assert(isinstance(item.get("semantic_limit"), str)
                and len(item["semantic_limit"]) >= 20,
                "candidate requires semantic exclusion")
        if quote is not None:
            _assert(type(offset) is int and raw[offset:offset+len(quote)] == quote
                    and raw.count(quote) == 1,
                    "original quote does not uniquely match its declared offset")
        else:
            _assert(offset is None and scope == "not_found",
                    "unsupported source absence is not evidence")
    _assert(seen == set(CANDIDATES), "incomplete candidate audit")
    _assert(appendix.get("promotion") == {
        "phase1_rules": 0, "phase2_rules": 0, "golden_cases": 0,
        "public_enabled": False, "ai_enabled": False,
        "independent_source_verified": False,
    }, "unreviewed candidate must not be promoted")
    return {"source_verified": True, "candidate_count": len(seen),
            "evidence_level": "D", "released": False,
            "independent_source_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-raw", required=True, type=Path)
    args = parser.parse_args()
    from import_public_snapshot import verify as verify_snapshot
    snapshot_manifest = verify_snapshot(BASE)
    _assert(snapshot_manifest["file_count"] == 235,
            "protected data inventory changed")
    result = verify_pending_review(
        args.original_raw.read_bytes(),
        json.loads(SNAPSHOT.read_text("utf-8")),
        json.loads(APPENDIX.read_text("utf-8")),
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
