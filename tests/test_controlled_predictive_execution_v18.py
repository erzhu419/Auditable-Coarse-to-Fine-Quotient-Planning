"""Full V17 histories stay exact with cached V18 scoring, including diagnostics."""

import pytest

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_execution_v13 import ExactEnvironment
from acfqp.science.controlled_predictive_execution_v17 import evaluate_balanced_gap_execution
from acfqp.science.controlled_predictive_gap_v16 import GapPlannerState
from acfqp.science.controlled_predictive_mass_bound_v14 import MassBoundPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState

BOARD = (1, 1, 3, 3, 5, 6, 7, 8, 9, 3, 4, 5, 6, 7, 8, 9)
ROOT = (2, BOARD)


@pytest.mark.parametrize("mode", ["STOP", "CONTINUE"])
@pytest.mark.parametrize("query_name", ["q", "zero"])
def test_full_recorded_histories_are_exact_including_gap_assessments(mode, query_name):
    warm = MassBoundPlannerState(ROOT, {"q": Query(1, 1, 0), "zero": Query(0, 0, 0)})
    provider = BatchRowSampleProvider(71)
    for action in warm.profiles[ROOT].legal_actions:
        warm.observe_row(ROOT, action, provider.sample(ROOT, action))
    environment = ExactEnvironment.from_closure(build_development_closure(horizon=2, boards={"fixture": BOARD}))
    full, cached = [evaluate_balanced_gap_execution(
        cls.from_warm(warm), BatchRowSampleProvider(71), query_name, environment,
        mode=mode, total_batch_cap=12) for cls in (GapPlannerState, CachedGapPlannerState)]
    assert cached["trace"] == full["trace"]
    assert cached["root_metrics"] == full["root_metrics"]
    assert cached["physical_audit"]["provider_counts"] == full["physical_audit"]["provider_counts"]
    for name in ("expected_total_batches", "maximum_total_batches", "expected_total_draws", "maximum_total_draws"):
        assert cached["deployment"][name] == full["deployment"][name]
    assert cached["deployment"]["maximum_total_batches"] <= 12
    if query_name == "q":
        old_work = full["deployment"]["expected_suffix_work_counts"]
        new_work = cached["deployment"]["expected_suffix_work_counts"]
        assert new_work["gap_score_state_visits"] < old_work["gap_score_state_visits"]
        assert new_work.get("resampling_score_state_visits", 0) == 0
