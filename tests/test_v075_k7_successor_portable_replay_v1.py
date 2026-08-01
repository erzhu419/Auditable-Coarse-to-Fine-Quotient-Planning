from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import pickle

import pytest

from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_k7_successor_portable_replay_v1 as portable
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-portable-request-replay-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def substrate():
    old_profile = accounted.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )
    profile = successor.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
        accounted_profile=old_profile
    )
    registry = public_authority.V075TrustedSignerRegistryV1(
        public_authority.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY", (1 << 2047) + 1
        ),
        public_authority.V075RSAPublicVerificationKeyV1(
            "OBSERVER_EVIDENCE", (1 << 2047) + 3
        ),
    )
    occurrence = campaign.LogicalOccurrenceV1(
        _id("workload"),
        _id("protocol"),
        1,
        _id("structural"),
        _id("query"),
        _id("selected-plan"),
        _id("threshold"),
        _id("build-epoch"),
        _id("rebuild"),
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id("preregistration"),
        occurrence.protocol_id,
        old_profile.comparison_profile_id,
        old_profile.counter_registry_id,
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
        _id("common-prefix"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        1,
        decision.frontier_snapshot_id,
        _id("route-cap"),
    )
    route = accounted.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=old_profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )
    request = successor.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=profile,
        route_identity=route,
        signer_registry=registry,
        opaque_environment_commitment_id=_id("opaque"),
        sealed_secret_commitment_id=_id("secret"),
        session_external_id=_id("session"),
        request_nonce=_id("nonce"),
        scientific_occurrence_id=_id("science"),
        schedule_id=_id("schedule"),
    )
    return old_profile, profile, request


def _profile_inputs(substrate):
    old_profile, profile, _request = substrate
    transport = old_profile.transport_profile
    lifecycle = old_profile.private_replay_profile
    return {
        "source_archive_raw": transport._archive_bytes,  # noqa: SLF001
        "transport_profile_raw": canonical_json_bytes(transport.to_document()),
        "lifecycle_profile_raw": canonical_json_bytes(lifecycle.to_document()),
        "successor_profile_raw": canonical_json_bytes(profile.to_document()),
    }


@pytest.fixture(scope="module")
def replayed(substrate):
    closure = portable.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        **_profile_inputs(substrate)
    )
    result = portable.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=substrate[2].canonical_bytes,
        profile_closure=closure,
    )
    return closure, result


def test_fresh_replay_requires_no_live_parent_authority(replayed, substrate) -> None:
    closure, result = replayed
    original = substrate[2]
    assert portable.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    assert "expected" not in inspect.signature(
        portable.replay_v075_k7_successor_request_bytes_portable_v1
    ).parameters
    assert result.request is not original
    assert result.request.request_id == original.request_id
    assert result.request.canonical_bytes == original.canonical_bytes
    assert result.request.profile is closure.successor_profile
    assert result.to_document()["fresh_request_authority_reconstructed"] is True
    assert result.to_document()["live_parent_request_object_accepted"] is False
    assert set(
        result.to_document()[name]
        for name in portable._locks()  # noqa: SLF001
    ) == {False}


def test_profile_closure_reconstructs_every_nested_profile(replayed, substrate) -> None:
    closure, _result = replayed
    old_profile, profile, _request = substrate
    assert closure.successor_profile is not profile
    assert closure.successor_profile.profile_id == profile.profile_id
    assert closure.accounted_profile is not old_profile
    assert closure.accounted_profile.profile_id == old_profile.profile_id
    assert (
        closure.transport_profile.to_document()
        == old_profile.transport_profile.to_document()
    )
    assert (
        closure.lifecycle_profile.to_document()
        == old_profile.private_replay_profile.to_document()
    )
    assert closure.to_document()["actual_isolated_runtime_verified"] is False


def test_profile_or_archive_mutation_fails_before_request_replay(substrate) -> None:
    inputs = _profile_inputs(substrate)
    changed = deepcopy(substrate[1].to_document())
    changed["bootstrap_source_entry"]["sha256"] = _id("forged-bootstrap")
    inputs["successor_profile_raw"] = canonical_json_bytes(changed)
    with pytest.raises(portable.V075K7SuccessorPortableReplayV1Error):
        portable.reconstruct_v075_k7_successor_portable_profile_closure_v1(
            **inputs
        )

    inputs = _profile_inputs(substrate)
    archive = bytearray(inputs["source_archive_raw"])
    archive[-1] ^= 1
    inputs["source_archive_raw"] = bytes(archive)
    with pytest.raises(portable.V075K7SuccessorPortableReplayV1Error):
        portable.reconstruct_v075_k7_successor_portable_profile_closure_v1(
            **inputs
        )


def test_route_and_bool_int_mutations_fail(replayed, substrate) -> None:
    closure, _result = replayed
    changed = deepcopy(substrate[2].to_document())
    changed["route_identity"]["logical_occurrence"]["query_id"] = _id(
        "crossed-query"
    )
    with pytest.raises(portable.V075K7SuccessorPortableReplayV1Error):
        portable.replay_v075_k7_successor_request_bytes_portable_v1(
            raw=canonical_json_bytes(changed), profile_closure=closure
        )

    changed = deepcopy(substrate[2].to_document())
    changed["expected_launched_output_frame_count"] = True
    with pytest.raises(portable.V075K7SuccessorPortableReplayV1Error):
        portable.replay_v075_k7_successor_request_bytes_portable_v1(
            raw=canonical_json_bytes(changed), profile_closure=closure
        )


def test_reconstructed_authorities_are_process_local_unpickleable(replayed) -> None:
    closure, result = replayed
    with pytest.raises(TypeError, match="process-local"):
        pickle.dumps(closure)
    with pytest.raises(TypeError, match="process-local"):
        pickle.dumps(result)
