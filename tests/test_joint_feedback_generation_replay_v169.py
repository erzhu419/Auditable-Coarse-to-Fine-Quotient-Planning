"""Gzip lifecycle integration with synthetic physics and zero environment draws."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

from scripts import analyze_controlled_predictive_joint_feedback_generation_v169 as audit
from acfqp.science.controlled_predictive_joint_feedback_generation_v169 import mutate, executable

ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 2]+[0]*14


def write_trace(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt') as output:
        for row in rows:
            output.write(json.dumps(row)+'\n')


def result(setup=None):
    return dict(score=0, steps=4, status='LOST', components=[0., 1., 0.], utility=-1.,
                environment_counts=dict(sampled_transitions=4), policy_counts={},
                policy_counts_by_query=dict(risk1={}, risk8={}),
                program_setup_counts=setup or {}, decision_seconds=0.)


def test_source_lifecycle_reads_four_gzip_games_and_only_SOURCE_cost(monkeypatch):
    directory = ROOT/'reports/v169_runtime_tmp/replay_fixtures/source'
    directory.mkdir(parents=True, exist_ok=True)
    rows, roots = [], []
    boards = [list(BOARD) for _ in range(4)]
    for replica in range(4):
        row = dict(life=0, query='risk1', replica=replica, phase='TRAIN_SOURCE',
                   seed=16910000000+replica, source_id=f'TRAIN_SOURCE:0:risk1:{replica}',
                   initial_board=list(BOARD), actions=['DOWN']*4, result=result())
        rows.append(row)
        roots.extend(audit.prior.expected_roots(boards, row))
    write_trace(directory/'source_games.jsonl.gz', rows)
    lifecycle = dict(phase='TRAIN_SOURCE', life=0, source_trace='source_games.jsonl.gz',
                     roots=roots, physical_games=4, environment_counts=dict(sampled_transitions=16),
                     policy_counts={}, statuses=dict(LOST=4), teacher_bank={})
    seen = []

    def replay(row, source):
        seen.append(row['replica'])
        assert source == {}
        return dict(synthetic_physics=True), 0, deepcopy(boards)

    monkeypatch.setattr(audit.prior.prior, 'replay_game', replay)
    monkeypatch.setattr(audit.prior, 'teacher_checks', lambda *args: {})
    task = (str(directory), 'TRAIN_SOURCE', lifecycle, {}, [], [])
    checked = audit.replay_lifecycle(task)
    assert seen == [0, 1, 2, 3] and all(checked['checks'].values())
    assert checked['roots'] == roots and len(checked['roots']) == 4
    assert set(checked['route_costs']) == {'SOURCE'}
    assert checked['costs']['physical_games'] == checked['route_costs']['SOURCE']['physical_games'] == 4
    assert checked['route_costs']['SOURCE']['environment_counts']['sampled_transitions'] == 16
    assert 'rule_before' not in lifecycle and 'rule_after' not in lifecycle
    lifecycle['roots'] = deepcopy(roots)
    lifecycle['roots'][0]['source_step'] += 1
    failed = audit.replay_lifecycle(task)
    assert not failed['checks']['selected_source_roots']
    assert failed['checks']['four_source_games']


def test_branch_lifecycle_binds_mutant_program_shared_first_spawn_None_and_route_cost(monkeypatch):
    directory = ROOT/'reports/v169_runtime_tmp/replay_fixtures/branch'
    directory.mkdir(parents=True, exist_ok=True)
    root = dict(root_id='TRAIN_SOURCE:0:risk1:0:0', phase='TRAIN_SOURCE', life=0,
                query='risk1', replica=0, slot=0, board=list(BOARD))
    parents = [dict(first_action='DOWN', probe_action='LEFT', true_suffix=['DOWN', 'LEFT', 'RIGHT'],
                    false_suffix=['RIGHT', 'LEFT', 'DOWN']),
               dict(first_action='UP', probe_action='LEFT', true_suffix=['DOWN', 'LEFT', 'RIGHT'],
                    false_suffix=['RIGHT', 'LEFT', 'DOWN'])]
    candidates = {slot['candidate_slot']: slot['program'] for slot in mutate(parents)}
    seed = audit.branch_seed('G1', root, 0, 3)
    plans, raw = [], []
    routes = [('H2', None, None)]+[(arm, slot, observed) for slot, observed in ((8, True), (9, None)) for arm in ('A', 'B')]
    for route, candidate_slot, observed in routes:
        mode = 'H2' if route == 'H2' else f'P{candidate_slot}_{route}'
        compiled = None if route == 'H2' else executable(candidates[candidate_slot], route)
        plan = dict(branch_id=f'G1:{root["root_id"]}:fold3:0:{mode}', phase='G1', heldout_life=3,
                    root_id=root['root_id'], life=0, query='risk1', replica=0, slot=0, suffix=0,
                    route=route, mode=mode, arm='H2' if route == 'H2' else 'FEEDBACK',
                    candidate_slot=candidate_slot, seed=seed, program=compiled)
        plans.append(plan)
        row = {key: deepcopy(value) for key, value in plan.items() if key != 'program'}
        word = [] if compiled is None else [compiled['first_action']]+(compiled['true_suffix'] if observed is not None else [])
        row.update(root_board=list(BOARD), actions=['DOWN', 'LEFT', 'DOWN', 'RIGHT'], scores=[0]*4,
                   choices=[dict(afterstate=list(BOARD)) for _ in range(4)],
                   spawned_cells=[2, 3, 4, 5], spawned_ranks=[1]*4,
                   module=dict(program=deepcopy(compiled), arm=plan['arm'], predicate=observed,
                               actual_word=word, prefix_steps=0 if observed is None else 4,
                               attempts=0 if route == 'H2' else 1 if observed is None else 4,
                               exit_reason='baseline' if route == 'H2' else 'illegal' if observed is None else 'budget',
                               exit_step=0 if observed is None else 4),
                   result=result(None if route == 'H2' else dict(program_action_transports=8)))
        raw.append(row)

    def persist():
        write_trace(directory/'branches.jsonl.gz', raw)
        compact = []
        for row in raw:
            current = {key: deepcopy(row[key]) for key in plans[0] if key != 'program'}
            current.update({key: deepcopy(row['result'][key]) for key in ('score', 'steps', 'status', 'components', 'utility')})
            current['module'] = deepcopy(row['module'])
            compact.append(current)
        (directory/'outcomes.json').write_text(json.dumps(compact)+'\n')

    persist()
    lifecycle = dict(phase='G1', life=0, branch_trace='branches.jsonl.gz', outcomes_ref='outcomes.json',
                     rule_before={}, rule_after={}, physical_branches=5,
                     environment_counts=dict(sampled_transitions=20), policy_counts={},
                     program_setup_counts=dict(program_action_transports=32), statuses=dict(LOST=5), teacher_bank={})
    seen = []

    def replay(row, max_steps):
        seen.append((row['candidate_slot'], row['route']))
        assert max_steps == 2000
        return dict(synthetic_physics=True), 0

    monkeypatch.setattr(audit.feedback, 'replay_branch', replay)
    monkeypatch.setattr(audit.prior, 'teacher_checks', lambda *args: {})
    task = (str(directory), 'G1', lifecycle, dict(rule={}), plans, [root])
    checked = audit.replay_lifecycle(task)
    assert len(seen) == 5 and all(checked['checks'].values())
    assert checked['costs']['physical_branches'] == 5
    assert set(checked['route_costs']) == {'H2', 'A', 'B'}
    assert [checked['route_costs'][route]['physical_branches'] for route in ('H2', 'A', 'B')] == [1, 2, 2]
    assert checked['route_costs']['A']['environment_counts']['sampled_transitions'] == 8
    assert checked['route_costs']['B']['program_setup_counts']['program_action_transports'] == 16
    null_pair = [{**row['result'], 'module': deepcopy(row['module'])} for row in raw[3:]]
    assert audit.paired_predicate_valid(*null_pair)
    null_pair[1]['module']['prefix_steps'] += 1
    assert not audit.paired_predicate_valid(*null_pair)

    plans[1]['program']['first_action'] = 'UP'
    frozen_failure = audit.replay_lifecycle(task)
    assert any(not valid for name, valid in frozen_failure['checks'].items() if name.startswith('frozen_program'))
    assert frozen_failure['checks']['shared_first_prefix_and_predicate']
    plans[1]['program'] = deepcopy(raw[1]['module']['program'])
    raw[2]['spawned_cells'][0] += 1
    persist()
    prefix_failure = audit.replay_lifecycle(task)
    assert not prefix_failure['checks']['shared_first_prefix_and_predicate']
    assert all(valid for name, valid in prefix_failure['checks'].items() if name.startswith('compact_matches_trace'))
