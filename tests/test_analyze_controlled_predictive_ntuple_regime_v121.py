"""Synthetic accounting checks; no actual environment or TD interactions."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_ntuple_regime_v121 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_ntuple_analysis_v121.checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, td_updates=0,
        scope='synthetic traces and sparse metadata; no environment or learner execution'))
    path.write_text(json.dumps(data,indent=2)+'\n')


def make_row(life=0, query='reward', phase='B', method='CONT', *, episode=None,
             transitions=0, n=1, updates=10, label=0, replica=0, cap=2000, status='LOST'):
    training = episode is not None
    delta = n-int(status in ('WON','CUTOFF')) if training else 0
    seed = (analysis.expected_train_seed(life,query,phase,episode) if training else
        analysis.expected_eval_seed(life,phase,replica))
    result = dict(score=4*n, status=status, steps=n,
        utility=analysis.expected_utility(4*n,status,query),
        environment_counts=dict(sampled_transitions=n,initial_spawns=2,
            environment_random_draws=2*n+4,ground_explicit_swipe_calls=n),
        learning_counts=dict(choose_calls=n,td_updates=delta,table_update_occurrences=32*delta),
        planning_counts={},setup_counts={},setup_seconds=0.,seconds=.01,
        updates_before=updates,updates_after=updates+delta)
    row = dict(life=life,query=query,phase=phase,method=method,checkpoint=label,
        replica=replica,seed=seed,max_steps=cap,result=result,
        initial_board=[1,1]+[0]*14,initial_spawns=[dict(cell=0,rank=1),dict(cell=1,rank=1)],
        final_board=([11]+[0]*15 if status=='WON' else [1]*16),
        actions=['RIGHT']*n,spawned_cells=[0]*n,spawned_ranks=[1]*n,scores=[4]*n)
    if training:
        row.update(episode_index=episode,transitions_before=transitions,transitions_after=transitions+n,
            terminal_update=status=='LOST',analytic_terminal=status=='WON',censored_last_update=status=='CUTOFF')
    else:
        row.update(eval_id=f'{life}/{query}/{phase}/{method}/{label}/{replica}',reused_from=None)
    return row


def train_rows(life=0, query='reward', phase='B', method='CONT', updates=10):
    rows=[];transitions=0
    for episode,n in enumerate((3,3,2)):
        status='CUTOFF' if episode==2 else 'LOST'
        row=make_row(life,query,phase,method,episode=episode,transitions=transitions,n=n,
            updates=updates,cap=min(2000,8-transitions),status=status)
        rows.append(row);transitions+=n;updates=row['result']['updates_after']
    return rows


def test_exact_caps_update_deltas_and_phase_identity_are_independent():
    rows=train_rows()
    result=analysis.inspect_training(rows,0,'reward','B','CONT',10,budget=8,middle=3)
    assert all(result['checks'].values()) and result['prefixes'][8]['updates']==17
    assert result['cost']['statuses']['CUTOFF']==1
    for field,value,check in [('phase','A_RETURN','training_roster'),
            ('max_steps',2000,'training_caps'),('transitions_after',9,'exact_training_budget')]:
        bad=deepcopy(rows);bad[-1][field]=value
        assert not analysis.inspect_training(bad,0,'reward','B','CONT',10,budget=8,middle=3)['checks'][check]
    bad=deepcopy(rows);bad[1]['result']['learning_counts']['choose_calls']+=10000
    assert not analysis.inspect_training(bad,0,'reward','B','CONT',10,budget=8,middle=3)['checks']['training_counter_deltas']
    bad=deepcopy(rows);bad[0]['result']['updates_before']=0
    assert not analysis.inspect_training(bad,0,'reward','B','CONT',10,budget=8,middle=3)['checks']['td_update_timing']


def test_outer_validity_checks_queries_seeds_no_updates_and_retains_cutoff():
    row=make_row(query='risk_goal')
    assert analysis.outer_valid(row,10)
    for field,value in [('utility',10),('updates_after',11)]:
        bad=deepcopy(row);bad['result'][field]=value
        assert not analysis.outer_valid(bad,10)
    bad=deepcopy(row);bad['phase']='A_RETURN'
    assert not analysis.outer_valid(bad,10)
    cutoff=make_row(n=2000,status='CUTOFF')
    assert analysis.outer_valid(cutoff,10)


def sparse(path,updates):
    meta=dict(schema='controlled_predictive_ntuple_td_v120',radix=11,updates=updates)
    np.savez_compressed(path,metadata=json.dumps(meta),indices=np.array([],dtype=np.int64),
        values=np.array([],dtype=float))


def dump_rows(path,rows):
    with gzip.open(path,'wt') as stream:
        for row in rows:stream.write(json.dumps(row)+'\n')


@pytest.fixture
def experiment(tmp_path,monkeypatch):
    monkeypatch.setattr(analysis,'LIVES',(0,1))
    monkeypatch.setattr(analysis,'LABELS',(0,3,8))
    monkeypatch.setattr(analysis,'BUDGET',8)
    monkeypatch.setattr(analysis,'REPLICAS',2)
    settings=dict(lifecycles=[0,1],queries=dict(reward=dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.),
        risk_goal=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)),phases=analysis.P_FOUR,
        checkpoints=[0,3,8],train_transitions=8,replicas=2,max_steps=2000,workers=4,alpha=.0025,
        block_episodes=64,version_base=analysis.BASE)
    source=dict(schema='acfqp.ntuple_regime.v121.source',snapshots=[],
        inherited_costs=dict(deterministic_prior={},v120_training=[],scope='fixture'))
    run=dict(status='complete',settings=settings,lifecycles=[],inherited_costs=source['inherited_costs'])
    trace_fields={'initial_board','initial_spawns','final_board','actions','spawned_cells','spawned_ranks','scores'}
    for life in analysis.LIVES:
        snapshot=dict(life=life,rule={},models={});source['snapshots'].append(snapshot)
        history=dict(life=life,queries={});run['lifecycles'].append(history)
        for query in analysis.QUERIES:
            folder=tmp_path/f'{life}_{query}';folder.mkdir()
            origin=folder/'source.npz';sparse(origin,10)
            snapshot['models'][query]=dict(path=str(origin),updates=10,nonzero_weights=0)
            data=dict(training_trace=str((folder/'train.gz').relative_to(tmp_path)),
                control_trace=str((folder/'outer.gz').relative_to(tmp_path)),model_setup=[],phases={})
            history['queries'][query]=data
            for method,phase in [('FROZEN_A','B'),('CONT','B'),('RESET','B'),('RESET','A_RETURN')]:
                reset=method=='RESET'
                data['model_setup'].append(dict(method=method,phase_origin=phase,
                    origin_ref='implicit_zero' if reset else str(origin),updates_at_creation=0 if reset else 10,
                    setup_counts={},setup_seconds=0.,load_seconds=0.,
                    load_counts={} if reset else dict(checkpoint_loads=1,checkpoint_loaded_parameters=0)))
            training,physical=[],[]
            for phase in analysis.PHASES:
                phase_data=dict(p_four=analysis.P_FOUR[phase],methods={});data['phases'][phase]=phase_data
                for method in ('FROZEN_A','CONT','RESET'):
                    initial=0 if method=='RESET' else 17 if method=='CONT' and phase=='A_RETURN' else 10
                    method_data=dict(checkpoints=[]);phase_data['methods'][method]=method_data
                    if method!='FROZEN_A':
                        rows=train_rows(life,query,phase,method,initial);training.extend(rows)
                        found=analysis.inspect_training(rows,life,query,phase,method,initial,budget=8,middle=3)
                        method_data.update(training_blocks=found['blocks'],final_updates=initial+7,
                            final_transitions=8,training_episodes=3)
                    for label in ((0,) if method=='FROZEN_A' else (0,3,8)):
                        updates=initial+(3 if label==3 else 7 if label==8 else 0)
                        ref='implicit_zero' if method=='RESET' else str(origin)
                        origin_kind='implicit_zero' if method=='RESET' else 'source_v120'
                        if method=='CONT' and phase=='A_RETURN':
                            ref=data['phases']['B']['methods']['CONT']['checkpoints'][-1]['model_ref'];origin_kind='v121'
                        cp=dict(label=label,updates=updates,transitions=label,model_ref=ref,
                            model_origin=origin_kind,evaluations=[])
                        if label:
                            path=folder/f'{phase}_{method}_{label}.npz';sparse(path,updates)
                            cp.update(model_ref=str(path.relative_to(tmp_path)),model_origin='v121',
                                model_bytes=path.stat().st_size,save_counts={},save_seconds=0.)
                        for replica in range(2):
                            raw=make_row(life,query,phase,method,label=label,replica=replica,updates=updates)
                            summary={key:value for key,value in raw.items() if key not in trace_fields}
                            if phase=='B' and method=='CONT' and label==0:
                                summary['reused_from']=f'{life}/{query}/B/FROZEN_A/0/{replica}'
                            else:physical.append(raw)
                            cp['evaluations'].append(summary)
                        method_data['checkpoints'].append(cp)
            dump_rows(tmp_path/data['training_trace'],training);dump_rows(tmp_path/data['control_trace'],physical)
    (tmp_path/'run.json').write_text(json.dumps(run));(tmp_path/'source_capsule.json').write_text(json.dumps(source))
    return tmp_path


def test_full_synthetic_roster_aliases_and_new_costs(experiment):
    report=analysis.analyze(experiment)
    assert report['complete'] and report['primary_complete'],report['checks']
    assert report['costs']['training_environment_transitions']==128
    assert report['costs']['physical_outer_games']==104
    assert report['costs']['logical_outer_rows']==112
    assert report['costs']['actual_environment_transitions']==232
    assert report['costs']['training']['statuses']['CUTOFF']==16


@pytest.mark.parametrize('mutation,check',[('alias','outer_aliases'),('reset','model_origins'),
    ('prefix','checkpoint_prefix_updates'),('cost','training_blocks_recomputed')])
def test_mutations_invalidate_only_claimed_success(experiment,mutation,check):
    path=experiment/'run.json';run=json.loads(path.read_text())
    methods=run['lifecycles'][0]['queries']['reward']['phases']['B']['methods']
    if mutation=='alias':methods['CONT']['checkpoints'][0]['evaluations'][0]['reused_from']=None
    elif mutation=='reset':methods['RESET']['checkpoints'][0]['updates']=10
    elif mutation=='prefix':methods['CONT']['checkpoints'][1]['transitions']+=1
    else:methods['CONT']['training_blocks'][0]['environment_counts']['sampled_transitions']+=1
    path.write_text(json.dumps(run));report=analysis.analyze(experiment)
    assert not report['checks'][check] and not report['primary_complete']
    assert report['costs']['training_environment_transitions']==128


def test_outer_cutoff_remains_charged_and_primary_is_incomplete(experiment):
    path=experiment/'run.json';run=json.loads(path.read_text())
    data=run['lifecycles'][0]['queries']['reward']
    cp=data['phases']['A_RETURN']['methods']['CONT']['checkpoints'][-1]
    replacement=make_row(phase='A_RETURN',method='CONT',label=8,updates=24,n=2000,status='CUTOFF')
    physical=list(analysis.read_rows(experiment/data['control_trace']))
    index=next(i for i,row in enumerate(physical) if row['eval_id']==replacement['eval_id'])
    physical[index]=replacement;dump_rows(experiment/data['control_trace'],physical)
    cp['evaluations'][0]={key:replacement[key] for key in cp['evaluations'][0]}
    path.write_text(json.dumps(run));report=analysis.analyze(experiment)
    assert report['complete'] and not report['primary_complete'],report['checks']
    assert report['costs']['actual_environment_transitions']==2231
    assert report['control']['comparisons']['A_RETURN']['CONT_final_minus_RESET']['reward']['mean_deltas']['utility'] is None
