"""Frozen acquisition boundaries and exact same-candidate controls without samples."""
from copy import deepcopy
import gzip
import json

import pytest
from scripts import run_controlled_predictive_joint_feedback_generation_v169 as runner


def roots(phase):
    return [dict(root_id=f'{phase}:{life}:risk1:{replica}:{slot}',phase=phase,
        life=life,query='risk1',replica=replica,slot=slot,board=[1,2]+[0]*14)
        for life in range(4) for replica in range(4 if phase=='EVAL_SOURCE' else 2) for slot in range(2)]


def sources():
    programs = [
        dict(first_action='DOWN',probe_action='LEFT',true_suffix=['LEFT','DOWN','LEFT'],false_suffix=['RIGHT','DOWN','RIGHT']),
        dict(first_action='LEFT',probe_action='DOWN',true_suffix=['DOWN','RIGHT','DOWN'],false_suffix=['UP','LEFT','UP'])]
    return [dict(heldout_life=life,query='risk1',parents=deepcopy(programs),complete=True,issues=[])
            for life in range(4)]


def test_all_physical_slots_pair_seeds_and_leave_heldout_roots_for_eval():
    initial = runner.phase_cells(sources(),None,'G1'); prior_seeds=set()
    for phase,count in (('G1',4848),('G2',4848),('FINAL',960),('EVAL',1536)):
        cells=deepcopy(initial)
        for cell in cells:
            cell.update(selected_parents=deepcopy(cell['parents'][:1] if phase=='EVAL' else cell['parents']),selected_twin='B')
        if phase=='FINAL': cells=runner.phase_cells(sources(),cells,phase)
        plan=runner.branch_roster(roots('EVAL_SOURCE') if phase=='EVAL' else roots('TRAIN_SOURCE'),cells,phase)
        assert len(plan)==len({p['branch_id'] for p in plan})==count
        assert all((p['heldout_life']==p['life'])==(phase=='EVAL') for p in plan)
        groups={}
        for p in plan: groups.setdefault((p['root_id'],p['heldout_life'],p['suffix']),[]).append(p)
        assert all(len({p['seed'] for p in ps})==1 and ps[0]['mode']=='H2' for ps in groups.values())
        assert all(len(ps)==(101 if phase in ('G1','G2') else 5 if phase=='FINAL' else 3) for ps in groups.values())
        seeds={p['seed'] for p in plan}; assert not prior_seeds.intersection(seeds); prior_seeds.update(seeds)
        if phase=='EVAL':
            for ps in groups.values():
                h2,cond,twin=ps
                assert h2['program'] is None and cond['program']['first_action']==twin['program']['first_action']
                assert cond['program']['probe_action']==twin['program']['probe_action']
                assert twin['program']['true_suffix']==twin['program']['false_suffix']==cond['program']['false_suffix']
                assert cond['arm']==twin['arm']=='FEEDBACK'
                assert all(p['candidate_slot'] is None for p in ps)
    seedset={runner.source_seed(p,l,r) for p in ('TRAIN_SOURCE','EVAL_SOURCE') for l in range(4) for r in range(4)}
    assert len(seedset)==32 and not seedset.intersection(prior_seeds)


def test_worker_executes_exact_forced_program_and_retains_candidate_and_root_slots(monkeypatch,tmp_path):
    train=roots('TRAIN_SOURCE'); cells=runner.phase_cells(sources(),None,'G1')
    plans=runner.branch_roster(train,cells,'G1')[:3]; calls=[]
    class Rule:
        @classmethod
        def from_payload(cls,payload): return cls()
        def to_payload(self): return {}
    def branch(board,bank,rule,query,program,arm,seed,max_steps,p_four):
        calls.append((program,arm,seed,max_steps,p_four))
        return dict(root_board=board,arm=arm,module=dict(program=program,arm=arm),result=dict(
            score=2048,steps=3,status='WON',components=[1.,0.,1.],utility=2.,
            environment_counts={'sampled_transitions':3},policy_counts={},program_setup_counts={}))
    monkeypatch.setattr(runner,'LearnedDynamics',Rule)
    monkeypatch.setattr(runner,'branch_roster',lambda *args: plans)
    monkeypatch.setattr(runner.prior,'teachers',lambda *args: ({'risk1':None,'risk8':None},{},{},{}))
    monkeypatch.setattr(runner.prior,'finish_teachers',lambda *args: None)
    monkeypatch.setattr(runner,'run_branch',branch)
    lifecycle=runner.branch_lifecycle(dict(life=0,rule={}),'G1',train,cells,tmp_path)
    assert calls==[(p['program'],p['arm'],p['seed'],2000,.1) for p in plans]
    with gzip.open(tmp_path/lifecycle['branch_trace'],'rt') as handle: rows=[json.loads(line) for line in handle]
    assert all(all(row[k]==v for k,v in plan.items() if k!='program') for row,plan in zip(rows,plans))
    outcomes=runner.read(tmp_path/lifecycle['outcomes_ref'])
    assert [r['candidate_slot'] for r in outcomes]==[None,0,0]
    assert [r['route'] for r in outcomes]==['H2','A','B']
    assert lifecycle['physical_branches']==3 and lifecycle['environment_counts']=={'sampled_transitions':9}


@pytest.mark.parametrize('stop_phase',[None,'SOURCE','G1','FINAL'])
def test_freeze_program_and_twin_before_eval_and_stop_after_incomplete_cohort(monkeypatch,tmp_path,stop_phase):
    directory=tmp_path/'run'; events=[]
    class Rule:
        @classmethod
        def from_payload(cls,payload): return cls()
    monkeypatch.setattr(runner,'LearnedDynamics',Rule)
    monkeypatch.setattr(runner,'extract_source',lambda: dict(snapshots=[dict(life=l,rule={}) for l in range(4)],cost_refs=[]))
    monkeypatch.setattr(runner,'snapshot_code',lambda folder: 0)
    def source(rows,rules,heldout):
        cell=sources()[heldout]
        if stop_phase=='SOURCE': cell.update(complete=False,issues=['source_program_pool'])
        return cell
    monkeypatch.setattr(runner,'source_candidates',source)
    monkeypatch.setattr(runner.prior,'read_rows',lambda path: [])
    monkeypatch.setattr(runner,'summarize_eval',lambda roots,rows: dict(complete=True))
    def execute(function,snapshots,phase,*args):
        assert (directory/'frozen_inputs.json').exists()
        events.append(phase)
        if phase.endswith('SOURCE'):
            if phase=='EVAL_SOURCE':
                programs=runner.read(directory/'frozen_programs.json')
                assert len(programs)==4 and all(len(c['selected_parents'])==1 and c['selected_twin']=='B' for c in programs)
                assert runner.read(directory/'run.json')['phase_order'][-1]=='PROGRAMS_FROZEN'
            return dict(lifecycles=[dict(life=l,roots=[r for r in roots(phase) if r['life']==l],source_trace=f'unused{l}') for l in range(4)],seconds=0.)
        assert (directory/f'inputs_{phase.lower()}.json').exists()
        path=directory/f'{phase}_outcomes.json'; runner.save(path,[])
        return dict(lifecycles=[dict(life=0,outcomes_ref=path.name)],seconds=0.)
    def choose(cells,roots,outcomes,phase):
        result=deepcopy(cells)
        for cell in result:
            cell['selected_parents']=cell['parents'][:1] if phase=='FINAL' else cell['parents']
            cell.update(complete=phase!=stop_phase,selected_twin='B')
        return result
    monkeypatch.setattr(runner.prior,'parallel_phase',execute)
    monkeypatch.setattr(runner,'choose_parents',choose)
    runner.run(directory); run=runner.read(directory/'run.json')
    if stop_phase:
        expected={'SOURCE':['TRAIN_SOURCE'],'G1':['TRAIN_SOURCE','G1'],'FINAL':['TRAIN_SOURCE','G1','G2','FINAL']}[stop_phase]
        assert events==expected and run['status']=='incomplete_training'
        assert not (directory/'frozen_programs.json').exists()
        assert run['phase_order'][-1]==('TRAIN_SOURCE' if stop_phase=='SOURCE' else stop_phase)
    else:
        assert events==['TRAIN_SOURCE','G1','G2','FINAL','EVAL_SOURCE','EVAL'] and run['status']=='complete'


def test_existing_run_directory_prevents_second_acquisition(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'extract_source',lambda: pytest.fail('must refuse before accessing teachers'))
    with pytest.raises(FileExistsError):
        runner.run(tmp_path)

