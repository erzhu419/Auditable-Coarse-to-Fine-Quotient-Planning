"""Independent, explicitly indexed batches for V15 row observations.

The history-local planner supplies the batch index. Repeated requests, including
identical indices on counterfactual histories, repeat and charge the physical
work. This provider retains no sampled rows or mutable random-stream position.
"""

from __future__ import annotations

from collections import Counter
import random
from time import perf_counter

from acfqp.domains.standard_2048 import (
    Swipe2048Action, Swipe2048State, Swipe2048Status, step_v1 as _step_v1,
)
from .controlled_predictive_partial_v12 import Key, SampleRow, row_seed


BATCH_SEED_STRIDE = 1_000_000
MAX_BATCH_INDEX = 127


class BatchRowSampleProvider:
    """Return 256 observations for one requested row and explicit batch index."""

    def __init__(self, seed: int, samples_per_batch: int = 256):
        if type(seed) is not int or not 0 <= seed < BATCH_SEED_STRIDE:
            raise ValueError("the base seed must lie in the first million-seed band")
        if samples_per_batch != 256:
            raise ValueError("V15 freezes 256 observations per requested batch")
        self.seed = seed
        self.samples_per_batch = samples_per_batch
        self.work_counts: Counter = Counter()
        self.provider_seconds = 0.0

    def sample(self, key: Key, action: str) -> SampleRow:
        """The first batch has exactly the V12/V14 row stream and row format."""
        return self.sample_batch(key, action, 0)

    def sample_batch(self, key: Key, action: str, batch_index: int) -> SampleRow:
        if type(batch_index) is not int or not 0 <= batch_index <= MAX_BATCH_INDEX:
            raise ValueError("V15 batch indices are integers in 0..127")
        started = perf_counter()
        stream_seed = row_seed(self.seed + BATCH_SEED_STRIDE * batch_index, key, action)
        self.work_counts["row_requests"] += 1
        self.work_counts["first_batch_requests" if batch_index == 0 else "repeat_batch_requests"] += 1
        support = _step_v1(Swipe2048State(key[1], Swipe2048Status.ACTIVE), Swipe2048Action(action))
        self.work_counts.update(exact_transition_row_calls=1, support_entries_enumerated=len(support))
        sampled = random.Random(stream_seed).choices(
            support, weights=[float(outcome.probability) for outcome in support], k=self.samples_per_batch,
        )
        counts = Counter(((key[0] - 1, outcome.next_state.board), outcome.merge_score / 2048.0)
                         for outcome in sampled)
        result = tuple((count / self.samples_per_batch, successor, reward)
                       for (successor, reward), count in sorted(counts.items()))
        self.work_counts.update(physical_draws=self.samples_per_batch,
                                sampled_successor_entries_returned=len(result))
        self.provider_seconds += perf_counter() - started
        return result
