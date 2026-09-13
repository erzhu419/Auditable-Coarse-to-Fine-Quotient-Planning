"""Independent H2 decision and specified-continuation evaluation on exact rows.

Inputs are frozen nested contracts containing Fraction probabilities/rewards.
This module imports no learned compiler, classifier, production solver, or
ground simulator. Ground acquisition and observation-encoding checks belong
to the caller's separate audit phase.
"""
from collections import Counter
from fractions import Fraction
import math


TOLERANCE = 1e-12
METRICS = ('reward', 'failure', 'success', 'value')


def _with_value(reward, failure, success, query):
    value = math.fsum((query.get('reward_weight', 1.0) * reward,
                      -query.get('failure_penalty', 0.0) * failure,
                      query.get('goal_bonus', 0.0) * success))
    return dict(reward=reward, failure=failure, success=success, value=value)


def _terminal(status, query):
    return _with_value(0.0, float(status == 'LOST'), float(status == 'WON'), query)


def _optima(actions):
    reference = max(sorted(actions), key=lambda action: actions[action]['value'])
    best = actions[reference]['value']
    members = [action for action in sorted(actions) if best - actions[action]['value'] <= TOLERANCE]
    return reference, members


def _h1_metrics(contract, query, work):
    work['h1_contracts_evaluated'] += 1
    actions = {}
    for action, score, mass in contract:
        work['h1_action_rows'] += 1
        work['h1_terminal_terms'] += len(mass)
        actions[action] = _with_value(float(Fraction(score, 2048)),
            math.fsum(float(p) for status, p in mass if status == 'LOST'),
            math.fsum(float(p) for status, p in mass if status == 'WON'), query)
    reference, members = _optima(actions)
    return dict(contract=contract, actions=actions, optimal_actions=members,
                reference_action=reference, action=reference, metrics=actions[reference])


def _row_metrics(row, h1_selected_metrics, query, work):
    rewards, failures, successes = [], [], []
    for child, immediate_reward, probability in row:
        work['root_joint_terms'] += 1
        continuation = (_terminal(child[1], query) if child[0] == 'TERMINAL'
                        else h1_selected_metrics[child[1]])
        p = float(probability)
        rewards.append(p * (float(immediate_reward) + continuation['reward']))
        failures.append(p * continuation['failure'])
        successes.append(p * continuation['success'])
    return _with_value(math.fsum(rewards), math.fsum(failures), math.fsum(successes), query)


def query_metrics(native_nested, query):
    """Compute true action Q and metrics with optimal H1 continuation.

    ``query`` is the JSON query dictionary. Returned ``h1`` records contain
    native contract tuples, a canonical exact-max action and its metrics.
    All actions within 1e-12 of the best value belong to ``optimal_actions``;
    the canonical reference does not determine membership by name equality.
    """
    work, h1 = Counter(), {}
    if native_nested and native_nested[0] == 'TERMINAL':
        return dict(actions={}, optimal_actions=[], reference_action=None,
            reference_metrics=_terminal(native_nested[1], query), h1=[], counts=dict(work))
    for _, row in native_nested:
        for child, _, probability in row:
            if probability and child[0] == 'H1' and child[1] not in h1:
                h1[child[1]] = _h1_metrics(child[1], query, work)
    chosen = {contract: record['metrics'] for contract, record in h1.items()}
    actions = {}
    for action, row in native_nested:
        work['root_action_rows'] += 1
        actions[action] = _row_metrics(row, chosen, query, work)
    reference, members = _optima(actions)
    return dict(actions=actions, optimal_actions=members, reference_action=reference,
        reference_metrics=actions[reference], h1=list(h1.values()), counts=dict(work))


def evaluate_choice(native_ground, query, selected_action, continuation_policy=None):
    """Evaluate the supplied H1 actions; never replace them with oracle actions.

    ``continuation_policy`` is a list of (native H1 contract, selected action).
    Missing or illegal actions make actual execution unverified. The caller
    must first establish correspondence of the learned H1 encoding on ground
    successor observations. This function uses the provided contracts directly.
    """
    oracle = query_metrics(native_ground, query)
    legal = selected_action in oracle['actions']
    reference = oracle['reference_metrics']
    selected_oracle = oracle['actions'].get(selected_action)
    errors, work = Counter(), Counter()
    policy, conflicts = {}, set()
    for contract, action in continuation_policy or ():
        if contract in policy and policy[contract] != action:
            conflicts.add(contract)
        policy[contract] = action
    h1 = {record['contract']: record for record in oracle['h1']}
    actual = None
    details = []
    if not legal:
        errors['illegal_root_action'] += 1
    else:
        selected_metrics = {}
        row = dict(native_ground)[selected_action]
        reached = dict.fromkeys(child[1] for child, _, p in row if p and child[0] == 'H1')
        for contract in reached:
            record = h1[contract]
            action = policy.get(contract)
            legal_child = action in record['actions'] and contract not in conflicts
            optimal = legal_child and action in record['optimal_actions']
            if contract in conflicts:
                errors['conflicting_continuation_actions'] += 1
            elif action is None:
                errors['missing_continuation_action'] += 1
            elif not legal_child:
                errors['illegal_continuation_action'] += 1
            if legal_child:
                selected_metrics[contract] = record['actions'][action]
            details.append(dict(contract=contract, action=action, legal=legal_child, optimal=optimal,
                metrics=record['actions'].get(action) if legal_child else None,
                reference_action=record['reference_action'], reference_metrics=record['metrics']))
        if not errors:
            work['selected_root_rows'] += 1
            actual = _row_metrics(row, selected_metrics, query, work)
    deltas = ({metric: actual[metric] - reference[metric] for metric in METRICS}
              if actual is not None else None)
    root_regret = (max(0.0, reference['value'] - selected_oracle['value'])
                   if selected_oracle is not None else None)
    continuation_regret = (max(0.0, selected_oracle['value'] - actual['value'])
                           if actual is not None else None)
    return dict(selected_action=selected_action, root_action_legal=legal,
        root_action_optimal_membership=legal and selected_action in oracle['optimal_actions'],
        root_decision_regret=root_regret, oracle_actions=oracle['actions'],
        optimal_actions=oracle['optimal_actions'], reference_action=oracle['reference_action'],
        reference_metrics=reference, selected_action_oracle_metrics=selected_oracle,
        execution_verified=actual is not None, actual_metrics=actual,
        total_regret=max(0.0, reference['value'] - actual['value']) if actual is not None else None,
        continuation_regret=continuation_regret,
        continuation_optimal=(all(record['optimal'] for record in details) if actual is not None else None),
        continuation_details=details, errors=dict(errors), deltas_to_reference=deltas,
        failure_delta=deltas['failure'] if deltas is not None else None,
        success_delta=deltas['success'] if deltas is not None else None,
        counts=dict(oracle=oracle['counts'], specified_execution=dict(work)),
        reference_scope='Deltas use the saved canonical ground-optimal root and H1 actions. '
            'Different optimal tied policies can have different failure or success probabilities; '
            'nonzero deltas alone do not establish nonoptimality.',
        execution_scope='Actual metrics use only the supplied legal H1 continuation actions. '
            'Missing actions are not completed by the oracle. Observation-to-contract correspondence '
            'must be independently verified by the caller before attributing these metrics to execution.')
