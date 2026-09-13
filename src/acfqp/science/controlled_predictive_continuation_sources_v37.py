"""Evaluator-only H2 continuation decomposition with the retained H1 action mask."""

from collections import Counter
from itertools import combinations
import math
from time import perf_counter

from .controlled_predictive_local_v21 import evaluate_local_snapshot, TOLERANCE
from .controlled_predictive_partial_v12 import _terminal, unknown_action_bounds
from .controlled_predictive_signed_errors_v25 import diagnose_target


MODES = ('RAW', 'REMOVE_E', 'REMOVE_C')
VALUE_FIELDS = ('q_hat', 'q_star', 'A_transition_error', 'D_continuation_error',
                'E_estimation_error', 'C_coverage_error', 'total_error', 'q_mask')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def margin(left_name, right_name, actions):
    """Keep one fixed signed action pair, including same-action zero records."""
    left, right = actions[left_name], actions[right_name]
    result = {'actions': [left_name, right_name],
        'observed_both': left['observed'] and right['observed'],
        'decomposable': left['decomposable'] and right['decomposable'],
        'batch_counts': [left['batch_count'], right['batch_count']],
        'lower_difference_bound': left['lower'] - right['upper'],
        'upper_difference_bound': left['upper'] - right['lower'],
        'raw_lower_difference': left['lower'] - right['lower']}
    for field in VALUE_FIELDS:
        a, b = left[field], right[field]
        result[field + '_difference'] = a - b if a is not None and b is not None else None
    for mode in MODES[1:]:
        a, b = left['mode_values'][mode], right['mode_values'][mode]
        result[mode + '_difference'] = a - b if a is not None and b is not None else None
    result.update(identity_residual=None, continuation_identity_residual=None)
    if result['decomposable']:
        a, d, e, c = (result[field + '_difference'] for field in VALUE_FIELDS[2:6])
        result['identity_residual'] = result['q_hat_difference'] - result['q_star_difference'] - math.fsum((a, e, c))
        result['continuation_identity_residual'] = d - math.fsum((e, c))
    return result


def _mask_value(state, key, query, truth, work):
    observed = state.profiles[key]
    work['mask_state_values'] += 1
    if observed.status != 'ACTIVE':
        work['mask_terminal_values'] += 1
        value = _terminal(observed.status, query)
        _require(value == truth.values[key], 'retained terminal value differs from truth')
        return value
    _require(key[0] == 1, 'V37 requires H1 active continuations')
    work['mask_active_h1_values'] += 1
    values = []
    for action in observed.legal_actions:
        pair = key, action
        if pair in state.rows:
            # At H1 this exact Q uses the entire true row and terminal values,
            # including terminal outcomes absent from the empirical support.
            values.append(truth.q_values[pair])
            work['mask_observed_exact_action_values'] += 1
        else:
            # This is precisely the original unknown cache.q_lower expression;
            # no oracle value for this unobserved action enters the maximum.
            values.append(unknown_action_bounds(key, observed, action, query)[0])
            work['mask_unobserved_structural_action_values'] += 1
    return max(values)


def evaluate_continuation_sources(state, query_name, target_key, oracle):
    """Compute D=E+C without changing observations, intervals or execution policy."""
    started = perf_counter()
    _require(target_key[0] == 2, 'V37 supports the retained H2 cohort only')
    local = evaluate_local_snapshot(state, query_name, target_key, oracle)
    legacy = diagnose_target(local)
    query = state.queries[query_name]
    truth = oracle.solution(query)
    tick = perf_counter()
    work = Counter()
    mask_values, actions, residuals = {}, {}, []
    for name, old in legacy['actions'].items():
        row = {key: value for key, value in old.items() if key not in ('mode_values', 'removal_algebra_residuals')}
        row.update(E_estimation_error=None, C_coverage_error=None, q_mask=None,
            continuation_identity_residual=None, full_identity_residual=None,
            mode_values={'RAW': old['lower'], 'REMOVE_E': None, 'REMOVE_C': None})
        if old['decomposable']:
            children = local['actions'][name]['children']
            for child in children:
                key = child['key'][0], tuple(child['key'][1])
                if key not in mask_values:
                    mask_values[key] = _mask_value(state, key, query, truth, work)
                _require(mask_values[key] <= child['v_star'] + TOLERANCE, 'mask value exceeds optimal value')
            def masked(child):
                return mask_values[child['key'][0], tuple(child['key'][1])]
            e = math.fsum(child['empirical_probability'] * (child['empirical_lower'] - masked(child)) for child in children)
            c = math.fsum(child['empirical_probability'] * (masked(child) - child['v_star']) for child in children)
            q_mask = math.fsum(child['empirical_probability'] * (query.reward_weight * child['immediate_reward'] + masked(child)) for child in children)
            row.update(E_estimation_error=e, C_coverage_error=c, q_mask=q_mask,
                continuation_identity_residual=old['D_continuation_error'] - math.fsum((e, c)),
                full_identity_residual=old['q_hat'] - old['q_star'] - math.fsum((old['A_transition_error'], e, c)))
            # Keep these prescribed numerical expressions; subtraction of E/C
            # from Qhat can perturb exact ties and change a diagnostic choice.
            row['mode_values'].update(REMOVE_E=q_mask, REMOVE_C=old['q_hat_exact_continuation'] + e)
            row['removal_algebra_residuals'] = {'REMOVE_E': q_mask - (old['q_hat'] - e),
                'REMOVE_C': row['mode_values']['REMOVE_C'] - (old['q_hat'] - c)}
            residuals.extend(abs(value) for value in (row['continuation_identity_residual'], row['full_identity_residual'], *row['removal_algebra_residuals'].values()))
            _require(c <= TOLERANCE, 'coverage term must be nonpositive')
            work['action_decompositions'] += 1
        actions[name] = row
    pairs = [margin(left, right, actions) for left, right in combinations(actions, 2)]
    for pair in pairs:
        if pair['decomposable']:
            residuals.extend(abs(pair[field]) for field in ('identity_residual', 'continuation_identity_residual'))
    maximum = max(residuals, default=0.)
    _require(math.isfinite(maximum) and maximum <= TOLERANCE, 'E/C decomposition identity differs')
    names = sorted(actions)
    reference = min(names, key=lambda action: (-actions[action]['q_star'], action))
    raw_action = legacy['original_selected_action']
    raw_wrong = legacy['modes']['RAW']['wrong']
    modes = {'RAW': legacy['modes']['RAW']}
    all_available = all(action['decomposable'] for action in actions.values())
    for mode in MODES[1:]:
        chosen = min(names, key=lambda action: (-actions[action]['mode_values'][mode], action)) if all_available else None
        wrong = chosen not in legacy['true_optimal_actions'] if all_available else None
        modes[mode] = {'available': all_available, 'selected_action': chosen,
            'selected_value': actions[chosen]['mode_values'][mode] if all_available else None,
            'wrong': wrong, 'regret': local['v_star'] - actions[chosen]['q_star'] if all_available else None,
            'raw_wrong_repaired': bool(raw_wrong and not wrong) if all_available else None,
            'raw_correct_new_error': bool(not raw_wrong and wrong) if all_available else None,
            'choice_changed': chosen != raw_action if all_available else None,
            'selected_action_batch_count': actions[chosen]['batch_count'] if all_available else None}
        if not all_available:
            modes[mode]['reason'] = 'AT_LEAST_ONE_LEGAL_ACTION_IS_NOT_DECOMPOSABLE'
    diagnostic = {'target_key': local['target_key'], 'query_name': query_name, 'actions': actions,
        'pair_margins': pairs, 'modes': modes, 'original_selected_action': raw_action,
        'true_optimal_actions': legacy['true_optimal_actions'], 'exact_reference_action': reference,
        'selected_minus_reference': margin(raw_action, reference, actions),
        'unavailable_actions': legacy['unavailable_actions'], 'mask_counts': dict(work),
        'validation': {'all_passed': True, 'maximum_absolute_checked_residual': maximum,
            'coverage_nonpositive': all(row['C_coverage_error'] is None or row['C_coverage_error'] <= TOLERANCE for row in actions.values())}}
    return {'local_evaluation': local, 'original_diagnostic': legacy, 'diagnostic': diagnostic,
        'accounting': {'local_decomposition_seconds': local['accounting']['whole_evaluation_seconds'],
            'diagnostic_clone_solve_seconds': local['accounting']['snapshot_clone_and_solve_seconds'],
            'legacy_numeric_diagnosis_seconds': legacy['accounting']['numeric_diagnosis_seconds'],
            'continuation_decomposition_seconds': perf_counter() - tick,
            'whole_evaluation_seconds': perf_counter() - started, **dict(work)}}
