"""Causal spawn-context routing of persistent, otherwise unchanged V120 values.

The caller supplies observed spawn ranks, never phase labels or probabilities.
Completed V115 blocks route subsequent choices. A pending afterstate whose
action bank differs from the current bank is skipped, so it cannot bootstrap
from another context's value. Inactive banks keep their exact parameters.
"""
from collections import Counter
from copy import copy
from pathlib import Path
from time import perf_counter

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ALPHA, NtupleValue
from .controlled_predictive_regime_memory_v115 import SpawnMemory, WARMUP

SCHEMA = 'acfqp.ntuple_context.v122'


def _delta(after, before):
    return {key: value-before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def _readonly_model(model):
    """Independent bookkeeping over immutable evaluation weights."""
    result = copy(model)
    result.weights = model.weights.view()
    result.weights.flags.writeable = False
    result.counts, result.setup_counts = Counter(), Counter()
    result.setup_seconds = 0.
    return result


class ContextValueBank:
    """One learned value bank per V115 LIBRARY context, without phase input.

    The supplied source model remains bank zero. The caller accounts for its
    initial load; this object's setup counters account only for new bank clones.
    ``updates`` counts inherited source updates once plus actual new TD calls.
    ``counts`` starts at zero, excluding historical source-model work and the
    separately reported 256-rank source-context initialization.
    """

    def __init__(self, source_model, initial_ranks, build_dir):
        ranks = tuple(initial_ranks)
        if len(ranks) != WARMUP:
            raise ValueError('V122 context initialization requires exactly 256 source ranks')
        self.router = SpawnMemory('LIBRARY')
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

    @property
    def active_bank_id(self):
        return self.router.module_id

    def _clone(self, source_id, target_id):
        source = self.banks[source_id]
        started = perf_counter()
        if self.training_enabled:
            cloned = NtupleValue(self.rule, self.build_dir)
            np.copyto(cloned.weights, source.weights)
            cloned.updates = source.updates
            self.setup_counts.update(cloned.setup_counts)
            self.setup_seconds += cloned.setup_seconds
            self.counts['bank_weight_copies'] += 1
            self.counts['bank_copied_parameters'] += source.weights.size
            self.counts['bank_copied_bytes'] += source.weights.nbytes
        else:
            cloned = _readonly_model(source)
            self.counts['evaluation_weight_views'] += 1
            self.counts['evaluation_shared_parameters'] += source.weights.size
        self.clone_seconds += perf_counter()-started
        self.banks[target_id] = cloned
        self.origins[target_id] = dict(kind='clone', parent_bank_id=source_id,
            updates_at_creation=cloned.updates)
        self.counts['bank_creations'] += 1

    def observe(self, rank):
        before = self.router.counts.copy()
        event = self.router.observe(rank)
        self.counts.update({f'router_{key}': value
            for key, value in _delta(self.router.counts, before).items()})
        if event is not None and event['kind'] == 'created':
            self._clone(event['previous_module_id'], event['module_id'])
        return event

    def choose(self, board, query):
        bank_id = self.active_bank_id
        model = self.banks[bank_id]
        before = model.counts.copy()
        chosen = model.choose(board, query)
        self.counts.update(_delta(model.counts, before))
        return dict(chosen, bank_id=bank_id)

    def update_pending(self, afterstate, bank_id, target, alpha=ALPHA):
        """Return whether TD was applied; a routed-bank change censors one target."""
        if not self.training_enabled:
            raise RuntimeError('V122 evaluation bank cannot update weights')
        if bank_id != self.active_bank_id:
            self.counts['cross_context_update_skips'] += 1
            return False
        model = self.banks[bank_id]
        before = model.counts.copy()
        model.update(afterstate, target, alpha)
        self.counts.update(_delta(model.counts, before))
        self.updates += 1
        return True

    def evaluation_copy(self):
        """A fresh causal router and readonly value views for one outer episode.

        Calling choose/observe changes only evaluation-local counters/router.
        New evaluation contexts share the active immutable values because
        neither bank can be trained during evaluation; no dense copy is needed.
        """
        result = copy(self)
        result.router = SpawnMemory.from_payload(self.router.to_payload())
        result.banks = {key: _readonly_model(model) for key, model in self.banks.items()}
        result.origins = {key: dict(value) for key, value in self.origins.items()}
        result.counts = Counter(evaluation_weight_views=len(result.banks),
            evaluation_shared_parameters=sum(model.weights.size for model in result.banks.values()))
        result.setup_counts = Counter()
        result.setup_seconds = result.clone_seconds = 0.
        result.training_enabled = False
        return result

    def to_payload(self):
        return dict(schema=SCHEMA, active_bank_id=self.active_bank_id,
            updates=self.updates, training_enabled=self.training_enabled,
            router=self.router.to_payload(), initial_router=self.initial_router_payload,
            banks=[dict(bank_id=key, **self.origins[key], updates=model.updates,
                parameters=model.weights.size, dense_bytes=model.weights.nbytes)
                for key, model in sorted(self.banks.items())],
            counts=dict(self.counts), setup_counts=dict(self.setup_counts),
            setup_seconds=self.setup_seconds, clone_seconds=self.clone_seconds)

    def save(self, directory):
        """Save all existing banks and return their paths plus router state."""
        directory = Path(directory)
        metadata = []
        for bank_id, model in sorted(self.banks.items()):
            before = model.counts.copy()
            saved = model.save(directory / f'bank_{bank_id}.npz')
            self.counts.update(_delta(model.counts, before))
            metadata.append(dict(bank_id=bank_id, **saved))
        return dict(self.to_payload(), model_files=metadata)
