from copy import deepcopy
from unittest.mock import patch

from acfqp.science.controlled_predictive_encoder_v7 import ACTIONS, TrainingModel
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome, Query
from acfqp.science.controlled_predictive_source_prior_v12 import fit_source_prior


LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)


def _board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


def _source(name, rank, safe_action):
    return TrainingModel(name, FiniteModel(
        {0: 1, 1: 0, 2: 0}, {0: "ACTIVE", 1: "CUTOFF", 2: "LOST"},
        {(0, action): (Outcome(1, 1 if action == safe_action else 2, 0),) for action in ACTIONS},
        (0,),
    ), {0: _board(rank), 1: _board(1), 2: LOST})


def _fit():
    return fit_source_prior([_source("source_a", 1, "UP"), _source("source_b", 2, "DOWN")],
                            {"risk": Query(1, 1, 0), "reward": Query()})


def test_disjoint_source_union_preserves_overlapping_input_ids_and_source_q_values():
    """Overlapping local state IDs must not overwrite a source or mix its successors."""
    sources = [_source("source_a", 1, "UP"), _source("source_b", 2, "DOWN")]
    before = deepcopy(sources)
    with patch("acfqp.science.controlled_predictive_quotient_v1.sample_model", side_effect=AssertionError("resampling")), \
         patch("acfqp.domains.standard_2048.step_v1", side_effect=AssertionError("true kernel")), \
         patch("acfqp.domains.standard_2048.support_outcomes_v1", side_effect=AssertionError("true support")):
        built = fit_source_prior(sources, {"risk": Query(1, 1, 0)})
    assert sources == before
    assert built.diagnostics["source_model_names"] == ["source_a", "source_b"]
    assert built.diagnostics["source_union_state_records"] == 6
    assert built.diagnostics["source_union_action_rows"] == 8
    assert built.diagnostics["source_union_root_count"] == 2
    assert len(set(built.compiled.roots)) == 2
    assert sorted(state for cell in built.compiled.cells.values() for state in cell.members) == list(range(6))
    for rank, safe in ((1, "UP"), (2, "DOWN")):
        code = built.encoder.encode(_board(rank), 1)
        assert built.q_by_query["risk"][code] == {action: 0.0 if action == safe else -1.0 for action in ACTIONS}
    assert built.diagnostics["source_queries"]["risk"]["q_extraction_counts"]["state_action_rows"] == 8


def test_priority_uses_query_object_and_returns_zero_for_unavailable_source_information():
    built = _fit()
    callback = built.make_priority()
    assert callback((1, _board(1)), Query(1, 1, 0))["UP"] == 0
    assert callback((1, _board(1)), Query(1, 1, 0))["DOWN"] == -1
    assert callback((1, _board(1)), Query()) == dict.fromkeys(ACTIONS, 0.0)
    assert callback((2, _board(1)), Query(1, 1, 0)) == dict.fromkeys(ACTIONS, 0.0)
    assert callback((1, _board(1)), Query(1, .37, .2)) == dict.fromkeys(ACTIONS, 0.0)
    code = built.encoder.encode(_board(1), 1)
    del built.q_by_query["risk"][code]["LEFT"]
    assert callback((1, _board(1)), Query(1, 1, 0))["LEFT"] == 0.0


def test_shuffled_priority_rotates_same_code_action_values_without_modifying_source_fit():
    built = _fit()
    original_payload = deepcopy(built.encoder.to_payload())
    original_q = deepcopy(built.q_by_query)
    plain, shuffled = built.make_priority(), built.make_priority(shuffled=True)
    key, query = (1, _board(1)), Query(1, 1, 0)
    values, rotated = plain(key, query), shuffled(key, query)
    assert rotated == {action: values[ACTIONS[(index + 1) % len(ACTIONS)]]
                       for index, action in enumerate(ACTIONS)}
    assert sorted(rotated.values()) == sorted(values.values())
    assert rotated != values
    assert built.encoder.to_payload() == original_payload and built.q_by_query == original_q


def test_each_arm_has_independent_cache_and_immutable_checkpoint_counter_snapshots():
    """Sharing warm encoding state would give later acquisition arms uncharged work."""
    built = _fit()
    first, second = built.make_priority(), built.make_priority()
    key, query = (1, _board(1)), Query(1, 1, 0)
    first(key, query)
    checkpoint = first.diagnostics()
    first(key, Query())
    second(key, query)
    assert checkpoint["work_counts"]["priority_callback_calls"] == 1
    assert first.diagnostics()["work_counts"]["priority_callback_calls"] == 2
    assert first.diagnostics()["work_counts"]["priority_code_cache_hits"] == 1
    assert second.diagnostics()["work_counts"]["priority_code_cache_misses"] == 1
    assert second.diagnostics()["work_counts"].get("priority_code_cache_hits", 0) == 0
    assert checkpoint["work_counts"]["states_profiled"] == second.diagnostics()["work_counts"]["states_profiled"] == 1
    assert checkpoint["cached_state_keys"] == second.diagnostics()["cached_state_keys"] == 1
