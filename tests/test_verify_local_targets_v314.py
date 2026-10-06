"""Focused independent V314 reader regressions; no prior SOURCE replay or re-fit audit."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_local_targets_v314 as audit

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import SplitLeaf, fit_split
from acfqp.science.native_local_targets_v314 import fit_local_targets
from acfqp.science.closed_loop_versions_v313 import save_version, snapshot_weights
from acfqp.science.native_policy_stream_v313 import NativePolicyStream

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/local_targets_v314/runtime/tests/independent_audit'


@pytest.fixture(scope='module')
def actual(tmp_path_factory):
    out = tmp_path_factory.mktemp('v314_native_targets')
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = .01
    template = QueryTD(QueryParent(source, audit.QUERY, audit.QUERY, .5), 'PRIOR', BUILD); template.freeze()
    first = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    first.risk_weights[:] = -.01; first.freeze()
    provenance = dict(parent=0, checkpoint='fresh-source.npz')
    v0 = save_version(first, provenance, 0, 0, 'FIRST_LOCAL', 0, out/'FIRST_LOCAL_v0.npz')
    seed = audit.post_seed(0, 'A', 1)
    native = NativePolicyStream(first, seed, BUILD)
    try:
        raw = native.advance(.37, .1, 256)
    finally:
        native.close()
    row = dict(raw, bank_update_counts={}, td_examples=[], actor_head_updates=0,
        actor_version=v0, model_p_four=.37)
    identity = {key:row[key] for key in ('actor_head_updates', 'actor_version', 'model_p_four')}
    world = audit.FactualWorld(seed, 256, .1, identity, 'LOCAL_RISK', radix=4); world.train(row)
    n = 4*len(world.games)//5; assert n > 0
    boards = np.concatenate(world.afterstate_chunks)
    rewards = np.asarray([score for scores in world.scores for score in scores]+
        (world.current_scores if world.state['status']=='ACTIVE' else []), dtype=np.float64)/2048.
    data = dict(afterstates=boards[:world.ends[-1]], rewards=rewards[:world.ends[-1]],
        ends=np.asarray(world.ends,dtype=np.int64),
        terminal_codes=np.asarray([1 if game['status']=='WON' else -1 for game in world.games],dtype=np.int32),
        fit_game_count=n,fit_step_end=world.ends[n-1])
    td, mc = SplitLeaf(template,'LOCAL_RISK',BUILD), SplitLeaf(template,'LOCAL_RISK',BUILD)
    for leaf in (td,mc):
        leaf.reward_weights[:] = first.reward_weights; leaf.risk_weights[:] = first.risk_weights
    previous = snapshot_weights(td)
    fit = fit_local_targets(td,data,previous,BUILD,out/'TD_targets.npz',bootstrap_version=v0)
    mc_fit = fit_split(mc,data,BUILD)
    head = audit.HeadVersions(source.weights,provenance['checkpoint'],dict(lifecycle=0,parent=0,context_id=0,arm='TD_LOCAL'),'LOCAL_RISK')
    head.apply(v0)
    return SimpleNamespace(fit=fit,mc_fit=mc_fit,head=head,version=v0,boards=boards,rewards=rewards,
        games=world.games,n=n,out=out,row=row,world=world,source=source,td=td,previous=previous)


def check(actual, fit=None, head=None):
    return audit.check_td_targets(actual.fit if fit is None else fit,actual.boards,actual.rewards,
        actual.games,actual.n,actual.head if head is None else head,actual.version,radix=4)


def corrupt_file(actual, key, change, name):
    fit=deepcopy(actual.fit)
    with np.load(fit['target_artifact']['file']) as saved:
        data={field:saved[field].copy() for field in saved.files}
    change(data[key]); path=actual.out/(name+'.npz'); np.savez_compressed(path,**data)
    fit['target_artifact']['file']=str(path); fit['target_artifact']['saved_bytes']=path.stat().st_size
    return fit


def test_actual_complete_native_targets_and_shared_address_writes_reconcile(actual):
    assert check(actual)==actual.fit['fitted_steps']
    expected=audit.factual_targets(actual.boards,actual.rewards,actual.games,actual.n,actual.head,radix=4)
    inventory=audit.address_inventory(actual.boards,actual.games,actual.n,radix=4)
    audit.check_complete_fit(actual.fit,actual.boards,actual.rewards,actual.games,actual.n,inventory,expected)
    audit.check_complete_fit(actual.mc_fit,actual.boards,actual.rewards,actual.games,actual.n,inventory)
    audit.check_equal_fit_work(actual.mc_fit,actual.fit)


@pytest.mark.parametrize('key',('targetreward','targetwin','targetkind'))
def test_one_wrong_native_target_is_rejected_everywhere_in_complete_arrays(actual,key):
    def change(array):
        array[len(array)//2] += 1 if key=='targetkind' else .25
    fit=corrupt_file(actual,key,change,key)
    with pytest.raises(ValueError,match='every saved native'):
        check(actual,fit)


def test_actual_current_reward_next_win_last_lost_and_unused_win_have_distinct_targets():
    head=SimpleNamespace(reward=np.full(4*4**6,.01),terminal=np.full(4*4**6,-.01))
    a=[1]+[0]*15; b=[2]+[0]*15; won=[4]+[0]*15
    boards=np.asarray([a,b,a,won,a,b],dtype=np.int32)
    rewards=np.asarray([100.,.2,200.,.7,300.,.9])
    games=[dict(steps=2,status='LOST'),dict(steps=2,status='WON'),dict(steps=2,status='LOST')]
    reward,win,kind=audit.factual_targets(boards,rewards,games,2,head,radix=4)
    assert kind.tolist()==[1,3,2,0]
    assert reward.tolist()==pytest.approx([.52,0.,.7,0.])
    assert win.tolist()==pytest.approx([1/(1+np.exp(.32)),0.,1.,0.])
    assert len(reward)==4  # HELDOUT next-game facts cannot enter a final FIT state.


def test_saved_targets_cannot_bootstrap_from_changed_current_or_other_arm_weights(actual):
    wrong=SimpleNamespace(reward=actual.head.reward+.02,terminal=actual.head.terminal+.1)
    with pytest.raises(ValueError,match='every saved native'):
        check(actual,head=wrong)


def test_bootstrap_receipt_must_be_actual_previous_own_version(actual):
    fit=deepcopy(actual.fit); fit['bootstrap_version']=dict(actual.version,arm='MC_LOCAL',version=1)
    with pytest.raises(ValueError,match='own actual batch-start head'):
        check(actual,fit)


def test_saved_target_file_metadata_json_must_match_actual_bootstrap_receipt(actual):
    def change(array):
        pass
    fit=deepcopy(actual.fit)
    with np.load(fit['target_artifact']['file']) as saved:
        data={key:saved[key].copy() for key in saved.files}
    metadata=json.loads(str(data['metadata_json'])); metadata['bootstrap_version']['file']='other_own_v1.npz'
    data['metadata_json']=json.dumps(metadata)
    path=actual.out/'wrong_metadata.npz'; np.savez_compressed(path,**data)
    fit['target_artifact']['file']=str(path); fit['target_artifact']['saved_bytes']=path.stat().st_size
    with pytest.raises(ValueError,match='actual own bootstrap version'):
        check(actual,fit)


def test_round_two_sparse_ancestry_uses_own_actual_td_v1(actual):
    td=actual.td; provenance=dict(parent=0,checkpoint='fresh-source.npz')
    v1=save_version(td,provenance,0,0,'TD_LOCAL',1,actual.out/'TD_LOCAL_v1.npz',base=actual.version,previous=actual.previous)
    rebuilt=audit.HeadVersions(actual.source.weights,provenance['checkpoint'],
        dict(lifecycle=0,parent=0,context_id=0,arm='TD_LOCAL'),'LOCAL_RISK')
    rebuilt.apply(actual.version); rebuilt.apply(v1)
    assert np.array_equal(rebuilt.reward,td.reward_weights.reshape(-1))
    assert np.array_equal(rebuilt.terminal,td.risk_weights.reshape(-1))
    changed=dict(v1,base_file='MC_LOCAL_v1.npz')
    other=audit.HeadVersions(actual.source.weights,provenance['checkpoint'],
        dict(lifecycle=0,parent=0,context_id=0,arm='TD_LOCAL'),'LOCAL_RISK'); other.apply(actual.version)
    with pytest.raises(ValueError,match='sequential previous-weight base'):
        other.apply(changed)


def test_updated_collector_cannot_replace_fixed_first_actual_v0(actual):
    row=deepcopy(actual.row); row['actor_version']=dict(actual.version,version=1,arm='TD_LOCAL')
    identity={key:actual.row[key] for key in ('actor_head_updates','actor_version','model_p_four')}
    world=audit.FactualWorld(audit.post_seed(0,'A',1),256,.1,identity,'LOCAL_RISK',radix=4)
    with pytest.raises(ValueError,match='frozen head version'):
        world.train(row)


def test_equal_state_quota_cannot_hide_wrong_actual_table_writes(actual):
    fit=deepcopy(actual.fit); fit['normalization_counts']['risk_parameter_writes']+=1
    with pytest.raises(ValueError,match='identical factual address normalization'):
        audit.check_equal_fit_work(actual.mc_fit,fit)


def test_bootstrap_cost_cannot_omit_real_reads_or_claim_mc_suffix_work(actual):
    fit=deepcopy(actual.fit); fit['bootstrap_counts']['reward_table_lookups']-=32
    with pytest.raises(ValueError,match='bootstrap reads'):
        check(actual,fit)
    fit=deepcopy(actual.fit); fit['target_counts']['reward_suffix_additions']=fit['fitted_steps']
    with pytest.raises(ValueError,match='phantom suffix work'):
        check(actual,fit)


def test_actual_target_save_and_generation_times_are_contained_in_fit(actual):
    fit=deepcopy(actual.fit); fit['target_artifact']['save_cpu_seconds']=fit['cpu_seconds']+1.
    with pytest.raises(ValueError,match='contained in complete fit timing'):
        check(actual,fit)


def test_source_cpu_is_once_and_contained_bootstrap_save_is_not_added_again():
    source=dict(full_source_cpu_seconds=10.)
    account=dict(worker_cpu_seconds=4.,compiler_cpu_seconds=1.,coordinator_cpu_seconds=2.,
        new_target_cpu_seconds=7.,economic_source_and_target_cpu_seconds=17.)
    audit.check_compute_totals(account,source)
    account['economic_source_and_target_cpu_seconds']+=2.
    with pytest.raises(ValueError,match='carried economically once'):
        audit.check_compute_totals(account,source)


def test_exact_new_freeze_and_disjoint_seed_coordinates():
    config=json.loads((ROOT/'reports/local_targets_v314/configuration.json').read_text())
    audit.equal_tree(config,audit.expected_configuration(config['source_summary']),'new V314 freeze')
    assert config['expected_evaluation_games']==6144 and config['initial_raw_per_task']==131072
    post={audit.post_seed(life,task,r) for life in range(16) for task in audit.TASKS for r in (1,2)}
    warm={audit.warmup_seed(life,task+'0',game) for life in range(16) for task in audit.TASKS for game in range(8)}
    initial={audit.training_seed(life,stage) for life in range(16) for stage in audit.STAGES}
    evaluation={audit.evaluation_seed(life,task,e) for life in range(16) for task in audit.TASKS for e in range(32)}
    assert len(post)==64 and not(post & warm or post & initial or post & evaluation)
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
    summary=dict(by_lifecycle=records,bootstrap_draws=20000,bootstrap_seed=31400001,interval_scope=audit.INTERVAL_SCOPE,
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


def test_positive_mean_and_net_source_gain_preserve_actual_negative_task_retention():
    summary,records=endpoint_summary()
    support=audit.check_analysis(summary,records)
    assert support['primary_self_improvement_supported'] and support['target_intervention_supported']
    assert not support['retained_improvement_supported'] and not support['target_mechanism_supported']


@pytest.mark.parametrize('key',('task_retention_supported','target_mechanism_supported'))
def test_source_adjusted_or_average_gain_cannot_replace_actual_own_first_retention(key):
    summary,records=endpoint_summary(); summary[key]=True
    with pytest.raises(ValueError,match='literal per-task retention'):
        audit.check_analysis(summary,records)
