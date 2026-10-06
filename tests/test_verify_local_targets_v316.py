"""New V316 namespace and fresh-cohort wiring only; settled kernels are not rerun."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_local_targets_v316 as audit

ROOT=Path(__file__).resolve().parents[1]


def test_new_training_and_evaluation_seed_coordinates_are_fresh_and_disjoint():
    warm={audit.warmup_seed(life,stage,game) for life in range(16) for stage in audit.STAGES for game in range(8)}
    initial={audit.training_seed(life,stage) for life in range(16) for stage in audit.STAGES}
    post={audit.post_seed(life,task,r) for life in range(16) for task in audit.TASKS for r in (1,2)}
    evaluation={audit.evaluation_seed(life,task,e) for life in range(16) for task in audit.TASKS for e in range(32)}
    assert len(warm)==256 and len(initial)==32 and len(post)==64 and len(evaluation)==1024
    groups=(warm,initial,post,evaluation)
    assert all(not(left & right) for i,left in enumerate(groups) for right in groups[i+1:])
    assert all(min(group)>316000000000 for group in groups)
    assert audit.warmup_seed(7,'B0',3)==316107100003
    assert audit.training_seed(7,'B0')==316270100000
    assert audit.post_seed(7,'B',2)==316571200000
    assert audit.evaluation_seed(7,'B',31)==316907100031


def test_exact_new_freeze_keeps_the_unchanged_dual_target_method_and_new_scope():
    from acfqp.science.local_target_run_v316 import configuration
    source=ROOT/'reports/fresh_source_v312/source_summary.json'
    actual=json.loads(json.dumps(configuration(source)))
    audit.equal_tree(actual,audit.expected_configuration(source),'exact new V316 freeze')
    assert actual['schema']=='acfqp.local_target_freeze.v316'
    assert actual['head_history_format']=='acfqp.head_version.v313'
    assert actual['bootstrap_seed']==31600001 and actual['expected_evaluation_games']==6144
    assert actual['initial_raw_per_task']==131072 and actual['round_raw_per_collector']==65536
    assert actual['primary']=='TD_LOCAL_minus_FIRST_LOCAL_FINAL_AB'
    assert actual['bootstrap']=='BATCH_START_FROZEN_OWN_HEAD_V0_THEN_V1'
    assert actual['source_summary']==str(source.resolve())


def test_new_training_cohort_preserves_actual_native_artifact_format():
    version=dict(file='reports/local_targets_v316/TD_LOCAL_v1.npz',version=1,arm='TD_LOCAL')
    metadata=audit.target_metadata(version,2,8)
    assert metadata['schema']=='acfqp.local_sampled_sarsa_targets.v314'
    assert metadata['bootstrap_version']==version and metadata['target_array_bytes']==160
    assert metadata['target_rule']=='RECORDED_SUCCESSOR_AFTERSTATE_NEXT_REWARD_UNDISCOUNTED'


def test_prior_experiment_terminal_schema_cannot_substitute_for_new_cohort(tmp_path):
    (tmp_path/'summary.json').write_text(json.dumps(dict(schema='acfqp.local_targets.v314',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE')))
    (tmp_path/'configuration.json').write_text('{}')
    with pytest.raises(ValueError,match='complete new V316'):
        audit.audit(tmp_path)


def test_prior_evaluation_seeds_cannot_be_presented_as_fresh_confirmation():
    belief=dict(estimated_p_four=.37)
    value=dict(estimated_p_four=.37,head_version=None,planner='H2',static_evaluation_valid=True,
        game_summaries=[dict(seed=314900000000+e) for e in range(32)])
    with pytest.raises(ValueError,match='paired V316 task seeds'):
        audit.check_evaluation(value,0,'A',belief,None)


def test_actual_fresh_source_and_new_target_cpu_are_carried_once():
    source=dict(full_source_cpu_seconds=1701.837954057)
    account=dict(worker_cpu_seconds=4.,compiler_cpu_seconds=1.,coordinator_cpu_seconds=2.,
        new_target_cpu_seconds=7.,economic_source_and_target_cpu_seconds=1708.837954057)
    audit.check_compute_totals(account,source)
    account['economic_source_and_target_cpu_seconds']+=864.903343098
    with pytest.raises(ValueError,match='carried economically once'):
        audit.check_compute_totals(account,source)


def endpoint_summary():
    def endpoint(value):
        return dict(games=32,mean_game_utility=value,wins=0,losses=32,cutoffs=0,cutoff_episodes=[],steps=320)
    records=[]
    for life in range(16):
        cells={}
        for task in audit.TASKS:
            first={'SOURCE':endpoint(-4.),'FIRST_LOCAL':endpoint(0.)}
            cells['FIRST_'+task]=dict(task=task,checkpoint='FIRST',estimated_p_four=.2,arms=first)
            for r in (1,2):
                cells[f'ROUND{r}_{task}']=dict(task=task,checkpoint=f'ROUND{r}',estimated_p_four=.2,quota=10,
                    arms=dict(first,MC_LOCAL=endpoint(-2.),TD_LOCAL=endpoint(-1. if task=='A' else 3.)))
        records.append(dict(lifecycle=life,parent=life%4,cells=cells))
    def contrast(values):
        value=values[0]; assert all(item==value for item in values)
        return dict(mean=value,ci95=[value,value],lifecycle_deltas={str(i):value for i in range(16)},
            parent_mean_deltas={str(p):value for p in range(4)},interval_scope=audit.INTERVAL_SCOPE,
            improved_equal_worse=[16*int(value>0),16*int(value==0),16*int(value<0)],
            adverse_lifecycles=list(range(16)) if value<0 else [])
    def utility(row,key,arm):
        return row['cells'][key]['arms'][arm]['mean_game_utility']
    cells={};rounds={};checkpoints={};physical={arm:[] for arm in audit.ARMS}
    for task in audit.TASKS:
        key='FIRST_'+task
        cells[key]=dict(task=task,checkpoint='FIRST',arms={arm:audit.aggregate([row['cells'][key]['arms'][arm] for row in records]) for arm in ('SOURCE','FIRST_LOCAL')},
            paired_contrasts={'FIRST_LOCAL_minus_SOURCE':contrast([4.]*16)})
        for row in records:
            for arm in ('SOURCE','FIRST_LOCAL'): physical[arm].append(row['cells'][key]['arms'][arm])
    for r in (1,2):
        rounds[str(r)]={}
        for left,right in audit.PAIRS:
            rounds[str(r)][left+'_minus_'+right]=contrast([sum(utility(row,f'ROUND{r}_{task}',left)-utility(row,f'ROUND{r}_{task}',right) for task in audit.TASKS)/2 for row in records])
        for task in audit.TASKS:
            key=f'ROUND{r}_{task}'
            cells[key]=dict(task=task,checkpoint=f'ROUND{r}',arms={arm:audit.aggregate([row['cells'][key]['arms'][arm] for row in records]) for arm in audit.ARMS},
                paired_contrasts={left+'_minus_'+right:contrast([utility(row,key,left)-utility(row,key,right) for row in records]) for left,right in audit.PAIRS})
            checkpoints[key]={arm:contrast([utility(row,key,arm)-utility(row,key,'FIRST_LOCAL') for row in records]) for arm in audit.UPDATING_ARMS}
            for row in records:
                for arm in audit.UPDATING_ARMS: physical[arm].append(row['cells'][key]['arms'][arm])
    checkpoints_status={key:{arm:'SUPPORTED_LOSS' if value['mean']<0 else 'SUPPORTED_NONDECREASE' for arm,value in contrasts.items()} for key,contrasts in checkpoints.items()}
    summary=dict(by_lifecycle=records,bootstrap_draws=20000,bootstrap_seed=31600001,interval_scope=audit.INTERVAL_SCOPE,
        primary_contrast='TD_LOCAL_minus_FIRST_LOCAL_FINAL_AB',estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        cells=cells,round_ab_contrasts=rounds,final_ab_contrasts=rounds['2'],checkpoint_contrasts=checkpoints,
        arms={arm:audit.aggregate(values) for arm,values in physical.items()},complete_game_endpoints=True,
        training_cutoffs=[],initial_context_precondition_met=True,initial_precondition_failed_lifecycles=[],
        primary_self_improvement_supported=True,primary_self_improvement_status='SUPPORTED_GAIN',
        target_intervention_supported=True,target_intervention_status='SUPPORTED_GAIN',
        final_net_gain_supported=True,final_net_gain_status='SUPPORTED_GAIN',
        mc_self_improvement_supported=False,mc_self_improvement_status='SUPPORTED_LOSS',
        final_task_improvement_supported={'A':False,'B':True},final_task_improvement_status={'A':'SUPPORTED_LOSS','B':'SUPPORTED_GAIN'},
        task_retention_status={'A':'SUPPORTED_LOSS','B':'SUPPORTED_NONDECREASE'},task_retention_supported=False,
        retained_improvement_supported=False,target_mechanism_supported=False,checkpoint_status=checkpoints_status)
    return summary,records


def test_new_primary_and_retention_flags_use_only_fresh_own_first_contrasts():
    summary,records=endpoint_summary()
    flags=audit.check_analysis(summary,records)
    assert flags['primary_self_improvement_supported'] and flags['target_intervention_supported']
    assert not flags['retained_improvement_supported'] and not flags['target_mechanism_supported']


@pytest.mark.parametrize('field,value',(('bootstrap_seed',31400001),('primary_contrast','TD_LOCAL_minus_MC_LOCAL_FINAL_AB')))
def test_old_bootstrap_or_component_intervention_cannot_replace_new_primary(field,value):
    summary,records=endpoint_summary();summary[field]=value
    with pytest.raises(ValueError,match='V316 own-FIRST primary'):
        audit.check_analysis(summary,records)


def test_positive_average_or_v315_component_diagnostics_cannot_override_new_task_retention():
    summary,records=endpoint_summary();summary['retained_improvement_supported']=True
    with pytest.raises(ValueError,match='literal per-task retention'):
        audit.check_analysis(summary,records)
