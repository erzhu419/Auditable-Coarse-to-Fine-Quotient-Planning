"""Synthetic evidence for causality, persistence, responsiveness and accounting."""
from copy import deepcopy
import json

import pytest

from acfqp.science.controlled_predictive_persistent_context_v123 import (
    PersistentSpawnMemory, SWITCH_PENALTY)
from acfqp.science import controlled_predictive_persistent_context_v123 as persistent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory

INITIAL = [2]*26 + [1]*230
B_BLOCK = [2]*32 + [1]*32
A_BLOCK = [2]*6 + [1]*58


def feed(model, ranks):
    events = []
    for rank in ranks:
        event = model.observe(rank)
        if event is not None:
            events.append(event)
    return events


def initialized():
    model = PersistentSpawnMemory()
    feed(model, INITIAL)
    return model


def test_warmup_and_partial_block_predictions_are_causal():
    model, reference = PersistentSpawnMemory(), SpawnMemory('LIBRARY')
    assert feed(model, INITIAL) == feed(reference, INITIAL)
    assert model.modules == reference.modules
    before = deepcopy(model.modules)
    predictions = []
    for rank in B_BLOCK[:-1]:
        predictions.append(model.predict())
        assert model.observe(rank) is None
    assert predictions == [27/258]*63
    assert model.module_id == 0 and model.modules == before
    event = model.observe(B_BLOCK[-1])
    assert event['obs_index'] == 320 and event['kind'] == 'created'
    assert model.module_id == 1 and model.predict() == .5
    assert model.counts['predict_calls'] == 64


def test_isolated_adverse_block_cannot_trigger_free_reactivation():
    model, reference = initialized(), SpawnMemory('LIBRARY')
    feed(reference, INITIAL)
    feed(model, B_BLOCK*16)
    feed(reference, B_BLOCK*16)
    before = deepcopy(model.modules[0])
    adverse = [2]*18 + [1]*46
    baseline_event = feed(reference, adverse)[0]
    event = feed(model, adverse)[0]
    assert baseline_event['kind'] == 'reactivated' and reference.module_id == 0
    assert event['kind'] == 'updated' and model.module_id == 1
    assert model.modules[0] == before
    raw = {row['module_id']: row['log_score'] for row in event['existing_log_scores']}
    adjusted = {row['module_id']: row['log_score']
                for row in event['adjusted_existing_log_scores']}
    assert 0 < raw[0]-raw[1] < SWITCH_PENALTY
    assert adjusted[1] == raw[1]
    assert adjusted[0] == raw[0]-SWITCH_PENALTY
    assert event['new_log_score'] == event['raw_new_log_score']-SWITCH_PENALTY
    assert event['switch_penalty'] == SWITCH_PENALTY


def test_real_change_and_return_reuse_source_without_drifting_it():
    model = initialized()
    original = deepcopy(model.modules[0])
    events = feed(model, B_BLOCK*16)
    assert events[0]['kind'] == 'created' and model.module_id == 1
    assert model.modules[0] == original
    event = feed(model, A_BLOCK)[0]
    assert event['kind'] == 'reactivated' and model.module_id == 0
    assert len(model.modules) == 2
    assert model.modules[0]['alpha'] == original['alpha']+6
    assert model.modules[0]['beta'] == original['beta']+58
    assert model.counts['module_creations'] == 1
    assert model.counts['module_reactivations'] == 1


def test_statistics_conserve_every_rank_and_work_counts():
    model = PersistentSpawnMemory()
    ranks = INITIAL + B_BLOCK*3 + A_BLOCK + B_BLOCK[:17]
    events = feed(model, ranks)
    payload = model.to_payload()
    assert payload['stored_observation_counts']['statistics'] + model.pending_n == len(ranks)
    assert sum(module['alpha']-1 for module in model.modules) + model.pending_fours == ranks.count(2)
    assert model.counts['beta_updates'] == len(ranks)-17
    assert model.counts['observations_received'] == len(ranks)
    assert model.counts['routing_blocks'] == 4
    assert model.counts['candidate_predictive_scores'] == sum(
        event['modules_before']+1 for event in events if event['kind'] != 'initialized')
    assert model.counts['predict_calls'] == 0


def test_existing_id_ties_and_new_candidate_ties_keep_original_rule(monkeypatch):
    model = initialized()
    feed(model, B_BLOCK*16 + [2]*64)
    assert model.module_id == 2
    current_alpha = model.modules[2]['alpha']
    monkeypatch.setattr(persistent, '_predictive',
                        lambda alpha, beta, n, fours: -100. if alpha == current_alpha else -10.)
    event = feed(model, A_BLOCK)[0]
    assert event['kind'] == 'reactivated' and event['module_id'] == 0
    assert event['adjusted_existing_log_scores'][0]['log_score'] == event['new_log_score']
    assert len(model.modules) == 3


@pytest.mark.parametrize('prefix', [INITIAL[:91], INITIAL+B_BLOCK*3+A_BLOCK[:13]])
def test_serialization_resumes_warmup_or_pending_block_exactly(prefix):
    model = PersistentSpawnMemory()
    feed(model, prefix)
    restored = PersistentSpawnMemory.from_payload(json.loads(json.dumps(model.to_payload())))
    assert restored.to_payload() == model.to_payload()
    suffix = B_BLOCK*7 + A_BLOCK*4 + B_BLOCK[:11]
    for rank in suffix:
        assert model.predict() == restored.predict()
        assert model.observe(rank) == restored.observe(rank)
    assert restored.to_payload() == model.to_payload()
