"""Continuous-event chronology, exact likelihoods and causal plan isolation."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from math import factorial, prod

import pytest

from acfqp.science import continuous_row_cs_v259 as core

S, D, R = core.OPERATORS
B_CASE = dict(context='B', stage='B', operating='low', retry_cost='17/20')
RETURN_CASE = dict(context='A', stage='A_RETURN', operating='low', retry_cost='17/20')


def increments(scale):
    return {S: dict(DELIVERY=9*scale, LOST=scale),
        D: dict(DELIVERY=7*scale, LOST=scale, RECOVERY=2*scale),
        R: dict(DELIVERY=2*scale, LOST=scale)}


def add(state, context, identity, rows):
    for op, counts in rows.items():
        core.observe_row(state, context, identity, op, counts)


def switched_state():
    work = Counter()
    state = core.prepare(0, 'CONTINUOUS_REUSE', work)
    for identity in range(3):
        add(state, 'A', identity, increments(identity+1))
    core.freeze_sources(state, 'A')
    add(state, 'A', 0, increments(4))
    core.begin_b(state, D, (2, 0, 1), work)
    for identity in range(3):
        add(state, 'B', identity, increments(identity+5))
    core.freeze_sources(state, 'B')
    add(state, 'B', 1, increments(7))
    return state


def normalizer(counts):
    # Independent exact Jeffreys sequence likelihood, without the producer.
    total = sum(counts)
    numerator = prod(factorial(2*n) for n in counts)
    denominator = prod(factorial(n) for n in counts)
    if len(counts) == 2:
        denominator *= 4**total*factorial(total)
    else:
        numerator *= factorial(total)
        denominator *= factorial(2*total+1)
    return F(numerator, denominator)


def inside(region, probabilities):
    counts = region['counts']
    likelihood = prod(probabilities[cat]**count for cat, count in counts.items())
    return normalizer(tuple(counts.values())) <= region['threshold']*likelihood


@pytest.mark.parametrize('arm,underlying', [
    ('CONTINUOUS_REUSE', 'TRAJECTORY_REUSE'),
    ('TRAJECTORY_REUSE', 'TRAJECTORY_REUSE'),
    ('TRAJECTORY_REBUILD', 'TRAJECTORY_REBUILD'),
])
def test_research_arm_preserves_native_banks_and_comparison_specific_round_reuse(arm, underlying):
    expected = core.original.prepare(1, underlying, Counter())
    actual = core.prepare(1, arm, Counter())
    assert actual.pop('research_arm') == arm
    assert actual == expected
    assert actual['trajectory_arm'] == underlying


def test_before_b_and_changed_rows_keep_the_exact_original_events_and_thresholds():
    state = core.prepare(0, 'CONTINUOUS_REUSE', Counter())
    add(state, 'A', 0, increments(1))
    core.freeze_sources(state, 'A')
    case = dict(RETURN_CASE, stage='A')
    assert core.regions(core.empty(), case, state, 0, 3) == core.row_views.regions(
        core.empty(), case, state, 0, 3)
    state = switched_state()
    for case, identity, index in ((B_CASE, 1, 30), (RETURN_CASE, 0, 54)):
        expected = core.row_views.regions(core.empty(), case, state, identity, index)
        actual = core.regions(core.empty(), case, state, identity, index)
        assert actual[D] == expected[D]
        assert len(actual[D]) == 3
        assert [row['threshold'] for row in actual[D]] == [720, 720, 8640]
        assert all('prefix_kind' not in row for row in actual[D])


def test_b_uses_one_mapped_a_event_and_never_counts_a_member_observation_twice():
    state, member = switched_state(), core.empty()
    member[S] = dict(DELIVERY=2, LOST=1)
    core.observe_row(state, 'B', 1, S, member[S])
    before = deepcopy(state)
    rows = core.regions(member, B_CASE, state, 1, 31)
    assert state == before
    for op in (S, R):
        assert [row['prefix_kind'] for row in rows[op]] == [
            'a_source', 'a_switch', 'a_switch_plus_b_source', 'continuous_current', 'member']
        assert [row['event'] for row in rows[op]][:4] == [f'l0/A/pool0/{op}']*4
        assert rows[op][4]['event'] == f'l0/member31/{op}'
        for region in rows[op][:4]:
            parts = region['native_context_counts']
            assert all(part['identity'] == (0 if context == 'A' else 1)
                for context, part in parts.items())
            assert region['counts'] == {cat: sum(part['counts'][cat] for part in parts.values())
                for cat in core.ALPHABETS[op]}
        assert rows[op][0]['counts'] == state['a']['sources'][0][op]
        assert rows[op][1]['counts'] == state['a_at_switch']['pools'][0][op]
        assert rows[op][2]['counts'] == {
            cat: state['a_at_switch']['pools'][0][op][cat]+state['b']['sources'][1][op][cat]
            for cat in core.ALPHABETS[op]}
        assert rows[op][3]['counts'] == {
            cat: state['a']['pools'][0][op][cat]+state['b']['pools'][1][op][cat]
            for cat in core.ALPHABETS[op]}
        assert rows[op][4]['counts'] == member[op]
        assert rows[op][4]['native_context_counts'] == {}
    rows[S][3]['counts']['DELIVERY'] += 99
    rows[S][3]['native_context_counts']['A']['counts']['DELIVERY'] += 99
    assert state == before and member[S]['DELIVERY'] == 2


def test_return_keeps_genuine_merge_ledger_and_extends_the_whole_prefix_not_a_only():
    state = switched_state()
    add(state, 'A', 0, increments(8))
    other = deepcopy(state)
    core.row_views.regions(core.empty(), RETURN_CASE, other, 0, 54)
    before = deepcopy(state)
    result = core.regions(core.empty(), RETURN_CASE, state, 0, 54)
    assert state['return_merge'] == other['return_merge']
    assert state['return_merge']['total_samples'] > 0
    for key in ('a', 'b', 'a_at_switch', 'trajectory', 'round_log'):
        assert state[key] == before[key]
    for op in (S, R):
        pool = result[op][:4]
        assert all(row['event'] == f'l0/A/pool0/{op}' for row in pool)
        assert all(all(left['counts'][cat] <= right['counts'][cat]
            for cat in core.ALPHABETS[op]) for left, right in zip(pool, pool[1:]))
        assert pool[-1]['counts'] != state['a']['pools'][0][op]
        assert pool[-1]['native_context_counts']['B']['counts'] == state['b']['pools'][1][op]
        assert pool[2]['native_context_counts']['A']['counts'] == state['a_at_switch']['pools'][0][op]


@pytest.mark.parametrize('counts,p', [
    ((7, 3), (F(1, 5), F(4, 5))),
    ((11, 2, 5), (F(1, 2), F(1, 3), F(1, 6))),
])
def test_jeffreys_eprocess_next_step_has_conditional_mean_one_for_every_admitted_row(counts, p):
    old = normalizer(counts)
    ratios = []
    for category in range(len(counts)):
        new = list(counts)
        new[category] += 1
        ratios.append(normalizer(tuple(new))/old/p[category])
    assert sum(probability*ratio for probability, ratio in zip(p, ratios)) == 1
    assert all(ratio > 0 for ratio in ratios)


def test_continued_likelihood_can_exclude_a_model_that_each_native_cs_still_admits():
    state = core.prepare(0, 'CONTINUOUS_REUSE', Counter())
    core.observe_row(state, 'A', 0, S, dict(DELIVERY=360, LOST=40))
    core.freeze_sources(state, 'A')
    core.begin_b(state, D, (0, 1, 2), Counter())
    core.observe_row(state, 'B', 0, S, dict(DELIVERY=360, LOST=40))
    core.freeze_sources(state, 'B')
    candidate = dict(DELIVERY=F(19,20), LOST=F(1,20))
    separate = core.row_views.regions(core.empty(), B_CASE, state, 0, 30)[S]
    continued = core.regions(core.empty(), B_CASE, state, 0, 30)[S]
    assert all(inside(row, candidate) for row in separate)
    assert not inside(continued[3], candidate)
    assert sum(continued[3]['counts'].values()) == 800
    assert continued[3]['threshold'] == 720


def test_continuous_execution_plan_keeps_the_same_point_policy_and_all_query_evidence():
    state = core.prepare(0, 'CONTINUOUS_REUSE', Counter())
    a_rows = {S: dict(DELIVERY=1200, LOST=0),
        D: dict(DELIVERY=0, LOST=1200, RECOVERY=0),
        R: dict(DELIVERY=1200, LOST=0)}
    add(state, 'A', 0, a_rows)
    core.freeze_sources(state, 'A')
    core.begin_b(state, D, (0, 1, 2), Counter())
    b_rows = {op: {cat: count//3 for cat, count in row.items()} for op, row in a_rows.items()}
    add(state, 'B', 0, b_rows)
    core.freeze_sources(state, 'B')
    control = deepcopy(state)
    control['research_arm'] = 'TRAJECTORY_REUSE'
    member = core.empty()
    before = deepcopy(state)
    continued = core.make_plan(member, B_CASE, state, 0, 30, {}, Counter())
    separate = core.make_plan(member, B_CASE, control, 0, 30, {}, Counter())
    assert state == before
    for key in ('posterior', 'pure_vectors', 'evidence_counts', 'effective_n',
            'queries', 'query_pure_vectors', 'query_ready', 'query_certificates',
            'query_blockers', 'query_gap_bounds', 'query_gap_bounds_kind',
            'query_evidence', 'native_round_ids', 'native_joint_outcome_counts',
            'native_complete_rounds'):
        assert continued[key] == separate[key]
    assert continued['envelopes'][S]['bounds']['DELIVERY'][0] > separate['envelopes'][S]['bounds']['DELIVERY'][0]
    assert continued['utility_lower'] >= 2 and separate['utility_lower'] >= 2
    assert continued['goal_feasibility']['skip_reason'] == 'execution_certified'
    assert continued['row_confidence_kind'] == 'continuous_compatible_jeffreys_prefixes'
    assert 'row_confidence_kind' not in separate


@pytest.mark.parametrize('arm', ['TRAJECTORY_REUSE', 'TRAJECTORY_REBUILD'])
def test_controls_delegate_without_rebuilding_or_decorating_the_original_plan(arm, monkeypatch):
    state = core.prepare(0, arm, Counter())
    member, cache, work = core.empty(), {}, Counter()
    expected, calls = {'original_plan': True}, []
    def base(*args):
        calls.append(args)
        return expected
    monkeypatch.setattr(core.original, 'make_plan', base)
    result = core.make_plan(member, B_CASE, state, 1, 30, cache, work)
    assert result is expected
    assert calls == [(member, B_CASE, state, 1, 30, cache, work)]
