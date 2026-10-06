"""Saved FIRST/v1/v2 probability checks; no natural suffix or evaluation pilots."""
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

from acfqp.science.natural_model_revision_v281 import load_leaf
from acfqp.science.query_supervision_run_v319 import _restore_first
from acfqp.science.reward_targets_run_v321 import _apply_delta
from acfqp.science.win_terminal_prediction_v325 import predict_win

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from verify_closed_loop_v313 import HeadVersions, PATTERNS, read_source_weights


def literal_probability(board, terminal, radix):
    addresses = []
    for index, pattern in enumerate(PATTERNS):
        address = 0
        for cell in pattern:
            address = radix*address+int(board[cell])
        addresses.append((index//8)*radix**6+address)
    logit = sum(float(terminal[address]) for address in addresses)
    if logit >= 0.:
        probability = 1./(1.+math.exp(-logit))
    else:
        value = math.exp(logit)
        probability = value/(1.+value)
    return logit, probability


@pytest.mark.parametrize('task', ['A', 'B'])
@pytest.mark.parametrize('arm', ['FACTUAL_WIN', 'QUERY_WIN'])
def test_actual_saved_first_and_both_own_rounds_match_literal_probability(task, arm):
    # Wrong sparse-chain restoration or a different sigmoid would corrupt the terminal-error diagnosis.
    saved = json.loads((ROOT/'reports/win_learning_v324/summary.json').read_text())
    source, life = saved['source_provenance']['parents'][0], saved['by_lifecycle'][0]
    initial = life['initial'][task]
    runtime = ROOT/'reports/win_terminal_v325/test_logs/prediction_fixture'/task/arm
    runtime.mkdir(parents=True, exist_ok=True)
    template, _ = load_leaf(source, runtime)
    leaf, _ = _restore_first(template, initial['head_version'], runtime)
    reference = HeadVersions(read_source_weights(source['checkpoint']), source['checkpoint'],
        dict(lifecycle=0, parent=0, context_id=initial['context_id'], arm=arm), 'LOCAL_RISK')
    with np.load(life['rounds']['1'][task]['arms'][arm]['supervision']['group_artifact']['file'],
            allow_pickle=False) as groups:
        roots = groups['roots'][np.linspace(0, len(groups['roots'])-1, 8, dtype=np.int64)]
    for number in (0, 1, 2):
        version = (initial['head_version'] if number == 0
            else life['rounds'][str(number)][task]['arms'][arm]['head_version'])
        if number:
            _apply_delta(leaf, version)
        reference.apply(version)
        prior_updates = leaf.updates
        reward = leaf.reward_weights.copy(); risk = leaf.risk_weights.copy()
        actual = predict_win(leaf, roots)
        expected = np.asarray([literal_probability(board, reference.terminal, leaf.radix)
            for board in roots])
        np.testing.assert_array_equal(actual['logits'], expected[:, 0])
        np.testing.assert_array_equal(actual['probabilities'], expected[:, 1])
        np.testing.assert_array_equal(leaf.reward_weights, reward)
        np.testing.assert_array_equal(leaf.risk_weights, risk)
        assert leaf.updates == prior_updates == reference.receipts[-1]['updates']
        assert actual['readonly'] and actual['updates_before'] == actual['updates_after'] == prior_updates
        assert actual['roots'] == 8
        assert actual['counts'] == dict(win_predictions=8, reward_predictions=8,
            win_table_lookups=256, reward_table_lookups=256, feature_extractions=8,
            feature_occurrences=256, feature_digit_reads=1536,
            feature_address_multiply_adds=1536, fit_updates=0, parameter_writes=0)
        assert actual['representation_counts'] == dict(risk_sigmoid_evaluations=8,
            local_risk_table_lookups=256, combined_value_additions=16,
            combined_value_multiplications=8)
        assert actual['cpu_seconds'] >= 0. and actual['seconds'] >= 0.


def test_saved_head_prediction_rejects_writable_parameters():
    # Writable heads indicate the caller has not finished restoration before diagnosis.
    from types import SimpleNamespace
    leaf = SimpleNamespace(kind='LOCAL_RISK', reward_weights=np.zeros(1), risk_weights=np.zeros(1))
    with pytest.raises(ValueError, match='frozen LOCAL_RISK'):
        predict_win(leaf, np.zeros((1, 16), dtype=np.int32))
