"""Withhold newly acquired action rows from an already observed endpoint."""

from time import perf_counter

from .controlled_predictive_score_cache_v18 import CachedGapPlannerState


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def project_endpoint(common_state, endpoint_state, *, query_name, panel):
    """Keep endpoint counts on the fixed initial row set, without refunding work.

    The result is an evaluation model. Its spent_batches records retained
    information, not the actual acquisition cost or an available new budget.
    """
    started = perf_counter()
    _require(common_state.root == endpoint_state.root, "common and endpoint roots differ")
    _require(list(common_state.queries) == list(endpoint_state.queries)
             and common_state.queries == endpoint_state.queries, "common and endpoint queries differ")
    _require(query_name in common_state.queries, "current query is missing")
    _require(all(key in common_state.profiles for key in panel), "fixed panel is absent from the common model")
    for key, profile in common_state.profiles.items():
        _require(endpoint_state.profiles.get(key) == profile, "common profile changed in endpoint")
    initial_rows = set(common_state.rows)
    _require(initial_rows <= endpoint_state.rows.keys(), "common action row is missing from endpoint")
    for pair in common_state.row_order:
        old_counts, counts = common_state.outcome_counts[pair], endpoint_state.outcome_counts[pair]
        batches = endpoint_state.batch_counts[pair]
        _require(type(batches) is int and batches >= common_state.batch_counts[pair],
                 "endpoint row lost prefix observation batches")
        _require(all(type(count) is int and count > 0 for count in counts.values())
                 and sum(counts.values()) == 256 * batches, "endpoint pooled integer counts differ from batches")
        _require(all(counts.get(outcome, 0) >= count for outcome, count in old_counts.items()),
                 "endpoint pooled counts lost prefix observations")
        row = endpoint_state.rows[pair]
        _require(len(row) == len(counts)
                 and {(successor, reward) for _, successor, reward in row} == set(counts)
                 and all(weight == counts[successor, reward] / (256 * batches)
                         for weight, successor, reward in row), "endpoint retained row differs from pooled counts")
    projected = endpoint_state.clone()
    projected.__class__ = CachedGapPlannerState
    projected.row_order = list(common_state.row_order)
    projected.rows = {pair: projected.rows[pair] for pair in projected.row_order}
    projected.outcome_counts = {pair: projected.outcome_counts[pair] for pair in projected.row_order}
    projected.batch_counts = {pair: projected.batch_counts[pair] for pair in projected.row_order}
    retained_profiles = set(common_state.profiles)
    projected.reverse_dependencies = {}
    for (key, _), row in projected.rows.items():
        for _, successor, _ in row:
            _require(successor in endpoint_state.profiles, "retained successor profile is missing")
            retained_profiles.add(successor)
            projected.reverse_dependencies.setdefault(successor, set()).add(key)
    projected.profiles = {key: profile for key, profile in endpoint_state.profiles.items() if key in retained_profiles}
    projected.spent_batches = sum(projected.batch_counts.values())
    projected.caches, projected.score_caches = {}, {}
    projected.stop_reason = None
    projected.work_counts.update(projection_calls=1,
        projection_prefix_outcomes_checked=sum(map(len, common_state.outcome_counts.values())),
        projection_retained_outcomes_checked=sum(map(len, projected.outcome_counts.values())),
        projection_profiles_retained=len(projected.profiles), projection_rows_retained=len(projected.rows),
        projection_reverse_edges_rebuilt=sum(map(len, projected.reverse_dependencies.values())),
        projection_query_caches_cleared=len(endpoint_state.caches),
        projection_score_caches_cleared=len(endpoint_state.score_caches))
    projected.solve(query_name)
    projected._gap_scores(query_name)
    masked_pairs = endpoint_state.rows.keys() - initial_rows
    masked_batches = sum(endpoint_state.batch_counts[pair] for pair in masked_pairs)
    _require(endpoint_state.spent_batches == projected.spent_batches + masked_batches,
             "endpoint total batches differ from retained and masked counts")
    report = {
        "original_common_batches": common_state.spent_batches,
        "original_endpoint_batches": endpoint_state.spent_batches,
        "original_local_observation_batches": endpoint_state.spent_batches - common_state.spent_batches,
        "retained_model_batches": projected.spent_batches,
        "retained_repeat_batches": projected.spent_batches - common_state.spent_batches,
        "retained_action_row_count": len(projected.rows),
        "masked_new_row_count": len(masked_pairs),
        "masked_observation_batches": masked_batches,
        "masked_draws": 256 * masked_batches,
        "retained_profile_count": len(projected.profiles),
        "retained_new_successor_profile_count": len(retained_profiles - common_state.profiles.keys()),
        "removed_profile_count": len(endpoint_state.profiles) - len(projected.profiles),
        "fixed_panel_count": len(panel),
        "original_acquisition_cost_refunded": False,
        "new_provider_calls": 0,
        "new_physical_draws": 0,
        "truth_calls": 0,
        "projection_work_counts": dict(projected.work_counts - endpoint_state.work_counts),
        "scope": "Information projection of the fixed endpoint; retained model batches are not a new acquisition budget.",
    }
    report["projection_seconds"] = perf_counter() - started
    # This complete span includes clone, validation and cache preparation once.
    projected.engine_seconds = endpoint_state.engine_seconds + report["projection_seconds"]
    return projected, report
