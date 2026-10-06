#!/usr/bin/env python3
"""Independent same-facts A1-history control audit; V303 worlds remain settled."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean

from verify_b_control_v300 import check_heldout
from verify_continual_v303 import check_belief, check_evaluation, check_local_fit
from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_split_risk_v301 import COMPONENT_METRICS, check_representation, check_split_heldout, nonpeak

ARMS = ('SOURCE', 'MC_FRESH_B', 'MC_AFTER_A1_B', 'LOCAL_FRESH_B', 'LOCAL_AFTER_A1_B')
INHERITED = {'MC_AFTER_A1_B': 'MC', 'LOCAL_AFTER_A1_B': 'LOCAL_RISK'}
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_HISTORIES'
PRIMARY = 'LOCAL_FRESH_B_minus_LOCAL_AFTER_A1_B'
PAIRS = (('LOCAL_FRESH_B', 'LOCAL_AFTER_A1_B'), ('MC_FRESH_B', 'MC_AFTER_A1_B'),
    ('LOCAL_FRESH_B', 'SOURCE'), ('LOCAL_AFTER_A1_B', 'SOURCE'),
    ('MC_FRESH_B', 'SOURCE'), ('MC_AFTER_A1_B', 'SOURCE'))


def scientific_receipt(value):
    """Setup/cache work and elapsed times differ; targets and numerical results cannot."""
    return {key: item for key, item in value.items()
        if key not in ('seconds', 'cpu_seconds', 'setup_counts')}


def check_inventory(current, previous):
    require(current['lifecycle'] == previous['lifecycle'] and current['parent'] == previous['parent'],
        'retained A1/B lifecycle/source membership')
    require(set(current['datasets']) == {'A1', 'B'} and all(
        current['datasets'][stage] == previous['stages'][stage]['dataset'] for stage in ('A1', 'B')),
        'same complete chronological A1 and B factual inventory')
    require(current['evaluation_belief'] == previous['evaluation_beliefs']['B'],
        'same original observed B fit-prefix belief')
    check_belief(current['evaluation_belief'], current['datasets']['B'])


def fit_samples(dataset):
    games = dataset['games'][:dataset['fit_game_count']]
    return sum(game['steps'] - (game['status'] == 'WON') for game in games)


def check_update_chain(value, arm, datasets):
    stages = () if arm == 'SOURCE' else ('A1', 'B') if arm in INHERITED else ('B',)
    require(set(value['fit_by_stage']) == set(value['head_updates_by_stage']) == set(stages),
        'fresh B and inherited A1/B have their exact fit-stage inventory')
    updates = 0
    for stage in stages:
        fit = value['fit_by_stage'][stage]; samples = fit_samples(datasets[stage])
        chain = value['head_updates_by_stage'][stage]
        require(fit['trained_afterstates'] == samples and chain == dict(before=updates, after=updates+samples),
            'cumulative updates retain A1 exactly once and use the same complete B samples')
        updates += samples
    require(value['head_updates'] == updates, 'final head updates equal its actual fitted history')
    require(value['evaluation_is_new'] == value['heldout_is_new'] == (arm != 'SOURCE'),
        'SOURCE diagnostics are reused and four fitted-head diagnostics are newly computed')
    return updates


def check_head_setup(setup, arm):
    counts = setup['setup_counts']
    if arm == 'SOURCE':
        require(setup['source_weights_shared'] and setup['private_weight_bytes'] == 0 and not counts,
            'SOURCE reuses unchanged original weights without a private allocation')
        return
    size = counts['source_parameters_copied']
    multiplier = 2 if arm.startswith('LOCAL_') else 1
    require(not setup['source_weights_shared'] and counts['source_weight_bytes_copied'] == 8*size
        and counts['allocated_weight_parameters'] == multiplier*size
        and counts['allocated_weight_bytes'] == setup['private_weight_bytes'] == 8*multiplier*size,
        'each learner initializes once from the original SOURCE and pays its private weight allocation')
    if multiplier == 2:
        require(counts['initialized_zero_risk_parameters'] == size,
            'both local branches initialize their risk head to zero logits before any fit')


def check_reproduced_arm(current, previous, old_arm):
    for stage in ('A1', 'B'):
        equal_tree(scientific_receipt(current['fit_by_stage'][stage]),
            scientific_receipt(previous['stages'][stage]['arms'][old_arm]['fit']),
            'inherited '+old_arm+' '+stage+' targets predictions gradients and writes reproduce V303')
    original = previous['stages']['B']['arms'][old_arm]
    equal_tree(scientific_receipt(current['heldout']), scientific_receipt(original['heldout']),
        'inherited '+old_arm+' full B heldout predictions reproduce V303')
    equal_tree(scientific_receipt(current['evaluation']), scientific_receipt(original['evaluations']['B']),
        'inherited '+old_arm+' all paired B actions and terminal game receipts reproduce V303')


def check_mc_fit(fit, original, dataset):
    games = dataset['games'][:dataset['fit_game_count']]
    steps = sum(game['steps'] for game in games); samples = fit_samples(dataset)
    require(fit['method'] == 'EPISODE_MEAN_MC' and fit['alpha'] == .0025
        and fit['fitted_games'] == len(games) and fit['fitted_steps'] == dataset['fit_step_end'] == steps
        and fit['trained_afterstates'] == samples, 'fixed MC method and complete chronological fit prefix')
    for key in ('learning_counts', 'target_counts', 'consolidation_counts', 'count_semantics'):
        equal_tree(fit[key], original[key], 'same B factual MC targets address normalization and work '+key)
    for key in ('first_sample', 'last_sample'):
        sample, old = fit[key], original[key]
        require(all(sample[name] == old[name] for name in ('episode', 'step', 'target', 'raw_target'))
            and close(sample['error'], sample['raw_target']-sample['raw_prediction_before_update']),
            'first and last MC labels remain fixed while prior predictions may change')


def check_lifecycle(current, previous):
    check_inventory(current, previous)
    require(set(current['arms']) == set(ARMS), 'all five frozen original and history-control arms')
    source = previous['stages']['B']['arms']['SOURCE']
    arms = {}; updates = {}; cutoffs = 0
    for arm in ARMS:
        value = current['arms'][arm]
        updates[arm] = check_update_chain(value, arm, current['datasets'])
        check_head_setup(value['head_setup'], arm)
        if arm == 'SOURCE':
            equal_tree(scientific_receipt(value['heldout']), scientific_receipt(source['heldout']),
                'original SOURCE full B heldout receipt is reused unchanged')
            equal_tree(scientific_receipt(value['evaluation']), scientific_receipt(source['evaluations']['B']),
                'original SOURCE complete B evaluation receipt is reused unchanged')
        if arm in INHERITED:
            check_reproduced_arm(value, previous, INHERITED[arm])
        if arm.startswith('MC_'):
            check_mc_fit(value['fit_by_stage']['B'], previous['stages']['B']['arms']['MC']['fit'],
                current['datasets']['B'])
        if arm.startswith('LOCAL_'):
            mc_arm = 'MC_FRESH_B' if arm == 'LOCAL_FRESH_B' else 'MC_AFTER_A1_B'
            check_local_fit(value['fit_by_stage']['B'], current['arms'][mc_arm]['fit_by_stage']['B'],
                current['datasets']['B'], 'A1' if arm == 'LOCAL_FRESH_B' else 'B')
            heldout = check_split_heldout(value['heldout'], source['heldout'], current['datasets']['B'], 'LOCAL_RISK')
        else:
            heldout = check_heldout(value['heldout'], source['heldout'])
        evaluation = value['evaluation']
        endpoint = check_evaluation(evaluation, current['lifecycle'], 'B', current['evaluation_belief'])
        if arm.startswith('LOCAL_'):
            check_representation(evaluation['representation_counts'], 'LOCAL_RISK',
                evaluation['counts']['planning'].get('value_predictions', 0))
        else:
            require(not evaluation['representation_counts'] and not evaluation['setup_counts'],
                'SOURCE and MC evaluation have no extra risk representation')
        arms[arm] = endpoint; cutoffs += endpoint['cutoffs']
    return dict(lifecycle=current['lifecycle'], parent=current['parent'], arms=arms), updates, cutoffs


def check_contrast(saved, values, direction=None):
    require(len(values) == 64 and close(saved['mean'], mean(values)), 'all matched-history signed lifecycle means')
    equal_tree(saved['lifecycle_deltas'], {str(i):value for i,value in enumerate(values)},
        'all original paired lifecycle differences remain retained')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent):mean(group) for parent,group in enumerate(groups)},
        'four fixed-parent paired mean differences')
    low, high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE and
        mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'interval stays conditional on retained training and fixed parents')
    if direction is not None:
        losses = [-value for value in values] if direction == 'higher_is_better' else values
        require(saved['improved_equal_worse'] == [sum(v < 0 for v in losses),sum(v == 0 for v in losses),sum(v > 0 for v in losses)]
            and saved['adverse_lifecycles'] == [i for i,v in enumerate(losses) if v > 0],
            'all signed adverse control results are retained')


def check_support(summary, cutoffs):
    complete = cutoffs == 0
    statuses = {}; gains = {}; transfers = {}
    for family in ('LOCAL', 'MC'):
        lower, upper = summary['paired_contrasts'][family+'_FRESH_B_minus_'+family+'_AFTER_A1_B']['ci95']
        statuses[family] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else 'SUPPORTED_PENALTY' if lower > 0.
            else 'SUPPORTED_BENEFIT' if upper < 0. else 'UNRESOLVED')
        gains[family] = complete and summary['paired_contrasts'][family+'_FRESH_B_minus_SOURCE']['ci95'][0] > 0.
        transfers[family] = statuses[family] == 'SUPPORTED_PENALTY' and \
            summary['paired_contrasts'][family+'_AFTER_A1_B_minus_SOURCE']['ci95'][1] < 0.
    supported = statuses['LOCAL'] == 'SUPPORTED_PENALTY'
    diagnosis = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else
        'FRESH_B_GAIN_WITH_HISTORY_NEGATIVE_TRANSFER_SUPPORTED' if gains['LOCAL'] and transfers['LOCAL'] else
        'HISTORY_NEGATIVE_TRANSFER_SUPPORTED' if transfers['LOCAL'] else
        'HISTORY_INITIALIZATION_PENALTY_SUPPORTED' if supported else
        'HISTORY_INITIALIZATION_BENEFIT_SUPPORTED' if statuses['LOCAL'] == 'SUPPORTED_BENEFIT' else
        'FRESH_B_GAIN_SUPPORTED_HISTORY_EFFECT_UNRESOLVED' if gains['LOCAL'] else
        'NO_SUPPORTED_HISTORY_PENALTY_OR_FRESH_B_GAIN')
    require(summary['complete_game_endpoints'] == complete and summary['history_effect_status'] == statuses
        and summary['fresh_b_gain_supported'] == gains and summary['history_negative_transfer_supported'] == transfers
        and summary['primary_history_penalty_supported'] == supported and summary['history_diagnosis'] == diagnosis,
        'initialization penalty absolute negative transfer and fresh B benefit remain separate claims')


def check_result_summary(summary, records, lives, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all same-seed B game endpoints without imported aggregates')
    require(summary['primary_contrast'] == PRIMARY and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_seed'] == 30400001
        and summary['estimator'] == 'EQUAL_B_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator'] == 'EQUAL_COMPLETE_B_HELDOUT_GAMES_THEN_LIFECYCLES',
        'frozen conditional matched-history primary and complete-game weighting')
    for arm in ARMS:
        endpoints = [row['arms'][arm] for row in records]
        expected = dict(mean_game_utility=mean(value['mean_game_utility'] for value in endpoints),
            **{key:sum(value[key] for value in endpoints) for key in ('games','wins','losses','cutoffs','steps')})
        equal_tree(summary['arms'][arm], expected, 'equal B game then lifecycle utility '+arm)
        heldouts = [life['arms'][arm]['heldout'] for life in lives]
        expected_heldout = dict(games=sum(len(value['game_metrics']) for value in heldouts),
            samples=sum(game['count'] for value in heldouts for game in value['game_metrics']),
            **{key:mean(mean(game[key] for game in value['game_metrics']) for value in heldouts)
                for key in ('bias','mse','mae')})
        if arm.startswith('LOCAL_'):
            expected_heldout['components'] = {key:mean(mean(game[key] for game in value['component_game_metrics'])
                for value in heldouts) for key in COMPONENT_METRICS}
        equal_tree(summary['heldout'][arm], expected_heldout, 'same factual descriptive B heldout '+arm)
    require(set(summary['paired_contrasts']) == {left+'_minus_'+right for left,right in PAIRS},
        'all frozen history-effect and original-SOURCE contrasts')
    for left,right in PAIRS:
        values = [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records]
        check_contrast(summary['paired_contrasts'][left+'_minus_'+right], values, 'higher_is_better')
    check_support(summary, cutoffs)


def check_training_budget(account, old):
    require(account['new_training_environment_observations'] == account['physical_acquisitions'] == 0,
        'same retained facts do not create new training acquisitions')
    raw = {stage:sum(life['stages'][stage]['acquisition']['warmup']['raw_tiles']+
        life['stages'][stage]['acquisition']['training']['raw_tiles'] for life in old['by_lifecycle'])
        for stage in ('A1','B')}
    require(account['inherited_raw_tiles_by_stage'] == raw,
        'both retained warmups complete actor boundaries and discarded tails remain paid')
    base = old['accounting']['inherited_costs_per_arm']['SOURCE']
    original = base['source_training_raw_tiles']+base['dynamics_raw_tiles']
    expected = {}
    for arm in ARMS:
        expected[arm] = original+raw['B']+(raw['A1'] if arm in INHERITED else 0)
        require(account['inherited_costs_per_arm'][arm] == base
            and account['economic_training_raw_tiles_per_arm'][arm] == expected[arm],
            'all arms pay observed B model data while only inherited learners additionally pay A1 history')
    require(account['historical_sequence_physical_training_raw_tiles_lower_bound'] ==
        old['recovery']['training_raw_tiles_physical_lower_bound'] and not account['historical_total_compute_closed'],
        'interrupted V303 physical costs and unavailable historical CPU remain explicit')
    return expected


def check_accounting(document, old, old_audit):
    account = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    economic = check_training_budget(account, old)
    require(account['new_evaluation_games'] == 8192 and account['reused_evaluation_games'] == 2048,
        '8192 new learned-head evaluations and 2048 reused SOURCE games are separate physical work')
    sections = {
        'fits':{arm:[fit for life in lives for fit in life['arms'][arm]['fit_by_stage'].values()] for arm in ARMS},
        'heldout':{arm:[life['arms'][arm]['heldout'] for life in lives if life['arms'][arm]['heldout_is_new']] for arm in ARMS},
        'evaluation':{arm:[life['arms'][arm]['evaluation'] for life in lives if life['arms'][arm]['evaluation_is_new']] for arm in ARMS}}
    fields = (('fit_counts','fits','learning_counts'),('fit_target_counts','fits','target_counts'),
        ('fit_normalization_counts','fits','normalization_counts'),('fit_consolidation_counts','fits','consolidation_counts'),
        ('fit_representation_counts','fits','representation_counts'),('heldout_prediction_counts','heldout','prediction_counts'),
        ('heldout_target_counts','heldout','target_counts'),('heldout_representation_counts','heldout','representation_counts'),
        ('evaluation_representation_counts','evaluation','representation_counts'),('evaluation_setup_counts','evaluation','setup_counts'))
    for arm in ARMS:
        fits = sections['fits'][arm]; evaluations = sections['evaluation'][arm]; heldouts = sections['heldout'][arm]
        samples = sum(fit['trained_afterstates'] for fit in fits)
        require(account['processed_training_samples'][arm] == account['final_cumulative_updates'][arm] == samples
            == sum(life['arms'][arm]['head_updates'] for life in lives),
            'new fit work equals actual retained or fresh cumulative parameter updates')
        for field,section,key in fields:
            values = [item.get(key,{}) for item in sections[section][arm]]
            require(account[field][arm] == sum_counts(nonpeak(value) for value in values), 'actual new '+field)
            peaks = {name:max(value.get(name,0) for value in values)
                for name in {name for value in values for name in value if name.endswith('_peak')}}
            require(account[field+'_buffer_peaks'][arm] == peaks, 'actual new '+field+' buffer peaks')
        setup = [life['arms'][arm]['head_setup'] for life in lives]
        require(account['head_setup_counts'][arm] == sum_counts(value['setup_counts'] for value in setup)
            and account['private_head_weight_bytes_created'][arm] == sum(value['private_weight_bytes'] for value in setup),
            'four new once-per-lifecycle private heads and original SOURCE allocation costs')
        times = account['processing_cpu_seconds_per_arm'][arm]
        require(close(times['fit'],sum(fit['cpu_seconds'] for fit in fits))
            and close(times['heldout'],sum(value['cpu_seconds'] for value in heldouts))
            and close(times['head_setup'],sum(value['setup_cpu_seconds'] for value in setup)),
            'actual new fit heldout and private initialization CPU excludes reused diagnostics')
        require(close(account['evaluation_cpu_seconds_per_arm'][arm],sum(value['cpu_seconds'] for value in evaluations)),
            'actual new evaluation CPU excludes reused SOURCE outcomes')
        for kind in ('environment','planning'):
            require(account['evaluation_counts_per_arm'][arm][kind] == sum_counts(value['counts'][kind] for value in evaluations),
                'actual new per-arm '+kind+' excludes reused SOURCE games')
    for kind in ('environment','planning'):
        require(account['evaluation_counts'][kind] == sum_counts(value['counts'][kind]
            for values in sections['evaluation'].values() for value in values),
            'all newly executed learned-head '+kind+' costs')
    require([parent['parent'] for parent in parents] == list(range(4)), 'four original SOURCE parent loads')
    for parent in parents:
        require(parent['lifecycle_ids'] == list(range(parent['parent'],64,4))
            and parent['source_setup']['checkpoint_loads'] == 1 and parent['source_setup']['new_leaf_updates'] == 0
            and parent['reconstruction']['reconstructed_stages'] == 32,
            'each unchanged original SOURCE supplies exactly its sixteen A1/B pairs')
    require(account['retained_canonical_trace_bytes'] == old['accounting']['canonical_trace_bytes']
        and account['canonical_rows_read'] == old_audit['canonical_rows']
        == sum(parent['reconstruction']['canonical_rows_read'] for parent in parents)
        and account['reconstructed_stages'] == 128 == sum(parent['reconstruction']['reconstructed_stages'] for parent in parents),
        'all old canonical rows are read with exactly the 128 selected A1/B reconstructions')
    require(account['reconstruction_counts'] == sum_counts(parent['reconstruction']['reconstruction_counts'] for parent in parents)
        and close(account['reconstruction_cpu_seconds'],sum(parent['reconstruction']['cpu_seconds'] for parent in parents)),
        'actual new same-facts reconstruction work')
    for field in ('worker_cpu_seconds','compiler_cpu_seconds'):
        key = 'cpu_seconds' if field == 'worker_cpu_seconds' else field
        require(close(account[field],sum(parent[key] for parent in parents)), 'actual '+field+' aggregate')
    return economic


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(document['schema'] == 'acfqp.history_control.v304' and document['status'] == 'EXPERIMENT_COMPLETE',
        'complete V304 history-control terminal document')
    equal_tree(settings,json_file(directory/'configuration.json'), 'unchanged pre-run V304 configuration')
    expected = dict(lifecycles=list(range(64)),parents=4,arms=list(ARMS),retained_stages=['A1','B'],true_p_four=.5,
        fit_fraction=.8,alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        seed_evaluation=303900100000,evaluation_games=32,max_steps=8192,bootstrap_draws=20000,bootstrap_seed=30400001,
        primary=PRIMARY,initialization='ORIGINAL_SOURCE_FOR_ALL_HEADS_WITH_A1_ONLY_IN_HISTORY_ARMS',
        representation='UNCHANGED_V301_LOCAL_AND_V290_MC',model_probability='UNCHANGED_V303_OBSERVED_B_FIT_PREFIX',
        observations='RETAINED_V303_B_MATCHED_WITH_ADDITIONAL_A1_ONLY_FOR_HISTORY_ARMS',
        interval_scope=INTERVAL_SCOPE,new_training_acquisitions=0,new_evaluation_games=8192,reused_source_games=2048,
        stop_rule='NO_HISTORY_OR_BUDGET_TUNING_ON_THIS_FIXED_COHORT')
    for key,value in expected.items():
        require(settings[key] == value, 'registered matched-history V304 '+key)
    old = json_file(settings['source_summary']); old_audit = json_file(Path(settings['source_summary']).with_name('audit.json'))
    require(old['schema'] == 'acfqp.continual.v303' and old_audit['status'] == 'PASS' and old_audit['independent_valid'],
        'settled V303 complete canonical-world and source control audit')
    require(document['source_provenance'] == old['source_provenance'], 'same original frozen sources and learned dynamics')
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64))
        and all(life['parent'] == life['lifecycle']%4 for life in lives), 'all 64 retained paired A1/B lifecycles')
    records = []; updates = Counter(); cutoffs = 0
    for life,previous in zip(lives,old['by_lifecycle']):
        record,chain,ncutoffs = check_lifecycle(life,previous)
        records.append(record); updates.update(chain); cutoffs += ncutoffs
    check_result_summary(document['summary'],records,lives,cutoffs)
    economic = check_accounting(document,old,old_audit)
    return dict(status='PASS',independent_valid=True,lifecycles=64,fixed_source_parents=4,
        retained_stage_histories=128,new_training_environment_observations=0,
        new_evaluation_games=8192,reused_evaluation_games=2048,distinct_evaluation_seed_conditions=2048,
        evaluation_cutoffs=cutoffs,processed_training_samples=dict(updates),economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates',0) for arm in ARMS},
        primary_history_penalty_supported=document['summary']['primary_history_penalty_supported'],
        history_negative_transfer_supported=document['summary']['history_negative_transfer_supported'],
        fresh_b_gain_supported=document['summary']['fresh_b_gain_supported'],
        history_diagnosis=document['summary']['history_diagnosis'],
        primary_utility=document['summary']['paired_contrasts'][PRIMARY],historical_total_compute_closed=False,
        method='Exact retained A1/B facts and B beliefs, full inherited A1/B fit and B heldout/game reproduction, '
            'unchanged complete B target/normalization work, paired terminal game counts, independent signed means and costs.',
        limitations='V303 physical-world audit is inherited without rereading canonical worlds. '
            'No value-weight replay or new bootstrap draws; saved intervals are checked for scope and feasible range. '
            'This is a retained-data diagnosis, not independent confirmation. B exposure is matched; total history differs. '
            'Historical interrupted V303 CPU remains unavailable.',errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    directory = parser.parse_args().output
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
