"""V0-054A same-query H2 durable proof-state regressions."""

from collections import Counter
import copy
from dataclasses import replace
import hashlib
import inspect
import os
from pathlib import Path
import shutil

import pytest

import acfqp.h2_durable_proof_state_v1 as durable_module
import acfqp.h2_durable_transport_v1 as transport_module
from acfqp.h2_temporal_incremental_proof_dag_v1 import (
    H2TemporalProofSlot as Slot,
)
from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests.test_live_query_local_epoch_invalidation_v1 import (
    live_contract as live_contract_fixture,
)


InvariantViolation = durable_module.DurableH2InvariantViolation
TransportViolation = transport_module.H2DurableTransportRoundTripViolation


@pytest.fixture(scope="module")
def durable_contract(tmp_path_factory):
    """Build the authentic V0-053 source once, then run V0-054A once."""

    source = live_contract_fixture.__wrapped__()
    store_root = tmp_path_factory.mktemp("acfqp-v0054a") / "store"
    result = durable_module.run_lmb_h2_same_query_durable_proof_state_v1(
        source["live_result"],
        store_root,
    )
    lease = durable_module.load_verified_durable_h2_checkpoint_v1(
        store_root,
        result.commit_id,
    )
    return {
        **source,
        "store_root": store_root,
        "durable_result": result,
        "lease": lease,
    }


def _clone_store(durable_contract, tmp_path: Path, label: str) -> Path:
    target = tmp_path / label
    shutil.copytree(durable_contract["store_root"], target)
    return target


def _payload_path(store_root: Path, payload_id: str) -> Path:
    return store_root / "blobs" / f"{payload_id}.json"


def _normalized_document(path: Path) -> dict:
    value = loads_canonical_json(path.read_bytes())
    return durable_module._normalize_document(value)


def _resign_mutated_payload(
    store_root: Path,
    old_commit_id: str,
    payload_id: str,
    mutate,
) -> str:
    """Rebuild every outer content-addressed layer around a malformed payload."""

    old_payload_path = _payload_path(store_root, payload_id)
    payload_document = _normalized_document(old_payload_path)
    mutate(payload_document)
    payload_body = dict(payload_document)
    payload_body.pop("payload_id")
    new_payload_id = durable_module._content_id("payload", payload_body)
    payload_document["payload_id"] = new_payload_id
    payload_bytes = canonical_json_bytes(payload_document)

    old_commit_path = store_root / "commits" / f"{old_commit_id}.json"
    old_commit = durable_module.DurableH2StateCommitV1.from_document(
        loads_canonical_json(old_commit_path.read_bytes())
    )
    old_manifest_path = (
        store_root / "blobs" / f"{old_commit.manifest_id}.json"
    )
    manifest_document = _normalized_document(old_manifest_path)
    manifest_document["payload_id"] = new_payload_id
    manifest_document["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    manifest_document["payload_size_bytes"] = len(payload_bytes)
    manifest_body = dict(manifest_document)
    manifest_body.pop("manifest_id")
    new_manifest_id = durable_module._content_id("manifest", manifest_body)
    manifest_document["manifest_id"] = new_manifest_id
    manifest_bytes = canonical_json_bytes(manifest_document)

    new_commit = durable_module.DurableH2StateCommitV1(
        old_commit.protocol_id,
        new_payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        new_manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
    )
    old_payload_path.unlink()
    old_manifest_path.unlink()
    old_commit_path.unlink()
    _payload_path(store_root, new_payload_id).write_bytes(payload_bytes)
    (store_root / "blobs" / f"{new_manifest_id}.json").write_bytes(
        manifest_bytes
    )
    new_commit_path = store_root / "commits" / f"{new_commit.commit_id}.json"
    new_commit_path.write_bytes(canonical_json_bytes(new_commit.to_document()))
    return new_commit.commit_id


def _resign_mutated_manifest(
    store_root: Path,
    old_commit_id: str,
    mutate,
) -> str:
    """Re-sign the manifest and commit around a source-identity mutation."""

    old_commit_path = store_root / "commits" / f"{old_commit_id}.json"
    old_commit = durable_module.DurableH2StateCommitV1.from_document(
        loads_canonical_json(old_commit_path.read_bytes())
    )
    old_manifest_path = (
        store_root / "blobs" / f"{old_commit.manifest_id}.json"
    )
    manifest_document = _normalized_document(old_manifest_path)
    mutate(manifest_document)
    manifest_body = dict(manifest_document)
    manifest_body.pop("manifest_id")
    new_manifest_id = durable_module._content_id("manifest", manifest_body)
    manifest_document["manifest_id"] = new_manifest_id
    manifest_bytes = canonical_json_bytes(manifest_document)
    new_commit = durable_module.DurableH2StateCommitV1(
        old_commit.protocol_id,
        old_commit.payload_id,
        old_commit.payload_sha256,
        old_commit.payload_size_bytes,
        new_manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
    )
    old_manifest_path.unlink()
    old_commit_path.unlink()
    (store_root / "blobs" / f"{new_manifest_id}.json").write_bytes(
        manifest_bytes
    )
    (store_root / "commits" / f"{new_commit.commit_id}.json").write_bytes(
        canonical_json_bytes(new_commit.to_document())
    )
    return new_commit.commit_id


def _resign_changed_threshold_store(
    durable_contract,
    store_root: Path,
) -> str:
    """Re-sign every outer layer around a valid but unregistered threshold."""

    result = durable_contract["durable_result"]
    lease = durable_contract["lease"]
    old_commit_path = store_root / "commits" / f"{result.commit_id}.json"
    old_manifest_path = store_root / "blobs" / f"{result.manifest_id}.json"
    old_payload_path = _payload_path(store_root, result.payload_id)

    changed_thresholds = replace(
        lease.thresholds,
        risk_tolerance=next(
            value
            for value in sorted(
                durable_module.audit.REGISTERED_RISK_TOLERANCES
            )
            if value != lease.thresholds.risk_tolerance
        ),
    )
    protocol_document = copy.deepcopy(lease.manifest.protocol.to_document())
    protocol_document["thresholds_id"] = changed_thresholds.thresholds_id
    protocol_body = dict(protocol_document)
    protocol_body.pop("protocol_id")
    new_protocol_id = durable_module._content_id("protocol", protocol_body)
    protocol_document["protocol_id"] = new_protocol_id

    payload_document = _normalized_document(old_payload_path)
    payload_document["protocol_id"] = new_protocol_id
    payload_document["thresholds_id"] = changed_thresholds.thresholds_id
    payload_body = dict(payload_document)
    payload_body.pop("payload_id")
    new_payload_id = durable_module._content_id("payload", payload_body)
    payload_document["payload_id"] = new_payload_id
    payload_bytes = canonical_json_bytes(payload_document)

    manifest_document = _normalized_document(old_manifest_path)
    manifest_document["protocol"] = protocol_document
    manifest_document["thresholds_document"] = changed_thresholds.to_document()
    manifest_document["candidate_request_documents"] = [
        item.to_document()
        for item in durable_module._canonical_candidate_requests(
            lease.model,
            changed_thresholds,
        )
    ]
    manifest_document["payload_id"] = new_payload_id
    manifest_document["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    manifest_document["payload_size_bytes"] = len(payload_bytes)
    manifest_body = dict(manifest_document)
    manifest_body.pop("manifest_id")
    new_manifest_id = durable_module._content_id("manifest", manifest_body)
    manifest_document["manifest_id"] = new_manifest_id
    manifest_bytes = canonical_json_bytes(manifest_document)

    new_commit = durable_module.DurableH2StateCommitV1(
        new_protocol_id,
        new_payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        new_manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
    )
    old_payload_path.unlink()
    old_manifest_path.unlink()
    old_commit_path.unlink()
    _payload_path(store_root, new_payload_id).write_bytes(payload_bytes)
    (store_root / "blobs" / f"{new_manifest_id}.json").write_bytes(
        manifest_bytes
    )
    (store_root / "commits" / f"{new_commit.commit_id}.json").write_bytes(
        canonical_json_bytes(new_commit.to_document())
    )
    return new_commit.commit_id


def test_public_runner_has_two_inputs_and_verifier_has_three() -> None:
    runner = durable_module.run_lmb_h2_same_query_durable_proof_state_v1
    verifier = durable_module.verify_lmb_h2_same_query_durable_proof_state_v1
    assert tuple(inspect.signature(runner).parameters) == (
        "source_live_result",
        "store_root",
    )
    assert tuple(inspect.signature(verifier).parameters) == (
        "source_live_result",
        "store_root",
        "claimed_result",
    )


def test_store_topology_canonical_bytes_and_strict_transport_roundtrip(
    durable_contract,
) -> None:
    store_root = durable_contract["store_root"]
    result = durable_contract["durable_result"]
    lease = durable_contract["lease"]
    assert (
        result.protocol_id,
        result.payload_id,
        result.manifest_id,
        result.commit_id,
        result.checkpoint_byte_snapshot_id,
        result.result_id,
    ) == (
        durable_module.EXPECTED_DURABLE_PROTOCOL_ID,
        durable_module.EXPECTED_DURABLE_PAYLOAD_ID,
        durable_module.EXPECTED_DURABLE_MANIFEST_ID,
        durable_module.EXPECTED_DURABLE_COMMIT_ID,
        durable_module.EXPECTED_DURABLE_SNAPSHOT_ID,
        durable_module.EXPECTED_DURABLE_CAMPAIGN_RESULT_ID,
    )

    assert {item.name for item in store_root.iterdir()} == {
        "blobs",
        "commits",
    }
    assert {item.name for item in (store_root / "commits").iterdir()} == {
        f"{result.commit_id}.json",
    }
    assert {item.name for item in (store_root / "blobs").iterdir()} == {
        f"{result.payload_id}.json",
        f"{result.manifest_id}.json",
    }
    for path in (
        store_root / "commits" / f"{result.commit_id}.json",
        store_root / "blobs" / f"{result.payload_id}.json",
        store_root / "blobs" / f"{result.manifest_id}.json",
    ):
        assert path.is_file()
        assert not path.is_symlink()
        assert path.read_bytes() == canonical_json_bytes(
            loads_canonical_json(path.read_bytes())
        )
    assert result.checkpoint_byte_snapshot_id == (
        durable_module._checkpoint_byte_snapshot_id(store_root, lease.commit)
    )

    manifest = lease.manifest
    model = transport_module.parse_query_scoped_partial_rapm_v3(
        manifest.final_model_document
    )
    thresholds = transport_module.parse_frozen_partial_audit_thresholds_v1(
        manifest.thresholds_document
    )
    plans = tuple(
        transport_module.parse_frozen_contingent_abstract_plan_v1(
            document["contingent_plan"]
        )
        for document in manifest.candidate_request_documents
    )
    assert model.to_document() == manifest.final_model_document
    assert thresholds.to_document() == manifest.thresholds_document
    assert tuple(item.to_document() for item in plans) == tuple(
        document["contingent_plan"]
        for document in manifest.candidate_request_documents
    )

    unknown_model_field = copy.deepcopy(manifest.final_model_document)
    unknown_model_field["unregistered_field"] = 1
    with pytest.raises(TransportViolation):
        transport_module.parse_query_scoped_partial_rapm_v3(unknown_model_field)
    tuple_where_list_is_required = copy.deepcopy(manifest.thresholds_document)
    tuple_where_list_is_required["initial_state_distribution"] = tuple(
        tuple_where_list_is_required["initial_state_distribution"]
    )
    with pytest.raises(TransportViolation):
        transport_module.parse_frozen_partial_audit_thresholds_v1(
            tuple_where_list_is_required
        )


def test_checkpoint_contains_exactly_thirty_lower_values_and_no_root(
    durable_contract,
) -> None:
    payload = durable_contract["lease"].payload
    assert payload.entry_count == 30
    assert payload.root_entry_count == 0
    assert len(payload.values) == 30
    assert all(item.slot is not Slot.R for item in payload.values)
    assert Counter(item.slot for item in payload.values) == {
        Slot.U1: 1,
        Slot.U0: 1,
        Slot.P1: 2,
        Slot.P0: 4,
        Slot.C0: 2,
        Slot.C1: 4,
        Slot.D: 4,
        Slot.E: 4,
        Slot.F: 4,
        Slot.G: 4,
    }
    seen = set()
    for value in payload.values:
        assert set(value.entry.key.ordered_parent_entry_ids) <= seen
        seen.add(value.entry.entry_id)


def test_two_distinct_warm_occurrences_and_all_three_matched_totals(
    durable_contract,
) -> None:
    result = durable_contract["durable_result"]
    first, second = result.occurrences
    assert tuple(item.occurrence_id for item in result.occurrences) == (
        durable_module.WARM_OCCURRENCE_IDS
    )
    assert first.occurrence_id != second.occurrence_id
    assert first.occurrence_result_id != second.occurrence_result_id
    assert (
        result.request_reset_computes,
        result.request_reset_hits,
        result.occurrence_reset_computes,
        result.occurrence_reset_hits,
        result.durable_computes,
        result.durable_hits,
    ) == (110, 0, 70, 40, 10, 100)
    for occurrence in result.occurrences:
        receipt = occurrence.load_receipt
        assert (
            receipt.loaded_lower_entry_count,
            receipt.loaded_root_entry_count,
            receipt.semantic_replay_computes,
            receipt.semantic_replay_hits,
            receipt.semantic_replay_resolution_count,
        ) == (30, 0, 34, 10, 44)
        assert len(receipt.loaded_entry_bindings) == 30
        assert receipt.canonical_bytes_verified is True
        assert receipt.exact_model_derived_payload_verified is True
        assert (
            occurrence.request_reset.computes,
            occurrence.request_reset.hits,
        ) == (55, 0)
        assert (
            occurrence.occurrence_reset.computes,
            occurrence.occurrence_reset.hits,
        ) == (35, 20)
        assert (
            occurrence.durable_continuation.computes,
            occurrence.durable_continuation.hits,
        ) == (5, 50)
        assert (
            occurrence.durable_continuation.lower_computes,
            occurrence.durable_continuation.lower_hits,
            occurrence.durable_continuation.root_computes,
            occurrence.durable_continuation.root_hits,
            occurrence.durable_continuation.preloaded_lower_entries,
        ) == (0, 50, 5, 0, 30)
        assert len(occurrence.durable_continuation.roots) == 5
        assert occurrence.request_reset.preloaded_entry_bindings == ()
        assert occurrence.occurrence_reset.preloaded_entry_bindings == ()
        assert (
            occurrence.durable_continuation.preloaded_entry_bindings
            == receipt.loaded_entry_bindings
        )
        for arm in (
            occurrence.request_reset,
            occurrence.occurrence_reset,
            occurrence.durable_continuation,
        ):
            assert len(arm.resolution_documents) == 55
            assert tuple(
                item["sequence_number"] for item in arm.resolution_documents
            ) == tuple(range(1, 56))
    assert result.avoided_cross_occurrence_lower_constructions == 60
    assert result.checkpoint_bytes_immutable_across_occurrences is True
    assert (
        result.parent_checkpoint_semantic_replay_computes,
        result.parent_checkpoint_semantic_replay_hits,
        result.parent_worker_output_verification_computes,
        result.parent_worker_output_verification_hits,
    ) == (34, 10, 190, 140)
    assert result.worker_output_exactly_bound_to_verified_lease is True


def test_warm_selection_is_a0a0_and_matches_the_source_certificate(
    durable_contract,
) -> None:
    result = durable_contract["durable_result"]
    source_final = (
        durable_contract["live_result"].global_cross_epoch_facet_arm.final_epoch
    )
    source_plan = source_final.plan_proposal.selected_plan
    assert source_plan is not None
    source_inner_audit_id = source_final.request_receipts[-1].audit_result.result_id
    assert (
        source_final.selected_plan_audit.result_id
        == durable_module.EXPECTED_FINAL_SELECTED_WRAPPER_AUDIT_ID
    )
    for occurrence in result.occurrences:
        for arm in (
            occurrence.request_reset,
            occurrence.occurrence_reset,
            occurrence.durable_continuation,
        ):
            assert arm.proposal.selected_schedule_code == "A0A0"
            assert arm.proposal.selected_plan_id == source_plan.plan_id
            assert arm.proposal.selected_semantic_key == (
                0,
                1,
                0,
                1,
                0,
                1,
                0,
                1,
            )
            assert arm.selected_audit_result_id == source_inner_audit_id
            assert arm.roots[-1].audit_result_id == source_inner_audit_id
            assert arm.roots[-1].plan_id == source_plan.plan_id


def test_warm_ground_access_is_zero_and_all_broader_claims_remain_locked(
    durable_contract,
) -> None:
    result = durable_contract["durable_result"]
    assert result.warm_process_launches == 2
    assert (
        result.warm_kernel_transition_calls,
        result.warm_action_catalogue_calls,
        result.warm_ground_optimizer_calls,
    ) == (0, 0, 0)
    for occurrence in result.occurrences:
        assert occurrence.fresh_process_attested is True
        assert occurrence.parent_process_distinct is True
        assert occurrence.process_launch_count == 1
        assert occurrence.target_kernel_object_available is False
        assert occurrence.ground_kernel_module_import_free_claimed is False
        assert occurrence.kernel_access_guard_installed is True
        assert occurrence.operational_ground_calls == 0
        assert (
            occurrence.load_receipt.kernel_transition_calls,
            occurrence.load_receipt.action_catalogue_calls,
            occurrence.load_receipt.ground_optimizer_calls,
        ) == (0, 0, 0)
        for arm in (
            occurrence.request_reset,
            occurrence.occurrence_reset,
            occurrence.durable_continuation,
        ):
            assert (
                arm.kernel_transition_calls,
                arm.action_catalogue_calls,
                arm.ground_optimizer_calls,
            ) == (0, 0, 0)
    assert result.registered_h2_same_query_durable_proof_state_claimed is True
    for field in (
        "generic_persistent_cache_claimed",
        "durable_complete_certificate_cache_claimed",
        "durable_R_persistence_claimed",
        "cross_query_cache_claimed",
        "cross_query_incremental_proof_claimed",
        "changed_threshold_incremental_proof_claimed",
        "changed_reward_incremental_proof_claimed",
        "generic_changed_model_incremental_proof_claimed",
        "generic_h_gt_1_recurrence_claimed",
        "semantic_policy_change_claimed",
        "generic_semantic_policy_change_claimed",
        "horizon_greater_than_two_claimed",
        "sample_reduction_claimed",
        "sample_efficiency_claimed",
        "total_work_or_wallclock_reduction_claimed",
        "workload_economics_claimed",
        "learned_or_partial_dynamics_claimed",
        "coordinate_invention_claimed",
        "official_execution_allowed",
        "sample_efficiency_gate_blocks_mainline",
    ):
        assert getattr(result, field) is False
    assert result.official_scalar_cost is None
    assert result.official_N_break_even is None
    assert result.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert result.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert result.sample_efficiency_gate == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"


def test_warm_ground_kernel_guard_fails_closed_and_restores_methods() -> None:
    kernel = LMBKernel(
        tile_types=(0, 0, 0),
        blockers=(frozenset(), frozenset(), frozenset()),
        type_count=1,
        capacity=3,
        max_layers=1,
    )
    state = LMBState(0, (0,))
    assert kernel.actions(state) == (
        LMBAction(0),
        LMBAction(1),
        LMBAction(2),
    )
    with durable_module._deny_lmb_ground_kernel_access():
        with pytest.raises(InvariantViolation):
            kernel.initial_distribution()
        with pytest.raises(InvariantViolation):
            kernel.actions(state)
        with pytest.raises(InvariantViolation):
            kernel.step(state, LMBAction(0))
    assert kernel.actions(state) == (
        LMBAction(0),
        LMBAction(1),
        LMBAction(2),
    )


def test_live_owner_authority_rejects_copied_result_and_lease(
    durable_contract,
) -> None:
    result = durable_contract["durable_result"]
    lease = durable_contract["lease"]
    durable_module.require_durable_h2_campaign_result_v1(result)
    durable_module.require_verified_durable_h2_lease_v1(lease)
    with pytest.raises(InvariantViolation):
        durable_module.require_durable_h2_campaign_result_v1(copy.copy(result))
    with pytest.raises(InvariantViolation):
        durable_module.require_verified_durable_h2_lease_v1(copy.copy(lease))


def test_loader_rejects_wrong_external_commit_and_extra_or_missing_artifacts(
    durable_contract,
    tmp_path,
) -> None:
    result = durable_contract["durable_result"]
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            durable_contract["store_root"],
            "0" * 64,
        )

    extra = _clone_store(durable_contract, tmp_path, "extra")
    (extra / "blobs" / "orphan.json").write_bytes(b"{}")
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            extra,
            result.commit_id,
        )

    missing = _clone_store(durable_contract, tmp_path, "missing")
    _payload_path(missing, result.payload_id).unlink()
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            missing,
            result.commit_id,
        )


@pytest.mark.parametrize("mode", ("truncated", "tampered"))
def test_loader_rejects_truncated_or_tampered_blob(
    durable_contract,
    tmp_path,
    mode,
) -> None:
    result = durable_contract["durable_result"]
    store = _clone_store(durable_contract, tmp_path, mode)
    payload = _payload_path(store, result.payload_id)
    original = payload.read_bytes()
    if mode == "truncated":
        payload.write_bytes(original[: len(original) // 2])
    else:
        replacement = b"0" if original[-2:-1] != b"0" else b"1"
        payload.write_bytes(original[:-2] + replacement + original[-1:])
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            store,
            result.commit_id,
        )


@pytest.mark.parametrize(
    "mode",
    (
        "r_injection",
        "missing_lower_entry",
        "hidden_value_poison",
        "wrong_parent_topology",
    ),
)
def test_loader_rejects_fully_resigned_semantic_payload_attacks(
    durable_contract,
    tmp_path,
    mode,
) -> None:
    result = durable_contract["durable_result"]
    store = _clone_store(durable_contract, tmp_path, mode)

    def mutate(document):
        if mode == "r_injection":
            document["values"][0]["slot"] = "R"
        elif mode == "missing_lower_entry":
            document["values"].pop()
        elif mode == "hidden_value_poison":
            rebuilt_values = []
            replacement_entry_ids = {}
            poisoned = False
            for item in durable_contract["lease"].payload.values:
                new_key = replace(
                    item.entry.key,
                    ordered_parent_entry_ids=tuple(
                        replacement_entry_ids.get(parent, parent)
                        for parent in item.entry.key.ordered_parent_entry_ids
                    ),
                )
                value_document = copy.deepcopy(dict(item.value_document))
                if item.slot is Slot.E and not poisoned:
                    value_document["support_certified"].append(True)
                    poisoned = True
                parsed_value = durable_module._parse_temporal_value(
                    item.slot,
                    value_document,
                )
                new_entry = replace(
                    item.entry,
                    key=new_key,
                    result_digest=durable_module.live._node_result_digest(
                        item.slot,
                        parsed_value,
                    ),
                )
                replacement_entry_ids[item.entry.entry_id] = new_entry.entry_id
                rebuilt_values.append(
                    durable_module.DurableH2ProofValueV1(
                        new_key.node_key_id,
                        new_entry,
                        item.slot,
                        value_document,
                    )
                )
            assert poisoned is True
            rebuilt_values.sort(
                key=lambda item: (
                    durable_module.live.LOWER_SLOT_ORDER.index(item.slot),
                    item.node_key_id,
                )
            )
            poisoned_payload = durable_module.DurableH2LowerProofPayloadV1(
                durable_contract["lease"].payload.protocol_id,
                durable_contract["lease"].payload.model_id,
                durable_contract["lease"].payload.thresholds_id,
                tuple(rebuilt_values),
            )
            document["values"] = [
                item.to_document() for item in poisoned_payload.values
            ]
        else:
            typed_values = durable_contract["lease"].payload.values
            target_index = next(
                index
                for index, item in enumerate(typed_values)
                if item.slot is Slot.D
                and item.entry.key.ordered_parent_entry_ids
            )
            target = typed_values[target_index]
            later_parent = next(
                item.entry.entry_id
                for item in typed_values
                if item.slot is Slot.E
            )
            bad_key = replace(
                target.entry.key,
                ordered_parent_entry_ids=(
                    later_parent,
                    *target.entry.key.ordered_parent_entry_ids[1:],
                ),
            )
            bad_entry = replace(target.entry, key=bad_key)
            bad_value = durable_module.DurableH2ProofValueV1(
                bad_key.node_key_id,
                bad_entry,
                target.slot,
                target.value_document,
            )
            document["values"][target_index] = bad_value.to_document()
            document["values"].sort(
                key=lambda item: (
                    durable_module.live.LOWER_SLOT_ORDER.index(
                        Slot(item["slot"])
                    ),
                    item["node_key_id"],
                )
            )

    new_commit_id = _resign_mutated_payload(
        store,
        result.commit_id,
        result.payload_id,
        mutate,
    )
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            store,
            new_commit_id,
        )


def test_loader_rejects_symlink_and_hardlink_artifacts(
    durable_contract,
    tmp_path,
) -> None:
    result = durable_contract["durable_result"]

    symlink_store = _clone_store(durable_contract, tmp_path, "symlink")
    commit = symlink_store / "commits" / f"{result.commit_id}.json"
    symlink_target = tmp_path / "external-commit.json"
    symlink_target.write_bytes(commit.read_bytes())
    commit.unlink()
    commit.symlink_to(symlink_target)
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            symlink_store,
            result.commit_id,
        )

    hardlink_store = _clone_store(durable_contract, tmp_path, "hardlink")
    payload = _payload_path(hardlink_store, result.payload_id)
    hardlink_target = tmp_path / "external-payload.json"
    try:
        os.link(payload, hardlink_target)
    except OSError as error:  # pragma: no cover - filesystem-specific fallback
        pytest.skip(f"hard links unavailable on this test filesystem: {error}")
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            hardlink_store,
            result.commit_id,
        )


@pytest.mark.parametrize(
    "field",
    (
        "build_result_id",
        "threshold_rebase_id",
        "evidence_request_id",
        "evidence_bundle_id",
        "source_selected_request_id",
        "source_selected_receipt_id",
        "source_selected_inner_audit_id",
        "source_selected_wrapper_audit_id",
        "source_final_execution_id",
    ),
)
def test_loader_rejects_fully_resigned_source_identity_attacks(
    durable_contract,
    tmp_path,
    field,
) -> None:
    result = durable_contract["durable_result"]
    store = _clone_store(durable_contract, tmp_path, f"source-{field}")
    new_commit_id = _resign_mutated_manifest(
        store,
        result.commit_id,
        lambda document: document.__setitem__(field, "0" * 64),
    )
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            store,
            new_commit_id,
        )


def test_loader_rejects_fully_resigned_changed_threshold_store(
    durable_contract,
    tmp_path,
) -> None:
    store = _clone_store(durable_contract, tmp_path, "changed-threshold")
    changed_commit_id = _resign_changed_threshold_store(
        durable_contract,
        store,
    )
    with pytest.raises(InvariantViolation):
        durable_module.load_verified_durable_h2_checkpoint_v1(
            store,
            changed_commit_id,
        )


def test_occurrence_proposal_and_root_bindings_fail_closed(
    durable_contract,
) -> None:
    first, second = durable_contract["durable_result"].occurrences
    arm = first.durable_continuation

    foreign_root = replace(
        arm.roots[0],
        occurrence_id=second.occurrence_id,
    )
    with pytest.raises(InvariantViolation):
        replace(arm, roots=(foreign_root, *arm.roots[1:]))

    reordered_candidate_roots = (
        arm.roots[1],
        arm.roots[0],
        *arm.roots[2:],
    )
    with pytest.raises(InvariantViolation):
        replace(arm, roots=reordered_candidate_roots)

    bad_proposal = replace(
        arm.proposal,
        candidate_root_ids=tuple(reversed(arm.proposal.candidate_root_ids)),
    )
    with pytest.raises(InvariantViolation):
        replace(arm, proposal=bad_proposal)

    wrong_selected_proposal = replace(
        arm.roots[-1],
        durable_proposal_id=durable_contract["live_result"].result_id,
    )
    with pytest.raises(InvariantViolation):
        replace(
            arm,
            roots=(*arm.roots[:-1], wrong_selected_proposal),
        )

    with pytest.raises(InvariantViolation):
        replace(first, occurrence_id=second.occurrence_id)
    with pytest.raises(InvariantViolation):
        replace(
            durable_contract["durable_result"],
            occurrences=(second, first),
            _instance_mint=None,
        )


def test_parent_rejects_structurally_valid_but_untrusted_worker_output(
    durable_contract,
    tmp_path,
    monkeypatch,
) -> None:
    source_occurrence = durable_contract["durable_result"].occurrences[0]
    arm = source_occurrence.request_reset
    bad_root = replace(arm.roots[0], audit_result_id="0" * 64)
    bad_proposal = replace(
        arm.proposal,
        candidate_root_ids=(bad_root.root_id, *arm.proposal.candidate_root_ids[1:]),
    )
    bad_selected_root = replace(
        arm.roots[-1],
        durable_proposal_id=bad_proposal.proposal_id,
    )
    bad_arm = replace(
        arm,
        proposal=bad_proposal,
        roots=(bad_root, *arm.roots[1:-1], bad_selected_root),
    )
    bad_occurrence = replace(source_occurrence, request_reset=bad_arm)

    def forged_worker(
        _store_root,
        _commit_id,
        occurrence_id,
        _output_path,
    ):
        return (
            replace(bad_occurrence, occurrence_id=occurrence_id),
            len(canonical_json_bytes(bad_occurrence.to_document())),
        )

    monkeypatch.setattr(durable_module, "_launch_warm_worker", forged_worker)
    with pytest.raises(
        InvariantViolation,
        match="trusted lease-bound replay",
    ):
        durable_module.run_lmb_h2_same_query_durable_proof_state_v1(
            durable_contract["live_result"],
            tmp_path / "untrusted-worker-store",
        )


def test_load_and_resolution_receipt_tampering_fails_closed(
    durable_contract,
) -> None:
    result = durable_contract["durable_result"]
    first, second = result.occurrences
    receipt = first.load_receipt
    with pytest.raises(InvariantViolation):
        replace(receipt, semantic_replay_hits=9)
    with pytest.raises(InvariantViolation):
        replace(
            receipt,
            loaded_entry_bindings=receipt.loaded_entry_bindings[:-1],
        )
    with pytest.raises(InvariantViolation):
        replace(first, load_receipt=second.load_receipt)

    arm = first.durable_continuation
    first_resolution = durable_module._parse_live_resolution(
        arm.resolution_documents[0]
    )
    with pytest.raises(
        (
            InvariantViolation,
            durable_module.live.LiveEpochInvariantViolation,
        )
    ):
        bad_resolution = replace(
            first_resolution,
            pre_cache_state_id=result.result_id,
        )
        replace(
            arm,
            resolution_documents=(
                bad_resolution.to_document(),
                *arm.resolution_documents[1:],
            ),
        )
    with pytest.raises(InvariantViolation):
        replace(
            arm,
            resolution_documents=(
                arm.resolution_documents[1],
                arm.resolution_documents[0],
                *arm.resolution_documents[2:],
            ),
        )


def test_independent_replay_rebuilds_checkpoint_and_both_warm_occurrences(
    durable_contract,
    monkeypatch,
) -> None:
    def public_runner_must_not_be_the_verifier(*_args, **_kwargs):
        raise AssertionError("independent verifier called the production runner")

    monkeypatch.setattr(
        durable_module,
        "run_lmb_h2_same_query_durable_proof_state_v1",
        public_runner_must_not_be_the_verifier,
    )
    report = durable_module.verify_lmb_h2_same_query_durable_proof_state_v1(
        durable_contract["live_result"],
        durable_contract["store_root"],
        durable_contract["durable_result"],
    )
    assert report.claimed_result_id == durable_contract["durable_result"].result_id
    assert report.replayed_result_id == durable_contract["durable_result"].result_id
    assert report.source_result_id == durable_contract["live_result"].result_id
    assert report.exact_document_match is True
    assert report.evaluation_lane_only is True
    assert report.included_in_operational_work is False
    assert (
        report.report_id
        == durable_module.EXPECTED_DURABLE_VERIFICATION_REPORT_ID
    )


def test_verifier_rejects_original_store_mutation_during_replay(
    durable_contract,
    tmp_path,
    monkeypatch,
) -> None:
    store = _clone_store(durable_contract, tmp_path, "mutated-during-verification")
    result = durable_contract["durable_result"]
    payload_path = _payload_path(store, result.payload_id)

    def mutate_original_after_replay(_source, _replay_store):
        data = payload_path.read_bytes()
        payload_path.write_bytes(
            data[:-2] + (b"0" if data[-2:-1] != b"0" else b"1") + data[-1:]
        )
        return result

    monkeypatch.setattr(
        durable_module,
        "_execute_lmb_h2_same_query_durable_proof_state_v1",
        mutate_original_after_replay,
    )
    with pytest.raises(InvariantViolation, match="changed during evaluation replay"):
        durable_module.verify_lmb_h2_same_query_durable_proof_state_v1(
            durable_contract["live_result"],
            store,
            result,
        )
