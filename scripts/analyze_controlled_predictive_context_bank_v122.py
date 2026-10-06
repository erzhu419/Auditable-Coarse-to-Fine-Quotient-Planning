"""Replay causal context routing and reconcile value-bank adaptation evidence."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import groupby
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from scripts import analyze_controlled_predictive_ntuple_regime_v121 as old

LIVES, QUERIES, PHASES = tuple(range(4)), ('reward','risk_goal'), ('B','A_RETURN')
LABELS, BUDGET, REPLICAS, BASE = (0,131072,524288), 524288, 8, 122*100000000
PARAMETERS, DENSE_BYTES = 4*11**6, 4*11**6*8


def evaluation_seed(life, phase, replica):
    return BASE+90000000+life*100000+PHASES.index(phase)*10000+replica


def initial_router(ranks):
    router=SpawnMemory('LIBRARY')
    for rank in ranks: router.observe(rank)
    return router


def replay_game(row, router, bank_updates, training):
    """Replay only the frozen inexpensive router, never ground-board dynamics."""
    r=row['result']; n=r['steps']; before=router.counts.copy()
    start_id, start_obs=router.module_id,router.observations_seen
    checks=dict(causal_bank_ids=True, route_events=True, cross_context_updates=True,
        router_observations=True, routing_counts=True)
    events, skips, source_actions, error, creations, applied=[],[],0,0.,0,0
    first_source=0 if start_id==0 else None
    for i,rank in enumerate(row['spawned_ranks']):
        active=router.module_id
        checks['causal_bank_ids'] &= i<len(row['bank_ids']) and row['bank_ids'][i]==active
        source_actions += active==0
        module=router.modules[active]
        error += abs(module['alpha']/(module['alpha']+module['beta'])-old.P_FOUR[row['phase']])
        event=router.observe(rank)
        if event is not None:
            events.append(dict(event,observed_action_index=i))
            if event['kind']=='created':
                bank_updates[event['module_id']]=bank_updates[event['previous_module_id']]
                creations+=1
        if first_source is None and router.module_id==0: first_source=i+1
        eligible=training and (i<n-1 or r['status']=='LOST')
        if eligible:
            if active!=router.module_id: skips.append(i)
            else: bank_updates[active]+=1; applied+=1
    checks['causal_bank_ids'] &= len(row['bank_ids'])==n and row['final_bank_id']==router.module_id
    checks['route_events'] &= row['routing_events']==events
    checks['cross_context_updates'] &= row['cross_context_skips']==skips
    checks['router_observations'] &= (r['active_bank_before']==start_id
        and r['active_bank_after']==router.module_id
        and r['router_observations_before']==start_obs
        and r['router_observations_after']==start_obs+n)
    counts=r['learning_counts']
    for key,value in router.counts.items():
        checks['routing_counts'] &= counts.get('router_'+key,0)==value-before.get(key,0)
    checks['routing_counts'] &= (counts.get('bank_creations',0)==creations
        and counts.get('cross_context_update_skips',0)==len(skips))
    if training:
        checks['routing_counts'] &= (counts.get('bank_weight_copies',0)==creations
            and counts.get('bank_copied_bytes',0)==creations*DENSE_BYTES
            and counts.get('bank_copied_parameters',0)==creations*PARAMETERS)
    else:
        checks['routing_counts'] &= (not counts.get('bank_weight_copies',0)
            and counts.get('evaluation_weight_views',0)==len(bank_updates)
            and counts.get('evaluation_shared_parameters',0)==len(bank_updates)*PARAMETERS)
    return dict(checks=checks, applied=applied, skips=skips,
        diagnostics=dict(decisions=n,source_bank_decisions=source_actions,
            absolute_probability_error_sum=error,first_source_observation=first_source,
            creations=creations,reactivations=sum(e['kind']=='reactivated' for e in events)))


def inspect_training(rows, life, query, phase, router, bank_updates, updates,
                     budget=BUDGET,middle=LABELS[1]):
    checks=dict(training_roster=True, training_streams=True, training_trace=True,
        exact_training_budget=True, td_timing=True, new_counter_deltas=True,
        training_caps=True, no_model_spawns=True)
    cost=old.new_cost(); block=old.empty_block(0,0); blocks=[]
    prefix={0:dict(transitions=0,updates=updates,router=router.to_payload(),bank_updates=dict(bank_updates))}
    transitions=episodes=0; diagnostics=Counter()
    first_source=0 if router.module_id==0 else None
    for i,row in enumerate(rows):
        r=row['result']; n=r['steps']; status=r['status']
        checks['training_roster'] &= (row['life']==life and row['query']==query
            and row['phase']==phase and row['method']=='BANK' and row['episode_index']==i)
        checks['training_streams'] &= row['seed']==old.expected_train_seed(life,query,phase,i)
        checks['training_trace'] &= old.compact_valid(row) and status in ('WON','LOST','CUTOFF')
        cap=min(2000,budget-transitions)
        checks['training_caps'] &= row['max_steps']==cap and 0<n<=cap and (status!='CUTOFF' or n==cap)
        checks['exact_training_budget'] &= row['transitions_before']==transitions and row['transitions_after']==transitions+n<=budget
        replay=replay_game(row,router,bank_updates,True)
        for k,v in replay['checks'].items(): checks[k]=checks.get(k,True) and v
        delta=replay['applied']; skips=replay['skips']; learn=r['learning_counts']
        checks['td_timing'] &= (r['updates_before']==updates and r['updates_after']==updates+delta
            and delta==n-int(status in ('WON','CUTOFF'))-len(skips)
            and row['terminal_update_attempted']==(status=='LOST')
            and row['terminal_update']==(status=='LOST' and n-1 not in skips)
            and row['analytic_terminal']==(status=='WON')
            and row['censored_last_update']==(status=='CUTOFF'))
        checks['new_counter_deltas'] &= (learn.get('td_updates',0)==delta
            and learn.get('choose_calls',0)==n and learn.get('table_update_occurrences',0)==32*delta)
        checks['no_model_spawns'] &= all(not r.get(f,{}).get('model_spawn_samples',0) for f in old.FIELDS)
        d=replay['diagnostics']
        if first_source is None and d['first_source_observation'] is not None:
            first_source=transitions+d['first_source_observation']
        diagnostics.update({k:v for k,v in d.items() if k!='first_source_observation'})
        old.add_cost(cost,row); transitions+=n; episodes+=1; updates=r['updates_after']
        block.update(end=episodes,transitions_after=transitions)
        block['games']+=1;block['statuses'][status]+=1;block['total_score']+=r['score'];block['seconds']+=r['seconds']
        for f in ('environment_counts','learning_counts'):block[f].update(r[f])
        block.setdefault('setup_counts',Counter()).update(r['setup_counts'])
        block['setup_seconds']=block.get('setup_seconds',0.)+r['setup_seconds']
        label=middle if middle not in prefix and transitions>=middle else None
        if transitions==budget:label=budget
        if label is not None:
            prefix[label]=dict(transitions=transitions,updates=updates,router=router.to_payload(),bank_updates=dict(bank_updates))
        if episodes%64==0 or label is not None:
            blocks.append(block);block=old.empty_block(episodes,transitions)
    if block['games']:blocks.append(block)
    checks['exact_training_budget'] &= transitions==budget and middle in prefix
    return dict(checks=checks,cost=cost,blocks=blocks,prefixes=prefix,episodes=episodes,
        diagnostics=dict(diagnostics,first_source_observation=first_source,
            final_bank_count=len(bank_updates),resident_bank_bytes=len(bank_updates)*DENSE_BYTES))


def outer_valid(row,checkpoint):
    r=row['result'];counts=r['learning_counts']
    ready=(old.compact_valid(row) and row['seed']==evaluation_seed(row['life'],row['phase'],row['replica'])
        and row['max_steps']==2000 and r['status'] in ('WON','LOST','CUTOFF')
        and (r['status']!='CUTOFF' or r['steps']==2000)
        and r['updates_before']==r['updates_after']==checkpoint['updates']
        and counts.get('td_updates',0)==0 and counts.get('choose_calls',0)==r['steps'])
    diagnostics=None
    if row['method']=='BANK':
        m=checkpoint['bank_manifest']; router=SpawnMemory.from_payload(m['router'])
        banks={b['bank_id']:b['updates'] for b in m['banks']}
        replay=replay_game(row,router,banks,False)
        ready &= all(replay['checks'].values());diagnostics=replay['diagnostics']
    else:
        ready &= not row['bank_ids'] and not row['routing_events'] and not row['cross_context_skips']
    return bool(ready),diagnostics


def summaries(indexed,valid,cps):
    methods={};contrasts={}
    for phase in PHASES:
        methods[phase]={}
        for method in ('BANK','CONT','FROZEN_A'):
            methods[phase][method]={}
            for label in ((0,) if method=='FROZEN_A' else LABELS):
                methods[phase][method][str(label)]={}
                for query in QUERIES:
                    lives=[]
                    for life in LIVES:
                        keys=[(life,query,phase,method,label,rep) for rep in range(REPLICAS)]
                        games=[indexed[k] for k in keys if k in indexed]
                        complete=len(games)==REPLICAS and all(valid.get(k,False) for k in keys)
                        lives.append(dict(life=life,complete=complete,games=len(games),
                            training_transitions=cps[(life,query,phase,method,label)]['transitions'],
                            means={f:old.mean(g['result'][f] for g in games) if complete else None for f in old.METRICS},
                            wins=sum(g['result']['status']=='WON' for g in games)))
                    methods[phase][method][str(label)][query]=dict(lifecycles=lives,
                        lifecycle_mean={f:old.mean(l['means'][f] for l in lives) for f in old.METRICS},
                        wins=sum(l['wins'] for l in lives),games=sum(l['games'] for l in lives))
        contrasts[phase]={}
        for label in LABELS:
            for right in ('CONT','FROZEN_A'):
                other=0 if right=='FROZEN_A' else label
                contrasts[phase][f'BANK_{label}_minus_{right}']={q:old.comparisons(
                    methods[phase]['BANK'][str(label)][q],methods[phase][right][str(other)][q]) for q in QUERIES}
    return dict(methods=methods,comparisons=contrasts)


def analyze(directory):
    run=json.loads((directory/'run.json').read_text())
    source=json.loads((directory/'source_capsule.json').read_text())
    expected_settings=dict(lifecycles=list(LIVES),queries=dict(
        reward=dict(reward_weight=1.,failure_penalty=0.,goal_bonus=0.),
        risk_goal=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)),
        phases=old.P_FOUR,checkpoints=list(LABELS),train_transitions=BUDGET,
        replicas=REPLICAS,max_steps=2000,workers=4,alpha=.0025,block_episodes=64,
        version_base=BASE,training_seed_version=121,context_initial_ranks=256,router_method='LIBRARY')
    checks=dict(frozen_settings=run['settings']==expected_settings,
        lifecycle_roster=len(run['lifecycles'])==len(LIVES) and {l['life'] for l in run['lifecycles']}==set(LIVES),
        source_roster=source['schema']=='acfqp.context_bank.v122.source' and
            len(source['snapshots'])==len(LIVES) and {s['life'] for s in source['snapshots']}==set(LIVES),
        inherited_costs_match=source['inherited_costs']==run['inherited_costs'],
        phase_method_roster=True,checkpoint_roster=True,model_origins=True,
        source_rank_prefix=True,context_initialization=True,bank_manifests=True,
        sparse_models=True,training_group_roster=True,training_blocks=True,
        checkpoint_prefix=True,model_setup=True,outer_roster=True,outer_aliases=True,
        outer_summary_match=True,outer_no_td_causal_routing=True)
    cps={};indexed={};valid={};training=[];outer_diagnostics=[]
    cost=old.new_cost();outer_cost=old.new_cost()
    train_by_phase={p:old.new_cost() for p in PHASES}
    outer_by_method={m:old.new_cost() for m in ('BANK','CONT','FROZEN_A')}
    setup_counts,loads,save_counts,initial_counts=Counter(),Counter(),Counter(),Counter()
    setup_seconds=load_seconds=save_seconds=initial_seconds=eval_copy_seconds=0.
    stored_bytes=physical=aliases=0;peak_banks=0;sparse_cache={}
    def sparse(path,updates,size=None):
        key=(str(path),updates,size)
        if key not in sparse_cache:
            cp=dict(model_ref=str(path),updates=updates)
            if size is not None:cp['model_bytes']=size
            sparse_cache[key]=old.model_valid(directory,cp)
        return sparse_cache[key]
    sources={s['life']:s for s in source['snapshots']}
    for life_data in run['lifecycles']:
        life=life_data['life'];src=sources[life]
        checks['lifecycle_roster'] &= set(life_data['queries'])==set(QUERIES)
        for query,data in life_data['queries'].items():
            origin=src['models'][query];ranks=src['initial_ranks'][query]
            actual=[];rows_read=0
            for row in old.read_rows(Path(src['initial_rank_sources'][query]['path'])):
                rows_read+=1;actual.extend(row['spawned_ranks'][:256-len(actual)])
                if len(actual)==256:break
            checks['source_rank_prefix'] &= len(ranks)==256 and ranks==actual and rows_read==src['initial_rank_sources'][query]['rows_read']
            router=initial_router(ranks);bank_updates={0:origin['updates']}
            initial_counts.update(router.counts);initial_seconds+=data['context_initialization']['seconds']
            checks['context_initialization'] &= data['context_initialization']['router']==router.to_payload()
            checks['phase_method_roster'] &= set(data['phases'])==set(PHASES)
            for phase in PHASES:
                pd=data['phases'][phase]
                checks['phase_method_roster'] &= pd['p_four']==old.P_FOUR[phase] and set(pd['methods'])=={'BANK','CONT','FROZEN_A'}
                for method,md in pd['methods'].items():
                    labels=(0,) if method=='FROZEN_A' else LABELS
                    checks['checkpoint_roster'] &= [c['label'] for c in md['checkpoints']]==list(labels)
                    for cp in md['checkpoints']:
                        key=(life,query,phase,method,cp['label']);cps[key]=cp
                        if method!='BANK':
                            source_cp=origin if method=='FROZEN_A' else next(c for c in src['continued'][query][phase] if c['label']==cp['label'])
                            checks['model_origins'] &= (cp['model_ref']==source_cp['path'] and cp['updates']==source_cp['updates']
                                and cp['transitions']==source_cp.get('transitions',0))
                            checks['sparse_models'] &= sparse(Path(cp['model_ref']),cp['updates'])
                        else:
                            m=cp['bank_manifest'];ids=[b['bank_id'] for b in m['banks']]
                            checks['bank_manifests'] &= (m['schema']=='acfqp.ntuple_context.v122' and m['training_enabled']
                                and ids==list(range(len(ids))) and m['active_bank_id']==m['router']['active_module_id']
                                and m['updates']==cp['updates'] and m['initial_router']==initial_router(ranks).to_payload()
                                and len(ids)==len(m['router']['modules']))
                            peak_banks=max(peak_banks,len(ids))
                            if cp['label']:
                                saved=json.loads((directory/cp['model_ref']).read_text())
                                checks['bank_manifests'] &= saved==m and len(m['model_files'])==len(ids)
                                file_by_id={f['bank_id']:f for f in m['model_files']}
                                for b in m['banks']:
                                    f=file_by_id[b['bank_id']]
                                    checks['sparse_models'] &= sparse(directory/f['path'],b['updates'],f['bytes'])
                                checks['bank_manifests'] &= cp['model_bytes']==sum(f['bytes'] for f in m['model_files'])
                                stored_bytes+=cp['model_bytes'];save_counts.update(cp['save_counts']);save_seconds+=cp['save_seconds']
                            elif phase=='B':
                                checks['model_origins'] &= cp['model_ref']==origin['path'] and ids==[0] and cp['updates']==origin['updates']
                                checks['sparse_models'] &= sparse(Path(origin['path']),origin['updates'])
                            else:
                                b=cps[(life,query,'B','BANK',BUDGET)]
                                checks['model_origins'] &= (cp['model_ref']==b['model_ref'] and cp['updates']==b['updates']
                                    and m['router']==b['bank_manifest']['router'] and m['banks']==b['bank_manifest']['banks'])
            groups=[];updates=origin['updates']
            for phase,rows in groupby(old.read_rows(directory/data['training_trace']),key=lambda r:r['phase']):
                groups.append(phase)
                found=inspect_training(rows,life,query,phase,router,bank_updates,updates,budget=BUDGET,middle=LABELS[1])
                for k,v in found['checks'].items():checks[k]=checks.get(k,True) and v
                md=data['phases'][phase]['methods']['BANK']
                checks['training_blocks'] &= md['training_blocks']==found['blocks'] and md['training_episodes']==found['episodes']
                for label in LABELS:
                    cp=cps[(life,query,phase,'BANK',label)];prefix=found['prefixes'][label];m=cp['bank_manifest']
                    checks['checkpoint_prefix'] &= (cp['transitions']==prefix['transitions'] and cp['updates']==prefix['updates']
                        and m['router']==prefix['router'] and {b['bank_id']:b['updates'] for b in m['banks']}==prefix['bank_updates'])
                updates=found['prefixes'][BUDGET]['updates']
                checks['checkpoint_prefix'] &= md['final_updates']==updates and md['final_transitions']==BUDGET
                old.merge_cost(cost,found['cost']);old.merge_cost(train_by_phase[phase],found['cost'])
                training.append(dict(life=life,query=query,phase=phase,diagnostics=found['diagnostics'],
                    games=found['episodes'],cost=found['cost'],checks=found['checks']))
            checks['training_group_roster'] &= groups==list(PHASES)
            expected_setups=[('FROZEN_A','B',origin),('BANK','B',origin)]+[
                ('CONT',phase,c) for phase in PHASES for c in src['continued'][query][phase] if not(phase=='B' and c['label']==0)]
            checks['model_setup'] &= len(data['model_setup'])==len(expected_setups)
            for entry,(method,phase,model) in zip(data['model_setup'],expected_setups):
                checks['model_setup'] &= (entry['method']==method and entry['phase_origin']==phase
                    and entry['origin_ref']==model['path'] and entry['updates_at_creation']==model['updates']
                    and entry['load_counts']==dict(checkpoint_loads=1,checkpoint_loaded_parameters=model['nonzero_weights']))
                setup_counts.update(entry['setup_counts']);loads.update(entry['load_counts'])
                setup_seconds+=entry['setup_seconds'];load_seconds+=entry['load_seconds']
            raw=list(old.read_rows(directory/data['control_trace']));raw_index={r['eval_id']:r for r in raw}
            logical=[r for phase in PHASES for md in data['phases'][phase]['methods'].values() for cp in md['checkpoints'] for r in cp['evaluations']]
            expected={(life,query,p,m,c,rep) for p in PHASES for m in ('BANK','CONT','FROZEN_A')
                for c in ((0,) if m=='FROZEN_A' else LABELS) for rep in range(REPLICAS)}
            alias_keys={(life,query,'B','CONT',0,rep) for rep in range(REPLICAS)}
            checks['outer_roster'] &= (len(logical)==len(expected) and {old.outer_key(r) for r in logical}==expected
                and len(raw)==len(raw_index)==len(expected-alias_keys) and {old.outer_key(r) for r in raw}==expected-alias_keys)
            for row in raw:
                physical+=1;old.add_cost(outer_cost,row);old.add_cost(outer_by_method[row['method']],row)
                eval_copy_seconds+=row['result'].get('evaluation_copy_seconds',0.)
                checks['outer_aliases'] &= row['reused_from'] is None
            for row in logical:
                key=old.outer_key(row);alias=key in alias_keys;reuse=row['reused_from'];cp=cps[key[:-1]]
                aliases+=alias;ref=raw_index.get(reuse or row['eval_id'])
                okay=bool(reuse)==alias and row['eval_id']=='/'.join(map(str,key))
                if alias:okay &= reuse==f'{life}/{query}/B/FROZEN_A/0/{row["replica"]}'
                checks['outer_aliases'] &= okay
                omitted={'eval_id','reused_from','method','checkpoint'} if alias else set()
                matches=ref is not None and all(ref.get(k)==v for k,v in row.items() if k not in omitted)
                checks['outer_summary_match'] &= matches
                ready,diag=outer_valid({**ref,**row},cp) if ref is not None else (False,None)
                checks['outer_no_td_causal_routing'] &= ready
                indexed[key]=row;valid[key]=ready and okay and matches and row['result']['status']!='CUTOFF'
                if diag is not None:outer_diagnostics.append(dict(life=life,query=query,phase=row['phase'],checkpoint=row['checkpoint'],replica=row['replica'],**diag))
    expected_new=len(LIVES)*len(QUERIES)*len(PHASES)*BUDGET
    checks['aggregate_budget']=cost['environment_counts']['sampled_transitions']==expected_new
    cohort=len(LIVES)*len(QUERIES)*REPLICAS
    checks['physical_logical_roster']=physical==13*cohort and len(indexed)==14*cohort and aliases==cohort
    prior=Counter();continued=Counter()
    for l in source['inherited_costs']['shared_v120']['v120_training']:
        for q in l['queries'].values():
            for b in q['training_blocks']:prior.update(b['environment_counts'])
    for l in source['inherited_costs']['v121_cont']:
        for q in l['queries'].values():
            for p in q['phases'].values():
                for b in p['training_blocks']:continued.update(b['environment_counts'])
    checks['inherited_cont_budget']=continued['sampled_transitions']==expected_new
    complete=run['status']=='complete' and all(checks.values())
    return dict(schema='acfqp.context_bank.v122.analysis',complete=complete,
        primary_complete=complete and all(valid.values()),checks={k:bool(v) for k,v in checks.items()},
        control=summaries(indexed,valid,cps),training=training,outer_routing=outer_diagnostics,
        costs=dict(training=cost,training_by_phase=train_by_phase,outer=outer_cost,outer_by_method=outer_by_method,
            physical_outer_games=physical,logical_outer_rows=len(indexed),reused_outer_rows=aliases,
            actual_environment_transitions=cost['environment_counts']['sampled_transitions']+outer_cost['environment_counts']['sampled_transitions'],
            model_load_counts=dict(loads),model_load_seconds=load_seconds,setup_counts=dict(setup_counts),setup_seconds=setup_seconds,
            source_context_processing_counts=dict(initial_counts),source_context_seconds=initial_seconds,
            model_save_counts=dict(save_counts),model_save_seconds=save_seconds,retained_model_bytes=stored_bytes,
            peak_resident_bank_count=peak_banks,peak_resident_bank_bytes=peak_banks*DENSE_BYTES,
            evaluation_copy_seconds=eval_copy_seconds,
            model_spawn_samples=sum(c[f].get('model_spawn_samples',0) for c in (cost,outer_cost) for f in old.FIELDS)),
        inherited_work=dict(v120_training=dict(prior),v121_cont_training=dict(continued),details=source['inherited_costs']),
        seconds=run.get('seconds'),scope='Fixed context-library mechanism, matched V121 training streams and fresh paired outer cohort; no structural learning or significance claim.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args();report=analyze(args.run_dir)
    (args.run_dir/'analysis.json').write_text(json.dumps(report,allow_nan=False,indent=2)+'\n')
    print(json.dumps(dict(complete=report['complete'],primary_complete=report['primary_complete'],checks=report['checks'])))
