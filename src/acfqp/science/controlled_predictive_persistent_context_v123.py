"""Persistent Bayesian spawn routing with fixed 64:1 stay-to-alternative odds."""
from collections import Counter, deque
from copy import deepcopy
from math import log

from .controlled_predictive_regime_memory_v115 import (
    BLOCK, WINDOW, WARMUP, SpawnMemory, _predictive)

SCHEMA = 'acfqp.persistent_context.v123'
SWITCH_ODDS = BLOCK
SWITCH_PENALTY = log(SWITCH_ODDS)


class PersistentSpawnMemory(SpawnMemory):
    """V115 LIBRARY with the creation penalty also applied to reactivation.

    A completed block has prior weight 64 for staying, 1 for each inactive
    existing module, and 1 for a new module. Only the selected module receives
    its observations. Predictions still use the committed module for the whole
    block; no phase or true spawn probability is supplied to this learner.
    """

    def __init__(self):
        super().__init__('LIBRARY')

    def observe(self, rank):
        if self.observations_seen < WARMUP:
            return super().observe(rank)
        if rank not in (1, 2):
            raise ValueError('observed spawn rank must be 1 or 2')
        self.observations_seen += 1
        self.counts['observations_received'] += 1
        self.pending_n += 1
        self.pending_fours += int(rank == 2)
        if self.pending_n != BLOCK:
            return None

        previous, before = self.active_module_id, len(self.modules)
        scores = [dict(module_id=module['id'], log_score=_predictive(
            module['alpha'], module['beta'], self.pending_n, self.pending_fours))
            for module in self.modules]
        adjusted = [dict(module_id=row['module_id'], log_score=row['log_score'] -
            (0. if row['module_id'] == previous else SWITCH_PENALTY)) for row in scores]
        best = max(adjusted, key=lambda row: (row['log_score'], -row['module_id']))
        raw_new_score = _predictive(1, 1, self.pending_n, self.pending_fours)
        new_score = raw_new_score - SWITCH_PENALTY
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
        event = self._event(kind, previous, self.pending_n, self.pending_fours,
                            before, scores, new_score)
        event.update(adjusted_existing_log_scores=adjusted,
                     raw_new_log_score=raw_new_score, switch_penalty=SWITCH_PENALTY)
        self.pending_n = self.pending_fours = 0
        return event

    def to_payload(self):
        return dict(super().to_payload(), schema=SCHEMA, switch_odds=SWITCH_ODDS)

    @classmethod
    def from_payload(cls, payload):
        if (payload['schema'] != SCHEMA or payload['switch_odds'] != SWITCH_ODDS
                or payload['method'] != 'LIBRARY' or payload['warmup_observations'] != WARMUP
                or payload['block_size'] != BLOCK or payload['recent_window'] != WINDOW):
            raise ValueError('retained spawn memory has a different frozen learning rule')
        result = cls()
        result.observations_seen = payload['observations_seen']
        result.active_module_id = payload['active_module_id']
        result.modules = deepcopy(payload['modules'])
        result.pending_n, result.pending_fours = payload['pending']['n'], payload['pending']['fours']
        result.recent = deque(payload['recent_ranks'])
        result.counts = Counter(payload['counts'])
        return result
