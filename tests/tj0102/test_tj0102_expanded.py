"""TJ-010.2: actual scoped matrix regression in sealed private runtime.

All cases invoke real four-pillar computation, real rules and production catalog.
No mocks, no skipped cases, no vacuous loops or hand-forged relationships.
"""
from copy import deepcopy

from tianji_kb.bazi_core import chart_from_datetime, chart_from_pillars, reviewed_relations
from tianji_kb.bazi_action_matrix import build_matrix_from_chart


def _run(year="甲寅", month="壬子", day="甲寅", hour="己酉"):
    chart = chart_from_pillars(year, month, day, hour)
    return chart, build_matrix_from_chart(chart)


def _roots_in(matrix, branch):
    return [r for r in matrix["roots"] if r["branch"] == branch]


def test_01_datetime_actual_calculation():
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    matrix = build_matrix_from_chart(chart)
    assert chart["deterministic"] is True
    assert len(chart["pillars"]) == 4
    assert matrix["day_master"] == chart["pillars"][2]["stem"]["value"]
    assert matrix["summary"]
    assert sum(matrix["summary"].values()) == sum(len(matrix[k]) for k in ("roots", "exposures", "actions"))


def test_02_no_root_actual_negative():
    chart, matrix = _run("庚子", "辛丑", "甲午", "丙申")
    assert chart["day_master"]["element"] == "木"
    assert matrix["roots"] == [], matrix["roots"]
    assert matrix["summary"].get("effective", 0) == 0, matrix["summary"]


def test_03_root_positions_actual_positive():
    chart, matrix = _run()
    roots = _roots_in(matrix, "寅")
    assert {r["pillar"] for r in roots} == {"year", "day"}, roots
    assert all(r["hidden_stem"] == "甲" and r["status"] == "effective" for r in roots), roots


def test_04_real_hidden_stem_exposure_positive():
    chart, matrix = _run("丙寅", "壬子", "甲寅", "丙午")
    matching = [e for e in matrix["exposures"]
                if e["hidden_stem"] == "丙" and e["hidden_pillar"] == "year"]
    assert len(matching) == 1, matching
    assert matching[0]["status"] == "observed"
    assert set(matching[0]["exposed_in"]) == {"year", "hour"}


def test_05_real_hidden_stem_exposure_negative():
    _, matrix = _run()
    missing = [e for e in matrix["exposures"]
               if e["hidden_stem"] == "丙" and e["hidden_pillar"] == "year"]
    assert len(missing) == 1, missing
    assert missing[0]["status"] == "not_applicable"
    assert missing[0]["exposed_in"] == []


def test_06_real_support_directions_at_positions():
    _, matrix = _run("甲寅", "壬子", "甲寅", "丁卯")
    directions = {row["pillar"]: row["relation"] for row in matrix["actions"]}
    assert directions == {
        "year": "same_element", "month": "generates_me", "hour": "i_generate"
    }, directions


def test_07_real_control_and_consumption_directions():
    _, matrix = _run("庚申", "戊子", "甲寅", "丙寅")
    directions = {row["pillar"]: row["relation"] for row in matrix["actions"]}
    assert directions == {
        "year": "controls_me", "month": "i_control", "hour": "i_generate"
    }, directions


def test_08_audited_effective_root_positive():
    _, matrix = _run()
    roots = _roots_in(matrix, "寅")
    assert roots
    assert all(row["status"] == "effective" and row["status_reason"] == "reviewed_sufficient_conditions"
               and row["availability"] == "effective" for row in roots)


def test_09_real_yin_shen_clash_abstains():
    chart, matrix = _run("甲寅", "壬申", "甲寅", "己酉")
    s = [p["stem"]["value"] for p in chart["pillars"]]
    b = [p["branch"]["value"] for p in chart["pillars"]]
    relations = reviewed_relations(s, b)
    assert any(set(r["branches"]) == {"寅", "申"} for r in relations["branch_six_clashes"])
    roots = _roots_in(matrix, "寅")
    assert roots
    assert all(r["status"] == "unresolved" and
               r["status_reason"] == "branch_interaction_effect_unresolved" for r in roots), roots


def test_10_same_root_without_clash_effective():
    _, clashed = _run("甲寅", "壬申", "甲寅", "己酉")
    _, baseline = _run()
    affected = _roots_in(clashed, "寅")
    unaffected = _roots_in(baseline, "寅")
    assert affected and unaffected
    assert all(r["status"] == "unresolved" for r in affected)
    assert all(r["status"] == "effective" for r in unaffected)
    assert {(r["pillar"], r["hidden_stem"]) for r in affected} == {
        (r["pillar"], r["hidden_stem"]) for r in unaffected
    }


def test_11_reviewed_six_harmony_abstains_on_wood_root():
    chart, matrix = _run("甲寅", "癸亥", "甲寅", "己酉")
    rel = reviewed_relations(
        [p["stem"]["value"] for p in chart["pillars"]],
        [p["branch"]["value"] for p in chart["pillars"]]
    )
    assert any(set(r["branches"]) == {"寅", "亥"} for r in rel["branch_six_harmonies"])
    roots = _roots_in(matrix, "寅")
    assert roots
    assert all(r["status"] == "unresolved" for r in roots), roots


def test_12_reviewed_stem_combination_action_unresolved():
    chart, matrix = _run("己酉", "壬子", "甲寅", "己卯")
    rel = reviewed_relations(
        [p["stem"]["value"] for p in chart["pillars"]],
        [p["branch"]["value"] for p in chart["pillars"]]
    )
    assert any(set(r["stems"]) == {"甲", "己"} for r in rel["stem_five_combinations"])
    affected = [r for r in matrix["actions"] if r["stem"] == "己"]
    assert {r["pillar"] for r in affected} == {"year", "hour"}, affected
    assert all(r["status"] == "unresolved" and r["status_reason"] == "interaction_conflict"
               for r in affected), affected


def test_13_unsupported_root_scope_not_promoted():
    _, matrix = _run("癸未", "辛酉", "乙未", "丁亥")
    roots = _roots_in(matrix, "未")
    assert roots, "Expected structural residual wood roots"
    assert all(r["status"] != "effective" for r in roots), roots


def test_14_invalid_sexagenary_pair_rejected():
    chart = chart_from_pillars("甲寅", "壬子", "甲寅", "己酉")
    forged = deepcopy(chart)
    forged["pillars"][0]["stem"]["value"] = "乙"  # 乙寅 is not a valid sexagenary pair
    try:
        build_matrix_from_chart(forged)
    except ValueError as exc:
        assert "ganzhi" in str(exc) or "combination" in str(exc), exc
    else:
        raise AssertionError("Invalid 乙寅 must not produce a matrix")


def test_15_inconsistent_day_master_rejected():
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    forged = deepcopy(chart)
    forged["day_master"]["stem"] = "乙" if chart["day_master"]["stem"] != "乙" else "丙"
    try:
        build_matrix_from_chart(forged)
    except ValueError as exc:
        assert "day_master" in str(exc), exc
    else:
        raise AssertionError("Mismatched day master must be rejected")


def test_16_entire_output_deterministic():
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    first = build_matrix_from_chart(chart)
    second = build_matrix_from_chart(chart)
    assert first == second
    assert first["overall_strength"] is None
    assert first["weights_available"] is False
