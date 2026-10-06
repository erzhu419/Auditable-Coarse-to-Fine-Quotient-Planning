from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
import json
from pathlib import Path

from acfqp.science import limited_source_v226 as core
from scripts.run_conditioned_mechanisms_v205 import exact_json

ROOT = Path(__file__).resolve().parents[1]
CASE = dict(id='unit_03', operating='low', retry_cost='17/20')


def low_anchors():
    return [
        dict(SHORT_PASS=dict(DELIVERY=80, LOST=48),
             DETOUR_PASS=dict(DELIVERY=100, LOST=2, RECOVERY=26),
             RECOVERY_RETRY=dict(DELIVERY=55, LOST=73)),
        dict(SHORT_PASS=dict(DELIVERY=126, LOST=2),
             DETOUR_PASS=dict(DELIVERY=83, LOST=20, RECOVERY=25),
             RECOVERY_RETRY=dict(DELIVERY=113, LOST=15)),
        dict(SHORT_PASS=dict(DELIVERY=110, LOST=18),
             DETOUR_PASS=dict(DELIVERY=105, LOST=2, RECOVERY=21),
             RECOVERY_RETRY=dict(DELIVERY=35, LOST=93)),
    ]


def unique_member(certified):
    member = core.empty()
    member['SHORT_PASS'].update(DELIVERY=384 if certified else 208,
                               LOST=0 if certified else 176)
    return member


def commit_two(state, source, work):
    for certified, index in ((False, 0), (True, 1)):
        member = unique_member(certified)
        plan = core.make_plan(member, source, CASE, 'LOW_PARAM', work, state)
        assert plan['mode'] == 'library' and plan['candidates'] == [index]
        assert (plan['utility_lower'] >= 2) == certified
        assert core.advance(state, member, source, 'LOW_PARAM', work, plan) == dict(
            source_index=index, samples=384)


def test_shared_low_prefix_inputs_are_scoped_and_initial_low_plans_match():
    low = low_anchors()
    full = []
    for anchor in low:
        observed = {}
        for op in core.OPERATORS:
            prefix = [cat for cat, count in anchor[op].items() for _ in range(count)]
            stream = prefix*3
            assert dict(Counter(stream[:128])) == {cat: k for cat, k in anchor[op].items() if k}
            observed[op] = {cat: Counter(stream)[cat] for cat in core.ALPHABETS[op]}
        full.append(observed)
    states = {a: core.prepare(low, a, Counter()) for a in ('LOW_FIXED', 'LOW_PARAM', 'LOW_UNION')}
    assert states['LOW_FIXED']['bounds'] == states['LOW_PARAM']['bounds'] == states['LOW_UNION']['bounds']
    assert states['LOW_PARAM']['counts'] == low and states['LOW_PARAM']['commits'] == [0, 0, 0]
    assert all(box[op]['n']==128 for state in states.values() for box in state['bounds'] for op in core.OPERATORS)
    full_state = core.prepare(full, 'FULL_FIXED', Counter())
    assert all(box[op]['n']==384 for box in full_state['bounds'] for op in core.OPERATORS)
    member = core.empty(); member['SHORT_PASS'].update(DELIVERY=15, LOST=1)
    plans = {a: core.make_plan(member, low, CASE, a, Counter(), state) for a, state in states.items()}
    assert plans['LOW_FIXED'] == plans['LOW_PARAM'] == plans['LOW_UNION']
    choices = {a: core.choose(member, low, CASE, a, plans[a], 16, Counter(), state) for a, state in states.items()}
    assert choices['LOW_FIXED'] == choices['LOW_PARAM'] == choices['LOW_UNION']
    assert low == low_anchors()


def test_unique_failed_and_certified_targets_commit_after_decisions_without_safety_updates():
    source, work = low_anchors(), Counter()
    state = core.prepare(source, 'LOW_PARAM', work)
    safety = deepcopy(state['bounds'])
    for certified, index in ((False, 0), (True, 1)):
        member = unique_member(certified)
        before = deepcopy(state)
        plan = core.make_plan(member, source, CASE, 'LOW_PARAM', work, state)
        saved = deepcopy(plan)
        assert state == before
        assert plan['candidates'] == [index] and (plan['utility_lower'] >= 2) == certified
        event = core.advance(state, member, source, 'LOW_PARAM', work, plan)
        assert event == dict(source_index=index, samples=384)
        assert plan == saved and state['bounds'] == safety
        for op in core.OPERATORS:
            for cat in core.ALPHABETS[op]:
                assert state['counts'][index][op][cat] == before['counts'][index][op][cat]+member[op][cat]
    assert state['commits'] == [1, 1, 0] and state['members'] == []
    assert work['parameter_committed_targets'] == 2 and work['parameter_committed_samples'] == 768
    assert work['controlled_samples'] == 0 and source == low_anchors()


def test_ambiguous_and_member_fallback_targets_do_not_commit_parameters():
    source = low_anchors()
    state = core.prepare(source, 'LOW_PARAM', Counter())
    before = deepcopy(state)
    for member, force in ((core.empty(), False), (unique_member(True), True)):
        plan = core.make_plan(member, source, CASE, 'LOW_PARAM', Counter(), state, force)
        assert len(plan['candidates']) != 1 or plan['mode'] == 'member'
        assert core.advance(state, member, source, 'LOW_PARAM', Counter(), plan) is None
        assert state == before


def test_updated_points_query_proxy_and_tv_use_cumulative_counts_once_but_safety_stays_fixed():
    source = low_anchors()
    state = core.prepare(source, 'LOW_PARAM', Counter())
    initial = core.make_plan(core.empty(), source, CASE, 'LOW_PARAM', Counter(), state)
    commit_two(state, source, Counter())
    current = core.empty()
    plan = core.make_plan(current, source, CASE, 'LOW_PARAM', Counter(), state)
    fixed_state = core.prepare(source, 'LOW_FIXED', Counter())
    fixed = core.make_plan(current, source, CASE, 'LOW_FIXED', Counter(), fixed_state)
    assert plan['risks'] == fixed['risks'] and plan['goals_lower'] == fixed['goals_lower']
    assert plan['candidate_envelopes'] == fixed['candidate_envelopes']
    assert plan['pure_vectors'] != initial['pure_vectors']
    means = {i: core.prior.evidence.posterior(state['counts'][i]) for i in plan['candidates']}
    average = {op: {cat: sum(mean[op][cat] for mean in means.values())/len(means)
                    for cat in core.ALPHABETS[op]} for op in core.OPERATORS}
    assert plan['pure_vectors'] == core.vectors(CASE, average)
    regrets = []
    weights = {'reward':(1, 0, 0), 'goal':(1, 0, 4), 'risk':(1, 4, 4)}
    chosen = core.queries(plan)
    for mean in means.values():
        pure = core.vectors(CASE, mean); values = []
        for query, weight in weights.items():
            value = lambda v: sum(v[i]*weight[i]*(-1 if i==1 else 1) for i in range(3))
            values.append(max(value(v) for v in pure.values())-value(pure[chosen[query]['policy']]))
        regrets.append(sum(values)/3)
    assert plan['query_proxy'] == max(regrets)
    assert not plan['query_ready']
    choice = core.choose(current, source, CASE, 'LOW_PARAM', plan, 0, Counter(), state)
    scores = {op: min(sum(abs(means[a][op][cat]-means[b][op][cat]) for cat in core.ALPHABETS[op])/2
                      for a, b in combinations(means, 2)) for op in core.OPERATORS}
    assert choice['reason'] == 'identify' and choice['scores'] == scores
    original_means = {i: core.prior.evidence.posterior(source[i]) for i in plan['candidates']}
    original_short = min(sum(abs(original_means[a]['SHORT_PASS'][cat]-original_means[b]['SHORT_PASS'][cat])
                             for cat in core.ALPHABETS['SHORT_PASS'])/2 for a,b in combinations(means,2))
    assert scores['SHORT_PASS'] != original_short


def test_union_retains_all_ambiguous_and_failed_terminal_counts():
    source, work = low_anchors(), Counter()
    state = core.prepare(source, 'LOW_UNION', work)
    failed, ambiguous = core.empty(), core.empty()
    ambiguous['SHORT_PASS'].update(DELIVERY=15, LOST=1)
    for member in (failed, ambiguous):
        before = deepcopy(state)
        core.make_plan(member, source, CASE, 'LOW_UNION', work, state)
        assert state == before
        core.advance(state, member, source, 'LOW_UNION', work)
    assert state['members'] == [failed, ambiguous]
    ambiguous['SHORT_PASS']['DELIVERY'] += 1
    assert state['members'][1]['SHORT_PASS']['DELIVERY'] == 15
    assert work['union_retained_targets'] == 2 and work['union_retained_samples'] == 16
    assert work['controlled_samples'] == 0 and not state['no_feasible']


def test_full_fixed_matches_actual_retained_v225_plans_and_choices():
    folder = ROOT/'reports/mixture_confidence_v225'
    libraries = json.loads((folder/'source_evidence.json').read_text())
    rows = [r for r in json.loads((folder/'records.json').read_text()) if r['arm']=='FIXED_CS']
    cases = [next(r for r in rows if r['stop']=='identified'), next(r for r in rows if r['stop']=='query_set')]
    saved = lambda value: json.loads(json.dumps(exact_json(value)))
    for row in cases:
        source, member, work = libraries[row['life']]['anchors'], core.empty(), Counter()
        state = core.prepare(source, 'FULL_FIXED', work); before = deepcopy(state)
        plan = core.make_plan(member, source, row['case'], 'FULL_FIXED', work, state)
        assert saved(plan) == row['initial_plan']
        for batch in row['batches']:
            choice = core.choose(member, source, row['case'], 'FULL_FIXED', plan, batch['spent']-16, work, state)
            assert saved(choice) == batch['choice']
            for cat, count in batch['increments'].items():member[batch['operator']][cat] += count
            plan = core.make_plan(member, source, row['case'], 'FULL_FIXED', work, state)
            assert saved(plan) == batch['plan']
        assert core.choose(member, source, row['case'], 'FULL_FIXED', plan, row['spent'], work, state) is None
        assert saved(plan) == row['terminal_plan']
        assert core.advance(state, member, source, 'FULL_FIXED', work, plan) is None and state == before
