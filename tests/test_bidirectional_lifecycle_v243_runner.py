"""Checks for fresh paired streams, paid limits and the three-arm conditions."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from io import StringIO
import pytest

from scripts import run_bidirectional_lifecycle_v243 as runner
from scripts import run_reuse_rebuild_lifecycle_v242 as old


def test_arm_rotation_has_all_three_first_positions_and_new_seed_bases():
    assert runner.arm_order(0, 0) == ('ONE_WAY', 'TWO_WAY', 'REBUILD')
    assert runner.arm_order(0, 1) == ('TWO_WAY', 'REBUILD', 'ONE_WAY')
    assert runner.arm_order(1, 1) == ('REBUILD', 'ONE_WAY', 'TWO_WAY')
    assert runner.SOURCE_BASE == 280000 and runner.TARGET_BASE == 281000
    assert runner.SOURCE_BASE != old.SOURCE_BASE and runner.TARGET_BASE != old.TARGET_BASE
    assert len(runner.LIVES)*len(runner.ARMS)*len(runner.TARGETS) == 648


def test_paid_member_prefixes_are_separate_even_with_paired_seeds(monkeypatch):
    calls = []
    case = dict(context='A', stage='A', operating='high', retry_cost='19/20')

    def make_plan(member, case, state, identity, index, cache, work):
        observed = sum(sum(row.values()) for row in member.values())
        cache.setdefault('calls', []).append(observed)
        ready = observed >= state['stop_after']
        return dict(case=case, mix=[('WAIT', F(1))], utility_lower=F(2 if ready else 0),
            goal_impossible=False, query_ready=ready,
            query_evidence=dict(queries={'reward': dict(policy='WAIT', certified=True)},
                all_ready=ready, threshold=960))

    def draw(generator, law, operator, increments, number, work, progress):
        calls.append(tuple(generator.random() for _ in range(number)))
        increments['DELIVERY'] += number
        progress['draw_end'] += number

    monkeypatch.setattr(runner.core, 'make_plan', make_plan)
    monkeypatch.setattr(runner, 'draw', draw)
    monkeypatch.setattr(runner.acquisition, 'choose', lambda *args: dict(operator='SHORT_PASS', reason='synthetic'))
    rows, caches = [], []
    for arm, stop in (('ONE_WAY', 16), ('TWO_WAY', 32)):
        cache = {}
        state = dict(a=dict(pools=[runner.core.empty()]), stop_after=stop)
        rows.append(runner.run_target(0, 3, case, 0, state, arm, object(), Counter(),
            3456, 9504, cache, StringIO(), {}))
        caches.append(cache)
    one, two = rows
    assert one['seeds'] == two['seeds']
    assert calls[0] == calls[1] and calls[1] != calls[2]
    assert one['spent'] == 16 and two['spent'] == 32
    assert one['life_budget_remaining_after'] == 16 and two['life_budget_remaining_after'] == 0
    assert one['pooled_after']['SHORT_PASS']['DELIVERY'] == 16
    assert two['pooled_after']['SHORT_PASS']['DELIVERY'] == 32
    assert caches == [{'calls': [0, 16]}, {'calls': [0, 16, 32]}]
    assert one['joint_completed'] and two['joint_completed']


def test_source_stream_uses_new_base_and_life_slot_operator_formula(monkeypatch):
    def draw(generator, law, operator, increments, number, work, progress):
        increments['DELIVERY'] += number
        progress['draw_end'] += number

    monkeypatch.setattr(runner, 'draw', draw)
    records = []
    anchors, _ = runner.sources(2, 'B', [None]*78, records, Counter())
    assert sum(sum(row.values()) for anchor in anchors for row in anchor.values()) == 1152
    assert len(records) == 3*3*8
    for record in records:
        assert record['seed'] == 280000+(2*6+record['slot'])*3+runner.OPERATORS.index(record['operator'])
        assert record['index'] == record['slot']+24
        assert record['draw_end']-record['draw_start'] == 16


def cohort():
    records = []
    for life in runner.LIVES:
        for arm in runner.ARMS:
            for index in runner.TARGETS:
                stage = 'A' if index < 30 else 'B' if index < 54 else 'A_RETURN'
                records.append(dict(life=life, arm=arm, index=index, stage=stage,
                    spent=16 if arm != 'TWO_WAY' else 0, query_certified=True,
                    joint_completed=True, execution_certified=True, goal_impossible=False,
                    fallback=False, budget_exhausted=False, model_seconds=1.,
                    history=[dict(false_query_certificates=0, false_execution_certificate=False,
                        false_impossible_certificate=False, violation=False, goal_upper_ok=True, coverage=True)],
                    executed=dict(actual_utility=F(3), violation=False)))
    timings = {scope: {arm: dict.fromkeys(runner.LIVES, .1) for arm in runner.ARMS}
               for scope in ('planning', 'initialization', 'begin_b', 'observation')}
    return records, timings


def test_stage_conditions_include_both_controls_and_actual_execution_risk():
    records, timings = cohort()
    summary = runner.summarize(records, timings)
    assert summary['stage_condition_met'] and len(summary['conditions']) == 11
    assert summary['records'] == 648 and summary['physical_source_samples'] == 13824
    assert summary['methods']['TWO_WAY']['model_seconds'] == pytest.approx(.9)
    assert all(row['return_one_way_minus_two_way_samples'] == 384 for row in summary['paired'])
    bad = deepcopy(records)
    next(row for row in bad if row['arm'] == 'ONE_WAY')['executed']['violation'] = True
    failed = runner.summarize(bad, timings)
    assert failed['methods']['ONE_WAY']['executed_risk_violations'] == 1
    assert failed['methods']['ONE_WAY']['risk_violations'] == 0
    assert not failed['stage_condition_met']
    # Equal cost against either control defeats the strict full-life condition.
    tied = deepcopy(records)
    for row in tied:
        if row['arm'] == 'ONE_WAY':
            row['spent'] = 0
    assert not runner.summarize(tied, timings)['conditions']['actual_acquisition_saving_vs_one_way']


def test_loaded_scoring_helper_keeps_wait_bounds_zero_without_changing_history(monkeypatch):
    plan = dict(mix=[('SHORT', F(1))], utility_lower=F(2), risk_upper=F(1, 20),
        goal_upper=F(3), goal_impossible=False,
        queries={query: dict(policy='SHORT') for query in ('reward', 'goal', 'risk')},
        query_certificates={query: dict(certified=False) for query in ('reward', 'goal', 'risk')})
    row = dict(life=0, index=3, arm='TWO_WAY', case=dict(stage='A_RETURN'), spent=0,
        initial_plan=plan, terminal_plan=plan, batches=[], model_seconds=0.,
        execution_certified=True, goal_impossible=False, query_certified=False,
        joint_completed=False, budget_exhausted=False, fallback=True, executed_mix=[('WAIT', '1')])
    before = deepcopy(row)
    monkeypatch.setattr(old, 'restored_plan', deepcopy)
    monkeypatch.setattr(old, 'oracle_goal', lambda *args: F(3))
    monkeypatch.setattr(old, 'query_score', lambda *args: {
        query: dict(regret=F(0)) for query in ('reward', 'goal', 'risk')})
    monkeypatch.setattr(old, 'score', lambda active, *args: dict(
        actual_utility=F(0) if active['mix'][0][0] == 'WAIT' else F(3),
        utility_lower=active['utility_lower'], risk_upper=active['risk_upper'], violation=False))
    result = runner.evaluate(row, object())
    assert result['executed']['actual_utility'] == result['executed']['utility_lower'] == 0
    assert result['executed']['risk_upper'] == 0
    assert result['history'][0]['utility_lower'] == 2 and row == before
