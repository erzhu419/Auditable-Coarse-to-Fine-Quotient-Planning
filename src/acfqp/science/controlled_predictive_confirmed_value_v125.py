"""Confirmed contexts with deferred causal TD targets and a matched shared bank.

The router observes a spawn before the next action is selected. Only after that
selection is its already computed TD target queued. A router commit then applies
the queued targets in order, censoring transitions from another context. Neither
an episode end nor a phase label flushes pending evidence or TD work.
"""
from collections import Counter
from copy import copy
from pathlib import Path

from .controlled_predictive_confirmed_context_v124 import ConfirmedSpawnMemory
from .controlled_predictive_ntuple_context_v122 import (
    ContextValueBank, _delta, _readonly_model)
from .controlled_predictive_ntuple_td_v120 import ALPHA
from .controlled_predictive_regime_memory_v115 import WARMUP

SCHEMA = 'acfqp.confirmed_value.v125'


class ConfirmedValueBank(ContextValueBank):
    """BANK retains context-specific values; DELAY trains one shared value.

    Both methods have identical routing, delay and cross-context censorship.
    ``context_id`` identifies router state; ``active_bank_id`` identifies weights.
    Their distinction matters for DELAY, whose only weight bank is always zero.
    """

    def __init__(self, source_model, initial_ranks, build_dir, method='BANK'):
        if method not in ('BANK', 'DELAY'):
            raise ValueError('V125 method must be BANK or DELAY')
        ranks = tuple(initial_ranks)
        if len(ranks) != WARMUP:
            raise ValueError('V125 context initialization requires exactly 256 source ranks')
        self.method = method
        self.router = ConfirmedSpawnMemory()
        for rank in ranks:
            self.router.observe(rank)
        self.initial_router_payload = self.router.to_payload()
        self.banks = {0: source_model}
        self.origins = {0: dict(kind='source', parent_bank_id=None,
                                updates_at_creation=source_model.updates)}
        self.rule, self.build_dir = source_model.rule, Path(build_dir)
        self.updates = source_model.updates
        self.counts, self.setup_counts = Counter(), Counter()
        self.setup_seconds = self.clone_seconds = 0.
        self.training_enabled = True
        self.pending_transitions = []
        self._awaiting_transition = False
        self._observation_event = None

    @property
    def context_id(self):
        return self.router.module_id

    @property
    def active_bank_id(self):
        return self.context_id if self.method == 'BANK' else 0

    def choose(self, board, query):
        return dict(super().choose(board, query), context_id=self.context_id)

    def observe(self, rank):
        """Route an observed spawn, creating any new bank before queued TD."""
        if self.training_enabled and self._awaiting_transition:
            raise RuntimeError('finish_transition must follow each training observation')
        before = self.router.counts.copy()
        event = self.router.observe(rank)
        self.counts.update({f'router_{key}': value
            for key, value in _delta(self.router.counts, before).items()})
        if event is not None and event['kind'] == 'created' and self.method == 'BANK':
            self._clone(event['previous_module_id'], event['module_id'])
        if self.training_enabled:
            self._awaiting_transition = True
            self._observation_event = event
        return event

    def finish_transition(self, afterstate, origin_context_id, target,
                          target_context_id=None, alpha=ALPHA):
        """Queue one observed transition after its next action has been chosen.

        A numeric target is the already chosen next-action value, or the fixed
        terminal loss value. A goal afterstate or censored cutoff has no target.
        ``target_context_id`` is None only for fixed terminal/no-target rows.
        The returned commit summary is None while routing evidence is unfinished.
        """
        if not self.training_enabled:
            raise RuntimeError('V125 evaluation bank cannot update weights')
        if not self._awaiting_transition:
            raise RuntimeError('observe must precede finish_transition')
        if target is not None and afterstate is None:
            raise ValueError('a TD target requires its observed afterstate')
        if alpha != ALPHA:
            raise ValueError('V125 uses the frozen V120 step size')
        row = dict(obs_index=self.router.observations_seen,
            afterstate=None if afterstate is None else list(afterstate),
            origin_context_id=origin_context_id,
            target=None if target is None else float(target),
            target_context_id=target_context_id)
        self.pending_transitions.append(row)
        self.counts['queued_transitions'] += 1
        self.counts['queued_targets'] += target is not None
        self.counts['queued_untargeted_transitions'] += target is None
        self.counts['max_pending_transitions'] = max(
            self.counts['max_pending_transitions'], len(self.pending_transitions))
        event = self._observation_event
        self._awaiting_transition = False
        self._observation_event = None
        if event is None or not event['committed_n']:
            return None
        if event['committed_n'] != len(self.pending_transitions):
            raise AssertionError('TD batch differs from the committed router observations')
        result = dict(obs_index=self.router.observations_seen,
            committed_n=len(self.pending_transitions), context_id=self.context_id,
            bank_id=self.active_bank_id, applied=0, censored=0, untargeted=0)
        model = self.banks[self.active_bank_id]
        before = model.counts.copy()
        for pending in self.pending_transitions:
            if pending['target'] is None:
                result['untargeted'] += 1
            elif (pending['origin_context_id'] != self.context_id
                  or pending['target_context_id'] not in (None, self.context_id)):
                result['censored'] += 1
            else:
                model.update(pending['afterstate'], pending['target'], ALPHA)
                self.updates += 1
                result['applied'] += 1
        self.counts.update(_delta(model.counts, before))
        self.counts['committed_batches'] += 1
        self.counts['committed_transitions'] += result['committed_n']
        self.counts['cross_context_target_skips'] += result['censored']
        self.counts['committed_untargeted_transitions'] += result['untargeted']
        self.pending_transitions = []
        return result

    def update_pending(self, *args, **kwargs):
        raise RuntimeError('V125 TD must pass through finish_transition')

    def evaluation_copy(self):
        """Private causal router and readonly weights, without training queue."""
        if self._awaiting_transition:
            raise RuntimeError('evaluation cannot interrupt an unfinished transition')
        result = copy(self)
        result.router = ConfirmedSpawnMemory.from_payload(self.router.to_payload())
        result.banks = {key: _readonly_model(model) for key, model in self.banks.items()}
        result.origins = {key: dict(value) for key, value in self.origins.items()}
        result.counts = Counter(evaluation_weight_views=len(result.banks),
            evaluation_shared_parameters=sum(model.weights.size for model in result.banks.values()))
        result.setup_counts = Counter()
        result.setup_seconds = result.clone_seconds = 0.
        result.training_enabled = False
        result.pending_transitions = []
        result._awaiting_transition = False
        result._observation_event = None
        return result

    def to_payload(self):
        if self._awaiting_transition:
            raise RuntimeError('checkpoint cannot interrupt an unfinished transition')
        return dict(super().to_payload(), schema=SCHEMA, method=self.method,
            context_id=self.context_id,
            pending_transitions=[dict(row, afterstate=None if row['afterstate'] is None
                else list(row['afterstate'])) for row in self.pending_transitions])
