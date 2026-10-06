#!/usr/bin/env python3
"""Independent fresh-B confirmation audit of the frozen V301 local risk method."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_episode_consolidation_v290 import check_normalized_fit
from verify_natural_online_value_v286 import Memory, check_chunk, planning_counts, terminal
from verify_retained_critic_v287 import check_holdout
from verify_stable_b_v298 import check_b_context, check_split, learned
from verify_split_risk_v301 import (
    COMPONENT_METRICS, check_representation, check_split_fit, check_split_heldout,
    nonpeak,
)

ARMS = ('SOURCE', 'MC', 'LOCAL_RISK')
PAIRS = (('LOCAL_RISK', 'SOURCE'), ('MC', 'SOURCE'), ('LOCAL_RISK', 'MC'))
RAW = 131072
EVALUATION_BASE = 302900000000
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def warmup_seed(life, game):
    return 302100000000+life*1000000+game


def training_seed(life):
    return 302200000000+life*10000000


def evaluation_seed(life, episode):
    return EVALUATION_BASE+life*1000000+episode


def check_acquisition_context(row):
    check_b_context(row)
    require(row['arm'] == 'FROZEN' and row['start']['stream_seed'] == training_seed(row['lifecycle']),
        'new V302 frozen SOURCE actor and independent B training stream')


def check_support(summary, cutoffs):
    supported = cutoffs == 0 and summary['paired_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95'][0] > 0
    require(summary['independent_local_learning_confirmed'] == supported
        and summary['independent_local_learning_status'] == ('CONFIRMED_' if supported else 'NOT_CONFIRMED_')+INTERVAL_SCOPE,
        'independent local utility against SOURCE is the confirmation endpoint')


def check_contrast(saved, values, direction=None):
    require(len(values) == 64 and close(saved['mean'], mean(values)), 'all fresh life signed paired means')
    equal_tree(saved['lifecycle_deltas'], {str(i):value for i,value in enumerate(values)},
        'all signed fresh lifecycle deltas')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent):mean(group) for parent,group in enumerate(groups)},
        'four fixed sixteen-life parent means')
    low, high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE
        and mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'fresh training whole-life conditional interval scope and range')
    if direction:
        losses = [-value for value in values] if direction == 'higher_is_better' else values
        require(saved['improved_equal_worse'] == [sum(v < 0 for v in losses),sum(v == 0 for v in losses),sum(v > 0 for v in losses)]
            and saved['adverse_lifecycles'] == [i for i,v in enumerate(losses) if v > 0],
            'signed adverse fresh histories are retained')
    else:
        require('improved_equal_worse' not in saved and 'adverse_lifecycles' not in saved, 'bias has no quality direction')
    if direction != 'higher_is_better':
        require(saved['positive_equal_negative'] == [sum(v > 0 for v in values),sum(v == 0 for v in values),sum(v < 0 for v in values)],
            'literal signed contrast inventory')


def check_result_summary(summary, records, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all new game and full heldout means')
    require(summary['primary_contrast'] == 'LOCAL_RISK_minus_SOURCE'
        and summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 30200001
        and summary['estimator'] == 'EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator'] == 'EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES'
        and summary['complete_game_endpoints'] == (cutoffs == 0), 'registered fresh confirmation endpoint')
    for arm in ARMS:
        rows = [row['arms'][arm] for row in records]; heldout = [row['heldout'] for row in rows]
        expected = dict(mean_game_utility=mean(row['mean_game_utility'] for row in rows),
            **{key:sum(row[key] for row in rows) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(row['games'] for row in heldout),samples=sum(row['samples'] for row in heldout),
                **{key:mean(row[key] for row in heldout) for key in ('bias','mse','mae')}))
        if arm == 'LOCAL_RISK':
            components = [row['components'] for row in heldout]
            expected['heldout']['components'] = dict(games=sum(row['games'] for row in components),
                samples=sum(row['samples'] for row in components),
                **{key:mean(row[key] for row in components) for key in COMPONENT_METRICS})
        equal_tree(summary['arms'][arm], expected, 'equal fresh-life weighting '+arm)
    require(set(summary['paired_contrasts']) == set(summary['heldout_contrasts']) ==
        {left+'_minus_'+right for left,right in PAIRS}, 'all registered fresh contrasts')
    for left,right in PAIRS:
        name = left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],
            [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records], 'higher_is_better')
        for metric in ('bias','mse','mae'):
            check_contrast(summary['heldout_contrasts'][name][metric],
                [row['arms'][left]['heldout'][metric]-row['arms'][right]['heldout'][metric] for row in records],
                None if metric == 'bias' else 'lower_is_better')
    check_support(summary, cutoffs)


def check_evaluation(games,life,counts):
    require(len(games)==32 and [g['seed'] for g in games]==[evaluation_seed(life,i) for i in range(32)],
        'registered V302 independent paired evaluation seeds')
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


def check_warmup(row,index,memory):
    require(memory.obs<256,'warmup continued beyond the fixed raw threshold')
    game=row['summary'];raw=row['raw_spawns'];steps=game['steps']
    require(game['seed']==warmup_seed(row['lifecycle'],index),'new V302 complete warmup seed')
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
                    check_acquisition_context(row)
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


def check_lifecycle(life, state):
    """New canonical carrier, frozen fit prefix, and all three final head receipts."""
    lid = life['lifecycle']; ds = life['dataset']; acq = life['acquisition']; warm = acq['warmup']
    require(acq['new_value_updates'] == 0 and acq['physical_acquisitions'] == 1 and acq['new_evaluation_games'] == 0,
        'fresh acquisition source is unchanged and carries no evaluation feedback')
    require(warm['game_summaries'] == state['warm_games'] and warm['raw_tiles'] == state['warm_raw']
        and warm['memory_events'] == state['warm_events'] and warm['final_memory'] == state['warm_final'],
        'new complete warmup and all-raw learned memory inventory')
    require(Counter(warm['environment_counts']) == state['warm_environment']
        and Counter(warm['direct_counts']) == state['warm_direct']
        and Counter({k:v for k,v in warm['memory_counts'].items() if k != 'predict_calls'}) == state['warm_counts'],
        'warmup environment, DIRECT and memory physical work')
    require(acq['snapshot'] == state['snapshot'] and acq['training'] == state['training'],
        'new canonical acquisition summary changed')
    require(learned(ds['actor_memory_B_end']) == state['memory'].learned(), 'final actor memory includes all acquired raw')
    n = check_split(ds, state['games'], state['scores'], state['game_memories'], state['warm_raw'], state['training'])
    for key in ('environment_counts','direct_counts','memory_counts'):
        require(ds['costs']['warmup_'+key] == warm[key], 'paid warmup reconstruction/acquisition ledger')
    rec = acq['reconstruction']
    require(rec['counts'] == ds['costs']['processing_counts']
        and rec['memory_counts'] == ds['costs']['processing_memory_counts']
        and rec['chunks'] == ds['costs']['reconstructed_chunks'] == state['training_rows']
        and rec['cpu_seconds'] == ds['costs']['processing_cpu_seconds'], 'actual new reconstruction work and CPU')
    snapshot = life['evaluation_snapshot']; prefix = learned(ds['fit_memory'])
    module = prefix['modules'][prefix['active_module_id']]
    require(learned(snapshot['memory']) == prefix
        and snapshot['estimated_p_four'] == module['alpha']/(module['alpha']+module['beta']),
        'static shared observed fit-prefix belief excludes heldout and new evaluation feedback')
    games = ds['games']; fit_games = games[:n]; heldout_games = games[n:]
    score_rows = [state['scores'][game['episode']] for game in heldout_games]
    samples = sum(game['steps']-(game['status'] == 'WON') for game in fit_games)
    processed = {}; arms = {}; cutoffs = 0
    require(set(life['arms']) == set(ARMS), 'only frozen SOURCE, MC and LOCAL_RISK arms')
    for arm in ARMS:
        value = life['arms'][arm]; fit = value['fit']; setup = value['head_setup']
        count = 0 if arm == 'SOURCE' else samples
        require(value['processed_training_samples'] == value['sample_counter'] == fit['trained_afterstates'] == count
            and value['static_evaluation_valid'], 'same complete nonwinning fit inventory and static evaluation')
        processed[arm] = count
        if arm == 'SOURCE':
            require(fit['method'] == 'NONE' and not fit['learning_counts'] and not fit['target_counts']
                and not fit['consolidation_counts'] and setup['source_weights_shared']
                and setup['private_weight_bytes'] == 0, 'SOURCE receives no new updates or copies')
        elif arm == 'MC':
            check_normalized_fit(fit, fit_games, ds, state['scores'], 'EPISODE_MEAN_MC')
            require(not setup['source_weights_shared']
                and setup['private_weight_bytes'] == setup['setup_counts']['source_weight_bytes_copied'],
                'original SOURCE initialization and actual private MC copy')
        else:
            check_split_fit(fit, life['arms']['MC']['fit'], ds, arm)
            head = setup['setup_counts']; source_parameters = head['source_parameters_copied']
            require(not setup['source_weights_shared'] and head['initialized_zero_risk_parameters'] == source_parameters
                and head['allocated_weight_parameters'] == 2*source_parameters
                and head['source_weight_bytes_copied'] == 8*source_parameters
                and head['allocated_weight_bytes'] == setup['private_weight_bytes'] == 16*source_parameters,
                'frozen original reward prior and fully zero-initialized local risk logit head')
        if arm == 'LOCAL_RISK':
            heldout = check_split_heldout(value['heldout'], life['arms']['SOURCE']['heldout'], ds, arm)
            check_representation(value['evaluation_representation_counts'], arm,
                value['evaluation_counts']['planning'].get('value_predictions', 0))
        else:
            heldout = check_holdout(value['heldout'], heldout_games, score_rows, ds['fit_step_end'])
            require(not value['evaluation_representation_counts'] and not value['evaluation_setup_counts'],
                'SOURCE and original MC evaluate without extra risk features')
        arms[arm] = dict(check_evaluation(value['game_summaries'], lid, value['evaluation_counts']), heldout=heldout)
        cutoffs += arms[arm]['cutoffs']
    return dict(lifecycle=lid, parent=life['parent'], arms=arms), processed, cutoffs


def check_training_budget(accounting, inherited, lives):
    warm = sum(life['acquisition']['warmup']['raw_tiles'] for life in lives)
    actor = 64*RAW
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+actor
    require(accounting['new_training_environment_observations'] == warm+actor
        and accounting['physical_acquisitions'] == 64 and accounting['new_warmup_raw_tiles'] == warm
        and accounting['new_actor_B_raw_tiles'] == actor, 'all fresh B raw and warmup are paid once')
    for arm in ARMS:
        require(accounting['inherited_costs_per_arm'][arm] == inherited
            and accounting['economic_training_raw_tiles_per_arm'][arm] == economic,
            'economic input includes only original source, dynamics and all NEW B raw')
    require(accounting['excluded_tail_raw_tiles'] ==
        sum(life['dataset']['costs']['excluded_tail_raw_tiles'] for life in lives),
        'unfinished new actor tail remains paid')
    actual_actor = {kind:sum_counts(life['acquisition']['training']['counts'][kind] for life in lives)
        for kind in ('environment','planning','learning')}
    require(accounting['new_actor_B_counts'] == actual_actor, 'new frozen actor work totals')
    for field,name in (('new_warmup_environment_counts','environment_counts'),
            ('new_warmup_direct_counts','direct_counts'),('new_warmup_memory_counts','memory_counts')):
        require(accounting[field] == sum_counts(life['acquisition']['warmup'][name] for life in lives), 'actual '+field)
    require(accounting['new_actor_memory_counts'] == sum_counts(
        life['acquisition']['training']['memory_counts'] for life in lives), 'all new actor memory observations')
    environment = Counter(actual_actor['environment'])+Counter(accounting['new_warmup_environment_counts'])
    environment['raw_tile_productions'] = warm+actor
    require(Counter(accounting['new_training_environment_counts']) == environment, 'all physical acquisition environment costs')
    for field,name in (('reconstruction_counts','counts'),('reconstruction_memory_counts','memory_counts')):
        require(accounting[field] == sum_counts(life['acquisition']['reconstruction'][name] for life in lives), 'actual '+field)
    require(close(accounting['reconstruction_cpu_seconds'], sum(
        life['acquisition']['reconstruction']['cpu_seconds'] for life in lives)), 'actual reconstruction CPU')
    return economic


def check_accounting(document, old):
    accounting = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    original = old['accounting']['inherited_costs_per_arm']['SOURCE']
    inherited = {key:original[key] for key in ('source_training_raw_tiles','source_training_games',
        'source_training_environment_counts','source_training_seconds','dynamics_raw_tiles','dynamics_costs')}
    economic = check_training_budget(accounting, inherited, lives)
    require(close(accounting['acquisition_cpu_seconds'],sum(life['acquisition']['cpu_seconds'] for life in lives))
        and accounting['acquisition_native_setup_counts'] == sum_counts(
            life['acquisition']['native_setup_counts'] for life in lives)
        and close(accounting['acquisition_native_setup_seconds'],sum(
            life['acquisition']['native_setup_seconds'] for life in lives)), 'actual native acquisition setup and scoped CPU')
    fields = (('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_consolidation_counts','fit','consolidation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('fit_representation_counts','fit','representation_counts'),
        ('heldout_prediction_counts','heldout','prediction_counts'),('heldout_target_counts','heldout','target_counts'),
        ('heldout_representation_counts','heldout','representation_counts'),('heldout_setup_counts','heldout','setup_counts'))
    for arm in ARMS:
        require(accounting['processed_training_samples'][arm] == sum(
            life['arms'][arm]['processed_training_samples'] for life in lives), 'actual complete new fit samples')
        for field,stage,key in fields:
            values = [life['arms'][arm][stage].get(key,{}) for life in lives]
            require(accounting[field][arm] == sum_counts(nonpeak(row) for row in values), 'actual '+field)
            peaks = {key:max(row.get(key,0) for row in values)
                for key in {key for row in values for key in row if key.endswith('_peak')}}
            require(accounting[field+'_buffer_peaks'][arm] == peaks, 'actual '+field+' buffer peak')
        for stage in ('fit','heldout'):
            for field,key in (('processing_seconds_per_arm','seconds'),('processing_cpu_seconds_per_arm','cpu_seconds')):
                require(close(accounting[field][arm][stage],sum(life['arms'][arm][stage][key] for life in lives)),
                    'scoped actual '+stage+' processing time')
        require(accounting['private_head_weight_bytes_created'][arm] == sum(
            life['arms'][arm]['head_setup']['private_weight_bytes'] for life in lives), 'all private reward and risk buffers')
        require(accounting['head_setup_counts'][arm] == sum_counts(
            life['arms'][arm]['head_setup']['setup_counts'] for life in lives), 'actual private head initialization work')
        for field,key in (('processing_seconds_per_arm','setup_seconds'),('processing_cpu_seconds_per_arm','setup_cpu_seconds')):
            require(close(accounting[field][arm]['head_setup'],sum(life['arms'][arm]['head_setup'][key] for life in lives)),
                'actual head initialization time')
        for field,key in (('evaluation_cpu_seconds_per_arm','evaluation_cpu_seconds'),('evaluation_seconds_per_arm','evaluation_seconds')):
            require(close(accounting[field][arm],sum(life['arms'][arm][key] for life in lives)), 'actual '+field)
        for field,key in (('evaluation_representation_counts','evaluation_representation_counts'),
            ('evaluation_setup_counts','evaluation_setup_counts')):
            require(accounting[field][arm] == sum_counts(life['arms'][arm][key] for life in lives), 'actual '+field)
        for kind in ('environment','planning'):
            require(accounting['evaluation_counts_per_arm'][arm][kind] == sum_counts(
                life['arms'][arm]['evaluation_counts'][kind] for life in lives), 'per-arm new evaluation '+kind)
    for kind in ('environment','planning'):
        require(accounting['evaluation_counts'][kind] == sum_counts(
            life['arms'][arm]['evaluation_counts'][kind] for life in lives for arm in ARMS), 'all actual new evaluation work')
    require([parent['parent'] for parent in parents] == list(range(4)), 'four original SOURCE loads')
    for parent in parents:
        require(parent['lifecycle_ids'] == list(range(parent['parent'],64,4))
            and parent['source_setup']['checkpoint_loads'] == 1 and parent['source_setup']['new_leaf_updates'] == 0,
            'each original SOURCE loaded once and unchanged')
    for field,key in (('worker_cpu_seconds','cpu_seconds'),('compiler_cpu_seconds','compiler_cpu_seconds')):
        require(close(accounting[field],sum(parent[key] for parent in parents)), 'actual process CPU aggregate')
    require(accounting['canonical_trace_bytes'] == sum(parent['trace_bytes'] for parent in parents),
        'all fresh canonical retention storage')
    development = accounting['development_reference']
    require(development['method_selection'] == 'V301_PRESPECIFIED_LOCAL_SECONDARY_RESULT'
        and development['previous_B_acquisition_raw_tiles'] == old['accounting']['retained_B_acquisition_raw_tiles']
        and development['previous_evaluation_counts'] == old['accounting']['evaluation_counts'],
        'old target inputs and evaluations remain development costs rather than fresh inputs')
    return economic


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(settings == json_file(directory/'configuration.json'), 'frozen V302 configuration changed')
    require(document['schema'] == 'acfqp.local_risk.v302' and document['status'] == 'EXPERIMENT_COMPLETE'
        and document['scientific_gate'] == 'NOT_A_FORMAL_GATE', 'fresh confirmation result status')
    expected = dict(schema='acfqp.local_risk_freeze.v302',lifecycles=list(range(64)),parents=4,arms=list(ARMS),
        phase='B',true_p_four=.5,canonical_acquisition_arm='FROZEN',raw_budget=RAW,fit_fraction=.8,alpha=.0025,
        query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='NEW_INDEPENDENT_PURE_B_COHORT_WITHOUT_OLD_TARGET_INPUTS',
        representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_TERMINAL_NTUPLES',
        reward_initialization='ORIGINAL_SOURCE_UTILITY_TABLE',risk_initialization='ZERO_LOGITS',
        combination='REWARD_PLUS_8_TIMES_PROBABILITY_MINUS_HALF',
        reward_target='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS',
        risk_target='COMPLETE_FIT_GAME_WON_LABEL',
        consolidation='GAME_START_PREDICTIONS_THEN_PER_FEATURE_MASS_NORMALIZED_MEAN',
        model_probability='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION',
        seed_warmup=302100000000,seed_training=302200000000,seed_evaluation=EVALUATION_BASE,
        evaluation_games=32,max_steps=8192,bootstrap_draws=20000,bootstrap_seed=30200001,
        primary='LOCAL_RISK_minus_SOURCE_COMPLETE_GAME_UTILITY',interval_scope=INTERVAL_SCOPE,
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        stop_rule='NO_TUNING_OR_OLD_COHORT_POOLING; ADVANCE_TO_CONTINUAL_TRANSFER_IF_CONFIRMED')
    for key,value in expected.items():
        require(settings[key] == value, 'registered V302 '+key)
    old = json_file(settings['source_summary'])
    require(old['schema'] == 'acfqp.split_risk.v301'
        and json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid'],
        'audited V301 frozen local method selection')
    require(document['source_provenance'] == old['source_provenance'], 'four original inherited source and dynamics')
    for key in ('alpha','fit_fraction','query','combination','reward_target','risk_target',
            'consolidation','model_probability','evaluation','source_initialization','max_steps','evaluation_games'):
        require(settings[key] == old['settings'][key], 'unchanged selected V301 LOCAL method '+key)
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64))
        and all(life['parent'] == life['lifecycle']%4 for life in lives), 'all 64 new B training histories')
    canonical, rows_read = read_canonical(document)
    records = []; processed = Counter(); cutoffs = 0
    for life in lives:
        record, counts, censored = check_lifecycle(life, canonical[life['lifecycle']])
        records.append(record); processed.update(counts); cutoffs += censored
    summary = document['summary']; check_result_summary(summary, records, cutoffs)
    economic = check_accounting(document, old)
    return dict(status='PASS',independent_valid=True,lifecycles=64,fixed_source_parents=4,
        canonical_rows=rows_read,fresh_actor_raw_tiles=64*RAW,
        fresh_warmup_raw_tiles=document['accounting']['new_warmup_raw_tiles'],
        fit_games=sum(life['dataset']['fit_game_count'] for life in lives),
        heldout_games=sum(len(life['dataset']['games'])-life['dataset']['fit_game_count'] for life in lives),
        heldout_samples_per_arm=summary['arms']['SOURCE']['heldout']['samples'],
        processed_training_samples=dict(processed),excluded_tail_raw_tiles=document['accounting']['excluded_tail_raw_tiles'],
        evaluation_games=6144,evaluation_cutoffs=cutoffs,economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates',0) for arm in ARMS},
        independent_local_learning_confirmed=summary['independent_local_learning_confirmed'],
        primary_utility=summary['paired_contrasts']['LOCAL_RISK_minus_SOURCE'],
        contrasts={name:{key:value[key] for key in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for name,value in summary['paired_contrasts'].items()},
        method='Once-read new canonical warmup and every training raw/action/score receipt; independent observed '
            'Beta/router and fit-prefix reconstruction, fresh complete-game factual suffixes, original SOURCE and '
            'normalized MC inventory, unchanged local Bernoulli/reward game-start fit, heldout component identities, '
            'new paired terminal outcomes, signed equal-game/life endpoints, fresh input and actual work accounting.',
        limitations='No world sampling, source-weight replay, new fitting or bootstrap regeneration. Canonical producer '
            'reconstructs boards; audit checks new raw, scores, terminals and memory independently. Intervals are checked '
            'for fixed-parent scope and feasible range. Confirmation is conditional on four original source models; '
            'it establishes neither fresh-source, continual-retention nor cross-task transfer performance.',errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--input',type=Path,required=True)
    directory = parser.parse_args().input
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False)); raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
