"""Joint terminal-value intervention on retained roots with fresh natural evaluation."""
import random

import numpy as np

TASKS = ('A', 'B')
ROUNDS = ('1', '2')
INITIAL_ARMS = ('SOURCE', 'FIRST_LOCAL')
UPDATING_ARMS = ('WIN_ONLY', 'JOINT_RETURN')
ARMS = INITIAL_ARMS + UPDATING_ARMS
PAIRS = (('JOINT_RETURN', 'FIRST_LOCAL'), ('JOINT_RETURN', 'WIN_ONLY'),
    ('JOINT_RETURN', 'SOURCE'), ('WIN_ONLY', 'FIRST_LOCAL'),
    ('WIN_ONLY', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
PRIMARY = 'JOINT_RETURN_minus_FIRST_LOCAL_FINAL_AB'
BOOTSTRAP_SEED = 32700001
EVALUATION_SEED = 3279000000000
GAMES_PER_CELL = 64
GROUPS, REPLICAS, EPOCHS = 1024, 4, 16
TRAIN_MEMBERS, VALIDATION_MEMBERS = (0, 1), (2, 3)
FITTED_GROUPS = GROUPS * EPOCHS
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_SOURCE_PARENTS_AND_RETAINED_V326_TARGET_COHORT'


def prediction_metrics(reward_predictions, win_predictions, reward_targets, win_targets, members):
    """Measure individual suffix errors; member holdout does not hold out roots."""
    reward = np.asarray(reward_predictions, dtype=np.float64)
    win = np.asarray(win_predictions, dtype=np.float64)
    target_reward = np.asarray(reward_targets, dtype=np.float64)
    target_win = np.asarray(win_targets, dtype=np.float64)
    members = tuple(members)
    if (reward.ndim != 1 or win.shape != reward.shape or not len(reward) or
            target_reward.shape != (len(reward), REPLICAS) or target_win.shape != target_reward.shape or
            members not in (TRAIN_MEMBERS, VALIDATION_MEMBERS)):
        raise ValueError('V327 predictions use complete roots and the frozen fit or validation members')
    if not all(np.all(np.isfinite(value)) for value in (reward, win, target_reward, target_win)):
        raise ValueError('V327 unfinished terminal targets cannot enter prediction metrics')
    reward_error = reward[:, None] - target_reward[:, members]
    win_error = win[:, None] - target_win[:, members]
    utility_error = reward_error + 8. * win_error
    return dict(rootgroups=len(reward), members=list(members), member_count=len(reward)*len(members),
        reward_mse=float(np.mean(reward_error**2)), win_brier=float(np.mean(win_error**2)),
        utility_mse=float(np.mean(utility_error**2)), reward_bias=float(np.mean(reward_error)),
        win_bias=float(np.mean(win_error)), utility_bias=float(np.mean(utility_error)),
        error_unit='INDIVIDUAL_TERMINAL_SUFFIX_MEMBER', utility_rule='R_PLUS_8_TIMES_WIN_MINUS_HALF')


def _samples(rows, draws):
    groups = [[index for index, row in enumerate(rows) if row['parent'] == parent] for parent in range(4)]
    rng = random.Random(BOOTSTRAP_SEED)
    return np.asarray([[rng.choices(group, k=4) for group in groups] for _ in range(draws)], dtype=np.int64)


def _status(interval, hold=None, retention=False):
    if hold:
        return hold
    lo, hi = interval['ci95']
    if lo >= 0 if retention else lo > 0:
        return 'SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN'
    return 'SUPPORTED_LOSS' if hi < 0 else 'UNRESOLVED'


def _interval(rows, values, samples):
    values = np.asarray(values, dtype=np.float64)
    distribution = values[samples].mean(axis=2).mean(axis=1)
    result = dict(mean=float(values.mean()), ci95=np.quantile(distribution, [.025, .975]).tolist(),
        lifecycle_values={str(row['lifecycle']): float(value) for row, value in zip(rows, values)},
        parent_mean_values={str(parent): float(np.mean([value for row, value in zip(rows, values)
            if row['parent'] == parent])) for parent in range(4)},
        positive_equal_negative=[int(np.sum(values > 0)), int(np.sum(values == 0)), int(np.sum(values < 0))],
        interval_scope=INTERVAL_SCOPE)
    result['status95'] = _status(result)
    return result


def _head_identity(version, row, task):
    if (version['schema'] != 'acfqp.head_version.v313' or version['head_kind'] != 'LOCAL_RISK' or
            version['lifecycle'] != row['lifecycle'] or version['parent'] != row['parent'] or
            version['context_id'] != row['initial'][task]['context_id']):
        raise ValueError('V327 uses the retained lifecycle and confirmed task bank')


def _fit_contract(fit, groups, arm):
    counts = fit['learning_counts']
    if (fit['alpha'] != .0025 or fit['fitted_rootgroups'] != groups or fit['replicates'] != 2 or
            any(counts[key] != groups for key in ('rootgroup_updates', 'current_predictions', 'win_predictions'))):
        raise ValueError('V327 both learners use two fit members and the same frozen update quota')
    reward_predictions = counts.get('reward_predictions', 0)
    reward_writes = fit['normalization_counts'].get('reward_parameter_writes', 0)
    if arm == 'WIN_ONLY':
        if reward_predictions or reward_writes:
            raise ValueError('V327 WIN_ONLY performs no reward prediction or update while fitting')
    elif reward_predictions != groups or reward_writes <= 0:
        raise ValueError('V327 JOINT_RETURN updates both terminal return and WIN')


def _metric_contract(metrics, members):
    if (metrics['rootgroups'] != GROUPS or metrics['members'] != list(members) or
            metrics['member_count'] != GROUPS*len(members) or
            metrics['error_unit'] != 'INDIVIDUAL_TERMINAL_SUFFIX_MEMBER' or
            metrics['utility_rule'] != 'R_PLUS_8_TIMES_WIN_MINUS_HALF' or
            any(not np.isfinite(metrics[key]) for key in
                ('reward_mse', 'win_brier', 'utility_mse', 'reward_bias', 'win_bias', 'utility_bias'))):
        raise ValueError('V327 prediction errors preserve the frozen train and validation partitions')


def _complete_contract(row, reasons):
    life = row['lifecycle']
    if row.get('failure'):
        if row['failure']['kind'] not in ('HOLD_RETAINED_COHORT', 'HOLD_CENSUS', 'HOLD_TERMINAL_CUTOFF'):
            raise ValueError('V327 retains an explicit incomplete-input or terminal-cutoff failure')
        reasons.append(dict(lifecycle=life, **row['failure']))
    initial = row.get('initial', {})
    if set(initial) != set(TASKS) or any(not all(key in initial[task] for key in
            ('head_version', 'context_id', 'planning_belief', 'evaluations')) for task in initial):
        reasons.append(dict(lifecycle=life, kind='HOLD_RETAINED_COHORT', reason='Both retained FIRST banks are required'))
        return
    if len({initial[task]['context_id'] for task in TASKS}) != 2:
        raise ValueError('V327 retained A and B banks remain distinct')
    for task in TASKS:
        teacher = initial[task]['head_version']
        _head_identity(teacher, row, task)
        if teacher['arm'] != 'FIRST_LOCAL' or teacher['version'] != 0:
            raise ValueError('V327 starts from the retained immutable FIRST_LOCAL v0')
        if set(initial[task]['evaluations']) != set(INITIAL_ARMS):
            reasons.append(dict(lifecycle=life, task=task, kind='HOLD_RETAINED_COHORT',
                reason='Fresh SOURCE and FIRST evaluation cells are required'))
        previous = {arm: teacher for arm in UPDATING_ARMS}
        for number in ROUNDS:
            stage = row.get('rounds', {}).get(number, {}).get(task)
            if stage is not None and stage.get('terminal_status_counts', {}).get('CUTOFF', 0):
                reasons.append(dict(lifecycle=life, task=task, round=int(number), kind='HOLD_TERMINAL_CUTOFF',
                    reason='At least one retained supervision member is unfinished'))
            if (stage is None or set(stage.get('arms', {})) != set(UPDATING_ARMS) or
                    any('evaluations' not in item for item in stage.get('arms', {}).values()) or
                    any(key not in stage for key in ('source_group_artifact', 'source_outcome_artifact',
                        'first_prediction_metrics', 'terminal_status_counts'))):
                reasons.append(dict(lifecycle=life, task=task, round=int(number), kind='HOLD_CENSUS',
                    reason='All retained members, both fitted arms and fresh evaluations are required'))
                break
            if (stage['groups'] != GROUPS or stage['replicas'] != REPLICAS or stage['epochs'] != EPOCHS or
                    stage['fit_members'] != list(TRAIN_MEMBERS) or
                    stage['validation_members'] != list(VALIDATION_MEMBERS) or
                    not stage['first_unchanged'] or stage['teacher_version'] != teacher or
                    not stage['win_weights_identical']):
                raise ValueError('V327 keeps its FIRST teacher, member split and exactly matched WIN trajectory')
            statuses = stage['terminal_status_counts']
            if (set(statuses) != {'WON', 'LOST', 'CUTOFF'} or any(count < 0 for count in statuses.values()) or
                    sum(statuses.values()) != GROUPS*REPLICAS):
                raise ValueError('V327 retains all four terminal members per root')
            for partition, members in (('train', TRAIN_MEMBERS), ('validation', VALIDATION_MEMBERS)):
                _metric_contract(stage['first_prediction_metrics'][partition], members)
            for arm in UPDATING_ARMS:
                item = stage['arms'][arm]
                fit, version = item['fit'], item['head_version']
                _head_identity(version, row, task)
                if (version['arm'] != arm or version['version'] != int(number) or
                        version['base_file'] != previous[arm]['file'] or
                        version['updates'] - previous[arm]['updates'] != FITTED_GROUPS or
                        item['updates_before'] != previous[arm]['updates'] or
                        item['updates_after'] != version['updates']):
                    raise ValueError('V327 each arm advances its own actual head from retained FIRST')
                expected_method = 'REPLAY_GROUPED_' + arm
                if (fit['method'] != expected_method or fit['distinct_rootgroups'] != GROUPS or
                        fit['epochs'] != EPOCHS or len(fit['epoch_receipts']) != EPOCHS):
                    raise ValueError('V327 both arms replay their two fixed members for sixteen epochs')
                _fit_contract(fit, FITTED_GROUPS, arm)
                for epoch in fit['epoch_receipts']:
                    _fit_contract(epoch, GROUPS, arm)
                    if arm == 'WIN_ONLY' and not epoch['reward_frozen']:
                        raise ValueError('V327 WIN_ONLY retains the complete FIRST reward')
                if arm == 'WIN_ONLY' and (not item['reward_unchanged'] or version['reward_indices_count'] != 0):
                    raise ValueError('V327 WIN_ONLY retains the complete FIRST reward')
                expected_before = 'FIRST' if number == '1' else arm + '_BEFORE'
                if item['prediction_keys'] != dict(before=expected_before, after=arm+'_AFTER'):
                    raise ValueError('V327 prediction snapshots correspond to the actual learning checkpoint')
                for boundary in ('before', 'after'):
                    for partition, members in (('train', TRAIN_MEMBERS), ('validation', VALIDATION_MEMBERS)):
                        _metric_contract(item['prediction_metrics'][boundary][partition], members)
                previous[arm] = version


def _prediction_summary(rows, hold):
    if hold:
        return None
    fields = ('reward_mse', 'win_brier', 'utility_mse', 'reward_bias', 'win_bias', 'utility_bias')
    result = {}
    for number in ROUNDS:
        for task in TASKS:
            stages = [row['rounds'][number][task] for row in rows]
            first = {partition: {field: float(np.mean([stage['first_prediction_metrics'][partition][field]
                for stage in stages])) for field in fields} for partition in ('train', 'validation')}
            arms = {}
            for arm in UPDATING_ARMS:
                boundaries = {boundary: {partition: {field: float(np.mean([
                    stage['arms'][arm]['prediction_metrics'][boundary][partition][field] for stage in stages]))
                    for field in fields} for partition in ('train', 'validation')} for boundary in ('before', 'after')}
                boundaries['change'] = {partition: {field: boundaries['after'][partition][field] -
                    boundaries['before'][partition][field] for field in fields} for partition in ('train', 'validation')}
                boundaries['after_minus_FIRST'] = {partition: {field: boundaries['after'][partition][field] -
                    first[partition][field] for field in fields} for partition in ('train', 'validation')}
                arms[arm] = boundaries
            result['ROUND'+number+'_'+task] = dict(FIRST_LOCAL=first, arms=arms)
    return dict(cells=result, estimator='EQUAL_LIFECYCLES_WITHIN_TASK_ROUND',
        inference='DESCRIPTIVE_PAIRED_SUFFIX_ERRORS_NO_UTILITY_GATE_OR_UNSEEN_ROOT_GENERALIZATION')


def summarize(lives, draws=20000):
    """Retain the observed cohort and pair fresh executions; incomplete evidence holds inference."""
    rows = sorted(lives, key=lambda row: row['lifecycle'])
    identities = [row['lifecycle'] for row in rows]
    if (len(set(identities)) != len(identities) or any(life not in range(16) for life in identities) or
            any(row['parent'] != row['lifecycle'] % 4 for row in rows)):
        raise ValueError('V327 retains the sixteen V326 lifecycle identities under their frozen SOURCE parents')
    if draws < 2:
        raise ValueError('V327 bootstrap requires at least two draws')
    reasons = []
    if identities != list(range(16)):
        reasons.append(dict(kind='HOLD_COHORT', reason='Not all sixteen retained target-learning histories are available'))
    for row in rows:
        _complete_contract(row, reasons)
    records, cutoffs, terminal_cutoffs = [], [], []
    physical_games, reused_terminal_members = 0, 0
    for row in rows:
        cells, endpoints = {}, {}
        for task_index, task in enumerate(TASKS):
            initial = row.get('initial', {}).get(task, {})
            belief, teacher = initial.get('planning_belief', {}).get('estimated_p_four'), initial.get('head_version')
            stages = [('FIRST', initial.get('evaluations', {}), {'FIRST_LOCAL': teacher})]
            for number in ROUNDS:
                stage = row.get('rounds', {}).get(number, {}).get(task, {})
                statuses = stage.get('terminal_status_counts', {})
                reused_terminal_members += sum(statuses.values())
                if statuses.get('CUTOFF', 0):
                    terminal_cutoffs.append(dict(lifecycle=row['lifecycle'], task=task, round=int(number),
                        count=statuses['CUTOFF']))
                arms = stage.get('arms', {})
                stages.append(('ROUND'+number, {arm: item['evaluations'] for arm, item in arms.items()
                    if 'evaluations' in item}, {arm: item['head_version'] for arm, item in arms.items()
                    if 'head_version' in item}))
            for checkpoint, evaluations, versions in stages:
                key = checkpoint+'_'+task
                cells[key], endpoints[key] = {}, {}
                for arm, evaluation in evaluations.items():
                    if arm not in (INITIAL_ARMS if checkpoint == 'FIRST' else UPDATING_ARMS):
                        raise ValueError('V327 evaluates only its frozen SOURCE, FIRST and fitted policy arms')
                    games = evaluation['game_summaries']
                    expected_seeds = [EVALUATION_SEED+row['lifecycle']*1000000+task_index*100000+episode
                        for episode in range(GAMES_PER_CELL)]
                    if (len(games) != GAMES_PER_CELL or [game['seed'] for game in games] != expected_seeds or
                            evaluation['estimated_p_four'] != belief):
                        raise ValueError('V327 uses all 64 paired fresh seeds and the immutable bank belief')
                    if evaluation['head_version'] != (None if arm == 'SOURCE' else versions.get(arm)):
                        raise ValueError('V327 natural evaluation uses the actual frozen checkpoint head')
                    if evaluation['planner'] != 'H2' or not evaluation['static_evaluation_valid']:
                        raise ValueError('V327 natural evaluation retains fixed H2 and frozen weights')
                    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
                        raise ValueError('V327 keeps explicit natural or cutoff endpoints')
                    cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, checkpoint=checkpoint,
                        arm=arm, seed=game['seed']) for game in games if game['status'] == 'CUTOFF')
                    physical_games += len(games)
                    cells[key][arm] = (None if any(game['status'] == 'CUTOFF' for game in games) else
                        float(np.mean([game['utility'] for game in games])))
                    endpoints[key][arm] = {status: sum(game['status'] == status for game in games)
                        for status in ('WON', 'LOST', 'CUTOFF')}
                if checkpoint != 'FIRST':
                    cells[key] = {**cells.get('FIRST_'+task, {}), **cells[key]}
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells,
            retained_endpoint_counts=endpoints, failure=row.get('failure')))
    if cutoffs:
        reasons.append(dict(kind='HOLD_CUTOFF', reason='At least one fresh natural evaluation is unfinished'))
    if terminal_cutoffs:
        reasons.append(dict(kind='HOLD_TERMINAL_CUTOFF', reason='At least one retained terminal member is unfinished'))
    hold = next((kind for kind in ('HOLD_TERMINAL_CUTOFF', 'HOLD_CUTOFF', 'HOLD_RETAINED_COHORT',
        'HOLD_CENSUS', 'HOLD_COHORT') if any(reason['kind'] == kind for reason in reasons)), None)
    samples = None if hold else _samples(rows, draws)

    def contrasts(number, tasks):
        if hold:
            return {left+'_minus_'+right: None for left, right in PAIRS}
        values = {arm: np.asarray([np.mean([record['cells']['ROUND'+number+'_'+task][arm]
            for task in tasks]) for record in records], dtype=np.float64) for arm in ARMS}
        return {left+'_minus_'+right: _interval(rows, values[left]-values[right], samples) for left, right in PAIRS}

    rounds = {number: contrasts(number, TASKS) for number in ROUNDS}
    task_contrasts = {'ROUND'+number+'_'+task: contrasts(number, (task,)) for number in ROUNDS for task in TASKS}
    checkpoints = {key: {arm: value[arm+'_minus_FIRST_LOCAL'] for arm in UPDATING_ARMS}
        for key, value in task_contrasts.items()}
    final, primary = rounds['2'], rounds['2']['JOINT_RETURN_minus_FIRST_LOCAL']
    primary_status = _status(primary, hold)
    retention = {task: _status(checkpoints['ROUND2_'+task]['JOINT_RETURN'], hold, retention=True) for task in TASKS}
    contribution = _status(final['JOINT_RETURN_minus_WIN_ONLY'], hold)
    retained = primary_status == 'SUPPORTED_GAIN' and all(status == 'SUPPORTED_NONDECREASE' for status in retention.values())
    route = ('HOLD_INCOMPLETE_EVIDENCE' if hold else
        'ADVANCE_TO_NEW_COHORT_CONFIRMATION' if retained else 'STOP_FIXED_FIRST_TERMINAL_REGRESSION')
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        primary_self_improvement_status=primary_status, primary_self_improvement_supported=primary_status == 'SUPPORTED_GAIN',
        task_retention_status=retention, retained_improvement_supported=retained,
        joint_reward_contribution_status=contribution, joint_reward_contribution_supported=contribution == 'SUPPORTED_GAIN',
        retained_joint_mechanism_supported=retained and contribution == 'SUPPORTED_GAIN',
        win_only_self_improvement_status=_status(final['WIN_ONLY_minus_FIRST_LOCAL'], hold),
        final_net_gain_status=_status(final['JOINT_RETURN_minus_SOURCE'], hold), final_ab_contrasts=final,
        round_ab_contrasts=rounds, task_contrasts=task_contrasts, checkpoint_contrasts=checkpoints,
        by_lifecycle=records, prediction_error_summary=_prediction_summary(rows, hold),
        complete_game_endpoints=not cutoffs and not terminal_cutoffs,
        complete_retained_target_cohort=not hold, hold_reasons=reasons, cutoffs=cutoffs,
        terminal_cutoffs=terminal_cutoffs, physical_evaluation_games=physical_games,
        physical_new_terminal_supervision_members=0, reused_terminal_supervision_members=reused_terminal_members,
        new_training_raw_tiles=0, new_target_learning_histories=False, reused_target_cohort=True,
        source_histories_repeated=False, independent_SOURCE=False, independent_learning_confirmation=False,
        bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=draws, bootstrap_executed=not hold,
        bootstrap_unit='PAIRED_RETAINED_TARGET_LEARNING_LIFECYCLE_WITHIN_FIXED_SOURCE_PARENT',
        estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        same_root_member_target_ablation=True, same_suffix_value_pairing=True, matched_optimization_quota=True,
        equal_total_raw_efficiency_evaluated=False, fixed_teacher_regression_route=route, next_route=route,
        evidence_scope='Sixteen retained V326 target-learning histories condition on four frozen SOURCE parents. '
            'Both arms restart from their actual FIRST head and share each root and actual terminal suffix pair. '
            'Only members 0 and 1 fit the heads in sixteen fixed passes; members 2 and 3 estimate suffix errors '
            'at those same observed roots. WIN_ONLY keeps the FIRST reward; JOINT_RETURN fits the same suffix '
            'return and WIN jointly. The WIN weight trajectory is exactly matched between arms. SOURCE, FIRST '
            'and both learned arms receive fresh paired natural H2 evaluations. The sole primary is final '
            'JOINT_RETURN minus own FIRST, with separate mandatory A/B nondecrease conditions. JOINT_RETURN '
            'minus WIN_ONLY is a nominal secondary reward-update contribution. No new training samples are '
            'acquired; inherited acquisition and suffix costs remain charged in economic accounting. This is '
            'a development mechanism intervention, not independent learning confirmation, unseen-root '
            'generalization or equal-total-raw efficiency. Missing input or any observed cutoff holds all '
            'inference. Without net learning gain and both task-retention conditions, the fixed-FIRST terminal '
            'regression route stops rather than changing alpha, passes, quotas or seeds.')
