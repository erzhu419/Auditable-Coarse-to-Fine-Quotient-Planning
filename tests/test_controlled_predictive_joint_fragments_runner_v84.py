"""Exercise the new selector inside all six unchanged episode controllers."""
from collections import Counter
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_joint_outputs_reach_committed_four_step_deployment():
    spec=importlib.util.spec_from_file_location('v84_runner',ROOT/'scripts/run_controlled_predictive_joint_fragments_v84.py')
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    targets={'SPACE_1':1.,'SNAKE_1':.5,'SPACE_4':2.,'SNAKE_4':3.}
    rows=[dict(query=q,episode=e,board=[1,1]+[0]*14,option=option,target=[value,0.,0.])
          for q in runner.QUERIES for e in range(8) for option,value in targets.items()]
    joint,log=runner.JointSelector.fit(rows,6)
    payload=joint.to_payload()
    zero_tree=dict(left=[-1],right=[-1],feature=[-2],threshold=[-2.],values=[[0.,0.,0.]],samples=[40])
    old=runner.Selector({q:dict(zero_tree) for q in runner.QUERIES},6)
    rule=runner.LearnedDynamics.from_payload(json.loads((runner.SOURCE/'supplied_dynamics.json').read_text()))
    games,raws,work={},{},Counter()
    for method in runner.METHODS:
        model=(runner.JointSelector.from_payload(payload) if method.startswith('JOINT')
               else old if method=='OLD_CONDITIONED' else None)
        games[method],raws[method]=runner.evaluate_game(method,model,rule,99,99,'reward',max_steps=100)
        work.update(games[method]['environment_counts'])
    ledger_path=ROOT/'reports/controlled_predictive_joint_fragments_v84.runner_checks.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'attempts':[]}
    ledger['attempts'].append(dict(lifecycle=99,replica=99,ground_work=dict(work),
        synthetic_tree_fits=log['counts']['tree_fits'],main_campaign_calls=0))
    runner.save(ledger_path,ledger)
    assert len({g['seed'] for g in games.values()})==1
    assert joint.to_payload()==payload
    assert games['JOINT']['selected_option']=='SNAKE_4'
    assert games['JOINT']['fragment_actions']==4
    assert games['JOINT_ONE_STEP']['selected_option']=='SPACE_1'
    assert games['JOINT_ONE_STEP']['fragment_actions']==1
    assert raws['JOINT']['episode']['steps']==raws['JOINT_FROZEN6']['episode']['steps']
    assert raws['H2_ONLY']['episode']['steps']==raws['OLD_CONDITIONED']['episode']['steps']
    trigger=games['JOINT']['initiation_step']
    assert trigger is not None
    for method,game in games.items():
        assert game['committed_length_matches']
        assert game['controller_events']<=1
        assert game['planning_counts']['model_uniform_draws']==4*game['steps']
        assert raws[method]['episode']['steps'][:trigger]==raws['H2_ONLY']['episode']['steps'][:trigger]
