"""First-spawn joint-support stratification for two frozen policies.

The two actions share a uniform cell-index variate and the same tile rank.
Independent block estimates measure conditional noise on eight fixed boards;
this module does not learn policies or define a strategy acceptance gate.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from math import isfinite, sqrt
from statistics import mean, variance

SCHEMA = 'acfqp.spawn_stratification.v176'
LIVES = (0, 1, 2, 3)
COHORTS = ('TRAIN', 'FRESH')
METHODS = ('STRAT', 'IID')
BLOCKS = 8
MIN_REPLICATES = 2
PAIRS_PER_STRATUM = 4
METRICS = ('utility', 'reward', 'failure', 'success')


def joint_support(tree_empty, one_empty):
    """Return the exact uniform-index coupling's positive-probability strata.

The input lists are the native spawn interface's ordered empty cell indices.
Fractions merge mathematically equal endpoints before JSON floats are made.
"""
    tree_empty, one_empty = list(tree_empty), list(one_empty)
    if not tree_empty or not one_empty:
        raise ValueError('both nonterminal actions need a nonempty spawn support')
    if len(set(tree_empty)) != len(tree_empty) or len(set(one_empty)) != len(one_empty):
        raise ValueError('distinct native empty cells required')
    sizes = (len(tree_empty), len(one_empty))
    boundaries = sorted({Fraction(index, size) for size in sizes for index in range(size+1)})
    strata = []
    for lower, upper in zip(boundaries, boundaries[1:]):
        midpoint = (lower+upper)/2
        tree_cell = tree_empty[int(midpoint*sizes[0])]
        one_cell = one_empty[int(midpoint*sizes[1])]
        for rank, mass in ((1, Fraction(9, 10)), (2, Fraction(1, 10))):
            strata.append(dict(stratum=len(strata), lower=float(lower), upper=float(upper), rank=rank,
                tree_cell=tree_cell, one_cell=one_cell, probability=float((upper-lower)*mass)))
    return strata


def allocation(support):
    """Allocate exactly 4*S pairs, retaining at least two per stratum.

    Extra pairs greedily maximize p_s**2/(n_s*(n_s+1)), with stratum ties.
    This minimizes sum(p_s**2/n_s) under equal conditional variance and the
    minimum counts. No outcome or estimated variance enters the allocation.
"""
    support = list(support)
    if not support:
        raise ValueError('nonempty joint support required')
    extras = MIN_REPLICATES*len(support)
    # Uniform native 16-cell supports and rank masses 9/10, 1/10 have
    # denominator at most 16*16*10. Recover their exact JSON probabilities
    # so equal mathematical marginal reductions obey the frozen tie order.
    probabilities = {row['stratum']: Fraction(row['probability']).limit_denominator(16*16*10) for row in support}
    counts = {stratum: MIN_REPLICATES for stratum in probabilities}
    for _ in range(extras):
        selected = min(counts, key=lambda stratum: (-probabilities[stratum]**2/(counts[stratum]*(counts[stratum]+1)), stratum))
        counts[selected] += 1
    return {stratum: counts[stratum] for stratum in sorted(counts)}


def _metrics(vector):
    return dict(zip(METRICS, [vector[0]-vector[1]+vector[2], *vector]))


def _series(rows, work):
    rows = sorted(rows, key=lambda row: row['block'])
    blocks = [dict(block=row['block'], components=list(row['components']), metrics=_metrics(row['components']),
                   physical_branches=row['physical_branches'], environment_samples=row['environment_samples']) for row in rows]
    mean_environment_samples = mean(row['environment_samples'] for row in blocks)
    work['batch_utility_evaluations'] += len(blocks)
    stats = {}
    for metric in METRICS:
        values = [row['metrics'][metric] for row in blocks]
        block_variance = variance(values)
        stats[metric] = dict(mean=mean(values), block_estimate_variance=block_variance,
                             mean_estimate_variance=block_variance/BLOCKS,
                             block_variance_environment_cost_product=block_variance*mean_environment_samples)
        work['batch_metric_sample_variances'] += 1
    return dict(per_block=blocks, metrics=stats,
                mean_per_block_physical_branches=mean(row['physical_branches'] for row in blocks),
                mean_per_block_environment_samples=mean_environment_samples,
                total_physical_branches=sum(row['physical_branches'] for row in blocks),
                total_environment_samples=sum(row['environment_samples'] for row in blocks))


def _contrast(strat, iid, work):
    stats = {}
    for metric in METRICS:
        strat_variance = strat['metrics'][metric]['block_estimate_variance']
        iid_variance = iid['metrics'][metric]['block_estimate_variance']
        strat_values = [row['metrics'][metric] for row in strat['per_block']]
        iid_values = [row['metrics'][metric] for row in iid['per_block']]
        leave_one = [variance(strat_values[:index]+strat_values[index+1:])-
                     variance(iid_values[:index]+iid_values[index+1:]) for index in range(BLOCKS)]
        center = mean(leave_one)
        jackknife_se = sqrt((BLOCKS-1)/BLOCKS*sum((value-center)**2 for value in leave_one))
        difference = strat_variance-iid_variance
        stats[metric] = dict(variance_ratio=strat_variance/iid_variance if iid_variance > 0 else None,
            block_variance_difference=difference, mean_variance_difference=difference/BLOCKS,
            variance_difference_jackknife_se=jackknife_se,
            variance_difference_jackknife_ci95=[difference-1.96*jackknife_se, difference+1.96*jackknife_se])
        work.update(variance_difference_leave_one_block_out_estimates=BLOCKS,
                    jackknife_metric_sample_variances=2*BLOCKS)
    return stats


def analyze_batches(batches):
    """Analyze exactly two methods x eight blocks x eight fixed boards.

Each batch already contains one unbiased TREE-minus-ONE complete-vector
estimate. The primary series averages all eight boards within each block,
then measures its eight independent estimates' variance. Utility is formed
from each complete vector before its variance is computed.
"""
    batches = list(batches)
    issues, work, index, identities = [], Counter(), {}, {}
    for row in batches:
        work['batch_rows_indexed'] += 1
        identity = (row['cohort'], row['root_id'])
        key = (row['method'], row['block'], *identity)
        if key in index:
            issues.append(f'duplicate_batch:{key}')
        index[key] = row
        if row['method'] not in METHODS or row['block'] not in range(BLOCKS):
            issues.append(f'unexpected_batch:{key}')
        if row['cohort'] not in COHORTS or row['life'] not in LIVES:
            issues.append(f'unknown_fixed_board:{identity}')
        if identity in identities and identities[identity] != row['life']:
            issues.append(f'board_history_mismatch:{identity}')
        identities[identity] = row['life']
        vector = row['components']
        if len(vector) != 3 or not all(isfinite(value) for value in vector):
            issues.append(f'incomplete_batch_vector:{key}')
        work['batch_component_reads'] += len(vector)
        if row['physical_branches'] <= 0 or row['environment_samples'] <= 0:
            issues.append(f'incomplete_batch_cost:{key}')
        work['batch_cost_reads'] += 2
    cohort_histories = Counter((cohort, life) for (cohort, _), life in identities.items())
    if set(cohort_histories) != {(cohort, life) for cohort in COHORTS for life in LIVES} or any(count != 1 for count in cohort_histories.values()):
        issues.append('fixed_eight_board_roster_mismatch')
    expected = {(method, block, *identity) for method in METHODS for block in range(BLOCKS) for identity in identities}
    if set(index) != expected or len(batches) != len(expected):
        issues.append('incomplete_batch_roster')
    if not issues:
        for identity in identities:
            for block in range(BLOCKS):
                if index[('STRAT', block, *identity)]['physical_branches'] != index[('IID', block, *identity)]['physical_branches']:
                    issues.append(f'unmatched_physical_budget:{identity}:{block}')
    result = dict(schema=SCHEMA, complete=not issues, issues=issues, blocks=BLOCKS,
                  roots=len(identities), methods={}, comparison={}, work=dict(work),
                  scope=('conditional variance on eight fixed boards and frozen TREE/ONE actions; '
                         'paired variance-difference jackknife normal intervals approximate with eight blocks; no strategy gate'))
    if issues:
        return result
    for method in METHODS:
        per_root = []
        for (cohort, root_id), life in sorted(identities.items()):
            series = _series([index[method, block, cohort, root_id] for block in range(BLOCKS)], work)
            per_root.append(dict(cohort=cohort, root_id=root_id, life=life, **series))
        all_blocks, history_blocks = [], defaultdict(list)
        for block in range(BLOCKS):
            rows = [index[(method, block, *identity)] for identity in identities]
            vector = [mean(row['components'][component] for row in rows) for component in range(3)]
            all_blocks.append(dict(block=block, components=vector,
                physical_branches=sum(row['physical_branches'] for row in rows),
                environment_samples=sum(row['environment_samples'] for row in rows)))
            work['fixed_board_component_mean_reads'] += 3*len(rows)
            for life in LIVES:
                local = [row for row in rows if row['life'] == life]
                vector = [mean(row['components'][component] for row in local) for component in range(3)]
                history_blocks[life].append(dict(block=block, components=vector,
                    physical_branches=sum(row['physical_branches'] for row in local),
                    environment_samples=sum(row['environment_samples'] for row in local)))
                work['fixed_history_component_mean_reads'] += 3*len(local)
        per_history = [dict(life=life, roots=2, **_series(history_blocks[life], work)) for life in LIVES]
        result['methods'][method] = dict(**_series(all_blocks, work), per_root=per_root, per_history=per_history)
    strat, iid = (result['methods'][method] for method in METHODS)
    result['comparison'] = dict(contrast='STRAT/IID', jackknife_blocks=BLOCKS, metrics=_contrast(strat, iid, work),
        per_root=[dict(cohort=left['cohort'], root_id=left['root_id'], life=left['life'], metrics=_contrast(left, right, work))
                  for left, right in zip(strat['per_root'], iid['per_root'])],
        per_history=[dict(life=left['life'], metrics=_contrast(left, right, work))
                     for left, right in zip(strat['per_history'], iid['per_history'])])
    result['work'] = dict(work)
    return result
