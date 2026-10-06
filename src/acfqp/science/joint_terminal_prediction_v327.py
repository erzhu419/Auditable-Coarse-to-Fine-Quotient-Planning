"""Read both learned targets once per retained root through the actual native head."""
from collections import Counter
from time import perf_counter, process_time

import numpy as np

from .native_query_supervision_v319 import _boards
from .native_split_risk_v301 import predict_components


def predict_components_batch(leaf, roots):
    if (leaf.kind != 'LOCAL_RISK' or leaf.reward_weights.flags.writeable
            or leaf.risk_weights.flags.writeable):
        raise ValueError('V327 prediction requires a frozen LOCAL_RISK head')
    started, cpu = perf_counter(), process_time()
    boards = _boards(roots)
    before = leaf.updates
    rewards, probabilities, logits, utilities = (np.empty(len(boards)) for _ in range(4))
    representation = Counter()
    for index, board in enumerate(boards):
        value = predict_components(leaf, board)
        rewards[index] = value['reward_prediction']
        probabilities[index] = value['risk_probability']
        logits[index] = value['risk_logit']
        utilities[index] = value['combined_prediction']
        representation.update(value['representation_counts'])
    if leaf.updates != before:
        raise ValueError('V327 read-only prediction changed the saved head')
    n = len(boards)
    return dict(rewards=rewards, probabilities=probabilities, logits=logits, utilities=utilities,
        roots=n, updates_before=before, updates_after=leaf.updates, readonly=True,
        prediction_rule='ACTUAL_V301_NATIVE_COMPONENT_PREDICTOR_SINGLE_PASS',
        counts=dict(win_predictions=n, reward_predictions=n,
            win_table_lookups=32*n, reward_table_lookups=32*n,
            feature_extractions=n, feature_occurrences=32*n,
            feature_digit_reads=192*n, feature_address_multiply_adds=192*n,
            fit_updates=0, parameter_writes=0),
        representation_counts=dict(representation),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
