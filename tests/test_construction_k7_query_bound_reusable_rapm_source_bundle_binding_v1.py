from __future__ import annotations

import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_accounted_continuation_v1 as continuation_v1
from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_v1 as snapshot_v1
from acfqp import construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, loads_canonical_json


def test_domain_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundReusableRAPMSourceBundleBindingV1",
        "bind_query_bound_reusable_rapm_source_bundle_v1",
    }


def _retained_paths() -> tuple[Path, Path]:
    prereg = os.environ.get(
        "ACFQP_RETAINED_QUERY_BOUND_CAMPAIGN_PREREGISTRATION"
    )
    bundle = os.environ.get("ACFQP_RETAINED_QUERY_BOUND_COMPLETE_BUNDLE")
    if not prereg or not bundle:
        pytest.skip("set retained query-bound preregistration and bundle paths")
    prereg_path = Path(prereg)
    bundle_path = Path(bundle)
    if not prereg_path.is_file() or not bundle_path.is_dir():
        pytest.fail("retained query-bound preregistration or bundle is absent")
    return prereg_path, bundle_path


def _role_bytes(
    preregistration: dict,
    *,
    occurrence_id: str,
) -> dict[str, bytes]:
    rows = [
        row
        for row in preregistration["preregistered_occurrences"]
        if row["logical_occurrence_id"] == occurrence_id
    ]
    assert len(rows) == 1
    blobs = {
        row["campaign_input_blob_id"]: bytes.fromhex(
            row["canonical_json_bytes_hex"]
        )
        for row in preregistration["input_blobs"]
    }
    return {
        row["role"]: blobs[row["campaign_input_blob_id"]]
        for row in rows[0]["input_roles"]
    }


@pytest.fixture(scope="module")
def real_source_bundle_binding():
    prereg_path, bundle_path = _retained_paths()
    preregistration_bytes = prereg_path.read_bytes()
    preregistration = loads_canonical_json(preregistration_bytes)
    business = loads_canonical_json(
        (bundle_path / "BUSINESS_RESULT.json").read_bytes()
    )
    inputs = _role_bytes(
        preregistration,
        occurrence_id=business["occurrence_id"],
    )
    continuation = continuation_v1.run_query_bound_accounted_continuation_v1(
        source_trace_bytes=inputs["SOURCE_TRACE"],
        build_epoch_envelope_bytes=inputs["BUILD_EPOCH_ENVELOPE"],
        root_query_result_bytes=inputs["ROOT_QUERY_RESULT"],
        overlay_bytes=inputs["RECOVERY_OVERLAY"],
        request_bytes=inputs["RECOVERY_REQUEST"],
    )
    snapshot = snapshot_v1.freeze_query_bound_reusable_rapm_snapshot_v1(
        continuation.final_local_replanning
    )
    snapshot_bytes = canonical_json_bytes(snapshot.to_document())
    binding = subject.bind_query_bound_reusable_rapm_source_bundle_v1(
        preregistration_bytes=preregistration_bytes,
        bundle_directory=bundle_path,
        snapshot_bytes=snapshot_bytes,
    )
    return preregistration_bytes, bundle_path, snapshot_bytes, binding


def test_real_snapshot_binds_to_exact_registered_complete_bundle(
    real_source_bundle_binding,
) -> None:
    _preregistration, _bundle, _snapshot, binding = real_source_bundle_binding
    document = binding.to_document()
    assert document["occurrence_index"] == 1
    assert document["campaign_preregistration_exactly_replayed"] is True
    assert document["complete_accounting_bundle_exactly_replayed"] is True
    assert document["five_scientific_input_blobs_exactly_joined"] is True
    assert document["source_final_local_identity_joined"] is True
    assert document["source_occurrence_complete_bundle_binding_present"] is True
    assert document["snapshot_model_and_proof_typed_replay"] is True
    assert document["source_ground_transaction_bytes_in_bundle"] is False
    assert document["portable_source_ground_transaction_replay_performed"] is False
    assert document["source_numerical_model_identity_joined_to_bundle"] is False
    assert document["persistent_proof_dependency_dag_present"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["cumulative_local_ground_draw_count"] == 25_344


def test_binding_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error
    ):
        subject.QueryBoundReusableRAPMSourceBundleBindingV1(
            object(),
            *("0" * 64 for _ in range(3)),
            1,
            "0" * 64,
            (),
            "0" * 64,
            "0" * 64,
            (),
            *("0" * 64 for _ in range(11)),
            1,
        )
