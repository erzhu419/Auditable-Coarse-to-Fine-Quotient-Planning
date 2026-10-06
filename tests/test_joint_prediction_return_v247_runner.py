"""Check equal paid prefixes, return-only acquisition, and frozen scoring."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import pytest

from scripts import run_joint_prediction_return_v247 as runner


def test_fresh_return_rotation_and_only_directed_arm_changes_allocator(monkeypatch):
    assert runner.TARGET_BASE == 286000
    assert runner.TARGETS == tuple(range(54, 78))
    assert len(runner.LIVES)*len(runner.ARMS)*len(runner.TARGETS) == 144
    assert runner.arm_order(0, 0) == ('ONE_WAY', 'JOINT_PREDICTION')
    assert runner.arm_order(0, 1) == runner.arm_order(1, 0) == ('JOINT_PREDICTION', 'ONE_WAY')
    assert [runner.TOTAL_BUDGETS[life]-runner.SOURCE_COST-runner.HISTORY_PAID[life]
            for life in runner.LIVES] == [2768, 3248, 4608]
    monkeypatch.setattr(runner.acquisition, 'choose', lambda *args: dict(operator='SHORT_PASS', reason='control'))
    monkeypatch.setattr(runner.query_acquisition, 'choose', lambda *args: dict(operator='RETRY', reason='directed'))
    assert [runner.choose(arm, {}, {}, 0, Counter())['reason'] for arm in runner.ARMS] == ['control', 'directed']


def test_same_initial_state_is_copied_into_isolated_arms_and_history_is_charged(monkeypatch, tmp_path):
    output = tmp_path/'cohort'
    output.mkdir()
    prefix_directory = tmp_path/'prefix'
    prefix_directory.mkdir()
    cases = [dict(context='A', stage='A_RETURN') for _ in range(78)]
    runner.save(prefix_directory/'cases.json', [dict(life=0, cases=cases)])
    runner.save(prefix_directory/'interfaces.json', [dict(life=0, identities=[0]*78, metadata={})])
    common = dict(arm='ONE_WAY', a=dict(pools=[runner.core.empty()]))
    ledger = dict(life=0, source_paid_samples=4608, history_paid_samples=6768, total_prefix_paid_samples=11376)
    monkeypatch.setattr(runner, 'OUTPUT', output)
    monkeypatch.setattr(runner, 'PREFIX_DIRECTORY', prefix_directory)
    monkeypatch.setattr(runner.inheritance, 'load_prefix', lambda *args: {})
    monkeypatch.setattr(runner.inheritance, 'replay_prefix', lambda *args: (common, ledger))
    monkeypatch.setattr(runner.task, 'world', lambda life: (None, [None]*78, None, None))
    monkeypatch.setattr(runner, 'activate_arm_caches', lambda *args: None)
    starts, histories, state_ids = {}, {}, {}

    def target(life, index, case, identity, state, arm, law, work, source_paid, history_paid,
               query_cache, profiles, profile_ids):
        assert state['arm'] == 'ONE_WAY' and source_paid == 4608
        if arm not in starts:
            starts[arm] = deepcopy(state)
            state_ids[arm] = id(state)
        histories.setdefault(arm, []).append(history_paid)
        state['a']['pools'][0]['SHORT_PASS']['DELIVERY'] += 1
        return dict(spent=16, model_seconds=0., acquisition_seconds=0., observation_seconds=0., output_seconds=0.,
            query_certified=True, joint_completed=True)

    monkeypatch.setattr(runner, 'run_target', target)
    artifact = runner.run_life(0)
    assert starts['ONE_WAY'] == starts['JOINT_PREDICTION'] == common
    assert state_ids['ONE_WAY'] != state_ids['JOINT_PREDICTION']
    assert common['a']['pools'][0]['SHORT_PASS']['DELIVERY'] == 0
    assert histories['ONE_WAY'] == histories['JOINT_PREDICTION'] == list(range(6768, 6768+24*16, 16))
    assert artifact['common_prefix_state']['state'] == common
    assert artifact['prefix_ledger'] == ledger
    assert all(state['a']['pools'][0]['SHORT_PASS']['DELIVERY'] == 24
        for state in artifact['final_states']['states'].values())


def test_paired_fresh_draws_stop_at_ready_life_budget_or_member_cap(monkeypatch):
    case = dict(context='A', stage='A_RETURN', operating='high', retry_cost='19/20')
    draws = []

    def make_plan(member, case, state, identity, index, cache, work):
        count = sum(sum(row.values()) for row in member.values())
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
    cpu_clock = iter(range(400))
    monkeypatch.setattr(runner, 'process_time', lambda: next(cpu_clock))
    rows = []
    for arm, stop, history in (('ONE_WAY', 16, 9504), ('JOINT_PREDICTION', 64, 9504),
                               ('JOINT_PREDICTION', 400, 6768)):
        state = dict(a=dict(pools=[runner.core.empty()]), stop_after=stop)
        rows.append(runner.run_target(0, 54, case, 0, state, arm, object(), Counter(),
            4608, history, {}, StringIO(), {}))
    one, budget_limited, cap_limited = rows
    assert one['seeds'] == budget_limited['seeds'] == cap_limited['seeds']
    assert one['seeds']['SHORT_PASS'] == 286000+54*3
    assert draws[0] == draws[1] and draws[1] != draws[2]
    assert one['spent'] == 16 and one['joint_completed']
    assert budget_limited['spent'] == 32 and budget_limited['budget_exhausted']
    assert not budget_limited['joint_completed'] and budget_limited['fallback']
    assert cap_limited['spent'] == 384 and cap_limited['member_cap_exhausted']
    assert not cap_limited['budget_exhausted'] and cap_limited['total_reference_paid_samples'] == 11760
    assert [row['acquisition_seconds'] for row in rows] == [1, 2, 24]
    assert [row['model_seconds'] for row in rows] == [4, 7, 73]


def cohort():
    records = []
    for life in runner.LIVES:
        for arm in runner.ARMS:
            for index in runner.TARGETS:
                records.append(dict(life=life, arm=arm, index=index, stage='A_RETURN',
                    spent=16, query_certified=True, joint_completed=True, execution_certified=True,
                    goal_impossible=False, fallback=False, budget_exhausted=False, model_seconds=1.,
                    history=[dict(false_query_certificates=0, false_execution_certificate=False,
                        false_impossible_certificate=False, violation=False, goal_upper_ok=True, coverage=True)],
                    executed=dict(actual_utility=F(3), violation=False)))
    timings = {scope: {arm: dict.fromkeys(runner.LIVES, .1) for arm in runner.ARMS}
               for scope in ('planning', 'initialization', 'acquisition', 'observation')}
    return records, timings


def test_return_only_conditions_charge_all_prefix_fees_and_allow_cost_tie():
    records, timings = cohort()
    summary = runner.summarize(records, timings)
    assert summary['stage_condition_met'] and len(summary['conditions']) == 5
    assert summary['physical_source_samples'] == 0
    assert summary['inherited_source_samples_charged_per_arm'] == 13824
    assert summary['inherited_target_samples_charged_per_arm'] == 23936
    assert summary['new_environment_observations'] == 144*16
    assert summary['methods']['JOINT_PREDICTION']['total_samples'] == 37760+72*16
    assert summary['methods']['JOINT_PREDICTION']['model_seconds'] == pytest.approx(.6)
    assert summary['methods']['JOINT_PREDICTION']['acquisition_seconds'] == pytest.approx(.3)
    next(row for row in records if row['arm'] == 'JOINT_PREDICTION')['spent'] += 16
    assert not runner.summarize(records, timings)['conditions']['actual_acquisition_nondegrading_vs_one_way']


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
        with gzip.open(output/f'records_life_{life:02d}.jsonl.gz', 'wt') as stream:
            for position, index in enumerate(runner.TARGETS):
                for arm in runner.arm_order(life, position):
                    stream.write(json.dumps(dict(life=life, index=index, arm=arm))+'\n')
        return dict(life=life, cases={}, interfaces={}, prefix_ledger={}, common_prefix_state={},
            final_states=dict(states={}), arm_orders=[], output_seconds=0., life_wall_seconds=1.,
            prefix_replay_seconds=0., prefix_read_seconds=0., prefix_replay_work={},
            profiles=0, work={arm: {} for arm in runner.ARMS},
            timings={scope: dict.fromkeys(runner.ARMS, 0.) for scope in ('planning', 'initialization', 'acquisition', 'observation')},
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
    assert result['records'] == events.count('score') == 144
    assert json.loads((output/'run.json').read_text())['complete']
