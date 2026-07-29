from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_production_occurrence_plan_v1 as production_plan
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests.test_v075_production_occurrence_plan_v1 import (
    _namespace as _v1_namespace,
)
from tests.test_v075_public_target_tape_namespace_v2 import anchored_graph
from tests.v075_signature_test_support import make_public_key


def _root_row():
    context = (
        public.freeze_v075_public_family_generation_v1()
        .replicate_contexts[0]
    )
    catalogue = graph.root_catalogue_v1(context)
    row = graph.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    return context, row


def test_exact_v2_namespace_flows_through_public_graph_without_projection(
    anchored_graph,
) -> None:
    _root, _anchor, _commitment, namespace = anchored_graph
    context, row = _root_row()

    assert graph.validate_v075_public_graph_namespace_v2(namespace) is namespace
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    stream_set = graph.freeze_five_arm_stream_set_v1(pairing)

    assert pairing.namespace is namespace
    assert all(item.namespace is namespace for item in stream_set.streams)
    assert {
        item.target_tape_namespace_id for item in stream_set.streams
    } == {namespace.target_tape_namespace_id}
    document = pairing.to_document()
    assert (
        document["target_tape_namespace_id"]
        == namespace.target_tape_namespace_id
    )
    assert "remote_main_anchor_claim_id" not in document
    assert "final_preregistration_claim_id" not in document
    assert "observer_profile_claim_id" not in document
    assert context in namespace.family.replicate_contexts


def test_v2_namespace_freezes_and_replays_complete_production_plan(
    anchored_graph,
) -> None:
    root, anchor, _commitment, namespace = anchored_graph
    plan = (
        production_plan
        .freeze_v075_production_occurrence_plan_from_namespace_v2(
            repository_root=root,
            namespace=namespace,
        )
    )
    replayed, verification = (
        production_plan
        .verify_v075_production_occurrence_plan_bytes_from_namespace_v2(
            repository_root=root,
            namespace=namespace,
            raw=plan.canonical_bytes,
        )
    )

    assert replayed == plan
    assert verification.plan_id == plan.plan_id
    assert plan.remote_main_anchor_id == anchor.anchor_id
    assert (
        plan.final_preregistration_id
        == anchor.final_preregistration_id
    )
    assert plan.target_tape_namespace_id == namespace.target_tape_namespace_id
    assert {
        item.target_tape_namespace_id for item in plan.entries
    } == {namespace.target_tape_namespace_id}
    assert {
        item.occurrence_identity.target_tape_namespace_id
        for item in plan.entries
    } == {namespace.target_tape_namespace_id}
    document = plan.to_document()
    assert "remote_main_anchor_claim_id" not in document
    assert "final_preregistration_claim_id" not in document
    assert "observer_profile_claim_id" not in document


def test_v2_namespace_freezes_batch_native_occurrence_without_projection(
    anchored_graph,
) -> None:
    _root, _anchor, _commitment, namespace = anchored_graph
    context, _row = _root_row()
    identity = (
        batch_native
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=0,
            threshold_profile=worker.V075WorkerThresholdProfileV1(),
            cap_profile=worker.V075WorkerCapProfileV1(),
            source_prior_transport=None,
        )
    )

    assert (
        identity.target_tape_namespace_id
        == namespace.target_tape_namespace_id
    )
    assert identity.context_id == context.context_id
    assert namespace.anchor.anchor_id != identity.target_tape_namespace_id
    assert (
        namespace.anchor.final_preregistration_id
        != identity.target_tape_namespace_id
    )


def test_explicit_v2_entries_reject_v1_namespace(anchored_graph) -> None:
    root, _anchor, _commitment, _namespace = anchored_graph
    v1_namespace = _v1_namespace("v2-entry-rejection")
    context, _row = _root_row()

    with pytest.raises(
        graph.V075PublicGraphSemanticsInvariantViolation
    ):
        graph.validate_v075_public_graph_namespace_v2(v1_namespace)
    with pytest.raises(
        production_plan.V075ProductionOccurrencePlanInvariantViolation
    ):
        (
            production_plan
            .freeze_v075_production_occurrence_plan_from_namespace_v2(
                repository_root=root,
                namespace=v1_namespace,
            )
        )
    with pytest.raises(
        batch_native.V075BatchNativeBackendInvariantViolation
    ):
        (
            batch_native
            .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
                namespace=v1_namespace,
                context=context,
                arm=worker.V075WorkerArmV1.NO_PRIOR,
                occurrence_ordinal=0,
                threshold_profile=worker.V075WorkerThresholdProfileV1(),
                cap_profile=worker.V075WorkerCapProfileV1(),
                source_prior_transport=None,
            )
        )


def test_duck_and_subclass_namespace_transplants_fail(anchored_graph) -> None:
    root, _anchor, _commitment, namespace = anchored_graph
    context, row = _root_row()
    duck = SimpleNamespace(
        family=namespace.family,
        signer_registry=namespace.signer_registry,
        anchor=namespace.anchor,
        target_tape_namespace_id=namespace.target_tape_namespace_id,
        to_document=namespace.to_document,
    )

    class NamespaceSubclass(namespace_v2.V075PublicTargetTapeNamespaceV2):
        pass

    subclass = object.__new__(NamespaceSubclass)
    for attacked in (duck, subclass):
        with pytest.raises(
            graph.V075PublicGraphSemanticsInvariantViolation
        ):
            graph.derive_shared_support_epoch_v1(
                namespace=attacked,
                row_binding=row,
                epoch_index=0,
                evidence=(),
            )
        with pytest.raises(
            batch_native.V075BatchNativeBackendInvariantViolation
        ):
            batch_native.freeze_v075_batch_native_occurrence_identity_v1(
                namespace=attacked,
                context=context,
                arm=worker.V075WorkerArmV1.NO_PRIOR,
                occurrence_ordinal=0,
                threshold_profile=worker.V075WorkerThresholdProfileV1(),
                cap_profile=worker.V075WorkerCapProfileV1(),
                source_prior_transport=None,
            )
        with pytest.raises(
            production_plan.V075ProductionOccurrencePlanInvariantViolation
        ):
            production_plan.freeze_v075_production_occurrence_plan_v1(
                repository_root=root,
                namespace=attacked,
            )


def test_exact_v2_object_with_cross_role_registry_is_rejected(
    anchored_graph,
) -> None:
    root, _anchor, _commitment, namespace = anchored_graph
    corrupted = object.__new__(
        namespace_v2.V075PublicTargetTapeNamespaceV2
    )
    for item in fields(namespace):
        object.__setattr__(
            corrupted,
            item.name,
            getattr(namespace, item.name),
        )
    wrong_registry = public.V075TrustedSignerRegistryV1(
        public.V075RSAPublicVerificationKeyV1(
            "CAMPAIGN_AUTHORITY",
            make_public_key("CAMPAIGN_AUTHORITY").modulus,
            public_exponent=65_539,
        ),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    object.__setattr__(corrupted, "signer_registry", wrong_registry)
    context, row = _root_row()

    with pytest.raises(
        graph.V075PublicGraphSemanticsInvariantViolation
    ):
        graph.derive_shared_support_epoch_v1(
            namespace=corrupted,
            row_binding=row,
            epoch_index=0,
            evidence=(),
        )
    with pytest.raises(
        batch_native.V075BatchNativeBackendInvariantViolation
    ):
        batch_native.freeze_v075_batch_native_occurrence_identity_v1(
            namespace=corrupted,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=0,
            threshold_profile=worker.V075WorkerThresholdProfileV1(),
            cap_profile=worker.V075WorkerCapProfileV1(),
            source_prior_transport=None,
        )
    with pytest.raises(
        production_plan.V075ProductionOccurrencePlanInvariantViolation
    ):
        production_plan.freeze_v075_production_occurrence_plan_v1(
            repository_root=root,
            namespace=corrupted,
        )
