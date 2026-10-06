"""Exercise allocation data flow and real controller deployment separately."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('allocation_runner_v86',ROOT/'scripts/run_controlled_predictive_budget_allocation_v86.py')
RUNNER=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def retain_work(request):
    yield
    path=ROOT/'reports/controlled_predictive_budget_allocation_v86.runner_checks.json'
    ledger=json.loads(path.read_text()) if path.exists() else {'attempts':[]}
    ledger['attempts'].append(dict(session_failures=request.session.testsfailed,ground_work=dict(WORK),
        main_campaign_calls=0,new_tree_fits=0))
    path.write_text(json.dumps(ledger,indent=2)+'\n')


def test_allocations_match_actual_budget_and_keep_root_means_weighted(monkeypatch,tmp_path):
    base=[dict(query=q,episode=e,board=[1,1]+[0]*14,option=o,target=[1.,0.,0.])
        for q in RUNNER.QUERIES for e in range(12) for o in RUNNER.OPTIONS[1:]]
    unchanged=deepcopy(base)
    sampled=[]

    def source(life,episode,query,rule,seed,remaining):
        n=min(2,remaining)
        root=dict(query=query,episode=episode,board=[2,1]+[0]*14)
        log=dict(ground_work={'sampled_transitions':n},planning_counts={},outcomes={'LOST':1},games=1)
        return root,dict(env_seed=seed),log

    def sample(root,rule,seed,remaining,replicas):
        used=min(8,remaining)
        complete=used==8
        sampled.append((root['query'],root['episode'],seed,remaining))
        rows=[dict(root,option=o,target=[3.,1.,-1.]) for o in RUNNER.OPTIONS[1:]] if complete else []
        return rows,[dict(seed=seed)],dict(ground_work={'sampled_transitions':used},planning_counts={},
            outcomes={'LOST':int(complete),'CUTOFF':int(not complete)},trajectories=1,
            complete_block=complete,pair_deltas={})

    monkeypatch.setattr(RUNNER,'collect_source',source)
    monkeypatch.setattr(RUNNER,'sample_root',sample)
    for arm in RUNNER.ALLOCATIONS:
        rows,record=RUNNER.acquire_allocation(0,arm,base,None,tmp_path/arm,budget=25)
        for query,result in record['queries'].items():
            assert result['used_transitions']==25
            assert (result['source_work'].get('sampled_transitions',0)
                +result['branch_work']['sampled_transitions'])==25
            assert result['incomplete_blocks']==1
            assert result['completed_blocks']==(2 if arm=='COVERAGE' else 3)
            assert result['training_roots_added']==(2 if arm=='COVERAGE' else 0)
        assert record['dataset']['training_roots']==(24 if arm=='COVERAGE' else 20)
        assert record['dataset']['heldout_roots']==4
        holdout=lambda data:{(r['query'],r['episode'],r['option']):r for r in data if r['episode']%5==4}
        assert holdout(rows)==holdout(base)
        if arm=='COVERAGE':
            assert all(r['episode'] in (100,101) and r['episode']%5!=4 for r in rows if r['episode']>=100)
        else:
            updated=[r for r in rows if r['target']!=[1.,0.,0.]]
            assert len(updated)==2*3*4
            assert all(r['target']==[2.,.5,-.5] for r in updated)
        assert base==unchanged
    assert len({seed for _,_,seed,_ in sampled})==len(sampled)


def test_all_four_real_methods_preserve_trigger_commitment_and_paired_draws():
    leaf=dict(left=[-1],right=[-1],feature=[-2],threshold=[-2.],values=[[0.]*12],samples=[2])
    from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
    anchor=JointSelector({q:deepcopy(leaf) for q in RUNNER.QUERIES},12)
    residual=deepcopy(leaf)
    residual['values']=[[1.,0.,0.,-4.,0.,0.,0.,0.,0.,3.,0.,0.]]
    model=RUNNER.CenteredSelector({q:deepcopy(residual) for q in RUNNER.QUERIES},12,anchor)
    payload=model.to_payload()
    rule=RUNNER.LearnedDynamics.from_payload(json.loads((RUNNER.SOURCE/'supplied_dynamics.json').read_text()))
    games,raws={},{}
    for method in RUNNER.METHODS:
        selector=None if method=='H2_ONLY' else RUNNER.CenteredSelector.from_payload(payload)
        games[method],raws[method]=RUNNER.evaluate_game(method,selector,rule,99,99,'reward',max_steps=100)
        WORK.update(games[method]['environment_counts'])
    assert len({g['seed'] for g in games.values()})==1
    trigger=games['COVERAGE']['initiation_step']
    assert trigger is not None
    for method,game in games.items():
        assert game['committed_length_matches']
        assert game['planning_counts']['model_uniform_draws']==4*game['steps']
        assert raws[method]['episode']['steps'][:trigger]==raws['H2_ONLY']['episode']['steps'][:trigger]
        if method!='H2_ONLY':
            assert game['selected_option']=='SNAKE_4' and game['fragment_actions']==4
            assert raws[method]['episode']['steps']==raws['FROZEN_V85']['episode']['steps']
    assert model.to_payload()==payload
