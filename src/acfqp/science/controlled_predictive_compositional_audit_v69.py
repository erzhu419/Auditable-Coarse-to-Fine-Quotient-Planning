"""Independent full-closure audit of frozen, generated compositional models."""
from collections import Counter, defaultdict
from itertools import combinations
import math
from time import perf_counter

from .controlled_predictive_learned_audit_v68 import _policy_metrics, _semantic_ids
from .controlled_predictive_quotient_v1 import FiniteModel

TOLERANCE = 1e-12
METRICS = ('reward', 'natural_failure', 'unsupported', 'success', 'failure', 'value')


def audit(build, compiled, closure, queries, solutions, reference, source_support=None):
    """Read-only evaluation; no ground row can update the frozen build or rules."""
    started, work, errors = perf_counter(), Counter(), Counter()
    ground = closure.model
    candidate = FiniteModel({c: d.layer for c, d in compiled.cells.items()},
        {c: d.terminal for c, d in compiled.cells.items()}, compiled.rows, compiled.roots)
    active = [s for s in ground.layers if ground.terminal[s] == 'ACTIVE']
    actions = defaultdict(set)
    for state, action in candidate.rows:
        actions[state].add(action)
    mapping, local_correct, witness = {}, {}, None

    def fail(reason, state, **detail):
        nonlocal witness
        errors[reason] += 1
        local_correct[state] = False
        if witness is None:
            witness = dict(reason=reason, state=state, **detail)

    for state, horizon in ground.layers.items():
        work['ground_state_encoding_checks'] += 1
        local_correct[state] = True
        raw_key = (horizon, tuple(closure.boards[state]))
        build_state = build.encoding.get(raw_key)
        cell = compiled.state_to_cell.get(build_state)
        if cell not in candidate.layers:
            fail('missing_encoded_state', state, horizon=horizon)
            mapping[state] = None
            continue
        mapping[state] = cell
        if (build.model.layers.get(build_state) != horizon or
                candidate.layers[cell] != horizon or
                build.model.terminal.get(build_state) != ground.terminal[state] or
                candidate.terminal[cell] != ground.terminal[state]):
            fail('layer_or_terminal_difference', state,
                 ground=ground.terminal[state], predicted=candidate.terminal[cell])
        if set(reference.actions.get(state, ())) != actions[cell]:
            fail('legal_action_set_difference', state)
    mapped_roots = tuple(mapping.get(s) for s in ground.roots)
    if mapped_roots != candidate.roots:
        errors['root_mapping_difference'] += 1
        if witness is None:
            witness = dict(reason='root_mapping_difference', expected=mapped_roots,
                           predicted=candidate.roots)

    maximum_tv = 0.
    for (state, action), outcomes in ground.rows.items():
        work['joint_distribution_rows'] += 1
        work['ground_joint_outcome_terms'] += len(outcomes)
        cell = mapping.get(state)
        if (cell, action) not in candidate.rows:
            fail('missing_candidate_action_row', state, action=action)
            continue
        if any(mapping.get(o.next_state) is None for o in outcomes if o.probability):
            fail('missing_joint_successor', state, action=action)
            continue
        actual, predicted = defaultdict(list), defaultdict(list)
        for o in outcomes:
            if o.probability:
                actual[mapping[o.next_state], o.reward].append(o.probability)
        row = candidate.rows[cell, action]
        work['candidate_joint_outcome_terms'] += len(row)
        for o in row:
            if o.probability:
                predicted[o.next_state, o.reward].append(o.probability)
        p = {k: math.fsum(v) for k, v in actual.items()}
        q = {k: math.fsum(v) for k, v in predicted.items()}
        tv = .5 * math.fsum(abs(p.get(k, 0.) - q.get(k, 0.)) for k in p.keys() | q.keys())
        maximum_tv = max(maximum_tv, tv)
        if tv > TOLERANCE:
            fail('reward_successor_joint_difference', state, action=action, total_variation=tv)

    recursive_correct = {}
    for state in sorted(ground.layers, key=lambda s: (ground.layers[s], s)):
        recursive_correct[state] = local_correct[state] and all(
            recursive_correct[o.next_state]
            for action in reference.actions.get(state, ())
            for o in ground.rows[state, action] if o.probability)
        work['recursive_correctness_states'] += 1

    query_results, policies = {}, {}
    all_query_optimal = {s: True for s in active}
    for name, query in queries.items():
        solution = solutions[name]
        lifted = {s: solution.policy.get(mapping.get(s)) for s in active}
        policies[name] = lifted
        actual = _policy_metrics(ground, lifted, query, work)
        predicted = _policy_metrics(candidate, solution.policy, query, work)
        max_loss, max_gap, max_residual, max_unsupported = 0., 0., 0., 0.
        missing, action_errors, ties = 0, 0, 0
        horizons = defaultdict(Counter)
        for state in active:
            horizon = str(ground.layers[state])
            horizons[horizon]['states'] += 1
            metric = actual[state]
            max_unsupported = max(max_unsupported, metric['unsupported'])
            loss = reference.queries[name]['values'][state] - metric['value']
            max_loss = max(max_loss, loss)
            optimal = loss <= TOLERANCE and metric['unsupported'] <= TOLERANCE
            all_query_optimal[state] &= optimal
            horizons[horizon]['policy_value_failures'] += int(not optimal)
            qvalues = reference.queries[name]['qvalues'][state]
            action_error = lifted[state] not in qvalues or (
                qvalues[lifted[state]] < reference.queries[name]['values'][state] - TOLERANCE)
            action_errors += int(action_error)
            horizons[horizon]['action_errors'] += int(action_error)
            ties += int(lifted[state] != reference.queries[name]['policy'][state])
            estimate = predicted.get(mapping.get(state))
            planned_value = solution.values.get(mapping.get(state))
            if estimate is None or planned_value is None:
                missing += 1
                continue
            max_gap = max(max_gap, *(abs(metric[k] - estimate[k]) for k in METRICS))
            max_residual = max(max_residual, abs(planned_value - estimate['value']))
            work['policy_state_comparisons'] += 1
        passed = (missing == 0 and action_errors == 0 and max_unsupported <= TOLERANCE and
                  max_loss <= TOLERANCE and max_gap <= TOLERANCE and max_residual <= TOLERANCE)
        query_results[name] = dict(valid=passed, maximum_value_loss=max_loss,
            maximum_metric_prediction_error=max_gap, maximum_plan_value_residual=max_residual,
            unavailable_state_metrics=missing, action_errors=action_errors,
            maximum_unsupported_probability=max_unsupported,
            strict_max_lex_action_mismatches=ties,
            by_horizon={h: dict(c) for h, c in sorted(horizons.items())},
            root_metrics=[dict(root=s, name=closure.root_names[i], selected=lifted.get(s),
                actual=actual[s], predicted=predicted.get(mapping.get(s)),
                ground_optimal=reference.queries[name]['metrics'][s],
                value_loss=reference.queries[name]['values'][s] - actual[s]['value'])
                for i, s in enumerate(ground.roots)])
    required, violations = 0, 0
    for left, right in combinations(queries, 2):
        a, b = reference.queries[left], reference.queries[right]
        for state in active:
            if a['policy'][state] != b['policy'][state] and min(a['margins'][state], b['margins'][state]) > TOLERANCE:
                required += 1
                violations += int(policies[left][state] != a['policy'][state] or
                                  policies[right][state] != b['policy'][state])
    work['strict_query_switch_checks'] = required

    by_horizon, novel = {}, None
    for horizon in sorted({ground.layers[s] for s in active}):
        states = [s for s in active if ground.layers[s] == horizon]
        groups = Counter(mapping[s] for s in states if mapping[s] is not None)
        by_horizon[str(horizon)] = dict(concrete_active_states=len(states),
            candidate_active_cells=sum(d.layer == horizon and d.terminal == 'ACTIVE' for d in compiled.cells.values()),
            reached_candidate_cells=len(groups), many_to_one_groups=sum(n > 1 for n in groups.values()),
            collapsed_concrete_states=sum(n - 1 for n in groups.values()),
            largest_group=max(groups.values(), default=0),
            recursive_correct_states=sum(recursive_correct[s] for s in states),
            all_query_optimal_states=sum(all_query_optimal[s] for s in states))
    if source_support is not None:
        # Only ground standard-2048 probabilities use the source support's exact
        # rational normalization. Candidate probabilities above are never rounded.
        semantic_work = Counter()
        semantic_ids = _semantic_ids(ground, dict(source_support.registry), semantic_work)
        work.update({'source_support_' + k: v for k, v in semantic_work.items()})
        novel = {}
        for horizon in by_horizon:
            states = [s for s in active if ground.layers[s] == int(horizon)]
            unseen = [s for s in states if semantic_ids[s] not in source_support.signatures]
            novel[horizon] = dict(active_states=len(states), source_unsupported_states=len(unseen),
                source_supported_states=len(states) - len(unseen),
                new_recursive_correct_states=sum(recursive_correct[s] for s in unseen),
                new_all_query_optimal_states=sum(all_query_optimal[s] for s in unseen),
                new_recursive_correct_and_all_query_optimal_states=sum(
                    recursive_correct[s] and all_query_optimal[s] for s in unseen))
    controlled = not errors
    planning = all(q['valid'] for q in query_results.values()) and violations == 0
    return dict(engineering_complete=True, valid_evidence=True,
        controlled_model_correct=controlled, planning_correct=planning,
        scientific_correct=controlled and planning, valid=controlled and planning,
        ground_states=len(ground.layers), ground_active_states=len(active),
        errors=dict(errors), worst_counterexample=witness,
        maximum_joint_total_variation=maximum_tv, queries=query_results,
        strict_query_switches=dict(required=required, violations=violations, preserved=violations == 0),
        by_horizon=by_horizon, novel_semantics=novel, counts=dict(work),
        elapsed_seconds=perf_counter() - started,
        scope='All concrete states and joint reward-successor rows are checked against the frozen planning artifact. New semantics are ground-defined and require recursive correctness through all successors. Construction and ground expansion costs are accounted by the runner, not inferred from compressed model size.')
