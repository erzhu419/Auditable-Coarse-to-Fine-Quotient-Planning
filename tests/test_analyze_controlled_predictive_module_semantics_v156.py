"""Independent finite H2, semantic-feature and residual integration checks."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_module_semantics_v156 as audit
from scripts import run_controlled_predictive_module_semantics_v156 as runner
from acfqp.science import controlled_predictive_module_semantics_v156 as core
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics,RewriteProgram

TEMP=Path(__file__).resolve().parents[1]/'reports/v156_runtime_tmp'
WORK=Counter();NATIVE=Counter();SETUP=Counter();ORACLE=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=0,raw_branch_reads=0,
        work=dict(WORK),native_counts=dict(NATIVE),setup_counts=dict(SETUP),oracle_counts=dict(ORACLE),
        scope='One finite synthetic native H2 comparison and one synthetic residual fold; no production roots or samples.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def test_python_h2_oracle_matches_native_nonzero_leaf_and_two_query_shifts():
    with TemporaryDirectory(prefix='oracle_',dir=TEMP) as folder:
        rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
        source=NtupleValue(rule,Path(folder));source.weights[:]=np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
        source.freeze() if hasattr(source,'freeze') else source.weights.setflags(write=False)
        source_query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.);target=audit.QUERIES['risk1']
        parent=QueryParent(source,source_query,target,.4);leaf=QueryTD(parent,'PRIOR',Path(folder));leaf.freeze()
        planner=FrozenLeafPlanner(leaf,2,Path(folder));board=[2,1,2,1,1,2,1,2,2,1,2,1,2,1,1,1]
        metadata=dict(kind='PRIOR',source_query=source_query,target_query=target,failure_shift=leaf.failure_shift,success_shift=leaf.success_shift)
        expected=audit.h2_oracle(board,rule,leaf.weights.reshape(-1),metadata,ORACLE)
        actual=planner.choose(board,target);NATIVE.update(planner.counts);WORK['native_root_queries']+=1
        for model in (source,leaf,planner):SETUP.update(model.setup_counts)
        assert audit.choice_matches(actual,expected)
        assert ORACLE['h2_queries']==1 and ORACLE['enumerated_spawn_outcomes']==actual['counts']['generated_spawn_outcomes']
        assert ORACLE['weight_lookups']==32*ORACLE['leaf_predictions']
        damaged=deepcopy(actual);next(iter(damaged['action_values'].values()))['value']+=.1
        assert not audit.choice_matches(damaged,expected)


def synthetic_choices(board):
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',11)
    choices={}
    for qi,query in enumerate(audit.QUERIES):
        values={}
        for i,action in enumerate(audit.ACTIONS):
            after,score,changed=rule.swipe(board,action)
            if changed:values[action]=dict(afterstate=list(after),score=score,value=float((i+1)*(1 if qi else -1)))
        action=min(values,key=lambda a:(-values[a]['value'],a));choices[query]=dict(action=action,action_values=values)
    return choices


def test_feature_definitions_and_settings_match_independent_fixed_contract():
    assert audit.expected_settings()==runner.settings()
    for board in ([1,1]+[0]*14,[1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,0]):
        choices=synthetic_choices(board)
        actual,work=core.build_local_features(board);assert actual==dict(audit.prior.features(board))
        assert work['feature_occurrences']==41
        for query in audit.QUERIES:
            actual,work=core.build_semantic_features(board,choices,query)
            assert actual==audit.semantic_features(board,choices,query)
            assert work['feature_rank_reads']==116 and work['feature_nonzero_addresses']==len(actual)
            WORK['synthetic_semantic_feature_extractions']+=1


def test_one_residual_fold_matches_independent_zero_fit_and_old_plus_residual_predictions():
    with TemporaryDirectory(prefix='residual_',dir=TEMP) as name:
        directory=Path(name);roots=[];examples=[];rows=[]
        for si,method in enumerate(audit.SOURCES):
            for slot in range(4):
                board=[1,slot+1,si+1,2]+[0]*12
                root=dict(root_id=f'0:risk1:{method}:{slot}',life=0,query='risk1',source_method=method,slot=slot,replica=4*slot,
                    source_seed=15290000000+4*slot,board=board);roots.append(root)
                examples.append(dict(root_id=root['root_id'],targets={'REPAIR_H2':[slot+.5,-.1,.1],'REPAIR_GATE':[si-slot+.2,.2,-.2]}))
                old=dict(components=[.3,.1,.2],advantage=.4,accept=True);choices=synthetic_choices(board)
                rows.append(dict(root_id=root['root_id'],old_prediction=old,features={
                    'LOCAL':[[k,v] for k,v in sorted(audit.prior.features(board).items())],
                    'SEMANTIC':[[k,v] for k,v in sorted(audit.semantic_features(board,choices,'risk1').items())]}))
        capsule=dict(roots=roots,examples=examples);package=dict(rows=rows)
        fold=dict(fold_id='0:risk1:0',life=0,query='risk1',replica=0,source_seed=15290000000,
            train_ids=[r['root_id'] for r in roots if r['replica']!=0],heldout_ids=[r['root_id'] for r in roots if r['replica']==0]);folds=[fold]
        metadata=runner.fit_models(capsule,folds,package,directory);WORK['real_residual_updates']+=768
        models,checks=audit.audit_fits(capsule,folds,package,metadata,directory);WORK['independent_residual_updates']+=768
        assert not checks['fit_roster']  # Deliberately four of the formal 128 fits.
        assert all(v for k,v in checks.items() if k!='fit_roster'),checks
        evaluation_rows,evaluation=runner.evaluate(capsule,folds,package,metadata,directory);WORK['real_residual_predictions']+=32
        checks,work=audit.audit_predictions(capsule,folds,package,evaluation_rows,evaluation,models)
        WORK['independent_residual_predictions']+=work['residual_oracle_predictions']
        assert not checks['prediction_roster'] and not checks['evaluation_models_frozen']
        assert checks['prediction_identity'] and checks['prediction_values'] and checks['evaluation_counts'],checks
        assert len(evaluation_rows)==32 and all(m['before']==m['after'] for m in evaluation['models'])
        assert all(m['before']['weights']==[] and m['new_updates']==192 for m in metadata)


def test_local_control_anchor_checks_cached_v155_components_and_exact_gate():
    original=[];rows=[]
    for life in audit.LIVES:
        for query in audit.QUERIES:
            for fold in (0,4,8,12):
                for arm in audit.ARMS:
                    for slot in range(8):
                        row=dict(fold_id=f'{life}:{query}:{fold}',arm=arm,root_id=f'{life}:{query}:{slot}',
                            prediction=dict(components=[.5,.1,.1],advantage=.5,accept=True))
                        original.append(row);rows.append(dict(deepcopy(row),representation='LOCAL'))
    assert all(audit.local_anchor_checks(rows,original).values())
    rows[0]['prediction']['accept']=False
    checks=audit.local_anchor_checks(rows,original)
    assert checks['local_anchor_components'] and checks['local_anchor_roster'] and not checks['local_anchor_gate']
    WORK['synthetic_anchor_prediction_rows_compared']+=1024
