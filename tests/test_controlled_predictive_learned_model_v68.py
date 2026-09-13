"""Small synthetic-kernel checks; no V68 source/target cohort is consumed."""
from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import torch

from acfqp.science.controlled_predictive_learned_model_v68 import (
    FEATURE_DIMENSION, assemble_sources, board_features, load_model, save_model, train_model,
)
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query, plan


LEDGER = dict(source_assemblies=[], training=[], planner_calls=0, planner_work=Counter(),
              artifact_writes=[], environment_calls=0, inference=[])


def _build(offset):
    model = FiniteModel({0:1,1:1,2:2,3:0,4:0},
        {0:'ACTIVE',1:'ACTIVE',2:'ACTIVE',3:'WON',4:'LOST'},
        {(0,'UP'):(Outcome(1.,3,1.),), (0,'DOWN'):(Outcome(1.,4,0.),),
         (1,'UP'):(Outcome(1.,4,0.),), (1,'DOWN'):(Outcome(1.,3,1.),),
         (2,'LEFT'):(Outcome(1.,0,0.),), (2,'RIGHT'):(Outcome(1.,1,0.),)}, (2,))
    return SimpleNamespace(model=model, boards={state:(state+1+offset,)+(0,)*15 for state in (0,1,2)})


@pytest.fixture(scope='module')
def fitted():
    source = assemble_sources([_build(0),_build(3)])
    LEDGER['source_assemblies'].append(dict(counts=source.counts, elapsed_seconds=source.elapsed_seconds))
    models = {v:train_model(source,v,steps=40,batch_size=16,seed=6801) for v in ('RAW','QUOTIENT')}
    for model in models.values(): LEDGER['training'].append(model.training_report)
    yield source,models
    for name,model in models.items(): LEDGER['inference'].append(dict(variant=name,
        counts=dict(model.inference_counts), elapsed_seconds=model.inference_seconds))


@pytest.fixture(scope='module',autouse=True)
def retain_work(request):
    yield
    path=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_learned_model_v68.core_checks.json'
    payload=json.loads(path.read_text()) if path.exists() else {'attempts':[]}
    payload['attempts'].append(dict(test_module=__file__,session_failures=request.session.testsfailed,
        scope='Two synthetic source kernels only; no real V68 source or target roots',**LEDGER))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def solve(model,query):
    result=plan(model,query);LEDGER['planner_calls']+=1;LEDGER['planner_work'].update(result.counts)
    return result


def test_source_recursive_teacher_merges_behavior_and_preserves_multistep_values(fitted):
    source,models=fitted
    raw,quotient=models['RAW'],models['QUOTIENT']
    assert source.counts['source_active_states']==6
    assert raw.training_report['classes_by_horizon']=={'1':4,'2':2}
    assert quotient.training_report['classes_by_horizon']=={'1':2,'2':1}
    for query in (Query(),Query(.7,.2,.5)):
        a,b=solve(raw.compiled,query),solve(quotient.compiled,query)
        for state in source.model.layers:
            assert a.values[raw.compiled.state_to_cell[state]]==pytest.approx(b.values[quotient.compiled.state_to_cell[state]])


def test_raw_features_and_horizon_only_classifier_do_not_call_target_dynamics(fitted):
    source,models=fitted
    features=board_features([(1,1)+(0,)*14,(1,2)+(0,)*14])
    assert features.shape==(2,FEATURE_DIMENSION)==(2,240)
    assert not torch.equal(features[0],features[1])
    unseen=(10,)+(0,)*15
    with patch('acfqp.domains.standard_2048.legal_actions_v1',side_effect=AssertionError('target legality read')), \
         patch('acfqp.domains.standard_2048.step_v1',side_effect=AssertionError('target transition read')):
        for model in models.values():
            cells=model.batch_encode([unseen,unseen,unseen],[1,2,9])
            assert model.compiled.cells[cells[0]].layer==1
            assert model.compiled.cells[cells[1]].layer==2
            assert cells[2] is None
    assert len(source.boards)==6


def test_actual_weights_and_source_kernel_reload_without_training_board_lookup(fitted,tmp_path):
    source,models=fitted
    boards=list(source.boards.values())+[(9,)+(0,)*15]
    horizons=[source.model.layers[state] for state in source.boards]+[2]
    for variant,model in models.items():
        path=tmp_path/variant
        LEDGER['artifact_writes'].append(dict(variant=variant,**save_model(model,path)))
        loaded=load_model(path)
        assert model.batch_encode(boards,horizons)==loaded.batch_encode(boards,horizons)
        old,new=solve(model.compiled,Query(.8,.3,.6)),solve(loaded.compiled,Query(.8,.3,.6))
        assert old.policy==new.policy and old.values==new.values and old.counts==new.counts
        payload=json.loads((path/'kernel.json').read_text())
        assert 'boards' not in payload and 'state_to_cell' not in payload
        assert loaded.compiled.state_to_cell=={} and all(not cell.members for cell in loaded.compiled.cells.values())
        LEDGER['inference'].append(dict(variant=variant+'_RELOADED',counts=dict(loaded.inference_counts),
            elapsed_seconds=loaded.inference_seconds))


def test_fixed_training_schedule_is_shared_and_does_not_select_on_targets(fitted):
    _,models=fitted
    reports=[model.training_report for model in models.values()]
    for report in reports:
        assert report['counts']['optimizer_steps']==40
        assert report['counts']['training_examples']==640
        assert report['target_model_updates']==0
        assert report['architecture']==[240,128,128]
        assert report['final_training_batch_loss']>=0
    assert reports[0]['counts']['h1_steps']==reports[1]['counts']['h1_steps']
    assert reports[0]['counts']['h2_steps']==reports[1]['counts']['h2_steps']
