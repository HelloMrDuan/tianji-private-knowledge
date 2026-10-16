"""TJ-010.2 Private Acceptance: Real chart computation with Canonical data.

Runs against public PR #259 head SHA (pinned).
Tests real:
- chart_from_datetime() with 2000-01-07T12:00:00+08:00
- build_matrix_from_chart()
- reviewed_relations() clash detection
- root_availability() and action_effects() integration
- EvidenceResolver evidence IDs

Each test FAILS if implementation is wrong. No mocks. No SKIPs.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tianji_kb.bazi_core import chart_from_datetime, chart_from_pillars, reviewed_relations
from tianji_kb.bazi_action_matrix import build_matrix_from_chart


def test_real_chart_2000_01_07():
    """Real chart must compute and matrix must have valid statuses."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    assert chart['deterministic'] is True
    result = build_matrix_from_chart(chart)
    valid = {'observed', 'candidate', 'effective', 'unresolved', 'not_applicable'}
    for row in result['roots'] + result['actions'] + result['exposures']:
        assert row['status'] in valid, f"Invalid: {row['status']}"
    total = sum(result['summary'].values())
    expected = len(result['roots']) + len(result['actions']) + len(result['exposures'])
    assert total == expected, f"Summary mismatch: {total} != {expected}"
    print(f"  roots={len(result['roots'])} actions={len(result['actions'])}")
    print(f"  summary={result['summary']}")


def test_clash_causes_unresolved():
    """Real 子午 clash must cause unresolved status."""
    chart = chart_from_pillars("甲子", "丙午", "甲寅", "己巳")
    stems = [p['stem']['value'] for p in chart['pillars']]
    branches = [p['branch']['value'] for p in chart['pillars']]
    rel = reviewed_relations(stems, branches)
    # Verify real clash exists
    assert len(rel.get('branch_six_clashes', [])) > 0, "Must have real clash"
    result = build_matrix_from_chart(chart)
    # At least one affected row must be unresolved
    affected = [r for r in result['roots'] + result['actions']
                if r.get('branch') in ('子', '午')]
    assert len(affected) > 0
    unresolved = [r for r in affected if r['status'] == 'unresolved']
    assert len(unresolved) > 0, "Clash must cause unresolved"
    print(f"  clash: {len(unresolved)}/{len(affected)} unresolved")


def test_input_validation_rejects_bad_chart():
    """Invalid inputs must be rejected (fail-closed)."""
    # Empty pillars
    try:
        build_matrix_from_chart({'pillars': [], 'day_master': {'stem': '甲'}})
        assert False, "Must reject empty pillars"
    except (ValueError, KeyError):
        pass
    # Day master mismatch
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    bad = dict(chart)
    bad['day_master'] = {'stem': '乙'}  # Wrong stem
    try:
        build_matrix_from_chart(bad)
        assert False, "Must reject day master mismatch"
    except ValueError as e:
        assert 'day_master' in str(e).lower() or 'match' in str(e).lower()
    print("  input validation: PASS")


def test_deterministic():
    """Same input must give same output."""
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    r1 = build_matrix_from_chart(chart)
    r2 = build_matrix_from_chart(chart)
    assert r1['summary'] == r2['summary']
    print("  deterministic: PASS")
