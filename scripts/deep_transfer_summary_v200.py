"""Frozen development decision for SOURCE-only successor-model transfer."""
from fractions import Fraction
from math import fsum


COEFFICIENTS = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
ARMS = ('COARSE', 'LEARNED', 'LEARNED_D1', 'NATIVE_H2')


def mean(values):
    values = list(values)
    return fsum(values)/len(values)


def utility(vector, query):
    r, f, s = COEFFICIENTS[query]
    return r*vector[0]-f*vector[1]+s*vector[2]


def strict_change(old, new, old_query, new_query):
    """Exclude old-query ties and require a real new-query root preference."""
    previous, selected = old['action'], new['action']
    if previous == selected:
        return False
    old_vectors = {a: tuple(Fraction(x) for x in v) for a, v in old['action_vector_fractions'].items()}
    new_vectors = {a: tuple(Fraction(x) for x in v) for a, v in new['action_vector_fractions'].items()}
    alternatives = [utility(v, old_query) for a, v in old_vectors.items() if a != previous]
    if not alternatives:
        return False
    margin = utility(old_vectors[previous], old_query)-max(alternatives)
    advantage = utility(new_vectors[selected], new_query)-utility(new_vectors[previous], new_query)
    return margin > Fraction(1, 10**10) and advantage > Fraction(1, 100)


def summarize(target_results, models, benchmark):
    """Aggregate all fixed roots; no fitting, physics or outcome selection."""
    changed, risk_changed = [], []
    for record in target_results:
        oracle = {row['query']: row['oracle'] for row in record['evaluations'] if row['horizon'] == 4}
        if any(strict_change(oracle['reward'], oracle[q], 'reward', q) for q in ('goal', 'risk')):
            changed.append(record['root_id'])
        if strict_change(oracle['goal'], oracle['risk'], 'goal', 'risk'):
            risk_changed.append(record['root_id'])
    terminal = benchmark['terminal_support_counts']
    informative = len(changed) >= 4 and len(risk_changed) >= 1 and terminal.get('WON', 0) > 0 and terminal.get('LOST', 0) > 0
    horizons = {}
    for h in (3, 4):
        rows = [row for case in target_results for row in case['evaluations'] if row['horizon'] == h]
        differences = {arm: mean(row['arms']['LEARNED']['actual']['utility']-row['arms'][arm]['actual']['utility'] for row in rows)
                       for arm in ('COARSE', 'LEARNED_D1', 'NATIVE_H2')}
        regret = mean(row['arms']['LEARNED']['regret'] for row in rows)
        predictions_complete = all(row['arms']['LEARNED']['predicted'] is not None for row in rows)
        errors = ([mean(abs(row['arms']['LEARNED']['predicted']['components'][k]-row['arms']['LEARNED']['actual']['components'][k])
                        for row in rows) for k in range(3)] if predictions_complete else None)
        fallback = max(row['arms']['LEARNED']['expected_fallback_visits'] for row in rows)
        active_ids = {cell for cell, layer, status in models['LEARNED']['cells'] if status == 'ACTIVE' and 2 <= layer <= h}
        active, action_rows = len(active_ids), sum(state in active_ids for state, _, _ in models['LEARNED']['rows'])
        baseline = benchmark[str(h)]
        cells_reduced = 1-active/baseline['D4_states'] if baseline['D4_states'] else 0.
        rows_reduced = 1-action_rows/baseline['D4_rows'] if baseline['D4_rows'] else 0.
        reuse = cells_reduced >= .2 and rows_reduced >= .2
        quality = predictions_complete and regret <= .05 and max(errors) <= .05 and differences['NATIVE_H2'] >= -.01 and fallback <= 1e-12
        depth = differences['COARSE'] >= .01 and differences['LEARNED_D1'] >= .01
        horizons[str(h)] = dict(root_query_records=len(rows), learned_mean_regret=regret,
            learned_max_regret=max(row['arms']['LEARNED']['regret'] for row in rows),
            learned_mean_absolute_prediction_errors=errors, predictions_complete=predictions_complete,
            learned_max_expected_fallback_visits=fallback, learned_minus=differences,
            deployed_deep_active_cells=active, deployed_deep_action_rows=action_rows,
            d4_deep_active_cells=baseline['D4_states'], d4_deep_action_rows=baseline['D4_rows'],
            deep_cell_reduction=cells_reduced, deep_row_reduction=rows_reduced,
            deep_reuse_pass=reuse, quality_pass=quality, added_depth_pass=depth,
            per_query={q: dict(learned_mean_regret=mean(row['arms']['LEARNED']['regret'] for row in rows if row['query'] == q),
                learned_minus={arm: mean(row['arms']['LEARNED']['actual']['utility']-row['arms'][arm]['actual']['utility']
                                       for row in rows if row['query'] == q) for arm in ('COARSE', 'LEARNED_D1', 'NATIVE_H2')})
                       for q in COEFFICIENTS})
    checks = dict(TASK=informative,
        DEEP_REUSE=all(row['deep_reuse_pass'] for row in horizons.values()),
        QUALITY=all(row['quality_pass'] for row in horizons.values()),
        ADDED_DEPTH=all(row['added_depth_pass'] for row in horizons.values()))
    complete = len(target_results) == 24 and all(row['root_query_records'] == 72 for row in horizons.values())
    advance = complete and all(checks.values())
    decision = 'RESUME_BOUNDED_LIFECYCLE' if advance else 'CLOSE_PARTITION_HYPOTHESIS' if informative and complete else 'TASK_NOT_INFORMATIVE' if complete else 'INCOMPLETE'
    return dict(schema='acfqp.deep_transfer.v200.summary', complete=complete,
        task=dict(reward_preference_changed_cases=changed, goal_to_risk_changed_cases=risk_changed,
                  terminal_support_counts=terminal, informative=informative),
        per_horizon=horizons, conditions=checks, advance=advance, decision=decision)
