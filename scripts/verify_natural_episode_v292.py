#!/usr/bin/env python3
"""Independent receipt audit of terminal-first online episode consolidation."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, factual_targets, json_file, require, sum_counts
from verify_episode_consolidation_v290 import check_normalized_fit, check_contrast
from verify_natural_online_value_v286 import Memory, planning_counts, terminal

ARMS=('FROZEN_H2','NSEQ_H2','MEAN_H2','FROZEN_DIRECT','MEAN_DIRECT')
PHASES=('A','B','A_prime')
RAW=131072


def warmup_seed(life,game):return 292100000000+life*1000000+game
def training_seed(life):return 292200000000+life*10000000
def evaluation_seed(life,phase,game):return 292900000000+life*1000000+phase*100000+game
def learned(payload):return {key:payload[key] for key in ('observations_seen','active_module_id','modules','pending')}


def accumulate(total,current):
    for key,value in current.items():total[key]=max(total.get(key,0),value) if key.endswith('_peak') else total.get(key,0)+value


def check_warmup(row,index,memory):
    require(memory.obs<256,'warmup continued after the fixed raw threshold')
    game=row['summary'];raw=row['raw_spawns'];steps=game['steps']
    require(game['seed']==warmup_seed(row['lifecycle'],index),'fresh shared complete warmup seed')
    terminal(row['final_board'],game['status'])
    require(game['utility']==game['score']/2048.+(4. if game['status']=='WON' else -4.),'warmup utility/terminal')
    require(len(row['actions'])==len(row['scores'])==steps and sum(row['scores'])==game['score'],'warmup actual scores')
    require(len(raw)==steps+2 and [r['kind'] for r in raw[:2]]==['INITIAL','INITIAL']
        and all(r['kind']=='POST_ACTION' for r in raw[2:]),'all warmup initial/post-action tiles')
    won=game['status']=='WON'
    env=dict(initial_spawns=2,sampled_transitions=steps,environment_random_draws=2*(steps+2),
        ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+1,
        ground_status_internal_swipe_calls=4*(steps+1-won),ground_swipe_calls=steps+4*(steps+1-won))
    require(Counter(row['counts']['environment'])==Counter(env),'warmup physical environment costs')
    direct=Counter(row['counts']['direct'])
    require(direct['choose_calls']==direct['inner_choose_calls']==steps
        and direct['inner_learned_swipe_calls']==4*steps
        and direct['inner_line_table_lookups']==4*direct['inner_learned_swipe_calls']
        and direct['inner_table_lookups']==32*direct['inner_value_predictions']
        and direct['td_updates']==direct['inner_td_updates']==0,'readonly DIRECT warmup costs')
    return memory.consume(spawn['rank'] for spawn in raw)


def check_training_chunk(row,phase_left,memory):
    """Check paused native chronology/costs without world or weight execution."""
    start,end=row['start'],row['end'];raw=row['raw_spawns'];n=len(raw)
    maximum=min(phase_left,64-memory.n)
    require(0<n<=maximum,'raw budget crosses phase or uncommitted memory block')
    require(row['module_id_before']==memory.active and row['model_p_four']==memory.probability(),
        'decision used a different observed prefix')
    require(row['depth']==(1 if row['arm'].endswith('DIRECT') else 2) and row['active_bank_id']==0,
        'actual actor depth/bank differs from frozen method')
    require(row['actor_weights_readonly'] and row['leaf_updates_before']==row['leaf_updates_after']
        and not {key:value for key,value in row['counts']['learning'].items() if key!='censored_pending_updates'}
        and not row['bank_update_counts'] and not row['td_examples'],
        'native execution performed SARSA/value updates before episode fitting')
    require(end['raw_tiles']==start['raw_tiles']+n and end['random_draw_position']==2*end['raw_tiles'],
        'raw/RNG budget excludes initial tiles')
    completed=row['completed_games']
    require(len(completed)<=1 and (not completed or completed[0]['end_raw']==end['raw_tiles']),
        'a decision or next-game spawn occurred before terminal fitting')
    require(n==maximum or completed,'early pause without a terminal or phase/block boundary')
    episode,step,score=start['episode'],start['step'],start['return_score']
    initial,game_start,status=start['initial_count'],start['game_start_raw'],start['status']
    pending=start['pending_bank_id'];actions=iter(zip(row['actions'],row['scores']))
    starts=init_done=posts=wins=losses=cutoffs=censored=0
    for index,spawn in enumerate(raw):
        require(spawn['rank'] in (1,2) and 0<=spawn['cell']<16,'raw spawn fields')
        if spawn['episode']!=episode:
            require(spawn['episode']==episode+1 and status!='ACTIVE','game restarted before terminal')
            episode+=1;step=score=initial=0
            game_start,status,pending=start['raw_tiles']+index,'INITIALIZING',None;starts+=1
        if spawn['kind']=='INITIAL':
            require(initial<2 and status=='INITIALIZING' and pending is None,'initial tile follows an action')
            initial+=1
            if initial==2:status='ACTIVE';init_done+=1
            continue
        require(spawn['kind']=='POST_ACTION' and initial==2 and status=='ACTIVE','action before complete initialization')
        action,reward=next(actions)
        require(action in ('DOWN','LEFT','RIGHT','UP') and reward>=0 and reward%4==0,'actual action/score ledger')
        step+=1;score+=reward;posts+=1;pending=0
        if completed and completed[0]['end_raw']==start['raw_tiles']+index+1:
            game=completed[0]
            require(game['stream_seed']==start['stream_seed'] and 'seed' not in game,
                'continuous training has a synthetic game seed')
            require((game['episode'],game['start_raw'],game['steps'],game['score'])==(episode,game_start,step,score),
                'terminal game differs from actual raw/actions')
            status=game['status'];require(status in ('WON','LOST','CUTOFF'),'completion is not terminal/cutoff')
            wins+=status=='WON';losses+=status=='LOST';cutoffs+=status=='CUTOFF'
            censored+=status=='CUTOFF';pending=None
            require(index==n-1,'native continued after the completed game')
    require(next(actions,None) is None and len(row['actions'])==len(row['scores'])==posts,'raw/action inventory')
    require((end['episode'],end['step'],end['return_score'],end['initial_count'],end['game_start_raw'],
        end['status'],end['pending_bank_id'])==(episode,step,score,initial,game_start,status,pending),
        'paused stream/pending state differs')
    require(end['post_action_spawns']==start['post_action_spawns']+posts,'post-action cumulative count')
    if status in ('WON','LOST'):terminal(end['board'],status)
    if status=='CUTOFF':require(step==8192 and max(end['board'])<11,'cutoff before cap or at winning board')
    env=dict(sampled_transitions=posts,post_action_spawns=posts,initial_spawns=n-posts,
        raw_tile_productions=n,environment_random_draws=2*n,ground_explicit_swipe_calls=posts,
        ground_state_status_calls=posts+init_done,ground_status_internal_swipe_calls=4*(posts+init_done-wins),
        ground_swipe_calls=posts+4*(posts+init_done-wins),episodes_started=starts,
        episodes_completed=wins+losses+cutoffs,won_games=wins,lost_games=losses,cutoff_games=cutoffs)
    require(Counter(row['counts']['environment'])==Counter(env),'actual environment ledger')
    require(Counter(row['counts']['learning'])==Counter(censored_pending_updates=censored),
        'cutoff censoring is not an actual value update')
    planning_counts(row['counts']['planning'],posts,row['depth'])
    return completed


def check_game_fit(row,pending,scores,updates):
    require(pending is not None and row['completion']==pending,'GAME_FIT is not immediately after its terminal TRAIN')
    require(row['old_value_updates']==updates,'episode fit starts from wrong value-update prefix')
    game=row['completion'];fit=row['fit'];arm=row['arm']
    method='NORMALIZED_SEQUENTIAL_MC' if arm=='NSEQ_H2' else 'EPISODE_MEAN_MC'
    fitted=not arm.startswith('FROZEN') and game['status'] in ('WON','LOST')
    require(row['fitted']==fitted,'incomplete/cutoff game fitted or complete game skipped')
    require(len(scores)==game['steps'] and sum(scores)==game['score'],'full actual game spans chunk/phase boundaries')
    if fitted:
        dataset=dict(fit_step_end=game['steps'])
        # The old multi-game checker selects its last position by game index.
        # With one game it checks the first position twice. Reuse its complete
        # work inventory and first check, then check the actual last below.
        check_normalized_fit(dict(fit,last_sample=fit['first_sample']),[game],dataset,{game['episode']:scores},method)
        labels=factual_targets(scores,game['status'])
        for example,position in ((fit['first_sample'],0),(fit['last_sample'],len(labels)-1)):
            require((example['episode'],example['step'],example['target'])==(0,position,labels[position]),
                'single-game local sample position or after-current-action suffix target')
            require(example['raw_target']==example['target']
                and close(example['error'],example['raw_target']-example['raw_prediction_before_update']),
                'single-game sample raw target/offset/residual')
            require(example['global_episode']==game['episode']
                and example['global_raw_before_action']==game['start_raw']+2+example['step'],
                'local fit sample credited to a different actual episode/raw')
        added=game['steps']-(game['status']=='WON')
    else:
        require(fit['method']==('SKIPPED_CUTOFF' if game['status']=='CUTOFF' else 'NONE')
            and fit['trained_afterstates']==0 and not fit['learning_counts'] and not fit['target_counts']
            and not fit['consolidation_counts'] and fit['first_sample'] is None and fit['last_sample'] is None,
            'frozen/censored game received label or value update')
        added=0
    require(row['new_value_updates']==updates+added,'online value counter includes non-episode updates')
    return added


def read_canonical(d):
    """Read every feedback/commit in order without fitting or running a world."""
    states={};warmups={};rows_read=0
    require([p['parent'] for p in d['parent_receipts']]==list(range(4)),'four source physical parent receipts')
    for parent in d['parent_receipts']:
        pid=parent['parent'];ids=list(range(pid,16,4))
        require(parent['lifecycle_ids']==ids,'life/source assignment')
        path=Path(parent['trace_file']);require(path.stat().st_size==parent['trace_bytes'],'canonical retained storage')
        for life in ids:
            warmups[life]=dict(memory=Memory(),games=[],events=[],environment=Counter(),direct=Counter())
        with gzip.open(path,'rt') as stream:
            for line in stream:
                row=json.loads(line);rows_read+=1;life=row['lifecycle']
                require(life in ids and row['parent']==pid,'canonical source/life context')
                if row['kind']=='WARMUP':
                    require(not any((life,arm) in states for arm in ARMS),'shared warmup after actor execution')
                    warm=warmups[life]
                    warm['events'].extend(check_warmup(row,len(warm['games']),warm['memory']))
                    warm['games'].append(row['summary']);warm['environment'].update(row['counts']['environment'])
                    warm['direct'].update(row['counts']['direct']);continue
                arm=row['arm'];require(arm in ARMS and row['phase'] in PHASES,'canonical actor/phase')
                key=(life,arm);warm=warmups[life]
                if key not in states:
                    require(row['kind']=='TRAIN' and warm['memory'].obs>=256,'actor missing complete shared warmup')
                    states[key]=dict(memory=deepcopy(warm['memory']),last_stream=None,pending_fit=None,updates=0,
                        ranks=bytearray(),scores=defaultdict(list),games=[],phase_index=0,phase_states={},
                        fit_totals=dict(fitted_games=0,fitted_steps=0,trained_afterstates=0,learning_counts={},
                            target_counts={},consolidation_counts={},setup_counts={},seconds=0.,cpu_seconds=0.))
                state=states[key];memory=state['memory'];index=state['phase_index']
                require(index<3 and row['phase']==PHASES[index],'phase transition/reset or extra continuation')
                if row['kind']=='TRAIN':
                    require(state['pending_fit'] is None,'next action/init preceded terminal GAME_FIT')
                    if state['last_stream'] is None:
                        require(row['start']['raw_tiles']==row['start']['random_draw_position']==0
                            and row['start']['stream_seed']==training_seed(life),'fresh continuous actor seed/prefix')
                    else:require(row['start']==state['last_stream'],'cross-phase stream continuity')
                    phase=state['phase_states'].setdefault(row['phase'],dict(before_stream=row['start'],
                        memory_before=memory.counts.copy(),chunks=0,events=0,completed=0,cutoffs=0,fitted=0,
                        counts={kind:Counter() for kind in ('environment','planning','learning')}))
                    require(row['leaf_updates_before']==state['updates'],'choose used wrong episode-fit value prefix')
                    check_training_chunk(row,(index+1)*RAW-row['start']['raw_tiles'],memory)
                    rewards=iter(row['scores'])
                    for spawn in row['raw_spawns']:
                        if spawn['kind']=='POST_ACTION':state['scores'][spawn['episode']].append(next(rewards))
                    events=memory.consume(spawn['rank'] for spawn in row['raw_spawns'])
                    require(events==row['memory_events'],'actual all-raw observed-prefix router events')
                    state['ranks'].extend(spawn['rank'] for spawn in row['raw_spawns'])
                    phase['chunks']+=1;phase['events']+=len(events)
                    for kind in phase['counts']:phase['counts'][kind].update(row['counts'][kind])
                    state['last_stream']=row['end']
                    if row['completed_games']:
                        state['pending_fit']=row['completed_games'][0];phase['completed']+=1
                        phase['cutoffs']+=row['completed_games'][0]['status']=='CUTOFF'
                    continue
                if row['kind']=='GAME_FIT':
                    pending=state['pending_fit'];require(pending is not None,'unexpected fit with no complete game')
                    added=check_game_fit(row,pending,state['scores'][pending['episode']],state['updates'])
                    state['updates']+=added;phase=state['phase_states'][row['phase']]
                    state['games'].append(dict(pending,terminal_phase=row['phase'],fitted=row['fitted']))
                    if row['fitted']:
                        fit=row['fit'];totals=state['fit_totals'];phase['fitted']+=1
                        for field in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):totals[field]+=fit[field]
                        for field in ('learning_counts','target_counts','consolidation_counts','setup_counts'):accumulate(totals[field],fit[field])
                        phase['counts']['learning'].update(fit['learning_counts'])
                    state['pending_fit']=None;continue
                require(row['kind']=='CHECKPOINT' and state['pending_fit'] is None,'checkpoint precedes immediate episode fit')
                require(state['last_stream']['raw_tiles']==(index+1)*RAW,'phase snapshot before exact raw quota')
                snapshot=row['snapshot'];phase=state['phase_states'][row['phase']];training=row['training']
                require(snapshot['stream']==state['last_stream'] and snapshot['memory']==memory.learned()
                    and snapshot['estimated_p_four']==memory.probability() and snapshot['value_updates']==state['updates'],
                    'phase head/memory/stream snapshot differs from actual prefix')
                active=state['last_stream']['status'] in ('ACTIVE','INITIALIZING');last=state['last_stream']
                unfinished=dict(episode=last['episode'] if active else None,
                    raw_tiles=last['raw_tiles']-last['game_start_raw'] if active else 0,steps=last['step'] if active else 0,
                    score=last['return_score'] if active else 0,status=last['status'],
                    retained_afterstates=last['step'] if active and not arm.startswith('FROZEN') else 0)
                require(snapshot['unfinished_game']==unfinished,'phase boundary resets or fits an unfinished game')
                require(training['raw_tiles']==RAW and training['chunks']==phase['chunks']
                    and training['before_stream']==phase['before_stream'] and training['after_stream']==last
                    and training['memory_event_count']==phase['events']
                    and (training['completed_games'],training['cutoff_games'],training['fitted_games'])==
                        (phase['completed'],phase['cutoffs'],phase['fitted']),'phase actual chunk/game/budget totals')
                require(Counter({k:v for k,v in training['memory_counts'].items() if k!='predict_calls'})==
                    memory.counts-phase['memory_before'],'phase all-raw memory processing work')
                require(all(Counter(training['counts'][kind])==value for kind,value in phase['counts'].items()),
                    'phase actual environment/planning/fitting work')
                phase['checkpoint']=row;state['phase_index']+=1
        print(json.dumps(dict(event='online_episode_parent_checked',parent=pid)),flush=True)
    require(set(states)=={(life,arm) for life in range(16) for arm in ARMS},'complete 16-life five-arm cohort')
    for life in range(16):
        reference=states[life,ARMS[0]]
        require(all(states[life,arm]['phase_index']==3 and states[life,arm]['pending_fit'] is None for arm in ARMS),
            'missing final snapshot/episode commitment')
        for arm in ARMS:
            state=states[life,arm]
            require(len(state['ranks'])==3*RAW and state['ranks']==reference['ranks'],'paired all-raw rank stream differs by actor')
            require(state['memory'].learned()==reference['memory'].learned(),'different actor-prefix all-raw learned memory')
            for phase in PHASES:
                require(state['phase_states'][phase]['checkpoint']['snapshot']['memory']==
                    reference['phase_states'][phase]['checkpoint']['snapshot']['memory'],'actor phase learned memory differs')
    return states,warmups,rows_read


def check_evaluation(games,life,phase,counts,depth):
    require(len(games)==32 and [g['seed'] for g in games]==[evaluation_seed(life,phase,i) for i in range(32)],
        'registered paired static game seeds')
    for game in games:
        require(1<=game['steps']<=8192,'static game cap')
        if game['status']=='CUTOFF':
            require(game['steps']==8192 and max(game['final_board'])<11,'premature static cutoff or goal cutoff');bonus=0.
        else:terminal(game['final_board'],game['status']);bonus=4. if game['status']=='WON' else -4.
        require(game['utility']==game['score']/2048.+bonus,'complete static utility')
    steps,wins=sum(g['steps'] for g in games),sum(g['status']=='WON' for g in games)
    env=dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=64,raw_tile_productions=steps+64,
        environment_random_draws=2*(steps+64),ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+32,
        ground_status_internal_swipe_calls=4*(steps+32-wins),ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment'])==Counter(env),'physical static evaluation cost includes all initial tiles')
    planning_counts(counts['planning'],steps,depth)
    return dict(mean_game_utility=mean(g['utility'] for g in games),games=32,wins=wins,
        losses=sum(g['status']=='LOST' for g in games),cutoffs=sum(g['status']=='CUTOFF' for g in games),
        cutoff_episodes=[i for i,g in enumerate(games) if g['status']=='CUTOFF'],steps=steps)


def check_arm(value,state,life,arm):
    require(value['fit_totals']==state['fit_totals'],'online chronological fit work/peak/CPU aggregate')
    require(learned(value['final_memory'])==state['memory'].learned()
        and value['final_stream']==state['last_stream'],'final uninterrupted actor/memory prefix')
    require(Counter({k:v for k,v in value['final_memory']['counts'].items() if k!='predict_calls'})==state['memory'].counts,
        'final all-raw memory work')
    require(value['completed_games']==len(state['games'])
        and value['cutoff_games']==sum(g['status']=='CUTOFF' for g in state['games']),'all complete/cutoff trajectories')
    setup=value['head_setup']
    if arm.startswith('FROZEN'):
        require(setup['source_weights_shared'] and setup['private_weight_bytes']==0 and not setup['setup_counts'],
            'frozen source copied or fitted')
    else:
        require(not setup['source_weights_shared']
            and setup['private_weight_bytes']==setup['setup_counts']['source_weight_bytes_copied'],
            'same source initialization/private head copy')
    if arm=='MEAN_H2':
        retained=value['retained_A_head_setup'];size=setup['private_weight_bytes']
        require(retained['private_weight_bytes']==retained['setup_counts']['source_weight_bytes_copied']==
            retained['setup_counts']['retained_A_weight_bytes_copied']==size
            and retained['setup_counts']['retained_A_parameters_copied']*8==size
            and retained['copied_from_value_updates']==value['phases']['A']['snapshot']['value_updates'],
            'saved A head copy origin/cost omitted')
    else:require(value['retained_A_head_setup'] is None,'unregistered extra saved value head')
    training={kind:Counter() for kind in ('environment','planning','learning')}
    evaluations={kind:Counter() for kind in ('environment','planning')}
    retention_counts={kind:Counter() for kind in evaluations};ahead_counts={kind:Counter() for kind in evaluations}
    phase_metrics={};retention_metrics={};ahead=None
    saved_p=value['phases']['A']['snapshot']['estimated_p_four'];depth=1 if arm.endswith('DIRECT') else 2
    for index,phase in enumerate(PHASES):
        saved=value['phases'][phase];canonical=state['phase_states'][phase]['checkpoint']
        require(all(saved[key]==canonical[key] for key in saved),'phase summary differs from canonical checkpoint')
        require(saved['snapshot']['value_updates']==sum(g['steps']-(g['status']=='WON')
            for g in state['games'] if g['fitted'] and PHASES.index(g['terminal_phase'])<=index),
            'snapshot fit inventory includes incomplete/censored/future game')
        phase_metrics[phase]=check_evaluation(saved['game_summaries'],life,index,saved['evaluation_counts'],depth)
        for kind in training:training[kind].update(saved['training']['counts'][kind])
        for kind in evaluations:evaluations[kind].update(saved['evaluation_counts'][kind])
        probe=saved['retention_probe']
        require(probe['model_p_four']==saved_p and probe['environment_p_four']==.1 and probe['depth']==depth,
            'A retention probe changed fixed A belief/law/depth')
        require(probe['shared_with_current']==(index==0),'A-end probe duplication or later probe omitted')
        if index==0:
            require(probe['game_summaries']==saved['game_summaries'] and not any(probe['counts'].values())
                and probe['seconds']==probe['cpu_seconds']==0,'shared A-end probe paid twice')
            retention_metrics[phase]=phase_metrics[phase]
        else:
            retention_metrics[phase]=check_evaluation(probe['game_summaries'],life,0,probe['counts'],depth)
            for kind in retention_counts:retention_counts[kind].update(probe['counts'][kind])
        if arm=='MEAN_H2' and phase=='B':
            held=saved['a_head_on_B'];require(held['model_p_four']==saved['snapshot']['estimated_p_four']
                and held['environment_p_four']==.5 and held['depth']==2,'B head contrast changed knowledge/law/depth')
            ahead=check_evaluation(held['game_summaries'],life,1,held['counts'],2)
            for kind in ahead_counts:ahead_counts[kind].update(held['counts'][kind])
        else:require('a_head_on_B' not in saved,'unregistered reference-head evaluation')
    for field,total in (('training_counts',training),('evaluation_counts',evaluations),
        ('retention_evaluation_counts',retention_counts),('a_head_on_B_evaluation_counts',ahead_counts)):
        require(all(Counter(value[field][kind])==count for kind,count in total.items()),'actual '+field)
    require(value['final_unfitted_game']==value['phases']['A_prime']['snapshot']['unfinished_game'],
        'unpaid/fitted final unfinished tail')
    return phase_metrics,retention_metrics,ahead


def check_accounting(d,old):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];account=d['accounting']
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN']
    warm_raw=sum(l['warmup']['raw_tiles'] for l in lives);raw_per_arm=16*3*RAW
    require(account['physical_training_raw_tiles']==5*raw_per_arm
        and account['physical_warmup_raw_tiles']==warm_raw
        and account['physical_warmup_games']==sum(len(l['warmup']['game_summaries']) for l in lives),
        'physical five trajectories/shared complete warmup acquisition')
    for name in ('environment','direct','memory'):
        require(account['warmup_'+name+'_counts']==sum_counts(l['warmup'][name+'_counts'] for l in lives),'actual warmup work')
    for arm in ARMS:
        require(account['training_raw_tiles_per_arm'][arm]==raw_per_arm
            and account['inherited_costs_per_arm'][arm]==inherited
            and account['economic_training_raw_tiles_per_arm'][arm]==
                inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm_raw+raw_per_arm,
            'per-method source/warmup/allraw economic budget')
        fits=[l['arms'][arm]['fit_totals'] for l in lives]
        require(account['processed_training_samples'][arm]==sum(f['trained_afterstates'] for f in fits)
            and account['fit_counts'][arm]==sum_counts(f['learning_counts'] for f in fits),'actual differing fit sample/write inventories')
        for field,part in (('fit_target_counts','target_counts'),('consolidation_counts','consolidation_counts')):
            require(account[field][arm]==sum_counts({k:v for k,v in f[part].items() if not k.endswith('_peak')} for f in fits),
                'actual fit target/consolidation cost')
        peaks={key:max(f[part].get(key,0) for f in fits) for part in ('target_counts','consolidation_counts')
            for key in {k for f in fits for k in f[part] if k.endswith('_peak')}}
        require(account['fit_buffer_peaks'][arm]==peaks,'buffer peaks added as work')
        require(account['final_unfitted_raw_tiles_per_arm'][arm]==sum(l['arms'][arm]['final_unfitted_game']['raw_tiles'] for l in lives)
            and account['private_head_weight_bytes_created'][arm]==sum(l['arms'][arm]['head_setup']['private_weight_bytes'] for l in lives),
            'unfinished raw/private head cost omitted')
        for kind in ('environment','planning','learning'):
            require(account['training_counts_per_arm'][arm][kind]==sum_counts(l['arms'][arm]['training_counts'][kind] for l in lives),
                'actual per-arm environment/planning/fitting cost')
        parts=('evaluation_counts','retention_evaluation_counts','a_head_on_B_evaluation_counts')
        for part in parts:
            for kind in ('environment','planning'):
                require(account['evaluation_components_per_arm'][arm][part][kind]==sum_counts(l['arms'][arm][part][kind] for l in lives),
                    'current/retention/reference-head physical evaluation cost')
        for kind in ('environment','planning'):
            require(account['evaluation_counts_per_arm'][arm][kind]==sum_counts(l['arms'][arm][part][kind] for l in lives for part in parts),
                'all evaluation components charged exactly once')
        require(close(account['fit_cpu_seconds_per_arm'][arm],sum(f['cpu_seconds'] for f in fits))
            and close(account['arm_cpu_seconds'][arm],sum(l['arms'][arm]['costs']['cpu_seconds'] for l in lives)),
            'actual fit/whole-arm CPU scopes')
        require(account['memory_counts_per_arm'][arm]==sum_counts(l['arms'][arm]['final_memory']['counts'] for l in lives),
            'imported warmup plus actor memory counter scope')
    for field,kinds in (('training_counts',('environment','planning','learning')),('evaluation_counts',('environment','planning'))):
        for kind in kinds:
            require(account[field][kind]==sum_counts(account[field+'_per_arm'][arm][kind] for arm in ARMS),
                'all physical trajectory/evaluation work')
    require(account['evaluation_counts']['environment']['initial_spawns']==2*13312,'missing or duplicated reference/retention evaluation games')
    require(account['retained_A_head_setups']==[l['arms']['MEAN_H2']['retained_A_head_setup'] for l in lives],
        'retained A head actual copy/storage/setup cost')
    require(account['reconstruction_counts']==sum_counts(l['arms'][arm]['costs']['reconstruction_counts'] for l in lives for arm in ARMS)
        and close(account['reconstruction_cpu_seconds'],sum(l['arms'][arm]['costs']['reconstruction_cpu_seconds'] for l in lives for arm in ARMS)),
        'actual board/afterstate processing cost')
    for parent in parents:
        require(parent['source_setup']['checkpoint_loads']==1 and parent['source_setup']['new_leaf_updates']==0,
            'source once/shared frozen initialization')
    for field in ('worker_cpu_seconds','compiler_cpu_seconds'):
        require(close(account[field],sum(p['cpu_seconds' if field=='worker_cpu_seconds' else field] for p in parents)),
            'actual process CPU aggregate')
    require(account['canonical_trace_bytes']==sum(p['trace_bytes'] for p in parents),'retained physical trace size')
    previous=account['development_reference']
    require(previous['previous_pilot']=='V291' and previous['previous_target_acquisition_raw_tiles']==
        old['accounting']['new_training_environment_observations'] and previous['previous_evaluation_counts']==old['accounting']['evaluation_counts'],
        'pilot costs duplicated as training inputs or lost')


PAIRS=(('MEAN_H2','FROZEN_H2'),('NSEQ_H2','FROZEN_H2'),('MEAN_H2','NSEQ_H2'),
    ('FROZEN_H2','FROZEN_DIRECT'),('MEAN_DIRECT','FROZEN_DIRECT'),('MEAN_H2','MEAN_DIRECT'))


def pooled(rows):
    return dict(mean_game_utility=mean(row['mean_game_utility'] for row in rows),
        **{key:sum(row[key] for row in rows) for key in ('games','wins','losses','cutoffs','steps')})


def check_result_summary(summary,records):
    equal_tree(summary['by_lifecycle'],records,'signed complete checkpoint outcomes')
    expected_arms={}
    for arm in ARMS:
        phases={}
        for phase in PHASES:
            rows=[row['arms'][arm]['phases'][phase] for row in records]
            phases[phase]=dict(pooled(rows),training_cutoffs=sum(row['training_cutoffs'] for row in rows),
                retention_probe=pooled([row['retention_probe'] for row in rows]))
        expected_arms[arm]=dict(mean_game_utility=mean(row['arms'][arm]['mean_game_utility'] for row in records),
            phases=phases,**{key:sum(phases[phase][key] for phase in PHASES)
                for key in ('games','wins','losses','cutoffs','steps','training_cutoffs')})
    equal_tree(summary['arms'],expected_arms,'equal games/three phases/life means')
    names={left+'_minus_'+right for left,right in PAIRS}
    require(set(summary['paired_contrasts'])==names and set(summary['phase_contrasts'])==set(PHASES)
        and all(set(summary['phase_contrasts'][phase])==names for phase in PHASES),'registered online contrasts')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],
            [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records],'higher_is_better')
        for phase in PHASES:
            check_contrast(summary['phase_contrasts'][phase][name],
                [row['arms'][left]['phases'][phase]['mean_game_utility']-row['arms'][right]['phases'][phase]['mean_game_utility']
                    for row in records],'higher_is_better')
    correction=summary['correction_contrast']
    require(correction['name']=='MEAN_H2_current_B_minus_A_head_on_B','registered correction endpoint')
    check_contrast(correction,[row['arms']['MEAN_H2']['phases']['B']['mean_game_utility']-
        row['arms']['MEAN_H2']['phases']['B']['a_head_on_B']['mean_game_utility'] for row in records],'higher_is_better')
    ahead=pooled([row['arms']['MEAN_H2']['phases']['B']['a_head_on_B'] for row in records])
    equal_tree(summary['a_head_on_B'],ahead,'saved A reference-head same B endpoint')
    require(set(summary['retention_contrasts'])==set(ARMS),'retention coverage')
    for arm in ARMS:
        require(set(summary['retention_contrasts'][arm])=={'after_B','restoration','final_vs_A'},'retention endpoint names')
        for name,left,right in (('after_B','B','A'),('restoration','A_prime','B'),('final_vs_A','A_prime','A')):
            check_contrast(summary['retention_contrasts'][arm][name],
                [row['arms'][arm]['phases'][left]['retention_probe']['mean_game_utility']-
                    row['arms'][arm]['phases'][right]['retention_probe']['mean_game_utility'] for row in records],'higher_is_better')
    training_cutoffs=sum(row['training_cutoffs'] for row in expected_arms.values())
    current_cutoffs=sum(row['cutoffs'] for row in expected_arms.values())
    additional_cutoffs=ahead['cutoffs']+sum(expected_arms[arm]['phases'][phase]['retention_probe']['cutoffs']
        for arm in ARMS for phase in ('B','A_prime'))
    evaluation_cutoffs=current_cutoffs+additional_cutoffs;complete=training_cutoffs==evaluation_cutoffs==0
    require(summary['bootstrap_draws']==20000 and summary['bootstrap_seed']==29200001
        and summary['primary_contrast']=='MEAN_H2_minus_FROZEN_H2'
        and summary['estimator']=='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES'
        and summary['training_cutoffs']==training_cutoffs and summary['evaluation_cutoffs']==evaluation_cutoffs
        and summary['current_evaluation_cutoffs']==current_cutoffs and summary['additional_probe_cutoffs']==additional_cutoffs
        and summary['physical_evaluation_games']==13312 and summary['complete_game_endpoints']==complete,
        'bootstrap scope/endpoint weights/natural terminal coverage')
    confirmed=complete and summary['paired_contrasts']['MEAN_H2_minus_FROZEN_H2']['ci95'][0]>0
    require(summary['online_learning_confirmed']==confirmed
        and summary['online_learning_status']==('SUPPORTED_' if confirmed else 'NOT_SUPPORTED_')+'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and summary['correction_supported']==(complete and correction['ci95'][0]>0),
        'online/correction support substitutes a different endpoint')


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected=dict(lifecycles=list(range(16)),parents=4,arms=list(ARMS),phases=[['A',.1],['B',.5],['A_prime',.1]],
        raw_tiles_per_phase=RAW,evaluation_games=32,max_steps=8192,alpha=.0025,
        query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        seed_warmup=292100000000,seed_training=292200000000,seed_evaluation=292900000000,
        bootstrap_seed=29200001,bootstrap_draws=20000,
        primary='MEAN_H2_minus_FROZEN_H2_THREE_PHASE_COMPLETE_GAME_UTILITY',
        training='IMMEDIATE_NATURAL_GAME_CONSOLIDATION_WITHOUT_NATIVE_SARSA',
        memory_input='ALL_RAW_SPAWNS_INCLUDING_INITIAL',retention='SAVED_A_BELIEF_AND_A_SEEDS_ACROSS_ALL_CHECKPOINTS',
        correction='CURRENT_B_HEAD_MINUS_SAVED_A_HEAD_WITH_SAME_B_BELIEF_AND_SEEDS',
        finite_test_passes=dict(native=13,online=7,analysis=18,driver=4))
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    require(d['schema']=='acfqp.natural_episode.v292' and d['status']=='EXPERIMENT_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE','experimental status')
    old=json_file(settings['source_summary'])
    require(json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid']
        and old['summary']['independent_learning_confirmed'],'confirmed V291 prerequisite')
    require(d['source_provenance']==old['source_provenance'],'source value/dynamics changed')
    lives=d['by_lifecycle']
    require([row['lifecycle'] for row in lives]==list(range(16)) and all(row['parent']==row['lifecycle']%4 for row in lives),
        'complete fixed-source new-life cohort')
    canonical,warmups,rows_read=read_canonical(d);records=[]
    for row in lives:
        life=row['lifecycle'];warm=row['warmup'];actual=warmups[life]
        require(warm['game_summaries']==actual['games'] and warm['raw_tiles']==actual['memory'].obs
            and warm['memory_events']==actual['events'] and warm['final_memory']==actual['memory'].learned(),
            'shared warmup prefix/provenance changed')
        require(Counter(warm['environment_counts'])==actual['environment'] and Counter(warm['direct_counts'])==actual['direct']
            and Counter({k:v for k,v in warm['memory_counts'].items() if k!='predict_calls'})==actual['memory'].counts,
            'physical shared warmup work')
        arms={}
        for arm in ARMS:
            metrics,probes,ahead=check_arm(row['arms'][arm],canonical[life,arm],life,arm)
            phases={phase:dict(metrics[phase],training_cutoffs=row['arms'][arm]['phases'][phase]['training']['cutoff_games'],
                retention_probe=probes[phase]) for phase in PHASES}
            if ahead is not None:phases['B']['a_head_on_B']=ahead
            arms[arm]=dict(mean_game_utility=mean(metrics[phase]['mean_game_utility'] for phase in PHASES),phases=phases)
        records.append(dict(lifecycle=life,parent=life%4,arms=arms))
    summary=d['summary'];check_result_summary(summary,records);check_accounting(d,old)
    account=d['accounting']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,canonical_rows=rows_read,
        physical_training_raw_tiles=5*16*3*RAW,physical_warmup_raw_tiles=account['physical_warmup_raw_tiles'],
        physical_evaluation_games=13312,training_cutoffs=summary['training_cutoffs'],evaluation_cutoffs=summary['evaluation_cutoffs'],
        processed_training_samples=account['processed_training_samples'],
        actual_parameter_writes={arm:account['fit_counts'][arm].get('table_updates',0) for arm in ARMS},
        final_unfitted_raw_tiles_per_arm=account['final_unfitted_raw_tiles_per_arm'],
        economic_training_raw_tiles_per_arm=account['economic_training_raw_tiles_per_arm'],
        online_learning_confirmed=summary['online_learning_confirmed'],correction_supported=summary['correction_supported'],
        primary=summary['paired_contrasts']['MEAN_H2_minus_FROZEN_H2'],correction=summary['correction_contrast'],
        retention={arm:{key:{field:value[field] for field in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for key,value in comparisons.items()} for arm,comparisons in summary['retention_contrasts'].items()},
        method='All raw/action/score receipts, native no-SARSA and terminal-first fitting chronology, '
            'full mixed-phase episode labels/sample/write inventories, shared raw/router memory, static terminal/utility '
            'and seed receipts, fixed-belief/reference-head contrasts, signed equal-game/phase/life endpoints and all physical/economic costs.',
        limitations='No world/full intermediate board/weight fitting replay or 20000-draw bootstrap regeneration. '
            'The producer deterministically reconstructs actual afterstates; this audit independently checks raw, action, '
            'score, game, fit and observed-memory receipts. Conditional on four inherited sources. '
            'Different online policies acquire different games; MEAN H2 versus DIRECT is a closed-loop comparison.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
