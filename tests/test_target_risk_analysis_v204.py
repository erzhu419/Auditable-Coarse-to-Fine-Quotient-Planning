"""Four synthetic mathematical/history fixtures, never a production lifecycle."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations, product

from scripts import analyze_target_risk_acquisition_v204 as audit

F = Fraction


def vertices(bounds):
    names = sorted(bounds); result = []
    for fixed in combinations(names, len(names) - 1):
        remaining = next(name for name in names if name not in fixed)
        for endpoints in product(*(bounds[name] for name in fixed)):
            row = dict(zip(fixed, endpoints)); row[remaining] = 1 - sum(endpoints)
            if bounds[remaining][0] <= row[remaining] <= bounds[remaining][1]:
                result.append(row)
    return result


def test_common_risk_and_goal_extrema_for_both_retry_coefficient_signs():
    case = dict(operating='low', retry_cost='17/20')
    weights = [('WAIT', F(1, 10)), ('SHORT', F(1, 5)), ('DETOUR_RETURN', F(3, 10)), ('DETOUR_RETRY', F(2, 5))]
    for retry_min in (F(1, 5), F(3, 10)):
        envelope = {
            'SHORT_PASS': dict(bounds=dict(DELIVERY=(F(7, 10), F(9, 10)), LOST=(F(1, 10), F(3, 10)))),
            'DETOUR_PASS': dict(bounds=dict(DELIVERY=(F(3, 5), F(4, 5)), LOST=(F(1, 20), F(1, 5)), RECOVERY=(F(1, 10), F(3, 10)))),
            'RECOVERY_RETRY': dict(bounds=dict(DELIVERY=(retry_min, F(2, 5)), LOST=(F(3, 5), 1 - retry_min)))}
        outcomes = []
        for triplet in product(*(vertices(envelope[operator]['bounds']) for operator in audit.OPERATORS)):
            laws = dict(zip(audit.OPERATORS, triplet)); point = audit.vectors(case, laws)
            outcomes.append(audit.joint(weights, point, Counter()))
        worst_risk = sum(weight * audit.risk_bounds(envelope)[name] for name, weight in weights)
        worst_goal = sum(weight * audit.goal_bounds(envelope, case)[name] for name, weight in weights)
        assert worst_risk == max(row[1] for row in outcomes)
        assert worst_goal == min(audit.goal(row) for row in outcomes)


def model_fixture():
    source = dict(id='synthetic_source', operating='high', retry_cost='17/20', weather='wet')
    table = {
        'SHORT_PASS': [dict(context=source, counts=dict(DELIVERY=90, LOST=10))],
        'DETOUR_PASS': [dict(context=source, counts=dict(DELIVERY=85, LOST=1, RECOVERY=14))],
        'RECOVERY_RETRY': [dict(context=source, counts=dict(DELIVERY=25, LOST=75))]}
    model = dict(selected_fields={operator: ['weather'] for operator in audit.OPERATORS},
                 tables=table, observations_used=300, scores={})
    target = dict(id='synthetic_target', operating='low', retry_cost='17/20', weather='wet')
    return model, target


def test_disposable_forecast_real_updates_and_cold_policy_do_not_fake_evidence():
    model, target = model_fixture(); work = Counter(); current = audit.make_plan(model, target, work)
    original, saved_plan = deepcopy(model), deepcopy(current)
    choice = audit.forecast(model, target, current, work)
    assert model == original and current == saved_plan and set(choice['forecast_scores']) == set(audit.OPERATORS)
    assert all(row['n'] == 0 for row in current['envelopes'].values())
    cold = deepcopy(model); cold['selected_fields'] = {operator: list(audit.FIELDS) for operator in audit.OPERATORS}
    cold_plan = audit.make_plan(cold, target, work); selection = audit.cold_policy(cold, target, cold_plan, work)
    assert selection['policy'] == 'DETOUR_RETURN' and selection['operator'] == 'DETOUR_PASS'
    assert selection['policy_scores']['DETOUR_RETURN'] == F(77, 20)
    assert selection['policy_scores']['SHORT'] == F(19, 5)
    audit.update(model, target, 'DETOUR_PASS', dict(DELIVERY=15, LOST=0, RECOVERY=1), work)
    assert model['observations_used'] == 316 and model['selected_fields'] == original['selected_fields']
    assert all(isinstance(count, int) for rows in model['tables'].values() for row in rows for count in row['counts'].values())
    assert audit.make_plan(model, target, work)['envelopes']['DETOUR_PASS']['n'] == 16


def test_shared_consumed_prefix_and_batch_boundary_budget_stopping():
    work = Counter(); probabilities = dict(DELIVERY=F(1, 4), LOST=F(3, 4))
    stream = audit.generate_prefix(7, 32, probabilities, ('DELIVERY', 'LOST'), work)
    counts16 = Counter(stream[:16]); counts32 = Counter(stream)
    assert counts32 == counts16 + Counter(stream[16:32])
    assert work['regenerated_consumed_samples'] == 32
    assert audit.stop_reason(dict(utility_lower=F(3, 2)), 368) is None
    assert audit.stop_reason(dict(utility_lower=F(3, 2)), 384) == 'budget'
    assert audit.stop_reason(dict(utility_lower=F(2)), 32) == 'certified'
    assert audit.stop_reason(dict(utility_lower=F(2)), 384) == 'certified'


def test_modified_real_plan_or_joint_result_is_rejected():
    model, target = model_fixture(); work = Counter(); expected = audit.make_plan(model, target, work)
    saved = audit.exact_json(expected)
    assert audit.plan_matches(saved, expected)
    changed = deepcopy(saved); changed['utility_lower'] = '2'
    assert not audit.plan_matches(changed, expected)
    probabilities = {'SHORT_PASS': dict(DELIVERY=F(4, 5), LOST=F(1, 5)),
        'DETOUR_PASS': dict(DELIVERY=F(3, 5), LOST=F(1, 10), RECOVERY=F(3, 10)),
        'RECOVERY_RETRY': dict(DELIVERY=F(3, 10), LOST=F(7, 10))}
    result = audit.score(expected, probabilities, target, 0, work); corrupted = deepcopy(result)
    assert audit.equal_numbers(corrupted, result)
    corrupted['actual_fractions'][1] = '1'
    assert not audit.equal_numbers(corrupted, result)
