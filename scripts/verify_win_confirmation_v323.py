#!/usr/bin/env python3
"""Independent frozen WIN-only head and new execution-stream reader."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (HeadVersions, check_representation, close,
    equal_tree, json_file, physical_status, planning_counts, read_source_weights,
    require, sum_counts)
from verify_query_supervision_v319 import effect_status

TASKS = ('A', 'B')
ARMS = ('SOURCE', 'FIRST_LOCAL', 'WIN_ONLY')
PAIRS = (('WIN_ONLY', 'FIRST_LOCAL'), ('WIN_ONLY', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_EXISTING_SIXTEEN_FROZEN_HEADS_NEW_V323_STREAMS'


def evaluation_seed(life, task, episode):
    return 323900000000 + life*1000000 + TASKS.index(task)*100000 + episode


def check_candidate(item, first_version, source_weights, checkpoint, identity):
    """Read the actual saved candidate relative to FIRST; inherit old separation PASS."""
    receipt = item['head_version']
    require(receipt['arm'] == 'WIN_ONLY' and receipt['version'] == 1
        and receipt['updates'] == first_version['updates']
        and receipt['base_file'] == first_version['file'],
        'the actual frozen WIN_ONLY v1 remains relative to its own FIRST v0 without new fitting')
    first = HeadVersions(source_weights, checkpoint, identity, 'LOCAL_RISK')
    first.apply(first_version)
    candidate = HeadVersions(source_weights, checkpoint, identity, 'LOCAL_RISK')
    candidate.apply(first_version); candidate.apply(receipt)
    require(np.array_equal(candidate.reward, first.reward)
        and receipt['reward_indices_count'] == 0,
        'the complete candidate reward table remains exactly FIRST while the actual saved WIN delta is restored')
    require(item['assembly']['method'] == 'SAVED_COMPONENT_CROSSOVER_NO_FIT'
        and item['assembly']['reward_source'] == 'FIRST_LOCAL'
        and item['assembly']['win_source'] == 'NSTEP_QUERY'
        and item['assembly']['new_fit_updates'] == 0
        and item['assembly']['weights_frozen'],
        'the frozen candidate retains the already audited V322 component ownership and zero fitting')
    return first, candidate


def check_evaluation(value, life, task, belief, version):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2'
        and value['head_version'] == version and value['static_evaluation_valid'],
        'each new evaluation uses its actual immutable own head and FIRST bank belief')
    games = value['game_summaries']
    require(len(games) == 64 and [game['seed'] for game in games]
        == [evaluation_seed(life, task, episode) for episode in range(64)],
        'all sixty-four new paired V323 streams remain distinct from the selection evaluations')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'every new game keeps the frozen natural-game horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE',
                'an actual active cutoff remains explicit without an imputed terminal label')
            bonus = 0.
        else:
            require(game['status'] in ('WON', 'LOST')
                and physical_status(game['final_board']) == game['status'],
                'each natural endpoint agrees with its actual physical final board')
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048. + bonus,
            'new whole-game utility uses the actual score and terminal outcome')
    steps = sum(game['steps'] for game in games)
    wins = sum(game['status'] == 'WON' for game in games)
    expected = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=128,
        raw_tile_productions=steps+128, environment_random_draws=2*(steps+128),
        ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+64,
        ground_status_internal_swipe_calls=4*(steps+64-wins),
        ground_swipe_calls=steps+4*(steps+64-wins))
    require(Counter(value['counts']['environment']) == Counter(expected),
        'all new initial tiles actions and winning-action spawns are paid exactly once')
    planning_counts(value['counts']['planning'], steps, depth=2)
    if version is not None:
        check_representation(value['representation_counts'], 'LOCAL_RISK',
            value['counts']['planning'].get('value_predictions', 0))
    require(not value['counts'].get('learning', {}) and value['cpu_seconds'] >= 0.
        and value['seconds'] >= 0., 'new frozen evaluations retain actual paid timing and zero learning')
    return mean(game['utility'] for game in games)


def check_setups(setups, first_version, candidate_version, size):
    require(set(setups) == {'FIRST_LOCAL', 'CANDIDATE'},
        'each task restores one actual FIRST and one private saved candidate')
    for arm, setup in setups.items():
        c = setup['setup_counts']
        require(c['source_parameters_copied'] == size and c['source_weight_bytes_copied'] == 8*size
            and c['allocated_weight_parameters'] == 2*size and c['allocated_weight_bytes'] == 16*size
            and c['initialized_zero_risk_parameters'] == size and setup['private_weight_bytes'] == 16*size,
            'every actual head allocation retains its paid SOURCE initialization and two complete tables')
        require(setup['cpu_seconds'] >= 0. and setup['wall_seconds'] >= 0.,
            'actual restoration allocation timings remain present')
        if arm == 'FIRST_LOCAL':
            equal_tree(setup['restored_version'], first_version, 'FIRST restores its exact existing saved v0')
            require(setup['restore_cpu_seconds'] >= 0., 'the actual FIRST file read and restore cost is paid')
        else:
            require(c['first_parameters_copied'] == 2*size and c['first_weight_bytes_copied'] == 16*size,
                'the candidate begins with a complete copy of the actual restored FIRST tables')
            equal_tree(setup['restored_version'], candidate_version,
                'the candidate restores its actual saved WIN_ONLY sparse delta after FIRST')
            require(setup['delta_restore']['file'] == candidate_version['file']
                and setup['delta_restore']['cpu_seconds'] >= 0.
                and setup['delta_restore']['wall_seconds'] >= 0.,
                'exactly one actual WIN_ONLY delta read is paid without reassembly or new parameters')


def check_lifecycle(row, old, source_weights, checkpoint):
    life, parent = row['lifecycle'], row['parent']
    require(life == old['lifecycle'] and parent == old['parent'] == life % 4,
        'all sixteen previously learned lives retain their actual four frozen SOURCE parents')
    equal_tree(row['initial'], old['initial'], 'both actual FIRST versions and immutable task beliefs remain frozen')
    require(set(row['evaluations']) == set(TASKS) and set(row['frozen_candidate']) == set(TASKS),
        'both A and B task banks remain complete without candidate selection')
    means, counts = {}, Counter()
    for task in TASKS:
        initial = row['initial'][task]; item = row['frozen_candidate'][task]
        previous = old['cells'][task]['WIN_ONLY']
        equal_tree(item, {key: previous[key] for key in ('head_version', 'assembly')},
            'the candidate is the exact V322 saved head and assembly receipt rather than a newly chosen or rebuilt head')
        identity = dict(lifecycle=life, parent=parent, context_id=initial['context_id'], arm='WIN_ONLY')
        first, candidate = check_candidate(item, initial['head_version'], source_weights, checkpoint, identity)
        check_setups(row['head_setups'][task], initial['head_version'], item['head_version'], first.reward.size)
        evaluations = row['evaluations'][task]
        require(set(evaluations) == set(ARMS), 'all three arms receive new evaluation streams')
        means[task] = {}
        for arm in ARMS:
            version = None if arm == 'SOURCE' else initial['head_version'] if arm == 'FIRST_LOCAL' else item['head_version']
            value = evaluations[arm]
            means[task][arm] = check_evaluation(value, life, task,
                initial['planning_belief']['estimated_p_four'], version)
            counts.update(new_evaluation_games=64,
                new_evaluation_raw_tiles=value['counts']['environment']['raw_tile_productions'])
        counts.update(actual_FIRST_files_read=1, actual_candidate_files_read=1)
        del first, candidate
    return dict(lifecycle=life, parent=parent, cells=means), counts


def check_interval(value, values):
    require(len(values) == 16 and close(value['mean'], mean(values)),
        'paired execution effects retain all sixteen signed lifecycle means')
    equal_tree(value['lifecycle_values'], {str(i): number for i, number in enumerate(values)},
        'the paired vector retains every favorable equal and adverse lifecycle')
    equal_tree(value['parent_mean_values'], {str(p): mean(values[p::4]) for p in range(4)},
        'the execution effects retain all four actual fixed-parent means')
    require(value['positive_equal_negative'] == [sum(x > 0 for x in values), sum(x == 0 for x in values), sum(x < 0 for x in values)],
        'effect direction counts retain adverse lives')
    low, high = value['ci95']
    minimum, maximum = mean(min(values[p::4]) for p in range(4)), mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= low <= high <= maximum+1e-10
        and value['interval_scope'] == INTERVAL_SCOPE
        and value['status95'] == effect_status(value, True),
        'the interval range sign and scope describe only the existing cohort under new execution streams')


def check_analysis(summary, records, lives):
    cutoffs, actual = [], []
    for row, record in zip(lives, records):
        endpoints = {}
        for task in TASKS:
            endpoints[task] = {}
            for arm in ARMS:
                games = row['evaluations'][task][arm]['game_summaries']
                endpoints[task][arm] = {status: sum(game['status'] == status for game in games)
                    for status in ('WON', 'LOST', 'CUTOFF')}
                cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, arm=arm, seed=game['seed'])
                    for game in games if game['status'] == 'CUTOFF')
        actual.append(dict(record, retained_endpoint_counts=endpoints))
    equal_tree(summary['by_lifecycle'], actual, 'all three new arm means and endpoint counts remain in the retained cohort')
    complete = not cutoffs
    require(summary['primary_contrast'] == 'WIN_ONLY_minus_FIRST_LOCAL_FINAL_AB'
        and summary['physical_evaluation_games'] == 6144 and summary['fresh_evaluation_streams']
        and not summary['independent_learning_histories'] and summary['cutoffs'] == cutoffs
        and summary['complete_game_endpoints'] == complete and summary['bootstrap_executed'] == complete
        and summary['bootstrap_seed'] == 32300001 and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_unit'] == 'PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        'the sole own-FIRST primary uses new execution streams and any cutoff holds the entire cohort')
    names = {left+'_minus_'+right for left, right in PAIRS}
    require(set(summary['final_ab_contrasts']) == names and set(summary['task_contrasts']) == set(TASKS),
        'the frozen primary SOURCE controls and both tasks remain explicit')
    def view(values, tasks):
        require(set(values) == names, 'each contrast view retains all three fixed pairs')
        means = {arm: [mean(record['cells'][task][arm] for task in tasks) for record in records] for arm in ARMS}
        for left, right in PAIRS:
            name = left+'_minus_'+right
            vector = [a-b for a, b in zip(means[left], means[right])]
            if complete: check_interval(values[name], vector)
            else: require(values[name] is None, 'any cutoff suppresses every terminal-effect interval without imputation')
    view(summary['final_ab_contrasts'], TASKS)
    for task in TASKS: view(summary['task_contrasts'][task], (task,))
    primary = summary['final_ab_contrasts']['WIN_ONLY_minus_FIRST_LOCAL']
    equal_tree(summary['primary'], primary, 'the sole primary cannot be replaced with a favorable SOURCE comparison')
    primary_status = effect_status(primary, complete)
    retention = {task: effect_status(summary['task_contrasts'][task]['WIN_ONLY_minus_FIRST_LOCAL'], complete, True)
        for task in TASKS}
    expected = dict(primary_status=primary_status, primary_execution_gain_supported=primary_status == 'SUPPORTED_GAIN',
        task_retention_status=retention, retained_execution_gain_supported=primary_status == 'SUPPORTED_GAIN'
            and all(status == 'SUPPORTED_NONDECREASE' for status in retention.values()),
        final_net_gain_status=effect_status(summary['final_ab_contrasts']['WIN_ONLY_minus_SOURCE'], complete))
    equal_tree({key: summary[key] for key in expected}, expected,
        'own-FIRST gain and A/B nondecrease remain separate conditions; unresolved retention is not preservation')
    require(summary['secondary_interval_scope'] == 'NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM'
        and 'not an independent learning cohort' in summary['evidence_scope'],
        'new execution evidence keeps the existing learned cohort and nominal secondary limits')


def check_parent(source, rows, previous):
    weights = read_source_weights(source['checkpoint']); records = []; physical = Counter()
    for row in rows:
        record, counts = check_lifecycle(row, previous[row['lifecycle']], weights, source['checkpoint'])
        records.append(record); physical.update(counts)
        print(json.dumps(dict(event='independent_win_confirmation_life_checked', lifecycle=row['lifecycle'])), flush=True)
    return records, physical


def expected_configuration(source):
    return dict(schema='acfqp.win_confirmation_freeze.v323', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/WIN_CONFIRMATION_V323.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS), arms=list(ARMS),
        candidate='ACTUAL_V322_WIN_ONLY_V1_FIRST_REWARD_PLUS_SAVED_QUERY_WIN',
        candidate_selection='V322_NOMINAL_SECONDARY_DEVELOPMENT_SIGNAL_BEFORE_NEW_STREAMS',
        restore='ACTUAL_FIRST_V0_THEN_WIN_ONLY_V1_ABSOLUTE_SPARSE_WRITES_NO_NEW_VERSIONS',
        planning_belief='ACTUAL_IMMUTABLE_V322_FIRST_BANK_BELIEF', true_probabilities={'A': .1, 'B': .5},
        evaluation_games_per_cell=64, max_steps=8192, seed_evaluation=323900000000,
        fresh_evaluation_streams=True, paired_stream_reuse=False, expected_new_evaluation_games=6144,
        maximum_new_evaluation_raw_tiles=50343936, new_training_raw_tiles=0, new_fit_updates=0, new_head_files=0,
        primary='WIN_ONLY_minus_FIRST_LOCAL_FINAL_AB', bootstrap_draws=20000, bootstrap_seed=32300001,
        retention='BOTH_TASK_WIN_ONLY_MINUS_FIRST_CI_LOWER_NONNEGATIVE',
        stop_rule='ANY_NATURAL_GAME_CUTOFF_GLOBAL_HOLD_NO_REPLACEMENTS_QUOTA_EXTENSION_OR_CANDIDATE_CHANGE',
        independent_learning_histories=False, evidence_scope='FRESH_EXECUTION_VALIDATION_CONDITIONAL_ON_EXISTING_LEARNT_COHORT')


def check_accounting(document, inherited, diagnostic, physical, execution):
    account = document['accounting']; lives = document['by_lifecycle']
    evaluations = [row['evaluations'][task][arm] for row in lives for task in TASKS for arm in ARMS]
    per_arm = {arm: dict(new_evaluation_games=sum(len(row['evaluations'][task][arm]['game_summaries']) for row in lives for task in TASKS),
        environment_counts=sum_counts(row['evaluations'][task][arm]['counts']['environment'] for row in lives for task in TASKS),
        evaluation_cpu_seconds=sum(row['evaluations'][task][arm]['cpu_seconds'] for row in lives for task in TASKS)) for arm in ARMS}
    equal_tree(account['per_arm'], per_arm, 'all three policies pay their actual new natural game work')
    expected = dict(new_training_raw_tiles=0, new_fit_updates=0, new_head_files=0,
        source_training_repeated=False, first_adaptation_repeated=False, prior_full_audit_repeated=False,
        new_evaluation_games=sum(len(value['game_summaries']) for value in evaluations), reused_evaluation_games=0,
        new_evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        new_evaluation_planning_counts=sum_counts(value['counts']['planning'] for value in evaluations),
        split_evaluation_representation_counts=sum_counts(value['representation_counts'] for value in evaluations if 'representation_counts' in value),
        representation_scope='FIRST_AND_WIN_ONLY_SPLIT_HEADS_SOURCE_ONLY_HAS_PLANNING_COUNTS',
        new_evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations))
    equal_tree({key: account[key] for key in expected}, expected,
        'all new game counts compute and split-head costs reconcile; training version creation and old-game reuse remain zero')
    require(account['new_evaluation_games'] == physical['new_evaluation_games'] == 6144
        and account['new_evaluation_environment_counts']['raw_tile_productions'] == physical['new_evaluation_raw_tiles'] <= 50343936
        and physical['actual_FIRST_files_read'] == physical['actual_candidate_files_read'] == 32,
        'all physical game work and actual saved head reads retain the frozen new raw bound')
    require([row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'all four frozen-parent workers remain present')
    worker = sum(row['cpu_seconds'] for row in document['parent_receipts'])
    compiler = sum(row['compiler_cpu_seconds'] for row in document['parent_receipts'])
    require(close(account['worker_cpu_seconds'], worker) and close(account['compiler_cpu_seconds'], compiler)
        and close(account['new_experiment_component_cpu_seconds'], worker+compiler+account['coordinator_cpu_seconds'])
        and close(account['inherited_successful_source_v317_v319_v321_v322_full_cpu_seconds'], inherited)
        and close(account['economic_source_v317_v319_v321_v322_and_experiment_component_cpu_seconds'], inherited+account['new_experiment_component_cpu_seconds'])
        and close(account['preceding_v320_diagnostic_full_cpu_seconds'], diagnostic),
        'restoration compiler worker coordinator and new evaluation cost is paid once; V320 diagnostic stays separate')
    require(execution['exit_code'] == 0 and execution['process_tree_cpu_seconds']+1e-6 >= account['new_experiment_component_cpu_seconds'],
        'full process-tree CPU includes final serialization and shutdown beyond component timings')


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.win_confirmation.v323'
        and document['status'] in ('EVALUATION_COMPLETE', 'HOLD_CUTOFF')
        and document['scientific_gate'] == 'FRESH_EXECUTION_VALIDATION_NOT_INDEPENDENT_LEARNING_OR_U006',
        'fresh execution validation keeps its actual fixed-cohort scientific scope and explicit cutoff HOLD')
    source = Path(document['source_summary']).resolve(); previous = json_file(source)
    prior = json_file(source.parent/'audit.json')
    require(previous['schema'] == 'acfqp.component_heads.v322' and previous['status'] == 'DIAGNOSTIC_COMPLETE'
        and prior['status'] == 'PASS' and prior['independent_valid']
        and prior['all_complete_hybrid_parameter_tables_and_exact_sparse_component_deltas_valid']
        and json_file(source.parent/'audit_execution.json')['exit_code'] == 0,
        'actual frozen candidate component separation inherits V322 independent PASS without old fitting or tape reaudit')
    configuration = expected_configuration(source)
    equal_tree(json_file(directory/'configuration.json'), configuration,
        'the candidate new seeds quota zero fitting and sole primary are frozen before new execution')
    equal_tree(document['settings'], configuration, 'final results retain the full frozen new-stream configuration')
    equal_tree(document['source_provenance'], previous['source_provenance'], 'the actual four SOURCE parents remain unchanged')
    lives = document['by_lifecycle']
    require([row['lifecycle'] for row in lives] == list(range(16)), 'every original learned lifecycle remains without selection')
    old = {row['lifecycle']: row for row in previous['by_lifecycle']}
    sources = {row['parent']: row for row in previous['source_provenance']['parents']}
    records, physical = [], Counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(check_parent, sources[parent], [row for row in lives if row['parent'] == parent],
            {life: row for life, row in old.items() if row['parent'] == parent}) for parent in range(4)]
        for job in as_completed(jobs):
            parent_records, counts = job.result(); records.extend(parent_records); physical.update(counts)
    records.sort(key=lambda row: row['lifecycle'])
    check_analysis(document['summary'], records, lives)
    require(document['status'] == ('EVALUATION_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'),
        'every retained cutoff holds the full prospective terminal-benefit conclusion')
    costs = json_file(source.parent/'audit_costs.json')
    inherited = costs['full_economic_source_v317_v319_v321_and_experiment_cpu_seconds']
    diagnostic = costs['preceding_v320_diagnostic_full_cpu_seconds']
    execution = json_file(directory/'execution.json')
    require((directory/'stderr.log').stat().st_size == 0, 'the completed new execution experiment has empty stderr')
    check_accounting(document, inherited, diagnostic, physical, execution)
    return dict(status='PASS', independent_valid=True, lifecycles=16, fixed_source_parents=4, **dict(physical),
        prior_v322_audit_status='PASS', prior_full_audit_repeated=False,
        actual_FIRST_then_actual_saved_WIN_ONLY_v1_restoration_valid=True,
        complete_candidate_reward_equals_FIRST_valid=True, frozen_candidate_receipts_unchanged=True,
        all_new_natural_game_summaries_physical_endpoints_fresh_paired_seeds_work_and_effects_valid=True,
        new_training_raw_tiles=0, new_fit_updates=0, new_head_files=0,
        complete_game_endpoints=document['summary']['complete_game_endpoints'], primary_status=document['summary']['primary_status'],
        retained_execution_gain_supported=document['summary']['retained_execution_gain_supported'],
        new_experiment_component_cpu_seconds=document['accounting']['new_experiment_component_cpu_seconds'],
        new_experiment_full_cpu_seconds=execution['process_tree_cpu_seconds'],
        full_economic_source_v317_v319_v321_v322_and_experiment_cpu_seconds=inherited+execution['process_tree_cpu_seconds'],
        preceding_v320_diagnostic_full_cpu_seconds=diagnostic,
        limitations='Actual SOURCE/FIRST/candidate parameter files and restore receipts are read independently. '
            'Every new natural-game summary, physical endpoint, seed, work count and paired effect vector is checked. '
            'Natural-game action physics/H2 decisions and bootstrap draws are not rerun; this interface retains summaries, not step tapes. '
            'Prior V322 component separation PASS is inherited without replaying training, targets or the old full audit. '
            'New execution streams validate a development-selected frozen candidate on the existing learned cohort under four frozen parents. '
            'No independent learning-history replication, ordinary online sampling-efficiency, general strategic-learning or U006 claim.')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('directory', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = audit(args.directory)
    target = args.output or args.directory/'audit.json'
    target.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_win_confirmation_audit_complete', status=result['status'],
        primary_status=result['primary_status'], retained_execution_gain=result['retained_execution_gain_supported'])), flush=True)


if __name__ == '__main__': main()
