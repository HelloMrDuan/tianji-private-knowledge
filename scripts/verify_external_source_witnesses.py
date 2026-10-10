"""Fail-closed external source witness registry; no publication authority."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DREAM = ROOT / "private-reviews/dream_external_witnesses_v1.json"
DAYUN = ROOT / "private-reviews/dayun_external_witnesses_v1.json"
EXPECTED_DREAM = {
    "zhougong-deceased": ("死人复活主有信", "死人复活主有信"),
    "zhougong-death-variant": ("见人死自死者吉", "见人死自死皆吉"),
}
EXPECTED_DAYUN = {
    "yuanhai-direction": "陽男陰女順行",
    "yuanhai-ratio": "俱折除三日爲一歲",
    "sanche-independent-work": "三日为一年",
}

def _ensure(condition, message):
    if not condition:
        raise ValueError("Source witness integrity: " + message)

def validate(dream, dayun):
    _ensure(dream["id"] == "research.dream.external-witness-register.v1"
            and dayun["id"] == "research.dayun.external-witness-register.v1",
            "identity drift")
    _ensure(dream["evidence_level"] == dayun["evidence_level"] == "D",
            "unauthorized evidence promotion")
    _ensure(dream["review_status"] == "transcription_comparison_only"
            and dayun["review_status"] ==
            "textual_comparison_not_method_adjudication", "review status drift")
    drows = {r["id"]: r for r in dream["witnesses"]}
    _ensure(len(drows) == len(dream["witnesses"]) == 2
            and set(drows) == set(EXPECTED_DREAM), "dream inventory")
    for key, excerpts in EXPECTED_DREAM.items():
        r = drows[key]
        _ensure((r["transcribed_excerpt"], r["pinned_original_excerpt"]) ==
                excerpts and r["section"] == "哀乐病死歌唱"
                and r["url"].startswith("https://zh.wikisource.org/")
                and "不" in r["semantic_scope"], "dream witness mismatch")
    arows = {r["id"]: r for r in dayun["witnesses"]}
    _ensure(len(arows) == len(dayun["witnesses"]) == 3
            and set(arows) == set(EXPECTED_DAYUN), "dayun inventory")
    for key, excerpt in EXPECTED_DAYUN.items():
        r = arows[key]
        _ensure(r["exact_excerpt"] == excerpt
                and r["url"].startswith("https://")
                and r["research_status"] == "transcription_located"
                and "不" in r["claim_scope"], "dayun witness mismatch")
    _ensure(all(v is False or v == 0 for v in dream["gate"].values())
            and all(v is False or v == 0 for v in dayun["gate"].values()),
            "unreviewed sources cannot authorize release")
    _ensure(len(dream["bibliography_leads"]) == 2
            and all(x["status"] == "bibliography_only"
                    and x["url"].startswith("https://ctext.org/library.pl?")
                    for x in dream["bibliography_leads"]), "invalid book catalogue")
    _ensure(len(dayun["conflict_register"]) == 3
            and all(x["status"] == "unresolved"
                    for x in dayun["conflict_register"]), "conflicts were hidden")
    return {"dream_excerpt_witnesses": 2, "dayun_excerpt_witnesses": 3,
            "bibliography_leads": 2, "production_promotions": 0}

def verify():
    dream = json.loads(DREAM.read_text(encoding="utf-8"))
    dayun = json.loads(DAYUN.read_text(encoding="utf-8"))
    try:
        from scripts.import_public_snapshot import verify as check_private
    except ModuleNotFoundError:
        from import_public_snapshot import verify as check_private
    _ensure(check_private(ROOT)["file_count"] == 235,
            "private canonical inventory drift")
    return validate(dream, dayun)

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
