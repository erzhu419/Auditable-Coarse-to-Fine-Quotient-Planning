"""Freeze rosters/model boundaries and stop acquisition on incomplete labels."""
from collections import defaultdict
from copy import deepcopy
import gzip
import json

import pytest
from scripts import run_controlled_predictive_causal_quotient_v171 as runner
from test_consequence_generation_core_v168 import source_game


def source(life,replica):
    row=source_game(life,replica)
    row.update(phase='SOURCE',source_id=f'SOURCE:{life}:risk1:{replica}')
    row['result']['status']='LOST'
    return row


def roots():
    return [root for life in range(4) for replica in range(4) for root in runner.roots_from_source(source(life,replica))]


def outcome(plan,reward=1.):
    return dict(plan,score=reward*2048.,steps=1,status='LOST',components=[reward,1.,0.],utility=reward-1.,
        module=dict(mode=plan.get('mode','FORCED_H2'),life=plan['life'],decisions=0,model_decisions=0,
                    h2_calls=1,unsupported_fallbacks=0,ground_legality_checks=0,source_counts=[0]*4))


def test_root_all_actions_paired_seeds_and_ordinary_five_arm_eval():
    rs=roots();assert len(rs)==128 and len({r['root_id'] for r in rs})==128
    assert all(r['source_step']==r['slot'] and r['source_steps']==8 for r in rs)
    prior=set()
    for phase,cap in (('TRAIN',2048),('VALID',1024)):
        plans=runner.branch_roster(rs,phase);assert len(plans)==len({p['branch_id'] for p in plans})<=cap
        groups=defaultdict(list)
        for p in plans:groups[p['root_id'],p['suffix']].append(p)
        assert all(len({p['seed'] for p in rows})==1 for rows in groups.values())
        seeds={p['seed'] for p in plans};assert not prior.intersection(seeds);prior.update(seeds)
        assert set(p['suffix'] for p in plans)==set(range(4 if phase=='TRAIN' else 2))
    plans=runner.eval_roster();assert len(plans)==640 and len({p['branch_id'] for p in plans})==640
    assert all('root_id' not in p and 'board' not in p for p in plans)
    groups=defaultdict(list)
    for p in plans:groups[p['life'],p['episode']].append(p)
    assert all(len(rows)==5 and len({p['seed'] for p in rows})==1 for rows in groups.values())
    assert not prior.intersection(p['seed'] for p in plans)
    assert runner.settings()['maximum_environment_transitions']==3712*8192


@pytest.mark.parametrize('failure',['cutoff','duplicate','seed','vector'])
def test_any_required_branch_error_blocks_downstream(failure):
    plans=runner.branch_roster(roots()[:1],'TRAIN');rows=[outcome(p) for p in plans]
    assert runner.complete_cohort(rows,plans)
    if failure=='cutoff':rows[-1].update(status='CUTOFF',utility=None)
    elif failure=='duplicate':rows.append(deepcopy(rows[-1]))
    elif failure=='seed':rows[-1]['seed']+=1
    else:rows[-1]['components'][1]=0.
    assert not runner.complete_cohort(rows,plans)


def test_worker_retains_full_model_and_paired_game_identity(monkeypatch,tmp_path):
    plans=runner.eval_roster()[:5];calls=[]
    monkeypatch.setattr(runner,'eval_roster',lambda:plans)
    monkeypatch.setattr(runner,'load_compiled',lambda payload,tables:payload)
    monkeypatch.setattr(runner.prior,'teachers',lambda *args:({}, {}, {}, {}))
    monkeypatch.setattr(runner.prior,'finish_teachers',lambda *args:None)
    def execute(bank,models,life,mode,seed,max_steps,p_four):
        calls.append((models,life,mode,seed,max_steps,p_four))
        row=outcome(dict(life=life,mode=mode))
        return dict(module=row['module'],result={**{k:row[k] for k in ('score','steps','status','components','utility')},
            'environment_counts':{'sampled_transitions':1},'policy_counts':{},'program_setup_counts':{}})
    monkeypatch.setattr(runner,'run_episode',execute)
    records=[dict(payload=j,tables={}) for j in range(4)]
    lc=runner.physical_lifecycle(dict(life=0),'EVAL',[],records,tmp_path)
    assert calls==[([0,1,2,3],0,p['mode'],p['seed'],8192,.1) for p in plans]
    with gzip.open(tmp_path/lc['branch_trace'],'rt') as handle:rows=[json.loads(line) for line in handle]
    assert all(all(row[k]==v for k,v in plan.items()) for row,plan in zip(rows,plans))
    assert lc['physical_branches']==5 and lc['environment_counts']['sampled_transitions']==5


@pytest.mark.parametrize('failure_phase',[None,'TRAIN','VALID'])
def test_all_models_freeze_before_valid_and_eval_and_incomplete_stops(monkeypatch,tmp_path,failure_phase):
    directory=tmp_path/'run';events=[]
    games=[source(l,r) for l in range(4) for r in range(4)]
    capsule=dict(snapshots=[dict(life=l) for l in range(4)],source_traces=[dict(life=0,path='source')],cost_refs=[])
    monkeypatch.setattr(runner,'extract_source',lambda:capsule)
    monkeypatch.setattr(runner,'snapshot_code',lambda directory:0)
    monkeypatch.setattr(runner,'read_rows',lambda path:games if path=='source' else [])
    monkeypatch.setattr(runner,'load_compiled',lambda *args:None)
    from scripts import causal_quotient_diagnostics_v171 as diagnostics
    monkeypatch.setattr(diagnostics,'prediction_report',lambda *args:{})
    def execute(function,snapshots,phase,*args):
        events.append(phase)
        assert (directory/'frozen_inputs.json').exists()
        if phase=='FIT':
            refs=[]
            for life in range(4):
                path=directory/f'model_{life}.json';runner.save(path,dict(payload={},tables={}))
                refs.append(dict(life=life,model_ref=path.name,training_lives=[life]))
            return dict(lifecycles=refs,seconds=0.)
        if phase in ('VALID','EVAL'):
            assert len(runner.read(directory/'frozen_models.json'))==4
            assert 'MODELS_FROZEN' in runner.read(directory/'run.json')['phase_order']
        plans=runner.eval_roster() if phase=='EVAL' else runner.branch_roster(roots(),phase)
        rows=[outcome(p) for p in plans]
        if phase==failure_phase:rows[-1].update(status='CUTOFF',utility=None)
        path=directory/f'{phase}_outcomes.json';runner.save(path,rows)
        return dict(lifecycles=[dict(life=0,outcomes_ref=path.name,branch_trace='unused')],seconds=0.)
    monkeypatch.setattr(runner.prior,'parallel_phase',execute)
    runner.run(directory);run=runner.read(directory/'run.json')
    if failure_phase:
        assert run['status']=='incomplete_training' and 'EVAL' not in events
        assert events==(['TRAIN'] if failure_phase=='TRAIN' else ['TRAIN','FIT','VALID'])
    else:
        assert run['status']=='complete' and events==['TRAIN','FIT','VALID','EVAL']
        assert run['phase_order']==['INPUTS_FROZEN','TRAIN','MODELS_FROZEN','VALID','EVAL']


def test_ordinary_whole_episode_pool_and_incomplete_null_statistics():
    rows=[outcome(p,reward=p['episode'] if p['mode']=='SAME_D3' else 0.) for p in runner.eval_roster()]
    summary=runner.eval_summary(rows);assert summary['complete']
    stat=summary['comparisons'][0]['metrics']['utility']
    assert stat['mean']==15.5 and stat['mean_variance']==pytest.approx(.6875)
    assert 'conditional_episode_ci95' in stat
    rows[0].update(status='CUTOFF',utility=None)
    summary=runner.eval_summary(rows)
    assert not summary['complete'] and summary['comparisons'][0]['metrics']['utility']['mean'] is None


def test_existing_directory_refuses_second_acquisition(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'extract_source',lambda:pytest.fail('already acquired'))
    with pytest.raises(FileExistsError):runner.run(tmp_path)
