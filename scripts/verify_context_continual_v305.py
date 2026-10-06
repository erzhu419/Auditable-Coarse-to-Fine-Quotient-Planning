#!/usr/bin/env python3
"""Independent observed-context parameter-bank audit on the retained V303 worlds."""
import argparse
from collections import Counter
import json
from math import lgamma
from pathlib import Path
from statistics import mean

from verify_continual_v303 import check_belief, check_evaluation, check_local_fit
from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_history_control_v304 import scientific_receipt
from verify_split_risk_v301 import COMPONENT_METRICS, check_representation, check_split_heldout, nonpeak

ARMS = ('SOURCE', 'SHARED_LOCAL', 'CONTEXT_LOCAL')
STAGES = ('A1', 'B', 'A2')
CELLS = ('A1_A', 'B_A', 'B_B', 'A2_A', 'A2_B')
PAIRS = (('CONTEXT_LOCAL', 'SOURCE'), ('SHARED_LOCAL', 'SOURCE'), ('CONTEXT_LOCAL', 'SHARED_LOCAL'))
CHECKPOINTS = dict(A_after_B=('B_A', 'A1_A'), B_after_A2=('A2_B', 'B_B'),
    A_restore_after_A2=('A2_A', 'B_A'), A_final_vs_A1=('A2_A', 'A1_A'))
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_HISTORIES'
PRIMARY = 'CONTEXT_LOCAL_minus_SHARED_LOCAL_FINAL_AB'


def check_inventory(current, previous):
    require(current['lifecycle'] == previous['lifecycle'] and current['parent'] == previous['parent'],
        'retained continual lifecycle/source membership')
    require(set(current['stages']) == set(STAGES) and current['evaluation_beliefs'] == previous['evaluation_beliefs'],
        'same three retained stages and original observed task beliefs')
    for stage in STAGES:
        value, old = current['stages'][stage], previous['stages'][stage]
        require(value['dataset'] == old['dataset'] and value['fit_snapshot'] == old['fit_snapshot'],
            'same chronological complete factual inventory and FIT-only snapshot')
        check_belief(value['fit_snapshot'], value['dataset'])
    check_belief(current['evaluation_beliefs']['A'], current['stages']['A1']['dataset'])
    check_belief(current['evaluation_beliefs']['B'], current['stages']['B']['dataset'])


def check_reused_arm(current, previous, old_arm):
    require(not current['evaluation_is_new'] and not current['heldout_is_new'],
        'original SOURCE and SHARED_LOCAL diagnostics are reused without new physical work')
    saved = {key: value for key, value in current.items() if key not in ('evaluation_is_new', 'heldout_is_new')}
    require(saved == previous['arms'][old_arm],
        'reused full V303 arm receipts remain unchanged including fitting and diagnostics')


def check_new_local(value, previous, stage, reference_mc):
    data = previous['dataset']; fit = value['fit']
    samples = check_local_fit(fit, reference_mc, data, stage)
    require(value['parameters_retained'] and value['processed_training_samples'] == samples
        and value['evaluation_is_new'] and value['heldout_is_new'],
        'CONTEXT fits retained complete games and computes new heldout and evaluation diagnostics')
    check_split_heldout(value['heldout'], previous['arms']['SOURCE']['heldout'], data, 'LOCAL_RISK')
    return samples


def check_new_head(setup):
    counts = setup['setup_counts']; size = counts['source_parameters_copied']
    require(not setup['source_weights_shared'] and counts['source_weight_bytes_copied'] == 8*size
        and counts['initialized_zero_risk_parameters'] == size
        and counts['allocated_weight_parameters'] == 2*size
        and counts['allocated_weight_bytes'] == setup['private_weight_bytes'] == 16*size,
        'each created context copies original SOURCE reward weights and initializes zero risk logits exactly once')


def check_anchor(value, original, message):
    equal_tree(scientific_receipt(value['fit']), scientific_receipt(original['fit']), message+' fit')
    equal_tree(scientific_receipt(value['heldout']), scientific_receipt(original['heldout']), message+' heldout')


def check_equal_evaluation(value, original, message):
    equal_tree(scientific_receipt(value), scientific_receipt(original), message)


def observed_statistics(memory):
    modules, pending = memory['modules'], memory['pending']
    observations = sum(module['alpha']+module['beta']-2 for module in modules)+pending['n']
    fours = sum(module['alpha']-1 for module in modules)+pending['fours']
    require(observations == memory['observations_seen'] and 0 <= fours <= observations,
        'FIT statistics include every observed module and the uncommitted raw-rank prefix')
    return dict(observations=observations, fours=fours)


def log_beta(fours, observations):
    return lgamma(1+fours)+lgamma(1+observations-fours)-lgamma(2+observations)


def route_scores(statistics, prototypes):
    n, k = statistics['observations'], statistics['fours']
    return [dict(context_id=value['context_id'], log_bayes_factor=
        log_beta(k+value['fours'], n+value['observations'])
        -log_beta(value['fours'], value['observations'])-log_beta(k, n)) for value in prototypes]


def check_training_route(route, memory, prototypes):
    statistics = observed_statistics(memory); scores = route_scores(statistics, prototypes)
    equal_tree(route['statistics'], statistics, 'training route uses complete observed FIT-prefix counts only')
    equal_tree(route['scores'], scores, 'context decisions use independent Beta(1,1) shared-versus-separate evidence')
    best = max(scores, key=lambda row:(row['log_bayes_factor'], -row['context_id'])) if scores else None
    created = best is None or best['log_bayes_factor'] < 0.
    context_id = len(prototypes) if created else best['context_id']
    require(route['created'] == created and route['context_id'] == context_id,
        'negative best evidence creates a context and nonnegative evidence reuses the lowest-ID best context')
    before = None if created else dict(prototypes[context_id])
    require(route['prototype_before'] == before, 'only the selected prior observed prototype is consulted')
    after = dict(context_id=context_id, observations=statistics['observations'], fours=statistics['fours'], visits=1)
    if before is not None:
        after.update(observations=before['observations']+statistics['observations'],
            fours=before['fours']+statistics['fours'], visits=before['visits']+1)
    require(route['prototype_after'] == after, 'the selected prototype receives this FIT-prefix observation once')
    if created:
        prototypes.append(after)
    else:
        prototypes[context_id] = after
    return context_id, created


def check_evaluation_route(route, belief, prototypes):
    statistics = observed_statistics(belief['memory']); scores = route_scores(statistics, prototypes)
    equal_tree(route['statistics'], statistics, 'evaluation uses the original frozen observed task FIT-prefix counts')
    equal_tree(route['scores'], scores, 'evaluation scores all existing observed prototypes without updating them')
    best = max(scores, key=lambda row:(row['log_bayes_factor'], -row['context_id']))
    require(route['context_id'] == best['context_id'],
        'readonly evaluation selects the highest-evidence existing context with lowest-ID ties')
    return best['context_id']


def check_context_updates(row, updates, context_id, samples):
    require(row['context_updates_before'] == {str(i):value for i, value in enumerate(updates)},
        'all context update counters preserve previous active and inactive histories')
    expected = list(updates); expected[context_id] += samples
    require(row['context_updates_after'] == {str(i):value for i, value in enumerate(expected)},
        'only the selected context receives the current complete FIT samples')
    updates[:] = expected


def check_router_counts(current):
    routes = []; modules = 0
    for stage in STAGES:
        row = current['stages'][stage]
        routes.append(row['context_route'])
        modules += len(row['dataset']['fit_memory']['modules'])
        for task, route in row['evaluation_routes'].items():
            routes.append(route); modules += len(current['evaluation_beliefs'][task]['memory']['modules'])
    candidates = sum(len(route['scores']) for route in routes)
    expected = dict(statistics_module_visits=modules, statistics_parameter_reads=2*modules,
        statistics_pending_reads=2*len(routes), statistics_extractions=len(routes),
        log_beta_evaluations=3*candidates, lgamma_evaluations=9*candidates,
        candidate_scores=candidates, score_comparisons=sum(max(0, len(route['scores'])-1) for route in routes),
        context_creations=len(current['context_bank']['banks']), observe_calls=3, prototype_commits=3, select_calls=5)
    require(Counter(current['context_bank']['counts']) == Counter(expected),
        'actual observed-statistic extraction beta scoring and readonly selection work remains paid')


def check_lifecycle(current, previous, fresh_b):
    check_inventory(current, previous)
    prototypes = []; updates = []; setups = []; cells = {}; cutoffs = 0
    evaluation_routes = {}; training_routes = {}
    for stage in STAGES:
        row, old = current['stages'][stage], previous['stages'][stage]
        require(set(row['arms']) == set(ARMS), 'all three original shared and context arms remain present')
        context_id, created = check_training_route(row['context_route'], row['dataset']['fit_memory'], prototypes)
        training_routes[stage] = context_id
        context = row['arms']['CONTEXT_LOCAL']
        if created:
            updates.append(0)
        reference_mc = fresh_b['arms']['MC_FRESH_B']['fit_by_stage']['B'] if stage == 'B' and created else old['arms']['MC']['fit']
        samples = check_new_local(context, old, 'A1' if stage == 'A1' else stage, reference_mc)
        require(context['head_updates_before'] == updates[context_id]
            and context['head_updates_after'] == updates[context_id]+samples,
            'selected context preserves its own update history while inactive contexts receive no fit')
        check_context_updates(row, updates, context_id, samples)
        if stage == 'A1':
            check_anchor(context, old['arms']['LOCAL_RISK'], 'first context reproduces V303 original-SOURCE A1')
        elif stage == 'B' and created:
            anchor = dict(fit=fresh_b['arms']['LOCAL_FRESH_B']['fit_by_stage']['B'],
                heldout=fresh_b['arms']['LOCAL_FRESH_B']['heldout'])
            check_anchor(context, anchor, 'new B context reproduces V304 SOURCE-initialized B')
        tasks = ('A',) if stage == 'A1' else ('A', 'B')
        require(set(row['evaluation_routes']) == set(tasks) and set(context['evaluations']) == set(tasks),
            'explicit observed context routes cover every registered checkpoint task')
        for task in tasks:
            evaluation_routes[(stage, task)] = check_evaluation_route(
                row['evaluation_routes'][task], current['evaluation_beliefs'][task], prototypes)
            cells[stage+'_'+task] = dict(arms={})
        for arm in ARMS:
            value = row['arms'][arm]
            if arm != 'CONTEXT_LOCAL':
                check_reused_arm(value, old, 'SOURCE' if arm == 'SOURCE' else 'LOCAL_RISK')
            require(set(value['evaluations']) == set(tasks), 'all arms retain the same five checkpoint/task cells')
            for task in tasks:
                evaluation = value['evaluations'][task]
                endpoint_row = check_evaluation(evaluation, current['lifecycle'], task, current['evaluation_beliefs'][task])
                if arm != 'SOURCE':
                    check_representation(evaluation['representation_counts'], 'LOCAL_RISK',
                        evaluation['counts']['planning'].get('value_predictions', 0))
                cells[stage+'_'+task]['arms'][arm] = endpoint_row; cutoffs += endpoint_row['cutoffs']
        if stage == 'A1':
            check_equal_evaluation(context['evaluations']['A'], old['arms']['LOCAL_RISK']['evaluations']['A'],
                'first A context reproduces all V303 A1 terminal games')
        elif stage == 'B' and created and evaluation_routes[(stage, 'B')] == context_id:
            check_equal_evaluation(context['evaluations']['B'], fresh_b['arms']['LOCAL_FRESH_B']['evaluation'],
                'new B context reproduces all V304 fresh-B terminal games')
    banks = current['context_bank']['banks']
    require(len(banks) == len(prototypes) and [bank['context_id'] for bank in banks] == list(range(len(prototypes))),
        'actual context growth is retained without imposing a two-context answer')
    for bank, prototype, count in zip(banks, prototypes, updates):
        require({key:bank[key] for key in prototype} == prototype and bank['head_updates'] == count,
            'final context prototypes and independent per-context updates reproduce all selected fits')
        check_new_head(bank['head_setup']); setups.append(bank['head_setup'])
    private = sum(setup['private_weight_bytes'] for setup in setups)
    require(current['context_bank']['private_weight_bytes'] == current['context_bank']['peak_private_weight_bytes'] == private,
        'all retained context heads contribute their allocation and peak memory cost')
    check_router_counts(current)
    if training_routes['B'] != training_routes['A1'] and evaluation_routes[('B', 'A')] == evaluation_routes[('A1', 'A')]:
        check_equal_evaluation(current['stages']['B']['arms']['CONTEXT_LOCAL']['evaluations']['A'],
            current['stages']['A1']['arms']['CONTEXT_LOCAL']['evaluations']['A'],
            'inactive A context retains exact A1 actions and terminal outcomes after B')
    if training_routes['A2'] != training_routes['B'] and evaluation_routes[('A2', 'B')] == evaluation_routes[('B', 'B')]:
        check_equal_evaluation(current['stages']['A2']['arms']['CONTEXT_LOCAL']['evaluations']['B'],
            current['stages']['B']['arms']['CONTEXT_LOCAL']['evaluations']['B'],
            'inactive B context retains exact B actions and terminal outcomes after A2')
    return dict(lifecycle=current['lifecycle'], parent=current['parent'], cells=cells), sum(updates), cutoffs


def check_contrast(saved, values):
    require(len(values) == 64 and close(saved['mean'], mean(values)), 'all signed paired continual lifecycle means')
    equal_tree(saved['lifecycle_deltas'], {str(i): value for i, value in enumerate(values)},
        'all adverse paired context histories remain retained')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent): mean(group) for parent, group in enumerate(groups)},
        'four frozen-parent paired means')
    low, high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE
        and mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'saved interval remains conditional on retained histories and four frozen parents')
    require(saved['improved_equal_worse'] == [sum(v > 0. for v in values), sum(v == 0. for v in values), sum(v < 0. for v in values)]
        and saved['adverse_lifecycles'] == [i for i, value in enumerate(values) if value < 0.],
        'negative context effects are reported without filtering')


def endpoint(records, cell, arm):
    return [row['cells'][cell]['arms'][arm]['mean_game_utility'] for row in records]


def check_support(summary, cutoffs):
    complete = cutoffs == 0
    supported = complete and summary['final_ab_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL']['ci95'][0] > 0.
    final_tasks = {task: complete
        and summary['cells']['A2_'+task]['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95'][0] > 0.
        for task in ('A', 'B')}
    retention = {}
    for name in ('A_after_B', 'B_after_A2', 'A_final_vs_A1'):
        low, high = summary['checkpoint_contrasts'][name]['CONTEXT_LOCAL']['ci95']
        retention[name] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else 'SUPPORTED_NONDECREASE' if low >= 0.
            else 'SUPPORTED_LOSS' if high < 0. else 'UNRESOLVED')
    require(summary['complete_game_endpoints'] == complete and summary['primary_repair_supported'] == supported
        and summary['primary_repair_status'] == ('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        'repair over shared parameters remains separate from a gain over original SOURCE')
    require(summary['final_task_gain_supported'] == final_tasks
        and summary['final_dual_task_gain_supported'] == all(final_tasks.values()),
        'both individual final task gains are required for the dual-task claim')
    require(summary['retention_status'] == retention and summary['retained_gain_supported']
        == all(status == 'SUPPORTED_NONDECREASE' for status in retention.values()),
        'zero-crossing retention intervals do not establish preservation')
    require(summary['a_restoration_supported'] == (complete
        and summary['checkpoint_contrasts']['A_restore_after_A2']['CONTEXT_LOCAL']['ci95'][0] > 0.),
        'positive restoration and nondecreasing retention are different claims')


def check_result_summary(summary, records, lives, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all three arms five checkpoint terminal-game aggregates')
    require(summary['primary_contrast'] == PRIMARY and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_seed'] == 30500001
        and summary['estimator'] == 'EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        'frozen final equal-task context-versus-shared structural-repair primary')
    require(set(summary['cells']) == set(CELLS), 'all five checkpoint/task cells remain retained')
    for cell in CELLS:
        saved = summary['cells'][cell]; stage, task = cell.split('_')
        require(saved['stage'] == stage and saved['task'] == task, 'registered checkpoint task identity')
        for arm in ARMS:
            values = [row['cells'][cell]['arms'][arm] for row in records]
            expected = dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
                **{key:sum(value[key] for value in values) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})
            equal_tree(saved['arms'][arm], expected, 'whole-game then lifecycle utility '+cell+' '+arm)
        require(set(saved['paired_contrasts']) == {a+'_minus_'+b for a, b in PAIRS},
            'context repair and original SOURCE contrasts remain separate')
        for left, right in PAIRS:
            check_contrast(saved['paired_contrasts'][left+'_minus_'+right],
                [a-b for a, b in zip(endpoint(records, cell, left), endpoint(records, cell, right))])
    for left, right in PAIRS:
        differences = [{cell:row['cells'][cell]['arms'][left]['mean_game_utility']
            -row['cells'][cell]['arms'][right]['mean_game_utility'] for cell in CELLS} for row in records]
        check_contrast(summary['final_ab_contrasts'][left+'_minus_'+right],
            [(value['A2_A']+value['A2_B'])/2 for value in differences])
        check_contrast(summary['current_task_sequence_contrasts'][left+'_minus_'+right],
            [mean(value[cell] for cell in ('A1_A', 'B_B', 'A2_A')) for value in differences])
    require(set(summary['checkpoint_contrasts']) == set(CHECKPOINTS), 'all signed retention and restoration comparisons')
    for name, (after, before) in CHECKPOINTS.items():
        for arm in ARMS:
            check_contrast(summary['checkpoint_contrasts'][name][arm],
                [a-b for a, b in zip(endpoint(records, after, arm), endpoint(records, before, arm))])
    for arm in ARMS:
        values = [row['cells'][cell]['arms'][arm] for row in records for cell in CELLS]
        expected = {key:sum(value[key] for value in values) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')}
        expected['mean_final_ab_game_utility'] = mean(mean(row['cells'][cell]['arms'][arm]['mean_game_utility']
            for cell in ('A2_A', 'A2_B')) for row in records)
        expected['mean_current_task_sequence_game_utility'] = mean(mean(row['cells'][cell]['arms'][arm]['mean_game_utility']
            for cell in ('A1_A', 'B_B', 'A2_A')) for row in records)
        equal_tree(summary['arms'][arm], expected, 'complete five-cell utility and physical endpoint inventory '+arm)
    require(set(summary['heldout_by_stage']) == set(STAGES), 'all stage heldout diagnostics remain descriptive')
    for stage in STAGES:
        for arm in ARMS:
            values = [life['stages'][stage]['arms'][arm]['heldout'] for life in lives]
            expected = dict(games=sum(len(value['game_metrics']) for value in values),
                samples=sum(game['count'] for value in values for game in value['game_metrics']),
                **{key:mean(mean(game[key] for game in value['game_metrics']) for value in values)
                    for key in ('bias', 'mse', 'mae')})
            if arm != 'SOURCE':
                expected['components'] = {key:mean(mean(game[key] for game in value['component_game_metrics'])
                    for value in values) for key in COMPONENT_METRICS}
            equal_tree(summary['heldout_by_stage'][stage][arm], expected, 'complete heldout game weighting '+stage+' '+arm)
    check_support(summary, cutoffs)


def check_training_budget(account, old):
    require(account['new_training_environment_observations'] == account['physical_acquisitions'] == 0,
        'retained continual observations create no new training acquisition')
    raw = {stage: sum(life['stages'][stage]['acquisition']['warmup']['raw_tiles']
        +life['stages'][stage]['acquisition']['training']['raw_tiles'] for life in old['by_lifecycle']) for stage in STAGES}
    require(account['inherited_raw_tiles_by_stage'] == raw,
        'all original three-stage warmups actor raw and unfinished tails remain paid')
    inherited = old['accounting']['inherited_costs_per_arm']['SOURCE']
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+sum(raw.values())
    require(account['economic_training_raw_tiles_per_arm'] == dict.fromkeys(ARMS, economic)
        and account['inherited_costs_per_arm'] == dict.fromkeys(ARMS, inherited),
        'every arm pays the original SOURCE dynamics and full observed three-stage sequence')
    require(account['historical_sequence_physical_training_raw_tiles_lower_bound']
        == old['recovery']['training_raw_tiles_physical_lower_bound'] and not account['historical_total_compute_closed'],
        'original interrupted sequence costs are retained without inventing unavailable historical CPU')
    return economic


def check_accounting(document, old, old_audit):
    account = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    economic = check_training_budget(account, old)
    stages = [life['stages'][stage] for life in lives for stage in STAGES]
    values = [row['arms']['CONTEXT_LOCAL'] for row in stages]
    evaluations = [evaluation for value in values for evaluation in value['evaluations'].values()]
    banks = [bank for life in lives for bank in life['context_bank']['banks']]
    reused = sum(len(evaluation['game_summaries']) for row in stages for arm in ('SOURCE', 'SHARED_LOCAL')
        for evaluation in row['arms'][arm]['evaluations'].values())
    require(account['new_evaluation_games'] == 10240 == sum(len(value['game_summaries']) for value in evaluations)
        and account['reused_evaluation_games'] == 20480 == reused,
        'new CONTEXT games and reused SOURCE/SHARED games have separate physical work inventories')
    samples = sum(value['processed_training_samples'] for value in values)
    require(account['new_processed_training_samples'] == dict(SOURCE=0, SHARED_LOCAL=0, CONTEXT_LOCAL=samples)
        and samples == sum(bank['head_updates'] for bank in banks),
        'only newly fitted CONTEXT samples accrue actual new learning work')
    require(account['total_contexts_created'] == len(banks)
        and account['contexts_per_lifecycle'] == {str(life['lifecycle']):len(life['context_bank']['banks']) for life in lives},
        'all actual context growth including fragmentation is retained')
    require(account['context_private_weight_bytes_created'] == sum(bank['head_setup']['private_weight_bytes'] for bank in banks)
        and account['peak_context_private_weight_bytes_per_lifecycle']
        == max(life['context_bank']['peak_private_weight_bytes'] for life in lives)
        and account['inherited_shared_private_weight_bytes_per_lifecycle']
        == max(life['head_setup']['LOCAL_RISK']['private_weight_bytes'] for life in old['by_lifecycle'])
        and account['context_head_setup_counts'] == sum_counts(bank['head_setup']['setup_counts'] for bank in banks),
        'new context capacity and original shared capacity have explicit allocation and peak memory costs')
    require(account['context_router_counts'] == sum_counts(life['context_bank']['counts'] for life in lives)
        and close(account['context_router_cpu_seconds'], sum(life['context_bank']['route_cpu_seconds'] for life in lives)),
        'all new observed-context routing operations and actual CPU remain paid')
    fields = (('fit_counts', 'fit', 'learning_counts'), ('fit_target_counts', 'fit', 'target_counts'),
        ('fit_normalization_counts', 'fit', 'normalization_counts'), ('fit_representation_counts', 'fit', 'representation_counts'),
        ('fit_setup_counts', 'fit', 'setup_counts'), ('heldout_prediction_counts', 'heldout', 'prediction_counts'),
        ('heldout_target_counts', 'heldout', 'target_counts'), ('heldout_representation_counts', 'heldout', 'representation_counts'),
        ('heldout_setup_counts', 'heldout', 'setup_counts'))
    for field, section, key in fields:
        rows = [value[section].get(key, {}) for value in values]
        require(account[field] == sum_counts(nonpeak(row) for row in rows), 'actual new CONTEXT '+field)
        peaks = {name:max(row.get(name, 0) for row in rows)
            for name in {name for row in rows for name in row if name.endswith('_peak')}}
        require(account[field+'_buffer_peaks'] == peaks, 'actual new CONTEXT '+field+' buffer peaks')
    for section in ('fit', 'heldout'):
        require(close(account['processing_cpu_seconds'][section], sum(value[section]['cpu_seconds'] for value in values)),
            'actual new CONTEXT '+section+' CPU excludes reused controls')
    require(close(account['processing_cpu_seconds']['head_setup'], sum(bank['head_setup']['setup_cpu_seconds'] for bank in banks)),
        'each created context initialization CPU is counted once')
    for kind in ('environment', 'planning'):
        require(account['new_evaluation_counts'][kind] == sum_counts(value['counts'][kind] for value in evaluations),
            'actual new context '+kind+' evaluation work excludes reused controls')
    require(account['new_evaluation_representation_counts'] == sum_counts(value['representation_counts'] for value in evaluations)
        and account['new_evaluation_setup_counts'] == sum_counts(value['setup_counts'] for value in evaluations)
        and close(account['new_evaluation_cpu_seconds'], sum(value['cpu_seconds'] for value in evaluations)),
        'all new context evaluation representation setup and CPU work is paid')
    require([parent['parent'] for parent in parents] == list(range(4)), 'four original SOURCE parent loads')
    for parent in parents:
        require(parent['lifecycle_ids'] == list(range(parent['parent'], 64, 4))
            and parent['source_setup']['checkpoint_loads'] == 1 and parent['source_setup']['new_leaf_updates'] == 0
            and parent['reconstruction']['reconstructed_stages'] == 48,
            'each original SOURCE supplies exactly sixteen retained three-stage sequences')
    require(account['retained_canonical_trace_bytes'] == old['accounting']['canonical_trace_bytes']
        and account['canonical_rows_read'] == old_audit['canonical_rows']
        == sum(parent['reconstruction']['canonical_rows_read'] for parent in parents)
        and account['reconstructed_stages'] == 192
        == sum(parent['reconstruction']['reconstructed_stages'] for parent in parents),
        'all original complete stage facts are reconstructed once without new acquisition')
    require(account['reconstruction_counts'] == sum_counts(parent['reconstruction']['counts'] for parent in parents)
        and close(account['reconstruction_cpu_seconds'], sum(parent['reconstruction']['cpu_seconds'] for parent in parents)),
        'actual new retained-fact reconstruction work and CPU')
    for field in ('worker_cpu_seconds', 'compiler_cpu_seconds'):
        key = 'cpu_seconds' if field == 'worker_cpu_seconds' else field
        require(close(account[field], sum(parent[key] for parent in parents)), 'actual new '+field+' aggregate')
    return economic


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(document['schema'] == 'acfqp.context_continual.v305' and document['status'] == 'EXPERIMENT_COMPLETE',
        'complete observed-context persistent-head experiment terminal document')
    equal_tree(settings, json_file(directory/'configuration.json'), 'unchanged pre-run V305 configuration')
    expected = dict(lifecycles=list(range(64)), parents=4, arms=list(ARMS), stages=list(STAGES), fit_fraction=.8, alpha=.0025,
        query=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.),
        representation='UNCHANGED_V301_LOCAL_PERSISTENT_OBSERVED_CONTEXT_BANKS',
        router='BETA_1_1_SAME_VERSUS_DISJOINT_LOG_BAYES_FACTOR', log_bayes_factor_threshold=0.,
        context_statistics='ALL_OBSERVED_FIT_PREFIX_SPAWNS_FROM_MODULES_AND_PENDING',
        context_update='COMMIT_FIT_PREFIX_ONCE_WITHOUT_TASK_OR_STAGE_LABELS',
        context_initialization='ORIGINAL_SOURCE_REWARD_AND_ZERO_RISK',
        evaluation_routing='MAX_EXISTING_BAYES_FACTOR_WITHOUT_PROTOTYPE_UPDATES',
        planning_probability='UNCHANGED_V303_FIRST_OBSERVED_TASK_BELIEF',
        observations='ALL_RETAINED_V303_A1_B_A2_WITHOUT_NEW_TRAINING_ACQUISITION',
        evaluation_cells=list(CELLS), seed_evaluation=303900000000, evaluation_task_offset=100000,
        evaluation_games_per_cell=32, max_steps=8192, primary=PRIMARY, bootstrap_draws=20000, bootstrap_seed=30500001,
        interval_scope=INTERVAL_SCOPE, new_training_acquisitions=0, new_evaluation_games=10240, reused_evaluation_games=20480,
        stop_rule='NO_ROUTING_TARGET_ALPHA_OR_SEED_TUNING_ON_THIS_RETAINED_SEQUENCE')
    for key, value in expected.items():
        require(settings[key] == value, 'registered observed-context V305 '+key)
    old = json_file(settings['source_summary']); fresh = json_file(settings['history_summary'])
    old_audit = json_file(Path(settings['source_summary']).with_name('audit.json'))
    fresh_audit = json_file(Path(settings['history_summary']).with_name('audit.json'))
    require(old['schema'] == 'acfqp.continual.v303' and fresh['schema'] == 'acfqp.history_control.v304'
        and old_audit['status'] == fresh_audit['status'] == 'PASS'
        and old_audit['independent_valid'] and fresh_audit['independent_valid'],
        'settled V303 complete canonical worlds and V304 same-facts fresh-B reference audits')
    require(fresh['settings']['source_summary'] == settings['source_summary']
        and document['source_provenance'] == old['source_provenance'] == fresh['source_provenance'],
        'context repairs inherit the same original SOURCE dynamics and factual sequence')
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64))
        and all(life['parent'] == life['lifecycle']%4 for life in lives), 'all 64 retained paired continual lifecycles')
    records = []; updates = 0; cutoffs = 0
    for life, previous, fresh_b in zip(lives, old['by_lifecycle'], fresh['by_lifecycle']):
        record, fitted, ncutoffs = check_lifecycle(life, previous, fresh_b)
        records.append(record); updates += fitted; cutoffs += ncutoffs
    check_result_summary(document['summary'], records, lives, cutoffs)
    economic = check_accounting(document, old, old_audit)
    return dict(status='PASS', independent_valid=True, lifecycles=64, fixed_source_parents=4,
        retained_stage_histories=192, new_training_environment_observations=0,
        new_evaluation_games=10240, reused_evaluation_games=20480, distinct_evaluation_seed_conditions=4096,
        evaluation_cutoffs=cutoffs, new_processed_training_samples=updates,
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS, economic),
        total_contexts_created=document['accounting']['total_contexts_created'],
        context_private_weight_bytes_created=document['accounting']['context_private_weight_bytes_created'],
        actual_new_parameter_writes=document['accounting']['fit_counts'].get('table_updates', 0),
        primary_repair_supported=document['summary']['primary_repair_supported'],
        final_task_gain_supported=document['summary']['final_task_gain_supported'],
        final_dual_task_gain_supported=document['summary']['final_dual_task_gain_supported'],
        retention_status=document['summary']['retention_status'], retained_gain_supported=document['summary']['retained_gain_supported'],
        primary_utility=document['summary']['final_ab_contrasts']['CONTEXT_LOCAL_minus_SHARED_LOCAL'],
        historical_total_compute_closed=False,
        method='Independent all-observed FIT statistics and Beta context routing, readonly evaluation routing, '
            'per-context update chains and allocation, unchanged V303 controls and V304 fresh-B numerical anchors, '
            'complete terminal-game work, signed paired means, retention claims and actual new costs.',
        limitations='V303 canonical-world integrity and V304 fresh-B controls are inherited without rereading raw worlds. '
            'No value-weight replay or new bootstrap draws; saved intervals are checked for scope and feasible range. '
            'This retained-data diagnosis changes context conditioning and parameter capacity together. '
            'Batch-boundary routing does not establish blind online task discovery or independent confirmation. '
            'Historical interrupted V303 CPU remains unavailable.', errors=[])


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
