"""Complementary partitions and root-only readouts preserve retained data."""

from collections import Counter
from copy import deepcopy
import math
import random

import pytest

from acfqp.science.controlled_predictive_crossfit_v38 import split_counts, pooled_root_readout, crossfit_root_readout
from acfqp.science.controlled_predictive_partial_v12 import row_seed
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from test_controlled_predictive_decomposition_v19 import ROOT, A, B, END

ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
WON = 0, (11,) + (0,) * 15


def fixture(observed=True):
    state = CachedGapPlannerState(ROOT, {'q': Query(1., 1., 1.)})
    if observed:
        for key in (A, B):
            for action in ('LEFT', 'RIGHT'):
                state.observe_batch(key, action, ((.5, END, .1), (.5, WON, .1)))
    for action in ACTIONS:
        p = .75 if action == 'UP' else .25
        state.observe_batch(ROOT, action, ((p, A, 0.), (1 - p, B, 0.)))
    state.solve('q')
    return state


def test_split_uses_sorted_multiset_exact_seed_and_complement_without_global_rng_changes():
    counts = Counter({(WON, .1): 193, (END, .1): 63})
    before = random.getstate()
    a, b, record = split_counts(counts, 38, 962001, A, 'LEFT')
    expected = Counter(random.Random(row_seed(38 * 1_000_000 + 962001, A, 'LEFT')).sample(range(2), counts=[63, 193], k=128))
    assert [a[outcome] for outcome in sorted(counts)] == [expected[0], expected[1]]
    assert sum(a.values()) == sum(b.values()) == 128
    assert all(a[outcome] + b[outcome] == counts[outcome] for outcome in counts)
    assert record['row_seed'] == row_seed(38962001, A, 'LEFT')
    assert split_counts(Counter(dict(reversed(list(counts.items())))), 38, 962001, A, 'LEFT') == (a, b, record)
    assert random.getstate() == before
    assert counts == Counter({(WON, .1): 193, (END, .1): 63})


def test_single_outcome_splits_without_rng_and_has_exact_equal_halves(monkeypatch):
    monkeypatch.setattr(random, 'Random', lambda *args: pytest.fail('a deterministic single-outcome split needs no RNG'))
    a, b, record = split_counts(Counter({(END, .1): 768}), 38, 962001, A, 'RIGHT')
    assert a == b == {(END, .1): 384} and not record['random_partition']


def test_cross_readout_uses_held_out_choices_without_changing_any_execution_state():
    state = fixture()
    before = deepcopy(state.__dict__)
    pooled = pooled_root_readout(state, 'q')
    readout = crossfit_root_readout(state, 'q', 38, 962001)
    assert state.__dict__ == before
    assert readout['validation']['passed']
    assert len(readout['split_rows']) == 4
    assert readout['accounting']['retained_draws_partitioned'] == 1024
    assert readout['accounting']['new_provider_calls'] == readout['accounting']['new_sampling_calls'] == readout['accounting']['new_physical_draws'] == 0
    for row in readout['continuations']:
        a, b = row['fold_actions']
        qa, qb = ({name: values[fold] for name, values in row['fold_q_values'].items()} for fold in ('A', 'B'))
        assert a == min(qa, key=lambda action: (-qa[action], action))
        assert b == min(qb, key=lambda action: (-qb[action], action))
        assert row['cross_value'] == .5 * math.fsum((qb[a], qa[b]))
        assert row['cross_value'] <= row['pooled_value'] + 1e-10
        assert row['fold_q_values']['UP']['A'] == row['fold_q_values']['UP']['B'] == -1
    assert all(readout['root_values'][action] <= pooled['root_values'][action] + 1e-10 for action in ACTIONS)
    assert readout['root_action'] == min(readout['root_values'], key=lambda action: (-readout['root_values'][action], action))


def test_all_unknown_h1_keeps_pooled_bounds_and_query_does_not_change_partitions():
    state = fixture(observed=False)
    readout = crossfit_root_readout(state, 'q', 38, 962001)
    assert readout['split_rows'] == []
    assert readout['root_values'] == pooled_root_readout(state, 'q')['root_values']
    assert all(row['cross_value'] == row['pooled_value'] == -1 for row in readout['continuations'])
    state = fixture()
    first = crossfit_root_readout(state, 'q', 38, 962001)
    state.queries['other'] = Query(1., 5., 2.)
    state.solve('other')
    second = crossfit_root_readout(state, 'other', 38, 962001)
    assert first['split_rows'] == second['split_rows']


def test_terminal_h1_keeps_values_and_near_ties_are_ranked_exactly():
    terminal = 1, WON[1]
    state = CachedGapPlannerState(ROOT, {'q': Query(1., 1., 2.)})
    for action in ACTIONS:
        state.observe_batch(ROOT, action, ((1., terminal, 5e-11 if action == 'UP' else 0.),))
    state.solve('q')
    readout = crossfit_root_readout(state, 'q', 38, 962001)
    assert readout['root_action'] == 'UP'
    assert readout['split_rows'] == []
    assert readout['continuations'][0]['cross_value'] == 2
    assert readout['root_values'] == pooled_root_readout(state, 'q')['root_values']
