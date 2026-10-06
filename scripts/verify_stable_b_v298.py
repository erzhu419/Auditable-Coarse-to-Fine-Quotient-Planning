#!/usr/bin/env python3
"""Independent stable-B acquisition, episode-label and result receipt audit."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, factual_targets, json_file, require, sum_counts
from verify_episode_consolidation_v290 import check_normalized_fit
from verify_natural_online_value_v286 import Memory, check_chunk, planning_counts, terminal
from verify_retained_critic_v287 import check_holdout

ARMS=('FROZEN','NORMALIZED_SEQUENTIAL_MC','EPISODE_MEAN_MC')
PAIRS=(('EPISODE_MEAN_MC','FROZEN'),('NORMALIZED_SEQUENTIAL_MC','FROZEN'),
    ('EPISODE_MEAN_MC','NORMALIZED_SEQUENTIAL_MC'))
RAW=131072
EVALUATION_BASE=298900000000


def warmup_seed(life,game):
    return 298100000000+life*1000000+game


def training_seed(life):
    return 298200000000+life*10000000


def evaluation_seed(life,episode):
    return EVALUATION_BASE+life*1000000+episode


def check_contrast(saved,values,direction=None):
    require(len(values)==64,'all fresh life endpoint values')
    require(close(saved['mean'],mean(values)),'signed paired mean')
    equal_tree(saved['lifecycle_deltas'],{str(i):value for i,value in enumerate(values)},'signed fresh life deltas')
    groups=[values[p::4] for p in range(4)]
    equal_tree(saved['parent_mean_deltas'],{str(p):mean(g) for p,g in enumerate(groups)},'fixed sixteen-life parent means')
    require(saved['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS','fixed source interval scope')
    low,high=saved['ci95']
    require(mean(min(g) for g in groups)-1e-10<=low<=high<=mean(max(g) for g in groups)+1e-10,
        'possible conditional whole-life resampling range')
    if direction:
        losses=values if direction=='lower_is_better' else [-value for value in values]
        require(saved['improved_equal_worse']==[sum(v<0 for v in losses),sum(v==0 for v in losses),sum(v>0 for v in losses)]
            and saved['adverse_lifecycles']==[i for i,v in enumerate(losses) if v>0],'signed adverse fresh histories')
    else:require('improved_equal_worse' not in saved and 'adverse_lifecycles' not in saved,'signed bias assigned quality')
    if direction!='higher_is_better':require(saved['positive_equal_negative']==[
        sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)],'literal endpoint sign counts')


def check_evaluation(games,life,counts):
    require(len(games)==32 and [g['seed'] for g in games]==[evaluation_seed(life,i) for i in range(32)],
        'registered independent paired evaluation seeds')
    for game in games:
        require(1<=game['steps']<=8192,'new evaluation horizon')
        if game['status']=='CUTOFF':
            require(game['steps']==8192 and max(game['final_board'])<11,'premature cutoff/goal at cutoff')
            bonus=0.
        else:
            terminal(game['final_board'],game['status']);bonus=4. if game['status']=='WON' else -4.
        require(game['utility']==game['score']/2048.+bonus,'new complete-game utility')
    steps,wins=sum(g['steps'] for g in games),sum(g['status']=='WON' for g in games)
    env=dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=64,
        raw_tile_productions=steps+64,environment_random_draws=2*(steps+64),ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32,ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment'])==Counter(env),'new 32-game evaluation physical ledger')
    planning_counts(counts['planning'],steps)
    return dict(games=32,mean_game_utility=mean(g['utility'] for g in games),wins=wins,
        losses=sum(g['status']=='LOST' for g in games),cutoffs=sum(g['status']=='CUTOFF' for g in games),
        cutoff_episodes=[i for i,g in enumerate(games) if g['status']=='CUTOFF'],steps=steps)


def check_b_context(row):
    require(row['phase']=='B' and row['true_p_four']==.5,
        'stable B actual environment context/probability')


def check_warmup(row,index,memory):
    require(memory.obs<256,'warmup continued beyond the fixed raw threshold')
    game=row['summary'];raw=row['raw_spawns'];steps=game['steps']
    require(game['seed']==warmup_seed(row['lifecycle'],index),'fresh complete warmup seed')
    terminal(row['final_board'],game['status'])
    require(game['utility']==game['score']/2048.+(4. if game['status']=='WON' else -4.),'warmup utility/terminal')
    require(len(row['actions'])==len(row['scores'])==steps and sum(row['scores'])==game['score'],'warmup actual score inventory')
    require(len(raw)==steps+2 and [r['kind'] for r in raw[:2]]==['INITIAL','INITIAL']
        and all(r['kind']=='POST_ACTION' for r in raw[2:]),'warmup all initial/post-action tiles')
    won=game['status']=='WON'
    env=dict(initial_spawns=2,sampled_transitions=steps,environment_random_draws=2*(steps+2),
        ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+1,
        ground_status_internal_swipe_calls=4*(steps+1-won),ground_swipe_calls=steps+4*(steps+1-won))
    require(Counter(row['counts']['environment'])==Counter(env),'warmup physical environment costs')
    direct=Counter(row['counts']['direct'])
    require(direct['choose_calls']==steps and direct['inner_choose_calls']==steps
        and direct['inner_learned_swipe_calls']==4*steps
        and direct['inner_line_table_lookups']==4*direct['inner_learned_swipe_calls']
        and direct['inner_table_lookups']==32*direct['inner_value_predictions']
        and direct['td_updates']==direct['inner_td_updates']==0,'frozen DIRECT warmup planning/value work')
    check_b_context(row)
    return memory.consume(r['rank'] for r in raw)


def learned(payload):
    return {key:payload[key] for key in ('observations_seen','active_module_id','modules','pending')}


def check_split(dataset,games,scores,fit_memories,warm_raw,training):
    n=4*len(games)//5
    require(0<n<len(games) and dataset['fit_game_count']==n,'chronological complete-game 80/20 split')
    require(dataset['games']==[dict(game,split='FIT' if i<n else 'HELDOUT') for i,game in enumerate(games)],
        'new complete-game membership/heldout prefix')
    require(all(len(scores[g['episode']])==g['steps'] and sum(scores[g['episode']])==g['score'] for g in games),
        'canonical complete factual score sequences')
    fit_steps=sum(g['steps'] for g in games[:n]);all_steps=sum(g['steps'] for g in games)
    fit_raw,complete_raw=games[n-1]['end_raw'],games[-1]['end_raw']
    require(dataset['fit_step_end']==fit_steps and dataset['fit_end_raw']==fit_raw,'complete fit temporal boundary')
    require(learned(dataset['fit_memory'])==fit_memories[games[n-1]['episode']]
        and dataset['fit_memory']['observations_seen']==warm_raw+fit_raw,'heldout/future leaked into fit-prefix belief')
    expected=dict(full_B_raw_tiles=RAW,fit_raw_tiles=fit_raw,heldout_raw_tiles=complete_raw-fit_raw,
        fit_steps=fit_steps,heldout_steps=all_steps-fit_steps,excluded_tail_games=int(complete_raw<RAW),
        excluded_tail_raw_tiles=RAW-complete_raw,
        excluded_tail_steps=training['after_stream']['post_action_spawns']-all_steps,warmup_raw_tiles=warm_raw)
    require(all(dataset['costs'][key]==value for key,value in expected.items()),'paid full acquisition/excluded tail ledger')
    require(dataset['costs']['full_B_acquisition_counts']==training['counts'],'new acquisition work omitted/reweighted')
    return n


def read_canonical(d):
    """All newly acquired ranks/actions/labels, without executing a world."""
    result={};rows_read=0
    for parent in d['parent_receipts']:
        pid=parent['parent'];ids=list(range(pid,64,4))
        require(parent['lifecycle_ids']==ids,'new source/lifecycle assignment')
        states={life:dict(memory=Memory(),warm_games=[],warm_environment=Counter(),warm_direct=Counter(),
            warm_events=[],warm_rows=0,training_rows=0,training_events=[],train_counts={k:Counter()
            for k in ('environment','planning','learning')},last_stream=None,games=[],scores=defaultdict(list),
            game_memories={},snapshot=None) for life in ids}
        trace=Path(parent['trace_file']);require(trace.stat().st_size==parent['trace_bytes'],'canonical acquisition storage')
        with gzip.open(trace,'rt') as stream:
            for line in stream:
                row=json.loads(line);rows_read+=1;life=row['lifecycle']
                require(life in states and row['parent']==pid,'canonical fresh life/source context')
                state=states[life];memory=state['memory']
                if row['kind']=='WARMUP':
                    require(state['last_stream'] is None,'warmup occurred after new training began')
                    state['warm_events'].extend(check_warmup(row,state['warm_rows'],memory))
                    state['warm_rows']+=1;state['warm_games'].append(row['summary'])
                    state['warm_environment'].update(row['counts']['environment']);state['warm_direct'].update(row['counts']['direct'])
                    continue
                if row['kind']=='TRAIN':
                    if state['last_stream'] is None:
                        require(memory.obs>=256,'fresh actor has no complete warmup')
                        state.update(warm_final=memory.learned(),warm_counts=memory.counts.copy(),warm_raw=memory.obs,
                            before_stream=row['start'])
                        require(row['start']['raw_tiles']==row['start']['random_draw_position']==0,'new actor starts inside an old history')
                    else:require(row['start']==state['last_stream'],'fresh training stream continuity')
                    check_b_context(row)
                    require(row['arm']=='FROZEN' and row['phase']=='B' and row['start']['stream_seed']==training_seed(life),
                        'acquisition actor/phase/fresh stream seed')
                    require(state['snapshot'] is None,'training continued after the fixed acquisition boundary')
                    check_chunk(row,RAW-row['start']['raw_tiles'],memory)
                    completions={g['end_raw']:g for g in row['completed_games']}
                    rewards=iter(row['scores']);events=[]
                    for offset,spawn in enumerate(row['raw_spawns']):
                        if spawn['kind']=='POST_ACTION':state['scores'][spawn['episode']].append(next(rewards))
                        events.extend(memory.consume([spawn['rank']]))
                        absolute=row['start']['raw_tiles']+offset+1
                        if absolute in completions:
                            game=completions[absolute];state['game_memories'][game['episode']]=memory.learned()
                    require(events==row['memory_events'],'new all-raw observed-prefix Beta/router events')
                    state['training_events'].extend(events);state['training_rows']+=1
                    for key in state['train_counts']:state['train_counts'][key].update(row['counts'][key])
                    state['games'].extend(row['completed_games']);state['last_stream']=row['end']
                    continue
                require(row['kind']=='ACQUISITION_SNAPSHOT' and state['snapshot'] is None,'new actor snapshot kind/inventory')
                require(state['last_stream'] is not None and state['last_stream']['raw_tiles']==RAW,
                    'snapshot before the fixed paid raw budget')
                check_b_context(row)
                snapshot=row['snapshot'];training=row['training']
                require(snapshot['stream']==state['last_stream'] and snapshot['memory']==memory.learned()
                    and snapshot['estimated_p_four']==memory.probability() and snapshot['new_value_updates']==0,
                    'final acquisition stream/learned memory/value freeze')
                require(training['raw_tiles']==RAW and training['chunks']==state['training_rows']
                    and training['memory_event_count']==len(state['training_events'])
                    and training['before_stream']==state['before_stream'] and training['after_stream']==state['last_stream'],
                    'canonical fixed raw/chunk/event boundary')
                require(all(Counter(training['counts'][key])==value for key,value in state['train_counts'].items()),
                    'canonical acquired environment/planning/value totals')
                require(Counter({k:v for k,v in training['memory_counts'].items() if k!='predict_calls'})
                    ==memory.counts-state['warm_counts'],'observed raw/model memory work')
                require(row['arm']=='FROZEN' and row['phase']=='B','canonical acquisition snapshot context')
                state['snapshot']=snapshot;state['training']=training
        for life,state in states.items():
            require(state['snapshot'] is not None,'missing fresh acquisition boundary snapshot')
            require(state['memory'].obs==state['warm_raw']+RAW,'all initial/post-action raw budget')
            result[life]=state
    require(set(result)==set(range(64)),'all 64 independent actor histories')
    return result,rows_read


def check_result_summary(summary,records,cutoffs):
    equal_tree(summary['by_lifecycle'],records,'complete new game/heldout means')
    require(summary['primary_contrast']==summary['primary_prediction_contrast']=='EPISODE_MEAN_MC_minus_FROZEN'
        and summary['primary_prediction_metric']=='mse' and summary['bootstrap_draws']==20000
        and summary['bootstrap_seed']==29800001
        and summary['estimator']=='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator']=='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES'
        and summary['complete_game_endpoints']==(cutoffs==0),'endpoint/weighting/complete terminal scope')
    for arm in ARMS:
        arm_rows=[r['arms'][arm] for r in records];heldout=[r['heldout'] for r in arm_rows]
        equal_tree(summary['arms'][arm],dict(mean_game_utility=mean(r['mean_game_utility'] for r in arm_rows),
            **{key:sum(r[key] for r in arm_rows) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(r['games'] for r in heldout),samples=sum(r['samples'] for r in heldout),
                **{key:mean(r[key] for r in heldout) for key in ('bias','mse','mae')})),'equal fresh life mean '+arm)
    names={left+'_minus_'+right for left,right in PAIRS}
    require(set(summary['paired_contrasts'])==set(summary['heldout_contrasts'])==names,'registered contrasts')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],
            [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records],'higher_is_better')
        for key in ('bias','mse','mae'):
            check_contrast(summary['heldout_contrasts'][name][key],
                [r['arms'][left]['heldout'][key]-r['arms'][right]['heldout'][key] for r in records],
                None if key=='bias' else 'lower_is_better')
    primary='EPISODE_MEAN_MC_minus_FROZEN'
    supported=cutoffs==0 and summary['paired_contrasts'][primary]['ci95'][0]>0
    require(summary['stable_b_learning_supported']==supported
        and summary['independent_learning_confirmed']==supported
        and summary['independent_learning_status']==('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+
            'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and summary['independent_prediction_supported']==(summary['heldout_contrasts'][primary]['mse']['ci95'][1]<0),
        'prediction substituted for independent complete-game gain')


def check_accounting(d,old,processed):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];account=d['accounting']
    inherited_old=old['accounting']['inherited_costs_per_arm']['FROZEN']
    inherited={key:inherited_old[key] for key in ('source_training_raw_tiles','source_training_games',
        'source_training_environment_counts','source_training_seconds','dynamics_raw_tiles','dynamics_costs')}
    warm=sum(l['acquisition']['warmup']['raw_tiles'] for l in lives);actor=64*RAW
    economic=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+actor
    require(account['new_training_environment_observations']==warm+actor and account['physical_acquisitions']==64
        and account['new_warmup_raw_tiles']==warm and account['new_actor_B_raw_tiles']==actor
        and account['processed_training_samples']==dict(processed),'fresh physical acquisition/sample budget')
    require(account['excluded_tail_raw_tiles']==sum(l['dataset']['costs']['excluded_tail_raw_tiles'] for l in lives),
        'paid excluded target tail omitted')
    actual_actor={kind:sum_counts(l['acquisition']['training']['counts'][kind] for l in lives)
        for kind in ('environment','planning','learning')}
    require(account['new_actor_B_counts']==actual_actor,'new actor work totals')
    for field,name in (('new_warmup_environment_counts','environment_counts'),
        ('new_warmup_direct_counts','direct_counts'),('new_warmup_memory_counts','memory_counts')):
        require(account[field]==sum_counts(l['acquisition']['warmup'][name] for l in lives),'actual '+field)
    require(account['new_actor_memory_counts']==sum_counts(l['acquisition']['training']['memory_counts'] for l in lives),
        'actual actor memory work')
    environment=Counter(actual_actor['environment'])+Counter(account['new_warmup_environment_counts'])
    environment['raw_tile_productions']=warm+actor
    require(Counter(account['new_training_environment_counts'])==environment,'physical initial/full-game/raw training costs')
    for field,name in (('reconstruction_counts','counts'),('reconstruction_memory_counts','memory_counts')):
        require(account[field]==sum_counts(l['acquisition']['reconstruction'][name] for l in lives),'actual '+field)
    require(close(account['reconstruction_cpu_seconds'],sum(l['acquisition']['reconstruction']['cpu_seconds'] for l in lives)),
        'reconstruction CPU aggregate')
    for arm in ARMS:
        require(account['inherited_costs_per_arm'][arm]==inherited
            and account['economic_training_raw_tiles_per_arm'][arm]==economic,'source once/new target full economic cost')
        for field,section,name in (('fit_counts','fit','learning_counts'),('heldout_prediction_counts','heldout','prediction_counts')):
            require(account[field][arm]==sum_counts(l['arms'][arm][section][name] for l in lives),'actual '+field)
        for section in ('fit','heldout'):
            targets=[l['arms'][arm][section]['target_counts'] for l in lives]
            require(account[section+'_target_counts'][arm]==sum_counts(
                {k:v for k,v in counts.items() if k!='target_buffer_doubles_peak'} for counts in targets),
                'actual target work')
            require(account[section+'_target_buffer_doubles_peak'][arm]==max(c.get('target_buffer_doubles_peak',0) for c in targets),
                'target buffer peaks accumulated')
        counts=[l['arms'][arm]['fit']['consolidation_counts'] for l in lives]
        require(account['consolidation_counts'][arm]==sum_counts(
            {k:v for k,v in c.items() if not k.endswith('_peak')} for c in counts),'actual consolidation work')
        peaks={key:max(c.get(key,0) for c in counts) for key in {k for c in counts for k in c if k.endswith('_peak')}}
        require(account['consolidation_buffer_peaks'][arm]==peaks,'consolidation buffer peaks accumulated')
        require(account['private_head_weight_bytes_created'][arm]==sum(l['arms'][arm]['head_setup']['private_weight_bytes'] for l in lives),
            'private head allocation cost')
        for kind in ('environment','planning'):
            require(account['evaluation_counts_per_arm'][arm][kind]==sum_counts(l['arms'][arm]['evaluation_counts'][kind] for l in lives),
                'per-arm new evaluation cost')
        for stage in ('fit','heldout'):
            for field,timing in (('processing_seconds_per_arm','seconds'),('processing_cpu_seconds_per_arm','cpu_seconds')):
                require(close(account[field][arm][stage],sum(l['arms'][arm][stage][timing] for l in lives)),
                    'scoped fit/heldout processing time')
        require(close(account['evaluation_cpu_seconds_per_arm'][arm],sum(l['arms'][arm]['evaluation_cpu_seconds'] for l in lives)),
            'scoped evaluation CPU')
    for kind in ('environment','planning'):
        require(account['evaluation_counts'][kind]==sum_counts(l['arms'][a]['evaluation_counts'][kind] for l in lives for a in ARMS),
            'physical new evaluation cost')
    require([p['parent'] for p in parents]==list(range(4)),'source physical loads')
    for parent in parents:
        require(parent['source_setup']['checkpoint_loads']==1 and parent['source_setup']['new_leaf_updates']==0,
            'source once/shared frozen initialization')
    for field in ('worker_cpu_seconds','compiler_cpu_seconds'):
        require(close(account[field],sum(p['cpu_seconds' if field=='worker_cpu_seconds' else field] for p in parents)),
            'actual process CPU aggregate')
    require(account['canonical_trace_bytes']==sum(p['trace_bytes'] for p in parents),'canonical retained storage aggregate')
    previous=account['development_reference']
    require(previous['previous_pilot']=='V291'
        and previous['previous_target_acquisition_raw_tiles']==old['accounting']['new_training_environment_observations']
        and previous['previous_evaluation_counts']==old['accounting']['evaluation_counts'],'pilot development costs dropped/reused as new inputs')
    return economic


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected=dict(lifecycles=list(range(64)),parents=4,arms=list(ARMS),phase='B',true_p_four=.5,raw_budget=RAW,
        fit_fraction=.8,alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        seed_warmup=298100000000,seed_training=298200000000,seed_evaluation=EVALUATION_BASE,
        evaluation_games=32,max_steps=8192,bootstrap_draws=20000,bootstrap_seed=29800001,
        primary='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_GAME_UTILITY',
        primary_prediction='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_HELDOUT_MSE',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        training='FROZEN_SOURCE_B_ONLY_FULL_GAME_OFFLINE_CONSOLIDATION')
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    require(settings['schema']=='acfqp.stable_b_freeze.v298', 'frozen stable-B schema')
    require(d['schema']=='acfqp.stable_b.v298' and d['status']=='EXPERIMENT_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE','experimental status')
    old=json_file(settings['source_summary'])
    require(old['schema']=='acfqp.independent_episode.v291'
        and json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid'],
        'frozen V291 source/method audit')
    require(d['source_provenance']==old['source_provenance'],'source value/dynamics provenance changed')
    lives=d['by_lifecycle']
    require([l['lifecycle'] for l in lives]==list(range(64)) and all(l['parent']==l['lifecycle']%4 for l in lives),
        'complete fresh fixed-source cohort')
    canonical,rows_read=read_canonical(d)
    records=[];processed=Counter();fit_games_total=heldout_games_total=heldout_samples=cutoffs=0
    for life in lives:
        lid=life['lifecycle'];state=canonical[lid];ds=life['dataset'];acq=life['acquisition'];warm=acq['warmup']
        require(acq['new_value_updates']==0 and acq['physical_acquisitions']==1 and acq['new_evaluation_games']==0,
            'fresh acquisition changed source/trained or evaluated')
        require(warm['game_summaries']==state['warm_games'] and warm['raw_tiles']==state['warm_raw']
            and warm['memory_events']==state['warm_events'] and warm['final_memory']==state['warm_final'],
            'complete warmup/all-raw learned memory inventory')
        require(Counter(warm['environment_counts'])==state['warm_environment']
            and Counter(warm['direct_counts'])==state['warm_direct']
            and Counter({k:v for k,v in warm['memory_counts'].items() if k!='predict_calls'})==state['warm_counts'],
            'warmup environment/DIRECT/memory physical counts')
        require(acq['snapshot']==state['snapshot'] and acq['training']==state['training'],'canonical acquisition summary changed')
        require(learned(ds['actor_memory_B_end'])==state['memory'].learned(),'final actor memory/heldout observation inventory')
        n=check_split(ds,state['games'],state['scores'],state['game_memories'],state['warm_raw'],state['training'])
        for key in ('environment_counts','direct_counts','memory_counts'):
            require(ds['costs']['warmup_'+key]==warm[key],'new warmup reconstruction/acquisition ledger')
        rec=acq['reconstruction']
        require(rec['counts']==ds['costs']['processing_counts'] and rec['memory_counts']==ds['costs']['processing_memory_counts']
            and rec['chunks']==ds['costs']['reconstructed_chunks']==state['training_rows']
            and rec['cpu_seconds']==ds['costs']['processing_cpu_seconds'],'actual reconstruction CPU/work cost')
        snapshot=life['evaluation_snapshot'];prefix=learned(ds['fit_memory'])
        module=prefix['modules'][prefix['active_module_id']]
        require(learned(snapshot['memory'])==prefix
            and snapshot['estimated_p_four']==module['alpha']/(module['alpha']+module['beta']),
            'static shared fit-prefix belief includes heldout/new evaluation feedback')
        games=ds['games'];fit_games=games[:n];heldout_games=games[n:]
        score_rows=[state['scores'][g['episode']] for g in heldout_games]
        fit_samples=sum(g['steps']-(g['status']=='WON') for g in fit_games)
        arms={}
        for arm in ARMS:
            value=life['arms'][arm];fit=value['fit'];setup=value['head_setup']
            expected_samples=0 if arm=='FROZEN' else fit_samples
            require(value['processed_training_samples']==value['sample_counter']==fit['trained_afterstates']==expected_samples,
                'same chronological nonwinning sample inventory')
            processed[arm]+=expected_samples
            if arm=='FROZEN':
                require(fit['method']=='NONE' and not fit['learning_counts'] and not fit['target_counts']
                    and not fit['consolidation_counts'] and setup['source_weights_shared']
                    and setup['private_weight_bytes']==0,'frozen acquisition source fitted/copied')
            else:
                check_normalized_fit(fit,fit_games,ds,state['scores'],arm)
                require(not setup['source_weights_shared']
                    and setup['private_weight_bytes']==setup['setup_counts']['source_weight_bytes_copied'],
                    'same inherited source head initialization/private copy cost')
            heldout=check_holdout(value['heldout'],heldout_games,score_rows,ds['fit_step_end'])
            arms[arm]=dict(check_evaluation(value['game_summaries'],lid,value['evaluation_counts']),heldout=heldout)
            cutoffs+=arms[arm]['cutoffs']
        left,right=(life['arms'][a]['fit']['consolidation_counts'] for a in ARMS[1:])
        for key in ('feature_extractions','feature_occurrences','feature_digit_reads','feature_address_multiply_adds',
            'game_sort_calls','game_sort_items','game_sort_comparisons','address_occurrence_count_visits',
            'address_occurrence_count_comparisons','sample_sort_calls','sample_sort_items','sample_sort_comparisons',
            'address_denominator_searches','address_denominator_search_comparisons','sample_unique_addresses','game_unique_addresses'):
            require(left[key]==right[key],'same full addresses/exposures for both methods')
        records.append(dict(lifecycle=lid,parent=lid%4,arms=arms))
        fit_games_total+=n;heldout_games_total+=len(heldout_games);heldout_samples+=arms['FROZEN']['heldout']['samples']
    summary=d['summary'];check_result_summary(summary,records,cutoffs)
    economic=check_accounting(d,old,processed)
    primary='EPISODE_MEAN_MC_minus_FROZEN'
    return dict(status='PASS',independent_valid=True,lifecycles=64,fixed_source_parents=4,canonical_rows=rows_read,
        fresh_actor_raw_tiles=64*RAW,fresh_warmup_raw_tiles=d['accounting']['new_warmup_raw_tiles'],
        fit_games=fit_games_total,heldout_games=heldout_games_total,heldout_samples_per_arm=heldout_samples,
        excluded_tail_raw_tiles=d['accounting']['excluded_tail_raw_tiles'],processed_training_samples=dict(processed),
        evaluation_games=6144,evaluation_cutoffs=cutoffs,economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={a:d['accounting']['fit_counts'][a].get('table_updates',0) for a in ARMS},
        independent_learning_confirmed=summary['independent_learning_confirmed'],
        stable_b_learning_supported=summary['stable_b_learning_supported'],
        primary_utility=summary['paired_contrasts'][primary],primary_full_heldout_mse=summary['heldout_contrasts'][primary]['mse'],
        contrasts={name:{key:value[key] for key in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for name,value in summary['paired_contrasts'].items()},
        method='Canonical fresh warmup and every training raw/action/score receipt, independent all-raw Beta/router '
            'and fit-prefix reconstruction, complete-game factual labels, normalized sample/write inventories, '
            'all evaluation terminal/utility/fresh-seed receipts, signed equal-game/life endpoints and physical/economic costs.',
        limitations='No environment, full intermediate board or source-weight/fit replay and no 20000-draw CI regeneration. '
            'The acquisition producer reconstructs its boards; this audit independently checks raw/score/terminal and memory ledgers. '
            'Inference is conditional on four inherited sources; normalization changes effective step sizes.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
