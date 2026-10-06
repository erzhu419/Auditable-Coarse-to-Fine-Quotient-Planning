"""Conditional fees, continuous cursors, immutable projections and score barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import io
import json
import pytest

from scripts import run_executable_trajectory_v254 as runner

S, D, R = runner.core.OPERATORS


def evidence(goal=False, risk=False):
    return dict(all_ready=goal and risk, threshold=4320, queries=dict(
        reward=dict(policy='WAIT', certified=True),
        goal=dict(policy='SHORT', certified=goal, comparisons=[dict(other='DETOUR_RETRY', certified=goal)]),
        risk=dict(policy='DETOUR_RETURN', certified=risk, comparisons=[])))


def fake_record(item, row_goal=False, direct_goal=False):
    return dict(deepcopy(item), queries=dict(reward=dict(policy='WAIT'), goal=dict(policy='SHORT'), risk=dict(policy='DETOUR_RETURN')),
        row_joint=dict(case=deepcopy(item['case']), query_evidence=evidence(row_goal, True)),
        trajectory=evidence(direct_goal, True), model_seconds=dict.fromkeys(('point_vectors', 'row_joint', 'trajectory'), 0.), output_seconds=0.)


def fake_artifact(life, records):
    return dict(life=life, records=records, primitive_samples=runner.TOTAL_CAPS[life], source_samples=runner.SOURCE_COST,
        acquisition_samples=runner.TOTAL_CAPS[life]-runner.SOURCE_COST, timings=dict.fromkeys(runner.MODEL_SCOPES, 1.),
        observation_seconds=2., output_seconds=3., worker_wall_seconds=4., cache_statistics={}, work={})


class ScriptedSimulator:
    def __init__(self):
        self.calls = []
        self.phase_steps = Counter()
        self.offsets = Counter()
    def observe(self, phase, identity, operator):
        self.calls.append((phase, identity, operator))
        key = phase, identity, operator
        start = self.offsets[key]
        self.offsets[key] += 1
        self.phase_steps[phase] += 1
        outcome = 'RECOVERY' if operator == D and identity == 0 else 'DELIVERY'
        return dict(seed=1, draw_start=start, draw_end=start+1, outcome=outcome,
            phase_step_index=self.phase_steps[phase])


def test_actual_conditional_costs_tails_and_cursor_continue_across_checkpoints():
    simulator, work = ScriptedSimulator(), Counter()
    states = [runner.core.new_type_state() for _ in range(3)]
    tape, rounds = io.StringIO(), io.StringIO()
    first = runner.sample_segment(0, 0, 7, states, simulator, 0, 0, 0, tape, rounds, work)
    assert (first['step'], first['round_id'], first['cursor']) == (7, 2, 4)
    assert simulator.calls == [('SOURCE', 0, S), ('SOURCE', 0, D), ('SOURCE', 0, R),
        ('SOURCE', 1, S), ('SOURCE', 1, D), ('SOURCE', 2, S), ('SOURCE', 0, S)]
    second = runner.sample_segment(0, 1, 11, states, simulator, first['step'], first['round_id'], first['cursor'], tape, rounds, work)
    third = runner.sample_segment(0, 2, 14, states, simulator, second['step'], second['round_id'], second['cursor'], tape, rounds, work)
    assert (third['step'], third['round_id'], third['cursor']) == (14, 4, 9)
    retained = [json.loads(line) for line in rounds.getvalue().splitlines()]
    assert [row['identity'] for row in retained] == [0, 1, 1, 1]
    assert [row['primitive_steps'] for row in retained] == [[1, 2, 3], [4, 5], [8, 9], [12, 13]]
    assert all(row['outcomes'][R] is None for row in retained[1:])
    assert work['standalone_S_tails'] == 5 and sum(len(state['rounds']) for state in states) == 4
    primitive = [json.loads(line) for line in tape.getvalue().splitlines()]
    assert len(primitive) == 14 and [row['step_index'] for row in primitive] == list(range(1, 15))
    assert [row['phase_step_index'] for row in primitive if row['phase'] == 'ACQUISITION'] == list(range(1, 8))
    assert sum(sum(counts.values()) for state in states for counts in state['native_counts'].values()) == 14


def test_simulator_phase_seeds_and_acquisition_offsets_are_not_reset(monkeypatch):
    seen = []
    def fake_draw(generator, law, operator, increments, amount, work, progress):
        seen.append((law, operator, generator.random()))
        increments['DELIVERY'] += 1
        progress['draw_end'] += 1
    monkeypatch.setattr(runner, 'draw', fake_draw)
    simulator = runner.PrimitiveSimulator(2, ['law0', 'law1', 'law2'], Counter())
    source = simulator.observe('SOURCE', 1, S)
    first = simulator.observe('ACQUISITION', 1, S)
    simulator.observe('ACQUISITION', 2, D)
    second = simulator.observe('ACQUISITION', 1, S)
    assert source['seed'] == 299000+(2*3+1)*3
    assert first['seed'] == second['seed'] == 300000+(2*3+1)*3
    assert first['draw_start'] == 0 and second['draw_start'] == 1 and second['draw_end'] == 2
    rng = runner.random.Random(first['seed'])
    assert seen[1][2] == rng.random() and seen[3][2] == rng.random()
    assert all(operator != R for _, operator, _ in seen)
    assert second['phase_step_index'] == 3


def test_qualify_uses_same_raw_point_policy_for_two_methods_and_separates_retention(monkeypatch):
    state = runner.core.new_type_state()
    runner.core.observe_round(state, {S:'DELIVERY', D:'RECOVERY', R:'LOST'}, 1)
    for _ in range(10):
        runner.core.observe_tail_s(state, 'LOST')
    item = dict(life=0, kind='CHECKPOINT', checkpoint_label='SOURCE', checkpoint_samples=4608,
        identity=0, cost_index=0, index=None, case=dict(operating='low', retry_cost='17/20'))
    received = []
    def row(counts, case, queries, cache, work):
        received.append(('row', deepcopy(counts), deepcopy(queries)))
        return evidence(False, False)
    def direct(rounds, case, queries, cache, work):
        received.append(('direct', deepcopy(rounds), deepcopy(queries)))
        return evidence(True, True)
    monkeypatch.setattr(runner.row_joint, 'certificates', row)
    monkeypatch.setattr(runner.core, 'trajectory_certificates', direct)
    clocks = iter((0., 1., 2., 3., 4., 5.))
    monkeypatch.setattr(runner, 'process_time', lambda: next(clocks))
    walls = iter((10., 17.))
    monkeypatch.setattr(runner, 'perf_counter', lambda: next(walls))
    monkeypatch.setattr(runner, 'retain_plan', lambda plan, stream, ids: deepcopy(plan))
    record = runner.qualify(item, state, {}, {}, Counter(), io.StringIO(), {})
    assert received[0][2] == received[1][2] == record['queries']
    assert record['queries']['goal']['policy'] == 'SHORT'
    assert received[0][1][S] == dict(DELIVERY=1, LOST=10) and len(received[1][1]) == 1
    assert record['model_seconds'] == dict(point_vectors=1., row_joint=1., trajectory=1.)
    assert record['output_seconds'] == 7. and record['native_n_by_operator'][R] == 1


def test_public_roster_and_terminal_projection_do_not_recompute_proofs(monkeypatch, tmp_path):
    worlds = {life: runner.task.world(life) for life in runner.LIVES}
    roster = runner.public_roster(worlds)
    assert len(roster) == 180 and Counter(item['kind'] for item in roster) == dict(CHECKPOINT=108, RETURN_PROJECTION=72)
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path)
    monkeypatch.setattr(runner, 'activate_cold_caches', lambda: {})
    calls, sample_args = [], []
    def sampling(life, segment, cap, states, simulator, step, round_id, cursor, tape, rounds, work):
        sample_args.append((segment, step, round_id, cursor, id(simulator)))
        for state in states:
            if not state['rounds']:
                runner.core.observe_round(state, {S:'DELIVERY', D:'DELIVERY', R:None}, 1)
        return dict(step=cap, round_id=round_id+1, cursor=cursor+4,
            observation_seconds=0., model_seconds=0., output_seconds=0.)
    def qualify(item, state, row_cache, score_cache, work, stream, ids):
        calls.append((item['checkpoint_label'], item['identity'], item['cost_index']))
        return fake_record(item, row_goal=True, direct_goal=True)
    monkeypatch.setattr(runner, 'sample_segment', sampling)
    monkeypatch.setattr(runner, 'qualify', qualify)
    artifact = runner.run_life(0, worlds[0][1][:3], [item for item in roster if item['life'] == 0])
    assert len(calls) == 36 and len(artifact['records']) == 60
    assert [row[:4] for row in sample_args] == [(0,0,0,0), (1,4608,1,4), (2,7680,2,8)]
    assert len({row[4] for row in sample_args}) == 1
    full = {(row['identity'],row['cost_index']):row for row in artifact['records']
        if row['kind']=='CHECKPOINT' and row['checkpoint_label']=='FULL_CAP'}
    for projected in artifact['records'][36:]:
        original = full[projected['identity'],projected['cost_index']]
        assert projected['trajectory'] == original['trajectory']
        assert projected['row_joint']['query_evidence'] == original['row_joint']['query_evidence']
        assert projected['row_joint']['case'] == worlds[0][0][projected['index']]
        assert not any(projected['model_seconds'].values())
        assert original['case']['stage'] == 'QUERY_QUALIFICATION'


def test_summary_charges_one_common_tape_and_requires_terminal_net_goal_gain_with_no_false_proof():
    records = []
    for life in runner.LIVES:
        for label in runner.LABELS:
            item = dict(life=life, kind='CHECKPOINT', checkpoint_label=label, identity=0, cost_index=0, index=None, case={})
            records.append(fake_record(item, False, True))
        for index in (54, 55):
            item = dict(life=life, kind='RETURN_PROJECTION', checkpoint_label='FULL_CAP', identity=0, cost_index=0, index=index, case={})
            records.append(fake_record(item, index==54, index==55))
    artifacts = [fake_artifact(life, []) for life in runner.LIVES]
    scores = [dict(false_certificates=dict.fromkeys(runner.METHODS, 0)) for _ in records]
    summary = runner.summarize(records, scores, artifacts)
    assert summary['physical_observations'] == 48384 and summary['physical_source_samples'] == 13824
    assert summary['physical_acquisition_samples'] == 34560 and summary['model_seconds'] == 12.
    assert [row['total_samples'] for row in summary['fee_ledger']] == list(runner.TOTAL_CAPS)
    assert summary['terminal_paired']['goal']['gains'] == summary['terminal_paired']['goal']['losses'] == 3
    assert not summary['positive_qualification_signal']  # checkpoint improvements and terminal ties do not qualify.
    records[-2]['row_joint']['query_evidence']['queries']['goal']['certified'] = False
    summary = runner.summarize(records, scores, artifacts)
    assert summary['positive_qualification_signal']
    scores[0]['false_certificates']['ROW_JOINT'] = 1
    assert not runner.summarize(records, scores, artifacts)['positive_qualification_signal']


def test_all_180_pairs_are_frozen_before_truth_scoring(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path/'output')
    calls, completed = [], []
    monkeypatch.setattr(runner, 'capture', lambda: calls.append('capture'))
    original_world = runner.task.world
    worlds = {life: original_world(life) for life in runner.LIVES}
    monkeypatch.setattr(runner.task, 'world', lambda life: worlds[life])
    class Future:
        def __init__(self, life, roster):
            self.life, self.roster = life, roster
        def result(self):
            completed.append(self.life)
            return fake_artifact(self.life, [fake_record(item, True, True) for item in self.roster])
    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 3
        def __enter__(self):
            return self
        def submit(self, function, life, laws, roster):
            assert calls == ['capture'] and function is runner.run_life
            assert laws == worlds[life][1][:3] and len(roster) == 60
            frozen = json.loads((runner.OUTPUT/'run.json').read_text())
            assert not frozen['complete'] and frozen['phases'] == ['protocol_and_roster_frozen', 'source_captured']
            assert len(json.loads((runner.OUTPUT/'public_roster.json').read_text())) == 180
            return Future(life, roster)
        def __exit__(self, *args):
            calls.append('executor_exit')
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Executor)
    scored = []
    def score(record, law):
        assert completed == [0,1,2] and calls == ['capture', 'executor_exit']
        frozen = json.loads((runner.OUTPUT/'run.json').read_text())
        assert frozen['phases'][-1] == 'all_180_decision_pairs_frozen' and not frozen['complete']
        assert law == worlds[record['life']][1][record['identity']]
        scored.append((record['life'], record['kind'], record['index']))
        return dict(false_certificates=dict.fromkeys(runner.METHODS, 0))
    monkeypatch.setattr(runner, 'score_record', score)
    summary = runner.run()
    assert len(scored) == summary['records'] == 180
    assert summary['checkpoint_pairs'] == 108 and summary['terminal_pairs'] == 72
    final = json.loads((runner.OUTPUT/'run.json').read_text())
    assert final['complete'] and final['phases'][-2:] == ['posthoc_truth_scored', 'complete']
    assert final['trajectory_threshold'] == 4320 and final['row_threshold'] == 960


def test_false_certificate_scoring_uses_retained_queries_and_both_methods(monkeypatch):
    record = fake_record(dict(life=0,kind='CHECKPOINT',checkpoint_samples=4608,identity=0,cost_index=0,index=None,case={}), True, False)
    seen = []
    def truth(queries, law, case):
        seen.append((queries,law,case))
        return {q:dict(regret=F(1,10) if q=='goal' else F(0)) for q in queries}
    monkeypatch.setattr(runner, 'query_score', truth)
    scored = runner.score_record(record, 'private_law')
    assert scored['false_certificates'] == dict(ROW_JOINT=1,TRAJECTORY=0)
    assert len(seen) == 1 and seen[0][0] is record['queries']
