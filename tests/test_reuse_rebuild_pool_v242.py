from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import reuse_rebuild_pool_v242 as pool
from acfqp.science import oracle_gap_acquisition_v231 as acquisition

S, D, R = pool.OPERATORS


def anchors(context):
    counts = ({S: {'DELIVERY': 310, 'LOST': 74},
        D: {'DELIVERY': 340, 'RECOVERY': 36, 'LOST': 8},
        R: {'DELIVERY': 80, 'LOST': 304}} if context == 'A' else
        {S: {'DELIVERY': 40, 'LOST': 88},
         D: {'DELIVERY': 112, 'RECOVERY': 12, 'LOST': 4},
         R: {'DELIVERY': 20, 'LOST': 108}})
    return [deepcopy(counts) for _ in range(3)]


def case(context):
    return {'context': context, 'operating': 'low', 'retry_cost': '17/20'}


def increments(operator, number=16):
    return {category: number*int(category == 'DELIVERY') for category in pool.ALPHABETS[operator]}


def states():
    result = {}
    for arm in ('REUSE', 'REBUILD'):
        state = pool.prepare(anchors('A'), 0, arm, Counter())
        for operator in pool.OPERATORS:
            pool.observe(state, case('A'), 1, operator, increments(operator))
        pool.begin_b(state, anchors('B'), S, (1, 2, 0), Counter())
        result[arm] = state
    return result


def test_b_changed_exclusion_and_rebuild_still_accumulates_b_targets():
    both = states()
    for state in both.values():
        pool.observe(state, case('B'), 0, S, increments(S))
        pool.observe(state, case('B'), 0, D, increments(D))
    reuse, rebuild = (pool.point_counts(case('B'), both[arm], 0) for arm in ('REUSE', 'REBUILD'))
    assert reuse[S] == rebuild[S] == {'DELIVERY': 56, 'LOST': 88}
    assert {operator: sum(row.values()) for operator, row in reuse.items()} == {S: 144, D: 544, R: 528}
    assert {operator: sum(row.values()) for operator, row in rebuild.items()} == {S: 144, D: 144, R: 128}
    member = pool.empty()
    member[D] = increments(D)
    reuse_constraints = pool.regions(member, case('B'), both['REUSE'], 0, 30)
    rebuild_constraints = pool.regions(member, case('B'), both['REBUILD'], 0, 30)
    assert len(reuse_constraints[S]) == len(rebuild_constraints[S]) == 3
    assert len(reuse_constraints[D]) == len(reuse_constraints[R]) == 5
    assert len(rebuild_constraints[D]) == len(rebuild_constraints[R]) == 3
    assert rebuild_constraints[D][1]['counts'] == rebuild[D]


def test_a_return_restores_own_a_and_cannot_change_frozen_b_inheritance():
    both = states()
    before = {arm: pool.point_counts(case('B'), state, 0) for arm, state in both.items()}
    for arm, state in both.items():
        pool.observe(state, case('A'), 1, R, increments(R))
        restored = pool.point_counts(case('A'), state, 1)
        assert sum(restored[R].values()) == 416
        assert sum(restored[S].values()) == sum(restored[D].values()) == 400
        assert pool.point_counts(case('B'), state, 0) == before[arm]
    assert pool.point_counts(case('A'), both['REUSE'], 1) == pool.point_counts(case('A'), both['REBUILD'], 1)


def test_planning_counts_current_samples_once_and_new_blockers_drive_existing_acquisition(monkeypatch):
    state, cache, observed = states()['REUSE'], {}, []
    current = {'DELIVERY': 6, 'LOST': 10}
    pool.observe(state, case('B'), 0, S, current)
    member = pool.empty()
    member[S] = current

    def certificates(counts, actual_case, point_queries, actual_cache, work):
        assert actual_cache is cache
        observed.append(deepcopy(counts))
        assert point_queries['risk']['policy'] == 'DETOUR_RETURN'
        queries, records = {}, []
        for query, choice in point_queries.items():
            comparisons = [dict(other=other, certified=not(query == 'risk' and other == 'SHORT'))
                for other in pool.original.joint.POLICIES if other != choice['policy']]
            queries[query] = dict(policy=choice['policy'], certified=all(row['certified'] for row in comparisons),
                                  comparisons=comparisons)
            records.extend(comparisons)
        return dict(queries=queries, comparison_records=records, all_ready=False)

    monkeypatch.setattr(pool.query_evidence, 'certificates', certificates)
    plan = pool.make_plan(member, case('B'), state, 0, 30, cache, Counter())
    assert observed == [pool.point_counts(case('B'), state, 0)]
    assert sum(plan['evidence_counts'][S].values()) == 144
    assert plan['query_blockers']['risk'] == ['SHORT']
    assert plan['query_gap_bounds']['risk']['SHORT'] == 1
    assert plan['query_gap_bounds']['risk']['DETOUR_RETRY'] == 0
    assert plan['query_certificates']['risk']['regret_upper'] == 20
    assert plan['query_certificates']['goal']['regret_upper'] == F(1, 20)
    assert plan['query_certificates']['reward']['regret_upper'] == 0
    assert not pool.ready(plan)
    choice = acquisition.choose(member, plan, 16, Counter())
    assert choice['query_influence'][S] > 0 and choice['query_influence'][D] > 0
    assert choice['query_influence'][R] == 0
