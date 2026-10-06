"""Four bounded synthetic audits; no producer or real lifecycle is executed."""
from copy import deepcopy
from fractions import Fraction
import math

from scripts import analyze_continual_route_kernels_v202 as audit

F = Fraction


def case(weather='normal', operating='low', retry='17/20'):
    return dict(id=f'synthetic_{weather}_{operating}_{retry}', weather=weather,
                operating=operating, retry_cost=retry)


def observation(context, delivery, lost):
    return dict(context=context, operator='SHORT_PASS',
                counts=dict(DELIVERY=delivery, LOST=lost))


def test_evidence_discovers_weather_sharing_without_multinomial_coefficient():
    records = [observation(case('normal', setting), 100, 0) for setting in ('low', 'high')]
    records += [observation(case('wet', setting), 0, 100) for setting in ('low', 'high')]
    model = audit.rebuild_model(records)
    assert model['selected_fields']['SHORT_PASS'] == ['weather']
    assert model['selected_fields']['DETOUR_PASS'] == []
    assert len(model['tables']['SHORT_PASS']) == 4
    grouped = {(): dict(DELIVERY=3, LOST=2)}
    expected = math.lgamma(1) - math.lgamma(6) + sum(
        math.lgamma(number + .5) - math.lgamma(.5) for number in (3, 2))
    assert audit.evidence(grouped, 'SHORT_PASS') == expected
    assert audit.posterior(model, case('normal', 'high'), 'SHORT_PASS')['DELIVERY'] == F(401, 402)


def test_zero_phase_reset_frozen_retention_and_unseen_support_prior():
    source = [observation(case(), 99, 1)]
    frozen = audit.rebuild_model(source, 'FROZEN')
    updated = source + [observation(case('wet', 'high'), 1, 99)]
    assert audit.rebuild_model(updated, 'FROZEN', frozen=frozen) is frozen
    assert frozen['observations_used'] == 100
    reset = audit.rebuild_model([], 'RESET')
    assert reset['observations_used'] == 0 and reset['tables']['SHORT_PASS'] == []
    assert audit.posterior(reset, case(), 'SHORT_PASS') == dict(DELIVERY=F(1, 2), LOST=F(1, 2))
    full = audit.rebuild_model(source, 'FULL_CONTEXT')
    assert audit.posterior(full, case('normal', 'high'), 'SHORT_PASS')['LOST'] == F(1, 2)
    assert audit.posterior(full, case(), 'SHORT_PASS')['LOST'] == F(3, 202) > 0


def test_joint_continuation_and_point_feasibility_do_not_certify_true_risk():
    actual = audit.complete_vectors(case())
    assert actual['DETOUR_RETURN'] == (-F(1, 20), F(1, 100), F(17, 20))
    assert actual['DETOUR_RETRY'][1] == F(23, 200)
    assert audit.selected_complete_policy('DETOUR', 'RETRY') == 'DETOUR_RETRY'
    mixture = [dict(policy='DETOUR_RETURN', weight='1/2'), dict(policy='DETOUR_RETRY', weight='1/2')]
    point = deepcopy(actual); point['DETOUR_RETRY'] = (actual['DETOUR_RETRY'][0], F(1, 100), actual['DETOUR_RETRY'][2])
    assert audit.mixture_vector(mixture, point)[1] <= audit.DELTA
    assert audit.mixture_vector(mixture, actual)[1] == F(1, 16) > audit.DELTA
    assert audit.constrained_bound(actual) >= audit.utility(actual['DETOUR_RETURN'], 'goal')
    vector = actual['DETOUR_RETURN']; utility = audit.utility(vector, 'risk')
    expected = dict(actual_vector=vector, predicted_vector=vector, actual_utility=utility,
                    oracle_vector=vector, oracle_utility=utility, regret=F(0))
    saved = dict(actual_fractions=[str(x) for x in vector], actual=[float(x) for x in vector],
                 utility_fraction=str(utility), utility=float(utility), oracle_fractions=[str(x) for x in vector],
                 oracle=[float(x) for x in vector], oracle_utility_fraction=str(utility), oracle_utility=float(utility),
                 regret_fraction='0', regret=0., abs_prediction_error=[0., 0., 0.])
    assert audit.query_result_matches(saved, expected)
    saved['actual_fractions'][1] = '0'
    assert not audit.query_result_matches(saved, expected)


def test_bootstrap_is_paired_by_lifecycle_and_preserves_fixed_contrasts():
    from collections import Counter
    work = Counter()
    result = audit.paired_bootstrap(dict(a=[1., 2., 3.], b=[11., 12., 13.]), work)
    assert result['b']['mean'] - result['a']['mean'] == 10
    assert all(abs(result['b']['ci'][i] - result['a']['ci'][i] - 10) < 1e-12 for i in (0, 1))
    assert work['bootstrap_index_draws'] == 15000
    assert work['bootstrap_resamples'] == 5000
    assert work['bootstrap_mean_terms'] == 30000
