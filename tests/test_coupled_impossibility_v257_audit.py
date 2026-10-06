"""Original LP, paired-kernel coupling and retained full-D proof regressions."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

import pytest

from scripts import audit_coupled_impossibility_v257 as audit


@pytest.fixture(scope='module')
def paid_bound():
    from acfqp.science import coupled_impossibility_v257 as producer
    row = next(row for life in audit.LIVES for row in audit.rows(
        audit.PREDECESSOR/f'records_life_{life:02d}_TRAJECTORY_REUSE.jsonl.gz') if 30 <= row['index'] < 54
               and row['query_certified'] and not row['execution_resolved'])
    plan = row['terminal_plan']
    return row, producer.upper_bound(plan, row['case'], Counter())


def test_exact_four_line_dual_chooses_smallest_non_grid_lambda_on_a_flat_optimum():
    rectangles = {
        'WAIT': dict(risk_min=F(0), goal_max=F(0)),
        'SHORT': dict(risk_min=F(1), goal_max=F(2)),
        'DETOUR_RETURN': dict(risk_min=F(1, 20), goal_max=F(1)),
        'DETOUR_RETRY': dict(risk_min=F(1), goal_max=F(0))}
    dual = audit.rectangle_dual(rectangles)
    assert dual['lambda_value'] == F(20, 19) and dual['value'] == 1
    assert dual['maximizing_policies'] == ['SHORT', 'DETOUR_RETURN']
    assert next(row['objective'] for row in dual['candidates'] if row['lambda_value'] == 20) == 1
    assert any(row['lambda_value'] == 0 for row in dual['candidates'])


def test_actual_paid_primary_endpoint_matches_old_LP_paired_and_full_D_dual(paid_bound):
    row, bound = paid_bound
    checks = []
    independent = audit.audit_bound(bound, row['terminal_plan'], row['case'],
                                    lambda name, ok: checks.append((name, ok)))
    audit.audit_original_events(dict(life=row['life'], arm=audit.ARMS[0], index=row['index'],
        identity=row['identity'], case=row['case'], plan=row['terminal_plan']),
        lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks)
    assert independent['upper'] == min(bound['old_goal_upper'], bound['paired_box']['upper'], bound['joint_candidate'])
    assert bound['paired_box']['upper'] <= bound['old_goal_upper']
    assert sum(name == 'outward_D_weak_dual_independent_100_digit_verification' for name, _ in checks) == 2


def test_outward_D_proof_rejects_a_too_small_upper_even_when_status_is_unchanged(paid_bound):
    row, original = paid_bound
    bound = deepcopy(original)
    bound['d_supports']['DETOUR_RETRY']['support']['upper'] -= F(1, 100)
    checks = []
    audit.audit_bound(bound, row['terminal_plan'], row['case'], lambda name, ok: checks.append((name, ok)))
    assert any(name == 'outward_D_weak_dual_independent_100_digit_verification' and not ok for name, ok in checks)


def test_coefficients_original_events_and_strict_impossibility_flags_are_not_trusted(paid_bound):
    row, original = paid_bound
    bound = deepcopy(original)
    bound['d_supports']['DETOUR_RETRY']['coefficients']['RECOVERY'] += F(1, 10)
    bound['new_impossible'] = not bound['new_impossible']
    failures = []
    audit.audit_bound(bound, row['terminal_plan'], row['case'],
                      lambda name, ok: failures.append(name) if not ok else None)
    assert 'exact_original_joint_D_support_coefficients' in failures
    assert 'strict_goal_impossibility_threshold_and_original_decision' in failures
    snapshot = dict(life=row['life'], arm=audit.ARMS[0], index=row['index'], identity=row['identity'],
                    case=row['case'], plan=deepcopy(row['terminal_plan']))
    snapshot['plan']['joint_constraints'][audit.D][2]['threshold'] = 720
    failures = []
    audit.audit_original_events(snapshot, lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['original_native_source_pool_member_and_compatible_event_labels_no_new_alpha']


def test_coupled_D_directions_equal_actual_goal_minus_lambda_risk_and_retry_is_monotone(paid_bound):
    row, bound = paid_bound
    lam = bound['old_dual']['lambda_value']
    q = bound['binary_upper'][audit.R]
    coefficients = audit.branch_coefficients(row['case'], lam, q)
    q0 = audit.branch_coefficients(row['case'], lam, F(0))['DETOUR_RETRY']
    q1 = audit.branch_coefficients(row['case'], lam, F(1))['DETOUR_RETRY']
    _, detour_cost = audit.joint.COSTS[row['case']['operating']]
    for kernel in bound['paired_box']['vertices']:
        centered = deepcopy(kernel)
        centered[audit.R] = dict(DELIVERY=q, LOST=1-q)
        vectors = audit.joint.vectors(row['case'], centered)
        for policy in ('DETOUR_RETURN', 'DETOUR_RETRY'):
            reward, risk, delivery = vectors[policy]
            assert reward+4*delivery-lam*risk == -detour_cost+sum(
                coefficients[policy][category]*kernel[audit.D][category] for category in coefficients[policy])
        assert sum((q1[category]-q0[category])*kernel[audit.D][category] for category in q0) == (4+lam)*kernel[audit.D]['RECOVERY'] >= 0


def test_literal_full_roster_deduplicates_terminals_and_keeps_all_observable_member_histories():
    snapshots, terminals, histories, fees = audit.collect_snapshots()
    assert len(snapshots) == 949 and len(terminals) == 432 and len(histories) == 16 and len(fees) == 6
    assert [row['snapshot_id'] for row in snapshots] == list(range(949))
    assert {row['snapshot_id'] for row in terminals} == {row['snapshot_id'] for row in snapshots if row['is_terminal']}
    for history in histories:
        original = history['retained_record']
        assert original['query_certified'] and not original['execution_resolved'] and original['case']['stage'] == 'B'
        assert history['snapshot_ids'][-1] == history['terminal_snapshot_id']
        assert len(history['snapshot_ids']) == 1+len(original['batches'])
        terminal = snapshots[history['terminal_snapshot_id']]
        assert terminal['plan'] == original['terminal_plan'] and terminal['spent'] == original['spent']
    assert all(row['fees']['source'] == 4608 and sum(row['fees'].values()) == row['total_samples'] for row in fees)
