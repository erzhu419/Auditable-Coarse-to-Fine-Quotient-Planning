"""V124 checks causal confirmation, pooled matching and exact data accounting."""
from copy import deepcopy
import json

import pytest

from acfqp.science.controlled_predictive_confirmed_context_v124 import (
    ConfirmedSpawnMemory, SWITCH_PENALTY)
from acfqp.science import controlled_predictive_confirmed_context_v124 as confirmed
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


def initialized(ranks=INITIAL):
    model = ConfirmedSpawnMemory()
    feed(model, ranks)
    return model


def test_warmup_and_quarantined_predictions_are_causal():
    model, reference = ConfirmedSpawnMemory(), SpawnMemory('LIBRARY')
    assert feed(model, INITIAL) == feed(reference, INITIAL)
    assert model.modules == reference.modules
    before = deepcopy(model.modules)
    for i, rank in enumerate(B_BLOCK + B_BLOCK[:-1]):
        assert model.predict() == 27/258
        event = model.observe(rank)
        if i == 63:
            assert event['kind'] == 'quarantined' and event['committed_n'] == 0
        else:
            assert event is None
        assert model.module_id == 0 and model.modules == before
    event = model.observe(B_BLOCK[-1])
    assert event['kind'] == 'created' and event['confirmed']
    assert event['block_n'] == 64 and event['block_fours'] == 32
    assert event['committed_n'] == 128 and event['committed_fours'] == 64
    assert model.module_id == 1 and model.predict() == .5
    assert model.modules[0] == before[0]


def test_isolated_outlier_commits_both_blocks_to_original_module():
    model = initialized()
    original = deepcopy(model.modules[0])
    first = feed(model, B_BLOCK)[0]
    second = feed(model, A_BLOCK)[0]
    assert first['kind'] == 'quarantined'
    assert second['kind'] == 'updated' and not second['confirmed']
    assert second['matching'] is None and second['committed_n'] == 128
    assert model.module_id == 0 and len(model.modules) == 1
    assert model.modules[0]['alpha'] == original['alpha']+38
    assert model.modules[0]['beta'] == original['beta']+90
    assert model.counts['rejections'] == 1 and model.counts['matching_predictive_scores'] == 0


def test_true_change_and_return_preserve_then_reuse_source():
    model = initialized()
    source = deepcopy(model.modules[0])
    events = feed(model, B_BLOCK*16)
    assert events[0]['kind'] == 'quarantined' and events[1]['kind'] == 'created'
    assert model.modules[0] == source and len(model.modules) == 2
    b_module = deepcopy(model.modules[1])
    events = feed(model, A_BLOCK*2)
    assert events[0]['kind'] == 'quarantined' and events[1]['kind'] == 'reactivated'
    assert model.module_id == 0 and len(model.modules) == 2
    assert model.modules[1] == b_module
    assert model.modules[0]['alpha'] == source['alpha']+12
    assert model.modules[0]['beta'] == source['beta']+116
    assert model.counts['module_creations'] == model.counts['module_reactivations'] == 1


def test_opposite_suspicious_blocks_jointly_select_active_module():
    model = initialized([2]*128+[1]*128)
    events = feed(model, [1]*64+[2]*64)
    assert events[0]['suspicious'] and events[1]['suspicious']
    assert events[1]['confirmed'] and events[1]['kind'] == 'updated'
    assert events[1]['matching']['fours'] == 64 and model.module_id == 0
    assert len(model.modules) == 1 and model.predict() == .5


def test_pooled_matching_ties_prefer_existing_then_smallest_id(monkeypatch):
    model = initialized()
    feed(model, B_BLOCK*16)
    active_alpha = model.modules[model.module_id]['alpha']

    def tied_scores(alpha, beta, n, fours):
        if n == 64 and alpha == active_alpha:
            return -20.
        if n == 128 and alpha == beta == 1:
            return -10.+SWITCH_PENALTY
        return -10.

    monkeypatch.setattr(confirmed, '_predictive', tied_scores)
    event = feed(model, A_BLOCK*2)[-1]
    assert event['confirmed'] and event['kind'] == 'reactivated'
    assert model.module_id == 0 and len(model.modules) == 2


def test_within_block_order_does_not_change_predictions_or_commits():
    left, right = initialized(), initialized()
    for block in [B_BLOCK]*4+[A_BLOCK]*4+[B_BLOCK]:
        for rank_left, rank_right in zip(block, reversed(block)):
            assert left.predict() == right.predict()
            event_left, event_right = left.observe(rank_left), right.observe(rank_right)
            assert event_left == event_right
        assert left.to_payload() == right.to_payload()


def test_observation_and_work_accounting_include_quarantined_samples():
    model = ConfirmedSpawnMemory()
    ranks = INITIAL+B_BLOCK*4+A_BLOCK*2+B_BLOCK+B_BLOCK[:17]
    events = []
    for i, rank in enumerate(ranks):
        event = model.observe(rank)
        if event is not None:
            events.append(event)
        stats = sum(m['alpha']+m['beta']-2 for m in model.modules)
        fours = sum(m['alpha']-1 for m in model.modules)
        assert stats+model.pending_n+model.quarantine_n == i+1
        assert fours+model.pending_fours+model.quarantine_fours == ranks[:i+1].count(2)
        assert model.counts['beta_updates'] == stats
    payload = model.to_payload()
    counts = payload['stored_observation_counts']
    assert sum(counts.values()) == len(ranks)
    assert counts['quarantined'] == 64 and counts['pending'] == 17
    assert model.counts['max_uncommitted_observations'] == 128
    blocks = [event for event in events if event['kind'] != 'initialized']
    detection = sum(event['modules_before']+1 for event in blocks)
    matching = sum(event['modules_before']+1 for event in blocks if event['confirmed'])
    assert model.counts['routing_blocks'] == len(blocks)
    assert model.counts['detection_predictive_scores'] == detection
    assert model.counts['matching_predictive_scores'] == matching
    assert model.counts['candidate_predictive_scores'] == detection+matching


@pytest.mark.parametrize('prefix', [INITIAL[:91], INITIAL+B_BLOCK, INITIAL+B_BLOCK+B_BLOCK[:13]])
def test_serialization_preserves_warmup_quarantine_and_partial_block(prefix):
    model = ConfirmedSpawnMemory()
    feed(model, prefix)
    restored = ConfirmedSpawnMemory.from_payload(json.loads(json.dumps(model.to_payload())))
    assert restored.to_payload() == model.to_payload()
    for rank in B_BLOCK*7+A_BLOCK*4+B_BLOCK[:11]:
        assert model.predict() == restored.predict()
        assert model.observe(rank) == restored.observe(rank)
    assert model.to_payload() == restored.to_payload()
