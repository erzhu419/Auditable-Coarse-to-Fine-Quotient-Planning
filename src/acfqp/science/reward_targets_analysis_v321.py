"""Paired reward-label intervention, own-FIRST growth and A/B retention."""
import random

import numpy as np

TASKS = ('A', 'B')
UPDATING_ARMS = ('OLD_FACTUAL', 'OLD_QUERY', 'NSTEP_FACTUAL', 'NSTEP_QUERY')
ARMS = ('SOURCE', 'FIRST_LOCAL') + UPDATING_ARMS
PRIMARY = 'NSTEP_QUERY_minus_OLD_QUERY_FINAL_AB'
PAIRS = (
    ('NSTEP_QUERY', 'OLD_QUERY'),
    ('NSTEP_QUERY', 'FIRST_LOCAL'),
    ('NSTEP_QUERY', 'SOURCE'),
    ('NSTEP_QUERY', 'NSTEP_FACTUAL'),
    ('NSTEP_FACTUAL', 'OLD_FACTUAL'),
    ('OLD_FACTUAL', 'FIRST_LOCAL'),
    ('OLD_QUERY', 'FIRST_LOCAL'),
)
INTERACTION = 'NSTEP_QUERY_minus_OLD_QUERY_minus_NSTEP_FACTUAL_plus_OLD_FACTUAL'


def _samples(rows, draws):
    groups = [[i for i, row in enumerate(rows) if row['parent'] == parent] for parent in range(4)]
    rng = random.Random(32100001)
    return np.asarray([[rng.choices(group, k=4) for group in groups] for _ in range(draws)], dtype=np.int64)


def _interval(rows, values, samples):
    values = np.asarray(values, dtype=np.float64)
    distribution = values[samples].mean(axis=2).mean(axis=1)
    interval = dict(mean=float(values.mean()), ci95=np.quantile(distribution, [.025, .975]).tolist(),
        lifecycle_values={str(row['lifecycle']): float(value) for row, value in zip(rows, values)},
        parent_mean_values={str(parent): float(np.mean([value for row, value in zip(rows, values)
            if row['parent'] == parent])) for parent in range(4)},
        positive_equal_negative=[int(np.sum(values > 0)), int(np.sum(values == 0)), int(np.sum(values < 0))],
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REUSED_FIRST_COHORT')
    interval['status95'] = _status(interval)
    return interval


def _status(interval, retention=False):
    if interval is None:
        return 'HOLD_CUTOFF'
    lo, hi = interval['ci95']
    if lo >= 0 if retention else lo > 0:
        return 'SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN'
    if hi < 0:
        return 'SUPPORTED_LOSS'
    return 'UNRESOLVED'


def summarize(lives, draws=20000):
    """Equal task/episode means and one common paired, parent-conditional bootstrap."""
    rows = sorted(lives, key=lambda row: row['lifecycle'])
    if len(rows) != 16 or [row['lifecycle'] for row in rows] != list(range(16)) or any(
            row['parent'] != row['lifecycle'] % 4 for row in rows):
        raise ValueError('V321 retains all sixteen FIRST lifecycles under their four fixed parents')
    records, cutoffs = [], []
    physical_games = 0
    for row in rows:
        cells, endpoint_counts = {}, {}
        for task_index, task in enumerate(TASKS):
            initial = row['initial'][task]
            teacher = initial['head_version']
            belief = initial['planning_belief']['estimated_p_four']
            previous = {arm: teacher for arm in UPDATING_ARMS}
            for number in ('1', '2'):
                stage = row['rounds'][number][task]
                if not stage['teacher_unchanged'] or stage['teacher_version'] != teacher:
                    raise ValueError('V321 reward continuations keep the immutable actual FIRST teacher')
                if stage['groups'] != 16384 or set(stage['arms']) != set(UPDATING_ARMS):
                    raise ValueError('V321 keeps all four arms and all 16384 original rootgroups per round')
                for arm in UPDATING_ARMS:
                    item = stage['arms'][arm]
                    fit = item['fit']
                    if fit['alpha'] != .0025 or fit['learning_counts']['rootgroup_updates'] != 16384:
                        raise ValueError('V321 reward-label arms keep alpha and rootgroup update quotas fixed')
                    if item['head_version']['base_file'] != previous[arm]['file']:
                        raise ValueError('V321 each learner advances its own actual previous head')
                    previous[arm] = item['head_version']
            evaluations = row['final_evaluations'][task]
            if set(evaluations) != set(ARMS):
                raise ValueError('V321 final evaluation retains exactly all six required arms')
            expected_seeds = [321900000000 + row['lifecycle'] * 1000000 + task_index * 100000 + episode
                for episode in range(32)]
            cells[task], endpoint_counts[task] = {}, {}
            for arm in ARMS:
                evaluation = evaluations[arm]
                games = evaluation['game_summaries']
                if len(games) != 32 or [game['seed'] for game in games] != expected_seeds or (
                        evaluation['estimated_p_four'] != belief):
                    raise ValueError('V321 final arms retain 32 paired fresh seeds and immutable bank belief')
                expected_head = teacher if arm == 'FIRST_LOCAL' else previous.get(arm)
                if expected_head is not None and evaluation['head_version'] != expected_head:
                    raise ValueError('V321 evaluation uses the actual frozen FIRST or final learned head')
                if any(game['status'] not in ('WON', 'LOST', 'CUTOFF') for game in games):
                    raise ValueError('V321 final games retain explicit natural or cutoff endpoint status')
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
        result = {left + '_minus_' + right: None if hold else _interval(rows, values[left] - values[right], samples)
            for left, right in PAIRS}
        result[INTERACTION] = None if hold else _interval(rows,
            (values['NSTEP_QUERY'] - values['OLD_QUERY']) -
            (values['NSTEP_FACTUAL'] - values['OLD_FACTUAL']), samples)
        return result

    final = contrasts(TASKS)
    task_contrasts = {task: contrasts((task,)) for task in TASKS}
    primary = final['NSTEP_QUERY_minus_OLD_QUERY']
    primary_status = _status(primary)
    self_status = _status(final['NSTEP_QUERY_minus_FIRST_LOCAL'])
    retention = {task: _status(task_contrasts[task]['NSTEP_QUERY_minus_FIRST_LOCAL'], retention=True)
        for task in TASKS}
    retained = self_status == 'SUPPORTED_GAIN' and all(value == 'SUPPORTED_NONDECREASE'
        for value in retention.values())
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        primary_intervention_supported=primary_status == 'SUPPORTED_GAIN',
        primary_self_improvement_status=self_status,
        primary_self_improvement_supported=self_status == 'SUPPORTED_GAIN',
        final_net_gain_status=_status(final['NSTEP_QUERY_minus_SOURCE']),
        factual_intervention_status=_status(final['NSTEP_FACTUAL_minus_OLD_FACTUAL']),
        interaction_status=_status(final[INTERACTION]),
        final_ab_contrasts=final, task_contrasts=task_contrasts, task_retention_status=retention,
        retained_improvement_supported=retained,
        repaired_query_supported=retained and primary_status == 'SUPPORTED_GAIN',
        by_lifecycle=records, complete_game_endpoints=not hold, cutoffs=cutoffs,
        physical_evaluation_games=physical_games, bootstrap_seed=32100001, bootstrap_draws=draws,
        bootstrap_executed=not hold, bootstrap_unit='PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        evidence_scope='Controlled reward-target intervention on the existing sixteen-life FIRST cohort under four '
            'frozen SOURCE parents. The four learners keep the same factual/query roots, all original members, '
            'unchanged WIN labels, alpha and update order. N-step reward labels use the retained DIRECT action, '
            'immutable FIRST H2 continuation and a frozen FIRST bootstrap after four total actions; they are not '
            'terminal truth. Final six-arm evaluation uses paired fresh natural-game streams, with lifecycle '
            'rather than individual games as the bootstrap unit. The sole primary tests NSTEP_QUERY minus '
            'OLD_QUERY; own-FIRST growth and both-task retention are separate requirements. Any cutoff preserves '
            'every endpoint and holds all terminal-benefit inference. Secondary intervals are nominal and '
            'exploratory; four fixed parents do not establish unconditional SOURCE replication or ordinary '
            'online sampling-efficiency, and actual data acquisition and computation costs can differ.')
