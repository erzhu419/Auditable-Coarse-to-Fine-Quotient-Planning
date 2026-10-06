#!/usr/bin/env python3
"""Independent new-history, terminal-target and equal-update reader for V326."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (HeadVersions, check_detection_route,
    check_initial_acquisition, check_initial_fit, check_representation, close,
    equal_tree, json_file, literal_choose, physical_status, planning_counts,
    read_source_weights, require, require_source_audit, sum_counts,
    check_fresh_source_document)
from verify_greedy_targets_v317 import (InitialWorld, FactualWorld,
    check_batch_dataset, feature_addresses, predict_components)
from verify_query_supervision_v319 import (CENSUS_FIELDS, GROUP_FIELDS, PROVENANCE_COLUMNS,
    anchor_census, artifact_arrays, check_group_arrays, check_selector,
    check_supervision_work, effect_status, ground_uniforms, selected_positions)
from verify_teacher_calibration_v320 import (TRACE_COLUMNS, DENSE_FIELDS,
    check_continuations, check_continuation_work, check_probes)

TASKS = ('A', 'B')
UPDATING_ARMS = ('BOOTSTRAP_WIN', 'TERMINAL_WIN')
ARMS = ('SOURCE', 'FIRST_LOCAL', *UPDATING_ARMS)
STAGES = ('A0', 'B0')
GROUPS, REPLICAS, EPOCHS = 1024, 4, 16
INITIAL_RAW, POST_RAW = 131072, 65536
PROBABILITIES = {'A': .1, 'B': .5}
PAIRS = (('TERMINAL_WIN', 'FIRST_LOCAL'), ('TERMINAL_WIN', 'BOOTSTRAP_WIN'), ('TERMINAL_WIN', 'SOURCE'),
    ('BOOTSTRAP_WIN', 'FIRST_LOCAL'), ('BOOTSTRAP_WIN', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))


def warmup_seed(life, stage, game):
    return 3261000000000+STAGES.index(stage)*100000+life*1000000+game


def training_seed(life, stage):
    return 3262000000000+STAGES.index(stage)*100000+life*10000000


def post_seed(life, task, number):
    return 3265000000000+life*10000000+TASKS.index(task)*1000000+number*100000


def selection_seed(life, task, number):
    return 3263000000000+life*10000000+TASKS.index(task)*1000000+number*100000


def draw_seed(life, task, number):
    return 3266000000000+life*10000000+TASKS.index(task)*1000000+number*100000


def evaluation_seed(life, task, episode):
    return 3269000000000+life*1000000+TASKS.index(task)*100000+episode


def continuation_seed(life, task, number, group, member):
    return 3267000000000+life*10000000+TASKS.index(task)*1000000+number*100000+group*4+member


def read_parent_tape(parent, rows):
    lives = {row['lifecycle']: row for row in rows}
    initial = {(life, stage): InitialWorld(life, stage, warmup_seed, training_seed)
        for life in lives for stage in STAGES}
    batches = {}; heads = set(); fits = set(); decoded = 0; raw_by_phase = Counter()
    path = Path(parent['trace_file'])
    require(path.stat().st_size == parent['trace_bytes'], 'new parent tapes retain their actual compressed bytes')
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line); life_id = row['lifecycle']; life = lives[life_id]
            require(row['parent'] == parent['parent'] == life_id % 4,
                'all new histories belong to their actual frozen SOURCE parent')
            decoded += 1
            raw_by_phase[row.get('phase', 'NONE')] += len(row.get('raw_spawns', ()))
            if row['kind'] == 'INITIAL_HEADS':
                task = row['task']; key = life_id, task
                require(key not in heads and initial[life_id, task+'0'].snapshot is not None
                    and row['head_versions'] == life['initial'][task]['head_versions'],
                    'FIRST versions follow their completed new detector and acquisition history once')
                heads.add(key); continue
            if row['kind'] == 'CONSOLIDATED_HEAD':
                task, number, arm = row['task'], row['round_index'], row['arm']
                key = life_id, task, number, arm; stage = life['rounds'][str(number)][task]
                value = stage['arms'][arm]
                require(key not in fits and batches[life_id, task, number].snapshot is not None
                    and row['head_version'] == value['head_version'] and row['fit'] == value['fit'],
                    'each WIN-only fit and sparse version follows the complete new fixed-FIRST collector once')
                fits.add(key); continue
            phase = row['phase']
            if phase in STAGES:
                world = initial[life_id, phase]
                if phase == 'B0': require((life_id, 'A') in heads, 'B detector follows actual completed new A adaptation')
                method = {'WARMUP': world.warmup, 'CONFIRMATION': world.warmup, 'DETECTOR_LOOK': world.look,
                    'DETECTION_SNAPSHOT': world.detect, 'TRAIN': world.train, 'ACQUISITION_SNAPSHOT': world.checkpoint}.get(row['kind'])
            else:
                task = row['task']; number = int(phase[-1]); key = life_id, task, number
                require(phase == f'{task}_R{number}' and number in (1, 2)
                    and row['arm'] == 'FIXED_FIRST' and (life_id, 'B') in heads,
                    'only new declared fixed-FIRST task/round cohorts feed the paired arms')
                if key not in batches:
                    first = life['initial'][task]; actor = first['head_version']
                    identity = dict(lifecycle=life_id, parent=parent['parent'], arm='FIXED_FIRST',
                        batch_id=phase, phase=phase, true_p_four=PROBABILITIES[task],
                        model_p_four=first['planning_belief']['estimated_p_four'], task=task,
                        actor_head_updates=actor['updates'], collector_policy_kind='LOCAL_RISK',
                        actor_version=actor, stream_seed=post_seed(life_id, task, number))
                    batches[key] = FactualWorld(identity['stream_seed'], POST_RAW, PROBABILITIES[task], identity, 'LOCAL_RISK')
                world = batches[key]
                method = {'TRAIN': world.train, 'ACQUISITION_SNAPSHOT': world.checkpoint}.get(row['kind'])
            require(method is not None, 'new canonical history contains only actual detector collection and declared head events')
            method(row)
    require(decoded == parent['canonical_rows'] and len(heads) == 2*len(lives)
        and len(fits) == 8*len(lives) and len(batches) == 4*len(lives)
        and all(world.snapshot is not None for world in initial.values())
        and all(world.snapshot is not None for world in batches.values()),
        'all new initial and post-round histories close without replacement or omission')
    require(Counter(parent['paid_raw_by_phase']) == raw_by_phase
        and parent['paid_factual_raw_tiles'] == sum(raw_by_phase.values()),
        'all actual newly generated detector initial and post-cohort raw tiles agree with the tape inventory')
    return initial, batches, decoded


def check_epoch_fit(fit, arrays, initial_head=None):
    roots = arrays['roots']; n = len(roots); features = np.sort(feature_addresses(roots), axis=1)
    unique = int(n+np.count_nonzero(features[:, 1:] != features[:, :-1]))
    require(fit['method'] == 'GROUPED_WIN_ONLY_LOCAL' and fit['alpha'] == .0025
        and fit['fitted_rootgroups'] == fit['trained_afterstates'] == fit['win_trained_afterstates'] == n
        and fit['reward_trained_afterstates'] == 0 and fit['replicates'] == 4
        and fit['frozen_rootgroup_predictions'] and fit['reward_frozen']
        and fit['sampling_unit'] == 'ROOTGROUP_MEAN_OF_FIXED_TEACHER_ONE_STEP_REPLICAS',
        'the current learner commits once per real WIN group while FIRST reward has no learning inputs')
    learning = dict(rootgroup_updates=n, current_predictions=n, win_predictions=n,
        table_lookups=32*n, win_table_lookups=32*n, table_update_occurrences=32*n,
        table_updates=unique, win_parameter_updates=unique)
    require(Counter(fit['learning_counts']) == Counter(learning),
        'every actual current WIN prediction and distinct-address write is paid without reward work')
    targets = dict(rootgroups_targeted=n, win_replica_reads=8*n, win_target_mean_additions=4*n,
        target_mean_divisions=n, replica_noise_residuals=4*n, replica_noise_squares=4*n,
        replica_noise_accumulations=4*n, replica_noise_divisions=1, replica_noise_square_roots=1)
    require(Counter(fit['target_counts']) == Counter(targets), 'actual target averaging and WIN-only dispersion work is paid')
    norm = dict(rootgroups_processed=n, feature_extractions=n, feature_occurrences=32*n,
        feature_digit_reads=192*n, feature_address_multiply_adds=192*n, sort_calls=n, sort_items=32*n,
        denominator_occurrence_visits=32*n, rootgroup_unique_addresses=unique,
        win_gradient_products=unique, normalization_divisions=unique, parameter_update_multiplications=unique,
        rootgroup_parameter_commits=n, win_rootgroup_commits=n, win_parameter_writes=unique, native_workspace_bytes=512)
    require(Counter({key: value for key, value in fit['normalization_counts'].items() if key != 'sort_comparisons'}) == Counter(norm)
        and fit['normalization_counts']['sort_comparisons'] > 0,
        'literal within-root multiplicities determine only actual WIN gradient normalization and commits')
    require(Counter(fit['representation_counts']) == Counter(risk_sigmoid_evaluations=n, local_risk_table_lookups=32*n),
        'WIN-only current predictions do not charge or execute combined reward-value prediction')
    pt = arrays['mean_win']; noise = fit['replicate_noise']
    require(noise['definition'] == 'SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'
        and close(noise['win_replica_rms'], float(np.sqrt(np.mean((arrays['targetwin']-pt[:, None])**2)))),
        'WIN dispersion uses the actual four member labels within each rootgroup')
    for sample, index in ((fit['first_sample'], 0), (fit['last_sample'], n-1)):
        require(sample['rootgroup'] == index and close(sample['risk_target'], pt[index])
            and close(sample['risk_error'], pt[index]-sample['risk_probability']),
            'actual first and last residuals use their own saved group means before the commit')
    if initial_head is not None:
        _, probability = predict_components(roots[:1], initial_head)
        require(close(fit['first_sample']['risk_probability'], probability[0]),
            'the first current WIN residual reads its actual previous learner head')
    require(fit['cpu_seconds'] >= 0. and fit['seconds'] >= 0., 'actual WIN-only fit timings remain present')
    return unique


def check_evaluation(value, life, task, belief, version):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2'
        and value['head_version'] == version and value['static_evaluation_valid'],
        'each new evaluation uses its own actual frozen head and immutable FIRST FIT belief')
    games = value['game_summaries']
    require(len(games) == 64 and [game['seed'] for game in games]
        == [evaluation_seed(life, task, episode) for episode in range(64)],
        'all sixty-four paired games use the new V326 family rather than development selection streams')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'every new natural game keeps its fixed horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE',
                'a real active cutoff stays explicit without a false terminal label')
            bonus = 0.
        else:
            require(game['status'] in ('WON', 'LOST') and physical_status(game['final_board']) == game['status'],
                'each natural terminal outcome matches its complete physical final board')
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'whole-game utility uses actual score and natural outcome')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    expected = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=128,
        raw_tile_productions=steps+128, environment_random_draws=2*(steps+128),
        ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+64,
        ground_status_internal_swipe_calls=4*(steps+64-wins), ground_swipe_calls=steps+4*(steps+64-wins))
    require(Counter(value['counts']['environment']) == Counter(expected),
        'all evaluation initial tiles actions and winning-action spawns are charged once')
    planning_counts(value['counts']['planning'], steps, depth=2)
    if version is not None:
        check_representation(value['representation_counts'], 'LOCAL_RISK', value['counts']['planning'].get('value_predictions', 0))
    require(not value['counts'].get('learning', {}) and value['cpu_seconds'] >= 0. and value['seconds'] >= 0.,
        'frozen evaluation retains actual paid timing and zero learner updates')
    return None if any(game['status'] == 'CUTOFF' for game in games) else mean(game['utility'] for game in games)


def check_census(receipt, world, collector, teacher, version, life, parent, task, number, belief):
    boards = np.concatenate(world.afterstate_chunks); postspawn = np.concatenate(world.postspawn_chunks)
    fit_games = 4*len(world.games)//5; fit_end = world.ends[fit_games-1]
    dataset = collector['dataset']
    require(dataset['fit_game_count'] == fit_games and dataset['fit_step_end'] == fit_end,
        'anchor source complete FIT boundary is independently reconstructed rather than a selected subset')
    indices = anchor_census(boards, world.games, fit_games, GROUPS)
    metadata = dict(schema='acfqp.terminal_win_census.v326', lifecycle=life, parent=parent, task=task, round=number,
        groups=GROUPS, anchors=2*GROUPS, teacher_version=version, selection_seed=selection_seed(life,task,number),
        planning_probability=belief, selection_rule='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        source_batch=dict(actor_version=collector['actor_version'], batch_id=f'{task}_R{number}',
            fit_step_end=fit_end, fit_game_count=fit_games, stream_seed=post_seed(life,task,number)))
    arrays = artifact_arrays(receipt, CENSUS_FIELDS, metadata)
    for name in CENSUS_FIELDS:
        dtype = np.int32 if name == 'validmask' else np.int64
        require(arrays[name].dtype == dtype, 'census indices masks and query paths retain exact declared integer types')
    require(np.array_equal(arrays['anchor_indices'], indices) and arrays['validmask'].shape == (2*GROUPS,)
        and arrays['query_ordinals'].shape == arrays['query_counts'].shape == (2*GROUPS,),
        'all twice-group-count census anchors are the frozen evenly spaced eligible complete FIT indices')
    preboards = postspawn[indices-1]; natural_roots = boards[indices]
    query_roots, paths = check_selector(preboards, arrays['query_ordinals'], arrays['query_counts'], arrays['validmask'],
        selection_seed(life,task,number))
    positions = selected_positions(arrays['validmask'], GROUPS)
    provenance = np.column_stack((paths[positions], arrays['query_ordinals'][positions], arrays['query_counts'][positions]))
    require(np.array_equal(arrays['selected_positions'], positions) and np.array_equal(arrays['selected_provenance'], provenance)
        and receipt['selected_groups'] == GROUPS, 'both arms use the same prespecified valid census positions and exact ordered H2-call roots')
    nonwin = np.max(boards[:fit_end], axis=1) < 11
    starts = np.asarray([0]+world.ends[:fit_games-1], dtype=np.int64)
    eligible = int(np.count_nonzero(nonwin))-int(np.count_nonzero(nonwin[starts]))
    anchor_counts = dict(fit_states=fit_end,fit_games=fit_games,eligible_anchors=eligible,selected_anchors=2*GROUPS,
        requested_groups=GROUPS,excluded_winning_fit_states=fit_end-int(np.count_nonzero(nonwin)),
        excluded_game_first_nonwinning_states=int(np.count_nonzero(nonwin[starts])),index_array_bytes=16*GROUPS,
        preboard_array_bytes=128*GROUPS,natural_root_array_bytes=128*GROUPS)
    equal_tree(receipt['anchor_counts'], anchor_counts, 'actual census construction excludes game starts WIN HELDOUT and paid tails before querying')
    query = receipt['query']; count = int(np.sum(arrays['query_counts'])); valid = int(np.count_nonzero(arrays['validmask']))
    require(query['selection_seed'] == metadata['selection_seed'] and query['p_model'] == belief
        and query['teacher_updates'] == version['updates'] and query['provenance_columns'] == PROVENANCE_COLUMNS
        and query['selection_rule'] == metadata['selection_rule'], 'actual query receipt uses its frozen FIRST bank and declared selector')
    expected_counts = dict(anchors_queried=2*GROUPS, actual_nonwin_leaf_queries=count, pool_board_cells_written=16*count,
        pool_path_fields_written=4*count, selector_random_draws=2*GROUPS, valid_anchors=valid, selected_roots=valid)
    equal_tree({key:query['counts'][key] for key in expected_counts}, expected_counts,
        'every actual H2 leaf-call pool preserves multiplicity and one selector draw per anchor')
    maximum = int(np.max(arrays['query_counts']))
    capacity = 0 if not maximum else 1 << (maximum-1).bit_length()
    require(query['counts']['native_pool_bytes_peak'] == 96*capacity,
        'actual shared query pool peak includes the native board/path capacity once')
    planning_counts(query['planning_counts'], 2*GROUPS, depth=2)
    require(query['planning_counts']['value_predictions'] == count, 'all independently reconstructed leaf calls reconcile actual query table reads')
    check_representation(query['representation_counts'], 'LOCAL_RISK', count)
    probes = 0
    for name, expected_indices in (('first_probes', range(8)), ('last_probes', range(2*GROUPS-8,2*GROUPS))):
        require(len(query[name]) == 8, 'all predeclared first-eight last-eight census teacher probes are retained')
        for saved, index in zip(query[name], expected_indices):
            actual = literal_choose(preboards[index].tolist(), teacher.reward, teacher.terminal, 'LOCAL_RISK', belief)
            require(saved['anchor_index'] == index and saved['preboard'] == preboards[index].tolist()
                and saved['chosen_action'] == actual['action'] and saved['chosen_afterstate'] == natural_roots[index].tolist()
                and actual['afterstate'] == natural_roots[index].tolist() and close(saved['chosen_h2_value'],actual['value'])
                and saved['status'] == 'ACTIVE', 'bounded actual FIRST H2 decisions reproduce factual natural roots at prescribed census boundaries')
            equal_tree(saved['action_values'], actual['action_values'], 'all literal candidate H2 values bind census teacher choice to actual frozen weights')
            probes += 1
    return query_roots[positions], probes



def check_head_setups(row, size):
    total = 0
    for task in TASKS:
        require(set(row['head_setups'][task]) == {'FIRST_LOCAL', *UPDATING_ARMS},
            'each task owns one new FIRST and two private WIN-only learner heads')
        for arm, setup in row['head_setups'][task].items():
            counts = setup['setup_counts']
            require(counts['source_parameters_copied'] == size and counts['source_weight_bytes_copied'] == 8*size
                and counts['allocated_weight_parameters'] == 2*size and counts['allocated_weight_bytes'] == 16*size
                and counts['initialized_zero_risk_parameters'] == size and setup['private_weight_bytes'] == 16*size,
                'each real head allocation pays its actual SOURCE copy zero WIN and two complete tables')
            if arm in UPDATING_ARMS:
                require(counts['first_parameters_copied'] == 2*size and counts['first_weight_bytes_copied'] == 16*size,
                    'both private learners start from complete copies of their new actual FIRST tables')
            require(setup['cpu_seconds'] >= 0. and setup['wall_seconds'] >= 0., 'actual new allocation timings remain present')
            total += setup['private_weight_bytes']
    require(row['private_head_weight_bytes'] == total, 'all six actual private tables pairs are counted once')


def check_collector(receipt, world, actor):
    check_batch_dataset(receipt['dataset'], world)
    acquisition = receipt['acquisition']
    require(receipt['actor_version'] == acquisition['actor_version'] == actor
        and acquisition['actor_head_updates_before'] == acquisition['actor_head_updates_after'] == actor['updates']
        and acquisition['new_actor_updates'] == 0 and acquisition['training'] == world.snapshot['training']
        and acquisition['snapshot'] == world.snapshot['snapshot'] and acquisition['reconstruction'] == world.snapshot['reconstruction']
        and acquisition['policy_probes'] == world.snapshot['policy_probes'],
        'the complete new collector remains frozen at its actual own FIRST v0 without fitting or uncharged acquisition')


def check_replay_fit(fit, arrays, initial_head, target_field):
    require(target_field in ('targetwin', 'terminal_win'), 'each learner has its fixed declared WIN target field')
    require(fit['method'] == 'REPLAY_GROUPED_WIN_ONLY_LOCAL' and fit['alpha'] == .0025
        and fit['distinct_rootgroups'] == GROUPS and fit['epochs'] == EPOCHS
        and fit['fitted_rootgroups'] == GROUPS*EPOCHS and fit['replicates'] == REPLICAS
        and fit['reward_frozen'] and len(fit['epoch_receipts']) == EPOCHS,
        'both learners replay exactly the same rootgroup update quota with frozen FIRST reward')
    labels = arrays[target_field]
    epoch_arrays = dict(roots=arrays['roots'], targetwin=labels, mean_win=np.mean(labels, axis=1))
    writes = 0
    for index, epoch in enumerate(fit['epoch_receipts']):
        writes += check_epoch_fit(epoch, epoch_arrays, initial_head if index == 0 else None)
    for field in ('learning_counts', 'normalization_counts', 'target_counts', 'representation_counts'):
        equal_tree(fit[field], sum_counts(epoch[field] for epoch in fit['epoch_receipts']),
            'actual repeated prediction target averaging normalization and table writes are charged for every epoch')
    require(fit['cpu_seconds'] >= sum(epoch['cpu_seconds'] for epoch in fit['epoch_receipts'])-1e-9
        and fit['seconds'] >= sum(epoch['seconds'] for epoch in fit['epoch_receipts'])-1e-9,
        'replay fit timing includes every epoch rather than just the final pass')
    return writes


def check_terminal_labels(stage, arrays, teacher, version, life, parent, task, number, belief):
    native = stage['continuation']; artifact = native['outcome_artifact']
    metadata = dict(schema='acfqp.terminal_win_outcome.v326', lifecycle=life, parent=parent,
        task=task, round=number, groups=GROUPS, members=REPLICAS, teacher_version=version,
        p_model=belief, p_true=PROBABILITIES[task], max_steps=8192,
        continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2')
    outcomes = artifact_arrays(artifact, tuple(field for field in DENSE_FIELDS if field != 'original_group_indices'), metadata)
    seeds = np.asarray([[continuation_seed(life, task, number, group, member)
        for member in range(REPLICAS)] for group in range(GROUPS)], dtype=np.uint64)
    require(np.array_equal(outcomes['rollout_seeds'], seeds),
        'all fresh suffixes use their prospective local group-member seeds without adaptive replacement')
    trace = native['trace_artifact']; path = Path(trace['file'])
    require(trace['columns'] == TRACE_COLUMNS and trace['dtype'] == 'int32'
        and trace['packing_rule'] == 'GROUP_MEMBER_CHRONOLOGICAL_EXECUTED_ACTIONS'
        and not trace['reused_start_spawn_included'] and trace['all_new_spawns_included']
        and path.stat().st_size == trace['compressed_bytes'],
        'every newly generated suffix action and spawn is retained in its complete chronological physical trace')
    with np.load(path, allow_pickle=False) as saved:
        require(saved.files == ['moves'], 'the suffix trace contains exactly its physical action rows')
        moves = saved['moves']
    require(len(moves) == trace['rows'] and moves.nbytes == trace['uncompressed_bytes'],
        'retained suffix row and byte inventory closes')
    _, wins, physical, probes = check_continuations(moves, arrays['roots'], arrays['spawn_cells'],
        arrays['spawn_ranks'], arrays['selected_action'], arrays['targetkind'], seeds, outcomes, PROBABILITIES[task])
    check_continuation_work(native, physical, outcomes, version, belief, PROBABILITIES[task])
    physical['literal_suffix_H2_probes'] += check_probes(native['boundary_probes'], probes, teacher, belief)
    require(np.array_equal(arrays['terminal_win'], wins, equal_nan=True)
        and np.array_equal(arrays['mean_terminal_win'], np.mean(wins, axis=1), equal_nan=True),
        'every learned terminal member and group mean is its independently replayed natural outcome')
    statuses = {name:int(np.count_nonzero(outcomes['status'] == code))
        for name, code in (('WON', 1), ('LOST', -1), ('CUTOFF', 0))}
    equal_tree(stage['terminal_status_counts'], statuses, 'all successful adverse and unfinished suffix labels remain present')
    physical.update(trace_files=1, outcome_files=1, trace_array_bytes=moves.nbytes,
        outcome_array_bytes=artifact['array_bytes'], terminal_member_labels=GROUPS*REPLICAS)
    return physical


def check_lifecycle(row, initial_worlds, worlds, source_weights, checkpoint):
    life, parent = row['lifecycle'], row['parent']; prototypes = []; counts = Counter()
    require(parent == life % 4 and row['initial_context_precondition_met'],
        'every fresh learning lifecycle retains its fixed source parent and genuinely distinct observed task banks')
    check_head_setups(row, source_weights.size)
    heads, teachers, versions, beliefs = {}, {}, {}, {}
    records = dict(lifecycle=life, parent=parent, cells={})
    require(len({row['initial'][task]['context_id'] for task in TASKS}) == 2,
        'the fresh A and B context banks are distinct')
    for task in TASKS:
        first = row['initial'][task]; world = initial_worlds[life, task+'0']
        context, created = check_detection_route(first['context_route'], world.detection['detector_belief'], prototypes, world.looks)
        require(created and context == first['context_id'], 'the fresh FIRST belongs to its actual blindly detected context')
        fit_games = check_initial_acquisition(first, world)
        require(set(first['head_versions']) == set(first['first_fits']) == {'FIRST_LOCAL'}
            and first['head_version'] == first['head_versions']['FIRST_LOCAL'], 'each task fits one actual fresh FIRST v0')
        fit, version = first['first_fits']['FIRST_LOCAL'], first['head_version']
        check_initial_fit(fit, world, fit_games, source_weights)
        require(version['updates'] == fit['trained_afterstates'] and version['source_checkpoint'] == checkpoint,
            'each fresh FIRST version records its actual new FIT updates and frozen SOURCE')
        identity = dict(lifecycle=life, parent=parent, context_id=context, arm='FIRST_LOCAL')
        teacher = HeadVersions(source_weights, checkpoint, identity, 'LOCAL_RISK'); teacher.apply(version)
        teachers[task] = teacher; heads[task] = {}; versions[task] = {arm:version for arm in UPDATING_ARMS}
        beliefs[task] = first['planning_belief']['estimated_p_four']
        for arm in UPDATING_ARMS:
            head = HeadVersions(source_weights, checkpoint, dict(identity, arm=arm), 'LOCAL_RISK')
            head.apply(version); heads[task][arm] = head
        require(set(first['evaluations']) == {'SOURCE', 'FIRST_LOCAL'}, 'fresh SOURCE and own-FIRST controls are complete')
        records['cells']['FIRST_'+task] = {arm:check_evaluation(value, life, task, beliefs[task],
            None if arm == 'SOURCE' else version) for arm, value in first['evaluations'].items()}
        counts.update(new_initial_acquisitions=1, new_initial_raw_tiles=INITIAL_RAW,
            new_detector_raw_tiles=world.warm_raw, actual_FIRST_versions=1)
    for number in (1, 2):
        r = str(number)
        for task in TASKS:
            stage = row['rounds'][r][task]; other = 'B' if task == 'A' else 'A'
            first = row['initial'][task]['head_version']
            require(set(stage['collectors']) == {'FIXED_FIRST'} and set(stage['arms']) == set(UPDATING_ARMS)
                and stage['groups'] == GROUPS and stage['replicas'] == REPLICAS
                and stage['teacher_unchanged'] and stage['teacher_version'] == first,
                'both learning arms retain the same fresh immutable FIRST teacher and physical root/member cohort')
            equal_tree(stage['inactive_head_versions_before'], versions[other], 'the other task heads precede this stage unchanged')
            collector = stage['collectors']['FIXED_FIRST']; world = worlds[life, task, number]
            check_collector(collector, world, first)
            counts['literal_collector_H2_probes'] += world.check_probes(teachers[task], collector['acquisition']['policy_probes'])
            roots, probes = check_census(stage['census'], world, collector, teachers[task], first,
                life, parent, task, number, beliefs[task]); counts['literal_teacher_H2_probes'] += probes
            metadata = dict(schema='acfqp.terminal_win_groups.v326', lifecycle=life, parent=parent,
                task=task, round=number, groups=GROUPS, replicas=REPLICAS,
                sampling_unit='ROOTGROUP_FOUR_SHARED_FRESH_GROUND_SPAWNS', teacher_version=first,
                draw_seed=draw_seed(life, task, number), true_probability=PROBABILITIES[task],
                census_file=stage['census']['file'], target_rule='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH')
            shared = stage['shared_supervision']; artifact = shared['group_artifact']
            arrays = artifact_arrays(artifact, (*GROUP_FIELDS, 'terminal_win', 'mean_terminal_win'), metadata)
            stats, kinds = check_group_arrays(arrays, roots, ground_uniforms(draw_seed(life,task,number), GROUPS),
                PROBABILITIES[task], teachers[task])
            check_supervision_work(shared, roots, stats, kinds, metadata['draw_seed'], first['updates'], PROBABILITIES[task])
            counts.update(check_terminal_labels(stage, arrays, teachers[task], first, life, parent, task, number, beliefs[task]))
            cell = dict(records['cells']['FIRST_'+task])
            for arm in UPDATING_ARMS:
                item = stage['arms'][arm]; head = heads[task][arm]; version = item['head_version']
                target = 'targetwin' if arm == 'BOOTSTRAP_WIN' else 'terminal_win'
                equal_tree(item['supervision'], dict(group_artifact=artifact, target_field=target),
                    'both actual learners reference the same physical roots and first spawns with only their label field changed')
                require(item['updates_before'] == versions[task][arm]['updates'] == head.receipts[-1]['updates']
                    and item['updates_after'] == version['updates'] == item['updates_before']+GROUPS*EPOCHS,
                    'each private WIN learner advances from its own actual previous head through all fixed replay epochs')
                writes = check_replay_fit(item['fit'], arrays, head, target)
                head.apply(version); versions[task][arm] = version
                require(item['reward_unchanged'] and version['reward_indices_count'] == 0
                    and np.array_equal(head.reward, teachers[task].reward),
                    'all learned versions preserve the complete actual FIRST reward table')
                cell[arm] = check_evaluation(item['evaluations'], life, task, beliefs[task], version)
                counts.update(fitted_rootgroups=GROUPS*EPOCHS, actual_win_parameter_writes=writes, new_win_versions=1)
            equal_tree(stage['inactive_head_versions_after'], versions[other], 'the other task heads survive this full stage unchanged')
            records['cells']['ROUND'+r+'_'+task] = cell
            counts.update(new_post_acquisitions=1, new_post_raw_tiles=POST_RAW,
                physical_supervision_samples=GROUPS*REPLICAS, independently_checked_joint_targets=GROUPS*REPLICAS,
                independently_checked_selected_actions=GROUPS*REPLICAS, group_artifact_array_bytes=artifact['array_bytes'])
    equal_tree(row['final_head_versions'], versions, 'all final pointers preserve their own actual full sparse chains')
    return records, counts

def check_parent(source, rows, parent):
    initial, worlds, decoded = read_parent_tape(parent, rows)
    weights = read_source_weights(source['checkpoint']); records = []; counts = Counter(canonical_rows=decoded)
    for row in rows:
        record, checked = check_lifecycle(row, initial, worlds, weights, source['checkpoint'])
        records.append(record); counts.update(checked)
        print(json.dumps(dict(event='independent_win_learning_life_checked', lifecycle=row['lifecycle'])), flush=True)
    return records, counts


INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_SOURCE_PARENTS_NEW_V326_TARGET_LEARNING_HISTORIES'


def check_interval(value, values):
    require(len(values) == 16 and close(value['mean'], mean(values)), 'the paired effect retains all sixteen new signed lifecycle means')
    equal_tree(value['lifecycle_values'], {str(i): number for i, number in enumerate(values)},
        'every positive equal and adverse new learning history remains in the paired vector')
    equal_tree(value['parent_mean_values'], {str(p): mean(values[p::4]) for p in range(4)},
        'all four actual fixed source groups remain in the effect')
    require(value['positive_equal_negative'] == [sum(x > 0 for x in values), sum(x == 0 for x in values), sum(x < 0 for x in values)],
        'the effect direction counts retain adverse new histories')
    low, high = value['ci95']
    minimum, maximum = mean(min(values[p::4]) for p in range(4)), mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= low <= high <= maximum+1e-10 and value['interval_scope'] == INTERVAL_SCOPE
        and value['status95'] == effect_status(value, True),
        'the interval range sign and scope describe new target histories under the four fixed parents')


def check_analysis(summary, records, lives):
    cutoffs = []; training_cutoffs = []; terminal_cutoffs = []; terminal_members = 0; actual = []
    for row, record in zip(lives, records):
        endpoints = {}
        for task in TASKS:
            first = row['initial'][task]
            training = [('FIRST_WARMUP', 'SOURCE', first['acquisition']['warmup']['game_summaries']),
                ('FIRST', 'SOURCE', first['dataset']['games'])]
            for r in ('1', '2'):
                training.append(('ROUND'+r, 'FIXED_FIRST', row['rounds'][r][task]['collectors']['FIXED_FIRST']['dataset']['games']))
                statuses = row['rounds'][r][task]['terminal_status_counts']
                terminal_members += sum(statuses.values())
                if statuses.get('CUTOFF', 0):
                    terminal_cutoffs.append(dict(lifecycle=row['lifecycle'], task=task, round=int(r), count=statuses['CUTOFF']))
            training_cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, checkpoint=checkpoint,
                collector=collector, episode=game['episode']) for checkpoint, collector, games in training
                for game in games if game['status'] == 'CUTOFF')
            stages = [('FIRST', first['evaluations'])]+[('ROUND'+r, {arm:item['evaluations']
                for arm,item in row['rounds'][r][task]['arms'].items()}) for r in ('1', '2')]
            for checkpoint, evaluations in stages:
                endpoints[checkpoint+'_'+task] = {}
                for arm, value in evaluations.items():
                    games = value['game_summaries']
                    endpoints[checkpoint+'_'+task][arm] = {status:sum(game['status'] == status for game in games)
                        for status in ('WON', 'LOST', 'CUTOFF')}
                    cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, checkpoint=checkpoint,
                        arm=arm, seed=game['seed']) for game in games if game['status'] == 'CUTOFF')
        actual.append(dict(record, retained_endpoint_counts=endpoints, failure=row.get('failure')))
    equal_tree(summary['by_lifecycle'], actual, 'all new natural endpoints and actual control means are retained')
    complete = not cutoffs and not training_cutoffs and not terminal_cutoffs
    require(summary['primary_contrast'] == 'TERMINAL_WIN_minus_FIRST_LOCAL_FINAL_AB'
        and summary['physical_evaluation_games'] == 12288 and summary['new_target_learning_histories']
        and not summary['source_histories_repeated'] and not summary['independent_SOURCE']
        and summary['cutoffs'] == cutoffs and summary['training_cutoffs'] == training_cutoffs
        and summary['terminal_cutoffs'] == terminal_cutoffs
        and summary['physical_terminal_supervision_members'] == terminal_members == 262144
        and summary['same_root_target_ablation'] and summary['matched_optimization_quota']
        and not summary['equal_total_raw_efficiency_evaluated']
        and summary['complete_game_endpoints'] == complete and summary['complete_target_learning_cohort'] == complete
        and summary['bootstrap_executed'] == complete and summary['bootstrap_seed'] == 32600001
        and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_unit'] == 'PAIRED_NEW_TARGET_LEARNING_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        'the prospective sole own-FIRST primary uses new target histories and any cutoff holds all inference')
    names = {left+'_minus_'+right for left, right in PAIRS}
    require(set(summary['round_ab_contrasts']) == {'1', '2'} and set(summary['task_contrasts']) ==
        {'ROUND'+r+'_'+task for r in ('1', '2') for task in TASKS},
        'both fixed learning rounds and all task checkpoints remain explicit')
    def view(values, number, tasks):
        require(set(values) == names, 'all six fixed utility control and target-intervention contrasts remain present')
        means = {arm:[mean(record['cells']['ROUND'+number+'_'+task][arm] for task in tasks) for record in records] for arm in ARMS}
        for left, right in PAIRS:
            value = values[left+'_minus_'+right]; vector = [a-b for a, b in zip(means[left], means[right])]
            if complete: check_interval(value, vector)
            else: require(value is None, 'any acquisition or evaluation cutoff suppresses every effect interval')
    for r in ('1', '2'):
        view(summary['round_ab_contrasts'][r], r, TASKS)
        for task in TASKS:
            key = 'ROUND'+r+'_'+task
            view(summary['task_contrasts'][key], r, (task,))
            equal_tree(summary['checkpoint_contrasts'][key], {arm:summary['task_contrasts'][key][arm+'_minus_FIRST_LOCAL']
                for arm in UPDATING_ARMS}, 'checkpoint preservation uses each actual own-FIRST task contrast')
    equal_tree(summary['final_ab_contrasts'], summary['round_ab_contrasts']['2'], 'the final effect is the actual second learning round')
    primary = summary['final_ab_contrasts']['TERMINAL_WIN_minus_FIRST_LOCAL']
    equal_tree(summary['primary'], primary, 'the sole primary cannot be replaced by a favorable SOURCE or bootstrap-control contrast')
    hold = 'HOLD_TERMINAL_CUTOFF' if terminal_cutoffs else 'HOLD_TRAINING_CUTOFF' if training_cutoffs else 'HOLD_CUTOFF'
    def status(value, retention=False):
        return effect_status(value, True, retention) if complete else hold
    primary_status = status(primary)
    retention = {task:status(summary['checkpoint_contrasts']['ROUND2_'+task]['TERMINAL_WIN'], True) for task in TASKS}
    contribution = status(summary['final_ab_contrasts']['TERMINAL_WIN_minus_BOOTSTRAP_WIN'])
    retained = primary_status == 'SUPPORTED_GAIN' and all(status == 'SUPPORTED_NONDECREASE' for status in retention.values())
    expected = dict(primary_status=primary_status, primary_self_improvement_status=primary_status,
        primary_self_improvement_supported=primary_status == 'SUPPORTED_GAIN', task_retention_status=retention,
        retained_improvement_supported=retained, terminal_target_contribution_status=contribution,
        terminal_target_contribution_supported=contribution == 'SUPPORTED_GAIN',
        retained_terminal_mechanism_supported=retained and contribution == 'SUPPORTED_GAIN',
        bootstrap_self_improvement_status=status(summary['final_ab_contrasts']['BOOTSTRAP_WIN_minus_FIRST_LOCAL']),
        final_net_gain_status=status(summary['final_ab_contrasts']['TERMINAL_WIN_minus_SOURCE']))
    equal_tree({key:summary[key] for key in expected}, expected,
        'new learning gain both-task preservation and terminal-target contribution remain separate conditions')
    require(summary['secondary_interval_scope'] == 'NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM'
        and 'not independent SOURCE replication' in summary['evidence_scope'],
        'new target-history evidence keeps fixed SOURCE and nominal secondary limitations')


def expected_configuration(source):
    return dict(schema='acfqp.terminal_win_freeze.v326', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/TERMINAL_WIN_V326.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS),
        arms=list(ARMS), updating_arms=list(UPDATING_ARMS), rounds=[1, 2],
        initial_raw_per_task=INITIAL_RAW, round_raw_per_collector=POST_RAW,
        fit_fraction=.8, alpha=.0025, groups_per_task_round=GROUPS, replicas_per_group=REPLICAS,
        epochs=EPOCHS, rootgroup_updates_per_arm_task_round=GROUPS*EPOCHS,
        census_anchors_per_task_round=2*GROUPS, true_probabilities=PROBABILITIES,
        query=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.),
        initial_contexts='V309_CONFIRMED_NEW_BANKS_DISTINCT_PRECONDITION',
        teacher='IMMUTABLE_NEW_FIRST_LOCAL_V0_ALL_ROUNDS_AND_BOTH_ARMS',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        collector='FROZEN_NEW_FIRST_LOCAL_V0_SHARED_PHYSICALLY_CHARGED_PER_ARM',
        reward='ACTUAL_FIRST_REWARD_FROZEN_WITH_ZERO_WRITES_BOTH_ROUNDS',
        query_root='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        valid_selection='EQUIDISTANT_VALID_CENSUS_POSITIONS_SHARED_BETWEEN_ARMS',
        reset_access='ARBITRARY_AFTERSTATE_GENERATIVE_ACCESS_FOR_BOTH_ARMS',
        target_fields={'BOOTSTRAP_WIN':'targetwin', 'TERMINAL_WIN':'terminal_win'},
        bootstrap_target='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH_WIN_COMPONENT_ONLY',
        terminal_target='SAVED_DIRECT_THEN_FROZEN_FIRST_H2_TRUE_WORLD_TERMINAL_WIN',
        update='SIXTEEN_FIXED_ORDER_PASSES_CURRENT_WIN_PREDICTION_RECOMPUTED_PER_GROUP',
        optimization_comparison='SAME_ROOTS_MEMBERS_ALPHA_PASSES_ORDER_AND_UPDATE_COUNTS',
        cost_comparison='SAME_ROOT_LABEL_ABLATION_EXTRA_TERMINAL_RAW_CHARGED_NOT_EQUAL_TOTAL_RAW_EFFICIENCY',
        max_steps=8192, evaluation_games_per_cell=64,
        seed_initial_warmup=3261000000000, seed_initial_training=3262000000000,
        seed_collection=3265000000000, seed_selector=3263000000000, seed_ground=3266000000000,
        seed_continuation=3267000000000, continuation_group_stride=4,
        collection_life_stride=10000000, collection_task_stride=1000000, collection_round_stride=100000,
        seed_evaluation=3269000000000, bootstrap_seed=32600001, bootstrap_draws=20000,
        primary='TERMINAL_WIN_minus_FIRST_LOCAL_FINAL_AB',
        terminal_target_contribution='TERMINAL_WIN_minus_BOOTSTRAP_WIN_FINAL_AB',
        retention='FINAL_TERMINAL_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        expected_initial_training_raw_tiles=4194304, expected_post_raw_physical=4194304,
        expected_shared_first_spawns=262144, expected_terminal_rollouts=262144,
        expected_updates_per_arm=1048576, expected_new_evaluation_games=12288,
        evidence_scope='NEW_TARGET_LEARNING_HISTORIES_UNDER_FOUR_FIXED_V312_SOURCES_SAME_ROOT_TERMINAL_LABEL_INTERVENTION',
        candidate_selection='V325_TASK_OPPOSED_FIRST_TEACHER_WIN_BIAS_AND_UNRESOLVED_V324_LEARNING_UTILITY',
        stop_rule='WHOLE_COHORT_HOLD_ON_BANK_CENSUS_ACQUISITION_EVALUATION_OR_TERMINAL_CUTOFF_NO_REPLACEMENT_OR_TUNING')


def check_accounting(document, source_costs, physical, execution):
    lives, account = document['by_lifecycle'], document['accounting']
    initial = [row['initial'][task] for row in lives for task in TASKS]
    stages = [row['rounds'][r][task] for row in lives for r in ('1', '2') for task in TASKS]
    collectors = [stage['collectors']['FIXED_FIRST'] for stage in stages]
    census = [stage['census'] for stage in stages]; queries = [item['query'] for item in census]
    labels = [stage['shared_supervision'] for stage in stages]; tails = [stage['continuation'] for stage in stages]
    items = [stage['arms'][arm] for stage in stages for arm in UPDATING_ARMS]
    evaluations = [value for item in initial for value in item['evaluations'].values()]+[item['evaluations'] for item in items]
    heads = [item['head_version'] for item in initial]+[item['head_version'] for item in items]
    groups = [item['group_artifact'] for item in labels]
    initial_raw = physical['new_initial_raw_tiles']+physical['new_detector_raw_tiles']
    post_raw = physical['new_post_raw_tiles']; factual = initial_raw+post_raw
    starts, tail_raw = physical['physical_supervision_samples'], physical['new_raw_tiles']
    inherited_raw = source_costs['source_training_raw_tiles']+source_costs['dynamics_raw_tiles']
    per_arm = {}
    for arm in UPDATING_ARMS:
        selected = [stage['arms'][arm] for stage in stages]
        extra = tail_raw if arm == 'TERMINAL_WIN' else 0
        per_arm[arm] = dict(distinct_rootgroups=65536, rootgroup_updates=1048576,
            economic_shared_factual_raw_tiles=factual, economic_shared_first_spawn_raw_tiles=starts,
            additional_terminal_raw_tiles=extra, economic_training_raw_tiles=inherited_raw+factual+starts+extra,
            fit_counts=sum_counts(item['fit']['learning_counts'] for item in selected),
            normalization_counts=sum_counts(item['fit']['normalization_counts'] for item in selected),
            target_counts=sum_counts(item['fit']['target_counts'] for item in selected),
            fit_representation_counts=sum_counts(item['fit']['representation_counts'] for item in selected),
            fit_cpu_seconds=sum(item['fit']['cpu_seconds'] for item in selected))
    worker = sum(row['cpu_seconds'] for row in document['parent_receipts'])
    compiler = sum(row['compiler_cpu_seconds'] for row in document['parent_receipts'])
    component = worker+compiler+account['coordinator_cpu_seconds']
    inherited = source_costs['fresh_source_compute']['full_source_cpu_seconds']
    expected = dict(inherited_source_costs=source_costs, source_training_repeated=False,
        old_target_data_reused=False, new_target_learning_histories=True, equal_total_raw_efficiency_test=False,
        new_initial_raw_tiles=initial_raw, new_post_factual_raw_tiles=post_raw,
        shared_first_spawn_raw_tiles=starts, additional_terminal_raw_tiles=tail_raw,
        terminal_rollouts=physical['rollouts'], terminal_status_counts={
            'WON':physical['won'], 'LOST':physical['lost'], 'CUTOFF':physical['cutoffs']},
        new_training_raw_tiles=factual+starts+tail_raw, per_arm=per_arm,
        economic_training_raw_tiles_per_arm={'SOURCE':inherited_raw, 'FIRST_LOCAL':inherited_raw+initial_raw,
            **{arm:value['economic_training_raw_tiles'] for arm,value in per_arm.items()}},
        initial_fit_cpu_seconds=sum(item['first_fits']['FIRST_LOCAL']['cpu_seconds'] for item in initial),
        initial_acquisition_cpu_seconds=sum(item['acquisition']['cpu_seconds'] for item in initial),
        post_acquisition_cpu_seconds=sum(item['acquisition']['cpu_seconds'] for item in collectors),
        physical_census_query_counts=sum_counts(value['counts'] for value in queries),
        physical_census_planning_counts=sum_counts(value['planning_counts'] for value in queries),
        physical_census_representation_counts=sum_counts(value['representation_counts'] for value in queries),
        shared_supervision_counts=sum_counts(value['counts'] for value in labels),
        shared_supervision_environment_counts=sum_counts(value['environment_counts'] for value in labels),
        shared_supervision_planning_counts=sum_counts(value['planning_counts'] for value in labels),
        shared_supervision_representation_counts=sum_counts(value['representation_counts'] for value in labels),
        shared_supervision_cpu_seconds=sum(value['cpu_seconds'] for value in labels),
        continuation_environment_counts=sum_counts(value['environment_counts'] for value in tails),
        continuation_planning_counts=sum_counts(value['planning_counts'] for value in tails),
        continuation_representation_counts=sum_counts(value['representation_counts'] for value in tails),
        continuation_counts=sum_counts(value['counts'] for value in tails),
        continuation_cpu_seconds=sum(value['cpu_seconds'] for value in tails),
        new_evaluation_games=12288, reused_evaluation_games=0,
        new_evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        new_evaluation_planning_counts=sum_counts(value['counts']['planning'] for value in evaluations),
        split_evaluation_representation_counts=sum_counts(value.get('representation_counts', {}) for value in evaluations),
        representation_scope='SPLIT_HEADS_ONLY_SOURCE_HAS_PLANNING_COUNTS',
        new_evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        new_head_files=160, new_head_saved_bytes=sum(value['saved_bytes'] for value in heads),
        group_files=64, group_saved_bytes=sum(value['saved_bytes'] for value in groups),
        census_files=64, census_saved_bytes=sum(value['saved_bytes'] for value in census),
        terminal_trace_files=64, terminal_trace_saved_bytes=sum(value['trace_artifact']['compressed_bytes'] for value in tails),
        terminal_outcome_files=64, terminal_outcome_saved_bytes=sum(value['outcome_artifact']['saved_bytes'] for value in tails),
        canonical_trace_bytes=sum(row['trace_bytes'] for row in document['parent_receipts']),
        worker_cpu_seconds=worker, compiler_cpu_seconds=compiler,
        new_experiment_component_cpu_seconds=component, inherited_successful_source_full_cpu_seconds=inherited,
        economic_source_and_experiment_component_cpu_seconds=inherited+component)
    equal_tree({key:account[key] for key in expected}, expected,
        'shared roots/spawns are paid once physically and per learner economically; all terminal suffix costs belong to TERMINAL_WIN')
    require(physical['new_initial_acquisitions'] == 32 and physical['new_post_acquisitions'] == 64
        and physical['new_initial_raw_tiles'] == physical['new_post_raw_tiles'] == 4194304
        and physical['physical_supervision_samples'] == physical['rollouts'] == 262144
        and physical['fitted_rootgroups'] == 2097152
        and sum(row['paid_factual_raw_tiles'] for row in document['parent_receipts']) == factual,
        'literal full tape/suffix reconstruction agrees with every fixed actual acquisition and optimization budget')
    require(execution['exit_code'] == 0 and execution['process_tree_cpu_seconds']+1e-6 >= component
        and account['wall_seconds'] > 0. and account['coordinator_cpu_seconds'] >= 0.
        and 'previous target experiments excluded' in account['cost_scope'],
        'full experiment CPU includes serialization/shutdown and excludes all earlier target experiment costs')

def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.terminal_win.v326'
        and document['status'] in ('EXPERIMENT_COMPLETE', 'HOLD_CUTOFF')
        and document['scientific_gate'] == 'TERMINAL_TARGET_LEARNING_UNDER_FIXED_SOURCES_NOT_U006',
        'V326 records a complete new target-learning cohort under fixed SOURCE without claiming U006')
    source = Path(document['source_summary']).resolve(); original = json_file(source)
    source_audit = require_source_audit(source.parent)
    inherited = check_fresh_source_document(original, document['source_provenance'])
    configuration = expected_configuration(source)
    equal_tree(json_file(directory/'configuration.json'), configuration, 'new learning seeds exact candidate budgets and sole primary were frozen before data')
    equal_tree(document['settings'], configuration, 'all completed new histories retain the original frozen learning contract')
    lives = document['by_lifecycle']
    require([row['lifecycle'] for row in lives] == list(range(16))
        and [row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'the full new target cohort and all four parent workers remain present without selection')
    sources = {row['parent']:row for row in original['source_provenance']['parents']}
    parents = {row['parent']:row for row in document['parent_receipts']}
    records, physical = [], Counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(check_parent, sources[parent], [row for row in lives if row['parent'] == parent], parents[parent]) for parent in range(4)]
        for job in as_completed(jobs):
            parent_records, counts = job.result(); records.extend(parent_records); physical.update(counts)
    records.sort(key=lambda row:row['lifecycle'])
    check_analysis(document['summary'], records, lives)
    require(document['status'] == ('EXPERIMENT_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'),
        'a retained cutoff prevents a completed prospective learning-benefit claim')
    execution = json_file(directory/'execution.json')
    require((directory/'stderr.log').stat().st_size == 0, 'the completed new learning producer has empty stderr')
    check_accounting(document, inherited, physical, execution)
    require(physical['literal_collector_H2_probes'] == physical['literal_teacher_H2_probes'] == 1024,
        'all prescribed first/last physical collector and H2 census probes are checked once')
    full = execution['process_tree_cpu_seconds']; source_cpu = inherited['fresh_source_compute']['full_source_cpu_seconds']
    return dict(status='PASS', independent_valid=True, lifecycles=16, fixed_source_parents=4, **dict(physical),
        fresh_source_audit_status=source_audit['status'], prior_full_audit_repeated=False,
        zero_old_target_data_reuse_valid=True, new_first_natural_mc_acquisitions_and_target_receipts_valid=True,
        all_actual_FIRST_and_WIN_only_sparse_head_chains_valid=True,
        complete_FIRST_reward_invariance_both_arms_both_rounds_valid=True,
        every_query_path_paired_physical_spawn_joint_teacher_target_and_WIN_group_mean_valid=True,
        every_terminal_label_bound_to_complete_literal_suffix_physics_and_rng_valid=True,
        same_root_same_spawn_equal_ALPHA_epochs_and_updates_valid=True,
        extra_terminal_environment_cost_charged_to_terminal_learning_valid=True,
        all_new_natural_game_summaries_physical_endpoints_fresh_paired_seeds_work_and_effects_valid=True,
        complete_game_endpoints=document['summary']['complete_game_endpoints'], primary_status=document['summary']['primary_status'],
        retained_improvement_supported=document['summary']['retained_improvement_supported'],
        terminal_target_contribution_status=document['summary']['terminal_target_contribution_status'],
        new_experiment_component_cpu_seconds=document['accounting']['new_experiment_component_cpu_seconds'],
        new_experiment_full_cpu_seconds=full, full_economic_source_and_experiment_cpu_seconds=source_cpu+full,
        limitations='Every new initial and fixed-FIRST tape is independently reconstructed with literal physics RNG labels and observed detection. '
            'Actual FIRST v0 and private v1/v2 files are read; every group label/path/target and complete unchanged reward table is checked. '
            'Every terminal suffix action/spawn is physically replayed and bound to its learned member/group WIN label. '
            'Initial MC examples/counts, every epoch target/residual/count and epoch-zero previous-head prediction are checked; complete fits are not replayed. '
            'Collection/census and suffix H2 policy use all first/last probes; natural evaluation action tapes and bootstrap draws are not rerun. '
            'New target histories condition on four reused SOURCE parents, immutable FIRST suffix policy and arbitrary generative reset access. '
            'Same-root labels and optimization quotas are matched; terminal suffix raw is additional paid work. '
            'No independent SOURCE replication, ordinary online sampling-efficiency, general strategic-learning or U006 claim.')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('directory', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = audit(args.directory)
    (args.output or args.directory/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_win_learning_audit_complete', status=result['status'],
        primary_status=result['primary_status'], retained_improvement=result['retained_improvement_supported'])), flush=True)


if __name__ == '__main__': main()
