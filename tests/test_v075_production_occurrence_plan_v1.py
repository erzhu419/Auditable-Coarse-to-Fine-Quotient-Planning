from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_production_occurrence_plan_v1 as production_plan
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-production-plan-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _secret_laws() -> tuple[
    tuple[tuple[int, Fraction], ...],
    ...,
]:
    return (
        ((1, Fraction(2, 3)), (2, Fraction(1, 3))),
        ((1, Fraction(3, 4)), (2, Fraction(1, 4))),
        ((1, Fraction(4, 5)), (2, Fraction(1, 5))),
    )


def _claim(
    registry: public.V075TrustedSignerRegistryV1,
    role: public.V075ExternalAuthorityRoleV1,
    marker: str,
) -> public.V075SignedExternalAuthorityClaimV1:
    external_id = _id(f"{marker}-{role.value}")
    message = public.external_authority_claim_signing_bytes_v1(
        signer_registry=registry,
        role=role,
        external_id=external_id,
    )
    return public.V075SignedExternalAuthorityClaimV1(
        registry,
        role,
        external_id,
        sign_test_message(message),
    )


def _namespace(
    marker: str = "primary",
) -> public.V075PublicTargetTapeNamespaceV1:
    family = public.freeze_v075_public_family_generation_v1()
    salt = hashlib.sha512(
        f"v075-production-plan-private-test-salt-{marker}".encode("utf-8")
    ).digest()
    commitment = public.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=salt,
        secret_laws=_secret_laws(),
    )
    registry = public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    role = public.V075ExternalAuthorityRoleV1
    anchor = _claim(registry, role.REMOTE_MAIN_ANCHOR, marker)
    preregistration = _claim(
        registry,
        role.FINAL_PREREGISTRATION,
        marker,
    )
    observer_profile = _claim(
        registry,
        role.OBSERVER_PROFILE,
        marker,
    )
    return public.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=anchor,
        final_preregistration=preregistration,
        observer_profile=observer_profile,
    )


def _plan(
    namespace: public.V075PublicTargetTapeNamespaceV1 | None = None,
) -> production_plan.V075ProductionOccurrencePlanV1:
    return production_plan.freeze_v075_production_occurrence_plan_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=_namespace() if namespace is None else namespace,
    )


def test_exact_context_major_plan_binds_all_production_identities() -> None:
    namespace = _namespace()
    plan = _plan(namespace)
    family = public.freeze_v075_public_family_generation_v1()
    document = plan.to_document()

    assert len(plan.entries) == 15
    assert tuple(item.scientific_ordinal for item in plan.entries) == tuple(
        range(15)
    )
    assert tuple(item.transport_ordinal for item in plan.entries) == tuple(
        range(1, 16)
    )
    assert tuple(
        (item.context_ordinal, item.arm_ordinal)
        for item in plan.entries
    ) == tuple(
        (context_ordinal, arm_ordinal)
        for context_ordinal in range(3)
        for arm_ordinal in range(5)
    )
    assert tuple(item.arm for item in plan.entries) == tuple(
        arm
        for _context in range(3)
        for arm in production_plan.REGISTERED_ARM_ORDER
    )
    assert plan.context_ids == tuple(
        item.context_id for item in family.replicate_contexts
    )
    assert plan.remote_main_anchor_id == (
        namespace.remote_main_anchor.external_id
    )
    assert plan.final_preregistration_id == (
        namespace.final_preregistration.external_id
    )
    assert plan.target_tape_namespace_id == (
        namespace.target_tape_namespace_id
    )
    assert plan.public_family_generation_id == family.generation_id
    assert document["remote_main_anchor_id"] != (
        namespace.remote_main_anchor.claim_id
    )
    assert document["final_preregistration_id"] != (
        namespace.final_preregistration.claim_id
    )

    for entry in plan.entries:
        assert (
            type(entry.occurrence_identity)
            is batch_native.V075BatchNativeOccurrenceIdentityV1
        )
        assert entry.occurrence_identity.occurrence_ordinal == (
            entry.scientific_ordinal
        )
        assert entry.occurrence_identity.context_id == entry.context_id
        assert entry.occurrence_identity.arm is entry.arm
        assert (
            entry.occurrence_identity.threshold_profile_id
            == plan.threshold_profile.threshold_profile_id
        )
        assert (
            entry.occurrence_identity.cap_profile_id
            == plan.cap_profile.cap_profile_id
        )
        if entry.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
            assert entry.source_transport_id == plan.source_transport_id
        else:
            assert entry.source_transport_id is None

    assert document["frozen_before_observation"] is True
    assert document["observer_open_calls_at_freeze"] == 0
    assert document["target_accesses_at_freeze"] == 0
    assert document["observation_batches_at_freeze"] == 0
    assert document["caller_totals_accepted"] is False
    assert document["caller_target_fields_accepted"] is False
    module_source = inspect.getsource(production_plan)
    assert "v075_private_observer_boundary" not in module_source
    assert "open_production" not in module_source


def test_tracked_source_factory_accepts_no_caller_totals_or_target_fields(
) -> None:
    signature = inspect.signature(
        production_plan.load_tracked_v075_source_prior_transport_v1
    )
    assert tuple(signature.parameters) == ("repository_root",)
    transport = (
        production_plan.load_tracked_v075_source_prior_transport_v1(
            REPOSITORY_ROOT
        )
    )
    document = transport.to_document()
    assert type(transport) is worker.V075SourcePriorTransportV1
    assert document["source_only"] is True
    assert document["proposal_only"] is True
    assert document["work_reference_only"] is True
    assert document["target_fields_present"] is False
    assert "caller_total" not in repr(document)


def test_plan_replay_is_byte_exact_and_target_free() -> None:
    namespace = _namespace()
    claimed = _plan(namespace)
    replayed, verification = (
        production_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            raw=claimed.canonical_bytes,
        )
    )
    assert replayed == claimed
    assert replayed.canonical_bytes == claimed.canonical_bytes
    assert verification.plan_id == claimed.plan_id
    assert verification.entry_ids == tuple(
        item.entry_id for item in claimed.entries
    )
    assert verification.occurrence_ids == tuple(
        item.occurrence_id for item in claimed.entries
    )
    assert verification.to_document()["target_accessed"] is False
    assert verification.to_document()["observer_open_calls"] == 0
    assert verification.to_document()["valid"] is True


@pytest.mark.parametrize(
    "mutation",
    (
        "REORDER",
        "DUPLICATE",
        "TRANSPORT_ORDINAL",
        "FOREIGN_SOURCE",
        "OLD_V072_ANCHOR",
        "CALLER_TOTAL",
    ),
)
def test_replay_rejects_order_duplicate_transplant_and_old_identity_attacks(
    mutation: str,
) -> None:
    namespace = _namespace()
    plan = _plan(namespace)
    attacked = copy.deepcopy(plan.to_document())

    if mutation == "REORDER":
        attacked["entries"][0], attacked["entries"][1] = (
            attacked["entries"][1],
            attacked["entries"][0],
        )
    elif mutation == "DUPLICATE":
        attacked["entries"][1] = copy.deepcopy(attacked["entries"][0])
    elif mutation == "TRANSPORT_ORDINAL":
        attacked["entries"][0]["transport_ordinal"] = 15
    elif mutation == "FOREIGN_SOURCE":
        foreign = _id("foreign-source-transport")
        attacked["source_transport_id"] = foreign
        attacked["entries"][0]["source_transport_id"] = foreign
        attacked["entries"][0]["occurrence_identity"][
            "source_transport_id"
        ] = foreign
    elif mutation == "OLD_V072_ANCHOR":
        attacked["remote_main_anchor_id"] = min(
            public.FORBIDDEN_HISTORICAL_TARGET_IDS
        )
    elif mutation == "CALLER_TOTAL":
        attacked["caller_online_draw_total"] = 0
    else:  # pragma: no cover
        raise AssertionError(mutation)

    with pytest.raises(
        production_plan.V075ProductionOccurrencePlanInvariantViolation
    ):
        production_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            raw=canonical_json_bytes(attacked),
        )


def test_plan_cannot_be_replayed_under_a_foreign_namespace() -> None:
    first = _namespace("first")
    second = _namespace("second")
    claimed = _plan(first)
    with pytest.raises(
        production_plan.V075ProductionOccurrencePlanInvariantViolation,
        match="transplanted",
    ):
        production_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=second,
            raw=claimed.canonical_bytes,
        )


def test_historical_v072_external_authority_is_rejected_before_plan_freeze(
) -> None:
    registry = public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    role = public.V075ExternalAuthorityRoleV1.REMOTE_MAIN_ANCHOR
    historical = min(public.FORBIDDEN_HISTORICAL_TARGET_IDS)
    message = public.external_authority_claim_signing_bytes_v1
    with pytest.raises(
        public.V075PublicCampaignAuthorityInvariantViolation,
        match="historical",
    ):
        message(
            signer_registry=registry,
            role=role,
            external_id=historical,
        )


def test_plan_factory_rejects_untyped_namespace() -> None:
    with pytest.raises(
        production_plan.V075ProductionOccurrencePlanInvariantViolation,
        match="exact current public namespace",
    ):
        production_plan.freeze_v075_production_occurrence_plan_v1(
            repository_root=REPOSITORY_ROOT,
            namespace={},  # type: ignore[arg-type]
        )
