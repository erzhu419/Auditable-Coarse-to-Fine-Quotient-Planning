"""Root-conditioned consequence models and committed policy modules for V151."""
from collections import Counter
from copy import deepcopy
import random
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_experience_v115 import _spawn
from .controlled_predictive_shared_local_advantage_v147 import (
    SharedLocalAdvantage, FEATURE_DEFINITION as LOCAL_FEATURE_DEFINITION)

SCHEMA = 'acfqp.root_consequences.v151'
COMPONENTS = ('score_over_2048_difference', 'failure_difference', 'success_difference')
QUERIES = dict(risk1=dict(reward_weight=1., failure_penalty=1., goal_bonus=1.),
               risk8=dict(reward_weight=1., failure_penalty=8., goal_bonus=8.))
FEATURE_DEFINITION = dict(LOCAL_FEATURE_DEFINITION, input='root_board', bias_address=-1,
                          bias_occurrences=1, total_occurrences=41)


def utility(components, query):
    q = QUERIES[query]
    return (q['reward_weight']*components[0]-q['failure_penalty']*components[1]
            +q['goal_bonus']*components[2])


def counter_delta(after, before):
    return {key: value-before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


class RootConsequences(SharedLocalAdvantage):
    """Predict a module's total component difference from its current root."""
    def __init__(self, radix=11):
        super().__init__(radix)
        self.setup_counts['bias_integer_cells'] = 1

    def _features(self, board):
        features = super()._features(board)
        features[-1] = 1
        self.counts.update(feature_occurrences=1, bias_feature_occurrences=1)
        return features

    def _root_predict(self, features):
        prediction = [0., 0., 0.]
        for address, multiplicity in features.items():
            weight = self._weights.get(address, (0., 0., 0.))
            for k in range(3):
                prediction[k] += multiplicity*weight[k]
        self.counts.update(root_predictions=1, weight_address_lookups=len(features),
                           component_weight_reads=3*len(features))
        return prediction

    def predict(self, board):
        return self._root_predict(self._features(board))

    def update(self, board, target, alpha=.1):
        if self.frozen:
            raise RuntimeError('frozen root consequence weights cannot be updated')
        target = list(map(float, target))
        if len(target) != 3:
            raise ValueError('a module target has three total components')
        before = dict(self.counts)
        features = self._features(board)
        prediction = self._root_predict(features)
        error = [target[k]-prediction[k] for k in range(3)]
        denominator = sum(x*x for x in features.values())
        for address, multiplicity in features.items():
            prior = self._weights.get(address, (0., 0., 0.))
            updated = tuple(prior[k]+float(alpha)*multiplicity*error[k]/denominator for k in range(3))
            if any(updated):
                if address not in self._weights:
                    self.counts['allocated_weight_addresses'] += 1
                self._weights[address] = updated
            elif address in self._weights:
                del self._weights[address]
        self.updates += 1
        self.counts.update(update_calls=1, root_updates=1, weight_address_updates=len(features),
                           component_weight_updates=3*len(features))
        return dict(prediction=prediction, error=error, denominator=denominator,
                    applied=True, work=counter_delta(self.counts, before))

    def to_payload(self):
        payload = super().to_payload()
        payload.update(schema=SCHEMA, components=list(COMPONENTS),
                       feature_definition=deepcopy(FEATURE_DEFINITION))
        return payload

    @classmethod
    def from_payload(cls, payload):
        if payload['schema'] != SCHEMA:
            raise ValueError('unsupported root consequence schema')
        model = cls(payload['radix'])
        model._weights = {int(row[0]): tuple(map(float, row[1:])) for row in payload['weights']}
        model.updates, model.frozen = int(payload['updates']), bool(payload['frozen'])
        model.setup_counts.update(loaded_weight_addresses=len(model._weights),
            loaded_weight_parameters=3*len(model._weights), loaded_numeric_weight_bytes=24*len(model._weights))
        return model


def run_module_branch(root_board, bank, target_query, duration, seed,
                      max_steps=2000, p_four=.1):
    """Run the other policy for duration steps, then the target policy to terminal.

    Each policy always receives its own query. There are no initial spawns;
    the winning swipe still spawns. The returned utility uses target_query.
    """
    if target_query not in QUERIES:
        raise ValueError('unknown target query')
    if duration < 0:
        raise ValueError('module duration must be nonnegative')
    if not 0 < max_steps <= 2000:
        raise ValueError('max_steps must be between 1 and 2000')
    if not 0. <= p_four <= 1.:
        raise ValueError('p_four must be between zero and one')
    started = perf_counter()
    other = 'risk8' if target_query == 'risk1' else 'risk1'
    board = tuple(root_board)
    rng, work = random.Random(seed), Counter()
    if _status(board, work) != 'ACTIVE':
        raise ValueError('the module root must be ACTIVE')
    before = {q: dict(bank[q].counts) for q in QUERIES}
    actions, cells, ranks, scores, policies = [], [], [], [], []
    decision_seconds = 0.
    for step in range(max_steps):
        policy = other if step < duration else target_query
        choice_started = perf_counter()
        choice = bank[policy].choose(board, QUERIES[policy])
        decision_seconds += perf_counter()-choice_started
        action = ground.Swipe2048Action(choice['action'])
        work['module_decisions' if step < duration else 'continuation_decisions'] += 1
        work.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
        after, score, changed = ground.swipe_board_v1(board, action)
        if not changed:
            raise ValueError(f'illegal action {action.value} at step {step}')
        board, cell, rank = _spawn(after, rng, work, p_four)
        work['sampled_transitions'] += 1
        status = _status(board, work)
        if not step:
            first_afterstate, first_exit = list(after), list(board)
        actions.append(action.value); cells.append(cell); ranks.append(rank)
        scores.append(score); policies.append(policy)
        if status != 'ACTIVE':
            break
    if status == 'ACTIVE':
        status = 'CUTOFF'
    components = [sum(scores)/2048., float(status == 'LOST'), float(status == 'WON')]
    by_query = {q: counter_delta(bank[q].counts, before[q]) for q in QUERIES}
    policy_counts = sum((Counter(c) for c in by_query.values()), Counter())
    result = dict(score=sum(scores), steps=len(actions), status=status, components=components,
        utility=None if status == 'CUTOFF' else utility(components, target_query),
        environment_counts=dict(work), policy_counts=dict(policy_counts), policy_counts_by_query=by_query,
        learning_counts={}, module_decisions=min(duration, len(actions)),
        continuation_decisions=max(0, len(actions)-duration),
        decision_seconds=decision_seconds, seconds=perf_counter()-started)
    return dict(seed=seed, root_board=list(root_board), target_query=target_query,
        other_query=other, duration=duration, first_action=actions[0],
        first_afterstate=first_afterstate, first_exit=first_exit, actions=actions,
        policy_keys=policies, spawned_cells=cells, spawned_ranks=ranks,
        scores=scores, final_board=list(board), result=result)


class ModuleGate:
    """Choose at module boundaries; a selected other-policy module is committed."""
    def __init__(self, bank, target_query, duration, model=None, mode='LEARNED'):
        if target_query not in QUERIES or mode not in ('LEARNED', 'H2', 'ALT'):
            raise ValueError('unknown module query or gate mode')
        if duration < 0 or (duration == 0 and mode != 'H2'):
            raise ValueError('only the H2 baseline may use zero duration')
        if mode == 'LEARNED' and (model is None or not model.frozen):
            raise ValueError('the learned module gate requires a frozen consequence model')
        self.bank, self.target_query = bank, target_query
        self.other_query = 'risk8' if target_query == 'risk1' else 'risk1'
        self.duration, self.model, self.mode = int(duration), model, mode
        self.remaining = 0
        self.counts, self.setup_counts = Counter(), Counter()
        self.policy_counts_by_query = {q: Counter() for q in QUERIES}
        self.latest_decision = None

    def choose(self, board, step):
        before = dict(self.counts)
        self.counts['choose_calls'] += 1
        boundary = self.remaining == 0
        predicted, advantage = None, None
        if boundary:
            self.counts['boundary_decisions'] += 1
            if self.mode == 'LEARNED':
                model_before = dict(self.model.counts)
                predicted = self.model.predict(board)
                self.counts.update({f'learner_{k}': v for k, v in counter_delta(self.model.counts, model_before).items()})
                advantage = utility(predicted, self.target_query)
                selected = advantage > 0.
            else:
                selected = self.mode == 'ALT'
            if selected:
                self.remaining = self.duration
                self.counts['module_accepts'] += 1
            else:
                self.counts['baseline_boundary_decisions'] += 1
        remaining_before = self.remaining
        selected = self.remaining > 0
        policy = self.other_query if selected else self.target_query
        if selected:
            self.remaining -= 1
        self.counts['module_policy_decisions' if selected else 'baseline_policy_decisions'] += 1
        if not boundary:
            self.counts['committed_module_decisions'] += 1
        policy_before = dict(self.bank[policy].counts)
        choice = self.bank[policy].choose(board, QUERIES[policy])
        delta = counter_delta(self.bank[policy].counts, policy_before)
        self.policy_counts_by_query[policy].update(delta)
        self.counts.update({f'policy_{policy}_{k}': v for k, v in delta.items()})
        self.latest_decision = dict(step=step, boundary=boundary, target_query=self.target_query,
            other_query=self.other_query, duration=self.duration, policy_key=policy,
            selected_other=selected, remaining_before=remaining_before, remaining_after=self.remaining,
            predicted_components=predicted, estimated_advantage=advantage)
        result = dict(choice)
        result['module_decision'] = deepcopy(self.latest_decision)
        result['module_counts'] = counter_delta(self.counts, before)
        return result
