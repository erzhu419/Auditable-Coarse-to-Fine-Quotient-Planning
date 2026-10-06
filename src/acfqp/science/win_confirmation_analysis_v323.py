"""Prospective execution-stream validation of the frozen saved WIN-only policy."""
import random

import numpy as np

TASKS = ('A', 'B')
ARMS = ('SOURCE', 'FIRST_LOCAL', 'WIN_ONLY')
PRIMARY = 'WIN_ONLY_minus_FIRST_LOCAL_FINAL_AB'
PAIRS = (('WIN_ONLY', 'FIRST_LOCAL'), ('WIN_ONLY', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
BOOTSTRAP_SEED = 32300001
EVALUATION_SEED = 323900000000
GAMES_PER_CELL = 64


def _samples(rows, draws):
    groups = [[i for i, row in enumerate(rows) if row['parent'] == parent] for parent in range(4)]
    rng = random.Random(BOOTSTRAP_SEED)
    return np.asarray([[rng.choices(group, k=4) for group in groups] for _ in range(draws)], dtype=np.int64)


def _status(interval, retention=False):
    if interval is None:
        return 'HOLD_CUTOFF'
    lo, hi = interval['ci95']
    if lo >= 0 if retention else lo > 0:
        return 'SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN'
    if hi < 0:
        return 'SUPPORTED_LOSS'
    return 'UNRESOLVED'


def _interval(rows, values, samples):
    values = np.asarray(values, dtype=np.float64)
    distribution = values[samples].mean(axis=2).mean(axis=1)
    result = dict(mean=float(values.mean()), ci95=np.quantile(distribution, [.025, .975]).tolist(),
        lifecycle_values={str(row['lifecycle']): float(value) for row, value in zip(rows, values)},
        parent_mean_values={str(parent): float(np.mean([value for row, value in zip(rows, values)
            if row['parent'] == parent])) for parent in range(4)},
        positive_equal_negative=[int(np.sum(values > 0)), int(np.sum(values == 0)), int(np.sum(values < 0))],
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_EXISTING_SIXTEEN_FROZEN_HEADS_NEW_V323_STREAMS')
    result['status95'] = _status(result)
    return result


def _head_identity(version, row, task):
    if (version['schema'] != 'acfqp.head_version.v313' or version['head_kind'] != 'LOCAL_RISK' or
            version['lifecycle'] != row['lifecycle'] or version['parent'] != row['parent'] or
            version['context_id'] != row['initial'][task]['context_id']):
        raise ValueError('V323 retains the actual lifecycle and task-bank sparse LOCAL head')


def summarize(lives, draws=20000):
    """One common paired bootstrap; any cutoff holds every terminal contrast."""
    rows = sorted(lives, key=lambda row: row['lifecycle'])
    if len(rows) != 16 or [row['lifecycle'] for row in rows] != list(range(16)) or any(
            row['parent'] != row['lifecycle'] % 4 for row in rows):
        raise ValueError('V323 retains all sixteen FIRST lifecycles under their four fixed parents')
    records, cutoffs = [], []
    physical_games = 0
    for row in rows:
        if any(set(row[key]) != set(TASKS) for key in ('initial', 'frozen_candidate', 'evaluations')):
            raise ValueError('V323 retains both A and B task banks')
        cells, endpoint_counts = {}, {}
        for task_index, task in enumerate(TASKS):
            initial = row['initial'][task]
            first = initial['head_version']
            _head_identity(first, row, task)
            if first['arm'] != 'FIRST_LOCAL' or first['version'] != 0:
                raise ValueError('V323 starts from each actual frozen FIRST_LOCAL v0')
            candidate = row['frozen_candidate'][task]
            head, assembly = candidate['head_version'], candidate['assembly']
            _head_identity(head, row, task)
            if (head['arm'] != 'WIN_ONLY' or head['version'] != 1 or head['base_file'] != first['file'] or
                    head['updates'] != first['updates']):
                raise ValueError('V323 evaluates the actual saved unfitted V322 WIN_ONLY v1 head')
            if (assembly['new_fit_updates'] != 0 or not assembly['weights_frozen'] or
                    not assembly['complete_component_equality'] or
                    assembly['parameter_updates_counter'] != first['updates'] or
                    assembly['reward_source'] != 'FIRST_LOCAL' or assembly['win_source'] != 'NSTEP_QUERY'):
                raise ValueError('V323 candidate retains the frozen V322 FIRST reward and learned WIN assembly')
            evaluations = row['evaluations'][task]
            if set(evaluations) != set(ARMS):
                raise ValueError('V323 retains exactly SOURCE, FIRST_LOCAL and frozen WIN_ONLY')
            belief = initial['planning_belief']['estimated_p_four']
            expected_seeds = [EVALUATION_SEED + row['lifecycle'] * 1000000 + task_index * 100000 + episode
                for episode in range(GAMES_PER_CELL)]
            cells[task], endpoint_counts[task] = {}, {}
            for arm in ARMS:
                evaluation = evaluations[arm]
                games = evaluation['game_summaries']
                if (len(games) != GAMES_PER_CELL or [game['seed'] for game in games] != expected_seeds or
                        evaluation['estimated_p_four'] != belief):
                    raise ValueError('V323 requires all 64 paired new seeds and the immutable bank belief')
                expected_head = {'SOURCE': None, 'FIRST_LOCAL': first, 'WIN_ONLY': head}[arm]
                if evaluation['head_version'] != expected_head:
                    raise ValueError('V323 evaluates actual SOURCE, FIRST and frozen saved WIN_ONLY heads')
                if evaluation['planner'] != 'H2' or not evaluation['static_evaluation_valid']:
                    raise ValueError('V323 natural evaluation keeps the fixed H2 planner and frozen weights')
                if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
                    raise ValueError('V323 retains explicit natural or cutoff endpoint status')
                cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, arm=arm, seed=game['seed'])
                    for game in games if game['status'] == 'CUTOFF')
                physical_games += len(games)
                cells[task][arm] = float(np.mean([game['utility'] for game in games]))
                endpoint_counts[task][arm] = {status: sum(game['status'] == status for game in games)
                    for status in ('WON', 'LOST', 'CUTOFF')}
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells=cells,
            retained_endpoint_counts=endpoint_counts))
    hold = bool(cutoffs)
    samples = None if hold else _samples(rows, draws)

    def contrasts(tasks):
        values = {arm: np.asarray([np.mean([record['cells'][task][arm] for task in tasks])
            for record in records], dtype=np.float64) for arm in ARMS}
        return {left + '_minus_' + right: None if hold else _interval(rows, values[left] - values[right], samples)
            for left, right in PAIRS}

    final = contrasts(TASKS)
    task_contrasts = {task: contrasts((task,)) for task in TASKS}
    primary = final['WIN_ONLY_minus_FIRST_LOCAL']
    primary_status = _status(primary)
    retention = {task: _status(task_contrasts[task]['WIN_ONLY_minus_FIRST_LOCAL'], retention=True)
        for task in TASKS}
    retained = primary_status == 'SUPPORTED_GAIN' and all(value == 'SUPPORTED_NONDECREASE'
        for value in retention.values())
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        primary_execution_gain_supported=primary_status == 'SUPPORTED_GAIN',
        task_retention_status=retention, retained_execution_gain_supported=retained,
        final_net_gain_status=_status(final['WIN_ONLY_minus_SOURCE']),
        final_ab_contrasts=final, task_contrasts=task_contrasts, by_lifecycle=records,
        complete_game_endpoints=not hold, cutoffs=cutoffs,
        physical_evaluation_games=physical_games, fresh_evaluation_streams=True,
        independent_learning_histories=False, bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=draws,
        bootstrap_executed=not hold, bootstrap_unit='PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        evidence_scope='Prospective new-execution-stream validation of the frozen WIN_ONLY candidate selected '
            'from V322 on the existing sixteen FIRST learning histories under four fixed SOURCE parents. '
            'All three policy arms execute 64 paired new natural-game streams per A/B task and lifecycle. '
            'Actual saved FIRST reward and learned WIN tables are reused without fitting, target acquisition '
            'or SOURCE retraining. The sole primary tests WIN_ONLY minus own FIRST; both-task nondecrease '
            'is separately required for retained execution gain. This is not an independent learning cohort '
            'or unconditional SOURCE replication and does not establish general strategic learning or '
            'sampling efficiency. Any cutoff keeps every game and holds all terminal inference without '
            'seed replacement, quota extension or bootstrap. Secondary intervals are nominal.')
