"""Synthetic data separation, development assumptions and retained paid work."""
import json
import pytest
from scripts import run_controlled_predictive_merge_relations_v190 as runner


def fake_inputs(tmp_path,monkeypatch):
    prior=tmp_path/'prior'; learned=tmp_path/'learned'
    monkeypatch.setattr(runner,'ROOT',tmp_path); monkeypatch.setattr(runner,'PREVIOUS',prior)
    monkeypatch.setattr(runner,'LEARNED',learned)
    runner.save(tmp_path/'reports/v189_runtime_tmp/stage_checks.json',{'valid':True})
    runner.save(prior/'run.json',{'status':'complete'})
    runner.save(prior/'diagnostics.json',{})
    runner.save(prior/'summary.json',{})
    source=[dict(root_id=f'source:{i}',source_id=f'group:{i%36}') for i in range(143)]
    runner.save(learned/'roots.json',{'SOURCE':source,'TARGET':[{'root_id':f'dev:{i}'} for i in range(96)]})
    runner.save(learned/'labels.json',[{'root_id':f'dev:{i}'} for i in range(96)])
    runner.save(learned/'inputs/inherited/expanded_models.json',{'RIDGE':{},'LAYOUT':{},'SHARED':{}})
    runner.save(learned/'inputs/inherited/baseline_models.json',{'SHARED':{},'ONE':{}})
    runner.save(learned/'inputs/inherited/learned_rule.json',{})
    runner.save(learned/'models.json',{'LINEAR':{},'INTERACT':{}})
    monkeypatch.setattr(runner.LearnedDynamics,'from_payload',lambda payload:object())
    events=[]
    monkeypatch.setattr(runner,'capture_code',lambda output:events.append('capture'))
    monkeypatch.setattr(runner.core,'cache_roots',lambda roots:{})
    def develop(roots,labels,*args):
        assert len(roots)==len(labels)==96 and roots[0]['root_id'].startswith('dev:')
        events.append('development'); return {'metrics':{},'work':{}}
    monkeypatch.setattr(runner,'development_diagnostics',develop)
    def fit(rows):
        assert len(rows)==143 and all(x['root_id'].startswith('source:') for x in rows)
        events.append('fit')
        return {'model':{'constants':{'columns':98},'rank':2,'root_mean_loss':.1},
            'selection':{'selected_lambda':.1,'selected_utility':.5,'candidates':[]},
            'costs':{'ridge_predictors_fitted':13}}
    monkeypatch.setattr(runner.learning,'fit_model',fit)
    monkeypatch.setattr(runner,'cohort_cases',lambda:events.append('cases') or [{'name':'fresh:target'}])
    monkeypatch.setattr(runner.acquisition,'observe_roots',lambda cases:([{'root_id':cases[0]['name']}],{}))
    monkeypatch.setattr(runner.coverage,'cache_roots',lambda roots:{})
    def choose(roots,models):
        assert set(models)==set(runner.MODEL_NAMES)
        events.append('choices'); return {},{}
    monkeypatch.setattr(runner,'freeze_choices',choose)
    def label(*args):
        events.append('label')
        return {'native':{},'teacher_policy':[], 'costs':{k:{} for k in (
            'construction','planning','label_evaluation','teacher_export','compilation')}}
    monkeypatch.setattr(runner.acquisition,'exact_labels',label)
    monkeypatch.setattr(runner,'canonical_labels',lambda root,*args:dict(root))
    monkeypatch.setattr(runner,'summarize',lambda *args:{'complete':True})
    return events


def test_development_separate_from_source_and_fresh_choices_precede_labels(tmp_path,monkeypatch):
    events=fake_inputs(tmp_path,monkeypatch); record=runner.run(tmp_path/'out')
    assert events==['capture','development','fit','cases','choices','label']
    assert [x['phase'] for x in record['phase_history']]==['protocol_frozen','development_diagnostics',
        'source_selection','models_frozen','target_roots','target_choices_frozen','target_labels','complete']
    assert [x['input_reads'] for x in record['phase_history']]==[0]+[10]*7
    assert record['new_predictors_fitted']==13 and record['new_learning_attempts']==1
    assert record['new_boards_generated']==record['new_reference_kernel_attempts']==record['completed_roots']==1


def test_failed_fit_preserves_paid_work_and_keeps_fresh_roster_closed(tmp_path,monkeypatch):
    events=fake_inputs(tmp_path,monkeypatch)
    def fail(*args):
        events.append('fit'); error=RuntimeError('synthetic third SVD failure')
        error.record={'costs':{'ridge_predictors_fitted':12,'ridge_svd_attempts':3}}
        raise error
    monkeypatch.setattr(runner.learning,'fit_model',fail)
    with pytest.raises(RuntimeError,match='third SVD'):
        runner.run(tmp_path/'out')
    record=json.loads((tmp_path/'out/run.json').read_text())
    assert events==['capture','development','fit'] and record['new_predictors_fitted']==12
    assert record['new_boards_generated']==record['new_reference_kernel_attempts']==0
    assert record['costs']['failed_learning']['ridge_svd_attempts']==3


def test_failed_acquisition_preserves_frozen_fit_and_attempt(tmp_path,monkeypatch):
    events=fake_inputs(tmp_path,monkeypatch)
    def fail(*args):
        error=ValueError('synthetic acquisition cap');error.counts={'concrete_states':200000}
        error.elapsed_seconds=.25;raise error
    monkeypatch.setattr(runner.acquisition,'exact_labels',fail)
    with pytest.raises(ValueError,match='acquisition cap'):
        runner.run(tmp_path/'out')
    record=json.loads((tmp_path/'out/run.json').read_text())
    assert record['new_predictors_fitted']==13 and record['new_reference_kernel_attempts']==1
    assert record['completed_roots']==0 and record['failure']['label_seconds']==.25


def test_development_uses_all_actions_and_only_certified_vertex_occurrences():
    feature=lambda x:[0.]*6+[float(x)]+[0.]*91
    rows=[dict(root_id=f'r{i}',legal_actions=['DOWN','LEFT'],immediate_rewards={'DOWN':1.,'LEFT':0.},
        relation_features={'DOWN':feature(2 if i==2 else 0),'LEFT':feature(1 if i==0 else 2)}) for i in range(3)]
    labels=[dict(root_id='r0',action_components={'DOWN':[0.,0.,0.],'LEFT':[1.,0.,0.]}),
        *[dict(root_id=f'r{i}',action_components={'DOWN':[1.,0.,0.],'LEFT':[0.,0.,0.]}) for i in (1,2)]]
    previous={'alias':{'root_records':[{'root_id':f'r{i}','within_root_regret':float(i==0)} for i in range(3)]},
        'problem':{'roots':[{'root_id':f'r{i}','classes':[{'vertex_id':1,'representative':'DOWN'},
            {'vertex_id':2,'representative':'LEFT'}]} for i in range(3)]}}
    certificate={'dual_explanations':[{'edges':[{'root_id':'r0','best':{'vertex_id':1,'action':'DOWN'},
        'bad':{'vertex_id':2,'action':'LEFT'}},{'root_id':'r1','best':{'vertex_id':2,'action':'LEFT'},
        'bad':{'vertex_id':1,'action':'DOWN'}}]}]}
    result=runner.development_diagnostics(rows,labels,previous,certificate)
    assert result['metrics']['old_loss_roots_now_accessible']==1
    assert not next(x for x in result['vertex_records'] if x['vertex_id']==1)['still_equal']
    assert next(x for x in result['certified_vertex_records'] if x['vertex_id']==1)['still_equal']
    assert result['metrics']['old_cycle_vertices_split']==1


def test_fixed_roster_geometry_with_mock_rng(monkeypatch):
    seeds=[]
    class MockRng:
        def __init__(self,seed):seeds.append(seed)
        def randint(self,*args):return 7
        def sample(self,values,k):return values[:k]
    monkeypatch.setattr(runner.random,'Random',MockRng)
    cases=runner.cohort_cases()
    assert seeds==list(range(1900200,1900296)) and len(cases)==96
    assert cases[0]['name']=='v190_target_r00_00' and cases[-1]['name']=='v190_target_r03_23'
    assert all(x['board'].count(0)==x['stratum']%3 and x['horizon']==3 for x in cases)
