from __future__ import annotations

import hashlib

import pytest

from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_os_supervisor_admission_v1 as os_admission
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-parent-owned-successor-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def substrate():
    old_profile = (
        accounted.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
            timeout_milliseconds=5_000
        )
    )
    profile = successor.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
        accounted_profile=old_profile,
    )
    return old_profile, profile


def _route(profile, label: str):
    occurrence = campaign.LogicalOccurrenceV1(
        _id(f"workload-{label}"),
        _id(f"protocol-{label}"),
        1,
        _id(f"structural-{label}"),
        _id(f"query-{label}"),
        _id(f"selected-plan-{label}"),
        _id(f"threshold-{label}"),
        _id(f"build-epoch-{label}"),
        _id(f"rebuild-{label}"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id(f"preregistration-{label}"),
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
        _id(f"frontier-{label}"),
        _id(f"causal-{label}"),
        _id(f"common-prefix-{label}"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        1,
        decision.frontier_snapshot_id,
        _id(f"route-cap-{label}"),
    )
    return accounted.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )


@pytest.fixture(scope="module")
def protocol(substrate):
    old_profile, profile = substrate
    route = _route(old_profile, "a")
    registry = public_authority.V075TrustedSignerRegistryV1(
        public_authority.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY", (1 << 2047) + 1
        ),
        public_authority.V075RSAPublicVerificationKeyV1(
            "OBSERVER_EVIDENCE", (1 << 2047) + 3
        ),
    )
    request = successor.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=profile,
        route_identity=route,
        signer_registry=registry,
        opaque_environment_commitment_id=_id("opaque"),
        sealed_secret_commitment_id=_id("sealed-secret"),
        session_external_id=_id("session"),
        request_nonce=_id("request-nonce"),
        scientific_occurrence_id=_id("scientific-occurrence"),
        schedule_id=_id("schedule"),
    )
    admission = os_admission.probe_v075_k7_os_supervisor_admission_v1()
    assert admission.status is os_admission.K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
    closure = successor.block_v075_k7_parent_owned_prelaunch_v1(
        request=request,
        admission_result=admission,
    )
    return route, registry, request, admission, closure


def test_profile_freezes_exact_predecessor_bootstrap_and_future_roles(substrate):
    old_profile, profile = substrate
    document = profile.to_document()
    assert document["accounted_sealed_profile_id"] == old_profile.profile_id
    assert document["accounted_sealed_profile"] == old_profile.to_document()
    expected = next(
        (digest, size)
        for path, digest, size in old_profile.transport_profile.source_entries
        if path == successor.BOOTSTRAP_SOURCE_PATH
    )
    assert document["bootstrap_source_entry"] == {
        "path": successor.BOOTSTRAP_SOURCE_PATH,
        "sha256": expected[0],
        "byte_count": expected[1],
        "derived_from_sealed_source_snapshot": True,
    }
    assert document["future_launched_output_frame_roles"] == list(
        successor.FUTURE_LAUNCHED_OUTPUT_ROLES
    )
    assert document["parent_owned_suffix"] is True
    assert successor.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS


def test_request_binds_full_route_registry_and_occurrence_mapping(protocol):
    route, registry, request, _admission, _closure = protocol
    document = request.to_document()
    assert document["route_identity"] == route.to_document()
    assert document["signer_registry_id"] == registry.registry_id
    assert document["signer_registry"] == registry.to_document()
    assert document["occurrence_mapping"]["scientific_occurrence_id"] == (
        document["scientific_occurrence_id"]
    )
    assert document["occurrence_mapping"]["phase3e_logical_occurrence_id"] == (
        route.logical_occurrence.logical_occurrence_id
    )
    assert document["caller_supplied_signer"] is False
    assert document["caller_supplied_private_result"] is False
    assert document["caller_supplied_cutoff"] is False
    assert not any("cutoff_sequence" in key for key in document)


def test_request_exact_bytes_reject_mismatch_cutoff_injection_and_bool_int(protocol):
    _route_value, _registry, request, _admission, _closure = protocol
    assert (
        successor.verify_v075_k7_parent_owned_successor_request_bytes_v1(
            raw=request.canonical_bytes, expected=request
        )
        is request
    )
    changed = request.to_document()
    changed["schedule_id"] = _id("another-schedule")
    with pytest.raises(
        successor.V075K7ParentOwnedSuccessorIPCV1Error,
        match="bytes/document binding changed",
    ):
        successor.verify_v075_k7_parent_owned_successor_request_bytes_v1(
            raw=canonical_json_bytes(changed), expected=request
        )
    injected = request.to_document()
    injected["operational_cutoff_sequence"] = 1
    with pytest.raises(successor.V075K7ParentOwnedSuccessorIPCV1Error):
        successor.verify_v075_k7_parent_owned_successor_request_bytes_v1(
            raw=canonical_json_bytes(injected), expected=request
        )
    mistyped = request.to_document()
    mistyped["expected_launched_output_frame_count"] = True
    with pytest.raises(successor.V075K7ParentOwnedSuccessorIPCV1Error):
        successor.verify_v075_k7_parent_owned_successor_request_bytes_v1(
            raw=canonical_json_bytes(mistyped), expected=request
        )


def test_mapping_crossing_and_caller_mint_are_rejected(substrate, protocol):
    old_profile, profile = substrate
    _route_a, registry, request_a, admission, _closure = protocol
    route_b = _route(old_profile, "b")
    with pytest.raises(
        successor.V075K7ParentOwnedSuccessorIPCV1Error,
        match="identity graph is crossed",
    ):
        successor.V075K7ParentOwnedSuccessorRequestV1(
            successor._REQUEST_ISSUER,  # noqa: SLF001
            profile,
            route_b,
            registry,
            _id("opaque-b"),
            _id("secret-b"),
            _id("session-b"),
            _id("request-nonce-b"),
            request_a.scientific_occurrence_id,
            _id("schedule-b"),
            request_a.occurrence_mapping,
        )
    with pytest.raises(
        successor.V075K7ParentOwnedSuccessorIPCV1Error,
        match="caller-minted",
    ):
        successor.V075K7ScientificPhase3EOccurrenceMappingV1(
            object(), _id("science"), _id("schedule"), _id("logical")
        )
    with pytest.raises(
        successor.V075K7ParentOwnedSuccessorIPCV1Error,
        match="caller-minted",
    ):
        successor.V075K7ParentOwnedPrelaunchBlockedResultV1(
            object(), request_a, admission
        )


def test_not_available_blocker_has_zero_launches_zero_frames_and_no_vectors(protocol):
    _route_value, _registry, _request, admission, closure = protocol
    document = closure.to_document()
    assert document["os_supervisor_admission_result"] == admission.to_document()
    assert document["blocked_scope"] == "STRUCTURAL_PRELAUNCH_ADMISSION"
    assert document["attempt_terminal_issued"] is False
    assert document["noncertificate_closure_issued"] is False
    assert document["successor_executor_process_launches"] == 0
    assert document["child_output_frame_count"] == 0
    assert document["parent_output_frame_count"] == 0
    assert document["total_output_frame_count"] == 0
    assert document["parent_owned_suffix_required_on_launched_path"] is True
    assert document["nine_shared_resource_paths_issued"] is False
    assert "counter_record_document" not in document
    assert "work_vector_document" not in document
    assert "comparison_vector_document" not in document
    for name, value in successor._locks().items():  # noqa: SLF001
        assert document[name] is value is False
    assert "shared_resource_paths" not in document
    assert "child_business_frame" not in document
    assert "parent_accounting_suffix_frame" not in document


def test_bootstrap_is_not_caller_supplied_and_bool_identity_fails(substrate):
    _old_profile, _profile = substrate
    with pytest.raises(successor.V075K7ParentOwnedSuccessorIPCV1Error):
        successor.V075K7ScientificPhase3EOccurrenceMappingV1(
            successor._MAPPING_ISSUER,  # noqa: SLF001
            True,
            _id("schedule"),
            _id("logical"),
        )
