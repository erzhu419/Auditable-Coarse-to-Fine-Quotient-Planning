#!/usr/bin/env python3
"""Independent saved-head component and reused-stream mechanism reader."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (HeadVersions, close, equal_tree, json_file,
    read_source_weights, require, sum_counts)
from verify_query_supervision_v319 import effect_status
from verify_reward_targets_v321 import check_evaluation

TASKS = ('A', 'B')
ARMS = ('FIRST_LOCAL', 'NSTEP_QUERY', 'REWARD_ONLY', 'WIN_ONLY')
NEW_ARMS = ('REWARD_ONLY', 'WIN_ONLY')
PAIRS = (('REWARD_ONLY', 'NSTEP_QUERY'), ('REWARD_ONLY', 'FIRST_LOCAL'),
    ('WIN_ONLY', 'FIRST_LOCAL'), ('NSTEP_QUERY', 'WIN_ONLY'), ('NSTEP_QUERY', 'FIRST_LOCAL'))
INTERACTION = 'NSTEP_QUERY_minus_REWARD_ONLY_minus_WIN_ONLY_plus_FIRST_LOCAL'
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_REUSED_FIRST_COHORT_AND_V321_STREAMS'


def versions(previous, task):
    first = previous['initial'][task]['head_version']
    return [first] + [previous['rounds'][str(number)][task]['arms']['NSTEP_QUERY']['head_version']
        for number in (1, 2)]


def reconstruct(source_weights, checkpoint, identity, chain):
    head = HeadVersions(source_weights, checkpoint, identity, 'LOCAL_RISK')
    for receipt in chain:
        head.apply(receipt)
    return head


def check_hybrid(item, arm, first, updated, chain, source_weights, checkpoint, identity):
    """Complete exact tables, sparse changes and source lineage, without any refit."""
    receipt, assembly = item['head_version'], item['assembly']
    require(arm in NEW_ARMS and receipt['version'] == 1
        and receipt['updates'] == chain[0]['updates'] and receipt['base_file'] == chain[0]['file'],
        'each hybrid is a new unfitted v1 based on its actual FIRST v0; updates remain the FIRST count')
    hybrid = reconstruct(source_weights, checkpoint, dict(identity, arm=arm), [chain[0], receipt])
    selected = 'reward' if arm == 'REWARD_ONLY' else 'terminal'
    for component in ('reward', 'terminal'):
        expected = getattr(updated if component == selected else first, component)
        require(np.array_equal(getattr(hybrid, component), expected),
            'each complete hybrid table equals exactly its selected final NSTEP or frozen FIRST component')
        with np.load(receipt['file'], allow_pickle=False) as saved:
            indices = np.flatnonzero(expected != getattr(first, component)).astype(np.int64)
            require(np.array_equal(saved[component+'_indices'], indices)
                and np.array_equal(saved[component+'_values'], expected[indices]),
                'hybrid sparse writes are exactly the selected component changes from FIRST; the other delta is empty')
    reward_source = 'NSTEP_QUERY' if arm == 'REWARD_ONLY' else 'FIRST_LOCAL'
    win_source = 'FIRST_LOCAL' if arm == 'REWARD_ONLY' else 'NSTEP_QUERY'
    expected = dict(method='SAVED_COMPONENT_CROSSOVER_NO_FIT',
        reward_source_versions=chain if reward_source == 'NSTEP_QUERY' else chain[:1],
        win_source_versions=chain if win_source == 'NSTEP_QUERY' else chain[:1],
        reward_source=reward_source, win_source=win_source, new_fit_updates=0,
        weights_frozen=True, parameter_updates_counter=chain[0]['updates'],
        component_copy_parameters=first.reward.size, component_copy_bytes=first.reward.nbytes,
        complete_component_equality=True)
    equal_tree({key: assembly[key] for key in expected}, expected,
        'the component assembly records actual saved source chains, one copied table and zero fitting')
    require(assembly['cpu_seconds'] >= 0. and assembly['wall_seconds'] >= 0.,
        'actual component assembly CPU and wall costs are retained')
    return hybrid


def check_lifecycle(row, previous, source_weights, checkpoint):
    life, parent = row['lifecycle'], row['parent']
    require(life == previous['lifecycle'] and parent == previous['parent'] == life % 4,
        'all sixteen saved-head lives retain their actual four frozen SOURCE parents')
    equal_tree(row['initial'], previous['initial'], 'hybrid evaluation keeps both actual FIRST versions and immutable bank beliefs')
    require(set(row['cells']) == set(TASKS), 'both independent A and B banks remain present')
    means, counts = {}, Counter()
    for task in TASKS:
        initial, cells = row['initial'][task], row['cells'][task]
        require(set(cells) == set(ARMS), 'all four component combinations remain present without arm selection')
        chain = versions(previous, task)
        identity = dict(lifecycle=life, parent=parent, context_id=initial['context_id'], arm='NSTEP_QUERY')
        first = reconstruct(source_weights, checkpoint, identity, chain[:1])
        updated = reconstruct(source_weights, checkpoint, identity, chain)
        means[task] = {}
        for arm in ARMS:
            item = cells[arm]
            require(item['reused'] == (arm not in NEW_ARMS),
                'only audited FIRST and final NSTEP game receipts are reused; hybrids are evaluated once')
            if arm in NEW_ARMS:
                check_hybrid(item, arm, first, updated, chain, source_weights, checkpoint, identity)
                version = item['head_version']
                counts.update(new_head_files=1, new_head_saved_bytes=version['saved_bytes'])
            else:
                equal_tree(item['evaluation'], previous['final_evaluations'][task][arm],
                    'reused FIRST and NSTEP evaluations retain exactly their existing V321 receipts')
                version = chain[0] if arm == 'FIRST_LOCAL' else chain[-1]
            value = item['evaluation']
            means[task][arm] = check_evaluation(value, life, task,
                initial['planning_belief']['estimated_p_four'], version)
            label = 'new' if arm in NEW_ARMS else 'reused'
            counts.update({label+'_evaluation_games': len(value['game_summaries']),
                label+'_evaluation_new_raw_tiles': value['counts']['environment']['raw_tile_productions']})
    return dict(lifecycle=life, parent=parent, cells=means), counts


def check_interval(value, values):
    require(len(values) == 16 and close(value['mean'], mean(values)),
        'paired component effects retain all sixteen actual signed lifecycle means')
    equal_tree(value['lifecycle_values'], {str(i): x for i, x in enumerate(values)},
        'every favorable equal and adverse lifecycle remains in the paired component effect vector')
    equal_tree(value['parent_mean_values'], {str(p): mean(values[p::4]) for p in range(4)},
        'component effects retain all four actual frozen-parent means')
    require(value['positive_equal_negative'] == [sum(x > 0 for x in values), sum(x == 0 for x in values), sum(x < 0 for x in values)],
        'component direction counts retain adverse lifecycles')
    low, high = value['ci95']
    minimum, maximum = mean(min(values[p::4]) for p in range(4)), mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= low <= high <= maximum+1e-10
        and value['interval_scope'] == INTERVAL_SCOPE and value['status95'] == effect_status(value, True),
        'interval bounds and signs retain their reused-stream fixed-parent conditional scope')


def check_analysis(summary, records, lives):
    cutoffs, actual_records = [], []
    for row, record in zip(lives, records):
        endpoints = {}
        for task in TASKS:
            endpoints[task] = {}
            for arm in ARMS:
                item = row['cells'][task][arm]; games = item['evaluation']['game_summaries']
                endpoints[task][arm] = {status: sum(game['status'] == status for game in games) for status in ('WON', 'LOST', 'CUTOFF')}
                cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, arm=arm, seed=game['seed'], reused=item['reused'])
                    for game in games if game['status'] == 'CUTOFF')
        actual_records.append(dict(record, retained_endpoint_counts=endpoints))
    equal_tree(summary['by_lifecycle'], actual_records, 'all four actual cell means and endpoint counts remain in the retained cohort')
    complete = not cutoffs
    require(summary['primary_contrast'] == 'REWARD_ONLY_minus_NSTEP_QUERY_FINAL_AB'
        and summary['physical_new_evaluation_games'] == 2048 and summary['reused_evaluation_games'] == 2048
        and summary['total_evaluation_games'] == 4096 and summary['cutoffs'] == cutoffs
        and summary['complete_game_endpoints'] == complete and summary['bootstrap_executed'] == complete
        and summary['bootstrap_seed'] == 32200001 and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_unit'] == 'PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT'
        and summary['paired_stream_reuse'],
        'sole component primary retains every reused stream and holds the entire cohort for any cutoff')
    names = {left+'_minus_'+right for left, right in PAIRS} | {INTERACTION}
    require(set(summary['final_ab_contrasts']) == names and set(summary['task_contrasts']) == set(TASKS),
        'all frozen final and task contrasts remain explicit')
    def view(value, tasks):
        require(set(value) == names, 'each contrast view retains all planned pairs and the component interaction')
        means = {arm: [mean(record['cells'][task][arm] for task in tasks) for record in records] for arm in ARMS}
        vectors = {left+'_minus_'+right: [a-b for a,b in zip(means[left], means[right])] for left,right in PAIRS}
        vectors[INTERACTION] = [both-r-w+first for both,r,w,first in zip(means['NSTEP_QUERY'], means['REWARD_ONLY'], means['WIN_ONLY'], means['FIRST_LOCAL'])]
        for name, values in vectors.items():
            if complete: check_interval(value[name], values)
            else: require(value[name] is None, 'any natural cutoff suppresses every terminal-effect interval without imputing unfinished truth')
    view(summary['final_ab_contrasts'], TASKS)
    for task in TASKS: view(summary['task_contrasts'][task], (task,))
    final = summary['final_ab_contrasts']; primary = final['REWARD_ONLY_minus_NSTEP_QUERY']
    equal_tree(summary['primary'], primary, 'the sole primary cannot be swapped for a favorable secondary component contrast')
    primary_status = effect_status(primary, complete)
    pure = {arm: effect_status(final[arm+'_minus_FIRST_LOCAL'], complete) for arm in NEW_ARMS}
    retention = {task: effect_status(summary['task_contrasts'][task]['REWARD_ONLY_minus_FIRST_LOCAL'], complete, True) for task in TASKS}
    expected = dict(primary_status=primary_status, primary_restoration_supported=primary_status == 'SUPPORTED_GAIN',
        reward_only_self_improvement_status=pure['REWARD_ONLY'], pure_component_status=pure,
        interaction_status=effect_status(final[INTERACTION], complete), task_retention_status=retention,
        restored_growth_supported=primary_status == 'SUPPORTED_GAIN' and pure['REWARD_ONLY'] == 'SUPPORTED_GAIN'
            and all(value == 'SUPPORTED_NONDECREASE' for value in retention.values()))
    equal_tree({key: summary[key] for key in expected}, expected,
        'restoration own-FIRST growth and both-task retention remain separate evidence requirements')
    require(summary['secondary_interval_scope'] == 'NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM'
        and 'not independent confirmation' in summary['evidence_scope'],
        'component diagnostics keep nominal secondary and reused-stream evidence limits')


def check_parent(source, rows, previous):
    weights = read_source_weights(source['checkpoint']); records = []; physical = Counter()
    for row in rows:
        record, counts = check_lifecycle(row, previous[row['lifecycle']], weights, source['checkpoint'])
        records.append(record); physical.update(counts)
        print(json.dumps(dict(event='independent_component_heads_life_checked', lifecycle=row['lifecycle'])), flush=True)
    return records, physical


def expected_configuration(source):
    return dict(schema='acfqp.component_heads_freeze.v322', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/COMPONENT_HEADS_V322.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS),
        new_arms=list(NEW_ARMS), reused_arms=['FIRST_LOCAL', 'NSTEP_QUERY'],
        components={'FIRST_LOCAL': ['FIRST_LOCAL', 'FIRST_LOCAL'], 'NSTEP_QUERY': ['NSTEP_QUERY', 'NSTEP_QUERY'],
            'REWARD_ONLY': ['NSTEP_QUERY', 'FIRST_LOCAL'], 'WIN_ONLY': ['FIRST_LOCAL', 'NSTEP_QUERY']},
        restore='ACTUAL_FIRST_V0_THEN_NSTEP_QUERY_V1_THEN_V2_ABSOLUTE_SPARSE_WRITES',
        assembly='FULL_SELECTED_COMPONENT_COPY_OTHER_COMPONENT_EXACT_FIRST_NO_FIT',
        updates_counter='INHERITED_FIRST_ONLY_HYBRID_VERSION_IS_ASSEMBLY_NOT_TRAINING',
        planning_belief='ACTUAL_IMMUTABLE_V321_FIRST_BANK_BELIEF', true_probabilities={'A': .1, 'B': .5},
        evaluation_games_per_cell=32, max_steps=8192, seed_evaluation=321900000000,
        paired_stream_reuse=True, expected_new_evaluation_games=2048, expected_reused_evaluation_games=2048,
        maximum_new_evaluation_raw_tiles=16781312, new_training_raw_tiles=0, new_fit_updates=0,
        primary='REWARD_ONLY_minus_NSTEP_QUERY_FINAL_AB', bootstrap_draws=20000, bootstrap_seed=32200001,
        stop_rule='ANY_NEW_OR_REUSED_NATURAL_GAME_CUTOFF_GLOBAL_HOLD_NO_REPLACEMENTS',
        evidence_scope='SAVED_COMPONENT_POLICY_MECHANISM_FIXED_V321_STREAMS_NOT_INDEPENDENT_CONFIRMATION')


def check_accounting(document, inherited, diagnostic, physical, execution):
    account = document['accounting']; lives = document['by_lifecycle']
    new = [row['cells'][task][arm] for row in lives for task in TASKS for arm in NEW_ARMS]
    evaluations = [item['evaluation'] for item in new]
    reused = [row['cells'][task][arm]['evaluation'] for row in lives for task in TASKS for arm in ('FIRST_LOCAL', 'NSTEP_QUERY')]
    per_arm = {arm: dict(new_evaluation_games=sum(len(row['cells'][task][arm]['evaluation']['game_summaries']) for row in lives for task in TASKS),
        environment_counts=sum_counts(row['cells'][task][arm]['evaluation']['counts']['environment'] for row in lives for task in TASKS),
        evaluation_cpu_seconds=sum(row['cells'][task][arm]['evaluation']['cpu_seconds'] for row in lives for task in TASKS)) for arm in NEW_ARMS}
    equal_tree(account['per_arm'], per_arm, 'both hybrid arms pay only their actual new natural evaluations')
    expected = dict(new_training_raw_tiles=0, new_fit_updates=0, source_training_repeated=False,
        first_adaptation_repeated=False, prior_full_audit_repeated=False,
        new_evaluation_games=sum(len(value['game_summaries']) for value in evaluations),
        reused_evaluation_games=sum(len(value['game_summaries']) for value in reused),
        new_evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        new_evaluation_planning_counts=sum_counts(value['counts']['planning'] for value in evaluations),
        new_evaluation_representation_counts=sum_counts(value['representation_counts'] for value in evaluations),
        new_evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        new_head_files=len(new), new_head_saved_bytes=sum(item['head_version']['saved_bytes'] for item in new),
        assembly_component_copy_parameters=sum(item['assembly']['component_copy_parameters'] for item in new),
        assembly_component_copy_bytes=sum(item['assembly']['component_copy_bytes'] for item in new))
    equal_tree({key: account[key] for key in expected}, expected,
        'all new game work component table copies and saved hybrid artifacts reconcile actual receipts; training remains zero')
    require(account['new_evaluation_games'] == physical['new_evaluation_games'] == 2048
        and account['reused_evaluation_games'] == physical['reused_evaluation_games'] == 2048
        and account['new_evaluation_environment_counts']['raw_tile_productions'] == physical['new_evaluation_new_raw_tiles'] <= 16781312
        and account['new_head_files'] == physical['new_head_files'] == 64
        and account['new_head_saved_bytes'] == physical['new_head_saved_bytes'],
        'new physical games raw and saved heads are counted separately from old evaluation references')
    require([row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'all four frozen-parent workers remain present')
    worker = sum(row['cpu_seconds'] for row in document['parent_receipts'])
    compiler = sum(row['compiler_cpu_seconds'] for row in document['parent_receipts'])
    require(close(account['worker_cpu_seconds'], worker) and close(account['compiler_cpu_seconds'], compiler)
        and close(account['new_experiment_component_cpu_seconds'], worker+compiler+account['coordinator_cpu_seconds'])
        and close(account['inherited_successful_source_v317_v319_v321_full_cpu_seconds'], inherited)
        and close(account['economic_source_v317_v319_v321_and_experiment_component_cpu_seconds'], inherited+account['new_experiment_component_cpu_seconds'])
        and close(account['preceding_v320_diagnostic_full_cpu_seconds'], diagnostic),
        'restoration assembly compiler coordinator and evaluation compute is paid once with inherited V321 cost; V320 diagnostic stays separate')
    require(execution['exit_code'] == 0 and execution['process_tree_cpu_seconds']+1e-6 >= account['new_experiment_component_cpu_seconds'],
        'full process-tree CPU includes final serialization and shutdown beyond component timing')


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.component_heads.v322'
        and document['status'] in ('DIAGNOSTIC_COMPLETE', 'HOLD_CUTOFF')
        and document['scientific_gate'] == 'SAVED_COMPONENT_MECHANISM_NOT_INDEPENDENT_CONFIRMATION_NO_U006',
        'the saved-head mechanism experiment retains its reused-stream scientific scope and explicit cutoff HOLD')
    source = Path(document['source_summary']).resolve(); previous = json_file(source)
    prior = json_file(source.parent/'audit.json')
    require(previous['schema'] == 'acfqp.reward_targets.v321' and previous['status'] == 'EXPERIMENT_COMPLETE'
        and prior['status'] == 'PASS' and prior['independent_valid']
        and json_file(source.parent/'audit_execution.json')['exit_code'] == 0,
        'actual FIRST and final NSTEP heads and natural game receipts inherit the completed independent V321 PASS without old reaudit')
    configuration = expected_configuration(source)
    equal_tree(json_file(directory/'configuration.json'), configuration,
        'both component combinations reused seeds zero fitting and sole primary are frozen before new evaluation')
    equal_tree(document['settings'], configuration, 'the final result retains the complete frozen component configuration')
    equal_tree(document['source_provenance'], previous['source_provenance'], 'the actual four SOURCE parents remain unchanged')
    lives = document['by_lifecycle']
    require([row['lifecycle'] for row in lives] == list(range(16)), 'every original FIRST lifecycle remains without selection')
    old = {row['lifecycle']: row for row in previous['by_lifecycle']}
    sources = {row['parent']: row for row in previous['source_provenance']['parents']}
    records = []; physical = Counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(check_parent, sources[parent], [row for row in lives if row['parent'] == parent],
            {life: row for life, row in old.items() if row['parent'] == parent}) for parent in range(4)]
        for job in as_completed(jobs):
            parent_records, parent_physical = job.result(); records.extend(parent_records); physical.update(parent_physical)
    records.sort(key=lambda row: row['lifecycle'])
    check_analysis(document['summary'], records, lives)
    require(document['status'] == ('DIAGNOSTIC_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'),
        'any retained new or reused cutoff holds the entire terminal-benefit conclusion')
    costs = json_file(source.parent/'audit_costs.json')
    inherited = costs['full_economic_source_v317_v319_and_experiment_cpu_seconds']
    diagnostic = costs['preceding_v320_diagnostic_full_cpu_seconds']
    execution = json_file(directory/'execution.json')
    require((directory/'stderr.log').stat().st_size == 0, 'the completed original component experiment has empty stderr')
    check_accounting(document, inherited, diagnostic, physical, execution)
    return dict(status='PASS', independent_valid=True, lifecycles=16, fixed_source_parents=4, **dict(physical),
        prior_v321_audit_status='PASS', prior_full_audit_repeated=False,
        all_complete_hybrid_parameter_tables_and_exact_sparse_component_deltas_valid=True,
        actual_FIRST_and_final_NSTEP_component_lineage_valid=True,
        all_reused_evaluation_receipts_exact=True, all_new_natural_game_summaries_and_paired_effects_valid=True,
        new_training_raw_tiles=0, new_fit_updates=0,
        complete_game_endpoints=document['summary']['complete_game_endpoints'], primary_status=document['summary']['primary_status'],
        new_experiment_component_cpu_seconds=document['accounting']['new_experiment_component_cpu_seconds'],
        new_experiment_full_cpu_seconds=execution['process_tree_cpu_seconds'],
        full_economic_source_v317_v319_v321_and_experiment_cpu_seconds=inherited+execution['process_tree_cpu_seconds'],
        preceding_v320_diagnostic_full_cpu_seconds=diagnostic,
        limitations='All complete saved hybrid tables, exact sparse component separation and source chains are read independently. '
            'Every new natural-game summary, physical endpoint, work count and paired effect vector is checked; '
            'natural game physics/H2 decisions, model fitting and bootstrap draws are not rerun. '
            'The prior V321 PASS is inherited without old target/tape reaudit. '
            'This mechanism diagnostic is conditional on the existing cohort, four frozen parents and reused V321 streams. '
            'No independent confirmation, ordinary online sampling-efficiency or U006 authorization claim.')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('directory', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = audit(args.directory)
    target = args.output or args.directory/'audit.json'; target.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_component_heads_audit_complete', status=result['status'], primary_status=result['primary_status'])), flush=True)


if __name__ == '__main__': main()
