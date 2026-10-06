from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import branch_acquisition_v220 as core


CASE = dict(id='unit_07', operating='low', retry_cost='17/20')


def anchors():
    # Retained V218 life0 FULL counts, unchanged in V219.
    return [
        dict(SHORT_PASS=dict(DELIVERY=243, LOST=141),
             DETOUR_PASS=dict(DELIVERY=307, LOST=5, RECOVERY=88),
             RECOVERY_RETRY=dict(DELIVERY=157, LOST=211)),
        dict(SHORT_PASS=dict(DELIVERY=378, LOST=6),
             DETOUR_PASS=dict(DELIVERY=250, LOST=58, RECOVERY=76),
             RECOVERY_RETRY=dict(DELIVERY=334, LOST=50)),
        dict(SHORT_PASS=dict(DELIVERY=341, LOST=43),
             DETOUR_PASS=dict(DELIVERY=320, LOST=6, RECOVERY=58),
             RECOVERY_RETRY=dict(DELIVERY=95, LOST=289)),
    ]


def failed_member():
    # V219 MEAN life0/task7 exhausted 384 samples without a library certificate.
    return dict(SHORT_PASS=dict(DELIVERY=47, LOST=1),
                DETOUR_PASS=dict(DELIVERY=217, LOST=39, RECOVERY=64),
                RECOVERY_RETRY=dict(DELIVERY=16, LOST=0))


def test_complete_dm_laws_have_exact_mass_moments_and_rare_outcomes():
    for op in core.OPERATORS:
        row = dict.fromkeys(core.ALPHABETS[op], 0)
        row['DELIVERY'] = 5
        if 'RECOVERY' in row:
            row['RECOVERY'] = 3
        law = core.dm_distribution(row, op)
        assert len(law) == (153 if len(row) == 3 else 17)
        assert sum(probability for _, probability in law) == 1
        assert all(probability > 0 and sum(outcome) == 16 for outcome, probability in law)
        for j, cat in enumerate(core.ALPHABETS[op]):
            expectation = sum(outcome[j]*probability for outcome, probability in law)
            assert expectation == 16*F(2*row[cat]+1, 2*sum(row.values())+len(row))
        lost = core.ALPHABETS[op].index('LOST')
        assert any(outcome[lost] == 16 and probability > 0 for outcome, probability in law)

    member, library = failed_member(), anchors()
    plan = dict(candidates=[0, 1])
    for op in core.OPERATORS:
        law = core.predictive_distribution(member, library, plan, op)
        conditional = [core.dm_distribution(
            {cat: member[op][cat]+library[i][op][cat] for cat in core.ALPHABETS[op]}, op)
            for i in plan['candidates']]
        assert [probability for _, probability in law] == [
            (conditional[0][j][1]+conditional[1][j][1])/2 for j in range(len(law))]


def test_all_187_cached_branch_plans_match_full_uncached_semantics():
    # Actual V219 MEAN life0/task7 prefix at 368: forecasts can still execute.
    member = dict(SHORT_PASS=dict(DELIVERY=47, LOST=1),
                  DETOUR_PASS=dict(DELIVERY=207, LOST=39, RECOVERY=58),
                  RECOVERY_RETRY=dict(DELIVERY=16, LOST=0))
    library, work = anchors(), Counter()
    cache = core.prepare(library, work)
    original = deepcopy((member, library, cache['source_boxes']))
    branches = 0
    for op in core.OPERATORS:
        for outcome, _ in core.OUTCOMES[op]:
            temporary = deepcopy(member)
            for cat, amount in zip(core.ALPHABETS[op], outcome):
                temporary[op][cat] += amount
            predicted = core.forecast_plan(temporary, library, CASE, work, cache)
            uncached = core.prior.make_plan(temporary, library, CASE, 'MEAN', Counter())
            assert predicted == uncached
            branches += 1
    assert branches == 187
    assert (member, library, cache['source_boxes']) == original
    assert all(key.startswith('forecast_') for key in work)


def test_branch_integral_does_not_change_real_plan_or_source_evidence():
    # The actual 48-sample pilot prefix of the same V219 failed task.
    member = dict(SHORT_PASS=dict(DELIVERY=15, LOST=1),
                  DETOUR_PASS=dict(DELIVERY=11, LOST=3, RECOVERY=2),
                  RECOVERY_RETRY=dict(DELIVERY=16, LOST=0))
    library, work = anchors(), Counter()
    plan = core.make_plan(member, library, CASE, 'BRANCH', Counter())
    cache = core.prepare(library, work)
    before = deepcopy((member, library, plan, cache['source_boxes']))
    choice = core.choose(member, library, CASE, 'BRANCH', plan, 48, work, cache)
    assert choice['scope'] == 'TARGET' and choice['reason'] == 'branch_integral'
    assert choice['source_index'] is None
    assert (member, library, plan, cache['source_boxes']) == before
    assert sum(score['branches'] for score in choice['scores'].values()) == 187
    for score in choice['scores'].values():
        assert score['probability_mass'] == F(1)
        assert score['expected_loss'] >= 0
        assert 0 <= score['ready_probability'] <= 1
        assert 0 <= score['unavailable_probability'] <= 1
    assert all(key.startswith('forecast_') for key in work)
    assert work['forecast_planning_calls'] == 187


def test_unavailable_branches_use_full_kernel_bound_without_changing_proxy():
    # Supported but source-incompatible observations yield a genuine None proxy.
    member = dict(SHORT_PASS=dict(DELIVERY=16, LOST=0),
                  DETOUR_PASS=dict(DELIVERY=0, LOST=16, RECOVERY=0),
                  RECOVERY_RETRY=dict(DELIVERY=0, LOST=16))
    library, work = anchors(), Counter()
    plan = core.make_plan(member, library, CASE, 'BRANCH', Counter())
    assert plan['query_proxy'] is None and not plan['candidates']
    bound = core.regret_bound(CASE, work)
    # The SHORT-delivery, DETOUR-recovery, RETRY-lost vertex attains this bound.
    assert bound == F(29, 6)
    assert work['forecast_query_bound_vertices'] == 12
    before = deepcopy(plan)
    assert core.forecast_loss(plan, bound) == max(F(0), 2-plan['utility_lower'])+bound-F(1, 20)
    cache = core.prepare(library, work)
    choice = core.choose(member, library, CASE, 'BRANCH', plan, 48, work, cache)
    assert any(score['unavailable_probability'] > 0 for score in choice['scores'].values())
    assert plan == before and plan['query_proxy'] is None
