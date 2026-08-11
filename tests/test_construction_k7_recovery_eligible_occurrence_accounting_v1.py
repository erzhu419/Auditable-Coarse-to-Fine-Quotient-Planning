from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_k7_recovery_eligible_occurrence_accounting_v1 as subject
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 6
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error",
        "LOCAL_DOMAINS",
        "RecoveryEligibleOccurrenceAccountingBundleV1",
        "RecoveryEligibleOutputCommitV1",
        "RecoveryEligibleOutputRoleCommitV1",
        "RecoveryEligiblePathAggregationV1",
        "RecoveryEligibleSharedResourceReceiptSetV1",
        "RecoveryEligibleSharedResourceReceiptV1",
        "finalize_recovery_eligible_occurrence_accounting_v1",
        "run_recovery_eligible_occurrence_accounting_v1",
        "verify_recovery_eligible_occurrence_accounting_v1",
    }


@pytest.fixture(scope="module")
def real_occurrence_bundle(tmp_path_factory):
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    if (
        os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") != "1"
        or not retained
    ):
        pytest.skip("real recovery occurrence accounting is disabled")
    retained_root = Path(retained)
    root = tmp_path_factory.mktemp("recovery-occurrence-accounting")
    output = root / "output"
    bundle = subject.run_recovery_eligible_occurrence_accounting_v1(
        repository_root=Path(__file__).parents[1],
        runtime_cas_root=root / "cas",
        output_directory=output,
        binding_bytes=(retained_root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(retained_root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(
            retained_root / "PROOF_DEPENDENCY_TRANSITION.json"
        ).read_bytes(),
        logical_occurrence_id=_fresh_id("recovery-accounted-occurrence-1"),
        query_ordinal=5,
        timeout_seconds=7_200,
    )
    return bundle, output


def test_real_nine_receipts_and_three_formal_chains_close(
    real_occurrence_bundle,
) -> None:
    bundle, output = real_occurrence_bundle
    verified = subject.verify_recovery_eligible_occurrence_accounting_v1(bundle)
    document = verified.to_document()
    assert tuple(row.path for row in bundle.receipt_set.receipts) == (
        shared_v1.SHARED_RESOURCE_PATHS
    )
    assert all(row.value > 0 for row in bundle.receipt_set.receipts)
    assert len(bundle.work_vectors) == 3
    assert all(len(row.records) == 202 for row in bundle.work_vectors)
    assert len(bundle.comparison_vectors) == 3
    assert all(row.projection_term_count == 182 for row in bundle.actual_projection_proofs)
    assert document["shared_resource_receipts_complete"] is True
    assert document["three_complete_202_counter_record_chains_present"] is True
    assert document["logical_occurrence_campaign_closed"] is False
    assert len(tuple(output.glob("*.json"))) == 8


def test_real_route_family_exclusivity_and_native_values_are_preserved(
    real_occurrence_bundle,
) -> None:
    bundle, _output = real_occurrence_bundle
    wrapper, local, fallback = bundle.work_vectors
    assert wrapper.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
    assert local.route_kind is RouteKindEnum.LOCAL_ATTEMPT
    assert fallback.route_kind is RouteKindEnum.DIRECT_FALLBACK
    assert local.values["acquisition.incremental_engine_ground_draws"] == 12_672
    assert local.values["build.open_checkpoint_model_rows_built"] == 6
    assert fallback.values["fallback.states_expanded"] == 30
    assert fallback.values["fallback.actions_evaluated"] == 96
    assert fallback.values["fallback.ground_steps"] == 96
    assert fallback.values["fallback.outcome_rows"] == 1_440
    assert fallback.values["fallback.bellman_backups"] == 102
    assert fallback.values["control.cap_checks"] == 420
    assert all(value == 0 for path, value in local.values.items() if path.startswith("fallback."))
    assert all(
        value == 0
        for path, value in fallback.values.items()
        if path.startswith(("acquisition.", "build.", "local."))
    )
    assert wrapper.values["process.launches"] == 1
    assert wrapper.values["io.output_bytes"] == bundle.fixed_point.output_bytes


def test_real_output_fixed_point_and_occurrence_vector_reconcile(
    real_occurrence_bundle,
) -> None:
    bundle, output = real_occurrence_bundle
    assert bundle.output_commit.output_bytes == sum(
        path.stat().st_size for path in output.glob("*.json")
    )
    assert bundle.output_commit.output_bytes == bundle.fixed_point.output_bytes
    assert bundle.work_vectors[0].values["io.mounted_bytes_peak"] == max(
        bundle.supervised_execution.measurement.pre_output_mounted_bytes_peak,
        bundle.fixed_point.output_bytes,
    )
    assert tuple(axis for axis, _value in bundle.occurrence_comparison_values) == (
        "kernel_transition_calls",
        "nonkernel_compute_events",
        "output_bytes",
        "peak_mounted_bytes",
        "peak_working_bytes",
        "process_launches",
        "read_bytes",
        "staged_bytes",
    )


def test_bundle_verifier_rejects_crossed_aggregation(real_occurrence_bundle) -> None:
    bundle, _output = real_occurrence_bundle
    row = bundle.path_aggregations[0]
    original = row.value
    try:
        object.__setattr__(row, "value", original + 1)
        with pytest.raises(
            subject.ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error
        ):
            subject.verify_recovery_eligible_occurrence_accounting_v1(bundle)
    finally:
        object.__setattr__(row, "value", original)


def test_bundle_type_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error
    ):
        subject.verify_recovery_eligible_occurrence_accounting_v1(object())  # type: ignore[arg-type]
