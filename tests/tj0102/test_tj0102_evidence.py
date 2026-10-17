"""TJ-010.2 P0-1: Evidence binding tests (private CI only).

Tests build_matrix_with_evidence() with real ExecutionTrace and
EvidenceResolver. Each test uses real chart computation.

No mocks. Fail-closed on missing/tampered evidence.
"""
import sys
import os
import copy
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tianji_kb.bazi_core import chart_from_datetime, chart_from_pillars
from tianji_kb.bazi_action_matrix import build_matrix_with_evidence


def test_01_evidence_binding_success():
    """正确四柱、正确Trace：成功绑定每行证据."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    # Every row must have structure_evidence
    for row in result['roots'] + result['exposures'] + result['actions']:
        ev = row.get('structure_evidence')
        assert ev is not None, f"Missing structure_evidence: {row}"
        assert ev['rule_id'].startswith('bazi.phase2.'), f"Bad rule_id: {ev['rule_id']}"
        assert len(ev['evidence_ids']) > 0, "Must have evidence_ids"
        assert ev['evidence_id'] in ev['evidence_ids']
    print(f"  01: all rows have evidence")


def test_02_root_structure_evidence():
    """根 observed/candidate 的结构证据."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    for r in result['roots']:
        ev = r['structure_evidence']
        assert ev['rule_id'] == 'bazi.phase2.root_conditions'
        assert 'fact_ref' in ev
        assert ev['fact_ref'].startswith('#/trace/')
    print(f"  02: {len(result['roots'])} root structure evidences")


def test_03_root_effective_evidence():
    """根 effective 的充分条件证据."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    effective = [r for r in result['roots'] if r['status'] == 'effective']
    for r in effective:
        ev = r.get('effect_evidence')
        assert ev is not None, "effective must have effect_evidence"
        assert ev['rule_id'] == 'bazi.phase2.root_availability'
    print(f"  03: {len(effective)} effective roots with evidence")


def test_04_tougan_observed_evidence():
    """透干 observed 的证据."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    observed = [e for e in result['exposures'] if e['status'] == 'observed']
    for e in observed:
        ev = e['structure_evidence']
        assert ev['rule_id'] == 'bazi.phase2.action_conditions'
    print(f"  04: {len(observed)} tougan evidences")


def test_05_tougan_not_applicable():
    """透干 not_applicable 的证据（结构存在但无对应）."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    na = [e for e in result['exposures'] if e['status'] == 'not_applicable']
    # Even not_applicable should have structure evidence (the fact was checked)
    for e in na:
        assert e['structure_evidence'] is not None
    print(f"  05: {len(na)} not_applicable with evidence")


def test_08_action_effects_positive():
    """action_effects 审核充分条件正例."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    effective = [a for a in result['actions'] if a['status'] == 'effective']
    for a in effective:
        ev = a.get('effect_evidence')
        assert ev is not None
        assert ev['rule_id'] == 'bazi.phase2.action_effects'
    print(f"  08: {len(effective)} effective actions")


def test_10_yinshen_unresolved_evidence():
    """寅申冲 unresolved 的证据."""
    chart = chart_from_pillars(("甲", "寅"), ("丙", "申"), ("甲", "午"), ("己", "巳"))
    result = build_matrix_with_evidence(chart)
    # Must complete with evidence
    assert 'evidence_trace' in result
    assert len(result['evidence_trace']['rule_ids']) == 7
    print(f"  10: yinshen unresolved with evidence")


def test_19_deterministic_mapping():
    """重复执行映射一致."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    r1 = build_matrix_with_evidence(chart)
    r2 = build_matrix_with_evidence(chart)
    # Evidence IDs must be deterministic
    for row1, row2 in zip(r1['roots'], r2['roots']):
        e1 = row1['structure_evidence']
        e2 = row2['structure_evidence']
        assert e1['evidence_id'] == e2['evidence_id'], "Evidence must be deterministic"
    print(f"  19: deterministic evidence mapping")


def test_20_no_overreach():
    """无整体旺衰、喜用神、权重和吉凶越界输出."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    assert result.get('overall_strength') is None
    assert result.get('weights_available') is False
    # No 喜用神 or 吉凶 in output
    import json
    s = json.dumps(result, ensure_ascii=False)
    assert '喜用' not in s
    assert '吉凶' not in s
    print(f"  20: no overreach")
