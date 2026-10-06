"""Acquisition roster, retained physical identities and whole-cohort stop rules."""
from copy import deepcopy
import gzip
import json

import pytest
from scripts import run_controlled_predictive_persistent_strategy_v170 as runner


def sources():
    nodes = [dict(probe_action=probe,true_action='DOWN',false_action='LEFT',
                  true_next=1-i,false_next=i) for i,probe in enumerate(('LEFT','DOWN'))]
    incumbent = deepcopy(nodes)
    for node in incumbent:
        node.update(true_action='H2',false_action='H2')
    parents = [dict(nodes=nodes),dict(nodes=incumbent)]
    return [dict(heldout_life=life,query='risk1',parents=deepcopy(parents),complete=True,issues=[])
            for life in range(4)]


def test_whole_episode_roster_paired_seeds_and_heldout_eval():
    initial = runner.phase_cells(sources(),None,'G1'); used = set()
    for phase,count in (('G1',2616),('G2',2616),('FINAL',240),('EVAL',384)):
        cells = deepcopy(initial)
        for cell in cells:
            cell['selected_parents'] = deepcopy(cell['parents'][:1] if phase == 'EVAL' else cell['parents'])
        if phase == 'FINAL': cells = runner.phase_cells(sources(),cells,phase)
        plans = runner.branch_roster(cells,phase)
        assert len(plans) == len({p['branch_id'] for p in plans}) == count
        assert all((p['heldout_life'] == p['life']) == (phase == 'EVAL') for p in plans)
        groups = {}
        for p in plans:
            assert 'root_board' not in p and 'root_id' not in p
            groups.setdefault((p['life'],p['heldout_life'],p['episode']),[]).append(p)
        assert all(len({p['seed'] for p in ps}) == 1 and ps[0]['mode'] == 'H2' for ps in groups.values())
        assert all(len(ps) == (109 if phase in ('G1','G2') else 5 if phase == 'FINAL' else 3) for ps in groups.values())
        seeds = {p['seed'] for p in plans}
        assert not used.intersection(seeds); used.update(seeds)
        for ps in groups.values():
            assert ps[0]['program'] is None
            for cond,latched in zip(ps[1::2],ps[2::2]):
                assert cond['program'] == latched['program']
                assert (cond['arm'],latched['arm']) == ('COND','LATCHED')
                assert cond['candidate_slot'] == latched['candidate_slot']
        if phase == 'EVAL':
            assert all(p['candidate_slot'] is None for p in plans)
    source = {runner.source_seed(life,r) for life in range(4) for r in range(4)}
    assert len(source) == 16 and not source.intersection(used)
    cfg = runner.settings()
    assert cfg['controlled_games'] == 5856 and cfg['total_games'] == 5872
    assert cfg['max_steps'] == 8192 and cfg['maximum_environment_transitions'] == 5872*8192


def test_worker_executes_and_retains_entire_program_and_game_identity(monkeypatch,tmp_path):
    cells = runner.phase_cells(sources(),None,'G1')
    plans = runner.branch_roster(cells,'G1')[:3]; calls = []
    class Rule:
        @classmethod
        def from_payload(cls,payload): return cls()
        def to_payload(self): return {}
    def episode(bank,rule,query,program,arm,seed,max_steps,p_four):
        calls.append((query,program,arm,seed,max_steps,p_four))
        return dict(arm=arm,module=dict(program=program,arm=arm),result=dict(
            score=2048,steps=3,status='WON',components=[1.,0.,1.],utility=2.,
            environment_counts={'sampled_transitions':3},policy_counts={},program_setup_counts={}))
    monkeypatch.setattr(runner,'LearnedDynamics',Rule)
    monkeypatch.setattr(runner,'branch_roster',lambda *args: plans)
    monkeypatch.setattr(runner.prior,'teachers',lambda *args: ({'risk1':None,'risk8':None},{},{},{}))
    monkeypatch.setattr(runner.prior,'finish_teachers',lambda *args: None)
    monkeypatch.setattr(runner,'run_episode',episode)
    lc = runner.branch_lifecycle(dict(life=0,rule={}),'G1',cells,tmp_path)
    assert calls == [('risk1',p['program'],p['arm'],p['seed'],8192,.1) for p in plans]
    with gzip.open(tmp_path/lc['branch_trace'],'rt') as handle:
        rows = [json.loads(line) for line in handle]
    assert all(all(row[k] == v for k,v in plan.items() if k != 'program') for row,plan in zip(rows,plans))
    outcomes = runner.read(tmp_path/lc['outcomes_ref'])
    assert [r['candidate_slot'] for r in outcomes] == [None,0,0]
    assert [r['route'] for r in outcomes] == ['H2','COND','LATCHED']
    assert all(r['module']['program'] == p['program'] for r,p in zip(outcomes,plans))
    assert lc['physical_branches'] == 3 and lc['environment_counts'] == {'sampled_transitions':9}


@pytest.mark.parametrize('stop_phase',[None,'SOURCE','G1','FINAL'])
def test_freeze_all_programs_before_eval_and_stop_after_incomplete_cohort(monkeypatch,tmp_path,stop_phase):
    directory = tmp_path/'run'; events = []
    class Rule:
        @classmethod
        def from_payload(cls,payload): return cls()
    monkeypatch.setattr(runner,'LearnedDynamics',Rule)
    monkeypatch.setattr(runner,'extract_source',lambda: dict(snapshots=[dict(life=l,rule={}) for l in range(4)],cost_refs=[]))
    monkeypatch.setattr(runner,'snapshot_code',lambda folder: 0)
    def source(rows,rules,heldout):
        cell = sources()[heldout]
        if stop_phase == 'SOURCE': cell.update(complete=False,issues=['source_program_pool'])
        return cell
    monkeypatch.setattr(runner,'source_candidates',source)
    monkeypatch.setattr(runner.prior,'read_rows',lambda path: [])
    monkeypatch.setattr(runner,'summarize_eval',lambda rows: dict(complete=True))
    def execute(function,snapshots,phase,*args):
        assert (directory/'frozen_inputs.json').exists()
        events.append(phase)
        if phase == 'SOURCE':
            return dict(lifecycles=[dict(life=l,source_trace=f'unused{l}') for l in range(4)],seconds=0.)
        assert (directory/f'inputs_{phase.lower()}.json').exists()
        if phase == 'EVAL':
            programs = runner.read(directory/'frozen_programs.json')
            assert len(programs) == 4 and all(len(c['selected_parents']) == 1 for c in programs)
            assert runner.read(directory/'run.json')['phase_order'][-1] == 'PROGRAMS_FROZEN'
        path = directory/f'{phase}_outcomes.json'; runner.save(path,[])
        return dict(lifecycles=[dict(life=0,outcomes_ref=path.name)],seconds=0.)
    def choose(cells,outcomes,phase):
        result = deepcopy(cells)
        for cell in result:
            cell['selected_parents'] = cell['parents'][:1] if phase == 'FINAL' else cell['parents']
            cell['complete'] = phase != stop_phase
        return result
    monkeypatch.setattr(runner.prior,'parallel_phase',execute)
    monkeypatch.setattr(runner,'choose_parents',choose)
    runner.run(directory); run = runner.read(directory/'run.json')
    if stop_phase:
        expected = {'SOURCE':['SOURCE'],'G1':['SOURCE','G1'],'FINAL':['SOURCE','G1','G2','FINAL']}[stop_phase]
        assert events == expected and run['status'] == 'incomplete_training'
        assert not (directory/'frozen_programs.json').exists()
        assert run['phase_order'][-1] == stop_phase
    else:
        assert events == ['SOURCE','G1','G2','FINAL','EVAL'] and run['status'] == 'complete'


def test_existing_run_directory_prevents_second_acquisition(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'extract_source',lambda: pytest.fail('must refuse before accessing teachers'))
    with pytest.raises(FileExistsError): runner.run(tmp_path)
