#!/usr/bin/env python3
"""Independent member-disjoint joint terminal-return learning and utility reader."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (HeadVersions, close, equal_tree, json_file,
    read_source_weights, require, sum_counts, check_representation, physical_status, planning_counts)
from verify_greedy_targets_v317 import feature_addresses, predict_components
from verify_query_supervision_v319 import artifact_arrays, effect_status, GROUP_FIELDS
from verify_teacher_calibration_v320 import DENSE_FIELDS

TASKS = ('A', 'B')
UPDATING_ARMS = ('WIN_ONLY', 'JOINT_RETURN')
ARMS = ('SOURCE', 'FIRST_LOCAL', *UPDATING_ARMS)
GROUPS, REPLICAS, EPOCHS, EPISODES = 1024, 4, 16, 64
TRAIN_MEMBERS, HELDOUT_MEMBERS = (0, 1), (2, 3)
TRAIN_KERNEL_MEMBERS = TRAIN_MEMBERS
PAIRS = (('JOINT_RETURN', 'FIRST_LOCAL'), ('JOINT_RETURN', 'WIN_ONLY'),
    ('JOINT_RETURN', 'SOURCE'), ('WIN_ONLY', 'FIRST_LOCAL'),
    ('WIN_ONLY', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_SOURCE_PARENTS_AND_RETAINED_V326_TARGET_COHORT'


def evaluation_seed(life, task, episode):
    return 3279000000000+life*1000000+TASKS.index(task)*100000+episode


def training_labels(arrays):
    """Only the two prespecified FIT members reach either learner."""
    require(arrays['reward_return'].shape == arrays['win'].shape == (GROUPS, REPLICAS),
        'all retained terminal rewards and WIN labels keep their original four member positions')
    require(np.all(np.isfinite(arrays['reward_return'])) and np.all(np.isin(arrays['win'], (0., 1.)))
        and np.all(np.isin(arrays['status'], (-1, 1))),
        'only naturally completed suffix labels enter either terminal learner')
    return arrays['reward_return'][:, TRAIN_KERNEL_MEMBERS], arrays['win'][:, TRAIN_KERNEL_MEMBERS]


def check_win_epoch(fit, arrays, initial_head=None):
    roots, labels = arrays['roots'], arrays['targetwin']; n, repeats = labels.shape
    features = np.sort(feature_addresses(roots), axis=1)
    writes = int(n+np.count_nonzero(features[:, 1:] != features[:, :-1]))
    require(fit['method'] == 'GROUPED_WIN_ONLY_LOCAL' and fit['alpha'] == .0025
        and fit['fitted_rootgroups'] == fit['trained_afterstates'] == fit['win_trained_afterstates'] == n
        and fit['reward_trained_afterstates'] == 0 and fit['replicates'] == repeats
        and fit['frozen_rootgroup_predictions'] and fit['reward_frozen']
        and fit['sampling_unit'] == 'ROOTGROUP_MEAN_OF_PROVIDED_REPLICAS',
        'WIN-only terminal learning keeps FIRST reward outside all target predictions and writes')
    equal_tree(fit['learning_counts'], dict(rootgroup_updates=n, current_predictions=n, win_predictions=n,
        table_lookups=32*n, win_table_lookups=32*n, table_update_occurrences=32*n,
        table_updates=writes, win_parameter_updates=writes),
        'all actual WIN-only predictions and distinct-address writes remain paid')
    equal_tree(fit['target_counts'], dict(rootgroups_targeted=n, win_replica_reads=2*repeats*n,
        win_target_mean_additions=repeats*n, target_mean_divisions=n, replica_noise_residuals=repeats*n,
        replica_noise_squares=repeats*n, replica_noise_accumulations=repeats*n,
        replica_noise_divisions=1, replica_noise_square_roots=1),
        'actual WIN targets and dispersion use only the two prespecified FIT members')
    norm = dict(rootgroups_processed=n, feature_extractions=n, feature_occurrences=32*n,
        feature_digit_reads=192*n, feature_address_multiply_adds=192*n, sort_calls=n, sort_items=32*n,
        denominator_occurrence_visits=32*n, rootgroup_unique_addresses=writes, win_gradient_products=writes,
        normalization_divisions=writes, parameter_update_multiplications=writes,
        rootgroup_parameter_commits=n, win_rootgroup_commits=n, win_parameter_writes=writes,
        native_workspace_bytes=512)
    equal_tree({key:value for key,value in fit['normalization_counts'].items() if key != 'sort_comparisons'}, norm,
        'WIN-only actual commits use the literal within-root feature inventory')
    require(fit['normalization_counts']['sort_comparisons'] > 0, 'native FIT feature sorting remains paid')
    equal_tree(fit['representation_counts'], dict(risk_sigmoid_evaluations=n, local_risk_table_lookups=32*n),
        'WIN-only fit performs exactly its actual sigmoid predictions without reward reads')
    targets = np.mean(labels, axis=1); noise = fit['replicate_noise']
    require(noise['definition'] == 'SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'
        and close(noise['win_replica_rms'], float(np.sqrt(np.mean((labels-targets[:, None])**2)))),
        'WIN-only training dispersion retains only its actual FIT targets')
    for sample, index in ((fit['first_sample'], 0), (fit['last_sample'], n-1)):
        require(sample['rootgroup'] == index and close(sample['risk_target'], targets[index])
            and close(sample['risk_error'], targets[index]-sample['risk_probability']),
            'WIN-only epoch boundary residuals bind to their actual two-member FIT targets')
    if initial_head is not None:
        _, probability = predict_components(roots[:1], initial_head)
        require(close(fit['first_sample']['risk_probability'], probability[0]),
            'WIN-only first prediction reads its actual preceding head')
    require(fit['cpu_seconds'] >= 0. and fit['seconds'] >= 0., 'actual WIN-only fit timing is retained')
    return writes


def check_joint_epoch(fit, roots, rewards, wins, initial_head=None):
    n, repeats = wins.shape
    features = np.sort(feature_addresses(roots), axis=1)
    writes = int(n+np.count_nonzero(features[:, 1:] != features[:, :-1]))
    require(fit['method'] == 'GROUPED_LOCAL' and fit['alpha'] == .0025
        and fit['fitted_rootgroups'] == fit['trained_afterstates'] == n and fit['replicates'] == repeats
        and fit['frozen_rootgroup_predictions']
        and fit['sampling_unit'] == 'ROOTGROUP_MEAN_OF_PROVIDED_REPLICAS',
        'joint return learning commits both current heads once per shared group with fixed alpha')
    learning = dict(rootgroup_updates=n, current_predictions=n, table_lookups=64*n,
        table_updates=2*writes, table_update_occurrences=32*n, reward_predictions=n, win_predictions=n,
        reward_table_lookups=32*n, win_table_lookups=32*n,
        reward_table_updates=writes, win_parameter_updates=writes)
    equal_tree(fit['learning_counts'], learning, 'all joint reward and WIN predictions and actual distinct-address writes are paid')
    target = dict(rootgroups_targeted=n, reward_replica_reads=2*repeats*n, win_replica_reads=2*repeats*n,
        reward_target_mean_additions=repeats*n, win_target_mean_additions=repeats*n,
        target_mean_divisions=2*n, replica_noise_residuals=2*repeats*n,
        replica_noise_squares=2*repeats*n, replica_noise_accumulations=2*repeats*n,
        replica_noise_divisions=2, replica_noise_square_roots=2)
    equal_tree(fit['target_counts'], target, 'both joint targets average only their actual training member inputs')
    norm = dict(rootgroups_processed=n, feature_extractions=n, feature_occurrences=32*n,
        feature_digit_reads=192*n, feature_address_multiply_adds=192*n, sort_calls=n, sort_items=32*n,
        denominator_occurrence_visits=32*n, rootgroup_unique_addresses=writes,
        reward_gradient_products=writes, win_gradient_products=writes,
        normalization_divisions=2*writes, parameter_update_multiplications=2*writes,
        rootgroup_parameter_commits=n, reward_rootgroup_commits=n, win_rootgroup_commits=n,
        reward_parameter_writes=writes, win_parameter_writes=writes, native_workspace_bytes=512)
    equal_tree({key:value for key,value in fit['normalization_counts'].items() if key != 'sort_comparisons'}, norm,
        'literal within-root address multiplicity normalizes actual joint gradient commits')
    require(fit['normalization_counts']['sort_comparisons'] > 0, 'the actual native within-root address sort is paid')
    check_representation(fit['representation_counts'], 'LOCAL_RISK', n)
    rm, wm = np.mean(rewards, axis=1), np.mean(wins, axis=1)
    noise = fit['replicate_noise']
    require(noise['definition'] == 'SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'
        and close(noise['reward_replica_rms'], float(np.sqrt(np.mean((rewards-rm[:, None])**2))))
        and close(noise['win_replica_rms'], float(np.sqrt(np.mean((wins-wm[:, None])**2)))),
        'joint training dispersion reads exactly the disjoint FIT member labels')
    for sample, index in ((fit['first_sample'], 0), (fit['last_sample'], n-1)):
        require(sample['rootgroup'] == index and close(sample['reward_target'], rm[index])
            and close(sample['risk_target'], wm[index])
            and close(sample['reward_error'], rm[index]-sample['reward_prediction'])
            and close(sample['risk_error'], wm[index]-sample['risk_probability'])
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(sample['risk_probability']-.5)),
            'every joint epoch boundary uses its actual reward and WIN targets and pre-commit residuals')
    if initial_head is not None:
        r, w = predict_components(roots[:1], initial_head)
        require(close(fit['first_sample']['reward_prediction'], r[0])
            and close(fit['first_sample']['risk_probability'], w[0]),
            'the first joint residual reads its own actual previous head before fitting')
    require(fit['cpu_seconds'] >= 0. and fit['seconds'] >= 0., 'actual joint fit timings remain present')
    return writes


def check_replay_fit(fit, arm, roots, rewards, wins, head):
    joint = arm == 'JOINT_RETURN'
    require(arm in UPDATING_ARMS and fit['alpha'] == .0025
        and fit['distinct_rootgroups'] == GROUPS and fit['epochs'] == EPOCHS
        and fit['fitted_rootgroups'] == GROUPS*EPOCHS and fit['replicates'] == 2
        and fit['method'] == 'REPLAY_GROUPED_'+arm and len(fit['epoch_receipts']) == EPOCHS,
        'both paired learners use the exact same FIT members groups epochs and update quota')
    writes = 0
    epoch_arrays = dict(roots=roots, targetwin=wins, mean_win=np.mean(wins, axis=1))
    for index, epoch in enumerate(fit['epoch_receipts']):
        prior = head if index == 0 else None
        writes += (check_joint_epoch(epoch, roots, rewards, wins, prior) if joint
            else check_win_epoch(epoch, epoch_arrays, prior))
    for field in ('learning_counts', 'target_counts', 'normalization_counts', 'representation_counts'):
        equal_tree(fit[field], sum_counts(e[field] for e in fit['epoch_receipts']),
            'all actual predictions target reads and commits are summed across all sixteen epochs')
    require(fit['cpu_seconds'] >= sum(e['cpu_seconds'] for e in fit['epoch_receipts'])-1e-9
        and fit['seconds'] >= sum(e['seconds'] for e in fit['epoch_receipts'])-1e-9,
        'replay timings include all actual epochs')
    return writes


def check_evaluation(value, life, task, belief, version):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2'
        and value['head_version'] == version and value['static_evaluation_valid'],
        'new natural evaluation uses the declared immutable belief and actual saved head')
    games = value['game_summaries']
    require(len(games) == EPISODES and [game['seed'] for game in games]
        == [evaluation_seed(life, task, episode) for episode in range(EPISODES)],
        'all paired natural games use the fresh V327 evaluation family')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'new whole-game evaluation retains its fixed natural horizon')
        status = game['status']
        require(status in ('WON', 'LOST', 'CUTOFF') and
            (game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE' if status == 'CUTOFF'
             else physical_status(game['final_board']) == status),
            'every retained natural endpoint matches its actual complete physical board')
        bonus = 0. if status == 'CUTOFF' else 4. if status == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'natural utility uses only actual score and terminal result')
    steps, wins = sum(g['steps'] for g in games), sum(g['status'] == 'WON' for g in games)
    expected = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=128,
        raw_tile_productions=steps+128, environment_random_draws=2*(steps+128),
        ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+64,
        ground_status_internal_swipe_calls=4*(steps+64-wins), ground_swipe_calls=steps+4*(steps+64-wins))
    equal_tree(value['counts']['environment'], expected, 'all actual evaluation initial and post-action spawns remain paid')
    planning_counts(value['counts']['planning'], steps, depth=2)
    if version is not None:
        check_representation(value['representation_counts'], 'LOCAL_RISK', value['counts']['planning'].get('value_predictions', 0))
    require(not value['counts'].get('learning', {}) and value['cpu_seconds'] >= 0. and value['seconds'] >= 0.,
        'static evaluation executes no learning and keeps its paid timing')
    return None if any(g['status'] == 'CUTOFF' for g in games) else mean(g['utility'] for g in games)


def check_prediction_metrics(receipt, rewards, probabilities, outcomes, members):
    re = rewards[:, None]-outcomes['reward_return'][:, members]
    we = probabilities[:, None]-outcomes['win'][:, members]
    ue = re+8.*we
    expected = dict(rootgroups=len(rewards), members=list(members), member_count=len(rewards)*len(members),
        reward_mse=float(np.mean(re*re)), win_brier=float(np.mean(we*we)), utility_mse=float(np.mean(ue*ue)),
        reward_bias=float(np.mean(re)), win_bias=float(np.mean(we)), utility_bias=float(np.mean(ue)),
        error_unit='INDIVIDUAL_TERMINAL_SUFFIX_MEMBER', utility_rule='R_PLUS_8_TIMES_WIN_MINUS_HALF')
    equal_tree(receipt, expected, 'training and disjoint validation errors use actual member labels without group-mean noise removal')


def check_prediction_snapshot(stage, arrays, key, roots, head, version):
    labels = stage['prediction_artifact']['metadata']['snapshot_labels']; index = labels.index(key)
    rewards, probabilities = predict_components(roots, head)
    addresses = feature_addresses(roots); logits = np.zeros(len(roots))
    for occurrence in range(32):
        logits += head.terminal[addresses[:, occurrence]]
    actual = dict(rewards=rewards, probabilities=probabilities, logits=logits,
        utilities=rewards+8.*(probabilities-.5))
    for field, expected in actual.items():
        require(arrays[field].shape == (len(labels), GROUPS)
            and np.allclose(arrays[field][index], expected, rtol=1e-12, atol=1e-12),
            'all saved component predictions equal their actual complete weights in literal 32-feature occurrence order')
    receipt = stage['unique_prediction_receipts'][key]
    require(receipt['roots'] == GROUPS and receipt['readonly']
        and receipt['updates_before'] == receipt['updates_after'] == version['updates']
        and receipt['prediction_rule'] == 'ACTUAL_V301_NATIVE_COMPONENT_PREDICTOR_SINGLE_PASS',
        'each unique component snapshot reads its actual frozen head without fitting or duplicate aliases')
    expected = dict(win_predictions=GROUPS, reward_predictions=GROUPS, win_table_lookups=32*GROUPS,
        reward_table_lookups=32*GROUPS, feature_extractions=GROUPS, feature_occurrences=32*GROUPS,
        feature_digit_reads=192*GROUPS, feature_address_multiply_adds=192*GROUPS, fit_updates=0, parameter_writes=0)
    equal_tree(receipt['counts'], expected, 'all actual snapshot feature extraction and reward WIN reads are paid once')
    check_representation(receipt['representation_counts'], 'LOCAL_RISK', GROUPS)
    require(receipt['cpu_seconds'] >= 0. and receipt['seconds'] >= 0., 'actual component prediction timing is retained')
    return rewards, probabilities


def check_interval(value, values):
    require(len(values) == 16 and close(value['mean'], mean(values)), 'all sixteen signed reused-cohort utility effects remain present')
    equal_tree(value['lifecycle_values'], {str(i): number for i, number in enumerate(values)},
        'the effect vector retains every positive equal and adverse retained learning history')
    equal_tree(value['parent_mean_values'], {str(p): mean(values[p::4]) for p in range(4)},
        'all four actual fixed source parent means remain in the effect')
    require(value['positive_equal_negative'] == [sum(x > 0 for x in values), sum(x == 0 for x in values), sum(x < 0 for x in values)],
        'effect direction counts retain adverse histories')
    lo, hi = value['ci95']; minimum = mean(min(values[p::4]) for p in range(4)); maximum = mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= lo <= hi <= maximum+1e-10
        and value['interval_scope'] == INTERVAL_SCOPE and value['status95'] == effect_status(value, True),
        'interval range sign and scope remain conditional on the retained V326 cohort')


def check_lifecycle(row, previous, source_weights, checkpoint):
    life, parent = row['lifecycle'], row['parent']
    require(life == previous['lifecycle'] and parent == previous['parent'] == life % 4,
        'joint intervention retains all actual V326 lifecycle and frozen source parent identities')
    heads, teachers, versions, beliefs = {}, {}, {}, {}
    records, counts = dict(lifecycle=life, parent=parent, cells={}), Counter()
    for task in TASKS:
        require(set(row['head_setups'][task]) == {'FIRST_LOCAL', *UPDATING_ARMS}, 'each task restores one FIRST and copies two actual private learner heads')
        for arm,setup in row['head_setups'][task].items():
            work = setup['setup_counts']; size = source_weights.size
            require(work['source_parameters_copied'] == size and work['source_weight_bytes_copied'] == 8*size
                and work['allocated_weight_parameters'] == 2*size and work['allocated_weight_bytes'] == 16*size
                and work['initialized_zero_risk_parameters'] == size and setup['private_weight_bytes'] == 16*size,
                'all actual restored and learner heads pay their two complete table allocations')
            if arm == 'FIRST_LOCAL':
                equal_tree(setup['restored_version'], previous['initial'][task]['head_version'], 'FIRST restore uses only the actual audited v0')
                require(setup['restore_cpu_seconds'] >= 0., 'actual FIRST sparse restoration CPU is paid')
            else:
                require(work['first_parameters_copied'] == 2*size and work['first_weight_bytes_copied'] == 16*size, 'both actual learner heads copy the complete same FIRST tables')
            require(setup['cpu_seconds'] >= 0. and setup['wall_seconds'] >= 0., 'actual head setup timings remain present')
    for task in TASKS:
        first, old = row['initial'][task], previous['initial'][task]
        for field in ('context_id', 'head_version', 'planning_belief'):
            equal_tree(first[field], old[field], 'actual audited FIRST bank version and FIT belief are reused without refitting')
        version = first['head_version']; identity = dict(lifecycle=life, parent=parent, context_id=first['context_id'])
        teacher = HeadVersions(source_weights, checkpoint, dict(identity, arm='FIRST_LOCAL'), 'LOCAL_RISK')
        teacher.apply(version); teachers[task] = teacher
        heads[task], versions[task] = {}, {arm:version for arm in UPDATING_ARMS}
        for arm in UPDATING_ARMS:
            head = HeadVersions(source_weights, checkpoint, dict(identity, arm=arm), 'LOCAL_RISK')
            head.apply(version); heads[task][arm] = head
        beliefs[task] = first['planning_belief']['estimated_p_four']
        require(set(first['evaluations']) == {'SOURCE', 'FIRST_LOCAL'}, 'all fresh SOURCE and own-FIRST natural controls are present')
        records['cells']['FIRST_'+task] = {arm:check_evaluation(value, life, task, beliefs[task],
            None if arm == 'SOURCE' else version) for arm,value in first['evaluations'].items()}
    for number in (1, 2):
        r = str(number)
        for task in TASKS:
            stage, old = row['rounds'][r][task], previous['rounds'][r][task]
            first = row['initial'][task]['head_version']; roots_receipt = stage['source_group_artifact']; tails_receipt = stage['source_outcome_artifact']
            require(stage['groups'] == GROUPS and stage['replicas'] == REPLICAS and stage['epochs'] == EPOCHS
                and stage['fit_members'] == list(TRAIN_MEMBERS) and stage['validation_members'] == list(HELDOUT_MEMBERS)
                and stage['teacher_version'] == first and set(stage['arms']) == set(UPDATING_ARMS),
                'both paired learners use exactly the retained roots and disjoint two-member FIT/validation split')
            equal_tree(roots_receipt, old['shared_supervision']['group_artifact'], 'all retained roots and physical first members come from the independently audited V326 cohort')
            equal_tree(tails_receipt, old['continuation']['outcome_artifact'], 'all retained terminal targets come from the actual independently audited suffix outcomes')
            groups = artifact_arrays(roots_receipt, (*GROUP_FIELDS, 'terminal_win', 'mean_terminal_win'), roots_receipt['metadata'])
            outcomes = artifact_arrays(tails_receipt, tuple(f for f in DENSE_FIELDS if f != 'original_group_indices'), tails_receipt['metadata'])
            rewards, wins = training_labels(outcomes); roots = groups['roots']
            require(roots.shape == (GROUPS, 16) and np.array_equal(groups['terminal_win'], outcomes['win'])
                and np.array_equal(groups['mean_terminal_win'], np.mean(outcomes['win'], axis=1))
                and np.array_equal(outcomes['reward_return'], outcomes['scores']/2048.)
                and np.array_equal(outcomes['win'], (outcomes['status'] == 1).astype(np.float64))
                and np.array_equal(outcomes['utility'], outcomes['reward_return']+8.*(outcomes['win']-.5)),
                'actual complete suffix scores and natural outcomes bind the joint labels without new simulation')
            statuses = {name:int(np.count_nonzero(outcomes['status'] == code)) for name,code in (('WON',1),('LOST',-1),('CUTOFF',0))}
            equal_tree(stage['terminal_status_counts'], statuses, 'all retained successful and adverse suffix endpoints remain present')
            labels = ['FIRST']+[key for arm in UPDATING_ARMS for key in ((arm+'_BEFORE',arm+'_AFTER') if number == 2 else (arm+'_AFTER',))]
            snapshot_versions = dict(FIRST=first, **({arm+'_BEFORE':versions[task][arm] for arm in UPDATING_ARMS} if number == 2 else {}),
                **{arm+'_AFTER':stage['arms'][arm]['head_version'] for arm in UPDATING_ARMS})
            metadata = dict(schema='acfqp.joint_terminal_predictions.v327', lifecycle=life, parent=parent, task=task,
                round=number, roots=GROUPS, snapshot_labels=labels, head_versions=snapshot_versions,
                source_group_file=roots_receipt['file'], source_outcome_file=tails_receipt['file'],
                fit_members=list(TRAIN_MEMBERS), validation_members=list(HELDOUT_MEMBERS))
            predictions = artifact_arrays(stage['prediction_artifact'], ('rewards','probabilities','logits','utilities'), metadata)
            require(list(stage['unique_prediction_receipts']) == labels, 'each actual prediction snapshot occurs once in its declared native execution order')
            first_prediction = check_prediction_snapshot(stage, predictions, 'FIRST', roots, teachers[task], first)
            for split,members in (('train',TRAIN_MEMBERS),('validation',HELDOUT_MEMBERS)):
                check_prediction_metrics(stage['first_prediction_metrics'][split], *first_prediction, outcomes, members)
            read = stage['source_read']
            equal_tree(read['counts'],dict(group_files_read=1,outcome_files_read=1,rootgroups_read=GROUPS,retained_suffix_members_read=GROUPS*REPLICAS,
                selected_array_bytes=roots.nbytes+groups['terminal_win'].nbytes+outcomes['reward_return'].nbytes+outcomes['win'].nbytes+outcomes['status'].nbytes),
                'retained target read inventory includes only the arrays actually consumed by the new learner')
            require(read['compressed_bytes_referenced'] == roots_receipt['saved_bytes']+tails_receipt['saved_bytes']
                and read['cpu_seconds'] >= 0. and read['wall_seconds'] >= 0.,'actual retained target reading keeps its paid bytes reference and timing')
            cell = dict(records['cells']['FIRST_'+task]); before_predictions = {}
            for arm in UPDATING_ARMS:
                key = 'FIRST' if number == 1 else arm+'_BEFORE'
                before_predictions[arm] = check_prediction_snapshot(stage,predictions,key,roots,heads[task][arm],versions[task][arm]) if number == 2 else (
                    predictions['rewards'][0], predictions['probabilities'][0])
            for arm in UPDATING_ARMS:
                item, head = stage['arms'][arm], heads[task][arm]; version = item['head_version']
                require(item['updates_before'] == versions[task][arm]['updates'] == head.receipts[-1]['updates']
                    and item['updates_after'] == version['updates'] == item['updates_before']+GROUPS*EPOCHS,
                    'each private learner advances its own chronological actual sparse chain through the same update quota')
                writes = check_replay_fit(item['fit'], arm, roots, rewards, wins, head)
                head.apply(version); versions[task][arm] = version
                if arm == 'WIN_ONLY':
                    require(item['reward_unchanged'] and version['reward_indices_count'] == 0
                        and np.array_equal(head.reward, teachers[task].reward),
                        'WIN-only keeps the entire actual FIRST reward table unchanged')
                else:
                    require(item['reward_unchanged'] == np.array_equal(head.reward, teachers[task].reward),
                        'joint reward invariance receipt reports the actual complete table comparison')
                expected_keys = dict(before='FIRST' if number == 1 else arm+'_BEFORE', after=arm+'_AFTER')
                equal_tree(item['prediction_keys'], expected_keys, 'FIT and validation metrics refer to their actual preceding and fitted snapshots')
                after_prediction = check_prediction_snapshot(stage,predictions,arm+'_AFTER',roots,head,version)
                for point, values in (('before',before_predictions[arm]),('after',after_prediction)):
                    for split,members in (('train',TRAIN_MEMBERS),('validation',HELDOUT_MEMBERS)):
                        check_prediction_metrics(item['prediction_metrics'][point][split], *values, outcomes, members)
                cell[arm] = check_evaluation(item['evaluations'],life,task,beliefs[task],version)
                counts.update(fitted_rootgroups=GROUPS*EPOCHS, actual_win_parameter_writes=writes,
                    actual_reward_parameter_writes=writes if arm == 'JOINT_RETURN' else 0,
                    new_head_files=1,new_head_saved_bytes=version['saved_bytes'])
            require(stage['win_weights_identical'] and stage['win_table_parameters_compared'] == source_weights.size
                and np.array_equal(heads[task]['WIN_ONLY'].terminal, heads[task]['JOINT_RETURN'].terminal),
                'complete paired WIN tables remain bit-exact after the same real two-member target trajectory')
            require(stage['first_unchanged'], 'the reused FIRST teacher remains frozen throughout the intervention')
            records['cells']['ROUND'+r+'_'+task] = cell
            counts.update(reused_rootgroups=GROUPS, reused_terminal_members=GROUPS*REPLICAS,
                training_terminal_members=GROUPS*len(TRAIN_MEMBERS), validation_terminal_members=GROUPS*len(HELDOUT_MEMBERS),
                literal_component_predictions=GROUPS*len(labels), prediction_artifacts=1,
                prediction_saved_bytes=stage['prediction_artifact']['saved_bytes'])
    equal_tree(row['final_head_versions'],versions,'both actual final bank pointers retain their own sparse chains')
    return records, counts


def check_prediction_summary(summary, rows):
    fields = ('reward_mse','win_brier','utility_mse','reward_bias','win_bias','utility_bias')
    cells = {}
    for r in ('1','2'):
        for task in TASKS:
            stages = [row['rounds'][r][task] for row in rows]
            first = {split:{field:mean(s['first_prediction_metrics'][split][field] for s in stages) for field in fields}
                for split in ('train','validation')}
            arms = {}
            for arm in UPDATING_ARMS:
                points = {point:{split:{field:mean(s['arms'][arm]['prediction_metrics'][point][split][field] for s in stages)
                    for field in fields} for split in ('train','validation')} for point in ('before','after')}
                points['change'] = {split:{field:points['after'][split][field]-points['before'][split][field] for field in fields} for split in ('train','validation')}
                points['after_minus_FIRST'] = {split:{field:points['after'][split][field]-first[split][field] for field in fields} for split in ('train','validation')}
                arms[arm] = points
            cells['ROUND'+r+'_'+task] = dict(FIRST_LOCAL=first,arms=arms)
    equal_tree(summary,dict(cells=cells,estimator='EQUAL_LIFECYCLES_WITHIN_TASK_ROUND',
        inference='DESCRIPTIVE_PAIRED_SUFFIX_ERRORS_NO_UTILITY_GATE_OR_UNSEEN_ROOT_GENERALIZATION'),
        'all descriptive FIT and member-validation errors retain equal sixteen-life means independently of the utility gate')


def check_analysis(summary, records, rows):
    cutoffs, terminal_cutoffs, actual, members = [], [], [], 0
    for row,record in zip(rows,records):
        endpoints = {}
        for task in TASKS:
            stages = [('FIRST',row['initial'][task]['evaluations'])]+[('ROUND'+r,{arm:item['evaluations']
                for arm,item in row['rounds'][r][task]['arms'].items()}) for r in ('1','2')]
            for checkpoint,evaluations in stages:
                key=checkpoint+'_'+task
                endpoints[key]={arm:{status:sum(g['status']==status for g in value['game_summaries'])
                    for status in ('WON','LOST','CUTOFF')} for arm,value in evaluations.items()}
                cutoffs.extend(dict(lifecycle=row['lifecycle'],task=task,checkpoint=checkpoint,arm=arm,seed=g['seed'])
                    for arm,value in evaluations.items() for g in value['game_summaries'] if g['status']=='CUTOFF')
            for r in ('1','2'):
                status=row['rounds'][r][task]['terminal_status_counts'];members+=sum(status.values())
                if status['CUTOFF']:
                    terminal_cutoffs.append(dict(lifecycle=row['lifecycle'],task=task,round=int(r),count=status['CUTOFF']))
        actual.append(dict(record,retained_endpoint_counts=endpoints,failure=row.get('failure')))
    equal_tree(summary['by_lifecycle'],actual,'all actual fresh control means adverse natural outcomes and retained cohort identities stay in analysis')
    complete=not cutoffs and not terminal_cutoffs
    require(summary['primary_contrast']=='JOINT_RETURN_minus_FIRST_LOCAL_FINAL_AB'
        and summary['physical_evaluation_games']==12288
        and summary['cutoffs']==cutoffs and summary['terminal_cutoffs']==terminal_cutoffs
        and summary['complete_game_endpoints']==complete and summary['complete_retained_target_cohort']==complete
        and summary['physical_new_terminal_supervision_members']==0
        and summary['reused_terminal_supervision_members']==members==262144
        and summary['new_training_raw_tiles']==0 and not summary['new_target_learning_histories']
        and summary['reused_target_cohort'] and not summary['source_histories_repeated']
        and not summary['independent_SOURCE'] and not summary['independent_learning_confirmation']
        and summary['same_root_member_target_ablation'] and summary['same_suffix_value_pairing']
        and summary['matched_optimization_quota'] and not summary['equal_total_raw_efficiency_evaluated']
        and summary['bootstrap_executed']==complete and summary['bootstrap_seed']==32700001
        and summary['bootstrap_draws']==20000
        and summary['bootstrap_unit']=='PAIRED_RETAINED_TARGET_LEARNING_LIFECYCLE_WITHIN_FIXED_SOURCE_PARENT',
        'the sole own-FIRST primary uses the retained cohort and fresh evaluation without a new-learning confirmation or equal-raw claim')
    names={a+'_minus_'+b for a,b in PAIRS}
    require(set(summary['round_ab_contrasts'])=={'1','2'} and set(summary['task_contrasts'])==
        {'ROUND'+r+'_'+task for r in ('1','2') for task in TASKS},'both fixed rounds and all A/B checkpoints remain explicit')
    def view(values,r,tasks):
        require(set(values)==names,'all six actual utility control and component-intervention contrasts remain present')
        means={arm:[mean(record['cells']['ROUND'+r+'_'+t][arm] for t in tasks) for record in records] for arm in ARMS}
        for left,right in PAIRS:
            if complete:check_interval(values[left+'_minus_'+right],[a-b for a,b in zip(means[left],means[right])])
            else:require(values[left+'_minus_'+right] is None,'an unfinished natural game suppresses every utility interval')
    for r in ('1','2'):
        view(summary['round_ab_contrasts'][r],r,TASKS)
        for task in TASKS:
            key='ROUND'+r+'_'+task;view(summary['task_contrasts'][key],r,(task,))
            equal_tree(summary['checkpoint_contrasts'][key],{arm:summary['task_contrasts'][key][arm+'_minus_FIRST_LOCAL'] for arm in UPDATING_ARMS},
                'task retention uses its own actual fresh FIRST contrast')
    equal_tree(summary['final_ab_contrasts'],summary['round_ab_contrasts']['2'],'the final primary remains its fixed second-round endpoint')
    primary=summary['final_ab_contrasts']['JOINT_RETURN_minus_FIRST_LOCAL'];equal_tree(summary['primary'],primary,'the sole primary cannot be replaced by a favorable source or WIN-only contrast')
    hold='HOLD_TERMINAL_CUTOFF' if terminal_cutoffs else 'HOLD_CUTOFF'
    def status(value,retention=False):return effect_status(value,True,retention) if complete else hold
    primary_status=status(primary);retention={task:status(summary['checkpoint_contrasts']['ROUND2_'+task]['JOINT_RETURN'],True) for task in TASKS}
    contribution=status(summary['final_ab_contrasts']['JOINT_RETURN_minus_WIN_ONLY'])
    retained=primary_status=='SUPPORTED_GAIN' and all(value=='SUPPORTED_NONDECREASE' for value in retention.values())
    route='HOLD_INCOMPLETE_EVIDENCE' if not complete else 'ADVANCE_TO_NEW_COHORT_CONFIRMATION' if retained else 'STOP_FIXED_FIRST_TERMINAL_REGRESSION'
    expected=dict(primary_status=primary_status,primary_self_improvement_status=primary_status,
        primary_self_improvement_supported=primary_status=='SUPPORTED_GAIN',task_retention_status=retention,
        retained_improvement_supported=retained,joint_reward_contribution_status=contribution,
        joint_reward_contribution_supported=contribution=='SUPPORTED_GAIN',retained_joint_mechanism_supported=retained and contribution=='SUPPORTED_GAIN',
        win_only_self_improvement_status=status(summary['final_ab_contrasts']['WIN_ONLY_minus_FIRST_LOCAL']),
        final_net_gain_status=status(summary['final_ab_contrasts']['JOINT_RETURN_minus_SOURCE']),
        fixed_teacher_regression_route=route,next_route=route)
    equal_tree({key:summary[key] for key in expected},expected,'net gain both task-retention conditions and the frozen stop route remain separate from prediction fit')
    if complete:check_prediction_summary(summary['prediction_error_summary'],rows)
    else:require(summary['prediction_error_summary'] is None,'unfinished evidence cannot acquire descriptive complete-cohort metrics')
    require(summary['secondary_interval_scope']=='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        'nominal secondary effects do not become additional primary confirmations')


def expected_configuration(source):
    return dict(schema='acfqp.joint_terminal_freeze.v327',source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/JOINT_TERMINAL_V327.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),arms=list(ARMS),updating_arms=list(UPDATING_ARMS),rounds=[1,2],
        groups=GROUPS,retained_members=REPLICAS,fit_members=list(TRAIN_MEMBERS),validation_members=list(HELDOUT_MEMBERS),fit_replicates=2,epochs=EPOCHS,alpha=.0025,
        rootgroup_updates_per_arm_task_round=GROUPS*EPOCHS,
        initial='ACTUAL_V326_FIRST_V0_RESTORE_NO_OLD_UPDATED_HEADS',targets='PAIRED_SAME_V326_FULL_SUFFIX_REWARD_RETURN_AND_WIN',
        target_policy='SAVED_DIRECT_THEN_IMMUTABLE_FIRST_H2_TRUE_WORLD',
        reward_contract='WIN_ONLY_COMPLETE_FIRST_REWARD_FROZEN_JOINT_RETURN_REWARD_LEARNED',
        win_contract='COMPLETE_WIN_TABLES_BIT_EXACT_EQUAL_BOTH_ARMS_AFTER_EVERY_STAGE',
        update='SIXTEEN_FIXED_ORDER_PASSES_TWO_REAL_MEMBERS_NO_DUPLICATION',
        validation='MEMBERS_TWO_THREE_UNUSED_BY_THESE_RETRAINED_MODELS_SAME_OBSERVED_ROOTS',
        prediction='ACTUAL_NATIVE_COMPONENTS_FIRST_BEFORE_AFTER_UNIQUE_SNAPSHOTS',planning_belief='ACTUAL_IMMUTABLE_V326_FIRST_BANK_BELIEF',
        true_probabilities={'A':.1,'B':.5},new_training_raw_tiles=0,new_source_fits=0,new_FIRST_fits=0,
        expected_fit_member_uses_per_arm=131072,expected_rootgroup_updates_per_arm=1048576,
        max_steps=8192,evaluation_games_per_cell=EPISODES,seed_evaluation=3279000000000,
        expected_new_evaluation_games=12288,reused_evaluation_games=0,bootstrap_draws=20000,bootstrap_seed=32700001,
        primary='JOINT_RETURN_minus_FIRST_LOCAL_FINAL_AB',target_combination_contribution='JOINT_RETURN_minus_WIN_ONLY_FINAL_AB',
        retention='FINAL_JOINT_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',route_if_retained_gain='ADVANCE_TO_NEW_COHORT_CONFIRMATION',
        route_otherwise='STOP_FIXED_FIRST_TERMINAL_REGRESSION',stop_rule='ANY_NATURAL_GAME_OR_RETAINED_SUFFIX_CUTOFF_GLOBAL_HOLD_NO_TUNING_OR_REPLACEMENT',
        evidence_scope='RETRAINED_V326_COHORT_MECHANISM_INTERVENTION_NEW_NATURAL_GAMES_NOT_NEW_LEARNING_CONFIRMATION')


def check_accounting(document, inherited, execution):
    account=document['accounting'];rows=document['by_lifecycle']
    stages=[row['rounds'][r][task] for row in rows for r in ('1','2') for task in TASKS]
    items=[stage['arms'][arm] for stage in stages for arm in UPDATING_ARMS]
    evaluations=[value for row in rows for task in TASKS for value in row['initial'][task]['evaluations'].values()]+[item['evaluations'] for item in items]
    predictions=[value for stage in stages for value in stage['unique_prediction_receipts'].values()]
    worker=sum(parent['cpu_seconds'] for parent in document['parent_receipts']);compiler=sum(parent['compiler_cpu_seconds'] for parent in document['parent_receipts'])
    component=worker+compiler+account['coordinator_cpu_seconds']
    per_arm={arm:dict(rootgroup_updates=sum(s['arms'][arm]['fit']['fitted_rootgroups'] for s in stages),
        fit_cpu_seconds=sum(s['arms'][arm]['fit']['cpu_seconds'] for s in stages),
        **{field:sum_counts(s['arms'][arm]['fit'][field] for s in stages) for field in
            ('learning_counts','normalization_counts','target_counts','representation_counts')}) for arm in UPDATING_ARMS}
    expected=dict(new_training_raw_tiles=0,new_source_fits=0,new_FIRST_fits=0,source_training_repeated=False,
        first_adaptation_repeated=False,old_full_physics_audit_repeated=False,reused_target_cohort=True,
        new_target_learning_histories=False,equal_total_raw_efficiency_test=False,retained_member_reads=262144,
        reused_fit_members_per_arm=131072,reused_validation_members=131072,new_fit_rootgroup_updates=2097152,per_arm=per_arm,
        retained_target_read_counts=sum_counts(s['source_read']['counts'] for s in stages),
        retained_target_read_cpu_seconds=sum(s['source_read']['cpu_seconds'] for s in stages),
        new_prediction_roots=262144,new_prediction_counts=sum_counts(p['counts'] for p in predictions),
        new_prediction_representation_counts=sum_counts(p['representation_counts'] for p in predictions),
        new_prediction_cpu_seconds=sum(p['cpu_seconds'] for p in predictions),
        win_table_parameters_compared=sum(s['win_table_parameters_compared'] for s in stages),
        new_evaluation_games=12288,reused_evaluation_games=0,
        new_evaluation_environment_counts=sum_counts(e['counts']['environment'] for e in evaluations),
        new_evaluation_planning_counts=sum_counts(e['counts']['planning'] for e in evaluations),
        split_evaluation_representation_counts=sum_counts(e.get('representation_counts',{}) for e in evaluations),
        new_evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations),new_head_files=128,
        new_head_saved_bytes=sum(item['head_version']['saved_bytes'] for item in items),prediction_files=64,
        prediction_saved_bytes=sum(s['prediction_artifact']['saved_bytes'] for s in stages),
        worker_cpu_seconds=worker,compiler_cpu_seconds=compiler,new_experiment_component_cpu_seconds=component,
        inherited_source_v326_actual_full_cpu_seconds=inherited,
        economic_source_v326_and_experiment_component_cpu_seconds=inherited+component)
    equal_tree({key:account[key] for key in expected},expected,'all new retained reads fits predictions and natural evaluations plus actual SOURCE/V326 costs are charged exactly once')
    require(execution['exit_code']==0 and execution['process_tree_cpu_seconds']+1e-6 >= component
        and account['wall_seconds']>0. and account['coordinator_cpu_seconds']>=0.
        and 'including its failed scientific' in account['cost_scope'] and 'Audit separate' in account['cost_scope'],
        'actual full process-tree cost includes serialization and the inherited failed experiment without charging audits as training')


def check_parent(source, rows, previous):
    weights=read_source_weights(source['checkpoint']);records=[];counts=Counter()
    for row in rows:
        record,checked=check_lifecycle(row,previous[row['lifecycle']],weights,source['checkpoint'])
        records.append(record);counts.update(checked)
        print(json.dumps(dict(event='independent_joint_terminal_life_checked',lifecycle=row['lifecycle'])),flush=True)
    return records,counts


def audit(directory):
    directory=Path(directory).resolve();document=json_file(directory/'summary.json')
    require(document['schema']=='acfqp.joint_terminal.v327' and document['status'] in ('EXPERIMENT_COMPLETE','HOLD_CUTOFF')
        and document['scientific_gate']=='FIXED_FIRST_TERMINAL_REGRESSION_LAST_MECHANISM_TEST_NOT_U006',
        'joint intervention preserves its final fixed-FIRST mechanism scope without claiming U006')
    source=Path(document['source_summary']).resolve();previous=json_file(source)
    old_audit=json_file(source.parent/'audit.json');old_execution=json_file(source.parent/'execution.json');old_costs=json_file(source.parent/'audit_costs.json')
    require(previous['schema']=='acfqp.terminal_win.v326' and previous['status']=='EXPERIMENT_COMPLETE'
        and old_audit['status']=='PASS' and old_audit['independent_valid'] and old_execution['exit_code']==0,
        'the actual retained cohort and all old suffix targets already passed their complete independent physics audit')
    inherited=old_execution['process_tree_cpu_seconds']+previous['accounting']['inherited_successful_source_full_cpu_seconds']
    require(close(old_costs['full_economic_source_and_experiment_cpu_seconds'],inherited)
        and close(old_audit['full_economic_source_and_experiment_cpu_seconds'],inherited),
        'actual SOURCE and full V326 execution cost is inherited once rather than adding the same SOURCE twice')
    equal_tree(document['source_provenance'],previous['source_provenance'],'all four actual old source checkpoint identities remain unchanged')
    configuration=expected_configuration(source)
    equal_tree(json_file(directory/'configuration.json'),configuration,'member partition actual two-member quota fresh seeds and stop route were frozen before fitting')
    equal_tree(document['settings'],configuration,'completed joint intervention keeps the frozen candidate contract')
    rows=document['by_lifecycle'];parents=document['parent_receipts']
    require([r['lifecycle'] for r in rows]==list(range(16)) and [p['parent'] for p in parents]==list(range(4)),
        'all retained learning histories and four workers remain present without selecting favorable lives')
    old={r['lifecycle']:r for r in previous['by_lifecycle']};sources={s['parent']:s for s in previous['source_provenance']['parents']}
    records=[];counts=Counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(check_parent,sources[p],[r for r in rows if r['parent']==p],old) for p in range(4)]
        for job in as_completed(jobs):
            values,checked=job.result();records.extend(values);counts.update(checked)
    records.sort(key=lambda r:r['lifecycle']);check_analysis(document['summary'],records,rows)
    require(document['status']==('EXPERIMENT_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'),
        'an unfinished natural game cannot yield a completed mechanism verdict')
    require((directory/'stderr.log').stat().st_size==0,'completed new producer retains empty stderr')
    execution=json_file(directory/'execution.json');check_accounting(document,inherited,execution)
    require(counts['reused_rootgroups']==65536 and counts['reused_terminal_members']==262144
        and counts['training_terminal_members']==counts['validation_terminal_members']==131072
        and counts['fitted_rootgroups']==2097152 and counts['literal_component_predictions']==262144
        and counts['new_head_files']==128 and counts['prediction_artifacts']==64,
        'actual reconstructed labels predictions and private head files close all declared finite budgets')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,**dict(counts),
        previous_v326_audit_status=old_audit['status'],prior_full_physics_audit_repeated=False,
        no_new_training_raw_tiles_valid=True,actual_member_disjoint_terminal_reward_WIN_targets_valid=True,
        complete_sparse_chains_and_WIN_ONLY_FIRST_reward_invariance_valid=True,
        complete_paired_WIN_weight_equality_valid=True,all_actual_native_predictions_match_literal_features_valid=True,
        actual_two_member_epoch_targets_noise_counts_and_boundary_predictions_valid=True,
        individual_validation_MSE_and_return_WIN_covariance_valid=True,
        fresh_paired_natural_game_endpoints_counts_and_effect_vectors_valid=True,
        fixed_stop_or_new_cohort_confirmation_route_valid=True,source_v326_cost_inherited_once_valid=True,
        complete_game_endpoints=document['summary']['complete_game_endpoints'],primary_status=document['summary']['primary_status'],
        retained_improvement_supported=document['summary']['retained_improvement_supported'],next_route=document['summary']['next_route'],
        new_experiment_component_cpu_seconds=document['accounting']['new_experiment_component_cpu_seconds'],
        new_experiment_full_cpu_seconds=execution['process_tree_cpu_seconds'],
        full_economic_source_and_experiment_cpu_seconds=inherited+execution['process_tree_cpu_seconds'],
        limitations='Existing V326 physics audit is trusted; small actual group/outcome arrays and all actual FIRST/new sparse heads are read. '
            'Every snapshot is independently recomputed in literal 32-feature order. FIT member targets, epoch boundaries/counts and complete '
            'WIN table equality are checked without refitting the full learner. Every new natural evaluation endpoint, paid work and paired '
            'effect vector is checked; natural action histories and bootstrap draws are not rerun. Members 2/3 are held out only from '
            'these new fits at the same observed roots. Fixed source parents and retained V326 learning cohort make this a development '
            'mechanism intervention, not independent learning confirmation, unseen-root generalization, equal-raw efficiency or U006.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=audit(args.directory)
    (args.output or args.directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_joint_terminal_audit_complete',status=result['status'],
        primary_status=result['primary_status'],next_route=result['next_route'])),flush=True)


if __name__=='__main__':main()
