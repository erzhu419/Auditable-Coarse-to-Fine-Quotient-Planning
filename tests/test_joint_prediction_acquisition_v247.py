"""Test complete bad-null bounds, joint selection and proof-free prediction."""
from collections import Counter
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction as F
from functools import lru_cache
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import convex_query_null_v240 as convex
from acfqp.science import joint_prediction_acquisition_v247 as core

S, D, R = core.OPERATORS
CASE = {'operating': 'low', 'retry_cost': '17/20'}
RAW = {S: {'DELIVERY': 4, 'LOST': 6},
       D: {'DELIVERY': 5, 'RECOVERY': 2, 'LOST': 3},
       R: {'DELIVERY': 1, 'LOST': 3}}


def global_proof(case=CASE):
    """The lambda=0 dual is valid on all 32 fixed null relaxations."""
    counts = deepcopy(RAW)
    leaves = []
    for index in range(32):
        endpoint = F(index+1, 32)
        constant, coefficients = core.dual.gap_coefficients(case, 'goal', 'SHORT', 'DETOUR_RETRY', endpoint)
        leaves.append(dict(kind='likelihood_dual', retry_interval=[F(index, 32), endpoint],
            gap_constant=constant, gap_coefficients=coefficients, multiplier=F(0),
            row_witnesses={op: dict(kind='simplex_likelihood_dual', nu=F(sum(counts[op].values())))
                           for op in (S, D)}, log_bad_likelihood_upper=F(0)))
    return dict(query='goal', chosen='SHORT', other='DETOUR_RETRY', certified=False,
        family='S_D_FULL_R', threshold=960, regret_threshold=F(1, 20),
        embedded_counts=counts, witness_kind='global_likelihood_dual', leaves=leaves)


@lru_cache(maxsize=1)
def retained_convex():
    """Use actual retained V245 points and parameters, without optimization."""
    path = Path(__file__).resolve().parents[1]/'reports/query_allocation_lifecycle_v245/profiles_life_00.jsonl.gz'
    found = {}
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            entry = json.loads(line)
            proof = entry['certificate']
            if (proof.get('engine') == 'convex_tangent' and proof['result']['global_tangent'] is not None
                    and proof['family'] not in found):
                found[proof['family']] = (entry['case'], proof)
                if len(found) == 2:
                    break
    assert set(found) == {'S_D_FULL', 'D_REC_R'}
    return found


def actual_log_likelihood(counts, parameters):
    with localcontext() as context:
        context.prec = 110
        value = Decimal(0)
        for name, row in counts.items():
            for category, count in row.items():
                if count:
                    p = F(parameters[name][category])
                    value += Decimal(count)*(Decimal(p.numerator)/Decimal(p.denominator)).ln()
        return F(value)


def test_integer_batch_is_rounded_in_the_full_row_before_projection():
    row = {category: 1 for category in core.ALPHABETS[D]}
    rounded = core.expected_increment(row)
    assert list(rounded.values()) == [6, 5, 5] and sum(rounded.values()) == 16
    full = deepcopy(RAW)
    full[D] = rounded
    projected = core.joint.project_counts(full, 'D_DEL')['D_DEL']
    assert projected == {'DELIVERY': 6, 'OTHER': 10}
    assert core.expected_increment({'DELIVERY': 1, 'OTHER': 2}) == {'DELIVERY': 5, 'OTHER': 11}


def test_all_32_cells_survive_and_a_nonleading_cell_becomes_dominant():
    proof = global_proof()
    current = core.predict(proof, CASE, RAW)
    updated = deepcopy(RAW)
    updated[R]['DELIVERY'] += 16
    predicted = core.predict(proof, CASE, updated)
    assert len(current['leaf_bounds']) == len(predicted['leaf_bounds']) == 32
    old = [row['index'] for row in current['leaf_bounds']
           if row['log_bad_likelihood_upper'] == current['log_bad_likelihood_upper']]
    new = [row['index'] for row in predicted['leaf_bounds']
           if row['log_bad_likelihood_upper'] == predicted['log_bad_likelihood_upper']]
    assert old == [7, 8] and new == [27]
    assert predicted['leaf_bounds'][15]['retry_probability'] == F(1, 2)
    assert predicted['leaf_bounds'][27]['retry_probability'] == F(17, 20)


def test_nu_increment_and_mle_are_recomputed_without_old_bound_reuse():
    proof = global_proof()
    updated = deepcopy(RAW)
    updated[S]['DELIVERY'] += 16
    result = core.predict(proof, CASE, updated)
    assert all(row['row_nus'][S] == 26 and row['row_nus'][D] == 10
               for row in result['leaf_bounds'])
    empirical = {name: {category: F(count, sum(row.values())) for category, count in row.items()}
                 for name, row in result['projected_counts'].items()}
    assert actual_log_likelihood(result['projected_counts'], empirical) <= result['log_bad_likelihood_upper']
    assert result['log_mixture_lower'] != core.predict(proof, CASE, RAW)['log_mixture_lower']


@pytest.mark.parametrize('family', ['S_D_FULL', 'D_REC_R'])
def test_actual_convex_retained_tangent_bounds_the_entire_new_count_null(family):
    case, retained = retained_convex()[family]
    raw = core.joint.embedded_counts(retained['projected_counts'], family)
    raw[S]['DELIVERY'] += 16 if family == 'S_D_FULL' else 0
    raw[R]['DELIVERY'] += 16 if family == 'D_REC_R' else 0
    result = core.predict(retained, case, raw)
    admitted = 0
    for a in (F(1, 10), F(1, 2), F(9, 10)):
        for b in (F(1, 10), F(1, 2), F(9, 10)):
            if family == 'S_D_FULL':
                parameters = {'S': {'DELIVERY': a, 'LOST': 1-a},
                              'D_FULL': {'DELIVERY': b, 'RECOVERY': (1-b)/2, 'LOST': (1-b)/2}}
            else:
                parameters = {'D_REC': {'RECOVERY': a, 'OTHER': 1-a},
                              'R': {'DELIVERY': b, 'LOST': 1-b}}
            if core.joint.gap(case, 'risk', retained['chosen'], retained['other'], parameters) >= F(1, 20):
                admitted += 1
                assert actual_log_likelihood(result['projected_counts'], parameters) <= result['log_bad_likelihood_upper']
    assert admitted > 0 and result['fallback'] is None
    point = retained['result']['global_tangent']['point']
    old_upper = F(retained['result']['global_tangent']['global_upper'])
    projected_delta = core.joint.project_counts(raw, family)
    naive = old_upper+sum((delta*core._log(F(point[name][category]))[1]
        for name, row in projected_delta.items() for category, new_count in row.items()
        if (delta := new_count-retained['projected_counts'][name][category])), F(0))
    assert result['log_bad_likelihood_upper'] > naive


def active_plan(proofs=None):
    return dict(utility_lower=F(2), goal_impossible=False, query_ready=False,
        case=deepcopy(CASE), evidence_counts=deepcopy(RAW),
        effective_n={op: sum(row.values()) for op, row in RAW.items()},
        query_certificates={query: dict(certified=False, regret_upper=F(20))
                            for query in ('goal', 'risk')},
        query_evidence={'queries': {'goal': {'comparisons': [global_proof()]},
                                   'risk': {'comparisons': []}}} if proofs is None else proofs)


def test_joint_minimax_uses_goal_and_risk_instead_of_goal_only(monkeypatch):
    first, second = global_proof(), global_proof()
    second.update(query='risk', chosen='DETOUR_RETURN', other='SHORT')
    proofs = {'queries': {'goal': {'comparisons': [first]}, 'risk': {'comparisons': [second]}}}
    tradeoff = {S: (1, 10), D: (4, 5), R: (8, 1)}

    def prediction(proof, case, raw, work):
        changed = next((op for op in core.OPERATORS if sum(raw[op].values()) != sum(RAW[op].values())), None)
        return dict(deficit=F(20 if changed is None else tradeoff[changed][proof['query'] == 'risk']))

    monkeypatch.setattr(core, 'predict', prediction)
    result = core.choose(core.original.route.empty(), active_plan(proofs), 0, Counter())
    assert result['operator'] == D
    assert [result['joint_prediction_candidates'][op]['worst_deficit'] for op in core.OPERATORS] == [10, 5, 8]
    member = core.original.route.empty()
    for op in core.OPERATORS:
        tradeoff[op] = (5, 5)
    member[S]['DELIVERY'] = 16
    assert core.choose(member, active_plan(proofs), 16, Counter())['operator'] == D


def test_no_optimizer_membership_or_certificate_and_no_input_mutation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('prediction called an optimizer, membership or certifier')

    monkeypatch.setattr(core.dual, 'minimize_scalar', forbidden)
    monkeypatch.setattr(core.dual, '_leaf', forbidden)
    monkeypatch.setattr(core.joint, 'certificate', forbidden)
    monkeypatch.setattr(core.joint, 'membership', forbidden)
    monkeypatch.setattr(convex, 'minimize', forbidden)
    monkeypatch.setattr(convex, '_tangent', forbidden)
    plan, member, work = active_plan(), core.original.route.empty(), Counter()
    before = deepcopy((plan, member))
    result = core.choose(member, plan, 0, work)
    assert (plan, member) == before and result['prediction_only']
    assert work['joint_prediction_current_comparison_evaluations'] == 1
    assert work['joint_prediction_candidate_comparison_evaluations'] == 3
    assert work['joint_prediction_cell_evaluations'] == 128
    assert all('certified' not in row for row in result['joint_prediction_current'])


def test_mle_fallback_is_explicit_and_cannot_predict_positive_evidence():
    proof = global_proof()
    proof.update(witness_kind='bad_null_mle', leaves=[])
    result = core.predict(proof, CASE, RAW)
    assert result['fallback'] == 'bad_null_mle' and result['log_e_lower'] <= 0
    case, proof = retained_convex()['S_D_FULL']
    proof = deepcopy(proof)
    proof['result']['global_tangent'] = None
    result = core.predict(proof, case, RAW)
    assert result['fallback'] == 'missing_retained_tangent' and result['log_e_lower'] <= 0


def test_active_arm_uses_the_current_per_arm_mixture_function(monkeypatch):
    normalizer, seen = core.joint.mixture_normalizer, []

    def active(counts):
        seen.append(counts)
        return normalizer(counts)

    monkeypatch.setattr(core.joint, 'mixture_normalizer', active)
    core.predict(global_proof(), CASE, RAW)
    assert len(seen) == 3


def test_stopping_and_unresolved_execution_preserve_original_branch(monkeypatch):
    active, work = active_plan(), Counter()
    monkeypatch.setattr(core, 'predict', lambda *args: pytest.fail('prediction outside query branch'))
    assert core.choose(core.original.route.empty(), active, 384, work) is None
    active['query_ready'] = True
    assert core.choose(core.original.route.empty(), active, 0, work) is None
    active.update(query_ready=False, utility_lower=F(1))
    sentinel = {'operator': S, 'reason': 'original'}
    monkeypatch.setattr(core.original, 'choose', lambda *args: sentinel)
    assert core.choose(core.original.route.empty(), active, 0, work) is sentinel and not work
