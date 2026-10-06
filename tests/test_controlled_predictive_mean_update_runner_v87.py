"""Mean changes reach real controller gates without changing candidate identity."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('mean_runner_v87',ROOT/'scripts/run_controlled_predictive_mean_update_v87.py')
RUNNER=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def retain_work(request):
    yield
    path=ROOT/'reports/controlled_predictive_mean_update_v87.runner_checks.json'
    ledger=json.loads(path.read_text()) if path.exists() else {'attempts':[]}
    ledger['attempts'].append(dict(session_failures=request.session.testsfailed,ground_work=dict(WORK),
        new_tree_fits=0,main_campaign_calls=0))
    path.write_text(json.dumps(ledger,indent=2)+'\n')


def leaf(values):
    return dict(left=[-1],right=[-1],feature=[-2],threshold=[-2.],values=[values],samples=[2])


def test_mean_gates_and_unchanged_histories_on_new_paired_stream(monkeypatch,tmp_path):
    from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
    old_models={}
    for arm,mean in (('COVERAGE',0.),('REPEAT',-4.)):
        anchor=JointSelector({q:leaf([mean,0.,0.]*4) for q in RUNNER.QUERIES},12)
        residual=[1.,0.,0.,-4.,0.,0.,0.,0.,0.,3.,0.,0.]
        old_models[arm]=RUNNER.CenteredSelector({q:leaf(residual) for q in RUNNER.QUERIES},12,anchor)
    deployed=dict(H2_ONLY=None)
    for arm,old in old_models.items():
        means=(-4.,0.) if arm=='COVERAGE' else (0.,-4.)
        model=RUNNER.MeanSelector({q:leaf([mean,0.,0.]) for q,mean in zip(RUNNER.QUERIES,means)},12,old)
        deployed[arm+'_OLD']=old
        deployed[arm+'_MEAN']=model
    before={name:model.to_payload() for name,model in deployed.items() if model}
    actual=RUNNER.evaluate_game

    def limited(*args,**kwargs):
        row,raw=actual(*args,**kwargs,max_steps=100)
        WORK.update(row['environment_counts'])
        return row,raw

    monkeypatch.setattr(RUNNER,'evaluate_game',limited)
    monkeypatch.setattr(RUNNER,'REPLICAS',1)
    rule=RUNNER.LearnedDynamics.from_payload(json.loads((RUNNER.SOURCE/'supplied_dynamics.json').read_text()))
    result=RUNNER.evaluate_methods(99,tmp_path,deployed,rule)
    assert all(result['wiring'].values())
    assert {name:model.to_payload() for name,model in deployed.items() if model}==before
    gates={(arm,row['query']):row['category'] for arm,rows in result['gate_changes'].items() for row in rows}
    assert gates=={('COVERAGE','reward'):'disabled',('REPEAT','reward'):'enabled',
        ('COVERAGE','risk_goal'):'same_fragment',('REPEAT','risk_goal'):'both_h2'}
    for record in result['methods'].values():
        assert len(record['games'])==2
        for game in record['games']:
            assert game['seed']==8790000+99*100
            assert game['planning_counts']['model_uniform_draws']==4*game['steps']
            assert game['committed_length_matches']
            if game['selected_option'] not in (None,'H2'):
                assert game['selected_option']=='SNAKE_4' and game['fragment_actions']==4


def test_gate_categories_reject_a_changed_fragment_and_handle_no_trigger():
    assert RUNNER.gate_category(None,None)=='both_h2'
    with pytest.raises(ValueError,match='changed'):
        RUNNER.gate_category('SPACE_1','SNAKE_4')
