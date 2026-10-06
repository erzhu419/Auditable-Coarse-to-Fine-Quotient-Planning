"""Actual conditional pairs, raw joint policies and unchanged predictable bets."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import pytest

from acfqp.science import executable_trajectory_v254 as core

S, D, R = core.OPERATORS
CASE = dict(operating='low', retry_cost='17/20')


def outcome(short, detour, retry=None):
    return {S: short, D: detour, R: retry}


def test_all_eight_real_outcomes_include_only_conditional_retry_cost():
    sc, dc = core.direct.COST_PRIOR['low']
    for values in core.OUTCOMES:
        short, detour, retry = values
        vectors = core.round_vectors(CASE, dict(zip(core.OPERATORS, values)))
        assert vectors['WAIT'] == [0, 0, 0]
        assert vectors['SHORT'] == [-sc, int(short == 'LOST'), int(short == 'DELIVERY')]
        assert vectors['DETOUR_RETURN'] == [-dc, int(detour == 'LOST'), int(detour == 'DELIVERY')]
        recovery = detour == 'RECOVERY'
        assert vectors['DETOUR_RETRY'] == [-dc-F(17, 20)*recovery,
            int(detour == 'LOST' or recovery and retry == 'LOST'),
            int(detour == 'DELIVERY' or recovery and retry == 'DELIVERY')]
        if recovery:
            assert vectors['DETOUR_RETURN'][1:] == [0, 0]
    assert len(core.OUTCOMES) == 8


def test_real_rounds_and_native_only_tails_have_distinct_evidence_units():
    state = core.new_type_state()
    rows = [outcome('DELIVERY', 'DELIVERY'), outcome('LOST', 'RECOVERY', 'DELIVERY')]
    for number, row in enumerate(rows, 1):
        core.observe_round(state, row, number)
    before = deepcopy(state)
    for _ in range(8):
        core.observe_tail_s(state, 'DELIVERY')
    assert state['rounds'] == rows and state['round_prefix_last_id'] == 2
    assert state['joint_outcome_counts'] == before['joint_outcome_counts']
    assert [sum(state['native_counts'][op].values()) for op in core.OPERATORS] == [10, 2, 1]
    assert state['tail_s_samples'] == 8
    vectors = core.pure_vectors(state, CASE)
    literal = [core.round_vectors(CASE, row) for row in rows]
    assert vectors == {policy: [sum(row[policy][position] for row in literal)/2
        for position in range(3)] for policy in core.POLICIES}
    assert vectors['SHORT'][2] == F(1, 2)
    with pytest.raises(ValueError, match='R exactly'):
        core.observe_round(state, outcome('DELIVERY', 'DELIVERY', 'LOST'), 3)
    assert len(state['rounds']) == 2


def test_point_policies_use_exact_raw_joint_means_and_lexical_ties():
    state = core.new_type_state()
    core.observe_round(state, outcome('DELIVERY', 'RECOVERY', 'LOST'), 1)
    queries = core.point_queries(core.pure_vectors(state, CASE))
    assert queries == dict(reward=dict(policy='WAIT'), goal=dict(policy='SHORT'), risk=dict(policy='SHORT'))
    tied = {policy: [F(0)]*3 for policy in core.POLICIES}
    assert all(value['policy'] == 'DETOUR_RETRY' for value in core.point_queries(tied).values())


def test_direct_statistics_include_nonrecovery_rounds_and_actual_pair_covariance(monkeypatch):
    monkeypatch.setattr(core.direct, 'stream_statistics', lambda *args, **kwargs: pytest.fail('synthetic row pairing'))
    rows = [outcome('DELIVERY', 'DELIVERY'), outcome('LOST', 'LOST'),
        outcome('DELIVERY', 'RECOVERY', 'DELIVERY')]
    statistics = core.actual_statistics(rows, 'goal', 'SHORT', 'DETOUR_RETRY', '17/20', {})
    assert statistics.n == 3  # R is physically observed only once.
    assert statistics.score_units == (0, 0, -17)
    assert statistics.bets == core.direct.predictable_bets(statistics.spec, statistics.score_units)
    shuffled = [outcome('DELIVERY', 'LOST'), outcome('LOST', 'DELIVERY'), rows[-1]]
    other = core.actual_statistics(shuffled, 'goal', 'SHORT', 'DETOUR_RETRY', '17/20', {})
    assert other.score_sum_units == statistics.score_sum_units
    assert other.score_square_sum_units != statistics.score_square_sum_units
    assert other.score_units == (-80, 80, -17)


def test_fixed_streams_cache_cost_reuse_and_predictability():
    rows = [outcome('DELIVERY', 'LOST'), outcome('LOST', 'RECOVERY', 'DELIVERY')]
    work, cache = Counter(), {}
    first = core.actual_statistics(rows, 'risk', 'SHORT', 'WAIT', '17/20', cache, work)
    assert core.actual_statistics(rows, 'risk', 'SHORT', 'WAIT', '19/20', cache, work) is first
    cheap = core.actual_statistics(rows, 'goal', 'SHORT', 'DETOUR_RETRY', '17/20', cache, work)
    dear = core.actual_statistics(rows, 'goal', 'SHORT', 'DETOUR_RETRY', '19/20', cache, work)
    assert cheap is not dear and cheap.score_units[-1]-dear.score_units[-1] == 2
    extended = core.actual_statistics(rows+[outcome('LOST', 'RECOVERY', 'LOST')],
        'goal', 'SHORT', 'DETOUR_RETRY', '17/20', cache, work)
    assert extended.bets[:2] == cheap.bets
    assert core.direct.evaluate(cheap, CASE)['threshold'] == 4320
    assert core.direct.evaluate(first, dict(operating='high', retry_cost='17/20'))['constant_gap'] != core.direct.evaluate(first, CASE)['constant_gap']
    assert work['trajectory_score_cache_hits'] == 1 and work['trajectory_unique_score_prefixes'] == 4


def test_certificates_keep_all_alternatives_and_original_threshold(monkeypatch):
    rows = [outcome('DELIVERY', 'RECOVERY', 'DELIVERY')]
    queries = dict(reward=dict(policy='WAIT'), goal=dict(policy='SHORT'), risk=dict(policy='DETOUR_RETURN'))
    seen = []
    def evaluate(statistics, case):
        seen.append((statistics.spec.query, statistics.spec.chosen, statistics.spec.other))
        return dict(certified=statistics.spec.other != 'DETOUR_RETRY', threshold=4320)
    monkeypatch.setattr(core.direct, 'evaluate', evaluate)
    proof = core.trajectory_certificates(rows, CASE, queries, {})
    assert proof['threshold'] == 4320 and not proof['all_ready']
    assert proof['queries']['reward']['certified']
    assert not proof['queries']['goal']['certified'] and not proof['queries']['risk']['certified']
    assert len(seen) == len(proof['comparison_records']) == 6
    for query in ('goal', 'risk'):
        assert {row['other'] for row in proof['queries'][query]['comparisons']} == set(core.POLICIES)-{queries[query]['policy']}
        assert all(row['n'] == 1 and row['score_source'] == 'actual_complete_conditional_rounds'
            for row in proof['queries'][query]['comparisons'])
