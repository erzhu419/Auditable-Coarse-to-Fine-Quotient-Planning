"""Replay fixtures catch retroactive scoring and failures to reproduce V122."""
from copy import deepcopy
from math import log

import pytest

from scripts.run_controlled_predictive_persistent_context_v123 import (
    PHASES, replay_stream)
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory

WARMUP = [2]*26+[1]*230


def fixture():
    router = SpawnMemory('LIBRARY')
    for rank in WARMUP:
        router.observe(rank)
    rows, payloads = [], {}
    # Split through a block and keep the pending block across episode boundaries.
    for phase, block in zip(PHASES, ([2]*32+[1]*32, [2]*6+[1]*58)):
        ranks = block*2
        for before, after in ((0, 17), (17, 128)):
            events, ids = [], []
            for index, rank in enumerate(ranks[before:after]):
                ids.append(router.module_id)
                event = router.observe(rank)
                if event is not None:
                    events.append(dict(event, observed_action_index=index))
            rows.append(dict(phase=phase, transitions_before=before, transitions_after=after,
                spawned_ranks=ranks[before:after], bank_ids=ids, routing_events=events,
                final_bank_id=router.module_id))
        payloads[phase] = router.to_payload()
    return rows, payloads


def test_replay_preserves_cross_game_blocks_and_causal_metrics(tmp_path):
    rows, payloads = fixture()
    result = replay_stream(WARMUP, rows, tmp_path/'blocks.jsonl.gz', 128, payloads)
    assert result['baseline_exact'] and result['rows_read'] == 4
    assert result['unique_reused_ranks'] == 256
    assert result['unique_reused_warmup'] == 256
    for name in ('BASELINE', 'PERSISTENT'):
        b = result['phases']['B'][name]
        a = result['phases']['A_RETURN'][name]
        # No retroactive use of the new posterior on the 64 observations triggering it.
        p = 27/258
        expected_loss = -32*log(p)-32*log(1-p)-64*log(.5)
        assert b['log_loss_sum'] == pytest.approx(expected_loss, abs=1e-12)
        assert b['source_action_fraction'] == a['source_action_fraction'] == .5
        assert b['first_expected_activation'] == a['first_expected_activation'] == 64
        assert b['last_wrong_action'] == a['last_wrong_action'] == 64
        assert b['source_probability_change'] == 0
        assert b['switches_after_first_expected'] == a['switches_after_first_expected'] == 0
        counts = result['processing_counts'][name]
        assert counts['observations_received'] == counts['beta_updates'] == 512
        assert counts['routing_blocks'] == 4
        assert counts['predict_calls'] == 0


@pytest.mark.parametrize('corruption,match', [
    ('bank_id', 'causal bank ID'), ('event', 'routing events'),
    ('payload', 'final retained payload'), ('budget', 'observation budget'),
    ('incomplete', 'incomplete retained stream')])
def test_disagreement_or_missing_data_cannot_be_reported_complete(tmp_path, corruption, match):
    rows, payloads = fixture()
    if corruption == 'bank_id':
        rows[0]['bank_ids'][0] = 1
    elif corruption == 'event':
        rows[1]['routing_events'][0]['block_fours'] += 1
    elif corruption == 'payload':
        payloads['B']['modules'][0]['alpha'] += 1
    elif corruption == 'budget':
        rows[0]['transitions_after'] -= 1
    else:
        rows.pop()
    with pytest.raises(ValueError, match=match):
        replay_stream(WARMUP, rows, tmp_path/'blocks.jsonl.gz', 128, payloads)
