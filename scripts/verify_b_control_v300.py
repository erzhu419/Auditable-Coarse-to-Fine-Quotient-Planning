#!/usr/bin/env python3
"""Independent V300 receipt audit; inherited V298 worlds are already settled."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_natural_online_value_v286 import planning_counts, terminal

ARMS = ('SOURCE', 'MC', 'EXPECTED_CONTROL')
PAIRS = (('EXPECTED_CONTROL', 'SOURCE'), ('EXPECTED_CONTROL', 'MC'), ('MC', 'SOURCE'))
EVALUATION_BASE = 300900000000
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_B_TRAINING'


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
        'new V300 independent paired game seeds')
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
    require(Counter(heldout['prediction_counts']) == Counter(dict(value_predictions=samples,table_lookups=32*samples)),
        'full heldout static predictions without updates')
    require(nonpeak(heldout['target_counts']) == nonpeak(original['target_counts']),
        'same full factual heldout target work')
    for metric in ('bias','mse','mae'):
        require(close(heldout['metrics'][metric],mean(game[metric] for game in metrics)),
            'equal complete heldout game weighting')
    return dict(games=len(metrics),samples=samples,
        **{metric:mean(game[metric] for game in metrics) for metric in ('bias','mse','mae')})


def check_control_fit(fit, mc, dataset, model_p):
    games = dataset['games'][:dataset['fit_game_count']]
    steps = sum(game['steps'] for game in games)
    wins = sum(game['status']=='WON' for game in games); samples = steps-wins
    require(fit['method']=='EXPECTED_CONTROL_MEAN' and fit['alpha']==.0025
        and fit['model_p_four']==model_p and fit['game_head_targets_frozen'],
        'control target uses fixed observed B prefix belief and game-start head')
    require(fit['fitted_games']==len(games) and fit['fitted_steps']==dataset['fit_step_end']==steps
        and fit['trained_afterstates']==samples, 'same chronological completed control fit games')
    require(fit['learning_counts']==mc['learning_counts']
        and nonpeak(fit['consolidation_counts'])==nonpeak(mc['consolidation_counts']),
        'target-only change preserves addresses normalization and parameter writes')
    require(Counter(nonpeak(fit['target_counts']))==Counter(dict(goal_checks=steps,
        raw_target_subtractions=samples,skipped_winning_afterstates=wins)),
        'control target excludes winning afterstates and factual MC suffix construction')
    work = Counter(fit['planning_counts']); outcomes = work['generated_spawn_outcomes']
    require(work['expected_control_target_assignments']==samples
        and work['empty_cell_count_visits']==work['empty_cell_branch_visits']==16*samples
        and 2*samples <= outcomes <= 32*samples, 'one enumerated control target per nonwinning fit sample')
    require(work['root_swipe_calls']==work['root_legal_actions']==work['root_goal_actions']==0
        and work['leaf_terminal_goal_states']==0
        and work['leaf_choose_calls']==work['expanded_postspawn_states']==outcomes
        and work['spawn_rank1_outcomes']==work['spawn_rank2_outcomes']
        and outcomes==work['spawn_rank1_outcomes']+work['spawn_rank2_outcomes']
        and work['expectimax_probability_products']==work['expectimax_probability_sums']==outcomes
        and work['spawn_board_cells_copied']==16*outcomes,
        'expected spawn branches probabilities and unchanged afterstate target scope')
    require(work['second_ply_swipe_calls']==work['learned_swipe_calls']==4*outcomes
        and work['line_table_lookups']==4*work['learned_swipe_calls']
        and work['table_lookups']==32*work['value_predictions'],
        'actual target planning and value lookup work')
    for key in ('first_sample','last_sample'):
        sample, original = fit[key], mc[key]
        require((sample['episode'],sample['step'])==(original['episode'],original['step'])
            and sample['raw_target']==sample['target']
            and close(sample['error'],sample['raw_target']-sample['raw_prediction_before_update']),
            'control first and last sample inventory and residual')
    return samples


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
    require(summary['primary_contrast']=='EXPECTED_CONTROL_minus_SOURCE'
        and summary['bootstrap_draws']==20000 and summary['bootstrap_seed']==30000001
        and summary['estimator']=='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator']=='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES'
        and summary['complete_game_endpoints']==(cutoffs==0), 'registered primary complete-game endpoint')
    for arm in ARMS:
        rows = [row['arms'][arm] for row in records]; heldout = [row['heldout'] for row in rows]
        expected = dict(mean_game_utility=mean(row['mean_game_utility'] for row in rows),
            **{key:sum(row[key] for row in rows) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(row['games'] for row in heldout),samples=sum(row['samples'] for row in heldout),
                **{key:mean(row[key] for row in heldout) for key in ('bias','mse','mae')}))
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
    supported = cutoffs==0 and summary['paired_contrasts']['EXPECTED_CONTROL_minus_SOURCE']['ci95'][0]>0
    require(summary['control_target_gain_supported']==supported and
        summary['control_target_gain_status']==('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        'secondary utility or prediction cannot substitute for primary source gain')


def check_accounting(document, old):
    accounting = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    require(accounting['new_training_environment_observations']==accounting['physical_acquisitions']==0
        and not accounting['new_training_environment_counts'], 'retained target-only fit cannot claim fresh acquisition')
    require(accounting['retained_B_acquisition_raw_tiles']==old['accounting']['new_training_environment_observations'],
        'old paid B acquisition omitted or charged as new')
    for arm in ARMS:
        require(accounting['economic_training_raw_tiles_per_arm'][arm]==old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN']
            and accounting['inherited_costs_per_arm'][arm]==old['accounting']['inherited_costs_per_arm']['FROZEN'],
            'all arms inherit source dynamics and paid B acquisition once')
        require(accounting['processed_training_samples'][arm]==sum(life['arms'][arm]['processed_training_samples'] for life in lives),
            'actual processed training samples')
        for field,section,key in (('fit_counts','fit','learning_counts'),
            ('fit_planning_counts','fit','planning_counts'),
            ('heldout_prediction_counts','heldout','prediction_counts'),
            ('fit_setup_counts','fit','setup_counts'),('heldout_setup_counts','heldout','setup_counts')):
            require(accounting[field][arm]==sum_counts(life['arms'][arm][section].get(key,{}) for life in lives),
                'actual '+field)
        for stage in ('fit','heldout'):
            target_counts = [life['arms'][arm][stage]['target_counts'] for life in lives]
            target_peaks = {key:max(value.get(key,0) for value in target_counts)
                for key in {key for value in target_counts for key in value if key.endswith('_peak')}}
            require(accounting[stage+'_target_counts'][arm]==sum_counts(nonpeak(counts) for counts in target_counts)
                and accounting[stage+'_target_buffer_peaks'][arm]==target_peaks,
                'actual '+stage+' target work and buffer peaks')
            for field,key in (('processing_seconds_per_arm','seconds'),('processing_cpu_seconds_per_arm','cpu_seconds')):
                require(close(accounting[field][arm][stage],sum(life['arms'][arm][stage][key] for life in lives)),
                    'scoped '+stage+' actual processing time')
        counts = [life['arms'][arm]['fit']['consolidation_counts'] for life in lives]
        require(accounting['consolidation_counts'][arm]==sum_counts(nonpeak(value) for value in counts),
            'actual address normalization and consolidation work')
        peaks = {key:max(value.get(key,0) for value in counts)
            for key in {key for value in counts for key in value if key.endswith('_peak')}}
        require(accounting['consolidation_buffer_peaks'][arm]==peaks, 'peak allocations are not summed')
        require(accounting['private_head_weight_bytes_created'][arm]==sum(life['arms'][arm]['head_setup']['private_weight_bytes'] for life in lives),
            'new private weight copy costs')
        require(accounting['head_setup_counts'][arm]==sum_counts(life['arms'][arm]['head_setup']['setup_counts'] for life in lives),
            'actual private head initialization counts')
        for field,key in (('processing_seconds_per_arm','setup_seconds'),('processing_cpu_seconds_per_arm','setup_cpu_seconds')):
            require(close(accounting[field][arm]['head_setup'],sum(life['arms'][arm]['head_setup'][key] for life in lives)),
                'actual private head initialization time')
        require(close(accounting['evaluation_cpu_seconds_per_arm'][arm],sum(life['arms'][arm]['evaluation_cpu_seconds'] for life in lives)),
            'actual evaluation processing CPU')
        require(close(accounting['evaluation_seconds_per_arm'][arm],sum(life['arms'][arm]['evaluation_seconds'] for life in lives)),
            'actual evaluation elapsed time')
        for kind in ('environment','planning'):
            require(accounting['evaluation_counts_per_arm'][arm][kind]==sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives),
                'per-arm actual new evaluation work')
    for kind in ('environment','planning'):
        require(accounting['evaluation_counts'][kind]==sum_counts(life['arms'][arm]['evaluation_counts'][kind] for life in lives for arm in ARMS),
            'all physical new evaluation work')
    require([parent['parent'] for parent in parents]==list(range(4)), 'four physical inherited source loads')
    for parent in parents:
        require(parent['lifecycle_ids']==list(range(parent['parent'],64,4))
            and parent['source_setup']['checkpoint_loads']==1 and parent['source_setup']['new_leaf_updates']==0,
            'each frozen source loaded once and unchanged')
    for field,key in (('worker_cpu_seconds','cpu_seconds'),('compiler_cpu_seconds','compiler_cpu_seconds')):
        require(close(accounting[field],sum(parent[key] for parent in parents)), 'actual '+field)
    require(accounting['canonical_rows_read']==sum(parent['reconstruction']['canonical_rows_read'] for parent in parents)
        and accounting['canonical_rows_read']==json_file(Path(document['settings']['source_summary']).with_name('audit.json'))['canonical_rows'],
        'retained reconstruction row count')
    require(accounting['reconstruction_counts']==sum_counts(parent['reconstruction']['reconstruction_counts'] for parent in parents)
        and close(accounting['reconstruction_cpu_seconds'],sum(parent['reconstruction']['cpu_seconds'] for parent in parents)),
        'actual retained reconstruction work')
    require(accounting['retained_canonical_trace_bytes']==sum(parent['trace_bytes'] for parent in old['parent_receipts']),
        'retained storage cost')
    return accounting['economic_training_raw_tiles_per_arm']['SOURCE']


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(settings==json_file(directory/'configuration.json'), 'frozen V300 configuration changed')
    require(document['schema']=='acfqp.b_control.v300' and document['status']=='EXPERIMENT_COMPLETE'
        and document['scientific_gate']=='NOT_A_FORMAL_GATE', 'exploratory result status')
    expected = dict(lifecycles=list(range(64)),parents=4,arms=list(ARMS),phase='B',true_p_four=.5,
        fit_fraction=.8,alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        evaluation_games=32,seed_evaluation=EVALUATION_BASE,max_steps=8192,
        bootstrap_draws=20000,bootstrap_seed=30000001,
        source_initialization='ORIGINAL_SOURCE_WITHOUT_A_STAGE_UPDATES',
        observations='ALL_RETAINED_V298_B_COMPLETE_GAMES_WITHOUT_NEW_TRAINING_ACQUISITION',
        target_probability='FIXED_OBSERVED_FIT_PREFIX_BELIEF_SHARED_WITH_EVALUATION',
        control_target='H2_EXPECTED_NEXT_DIRECT_MAX_FROM_GAME_START_HEAD',
        consolidation='PER_GAME_ADDRESS_OCCURRENCE_NORMALIZED_MEAN',
        primary='EXPECTED_CONTROL_minus_SOURCE_COMPLETE_GAME_UTILITY',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES',
        training='RETAINED_PURE_B_TARGET_ONLY_COMPARISON')
    for key,value in expected.items():
        require(settings[key]==value, 'registered V300 '+key)
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
        samples = check_control_fit(life['arms']['EXPECTED_CONTROL']['fit'],life['arms']['MC']['fit'],
            life['dataset'],life['evaluation_snapshot']['estimated_p_four'])
        arms = {}
        for arm in ARMS:
            value = life['arms'][arm]; fit = value['fit']; setup = value['head_setup']
            expected_samples = 0 if arm=='SOURCE' else samples
            require(value['processed_training_samples']==value['sample_counter']==fit['trained_afterstates']==expected_samples
                and value['static_evaluation_valid'], 'same sample inventory and static unchanged evaluation')
            processed[arm] += expected_samples
            if arm=='SOURCE':
                require(fit['method']=='NONE' and not fit['learning_counts'] and not fit['target_counts']
                    and not fit.get('planning_counts') and not fit['consolidation_counts']
                    and setup['source_weights_shared'] and setup['private_weight_bytes']==0,
                    'SOURCE receives no new value updates or copies')
            else:
                require(not setup['source_weights_shared'] and setup['private_weight_bytes']==setup['setup_counts']['source_weight_bytes_copied'],
                    'private source initialization and copy costs')
            heldout = check_heldout(value['heldout'],previous['arms']['FROZEN']['heldout'])
            arms[arm] = dict(check_evaluation(value['game_summaries'],life['lifecycle'],value['evaluation_counts']),heldout=heldout)
            cutoffs += arms[arm]['cutoffs']
        records.append(dict(lifecycle=life['lifecycle'],parent=life['parent'],arms=arms))
    summary = document['summary']; check_result_summary(summary,records,cutoffs)
    economic = check_accounting(document,old)
    return dict(status='PASS',independent_valid=True,lifecycles=64,fixed_source_parents=4,
        new_training_environment_observations=0,retained_B_acquisition_raw_tiles=document['accounting']['retained_B_acquisition_raw_tiles'],
        fit_games=sum(life['dataset']['fit_game_count'] for life in lives),
        processed_training_samples=dict(processed),evaluation_games=6144,evaluation_cutoffs=cutoffs,
        economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates',0) for arm in ARMS},
        control_target_gain_supported=summary['control_target_gain_supported'],
        primary_utility=summary['paired_contrasts']['EXPECTED_CONTROL_minus_SOURCE'],
        method='Fixed retained B and fit-prefix inventory, original MC fit and full heldout reproduction, '
            'target-only normalization and branch work, fresh complete paired games, signed endpoint means and actual costs.',
        limitations='No replay of settled V298 canonical worlds or value weights; no new bootstrap draws. '
            'Intervals are checked for their saved receipt scope and feasible range. New evaluation is independent; '
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
