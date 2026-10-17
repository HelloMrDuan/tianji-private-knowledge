"""TJ-010.2: Evidence tampering rejection tests (private CI).

Each test tampers with REAL trace/result and MUST trigger ValueError.
No WARNING, no pass-through, no empty loops.
"""
import sys
import os
import copy
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tianji_kb.bazi_core import chart_from_datetime
from tianji_kb.bazi_action_matrix import (
    build_matrix_with_evidence,
    _verify_evidence_consistency,
)
from tianji_kb.resolver import ExecutionTrace
from tianji_kb.bazi_core import VARIANT as CORE_VARIANT


def _real_result_and_trace():
    chart = chart_from_datetime("2000-01-07T12:00:00+08:00")
    result = build_matrix_with_evidence(chart)
    from tianji_kb.bazi_core import reviewed_relations
    from tianji_kb.bazi_commander import month_command, principal_month, COMMAND_VARIANT, PRINCIPAL_VARIANT
    from tianji_kb.bazi_strength import factors as strength_factors, FACTOR_VARIANT
    from tianji_kb.bazi_root_conditions import root_conditions, root_availability, ROOT_VARIANT, AVAILABILITY_VARIANT
    from tianji_kb.bazi_action_conditions import action_conditions, action_effects, ACTION_VARIANT, EFFECT_VARIANT
    pillars = chart['pillars']
    day_master = chart['day_master']['stem']
    stems = [p['stem']['value'] for p in pillars]
    branches = [p['branch']['value'] for p in pillars]
    relations = reviewed_relations(stems, branches)
    trace = ExecutionTrace('bazi', CORE_VARIANT)
    cmd = month_command(pillars, day_master, command_variant=COMMAND_VARIANT)
    trace.add('bazi.phase2.month_command_variant', {'command_variant': COMMAND_VARIANT}, cmd)
    principal = principal_month(cmd, day_master, command_variant=PRINCIPAL_VARIANT)
    trace.add('bazi.phase2.principal_month', {'command_variant': PRINCIPAL_VARIANT}, principal)
    strength = strength_factors(pillars, day_master, variant=FACTOR_VARIANT)
    roots = root_conditions(pillars, day_master, relations=relations, month_command=cmd, root_variant=ROOT_VARIANT)
    trace.add('bazi.phase2.root_conditions', {'root_variant': ROOT_VARIANT}, roots)
    availability = root_availability(roots, root_variant=AVAILABILITY_VARIANT)
    trace.add('bazi.phase2.root_availability', {'root_variant': AVAILABILITY_VARIANT}, availability)
    actions = action_conditions(pillars, day_master, support=strength['support_relations'],
                                relations=relations, month_command=cmd, action_variant=ACTION_VARIANT)
    trace.add('bazi.phase2.action_conditions', {'action_variant': ACTION_VARIANT}, actions)
    effects = action_effects(pillars, observed=actions, relations=relations,
                             principal=principal, availability=availability, action_variant=EFFECT_VARIANT)
    trace.add('bazi.phase2.action_effects', {'action_variant': EFFECT_VARIANT}, effects)
    return chart, result, trace


def test_neg01_delete_structure_evidence_rejected():
    """删除结构证据必须拒绝."""
    chart, result, trace = _real_result_and_trace()
    bad = copy.deepcopy(result)
    assert len(bad['roots']) > 0, "Test requires roots"
    # Verify original has evidence
    assert bad['roots'][0]['structure_evidence'] is not None
    # Tamper: delete it
    bad['roots'][0]['structure_evidence'] = None
    # Must throw
    try:
        _verify_evidence_consistency(bad, trace, chart)
    except ValueError:
        print("  neg01: PASS")
        return
    raise AssertionError("neg01 FAILED: deleted structure_evidence not rejected")


def test_neg02_cross_rule_mismatch_rejected():
    """跨Rule错配必须拒绝."""
    chart, result, trace = _real_result_and_trace()
    bad = copy.deepcopy(result)
    assert len(bad['roots']) > 0 and len(bad['actions']) > 0
    root_ev = bad['roots'][0]['structure_evidence']
    action_ev = bad['actions'][0]['structure_evidence']
    assert root_ev is not None and action_ev is not None
    assert root_ev['rule_id'] != action_ev['rule_id'], "Need different rules"
    # Tamper: put action's evidence on root (cross-rule)
    bad['roots'][0]['structure_evidence'] = copy.deepcopy(action_ev)
    try:
        _verify_evidence_consistency(bad, trace, chart)
    except ValueError:
        print("  neg02: PASS")
        return
    raise AssertionError("neg02 FAILED: cross-rule mismatch not rejected")


def test_neg03_modify_rule_rejected():
    """修改Rule ID必须拒绝."""
    chart, result, trace = _real_result_and_trace()
    bad = copy.deepcopy(result)
    assert len(bad['roots']) > 0
    ev = bad['roots'][0]['structure_evidence']
    assert ev is not None
    ev['rule_id'] = 'bazi.phase2.fake_rule'
    try:
        _verify_evidence_consistency(bad, trace, chart)
    except ValueError:
        print("  neg03: PASS")
        return
    raise AssertionError("neg03 FAILED: modified rule not rejected")


def test_neg04_modify_variant_rejected():
    """修改Variant必须拒绝."""
    chart, result, trace = _real_result_and_trace()
    bad = copy.deepcopy(result)
    assert len(bad['roots']) > 0
    ev = bad['roots'][0]['structure_evidence']
    assert ev is not None
    ev['variant'] = 'fake-variant'
    try:
        _verify_evidence_consistency(bad, trace, chart)
    except ValueError:
        print("  neg04: PASS")
        return
    raise AssertionError("neg04 FAILED: modified variant not rejected")


def test_neg05_forge_effective_rejected():
    """伪造effective必须拒绝."""
    chart, result, trace = _real_result_and_trace()
    bad = copy.deepcopy(result)
    # Find unresolved row and forge to effective
    forged = None
    for row in bad['roots'] + bad['actions']:
        if row['status'] == 'unresolved':
            row['status'] = 'effective'
            forged = row
            break
    assert forged is not None, "Need unresolved row for forge test"
    # The forged row now claims effective but trace doesn't support it
    # _verify_evidence_consistency must detect via index correspondence
    try:
        _verify_evidence_consistency(bad, trace, chart)
    except ValueError:
        print("  neg05: PASS")
        return
    # If no exception, the forge wasn't detected - this is a test failure
    # (not a pass with warning)
    raise AssertionError("neg05 FAILED: forged effective not rejected")
