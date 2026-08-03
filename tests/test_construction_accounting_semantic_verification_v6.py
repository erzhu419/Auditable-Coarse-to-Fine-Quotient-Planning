from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import accounting_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_semantic_verification_v6 as verifier_v6
from acfqp import semantic_verification_v1
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _profiles():
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    return registry, stage, comparison, actual


def _values(registry):
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "common.protocol_checks": 3,
            "control.cap_checks": 7,
            "fallback.states_expanded": 2,
            "fallback.actions_evaluated": 4,
            "fallback.ground_steps": 4,
            "fallback.outcome_rows": 12,
            "fallback.bellman_backups": 4,
            "io.read_bytes": 101,
            "io.staged_bytes": 102,
            "io.output_bytes": 103,
            "io.mounted_bytes_peak": 104,
            "memory.working_bytes_peak": 105,
            "process.launches": 2,
            "process.exit_successes": 2,
            "route.attempts": 1,
            "route.successes": 1,
            "solver.attempts": 1,
            "solver.successes": 1,
        }
    )
    return values


def _records(registry, values=None):
    selected_values = _values(registry) if values is None else values
    return tuple(
        CounterRecordV1(
            registry.registry_id,
            path,
            selected_values[path],
            True,
            f"native-v6-recorder:{path}",
            registry.by_path[path].semantics_id,
            registry.by_path[path].owner,
            registry.by_path[path].unit,
            registry.by_path[path].lane,
            registry.by_path[path].scope,
            registry.by_path[path].reducer,
        )
        for path in registry.required_paths
    )


def _projection(vector, comparison, actual):
    values = {axis: 0 for axis in SHARED_AXES}
    source = vector.values
    for term in actual.terms:
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            values[term.target_axis] += contribution
        else:
            values[term.target_axis] = max(
                values[term.target_axis], contribution
            )
    return ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        tuple((axis, values[axis]) for axis in SHARED_AXES),
    )


def _chain(
    *,
    route_kind=RouteKindEnum.DIRECT_FALLBACK,
    stage_kind=registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
    values=None,
):
    registry, stage, comparison, actual = _profiles()
    records = _records(registry, values)
    subject = _id("v6-semantic-subject")
    vector = WorkVectorV1(
        registry.registry_id,
        subject,
        route_kind,
        records,
    )
    projected = _projection(vector, comparison, actual)
    kwargs = {
        "native_counter_records": records,
        "expected_subject_id": subject,
        "expected_route_kind": route_kind,
        "expected_stage_kind": stage_kind,
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": actual.actual_projection_profile_id,
        "claimed_work_vector": vector,
        "claimed_comparison_vector": projected,
    }
    return registry, stage, comparison, actual, records, vector, projected, kwargs


def test_v6_replay_recomputes_both_vectors_without_v1_semantic_relabel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        registry,
        stage,
        comparison,
        actual,
        records,
        vector,
        projected,
        kwargs,
    ) = _chain()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("V1 registry/projection authority was called")

    monkeypatch.setattr(accounting_v1, "derive_comparison_vector_v1", forbidden)
    monkeypatch.setattr(
        semantic_verification_v1, "verify_work_vector_semantics_v1", forbidden
    )
    monkeypatch.setattr(
        semantic_verification_v1,
        "verify_actual_projection_semantics_v1",
        forbidden,
    )
    result = verifier_v6.verify_construction_accounting_semantics_v6(**kwargs)

    assert result.counter_registry_id == registry.registry_id
    assert result.stage_profile_id == stage.stage_profile_id
    assert result.comparison_profile_id == comparison.comparison_profile_id
    assert result.actual_projection_profile_id == (
        actual.actual_projection_profile_id
    )
    assert result.work_vector.to_dict() == vector.to_dict()
    assert result.comparison_vector.to_dict() == projected.to_dict()
    assert len(result.work_vector.records) == len(records) == 202
    assert len(result.projected_counter_record_ids) == 182
    assert len(result.native_zero_paths) > 0
    assert result.stage_kind is (
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    )
    allowed = set(
        stage.by_stage[result.stage_kind].allowed_nonzero_paths
    )
    assert len(allowed & set(registry.required_paths)) == 24
    assert len(result.forbidden_required_zero_paths) == 178
    assert len(allowed & {row.path for row in registry.operational_leaves}) == 16
    assert len(result.forbidden_operational_zero_paths) == 166
    by_path = {row.path: row for row in result.work_vector.records}
    assert all(
        by_path[path].value == 0
        for path in result.forbidden_required_zero_paths
    )
    assert result.forbidden_required_zero_counter_record_ids == tuple(
        by_path[path].record_id
        for path in result.forbidden_required_zero_paths
    )
    assert result.forbidden_operational_zero_counter_record_ids == tuple(
        by_path[path].record_id
        for path in result.forbidden_operational_zero_paths
    )
    assert result.to_document()["v1_registry_or_semantic_verifier_used"] is False


def test_native_record_order_is_not_trusted_and_canonical_work_is_rebuilt() -> None:
    *_prefix, kwargs = _chain()
    reversed_records = tuple(reversed(kwargs["native_counter_records"]))
    result = verifier_v6.verify_construction_accounting_semantics_v6(
        **{**kwargs, "native_counter_records": reversed_records}
    )
    assert tuple(row.path for row in result.work_vector.records) == tuple(
        sorted(row.path for row in reversed_records)
    )


@pytest.mark.parametrize(
    "field",
    (
        "counter_registry_id",
        "stage_profile_id",
        "comparison_profile_id",
        "actual_projection_profile_id",
    ),
)
def test_every_v6_profile_identity_is_mandatory(field: str) -> None:
    *_prefix, kwargs = _chain()
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="profile identity mismatch",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, field: _id("wrong-" + field)}
        )


def test_missing_duplicate_and_non_tuple_native_records_are_rejected() -> None:
    *_prefix, records, _vector, _comparison, kwargs = _chain()
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="omit explicit required",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": records[:-1]}
        )
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="repeat paths",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": (*records, records[0])}
        )
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="retained exact tuple",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": list(records)}
        )


def test_unobserved_native_zero_and_wrong_registry_record_are_rejected() -> None:
    registry, *_profiles_and_records, kwargs = _chain()
    records = kwargs["native_counter_records"]
    zero_index = next(
        index for index, record in enumerate(records) if record.value == 0
    )
    unobserved = replace(records[zero_index], observed=False)
    changed = (*records[:zero_index], unobserved, *records[zero_index + 1 :])
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="metadata/observation",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": changed}
        )

    foreign = replace(records[zero_index], counter_registry_id=_id("foreign-registry"))
    changed = (*records[:zero_index], foreign, *records[zero_index + 1 :])
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="metadata/observation",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": changed}
        )
    assert registry.registry_id != foreign.counter_registry_id


def test_evaluation_optional_and_unknown_paths_cannot_enter_v6_work() -> None:
    registry, *_profiles_and_records, kwargs = _chain()
    records = kwargs["native_counter_records"]
    evaluation_leaf = registry.by_path["evaluation.semantic_integrity_checks"]
    evaluation = CounterRecordV1(
        registry.registry_id,
        evaluation_leaf.path,
        1,
        True,
        "forbidden-evaluation-recorder",
        evaluation_leaf.semantics_id,
        evaluation_leaf.owner,
        evaluation_leaf.unit,
        evaluation_leaf.lane,
        evaluation_leaf.scope,
        evaluation_leaf.reducer,
    )
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="unknown/optional paths",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": (*records, evaluation)}
        )

    unknown = CounterRecordV1(
        registry.registry_id,
        "unknown.injected_path",
        1,
        True,
        "unknown-recorder",
        "unknown-semantics",
        "unknown-owner",
        "events",
        LaneEnum.OPERATIONAL,
        "unknown-scope",
        ReducerEnum.SUM,
    )
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="unknown/optional paths",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": (*records, unknown)}
        )


def test_lane_or_metadata_spoof_is_rejected_before_projection() -> None:
    *_prefix, kwargs = _chain()
    records = kwargs["native_counter_records"]
    index = next(
        index
        for index, record in enumerate(records)
        if record.lane is LaneEnum.OPERATIONAL
    )
    forged = replace(records[index], lane=LaneEnum.EVALUATION)
    changed = (*records[:index], forged, *records[index + 1 :])
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="metadata/observation",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": changed}
        )


def test_claimed_work_vector_is_not_a_source_of_native_records() -> None:
    *_prefix, kwargs = _chain()
    claimed = kwargs["claimed_work_vector"]
    forged = WorkVectorV1(
        claimed.counter_registry_id,
        _id("self-filled-other-subject"),
        claimed.route_kind,
        claimed.records,
    )
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="differs from native-record recomputation",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "claimed_work_vector": forged}
        )


def test_result_self_filled_comparison_is_recomputed_and_rejected() -> None:
    *_prefix, kwargs = _chain()
    claimed = kwargs["claimed_comparison_vector"]
    values = dict(claimed.values)
    values["nonkernel_compute_events"] += 1
    forged = ComparisonVectorV1(
        claimed.comparison_profile_id,
        claimed.work_vector_id,
        claimed.subject_id,
        claimed.route_kind,
        tuple((axis, values[axis]) for axis in SHARED_AXES),
    )
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="actual-projection recomputation",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "claimed_comparison_vector": forged}
        )


def test_reconciliation_and_stage_exclusivity_are_replayed_from_records() -> None:
    *_prefix, kwargs = _chain()
    records = kwargs["native_counter_records"]
    by_path = {record.path: index for index, record in enumerate(records)}

    index = by_path["route.attempts"]
    bad = replace(records[index], value=2)
    changed = (*records[:index], bad, *records[index + 1 :])
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="reconciliation failed",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": changed}
        )

    index = by_path["local.causal_candidate_evaluations"]
    bad = replace(records[index], value=1)
    changed = (*records[:index], bad, *records[index + 1 :])
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match="stage-family exclusivity",
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{**kwargs, "native_counter_records": changed}
        )


def test_each_direct_fallback_forbidden_required_path_rejects_positive_value() -> None:
    *_prefix, kwargs = _chain()
    result = verifier_v6.verify_construction_accounting_semantics_v6(**kwargs)
    assert len(result.forbidden_required_zero_paths) == 178
    records = kwargs["native_counter_records"]
    by_path = {record.path: index for index, record in enumerate(records)}

    for path in result.forbidden_required_zero_paths:
        index = by_path[path]
        changed = (
            *records[:index],
            replace(records[index], value=1),
            *records[index + 1 :],
        )
        with pytest.raises(
            verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
            match="stage-family exclusivity",
        ):
            verifier_v6.verify_construction_accounting_semantics_v6(
                **{**kwargs, "native_counter_records": changed}
            )


def test_every_direct_fallback_allowed_path_can_be_positive_together() -> None:
    registry, stage, *_rest = _profiles()
    allowed = stage.by_stage[
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    ].allowed_nonzero_paths
    values = {path: 0 for path in registry.required_paths}
    values.update({path: 1 for path in allowed})
    values.update(
        {
            "process.launches": 2,
            "route.attempts": 2,
            "solver.attempts": 2,
        }
    )
    *_prefix, kwargs = _chain(values=values)
    result = verifier_v6.verify_construction_accounting_semantics_v6(**kwargs)
    assert all(result.work_vector.values[path] > 0 for path in allowed)
    assert len(result.forbidden_required_zero_paths) == 178
    assert len(result.forbidden_operational_zero_paths) == 166


def test_rebuild_accepts_its_exact_three_common_paths() -> None:
    registry, *_rest = _profiles()
    values = {path: 0 for path in registry.required_paths}
    common_paths = (
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
    )
    values.update({path: 1 for path in common_paths})
    values.update(
        {
            "rebuild.ground_steps": 1,
            "rebuild.outcome_rows": 1,
            "rebuild.partition_candidate_evaluations": 1,
        }
    )
    *_prefix, kwargs = _chain(
        route_kind=RouteKindEnum.REBUILD,
        stage_kind=registry_v6.ConstructionStageKindV6.REBUILD,
        values=values,
    )
    result = verifier_v6.verify_construction_accounting_semantics_v6(**kwargs)
    assert all(result.work_vector.values[path] == 1 for path in common_paths)


@pytest.mark.parametrize(
    ("route_kind", "stage_kind", "message"),
    (
        (
            RouteKindEnum.DIRECT_FALLBACK,
            registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
            "not an accepted exact pair",
        ),
        (
            RouteKindEnum.REBUILD,
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
            "not an accepted exact pair",
        ),
        (
            RouteKindEnum.DIRECT_FALLBACK,
            "NOT_A_STAGE",
            "construction stage kind is not registered",
        ),
    ),
)
def test_wrong_stage_kind_or_route_stage_pair_is_rejected(
    route_kind,
    stage_kind,
    message,
) -> None:
    *_prefix, kwargs = _chain()
    with pytest.raises(
        verifier_v6.ConstructionAccountingSemanticVerificationV6Error,
        match=message,
    ):
        verifier_v6.verify_construction_accounting_semantics_v6(
            **{
                **kwargs,
                "expected_route_kind": route_kind,
                "expected_stage_kind": stage_kind,
            }
        )
