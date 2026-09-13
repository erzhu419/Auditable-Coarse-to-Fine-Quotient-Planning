from dataclasses import replace

import pytest

from acfqp.science import controlled_predictive_incremental_v13 as incremental
from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_mass_bound_v14 import mass_bound_unknown_action_bounds
from acfqp.science.controlled_predictive_projection_v23 import project_endpoint
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_snapshot_v21 import state_record


def _key(horizon, rank):
    return horizon, (0,) * 5 + (rank,) + (0,) * 10


ROOT, A, B = _key(3, 1), _key(2, 2), _key(2, 3)
TAIL, NEW, ORPHAN = _key(1, 1), _key(1, 2), _key(1, 4)
END = _key(0, 3)
QUERIES = {"risk": Query(1, 5, 0), "alt": Query(.2, .25, 3)}
PANEL = (ROOT, A, B, TAIL)


def _states():
    common = CachedGapPlannerState(ROOT, QUERIES)
    for key, action, successor in ((ROOT, "DOWN", A), (ROOT, "RIGHT", B),
                                   (A, "DOWN", TAIL), (B, "DOWN", TAIL)):
        common.observe_batch(key, action, ((1., successor, 0.),))
    endpoint = common.clone()
    endpoint.observe_batch(A, "DOWN", ((.5, TAIL, 0.), (.5, NEW, 0.)))
    endpoint.observe_batch(A, "DOWN", ((.25, TAIL, 0.), (.75, NEW, 0.)))
    endpoint.observe_batch(A, "LEFT", ((1., ORPHAN, 0.),))
    endpoint.observe_batch(A, "LEFT", ((1., ORPHAN, 0.),))
    endpoint.observe_batch(NEW, "DOWN", ((1., END, 0.),))
    for state in (common, endpoint):
        for name in QUERIES:
            state.solve(name)
            state._gap_scores(name)
    return common, endpoint


def _forbidden(*args, **kwargs):
    raise AssertionError("projection accessed profiling, sampling, truth or warm conversion")


def test_masked_rows_restore_unknown_bounds_and_remove_their_only_profiles():
    # Both first observations and later repeats of a newly acquired row vanish.
    common, endpoint = _states()
    projected, report = project_endpoint(common, endpoint, query_name="risk", panel=PANEL)
    assert projected.row_order == common.row_order and projected.rows.keys() == common.rows.keys()
    assert (A, "LEFT") not in projected.rows and (NEW, "DOWN") not in projected.rows
    assert ORPHAN not in projected.profiles and END not in projected.profiles
    assert set(common.profiles) <= projected.profiles.keys()
    for pair in ((A, "LEFT"), (NEW, "DOWN")):
        lower, upper = mass_bound_unknown_action_bounds(pair[0], projected.profiles[pair[0]], pair[1], QUERIES["risk"])
        assert projected.caches["risk"].q_lower[pair] == lower
        assert projected.caches["risk"].q_upper[pair] == upper
        assert projected.score_caches["risk"].scores.q_lower[pair] == lower
        assert projected.score_caches["risk"].scores.q_upper[pair] == upper
    assert report["original_endpoint_batches"] == 9
    assert report["retained_model_batches"] == projected.spent_batches == 6
    assert report["masked_new_row_count"] == 2
    assert report["masked_observation_batches"] == 3
    assert report["masked_draws"] == 768
    assert report["retained_repeat_batches"] == 2
    assert not report["original_acquisition_cost_refunded"]
    assert report["original_local_observation_batches"] == 5


def test_retained_row_repeats_and_new_successor_profiles_survive_without_external_calls(monkeypatch):
    common, endpoint = _states()
    monkeypatch.setattr(incremental, "profile", _forbidden)
    monkeypatch.setattr(BatchRowSampleProvider, "sample_batch", _forbidden)
    monkeypatch.setattr(DevelopmentClosure, "__init__", _forbidden)
    monkeypatch.setattr(CachedGapPlannerState, "from_warm", _forbidden)
    projected, report = project_endpoint(common, endpoint, query_name="risk", panel=PANEL)
    pair = A, "DOWN"
    assert projected.batch_counts[pair] == 3
    assert projected.outcome_counts[pair] == {(TAIL, 0.): 448, (NEW, 0.): 320}
    assert projected.outcome_counts[pair] == endpoint.outcome_counts[pair]
    assert projected.rows[pair] == endpoint.rows[pair]
    assert projected.profiles[NEW] == endpoint.profiles[NEW]
    assert report["retained_new_successor_profile_count"] == 1
    assert report["new_provider_calls"] == report["new_physical_draws"] == report["truth_calls"] == 0


def test_reverse_dependencies_and_only_current_caches_are_rebuilt_without_contaminating_inputs():
    common, endpoint = _states()
    before_common, before_endpoint = state_record(common, "risk"), state_record(endpoint, "risk")
    projected, report = project_endpoint(common, endpoint, query_name="risk", panel=PANEL)
    assert projected.reverse_dependencies == {A: {ROOT}, B: {ROOT}, TAIL: {A, B}, NEW: {A}}
    assert list(projected.caches) == list(projected.score_caches) == ["risk"]
    assert set(projected.caches["risk"].lower) == set(projected.profiles)
    assert set(projected.score_caches["risk"].scores.lower) == set(projected.profiles)
    assert not projected.caches["risk"].dirty and not projected.score_caches["risk"].dirty
    assert projected.engine_seconds == endpoint.engine_seconds + report["projection_seconds"]
    assert report["projection_work_counts"]["query_cache_initializations"] == 1
    assert report["projection_work_counts"]["gap_score_cache_initializations"] == 1
    projected.outcome_counts[A, "DOWN"][TAIL, 0.] += 1
    projected.batch_counts[A, "DOWN"] += 1
    projected.reverse_dependencies[TAIL].clear()
    projected.caches["risk"].lower[A] = -999
    projected.score_caches["risk"].scores.lower[A] = -998
    assert state_record(common, "risk") == before_common
    assert state_record(endpoint, "risk") == before_endpoint


def test_identity_projection_preserves_complete_model_scores_and_actions():
    common, _ = _states()
    endpoint = common.clone()
    endpoint.observe_batch(A, "DOWN", endpoint.rows[A, "DOWN"])
    for name in QUERIES:
        endpoint.solve(name)
        endpoint._gap_scores(name)
    before = state_record(endpoint, "risk")
    projected, report = project_endpoint(common, endpoint, query_name="risk", panel=PANEL)
    assert state_record(projected, "risk") == before
    assert projected._gap_scores("risk") == endpoint._gap_scores("risk")
    assert projected.assess_gap(ROOT, "risk") == endpoint.assess_gap(ROOT, "risk")
    assert report["masked_new_row_count"] == report["masked_observation_batches"] == report["masked_draws"] == 0
    assert projected.spent_batches == endpoint.spent_batches == 5


@pytest.mark.parametrize("damage,message", [
    ("missing_row", "common action row is missing"),
    ("prefix_count", "lost prefix observations"),
    ("profile", "common profile changed"),
    ("panel", "fixed panel is absent"),
])
def test_projection_rejects_prefix_or_fixed_panel_changes(damage, message):
    common, endpoint = _states()
    panel = PANEL
    if damage == "missing_row":
        del endpoint.rows[A, "DOWN"]
    elif damage == "prefix_count":
        counts = endpoint.outcome_counts[A, "DOWN"]
        counts[TAIL, 0.] = 255
        counts[NEW, 0.] = 513
    elif damage == "profile":
        endpoint.profiles[A] = replace(endpoint.profiles[A], mass=999)
    else:
        panel = (*PANEL, NEW)
    with pytest.raises(ValueError, match=message):
        project_endpoint(common, endpoint, query_name="risk", panel=panel)
