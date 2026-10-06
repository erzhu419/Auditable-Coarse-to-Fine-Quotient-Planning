#!/usr/bin/env python3
"""Independent A1/B/A2 continual-head audit; no worlds or fit replay."""
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
from verify_stable_b_v298 import learned
from verify_split_risk_v301 import (
    COMPONENT_METRICS, check_representation, check_split_counts, check_split_heldout, nonpeak,
)

ARMS = ('SOURCE', 'MC', 'LOCAL_RISK')
STAGES = ('A1', 'B', 'A2')
TASKS = ('A', 'B')
RAW = 131072
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def check_local_fit(fit, mc, dataset, stage):
    kind = 'LOCAL_RISK'
    games = dataset['games'][:dataset['fit_game_count']]
    steps = sum(game['steps'] for game in games); wins = sum(game['status']=='WON' for game in games)
    samples = steps-wins
    require(fit['method']==kind and fit['alpha']==.0025 and fit['frozen_game_start_targets'],
        'fixed split-head learning rate and game-start predictions')
    require(fit['fitted_games']==len(games) and fit['fitted_steps']==dataset['fit_step_end']==steps
        and fit['trained_afterstates']==fit['reward_trained_afterstates']==fit['risk_trained_afterstates']==samples,
        'both split heads fit the same complete-game nonwinning samples')
    check_split_counts(fit,kind,len(games),steps,wins,samples)
    work = Counter(fit['learning_counts']); norm = Counter(fit['normalization_counts'])
    reward_writes = mc['learning_counts']['table_updates']
    risk_writes = reward_writes if kind=='LOCAL_RISK' else 20*len(games)-norm['global_zero_denominators']
    require(0<=norm['global_zero_denominators']<=19*len(games)
        and (kind=='GLOBAL_RISK' or norm['global_zero_denominators']==0), 'actual zero feature mass skips')
    expected = dict(td_updates=samples,value_predictions=samples,
        table_lookups=(64 if kind=='LOCAL_RISK' else 32)*samples,
        table_updates=reward_writes+risk_writes,table_update_occurrences=32*samples,
        reward_predictions=samples,risk_predictions=samples,reward_table_lookups=32*samples,
        risk_table_lookups=32*samples if kind=='LOCAL_RISK' else 0,
        reward_table_updates=reward_writes,risk_parameter_updates=risk_writes)
    require(work==Counter(expected), 'actual separate reward and risk sample lookups and parameter writes')
    mc_norm = mc['consolidation_counts']; products = mc_norm['sample_unique_addresses']
    known = dict(games_processed=len(games),feature_extractions=samples,feature_occurrences=32*samples,
        feature_digit_reads=192*samples,feature_address_multiply_adds=192*samples,
        sort_calls=len(games)+samples,sort_items=64*samples,
        denominator_occurrence_visits=32*samples,game_unique_addresses=reward_writes,
        reward_gradient_products=products,reward_gradient_accumulations=products,
        risk_gradient_products=products if kind=='LOCAL_RISK' else 20*samples,
        risk_gradient_accumulations=products if kind=='LOCAL_RISK' else 20*samples,
        global_denominator_accumulations=20*samples if kind=='GLOBAL_RISK' else 0,
        normalization_divisions=reward_writes+risk_writes,
        parameter_update_multiplications=reward_writes+risk_writes,
        game_parameter_commits=len(games),reward_game_commits=len(games),risk_game_commits=len(games),
        reward_parameter_writes=reward_writes,risk_parameter_writes=risk_writes,
        address_denominator_searches=products)
    require(all(norm[key]==value for key,value in known.items()),
        'actual game-start mass-normalized reward and risk gradient work')
    for key in ('first_sample','last_sample'):
        sample,previous = fit[key],mc[key]; game = games[previous['episode']]
        y = float(game['status']=='WON'); bonus = 4. if y else -4.
        require((sample['episode'],sample['step'])==(previous['episode'],previous['step'])
            and sample['risk_target']==y and sample['reward_target']==previous['raw_target']-bonus,
            'first and last targets exclude current reward and terminal bonus')
        p = sample['risk_probability']
        require(0.<=p<=1. and close(sample['risk_error'],y-p)
            and close(sample['reward_error'],sample['reward_target']-sample['reward_prediction'])
            and close(sample['combined_prediction'],sample['reward_prediction']+8.*(p-.5)),
            'first and last frozen head predictions and residuals')
    if stage == 'A1':
        require(fit['first_sample']['risk_probability']==.5
            and fit['first_sample']['reward_prediction']==mc['first_sample']['raw_prediction_before_update'],
            'A1 starts at original SOURCE with zero-logit risk')
    return samples




def warmup_seed(life, stage, game):
    return 303100000000+STAGES.index(stage)*100000+life*1000000+game


def training_seed(life, stage):
    return 303200000000+STAGES.index(stage)*100000+life*10000000


def evaluation_seed(life, task, episode):
    return 303900000000+(100000 if task == 'B' else 0)+life*1000000+episode


def check_stage_context(row):
    stage = row['phase']
    require(stage in STAGES and row['true_p_four'] == (.5 if stage == 'B' else .1),
        'registered A1/B/A2 actual environment context')


def check_acquisition_context(row):
    check_stage_context(row)
    require(row['arm'] == 'FROZEN', 'canonical acquisition uses original frozen SOURCE')
    require(row['start']['stream_seed'] == training_seed(row['lifecycle'],row['phase']),
        'fresh independent stage training stream')


def check_update_chain(value, arm, previous):
    fitted = value['fit']['trained_afterstates']
    expected = 0 if arm == 'SOURCE' else fitted
    require(value['head_updates_before'] == previous
        and value['head_updates_after'] == previous+expected,
        'head continuation preserves cumulative updates without reset or double fit')
    require(arm != 'SOURCE' or fitted == 0, 'SOURCE remains unfitted throughout all stages')
    return previous+expected


def check_warmup(row,index,memory):
    require(memory.obs<256,'warmup continued beyond the fixed raw threshold')
    game=row['summary'];raw=row['raw_spawns'];steps=game['steps']
    require(game['seed']==warmup_seed(row['lifecycle'],row['phase'],index),'new V303 complete stage warmup seed')
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
    check_stage_context(row)
    return memory.consume(r['rank'] for r in raw)



def read_canonical(document):
    """Read new 192 histories once and independently rebuild all observed beliefs."""
    result = {}; rows_read = 0
    for parent in document['parent_receipts']:
        pid = parent['parent']; ids = list(range(pid,64,4))
        require(parent['lifecycle_ids'] == ids, 'fresh source/lifecycle assignment')
        states = {(life,stage):dict(memory=Memory(),warm_games=[],warm_environment=Counter(),warm_direct=Counter(),
            warm_events=[],warm_rows=0,training_rows=0,training_events=[],train_counts={key:Counter()
                for key in ('environment','planning','learning')},last_stream=None,games=[],scores=defaultdict(list),
            game_memories={},snapshot=None) for life in ids for stage in STAGES}
        trace = Path(parent['trace_file'])
        require(trace.stat().st_size == parent['trace_bytes'], 'new canonical stage storage')
        with gzip.open(trace,'rt') as stream:
            for line in stream:
                row = json.loads(line); rows_read += 1; key = (row['lifecycle'],row['phase'])
                require(key in states and row['parent'] == pid, 'canonical life/source/stage membership')
                state = states[key]; memory = state['memory']; stage = key[1]
                if stage != 'A1':
                    require(states[(key[0],STAGES[STAGES.index(stage)-1])]['snapshot'] is not None,
                        'new stage began before previous stage acquisition completed')
                if row['kind'] == 'WARMUP':
                    require(state['last_stream'] is None, 'stage warmup occurred after training')
                    state['warm_events'].extend(check_warmup(row,state['warm_rows'],memory))
                    state['warm_rows'] += 1; state['warm_games'].append(row['summary'])
                    state['warm_environment'].update(row['counts']['environment'])
                    state['warm_direct'].update(row['counts']['direct'])
                    continue
                if row['kind'] == 'TRAIN':
                    if state['last_stream'] is None:
                        require(memory.obs >= 256, 'new stage lacks complete observed warmup')
                        state.update(warm_final=memory.learned(),warm_counts=memory.counts.copy(),warm_raw=memory.obs,
                            before_stream=row['start'])
                        require(row['start']['raw_tiles'] == row['start']['random_draw_position'] == 0,
                            'new stage acquired an old actor history')
                    else:
                        require(row['start'] == state['last_stream'], 'new stage stream continuity')
                    check_acquisition_context(row)
                    require(state['snapshot'] is None, 'actor continued after fixed stage raw boundary')
                    check_chunk(row,RAW-row['start']['raw_tiles'],memory)
                    completions = {game['end_raw']:game for game in row['completed_games']}
                    rewards = iter(row['scores']); events = []
                    for offset,spawn in enumerate(row['raw_spawns']):
                        if spawn['kind'] == 'POST_ACTION':
                            state['scores'][spawn['episode']].append(next(rewards))
                        events.extend(memory.consume([spawn['rank']]))
                        absolute = row['start']['raw_tiles']+offset+1
                        if absolute in completions:
                            game = completions[absolute]; state['game_memories'][game['episode']] = memory.learned()
                    require(events == row['memory_events'], 'new all-raw causal observed Beta/router events')
                    state['training_events'].extend(events); state['training_rows'] += 1
                    for kind in state['train_counts']:
                        state['train_counts'][kind].update(row['counts'][kind])
                    state['games'].extend(row['completed_games']); state['last_stream'] = row['end']
                    continue
                require(row['kind'] == 'ACQUISITION_SNAPSHOT' and state['snapshot'] is None,
                    'stage snapshot kind/inventory')
                require(state['last_stream'] is not None and state['last_stream']['raw_tiles'] == RAW,
                    'snapshot before paid fixed stage raw boundary')
                check_stage_context(row)
                require(row['arm'] == 'FROZEN', 'canonical snapshot uses original frozen SOURCE')
                snapshot = row['snapshot']; training = row['training']
                require(snapshot['stream'] == state['last_stream'] and snapshot['memory'] == memory.learned()
                    and snapshot['estimated_p_four'] == memory.probability() and snapshot['new_value_updates'] == 0,
                    'new frozen acquisition stream/memory/parameters')
                require(training['raw_tiles'] == RAW and training['chunks'] == state['training_rows']
                    and training['memory_event_count'] == len(state['training_events'])
                    and training['before_stream'] == state['before_stream'] and training['after_stream'] == state['last_stream'],
                    'new paid raw/chunk/event boundary')
                require(all(Counter(training['counts'][kind]) == counts for kind,counts in state['train_counts'].items()),
                    'stage actor environment/planning/value totals')
                require(Counter({k:v for k,v in training['memory_counts'].items() if k != 'predict_calls'})
                    == memory.counts-state['warm_counts'], 'stage all-raw observed memory work')
                state['snapshot'] = snapshot; state['training'] = training
        for key,state in states.items():
            require(state['snapshot'] is not None and state['memory'].obs == state['warm_raw']+RAW,
                'complete fresh stage history includes every initial/post-action tile')
            result[key] = state
    require(set(result) == {(life,stage) for life in range(64) for stage in STAGES}, 'all 192 fresh stage histories')
    return result,rows_read


def check_stage_split(dataset,games,scores,fit_memories,warm_raw,training,stage):
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
    expected=dict(fit_raw_tiles=fit_raw,heldout_raw_tiles=complete_raw-fit_raw,
        fit_steps=fit_steps,heldout_steps=all_steps-fit_steps,excluded_tail_games=int(complete_raw<RAW),
        excluded_tail_raw_tiles=RAW-complete_raw,
        excluded_tail_steps=training['after_stream']['post_action_spawns']-all_steps,warmup_raw_tiles=warm_raw)
    expected['full_'+stage+'_raw_tiles'] = RAW
    require(all(dataset['costs'][key]==value for key,value in expected.items()),'paid full acquisition/excluded tail ledger')
    require(dataset['costs']['full_'+stage+'_acquisition_counts']==training['counts'],'new acquisition work omitted/reweighted')
    return n


def check_acquisition(row, state, stage):
    ds = row['dataset']; acq = row['acquisition']; warm = acq['warmup']
    require(acq['new_value_updates'] == 0 and acq['physical_acquisitions'] == 1
        and acq['new_evaluation_games'] == 0, 'each stage SOURCE actor has no learned-head/evaluation feedback')
    require(warm['game_summaries'] == state['warm_games'] and warm['raw_tiles'] == state['warm_raw']
        and warm['memory_events'] == state['warm_events'] and warm['final_memory'] == state['warm_final'],
        'new stage complete warmup and observed memory inventory')
    require(Counter(warm['environment_counts']) == state['warm_environment']
        and Counter(warm['direct_counts']) == state['warm_direct']
        and Counter({k:v for k,v in warm['memory_counts'].items() if k != 'predict_calls'}) == state['warm_counts'],
        'new warmup physical costs')
    require(acq['snapshot'] == state['snapshot'] and acq['training'] == state['training'],
        'new canonical stage acquisition summary')
    require(learned(ds['actor_memory_'+stage+'_end']) == state['memory'].learned(), 'actual all-raw stage final actor memory')
    n = check_stage_split(ds,state['games'],state['scores'],state['game_memories'],state['warm_raw'],state['training'],stage)
    for name in ('environment_counts','direct_counts','memory_counts'):
        require(ds['costs']['warmup_'+name] == warm[name], 'paid stage warmup reconstruction ledger')
    rec = acq['reconstruction']
    require(rec['counts'] == ds['costs']['processing_counts']
        and rec['memory_counts'] == ds['costs']['processing_memory_counts']
        and rec['chunks'] == ds['costs']['reconstructed_chunks'] == state['training_rows']
        and rec['cpu_seconds'] == ds['costs']['processing_cpu_seconds'], 'new reconstruction work and CPU')
    return n


def check_evaluation(evaluation, life, task, belief):
    games = evaluation['game_summaries']; counts = evaluation['counts']
    require(evaluation['estimated_p_four'] == belief['estimated_p_four'] and evaluation['static_evaluation_valid'],
        'fixed first-task observed belief and frozen evaluation')
    require(len(games) == 32 and [game['seed'] for game in games]
        == [evaluation_seed(life,task,episode) for episode in range(32)],
        'paired task evaluation seeds remain identical across checkpoints')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'new task evaluation horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and max(game['final_board']) < 11, 'premature cutoff or goal at cutoff')
            bonus = 0.
        else:
            terminal(game['final_board'],game['status']); bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'new complete-game task utility')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    expected = dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=64,
        raw_tile_productions=steps+64,environment_random_draws=2*(steps+64),ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32,ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment']) == Counter(expected), 'actual evaluation includes initial/winning spawns')
    planning_counts(counts['planning'],steps)
    return dict(games=32,mean_game_utility=mean(game['utility'] for game in games),wins=wins,
        losses=sum(game['status'] == 'LOST' for game in games),cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        cutoff_episodes=[episode for episode,game in enumerate(games) if game['status'] == 'CUTOFF'],steps=steps)


def check_head_setup(setup):
    require(set(setup) == set(ARMS), 'once/lifecycle private-head inventory')
    source = setup['SOURCE']; mc = setup['MC']; local = setup['LOCAL_RISK']
    require(source['source_weights_shared'] and source['private_weight_bytes'] == 0
        and not source['setup_counts'], 'SOURCE reuses original frozen shared weights')
    require(not mc['source_weights_shared']
        and mc['private_weight_bytes'] == mc['setup_counts']['source_weight_bytes_copied'],
        'MC initializes once from original SOURCE')
    head = local['setup_counts']; size = head['source_parameters_copied']
    require(not local['source_weights_shared'] and head['initialized_zero_risk_parameters'] == size
        and head['allocated_weight_parameters'] == 2*size and head['source_weight_bytes_copied'] == 8*size
        and head['allocated_weight_bytes'] == local['private_weight_bytes'] == 16*size,
        'LOCAL reward prior and zero risk logits are created exactly once per lifecycle')


def check_belief(belief, data):
    prefix = learned(data['fit_memory']); module = prefix['modules'][prefix['active_module_id']]
    require(learned(belief['memory']) == prefix
        and belief['estimated_p_four'] == module['alpha']/(module['alpha']+module['beta']),
        'first-task complete FIT-prefix belief excludes heldout/future tasks and true task probability')


def check_lifecycle(life, canonical):
    lid = life['lifecycle']; stages = life['stages']; beliefs = life['evaluation_beliefs']
    require(set(stages) == set(STAGES) and set(beliefs) == set(TASKS), 'complete three-stage/task receipt inventory')
    check_head_setup(life['head_setup'])
    check_belief(beliefs['A'],stages['A1']['dataset']); check_belief(beliefs['B'],stages['B']['dataset'])
    updates = dict.fromkeys(ARMS,0); processed = Counter(); cutoffs = 0; cells = {}; source_evaluations = {}
    for stage in STAGES:
        row = stages[stage]; ds = row['dataset']; state = canonical[(lid,stage)]
        require(row['task'] == ('B' if stage == 'B' else 'A'), 'stage training task')
        check_belief(row['fit_snapshot'],ds)
        n = check_acquisition(row,state,stage); games = ds['games']; fit_games = games[:n]; heldout_games = games[n:]
        scores = [state['scores'][game['episode']] for game in heldout_games]
        samples = sum(game['steps']-(game['status'] == 'WON') for game in fit_games)
        require(set(row['arms']) == set(ARMS), 'same three heads throughout the continual sequence')
        tasks = ('A',) if stage == 'A1' else TASKS
        for task in tasks:
            cells[stage+'_'+task] = dict(arms={})
        for arm in ARMS:
            value = row['arms'][arm]; fit = value['fit']
            require(value['parameters_retained'] and value['processed_training_samples'] == fit['trained_afterstates']
                and fit['trained_afterstates'] == (0 if arm == 'SOURCE' else samples),
                'both continuing learners fit all and only stage nonwinning samples')
            updates[arm] = check_update_chain(value,arm,updates[arm]); processed[arm] += fit['trained_afterstates']
            if arm == 'SOURCE':
                require(fit['method'] == 'NONE' and not fit['learning_counts'] and not fit['target_counts']
                    and not fit['consolidation_counts'], 'SOURCE receives no updates in any stage')
            elif arm == 'MC':
                check_normalized_fit(fit,fit_games,ds,state['scores'],'EPISODE_MEAN_MC')
            else:
                check_local_fit(fit,row['arms']['MC']['fit'],ds,stage)
            if arm == 'LOCAL_RISK':
                check_split_heldout(value['heldout'],row['arms']['SOURCE']['heldout'],ds,arm)
            else:
                check_holdout(value['heldout'],heldout_games,scores,ds['fit_step_end'])
            require(set(value['evaluations']) == set(tasks), 'all registered task checkpoint evaluations')
            for task in tasks:
                evaluation = value['evaluations'][task]
                game_row = check_evaluation(evaluation,lid,task,beliefs[task])
                if arm == 'LOCAL_RISK':
                    check_representation(evaluation['representation_counts'],arm,
                        evaluation['counts']['planning'].get('value_predictions',0))
                else:
                    require(not evaluation['representation_counts'] and not evaluation['setup_counts'],
                        'SOURCE/MC evaluate without extra risk representation')
                if arm == 'SOURCE':
                    identity = dict(game_summaries=evaluation['game_summaries'],counts=evaluation['counts'])
                    if task in source_evaluations:
                        equal_tree(identity,source_evaluations[task], 'SOURCE has exact same task behavior across checkpoints')
                    else:
                        source_evaluations[task] = identity
                cells[stage+'_'+task]['arms'][arm] = game_row; cutoffs += game_row['cutoffs']
    return dict(lifecycle=lid,parent=life['parent'],cells=cells),processed,cutoffs


def check_contrast(saved, values, direction='higher_is_better'):
    require(len(values) == 64 and close(saved['mean'],mean(values)), 'signed paired whole-life mean')
    equal_tree(saved['lifecycle_deltas'],{str(i):value for i,value in enumerate(values)}, 'all signed lifecycle deltas')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'],{str(parent):mean(group) for parent,group in enumerate(groups)},
        'four fixed sixteen-sequence parent means')
    low,high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE
        and mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'conditional whole-sequence interval scope and possible range')
    losses = [-value for value in values] if direction == 'higher_is_better' else values
    require(saved['improved_equal_worse'] == [sum(v < 0 for v in losses),sum(v == 0 for v in losses),sum(v > 0 for v in losses)]
        and saved['adverse_lifecycles'] == [i for i,v in enumerate(losses) if v > 0],
        'signed adverse continual histories are retained')


def endpoint(records, cell, arm):
    return [row['cells'][cell]['arms'][arm]['mean_game_utility'] for row in records]


def check_result_summary(summary, records, cutoffs):
    equal_tree(summary['by_lifecycle'],records,'all new task checkpoint game means')
    require(summary['primary_contrast'] == 'LOCAL_RISK_minus_SOURCE_FINAL_AB'
        and summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 30300001
        and summary['complete_game_endpoints'] == (cutoffs == 0), 'frozen final two-task primary and complete endpoints')
    pairs = (('LOCAL_RISK','SOURCE'),('MC','SOURCE'),('LOCAL_RISK','MC'))
    expected_cells = ('A1_A','B_A','B_B','A2_A','A2_B')
    require(set(summary['cells']) == set(expected_cells), 'complete registered checkpoint/task cell summary')
    for cell in expected_cells:
        saved = summary['cells'][cell]; stage,task = cell.split('_')
        require(saved['stage'] == stage and saved['task'] == task, 'checkpoint/task summary identity')
        for arm in ARMS:
            values = [row['cells'][cell]['arms'][arm] for row in records]
            expected = dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
                **{key:sum(value[key] for value in values) for key in ('games','wins','losses','cutoffs','steps')})
            equal_tree(saved['arms'][arm],expected,'equal game then lifecycle task summary '+cell+' '+arm)
        for left,right in pairs:
            values = [a-b for a,b in zip(endpoint(records,cell,left),endpoint(records,cell,right))]
            check_contrast(saved['paired_contrasts'][left+'_minus_'+right],values)
    for left,right in pairs:
        final = []; sequence = []
        for row in records:
            differences = {cell:row['cells'][cell]['arms'][left]['mean_game_utility']
                -row['cells'][cell]['arms'][right]['mean_game_utility'] for cell in expected_cells}
            final.append((differences['A2_A']+differences['A2_B'])/2)
            sequence.append(mean(differences[cell] for cell in ('A1_A','B_B','A2_A')))
        name = left+'_minus_'+right
        check_contrast(summary['final_ab_contrasts'][name],final)
        check_contrast(summary['current_task_sequence_contrasts'][name],sequence)
    checkpoints = dict(A_after_B=('B_A','A1_A'),B_after_A2=('A2_B','B_B'),
        A_restore_after_A2=('A2_A','B_A'),A_final_vs_A1=('A2_A','A1_A'))
    require(set(summary['checkpoint_contrasts']) == set(checkpoints), 'all forgetting and restoration contrasts')
    for name,(after,before) in checkpoints.items():
        for arm in ARMS:
            values = [a-b for a,b in zip(endpoint(records,after,arm),endpoint(records,before,arm))]
            check_contrast(summary['checkpoint_contrasts'][name][arm],values)
    supported = cutoffs == 0 and summary['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95'][0] > 0
    require(summary['primary_sequence_gain_supported'] == supported
        and summary['primary_sequence_gain_status'] == ('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE
        and summary['estimator'] == 'EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        'primary support uses final whole-game equal-task gain over SOURCE')
    final_tasks = {task:cutoffs == 0
        and summary['cells']['A2_'+task]['paired_contrasts']['LOCAL_RISK_minus_SOURCE']['ci95'][0] > 0
        for task in TASKS}
    require(summary['final_task_gain_supported'] == final_tasks
        and summary['final_dual_task_gain_supported'] == all(final_tasks.values()),
        'final individual task gains are distinct from final average')
    retention = {}
    for name in ('A_after_B','B_after_A2','A_final_vs_A1'):
        low,high = summary['checkpoint_contrasts'][name]['LOCAL_RISK']['ci95']
        retention[name] = ('INCOMPLETE_GAME_ENDPOINTS' if cutoffs else 'SUPPORTED_NONDECREASE' if low >= 0.
            else 'SUPPORTED_LOSS' if high < 0. else 'UNRESOLVED')
    require(summary['retention_status'] == retention and summary['retained_gain_supported']
        == all(status == 'SUPPORTED_NONDECREASE' for status in retention.values()),
        'zero-crossing intervals do not establish preservation')
    require(summary['a_restoration_supported'] == (cutoffs == 0
        and summary['checkpoint_contrasts']['A_restore_after_A2']['LOCAL_RISK']['ci95'][0] > 0),
        'positive recovery is separate from capability preservation')


def flat_stages(lives):
    return [life['stages'][stage] for life in lives for stage in STAGES]


def check_training_budget(account, inherited, lives):
    rows = flat_stages(lives)
    warm = sum(row['acquisition']['warmup']['raw_tiles'] for row in rows); actor = 192*RAW
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+actor
    require(account['physical_acquisitions'] == 192 and account['new_actor_raw_tiles'] == actor
        and account['new_warmup_raw_tiles'] == warm and account['new_training_environment_observations'] == warm+actor,
        'all three fresh carriers and complete warmups are paid once')
    expected = {stage:sum(life['stages'][stage]['acquisition']['warmup']['raw_tiles']+RAW for life in lives)
        for stage in STAGES}
    require(account['new_raw_tiles_by_stage'] == expected, 'actual per-stage warmup and actor budget')
    for arm in ARMS:
        require(account['inherited_costs_per_arm'][arm] == inherited
            and account['economic_training_raw_tiles_per_arm'][arm] == economic,
            'original SOURCE/dynamics charged once and all fresh stages charged to each arm')
    require(account['excluded_tail_raw_tiles'] == sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in rows),
        'every unfinished stage tail remains paid')
    return economic


def check_accounting(document, old):
    account = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    rows = flat_stages(lives); original = old['accounting']['inherited_costs_per_arm']['SOURCE']
    inherited = {key:original[key] for key in ('source_training_raw_tiles','source_training_games',
        'source_training_environment_counts','source_training_seconds','dynamics_raw_tiles','dynamics_costs')}
    economic = check_training_budget(account,inherited,lives)
    actual = {kind:sum_counts(row['acquisition']['training']['counts'][kind] for row in rows)
        for kind in ('environment','planning','learning')}
    require(account['new_actor_counts'] == actual, 'actual three-stage frozen actor work')
    for field,name in (('new_warmup_environment_counts','environment_counts'),('new_warmup_direct_counts','direct_counts'),
            ('new_warmup_memory_counts','memory_counts')):
        require(account[field] == sum_counts(row['acquisition']['warmup'][name] for row in rows), 'actual '+field)
    require(account['new_actor_memory_counts'] == sum_counts(row['acquisition']['training']['memory_counts'] for row in rows),
        'all fresh three-stage observed memory work')
    environment = Counter(actual['environment'])+Counter(account['new_warmup_environment_counts'])
    environment['raw_tile_productions'] = account['new_training_environment_observations']
    require(Counter(account['new_training_environment_counts']) == environment, 'all initial/post-action training costs')
    for field,name in (('reconstruction_counts','counts'),('reconstruction_memory_counts','memory_counts')):
        require(account[field] == sum_counts(row['acquisition']['reconstruction'][name] for row in rows), 'actual '+field)
    require(close(account['reconstruction_cpu_seconds'],sum(row['acquisition']['reconstruction']['cpu_seconds'] for row in rows)),
        'actual three-stage reconstruction CPU')
    require(close(account['acquisition_cpu_seconds'],sum(row['acquisition']['cpu_seconds'] for row in rows))
        and account['acquisition_native_setup_counts'] == sum_counts(row['acquisition']['native_setup_counts'] for row in rows)
        and close(account['acquisition_native_setup_seconds'],sum(row['acquisition']['native_setup_seconds'] for row in rows)),
        'actual acquisition setup and scoped CPU')
    fields = (('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_consolidation_counts','fit','consolidation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('fit_representation_counts','fit','representation_counts'),
        ('heldout_prediction_counts','heldout','prediction_counts'),('heldout_target_counts','heldout','target_counts'),
        ('heldout_representation_counts','heldout','representation_counts'),('heldout_setup_counts','heldout','setup_counts'))
    for arm in ARMS:
        samples = sum(row['arms'][arm]['processed_training_samples'] for row in rows)
        require(account['processed_training_samples'][arm] == account['final_cumulative_updates'][arm] == samples
            == sum(life['stages']['A2']['arms'][arm]['head_updates_after'] for life in lives),
            'summed stage fit samples equal retained final cumulative head updates')
        for field,stage,key in fields:
            values = [row['arms'][arm][stage].get(key,{}) for row in rows]
            require(account[field][arm] == sum_counts(nonpeak(value) for value in values), 'actual '+field)
            peaks = {key:max(value.get(key,0) for value in values)
                for key in {key for value in values for key in value if key.endswith('_peak')}}
            require(account[field+'_buffer_peaks'][arm] == peaks, 'actual '+field+' buffer peaks')
        for stage in ('fit','heldout'):
            for field,key in (('processing_seconds_per_arm','seconds'),('processing_cpu_seconds_per_arm','cpu_seconds')):
                require(close(account[field][arm][stage],sum(row['arms'][arm][stage][key] for row in rows)),
                    'actual '+stage+' processing time')
        require(account['private_head_weight_bytes_created'][arm]
            == sum(life['head_setup'][arm]['private_weight_bytes'] for life in lives)
            and account['head_setup_counts'][arm] == sum_counts(life['head_setup'][arm]['setup_counts'] for life in lives),
            'persistent private heads allocated once rather than once per stage')
        for field,key in (('processing_seconds_per_arm','setup_seconds'),('processing_cpu_seconds_per_arm','setup_cpu_seconds')):
            require(close(account[field][arm]['head_setup'],sum(life['head_setup'][arm][key] for life in lives)),
                'actual once-per-life head initialization CPU/time')
        evaluations = [value for row in rows for value in row['arms'][arm]['evaluations'].values()]
        for field,key in (('evaluation_cpu_seconds_per_arm','cpu_seconds'),('evaluation_seconds_per_arm','seconds')):
            require(close(account[field][arm],sum(value[key] for value in evaluations)), 'actual '+field)
        for field,key in (('evaluation_representation_counts','representation_counts'),('evaluation_setup_counts','setup_counts')):
            require(account[field][arm] == sum_counts(value[key] for value in evaluations), 'actual '+field)
        for kind in ('environment','planning'):
            require(account['evaluation_counts_per_arm'][arm][kind] == sum_counts(value['counts'][kind] for value in evaluations),
                'actual per-arm five-checkpoint '+kind)
    for kind in ('environment','planning'):
        require(account['evaluation_counts'][kind] == sum_counts(value['counts'][kind]
            for row in rows for arm in ARMS for value in row['arms'][arm]['evaluations'].values()),
            'all physical checkpoint evaluations counted rather than only distinct seed conditions')
    require([parent['parent'] for parent in parents] == list(range(4)), 'four original SOURCE loads')
    for parent in parents:
        require(parent['lifecycle_ids'] == list(range(parent['parent'],64,4))
            and parent['source_setup']['checkpoint_loads'] == 1 and parent['source_setup']['new_leaf_updates'] == 0,
            'each original SOURCE loaded once and unchanged')
    for field,key in (('worker_cpu_seconds','cpu_seconds'),('compiler_cpu_seconds','compiler_cpu_seconds')):
        require(close(account[field],sum(parent[key] for parent in parents)), 'actual process CPU aggregate')
    require(account['canonical_trace_bytes'] == sum(parent['trace_bytes'] for parent in parents), 'all new canonical storage')
    development = account['development_reference']
    require(development['previous_experiment'] == 'V302'
        and development['previous_target_raw_tiles'] == old['accounting']['new_training_environment_observations']
        and development['previous_evaluation_counts'] == old['accounting']['evaluation_counts'],
        'old confirmation inputs/evaluations remain development costs rather than new sequence inputs')
    return economic


def check_heldout_summary(summary, lives):
    require(set(summary['heldout_by_stage']) == set(STAGES), 'complete three-stage heldout diagnostics')
    for stage in STAGES:
        for arm in ARMS:
            rows = [life['stages'][stage]['arms'][arm]['heldout'] for life in lives]
            metrics = [row['game_metrics'] for row in rows]
            expected = dict(games=sum(len(values) for values in metrics),
                samples=sum(game['count'] for values in metrics for game in values),
                **{key:mean(mean(game[key] for game in values) for values in metrics) for key in ('bias','mse','mae')})
            if arm == 'LOCAL_RISK':
                expected['components'] = {key:mean(mean(game[key] for game in row['component_game_metrics']) for row in rows)
                    for key in COMPONENT_METRICS}
            equal_tree(summary['heldout_by_stage'][stage][arm],expected, 'same equal-game/life stage heldout '+stage+' '+arm)
    for arm in ARMS:
        cells = [row['cells'][cell]['arms'][arm] for row in summary['by_lifecycle'] for cell in summary['cells']]
        expected = {key:sum(row[key] for row in cells) for key in ('games','wins','losses','cutoffs','steps')}
        expected['mean_final_ab_game_utility'] = mean(mean(row['cells'][cell]['arms'][arm]['mean_game_utility']
            for cell in ('A2_A','A2_B')) for row in summary['by_lifecycle'])
        expected['mean_current_task_sequence_game_utility'] = mean(mean(row['cells'][cell]['arms'][arm]['mean_game_utility']
            for cell in ('A1_A','B_B','A2_A')) for row in summary['by_lifecycle'])
        equal_tree(summary['arms'][arm],expected, 'overall physical checkpoint games and declared endpoint means')


def check_old_logged_events(document, events):
    lives = {life['lifecycle']:life for life in document['by_lifecycle']}; seen = set()
    counts = {kind:Counter() for kind in ('environment','planning')}
    for event in events:
        key = (event['lifecycle'],event['stage'],event['arm'])
        require(key not in seen, 'one preserved original logged arm receipt per checkpoint')
        seen.add(key); value = lives[key[0]]['stages'][key[1]]['arms'][key[2]]
        expected = dict(event='continual_arm_complete',lifecycle=key[0],stage=key[1],arm=key[2],
            updates_before=value['head_updates_before'],updates_after=value['head_updates_after'],
            utilities={task:sum(game['utility'] for game in evaluation['game_summaries'])/32
                for task,evaluation in value['evaluations'].items()})
        require(event == expected, 'every preserved original utility/update receipt reproduced exactly')
        for evaluation in value['evaluations'].values():
            for kind in counts:
                counts[kind].update(evaluation['counts'][kind])
    recovery = document['recovery']
    require(len(events) == recovery['original_completed_arm_receipts'] == recovery['regenerated_logged_arm_receipts'],
        'all interrupted logged endpoints remain present without statistical pooling')
    require(all(Counter(recovery['interrupted_logged_evaluation_counts'][kind]) == value
        for kind,value in counts.items()), 'original completed evaluation work is separately reconstructed and paid')


def check_recovery_cost_scope(recovery, account):
    require(recovery['status'] == 'RECOVERED_SAME_FROZEN_COHORT' and recovery['original_exit_code'] == 143
        and recovery['historical_total_compute_closed'] is False,
        'interrupted unretained compute stays unknown rather than falsely closed')
    actual = recovery['interrupted_retained_raw_tiles']+recovery['current_new_acquisition_raw_tiles']
    extra = recovery['additional_retained_incomplete_prefix_raw_tiles']
    require(recovery['training_raw_tiles_physical_lower_bound'] == actual
        == account['new_training_environment_observations']+extra,
        'all retained interrupted prefixes are extra paid physical work')
    require(recovery['economic_training_raw_tiles_lower_bound_per_arm']
        == {arm:account['economic_training_raw_tiles_per_arm'][arm]+extra for arm in ARMS},
        'economic lower bounds include interrupted discarded prefixes for every arm')


def check_recovery(document, directory):
    recovery = document['recovery']; check_recovery_cost_scope(recovery,document['accounting'])
    events = [json.loads(line) for line in (directory/'interrupted'/'stdout.log').read_text().splitlines()]
    check_old_logged_events(document,events)
    lives = {life['lifecycle']:life for life in document['by_lifecycle']}
    ledgers = [parent['recovery'] for parent in document['parent_receipts']]
    stages = [row for ledger in ledgers for row in ledger['reused_complete_stages']]
    pairs = [(row['lifecycle'],row['stage']) for row in stages]
    require(len(set(pairs)) == len(pairs) == recovery['reused_complete_acquisition_stages'],
        'each interrupted completed stage enters the frozen cohort once')
    reused_raw = 0; training_cpu = 0.; environment = Counter()
    for row in stages:
        require(row['lifecycle'] in lives and row['stage'] in STAGES, 'reused frozen lifecycle/stage membership')
        acquisition = lives[row['lifecycle']]['stages'][row['stage']]['acquisition']
        raw = acquisition['warmup']['raw_tiles']+acquisition['training']['raw_tiles']
        require(row['raw_tiles'] == raw and close(row['retained_training_loop_cpu_seconds'],acquisition['training']['cpu_seconds'])
            and not acquisition['native_setup_counts'] and acquisition['native_setup_seconds'] == 0.
            and close(acquisition['cpu_seconds'],acquisition['reconstruction']['cpu_seconds']),
            'complete original stages reused without a new actor setup and current CPU is reconstruction only')
        reused_raw += raw; training_cpu += row['retained_training_loop_cpu_seconds']
        environment.update(acquisition['warmup']['environment_counts']); environment.update(acquisition['training']['counts']['environment'])
    require(reused_raw+recovery['current_new_acquisition_raw_tiles']
        == document['accounting']['new_training_environment_observations']
        and recovery['interrupted_retained_raw_tiles'] == reused_raw+recovery['additional_retained_incomplete_prefix_raw_tiles'],
        'reused complete raw plus new raw exactly supplies the original frozen input cohort')
    require(close(recovery['retained_original_training_loop_cpu_seconds'],training_cpu),
        'original serialized training-loop CPU is separate from current worker CPU')
    retained_environment = Counter(recovery['interrupted_retained_environment_counts'])
    require(all(retained_environment[key] >= value for key,value in environment.items()),
        'interrupted retained environment includes every reused complete carrier')
    for field,key in (('interrupted_retained_raw_tiles',None),('current_new_acquisition_raw_tiles','new_acquisition_raw_tiles'),
            ('additional_retained_incomplete_prefix_raw_tiles','discarded_incomplete_prefix_raw_tiles')):
        values = [ledger['retained_actor_raw_tiles']+ledger['retained_warmup_raw_tiles']
            if key is None else ledger[key] for ledger in ledgers]
        require(recovery[field] == sum(values), 'original parent recovery ledger '+field)
    require(recovery['interrupted_retained_environment_counts'] == sum_counts(ledger['retained_environment_counts'] for ledger in ledgers)
        and close(recovery['retained_original_native_actor_cpu_seconds'],sum(ledger['retained_actor_native_cpu_seconds'] for ledger in ledgers)),
        'separate original canonical actor work and native CPU lower bounds')


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(settings == json_file(directory/'configuration.json'), 'frozen V303 configuration changed')
    require(document['schema'] == 'acfqp.continual.v303' and document['status'] == 'EXPERIMENT_COMPLETE'
        and document['scientific_gate'] == 'NOT_A_FORMAL_GATE', 'completed continual experiment status')
    expected = dict(schema='acfqp.continual_freeze.v303',lifecycles=list(range(64)),parents=4,arms=list(ARMS),
        stages=list(STAGES),tasks=dict(A1='A',B='B',A2='A'),true_probabilities=dict(A=.1,B=.5),
        canonical_acquisition_arm='FROZEN',source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='THREE_NEW_SOURCE_CARRIER_COHORTS_WITH_RETAINED_LEARNER_PARAMETERS',
        raw_budget_per_stage=RAW,fit_fraction=.8,alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_TERMINAL_NTUPLES',
        reward_initialization='ORIGINAL_SOURCE_UTILITY_TABLE_ONCE',risk_initialization='ZERO_LOGITS_ONCE',
        combination='REWARD_PLUS_8_TIMES_PROBABILITY_MINUS_HALF',
        reward_target='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS',
        risk_target='COMPLETE_FIT_GAME_WON_LABEL',
        consolidation='GAME_START_PREDICTIONS_THEN_PER_FEATURE_MASS_NORMALIZED_MEAN',
        model_probability='FIRST_ENCOUNTER_OBSERVED_FIT_PREFIX_FIXED_BY_TASK',
        seed_warmup={stage:warmup_seed(0,stage,0) for stage in STAGES},
        seed_training={stage:training_seed(0,stage) for stage in STAGES},seed_evaluation=303900000000,
        evaluation_task_offset=100000,evaluation_games_per_cell=32,evaluation_cells=['A1_A','B_A','B_B','A2_A','A2_B'],
        max_steps=8192,bootstrap_draws=20000,bootstrap_seed=30300001,
        primary='LOCAL_RISK_minus_SOURCE_FINAL_AB_COMPLETE_GAME_UTILITY',interval_scope=INTERVAL_SCOPE,
        evaluation='STATIC_TASK_BELIEF_AND_PAIRED_TASK_SEEDS_ACROSS_CHECKPOINTS',
        stop_rule='RETAIN_ALL_NEGATIVE_RETENTION_RESULTS_WITHOUT_SEQUENCE_TUNING')
    for key,value in expected.items():
        require(settings[key] == value, 'registered V303 '+key)
    old = json_file(settings['source_summary'])
    require(old['schema'] == 'acfqp.local_risk.v302' and old['summary']['independent_local_learning_confirmed']
        and json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid'],
        'audited V302 independent local confirmation precedes this continual test')
    require(document['source_provenance'] == old['source_provenance'], 'four original inherited source models/dynamics')
    for key in ('alpha','fit_fraction','query','combination','reward_target','risk_target','consolidation',
            'source_initialization','representation','max_steps'):
        require(settings[key] == old['settings'][key], 'unchanged confirmed local method '+key)
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64))
        and all(life['parent'] == life['lifecycle']%4 for life in lives), 'all 64 fresh continuous head histories')
    canonical,rows_read = read_canonical(document); records = []; processed = Counter(); cutoffs = 0
    for life in lives:
        record,counts,censored = check_lifecycle(life,canonical)
        records.append(record); processed.update(counts); cutoffs += censored
    summary = document['summary']; check_result_summary(summary,records,cutoffs); check_heldout_summary(summary,lives)
    economic = check_accounting(document,old); check_recovery(document,directory)
    return dict(status='PASS',independent_valid=True,lifecycles=64,fixed_source_parents=4,
        fresh_stage_histories=192,canonical_rows=rows_read,fresh_actor_raw_tiles=192*RAW,
        fresh_warmup_raw_tiles=document['accounting']['new_warmup_raw_tiles'],
        fit_games=sum(row['dataset']['fit_game_count'] for row in flat_stages(lives)),
        heldout_games=sum(len(row['dataset']['games'])-row['dataset']['fit_game_count'] for row in flat_stages(lives)),
        processed_training_samples=dict(processed),final_cumulative_updates=document['accounting']['final_cumulative_updates'],
        excluded_tail_raw_tiles=document['accounting']['excluded_tail_raw_tiles'],evaluation_games=30720,
        distinct_evaluation_seed_conditions=4096,evaluation_cutoffs=cutoffs,economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates',0) for arm in ARMS},
        primary_sequence_gain_supported=summary['primary_sequence_gain_supported'],
        primary_utility=summary['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE'],
        retention_status=summary['retention_status'],final_task_gain_supported=summary['final_task_gain_supported'],
        operational_recovery_valid=True,historical_total_compute_closed=False,
        training_raw_tiles_physical_lower_bound=document['recovery']['training_raw_tiles_physical_lower_bound'],
        economic_training_raw_tiles_lower_bound_per_arm=document['recovery']['economic_training_raw_tiles_lower_bound_per_arm'],
        regenerated_original_arm_receipts=document['recovery']['regenerated_logged_arm_receipts'],
        method='Once-read new canonical warmup and all 192 stage raw/action/score histories; independent observed '
            'Beta/router and fit-prefix reconstruction, complete factual targets, once-created SOURCE/MC/local head '
            'inventory, cumulative updates and preserved-buffer receipts, full heldout components, unchanged first-task '
            'beliefs and paired checkpoint seeds, exact SOURCE repetition, literal forgetting/restoration contrasts, '
            'final equal-task primary and all fresh input/actual work costs.',
        limitations='No world sampling, experimental weight replay, new fitting or bootstrap regeneration. '
            'Producer reconstructs boards; audit checks raw, scores, terminal and memory receipts independently. '
            'Head preservation is verified from driver array-identity/counter receipts and finite driver tests. '
            'Intervals are checked for fixed-parent scope and feasible range. Stages are externally supplied and '
            'SOURCE supplies target data; four inherited source models are reused. All preserved interrupted arm '
            'means and updates reproduce exactly; original completed evaluation work is deterministically reconstructed. '
            'Unretained original process, fit and evaluation CPU remains unavailable; historical costs are lower bounds.',errors=[])


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
