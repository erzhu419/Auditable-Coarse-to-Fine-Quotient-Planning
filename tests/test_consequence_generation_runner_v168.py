"""Acquisition, paired slots and the final-program/EVAL boundary without sampling."""
from copy import deepcopy
import gzip
import json

import pytest

from scripts import run_controlled_predictive_consequence_generation_v168 as runner


def roots(phase):
    return [dict(root_id=f'{phase}:{life}:risk1:{replica}:{slot}', phase=phase,
                 life=life, query='risk1', replica=replica, slot=slot, board=[1, 2]+[0]*14)
            for life in range(4) for replica in range(4 if phase == 'EVAL_SOURCE' else 2) for slot in range(2)]


def frequencies():
    return [dict(heldout_life=life, source_frequencies=[
        dict(word=['DOWN', 'LEFT', 'RIGHT', 'UP'], frequency=10),
        dict(word=['LEFT', 'DOWN', 'UP', 'RIGHT'], frequency=5)],
        complete=True, issues=[]) for life in range(4)]


def test_fixed_phase_rosters_pair_all_slots_and_exclude_heldout_roots():
    train = roots('TRAIN_SOURCE'); initial = runner.phase_cells(frequencies(), None, 'G1')
    prior_seeds = set()
    for phase, count in (('G1', 5088), ('G2', 5088), ('FINAL', 960), ('EVAL', 1536)):
        cells = deepcopy(initial)
        for cell in cells:
            cell['selected_parents'] = deepcopy(cell['parents'][:1] if phase == 'EVAL' else cell['parents'])
        if phase == 'FINAL': cells = runner.phase_cells(frequencies(), cells, 'FINAL')
        plan = runner.branch_roster(roots('EVAL_SOURCE') if phase == 'EVAL' else train, cells, phase)
        assert len(plan) == len({row['branch_id'] for row in plan}) == count
        assert all((row['heldout_life'] == row['life']) == (phase == 'EVAL') for row in plan)
        groups = {}
        for row in plan:
            groups.setdefault((row['root_id'], row['heldout_life'], row['suffix']), []).append(row)
        assert all(len({row['seed'] for row in group}) == 1 and group[0]['mode'] == 'H2' for group in groups.values())
        seeds = {row['seed'] for row in plan}
        assert not prior_seeds.intersection(seeds); prior_seeds.update(seeds)
        expected = 53 if phase in ('G1', 'G2') else 5 if phase == 'FINAL' else 3
        assert all(len(group) == expected for group in groups.values())
    source_seeds = {runner.source_seed(phase, life, replica) for phase in ('TRAIN_SOURCE', 'EVAL_SOURCE') for life in range(4) for replica in range(4)}
    assert len(source_seeds) == 32 and not prior_seeds.intersection(source_seeds)


def test_worker_binds_frozen_word_and_keeps_root_and_candidate_slots(monkeypatch, tmp_path):
    train = roots('TRAIN_SOURCE'); cells = runner.phase_cells(frequencies(), None, 'G1')
    plans = runner.branch_roster(train, cells, 'G1')[:2]
    calls = []
    class Rule:
        @classmethod
        def from_payload(cls, payload): return cls()
        def to_payload(self): return {}
    def branch(board, bank, rule, query, program, seed, max_steps, p_four):
        calls.append((program, seed, max_steps, p_four))
        return dict(root_board=board, module=dict(program=program), result=dict(
            score=2048, steps=3, status='WON', components=[1., 0., 1.], utility=2.,
            environment_counts={'sampled_transitions':3}, policy_counts={}, program_setup_counts={}))
    monkeypatch.setattr(runner, 'LearnedDynamics', Rule)
    monkeypatch.setattr(runner, 'branch_roster', lambda *args: plans)
    monkeypatch.setattr(runner.prior, 'teachers', lambda *args: ({'risk1':None, 'risk8':None}, {}, {}, {}))
    monkeypatch.setattr(runner.prior, 'finish_teachers', lambda *args: None)
    monkeypatch.setattr(runner, 'run_branch', branch)
    record = runner.branch_lifecycle(dict(life=0, rule={}), 'G1', train, cells, tmp_path)
    assert calls == [(None, plans[0]['seed'], 2000, .1), (plans[1]['program'], plans[1]['seed'], 2000, .1)]
    with gzip.open(tmp_path/record['branch_trace'], 'rt') as trace: rows = [json.loads(line) for line in trace]
    assert all(all(row[key] == value for key, value in plan.items() if key != 'program') for row, plan in zip(rows, plans))
    outcomes = json.loads((tmp_path/record['outcomes_ref']).read_text())
    assert [row['candidate_slot'] for row in outcomes] == [None, 0]
    assert record['physical_branches'] == 2 and record['environment_counts'] == {'sampled_transitions':6}


@pytest.mark.parametrize('stop_phase', [None, 'G1', 'FINAL'])
def test_final_programs_are_frozen_before_eval_acquisition_and_incomplete_stops(monkeypatch, tmp_path, stop_phase):
    directory = tmp_path/'run'; events = []
    monkeypatch.setattr(runner, 'extract_source', lambda: dict(snapshots=[dict(life=life) for life in range(4)], cost_refs=[]))
    monkeypatch.setattr(runner, 'snapshot_code', lambda folder: 0)
    monkeypatch.setattr(runner, 'source_frequencies', lambda rows, heldout: frequencies()[heldout])
    monkeypatch.setattr(runner.prior, 'read_rows', lambda path: [])
    monkeypatch.setattr(runner, 'summarize_eval', lambda roots, rows: dict(complete=True))
    def execute(function, snapshots, phase, *args):
        assert (directory/'frozen_inputs.json').exists()
        events.append(phase)
        if phase.endswith('SOURCE'):
            if phase == 'EVAL_SOURCE':
                programs = runner.read(directory/'frozen_programs.json')
                assert len(programs) == 8 and all(len(cell['selected_parents']) == 1 for cell in programs)
                assert runner.read(directory/'run.json')['phase_order'][-1] == 'PROGRAMS_FROZEN'
            return dict(lifecycles=[dict(life=life, roots=[root for root in roots(phase) if root['life']==life], source_trace=f'unused_{life}') for life in range(4)], seconds=0.)
        assert (directory/f'inputs_{phase.lower()}.json').exists()
        out = directory/f'{phase}_outcomes.json'; runner.save(out, [])
        return dict(lifecycles=[dict(life=0, outcomes_ref=out.name)], seconds=0.)
    def select(cells, roots, outcomes, phase):
        result = deepcopy(cells)
        for cell in result:
            cell['selected_parents'] = cell['parents'][:1] if phase == 'FINAL' else cell['parents']
            cell['complete'] = phase != stop_phase
        return result
    monkeypatch.setattr(runner.prior, 'parallel_phase', execute)
    monkeypatch.setattr(runner, 'choose_parents', select)
    runner.run(directory)
    run = runner.read(directory/'run.json')
    if stop_phase:
        expected = ['TRAIN_SOURCE', 'G1'] if stop_phase == 'G1' else ['TRAIN_SOURCE', 'G1', 'G2', 'FINAL']
        assert events == expected and run['status'] == 'incomplete_training'
        assert not (directory/'frozen_programs.json').exists()
        assert run['phase_order'][-1] == stop_phase
        assert (directory/f'selections_{stop_phase.lower()}.json').exists()
    else:
        assert events == ['TRAIN_SOURCE', 'G1', 'G2', 'FINAL', 'EVAL_SOURCE', 'EVAL']
        assert run['status'] == 'complete'
