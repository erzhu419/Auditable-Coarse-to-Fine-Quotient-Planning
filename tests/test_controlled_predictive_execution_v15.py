"""Actual batch caps, first-observation priority and paid repeated execution."""

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v15 import evaluate_resampling_execution
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_resampling_v15 import ResamplingPlannerState
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider


BOARD = (0,) * 5 + (1,) + (0,) * 10
ROOT = (1, BOARD)


def setup_warm(query, complete=True):
    warm = MassBoundPlannerState(ROOT, {"q": query})
    provider = BatchRowSampleProvider(71)
    if complete:
        for action in warm.profiles[ROOT].legal_actions:
            warm.observe_row(ROOT, action, provider.sample(ROOT, action))
    warm.solve("q")
    closure = build_development_closure(horizon=1, boards={"fixture": BOARD})
    return ResamplingPlannerState.from_warm(warm), ExactEnvironment.from_closure(closure)


@pytest.mark.parametrize("mode", ["BALANCED", "DIRECTED"])
def test_repeat_batches_consume_cap_even_when_distinct_rows_do_not_increase(mode):
    warm, environment = setup_warm(Query(1, 1, 0))
    provider = BatchRowSampleProvider(71)
    result = evaluate_resampling_execution(warm, provider, "q", environment, mode=mode, total_batch_cap=7)
    trace, deploy = result["trace"], result["deployment"]
    assert trace["rows_before"] == trace["rows_after"] == 4
    assert trace["batches_before"] == 4 and trace["batches_after"] == 7
    assert trace["quota"] == 3
    assert all(item["batch_index"] >= 1 and item["kind"] == "REPEAT_OBSERVATION"
               for item in trace["requested_batches"])
    assert deploy["expected_total_batches"] == deploy["maximum_total_batches"] == 7
    assert deploy["expected_total_draws"] == deploy["maximum_total_draws"] == 1792
    assert deploy["expected_total_distinct_rows"] == deploy["maximum_total_distinct_rows"] == 4
    assert deploy["expected_suffix_work_counts"]["provider_physical_draws"] == 768
    assert result["physical_audit"]["provider_counts"]["repeat_batch_requests"] == 3
    assert deploy["expected_seconds_by_stage"]["query_initialization_clone"] == result["initial_query_clone_seconds"]
    assert warm.spent_batches == 4 and all(count == 1 for count in warm.batch_counts.values())
    assert "initial_rows" not in deploy


def test_zero_physical_range_stops_without_spending_and_is_not_a_confidence_claim():
    warm, environment = setup_warm(Query(0, 0, 0))
    provider = BatchRowSampleProvider(71)
    result = evaluate_resampling_execution(warm, provider, "q", environment, total_batch_cap=7)
    assert result["deployment"]["expected_total_batches"] == 4
    assert not provider.work_counts
    assert result["trace"]["acquisition_stop_reason"] == "NO_POSITIVE_RANGE_OBSERVED_CANDIDATE"
    assert "not a confidence interval" in result["acquisition_score_scope"]


def test_structural_first_observation_precedes_any_resampling_score(monkeypatch):
    warm, environment = setup_warm(Query(1, 1, 0), complete=False)
    def should_not_run(*args, **kwargs):
        raise AssertionError("one structural batch must use the entire local quota")
    monkeypatch.setattr(ResamplingPlannerState, "select_resample", should_not_run)
    result = evaluate_resampling_execution(warm, BatchRowSampleProvider(71), "q", environment,
                                          total_batch_cap=1)
    assert result["trace"]["requested_batches"][0]["batch_index"] == 0
    assert result["trace"]["requested_batches"][0]["kind"] == "FIRST_OBSERVATION"
    assert result["deployment"]["maximum_total_batches"] == 1
    assert warm.spent_batches == 0
