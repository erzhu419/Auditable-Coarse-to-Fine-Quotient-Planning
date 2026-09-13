"""Independent finite-window certificates for observed trajectory decisions."""
from collections import Counter
from itertools import combinations, product
import math


TOLERANCE = 1e-10
DEPTHS = {'LOOKAHEAD_1_ANALYTIC': 1, 'LOOKAHEAD_2_ANALYTIC': 2}
COUNTERS = ('dp_states', 'action_value_evaluations', 'kernel_builds', 'kernel_cache_hits',
            'transition_outcomes', 'target_probability_evaluations', 'score_node_evaluations',
            'immediate_expectation_terms', 'bellman_expectation_terms',
            'analytic_expectation_calls', 'analytic_probability_terms')


def verify_decision(decision, graph_metadata, method):
    """Recompute one cold short-window query without evaluating a complete policy."""
    errors, counts = Counter(), Counter(dict.fromkeys(COUNTERS, 0))
    fees = Counter(queries=1, graph_model_builds=1, parent_membership_checks=0,
                   parent_product_factors=0, outcome_probability_factors=0,
                   value_cache_hits=0, root_Q_comparisons=0)
    parents = [[] for _ in range(graph_metadata['nodes'])]
    for source, target in graph_metadata['edges']:
        parents[target].append(source)
    parents = [sorted(items) for items in parents]
    statuses = tuple(decision['statuses'])
    budget, days = decision['remaining_budget'], decision['remaining_days']
    depth = min(DEPTHS[method], days)
    values, kernels = {}, {}

    def legal(state, b, h):
        inactive = tuple(i for i, status in enumerate(state) if status == 0)
        size = min(len(inactive), b, (b + h - 1) // h)
        return inactive, size

    def probabilities(state, selected):
        active = {i for i, status in enumerate(state) if status == 1} | set(selected)
        result = []
        for target, status in enumerate(state):
            if status != 0 or target in active:
                continue
            counts['target_probability_evaluations'] += 1
            fees['parent_membership_checks'] += len(parents[target])
            factors = [1. - 1. / len(parents[target]) for source in parents[target] if source in active]
            fees['parent_product_factors'] += len(factors)
            result.append((target, 1. - math.prod(factors)))
        return active, result

    def outcomes(state, selected):
        key = state, selected
        if key in kernels:
            counts['kernel_cache_hits'] += 1
            return kernels[key]
        counts['kernel_builds'] += 1
        active, probabilities_by_target = probabilities(state, selected)
        certain = {target for target, p in probabilities_by_target if p == 1.}
        uncertain = [(target, p) for target, p in probabilities_by_target if 0. < p < 1.]
        result = []
        for bits in product((False, True), repeat=len(uncertain)):
            probability = math.prod(p if bit else 1. - p for (_, p), bit in zip(uncertain, bits))
            fees['outcome_probability_factors'] += len(uncertain)
            activated = certain | {target for (target, _), bit in zip(uncertain, bits) if bit}
            after = tuple(2 if i in active else 1 if i in activated else status
                          for i, status in enumerate(state))
            result.append((probability, after, len(selected) + len(activated)))
        counts['transition_outcomes'] += len(result)
        kernels[key] = result
        return result

    def query(state, b, h, d):
        key = state, b, h, d
        if key in values:
            fees['value_cache_hits'] += 1
            return values[key]
        counts['dp_states'] += 1
        inactive, size = legal(state, b, h)
        action_values = []
        for selected in combinations(inactive, size):
            counts['action_value_evaluations'] += 1
            if d == 1:
                counts['analytic_expectation_calls'] += 1
                _, target_probabilities = probabilities(state, selected)
                counts['analytic_probability_terms'] += len(target_probabilities)
                value = math.fsum([float(len(selected)), *(p for _, p in target_probabilities)])
            else:
                branches = outcomes(state, selected)
                counts['bellman_expectation_terms'] += len(branches)
                value = math.fsum(p * (reward + max(q for _, q in query(after, b - size, h - 1, d - 1)))
                                  for p, after, reward in branches)
            action_values.append((selected, value))
        values[key] = action_values
        return action_values

    inactive, size = legal(statuses, budget, days)
    forced = size == 0 or size == len(inactive)
    maximum_difference = 0.
    if forced:
        if (decision['selected'] != (list(inactive) if size else [])
                or decision['planned_value'] is not None or decision['root_action_values'] != []):
            errors['forced_decision'] += 1
    else:
        independent = query(statuses, budget, days, depth)
        reported = decision['root_action_values']
        if [row['selected'] for row in reported] != [list(selected) for selected, _ in independent]:
            errors['root_action_roster'] += 1
        else:
            for row, (_, expected) in zip(reported, independent):
                fees['root_Q_comparisons'] += 1
                actual = row['value']
                if not isinstance(actual, (int, float)) or not math.isfinite(actual):
                    errors['nonfinite_root_Q'] += 1
                    continue
                difference = abs(actual - expected)
                maximum_difference = max(maximum_difference, difference)
                if difference > TOLERANCE:
                    errors['root_Q_value'] += 1
            if not errors['nonfinite_root_Q']:
                winner = max(reported, key=lambda row: row['value'])
                if decision['selected'] != winner['selected']:
                    errors['reported_strict_max_lex_choice'] += 1
                if decision['planned_value'] != winner['value']:
                    errors['reported_planned_value'] += 1
    expected_work = {'planner_calls': 1, **counts, 'forced_choice': int(forced)}
    if decision['decision_work'] != expected_work:
        errors['decision_work'] += 1
    fees.update({'independent_' + key: value for key, value in counts.items()})
    return dict(passed=not any(errors.values()), errors={key: value for key, value in errors.items() if value},
                maximum_Q_difference=maximum_difference, expected_decision_work=expected_work,
                verification_work=dict(fees))
