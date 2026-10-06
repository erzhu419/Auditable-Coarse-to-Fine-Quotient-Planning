from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import io
import json

import pytest

from scripts import audit_executable_trajectory_v254 as audit


def complete_rounds():
    return [{audit.S: short, audit.DETOUR: detour, audit.R: retry} for short, detour, retry in (
        ('DELIVERY', 'DELIVERY', None), ('LOST', 'DELIVERY', None),
        ('DELIVERY', 'RECOVERY', 'DELIVERY'), ('DELIVERY', 'LOST', None),
        ('LOST', 'RECOVERY', 'LOST'), ('DELIVERY', 'DELIVERY', None))]


@pytest.mark.parametrize('operating,retry_cost', [('low', '17/20'), ('low', '19/20'),
                                                ('high', '17/20'), ('high', '19/20')])
def test_direct_complete_round_vectors_all_ordered_scores_and_old_bets_match(operating, retry_cost):
    from acfqp.science import executable_trajectory_v254 as producer
    observations = complete_rounds()
    case = dict(operating=operating, retry_cost=retry_cost)
    state = producer.new_type_state()
    for index, outcomes in enumerate(observations, 1):
        producer.observe_round(state, outcomes, index)
        assert audit.round_vectors(outcomes, case) == producer.round_vectors(case, outcomes)
    producer.observe_tail_s(state, 'LOST')
    vectors = audit.empirical_vectors(observations, case)
    assert vectors == producer.pure_vectors(state, case)
    assert audit.point_queries(vectors) == {query: decision['policy']
                                          for query, decision in producer.point_queries(vectors).items()}
    assert vectors['DETOUR_RETRY'][0] == -audit.trajectory.COSTS[operating][1]-F(retry_cost)*F(2, 6)
    checks = []
    for query in ('goal', 'risk'):
        for chosen in audit.POLICIES:
            for other in audit.POLICIES:
                if chosen == other:
                    continue
                statistics = producer.actual_statistics(observations, query, chosen, other, retry_cost, {})
                needed, scores, lower, upper = audit.direct_scores(observations, query, chosen, other, retry_cost)
                assert statistics.n == len(scores) == 6
                assert statistics.score_units == tuple(int(score*20) for score in scores)
                assert statistics.bets == tuple((bet.numerator, bet.denominator)
                    for bet in audit.trajectory.predictable_bets(scores, lower, upper))
                saved = dict(producer.direct.statistics_record(statistics),
                    **producer.direct.evaluate(statistics, case), score_source='actual_complete_conditional_rounds')
                assert audit.audit_direct_comparison(observations, case, query, chosen, other, saved,
                    lambda name, ok: checks.append((name, ok)), {}) == saved['certified']
    assert all(ok for _, ok in checks)
    assert sum(state['native_counts'][audit.R].values()) == 2 < len(observations)
    assert sum(state['native_counts'][audit.S].values()) == 7


def test_direct_certificate_AND_and_row_minimum_substitution_is_detected():
    from acfqp.science import executable_trajectory_v254 as producer
    observations, case = complete_rounds(), dict(operating='low', retry_cost='17/20')
    chosen = audit.point_queries(audit.empirical_vectors(observations, case))
    queries = {query: dict(policy=policy) for query, policy in chosen.items()}
    saved = producer.trajectory_certificates(observations, case, queries, {})
    checks = []
    ready = audit.audit_trajectory_certificate(observations, case, chosen, saved,
        lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks) and all(ready.values()) == saved['all_ready']
    assert len(saved['comparison_records']) == 6
    invalid = deepcopy(saved['queries']['goal']['comparisons'][0])
    invalid['n'] = 2
    failures = []
    audit.audit_direct_comparison(observations, case, 'goal', chosen['goal'], invalid['other'], invalid,
                                 lambda name, ok: failures.append(name) if not ok else None, {})
    assert failures == ['complete_conditional_round_score_statistics_without_row_minimum']


def test_postfreeze_truth_queries_use_complete_conditional_retry_expectation():
    observations, case = complete_rounds(), dict(operating='high', retry_cost='19/20')
    law = {audit.S: dict(DELIVERY=F(4, 6), LOST=F(2, 6)),
           audit.DETOUR: dict(DELIVERY=F(3, 6), LOST=F(1, 6), RECOVERY=F(2, 6)),
           audit.R: dict(DELIVERY=F(1, 2), LOST=F(1, 2))}
    queries = {query: dict(policy=policy) for query, policy in audit.point_queries(
        audit.empirical_vectors(observations, case)).items()}
    actual = audit.score_queries(queries, case, law)
    pure = audit.trajectory.vectors(case, law)
    assert pure['DETOUR_RETRY'][0] == -F(7, 100)-F(19, 20)*F(1, 3)
    for query, weights in audit.trajectory.WEIGHTS.items():
        assert actual[query]['actual'] == pure[queries[query]['policy']]
        assert actual[query]['regret'] == max(audit.trajectory.utility(vector, weights) for vector in pure.values()) \
            -audit.trajectory.utility(actual[query]['actual'], weights)


def test_postfreeze_score_equality_normalizes_public_cost_and_detects_mutated_regret():
    case = dict(id='v254_l00_source_t0_c0', operating='low', retry_cost='17/20', context='A', stage='QUERY_QUALIFICATION')
    law = {audit.S: dict(DELIVERY=F(4, 6), LOST=F(2, 6)),
           audit.DETOUR: dict(DELIVERY=F(3, 6), LOST=F(1, 6), RECOVERY=F(2, 6)),
           audit.R: dict(DELIVERY=F(1, 2), LOST=F(1, 2))}
    queries = {query: dict(policy=policy) for query, policy in audit.point_queries(
        audit.empirical_vectors(complete_rounds(), case)).items()}
    independent = [dict(life=0, kind='CHECKPOINT', checkpoint_samples=4608, identity=0, cost_index=0,
        index=None, case=case, queries=audit.score_queries(queries, case, law),
        false_certificates=dict(ROW_JOINT=0, TRAJECTORY=0))]
    serialized = json.loads(json.dumps(independent, default=str))
    assert audit.exact(serialized) != independent
    assert audit.posthoc_scores_equal(serialized, independent)
    assert independent[0]['case']['retry_cost'] == '17/20'
    invalid = deepcopy(serialized)
    invalid[0]['queries']['goal']['regret'] = str(F(invalid[0]['queries']['goal']['regret'])+F(1, 100))
    assert not audit.posthoc_scores_equal(invalid, independent)


def test_compact_actual_primitive_sampler_replay_preserves_tails_cursor_and_target_offsets(monkeypatch):
    from scripts import run_executable_trajectory_v254 as producer
    monkeypatch.setattr(audit, 'SOURCE_COST', 9)
    monkeypatch.setattr(audit, 'MIDDLE_COST', 17)
    monkeypatch.setattr(audit, 'LIFE_CAPS', (31, 31, 31))
    monkeypatch.setattr(audit, 'SOURCE_BASE', 123000)
    monkeypatch.setattr(audit, 'TARGET_BASE', 124000)
    monkeypatch.setattr(producer, 'SOURCE_BASE', 123000)
    monkeypatch.setattr(producer, 'TARGET_BASE', 124000)
    _, laws, _, _ = producer.task.world(0)
    work, states = Counter(), [producer.core.new_type_state() for _ in range(3)]
    simulator = producer.PrimitiveSimulator(0, laws[:3], work)
    tape, rounds, step, round_id, cursor = io.StringIO(), io.StringIO(), 0, 0, 0
    expected = {}
    for segment, cap in enumerate((9, 17, 31)):
        sampled = producer.sample_segment(0, segment, cap, states, simulator, step, round_id, cursor,
                                          tape, rounds, work)
        step, round_id, cursor = (sampled[field] for field in ('step', 'round_id', 'cursor'))
        expected[cap] = deepcopy(states)
    primitive_rows = [json.loads(line) for line in tape.getvalue().splitlines()]
    round_rows = [json.loads(line) for line in rounds.getvalue().splitlines()]
    checks = []
    prefixes = audit.replay_life(0, primitive_rows, round_rows, lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks) and len(primitive_rows) == work['controlled_samples'] == 31
    for cap, states_ in expected.items():
        assert prefixes[cap]['native_counts'] == [state['native_counts'] for state in states_]
        assert prefixes[cap]['rounds'] == [state['rounds'] for state in states_]
        assert prefixes[cap]['tail_s_samples'] == [state['tail_s_samples'] for state in states_]
        assert prefixes[cap]['round_prefix_last_ids'] == [state['round_prefix_last_id'] for state in states_]
    assert sum(row['role'] == 'tail_S' for row in primitive_rows) > 0
    assert any(row['operator'] == audit.R for row in primitive_rows)
    assert all(row['outcomes'][audit.R] is None if row['outcomes'][audit.DETOUR] != 'RECOVERY'
               else row['outcomes'][audit.R] in audit.ALPHABETS[audit.R] for row in round_rows)
    first_after_middle = next(row for row in primitive_rows if row['segment'] == 2)
    assert first_after_middle['operator'] == audit.S and first_after_middle['draw_start'] > 0
    invalid = deepcopy(primitive_rows)
    invalid[first_after_middle['step_index']-1]['draw_start'] = 0
    failures = []
    audit.replay_life(0, invalid, round_rows, lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['fresh_actual_conditional_primitive_seed_phase_offset_and_fee']


def evidence(goal, risk):
    choices = dict(reward='WAIT', goal='SHORT', risk='DETOUR_RETURN')
    decisions = {query: dict(policy=policy, certified={'reward': True, 'goal': goal, 'risk': risk}[query])
                 for query, policy in choices.items()}
    decisions['goal']['comparisons'] = [dict(other='DETOUR_RETRY', certified=goal)]
    return dict(queries=decisions, all_ready=goal and risk, threshold=960)


def test_independent_public_roster_and_terminal_exact_full_cap_copy_are_fixed():
    from scripts import run_executable_trajectory_v254 as producer
    expected = audit.public_roster()
    worlds = {life: producer.task.world(life) for life in audit.LIVES}
    assert producer.public_roster(worlds) == expected
    assert len(expected) == 180
    assert Counter(row['kind'] for row in expected) == dict(CHECKPOINT=108, RETURN_PROJECTION=72)
    terminal = next(row for row in expected if row['kind'] == 'RETURN_PROJECTION')
    full = dict(life=terminal['life'], identity=terminal['identity'], cost_index=terminal['cost_index'],
        case=dict(operating=terminal['case']['operating'], retry_cost=terminal['case']['retry_cost']),
        row_joint=dict(case=dict(original='full_case'), query_evidence=evidence(False, True)),
        trajectory=evidence(True, False), native_counts={audit.S: dict(DELIVERY=1, LOST=2)},
        total_paid_samples=audit.LIFE_CAPS[terminal['life']], model_seconds=dict(point_vectors=1., row_joint=2., trajectory=3.),
        output_seconds=1.)
    before = deepcopy(full)
    projected = audit.projected_record(full, terminal)
    assert projected['selected_full_cap_record'] == {field: terminal[field] for field in ('life', 'identity', 'cost_index')}
    assert projected['row_joint']['case'] == terminal['case']
    assert projected['row_joint']['query_evidence'] == full['row_joint']['query_evidence']
    assert projected['trajectory'] == full['trajectory']
    assert projected['native_counts'] == full['native_counts'] and projected['total_paid_samples'] == full['total_paid_samples']
    assert all(value == 0 for value in projected['model_seconds'].values()) and projected['output_seconds'] == 0
    assert full == before


def test_paired_fixed_backend_summary_full_fees_and_positive_signal_match_frozen_rule():
    from scripts import run_executable_trajectory_v254 as producer
    records, scores, artifacts = [], [], []
    for life in audit.LIVES:
        for label in audit.CHECKPOINTS:
            records.append(dict(life=life, kind='CHECKPOINT', checkpoint_label=label,
                identity=0, cost_index=0, index=None, row_joint=dict(query_evidence=evidence(False, True)),
                trajectory=evidence(True, True)))
        records.append(dict(life=life, kind='RETURN_PROJECTION', checkpoint_label='FULL_CAP',
            identity=0, cost_index=0, index=54, row_joint=dict(query_evidence=evidence(False, True)),
            trajectory=evidence(True, False)))
        artifacts.append(dict(life=life, primitive_samples=audit.LIFE_CAPS[life], source_samples=4608,
            acquisition_samples=audit.LIFE_CAPS[life]-4608,
            timings=dict(observation_updates=1., point_vectors=2., row_joint=3., trajectory=4.),
            observation_seconds=1., output_seconds=1., cache_statistics={}, work={}))
    scores = [dict(false_certificates=dict(ROW_JOINT=0, TRAJECTORY=0)) for _ in records]
    expected = audit.summarize(records, scores, artifacts)
    assert expected == producer.summarize(records, scores, artifacts)
    assert expected['physical_observations'] == 48384 and expected['physical_source_samples'] == 13824
    assert expected['terminal_paired']['goal']['gains'] == 3
    assert expected['terminal_paired']['risk']['losses'] == 3
    assert expected['terminal_paired']['query_ready']['unchanged'] == 3
    assert expected['positive_qualification_signal']
    scores[0]['false_certificates']['TRAJECTORY'] = 1
    expected = audit.summarize(records, scores, artifacts)
    assert expected == producer.summarize(records, scores, artifacts)
    assert not expected['positive_qualification_signal'] and expected['methods']['TRAJECTORY']['false_certificates'] == 1
    assert expected['qualification_only'] and not expected['complete_lifecycle_test'] and not expected['scientific_gate_changed']
