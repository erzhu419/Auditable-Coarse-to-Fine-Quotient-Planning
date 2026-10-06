"""Synthetic V154 label, warm-fit and evaluation wiring integration checks."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from scripts import analyze_controlled_predictive_module_repair_v154 as audit
from scripts import run_controlled_predictive_module_repair_v154 as runner
from acfqp.science.controlled_predictive_policy_modules_v151 import RootConsequences

TEMP=Path(__file__).resolve().parents[1]/'reports/v154_runtime_tmp'
WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__==__name__ for i in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=0,native_calls=0,work=dict(WORK),
        scope='Synthetic retained labels, actual warm RootConsequences fits, independent LMS oracle, and stubbed replay routing.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def directory():
    with TemporaryDirectory(prefix='analyzer_',dir=TEMP) as name:yield Path(name)


def test_frozen_settings_and_rosters_detect_wrong_alias_and_seed():
    assert audit.expected_settings()==runner.settings()
    physical,logical=runner.rosters();assert all(audit.roster_checks(physical,logical).values())
    assert len({audit.evaluation_seed(l,r) for l in audit.LIVES for r in range(16)})==64
    wrong=deepcopy(logical);alias=next(r for r in wrong if r['arm']=='ALT');alias['physical_id']=f'{alias["life"]}:{alias["query"]}:H2:{alias["replica"]}'
    checks=audit.roster_checks(physical,wrong);assert not checks['logical_roster'] and not checks['alias_reuse']
    wrong=deepcopy(physical);wrong[0]['seed']+=1;assert not audit.roster_checks(wrong,logical)['physical_roster']


def fixture_capsule(directory):
    capsule=dict(roots=[],models=[],source_traces=[]);models={}
    for life in audit.LIVES:
        trace=directory/f'life_{life}.jsonl.gz';capsule['source_traces'].append(dict(life=life,path=str(trace)))
        with gzip.open(trace,'wt') as output:
            for qi,query in enumerate(audit.QUERIES):
                model=RootConsequences();model._weights={-1:(.2+life,.1,0.),17:(.5,0.,-.2)};model.updates=19+life
                model.counts['root_predictions']=77;model.freeze();payload=model.to_payload();WORK['fixture_checkpoint_saves']+=1
                path=directory/f'models/{life}/{query}/OLD.json';path.parent.mkdir(parents=True,exist_ok=True);runner.save(path,payload)
                meta=dict(life=life,query=query,arm='OLD',model_ref=str(path.relative_to(directory)),frozen_state=model.state(),model_bytes=path.stat().st_size)
                capsule['models'].append(meta);models[life,query,'OLD']=dict(metadata=meta,payload=payload,weights=dict(model.weights))
                for si,source in enumerate(audit.diagnosis.SOURCES):
                    for slot in range(4):
                        root=dict(root_id=f'{life}:{query}:{source}:{slot}',life=life,query=query,source_method=source,slot=slot,
                            board=[life+1,qi+1,si+1,slot+1]+[0]*12,prediction=dict(accept=slot%2==0),old_label=[999.,999.,999.])
                        capsule['roots'].append(root)
                        for suffix in range(16):
                            values={'H_H2':(100+suffix,'LOST'),'M_H2':(100+2*suffix+slot,'WON'),
                                'H_GATE':(200+suffix,'WON'),'M_GATE':(200+3*suffix+2*slot,'LOST')}
                            for mode,(units,status) in values.items():
                                components=[units/2048,int(status=='LOST'),int(status=='WON')]
                                row=dict(root_id=root['root_id'],branch_id=f'{root["root_id"]}:{suffix}:{mode}',life=life,query=query,
                                    source_method=source,slot=slot,root_board=root['board'],suffix=suffix,mode=mode,seed=audit.diagnosis.branch_seed(root,suffix),
                                    result=dict(score=units,steps=suffix+1,status=status,components=components,utility=audit.prior.utility(components,query)))
                                output.write(json.dumps(row)+'\n')
    return capsule,models


def test_actual_retained_label_reader_matches_independent_means_and_cost_views(directory):
    capsule,_=fixture_capsule(directory);expected,read_work,checks=audit.training_examples(capsule)
    actual,actual_work=runner.prepare_examples(capsule);WORK['synthetic_retained_records_read']+=8192
    assert all(checks.values()),checks
    assert actual==expected and actual_work==read_work
    assert read_work==dict(retained_rows_read=4096,retained_environment_transitions=34816,new_training_environment_samples=0,
        matched_budget_views={'REPAIR_H2':34816,'REPAIR_GATE':34816})
    assert len(expected)==64 and [e['root_id'] for e in expected]==[r['root_id'] for r in capsule['roots']]
    for example in expected:
        slot=example['slot'];assert example['targets']=={'REPAIR_H2':[(slot+7.5)/2048,-1.,1.],'REPAIR_GATE':[(2*slot+15)/2048,1.,-1.]}
        assert 'old_label' not in example and 'prediction' not in example
    original=audit.prior.old.read_rows
    def changed(path):
        for i,row in enumerate(original(path)):
            if not i:row['seed']+=1;row['result']['status']='CUTOFF';row['result']['utility']=None
            yield row
    with patch.object(audit.prior.old,'read_rows',changed):
        _,_,bad=audit.training_examples(capsule);WORK['synthetic_retained_records_read']+=4096
    assert not bad['training_branch_identity'] and not bad['training_terminal_labels']


def test_actual_warm_fits_match_independent_weights_historical_updates_and_new_counters(directory):
    capsule,models=fixture_capsule(directory);examples,_=runner.prepare_examples(capsule);WORK['synthetic_retained_records_read']+=4096
    metadata=runner.fit_models(capsule,examples,directory);WORK['real_normalized_lms_updates']+=4096
    fitted,checks,diagnostics=audit.audit_fits(examples,metadata,models,directory);WORK['independent_fit_oracle_updates']+=4096;WORK['independent_training_diagnostic_predictions']+=256
    assert all(checks.values()),checks
    assert len(fitted)==len(diagnostics)==16 and sum(m['new_updates'] for m in metadata)==4096
    assert all(m['fit_counts']['root_predictions']==256 and m['total_counts']['checkpoint_saves']==1 for m in metadata)
    for meta in metadata:
        assert meta['frozen_state']['updates']==meta['before']['updates']+256
        assert meta['before']==models[meta['life'],meta['query'],'OLD']['metadata']['frozen_state']
    bad=deepcopy(metadata[:1]);bad[0]['fit_counts']['root_predictions']+=77;bad[0]['frozen_state']['updates']=256
    _,checks,_=audit.audit_fits(examples,bad,models,directory);WORK['independent_fit_oracle_updates']+=256;WORK['independent_training_diagnostic_predictions']+=16
    assert not checks['fit_weights'] and not checks['fit_counts']


def test_lifecycle_routes_each_arm_to_its_frozen_model_and_charges_physical_only(directory):
    physical,_=runner.rosters();physical={r['physical_id']:r for r in physical if r['life']==0};models={};records=[]
    for qi,query in enumerate(audit.QUERIES):
        for ai,arm in enumerate(audit.LEARNED):
            weights={-1:(qi*10+ai+1.,0.,0.)};state=audit.prior.model_state(weights,33)
            meta=dict(model_ref=f'{query}/{arm}',frozen_state=state);models[query,arm]=dict(metadata=meta,weights=weights)
            records.append(dict(query=query,arm=arm,model_ref=meta['model_ref'],before=state,after=state,
                counts={'root_predictions':16},setup_counts=dict(audit.diagnosis.model_setup(1)),setup_seconds=0.))
    trace=directory/'control.jsonl.gz';policies=Counter()
    with gzip.open(trace,'wt') as output:
        for reference in physical.values():
            row=deepcopy(reference);arm=row['arm'];query=row['query'];work={f'policy_{query}_choose_calls':1}
            if arm!='H2':work['learner_root_predictions']=1
            policies.update(work);row.update(max_steps=2000,result=dict(score=1.,steps=1,status='LOST',components=[1/2048,1,0],
                utility=1/2048-audit.QUERIES[query]['failure_penalty'],environment_counts={'sampled_transitions':1},policy_counts=work,decision_seconds=.01))
            output.write(json.dumps(row)+'\n')
    lifecycle=dict(life=0,control_trace=trace.name,models=records,physical_games=128,environment_counts={'sampled_transitions':128},
        policy_counts=dict(policies),statuses={'LOST':128},teacher_bank={q:dict(loads={},parent_before={},parent_after={},
            leaf_before={},leaf_after={},total_counts={'choose_calls':64}) for q in audit.QUERIES})
    def replay(row,weights):
        WORK['stubbed_replay_calls']+=1
        expected={} if row['arm']=='H2' else models[row['query'],row['arm']]['weights']
        return {'fixture_model_binding':weights==expected},0,[]
    with patch.object(audit.prior,'replay_game',replay), \
            patch.object(audit.prior.h1.teacher_analysis,'teacher_loads_valid',return_value=True), \
            patch.object(audit.prior.planning.previous,'model_state',return_value={}), \
            patch.object(audit.prior.planning,'expected_model_state',return_value={}):
        result=audit.audit_lifecycle(lifecycle,{},models,physical,directory)
    assert all(result['checks'].values()),result['checks']
    assert len(result['physical'])==result['costs']['physical_games']==128
    assert result['costs']['environment_counts']=={'sampled_transitions':128}
    assert result['costs']['policy_counts']==policies and len(result['costs']['physical_cells'])==8
    assert all(cell['games']==16 for cell in result['costs']['physical_cells'].values())
