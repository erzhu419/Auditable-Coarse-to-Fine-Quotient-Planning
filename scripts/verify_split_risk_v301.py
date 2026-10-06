#!/usr/bin/env python3
"""Independent V301 receipt audit; inherited V298 worlds are already settled."""
import argparse
from collections import Counter
import json
from math import log
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_natural_online_value_v286 import planning_counts, terminal

ARMS = ('SOURCE', 'MC', 'LOCAL_RISK', 'GLOBAL_RISK')
PAIRS = (('GLOBAL_RISK', 'SOURCE'), ('LOCAL_RISK', 'SOURCE'), ('MC', 'SOURCE'),
    ('GLOBAL_RISK', 'LOCAL_RISK'), ('GLOBAL_RISK', 'MC'))
EVALUATION_BASE = 301900000000
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_B_TRAINING'
COMPONENT_METRICS = ('reward_bias', 'reward_mse', 'reward_mae', 'risk_brier',
    'risk_log_loss', 'risk_bias', 'mean_risk_probability', 'win_label')
GLOBAL_FEATURE_NAMES = ('bias','empty_fraction','empty_component_fraction',
    'largest_empty_component_fraction','max_rank_fraction','second_rank_fraction',
    'rank_sum_fraction','max_in_corner','max_on_edge','max_tile_fraction',
    'max_tile_empty_neighbors_fraction','max_tile_equal_neighbors_fraction',
    'equal_occupied_adjacent_fraction','adjacent_rank_difference_fraction',
    'compressed_equal_adjacent_fraction','monotone_line_fraction',
    'rank1_fraction','rank2_fraction','top_two_mass_fraction','occupied_edge_fraction')


def nonpeak(counts):
    return {key:value for key,value in counts.items() if not key.endswith('_peak')}


def retained_fit(fit):
    """Exclude only work timings, allocation peaks and setup, never examples."""
    return {key:nonpeak(value) if key in ('target_counts','consolidation_counts') else value
        for key,value in fit.items() if key not in ('seconds','cpu_seconds','setup_counts','setup_seconds')}


def check_retained_inventory(current, previous):
    require(current['lifecycle'] == previous['lifecycle']
        and current['parent'] == previous['parent'], 'retained B lifecycle/source membership')
    require(current['dataset'] == previous['dataset'], 'fixed complete B training and heldout inventory')
    require(current['evaluation_snapshot'] == previous['evaluation_snapshot'],
        'same blind fit-prefix belief without heldout observations')


def check_mc_reproduction(current, previous):
    equal_tree(retained_fit(current['fit']), retained_fit(previous['fit']),
        'original MC nonpeak fit counts and examples')
    equal_tree(current['heldout']['game_metrics'], previous['heldout']['game_metrics'],
        'original full heldout MC reproduction')


def check_evaluation(games, life, counts):
    require(len(games) == 32 and [game['seed'] for game in games] ==
        [EVALUATION_BASE+life*1000000+episode for episode in range(32)],
        'new V301 independent paired game seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'evaluation horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and max(game['final_board']) < 11,
                'premature cutoff or goal at cutoff')
            bonus = 0.
        else:
            terminal(game['final_board'], game['status'])
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'complete game utility')
    steps = sum(game['steps'] for game in games)
    wins = sum(game['status'] == 'WON' for game in games)
    environment = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64,
        raw_tile_productions=steps+64, environment_random_draws=2*(steps+64),
        ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+32,
        ground_status_internal_swipe_calls=4*(steps+32-wins), ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment']) == Counter(environment),
        'actual evaluation costs including initial and winning spawns')
    planning_counts(counts['planning'], steps)
    return dict(games=32,mean_game_utility=mean(game['utility'] for game in games),wins=wins,
        losses=sum(game['status']=='LOST' for game in games),
        cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[i for i,game in enumerate(games) if game['status']=='CUTOFF'],steps=steps)


def check_heldout(heldout, original):
    """Reuse settled factual labels but check this head's full prediction inventory."""
    metrics = heldout['game_metrics']; previous = original['game_metrics']
    require(len(metrics) == len(previous), 'same complete heldout games')
    identity = ('episode','start','end','count','mean_factual_future_utility')
    for saved, old in zip(metrics, previous):
        require(all(saved[key] == old[key] for key in identity), 'same factual full heldout labels and samples')
        require(close(saved['bias'], saved['mean_prediction']-saved['mean_factual_future_utility']),
            'heldout signed prediction bias')
        require(saved['mse']+1e-10 >= saved['bias']**2 and saved['mae']+1e-10 >= abs(saved['bias'])
            and saved['mse']+1e-10 >= saved['mae']**2, 'heldout error moments')
    samples = sum(game['count'] for game in metrics)
    for metric in ('bias','mse','mae'):
        require(close(heldout['metrics'][metric],mean(game[metric] for game in metrics)),
            'equal complete heldout game weighting')
    return dict(games=len(metrics),samples=samples,
        **{metric:mean(game[metric] for game in metrics) for metric in ('bias','mse','mae')})


def check_representation(counts,kind,samples,log_losses=0):
    work = Counter(counts)
    require(work['risk_sigmoid_evaluations']==samples
        and work['combined_value_additions']==2*samples
        and work['combined_value_multiplications']==samples
        and work['risk_log_loss_evaluations']==log_losses,
        'actual sigmoid, combination and risk-loss work')
    if kind=='LOCAL_RISK':
        require(work==Counter(dict(risk_sigmoid_evaluations=samples,local_risk_table_lookups=32*samples,
            combined_value_additions=2*samples,combined_value_multiplications=samples,
            risk_log_loss_evaluations=log_losses)), 'local risk lookup work without global features')
    else:
        require(work['local_risk_table_lookups']==0 and work['global_feature_extractions']==samples
            and work['global_board_cell_visits']==16*samples and work['adjacent_pair_visits']==24*samples
            and work['global_line_cell_visits']==32*samples
            and work['global_dot_products']==samples
            and work['global_weight_reads']==work['global_dot_multiplications']==work['global_dot_additions']==20*samples,
            'actual 20 visible global features and risk dot products')
        require(0<=work['empty_component_node_visits']<=16*samples
            and work['empty_component_neighbor_probes']==4*work['empty_component_node_visits']
            and work['compressed_pair_comparisons']==work['monotone_pair_comparisons']<=24*samples
            and 4*samples<=work['max_tile_neighbor_probes']<=64*samples
            and work['max_tile_neighbor_probes']%4==0, 'actual global board traversal work')


def check_split_counts(stage,kind,games,steps,wins,samples):
    targets = dict(terminal_game_labels=games,risk_label_assignments=samples,
        reward_suffix_target_assignments=steps,reward_suffix_additions=steps,
        goal_checks=steps,skipped_winning_afterstates=wins)
    if 'prediction_counts' in stage:
        targets.update(utility_suffix_target_assignments=steps,utility_suffix_reward_additions=steps)
    require(Counter(stage['target_counts'])==Counter(targets),
        'split reward suffix excludes terminal bonus and risk labels use all nonwinning samples')
    check_representation(stage['representation_counts'],kind,samples,
        samples if 'prediction_counts' in stage else 0)


def check_split_fit(fit,mc,dataset,kind):
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
    require(fit['first_sample']['risk_probability']==.5
        and fit['first_sample']['reward_prediction']==mc['first_sample']['raw_prediction_before_update'],
        'initial value equals original SOURCE with zero-logit risk')
    return samples


def check_split_heldout(heldout,previous,dataset,kind):
    result = check_heldout(heldout,previous)
    games = dataset['games'][dataset['fit_game_count']:]
    steps = sum(game['steps'] for game in games); wins = sum(game['status']=='WON' for game in games)
    samples = steps-wins
    require(result['samples']==samples, 'full split-head heldout nonwinning samples')
    check_split_counts(heldout,kind,len(games),steps,wins,samples)
    expected = dict(value_predictions=samples,table_lookups=(64 if kind=='LOCAL_RISK' else 32)*samples,
        reward_predictions=samples,risk_predictions=samples,reward_table_lookups=32*samples,
        risk_table_lookups=32*samples if kind=='LOCAL_RISK' else 0)
    require(Counter(heldout['prediction_counts'])==Counter(expected), 'static split heldout predictions without writes')
    result['components'] = check_components(heldout,dataset)
    require(all(close(heldout['component_metrics'][key],result['components'][key])
        for key in COMPONENT_METRICS if key!='win_label'), 'equal complete heldout component game weighting')
    return result


def check_components(heldout, dataset):
    """Check the split-head diagnostics against the already settled heldout labels."""
    values = heldout['component_game_metrics']; combined = heldout['game_metrics']
    factual = dataset['games'][dataset['fit_game_count']:]
    require(len(values)==len(combined)==len(factual), 'full split-head heldout game inventory')
    for component, utility, game in zip(values,combined,factual):
        require(all(component[key]==utility[key] for key in ('episode','start','end','count')),
            'split components use the same heldout afterstates')
        label = float(game['status']=='WON')
        require(component['win_label']==label, 'risk label is factual heldout game outcome')
        p = component['mean_risk_probability']; bias = component['risk_bias']
        require(0. <= p <= 1. and close(bias,p-label), 'bounded Bernoulli probability and signed risk bias')
        require(bias*bias-1e-10 <= component['risk_brier'] <= abs(bias)+1e-10,
            'Bernoulli Brier moments')
        correct = p if label else 1.-p
        require(component['risk_log_loss']+1e-10 >= -log(max(correct,1e-15)),
            'risk log-loss Jensen bound')
        reward_bias = component['reward_bias']
        require(component['reward_mae']+1e-10 >= abs(reward_bias)
            and component['reward_mse']+1e-10 >= component['reward_mae']**2,
            'heldout reward error moments')
        require(close(utility['bias'],reward_bias+8.*bias),
            'reward and terminal-risk predictions recombine once')
    return dict(games=len(values),samples=sum(row['count'] for row in values),
        **{key:mean(row[key] for row in values) for key in COMPONENT_METRICS})


def check_contrast(saved, values, direction=None):
    require(len(values)==64 and close(saved['mean'],mean(values)), 'all retained life signed paired means')
    equal_tree(saved['lifecycle_deltas'],{str(i):value for i,value in enumerate(values)}, 'all signed retained lifecycle deltas')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'],{str(parent):mean(group) for parent,group in enumerate(groups)},
        'fixed parent means')
    low,high = saved['ci95']
    require(saved['interval_scope']==INTERVAL_SCOPE and
        mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'conditional retained-training interval scope and possible range')
    if direction:
        losses = [-value for value in values] if direction=='higher_is_better' else values
        require(saved['improved_equal_worse']==[sum(value<0 for value in losses),sum(value==0 for value in losses),sum(value>0 for value in losses)]
            and saved['adverse_lifecycles']==[i for i,value in enumerate(losses) if value>0],
            'signed adverse retained histories')
    else:
        require('improved_equal_worse' not in saved and 'adverse_lifecycles' not in saved, 'bias has no quality direction')
    if direction!='higher_is_better':
        require(saved['positive_equal_negative']==[sum(value>0 for value in values),sum(value==0 for value in values),sum(value<0 for value in values)],
            'literal signed contrast inventory')


def check_result_summary(summary, records, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all new game and full heldout means')
    require(summary['primary_contrast']=='GLOBAL_RISK_minus_SOURCE'
        and summary['bootstrap_draws']==20000 and summary['bootstrap_seed']==30100001
        and summary['estimator']=='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator']=='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES'
        and summary['complete_game_endpoints']==(cutoffs==0), 'registered primary complete-game endpoint')
    for arm in ARMS:
        rows = [row['arms'][arm] for row in records]; heldout = [row['heldout'] for row in rows]
        expected = dict(mean_game_utility=mean(row['mean_game_utility'] for row in rows),
            **{key:sum(row[key] for row in rows) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(row['games'] for row in heldout),samples=sum(row['samples'] for row in heldout),
                **{key:mean(row[key] for row in heldout) for key in ('bias','mse','mae')}))
        if arm in ('LOCAL_RISK','GLOBAL_RISK'):
            values = [row['components'] for row in heldout]
            expected['heldout']['components'] = dict(games=sum(row['games'] for row in values),
                samples=sum(row['samples'] for row in values),
                **{key:mean(row[key] for row in values) for key in COMPONENT_METRICS})
        equal_tree(summary['arms'][arm], expected, 'equal retained-lifecycle weighting '+arm)
    require(set(summary['paired_contrasts'])==set(summary['heldout_contrasts'])=={left+'_minus_'+right for left,right in PAIRS},
        'all registered contrasts')
    for left,right in PAIRS:
        name = left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],
            [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records],'higher_is_better')
        for metric in ('bias','mse','mae'):
            check_contrast(summary['heldout_contrasts'][name][metric],
                [row['arms'][left]['heldout'][metric]-row['arms'][right]['heldout'][metric] for row in records],
                None if metric=='bias' else 'lower_is_better')
    check_support(summary,cutoffs)


def check_support(summary,cutoffs):
    supported = cutoffs==0 and summary['paired_contrasts']['GLOBAL_RISK_minus_SOURCE']['ci95'][0]>0
    require(summary['split_risk_gain_supported']==supported and
        summary['split_risk_gain_status']==('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        'secondary utility or prediction cannot substitute for primary source gain')


def check_accounting(document, old):
    accounting = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    require(accounting['new_training_environment_observations']==accounting['physical_acquisitions']==0
        and not accounting['new_training_environment_counts'], 'retained representation fit cannot claim fresh acquisition')
    require(accounting['retained_B_acquisition_raw_tiles']==old['accounting']['new_training_environment_observations'],
        'all paid old B acquisition retained without new acquisition')
    inherited_keys = ('new_training_environment_observations','new_actor_B_raw_tiles','new_warmup_raw_tiles',
        'new_training_environment_counts','new_actor_B_counts','new_warmup_direct_counts','excluded_tail_raw_tiles')
    require(accounting['inherited_B_acquisition']=={key:old['accounting'][key] for key in inherited_keys},
        'paid actor, warmup and excluded-tail input costs inherited once')
    fields = (('fit_counts','fit','learning_counts'),('fit_target_counts','fit','target_counts'),
        ('fit_normalization_counts','fit','normalization_counts'),('fit_consolidation_counts','fit','consolidation_counts'),
        ('fit_setup_counts','fit','setup_counts'),('fit_representation_counts','fit','representation_counts'),
        ('heldout_prediction_counts','heldout','prediction_counts'),('heldout_target_counts','heldout','target_counts'),
        ('heldout_representation_counts','heldout','representation_counts'),('heldout_setup_counts','heldout','setup_counts'))
    for arm in ARMS:
        require(accounting['economic_training_raw_tiles_per_arm'][arm]==old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN']
            and accounting['inherited_costs_per_arm'][arm]==old['accounting']['inherited_costs_per_arm']['FROZEN'],
            'all arms inherit source dynamics and paid B input costs once')
        require(accounting['processed_training_samples'][arm]==sum(life['arms'][arm]['processed_training_samples'] for life in lives),
            'actual processed training samples')
        for field,stage,key in fields:
            values = [life['arms'][arm][stage].get(key,{}) for life in lives]
            require(accounting[field][arm]==sum_counts(nonpeak(row) for row in values), 'actual '+field)
            peaks = {key:max(row.get(key,0) for row in values)
                for key in {key for row in values for key in row if key.endswith('_peak')}}
            require(accounting[field+'_buffer_peaks'][arm]==peaks, 'actual '+field+' buffer peak')
        for stage in ('fit','heldout'):
            for field,key in (('processing_seconds_per_arm','seconds'),('processing_cpu_seconds_per_arm','cpu_seconds')):
                require(close(accounting[field][arm][stage],sum(life['arms'][arm][stage][key] for life in lives)),
                    'scoped '+stage+' actual processing time')
        require(accounting['private_head_weight_bytes_created'][arm]==sum(life['arms'][arm]['head_setup']['private_weight_bytes'] for life in lives),
            'private reward and risk buffers included')
        require(accounting['head_setup_counts'][arm]==sum_counts(life['arms'][arm]['head_setup']['setup_counts'] for life in lives),
            'actual private head initialization work')
        for field,key in (('processing_seconds_per_arm','setup_seconds'),('processing_cpu_seconds_per_arm','setup_cpu_seconds')):
            require(close(accounting[field][arm]['head_setup'],sum(life['arms'][arm]['head_setup'][key] for life in lives)),
                'actual private head initialization time')
        for field,key in (('evaluation_cpu_seconds_per_arm','evaluation_cpu_seconds'),('evaluation_seconds_per_arm','evaluation_seconds')):
            require(close(accounting[field][arm],sum(life['arms'][arm][key] for life in lives)), 'actual '+field)
        for field,key in (('evaluation_representation_counts','evaluation_representation_counts'),
            ('evaluation_setup_counts','evaluation_setup_counts')):
            require(accounting[field][arm]==sum_counts(life['arms'][arm][key] for life in lives), 'actual '+field)
        for kind in ('environment','planning'):
            require(accounting['evaluation_counts_per_arm'][arm][kind]==sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives),
                'per-arm actual new evaluation work')
    for kind in ('environment','planning'):
        require(accounting['evaluation_counts'][kind]==sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives for arm in ARMS),
            'all physical new evaluation work')
    require([parent['parent'] for parent in parents]==list(range(4)), 'four physical original source loads')
    for parent in parents:
        require(parent['lifecycle_ids']==list(range(parent['parent'],64,4))
            and parent['source_setup']['checkpoint_loads']==1 and parent['source_setup']['new_leaf_updates']==0,
            'each original source loaded once and unchanged')
    for field,key in (('worker_cpu_seconds','cpu_seconds'),('compiler_cpu_seconds','compiler_cpu_seconds')):
        require(close(accounting[field],sum(parent[key] for parent in parents)), 'actual '+field)
    require(accounting['canonical_rows_read']==sum(parent['reconstruction']['canonical_rows_read'] for parent in parents)
        and accounting['canonical_rows_read']==json_file(Path(document['settings']['source_summary']).with_name('audit.json'))['canonical_rows'],
        'retained reconstruction row count')
    require(accounting['reconstruction_counts']==sum_counts(parent['reconstruction']['reconstruction_counts'] for parent in parents)
        and close(accounting['reconstruction_cpu_seconds'],sum(parent['reconstruction']['cpu_seconds'] for parent in parents)),
        'actual retained reconstruction work')
    require(accounting['retained_canonical_trace_bytes']==old['accounting']['canonical_trace_bytes'], 'inherited retained storage cost')
    return accounting['economic_training_raw_tiles_per_arm']['SOURCE']


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(settings==json_file(directory/'configuration.json'), 'frozen V301 configuration changed')
    require(document['schema']=='acfqp.split_risk.v301' and document['status']=='EXPERIMENT_COMPLETE'
        and document['scientific_gate']=='NOT_A_FORMAL_GATE', 'exploratory result status')
    expected = dict(lifecycles=list(range(64)),parents=4,arms=list(ARMS),phase='B',true_p_four=.5,
        fit_fraction=.8,alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        evaluation_games=32,seed_evaluation=EVALUATION_BASE,max_steps=8192,
        bootstrap_draws=20000,bootstrap_seed=30100001,
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='ALL_RETAINED_V298_B_COMPLETE_GAMES_WITHOUT_NEW_TRAINING_ACQUISITION',
        representation='SOURCE_INITIALIZED_REWARD_NTUPLE_PLUS_ZERO_INITIALIZED_SIGMOID_TERMINAL_HEAD',
        combination='REWARD_PLUS_8_TIMES_PROBABILITY_MINUS_HALF',
        reward_target='FACTUAL_FUTURE_REWARD_EXCLUDING_CURRENT_REWARD_AND_TERMINAL_BONUS',
        risk_target='COMPLETE_FIT_GAME_WON_LABEL',global_feature_names=list(GLOBAL_FEATURE_NAMES),
        consolidation='GAME_START_PREDICTIONS_THEN_PER_FEATURE_MASS_NORMALIZED_MEAN',
        model_probability='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION',
        primary='GLOBAL_RISK_minus_SOURCE_COMPLETE_GAME_UTILITY',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        training='RETAINED_PURE_B_REWARD_AND_RISK_REPRESENTATION_COMPARISON',
        stop_rule='NO_FEATURE_LEARNING_RATE_OR_BUDGET_TUNING_ON_THIS_FROZEN_COHORT')
    for key,value in expected.items(): require(settings[key]==value, 'registered V301 '+key)
    old = json_file(settings['source_summary']); old_audit = json_file(Path(settings['source_summary']).with_name('audit.json'))
    require(old['schema']=='acfqp.stable_b.v298' and old_audit['independent_valid'], 'settled V298 B data audit')
    require(document['source_provenance']==old['source_provenance'], 'original inherited source and dynamics')
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives]==list(range(64))
        and all(life['parent']==life['lifecycle']%4 for life in lives), 'all 64 retained B histories')
    records = []; processed = Counter(); cutoffs = 0
    for life,previous in zip(lives,old['by_lifecycle']):
        check_retained_inventory(life,previous)
        check_mc_reproduction(life['arms']['MC'],previous['arms']['EPISODE_MEAN_MC'])
        equal_tree(life['arms']['SOURCE']['heldout']['game_metrics'],previous['arms']['FROZEN']['heldout']['game_metrics'],
            'original SOURCE full heldout reproduction')
        arms = {}; samples = life['arms']['MC']['fit']['trained_afterstates']
        for arm in ARMS:
            value = life['arms'][arm]; fit = value['fit']; setup = value['head_setup']
            expected_samples = 0 if arm=='SOURCE' else samples
            require(value['processed_training_samples']==value['sample_counter']==fit['trained_afterstates']==expected_samples
                and value['static_evaluation_valid'], 'same sample inventory and static unchanged evaluation')
            processed[arm] += expected_samples
            if arm=='SOURCE':
                require(fit['method']=='NONE' and not fit['learning_counts'] and not fit['target_counts']
                    and not fit['consolidation_counts'] and setup['source_weights_shared'] and setup['private_weight_bytes']==0,
                    'SOURCE receives no new updates or copies')
            else:
                require(not setup['source_weights_shared'] and setup['private_weight_bytes']==setup['setup_counts']['allocated_weight_bytes']
                    and setup['setup_counts']['source_weight_bytes_copied']==8*setup['setup_counts']['source_parameters_copied'],
                    'actual private source copy and full weight buffer costs')
            if arm in ('LOCAL_RISK','GLOBAL_RISK'):
                check_split_fit(fit,life['arms']['MC']['fit'],life['dataset'],arm)
                head = setup['setup_counts']; source_parameters = head['source_parameters_copied']
                risk_parameters = source_parameters if arm=='LOCAL_RISK' else 20
                require(head['initialized_zero_risk_parameters']==risk_parameters
                    and head['allocated_weight_parameters']==source_parameters+risk_parameters
                    and head['allocated_weight_bytes']==8*(source_parameters+risk_parameters),
                    'original reward prior and all zero-logit risk parameters')
                heldout = check_split_heldout(value['heldout'],previous['arms']['FROZEN']['heldout'],life['dataset'],arm)
                check_representation(value['evaluation_representation_counts'],arm,
                    value['evaluation_counts']['planning'].get('value_predictions',0))
            else:
                original = previous['arms']['FROZEN' if arm=='SOURCE' else 'EPISODE_MEAN_MC']['heldout']
                require(value['heldout']['prediction_counts']==original['prediction_counts']
                    and nonpeak(value['heldout']['target_counts'])==nonpeak(original['target_counts'])
                    and not value['evaluation_representation_counts'] and not value['evaluation_setup_counts'],
                    'original SOURCE/MC static scoring and evaluation implementation')
                heldout = check_heldout(value['heldout'],original)
            arms[arm] = dict(check_evaluation(value['game_summaries'],life['lifecycle'],value['evaluation_counts']),heldout=heldout)
            cutoffs += arms[arm]['cutoffs']
        for local,global_ in zip(life['arms']['LOCAL_RISK']['heldout']['component_game_metrics'],
                life['arms']['GLOBAL_RISK']['heldout']['component_game_metrics']):
            require(all(local[key]==global_[key] for key in ('episode','start','end','count','reward_bias','reward_mse','reward_mae')),
                'local versus global changes only the risk representation within shared reward fitting')
        records.append(dict(lifecycle=life['lifecycle'],parent=life['parent'],arms=arms))
    summary = document['summary']; check_result_summary(summary,records,cutoffs)
    economic = check_accounting(document,old)
    return dict(status='PASS',independent_valid=True,lifecycles=64,fixed_source_parents=4,
        new_training_environment_observations=0,retained_B_acquisition_raw_tiles=document['accounting']['retained_B_acquisition_raw_tiles'],
        fit_games=sum(life['dataset']['fit_game_count'] for life in lives),processed_training_samples=dict(processed),
        evaluation_games=8192,evaluation_cutoffs=cutoffs,economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates',0) for arm in ARMS},
        split_risk_gain_supported=summary['split_risk_gain_supported'],
        primary_utility=summary['paired_contrasts']['GLOBAL_RISK_minus_SOURCE'],
        method='Fixed retained B and fit-prefix inventory, original MC and SOURCE reproduction; split factual reward '
            'and Bernoulli target sample ledgers, game-start normalized writes, shared reward head, bounded heldout '
            'component moments, fresh complete paired games, signed endpoint means and actual total costs.',
        limitations='No replay of settled V298 canonical worlds or value weights; no new bootstrap draws. '
            'Saved intervals checked for conditional scope and feasible range. New evaluation is independent; '
            'training histories and source parents remain inherited.',errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--input',type=Path,required=True)
    directory = parser.parse_args().input
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False)); raise SystemExit(not result['independent_valid'])


if __name__=='__main__':
    main()
