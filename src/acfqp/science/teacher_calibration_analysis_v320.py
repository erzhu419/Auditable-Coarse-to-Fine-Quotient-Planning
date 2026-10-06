"""Frozen FIRST teacher errors against conditional terminal continuations."""
from math import floor
import random

import numpy as np

TASKS = ('A', 'B')
ARMS = ('FACTUAL_LOCAL', 'QUERY_LOCAL')
COMPONENTS = ('reward', 'win', 'combined')
GROUP_INDICES = np.linspace(0, 16383, 64, dtype=np.int64).tolist()
PRIMARY = 'QUERY_MINUS_FACTUAL_SIGNED_COMBINED_TEACHER_ERROR'


def _samples(rows, draws):
    groups = [[i for i, row in enumerate(rows) if row['parent'] == p] for p in range(4)]
    rng = random.Random(32000001)
    return np.asarray([[rng.choices(group, k=4) for group in groups] for _ in range(draws)], dtype=np.int64)


def _interval(rows, values, samples):
    values = np.asarray(values, dtype=np.float64)
    distribution = np.sort(values[samples].mean(axis=2).mean(axis=1))

    def quantile(level):
        position = (len(distribution)-1)*level
        lo = floor(position)
        hi = min(lo+1, len(distribution)-1)
        return float(distribution[lo]+(distribution[hi]-distribution[lo])*(position-lo))

    return dict(mean=float(values.mean()), ci95=[quantile(.025), quantile(.975)],
        lifecycle_values={str(row['lifecycle']):float(value) for row, value in zip(rows, values)},
        positive_equal_negative=[int(np.sum(values > 0)), int(np.sum(values == 0)), int(np.sum(values < 0))],
        parent_mean_values={str(p):float(np.mean([v for row, v in zip(rows, values) if row['parent'] == p]))
            for p in range(4)},
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_64_FIXED_EQUIDISTANT_V319_ROOTGROUPS')


def _status(interval, hold, difference=False):
    if hold:
        return 'HOLD_CUTOFF'
    lo, hi = interval['ci95']
    if lo > 0:
        return 'SUPPORTED_MORE_OPTIMISTIC' if difference else 'SUPPORTED_OPTIMISTIC_BIAS'
    if hi < 0:
        return 'SUPPORTED_MORE_PESSIMISTIC' if difference else 'SUPPORTED_PESSIMISTIC_BIAS'
    return 'UNRESOLVED'


def _calibration(groups):
    teacher = np.asarray([[[replica['teacher_reward'], replica['teacher_win']] for replica in group['replicas']]
        for group in groups], dtype=np.float64)
    actual = np.asarray([[[replica['actual_reward'], replica['actual_win']] for replica in group['replicas']]
        for group in groups], dtype=np.float64)
    teacher = np.concatenate((teacher, (teacher[..., 0]+8*teacher[..., 1])[..., None]), axis=2)
    actual = np.concatenate((actual, (actual[..., 0]+8*actual[..., 1])[..., None]), axis=2)
    error = teacher-actual
    centered = error-error.mean(axis=1, keepdims=True)

    def columns(values):
        return {name:float(values[i]) for i, name in enumerate(COMPONENTS)}

    return dict(mean_teacher=columns(teacher.mean(axis=(0, 1))), mean_actual=columns(actual.mean(axis=(0, 1))),
        signed_error=columns(error.mean(axis=(0, 1))), mean_absolute_error=columns(np.abs(error).mean(axis=(0, 1))),
        rms_error=columns(np.sqrt(np.square(error).mean(axis=(0, 1)))),
        centered_replica_error_rms=columns(np.sqrt(np.square(centered).mean(axis=(0, 1)))))


def summarize(lives, draws=20000):
    """Aggregate equal rootgroup/member weights, then paired lifecycle intervals."""
    rows = sorted(lives, key=lambda row:row['lifecycle'])
    if len(rows) != 16 or [row['lifecycle'] for row in rows] != list(range(16)) or any(
            row['parent'] != row['lifecycle'] % 4 for row in rows):
        raise ValueError('V320 retains all sixteen FIRST lifecycles under their four fixed parents')
    records, cutoffs, retained = [], [], []
    physical_rollouts = 0
    for row in rows:
        cells = {}
        for number in ('1', '2'):
            for task in TASKS:
                stage = row['stages'][number][task]
                if not stage['teacher_unchanged'] or stage['teacher_version'] != row['initial'][task]['teacher_version']:
                    raise ValueError('V320 continuation keeps the actual immutable FIRST teacher')
                if stage['groups'] != 64 or stage['replicas'] != 4 or stage['selected_group_indices'] != GROUP_INDICES:
                    raise ValueError('V320 uses all four replicas at the frozen 64 equidistant rootgroup indices')
                arms = {}
                paired_seeds = {}
                for arm in ARMS:
                    groups = stage['arms'][arm]['groups']
                    if len(groups) != 64 or [group['index'] for group in groups] != GROUP_INDICES or any(
                            len(group['replicas']) != 4 for group in groups):
                        raise ValueError('V320 both arms retain the complete paired rootgroup and member grid')
                    paired_seeds[arm] = [[replica['seed'] for replica in group['replicas']] for group in groups]
                    for group in groups:
                        for member, replica in enumerate(group['replicas']):
                            status = replica['status']
                            if status not in ('WON', 'LOST', 'CUTOFF'):
                                raise ValueError('V320 retains each explicit natural or cutoff continuation endpoint')
                            if status == 'CUTOFF' and (replica['actual_reward'] is not None or replica['actual_win'] is not None):
                                raise ValueError('V320 CUTOFF has no fabricated terminal reward or WIN label')
                            if status != 'CUTOFF' and replica['actual_reward'] != replica['score']/2048.:
                                raise ValueError('V320 terminal reward includes the retained DIRECT action and subsequent H2 actions')
                            if status != 'CUTOFF' and replica['actual_win'] != int(status == 'WON'):
                                raise ValueError('V320 terminal WIN labels agree with natural endpoint status')
                            if status == 'CUTOFF':
                                cutoffs.append(dict(lifecycle=row['lifecycle'], task=task, round=int(number),
                                    arm=arm, group_index=group['index'], member=member, seed=replica['seed']))
                            physical_rollouts += 1
                    arms[arm] = groups
                if paired_seeds[ARMS[0]] != paired_seeds[ARMS[1]]:
                    raise ValueError('V320 corresponding arms retain paired suffix seeds at the same rootgroup/member positions')
                cells['R'+number+'_'+task] = arms
        retained.append(cells)
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells={}))
    hold = bool(cutoffs)
    cell_names = ('R1_A', 'R1_B', 'R2_A', 'R2_B')
    for record, cells in zip(records, retained):
        record['cells'] = {cell:{arm:None if hold else _calibration(cells[cell][arm]) for arm in ARMS}
            for cell in cell_names}
        record['retained_endpoint_counts'] = {cell:{arm:dict(rootgroups=len(cells[cell][arm]),
            replicas=sum(len(group['replicas']) for group in cells[cell][arm]),
            cutoff=sum(replica['status'] == 'CUTOFF' for group in cells[cell][arm] for replica in group['replicas']))
            for arm in ARMS} for cell in cell_names}
    samples = None if hold else _samples(rows, draws)

    def intervals(cells):
        contrast, biases = {}, {arm:{} for arm in ARMS}
        for component in COMPONENTS:
            values = {arm:[float(np.mean([record['cells'][cell][arm]['signed_error'][component] for cell in cells]))
                for record in records] for arm in ARMS}
            contrast[component] = _interval(rows, np.subtract(values['QUERY_LOCAL'], values['FACTUAL_LOCAL']), samples)
            contrast[component]['status95'] = _status(contrast[component], hold, difference=True)
            for arm in ARMS:
                biases[arm][component] = _interval(rows, values[arm], samples)
                biases[arm][component]['status95'] = _status(biases[arm][component], hold)
        return dict(query_minus_factual=contrast, own_signed_bias=biases)

    overall = None if hold else intervals(cell_names)
    primary = None if hold else overall['query_minus_factual']['combined']
    primary_status = 'HOLD_CUTOFF' if hold else primary['status95']
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        differential_teacher_bias_supported=primary_status in ('SUPPORTED_MORE_OPTIMISTIC', 'SUPPORTED_MORE_PESSIMISTIC'),
        overall=overall, by_task=None if hold else {task:intervals(('R1_'+task, 'R2_'+task)) for task in TASKS},
        by_round=None if hold else {number:intervals(('R'+number+'_A', 'R'+number+'_B')) for number in ('1', '2')},
        by_stage=None if hold else {cell:intervals((cell,)) for cell in cell_names}, by_lifecycle=records,
        complete_terminal_endpoints=not hold, cutoffs=cutoffs, physical_conditional_rollouts=physical_rollouts,
        selected_group_indices=GROUP_INDICES, replicas_per_rootgroup=4,
        bootstrap_seed=32000001, bootstrap_draws=draws, bootstrap_executed=not hold,
        bootstrap_unit='PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        centered_replica_error_definition='SQRT_MEAN_WITHIN_ROOTGROUP_CENTERED_REPLICA_ERROR_SQUARES; '
            'DESCRIBES_FOUR_REALIZATIONS_NOT_EXACT_POPULATION_VARIANCE',
        evidence_scope='Conditional terminal calibration on 64 frozen equidistant V319 rootgroup positions per stage, '
            'all four retained initial spawn members, both arms, tasks and rounds, sixteen existing FIRST lifecycles '
            'and four frozen SOURCE parents. Each continuation replays the retained DIRECT action before immutable '
            'FIRST H2 execution. Actual reward includes that DIRECT score and later scores, excluding the action '
            'entering the root. Teacher-minus-terminal error is conditional on this continuation policy and fixed grid; '
            'it is not an optimal-value error or a representative-all-query-pool estimate. Any CUTOFF keeps every '
            'observation and holds all terminal-bias inference; its terminal reward and WIN label remain null. '
            'Secondary intervals are nominal and exploratory. No new fitting, learning benefit or causal explanation '
            'of the V319 behavioral loss is established by this calibration alone.')
