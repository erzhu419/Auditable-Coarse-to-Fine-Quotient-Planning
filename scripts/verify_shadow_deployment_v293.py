#!/usr/bin/env python3
"""Compact independent audit of shared shadow learning and validation deployment."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from math import sqrt
from pathlib import Path
from statistics import mean
from types import SimpleNamespace

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_episode_consolidation_v290 import check_contrast
from verify_natural_online_value_v286 import Memory, planning_counts, terminal
from verify_natural_episode_v292 import check_training_chunk, check_game_fit, accumulate, learned

ARMS=('FROZEN_H2','UNCONDITIONAL_H2','VALIDATED_H2')
PHASES=('A','B','A_prime')
CARRIER_RAW=65536
ONLINE_RAW=262144
T_CRITICAL=2.364624251


def warmup_seed(life,game):return 293100010000+life*1000000+game
def carrier_seed(life):return 293200010000+life*10000000
def deployment_seed(life,arm):return 293400010000+life*10000000+ARMS.index(arm)*1000000
def validation_seed(life,phase,pair):return 293600010000+life*1000000+phase*100000+pair
def evaluation_seed(life,phase,game):return 293900010000+life*1000000+phase*100000+game


def paired_decision(deltas,cutoffs,arm):
    require(len(deltas)==8 and arm in ARMS,'eight fixed paired validation games')
    center=mean(deltas)
    se=sqrt(sum((delta-center)**2 for delta in deltas)/(8*7))
    interval=[center-T_CRITICAL*se,center+T_CRITICAL*se]
    accepted=arm=='UNCONDITIONAL_H2' or (arm=='VALIDATED_H2' and cutoffs==0 and interval[0]>0)
    return dict(mean=center,standard_error=se,ci95=interval,accepted=accepted)


def check_games(games,seeds,counts):
    require(len(games)==len(seeds) and [g['seed'] for g in games]==seeds,'declared complete paired/science seeds')
    for game in games:
        require(1<=game['steps']<=8192,'complete game cap')
        if game['status']=='CUTOFF':
            require(game['steps']==8192 and max(game['final_board'])<11,'premature cutoff/goal cutoff');bonus=0.
        else:terminal(game['final_board'],game['status']);bonus=4. if game['status']=='WON' else -4.
        require(game['utility']==game['score']/2048.+bonus,'complete utility/terminal')
    steps,wins=sum(g['steps'] for g in games),sum(g['status']=='WON' for g in games);initial=2*len(games)
    env=dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=initial,
        raw_tile_productions=steps+initial,environment_random_draws=2*(steps+initial),
        ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+len(games),
        ground_status_internal_swipe_calls=4*(steps+len(games)-wins),
        ground_swipe_calls=steps+4*(steps+len(games)-wins))
    require(Counter(counts['environment'])==Counter(env),'all physical complete-game raw costs, including initial')
    planning_counts(counts['planning'],steps,2)
    return dict(mean_game_utility=mean(g['utility'] for g in games),games=len(games),wins=wins,
        losses=sum(g['status']=='LOST' for g in games),cutoffs=sum(g['status']=='CUTOFF' for g in games),
        cutoff_episodes=[i for i,g in enumerate(games) if g['status']=='CUTOFF'],steps=steps)


def check_warmup(row,index,memory):
    require(memory.obs<256,'shared warmup continued after threshold')
    game=row['summary'];steps=game['steps'];raw=row['raw_spawns']
    require(game['seed']==warmup_seed(row['lifecycle'],index),'fresh warmup seed')
    terminal(row['final_board'],game['status']);won=game['status']=='WON'
    require(game['utility']==game['score']/2048.+(4. if won else -4.)
        and len(row['actions'])==len(row['scores'])==steps and sum(row['scores'])==game['score'],'warmup actual scores/terminal utility')
    require(len(raw)==steps+2 and [r['kind'] for r in raw[:2]]==['INITIAL','INITIAL']
        and all(r['kind']=='POST_ACTION' for r in raw[2:]),'warmup all initial/post-action observations')
    env=dict(initial_spawns=2,sampled_transitions=steps,environment_random_draws=2*(steps+2),
        ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+1,
        ground_status_internal_swipe_calls=4*(steps+1-won),ground_swipe_calls=steps+4*(steps+1-won))
    require(Counter(row['counts']['environment'])==Counter(env),'warmup physical counts')
    direct=Counter(row['counts']['direct'])
    require(direct['choose_calls']==direct['inner_choose_calls']==steps and direct['inner_learned_swipe_calls']==4*steps
        and direct['inner_line_table_lookups']==4*direct['inner_learned_swipe_calls']
        and direct['inner_table_lookups']==32*direct['inner_value_predictions']
        and direct['td_updates']==direct['inner_td_updates']==0,'shared readonly DIRECT work')
    return memory.consume(r['rank'] for r in raw)


def check_passive_chunk(row,remaining,p):
    # These streams have a fixed observed carrier probability and no observer.
    # Use the established chronology/cost proof with a 64-raw native call cap;
    # there is no adaptive memory block or value learning on this path.
    knowledge=SimpleNamespace(n=0,active=0,probability=lambda:p)
    projected=dict(row,arm='FROZEN_H2',depth=2,active_bank_id=0,module_id_before=0)
    return check_training_chunk(projected,remaining,knowledge)


def check_submission(row,pairs,old_id,proposal_id,shadow_updates):
    require(len(pairs)==8,'submission before all eight pairs')
    deltas=[pair['candidate']['utility']-pair['incumbent']['utility'] for pair in pairs]
    cutoffs=[i for i,pair in enumerate(pairs) if any(pair[branch]['status']=='CUTOFF' for branch in ('incumbent','candidate'))]
    gate=row['gate'];decision=paired_decision(deltas,len(cutoffs),row['arm'])
    require(gate['pairs']==8 and gate['pair_deltas']==deltas and close(gate['mean_delta'],decision['mean'])
        and close(gate['standard_error'],decision['standard_error'])
        and close(gate['sample_std'],decision['standard_error']*sqrt(8))
        and close(gate['lower95'],decision['ci95'][0]) and gate['t_critical']==T_CRITICAL
        and gate['no_cutoffs']==(not cutoffs) and gate['cutoff_pairs']==cutoffs
        and gate['accept']==(not cutoffs and decision['ci95'][0]>0),'paired Student-t selector recomputation')
    candidate_id=0 if row['arm']=='FROZEN_H2' else proposal_id
    deployed=candidate_id if decision['accepted'] else old_id
    rule='FROZEN_SOURCE' if row['arm']=='FROZEN_H2' else 'ALWAYS' if row['arm']=='UNCONDITIONAL_H2' else 'PAIRED_T_LOWER95_POSITIVE_NO_CUTOFF'
    require(row['previous_submission_id']==old_id and row['candidate_submission_id']==candidate_id
        and row['deployed_submission_id']==deployed and row['accepted']==decision['accepted']
        and row['rule']==rule and row['shadow_value_updates']==shadow_updates,'declared candidate/deployment version/rule')
    return deployed


def read_canonical(d):
    lives={row['lifecycle']:row for row in d['by_lifecycle']};states={};rows_read=0
    require([p['parent'] for p in d['parent_receipts']]==list(range(4)),'four physical sources')
    for parent in d['parent_receipts']:
        pid=parent['parent'];require(parent['lifecycle_ids']==list(range(pid,16,4)),'source/life roster')
        path=Path(parent['trace_file']);require(path.stat().st_size==parent['trace_bytes'],'canonical trace storage')
        with gzip.open(path,'rt') as stream:
            for line in stream:
                row=json.loads(line);rows_read+=1;life=row['lifecycle']
                require(life in parent['lifecycle_ids'] and row['parent']==pid,'canonical source/life context')
                if life not in states:
                    states[life]=dict(memory=Memory(),warm_games=[],warm_events=[],warm_environment=Counter(),warm_direct=Counter(),
                        carrier_stream=None,pending_fit=None,scores=defaultdict(list),updates=0,copies=[],phase_index=0,
                        carrier_phases={},slots={},deployments={},checkpoints={},incumbents=dict.fromkeys(ARMS,0),
                        submissions={},fit_totals=dict(fitted_games=0,fitted_steps=0,trained_afterstates=0,
                            learning_counts={},target_counts={},consolidation_counts={},setup_counts={},seconds=0.,cpu_seconds=0.))
                state=states[life];memory=state['memory'];kind=row['kind']
                if kind=='WARMUP':
                    require(state['carrier_stream'] is None,'warmup after carrier acquisition')
                    state['warm_events'].extend(check_warmup(row,len(state['warm_games']),memory))
                    state['warm_games'].append(row['summary']);state['warm_environment'].update(row['counts']['environment'])
                    state['warm_direct'].update(row['counts']['direct']);continue
                require(state['pending_fit'] is None or kind=='SHADOW_FIT','candidate/activity preceded immediate shadow game fit')
                if kind=='CARRIER_TRAIN':
                    phase=row['phase'];index=PHASES.index(phase)
                    if state['carrier_stream'] is None:
                        require(memory.obs>=256 and row['start']['raw_tiles']==0
                            and row['start']['stream_seed']==carrier_seed(life),'shared fresh carrier lacks warmup/seed')
                        state.update(warm_memory=memory.learned(),warm_counts=memory.counts.copy(),warm_raw=memory.obs)
                    else:require(row['start']==state['carrier_stream'],'source carrier resets across phases')
                    if index!=state['phase_index']:
                        require(index==state['phase_index']+1 and all((PHASES[index-1],arm) in state['checkpoints'] for arm in ARMS),
                            'next proposal trained before all old-phase activity finished')
                        state['phase_index']=index
                    phase_state=state['carrier_phases'].setdefault(phase,dict(before_stream=row['start'],before_memory=memory.counts.copy(),
                        chunks=0,events=0,cutoffs=0,counts={k:Counter() for k in ('environment','planning','learning')},shadow=Counter(),realized_utility=0.))
                    projected=dict(row,arm='FROZEN_H2',depth=2,active_bank_id=0)
                    require(row['leaf_updates_before']==row['leaf_updates_after']==0,'source carrier learned')
                    check_training_chunk(projected,(index+1)*CARRIER_RAW-row['start']['raw_tiles'],memory)
                    rewards=iter(row['scores'])
                    for spawn in row['raw_spawns']:
                        if spawn['kind']=='POST_ACTION':state['scores'][spawn['episode']].append(next(rewards))
                    events=memory.consume(spawn['rank'] for spawn in row['raw_spawns'])
                    require(events==row['memory_events'],'carrier-only observed-prefix router')
                    phase_state['chunks']+=1;phase_state['events']+=len(events)
                    for part in phase_state['counts']:phase_state['counts'][part].update(row['counts'][part])
                    phase_state['realized_utility']+=sum(row['scores'])/2048.+sum(4. if g['status']=='WON' else -4. if g['status']=='LOST' else 0.
                        for g in row['completed_games'])
                    state['carrier_stream']=row['end']
                    if row['completed_games']:
                        state['pending_fit']=row['completed_games'][0]
                        phase_state['cutoffs']+=row['completed_games'][0]['status']=='CUTOFF'
                    continue
                if kind=='SHADOW_FIT':
                    pending=state['pending_fit'];require(pending is not None,'shadow fit with no complete source game')
                    projected=dict(row,arm='MEAN_H2')
                    added=check_game_fit(projected,pending,state['scores'][pending['episode']],state['updates'])
                    state['updates']+=added;phase_state=state['carrier_phases'][row['phase']]
                    if row['fitted']:
                        fit=row['fit'];totals=state['fit_totals']
                        for field in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):totals[field]+=fit[field]
                        for field in ('learning_counts','target_counts','consolidation_counts','setup_counts'):accumulate(totals[field],fit[field])
                        phase_state['shadow'].update(fit['learning_counts'])
                    state['pending_fit']=None;del state['scores'][pending['episode']];continue
                if kind=='HEAD_COPY':
                    require(row['private_weight_bytes']==row['setup_counts']['source_weight_bytes_copied']==row['setup_counts']['snapshot_weight_bytes_copied']
                        and row['private_weight_bytes']==8*row['setup_counts']['snapshot_parameters_copied'],'actual head initialization/snapshot copy bytes')
                    if row['purpose']=='CANDIDATE':
                        index=row['submission_id']-1;require(index==state['phase_index'] and state['carrier_stream']['raw_tiles']==(index+1)*CARRIER_RAW
                            and row['copied_from_value_updates']==state['updates'],'proposal snapshot not the same persistent shadow prefix')
                        state['proposal_id']=row['submission_id'];state['proposal_updates']=state['updates'];state['p']=memory.probability()
                        state['carrier_phases'][PHASES[index]].update(memory_after=memory.counts.copy(),
                            memory_snapshot=memory.learned(),stream_snapshot=deepcopy(state['carrier_stream']),shadow_updates=state['updates'])
                    else:
                        arm=row['purpose'].removeprefix('RETAINED_A_');require(arm in ARMS and state['phase_index']==0
                            and row['submission_id']==state['incumbents'][arm] and row['copied_from_value_updates']==0,'saved A deployment origin')
                    state['copies'].append({k:v for k,v in row.items() if k not in ('kind','lifecycle','parent')});continue
                arm=row['arm'];phase=row['phase'];index=PHASES.index(phase)
                require(arm in ARMS and index==state['phase_index'],'activity arm/proposal phase')
                require(memory.probability()==state['p'],'validation or deployment fed the shared belief')
                if kind in ('VALIDATION_TRAIN','VALIDATION_GAME'):
                    key=(phase,arm,row['pair_index'],row['branch']);require(row['branch'] in ('incumbent','candidate') and 0<=row['pair_index']<8,'fixed validation slot')
                    slot=state['slots'].setdefault(key,dict(last=None,counts={k:Counter() for k in ('environment','planning','learning')},completion=None))
                    expected_id=state['incumbents'][arm] if row['branch']=='incumbent' else 0 if arm=='FROZEN_H2' else state['proposal_id']
                    require(row['submission_id']==expected_id and row['model_p_four']==state['p'],'validation changed head/observed belief')
                    if kind=='VALIDATION_TRAIN':
                        require(slot['completion'] is None,'validation continued after its complete game')
                        if slot['last'] is None:require(row['start']['raw_tiles']==0 and row['seed']==row['start']['stream_seed']==validation_seed(life,index,row['pair_index']),
                            'fresh paired validation seed')
                        else:require(row['start']==slot['last'],'validation sequence discontinuity')
                        require(row['leaf_updates_before']==row['leaf_updates_after']==0,'validation fitted a copied head')
                        check_passive_chunk(row,64,state['p'])
                        for part in slot['counts']:slot['counts'][part].update(row['counts'][part])
                        slot['last']=row['end']
                        if row['completed_games']:slot['completion']=row['completed_games'][0]
                    else:
                        game=row['game_summary'];completion=slot['completion']
                        require(completion is not None and all(game[k]==v for k,v in completion.items())
                            and game['seed']==validation_seed(life,index,row['pair_index']) and game['raw_tiles']==game['steps']+2==slot['last']['raw_tiles'],
                            'full validation game/raw inventory')
                        require(game['utility']==game['score']/2048.+(4. if game['status']=='WON' else -4. if game['status']=='LOST' else 0.),'validation actual utility')
                        require(all(Counter(row['counts'][k])==v for k,v in slot['counts'].items()),'all actual validation cost')
                        slot['receipt']=row
                    continue
                if kind=='SUBMISSION':
                    pairs=[]
                    for pair_index in range(8):
                        pair={branch:state['slots'][phase,arm,pair_index,branch]['receipt']['game_summary'] for branch in ('incumbent','candidate')}
                        pairs.append(pair)
                        if arm=='FROZEN_H2':require(pair['incumbent']==pair['candidate'],'frozen source/source pair changed policy or seed')
                    state['incumbents'][arm]=check_submission(row,pairs,state['incumbents'][arm],state['proposal_id'],state['proposal_updates'])
                    state['submissions'][phase,arm]=row;continue
                if kind in ('DEPLOYMENT_TRAIN','DEPLOYMENT_GAME'):
                    require((phase,arm) in state['submissions'],'deployment before paid validation/submission')
                    deploy=state['deployments'].setdefault(arm,dict(last=None,phases={}))
                    val_raw=sum(state['slots'][phase,arm,pair,branch]['receipt']['game_summary']['raw_tiles'] for pair in range(8) for branch in ('incumbent','candidate'))
                    remain=ONLINE_RAW-CARRIER_RAW-val_raw
                    phase_state=deploy['phases'].setdefault(phase,dict(before=row['start'] if kind=='DEPLOYMENT_TRAIN' else None,
                        raw_tiles=0,counts={k:Counter() for k in ('environment','planning','learning')},games=[],pending=None,realized_utility=0.))
                    require(row['submission_id']==state['incumbents'][arm],'deployment changed submitted head')
                    if kind=='DEPLOYMENT_TRAIN':
                        require(phase_state['pending'] is None,'missing retained deployment completion')
                        if deploy['last'] is None:require(row['start']['raw_tiles']==0 and row['start']['stream_seed']==deployment_seed(life,arm),'fresh continuous deployed stream')
                        else:require(row['start']==deploy['last'],'deployed stream resets across phase')
                        require(row['leaf_updates_before']==row['leaf_updates_after']==0,'deployment trains the policy')
                        check_passive_chunk(row,remain-phase_state['raw_tiles'],state['p'])
                        phase_state['raw_tiles']+=len(row['raw_spawns'])
                        for part in phase_state['counts']:phase_state['counts'][part].update(row['counts'][part])
                        phase_state['realized_utility']+=sum(row['scores'])/2048.+sum(4. if g['status']=='WON' else -4. if g['status']=='LOST' else 0. for g in row['completed_games'])
                        deploy['last']=row['end']
                        if row['completed_games']:phase_state['pending']=row['completed_games'][0]
                    else:
                        game=row['game_summary'];require(phase_state['pending'] is not None and all(game[k]==v for k,v in phase_state['pending'].items()),'actual deployment game completion')
                        require(game['utility']==game['score']/2048.+(4. if game['status']=='WON' else -4. if game['status']=='LOST' else 0.),'deployment terminal utility')
                        phase_state['games'].append(game);phase_state['pending']=None
                    continue
                require(kind=='CHECKPOINT','unknown canonical event')
                state['checkpoints'][phase,arm]=row
        print(json.dumps(dict(event='shadow_parent_receipts_checked',parent=pid)),flush=True)
    require(set(states)==set(range(16)),'all retained new target lives')
    return states,rows_read


def check_lifecycle(row,state):
    life=row['lifecycle'];memory=state['memory'];warm=row['warmup']
    require(warm['game_summaries']==state['warm_games'] and warm['raw_tiles']==state['warm_raw']
        and warm['final_memory']==state['warm_memory'] and warm['memory_events']==state['warm_events'],
        'actual shared warmup prefix')
    require(Counter(warm['environment_counts'])==state['warm_environment'] and Counter(warm['direct_counts'])==state['warm_direct']
        and Counter({k:v for k,v in warm['memory_counts'].items() if k!='predict_calls'})==state['warm_counts'],'shared warmup work')
    carrier=row['carrier'];shadow=row['shadow']
    require(state['pending_fit'] is None and memory.obs==state['warm_raw']+3*CARRIER_RAW
        and learned(carrier['final_memory'])==memory.learned() and carrier['final_stream']==state['carrier_stream'],
        'only carrier ranks enter belief/full final carrier prefix')
    require(shadow['new_value_updates']==state['updates'] and shadow['fit_totals']==state['fit_totals'],
        'acceptance-independent persistent shadow learning/actual operation work')
    require(row['head_copies']==state['copies'] and len(state['copies'])==6,'three candidate/three retained-A snapshots')
    require(shadow['head_setup']['private_weight_bytes']==shadow['head_setup']['setup_counts']['source_weight_bytes_copied'],
        'shadow source initialization/copy cost')
    arms={};carrier_counts={k:Counter() for k in ('environment','planning','learning')}
    p_a=carrier['phases']['A']['snapshot']['estimated_p_four']
    for index,phase in enumerate(PHASES):
        saved=carrier['phases'][phase];actual=state['carrier_phases'][phase];training=saved['training'];snapshot=saved['snapshot']
        require(training['raw_tiles']==CARRIER_RAW and training['chunks']==actual['chunks']
            and training['before_stream']==actual['before_stream'] and training['after_stream']==snapshot['stream']
            and snapshot['stream']['raw_tiles']==(index+1)*CARRIER_RAW and training['memory_event_count']==actual['events'],
            'shared carrier exact phase/chunk/stream budget')
        require(snapshot['stream']==actual['stream_snapshot'] and snapshot['memory']==actual['memory_snapshot']
            and snapshot['estimated_p_four']==actual['memory_snapshot']['modules'][actual['memory_snapshot']['active_module_id']]['alpha']/
                sum(actual['memory_snapshot']['modules'][actual['memory_snapshot']['active_module_id']][k] for k in ('alpha','beta'))
            and snapshot['shadow_value_updates']==actual['shadow_updates'], 'carrier phase prefix/independent shadow snapshot')
        require(Counter({k:v for k,v in training['memory_counts'].items() if k!='predict_calls'})==
            actual['memory_after']-actual['before_memory'],'only carrier ranks processed into memory')
        for part in carrier_counts:
            require(Counter(training['counts'][part])==actual['counts'][part],'actual carrier native work')
            carrier_counts[part].update(actual['counts'][part])
        require(Counter(training['shadow_learning_counts'])==actual['shadow'],'same-data shadow learning per phase')
        require(close(saved['realized_utility'],actual['realized_utility']),'physical phase carrier reward/terminal allocation')
    require(all(Counter(carrier['training_counts'][k])==v for k,v in carrier_counts.items()),'physical source carrier counts')
    for arm in ARMS:
        phases={};current_counts={k:Counter() for k in ('environment','planning')}
        ret_counts={k:Counter() for k in current_counts};a_counts={k:Counter() for k in current_counts}
        deploy_counts={k:Counter() for k in carrier_counts};previous=0
        for index,phase in enumerate(PHASES):
            value=row['arms'][arm]['phases'][phase];canonical=state['checkpoints'][phase,arm]
            require(all(value[k]==canonical[k] for k in value),'phase summary differs from canonical checkpoint')
            cs=carrier['phases'][phase]['snapshot'];snapshot=value['snapshot']
            require(snapshot['carrier_memory']==cs['memory'] and snapshot['carrier_stream']==cs['stream']
                and snapshot['estimated_p_four']==cs['estimated_p_four'] and snapshot['candidate_shadow_value_updates']==cs['shadow_value_updates']
                and snapshot['deployed_submission_id']==value['submission']['deployed_submission_id'],
                'all arms share fixed carrier-only belief/candidate prefix')
            submission=state['submissions'][phase,arm]
            require(all(value['submission'][k]==submission[k] for k in value['submission']),'actual deployment decision')
            validation=value['validation'];pairs=[];all_games=[];val_counts={k:Counter() for k in carrier_counts}
            val_setups=[];val_seconds=val_cpu=0.
            for pair_index in range(8):
                pair=dict(pair_index=pair_index,seed=validation_seed(life,index,pair_index),incumbent_submission_id=previous,
                    candidate_submission_id=0 if arm=='FROZEN_H2' else index+1)
                for branch in ('incumbent','candidate'):
                    receipt=state['slots'][phase,arm,pair_index,branch]['receipt'];pair[branch]=receipt['game_summary'];all_games.append(pair[branch])
                    for part in val_counts:val_counts[part].update(receipt['counts'][part])
                    val_setups.append(receipt['native_setup_counts']);val_seconds+=receipt['seconds'];val_cpu+=receipt['cpu_seconds']
                pairs.append(pair)
            require(validation['pairs']==pairs and validation['game_summaries']==all_games
                and validation['raw_tiles']==sum(g['raw_tiles'] for g in all_games)
                and all(Counter(validation['counts'][k])==v for k,v in val_counts.items()),'all sixteen paired validation games/costs')
            require(validation['native_setup_counts']==sum_counts(val_setups)
                and close(validation['seconds'],val_seconds) and close(validation['cpu_seconds'],val_cpu),'actual complete validation setup/CPU')
            deployed=state['deployments'][arm]['phases'][phase];deployment=value['deployment']
            require(deployed['pending'] is None and deployment['raw_tiles']==deployed['raw_tiles']==ONLINE_RAW-CARRIER_RAW-validation['raw_tiles']
                and deployment['before_stream']==deployed['before'] and deployment['completed_game_summaries']==deployed['games']
                and close(deployment['realized_utility'],deployed['realized_utility'])
                and all(Counter(deployment['counts'][k])==v for k,v in deployed['counts'].items()),
                'actual remaining deployment quota/continuous complete games/costs')
            require(value['online_raw_tiles']==ONLINE_RAW and close(value['online_realized_utility'],
                carrier['phases'][phase]['realized_utility']+validation['realized_utility']+deployment['realized_utility']),
                'inclusive actual online budget/returns')
            current=check_games(value['game_summaries'],[evaluation_seed(life,index,e) for e in range(32)],value['evaluation_counts'])
            for part in current_counts:current_counts[part].update(value['evaluation_counts'][part]);deploy_counts[part].update(deployed['counts'][part])
            deploy_counts['learning'].update(deployed['counts']['learning'])
            probe=value['retention_probe'];require(probe['model_p_four']==p_a and probe['environment_p_four']==.1 and probe['depth']==2
                and probe['shared_with_current']==(index==0),'fixed A retention belief/law/seed path')
            if index==0:
                require(probe['game_summaries']==value['game_summaries'] and not any(probe['counts'].values())
                    and probe['seconds']==probe['cpu_seconds']==0,'initial A probe duplicated its physical cost');ret=current
            else:
                ret=check_games(probe['game_summaries'],[evaluation_seed(life,0,e) for e in range(32)],probe['counts'])
                for part in ret_counts:ret_counts[part].update(probe['counts'][part])
            metrics=dict(current,validation=dict(games=16,raw_tiles=validation['raw_tiles'],
                cutoffs=sum(g['status']=='CUTOFF' for g in all_games),accepted=value['submission']['accepted'],
                deployed_submission_id=value['submission']['deployed_submission_id']),deployment_cutoffs=sum(g['status']=='CUTOFF' for g in deployed['games']),
                deployment_raw_tiles=deployment['raw_tiles'],online_raw_tiles=ONLINE_RAW,online_realized_utility=value['online_realized_utility'],retention_probe=ret)
            if phase=='B':
                ahead=value['a_head_on_B'];require(ahead['model_p_four']==snapshot['estimated_p_four']
                    and ahead['environment_p_four']==.5 and ahead['depth']==2,'saved A versus current B uses different belief/law')
                metrics['a_head_on_B']=check_games(ahead['game_summaries'],[evaluation_seed(life,1,e) for e in range(32)],ahead['counts'])
                for part in a_counts:a_counts[part].update(ahead['counts'][part])
            phases[phase]=metrics;previous=value['submission']['deployed_submission_id']
        arm_value=row['arms'][arm]
        for field,counts in (('evaluation_counts',current_counts),('retention_evaluation_counts',ret_counts),
            ('a_head_on_B_evaluation_counts',a_counts),('deployment_counts',deploy_counts)):
            require(all(Counter(arm_value[field][k])==v for k,v in counts.items()),'actual '+field)
        require(arm_value['final_stream']==state['deployments'][arm]['last'],'continuous final deployment stream')
        arms[arm]=dict(mean_game_utility=mean(phases[phase]['mean_game_utility'] for phase in PHASES),phases=phases)
    return dict(lifecycle=life,parent=life%4,arms=arms)


def unfinished(stream,retained=False):
    active=stream['status'] in ('ACTIVE','INITIALIZING')
    result=dict(episode=stream['episode'] if active else None,raw_tiles=stream['raw_tiles']-stream['game_start_raw'] if active else 0,
        steps=stream['step'] if active else 0,score=stream['return_score'] if active else 0,status=stream['status'])
    if retained:result['retained_afterstates']=stream['step'] if active else 0
    return result


PAIRS=(('VALIDATED_H2','FROZEN_H2'),('VALIDATED_H2','UNCONDITIONAL_H2'),('UNCONDITIONAL_H2','FROZEN_H2'))


def pooled(rows):
    return dict(mean_game_utility=mean(r['mean_game_utility'] for r in rows),
        **{key:sum(r[key] for r in rows) for key in ('games','wins','losses','cutoffs','steps')})


def check_result_summary(summary,records,carrier_cutoffs):
    equal_tree(summary['by_lifecycle'],records,'independent complete science games/actual submissions')
    arms={}
    totals=('games','wins','losses','cutoffs','accepted_submissions','validation_games','validation_raw_tiles',
        'validation_cutoffs','deployment_cutoffs','deployment_raw_tiles','online_raw_tiles','online_realized_utility')
    for arm in ARMS:
        phases={}
        for phase in PHASES:
            rows=[r['arms'][arm]['phases'][phase] for r in records]
            phases[phase]=dict(pooled(rows),retention_probe=pooled([r['retention_probe'] for r in rows]),
                accepted_submissions=sum(r['validation']['accepted'] for r in rows),validation_games=16*16,
                validation_raw_tiles=sum(r['validation']['raw_tiles'] for r in rows),validation_cutoffs=sum(r['validation']['cutoffs'] for r in rows),
                **{key:sum(r[key] for r in rows) for key in ('deployment_cutoffs','deployment_raw_tiles','online_raw_tiles','online_realized_utility')})
        phases['B']['a_head_on_B']=pooled([r['arms'][arm]['phases']['B']['a_head_on_B'] for r in records])
        arms[arm]=dict(mean_game_utility=mean(r['arms'][arm]['mean_game_utility'] for r in records),phases=phases,
            **{key:sum(v[key] for v in phases.values()) for key in totals})
    equal_tree(summary['arms'],arms,'equal game/phase/life means and all paid validation/deployment summaries')
    names={left+'_minus_'+right for left,right in PAIRS}
    require(set(summary['paired_contrasts'])==names and set(summary['phase_contrasts'])==set(PHASES)
        and all(set(summary['phase_contrasts'][phase])==names for phase in PHASES),'predeclared science contrasts')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],[r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records],'higher_is_better')
        for phase in PHASES:
            check_contrast(summary['phase_contrasts'][phase][name],[r['arms'][left]['phases'][phase]['mean_game_utility']-
                r['arms'][right]['phases'][phase]['mean_game_utility'] for r in records],'higher_is_better')
    require(set(summary['correction_contrasts'])==set(summary['retention_contrasts'])==set(ARMS),'all deployed head correction/retention contrasts')
    for arm in ARMS:
        correction=summary['correction_contrasts'][arm]
        require(correction['name']==arm+'_current_B_minus_A_head_on_B','same-law correction name')
        check_contrast(correction,[r['arms'][arm]['phases']['B']['mean_game_utility']-
            r['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for r in records],'higher_is_better')
        for name,left,right in (('after_B','B','A'),('restoration','A_prime','B'),('final_vs_A','A_prime','A')):
            contrast=summary['retention_contrasts'][arm][name]
            values=[r['arms'][arm]['phases'][left]['retention_probe']['mean_game_utility']-
                r['arms'][arm]['phases'][right]['retention_probe']['mean_game_utility'] for r in records]
            check_contrast(contrast,values,'higher_is_better')
            direction='POSITIVE_CHANGE_SUPPORTED' if contrast['ci95'][0]>0 else 'NEGATIVE_CHANGE_SUPPORTED' if contrast['ci95'][1]<0 else 'ZERO_OBSERVED_CHANGE' if all(v==0 for v in values) else 'CHANGE_UNCERTAIN'
            require(contrast['direction']==direction,'retention/equivalence sign claim')
    require(summary['correction_contrast']==summary['correction_contrasts']['VALIDATED_H2'],'validated correction primary scope')
    current=sum(a['cutoffs'] for a in arms.values());validation=sum(a['validation_cutoffs'] for a in arms.values())
    deployment=sum(a['deployment_cutoffs'] for a in arms.values())
    extra=(sum(arms[a]['phases'][p]['retention_probe']['cutoffs'] for a in ARMS for p in ('B','A_prime'))+
        sum(arms[a]['phases']['B']['a_head_on_B']['cutoffs'] for a in ARMS))
    complete=carrier_cutoffs+validation+deployment+current+extra==0
    require(summary['carrier_cutoffs']==carrier_cutoffs and summary['validation_cutoffs']==validation
        and summary['deployment_cutoffs']==deployment and summary['current_science_cutoffs']==current
        and summary['additional_probe_cutoffs']==extra and summary['science_cutoffs']==current+extra
        and summary['physical_science_games']==9216 and summary['physical_validation_games']==2304
        and summary['bootstrap_draws']==20000 and summary['bootstrap_seed']==29300001
        and summary['estimator']=='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES'
        and summary['primary_contrast']=='VALIDATED_H2_minus_FROZEN_H2'
        and summary['mechanism_contrast']=='VALIDATED_H2_minus_UNCONDITIONAL_H2'
        and summary['complete_game_endpoints']==complete,'declared science/statistics/natural completion scope')
    net=complete and summary['paired_contrasts']['VALIDATED_H2_minus_FROZEN_H2']['ci95'][0]>0
    require(summary['net_gain_supported']==net
        and summary['net_gain_status']==('SUPPORTED_' if net else 'NOT_SUPPORTED_')+'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and summary['mechanism_supported']==(complete and summary['paired_contrasts']['VALIDATED_H2_minus_UNCONDITIONAL_H2']['ci95'][0]>0)
        and summary['correction_supported']==(complete and summary['correction_contrast']['ci95'][0]>0),
        'rejection/validation substituted for independent science gain/correction')


def check_accounting(d,old):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];a=d['accounting'];kinds=('environment','planning','learning')
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN_H2'];warm=sum(l['warmup']['raw_tiles'] for l in lives)
    carrier={k:sum_counts(l['carrier']['training_counts'][k] for l in lives) for k in kinds}
    require(a['physical_online_raw_tiles']==31457280 and a['physical_carrier_raw_tiles']==16*3*CARRIER_RAW
        and a['carrier_counts']==carrier and a['physical_warmup_raw_tiles']==warm
        and a['physical_warmup_games']==sum(len(l['warmup']['game_summaries']) for l in lives),'physical shared carrier/warmup/online budget')
    for name in ('environment','direct','memory'):
        require(a['warmup_'+name+'_counts']==sum_counts(l['warmup'][name+'_counts'] for l in lives),'warmup physical work')
    require(a['physical_carrier_memory_counts']==sum_counts(l['carrier']['phases'][p]['training']['memory_counts'] for l in lives for p in PHASES),
        'carrier-only learned memory cost')
    physical={k:Counter(carrier[k]) for k in kinds}
    for arm in ARMS:
        validation={k:sum_counts(l['arms'][arm]['phases'][p]['validation']['counts'][k] for l in lives for p in PHASES) for k in kinds}
        deployment={k:sum_counts(l['arms'][arm]['deployment_counts'][k] for l in lives) for k in kinds}
        require(a['validation_counts_per_arm'][arm]==validation and a['deployment_counts_per_arm'][arm]==deployment,
            'all actual streamed validation/deployment costs')
        for part in kinds:
            require(Counter(a['online_counts_per_arm'][arm][part])==Counter(carrier[part])+Counter(validation[part])+Counter(deployment[part]),
                'shared carrier once per-method economic work')
            physical[part].update(validation[part]);physical[part].update(deployment[part])
        require(a['physical_validation_raw_tiles'][arm]==validation['environment']['raw_tile_productions']
            and a['physical_deployment_raw_tiles'][arm]==deployment['environment']['raw_tile_productions']
            and a['online_raw_tiles_per_arm'][arm]==16*3*ONLINE_RAW
            and a['inherited_costs_per_arm'][arm]==inherited
            and a['economic_online_raw_tiles_per_arm'][arm]==inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+16*3*ONLINE_RAW,
            'inclusive equal raw/old source-only economic budget')
        parts=('evaluation_counts','retention_evaluation_counts','a_head_on_B_evaluation_counts')
        for component in parts:
            for k in ('environment','planning'):
                require(a['evaluation_components_per_arm'][arm][component][k]==sum_counts(l['arms'][arm][component][k] for l in lives),
                    'physical current/fixed-A/saved-head evaluation')
        for k in ('environment','planning'):
            require(a['evaluation_counts_per_arm'][arm][k]==sum_counts(l['arms'][arm][part][k] for l in lives for part in parts),
                'science evaluations charged once')
        require(a['final_unfitted_deployment_raw_tiles_per_arm'][arm]==sum(l['arms'][arm]['final_unfitted_game']['raw_tiles'] for l in lives),
            'paid unfinished deployed tail omitted')
        for prefix in ('validation','deployment'):
            require(close(a[prefix+'_cpu_seconds_per_arm'][arm],sum(l['arms'][arm]['phases'][p][prefix]['cpu_seconds'] for l in lives for p in PHASES)),
                'scoped streamed environment CPU')
    require(all(Counter(a['physical_online_counts'][k])==v for k,v in physical.items()),'carrier physically shared once')
    require(a['physical_validation_games']==2304 and a['physical_evaluation_games']==9216
        and a['evaluation_counts']['environment']['initial_spawns']==2*9216,'validation/science games conflated or A-end probe duplicated')
    for k in ('environment','planning'):
        require(a['evaluation_counts'][k]==sum_counts(a['evaluation_counts_per_arm'][arm][k] for arm in ARMS),'all scientific evaluation cost')
    fits=[l['shadow']['fit_totals'] for l in lives];samples=sum(f['trained_afterstates'] for f in fits)
    require(a['physical_processed_training_samples']==samples and a['economic_processed_training_samples_per_arm']==
        {arm:0 if arm=='FROZEN_H2' else samples for arm in ARMS},'physical once/shared shadow economic samples')
    for part in ('learning_counts','target_counts','consolidation_counts','setup_counts'):
        require(a['shared_fit_counts'][part]==sum_counts({k:v for k,v in f[part].items() if not k.endswith('_peak')} for f in fits),
            'actual shared shadow target/write/aggregation work')
    peaks={k:max(f[part].get(k,0) for f in fits) for part in ('target_counts','consolidation_counts')
        for k in {key for f in fits for key in f[part] if key.endswith('_peak')}}
    require(a['fit_buffer_peaks']==peaks and a['carrier_retained_afterstate_steps_peak']==max(l['carrier']['retained_afterstate_steps_peak'] for l in lives),
        'actual buffer capacity peaks')
    copies=[c for l in lives for c in l['head_copies']];setups=[l['shadow']['head_setup'] for l in lives]
    require(a['physical_head_copies']==len(copies)==96 and a['head_copy_setup_counts']==sum_counts(c['setup_counts'] for c in copies)
        and a['shadow_head_setup_counts']==sum_counts(s['setup_counts'] for s in setups)
        and a['physical_private_head_weight_bytes_created']==sum(c['private_weight_bytes'] for c in copies)+sum(s['private_weight_bytes'] for s in setups),
        'immutable proposal/retained-head/source-initialization costs')
    require(close(a['head_copy_cpu_seconds'],sum(c['cpu_seconds'] for c in copies))
        and close(a['physical_fit_cpu_seconds'],sum(f['cpu_seconds'] for f in fits)),'physical snapshot/fit CPU')
    require(a['final_unfitted_carrier_raw_tiles']==sum(l['carrier']['final_unfitted_game']['raw_tiles'] for l in lives)
        and a['reconstruction_counts']==sum_counts(l['carrier']['reconstruction_counts'] for l in lives)
        and close(a['reconstruction_cpu_seconds'],sum(l['carrier']['reconstruction_cpu_seconds'] for l in lives)),
        'paid carrier tails/needed afterstate reconstruction')
    for parent in parents:require(parent['source_setup']['checkpoint_loads']==1 and parent['source_setup']['new_leaf_updates']==0,'four immutable physical source loads')
    for field in ('worker_cpu_seconds','compiler_cpu_seconds'):
        require(close(a[field],sum(p['cpu_seconds' if field=='worker_cpu_seconds' else field] for p in parents)),'actual process CPU')
    require(a['canonical_trace_bytes']==sum(p['trace_bytes'] for p in parents),'physical retained storage')
    ref=a['development_reference'];require(ref['previous']=='V292' and ref['previous_target_online_raw_tiles']==
        old['accounting']['physical_training_raw_tiles'] and ref['previous_evaluation_counts']==old['accounting']['evaluation_counts'],
        'old target cost not training inputs')


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected=dict(lifecycles=list(range(16)),parents=4,arms=list(ARMS),phases=[['A',.1],['B',.5],['A_prime',.1]],
        carrier_raw_tiles_per_phase=CARRIER_RAW,online_raw_tiles_per_arm_phase=ONLINE_RAW,validation_pairs=8,evaluation_games=32,
        max_steps=8192,alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        seed_warmup=293100010000,seed_carrier=293200010000,seed_deployment=293400010000,seed_validation=293600010000,
        seed_evaluation=293900010000,bootstrap_seed=29300001,bootstrap_draws=20000,
        primary='VALIDATED_H2_minus_FROZEN_H2_THREE_PHASE_COMPLETE_GAME_UTILITY',mechanism='VALIDATED_H2_minus_UNCONDITIONAL_H2',
        submission='EIGHT_PAIRED_T_95_LOWER_STRICTLY_POSITIVE_AND_NO_CUTOFF',student_t_critical_df7=T_CRITICAL,
        acquisition='FROZEN_SOURCE_H2_CARRIER_WITH_PERSISTENT_SHARED_EPISODE_MEAN_SHADOW',memory_input='CARRIER_RAW_ONLY_INCLUDING_INITIAL',
        online_budget='SHARED_CARRIER_PLUS_ACTUAL_COMPLETE_VALIDATION_PLUS_REMAINING_DEPLOYMENT_RAW',
        retention='SAVED_A_BELIEF_AND_A_SEEDS_ACROSS_ALL_CHECKPOINTS',
        correction='CURRENT_B_HEAD_MINUS_OWN_SAVED_A_HEAD_WITH_SAME_B_BELIEF_AND_SEEDS',finite_test_passes=dict(core=6,analysis=14,driver=3))
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    require(d['schema']=='acfqp.shadow_deployment.v293' and d['status']=='EXPERIMENT_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE','experimental completion scope')
    old=json_file(settings['source_summary']);require(json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid'],
        'valid retained V292 evidence prerequisite')
    require(d['source_provenance']==old['source_provenance'],'source/dynamics provenance changed')
    lives=d['by_lifecycle'];require([l['lifecycle'] for l in lives]==list(range(16)) and all(l['parent']==l['lifecycle']%4 for l in lives),
        'complete fixed source paired cohort')
    states,rows_read=read_canonical(d);records=[];carrier_cutoffs=0
    for row in lives:
        state=states[row['lifecycle']];records.append(check_lifecycle(row,state));carrier=row['carrier']
        actual_cutoffs=sum(phase['cutoffs'] for phase in state['carrier_phases'].values())
        require(carrier['cutoff_games']==actual_cutoffs and carrier['final_unfitted_game']==unfinished(state['carrier_stream'],True),
            'carrier cutoff/tail turned into a label')
        carrier_cutoffs+=actual_cutoffs
        for phase in PHASES:
            require(carrier['phases'][phase]['cutoff_games']==state['carrier_phases'][phase]['cutoffs']
                and carrier['phases'][phase]['snapshot']['unfinished_game']==unfinished(state['carrier_phases'][phase]['stream_snapshot'],True),
                'carrier phase mixed-law game boundary')
        for arm in ARMS:
            value=row['arms'][arm];require(value['final_unfitted_game']==unfinished(state['deployments'][arm]['last'])
                and value['cutoff_games']==sum(g['status']=='CUTOFF' for phase in state['deployments'][arm]['phases'].values() for g in phase['games']),
                'actual deployed cutoff/unfinished tail')
    summary=d['summary'];check_result_summary(summary,records,carrier_cutoffs);check_accounting(d,old);a=d['accounting']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,canonical_rows=rows_read,
        physical_online_raw_tiles=a['physical_online_raw_tiles'],physical_carrier_raw_tiles=a['physical_carrier_raw_tiles'],
        physical_warmup_raw_tiles=a['physical_warmup_raw_tiles'],physical_validation_games=2304,physical_science_games=9216,
        physical_validation_raw_tiles=a['physical_validation_raw_tiles'],physical_deployment_raw_tiles=a['physical_deployment_raw_tiles'],
        economic_online_raw_tiles_per_arm=a['economic_online_raw_tiles_per_arm'],physical_shadow_training_samples=a['physical_processed_training_samples'],
        physical_parameter_writes=a['shared_fit_counts']['learning_counts'].get('table_updates',0),physical_head_copies=a['physical_head_copies'],
        cutoff_totals={key:summary[key] for key in ('carrier_cutoffs','validation_cutoffs','deployment_cutoffs','science_cutoffs')},
        accepted_submissions={arm:summary['arms'][arm]['accepted_submissions'] for arm in ARMS},
        net_gain_supported=summary['net_gain_supported'],mechanism_supported=summary['mechanism_supported'],correction_supported=summary['correction_supported'],
        primary=summary['paired_contrasts']['VALIDATED_H2_minus_FROZEN_H2'],mechanism=summary['paired_contrasts']['VALIDATED_H2_minus_UNCONDITIONAL_H2'],
        correction=summary['correction_contrasts'],retention=summary['retention_contrasts'],
        method='Shared carrier raw/router and factual complete-game shadow fits; immutable head versions, all paid validation/deployment '
            'raw/state/score/terminal receipts; eight-pair Student-t submission recomputation; independent static game utility/seed receipts; '
            'equal game/phase/life signed estimates and complete physical/economic costs.',
        limitations='No world, full intermediate boards/weights or fitting replay, and no 20000-draw CI regeneration. '
            'Only carrier feedback trains belief/values; all validation and deployment observations are charged. '
            'Submission intervals are approximate decision rules. Inference is conditional on four old source parents.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
