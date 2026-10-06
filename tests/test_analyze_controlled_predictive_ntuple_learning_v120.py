"""Bookkeeping fixtures detect bad TD counts, censoring and evaluation leakage."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import numpy as np
import pytest
from scripts import analyze_controlled_predictive_ntuple_learning_v120 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_ntuple_analysis_v120.checks.json'
    log = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, td_updates=0,
        scope='synthetic trace/model-file accounting; no actual learning or gameplay'))
    path.write_text(json.dumps(log,indent=2)+'\n')


def row(life=0, query='reward', method='TRAIN', age=None, replica=None, episode=0, score=4):
    train = method == 'TRAIN'
    seed = (analysis.BASE+1_000_000+life*100000+analysis.QUERIES.index(query)*10000+episode
        if train else analysis.BASE+2_000_000+life*100000+replica)
    result = dict(score=score,status='LOST',steps=1,utility=analysis.expected_utility(score,'LOST',query),
        environment_counts=dict(sampled_transitions=1,initial_spawns=2,environment_random_draws=6,
            ground_explicit_swipe_calls=1),planning_counts={},learning_counts={'td_updates':1} if train else {},
        setup_counts={},setup_seconds=0.,seconds=0.,updates_before=episode if train else age or 0,
        updates_after=episode+1 if train else age or 0)
    value = dict(life=life,query=query,method=method,checkpoint=age,replica=replica,seed=seed,result=result,
        initial_board=[0]*16,final_board=[1]*16,initial_spawns=[dict(cell=0,rank=1),dict(cell=1,rank=1)],
        actions=['RIGHT'],spawned_cells=[0],spawned_ranks=[1],scores=[score])
    if train:
        value.update(episode_index=episode,terminal_update=True,censored_last_update=False,analytic_terminal=False)
    elif method != 'TD':
        value.update(planner_seed=seed+50_000_000,rollout_seed=seed+60_000_000 if method=='MC4' else None)
        result['consequence_counts'] = dict(model_spawn_samples=7) if method=='MC4' else {}
    return value


def test_training_stream_update_error_and_censoring_are_retained():
    rows=[row(episode=i) for i in range(3)]
    result=analysis.inspect_training(rows,0,'reward',ages=(0,2,3),block_size=1)
    assert all(result['checks'].values()) and result['prefix_updates']=={0:0,2:2,3:3}
    rows[1]['result']['updates_after']=50
    assert not analysis.inspect_training(rows,0,'reward',ages=(0,2,3),block_size=1)['checks']['td_update_timing']
    cut=row()
    cut.update(terminal_update=False,censored_last_update=True)
    cut['result'].update(status='CUTOFF',updates_after=0,learning_counts={})
    result=analysis.inspect_training([cut],0,'reward',ages=(0,1),block_size=1)
    assert not result['checks']['training_terminal'] and result['checks']['td_update_timing']
    assert result['blocks'][0]['environment_counts']['sampled_transitions']==1


def test_outer_rejects_parameter_update_wrong_seed_and_wrong_utility():
    value=row(method='TD',age=256,replica=0)
    assert analysis.outer_valid(value,256)
    for field,delta in (('updates_after',1),('utility',1)):
        bad=deepcopy(value);bad['result'][field]+=delta
        assert not analysis.outer_valid(bad,256)
    value['seed']+=1
    assert not analysis.outer_valid(value,256)


@pytest.fixture(scope='module')
def experiment(tmp_path_factory):
    directory=tmp_path_factory.mktemp('analysis')
    source=dict(schema='acfqp.ntuple_source.v120',
        snapshots=[dict(life=i,rule={}) for i in range(4)],inherited_costs=dict(scope='fixture'))
    settings=dict(lifecycles=list(range(4)),train_episodes=4096,checkpoints=list(analysis.AGES),replicas=8,
        max_steps=2000,alpha=.0025,block_size=256,p_four=.1,version_base=analysis.BASE,
        planner_offset=50_000_000,rollout_offset=60_000_000,
        queries=dict(reward=dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.),
            risk_goal=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)))
    run=dict(status='complete',settings=settings,lifecycles=[],inherited_costs=source['inherited_costs'])
    trace_fields=('initial_board','final_board','initial_spawns','actions','spawned_cells','spawned_ranks','scores')
    for life in range(4):
        history=dict(life=life,queries={});run['lifecycles'].append(history)
        for query in analysis.QUERIES:
            folder=directory/f'life_{life}'/query;folder.mkdir(parents=True)
            training=[row(life,query,episode=e) for e in range(4096)]
            found=analysis.inspect_training(iter(training),life,query)
            data=dict(training_trace=str((folder/'train.gz').relative_to(directory)),
                control_trace=str((folder/'outer.gz').relative_to(directory)),
                training_blocks=found['blocks'],checkpoints=[],references=[],setup_counts={},setup_seconds=0.)
            history['queries'][query]=data
            with gzip.open(directory/data['training_trace'],'wt') as stream:
                for value in training:stream.write(json.dumps(value)+'\n')
            outer=[]
            for age in analysis.AGES:
                path=folder/f'checkpoint_{age}.npz'
                meta=dict(schema='controlled_predictive_ntuple_td_v120',radix=11,updates=age)
                np.savez_compressed(path,metadata=json.dumps(meta),indices=np.array([],dtype=np.int64),values=np.array([],dtype=float))
                cp=dict(episodes=age,updates=age,model_file=str(path.relative_to(directory)),
                    model_bytes=path.stat().st_size,save_seconds=0.,save_counts={},evaluations=[])
                data['checkpoints'].append(cp)
                for replica in range(8):
                    value=row(life,query,'TD',age,replica,score=age+4);outer.append(value)
                    cp['evaluations'].append({k:v for k,v in value.items() if k not in trace_fields})
            for method,score in (('H2_ONLY',1024),('MC4',2048)):
                for replica in range(8):
                    value=row(life,query,method,None,replica,score=score);outer.append(value)
                    data['references'].append({k:v for k,v in value.items() if k not in trace_fields})
            with gzip.open(directory/data['control_trace'],'wt') as stream:
                for value in outer:stream.write(json.dumps(value)+'\n')
    (directory/'run.json').write_text(json.dumps(run))
    (directory/'source_capsule.json').write_text(json.dumps(source))
    return directory


def test_full_roster_uses_cached_frozen_comparison_without_double_counting(experiment):
    result=analysis.analyze(experiment)
    assert result['complete'],result['checks']
    assert result['costs']['training_environment_transitions']==32768
    assert result['costs']['actual_environment_transitions']==32768+384
    assert result['costs']['model_spawn_samples']==64*7
    effect=result['control']['comparisons']['TD_4096_minus_TD_256']['reward']
    assert effect['mean_deltas']['utility']==(4096-256)/2048 and effect['positive']==4


def test_missing_retained_outer_game_makes_primary_incomplete_without_refunding_training(experiment):
    path=experiment/'life_0/reward/outer.gz'
    saved=path.read_bytes()
    try:
        with gzip.open(path,'rt') as stream: lines=stream.readlines()
        with gzip.open(path,'wt') as stream:stream.writelines(lines[:-1])
        result=analysis.analyze(experiment)
        assert not result['primary_complete'] and not result['checks']['outer_roster']
        assert result['costs']['training_environment_transitions']==32768
        assert result['control']['comparisons']['TD_4096_minus_MC4']['reward']['mean_deltas']['utility'] is None
    finally:
        path.write_bytes(saved)


def test_model_checkpoint_update_mismatch_is_detected(experiment):
    path=experiment/'run.json';saved=path.read_text()
    try:
        data=json.loads(saved);data['lifecycles'][0]['queries']['reward']['checkpoints'][1]['updates']+=1
        path.write_text(json.dumps(data))
        result=analysis.analyze(experiment)
        assert not result['checks']['checkpoint_prefix_updates'] and not result['checks']['sparse_models_complete']
    finally:
        path.write_text(saved)
