"""Blind online spawn estimates with a persistent library of local Beta modules."""
from collections import Counter, deque
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from math import lgamma, log

METHODS = ('FROZEN', 'POOLED', 'RECENT', 'LIBRARY')
WARMUP = WINDOW = 256
BLOCK = 64


def _log_beta(alpha, beta):
    return lgamma(alpha) + lgamma(beta) - lgamma(alpha + beta)


def _predictive(alpha, beta, n, fours):
    """Ordered Bernoulli block marginal; its common binomial factor cancels."""
    return _log_beta(alpha + fours, beta + n - fours) - _log_beta(alpha, beta)


class SpawnMemory:
    """Observe post-action spawn ranks only; phases and true probabilities are absent.

    LIBRARY predictions retain the currently committed module throughout each
    block. Routing commits only its completed block to one winner; it never
    changes a preceding prediction. Inactive modules keep all their statistics.
    """
    def __init__(self, method):
        if method not in METHODS:
            raise ValueError(f'unknown spawn-memory method {method}')
        self.method = method
        self.observations_seen = 0
        self.active_module_id = 0
        self.modules = [dict(id=0, alpha=1, beta=1, visits=0)]
        self.pending_n = self.pending_fours = 0
        self.recent = deque()
        self.counts = Counter(observations_received=0, beta_updates=0, predict_calls=0,
            routing_blocks=0, candidate_predictive_scores=0, module_creations=0,
            module_reactivations=0)

    @property
    def module_id(self):
        return self.active_module_id

    def _probability(self):
        module = self.modules[self.active_module_id]
        return Fraction(module['alpha'], module['alpha'] + module['beta'])

    def predict(self):
        self.counts['predict_calls'] += 1
        return float(self._probability())

    def to_rule(self, template):
        """Replace only spawn probabilities; the supplied template probability is ignored."""
        probability = self._probability()
        return replace(template, spawn_distribution=((1, 1 - probability), (2, probability)))

    def _add(self, module, n, fours):
        module['alpha'] += fours
        module['beta'] += n - fours
        self.counts['beta_updates'] += n

    def _event(self, kind, previous, n, fours, modules_before, scores=(), new_score=None):
        return dict(obs_index=self.observations_seen, kind=kind, module_id=self.active_module_id,
            previous_module_id=previous, block_n=n, block_fours=fours,
            modules_before=modules_before, modules_after=len(self.modules),
            existing_log_scores=list(scores), new_log_score=new_score)

    def observe(self, rank):
        """Consume one observed rank; return initialization or a LIBRARY block event."""
        if rank not in (1, 2):
            raise ValueError('observed spawn rank must be 1 or 2')
        fours = int(rank == 2)
        self.observations_seen += 1
        self.counts['observations_received'] += 1
        active = self.modules[self.active_module_id]
        if self.observations_seen <= WARMUP:
            self._add(active, 1, fours)
            if self.method == 'RECENT':
                self.recent.append(rank)
            if self.observations_seen == WARMUP:
                active['visits'] = 1
                return self._event('initialized', 0, WARMUP, active['alpha'] - 1, 1)
            return None
        if self.method == 'FROZEN':
            return None
        if self.method == 'POOLED':
            self._add(active, 1, fours)
            return None
        if self.method == 'RECENT':
            removed = self.recent.popleft()
            self.recent.append(rank)
            active['alpha'] -= int(removed == 2)
            active['beta'] -= int(removed == 1)
            self._add(active, 1, fours)
            return None
        self.pending_n += 1
        self.pending_fours += fours
        if self.pending_n != BLOCK:
            return None
        previous, before = self.active_module_id, len(self.modules)
        scores = [dict(module_id=module['id'], log_score=_predictive(module['alpha'], module['beta'],
            self.pending_n, self.pending_fours)) for module in self.modules]
        best = max(scores, key=lambda row: (row['log_score'], -row['module_id']))
        new_score = _predictive(1, 1, self.pending_n, self.pending_fours) - log(BLOCK)
        self.counts['routing_blocks'] += 1
        self.counts['candidate_predictive_scores'] += len(scores) + 1
        if new_score > best['log_score']:
            self.active_module_id = len(self.modules)
            self.modules.append(dict(id=self.active_module_id, alpha=1, beta=1, visits=0))
            self.counts['module_creations'] += 1
            kind = 'created'
        else:
            self.active_module_id = best['module_id']
            kind = 'reactivated' if self.active_module_id != previous else 'updated'
            self.counts['module_reactivations'] += kind == 'reactivated'
        winner = self.modules[self.active_module_id]
        self._add(winner, self.pending_n, self.pending_fours)
        winner['visits'] += 1
        event = self._event(kind, previous, self.pending_n, self.pending_fours, before, scores, new_score)
        self.pending_n = self.pending_fours = 0
        return event

    def to_payload(self):
        return dict(schema='acfqp.regime_memory.v115', method=self.method,
            warmup_observations=WARMUP, block_size=BLOCK, recent_window=WINDOW,
            observations_seen=self.observations_seen, warmup_complete=self.observations_seen >= WARMUP,
            active_module_id=self.active_module_id, modules=deepcopy(self.modules),
            pending=dict(n=self.pending_n, fours=self.pending_fours), recent_ranks=list(self.recent),
            stored_observation_counts=dict(statistics=sum(m['alpha'] + m['beta'] - 2 for m in self.modules),
                pending=self.pending_n, raw=len(self.recent)), counts=dict(self.counts))

    @classmethod
    def from_payload(cls, payload):
        if (payload['schema'] != 'acfqp.regime_memory.v115' or payload['warmup_observations'] != WARMUP
                or payload['block_size'] != BLOCK or payload['recent_window'] != WINDOW):
            raise ValueError('retained spawn memory has a different frozen learning rule')
        result = cls(payload['method'])
        result.observations_seen = payload['observations_seen']
        result.active_module_id = payload['active_module_id']
        result.modules = deepcopy(payload['modules'])
        result.pending_n, result.pending_fours = payload['pending']['n'], payload['pending']['fours']
        result.recent = deque(payload['recent_ranks'])
        result.counts = Counter(payload['counts'])
        return result
