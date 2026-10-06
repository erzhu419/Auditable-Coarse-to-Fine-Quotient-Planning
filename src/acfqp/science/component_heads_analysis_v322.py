"""Saved reward/WIN head intervention on the reused V321 evaluation streams."""
import random

import numpy as np

TASKS = ('A', 'B')
ARMS = ('FIRST_LOCAL', 'NSTEP_QUERY', 'REWARD_ONLY', 'WIN_ONLY')
REUSED_ARMS = ('FIRST_LOCAL', 'NSTEP_QUERY')
NEW_ARMS = ('REWARD_ONLY', 'WIN_ONLY')
PRIMARY = 'REWARD_ONLY_minus_NSTEP_QUERY_FINAL_AB'
PAIRS = (
    ('REWARD_ONLY', 'NSTEP_QUERY'),
    ('REWARD_ONLY', 'FIRST_LOCAL'),
    ('WIN_ONLY', 'FIRST_LOCAL'),
    ('NSTEP_QUERY', 'WIN_ONLY'),
    ('NSTEP_QUERY', 'FIRST_LOCAL'),
)
INTERACTION = 'NSTEP_QUERY_minus_REWARD_ONLY_minus_WIN_ONLY_plus_FIRST_LOCAL'
BOOTSTRAP_SEED = 32200001


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
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_REUSED_FIRST_COHORT_AND_V321_STREAMS')
    result['status95'] = _status(result)
    return result


def _head_identity(version, row, task):
    initial = row['initial'][task]
    if (version['schema'] != 'acfqp.head_version.v313' or version['head_kind'] != 'LOCAL_RISK' or
            version['lifecycle'] != row['lifecycle'] or version['parent'] != row['parent'] or
            version['context_id'] != initial['context_id']):
        raise ValueError('V322 evaluation uses the actual lifecycle and task-bank sparse LOCAL head')


def summarize(lives, draws=20000):
    """Four saved-head cells; one paired bootstrap and global HOLD for any cutoff."""
    rows = sorted(lives, key=lambda row: row['lifecycle'])
    if len(rows) != 16 or [row['lifecycle'] for row in rows] != list(range(16)) or any(
            row['parent'] != row['lifecycle'] % 4 for row in rows):
        raise ValueError('V322 retains all sixteen FIRST lifecycles under their four fixed parents')
    records, cutoffs = [], []
    physical_new_games, reused_games = 0, 0
    for row in rows:
        cells, endpoint_counts = {}, {}
        if set(row['cells']) != set(TASKS):
            raise ValueError('V322 retains both A and B task banks')
        for task_index, task in enumerate(TASKS):
            initial = row['initial'][task]
            first = initial['head_version']
            _head_identity(first, row, task)
            if first['arm'] != 'FIRST_LOCAL' or first['version'] != 0:
                raise ValueError('V322 starts from each actual frozen FIRST_LOCAL v0')
            belief = initial['planning_belief']['estimated_p_four']
            evaluations = row['cells'][task]
            if set(evaluations) != set(ARMS):
                raise ValueError('V322 retains exactly the four reward/WIN head combinations')
            expected_seeds = [321900000000 + row['lifecycle'] * 1000000 + task_index * 100000 + episode
                for episode in range(32)]
            cells[task], endpoint_counts[task] = {}, {}
            for arm in ARMS:
                item = evaluations[arm]
                if item['reused'] != (arm in REUSED_ARMS):
                    raise ValueError('V322 reuses only FIRST_LOCAL and final NSTEP_QUERY game receipts')
                evaluation = item['evaluation']
                games = evaluation['game_summaries']
                if len(games) != 32 or [game['seed'] for game in games] != expected_seeds or (
                        evaluation['estimated_p_four'] != belief):
                    raise ValueError('V322 keeps all 32 paired V321 seeds and the immutable bank belief')
                version = evaluation['head_version']
                _head_identity(version, row, task)
                if arm == 'FIRST_LOCAL':
                    valid = version == first
                elif arm == 'NSTEP_QUERY':
                    valid = version['arm'] == arm and version['version'] == 2 and (
                        version['updates'] == first['updates'] + 32768)
                else:
                    valid = version == item['head_version'] and version['arm'] == arm and (
                        version['base_file'] == first['file'] and version['updates'] == first['updates'])
                if not valid:
                    raise ValueError('V322 evaluates actual saved FIRST, final BOTH or unfitted hybrid heads')
                if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
                    raise ValueError('V322 retains explicit natural or cutoff endpoint status')
                cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, arm=arm,
                    seed=game['seed'], reused=item['reused']) for game in games if game['status'] == 'CUTOFF')
                if item['reused']:
                    reused_games += len(games)
                else:
                    physical_new_games += len(games)
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
        result = {left + '_minus_' + right: None if hold else _interval(rows, values[left] - values[right], samples)
            for left, right in PAIRS}
        result[INTERACTION] = None if hold else _interval(rows,
            values['NSTEP_QUERY'] - values['REWARD_ONLY'] - values['WIN_ONLY'] + values['FIRST_LOCAL'], samples)
        return result

    final = contrasts(TASKS)
    task_contrasts = {task: contrasts((task,)) for task in TASKS}
    primary = final['REWARD_ONLY_minus_NSTEP_QUERY']
    primary_status = _status(primary)
    pure = {arm: _status(final[arm + '_minus_FIRST_LOCAL']) for arm in NEW_ARMS}
    retention = {task: _status(task_contrasts[task]['REWARD_ONLY_minus_FIRST_LOCAL'], retention=True)
        for task in TASKS}
    restored_growth = (primary_status == 'SUPPORTED_GAIN' and pure['REWARD_ONLY'] == 'SUPPORTED_GAIN' and
        all(value == 'SUPPORTED_NONDECREASE' for value in retention.values()))
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        primary_restoration_supported=primary_status == 'SUPPORTED_GAIN',
        reward_only_self_improvement_status=pure['REWARD_ONLY'], pure_component_status=pure,
        interaction_status=_status(final[INTERACTION]), final_ab_contrasts=final,
        task_contrasts=task_contrasts, task_retention_status=retention,
        restored_growth_supported=restored_growth, by_lifecycle=records,
        complete_game_endpoints=not hold, cutoffs=cutoffs,
        physical_new_evaluation_games=physical_new_games, reused_evaluation_games=reused_games,
        total_evaluation_games=physical_new_games + reused_games,
        bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=draws, bootstrap_executed=not hold,
        bootstrap_unit='PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT', paired_stream_reuse=True,
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        evidence_scope='Controlled saved-head component intervention on the existing sixteen-life FIRST cohort '
            'under four frozen SOURCE parents. FIRST_LOCAL and final NSTEP_QUERY natural-game receipts are '
            'reused; REWARD_ONLY and WIN_ONLY use those same paired V321 random streams. Hybrid heads combine '
            'the frozen FIRST and final NSTEP_QUERY reward/WIN tables without parameter fitting or new labels. '
            'The sole primary tests REWARD_ONLY minus NSTEP_QUERY. Reward-only own-FIRST growth and both-task '
            'nondecrease are separate requirements for restored growth. This is a conditional mechanism '
            'diagnostic, not independent confirmation of a new method or sampling-efficiency claim. Any new '
            'or reused cutoff retains every game and holds all terminal inference without resampling, seed '
            'replacement or bootstrap. Secondary intervals are nominal; four fixed parents do not establish '
            'unconditional SOURCE replication, and new physical evaluation cost excludes reused game cost.')
