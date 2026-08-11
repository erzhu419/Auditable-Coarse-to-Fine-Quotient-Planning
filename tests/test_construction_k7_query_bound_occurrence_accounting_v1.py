from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import tempfile

import pytest

from acfqp import construction_k7_query_bound_occurrence_accounting_v1 as subject
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as independent
from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-occurrence-accounting-test:v1\x00"
        + label.encode()
    ).hexdigest()


def test_public_surface_freezes_the_nine_receipt_boundary() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundOccurrenceAccountingV1Error",
        "EXPECTED_REQUIRED_PATH_COUNT",
        "EXPECTED_SHARED_PATH_COUNT",
        "PRE_OUTPUT_SHARED_PATHS",
        "QueryBoundOccurrenceAccountingBundleV1",
        "QueryBoundOutputCommitV1",
        "QueryBoundOutputRoleCommitV1",
        "QueryBoundPathAggregationV1",
        "QueryBoundSharedResourceReceiptSetV1",
        "QueryBoundSharedResourceReceiptV1",
        "SHARED_PATHS",
        "finalize_query_bound_occurrence_accounting_v1",
        "run_query_bound_occurrence_accounting_v1",
        "verify_query_bound_occurrence_accounting_v1",
    }
    assert subject.EXPECTED_SHARED_PATH_COUNT == len(subject.SHARED_PATHS) == 9
    assert subject.EXPECTED_REQUIRED_PATH_COUNT == 202


def test_occurrence_bundle_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundOccurrenceAccountingV1Error):
        subject.verify_query_bound_occurrence_accounting_v1(object())  # type: ignore[arg-type]


def test_local_recovery_prefixes_are_not_charged_to_the_common_wrapper() -> None:
    assert subject._LOCAL_RECOVERY_PATH_PREFIXES == (
        "local.",
        "acquisition.",
        "build.",
    )


@pytest.fixture(scope="module")
def real_occurrence_accounting():
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_OCCURRENCE") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_OCCURRENCE=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if not retained:
        pytest.fail("ACFQP_CAUSAL_RECOVERY_TRACE must name the retained real trace")
    repository_root = Path(__file__).parents[1]
    trace_raw = Path(retained).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-formal-occurrence"),
        query_ordinal=0,
    )
    root = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=query,
    )
    root_bytes = canonical_json_bytes(root.to_document())
    overlay = overlay_v1.apply_query_bound_cached_recovery_overlay_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
    )
    overlay_bytes = canonical_json_bytes(overlay.to_document())
    request = request_v1.prepare_query_bound_recovery_request_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
    )
    with tempfile.TemporaryDirectory(prefix="acfqp-qb-occurrence-", dir="/tmp") as temporary:
        temporary_root = Path(temporary)
        output = temporary_root / "output"
        bundle = subject.run_query_bound_occurrence_accounting_v1(
            repository_root=repository_root,
            runtime_cas_root=temporary_root / "cas",
            output_directory=output,
            source_trace_bytes=trace_raw,
            build_epoch_envelope_bytes=envelope_bytes,
            root_query_result_bytes=root_bytes,
            overlay_bytes=overlay_bytes,
            request_bytes=canonical_json_bytes(request.to_document()),
        )
        yield bundle, output


def test_real_occurrence_closes_receipts_vectors_and_output_fixed_point(
    real_occurrence_accounting,
) -> None:
    bundle, output = real_occurrence_accounting
    result = subject.verify_query_bound_occurrence_accounting_v1(bundle)
    assert len(result.receipt_set.receipts) == 9
    assert tuple(row.path for row in result.receipt_set.receipts) == subject.SHARED_PATHS
    assert all(row.value > 0 for row in result.receipt_set.receipts)
    assert tuple(row.route_kind.value for row in result.work_vectors) == (
        "ABSTRACT_FAILED_PREFIX",
        "LOCAL_ATTEMPT",
        "DIRECT_FALLBACK",
    )
    assert all(len(row.records) == 202 for row in result.work_vectors)
    assert len(result.path_aggregations) == 202
    assert all(row.projection_term_count == 182 for row in result.actual_projection_proofs)
    wrapper, local, fallback = result.work_vectors
    assert wrapper.values["io.output_bytes"] == result.fixed_point.output_bytes
    assert wrapper.values["process.launches"] == 1
    assert wrapper.values["process.exit_successes"] == 1
    assert wrapper.values["process.exit_failures"] == 0
    assert wrapper.values["acquisition.incremental_engine_ground_draws"] == 0
    assert local.values["acquisition.incremental_engine_ground_draws"] == 25_344
    assert local.values["build.open_checkpoint_model_rows_built"] == 12
    assert all(
        value == 0
        for path, value in local.values.items()
        if path.startswith("fallback.")
    )
    assert fallback.values["fallback.states_expanded"] == 30
    assert fallback.values["fallback.actions_evaluated"] == 96
    assert fallback.values["fallback.ground_steps"] == 96
    assert fallback.values["fallback.outcome_rows"] == 1_440
    assert fallback.values["fallback.bellman_backups"] == 102
    assert tuple(sorted(path.name for path in output.iterdir())) == tuple(
        sorted(
            f"{role}.json"
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        )
    )
    assert sum(path.stat().st_size for path in output.iterdir()) == result.fixed_point.output_bytes
    document = result.to_document()
    assert document["shared_resource_receipts_complete"] is True
    assert document["three_complete_202_counter_record_chains_present"] is True
    assert document["all_182_operational_leaves_projected_exactly_once_per_component"] is True
    assert document["route_family_exclusivity_preserved"] is True
    assert document["marginal_route_upper_compliance_authority"] is False
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["workload_economics_gate_status"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_real_occurrence_bytes_replay_independently(
    real_occurrence_accounting,
) -> None:
    _bundle, output = real_occurrence_accounting
    verification = independent.verify_query_bound_complete_bundle_directory_v1(output)
    document = verification.to_document()
    assert document["occurrence_id"] == verification.occurrence_id
    assert document["five_stage_event_chains_replayed"] is True
    assert document["nine_shared_resource_receipts_replayed"] is True
    assert document["three_route_exclusive_202_record_vectors_replayed"] is True
    assert document["three_182_term_projections_recomputed"] is True
    assert document["output_fixed_point_replayed"] is True
    assert document["producer_modules_imported"] is False
    assert document["upstream_scientific_identity_chain_joined"] is True
    assert document["scientific_planner_recomputed_by_this_verifier"] is False
    assert document["source_bytes_embedded_or_externally_anchored"] is False
    assert document["accounting_bundle_semantics_only"] is True
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["workload_economics_gate_status"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_independent_replay_rejects_role_tampering(
    real_occurrence_accounting,
    tmp_path: Path,
) -> None:
    _bundle, output = real_occurrence_accounting
    attacked = tmp_path / "attacked"
    shutil.copytree(output, attacked)
    role = attacked / "TERMINAL_ARTIFACT.json"
    original_role_raw = role.read_bytes()
    document = loads_canonical_json(role.read_bytes())
    document["terminal_code"] = "X" * len(document["terminal_code"])
    forged_role_raw = canonical_json_bytes(document)
    assert len(forged_role_raw) == len(original_role_raw)
    role.write_bytes(forged_role_raw)
    role.chmod(0o600)
    manifest_path = attacked / "OUTPUT_MANIFEST.json"
    manifest = loads_canonical_json(manifest_path.read_bytes())
    row = next(
        item
        for item in manifest["ordered_preceding_roles"]
        if item["artifact_role"] == "TERMINAL_ARTIFACT"
    )
    row["bytes_sha256"] = hashlib.sha256(forged_role_raw).hexdigest()
    forged_manifest_raw = canonical_json_bytes(manifest)
    assert len(forged_manifest_raw) == manifest_path.stat().st_size
    manifest_path.write_bytes(forged_manifest_raw)
    manifest_path.chmod(0o600)
    with pytest.raises(
        independent.ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error
    ):
        independent.verify_query_bound_complete_bundle_directory_v1(attacked)
