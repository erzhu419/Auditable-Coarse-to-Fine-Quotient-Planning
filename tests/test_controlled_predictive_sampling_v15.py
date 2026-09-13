"""Indexed batch streams preserve V14 and charge every actual request."""

import pytest

from acfqp.science.controlled_predictive_partial_v12 import RowSampleProvider, row_seed
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider, BATCH_SEED_STRIDE
import acfqp.science.controlled_predictive_sampling_v15 as sampling


DENSE = (1, 1, 3, 4, 5, 6, 7, 8, 9, 3, 4, 5, 6, 7, 8, 9)
SPARSE = (0,) * 5 + (1,) + (0,) * 10


@pytest.mark.parametrize('key,action', [((2, DENSE), 'LEFT'), ((1, SPARSE), 'DOWN')])
def test_batch_zero_and_sample_are_exactly_the_original_v14_stream(key, action):
    original = RowSampleProvider(832101)
    expected = original.sample(key, action)
    provider = BatchRowSampleProvider(832101)
    assert provider.sample(key, action) == expected
    assert provider.sample_batch(key, action, 0) == expected
    for field in ('row_requests', 'exact_transition_row_calls', 'support_entries_enumerated',
                  'physical_draws', 'sampled_successor_entries_returned'):
        assert provider.work_counts[field] == 2 * original.work_counts[field]
    assert provider.work_counts['first_batch_requests'] == 2
    assert provider.work_counts['repeat_batch_requests'] == 0
    assert provider.provider_seconds > 0


def test_batches_are_order_independent_and_identical_repeat_requests_remain_paid():
    key, action = (2, DENSE), 'LEFT'
    first, second = BatchRowSampleProvider(832102), BatchRowSampleProvider(832102)
    order_a, order_b = (2, 0, 1), (1, 2, 0)
    rows_a = {index: first.sample_batch(key, action, index) for index in order_a}
    rows_b = {index: second.sample_batch(key, action, index) for index in order_b}
    assert rows_a == rows_b
    assert first.sample_batch(key, action, 2) == rows_a[2]
    assert first.work_counts['row_requests'] == first.work_counts['exact_transition_row_calls'] == 4
    assert first.work_counts['physical_draws'] == 4 * 256
    assert first.work_counts['first_batch_requests'] == 1
    assert first.work_counts['repeat_batch_requests'] == 3
    assert second.work_counts['physical_draws'] == 3 * 256
    expected = RowSampleProvider(832102 + BATCH_SEED_STRIDE).sample(key, action)
    assert rows_a[1] == expected


def test_direct_late_batch_enumerates_and_draws_once_without_replaying_prefix(monkeypatch):
    key, action, seed, index = (1, SPARSE), 'DOWN', 832103, 127
    actual_step, actual_random = sampling._step_v1, sampling.random.Random
    step_calls, stream_seeds, draw_sizes = [], [], []

    def recorded_step(state, selected_action):
        step_calls.append((state, selected_action))
        return actual_step(state, selected_action)

    class RecordedRandom:
        def __init__(self, stream_seed):
            stream_seeds.append(stream_seed)
            self.stream = actual_random(stream_seed)

        def choices(self, population, weights, k):
            draw_sizes.append(k)
            return self.stream.choices(population, weights=weights, k=k)

    monkeypatch.setattr(sampling, '_step_v1', recorded_step)
    monkeypatch.setattr(sampling.random, 'Random', RecordedRandom)
    provider = BatchRowSampleProvider(seed)
    row = provider.sample_batch(key, action, index)
    assert len(step_calls) == 1
    assert stream_seeds == [row_seed(seed + BATCH_SEED_STRIDE * index, key, action)]
    assert draw_sizes == [256]
    assert provider.work_counts['physical_draws'] == 256
    assert sum(weight for weight, _, _ in row) == 1
    assert all((weight * 256).is_integer() and successor[0] == 0 for weight, successor, _ in row)
    with pytest.raises(ValueError, match='0..127'):
        provider.sample_batch(key, action, 128)
    assert provider.work_counts['physical_draws'] == 256
