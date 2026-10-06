from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import online_joint_query_v242 as core


def counts():
    s, d, r = core.joint.OPERATORS
    return {s: {'DELIVERY': 1, 'LOST': 999},
            d: {'DELIVERY': 500, 'RECOVERY': 500, 'LOST': 10},
            r: {'DELIVERY': 600, 'LOST': 400}}


def case(retry_cost='17/20'):
    return dict(operating='low', retry_cost=retry_cost)


def queries(goal='DETOUR_RETRY', risk='DETOUR_RETURN'):
    return {'reward': {'policy': 'WAIT'}, 'goal': {'policy': goal}, 'risk': {'policy': risk}}


def comparison(result, query, other):
    return next(item for item in result['queries'][query]['comparisons'] if item['other'] == other)


def test_changed_retry_cost_and_paid_counts_get_new_relevant_convex_proofs():
    cache, work, observed = {}, {}, counts()
    first = core.certificates(observed, case(), queries(), cache, work)
    second = core.certificates(observed, case('19/20'), queries(), cache, work)
    first_retry, second_retry = (comparison(result, 'risk', 'DETOUR_RETRY') for result in (first, second))
    assert first_retry is not second_retry
    assert (first_retry['relevant_cost'], second_retry['relevant_cost']) == (F(17, 20), F(19, 20))
    assert comparison(first, 'risk', 'SHORT') is comparison(second, 'risk', 'SHORT')
    assert len(cache['convex_tangent']) == 3
    updated = deepcopy(observed)
    updated[core.joint.OPERATORS[0]]['DELIVERY'] += 16
    third = core.certificates(updated, case('19/20'), queries(), cache, work)
    assert comparison(third, 'risk', 'SHORT') is not comparison(second, 'risk', 'SHORT')
    assert comparison(third, 'risk', 'DETOUR_RETRY') is second_retry
    assert len(cache['convex_tangent']) == 4 and work['online_convex_proposal_calls'] == 4


def test_reverse_direction_and_goal_query_use_the_original_joint_engine():
    cache, work = {}, {}
    result = core.certificates(counts(), case(), queries(goal='DETOUR_RETURN', risk='SHORT'), cache, work)
    reverse = comparison(result, 'risk', 'DETOUR_RETURN')
    assert reverse['family'] == 'S_D_FULL' and 'engine' not in reverse
    goal = comparison(result, 'goal', 'SHORT')
    assert goal['family'] == 'S_D_DEL' and 'engine' not in goal
    assert not cache['convex_tangent'] and len(cache['V235']) == 6
    assert work.get('online_convex_proposal_calls', 0) == 0


def test_false_optimizer_flag_cannot_override_a_valid_global_certificate(monkeypatch):
    point = {'S': {'DELIVERY': F(1, 2), 'LOST': F(1, 2)},
             'D_FULL': {'DELIVERY': F(77, 160), 'RECOVERY': F(1, 80), 'LOST': F(81, 160)}}
    original = core.convex._proposal

    def proposed(observed, task, family):
        if family == 'S_D_FULL':
            return point, {'success': False, 'iterations': 500, 'message': 'iteration limit'}
        return original(observed, task, family)

    monkeypatch.setattr(core.convex, '_proposal', proposed)
    observed = counts()
    observed[core.joint.OPERATORS[1]] = {'DELIVERY': 998, 'RECOVERY': 1, 'LOST': 1}
    proof = comparison(core.certificates(observed, case(), queries(), {}, {}), 'risk', 'SHORT')
    assert not proof['result']['optimizer']['success']
    assert proof['result']['global_tangent']['certified']
    assert proof['certified'] and proof['status'] == 'certified'


def test_one_certified_risk_comparison_cannot_bypass_the_other_blocker():
    selected = queries()
    result = core.certificates(counts(), case(), selected, {}, {})
    assert comparison(result, 'risk', 'SHORT')['certified']
    assert not comparison(result, 'risk', 'DETOUR_RETRY')['certified']
    assert not result['queries']['risk']['certified'] and not result['all_ready']
    assert len(result['comparison_records']) == 6
    assert {query: decision['policy'] for query, decision in result['queries'].items()} == {
        query: decision['policy'] for query, decision in selected.items()}
    assert result['queries']['reward']['certified']
