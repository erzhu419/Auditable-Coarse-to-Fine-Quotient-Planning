"""Saved WIN predictions against fresh conditional FIRST terminal outcomes."""
import random

import numpy as np

TASKS = ('A', 'B')
ROUNDS = ('1', '2')
ARMS = ('FACTUAL_WIN', 'QUERY_WIN')
SNAPSHOTS = ('FIRST', 'before', 'after', 'FINAL')
GROUP_INDICES = np.linspace(0, 16383, 64, dtype=np.int64).tolist()
PRIMARY = 'FINAL_QUERY_WIN_MINUS_FIRST_BRIER_ON_QUERY_ROOTS'
BOOTSTRAP_SEED = 32500001
CONTINUATION_SEED = 325500000000
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_SOURCE_PARENTS_AND_64_FIXED_EQUIDISTANT_V324_ROOTGROUPS'


def _samples(rows, draws):
    groups = [[index for index, row in enumerate(rows) if row['parent'] == parent] for parent in range(4)]
    rng = random.Random(BOOTSTRAP_SEED)
    return np.asarray([[rng.choices(group, k=4) for group in groups] for _ in range(draws)], dtype=np.int64)


def _status(interval, kind):
    lo, hi = interval['ci95']
    if kind == 'brier_change':
        return 'SUPPORTED_WORSE_PREDICTION' if lo > 0 else 'SUPPORTED_BETTER_PREDICTION' if hi < 0 else 'UNRESOLVED'
    if kind == 'bias':
        return 'SUPPORTED_OPTIMISTIC_BIAS' if lo > 0 else 'SUPPORTED_PESSIMISTIC_BIAS' if hi < 0 else 'UNRESOLVED'
    return 'SUPPORTED_MORE_OPTIMISTIC' if lo > 0 else 'SUPPORTED_MORE_PESSIMISTIC' if hi < 0 else 'UNRESOLVED'


def _interval(rows, values, samples, kind=None):
    values = np.asarray(values, dtype=np.float64)
    distribution = values[samples].mean(axis=2).mean(axis=1)
    result = dict(mean=float(values.mean()), ci95=np.quantile(distribution, [.025, .975]).tolist(),
        lifecycle_values={str(row['lifecycle']): float(value) for row, value in zip(rows, values)},
        parent_mean_values={str(parent): float(np.mean([value for row, value in zip(rows, values)
            if row['parent'] == parent])) for parent in range(4)},
        positive_equal_negative=[int(np.sum(values > 0)), int(np.sum(values == 0)), int(np.sum(values < 0))],
        interval_scope=INTERVAL_SCOPE)
    if kind is not None:
        result['status95'] = _status(result, kind)
    return result


def _probability(value):
    if not isinstance(value, (int, float)) or not np.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('V325 retains finite WIN probabilities between zero and one')


def _versions(row, task, number, arm, item):
    versions, first = item['prediction_versions'], row['initial'][task]['teacher_version']
    if set(versions) != set(SNAPSHOTS) or versions['FIRST'] != first:
        raise ValueError('V325 root predictions keep the actual FIRST teacher version')
    for name, version in versions.items():
        if (version['lifecycle'] != row['lifecycle'] or version['parent'] != row['parent'] or
                version['context_id'] != first['context_id']):
            raise ValueError('V325 prediction versions retain their actual lifecycle and bank')
        expected_arm = 'FIRST_LOCAL' if name == 'FIRST' or (name == 'before' and number == '1') else arm
        expected_number = {'FIRST': 0, 'before': int(number)-1, 'after': int(number), 'FINAL': 2}[name]
        if version['arm'] != expected_arm or version['version'] != expected_number:
            raise ValueError('V325 before, after and final predictions use the declared own checkpoints')
    if number == '1':
        if versions['before'] != first or versions['after']['base_file'] != first['file']:
            raise ValueError('V325 round one starts from the actual FIRST version')
        if versions['FINAL']['base_file'] != versions['after']['file']:
            raise ValueError('V325 final snapshot advances its own round-one checkpoint')
    else:
        previous = row['stages']['1'][task]['arms'][arm]['prediction_versions']
        if (versions['before'] != previous['after'] or versions['after'] != previous['FINAL'] or
                versions['FINAL'] != versions['after'] or versions['after']['base_file'] != versions['before']['file']):
            raise ValueError('V325 round two preserves the saved own update lineage')


def _calibration(groups):
    actual = np.asarray([[replica['actual_win'] for replica in group['replicas']] for group in groups], dtype=np.float64)
    teacher = np.asarray([[replica['teacher_win'] for replica in group['replicas']] for group in groups], dtype=np.float64)
    predictions = {name: np.asarray([group['predictions'][name] for group in groups], dtype=np.float64)[:, None]
        for name in SNAPSHOTS}

    def metrics(probability):
        error = probability-actual
        return dict(mean_probability=float(probability.mean()), signed_bias=float(error.mean()),
            brier=float(np.square(error).mean()))

    root = {name: metrics(prediction) for name, prediction in predictions.items()}
    changes = {metric: {left+'_minus_'+right: root[left][metric]-root[right][metric]
        for left, right in (('after', 'before'), ('FINAL', 'FIRST'))} for metric in ('brier', 'signed_bias')}
    return dict(root_prediction=root, member_teacher=metrics(teacher), terminal_win_rate=float(actual.mean()),
        root_brier_change=changes['brier'], root_signed_bias_change=changes['signed_bias'])


def summarize(lives, draws=20000):
    """Use equal task/round/root/member weights and paired existing-lifecycle intervals."""
    rows = sorted(lives, key=lambda row: row['lifecycle'])
    if ([row['lifecycle'] for row in rows] != list(range(16)) or
            any(row['parent'] != row['lifecycle'] % 4 for row in rows)):
        raise ValueError('V325 retains all sixteen V324 learning histories under their four fixed parents')
    if draws < 2:
        raise ValueError('V325 bootstrap requires at least two draws')
    records, retained, cutoffs = [], [], []
    physical_rollouts = 0
    for row in rows:
        cells = {}
        for number in ROUNDS:
            for task in TASKS:
                stage = row['stages'][number][task]
                if not stage['teacher_unchanged'] or stage['teacher_version'] != row['initial'][task]['teacher_version']:
                    raise ValueError('V325 continuation keeps the actual immutable FIRST teacher')
                if stage['groups'] != 64 or stage['replicas'] != 4 or stage['selected_group_indices'] != GROUP_INDICES:
                    raise ValueError('V325 uses all four members at the frozen 64 equidistant rootgroup indices')
                if set(stage['arms']) != set(ARMS):
                    raise ValueError('V325 retains both factual and query root distributions')
                arms, paired_seeds = {}, {}
                for arm in ARMS:
                    item = stage['arms'][arm]
                    _versions(row, task, number, arm, item)
                    if item['prediction_versions']['after']['arm'] != arm:
                        raise ValueError('V325 predictions use the declared own WIN learner')
                    groups = item['groups']
                    if (len(groups) != 64 or [group['index'] for group in groups] != GROUP_INDICES or
                            any(len(group['replicas']) != 4 for group in groups)):
                        raise ValueError('V325 retains the complete paired rootgroup and member grid')
                    paired_seeds[arm] = [[replica['seed'] for replica in group['replicas']] for group in groups]
                    for group in groups:
                        predictions = group['predictions']
                        if set(predictions) != set(SNAPSHOTS):
                            raise ValueError('V325 retains all four common-root prediction snapshots')
                        for value in predictions.values():
                            _probability(value)
                        if ((number == '1' and predictions['before'] != predictions['FIRST']) or
                                (number == '2' and predictions['after'] != predictions['FINAL'])):
                            raise ValueError('V325 identical saved snapshots give identical root predictions')
                        for member, replica in enumerate(group['replicas']):
                            expected_seed = (CONTINUATION_SEED + row['lifecycle']*10000000 + TASKS.index(task)*1000000
                                + int(number)*100000 + group['index']*4 + member)
                            if replica['seed'] != expected_seed:
                                raise ValueError('V325 retains the declared fresh suffix seed for every root position and member')
                            _probability(replica['teacher_win'])
                            status = replica['status']
                            if status not in ('WON', 'LOST', 'CUTOFF'):
                                raise ValueError('V325 retains each explicit natural or cutoff continuation endpoint')
                            if status == 'CUTOFF':
                                if replica['actual_win'] is not None:
                                    raise ValueError('V325 CUTOFF has no fabricated terminal WIN label')
                                cutoffs.append(dict(lifecycle=row['lifecycle'], task=task, round=int(number),
                                    arm=arm, group_index=group['index'], member=member, seed=replica['seed']))
                            elif replica['actual_win'] != int(status == 'WON'):
                                raise ValueError('V325 terminal WIN labels agree with natural endpoint status')
                            physical_rollouts += 1
                    arms[arm] = groups
                if paired_seeds[ARMS[0]] != paired_seeds[ARMS[1]]:
                    raise ValueError('V325 corresponding root positions retain paired suffix seeds across arms')
                cells['R'+number+'_'+task] = arms
        retained.append(cells)
        records.append(dict(lifecycle=row['lifecycle'], parent=row['parent'], cells={}))
    hold = bool(cutoffs)
    cell_names = ('R1_A', 'R1_B', 'R2_A', 'R2_B')
    for record, cells in zip(records, retained):
        record['cells'] = {cell: {arm: None if hold else _calibration(cells[cell][arm]) for arm in ARMS}
            for cell in cell_names}
        record['retained_endpoint_counts'] = {cell: {arm: dict(rootgroups=len(cells[cell][arm]),
            replicas=sum(len(group['replicas']) for group in cells[cell][arm]),
            **{status: sum(replica['status'] == status for group in cells[cell][arm] for replica in group['replicas'])
                for status in ('WON', 'LOST', 'CUTOFF')}) for arm in ARMS} for cell in cell_names}
    samples = None if hold else _samples(rows, draws)

    def intervals(cells):
        def metric(path, kind=None):
            def get(value):
                for key in path:
                    value = value[key]
                return value
            return _interval(rows, [float(np.mean([get(record['cells'][cell][arm]) for cell in cells]))
                for record in records], samples, kind)
        root, teacher, brier_changes, bias_changes, rates = {}, {}, {}, {}, {}
        for arm in ARMS:
            root[arm] = {name: {key: metric(('root_prediction', name, key), 'bias' if key == 'signed_bias' else None)
                for key in ('mean_probability', 'signed_bias', 'brier')} for name in SNAPSHOTS}
            teacher[arm] = {key: metric(('member_teacher', key), 'bias' if key == 'signed_bias' else None)
                for key in ('mean_probability', 'signed_bias', 'brier')}
            brier_changes[arm] = {name: metric(('root_brier_change', name), 'brier_change')
                for name in ('after_minus_before', 'FINAL_minus_FIRST')}
            bias_changes[arm] = {name: metric(('root_signed_bias_change', name), 'bias_change')
                for name in ('after_minus_before', 'FINAL_minus_FIRST')}
            rates[arm] = metric(('terminal_win_rate',))
        return dict(root_prediction=root, member_teacher=teacher, root_brier_change=brier_changes,
            root_signed_bias_change=bias_changes, terminal_win_rate=rates)

    overall = None if hold else intervals(cell_names)
    primary = None if hold else overall['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST']
    primary_status = 'HOLD_CUTOFF' if hold else primary['status95']
    return dict(primary_contrast=PRIMARY, primary=primary, primary_status=primary_status,
        updated_prediction_worse_supported=primary_status == 'SUPPORTED_WORSE_PREDICTION',
        updated_prediction_better_supported=primary_status == 'SUPPORTED_BETTER_PREDICTION',
        overall=overall, by_task=None if hold else {task: intervals(('R1_'+task, 'R2_'+task)) for task in TASKS},
        by_round=None if hold else {number: intervals(('R'+number+'_A', 'R'+number+'_B')) for number in ROUNDS},
        by_stage=None if hold else {cell: intervals((cell,)) for cell in cell_names}, by_lifecycle=records,
        complete_terminal_endpoints=not hold, cutoffs=cutoffs, physical_conditional_rollouts=physical_rollouts,
        selected_group_indices=GROUP_INDICES, replicas_per_rootgroup=4,
        continuation_seed=CONTINUATION_SEED,
        bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=draws, bootstrap_executed=not hold,
        bootstrap_unit='PAIRED_EXISTING_V324_TARGET_LEARNING_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        estimator='EQUAL_TASKS_THEN_ROUNDS_THEN_ROOTGROUPS_THEN_MEMBERS_THEN_LIFECYCLES',
        secondary_interval_scope='NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM',
        root_brier_definition='MEAN_OF_SQUARED_COMMON_ROOT_PROBABILITY_MINUS_BINARY_TERMINAL_WIN_LABEL; '
            'EACH_ROOT_PROBABILITY_IS_COMPARED_WITH_ALL_FOUR_SAVED_SPAWN_DIRECT_MEMBER_CONTINUATIONS',
        target_calibration_definition='SAVED_FIRST_MEMBER_TARGET_WIN_MINUS_TERMINAL_WIN_UNDER_ITS_PRESCRIBED_DIRECT_AND_FROZEN_FIRST_H2',
        evidence_scope='Saved prediction snapshots are diagnosed on 64 frozen equidistant V324 rootgroup positions '
            'per distribution, task and round, all four saved initial spawn/DIRECT members, sixteen existing target '
            'learning histories and four frozen SOURCE parents. Each fresh continuation follows the saved DIRECT '
            'action and immutable FIRST H2 until its natural terminal endpoint. Root prediction error and conditional '
            'member teacher-target error are separate quantities: the teacher has member information unavailable to '
            'the common root probability. The sole primary is final QUERY root Brier minus its own FIRST Brier on '
            'QUERY roots; negative means better prediction. This fixed-grid, fixed-FIRST-policy diagnostic is not '
            'an independent learning cohort, an optimal WIN probability, whole-game utility or a causal explanation '
            'of V324 results. No new fits, policy evaluation games or changes to saved checkpoints occur. Any CUTOFF '
            'retains all observations and holds every terminal statistic without bootstrap or label imputation.')
