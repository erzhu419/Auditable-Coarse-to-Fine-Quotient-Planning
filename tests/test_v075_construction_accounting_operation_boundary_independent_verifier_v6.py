from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import pickle
from functools import lru_cache

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, content_id
from acfqp import construction_accounting_owned_runtime_v1 as runtime
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import construction_accounting_registry_v5 as registry_v5
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import (
    v075_construction_accounting_operation_boundary_independent_verifier_v6
    as verifier,
)
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    official_k7_root_cap_operation_boundary_manifest_v3,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:independent-v6-test\x00" + label.encode("utf-8")
    ).hexdigest()


def _transcript_bytes() -> bytes:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    boundary = official_k7_root_cap_operation_boundary_manifest_v3()
    with runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id("valid-independent-bundle"),
        recorder_id="independent-v6-test-recorder-v1",
        counter_registry=registry,
        stage_profile=stage,
        boundary_profile=boundary,
        _allow_low_level_test_api=True,
    ):
        for selected in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1:
            runtime.enter_owned_stage_v1(selected)
            if selected is partial.PartialNativeStageV1.INITIAL_ACQUISITION:
                row = next(
                    item
                    for item in boundary.boundaries
                    if item.stage.value == selected.value
                    and item.target_path
                    == "acquisition.initial_engine_ground_draws"
                )
                runtime.emit_owned_sum_v1(
                    row.boundary_key,
                    row.target_path,
                    4,
                )
            elif selected is partial.PartialNativeStageV1.INITIAL_MODEL_BUILD:
                for path in (
                    "build.initial_confidence_cache_lookups",
                    "build.initial_confidence_cache_hits",
                ):
                    row = next(
                        item
                        for item in boundary.boundaries
                        if item.stage.value == selected.value
                        and item.target_path == path
                    )
                    runtime.emit_owned_sum_v1(
                        row.boundary_key,
                        row.target_path,
                        1,
                    )
            runtime.exit_owned_stage_v1(selected)
        transcript = runtime.complete_owned_occurrence_v1()
    assert transcript is not None
    return canonical_json_bytes(transcript.to_document())


@lru_cache(maxsize=1)
def _bundle() -> dict[str, bytes]:
    profiles = registry_v6.freeze_construction_accounting_registry_v6()
    manifest = official_k7_root_cap_operation_boundary_manifest_v3()
    return {
        "v5_counter_registry_bytes": canonical_json_bytes(
            registry_v5.official_counter_registry_v5().to_document()
        ),
        "counter_registry_bytes": canonical_json_bytes(
            profiles["counter_registry"]
        ),
        "stage_profile_bytes": canonical_json_bytes(profiles["stage_profile"]),
        "comparison_profile_bytes": canonical_json_bytes(
            profiles["comparison_profile"]
        ),
        "actual_projection_profile_bytes": canonical_json_bytes(
            profiles["actual_projection_profile"]
        ),
        "boundary_manifest_bytes": canonical_json_bytes(manifest.to_document()),
        "partial_native_transcript_bytes": _transcript_bytes(),
    }


def _abort_transcript_bytes() -> bytes:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    boundary = official_k7_root_cap_operation_boundary_manifest_v3()
    with runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id("valid-independent-abort"),
        recorder_id="independent-v6-test-recorder-v1",
        counter_registry=registry,
        stage_profile=stage,
        boundary_profile=boundary,
    ):
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        transcript = runtime.abort_owned_occurrence_v1("TEST_ABORT")
    assert transcript is not None
    return canonical_json_bytes(transcript.to_document())


def _verify():
    return verifier.verify_v075_construction_accounting_operation_boundary_bundle_v6(
        **_bundle()
    )


def _rehash(document: dict, id_field: str, domain: str) -> None:
    payload = copy.deepcopy(document)
    payload.pop(id_field)
    document[id_field] = content_id(domain, payload)


_NODE_DOMAINS = {
    "acfqp.construction_partial_native_stage_start.v1": (
        "stage_start_id",
        verifier.TRANSCRIPT_STAGE_START_DOMAIN,
    ),
    "acfqp.construction_partial_native_operation_event.v1": (
        "operation_event_id",
        verifier.TRANSCRIPT_EVENT_DOMAIN,
    ),
    "acfqp.construction_partial_native_stage_completion.v1": (
        "stage_completion_id",
        verifier.TRANSCRIPT_STAGE_COMPLETION_DOMAIN,
    ),
    "acfqp.construction_partial_native_occurrence_completion.v1": (
        "occurrence_completion_id",
        verifier.TRANSCRIPT_COMPLETION_DOMAIN,
    ),
    "acfqp.construction_partial_native_occurrence_abort.v1": (
        "occurrence_abort_id",
        verifier.TRANSCRIPT_ABORT_DOMAIN,
    ),
}


def _rechain_transcript(
    document: dict,
    *,
    wrong_domain_event_index: int | None = None,
) -> None:
    start = document["occurrence_start"]
    _rehash(start, "occurrence_start_id", verifier.TRANSCRIPT_START_DOMAIN)
    predecessor = start["occurrence_start_id"]
    event_ids = []
    for index, node in enumerate(document["chain_nodes"]):
        node["chain_sequence"] = index + 1
        node["predecessor_chain_id"] = predecessor
        id_field, domain = _NODE_DOMAINS[node["schema"]]
        if node["schema"].endswith("occurrence_completion.v1") or node[
            "schema"
        ].endswith("occurrence_abort.v1"):
            node["emitted_event_ids"] = list(event_ids)
            node["total_event_count"] = len(event_ids)
        selected_domain = (
            verifier.TRANSCRIPT_STAGE_START_DOMAIN
            if wrong_domain_event_index == index
            else domain
        )
        _rehash(node, id_field, selected_domain)
        predecessor = node[id_field]
        if node["schema"].endswith("operation_event.v1"):
            event_ids.append(predecessor)
    terminal = document["chain_nodes"][-1]
    if terminal["schema"].endswith("occurrence_completion.v1"):
        document["occurrence_completion_id"] = terminal[
            "occurrence_completion_id"
        ]
    else:
        document["occurrence_abort_id"] = terminal["occurrence_abort_id"]
    _rehash(document, "partial_native_transcript_id", verifier.TRANSCRIPT_DOMAIN)


def _reject(bundle: dict[str, bytes]) -> None:
    with pytest.raises(
        verifier.V075ConstructionAccountingOperationBoundaryIndependentV6Violation
    ):
        verifier.verify_v075_construction_accounting_operation_boundary_bundle_v6(
            **bundle
        )


def test_independent_v6_bundle_replay_and_nonofficial_locks() -> None:
    verification = _verify()
    document = verification.to_document()
    assert verification.v5_registry_id == verifier.EXPECTED_V5_REGISTRY_ID
    assert verification.counter_registry_id == verifier.EXPECTED_V6_REGISTRY_ID
    assert verification.stage_profile_id == verifier.EXPECTED_V6_STAGE_ID
    assert verification.comparison_profile_id == (
        verifier.EXPECTED_V6_COMPARISON_ID
    )
    assert verification.actual_projection_profile_id == (
        verifier.EXPECTED_V6_ACTUAL_ID
    )
    assert verification.boundary_manifest_id == (
        verifier.EXPECTED_BOUNDARY_MANIFEST_ID
    )
    assert verification.partial_native_event_count == 3
    assert document["producer_modules_imported"] is False
    assert document[
        "v6_fifty_eight_additions_reconstructed_independently"
    ] is True
    assert document["v4_117_required_paths_partitioned_independently"] is True
    assert document["v4_20_owner_matched_boundaries_verified"] is True
    assert verification.operation_boundary_count == 150
    assert document["all_operation_boundary_ids_rehashed_independently"] is True
    assert document["partial_native_hash_chain_replayed_independently"] is True
    assert document["counter_record_count"] == 0
    assert document["work_vector_count"] == 0
    assert document["official_execution_allowed"] is False
    assert document["production_authorizing"] is False
    assert document["official_scalar_cost"] is None
    assert verification.canonical_bytes == canonical_json_bytes(document)
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False
    with pytest.raises(TypeError):
        pickle.dumps(verification)


def test_verifier_source_has_no_forbidden_producer_imports() -> None:
    source = inspect.getsource(verifier)
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = {
        "acfqp.construction_accounting_registry_v6",
        "acfqp.v075_k7_root_cap_operation_boundary_manifest_v3",
        "acfqp.construction_accounting_partial_native_v1",
        "acfqp.construction_accounting_owned_runtime_v1",
    }
    assert not (imported & forbidden)


def test_independent_verifier_accepts_a_typed_partial_abort_chain() -> None:
    bundle = dict(_bundle())
    bundle["partial_native_transcript_bytes"] = _abort_transcript_bytes()
    verification = (
        verifier.verify_v075_construction_accounting_operation_boundary_bundle_v6(
            **bundle
        )
    )
    assert verification.occurrence_id == _id("valid-independent-abort")
    assert verification.partial_native_event_count == 0
    assert verification.to_document()["official_execution_allowed"] is False


def test_unknown_field_and_v5_substitution_attacks_fail() -> None:
    bundle = _bundle()
    registry = copy.deepcopy(
        __import__("json").loads(bundle["counter_registry_bytes"])
    )
    registry["forged"] = False
    _rehash(registry, "counter_registry_id", verifier.V6_REGISTRY_DOMAIN)
    attacked = dict(bundle)
    attacked["counter_registry_bytes"] = canonical_json_bytes(registry)
    _reject(attacked)

    v5 = copy.deepcopy(__import__("json").loads(bundle["v5_counter_registry_bytes"]))
    v5["leaves"][0]["unit"] = "forged_unit"
    _rehash(v5, "counter_registry_id", verifier.V5_REGISTRY_DOMAIN)
    attacked = dict(bundle)
    attacked["v5_counter_registry_bytes"] = canonical_json_bytes(v5)
    _reject(attacked)


def test_boundary_tamper_reorder_and_missing_site_attacks_fail() -> None:
    bundle = _bundle()
    manifest = __import__("json").loads(bundle["boundary_manifest_bytes"])

    tampered = copy.deepcopy(manifest)
    tampered["boundaries"][0]["registered_owner"] = "forged_owner"
    _rehash(tampered["boundaries"][0], "boundary_id", verifier.BOUNDARY_DOMAIN)
    _rehash(tampered, "manifest_id", verifier.BOUNDARY_MANIFEST_DOMAIN)
    attacked = dict(bundle)
    attacked["boundary_manifest_bytes"] = canonical_json_bytes(tampered)
    _reject(attacked)

    reordered = copy.deepcopy(manifest)
    reordered["boundaries"][0], reordered["boundaries"][1] = (
        reordered["boundaries"][1],
        reordered["boundaries"][0],
    )
    _rehash(reordered, "manifest_id", verifier.BOUNDARY_MANIFEST_DOMAIN)
    attacked = dict(bundle)
    attacked["boundary_manifest_bytes"] = canonical_json_bytes(reordered)
    _reject(attacked)

    missing = copy.deepcopy(manifest)
    missing["boundaries"].pop()
    _rehash(missing, "manifest_id", verifier.BOUNDARY_MANIFEST_DOMAIN)
    attacked = dict(bundle)
    attacked["boundary_manifest_bytes"] = canonical_json_bytes(missing)
    _reject(attacked)


def test_transcript_tamper_cross_domain_and_cross_occurrence_attacks_fail() -> None:
    bundle = _bundle()
    base = __import__("json").loads(bundle["partial_native_transcript_bytes"])
    event_index = next(
        index
        for index, node in enumerate(base["chain_nodes"])
        if node["schema"].endswith("operation_event.v1")
    )

    tampered = copy.deepcopy(base)
    tampered["chain_nodes"][event_index]["amount"] = 99
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(tampered)
    _reject(attacked)

    reordered = copy.deepcopy(base)
    reordered["chain_nodes"][0], reordered["chain_nodes"][1] = (
        reordered["chain_nodes"][1],
        reordered["chain_nodes"][0],
    )
    _rechain_transcript(reordered)
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(reordered)
    _reject(attacked)

    wrong_domain = copy.deepcopy(base)
    _rechain_transcript(wrong_domain, wrong_domain_event_index=event_index)
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(
        wrong_domain
    )
    _reject(attacked)

    cross_occurrence = copy.deepcopy(base)
    cross_occurrence["chain_nodes"][event_index]["occurrence_id"] = _id(
        "foreign-occurrence"
    )
    _rechain_transcript(cross_occurrence)
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(
        cross_occurrence
    )
    _reject(attacked)


def test_duplicate_stage_output_role_attack_fails_after_full_rehash() -> None:
    bundle = _bundle()
    transcript = __import__("json").loads(
        bundle["partial_native_transcript_bytes"]
    )
    completion = next(
        node
        for node in transcript["chain_nodes"]
        if node["schema"].endswith("stage_completion.v1")
    )
    completion["output_bindings"] = [
        {"role": "same_role", "artifact_id": _id("same-a")},
        {"role": "same_role", "artifact_id": _id("same-b")},
    ]
    _rechain_transcript(transcript)
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(
        transcript
    )
    _reject(attacked)


def test_unknown_site_and_cache_summary_charging_attacks_fail() -> None:
    bundle = _bundle()
    base = __import__("json").loads(bundle["partial_native_transcript_bytes"])
    event_index = next(
        index
        for index, node in enumerate(base["chain_nodes"])
        if node["schema"].endswith("operation_event.v1")
        and node["stage_kind"] == "INITIAL_MODEL_BUILD"
    )

    unknown = copy.deepcopy(base)
    unknown["chain_nodes"][event_index]["site_id"] = "unknown.site"
    _rechain_transcript(unknown)
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(unknown)
    _reject(attacked)

    # A caller-returned cached checkpoint summary is a registered legacy-zero
    # boundary, not a live operation event, even when the attacker rebuilds the
    # complete transcript chain around it.
    summary = copy.deepcopy(base)
    node = summary["chain_nodes"][event_index]
    node["site_id"] = "legacy-zero.build-initial-exact-likelihood-comparisons"
    node["path"] = "build.initial_exact_likelihood_comparisons"
    node["amount"] = 110
    _rechain_transcript(summary)
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(summary)
    _reject(attacked)


@pytest.mark.parametrize(
    "field",
    ("counter_records", "work_vector", "comparison_vector", "actual_projection"),
)
def test_any_nonnull_accounting_output_injection_fails(field: str) -> None:
    bundle = _bundle()
    transcript = __import__("json").loads(
        bundle["partial_native_transcript_bytes"]
    )
    transcript[field] = {"work_vector_id": _id("forged-work-vector")}
    _rehash(
        transcript,
        "partial_native_transcript_id",
        verifier.TRANSCRIPT_DOMAIN,
    )
    attacked = dict(bundle)
    attacked["partial_native_transcript_bytes"] = canonical_json_bytes(transcript)
    _reject(attacked)
