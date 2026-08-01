from __future__ import annotations

from dataclasses import fields
from functools import cache
import hashlib

import pytest

from acfqp import campaign_v1 as campaign
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import routing_v1 as routing
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as ipc_v1
from acfqp import v075_k7_root_cap_shared_resource_identity_v1 as identity_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-shared-resource-identity-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@cache
def _route_identity() -> ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1:
    profile = ipc_v1.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )
    occurrence = campaign.LogicalOccurrenceV1(
        _id("workload"),
        _id("protocol"),
        1,
        _id("structural"),
        _id("query"),
        _id("plan"),
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
        decision.transaction_index,
        decision.frontier_snapshot_id,
        _id("route-cap"),
    )
    return ipc_v1.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )


def _derivation() -> identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1:
    return identity_v1.derive_v075_k7_root_cap_shared_resource_identity_v1(
        _route_identity()
    )


def test_derives_every_binding_field_from_the_exact_typed_route() -> None:
    route = _route_identity()
    derivation = _derivation()
    binding = derivation.identity_binding
    document = derivation.to_document()

    assert binding.counter_registry_id == route.profile.counter_registry_id
    assert binding.stage_profile_id == route.profile.stage_profile_id
    assert binding.boundary_profile_id == route.profile.boundary_manifest_id
    assert binding.execution_profile_id == route.profile.execution_profile_id
    assert binding.occurrence_id == route.logical_occurrence.logical_occurrence_id
    assert binding.route_attempt_id == route.route_attempt.route_attempt_id
    assert binding.decision_point_id == route.decision_point.decision_point_id
    assert document["caller_selected_identity_fields"] == []
    assert document["all_identity_fields_route_derived"] is True
    assert document["shared_resource_identity_binding_id"] == (
        binding.identity_binding_id
    )
    assert document["shared_resource_identity_binding"] == binding.to_document()


def test_domains_are_central_registered_and_role_separated() -> None:
    assert len(identity_v1.LOCAL_DOMAIN_TAGS) == 2
    assert identity_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    assert len(identity_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS) == 2
    payload = {"same": "payload"}
    assert len(
        {content_id(domain, payload) for domain in identity_v1.LOCAL_DOMAIN_TAGS}
    ) == 2


def test_no_public_constructor_accepts_field_level_identity_overrides() -> None:
    route = _route_identity()
    public_parameters = {
        item.name
        for item in fields(identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1)
        if item.init
    }
    assert public_parameters == {"route_identity"}
    with pytest.raises(
        identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
        match="caller-minted",
    ):
        identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1(
            object(), route
        )
    with pytest.raises(
        identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
        match="exact typed",
    ):
        identity_v1.derive_v075_k7_root_cap_shared_resource_identity_v1(  # type: ignore[arg-type]
            object()
        )


@pytest.mark.parametrize(
    "field_name",
    [name for name, _source in identity_v1.DERIVED_FIELD_SOURCES],
)
def test_each_crossed_binding_field_fails_closed(field_name: str) -> None:
    derivation = _derivation()
    binding = derivation._identity_binding  # noqa: SLF001 - mutation attack
    original = getattr(binding, field_name)
    object.__setattr__(binding, field_name, _id(f"foreign-{field_name}"))
    try:
        with pytest.raises(
            identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
            match="stale or crossed",
        ):
            derivation.to_document()
    finally:
        object.__setattr__(binding, field_name, original)
    derivation.to_document()


def test_equal_route_or_binding_object_transplant_fails_closed() -> None:
    derivation = _derivation()
    route = derivation.route_identity
    equal_route = ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1.from_document(
        route.to_document(), profile=route.profile
    )
    assert equal_route == route
    assert equal_route is not route
    object.__setattr__(derivation, "route_identity", equal_route)
    try:
        with pytest.raises(
            identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
            match="object was replaced",
        ):
            derivation.to_document()
    finally:
        object.__setattr__(derivation, "route_identity", route)

    binding = derivation._identity_binding  # noqa: SLF001 - mutation attack
    equal_binding = receipts_v1.SharedResourceIdentityBindingV1(
        **{
            name: getattr(binding, name)
            for name, _source in identity_v1.DERIVED_FIELD_SOURCES
        }
    )
    assert equal_binding == binding
    assert equal_binding is not binding
    object.__setattr__(derivation, "_identity_binding", equal_binding)
    try:
        with pytest.raises(
            identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
            match="object was replaced",
        ):
            derivation.to_document()
    finally:
        object.__setattr__(derivation, "_identity_binding", binding)
    derivation.to_document()


def test_upstream_route_graph_mutation_is_replayed_and_rejected() -> None:
    derivation = _derivation()
    decision = derivation.route_identity.decision_point
    original = decision.common_prefix_work_id
    object.__setattr__(decision, "common_prefix_work_id", _id("crossed-prefix"))
    try:
        with pytest.raises(
            identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
            match="typed accounted K7 route identity failed replay",
        ):
            derivation.to_document()
    finally:
        object.__setattr__(decision, "common_prefix_work_id", original)
    derivation.to_document()


def test_verification_replays_derivation_and_preserves_all_formal_locks() -> None:
    derivation = _derivation()
    verification = (
        identity_v1.verify_v075_k7_root_cap_shared_resource_identity_v1(
            derivation
        )
    )
    document = verification.to_document()
    assert document["verification_result"] == "PASS"
    assert document["verified_fields"] == [
        name for name, _source in identity_v1.DERIVED_FIELD_SOURCES
    ]
    for lock in (
        "semantic_source_authority_present",
        "shared_resource_semantics_verified",
        "counter_records_issued",
        "work_vector_issued",
        "comparison_vector_issued",
        "actual_projection_proof_issued",
        "formal_vector_authorized",
        "official_execution_allowed",
    ):
        assert document[lock] is False

    foreign = _derivation()
    assert foreign is not derivation
    object.__setattr__(verification, "derivation", foreign)
    try:
        with pytest.raises(
            identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
            match="object was replaced",
        ):
            verification.to_document()
    finally:
        object.__setattr__(verification, "derivation", derivation)
    verification.to_document()


def test_verification_cannot_be_caller_minted() -> None:
    with pytest.raises(
        identity_v1.V075K7RootCapSharedResourceIdentityV1Error,
        match="caller-minted",
    ):
        identity_v1.V075K7RootCapSharedResourceIdentityVerificationV1(
            object(), _derivation()
        )
