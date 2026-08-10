from __future__ import annotations

from collections import Counter

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_causal_promotion_operation_boundary_manifest_v4 as v4
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as v3


def test_open_stage_successor_changes_only_43_native_zero_classifications() -> None:
    before = v3.official_k7_root_cap_operation_boundary_manifest_v3()
    after = v4.official_k7_causal_promotion_operation_boundary_manifest_v4()
    changed = tuple(
        (left, right)
        for left, right in zip(before.boundaries, after.boundaries)
        if left.classification is not right.classification
    )
    assert len(changed) == v4.EXPECTED_RECLASSIFIED_BOUNDARY_COUNT == 43
    assert all(left.stage in v4.OPEN_STAGES for left, _right in changed)
    assert all(
        left.classification
        is v3.OperationBoundaryClassificationV3.OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
        and right.classification in v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
        and right.predecessor_boundary_id == left.boundary_id
        and right.boundary_key == left.boundary_key
        and right.dispatch_key == left.dispatch_key
        and right.target_path == left.target_path
        for left, right in changed
    )
    assert all(
        right.predecessor_boundary_id == left.boundary_id
        and right.classification is left.classification
        and right.boundary_key == left.boundary_key
        and right.dispatch_key == left.dispatch_key
        and right.target_path == left.target_path
        for left, right in zip(before.boundaries, after.boundaries)
        if left.stage not in v4.OPEN_STAGES
    )


def test_causal_manifest_has_seven_stage_kinds_and_no_runtime_claim() -> None:
    frozen = v4.official_k7_causal_promotion_operation_boundary_manifest_v4()
    document = frozen.to_document()
    assert tuple(document["stage_kinds"]) == tuple(
        item.value for item in v4.CAUSAL_PROMOTION_STAGE_KINDS
    )
    assert document["repeatable_stage_kinds"] == [
        "OPEN_CHECKPOINT_REPLANNING",
        "OPEN_INCREMENTAL_ACQUISITION",
    ]
    assert document["registered_terminal_code"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert document["runtime_emitters_installed"] is False
    assert document["counter_records_issued"] == 0
    assert document["official_execution_allowed"] is False


def test_every_open_dispatch_is_unique_and_bound_to_v6_stage_profile() -> None:
    frozen = v4.official_k7_causal_promotion_operation_boundary_manifest_v4()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    rows = tuple(
        row
        for row in frozen.boundaries
        if row.stage in v4.OPEN_STAGES
        and row.classification in v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
    )
    assert len(rows) == 43
    assert len({(row.stage, row.dispatch_key) for row in rows}) == len(rows)
    assert Counter(row.stage.value for row in rows) == {
        "OPEN_INCREMENTAL_ACQUISITION": 9,
        "OPEN_CHECKPOINT_REPLANNING": 34,
    }
    assert all(
        row.target_path in stage.by_stage[row.stage].allowed_nonzero_paths
        and row.registered_owner == registry.by_path[row.target_path].owner
        for row in rows
    )
