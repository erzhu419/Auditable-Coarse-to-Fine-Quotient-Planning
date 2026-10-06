"""Fresh target-learning histories with FIRST reward frozen and matched WIN updates."""
import random

import numpy as np

TASKS = ('A', 'B')
ROUNDS = ('1', '2')
INITIAL_ARMS = ('SOURCE', 'FIRST_LOCAL')
UPDATING_ARMS = ('QUERY_WIN', 'FACTUAL_WIN')
ARMS = INITIAL_ARMS + UPDATING_ARMS
PAIRS = (('QUERY_WIN', 'FIRST_LOCAL'), ('QUERY_WIN', 'FACTUAL_WIN'), ('QUERY_WIN', 'SOURCE'),
    ('FACTUAL_WIN', 'FIRST_LOCAL'), ('FACTUAL_WIN', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
PRIMARY = 'QUERY_WIN_minus_FIRST_LOCAL_FINAL_AB'
BOOTSTRAP_SEED = 32400001
EVALUATION_SEED = 324900000000
GAMES_PER_CELL = 64
GROUPS, REPLICAS = 16384, 4
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_SOURCE_PARENTS_NEW_V324_TARGET_LEARNING_HISTORIES'


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
        raise ValueError('V324 heads retain their actual lifecycle and confirmed task bank')


def _complete_contract(row, reasons):
    """Missing acquisition/census is HOLD; changing a completed learning contract is an error."""
    life = row['lifecycle']
    if row.get('failure'):
        if row['failure']['kind'] not in ('HOLD_INITIAL_BANK', 'HOLD_CENSUS', 'HOLD_TRAINING_CUTOFF'):
            raise ValueError('V324 retains an explicit initial-bank, census or acquisition-cutoff failure')
        reasons.append(dict(lifecycle=life, **row['failure']))
    if not row.get('initial_context_precondition_met', False):
        reasons.append(dict(lifecycle=life, kind='HOLD_INITIAL_BANK', reason='Initial distinct banks are not confirmed'))
    initial = row.get('initial', {})
    if set(initial) != set(TASKS) or any(not all(key in initial[task] for key in
            ('head_version', 'head_versions', 'context_id', 'planning_belief', 'evaluations')) or
            initial[task].get('head_versions', {}).get('FIRST_LOCAL') is None for task in initial):
        reasons.append(dict(lifecycle=life, kind='HOLD_INITIAL_BANK', reason='Both actual FIRST banks are required'))
        return
    if len({initial[task]['context_id'] for task in TASKS}) != 2:
        reasons.append(dict(lifecycle=life, kind='HOLD_INITIAL_BANK', reason='Initial A and B bank identities coincide'))
    for task in TASKS:
        teacher = initial[task]['head_version']
        _head_identity(teacher, row, task)
        if (teacher != initial[task]['head_versions']['FIRST_LOCAL'] or teacher['arm'] != 'FIRST_LOCAL' or
                teacher['version'] != 0):
            raise ValueError('V324 uses the actual newly learned FIRST_LOCAL v0 teacher')
        if set(initial[task]['evaluations']) != set(INITIAL_ARMS):
            reasons.append(dict(lifecycle=life, task=task, kind='HOLD_INITIAL_BANK', reason='Initial SOURCE/FIRST cells are incomplete'))
        previous = {arm: teacher for arm in UPDATING_ARMS}
        for number in ROUNDS:
            stage = row.get('rounds', {}).get(number, {}).get(task)
            if (stage is None or 'census' not in stage or 'selected_groups' not in stage['census'] or
                    set(stage.get('arms', {})) != set(UPDATING_ARMS) or
                    any('evaluations' not in item for item in stage.get('arms', {}).values())):
                reasons.append(dict(lifecycle=life, task=task, round=int(number), kind='HOLD_CENSUS',
                    reason='A complete matched census and both WIN learners are required'))
                break
            if stage['census']['selected_groups'] < GROUPS:
                reasons.append(dict(lifecycle=life, task=task, round=int(number), kind='HOLD_CENSUS',
                    reason='The fixed census quota is unavailable'))
                break
            if (stage['groups'] != GROUPS or stage['replicas'] != REPLICAS or
                    stage['census']['selected_groups'] != GROUPS or not stage['teacher_unchanged'] or
                    stage['teacher_version'] != teacher):
                raise ValueError('V324 keeps its immutable FIRST teacher and exactly matched root-group quota')
            for arm in UPDATING_ARMS:
                item = stage['arms'][arm]
                fit, version = item['fit'], item['head_version']
                _head_identity(version, row, task)
                if (version['arm'] != arm or version['version'] != int(number) or
                        version['base_file'] != previous[arm]['file'] or
                        version['updates'] - previous[arm]['updates'] != GROUPS or
                        item['updates_before'] != previous[arm]['updates'] or
                        item['updates_after'] != version['updates']):
                    raise ValueError('V324 each private WIN learner advances its own actual sparse head')
                counts = fit['learning_counts']
                if (fit['alpha'] != .0025 or fit['fitted_rootgroups'] != GROUPS or fit['replicates'] != REPLICAS or
                        not fit['reward_frozen'] or any(counts[key] != GROUPS for key in
                        ('rootgroup_updates', 'current_predictions', 'win_predictions')) or
                        counts.get('reward_predictions', 0) != 0 or
                        fit['normalization_counts'].get('reward_parameter_writes', 0) != 0 or
                        not item['reward_unchanged'] or version['reward_indices_count'] != 0):
                    raise ValueError('V324 fits WIN only with fixed alpha and keeps complete FIRST reward unchanged')
                previous[arm] = version


def summarize(lives, draws=20000):
    """Pair new learning lifecycles under fixed parents; never resample incomplete evidence."""
    rows = sorted(lives, key=lambda row: row['lifecycle'])
    identities = [row['lifecycle'] for row in rows]
    if (len(set(identities)) != len(identities) or any(life not in range(16) for life in identities) or
            any(row['parent'] != row['lifecycle'] % 4 for row in rows)):
        raise ValueError('V324 retains actual lifecycle identities under their four frozen SOURCE parents')
    if draws < 2:
        raise ValueError('V324 bootstrap requires at least two draws')
    reasons = []
    if identities != list(range(16)):
        reasons.append(dict(kind='HOLD_COHORT', reason='Not all sixteen new target-learning histories are complete'))
    for row in rows:
        _complete_contract(row, reasons)
    records, cutoffs, training_cutoffs = [], [], []
    physical_games = 0
    for row in rows:
        cells, endpoints = {}, {}
        for task_index, task in enumerate(TASKS):
            initial = row.get('initial', {}).get(task, {})
            training = [('FIRST_WARMUP', 'SOURCE', initial.get('acquisition', {}).get('warmup', {}).get('game_summaries', [])),
                ('FIRST', 'SOURCE', initial.get('dataset', {}).get('games', []))]
            for number in ROUNDS:
                collector = row.get('rounds', {}).get(number, {}).get(task, {}).get('collectors', {}).get('FIXED_FIRST', {})
                training.append(('ROUND' + number, 'FIXED_FIRST', collector.get('dataset', {}).get('games', [])))
            training_cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, checkpoint=checkpoint,
                collector=collector, episode=game['episode']) for checkpoint, collector, games in training
                for game in games if game['status'] == 'CUTOFF')
            belief = initial.get('planning_belief', {}).get('estimated_p_four')
            teacher = initial.get('head_version')
            stages = [('FIRST', initial.get('evaluations', {}), {'FIRST_LOCAL': teacher})]
            for number in ROUNDS:
                stage = row.get('rounds', {}).get(number, {}).get(task, {})
                arms = stage.get('arms', {})
                stages.append(('ROUND' + number, {arm: item['evaluations'] for arm, item in arms.items()
                    if 'evaluations' in item}, {arm: item['head_version'] for arm, item in arms.items()
                    if 'head_version' in item}))
            for checkpoint, evaluations, versions in stages:
                key = checkpoint + '_' + task
                cells[key], endpoints[key] = {}, {}
                for arm, evaluation in evaluations.items():
                    allowed = INITIAL_ARMS if checkpoint == 'FIRST' else UPDATING_ARMS
                    if arm not in allowed:
                        raise ValueError('V324 retains only its declared initial and learned policy arms')
                    games = evaluation['game_summaries']
                    expected_seeds = [EVALUATION_SEED + row['lifecycle'] * 1000000 + task_index * 100000 + episode
                        for episode in range(GAMES_PER_CELL)]
                    if (len(games) != GAMES_PER_CELL or [game['seed'] for game in games] != expected_seeds or
                            evaluation['estimated_p_four'] != belief):
                        raise ValueError('V324 requires all 64 paired fresh seeds and the immutable bank belief')
                    if evaluation['head_version'] != (None if arm == 'SOURCE' else versions.get(arm)):
                        raise ValueError('V324 evaluation uses the actual frozen checkpoint head')
                    if evaluation['planner'] != 'H2' or not evaluation['static_evaluation_valid']:
                        raise ValueError('V324 natural evaluation keeps fixed H2 planning and frozen weights')
                    if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
                        raise ValueError('V324 evaluation retains explicit natural or cutoff endpoints')
                    cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, checkpoint=checkpoint,
                        arm=arm, seed=game['seed']) for game in games if game['status'] == 'CUTOFF')
                    physical_games += len(games)
                    cells[key][arm] = float(np.mean([game['utility'] for game in games]))
                    endpoints[key][arm] = {status: sum(game['status'] == status for game in games)
                        for status in ('WON', 'LOST', 'CUTOFF')}
                if checkpoint != 'FIRST':
                    cells[key] = {**cells.get('FIRST_' + task, {}), **cells[key]}
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells,
            retained_endpoint_counts=endpoints, failure=row.get('failure')))
    if cutoffs:
        reasons.append(dict(kind='HOLD_CUTOFF', reason='At least one retained evaluation game is unfinished'))
    if training_cutoffs:
        reasons.append(dict(kind='HOLD_TRAINING_CUTOFF', reason='At least one retained acquisition game is unfinished'))
    hold = next((kind for kind in ('HOLD_TRAINING_CUTOFF', 'HOLD_CUTOFF', 'HOLD_INITIAL_BANK', 'HOLD_CENSUS', 'HOLD_COHORT')
        if any(reason['kind'] == kind for reason in reasons)), None)
    samples = None if hold else _samples(rows, draws)

    def contrasts(number, tasks):
        if hold:
            return {left + '_minus_' + right: None for left, right in PAIRS}
        values = {arm: np.asarray([np.mean([record['cells']['ROUND' + number + '_' + task][arm]
            for task in tasks]) for record in records], dtype=np.float64) for arm in ARMS}
        return {left + '_minus_' + right: _interval(rows, values[left] - values[right], samples)
            for left, right in PAIRS}

    rounds = {number: contrasts(number, TASKS) for number in ROUNDS}
    task_contrasts = {'ROUND' + number + '_' + task: contrasts(number, (task,)) for number in ROUNDS for task in TASKS}
    checkpoints = {key: {arm: value[arm + '_minus_FIRST_LOCAL'] for arm in UPDATING_ARMS}
        for key, value in task_contrasts.items()}
    final, primary = rounds['2'], rounds['2']['QUERY_WIN_minus_FIRST_LOCAL']
    primary_status = _status(primary, hold)
    retention = {task: _status(checkpoints['ROUND2_' + task]['QUERY_WIN'], hold, retention=True) for task in TASKS}
    contribution = _status(final['QUERY_WIN_minus_FACTUAL_WIN'], hold)
    retained = primary_status == 'SUPPORTED_GAIN' and all(status == 'SUPPORTED_NONDECREASE' for status in retention.values())
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        primary_self_improvement_status=primary_status, primary_self_improvement_supported=primary_status == 'SUPPORTED_GAIN',
        task_retention_status=retention, retained_improvement_supported=retained,
        query_distribution_contribution_status=contribution, query_distribution_contribution_supported=contribution == 'SUPPORTED_GAIN',
        retained_query_mechanism_supported=retained and contribution == 'SUPPORTED_GAIN',
        factual_self_improvement_status=_status(final['FACTUAL_WIN_minus_FIRST_LOCAL'], hold),
        final_net_gain_status=_status(final['QUERY_WIN_minus_SOURCE'], hold), final_ab_contrasts=final,
        round_ab_contrasts=rounds, task_contrasts=task_contrasts, checkpoint_contrasts=checkpoints,
        by_lifecycle=records, complete_game_endpoints=not cutoffs and not any(reason['kind'] == 'HOLD_TRAINING_CUTOFF' for reason in reasons),
        complete_target_learning_cohort=not hold,
        hold_reasons=reasons, cutoffs=cutoffs, training_cutoffs=training_cutoffs, physical_evaluation_games=physical_games,
        new_target_learning_histories=True, source_histories_repeated=False, independent_SOURCE=False,
        bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=draws, bootstrap_executed=not hold,
        bootstrap_unit='PAIRED_NEW_TARGET_LEARNING_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        evidence_scope='Sixteen new initial acquisitions, FIRST adaptations, subsequent factual collections and WIN-only '
            'learning histories condition on four frozen SOURCE parents. All observed natural games are retained. '
            'QUERY and FACTUAL start from the same new FIRST head, keep its reward table and immutable teacher fixed, '
            'and receive matched root-group and fresh generative-spawn budgets. The sole primary is final QUERY minus '
            'own FIRST; A and B nondecrease are separate mandatory retention conditions. QUERY minus FACTUAL is a '
            'nominal secondary distribution-intervention contrast. Reused SOURCE training and dynamics mean this is '
            'not independent SOURCE replication, general strategic learning or ordinary online sampling efficiency. '
            'Missing banks/census or any cutoff hold all inference without resampling, replacement or quota extension.')
