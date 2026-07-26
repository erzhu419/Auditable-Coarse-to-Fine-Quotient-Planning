"""V0-055 durable two-generation action-local recovery regressions."""

from __future__ import annotations

import copy
from dataclasses import fields, replace
from fractions import Fraction
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable

import pytest

import acfqp.h2_action_indexed_proof_dag_v1 as dag
import acfqp.h2_action_local_semantic_switch_v1 as action_local
import acfqp.h2_durable_action_local_recovery_v1 as recovery
import acfqp.h2_durable_action_local_recovery_pins_v1 as pins
import acfqp.h2_durable_action_switch_transport_v1 as transport
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.phase3e_ids import Phase3EIdentityError, canonical_json_bytes


RecoveryViolation = recovery.DurableActionLocalRecoveryInvariantViolation
TransportViolation = transport.DurableActionSwitchInvariantViolation
ANY_V0055_VIOLATION = (
    RecoveryViolation,
    TransportViolation,
    Phase3EIdentityError,
)


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    root = tmp_path_factory.mktemp("v0055-campaign") / "store"
    result = recovery.run_registered_h2_durable_action_local_recovery_v1(root)
    return root, result


def _unsafe_exact_clone(instance: Any, **changes: Any) -> Any:
    """Create an exact-class negative control without running post-init."""

    clone = object.__new__(type(instance))
    for item in fields(instance):
        object.__setattr__(
            clone,
            item.name,
            changes.get(item.name, getattr(instance, item.name)),
        )
    return clone


def _clone_store(
    campaign,
    tmp_path: Path,
    name: str,
) -> tuple[Path, recovery.DurableActionLocalRecoveryResultV1]:
    source, result = campaign
    target = tmp_path / name
    shutil.copytree(source, target)
    return target, result


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _write_canonical(path: Path, document: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(document))


def _checkpoint_paths(
    store: Path,
    checkpoint: str,
    result: recovery.DurableActionLocalRecoveryResultV1,
) -> tuple[Path, Path, Path]:
    if checkpoint == "c1":
        payload_id = result.c1_payload_id
        commit_id = result.c1_commit_id
    elif checkpoint == "c2":
        payload_id = result.c2_payload_id
        commit_id = result.c2_commit_id
    else:  # pragma: no cover - test helper guard
        raise AssertionError(checkpoint)
    commit_path = store / checkpoint / "commits" / f"{commit_id}.json"
    commit = _read_json(commit_path)
    return (
        store / checkpoint / "blobs" / f"{payload_id}.json",
        store / checkpoint / "blobs" / f"{commit['manifest_id']}.json",
        commit_path,
    )


def _load_checkpoint(
    store: Path,
    checkpoint: str,
    result: recovery.DurableActionLocalRecoveryResultV1,
) -> Any:
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        store / "c1",
        result.c1_commit_id,
    )
    if checkpoint == "c1":
        return c1
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        store / "overlay",
        result.overlay_projection_id,
    )
    return transport.load_verified_durable_action_switch_c2_v1(
        store / "c2",
        result.c2_commit_id,
        c1,
        projection,
    )


def _rehash_checkpoint(
    checkpoint_root: Path,
    *,
    kind: str,
    payload_mutator: Callable[[dict[str, Any]], None],
    manifest_mutator: Callable[[dict[str, Any]], None] | None = None,
    commit_mutator: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    """Fully re-address an outer checkpoint chain after a semantic attack."""

    commit_path = next((checkpoint_root / "commits").iterdir())
    commit = _read_json(commit_path)
    payload_path = (
        checkpoint_root / "blobs" / f"{commit['payload_id']}.json"
    )
    manifest_path = (
        checkpoint_root / "blobs" / f"{commit['manifest_id']}.json"
    )
    payload = _read_json(payload_path)
    manifest = _read_json(manifest_path)

    payload_mutator(payload)
    payload_role = "c1_payload" if kind == "c1" else "c2_payload"
    payload["payload_id"] = transport._content_id(
        payload_role,
        {key: value for key, value in payload.items() if key != "payload_id"},
    )
    payload_bytes = canonical_json_bytes(payload)

    manifest["payload_id"] = payload["payload_id"]
    manifest["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    manifest["payload_size_bytes"] = len(payload_bytes)
    if manifest_mutator is not None:
        manifest_mutator(manifest)
    manifest_role = "c1_manifest" if kind == "c1" else "c2_manifest"
    manifest["manifest_id"] = transport._content_id(
        manifest_role,
        {
            key: value
            for key, value in manifest.items()
            if key != "manifest_id"
        },
    )
    manifest_bytes = canonical_json_bytes(manifest)

    commit["payload_id"] = payload["payload_id"]
    commit["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    commit["payload_size_bytes"] = len(payload_bytes)
    commit["manifest_id"] = manifest["manifest_id"]
    commit["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    commit["manifest_size_bytes"] = len(manifest_bytes)
    if commit_mutator is not None:
        commit_mutator(commit)
    commit["commit_id"] = transport._content_id(
        "commit",
        {key: value for key, value in commit.items() if key != "commit_id"},
    )
    commit_bytes = canonical_json_bytes(commit)

    for path in (checkpoint_root / "blobs").iterdir():
        path.unlink()
    for path in (checkpoint_root / "commits").iterdir():
        path.unlink()
    _write_canonical(
        checkpoint_root / "blobs" / f"{payload['payload_id']}.json",
        payload,
    )
    _write_canonical(
        checkpoint_root / "blobs" / f"{manifest['manifest_id']}.json",
        manifest,
    )
    _write_canonical(
        checkpoint_root / "commits" / f"{commit['commit_id']}.json",
        commit,
    )
    return commit["commit_id"]


def _rehash_overlay(
    overlay_root: Path,
    mutator: Callable[[dict[str, Any]], None],
) -> str:
    path = next(overlay_root.iterdir())
    document = _read_json(path)
    mutator(document)
    document["projection_id"] = transport._content_id(
        "overlay",
        {
            key: value
            for key, value in document.items()
            if key != "projection_id"
        },
    )
    path.unlink()
    _write_canonical(
        overlay_root / f"{document['projection_id']}.json",
        document,
    )
    return document["projection_id"]


def _canonical_registry_observation(
    root: Path,
    result: recovery.DurableActionLocalRecoveryResultV1,
    report: recovery.DurableActionLocalRecoveryVerificationV1,
) -> dict[str, str]:
    observed = recovery._visible_canonical_result_ids(result)
    c1_commit = _read_json(
        root / "c1" / "commits" / f"{result.c1_commit_id}.json"
    )
    c2_commit = _read_json(
        root / "c2" / "commits" / f"{result.c2_commit_id}.json"
    )
    observed["c1_manifest"] = c1_commit["manifest_id"]
    observed["c2_manifest"] = c2_commit["manifest_id"]
    observed["evaluation_replay_report"] = report.report_id
    return observed


def test_public_api_is_narrow_and_sources_are_pinned() -> None:
    signature = inspect.signature(
        recovery.run_registered_h2_durable_action_local_recovery_v1
    )
    assert tuple(signature.parameters) == ("store_root",)
    assert recovery.CONTRACT_VERSION == "1.19.0"
    assert (
        recovery.PROFILE_KEY
        == "lmb_h2_two_generation_durable_action_local_recovery_v0"
    )
    assert recovery.EXPECTED_B_RUNNER_SOURCE_SHA256 == (
        pins.EXPECTED_B_RUNNER_SOURCE_SHA256
    )
    assert recovery.EXPECTED_B_MODULE_SHA256 == pins.EXPECTED_B_MODULE_SHA256
    assert recovery.EXPECTED_TRANSPORT_MODULE_SHA256 == (
        pins.EXPECTED_TRANSPORT_MODULE_SHA256
    )
    assert transport.EXPECTED_ACTION_INDEXED_SOURCE_SHA256 == (
        pins.EXPECTED_ACTION_INDEXED_SOURCE_SHA256
    )
    assert recovery._callable_sha256(recovery._CANONICAL_B_RUNNER) == (
        pins.EXPECTED_B_RUNNER_SOURCE_SHA256
    )
    assert recovery._module_sha256(action_local) == pins.EXPECTED_B_MODULE_SHA256
    assert recovery._module_sha256(transport) == (
        pins.EXPECTED_TRANSPORT_MODULE_SHA256
    )
    assert recovery._file_sha256(Path(recovery.__file__).resolve()) == (
        pins.EXPECTED_ORCHESTRATOR_MODULE_SHA256
    )
    assert transport._source_sha256(dag) == (
        pins.EXPECTED_ACTION_INDEXED_SOURCE_SHA256
    )
    assert all(
        len(value) == 64 and value != "0" * 64
        for value in (
            pins.EXPECTED_ACTION_INDEXED_SOURCE_SHA256,
            pins.EXPECTED_B_MODULE_SHA256,
            pins.EXPECTED_B_RUNNER_SOURCE_SHA256,
            pins.EXPECTED_ORCHESTRATOR_MODULE_SHA256,
            pins.EXPECTED_TRANSPORT_MODULE_SHA256,
        )
    )
    recovery._assert_source_pins()


def test_exact_success_chain_and_identity_binding(campaign) -> None:
    root, result = campaign
    assert root.is_dir()
    assert result.status == recovery.SUCCESS_STATUS
    assert result.trace.events == recovery.EXPECTED_EVENTS
    assert result.protocol.protocol_id == result.failed_verification.protocol_id
    assert result.c1_commit_id == result.p1_attestation.c1_commit_id
    assert (
        result.failed_verification.p1_attestation_id
        == result.p1_attestation.attestation_id
    )
    assert (
        result.ground_authorization.failed_verification_id
        == result.failed_verification.verification_id
    )
    assert result.source_result_id == result._source_result.result_id
    assert (
        result.source_result_id
        == result.p2_continuation.overlay_source_result_id
    )
    assert result.overlay_projection_id == result.p2_continuation.overlay_projection_id
    assert result.c2_commit_id == result.p3_attestation.c2_commit_id
    assert (
        result.trace.p3_attestation_id
        == result.p3_attestation.attestation_id
    )
    assert len(result.result_id) == 64
    assert recovery.require_durable_action_local_recovery_result_v1(result) is result


def test_root_free_c1_c2_and_exact_two_generation_partition(campaign) -> None:
    root, result = campaign
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        root / "c1", result.c1_commit_id
    )
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        root / "overlay", result.overlay_projection_id
    )
    c2 = transport.load_verified_durable_action_switch_c2_v1(
        root / "c2",
        result.c2_commit_id,
        c1,
        projection,
    )

    assert c1.commit.generation == 1
    assert c1.commit.previous_commit_id is None
    assert c1.payload.lower_entry_count == 18
    assert c1.payload.persisted_root_artifact_count == 0
    assert c1.payload.cached_root_entry_count == 0
    assert len(c1.payload.lower_node_documents) == 18
    assert {
        row["schema"] for row in c1.payload.lower_node_documents
    } == {"acfqp.action_indexed_proof_node.v1"}

    assert c2.commit.generation == 2
    assert c2.commit.previous_commit_id == c1.commit.commit_id
    assert c2.payload.full_cache_entry_count == 28
    assert c2.payload.active_final_entry_count == 18
    assert c2.payload.cached_root_entry_count == 0
    assert len(c2.payload.lower_node_documents) == 28
    assert {
        row["schema"] for row in c2.payload.lower_node_documents
    } == {"acfqp.action_indexed_proof_node.v1"}

    first_active = set(c1.payload.active_lower_node_ids)
    final_active = {
        node_id for _address, _key_id, node_id in c2.payload.active_final_bindings
    }
    union = set(c2.payload.full_cache_node_ids)
    assert len(first_active & final_active) == 8
    assert len(first_active - final_active) == 10
    assert len(final_active - first_active) == 10
    assert union - final_active == first_active - final_active


def test_exact_model_only_and_ground_work_lanes(campaign) -> None:
    _root, result = campaign
    p1 = result.p1_attestation
    p2 = result.p2_continuation
    p3 = result.p3_attestation

    assert (
        p1.selected_action,
        p1.normalized_regret,
        p1.certified,
    ) == ("N", Fraction(3, 4), False)
    assert (p1.lower_computed, p1.lower_reused, p1.fresh_roots) == (0, 18, 3)
    assert (
        p1.warm_replay.semantic_validation_lower_obligations,
        p1.warm_replay.operational_lower_computes,
        p1.warm_replay.operational_lower_hits,
        p1.warm_replay.roots_loaded,
        p1.warm_replay.fresh_root_computes,
    ) == (18, 0, 18, 0, 3)
    assert not hasattr(
        p1.warm_replay,
        "semantic_validation_lower_computes",
    )
    assert p1.matching_buffer_imported is False
    assert p1.ground_transition_calls == 0

    assert (
        p2.first_action,
        p2.final_action,
        p2.first_certified,
        p2.final_certified,
    ) == ("N", "M", False, True)
    assert (
        p2.source_first_execution_lower_computed,
        p2.source_first_execution_lower_reused,
        p2.semantic_validation_first_lower_obligations,
        p2.operational_first_lower_computes,
        p2.operational_first_lower_hits,
        p2.final_lower_computed,
        p2.final_lower_reused,
    ) == (18, 0, 18, 0, 18, 10, 8)
    assert not hasattr(
        p2,
        "semantic_validation_first_lower_computes",
    )
    assert p2.final_execution_document["work"]["fresh_root_computed"] == 3
    assert p2.matching_buffer_imported is False
    assert p2.worker_ground_transition_calls == 0

    assert (p3.selected_action, p3.final_certified) == ("M", True)
    assert (
        p3.warm_replay.semantic_validation_lower_obligations,
        p3.warm_replay.operational_lower_computes,
        p3.warm_replay.operational_lower_hits,
        p3.warm_replay.roots_loaded,
        p3.warm_replay.fresh_root_computes,
    ) == (18, 0, 18, 0, 3)
    assert not hasattr(
        p3.warm_replay,
        "semantic_validation_lower_computes",
    )
    assert p3.matching_buffer_imported is False
    assert p3.ground_transition_calls == 0

    assert (
        result.trace.preground_transition_calls,
        result.trace.operational_ground_transition_calls,
        result.trace.model_only_worker_ground_transition_calls,
        result.trace.process_launches,
    ) == (0, 1, 0, 3)
    assert result._source_result.access_trace.total_ground_transition_calls == 1
    assert result.claim_locks.native_compute_event_accounting_claimed is False


def test_p1_p3_restore_deserialized_nodes_and_build_roots_after_restore(
    campaign,
) -> None:
    root, result = campaign
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        root / "c1", result.c1_commit_id
    )
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        root / "overlay", result.overlay_projection_id
    )
    c2 = transport.load_verified_durable_action_switch_c2_v1(
        root / "c2", result.c2_commit_id, c1, projection
    )

    assert tuple(
        item.to_document() for item in c1.stored_lower_nodes
    ) == tuple(c1.payload.lower_node_documents)
    assert all(
        stored is not semantic
        for stored, semantic in zip(
            c1.stored_lower_nodes,
            c1.first_execution.nodes,
        )
    )
    assert tuple(
        item.to_document() for item in c2.stored_lower_nodes
    ) == tuple(c2.payload.lower_node_documents)

    first_runtime, first_restore = (
        dag.restore_verified_action_indexed_first_lower_graph_v1(
            c1.first_model,
            c1.query,
            c1.stored_lower_nodes,
            c1.first_execution.execution_id,
        )
    )
    assert all(
        first_runtime._cache[node.node_key_id] is node
        for node in c1.stored_lower_nodes
    )
    first_roots = dag.rebuild_action_indexed_roots_from_restored_runtime_v1(
        c1.first_model,
        c1.query,
        first_runtime,
        first_restore,
    )

    final_model = dag.registered_final_action_indexed_h2_model_v1()
    final_execution_id = c2.continuation.final_execution_document[
        "execution_id"
    ]
    final_runtime, final_restore = (
        dag.restore_verified_action_indexed_final_lower_graph_v1(
            final_model,
            c1.query,
            c2.stored_lower_nodes,
            c2.continuation.active_final_bindings,
            final_execution_id,
        )
    )
    final_by_id = {
        node.node_id: node for node in c2.stored_lower_nodes
    }
    assert all(
        final_runtime._cache[key_id] is final_by_id[node_id]
        for _address, key_id, node_id
        in c2.continuation.active_final_bindings
    )
    final_roots = dag.rebuild_action_indexed_roots_from_restored_runtime_v1(
        final_model,
        c1.query,
        final_runtime,
        final_restore,
    )

    p1 = transport._derive_p1(c1)
    p3 = transport._derive_c2_attestation(c2)
    assert (
        first_roots.lower_computed,
        first_roots.lower_reused,
        first_roots.roots_loaded,
        first_roots.fresh_root_computed,
    ) == (0, 18, 0, 3)
    assert (
        final_roots.lower_computed,
        final_roots.lower_reused,
        final_roots.roots_loaded,
        final_roots.fresh_root_computed,
    ) == (0, 18, 0, 3)
    assert p1.warm_replay.restore_binding_id == first_restore.restore_id
    assert p1.warm_replay.restored_root_replay_id == first_roots.replay_id
    assert p3.warm_replay.restore_binding_id == final_restore.restore_id
    assert p3.warm_replay.restored_root_replay_id == final_roots.replay_id


def test_store_topologies_are_exact_and_have_no_mutable_head(campaign) -> None:
    root, result = campaign
    assert {path.name for path in root.iterdir()} == {"c1", "overlay", "c2"}
    for checkpoint, commit_id in (
        ("c1", result.c1_commit_id),
        ("c2", result.c2_commit_id),
    ):
        checkpoint_root = root / checkpoint
        assert {path.name for path in checkpoint_root.iterdir()} == {
            "blobs",
            "commits",
        }
        assert {path.name for path in (checkpoint_root / "commits").iterdir()} == {
            f"{commit_id}.json"
        }
        assert not (checkpoint_root / "HEAD").exists()
    assert {path.name for path in (root / "overlay").iterdir()} == {
        f"{result.overlay_projection_id}.json"
    }


def test_fresh_verifier_bypasses_public_runner_and_preserves_store(
    campaign,
    monkeypatch,
) -> None:
    root, result = campaign

    def forbidden_public_runner(*_args, **_kwargs):
        raise AssertionError("verifier called public V0-055 runner")

    monkeypatch.setattr(
        recovery,
        "run_registered_h2_durable_action_local_recovery_v1",
        forbidden_public_runner,
    )
    report = recovery.verify_registered_h2_durable_action_local_recovery_v1(
        root, result
    )
    assert report.claimed_result_id == result.result_id
    assert report.replayed_result_id == result.result_id
    assert report.exact_document_match is True
    assert report.original_store_unchanged is True
    assert report.evaluation_lane_only is True
    assert report.included_in_operational_work is False
    assert report.same_implementation_replay is True
    assert report.independent_algorithm is False
    assert (
        report.evaluation_ground_transition_calls,
        report.evaluation_process_launches,
    ) == (1, 3)
    assert len(report.report_id) == 64
    assert (
        recovery.require_durable_action_local_recovery_verification_v1(report)
        is report
    )
    for copied in (copy.copy(report), replace(report)):
        with pytest.raises(RecoveryViolation):
            recovery.require_durable_action_local_recovery_verification_v1(
                copied
            )
    forged = recovery.DurableActionLocalRecoveryVerificationV1(
        result.result_id,
        result.result_id,
        True,
        True,
        True,
        False,
        True,
        False,
        1,
        3,
    )
    with pytest.raises(RecoveryViolation):
        recovery.require_durable_action_local_recovery_verification_v1(forged)
    with pytest.raises(RecoveryViolation):
        _ = forged.report_id


def test_two_clean_runs_and_verifiers_match_literal_canonical_registry(
    campaign,
    tmp_path,
) -> None:
    first_root, first = campaign
    first_report = (
        recovery.verify_registered_h2_durable_action_local_recovery_v1(
            first_root,
            first,
        )
    )
    second_root = tmp_path / "second-clean-store"
    second = recovery.run_registered_h2_durable_action_local_recovery_v1(
        second_root
    )
    second_report = (
        recovery.verify_registered_h2_durable_action_local_recovery_v1(
            second_root,
            second,
        )
    )

    first_observed = _canonical_registry_observation(
        first_root,
        first,
        first_report,
    )
    second_observed = _canonical_registry_observation(
        second_root,
        second,
        second_report,
    )
    expected_keys = {
        "protocol",
        "c1_payload",
        "c1_manifest",
        "c1_commit",
        "c1_snapshot",
        "p1_root_replay",
        "p1_attestation",
        "failed_proof_verification",
        "ground_authorization",
        "source_v0054b_result",
        "source_evidence_bundle",
        "source_overlay_build",
        "overlay_projection",
        "overlay_snapshot",
        "p2_continuation",
        "c2_payload",
        "c2_manifest",
        "c2_commit",
        "c2_snapshot",
        "p3_root_replay",
        "p3_attestation",
        "recovery_trace",
        "campaign_result",
        "evaluation_replay_report",
    }
    assert len(expected_keys) == 24
    assert set(pins.EXPECTED_CANONICAL_IDS) == expected_keys
    assert first_observed == pins.EXPECTED_CANONICAL_IDS
    assert second_observed == pins.EXPECTED_CANONICAL_IDS
    assert first_observed == second_observed
    assert first.to_document() == second.to_document()
    assert first_report.to_document() == second_report.to_document()


def test_result_is_owner_bound_and_claim_locks_fail_closed(campaign) -> None:
    _root, result = campaign
    for copied in (copy.copy(result), replace(result)):
        with pytest.raises(RecoveryViolation):
            recovery.require_durable_action_local_recovery_result_v1(copied)
    unbound = replace(result, _instance_mint=None)
    with pytest.raises(RecoveryViolation):
        recovery.require_durable_action_local_recovery_result_v1(unbound)
    with pytest.raises(RecoveryViolation):
        _ = unbound.result_id

    tampered = _unsafe_exact_clone(result, status="FORGED_SUCCESS")
    with pytest.raises(RecoveryViolation):
        recovery.require_durable_action_local_recovery_result_v1(tampered)

    with pytest.raises(RecoveryViolation):
        replace(
            result.claim_locks,
            generic_durable_persistence_claimed=True,
        )
    with pytest.raises(RecoveryViolation):
        replace(
            result.claim_locks,
            official_execution_allowed=True,
        )
    with pytest.raises(RecoveryViolation):
        replace(
            result.claim_locks,
            sample_efficiency_claimed=True,
        )
    with pytest.raises(RecoveryViolation):
        replace(
            result.claim_locks,
            native_compute_event_accounting_claimed=True,
        )


def test_fully_resigned_in_place_nested_regret_tamper_is_rejected(
    campaign,
) -> None:
    _root, result = campaign
    changes: list[tuple[Any, str, Any]] = []

    def mutate(target: Any, field_name: str, value: Any) -> None:
        changes.append((target, field_name, getattr(target, field_name)))
        object.__setattr__(target, field_name, value)

    try:
        mutate(result.p1_attestation, "normalized_regret", Fraction(0))
        resigned_p1_id = result.p1_attestation.attestation_id
        mutate(
            result.failed_verification,
            "p1_attestation_id",
            resigned_p1_id,
        )
        mutate(
            result.failed_verification,
            "normalized_regret",
            Fraction(0),
        )
        resigned_failed_id = result.failed_verification.verification_id
        mutate(
            result.ground_authorization,
            "failed_verification_id",
            resigned_failed_id,
        )
        mutate(
            result.ground_authorization,
            "p1_attestation_id",
            resigned_p1_id,
        )
        resigned_authorization_id = (
            result.ground_authorization.authorization_id
        )
        mutate(
            result.trace,
            "failed_verification_id",
            resigned_failed_id,
        )
        mutate(
            result.trace,
            "ground_authorization_id",
            resigned_authorization_id,
        )
        mutate(result.trace, "p1_attestation_id", resigned_p1_id)

        with pytest.raises(ANY_V0055_VIOLATION):
            recovery.require_durable_action_local_recovery_result_v1(result)
    finally:
        for target, field_name, original in reversed(changes):
            object.__setattr__(target, field_name, original)
    assert recovery.require_durable_action_local_recovery_result_v1(result) is result


@pytest.mark.parametrize(
    "public_name",
    (
        "run_durable_action_switch_p1_fresh_worker_v1",
        "run_durable_action_switch_p2_fresh_worker_v1",
        "run_durable_action_switch_c2_fresh_worker_v1",
    ),
)
def test_public_fresh_worker_substitution_is_source_pin_rejected(
    monkeypatch,
    public_name: str,
) -> None:
    attempted = 0

    def malicious_worker(*_args, **_kwargs):
        nonlocal attempted
        attempted += 1
        return LMBKernel.step(None, None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(
        transport,
        public_name,
        malicious_worker,
    )
    with pytest.raises(RecoveryViolation):
        recovery._assert_source_pins()
    assert attempted == 0


@pytest.mark.parametrize(
    "alias_name",
    (
        "_CANONICAL_TRANSPORT_RUN_P1",
        "_CANONICAL_TRANSPORT_RUN_P2",
        "_CANONICAL_TRANSPORT_RUN_P3",
    ),
)
def test_frozen_fresh_worker_alias_substitution_is_source_pin_rejected(
    monkeypatch,
    alias_name: str,
) -> None:
    attempted = 0

    def malicious_worker(*_args, **_kwargs):
        nonlocal attempted
        attempted += 1
        return LMBKernel.step(None, None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(
        recovery,
        alias_name,
        malicious_worker,
    )
    with pytest.raises(RecoveryViolation):
        recovery._assert_source_pins()
    assert attempted == 0


@pytest.mark.parametrize(
    "dag_name",
    (
        "restore_verified_action_indexed_first_lower_graph_v1",
        "restore_verified_action_indexed_final_lower_graph_v1",
    ),
)
def test_dag_restore_authority_substitution_is_rejected(
    monkeypatch,
    dag_name: str,
) -> None:
    def freshly_recomputed_substitute(*_args, **_kwargs):
        raise AssertionError("substituted restore authority ran")

    monkeypatch.setattr(dag, dag_name, freshly_recomputed_substitute)
    with pytest.raises(TransportViolation):
        transport._assert_model_only_import_boundary()


@pytest.mark.parametrize(
    "alias_name",
    (
        "_CANONICAL_DAG_RESTORE_FIRST",
        "_CANONICAL_DAG_RESTORE_FINAL",
    ),
)
def test_frozen_dag_restore_alias_substitution_is_rejected(
    monkeypatch,
    alias_name: str,
) -> None:
    def freshly_recomputed_substitute(*_args, **_kwargs):
        raise AssertionError("substituted frozen restore ran")

    monkeypatch.setattr(
        transport,
        alias_name,
        freshly_recomputed_substitute,
    )
    with pytest.raises(TransportViolation):
        transport._assert_model_only_import_boundary()


def test_preground_guard_install_substitution_is_source_pin_rejected(
    monkeypatch,
) -> None:
    called = 0

    def no_op_install(_self):
        nonlocal called
        called += 1

    monkeypatch.setattr(
        recovery._PreGroundGuardV1,
        "install",
        no_op_install,
    )
    with pytest.raises(RecoveryViolation):
        recovery._assert_source_pins()
    assert called == 0


def test_transport_stable_read_substitution_is_source_pin_rejected(
    monkeypatch,
) -> None:
    called = 0

    def forged_stable_read(_path):
        nonlocal called
        called += 1
        return b"{}"

    monkeypatch.setattr(
        transport,
        "_read_stable_regular",
        forged_stable_read,
    )
    with pytest.raises(TransportViolation):
        transport._assert_model_only_import_boundary()
    assert called == 0


def test_transport_boundary_assert_noop_is_source_pin_rejected(
    monkeypatch,
) -> None:
    called = 0

    def no_op_boundary(*, fresh_worker: bool = False):
        nonlocal called
        called += 1
        assert type(fresh_worker) is bool

    monkeypatch.setattr(
        transport,
        "_assert_model_only_import_boundary",
        no_op_boundary,
    )
    with pytest.raises(RecoveryViolation):
        recovery._assert_source_pins()
    assert called == 0


@pytest.mark.parametrize(
    ("target", "helper_name"),
    (
        (
            recovery,
            "require_durable_action_local_recovery_result_v1",
        ),
        (
            recovery,
            "require_durable_action_local_recovery_verification_v1",
        ),
        (
            action_local,
            "require_action_local_semantic_switch_result_v1",
        ),
        (recovery, "bind_runtime_authority_v1"),
        (recovery, "require_runtime_authority_v1"),
        (recovery, "_CANONICAL_RESULT_REQUIRE"),
        (recovery, "_CANONICAL_VERIFICATION_REQUIRE"),
        (recovery, "_CANONICAL_ACTION_LOCAL_REQUIRE"),
        (recovery, "_CANONICAL_BIND_RUNTIME_AUTHORITY"),
        (recovery, "_CANONICAL_REQUIRE_RUNTIME_AUTHORITY"),
    ),
)
def test_noop_require_and_mint_helper_substitution_is_rejected(
    monkeypatch,
    target: Any,
    helper_name: str,
) -> None:
    called = 0

    def no_op_helper(value, *_args, **_kwargs):
        nonlocal called
        called += 1
        return value

    monkeypatch.setattr(target, helper_name, no_op_helper)
    with pytest.raises(RecoveryViolation):
        recovery._CANONICAL_SOURCE_PIN_ASSERT()
    assert called == 0


@pytest.mark.parametrize(
    "helper_name",
    (
        "_assert_projection_matches_live_source",
        "_snapshot_id",
    ),
)
def test_orchestrator_projection_and_snapshot_helper_substitution_is_rejected(
    monkeypatch,
    helper_name: str,
) -> None:
    called = 0

    def poisoned_helper(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("substituted orchestrator helper ran")

    monkeypatch.setattr(recovery, helper_name, poisoned_helper)
    with pytest.raises(RecoveryViolation):
        recovery._CANONICAL_SOURCE_PIN_ASSERT()
    assert called == 0


def test_projection_helper_wrong_ground_id_poison_is_rejected(
    monkeypatch,
) -> None:
    original = recovery._freeze_projection
    called = 0

    def poisoned_projection(source):
        nonlocal called
        called += 1
        honest = original(source)
        return replace(honest, m_ground_row_id="0" * 64)

    monkeypatch.setattr(recovery, "_freeze_projection", poisoned_projection)
    with pytest.raises(RecoveryViolation):
        recovery._CANONICAL_SOURCE_PIN_ASSERT()
    assert called == 0


@pytest.mark.parametrize(
    "producer_name",
    (
        "_run_registered_h2_durable_action_local_recovery_v1",
        "_CANONICAL_ORCHESTRATOR_PRODUCER",
    ),
)
def test_verifier_rejects_private_producer_substitution_without_execution(
    campaign,
    monkeypatch,
    producer_name: str,
) -> None:
    root, claimed = campaign
    called = 0

    def replay_bypass(_store_root):
        nonlocal called
        called += 1
        return claimed

    monkeypatch.setattr(recovery, producer_name, replay_bypass)
    with pytest.raises(RecoveryViolation):
        recovery.verify_registered_h2_durable_action_local_recovery_v1(
            root,
            claimed,
        )
    assert called == 0


def test_pre_ground_guard_records_attempt_and_restores_canonical_step() -> None:
    guard = recovery._PreGroundGuardV1()
    guard.install()
    try:
        with pytest.raises(RecoveryViolation):
            LMBKernel.step(None, None, None)  # type: ignore[arg-type]
        assert guard.attempted_calls == 1
    finally:
        guard.abort()
    assert LMBKernel.step is recovery._CANONICAL_LMB_STEP


def test_source_pin_substitution_fails_before_any_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    def fake_source():
        raise AssertionError("substituted source must not run")

    monkeypatch.setattr(
        action_local,
        "run_registered_h2_action_local_semantic_switch_v1",
        fake_source,
    )
    root = tmp_path / "source-pin"
    with pytest.raises(RecoveryViolation):
        recovery.run_registered_h2_durable_action_local_recovery_v1(root)
    assert not root.exists()
    assert LMBKernel.step is recovery._CANONICAL_LMB_STEP


def test_untrusted_worker_outputs_are_rederived_and_rejected(
    campaign,
    monkeypatch,
) -> None:
    root, result = campaign
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        root / "c1", result.c1_commit_id
    )
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        root / "overlay", result.overlay_projection_id
    )
    c2 = transport.load_verified_durable_action_switch_c2_v1(
        root / "c2", result.c2_commit_id, c1, projection
    )

    attacks = (
        (
            lambda: transport.run_durable_action_switch_p1_fresh_worker_v1(
                root / "c1", result.c1_commit_id
            ),
            transport._derive_p1(c1).to_document(),
            "selected_action",
            "M",
        ),
        (
            lambda: transport.run_durable_action_switch_p2_fresh_worker_v1(
                root / "c1",
                result.c1_commit_id,
                root / "overlay",
                result.overlay_projection_id,
            ),
            transport._derive_p2(c1, projection).to_document(),
            "worker_ground_transition_calls",
            1,
        ),
        (
            lambda: transport.run_durable_action_switch_c2_fresh_worker_v1(
                root / "c1",
                result.c1_commit_id,
                root / "overlay",
                result.overlay_projection_id,
                root / "c2",
                result.c2_commit_id,
            ),
            transport._derive_c2_attestation(c2).to_document(),
            "selected_action",
            "N",
        ),
    )
    for invoke, honest, field_name, forged_value in attacks:
        forged = copy.deepcopy(honest)
        forged[field_name] = forged_value
        with monkeypatch.context() as context:
            context.setattr(
                transport,
                "_launch_worker",
                lambda **_kwargs: forged,
            )
            with pytest.raises(TransportViolation):
                invoke()


def test_wrong_expected_commit_head_extra_blob_and_extra_commit_fail(
    campaign,
    tmp_path,
) -> None:
    root, result = campaign
    with pytest.raises(TransportViolation):
        transport.load_verified_durable_action_switch_c1_v1(
            root / "c1", "0" * 64
        )
    with pytest.raises(TransportViolation):
        transport.load_verified_durable_action_switch_c2_v1(
            root / "c2",
            "0" * 64,
            transport.load_verified_durable_action_switch_c1_v1(
                root / "c1", result.c1_commit_id
            ),
            transport.load_durable_action_switch_overlay_projection_v1(
                root / "overlay", result.overlay_projection_id
            ),
        )

    attacks = (
        ("c1-head", "c1", "HEAD"),
        ("c2-head", "c2", "HEAD"),
        ("c1-extra-blob", "c1/blobs", f"{'1' * 64}.json"),
        ("c2-extra-commit", "c2/commits", f"{'2' * 64}.json"),
    )
    for name, relative, filename in attacks:
        copied, copied_result = _clone_store(campaign, tmp_path, name)
        (copied / relative / filename).write_bytes(b"{}")
        checkpoint = "c1" if name.startswith("c1") else "c2"
        with pytest.raises(TransportViolation):
            _load_checkpoint(copied, checkpoint, copied_result)


@pytest.mark.parametrize(
    ("checkpoint", "artifact_index", "mode"),
    (
        ("c1", 0, "truncate"),
        ("c1", 1, "hardlink"),
        ("c1", 2, "mutate"),
        ("c2", 0, "symlink"),
        ("c2", 1, "truncate"),
        ("c2", 2, "hardlink"),
    ),
)
def test_checkpoint_payload_manifest_commit_integrity_attacks_fail(
    campaign,
    tmp_path,
    checkpoint: str,
    artifact_index: int,
    mode: str,
) -> None:
    copied, result = _clone_store(
        campaign,
        tmp_path,
        f"{checkpoint}-{artifact_index}-{mode}",
    )
    target = _checkpoint_paths(copied, checkpoint, result)[artifact_index]
    original = target.read_bytes()
    if mode == "truncate":
        target.write_bytes(original[: max(1, len(original) // 2)])
    elif mode == "mutate":
        target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    elif mode in {"symlink", "hardlink"}:
        outside = tmp_path / f"outside-{checkpoint}-{artifact_index}-{mode}"
        outside.write_bytes(original)
        target.unlink()
        if mode == "symlink":
            target.symlink_to(outside)
        else:
            os.link(outside, target)
    else:  # pragma: no cover - parameter guard
        raise AssertionError(mode)
    with pytest.raises(ANY_V0055_VIOLATION):
        _load_checkpoint(copied, checkpoint, result)


def test_overlay_extra_truncate_symlink_hardlink_and_wrong_id_fail(
    campaign,
    tmp_path,
) -> None:
    root, result = campaign
    with pytest.raises(TransportViolation):
        transport.load_durable_action_switch_overlay_projection_v1(
            root / "overlay", "0" * 64
        )
    for mode in ("extra", "truncate", "symlink", "hardlink"):
        copied, _ = _clone_store(campaign, tmp_path, f"overlay-{mode}")
        overlay = copied / "overlay"
        target = overlay / f"{result.overlay_projection_id}.json"
        original = target.read_bytes()
        if mode == "extra":
            (overlay / f"{'1' * 64}.json").write_bytes(b"{}")
        elif mode == "truncate":
            target.write_bytes(original[: len(original) // 2])
        else:
            outside = tmp_path / f"overlay-outside-{mode}"
            outside.write_bytes(original)
            target.unlink()
            if mode == "symlink":
                target.symlink_to(outside)
            else:
                os.link(outside, target)
        with pytest.raises(ANY_V0055_VIOLATION):
            transport.load_durable_action_switch_overlay_projection_v1(
                overlay, result.overlay_projection_id
            )


def test_fully_rehashed_c1_root_injection_and_poisoned_lower_fail(
    campaign,
    tmp_path,
) -> None:
    for name, mutator in (
        (
            "c1-root-injection",
            lambda payload: payload.__setitem__(
                "selected_root_document",
                {"forged": True},
            ),
        ),
        (
            "c1-poisoned-lower",
            lambda payload: payload["lower_node_documents"][0].__setitem__(
                "result_digest",
                "0" * 64,
            ),
        ),
    ):
        copied, _result = _clone_store(campaign, tmp_path, name)
        new_commit = _rehash_checkpoint(
            copied / "c1",
            kind="c1",
            payload_mutator=mutator,
        )
        with pytest.raises(TransportViolation):
            transport.load_verified_durable_action_switch_c1_v1(
                copied / "c1", new_commit
            )


def test_fully_rehashed_overlay_second_row_and_identity_tamper_fail_campaign(
    campaign,
    tmp_path,
) -> None:
    for name, mutator in (
        (
            "overlay-second-row",
            lambda document: document.__setitem__(
                "second_row_document",
                copy.deepcopy(document["m_row_document"]),
            ),
        ),
        (
            "overlay-wrong-ground-row-id",
            lambda document: document.__setitem__(
                "m_ground_row_id",
                "0" * 64,
            ),
        ),
    ):
        copied, result = _clone_store(campaign, tmp_path, name)
        _rehash_overlay(copied / "overlay", mutator)
        with pytest.raises(RecoveryViolation):
            recovery.verify_registered_h2_durable_action_local_recovery_v1(
                copied, result
            )


def test_fully_rehashed_c2_wrong_parent_and_old_affected_activation_fail(
    campaign,
    tmp_path,
) -> None:
    copied, result = _clone_store(campaign, tmp_path, "c2-wrong-parent")
    wrong_parent = "0" * 64
    new_commit = _rehash_checkpoint(
        copied / "c2",
        kind="c2",
        payload_mutator=lambda payload: payload.__setitem__(
            "c1_commit_id", wrong_parent
        ),
        manifest_mutator=lambda manifest: manifest.__setitem__(
            "previous_c1_commit_id", wrong_parent
        ),
        commit_mutator=lambda commit: commit.__setitem__(
            "previous_commit_id", wrong_parent
        ),
    )
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        copied / "c1", result.c1_commit_id
    )
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        copied / "overlay", result.overlay_projection_id
    )
    with pytest.raises(TransportViolation):
        transport.load_verified_durable_action_switch_c2_v1(
            copied / "c2", new_commit, c1, projection
        )

    copied, result = _clone_store(campaign, tmp_path, "c2-old-affected")
    c1_payload = _read_json(
        copied / "c1" / "blobs" / f"{result.c1_payload_id}.json"
    )
    old_row_m = next(
        row
        for row in c1_payload["lower_node_documents"]
        if row["address"] == "ROW_M"
    )

    def activate_old_affected(payload: dict[str, Any]) -> None:
        binding = next(
            row
            for row in payload["active_final_bindings"]
            if row["address"] == "ROW_M"
        )
        binding["node_key_id"] = old_row_m["node_key_id"]
        binding["node_id"] = old_row_m["node_id"]

    new_commit = _rehash_checkpoint(
        copied / "c2",
        kind="c2",
        payload_mutator=activate_old_affected,
    )
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        copied / "c1", result.c1_commit_id
    )
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        copied / "overlay", result.overlay_projection_id
    )
    with pytest.raises(TransportViolation):
        transport.load_verified_durable_action_switch_c2_v1(
            copied / "c2", new_commit, c1, projection
        )


def test_c2_rejects_foreign_projection_and_parent_lease(campaign) -> None:
    root, result = campaign
    c1 = transport.load_verified_durable_action_switch_c1_v1(
        root / "c1", result.c1_commit_id
    )
    projection = transport.load_durable_action_switch_overlay_projection_v1(
        root / "overlay", result.overlay_projection_id
    )
    foreign_projection = replace(projection, source_result_id="0" * 64)
    with pytest.raises(TransportViolation):
        transport.load_verified_durable_action_switch_c2_v1(
            root / "c2",
            result.c2_commit_id,
            c1,
            foreign_projection,
        )

    foreign_commit = replace(c1.commit, protocol_id="0" * 64)
    foreign_c1 = replace(
        c1,
        expected_commit_id=foreign_commit.commit_id,
        commit=foreign_commit,
    )
    with pytest.raises(TransportViolation):
        transport.load_verified_durable_action_switch_c2_v1(
            root / "c2",
            result.c2_commit_id,
            foreign_c1,
            projection,
        )


def test_existing_nonempty_or_non_directory_store_is_rejected(
    tmp_path,
) -> None:
    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "foreign").write_bytes(b"x")
    with pytest.raises(RecoveryViolation):
        recovery.run_registered_h2_durable_action_local_recovery_v1(nonempty)

    regular = tmp_path / "regular"
    regular.write_bytes(b"x")
    with pytest.raises(RecoveryViolation):
        recovery.run_registered_h2_durable_action_local_recovery_v1(regular)
