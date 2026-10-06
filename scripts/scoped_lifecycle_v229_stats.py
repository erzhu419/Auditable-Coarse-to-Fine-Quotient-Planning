"""Frozen, whole-lifecycle paired statistics for the fresh scoped repair test."""
from fractions import Fraction as F
import random

ARMS = ('REPAIR_CS', 'REBUILD_CS', 'PARAM')
STAGES = ('A', 'B', 'A_RETURN')
LIVES, BOOTSTRAP_SEED, BOOTSTRAP_REPEATS = 12, 251900, 5000
REFERENCES = ('REBUILD_CS', 'PARAM')
CONTRASTS = tuple(name for reference in REFERENCES for name in (
    reference.lower()+'_minus_repair_samples',
    reference.lower()+'_minus_repair_b_samples',
    'repair_minus_'+reference.lower()+'_late_b_utility',
    'repair_minus_'+reference.lower()+'_late_b_regret',
    'repair_minus_'+reference.lower()+'_late_b_resolved_queries'))


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def number(value):
    return float(F(value))


def resolved(row):
    return row['execution_certified'] or row['goal_impossible']


def late_b(row):
    return row['stage'] == 'B' and row['index'] >= 42


def metrics(rows):
    points = [point for row in rows for point in row['history']]
    return dict(targets=len(rows), target_samples=sum(row['spent'] for row in rows),
        execution_certified=sum(row['execution_certified'] for row in rows),
        goal_impossible_certified=sum(row['goal_impossible'] for row in rows),
        oracle_unreachable=sum(F(row['oracle_goal']) < 2 for row in rows),
        false_impossible_certificates=sum(row['goal_impossible'] and F(row['oracle_goal']) >= 2 for row in rows),
        goal_resolved=sum(resolved(row) for row in rows),
        query_certified=sum(row['query_certified'] for row in rows),
        resolved_queries=sum(resolved(row) and row['query_certified'] for row in rows),
        actual_utility=mean(number(row['terminal']['actual_utility']) for row in rows),
        actual_query_regret=mean(number(query['regret']) for row in rows for query in row['query_post'].values()),
        maximum_actual_risk=max(number(point['actual'][1]) for point in points),
        point_commits=sum(row['point_committed'] for row in rows),
        wrong_point_commits=sum(row['point_committed'] and not row['point_commit_correct'] for row in rows))


def summarize(results, source_costs, arm_seconds, work, common_A_path):
    """Rows include oracle scores only after all chronological decisions freeze."""
    arms = {}
    for arm in ARMS:
        rows = [row for row in results if row['arm'] == arm]
        stage = {name: metrics([row for row in rows if row['stage'] == name]) for name in STAGES}
        late = metrics([row for row in rows if late_b(row)])
        source = sum(source_costs[arm])
        total = metrics(rows)
        total.update(source_samples=source, total_samples=source+total['target_samples'],
                     model_processing_seconds=sum(arm_seconds[arm]),
                     model_processing_seconds_per_life=arm_seconds[arm], stages=stage, late_b=late)
        arms[arm] = total

    contrasts = {key: [] for key in CONTRASTS}
    for life in range(LIVES):
        rows = {arm: [row for row in results if row['life'] == life and row['arm'] == arm] for arm in ARMS}
        totals = {arm: source_costs[arm][life]+sum(row['spent'] for row in rows[arm]) for arm in ARMS}
        b_samples = {arm: sum(row['spent'] for row in rows[arm] if row['stage'] == 'B') for arm in ARMS}
        late = {arm: metrics([row for row in rows[arm] if late_b(row)]) for arm in ARMS}
        for reference in REFERENCES:
            values = (totals[reference]-totals['REPAIR_CS'], b_samples[reference]-b_samples['REPAIR_CS'],
                late['REPAIR_CS']['actual_utility']-late[reference]['actual_utility'],
                late['REPAIR_CS']['actual_query_regret']-late[reference]['actual_query_regret'],
                late['REPAIR_CS']['resolved_queries']-late[reference]['resolved_queries'])
            keys = (reference.lower()+'_minus_repair_samples', reference.lower()+'_minus_repair_b_samples',
                'repair_minus_'+reference.lower()+'_late_b_utility',
                'repair_minus_'+reference.lower()+'_late_b_regret',
                'repair_minus_'+reference.lower()+'_late_b_resolved_queries')
            for key, value in zip(keys, values):
                contrasts[key].append(value)
    rng = random.Random(BOOTSTRAP_SEED)
    samples = {key: [] for key in CONTRASTS}
    for _ in range(BOOTSTRAP_REPEATS):
        indices = [rng.randrange(LIVES) for _ in range(LIVES)]
        work['bootstrap_index_draws'] += LIVES
        for key, values in contrasts.items():
            samples[key].append(mean(values[i] for i in indices))
            work['bootstrap_mean_terms'] += LIVES
    bootstrap = {key: dict(mean=mean(values), ci=[sorted(samples[key])[124], sorted(samples[key])[4874]])
                 for key, values in contrasts.items()}

    repair = arms['REPAIR_CS']
    history = [point for row in results for point in row['history']]
    common_a = common_A_path
    processing_ratio = sum(arm_seconds['REPAIR_CS'])/sum(arm_seconds['REBUILD_CS'])
    conditions = dict(
        RISK_SCOPE=all(F(point['actual'][1]) <= F(1,20) and F(point['risk_upper']) <= F(1,20)
                       and point['coverage'] and point['true_candidate'] and point['true_candidate_coverage']
                       and point['query_bounds_ok'] and point['goal_upper_ok'] for point in history)
            and all(row['true_branch_retained'] and row['true_masks_retained'] for row in results)
            and all(arm['wrong_point_commits'] == 0 and arm['false_impossible_certificates'] == 0 for arm in arms.values()),
        B_QUALITY=repair['late_b']['resolved_queries'] >= 108 and repair['late_b']['actual_query_regret'] <= .05
            and all(repair['late_b']['resolved_queries'] >= arms[reference]['late_b']['resolved_queries']
                    and bootstrap['repair_minus_'+reference.lower()+'_late_b_utility']['ci'][0] >= -.05
                    for reference in REFERENCES),
        OLD_RETENTION=common_a and repair['stages']['A_RETURN']['resolved_queries'] >= 216
            and all(repair['stages'][stage]['actual_query_regret'] <= .05 for stage in ('A', 'A_RETURN')),
        REBUILD_REFERENCE=bootstrap['rebuild_cs_minus_repair_samples']['mean'] >= 64
            and bootstrap['rebuild_cs_minus_repair_samples']['ci'][0] > 0,
        PARAMETER_REFERENCE=bootstrap['param_minus_repair_samples']['mean'] >= 64
            and bootstrap['param_minus_repair_samples']['ci'][0] > 0,
        PROCESSING_COST=processing_ratio <= 1.25)
    complete = len(results) == LIVES*72*len(ARMS) and all(
        arms[arm]['stages'][stage]['targets'] == LIVES*24 for arm in ARMS for stage in STAGES)
    return dict(complete=complete, arms=arms, contrasts=contrasts, bootstrap=bootstrap, conditions=conditions,
        common_A_paths=common_a,
        processing_ratio_repair_to_rebuild=processing_ratio,
        bootstrap_design=dict(unit='whole_paired_lifecycle', lives=LIVES, seed=BOOTSTRAP_SEED,
                              repeats=BOOTSTRAP_REPEATS, interval='95_percent_percentile'),
        confidence=dict(scope='per_arm_per_lifecycle', delta=.05, member_streams=504,
                        member_delta=.025, member_threshold=20160, A_pool_streams=21,
                        A_pool_delta=.0125, B_pool_streams=21, B_pool_delta=.0125, pool_threshold=1680),
        decision='SCOPED_REPAIR_LIFECYCLE_SUPPORTED' if complete and all(conditions.values())
                 else 'SCOPED_REPAIR_LIFECYCLE_NOT_SUPPORTED')
