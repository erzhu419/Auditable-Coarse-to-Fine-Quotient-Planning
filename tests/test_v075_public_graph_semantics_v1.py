from __future__ import annotations

import ast
from dataclasses import fields, replace
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_public_graph_semantics_v1 as public
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _test_laws() -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    # Synthetic unit-test material only; no production law lives in source.
    return (
        ((1, Fraction(1)),),
        ((1, Fraction(1)),),
        ((1, Fraction(1)),),
    )


def _namespace(
    marker: str = "one",
) -> authority.V075PublicTargetTapeNamespaceV1:
    family = authority.freeze_v075_public_family_generation_v1()
    commitment = authority.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=hashlib.sha256(
            ("test-salt-" + marker).encode("utf-8")
        ).digest(),
        secret_laws=_test_laws(),
    )
    role = authority.V075ExternalAuthorityRoleV1
    registry = authority.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )

    def claim(
        claim_role: authority.V075ExternalAuthorityRoleV1,
        external_id: str,
    ) -> authority.V075SignedExternalAuthorityClaimV1:
        message = authority.external_authority_claim_signing_bytes_v1(
            signer_registry=registry,
            role=claim_role,
            external_id=external_id,
        )
        return authority.V075SignedExternalAuthorityClaimV1(
            registry,
            claim_role,
            external_id,
            sign_test_message(message),
        )

    return authority.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=claim(
            role.REMOTE_MAIN_ANCHOR,
            _id("anchor-" + marker),
        ),
        final_preregistration=claim(
            role.FINAL_PREREGISTRATION,
            _id("prereg-" + marker),
        ),
        observer_profile=claim(
            role.OBSERVER_PROFILE,
            _id("observer-" + marker),
        ),
    )


def _root_row(
    *,
    context_index: int = 0,
) -> tuple[
    authority.V075PublicReplicateContextV1,
    public.V075LegalActionCatalogueV1,
    public.V075ObservationRowBindingV1,
]:
    context = (
        authority.freeze_v075_public_family_generation_v1()
        .replicate_contexts[context_index]
    )
    catalogue = public.root_catalogue_v1(context)
    row = public.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    return context, catalogue, row


def _bootstrap_pairing(
    *,
    namespace: authority.V075PublicTargetTapeNamespaceV1 | None = None,
    context_index: int = 0,
) -> public.V075FiveArmPairingAuthorityV1:
    selected_namespace = _namespace() if namespace is None else namespace
    _, _, row = _root_row(context_index=context_index)
    root = public.derive_shared_support_epoch_v1(
        namespace=selected_namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = public.freeze_shared_support_chain_v1(
        namespace=selected_namespace,
        row_binding=row,
        epochs=(root,),
    )
    return public.freeze_five_arm_pairing_authority_v1(
        namespace=selected_namespace,
        row_binding=row,
        support_chain=chain,
    )


def _support_evidence(
    *,
    namespace: authority.V075PublicTargetTapeNamespaceV1,
    row: public.V075ObservationRowBindingV1,
    marker: str,
    draw_index: int = 1,
) -> public.V075SupportEvidenceV1:
    message = public.support_evidence_signing_bytes_v1(
        namespace=namespace,
        row_binding=row,
        observed_state=row.catalogue.state,
        source_observer_epoch_index=0,
        accepted_draw_index=draw_index,
    )
    return public.bind_support_evidence_v1(
        namespace=namespace,
        row_binding=row,
        observed_state=row.catalogue.state,
        source_observer_epoch_index=0,
        accepted_draw_index=draw_index,
        observer_signature_hex=sign_test_message(
            message,
            key_role="OBSERVER_EVIDENCE",
        ),
    )


def _promoted_pairing(
    *,
    marker: str,
) -> public.V075FiveArmPairingAuthorityV1:
    namespace = _namespace()
    _, _, row = _root_row()
    root = public.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    promoted = public.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=(
            _support_evidence(
                namespace=namespace,
                row=row,
                marker=marker,
                draw_index=1 if marker == "first" else 2,
            ),
        ),
        parent=root,
    )
    chain = public.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root, promoted),
    )
    return public.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )


def test_public_root_catalogue_and_row_are_complete_typed_graphs() -> None:
    family = authority.freeze_v075_public_family_generation_v1()
    for context in family.replicate_contexts:
        catalogue = public.root_catalogue_v1(context)
        row = public.observation_row_binding_v1(
            context,
            catalogue,
            catalogue.actions[0],
        )
        assert catalogue.context is context
        assert catalogue.state.context is context
        assert catalogue.actions
        assert row.context is context
        assert row.catalogue is catalogue
        assert row.state_id == catalogue.state.state_id
        assert row.remaining_horizon == catalogue.remaining_horizon == 2
        assert row.action in catalogue.actions
        assert "v072" not in row.to_document()["schema"]


def test_one_shared_pairing_lineage_freezes_all_five_arms() -> None:
    pairing = _bootstrap_pairing()
    stream_set = public.freeze_five_arm_stream_set_v1(pairing)
    assert tuple(stream.arm for stream in stream_set.streams) == (
        authority.ARM_ORDER
    )
    assert len(
        {stream.pairing_group_id for stream in stream_set.streams}
    ) == 1
    assert len({stream.seed for stream in stream_set.streams}) == 1
    assert len({stream.stream_id for stream in stream_set.streams}) == 5
    assert all(
        stream.pairing_lineage_id
        == pairing.support_chain.leaf.pairing_lineage_id
        for stream in stream_set.streams
    )


def test_fresh_namespace_changes_pairing_group_and_seed() -> None:
    first = public.freeze_five_arm_stream_set_v1(
        _bootstrap_pairing(namespace=_namespace("a"))
    ).streams[0]
    second = public.freeze_five_arm_stream_set_v1(
        _bootstrap_pairing(namespace=_namespace("b"))
    ).streams[0]
    assert first.pairing_group_id != second.pairing_group_id
    assert first.seed != second.seed


def test_worker_metadata_cannot_enter_stream_identity() -> None:
    stream = public.freeze_five_arm_stream_set_v1(
        _bootstrap_pairing()
    ).streams[0]
    document = stream.to_document()
    signature = inspect.signature(
        public.derive_transition_stream_identity_v1
    )
    assert tuple(signature.parameters) == ("pairing_authority", "arm")
    assert document["seed_serialized"] is False
    assert document["target_observer_open_authority"] is False
    assert document["pairing_authority"][
        "raw_word_pairing_key_id"
    ]
    assert "worker_count" not in repr(document)
    assert "worker_pid" not in repr(document)


def test_support_promotion_is_evidence_bound_and_arm_free() -> None:
    pairing = _promoted_pairing(marker="first")
    leaf = pairing.support_chain.leaf
    stream_set = public.freeze_five_arm_stream_set_v1(pairing)
    assert leaf.epoch_index == 1
    assert leaf.required_lane is public.V075ObservationLaneV1.VALIDATION
    assert leaf.evidence
    evidence_document = leaf.evidence[0].to_document()
    assert evidence_document["observer_signature_verified"] is True
    assert evidence_document["signature_scope"] == (
        "REGISTRY_RELATIVE_PROVENANCE_ONLY"
    )
    assert evidence_document["production_observation_authorized"] is False
    assert leaf.to_document()["shared_by_arms"] == list(
        authority.ARM_ORDER
    )
    assert len({stream.seed for stream in stream_set.streams}) == 1
    assert all(
        stream.pairing_lineage_id == leaf.pairing_lineage_id
        for stream in stream_set.streams
    )


def test_arbitrary_cid_or_campaign_signature_cannot_mint_support_evidence() -> None:
    namespace = _namespace()
    _, _, row = _root_row()
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.bind_support_evidence_v1(
            namespace=namespace,
            row_binding=row,
            observed_state=row.catalogue.state,
            source_observer_epoch_index=0,
            accepted_draw_index=1,
            observer_signature_hex="00" * 256,
        )

    message = public.support_evidence_signing_bytes_v1(
        namespace=namespace,
        row_binding=row,
        observed_state=row.catalogue.state,
        source_observer_epoch_index=0,
        accepted_draw_index=1,
    )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.bind_support_evidence_v1(
            namespace=namespace,
            row_binding=row,
            observed_state=row.catalogue.state,
            source_observer_epoch_index=0,
            accepted_draw_index=1,
            observer_signature_hex=sign_test_message(
                message,
                key_role="CAMPAIGN_AUTHORITY",
            ),
        )

    alternate_row = public.observation_row_binding_v1(
        row.context,
        row.catalogue,
        row.catalogue.actions[1],
    )
    observer_signature = sign_test_message(
        message,
        key_role="OBSERVER_EVIDENCE",
    )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.bind_support_evidence_v1(
            namespace=namespace,
            row_binding=alternate_row,
            observed_state=alternate_row.catalogue.state,
            source_observer_epoch_index=0,
            accepted_draw_index=1,
            observer_signature_hex=observer_signature,
        )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.bind_support_evidence_v1(
            namespace=namespace,
            row_binding=row,
            observed_state=row.catalogue.state,
            source_observer_epoch_index=0,
            accepted_draw_index=2,
            observer_signature_hex=observer_signature,
        )


def test_support_change_cannot_reroll_raw_word_crn() -> None:
    first = public.freeze_five_arm_stream_set_v1(
        _promoted_pairing(marker="first")
    ).streams[0]
    second = public.freeze_five_arm_stream_set_v1(
        _promoted_pairing(marker="second")
    ).streams[0]
    assert first.pairing_lineage_id != second.pairing_lineage_id
    assert first.stream_id != second.stream_id
    assert first.pairing_group_id == second.pairing_group_id
    assert first.seed == second.seed


def test_arm_lineage_drift_is_rejected() -> None:
    pairing = _bootstrap_pairing()
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        replace(pairing, arms=tuple(reversed(authority.ARM_ORDER)))
    stream_set = public.freeze_five_arm_stream_set_v1(pairing)
    drifted = replace(
        stream_set.streams[0],
        arm=authority.ARM_ORDER[1],
    )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        replace(
            stream_set,
            streams=(drifted, *stream_set.streams[1:]),
        )


def test_bootstrap_parent_and_members_are_rejected() -> None:
    namespace = _namespace()
    _, _, row = _root_row()
    root = public.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.derive_shared_support_epoch_v1(
            namespace=namespace,
            row_binding=row,
            epoch_index=0,
            evidence=(),
            parent=root,
        )
    evidence = _support_evidence(
        namespace=namespace,
        row=row,
        marker="bootstrap",
    )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.derive_shared_support_epoch_v1(
            namespace=namespace,
            row_binding=row,
            epoch_index=0,
            evidence=(evidence,),
        )


def test_fake_state_action_and_horizon_cannot_enter_row() -> None:
    context, catalogue, row = _root_row()
    row_fields = {field.name for field in fields(row)}
    assert row_fields == {"context", "catalogue", "action"}
    assert {
        "state_id",
        "catalogue_id",
        "remaining_horizon",
    }.isdisjoint(row_fields)

    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.V075ObservationRowBindingV1(
            context,
            catalogue,
            (4, 6, 4),
        )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.V075SymbolicGraphStateV1(
            context,
            (1, 1),
            False,
        )

    other_context = (
        authority.freeze_v075_public_family_generation_v1()
        .replicate_contexts[1]
    )
    other_catalogue = public.root_catalogue_v1(other_context)
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.V075ObservationRowBindingV1(
            context,
            other_catalogue,
            other_catalogue.actions[0],
        )

    horizon_one = replace(catalogue, remaining_horizon=1)
    horizon_one_row = public.V075ObservationRowBindingV1(
        context,
        horizon_one,
        horizon_one.actions[0],
    )
    assert horizon_one_row.remaining_horizon == 1
    assert horizon_one_row.row_binding_id != row.row_binding_id


def test_id_only_and_v072_identity_laundering_are_rejected() -> None:
    old_v072_id = (
        "966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26"
    )
    with pytest.raises(
        authority.V075PublicCampaignAuthorityInvariantViolation
    ):
        registry = authority.V075TrustedSignerRegistryV1(
            make_public_key("CAMPAIGN_AUTHORITY"),
            make_public_key("OBSERVER_EVIDENCE"),
        )
        authority.external_authority_claim_signing_bytes_v1(
            signer_registry=registry,
            role=authority.V075ExternalAuthorityRoleV1.OBSERVER_PROFILE,
            external_id=old_v072_id,
        )

    context, catalogue, _ = _root_row()
    with pytest.raises(TypeError):
        public.V075ObservationRowBindingV1(
            context_id=context.context_id,
            catalogue_id=catalogue.catalogue_id,
            state_id=_id("fake-state"),
            remaining_horizon=1,
            action=(4, 6, 4),
        )
    with pytest.raises(TypeError):
        public.V075TransitionStreamIdentityV1(
            target_tape_namespace_id=old_v072_id,
            context_id=old_v072_id,
            row_binding_id=old_v072_id,
            catalogue_id=old_v072_id,
            support_epoch_id=old_v072_id,
            support_chain_id=old_v072_id,
            pairing_lineage_id=old_v072_id,
            observer_epoch_index=0,
            lane=public.V075ObservationLaneV1.DISCOVERY,
            arm=authority.ARM_ORDER[0],
            action=(0, 1, 0),
        )


def test_raw_member_ids_cannot_create_or_reroll_support() -> None:
    namespace = _namespace()
    _, _, row = _root_row()
    with pytest.raises(TypeError):
        public.derive_shared_support_epoch_v1(
            namespace=namespace,
            row_binding=row,
            epoch_index=1,
            member_ids=(_id("caller-selected-member"),),
            parent=None,
        )


def test_public_dependency_graph_contains_no_exposed_law_authority() -> None:
    public_source = inspect.getsource(public)
    authority_source = inspect.getsource(authority)
    combined = public_source + authority_source
    assert "v075_fresh_campaign_authority_v1" not in combined
    assert "_HIDDEN_LAW_SPECS" not in combined
    assert "freeze_v075_environment_manifest_v1" not in combined
    assert "V075HiddenSpawnLawV1" not in combined
    assert "991, 1_000" not in combined
    assert "197, 200" not in combined
    assert "393, 400" not in combined
    assert public.public_authority is authority


def test_transitive_public_dependency_graph_excludes_construction_authority() -> None:
    package = Path(public.__file__).resolve().parent
    pending = [
        Path(public.__file__).resolve(),
        Path(authority.__file__).resolve(),
    ]
    visited: set[Path] = set()
    imported_modules: set[str] = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            candidates: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module == "acfqp":
                candidates.extend(alias.name for alias in node.names)
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.startswith("acfqp.")
            ):
                candidates.append(node.module.split(".", 1)[1])
            elif isinstance(node, ast.Import):
                candidates.extend(
                    alias.name.split(".", 1)[1]
                    for alias in node.names
                    if alias.name.startswith("acfqp.")
                )
            for candidate in candidates:
                module = candidate.split(".", 1)[0]
                imported_modules.add(module)
                dependency = package / f"{module}.py"
                if dependency.is_file() and dependency not in visited:
                    pending.append(dependency)
    assert "v075_fresh_campaign_authority_v1" not in imported_modules


def test_public_layer_cannot_open_hidden_kernel() -> None:
    context = (
        authority.freeze_v075_public_family_generation_v1()
        .replicate_contexts[0]
    )
    with pytest.raises(public.V075PublicGraphSemanticsInvariantViolation):
        public.public_h2_kernel_without_hidden_law_v1(context)
