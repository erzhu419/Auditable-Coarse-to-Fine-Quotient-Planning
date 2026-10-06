"""Check the one-variable arm switch, paid stopping, and scoring barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import pytest

from scripts import run_query_allocation_lifecycle_v245 as runner


def test_fresh_streams_rotation_and_new_arm_uses_one_way_state(monkeypatch):
    assert runner.SOURCE_BASE == 282000 and runner.TARGET_BASE == 283000
    assert len(runner.LIVES)*len(runner.ARMS)*len(runner.TARGETS) == 648
    assert runner.arm_order(0, 0) == ('ONE_WAY', 'QUERY_DIRECTED', 'REBUILD')
    assert runner.arm_order(0, 1) == ('QUERY_DIRECTED', 'REBUILD', 'ONE_WAY')
    assert runner.arm_order(1, 1) == ('REBUILD', 'ONE_WAY', 'QUERY_DIRECTED')
    monkeypatch.setattr(runner.core, 'prepare', lambda anchors, life, arm, work: dict(arm=arm))
    assert [runner.prepare_state([], 0, arm, Counter())['arm'] for arm in runner.ARMS] == [
        'ONE_WAY', 'ONE_WAY', 'REBUILD']


def test_only_directed_arm_changes_allocator(monkeypatch):
    monkeypatch.setattr(runner.acquisition, 'choose', lambda *args: dict(operator='SHORT_PASS', reason='control'))
    monkeypatch.setattr(runner.query_acquisition, 'choose', lambda *args: dict(operator='RETRY', reason='directed'))
    assert [runner.choose(arm, {}, {}, 0, Counter())['reason'] for arm in runner.ARMS] == [
        'control', 'directed', 'control']


def test_paid_prefixes_remain_separate_and_stop_at_ready_or_life_budget(monkeypatch):
    case = dict(context='A', stage='A', operating='high', retry_cost='19/20')
    draws = []

    def make_plan(member, case, state, identity, index, cache, work):
        count = sum(sum(row.values()) for row in member.values())
        cache.setdefault('counts', []).append(count)
        ready = count >= state['stop_after']
        return dict(case=case, mix=[('WAIT', F(1))], utility_lower=F(2 if ready else 0),
            goal_impossible=False, query_ready=ready,
            query_evidence=dict(queries={'reward': dict(policy='WAIT', certified=True)},
                all_ready=ready, threshold=960))

    def draw(generator, law, operator, increments, number, work, progress):
        draws.append(tuple(generator.random() for _ in range(number)))
        increments['DELIVERY'] += number
        progress['draw_end'] += number

    monkeypatch.setattr(runner.core, 'make_plan', make_plan)
    monkeypatch.setattr(runner, 'draw', draw)
    monkeypatch.setattr(runner, 'choose', lambda *args: dict(operator='SHORT_PASS', reason='synthetic'))
    rows, caches = [], []
    for arm, stop in (('ONE_WAY', 16), ('QUERY_DIRECTED', 64)):
        cache = {}
        state = dict(a=dict(pools=[runner.core.empty()]), stop_after=stop)
        rows.append(runner.run_target(0, 3, case, 0, state, arm, object(), Counter(),
            3456, 9504, cache, StringIO(), {}))
        caches.append(cache)
    one, directed = rows
    assert one['seeds'] == directed['seeds']
    assert draws[0] == draws[1] and draws[1] != draws[2]
    assert one['spent'] == 16 and one['joint_completed']
    assert directed['spent'] == 32 and not directed['joint_completed'] and directed['fallback']
    assert directed['life_budget_remaining_after'] == 0 and directed['budget_exhausted']
    assert one['pooled_after']['SHORT_PASS']['DELIVERY'] == 16
    assert directed['pooled_after']['SHORT_PASS']['DELIVERY'] == 32
    assert caches == [{'counts': [0, 16]}, {'counts': [0, 16, 32]}]


def cohort():
    records = []
    for life in runner.LIVES:
        for arm in runner.ARMS:
            for index in runner.TARGETS:
                stage = 'A' if index < 30 else 'B' if index < 54 else 'A_RETURN'
                records.append(dict(life=life, arm=arm, index=index, stage=stage,
                    spent=16 if arm == 'REBUILD' else 0, query_certified=True,
                    joint_completed=True, execution_certified=True, goal_impossible=False,
                    fallback=False, budget_exhausted=False, model_seconds=1.,
                    history=[dict(false_query_certificates=0, false_execution_certificate=False,
                        false_impossible_certificate=False, violation=False, goal_upper_ok=True, coverage=True)],
                    executed=dict(actual_utility=F(3), violation=False)))
    timings = {scope: {arm: dict.fromkeys(runner.LIVES, .1) for arm in runner.ARMS}
               for scope in ('planning', 'initialization', 'begin_b', 'observation')}
    return records, timings


def test_frozen_conditions_allow_one_way_cost_tie_but_require_rebuild_saving():
    records, timings = cohort()
    summary = runner.summarize(records, timings)
    assert summary['stage_condition_met'] and len(summary['conditions']) == 11
    assert summary['records'] == 648 and summary['physical_source_samples'] == 13824
    assert summary['methods']['QUERY_DIRECTED']['model_seconds'] == pytest.approx(.9)
    assert summary['conditions']['actual_acquisition_nondegrading_vs_one_way']
    tied = deepcopy(records)
    for row in tied:
        if row['arm'] == 'REBUILD':
            row['spent'] = 0
    assert not runner.summarize(tied, timings)['conditions']['actual_acquisition_saving_vs_rebuild']
    worse = deepcopy(records)
    next(row for row in worse if row['arm'] == 'QUERY_DIRECTED')['spent'] = 16
    assert not runner.summarize(worse, timings)['conditions']['actual_acquisition_nondegrading_vs_one_way']


@pytest.mark.parametrize('error', ['false_goal_upper', 'executed_risk', 'planned_risk'])
def test_conditions_reject_goal_upper_and_both_risk_error_scopes(error):
    records, timings = cohort()
    row = next(row for row in records if row['arm'] == 'ONE_WAY')
    if error == 'false_goal_upper':
        row['history'][0]['goal_upper_ok'] = False
    elif error == 'executed_risk':
        row['executed']['violation'] = True
    else:
        row['history'][0]['violation'] = True
    assert not runner.summarize(records, timings)['conditions']['valid_certificates_and_execution']


def test_parent_completes_all_lives_and_writes_freeze_before_any_scoring(monkeypatch, tmp_path):
    output, events = tmp_path/'cohort', []
    monkeypatch.setattr(runner, 'OUTPUT', output)
    monkeypatch.setattr(runner, 'prerequisites', lambda: dict(admitted=True))
    monkeypatch.setattr(runner, 'capture', lambda: events.append('capture'))

    def artifact(life):
        output.mkdir(exist_ok=True)
        with gzip.open(output/f'records_life_{life:02d}.jsonl.gz', 'wt') as stream:
            for position, index in enumerate(runner.TARGETS):
                for arm in runner.arm_order(life, position):
                    stream.write(json.dumps(dict(life=life, index=index, arm=arm))+'\n')
        return dict(life=life, source_records=[], source_evidence={}, cases={}, interfaces={},
            final_states=dict(states={arm: dict(return_merge=None) for arm in runner.ARMS}),
            arm_orders=[], output_seconds=0., source_seconds=0., source_work={}, life_wall_seconds=1.,
            profiles=0, work={arm: {} for arm in runner.ARMS},
            timings={scope: dict.fromkeys(runner.ARMS, 0.)
                for scope in ('planning', 'initialization', 'begin_b', 'observation')},
            normalizer_cache_statistics={arm: {} for arm in runner.ARMS})

    class Future:
        def __init__(self, life):
            self.life = life

        def result(self):
            assert events[:4] == ['capture', 'submit0', 'submit1', 'submit2']
            events.append('finish'+str(self.life))
            return artifact(self.life)

    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 3

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append('workers_exited')

        def submit(self, operation, life):
            assert operation is runner.run_life
            assert json.loads((output/'run.json').read_text())['phases'] == ['protocol_frozen']
            events.append('submit'+str(life))
            return Future(life)

    def evaluate(row, law):
        assert events[4:8] == ['finish0', 'finish1', 'finish2', 'workers_exited']
        assert json.loads((output/'run.json').read_text())['phases'] == ['protocol_frozen', 'all_decisions_frozen']
        events.append('score')
        return row

    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Executor)
    monkeypatch.setattr(runner.task, 'world', lambda life: (None, [None]*78, None, None))
    monkeypatch.setattr(runner, 'evaluate', evaluate)
    monkeypatch.setattr(runner, 'summarize', lambda records, timings: dict(records=len(records)))
    result = runner.run()
    assert result['records'] == events.count('score') == 648
    assert json.loads((output/'run.json').read_text())['complete']
