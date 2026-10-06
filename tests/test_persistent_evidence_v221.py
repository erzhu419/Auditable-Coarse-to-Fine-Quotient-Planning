from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import persistent_evidence_v221 as core


CASE = dict(id='unit_03', operating='low', retry_cost='17/20')


def anchors():
    # V220 retained life0 FULL source observations.
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


def certified_member():
    # Actual V220 SET life0/task3 terminal evidence; uniquely certified source0.
    return dict(SHORT_PASS=dict(DELIVERY=130, LOST=78),
                DETOUR_PASS=dict(DELIVERY=0, LOST=0, RECOVERY=0),
                RECOVERY_RETRY=dict(DELIVERY=20, LOST=28))


def test_commit_keeps_intersection_confidence_separate_from_accumulated_counts():
    source, member, work = anchors(), certified_member(), Counter()
    state = core.prepare(source, work)
    before = deepcopy(state)
    plan = core.make_plan(member, source, CASE, 'PERSIST', work, state=state)
    assert plan['candidates'] == [0] and plan['utility_lower'] >= 2
    event = core.commit(state, member, plan, work)
    assert event == dict(source_index=0, samples=256)
    assert state['commits'] == [1, 0, 0]
    raw = core.evidence.boxes(member, Counter())
    pooled_box = core.evidence.boxes(state['counts'][0], Counter())
    differences_from_pooled_kl = []
    for op in core.OPERATORS:
        assert state['bounds'][0][op]['n'] == before['bounds'][0][op]['n']
        assert state['bounds'][0][op]['counts'] == before['bounds'][0][op]['counts']
        for cat in core.ALPHABETS[op]:
            old, new = before['bounds'][0][op]['bounds'][cat], raw[op]['bounds'][cat]
            assert state['counts'][0][op][cat] == source[0][op][cat]+member[op][cat]
            assert state['bounds'][0][op]['bounds'][cat] == [max(old[0], new[0]), min(old[1], new[1])]
            differences_from_pooled_kl.append(state['bounds'][0][op]['bounds'][cat] != pooled_box[op]['bounds'][cat])
    assert any(differences_from_pooled_kl)
    assert state['counts'][1:] == before['counts'][1:]
    assert state['bounds'][1:] == before['bounds'][1:]
    assert source == anchors() and member == certified_member()
    assert work['controlled_samples'] == 0 and work['persistent_committed_samples'] == 256


def test_planning_precedes_commit_and_counts_each_target_once():
    source, member, work = anchors(), certified_member(), Counter()
    state = core.prepare(source, work)
    initial = deepcopy(state)
    current = core.make_plan(member, source, CASE, 'PERSIST', work, state=state)
    assert state == initial
    assert current == core.prior.make_plan(member, source, CASE, 'SET', Counter())
    assert core.choose(member, source, CASE, 'PERSIST', current, 256, work, state) is None
    core.commit(state, member, current, work)
    committed = deepcopy(state)
    # A later independent target may have the same observed counts.
    next_plan = core.make_plan(member, source, CASE, 'PERSIST', work, state=state)
    assert state == committed and next_plan['candidates'] == [0]
    combined = {op: {cat: source[0][op][cat]+2*member[op][cat]
                     for cat in core.ALPHABETS[op]} for op in core.OPERATORS}
    assert next_plan['pure_vectors'] == core.vectors(CASE, core.evidence.posterior(combined))
    assert current['pure_vectors'] != next_plan['pure_vectors']
    assert state['commits'] == [1, 0, 0]


def test_query_ready_candidate_set_failure_and_member_fallback_do_not_commit():
    # Actual V220 SET life3/task3 is query-ready with two candidates after 32.
    source = [
        dict(SHORT_PASS=dict(DELIVERY=347, LOST=37),
             DETOUR_PASS=dict(DELIVERY=325, LOST=2, RECOVERY=57),
             RECOVERY_RETRY=dict(DELIVERY=98, LOST=286)),
        dict(SHORT_PASS=dict(DELIVERY=238, LOST=130),
             DETOUR_PASS=dict(DELIVERY=338, LOST=7, RECOVERY=71),
             RECOVERY_RETRY=dict(DELIVERY=165, LOST=203)),
        dict(SHORT_PASS=dict(DELIVERY=379, LOST=5),
             DETOUR_PASS=dict(DELIVERY=257, LOST=45, RECOVERY=82),
             RECOVERY_RETRY=dict(DELIVERY=352, LOST=32)),
    ]
    member = dict(SHORT_PASS=dict(DELIVERY=10, LOST=6),
                  DETOUR_PASS=dict(DELIVERY=0, LOST=0, RECOVERY=0),
                  RECOVERY_RETRY=dict(DELIVERY=4, LOST=12))
    work, state = Counter(), core.prepare(source, Counter())
    initial = deepcopy(state)
    plan = core.make_plan(member, source, CASE, 'PERSIST', work, state=state)
    assert plan['query_ready'] and plan['candidates'] == [0, 1]
    assert core.commit(state, member, plan, work) is None and state == initial

    source, member = anchors(), certified_member()
    state = core.prepare(source, Counter())
    initial = deepcopy(state)
    failure = core.make_plan(core.empty(), source, CASE, 'PERSIST', work, state=state)
    assert failure['utility_lower'] < 2
    assert core.commit(state, core.empty(), failure, work) is None and state == initial
    fallback = core.make_plan(member, source, CASE, 'PERSIST', work, force_member=True, state=state)
    assert fallback['mode'] == 'member' and not fallback['candidates']
    assert core.commit(state, member, fallback, work) is None and state == initial


def test_frozen_reference_keeps_prior_plans_and_choices_after_persistent_commit():
    source, member, work = anchors(), certified_member(), Counter()
    state = core.prepare(source, work)
    persist = core.make_plan(member, source, CASE, 'PERSIST', work, state=state)
    core.commit(state, member, persist, work)
    for counts, spent in ((core.empty(), 0), (member, 256)):
        frozen = core.make_plan(counts, source, CASE, 'FROZEN', Counter(), state=state)
        old = core.prior.make_plan(counts, source, CASE, 'SET', Counter())
        assert frozen == old
        assert core.choose(counts, source, CASE, 'FROZEN', frozen, spent, Counter(), state) == core.prior.choose(
            counts, source, CASE, 'SET', old, spent, Counter())
