"""Real gzip-reader integration with synthetic replay and teacher callbacks."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

from scripts import analyze_controlled_predictive_consequence_generation_v168 as audit

ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 2]+[0]*14


def write_trace(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt') as output:
        for row in rows:
            output.write(json.dumps(row)+'\n')


def result(steps=4, setup=None):
    return dict(score=0, steps=steps, status='LOST', components=[0., 1., 0.], utility=-1.,
        environment_counts=dict(sampled_transitions=steps), policy_counts={},
        policy_counts_by_query=dict(risk1={}, risk8={}), program_setup_counts=setup or {},
        decision_seconds=0.)


def test_source_lifecycle_reads_gzip_roots_and_SOURCE_cost_without_branch_rule_keys(monkeypatch):
    directory = ROOT/'reports/v168_runtime_tmp/replay_fixtures/source'
    directory.mkdir(parents=True, exist_ok=True)
    rows, roots = [], []
    boards = [list(BOARD) for _ in range(4)]
    for replica in range(4):
        row = dict(life=0, query='risk1', replica=replica, phase='TRAIN_SOURCE',
            seed=16810000000+replica, source_id=f'TRAIN_SOURCE:0:risk1:{replica}',
            actions=['UP']*4, initial_board=list(BOARD), result=result())
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
    report = audit.replay_lifecycle((str(directory), 'TRAIN_SOURCE', lifecycle, {}, [], []))
    assert seen == [0, 1, 2, 3]
    assert all(report['checks'].values())
    assert report['roots'] == roots and len(roots) == 4
    assert report['costs']['physical_games'] == report['route_costs']['SOURCE']['physical_games'] == 4
    assert report['costs']['environment_counts']['sampled_transitions'] == 16
    assert report['route_costs']['SOURCE']['environment_counts']['sampled_transitions'] == 16
    assert sum(cost['physical_games'] for cost in report['route_costs'].values()) == 4
    assert 'rule_before' not in lifecycle and 'rule_after' not in lifecycle


def test_branch_lifecycle_binds_compact_metadata_program_slots_and_CONS_cost(monkeypatch):
    directory = ROOT/'reports/v168_runtime_tmp/replay_fixtures/branch'
    directory.mkdir(parents=True, exist_ok=True)
    root = dict(root_id='TRAIN_SOURCE:0:risk1:0:0', phase='TRAIN_SOURCE', life=0,
        query='risk1', replica=0, slot=0, board=list(BOARD))
    program = ['DOWN', 'LEFT', 'RIGHT', 'UP']
    plan = dict(branch_id='G1:synthetic:CONS_W7', phase='G1', heldout_life=3,
        root_id=root['root_id'], life=0, query='risk1', replica=0, slot=0,
        suffix=0, route='CONS', mode='CONS_W7', candidate_slot=7, seed=16823000000,
        program=program)
    raw = {key: deepcopy(value) for key, value in plan.items() if key != 'program'}
    raw.update(root_board=list(BOARD), module=dict(program=deepcopy(program)),
               result=result(setup=dict(program_action_transports=4)))
    compact = {key: deepcopy(value) for key, value in plan.items() if key != 'program'}
    compact.update({key: deepcopy(raw['result'][key]) for key in ('score', 'steps', 'status', 'components', 'utility')})
    compact['module'] = deepcopy(raw['module'])
    write_trace(directory/'branches.jsonl.gz', [raw])
    (directory/'outcomes.json').write_text(json.dumps([compact])+'\n')
    lifecycle = dict(phase='G1', life=0, branch_trace='branches.jsonl.gz', outcomes_ref='outcomes.json',
        rule_before={}, rule_after={}, physical_branches=1,
        environment_counts=dict(sampled_transitions=4), policy_counts={},
        program_setup_counts=dict(program_action_transports=4), statuses=dict(LOST=1), teacher_bank={})
    seen = []

    def replay(row, max_steps):
        seen.append((row['slot'], row['candidate_slot']))
        assert max_steps == 2000
        return dict(synthetic_physics=True), 0

    monkeypatch.setattr(audit.prior, 'replay_branch', replay)
    monkeypatch.setattr(audit.prior, 'teacher_checks', lambda *args: {})
    report = audit.replay_lifecycle((str(directory), 'G1', lifecycle, dict(rule={}), [plan], [root]))
    assert seen == [(0, 7)]
    assert all(report['checks'].values())
    assert report['costs']['physical_branches'] == report['route_costs']['CONS']['physical_branches'] == 1
    assert report['route_costs']['CONS']['environment_counts']['sampled_transitions'] == 4
    assert report['route_costs']['CONS']['program_setup_counts']['program_action_transports'] == 4
    assert sum(cost['physical_branches'] for cost in report['route_costs'].values()) == 1
    assert compact['slot'] == 0 and compact['candidate_slot'] == 7
