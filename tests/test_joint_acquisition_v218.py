from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import joint_acquisition_v218 as core


CASE = dict(id='opaque', operating='low', retry_cost='19/20')


def source_bound_fixture():
    # Retained V217 life1/task10 counts: member 256, sources 384/368/240.
    member = dict(
        SHORT_PASS=dict(DELIVERY=31, LOST=17),
        DETOUR_PASS=dict(DELIVERY=154, LOST=4, RECOVERY=34),
        RECOVERY_RETRY=dict(DELIVERY=9, LOST=7),
    )
    anchors = [
        dict(SHORT_PASS=dict(DELIVERY=29, LOST=3),
             DETOUR_PASS=dict(DELIVERY=277, LOST=4, RECOVERY=39),
             RECOVERY_RETRY=dict(DELIVERY=9, LOST=23)),
        dict(SHORT_PASS=dict(DELIVERY=18, LOST=14),
             DETOUR_PASS=dict(DELIVERY=252, LOST=3, RECOVERY=49),
             RECOVERY_RETRY=dict(DELIVERY=10, LOST=22)),
        dict(SHORT_PASS=dict(DELIVERY=175, LOST=1),
             DETOUR_PASS=dict(DELIVERY=26, LOST=2, RECOVERY=4),
             RECOVERY_RETRY=dict(DELIVERY=27, LOST=5)),
    ]
    return member, anchors


def unsettled_plan():
    return dict(candidates=[0, 1], utility_lower=F(1), query_proxy=F(1, 10),
                query_ready=False)


def fake_prediction(*args):
    return dict(utility_lower=F(1), query_proxy=F(1, 10))


def test_finite_forecasts_preserve_observations_plan_and_actual_work(monkeypatch):
    member, anchors = source_bound_fixture()
    plan = unsettled_plan()
    before = deepcopy((member, anchors, plan))
    forecast_inputs = []

    def predict(temporary_member, temporary_anchors, case, arm, work):
        forecast_inputs.append(deepcopy((temporary_member, temporary_anchors)))
        work['planning_calls'] += 1
        return fake_prediction()

    monkeypatch.setattr(core, 'make_plan', predict)
    work = Counter()
    choice = core.choose(member, anchors, CASE, 'JOINT', plan, 256, work)
    assert (member, anchors, plan) == before
    assert all(isinstance(n, int) for counts in [member] + anchors
               for row in counts.values() for n in row.values())
    assert 'planning_calls' not in work
    assert work['forecast_planning_calls'] == len(choice['scores'])
    for score, (temporary_member, temporary_anchors) in zip(choice['scores'], forecast_inputs):
        changed = []
        for index, (real, temporary) in enumerate(zip([member] + anchors,
                                                     [temporary_member] + temporary_anchors)):
            for op in core.OPERATORS:
                delta = {cat: temporary[op][cat] - real[op][cat]
                         for cat in core.ALPHABETS[op]}
                if any(delta.values()):
                    changed.append((index, op, sum(delta.values())))
        index = 0 if score['scope'] == 'TARGET' else score['source_index'] + 1
        assert changed == [(index, score['operator'], 16)]


def test_unavailable_query_forecast_cannot_win_as_zero_deficit(monkeypatch):
    member, anchors = source_bound_fixture()
    monkeypatch.setattr(core, 'forecasts', lambda *args: [
        dict(scope='TARGET', source_index=None, operator='SHORT_PASS',
             operator_n=48, query_proxy=None, utility_lower=F(100), deficit=F(0)),
        dict(scope='SOURCE', source_index=0, operator='DETOUR_PASS',
             operator_n=320, query_proxy=F(0), utility_lower=F(1), deficit=F(1)),
    ])
    choice = core.choose(member, anchors, CASE, 'JOINT', unsettled_plan(), 256, Counter())
    assert (choice['scope'], choice['operator']) == ('SOURCE', 'DETOUR_PASS')


def test_member_cap_still_allows_paid_source_evidence(monkeypatch):
    member, anchors = source_bound_fixture()
    monkeypatch.setattr(core, 'make_plan', fake_prediction)
    choice = core.choose(member, anchors, CASE, 'JOINT', unsettled_plan(), 384, Counter())
    assert choice['scope'] == 'SOURCE'
    assert all(score['scope'] == 'SOURCE' for score in choice['scores'])
    assert core.choose(member, anchors, CASE, 'MEMBER', unsettled_plan(), 384, Counter()) is None


def test_each_source_cap_excludes_further_revisits(monkeypatch):
    member, anchors = source_bound_fixture()
    monkeypatch.setattr(core, 'make_plan', fake_prediction)
    full = core.empty()
    full['SHORT_PASS']['DELIVERY'] = 1088
    full['DETOUR_PASS']['DELIVERY'] = 32
    full['RECOVERY_RETRY']['DELIVERY'] = 32
    capped = [deepcopy(full), anchors[1], deepcopy(full)]
    choice = core.choose(member, capped, CASE, 'JOINT', unsettled_plan(), 384, Counter())
    assert choice['scope'] == 'SOURCE' and choice['source_index'] == 1
    assert {score['source_index'] for score in choice['scores']} == {1}
    capped[1] = deepcopy(full)
    assert core.choose(member, capped, CASE, 'JOINT', unsettled_plan(), 384, Counter()) is None


def test_reachable_source_bound_case_selects_paid_source_batch():
    member, anchors = source_bound_fixture()
    plan = core.make_plan(member, anchors, CASE, 'JOINT', Counter())
    assert not plan['query_ready'] and plan['utility_lower'] < 2
    before = deepcopy((member, anchors, plan))
    joint = core.choose(member, anchors, CASE, 'JOINT', plan, 256, Counter())
    target_only = core.choose(member, anchors, CASE, 'MEMBER', plan, 256, Counter())
    assert joint['scope'] == 'SOURCE'
    assert target_only['scope'] == 'TARGET'
    selected = next(score for score in joint['scores']
                    if (score['scope'], score['source_index'], score['operator']) ==
                    (joint['scope'], joint['source_index'], joint['operator']))
    temporary_anchors = deepcopy(anchors)
    index, op = joint['source_index'], joint['operator']
    mean = core.evidence.posterior(anchors[index])
    for cat in core.ALPHABETS[op]:
        temporary_anchors[index][op][cat] += 16 * mean[op][cat]
    finite = core.make_plan(member, temporary_anchors, CASE, 'JOINT', Counter())
    assert selected['utility_lower'] == finite['utility_lower']
    assert selected['query_proxy'] == finite['query_proxy']
    assert selected['deficit'] == core.deficit(finite) < core.deficit(plan)
    assert (member, anchors, plan) == before
