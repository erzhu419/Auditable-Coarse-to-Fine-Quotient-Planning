"""Confirm change across two blocks, then match stored spawn contexts."""
from collections import Counter, deque
from copy import deepcopy
from math import log

from .controlled_predictive_regime_memory_v115 import (
    BLOCK, WINDOW, WARMUP, SpawnMemory, _predictive)

SCHEMA = 'acfqp.confirmed_context.v124'
SWITCH_ODDS = BLOCK
SWITCH_PENALTY = log(SWITCH_ODDS)
CONFIRMATION_BLOCKS = 2


class ConfirmedSpawnMemory(SpawnMemory):
    """Quarantine one suspicious block without changing its causal predictions.

    A second independently suspicious block triggers pooled context matching.
    A rejected suspicion commits both blocks to the unchanged active context.
    No phase boundary is an input, and unfinished evidence is never flushed.
    """

    def __init__(self):
        super().__init__('LIBRARY')
        self.quarantine_n = self.quarantine_fours = 0
        self.counts.update(detection_predictive_scores=0, matching_predictive_scores=0,
            quarantines=0, confirmations=0, rejections=0, max_uncommitted_observations=0)

    def _scores(self, n, fours, stage):
        scores = [dict(module_id=m['id'], log_score=_predictive(
            m['alpha'], m['beta'], n, fours)) for m in self.modules]
        raw_new = _predictive(1, 1, n, fours)
        self.counts[f'{stage}_predictive_scores'] += len(scores) + 1
        self.counts['candidate_predictive_scores'] += len(scores) + 1
        return scores, raw_new

    def observe(self, rank):
        if self.observations_seen < WARMUP:
            return super().observe(rank)
        if rank not in (1, 2):
            raise ValueError('observed spawn rank must be 1 or 2')
        self.observations_seen += 1
        self.counts['observations_received'] += 1
        self.pending_n += 1
        self.pending_fours += int(rank == 2)
        self.counts['max_uncommitted_observations'] = max(
            self.counts['max_uncommitted_observations'], self.pending_n + self.quarantine_n)
        if self.pending_n != BLOCK:
            return None

        previous, before = self.active_module_id, len(self.modules)
        fours = self.pending_fours
        scores, raw_new = self._scores(BLOCK, fours, 'detection')
        active_score = next(row['log_score'] for row in scores if row['module_id'] == previous)
        alternative_score = max([raw_new] + [row['log_score'] for row in scores
                                             if row['module_id'] != previous])
        margin = alternative_score - active_score
        suspicious = margin > SWITCH_PENALTY
        self.counts['routing_blocks'] += 1
        confirmed, matching = False, None
        committed_n = committed_fours = 0
        if self.quarantine_n:
            committed_n, committed_fours = self.quarantine_n + BLOCK, self.quarantine_fours + fours
            confirmed = suspicious
            if confirmed:
                self.counts['confirmations'] += 1
                joint_scores, joint_new = self._scores(committed_n, committed_fours, 'matching')
                best = max(joint_scores, key=lambda row: (row['log_score'], -row['module_id']))
                matching = dict(n=committed_n, fours=committed_fours,
                    existing_log_scores=joint_scores, raw_new_log_score=joint_new,
                    new_log_score=joint_new - SWITCH_PENALTY)
                if matching['new_log_score'] > best['log_score']:
                    self.active_module_id = len(self.modules)
                    self.modules.append(dict(id=self.active_module_id, alpha=1, beta=1, visits=0))
                    self.counts['module_creations'] += 1
                    kind = 'created'
                else:
                    self.active_module_id = best['module_id']
                    kind = 'reactivated' if self.active_module_id != previous else 'updated'
                    self.counts['module_reactivations'] += kind == 'reactivated'
            else:
                self.counts['rejections'] += 1
                kind = 'updated'
            self.quarantine_n = self.quarantine_fours = 0
        elif suspicious:
            self.quarantine_n, self.quarantine_fours = BLOCK, fours
            self.counts['quarantines'] += 1
            kind = 'quarantined'
        else:
            committed_n, committed_fours = BLOCK, fours
            kind = 'updated'
        if committed_n:
            winner = self.modules[self.active_module_id]
            self._add(winner, committed_n, committed_fours)
            winner['visits'] += committed_n // BLOCK
        event = self._event(kind, previous, BLOCK, fours, before, scores, raw_new - SWITCH_PENALTY)
        event.update(committed_n=committed_n, committed_fours=committed_fours,
            confirmed=confirmed, suspicious=suspicious, raw_new_log_score=raw_new,
            detection_margin=margin, detection_active_log_score=active_score,
            detection_alternative_log_score=alternative_score, switch_penalty=SWITCH_PENALTY,
            matching=matching, quarantine=dict(n=self.quarantine_n, fours=self.quarantine_fours))
        self.pending_n = self.pending_fours = 0
        return event

    def to_payload(self):
        payload = dict(super().to_payload(), schema=SCHEMA, switch_odds=SWITCH_ODDS,
            confirmation_blocks=CONFIRMATION_BLOCKS,
            quarantine=dict(n=self.quarantine_n, fours=self.quarantine_fours))
        payload['stored_observation_counts']['quarantined'] = self.quarantine_n
        return payload

    @classmethod
    def from_payload(cls, payload):
        if (payload['schema'] != SCHEMA or payload['switch_odds'] != SWITCH_ODDS
                or payload['confirmation_blocks'] != CONFIRMATION_BLOCKS
                or payload['method'] != 'LIBRARY' or payload['warmup_observations'] != WARMUP
                or payload['block_size'] != BLOCK or payload['recent_window'] != WINDOW):
            raise ValueError('retained spawn memory has a different frozen learning rule')
        result = cls()
        result.observations_seen = payload['observations_seen']
        result.active_module_id = payload['active_module_id']
        result.modules = deepcopy(payload['modules'])
        result.pending_n, result.pending_fours = payload['pending']['n'], payload['pending']['fours']
        result.quarantine_n = payload['quarantine']['n']
        result.quarantine_fours = payload['quarantine']['fours']
        result.recent = deque(payload['recent_ranks'])
        result.counts = Counter(payload['counts'])
        return result
