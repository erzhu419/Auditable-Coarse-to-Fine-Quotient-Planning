from fractions import Fraction as F
from types import SimpleNamespace

import numpy as np

from scripts import probe_joint_query_countermodels_v235 as probe


def row():
    return dict(life=0, index=58, arm='ORACLE_BALANCED', kind='failure', phase='A_RETURN',
        case={'operating': 'low', 'retry_cost': '17/20'}, query='risk',
        chosen='DETOUR_RETURN', other='SHORT', family='S_D_FULL',
        projected_counts={'S': {'DELIVERY': 19, 'LOST': 1},
            'D_FULL': {'DELIVERY': 18, 'RECOVERY': 1, 'LOST': 1}},
        initials=[dict(name='projected_mle_smoothed', coordinates=[.7, .65, .075]),
                  dict(name='saved_bad_witness', coordinates=[.95, .9, .05])])


def test_exact_acceptance_rejects_simplex_errors_threshold_equality_and_outside_region():
    selected = row()
    accepted = probe.accepted(selected, probe.parameters([F(19, 20), F(9, 10), F(1, 20)], 'S_D_FULL'))
    assert accepted['gap'] == F(3, 20) and accepted['membership']['exact_inside']
    assert probe.accepted(selected, probe.parameters([F(7, 10), F(13, 20), F(3, 40)], 'S_D_FULL')) is None
    assert probe.accepted(selected, probe.parameters([F(19, 20), F(9, 10), F(1, 5)], 'S_D_FULL')) is None
    wrong = probe.parameters([F(99, 100), F(1, 100), F(1, 100)], 'S_D_FULL')
    assert probe.accepted(selected, wrong) is None


def test_optimizer_success_does_not_replace_exact_acceptance_and_attempt_order_is_fixed(monkeypatch):
    calls = []
    candidates = iter(([.7, .65, .075], [.95, .9, .05]))

    def minimize(function, initial, **kwargs):
        calls.append((initial.tolist(), kwargs))
        return SimpleNamespace(x=np.array(next(candidates)), nit=3, success=True)

    monkeypatch.setattr(probe, 'minimize', minimize)
    result = probe.probe(row())
    assert result['found'] and result['valid'] and len(calls) == 2
    assert [attempt['initial'] for attempt in result['attempts']] == ['projected_mle_smoothed', 'saved_bad_witness']
    assert result['gap'] > F(1, 20)
    assert all(call[1]['method'] == 'SLSQP' and call[1]['options'] == dict(maxiter=200, ftol=1e-12) for call in calls)
    assert result['scope'] == 'canonical_terminal_only'


def test_failed_fixed_proposals_remain_unknown_without_negative_inference(monkeypatch):
    monkeypatch.setattr(probe, 'minimize', lambda *args, **kwargs:
        SimpleNamespace(x=np.array([.7, .65, .075]), nit=200, success=False))
    result = probe.probe(row())
    assert not result['found'] and not result['valid'] and len(result['attempts']) == 2
    assert 'parameters' not in result and 'gap' not in result


def test_analytic_proposal_gradients_match_likelihood_and_gap_changes():
    selected = row()
    point = np.array([.8, .7, .15])
    value, gradient = probe.objective(point, selected)
    gap, gap_gradient = probe.floating_gap(point, selected)
    for index in range(3):
        offset = np.eye(3)[index]*1e-6
        numeric = (probe.objective(point+offset, selected)[0]-probe.objective(point-offset, selected)[0])/2e-6
        assert np.isclose(gradient[index], numeric, atol=1e-8)
        gap_numeric = (probe.floating_gap(point+offset, selected)[0]-probe.floating_gap(point-offset, selected)[0])/2e-6
        assert np.isclose(gap_gradient[index], gap_numeric, atol=1e-8)
    assert np.isfinite(value) and np.isfinite(gap)


def test_geometry_is_conditional_and_zero_at_the_empirical_candidate():
    counts = row()['projected_counts']
    geometry = probe.geometry(counts, probe.mle(counts))
    assert geometry['log_mle_minus_log_bad'] == dict(lower='0', upper='0')
    assert all(item['lower'] == item['upper'] == '0'
               for item in geometry['per_row_kl_empirical_to_bad'].values())
    assert F(geometry['log_mle_minus_log_mixture']['lower']) > 0
    assert geometry['scope'] == 'conditional_observed_geometry_not_true_KL_or_new_sample_guarantee'
