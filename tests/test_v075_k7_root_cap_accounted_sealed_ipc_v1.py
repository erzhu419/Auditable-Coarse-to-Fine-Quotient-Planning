from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as ipc
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-accounted-sealed-ipc-test:v1\x00" + label.encode()
    ).hexdigest()


@pytest.fixture(scope="module")
def profile() -> ipc.V075K7RootCapAccountedSealedIPCProfileV1:
    return ipc.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )


@pytest.fixture(scope="module")
def protocol(profile):
    occurrence = campaign.LogicalOccurrenceV1(
        _id("workload"),
        _id("protocol"),
        1,
        _id("structural"),
        _id("query"),
        _id("selected-plan"),
        _id("threshold"),
        _id("build-epoch"),
        _id("rebuild-policy"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id("preregistration"),
        occurrence.protocol_id,
        profile.comparison_profile_id,
        profile.counter_registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = routing.DecisionPointV1(
        context.route_decision_context_id,
        1,
        _id("frontier"),
        _id("causal"),
        _id("common-prefix-work"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        1,
        decision.frontier_snapshot_id,
        _id("route-cap-profile"),
    )
    identity = ipc.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )
    request = ipc.freeze_v075_k7_root_cap_accounted_sealed_request_v1(
        profile=profile,
        route_identity=identity,
        request_nonce=_id("request-nonce"),
    )
    business = ipc.freeze_v075_k7_root_cap_accounted_sealed_business_frame_v1(
        request=request,
        business_result_id=_id("business-result"),
        partial_native_transcript_id=_id("partial-native-transcript"),
        terminal_artifact_id=_id("terminal"),
        private_replay_attestation_id=_id("private-replay-attestation"),
        cutoff_marker_id=_id("cutoff"),
        cutoff_sequence=100,
    )
    suffix = (
        ipc.freeze_v075_k7_root_cap_accounted_sealed_accounting_suffix_frame_v1(
            business_frame=business,
            suffix_start_sequence=101,
            suffix_end_sequence=109,
        )
    )
    raw = ipc.encode_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
        business_frame=business,
        accounting_suffix_frame=suffix,
    )
    return {
        "occurrence": occurrence,
        "attempt": attempt,
        "context": context,
        "decision": decision,
        "transaction": transaction,
        "identity": identity,
        "request": request,
        "business": business,
        "suffix": suffix,
        "raw": raw,
    }


def _frame(raw: bytes) -> bytes:
    return ipc.sealed_transport._frame(raw, cap=ipc.MAX_FRAME_BYTES)  # noqa: SLF001


def _documents(raw: bytes) -> tuple[dict, dict]:
    first, second = ipc._split_two_frames(raw)  # noqa: SLF001
    return json.loads(first), json.loads(second)


def test_profile_reuses_one_sealed_source_process_and_private_replay_substrate(
    profile,
) -> None:
    document = profile.to_document()
    assert profile.private_replay_profile.transport_profile is profile.transport_profile
    assert document["source_snapshot_id"] == profile.transport_profile.source_snapshot_id
    assert document["runtime_id"] == profile.transport_profile.runtime_id
    assert document["output_frame_count"] == 2
    assert document["ordered_output_frame_roles"] == list(
        ipc.REGISTERED_OUTPUT_FRAME_ROLES
    )
    assert document["live_execution_blockers"] == list(ipc.LIVE_EXECUTION_BLOCKERS)
    assert document["shared_resource_semantics_verified"] is False
    assert document["output_byte_fixed_point_verified"] is False
    assert document["formal_vector_authorized"] is False
    assert document["official_execution_allowed"] is False
    assert len(ipc.REQUESTED_PHASE3E_DOMAIN_CONSTANTS) == 7
    assert ipc.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    assert len(ipc.LOCAL_DOMAIN_TAGS) == 7


def test_profile_authority_snapshot_rejects_id_object_and_content_mutation(
    profile,
) -> None:
    original_registry_id = profile.counter_registry_id
    object.__setattr__(profile, "counter_registry_id", _id("foreign-registry"))
    try:
        with pytest.raises(
            ipc.V075K7RootCapAccountedSealedIPCV1Error,
            match="authority chain is stale",
        ):
            profile.to_document()
    finally:
        object.__setattr__(profile, "counter_registry_id", original_registry_id)
    profile.to_document()

    snapshot = profile._authority_snapshot  # noqa: SLF001
    original_registry = snapshot.registry
    replacement_registry = ipc.registry_v6.official_counter_registry_v6()
    assert replacement_registry == original_registry
    assert replacement_registry is not original_registry
    object.__setattr__(snapshot, "registry", replacement_registry)
    try:
        with pytest.raises(
            ipc.V075K7RootCapAccountedSealedIPCV1Error,
            match="authority object was replaced",
        ):
            profile.to_document()
    finally:
        object.__setattr__(snapshot, "registry", original_registry)
    profile.to_document()

    original_registry_key = original_registry.registry_key
    object.__setattr__(original_registry, "registry_key", "forged_registry")
    try:
        with pytest.raises(
            ipc.V075K7RootCapAccountedSealedIPCV1Error,
            match="authority snapshot",
        ):
            profile.to_document()
    finally:
        object.__setattr__(
            original_registry,
            "registry_key",
            original_registry_key,
        )
    profile.to_document()

    object.__setattr__(profile, "_authority_snapshot", object())
    try:
        with pytest.raises(
            ipc.V075K7RootCapAccountedSealedIPCV1Error,
            match="authority snapshot was replaced",
        ):
            profile.to_document()
    finally:
        object.__setattr__(profile, "_authority_snapshot", snapshot)
    profile.to_document()


def test_complete_route_occurrence_identity_and_two_frame_replay(profile, protocol) -> None:
    request = ipc.verify_v075_k7_root_cap_accounted_sealed_request_bytes_v1(
        raw=protocol["request"].canonical_bytes,
        profile=profile,
    )
    replay = ipc.verify_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
        raw=protocol["raw"], request=request
    )
    identity = protocol["identity"]
    suffix_document = protocol["suffix"].to_document()
    assert request.request_id == protocol["request"].request_id
    assert replay.route_identity_id == identity.route_identity_id
    assert replay.business_frame_id == protocol["business"].frame_id
    assert replay.accounting_suffix_frame_id == protocol["suffix"].frame_id
    assert replay.to_document()["decoded_frame_count"] == 2
    assert replay.to_document()["formal_vector_authorized"] is False
    assert suffix_document["shared_resource_path_count"] == 9
    assert [row["path"] for row in suffix_document["shared_resource_paths"]] == list(
        ipc.receipts_v1.SHARED_RESOURCE_PATHS
    )
    assert all(
        row["measurement"]["kind"] == "NOT_AVAILABLE"
        and row["semantic_authority_present"] is False
        for row in suffix_document["shared_resource_paths"]
    )
    assert suffix_document["output_byte_receipt"] == {
        "kind": "NOT_AVAILABLE",
        "reason": "OUTPUT_BYTE_FIXED_POINT_NOT_CONNECTED",
    }
    assert suffix_document["accounting_suffix_bytes_are_chargeable_output"] is True


def test_crossed_or_incomplete_route_identity_fails_closed(profile, protocol) -> None:
    transaction = replace(
        protocol["transaction"], route_attempt_id=_id("foreign-route-attempt")
    )
    with pytest.raises(
        ipc.V075K7RootCapAccountedSealedIPCV1Error,
        match="does not join exactly",
    ):
        ipc.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
            profile=profile,
            logical_occurrence=protocol["occurrence"],
            route_attempt=protocol["attempt"],
            route_context=protocol["context"],
            decision_point=protocol["decision"],
            transaction=transaction,
        )

    with pytest.raises(
        ipc.V075K7RootCapAccountedSealedIPCV1Error,
        match="Phase-3E typed authorities",
    ):
        ipc.V075K7RootCapAccountedSealedRouteIdentityV1(
            ipc._IDENTITY_ISSUER,  # noqa: SLF001 - fail-closed attack
            profile,
            protocol["occurrence"],
            protocol["attempt"],
            protocol["context"],
            protocol["decision"],
            None,
        )


@pytest.mark.parametrize("attack", ["missing", "swapped", "extra", "crossed", "short_shared"])
def test_two_frame_protocol_rejects_missing_reordered_extra_and_crossed_frames(
    profile, protocol, attack
) -> None:
    first, second = _documents(protocol["raw"])
    if attack == "missing":
        del first["route_attempt_id"]
    elif attack == "swapped":
        first, second = second, first
    elif attack == "extra":
        attacked = protocol["raw"] + _frame(canonical_json_bytes(first))
        with pytest.raises(ipc.V075K7RootCapAccountedSealedIPCV1Error):
            ipc.verify_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
                raw=attacked, request=protocol["request"]
            )
        return
    elif attack == "crossed":
        second["logical_occurrence_id"] = _id("foreign-occurrence")
    else:
        second["shared_resource_paths"] = second["shared_resource_paths"][:-1]
        second["shared_resource_path_count"] = 8
    attacked = _frame(canonical_json_bytes(first)) + _frame(canonical_json_bytes(second))
    with pytest.raises(ipc.V075K7RootCapAccountedSealedIPCV1Error):
        ipc.verify_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
            raw=attacked, request=protocol["request"]
        )


def test_request_missing_identity_and_live_execution_are_rejected(profile, protocol) -> None:
    document = protocol["request"].to_document()
    del document["decision_point_id"]
    with pytest.raises(ipc.V075K7RootCapAccountedSealedIPCV1Error):
        ipc.verify_v075_k7_root_cap_accounted_sealed_request_bytes_v1(
            raw=canonical_json_bytes(document), profile=profile
        )
    with pytest.raises(
        ipc.V075K7RootCapAccountedSealedProductionV1NotReady,
        match="output-byte fixed point",
    ):
        ipc.open_v075_k7_root_cap_accounted_sealed_production_v1()


@pytest.mark.parametrize(
    "target",
    (
        "request_transaction_index",
        "route_identity_transaction_index",
        "business_frame_index",
        "business_transaction_index",
        "suffix_transaction_index",
    ),
)
def test_raw_boolean_cannot_alias_any_replayed_integer_one(
    profile, protocol, target
) -> None:
    """Canonical ``true`` must never replay as the exact integer ``1``."""

    if target.startswith("request_") or target.startswith("route_identity_"):
        document = protocol["request"].to_document()
        if target == "request_transaction_index":
            document["transaction_index"] = True
        else:
            document["route_identity"]["transaction_index"] = True
        with pytest.raises(ipc.V075K7RootCapAccountedSealedIPCV1Error):
            ipc.verify_v075_k7_root_cap_accounted_sealed_request_bytes_v1(
                raw=canonical_json_bytes(document), profile=profile
            )
        return

    first, second = _documents(protocol["raw"])
    if target == "business_frame_index":
        first["frame_index"] = True
    elif target == "business_transaction_index":
        first["transaction_index"] = True
    else:
        second["transaction_index"] = True
    attacked = _frame(canonical_json_bytes(first)) + _frame(canonical_json_bytes(second))
    with pytest.raises(ipc.V075K7RootCapAccountedSealedIPCV1Error):
        ipc.verify_v075_k7_root_cap_accounted_sealed_two_frame_output_v1(
            raw=attacked, request=protocol["request"]
        )


@pytest.mark.parametrize("token", ("NaN", "Infinity", "-Infinity"))
def test_canonical_loader_converts_nonfinite_json_to_typed_error(token) -> None:
    raw = ('{"value":' + token + "}").encode("ascii")
    with pytest.raises(
        ipc.V075K7RootCapAccountedSealedIPCV1Error,
        match="non-finite",
    ):
        ipc._load_canonical(raw, "attack document")  # noqa: SLF001


def test_canonical_replay_equality_distinguishes_boolean_and_integer() -> None:
    with pytest.raises(
        ipc.V075K7RootCapAccountedSealedIPCV1Error,
        match="exact canonical content replay",
    ):
        ipc._require_same_canonical_document(  # noqa: SLF001
            {"value": True}, {"value": 1}, "attack document"
        )
