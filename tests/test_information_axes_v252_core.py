"""Verify the independent S/D-fixed algebra and unchanged retained variants."""
from copy import deepcopy
from fractions import Fraction as F
import pytest

from acfqp.science import information_axes_v252 as core

S, D, R = core.S, core.D, core.R
COUNTS = {S: {'DELIVERY': 6, 'LOST': 4},
    D: {'DELIVERY': 5, 'LOST': 3, 'RECOVERY': 2}, R: {'DELIVERY': 2, 'LOST': 8}}
CASE = dict(operating='low', retry_cost='17/20')


def events(counts=COUNTS):
    return {op: [dict(counts=deepcopy(counts[op]), threshold=threshold, event=f'A/{role}/{op}')
        for role, threshold in (('source', 720), ('pool', 720), ('member', 8640))] for op in (S, D, R)}


def proof():
    return dict(witness_kind='bad_null_mle', bad_null_kernel={
        S: {'DELIVERY': F(9, 10), 'LOST': F(1, 10)},
        D: {'DELIVERY': F(1, 2), 'LOST': F(1, 4), 'RECOVERY': F(1, 4)},
        R: {'DELIVERY': F(3, 4), 'LOST': F(1, 4)}})


@pytest.mark.parametrize('operating,retry_cost', [('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20')])
def test_sd_fixed_exact_full_rows_and_strict_gap(operating, retry_cost):
    case = dict(operating=operating, retry_cost=retry_cost)
    c = core.sd_centered(COUNTS, case)
    expected = (F(50001, 10**6)-F(1, 20)+4*F(6, 10)-4*F(5, 10)+F(2, 10)*F(retry_cost))/(4*F(2, 10))
    assert c['kind'] == 'sd_centered_analytic_r' and c['solve_applied']
    assert c['retry_delivery_unclipped'] == expected == c['kernel'][R]['DELIVERY']
    assert c['kernel'][R]['LOST'] == 1-expected
    assert c['kernel'][S] == {cat: F(count, 10) for cat, count in COUNTS[S].items()}
    assert c['kernel'][D] == {cat: F(count, 10) for cat, count in COUNTS[D].items()}
    assert c['kernel'][D]['LOST'] == F(3, 10) and c['kernel'][D]['RECOVERY'] == F(1, 5)
    assert c['fixed_rows'] == {op: c['kernel'][op] for op in (S, D)}
    assert c['gap'] == core.STRICT_GAP == F(50001, 10**6)
    assert c['reason'] is None and 'certified' not in c


def test_original_two_classifications_exact_and_sd_uses_all_events_without_certifying(monkeypatch):
    constraints, certificate = events(), proof()
    before = deepcopy((COUNTS, constraints, certificate))
    monkeypatch.setattr(core.joint, 'certificate', lambda *args: pytest.fail('new certificate from diagnosis'))
    old = core.original.classify(COUNTS, constraints, CASE, certificate)
    result = core.classify(COUNTS, constraints, CASE, certificate)
    assert all(result['variants'][variant] == old['variants'][variant] for variant in core.original.VARIANTS)
    sd = result['variants']['SD_CENTERED']
    assert sd['status'] == 'full_region_bad_witness'
    assert set(sd['query_regions']) == set(core.joint.FAMILIES) and len(sd['query_regions']) == 8
    assert len(sd['execution_regions']) == 9
    assert [e['threshold'] for e in sd['execution_regions']] == [720, 720, 8640]*3
    assert all(e['membership']['exact_inside'] for e in sd['execution_regions'])
    assert result['distances']['SD_CENTERED'][S] == result['distances']['SD_CENTERED'][D] == 0
    assert result['distances']['SD_CENTERED'][R] == abs(sd['candidate']['kernel'][R]['DELIVERY']-F(1, 5))
    assert (COUNTS, constraints, certificate) == before
    assert 'certified' not in sd and 'query_ready' not in sd


def test_sd_candidate_is_available_despite_unavailable_retained_recovery():
    certificate = dict(witness_kind='global_likelihood_dual', leaves=[])
    result = core.classify(COUNTS, events(), CASE, certificate)
    assert all(result['variants'][variant]['candidate']['kernel'] is None for variant in ('RETAINED', 'R_CENTERED'))
    assert all(result['variants'][variant]['status'] == 'unknown' for variant in ('RETAINED', 'R_CENTERED'))
    assert result['variants']['SD_CENTERED']['candidate']['kernel'] is not None
    assert result['variants']['SD_CENTERED']['status'] == 'full_region_bad_witness'


@pytest.mark.parametrize('counts,sign', [
    ({S: {'DELIVERY': 0, 'LOST': 10}, D: {'DELIVERY': 8, 'LOST': 0, 'RECOVERY': 2}, R: COUNTS[R]}, -1),
    ({S: {'DELIVERY': 10, 'LOST': 0}, D: {'DELIVERY': 0, 'LOST': 9, 'RECOVERY': 1}, R: COUNTS[R]}, 1)])
def test_infeasible_analytic_r_is_preserved_without_clipping_or_membership(monkeypatch, counts, sign):
    c = core.sd_centered(counts, CASE)
    assert c['retry_delivery_unclipped'] < 0 if sign < 0 else c['retry_delivery_unclipped'] > 1
    assert c['solve_applied'] and c['kernel'] is None and c['reason'] == 'retry_delivery_outside_simplex'
    monkeypatch.setattr(core.joint, 'membership', lambda *args: pytest.fail('membership for unavailable point'))
    classified = core.original._classify(counts, events(counts), c)
    assert classified['status'] == 'unknown' and classified['query_regions'] == {}


def test_zero_empirical_recovery_keeps_analytic_solve_unknown():
    counts = deepcopy(COUNTS)
    counts[D] = {'DELIVERY': 5, 'LOST': 5, 'RECOVERY': 0}
    c = core.sd_centered(counts, CASE)
    assert c['kernel'] is None and c['retry_delivery_unclipped'] is None and not c['solve_applied']
    assert c['reason'] == 'zero_empirical_detour_recovery'


def test_complete_d_event_can_reject_sd_fixed_candidate_without_empty_null_claim():
    constraints = events()
    constraints[D][0] = dict(counts={'DELIVERY': 100, 'LOST': 0, 'RECOVERY': 100},
        threshold=720, event='full_D_source')
    sd = core.classify(COUNTS, constraints, CASE, proof())['variants']['SD_CENTERED']
    assert sd['canonical_inside'] and sd['all_query_inside'] and not sd['all_execution_inside']
    assert sd['status'] == 'paid_constraints_reject_candidate'
    rejected = next(e for e in sd['execution_regions'] if e['event'] == 'full_D_source')
    assert not rejected['membership']['exact_inside']
    assert 'null_empty' not in sd and 'conservative_certificate' not in sd


def test_canonical_rejection_remains_unknown_even_with_exact_strict_gap():
    counts = {op: {cat: count*100 for cat,count in row.items()} for op,row in COUNTS.items()}
    sd = core.classify(counts, events(counts), CASE, proof())['variants']['SD_CENTERED']
    assert sd['candidate']['gap'] == core.STRICT_GAP
    assert sd['canonical_inside'] is False and sd['status'] == 'unknown'
    assert sd['candidate']['kernel'] is not None and set(sd['query_regions']) == set(core.joint.FAMILIES)
