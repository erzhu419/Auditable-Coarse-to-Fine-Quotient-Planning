from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from acfqp.science import deficit_acquisition_v217 as core

CASE = dict(id='opaque', operating='high', retry_cost='19/20')


def anchors():
    # Actual V216 life0 early-source observations, without private labels.
    return [
        dict(SHORT_PASS=dict(DELIVERY=25,LOST=7),
             DETOUR_PASS=dict(DELIVERY=257,LOST=3,RECOVERY=60),
             RECOVERY_RETRY=dict(DELIVERY=13,LOST=19)),
        dict(SHORT_PASS=dict(DELIVERY=144,LOST=0),
             DETOUR_PASS=dict(DELIVERY=24,LOST=2,RECOVERY=6),
             RECOVERY_RETRY=dict(DELIVERY=31,LOST=1)),
        dict(SHORT_PASS=dict(DELIVERY=29,LOST=3),
             DETOUR_PASS=dict(DELIVERY=157,LOST=0,RECOVERY=19),
             RECOVERY_RETRY=dict(DELIVERY=8,LOST=24)),
    ]


def member(failures=0):
    return dict(SHORT_PASS=dict(DELIVERY=11,LOST=5),
                DETOUR_PASS=dict(DELIVERY=12-failures,LOST=failures,RECOVERY=4),
                RECOVERY_RETRY=dict(DELIVERY=128,LOST=192))


def test_query_sufficient_ambiguity_refines_detour_certificate():
    counts, library = member(), anchors()
    plan = core.make_plan(counts,library,CASE,'DEFICIT',Counter())
    assert len(plan['candidates']) > 1 and plan['query_proxy'] == 0 and plan['utility_lower'] < 2
    choice = core.choose(counts,library,CASE,'DEFICIT',plan,352,Counter())
    assert choice['reason'] == 'certificate_deficit' and choice['operator'] == 'DETOUR_PASS'


def test_one_rare_member_failure_preserves_source_information():
    counts, library = member(failures=1), anchors()
    plan = core.make_plan(counts,library,CASE,'DEFICIT',Counter())
    assert plan['query_proxy'] == 0 and plan['utility_lower'] < 2
    choice = core.choose(counts,library,CASE,'DEFICIT',plan,352,Counter())
    assert choice['reason'] == 'certificate_deficit' and choice['operator'] == 'DETOUR_PASS'


def test_fractional_forecasts_do_not_change_real_observations_or_certificate():
    counts, library = member(), anchors()
    plan = core.make_plan(counts,library,CASE,'DEFICIT',Counter())
    before = deepcopy((counts,library,plan))
    means = core.candidate_means(counts,library,plan)
    core.query_scores(counts,library,CASE,means,Counter())
    core.certificate_scores(CASE,plan,means,Counter())
    assert (counts,library,plan) == before
    assert all(isinstance(k,int) for row in counts.values() for k in row.values())


def test_unobserved_operator_pilot_and_budget_stop():
    counts = core.empty()
    plan = dict(query_ready=False)
    assert core.choose(counts,anchors(),CASE,'DEFICIT',plan,0,Counter())['operator'] == 'SHORT_PASS'
    counts['SHORT_PASS']['DELIVERY'] = 16
    assert core.choose(counts,anchors(),CASE,'DEFICIT',plan,16,Counter())['operator'] == 'DETOUR_PASS'
    assert core.choose(counts,anchors(),CASE,'DEFICIT',plan,384,Counter()) is None


def test_unavailable_query_forecast_cannot_win_over_a_valid_proxy(monkeypatch):
    counts, library = member(), anchors()
    plan = core.make_plan(counts,library,CASE,'DEFICIT',Counter())
    plan['query_proxy'] = F(1,10)
    monkeypatch.setattr(core,'query_scores',lambda *args: {
        'SHORT_PASS': dict(query_proxy=None,utility_lower=F(100)),
        'DETOUR_PASS': dict(query_proxy=F(1,20),utility_lower=F(1)),
        'RECOVERY_RETRY': dict(query_proxy=F(1,10),utility_lower=F(1)),
    })
    choice = core.choose(counts,library,CASE,'DEFICIT',plan,352,Counter())
    assert choice['reason'] == 'query_deficit' and choice['operator'] == 'DETOUR_PASS'
