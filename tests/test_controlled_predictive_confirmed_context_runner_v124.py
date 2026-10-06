"""Paired sufficient-statistic replay, causal loss, and quarantine boundaries."""
from copy import deepcopy
from math import log

import pytest

from scripts.run_controlled_predictive_confirmed_context_v124 import replay_blocks
from scripts.run_controlled_predictive_persistent_context_v123 import probability
from acfqp.science.controlled_predictive_persistent_context_v123 import PersistentSpawnMemory

WARMUP = [2]*26+[1]*230


def fixture(b=(32,)*4, a=(6,)*4, reverse=False):
    router = PersistentSpawnMemory()
    for rank in WARMUP:
        router.observe(rank)
    rows, payloads = [], {}
    for phase, blocks in (('B', b), ('A_RETURN', a)):
        for index, k in enumerate(blocks):
            pre = dict(pre_module=router.module_id, pre_probability=probability(router))
            ranks = [2]*k+[1]*(64-k)
            if reverse:
                ranks.reverse()
            for rank in ranks:
                event = router.observe(rank)
            original = dict(pre, n=64, fours=k, event=event, source_probability=probability(router, 0))
            rows.append(dict(phase=phase, phase_end=(index+1)*64, methods={'PERSISTENT': original}))
        payloads[phase] = router.to_payload()
    return rows, payloads


def test_confirmed_loss_and_identity_cannot_use_later_observations(tmp_path):
    rows, payloads = fixture()
    out = replay_blocks(WARMUP, rows, tmp_path/'blocks.gz', payloads, budget=256)
    assert out['control_exact'] and out['observation_conservation']
    b = out['phases']['B']['CONFIRMED']
    a = out['phases']['A_RETURN']['CONFIRMED']
    p = 27/258
    assert b['log_loss_sum'] == pytest.approx(-64*log(p)-64*log(1-p)-128*log(.5))
    assert b['first_expected_activation'] == a['first_expected_activation'] == 128
    assert b['last_wrong_action'] == a['last_wrong_action'] == 128
    assert b['source_action_fraction'] == a['source_action_fraction'] == .5
    assert b['source_probability_change'] == 0
    assert out['unique_reused_ranks'] == 512
    assert out['processing_counts']['CONFIRMED']['beta_updates'] == 768
    assert out['processing_counts']['CONFIRMED']['confirmations'] == 2


def test_phase_boundary_does_not_flush_quarantined_observations(tmp_path):
    rows, payloads = fixture(b=(32,), a=(32,))
    out = replay_blocks(WARMUP, rows, tmp_path/'blocks.gz', payloads, budget=64)
    b = out['phases']['B']['CONFIRMED']['final_router']
    a = out['phases']['A_RETURN']['CONFIRMED']['final_router']
    assert b['quarantine'] == dict(n=64, fours=32)
    assert b['counts']['beta_updates'] == 256
    assert b['active_module_id'] == 0
    assert a['quarantine'] == dict(n=0, fours=0)
    assert a['counts']['beta_updates'] == 384
    assert a['modules'][1]['alpha'] == a['modules'][1]['beta'] == 65


def test_within_block_order_is_exactly_sufficient(tmp_path):
    rows, payloads = fixture()
    reversed_rows, reversed_payloads = fixture(reverse=True)
    assert rows == reversed_rows and payloads == reversed_payloads
    original = replay_blocks(WARMUP, rows, tmp_path/'a.gz', payloads, budget=256)
    reversed_result = replay_blocks(WARMUP, reversed_rows, tmp_path/'b.gz', reversed_payloads, budget=256)
    assert original == reversed_result


@pytest.mark.parametrize('corruption,match', [
    ('pre', 'pre-block state'), ('event', 'retained event'),
    ('final', 'final payload'), ('missing', 'incomplete retained replay')])
def test_invalid_control_is_not_reported_complete(tmp_path, corruption, match):
    rows, payloads = fixture()
    if corruption == 'pre':
        rows[0]['methods']['PERSISTENT']['pre_module'] = 1
    elif corruption == 'event':
        rows[0]['methods']['PERSISTENT']['event']['kind'] = 'updated'
    elif corruption == 'final':
        payloads['B']['modules'][0]['alpha'] += 1
    else:
        rows.pop()
    with pytest.raises(ValueError, match=match):
        replay_blocks(WARMUP, rows, tmp_path/'blocks.gz', payloads, budget=256)
