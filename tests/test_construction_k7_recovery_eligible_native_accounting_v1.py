from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
from acfqp import construction_k7_recovery_eligible_accounting_manifest_v1 as manifest_v1
from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
from acfqp import construction_k7_recovery_eligible_native_accounting_v1 as subject
from acfqp import construction_k7_recovery_eligible_stage_accounting_v1 as stage_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_manifest_and_public_surface_are_additive() -> None:
    assert (
        subject.LOCAL_DOMAINS
        | stage_v1.LOCAL_DOMAINS
        | manifest_v1.LOCAL_DOMAINS
    ) <= PHASE3E_DOMAIN_TAGS
    manifest = manifest_v1.official_recovery_eligible_accounting_manifest_v1()
    document = manifest.to_document()
    assert len(manifest.boundaries) == 53
    assert document["stage_plan"] == [
        "OPEN_INCREMENTAL_ACQUISITION",
        "OPEN_CHECKPOINT_REPLANNING",
        "DIRECT_FALLBACK",
    ]
    assert document["open_boundary_count"] == 46
    assert document["direct_fallback_boundary_count"] == 7
    assert document["nine_shared_resource_receipts_present"] is False
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleNativeAccountingV1Error",
        "LOCAL_DOMAINS",
        "RecoveryEligibleNativeAccountedOccurrenceV1",
        "execute_recovery_eligible_native_accounted_occurrence_v1",
        "verify_recovery_eligible_native_accounting_v1",
    }


@pytest.fixture(scope="module")
def real_accounted_occurrence():
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    real = os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") == "1"
    if not retained or not real:
        pytest.skip("real recovery-eligible native accounting is disabled")
    root = Path(retained)
    cache = cache_v1.materialize_query_bound_persistent_proof_cache_bytes_v1(
        binding_bytes=(root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(root / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
    )
    checkpoint = checkpoint_v1.materialize_recovery_eligible_checkpoint_fixture_v1(
        canonical_json_bytes(cache.to_document())
    )
    query = checkpoint_v1.freeze_recovery_eligible_checkpoint_query_v1(
        checkpoint,
        logical_occurrence_id=_fresh_id("recovery-native-accounting-occurrence-1"),
        query_ordinal=3,
    )
    consumption = checkpoint_v1.consume_recovery_eligible_checkpoint_v1(
        checkpoint, query
    )
    request = checkpoint_v1.prepare_recovery_eligible_recovery_request_v1(
        checkpoint, consumption
    )
    return subject.execute_recovery_eligible_native_accounted_occurrence_v1(request)


def test_real_three_stage_native_chain_is_exact(real_accounted_occurrence) -> None:
    result = subject.verify_recovery_eligible_native_accounting_v1(
        real_accounted_occurrence
    )
    document = result.to_document()
    assert document["stage_count"] == 3
    assert document["stage_counter_record_counts"] == [202, 202, 202]
    assert document["local_ground_draw_count"] == 12_672
    assert document["changed_abstract_row_count"] == 6
    assert document["fallback_ground_step_count"] == 96
    assert document["terminal_class"] == "PLAN_CERTIFICATE"
    assert document["terminal_code"] == "FULL_GROUND_FALLBACK"
    assert document["nine_shared_resource_receipts_present"] is False
    assert document["route_family_occurrence_vectors_issued"] is False


def test_real_native_values_join_scientific_work(real_accounted_occurrence) -> None:
    acquisition, replanning, fallback = (
        row.work_vector.values
        for row in real_accounted_occurrence.stage_accounting.recorded_stages
    )
    assert acquisition["acquisition.incremental_engine_ground_draws"] == 12_672
    assert acquisition["acquisition.incremental_signed_batches_committed"] == 12
    assert acquisition["acquisition.incremental_support_freezes"] == 6
    assert replanning["build.open_checkpoint_model_rows_built"] == 6
    assert replanning["build.open_checkpoint_batch_v2_frontier_obligations_built"] == 7
    assert fallback["control.cap_checks"] == 420
    assert fallback["fallback.states_expanded"] == 30
    assert fallback["fallback.actions_evaluated"] == 96
    assert fallback["fallback.outcome_rows"] == 1_440
    assert fallback["fallback.bellman_backups"] == 102


def test_all_shared_paths_remain_explicit_stage_placeholders(
    real_accounted_occurrence,
) -> None:
    for row in real_accounted_occurrence.stage_accounting.recorded_stages:
        assert all(
            row.work_vector.values[path] == 0
            for path in stage_v1.SHARED_RESOURCE_PATHS
        )
        assert len(row.actual_projection_proof.to_document()) > 0


def test_stage_result_rejects_crossed_output_binding(real_accounted_occurrence) -> None:
    result = real_accounted_occurrence.stage_accounting
    crossed = object.__new__(stage_v1.RecoveryEligibleStageAccountingResultV1)
    for name in result.__slots__:
        object.__setattr__(crossed, name, getattr(result, name))
    bindings = list(result.stage_output_bindings)
    bindings[1] = (("WORLD_MODEL_LOOP", result.stage_output_bindings[0][0][1]),)
    object.__setattr__(crossed, "stage_output_bindings", tuple(bindings))
    forged = object.__new__(subject.RecoveryEligibleNativeAccountedOccurrenceV1)
    for name in real_accounted_occurrence.__slots__:
        object.__setattr__(forged, name, getattr(real_accounted_occurrence, name))
    object.__setattr__(forged, "stage_accounting", crossed)
    with pytest.raises(subject.ConstructionK7RecoveryEligibleNativeAccountingV1Error):
        subject.verify_recovery_eligible_native_accounting_v1(forged)
