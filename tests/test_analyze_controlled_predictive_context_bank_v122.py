"""Synthetic causal route, matched-cost and physical-evaluation checks."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import numpy as np
import pytest
from scripts import analyze_controlled_predictive_context_bank_v122 as a

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    before=request.session.testsfailed
    yield
    p=ROOT/'reports/controlled_predictive_context_bank_v122.analysis_checks.json'
    d=json.loads(p.read_text()) if p.exists() else dict(attempts=[])
    d['attempts'].append(dict(failures=request.session.testsfailed-before,environment_samples=0,model_samples=0,td_updates=0,
        scope='synthetic causal routing, budgets, sparse metadata and alias/source mutations'))
    p.write_text(json.dumps(d,indent=2)+'\n')

def row_for(router,banks,*,phase='B',query='reward',method='BANK',n=96,updates=100,episode=None,
            transitions=0,cap=2000,label=0,replica=0,status='LOST'):
    training=episode is not None;banked=method=='BANK'
    active=router.module_id;seen=router.observations_seen;before=router.counts.copy()
    ids=[];events=[];skips=[];created=delta=0
    ranks=[2 if phase=='B' else 1]*n
    initial_banks=len(banks)
    for i,rank in enumerate(ranks):
        origin=router.module_id
        if banked:
            ids.append(origin);event=router.observe(rank)
            if event:
                events.append(dict(event,observed_action_index=i))
                if event['kind']=='created':
                    created+=1;banks[event['module_id']]=banks[event['previous_module_id']]
        if training and (i<n-1 or status=='LOST'):
            if origin!=router.module_id:skips.append(i)
            else:delta+=1;banks[origin]+=1
    counts=dict(choose_calls=n,td_updates=delta,table_update_occurrences=32*delta)
    if banked:
        counts.update({'router_'+k:v-before.get(k,0) for k,v in router.counts.items()})
        counts.update(bank_creations=created,cross_context_update_skips=len(skips))
        if training:counts.update(bank_weight_copies=created,bank_copied_bytes=created*a.DENSE_BYTES,bank_copied_parameters=created*a.PARAMETERS)
        else:counts.update(evaluation_weight_views=initial_banks+created,evaluation_shared_parameters=(initial_banks+created)*a.PARAMETERS)
    result=dict(score=4*n,status=status,steps=n,utility=a.old.expected_utility(4*n,status,query),seconds=.01,
        environment_counts=dict(sampled_transitions=n,initial_spawns=2,environment_random_draws=2*n+4,ground_explicit_swipe_calls=n),
        learning_counts=counts,planning_counts={},setup_counts={},setup_seconds=0.,updates_before=updates,updates_after=updates+delta,
        active_bank_before=active if banked else None,active_bank_after=router.module_id if banked else None,
        router_observations_before=seen if banked else None,router_observations_after=router.observations_seen if banked else None)
    row=dict(life=0,query=query,phase=phase,method=method,checkpoint=label,replica=replica,
        seed=a.old.expected_train_seed(0,query,phase,episode) if training else a.evaluation_seed(0,phase,replica),
        max_steps=cap,result=result,initial_board=[1,1]+[0]*14,initial_spawns=[dict(cell=0,rank=1),dict(cell=1,rank=1)],
        final_board=[11]+[0]*15 if status=='WON' else [1]*16,actions=['LEFT']*n,spawned_cells=[0]*n,spawned_ranks=ranks,scores=[4]*n,
        bank_ids=ids,routing_events=events,cross_context_skips=skips,final_bank_id=router.module_id if banked else None)
    if training:row.update(episode_index=episode,transitions_before=transitions,transitions_after=transitions+n,
        terminal_update=status=='LOST' and n-1 not in skips,terminal_update_attempted=status=='LOST',
        analytic_terminal=status=='WON',censored_last_update=status=='CUTOFF')
    else:row.update(eval_id=f'0/{query}/{phase}/{method}/{label}/{replica}',reused_from=None)
    return row

def test_causal_route_and_cross_bank_skip():
    row=row_for(a.initial_router([1]*256),{0:100},episode=0)
    replay=a.replay_game(row,a.initial_router([1]*256),{0:100},True)
    assert all(replay['checks'].values()) and replay['skips']==[63] and replay['applied']==95
    for mutation,check in [('bank','causal_bank_ids'),('skip','cross_context_updates'),('event','route_events')]:
        bad=deepcopy(row)
        if mutation=='bank':bad['bank_ids'][0]=1
        elif mutation=='skip':bad['cross_context_skips']=[]
        else:bad['routing_events'][0]['observed_action_index']=0
        assert not a.replay_game(bad,a.initial_router([1]*256),{0:100},True)['checks'][check]

def test_cutoff_keeps_last_router_observation_without_terminal_td():
    router=a.initial_router([1]*256);banks={0:100}
    rows=[row_for(router,banks,n=3,episode=0,cap=5)]
    rows.append(row_for(router,banks,n=2,episode=1,cap=2,transitions=3,updates=103,status='CUTOFF'))
    found=a.inspect_training(rows,0,'reward','B',a.initial_router([1]*256),{0:100},100,budget=5,middle=3)
    assert all(found['checks'].values()) and found['prefixes'][5]['updates']==104
    assert found['prefixes'][5]['router']['observations_seen']==261
    bad=deepcopy(rows);bad[-1]['result']['updates_after']+=1
    assert not a.inspect_training(bad,0,'reward','B',a.initial_router([1]*256),{0:100},100,budget=5,middle=3)['checks']['td_timing']

def write_rows(path,rows):
    with gzip.open(path,'wt') as f:
        for row in rows:f.write(json.dumps(row)+'\n')

def write_model(path,updates):
    np.savez_compressed(path,indices=np.array([],dtype=np.int64),values=np.array([],dtype=float),
        metadata=json.dumps(dict(schema='controlled_predictive_ntuple_td_v120',radix=11,updates=updates)))
    return dict(path=str(path),updates=updates,nonzero_weights=0)

def manifest(router,banks,updates):
    return dict(schema='acfqp.ntuple_context.v122',training_enabled=True,updates=updates,active_bank_id=router.module_id,
        router=router.to_payload(),initial_router=a.initial_router([1]*256).to_payload(),
        banks=[dict(bank_id=k,updates=v) for k,v in sorted(banks.items())])

@pytest.fixture
def experiment(tmp_path,monkeypatch):
    monkeypatch.setattr(a,'LIVES',(0,));monkeypatch.setattr(a,'LABELS',(0,96,192));monkeypatch.setattr(a,'BUDGET',192);monkeypatch.setattr(a,'REPLICAS',2)
    settings=dict(lifecycles=[0],queries=dict(reward=dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.),risk_goal=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)),
        phases=a.old.P_FOUR,checkpoints=[0,96,192],train_transitions=192,replicas=2,max_steps=2000,workers=4,alpha=.0025,block_episodes=64,
        version_base=a.BASE,training_seed_version=121,context_initial_ranks=256,router_method='LIBRARY')
    src=dict(life=0,models={},initial_ranks={},initial_rank_sources={},continued={})
    inherited=dict(shared_v120=dict(v120_training=[]),v121_cont=[dict(life=0,queries={})])
    source=dict(schema='acfqp.context_bank.v122.source',snapshots=[src],inherited_costs=inherited)
    run=dict(status='complete',settings=settings,inherited_costs=inherited,lifecycles=[dict(life=0,queries={})])
    trace={'initial_board','initial_spawns','final_board','actions','spawned_cells','spawned_ranks','scores','bank_ids','routing_events','cross_context_skips','final_bank_id'}
    for query in a.QUERIES:
        folder=tmp_path/query;folder.mkdir();origin=write_model(folder/'origin.npz',100)
        src['models'][query]=origin;src['initial_ranks'][query]=[1]*256
        prefix_path=folder/'source.gz';write_rows(prefix_path,[dict(spawned_ranks=[1]*256)])
        src['initial_rank_sources'][query]=dict(path=str(prefix_path),rows_read=1,retained_ranks=256)
        router=a.initial_router([1]*256);banks={0:100};updates=100;ref=origin['path']
        data=dict(phases={},training_trace=f'{query}/train.gz',control_trace=f'{query}/outer.gz',model_setup=[],context_initialization=dict(router=router.to_payload(),seconds=0.))
        run['lifecycles'][0]['queries'][query]=data;src['continued'][query]={}
        inherited['v121_cont'][0]['queries'][query]=dict(phases={})
        def setup(method,phase,model):
            data['model_setup'].append(dict(method=method,phase_origin=phase,origin_ref=model['path'],updates_at_creation=model['updates'],
                load_counts=dict(checkpoint_loads=1,checkpoint_loaded_parameters=0),load_seconds=0.,setup_counts={},setup_seconds=0.))
        setup('FROZEN_A','B',origin);setup('BANK','B',origin)
        training=[];physical=[]
        for pi,phase in enumerate(a.PHASES):
            methods={};data['phases'][phase]=dict(p_four=a.old.P_FOUR[phase],methods=methods);cont=[]
            for label in a.LABELS:
                model=origin if phase=='B' and label==0 else write_model(folder/f'{phase}_{label}_cont.npz',100+pi*192+label)
                cont.append(dict(model,label=label,transitions=label))
                if not(phase=='B' and label==0):setup('CONT',phase,model)
            src['continued'][query][phase]=cont
            inherited['v121_cont'][0]['queries'][query]['phases'][phase]=dict(training_blocks=[dict(environment_counts=dict(sampled_transitions=192))])
            for method,sources in [('FROZEN_A',[dict(origin,label=0,transitions=0)]),('CONT',cont)]:
                cps=[];methods[method]=dict(checkpoints=cps)
                for model in sources:
                    cp=dict(label=model['label'],transitions=model['transitions'],updates=model['updates'],model_ref=model['path'],evaluations=[])
                    for rep in range(2):
                        row=row_for(a.initial_router([1]*256),{0:model['updates']},n=1,query=query,phase=phase,method=method,label=model['label'],replica=rep,updates=model['updates'])
                        if method=='CONT' and phase=='B' and model['label']==0:row['reused_from']=f'0/{query}/B/FROZEN_A/0/{rep}'
                        else:physical.append(row)
                        cp['evaluations'].append({k:v for k,v in row.items() if k not in trace})
                    cps.append(cp)
            bank_cps=[];rows=[]
            for label in a.LABELS:
                if label:
                    row=row_for(router,banks,query=query,phase=phase,episode=len(rows),transitions=label-96,cap=192-(label-96),n=96,updates=updates)
                    updates=row['result']['updates_after'];rows.append(row);training.append(row)
                m=manifest(router,banks,updates);cp=dict(label=label,transitions=label,updates=updates,model_ref=ref,bank_manifest=m,evaluations=[])
                if label:
                    files=[]
                    for b in m['banks']:
                        path=folder/f'{phase}_{label}_bank_{b["bank_id"]}.npz';write_model(path,b['updates'])
                        files.append(dict(bank_id=b['bank_id'],path=str(path.relative_to(tmp_path)),bytes=path.stat().st_size))
                    m['model_files']=files;path=folder/f'{phase}_{label}_manifest.json';path.write_text(json.dumps(m))
                    ref=str(path.relative_to(tmp_path));cp.update(model_ref=ref,model_bytes=sum(f['bytes'] for f in files),save_counts={},save_seconds=0.)
                for rep in range(2):
                    row=row_for(a.SpawnMemory.from_payload(m['router']),dict(banks),n=1,query=query,phase=phase,label=label,replica=rep,updates=updates)
                    physical.append(row);cp['evaluations'].append({k:v for k,v in row.items() if k not in trace})
                bank_cps.append(cp)
            start=bank_cps[0]
            found=a.inspect_training(rows,0,query,phase,a.SpawnMemory.from_payload(start['bank_manifest']['router']),
                {b['bank_id']:b['updates'] for b in start['bank_manifest']['banks']},start['updates'],budget=192,middle=96)
            methods['BANK']=dict(checkpoints=bank_cps,training_blocks=found['blocks'],training_episodes=2,final_updates=updates,final_transitions=192)
        write_rows(folder/'train.gz',training);write_rows(folder/'outer.gz',physical)
    (tmp_path/'run.json').write_text(json.dumps(run));(tmp_path/'source_capsule.json').write_text(json.dumps(source))
    return tmp_path

def test_full_cost_roster_and_return_routing(experiment):
    report=a.analyze(experiment)
    assert report['complete'] and report['primary_complete'],report['checks']
    assert report['costs']['training']['environment_counts']['sampled_transitions']==768
    assert report['costs']['physical_outer_games']==52 and report['costs']['logical_outer_rows']==56
    assert report['inherited_work']['v121_cont_training']['sampled_transitions']==768
    assert all(t['diagnostics']['first_source_observation']==64 for t in report['training'] if t['phase']=='A_RETURN')

@pytest.mark.parametrize('kind,check',[('alias','outer_aliases'),('prefix','checkpoint_prefix'),('inherit','inherited_cont_budget')])
def test_mutations_reject_completion(experiment,kind,check):
    p=experiment/'run.json';run=json.loads(p.read_text());srcpath=experiment/'source_capsule.json';source=json.loads(srcpath.read_text())
    md=run['lifecycles'][0]['queries']['reward']['phases']['B']['methods']
    if kind=='alias':md['CONT']['checkpoints'][0]['evaluations'][0]['reused_from']=None
    elif kind=='prefix':md['BANK']['checkpoints'][1]['transitions']+=1
    else:
        source['inherited_costs']['v121_cont'][0]['queries']['reward']['phases']['B']['training_blocks'][0]['environment_counts']['sampled_transitions']+=1
        run['inherited_costs']=source['inherited_costs'];srcpath.write_text(json.dumps(source))
    p.write_text(json.dumps(run));report=a.analyze(experiment)
    assert not report['checks'][check] and not report['primary_complete']

def test_outer_cutoff_is_charged_and_prevents_primary_completion(experiment):
    p=experiment/'run.json';run=json.loads(p.read_text())
    data=run['lifecycles'][0]['queries']['reward']
    cp=data['phases']['A_RETURN']['methods']['BANK']['checkpoints'][-1]
    m=cp['bank_manifest']
    row=row_for(a.SpawnMemory.from_payload(m['router']),{b['bank_id']:b['updates'] for b in m['banks']},
        phase='A_RETURN',n=2000,updates=cp['updates'],label=192,status='CUTOFF')
    physical=list(a.old.read_rows(experiment/data['control_trace']))
    physical[next(i for i,r in enumerate(physical) if r['eval_id']==row['eval_id'])]=row
    write_rows(experiment/data['control_trace'],physical)
    cp['evaluations'][0]={k:row[k] for k in cp['evaluations'][0]}
    p.write_text(json.dumps(run));report=a.analyze(experiment)
    assert report['complete'] and not report['primary_complete'],report['checks']
    assert report['costs']['actual_environment_transitions']==768+52+1999
