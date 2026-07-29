from __future__ import annotations

from dataclasses import fields
import hashlib
from typing import Any

import pytest

from acfqp import v072_cold_h2_closure_v1 as closure
from acfqp import (
    v072_cold_h2_closure_independent_verifier_v1 as independent,
)
from acfqp import v072_synthetic_row_observation_adapter_v1 as row_adapter
from acfqp import partial_support_confidence_v2 as confidence_v2
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp.phase3e_ids import canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


CONTEXT_ID = _id("disjoint-cold-h2-synthetic-context")
CONTEXT_KEY = "disjoint_cold_h2_synthetic_context_v1"
DEVELOPMENT_SCOPE_ID = _id("disjoint-cold-h2-development-scope")
ROOT = "root"
CHILD_A = "child-a"
CHILD_B = "child-b"
NOVEL_ONLY = "validation-novel-only"


def _state(label: str) -> closure.ColdPublicStateV1:
    return closure.ColdPublicStateV1(
        _id(f"semantic-state:{label}"),
        {
            "schema": "test.disjoint_cold_h2_state.v1",
            "label": label,
            "registered_target": False,
        },
    )


def _action(state_label: str, index: int) -> closure.ColdPublicActionV1:
    return closure.ColdPublicActionV1(
        _id(f"semantic-action:{state_label}:{index}"),
        {
            "schema": "test.disjoint_cold_h2_action.v1",
            "state_label": state_label,
            "index": index,
            "registered_target": False,
        },
    )


def _legal_action_count(label: str) -> int:
    return {
        ROOT: 2,
        CHILD_A: 2,
        CHILD_B: 1,
        NOVEL_ONLY: 1,
    }[label]


def _synthetic_cap(
    total_physical_row_cap: int = 8,
) -> closure.ColdH2ContextTotalRowCapEvidenceV1:
    return closure.development_synthetic_cold_h2_cap_evidence_v1(
        context_id=CONTEXT_ID,
        context_key=CONTEXT_KEY,
        total_physical_row_cap=total_physical_row_cap,
        development_scope_id=DEVELOPMENT_SCOPE_ID,
    )


def _label(state: closure.ColdPublicStateV1) -> str:
    return str(state.document["label"])


class BuilderSyntheticPublicGraph:
    """Construction semantics; contains no transition or sampling method."""

    context_id = CONTEXT_ID
    horizon = 2

    def root_state_v1(self) -> closure.ColdPublicStateV1:
        return _state(ROOT)

    def canonical_state_v1(
        self,
        state: closure.ColdPublicStateV1,
    ) -> closure.ColdPublicStateV1:
        return _state(_label(state))

    def legal_actions_v1(
        self,
        state: closure.ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[closure.ColdPublicActionV1, ...]:
        label = _label(state)
        assert remaining_horizon == (2 if label == ROOT else 1)
        return tuple(
            _action(label, index)
            for index in range(_legal_action_count(label))
        )


class IndependentSyntheticPublicGraph:
    """Separately written public replay used only by the verifier."""

    @property
    def context_id(self) -> str:
        return CONTEXT_ID

    @property
    def horizon(self) -> int:
        return 2

    def root_state_v1(self) -> closure.ColdPublicStateV1:
        return _state("".join(("ro", "ot")))

    def canonical_state_v1(
        self,
        state: closure.ColdPublicStateV1,
    ) -> closure.ColdPublicStateV1:
        label = state.document.get("label")
        if label not in {ROOT, CHILD_A, CHILD_B, NOVEL_ONLY}:
            raise AssertionError("unknown public synthetic state")
        return _state(str(label))

    def legal_actions_v1(
        self,
        state: closure.ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[closure.ColdPublicActionV1, ...]:
        label = str(state.document["label"])
        counts = (2, 2, 1, 1)
        labels = (ROOT, CHILD_A, CHILD_B, NOVEL_ONLY)
        count = counts[labels.index(label)]
        expected_horizon = 2 if labels.index(label) == 0 else 1
        if remaining_horizon != expected_horizon:
            raise AssertionError("public horizon mismatch")
        return tuple(_action(label, position) for position in range(count))


def _terminal_descriptor(label: str) -> closure.ColdOutcomeDescriptorV1:
    return closure.ColdOutcomeDescriptorV1(
        _id(f"semantic-descriptor:terminal:{label}"),
        failure=False,
        terminal=True,
        successor_state=None,
        document={
            "schema": "test.disjoint_cold_h2_outcome.v1",
            "kind": "terminal",
            "label": label,
        },
    )


def _active_descriptor(label: str) -> closure.ColdOutcomeDescriptorV1:
    return closure.ColdOutcomeDescriptorV1(
        _id(f"semantic-descriptor:active:{label}"),
        failure=False,
        terminal=False,
        successor_state=_state(label),
        document={
            "schema": "test.disjoint_cold_h2_outcome.v1",
            "kind": "active",
            "label": label,
        },
    )


def _row(
    state_label: str,
    horizon: int,
    action_index: int,
    *,
    discovery: tuple[closure.ColdOutcomeDescriptorV1, ...],
    novel: tuple[closure.ColdOutcomeDescriptorV1, ...] = (),
) -> closure.ColdRowEvidenceV1:
    label = f"{state_label}:{horizon}:{action_index}"
    return closure.ColdRowEvidenceV1(
        CONTEXT_ID,
        _state(state_label),
        horizon,
        _action(state_label, action_index),
        tuple(
            sorted(
                discovery,
                key=lambda item: item.descriptor_record_id,
            )
        ),
        tuple(
            sorted(novel, key=lambda item: item.descriptor_record_id)
        ),
        _id(f"support-epoch:{label}"),
        _id(f"confidence-snapshot:{label}"),
        _id(f"row-replay-verification:{label}"),
        _id(f"physical-evidence:{label}"),
        closure.ColdRowNativeWorkV1(
            discovery_random_word_calls=65,
            validation_random_word_calls=2_050,
            discovery_rejections=1,
            validation_rejections=2,
        ),
    )


@pytest.fixture(scope="module")
def synthetic_inventory() -> tuple[closure.ColdRowEvidenceV1, ...]:
    rows = (
        _row(
            ROOT,
            2,
            0,
            discovery=(
                _active_descriptor(CHILD_A),
                _terminal_descriptor("root-a-success"),
            ),
            novel=(_active_descriptor(NOVEL_ONLY),),
        ),
        _row(
            ROOT,
            2,
            1,
            discovery=(_active_descriptor(CHILD_B),),
        ),
        _row(
            CHILD_A,
            1,
            0,
            discovery=(_terminal_descriptor("child-a-0-success"),),
        ),
        _row(
            CHILD_A,
            1,
            1,
            discovery=(_terminal_descriptor("child-a-1-success"),),
        ),
        _row(
            CHILD_B,
            1,
            0,
            discovery=(_terminal_descriptor("child-b-0-success"),),
        ),
    )
    return tuple(sorted(rows, key=lambda item: item.row_evidence_id))


@pytest.fixture(scope="module")
def synthetic_bundle(
    synthetic_inventory: tuple[closure.ColdRowEvidenceV1, ...],
) -> closure.V072ColdH2ClosureBundleV1:
    return closure.freeze_v072_cold_h2_closure_v1(
        public_graph=BuilderSyntheticPublicGraph(),
        row_evidence=synthetic_inventory,
        logical_occurrence_id=_id("synthetic-logical-occurrence"),
        arm="NO_PRIOR",
        cap_evidence=_synthetic_cap(),
    )


def _unsafe_clone(value: Any, **changes: Any) -> Any:
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            result,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return result


class SyntheticRowProtocolAdapter:
    """Test-only adapter; it carries no development-sampler role."""

    def __init__(self, row: closure.ColdRowEvidenceV1) -> None:
        self._row = row

    @property
    def context_id(self):
        return self._row.context_id

    @property
    def state(self):
        return self._row.state

    @property
    def remaining_horizon(self):
        return self._row.remaining_horizon

    @property
    def action(self):
        return self._row.action

    @property
    def discovery_support(self):
        return self._row.discovery_support

    @property
    def validation_novel(self):
        return self._row.validation_novel

    @property
    def support_epoch_id(self):
        return self._row.support_epoch_id

    @property
    def confidence_snapshot_id(self):
        return self._row.confidence_snapshot_id

    @property
    def row_replay_verification_id(self):
        return self._row.row_replay_verification_id

    @property
    def physical_evidence_id(self):
        return self._row.physical_evidence_id

    @property
    def native_work(self):
        return self._row.native_work

    @property
    def discovery_frozen(self):
        return self._row.discovery_frozen

    @property
    def validation_novel_separate(self):
        return self._row.validation_novel_separate

    @property
    def route_independent_physical_evidence(self):
        return self._row.route_independent_physical_evidence


def _verify(
    inventory: tuple[closure.ColdRowEvidenceV1, ...],
    bundle: closure.V072ColdH2ClosureBundleV1,
):
    return independent.verify_v072_cold_h2_closure_independently_v1(
        public_graph=IndependentSyntheticPublicGraph(),
        authoritative_row_evidence=inventory,
        claimed=bundle,
    )


def test_cold_closure_is_complete_shared_and_independently_replayable(
    synthetic_inventory,
    synthetic_bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("production closure derivation was called")

    for name in (
        "freeze_v072_cold_h2_closure_v1",
        "_catalogue_from_public_semantics",
        "_discovery_child_states",
        "_aggregate_native_counters",
        "_bundle_core_payload",
        "registered_confirmatory_cold_h2_cap_registry_v1",
        "verify_total_physical_row_cap_v1",
        "cold_h2_consumer_profile_for_arm_v1",
        "_consumer_routes_for_arm",
        "_public_total_row_cap_key",
        "_public_total_row_cap_binding_id",
    ):
        monkeypatch.setattr(closure, name, forbidden)
    verification = _verify(synthetic_inventory, synthetic_bundle)
    assert verification.valid
    assert verification.root_row_count == 2
    assert verification.child_state_count == 2
    assert verification.child_row_count == 3
    assert {
        _label(item) for item in synthetic_bundle.child_states
    } == {CHILD_A, CHILD_B}
    assert NOVEL_ONLY not in {
        _label(item) for item in synthetic_bundle.child_states
    }
    assert synthetic_bundle.counters.total_draws == 5 * (64 + 2_048)
    assert synthetic_bundle.counters.planner_calls == 0
    assert synthetic_bundle.counters.audit_calls == 0
    assert synthetic_bundle.counters.kernel_calls == 0
    assert synthetic_bundle.counters.hidden_law_queries == 0
    assert synthetic_bundle.shared_charge.consumer_routes == (
        "DIRECT",
        "QUOTIENT",
    )
    assert synthetic_bundle.shared_charge.native_physical_charge_count == 1
    assert verification.closure_id == (
        synthetic_bundle.shared_charge.physical_bundle_id
    )


def test_generic_row_protocol_adapter_freezes_the_same_bundle(
    synthetic_inventory,
    synthetic_bundle,
) -> None:
    adapted = closure.freeze_v072_cold_h2_closure_v1(
        public_graph=BuilderSyntheticPublicGraph(),
        row_evidence=tuple(
            SyntheticRowProtocolAdapter(item)
            for item in synthetic_inventory
        ),
        logical_occurrence_id=_id("synthetic-logical-occurrence"),
        arm="NO_PRIOR",
        cap_evidence=_synthetic_cap(),
    )
    assert adapted == synthetic_bundle
    assert adapted.closure_id == synthetic_bundle.closure_id
    verification = _verify(synthetic_inventory, adapted)
    assert verification.document_digest == hashlib.sha256(
        b"acfqp:v072-cold-h2-independent-document:v1\x00"
        + canonical_json_bytes(adapted.to_document())
    ).hexdigest()


@pytest.mark.parametrize(
    ("field_name", "mutation"),
    (
        ("root_rows", lambda values: values[:-1]),
        ("root_rows", lambda values: (*values, values[0])),
        ("child_rows", lambda values: values[:-1]),
        ("child_rows", lambda values: (*values, values[0])),
    ),
)
def test_missing_or_extra_root_and_child_rows_are_rejected(
    synthetic_inventory,
    synthetic_bundle,
    field_name,
    mutation,
) -> None:
    forged = _unsafe_clone(
        synthetic_bundle,
        **{
            field_name: tuple(
                mutation(getattr(synthetic_bundle, field_name))
            )
        },
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="row inventory",
    ):
        _verify(synthetic_inventory, forged)


def test_incomplete_catalogue_and_validation_novel_expansion_are_rejected(
    synthetic_inventory,
    synthetic_bundle,
) -> None:
    incomplete_root = _unsafe_clone(
        synthetic_bundle.root_catalogue,
        actions=synthetic_bundle.root_catalogue.actions[:-1],
    )
    incomplete = _unsafe_clone(
        synthetic_bundle,
        root_catalogue=incomplete_root,
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="root state/catalogue",
    ):
        _verify(synthetic_inventory, incomplete)

    novel_state = _state(NOVEL_ONLY)
    novel_catalogue = closure.ColdPublicCatalogueV1(
        CONTEXT_ID,
        novel_state,
        1,
        (_action(NOVEL_ONLY, 0),),
    )
    expanded = _unsafe_clone(
        synthetic_bundle,
        child_states=tuple(
            sorted(
                (*synthetic_bundle.child_states, novel_state),
                key=lambda item: item.state_record_id,
            )
        ),
        child_catalogues=tuple(
            sorted(
                (*synthetic_bundle.child_catalogues, novel_catalogue),
                key=lambda item: item.catalogue_id,
            )
        ),
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="validation novelty",
    ):
        _verify(synthetic_inventory, expanded)

    novel_row = _row(
        NOVEL_ONLY,
        1,
        0,
        discovery=(_terminal_descriptor("novel-success"),),
    )
    with pytest.raises(
        closure.V072ColdH2ClosureInvariantViolation,
        match="extra/non-discovery",
    ):
        closure.freeze_v072_cold_h2_closure_v1(
            public_graph=BuilderSyntheticPublicGraph(),
            row_evidence=tuple(
                sorted(
                    (*synthetic_inventory, novel_row),
                    key=lambda item: item.row_evidence_id,
                )
            ),
            logical_occurrence_id=_id("novel-expansion-attempt"),
            arm="NO_PRIOR",
            cap_evidence=_synthetic_cap(),
        )


def test_state_row_transplant_and_fabricated_support_are_rejected(
    synthetic_inventory,
    synthetic_bundle,
) -> None:
    old_child = synthetic_bundle.child_rows[0]
    transplanted = _unsafe_clone(
        old_child,
        state=_state(CHILD_B),
    )
    transplanted_bundle = _unsafe_clone(
        synthetic_bundle,
        child_rows=tuple(
            sorted(
                (
                    transplanted if item is old_child else item
                    for item in synthetic_bundle.child_rows
                ),
                key=lambda item: item.row_evidence_id,
            )
        ),
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="row inventory",
    ):
        _verify(synthetic_inventory, transplanted_bundle)

    old_root = synthetic_bundle.root_rows[0]
    fabricated_descriptor = _active_descriptor(NOVEL_ONLY)
    fabricated_row = _unsafe_clone(
        old_root,
        discovery_support=tuple(
            sorted(
                (*old_root.discovery_support, fabricated_descriptor),
                key=lambda item: item.descriptor_record_id,
            )
        ),
    )
    fabricated_bundle = _unsafe_clone(
        synthetic_bundle,
        root_rows=tuple(
            sorted(
                (
                    fabricated_row if item is old_root else item
                    for item in synthetic_bundle.root_rows
                ),
                key=lambda item: item.row_evidence_id,
            )
        ),
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="row inventory|child closure|support/novel",
    ):
        _verify(synthetic_inventory, fabricated_bundle)


def test_duplicate_charge_and_arm_route_transplants_are_rejected(
    synthetic_inventory,
    synthetic_bundle,
) -> None:
    duplicate_charge = _unsafe_clone(
        synthetic_bundle.shared_charge,
        native_physical_charge_count=2,
    )
    forged = _unsafe_clone(
        synthetic_bundle,
        shared_charge=duplicate_charge,
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="duplicated|mischarged",
    ):
        _verify(synthetic_inventory, forged)

    transplanted_routes = _unsafe_clone(
        synthetic_bundle.shared_charge,
        consumer_routes=("DIRECT",),
    )
    forged_routes = _unsafe_clone(
        synthetic_bundle,
        shared_charge=transplanted_routes,
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="duplicated|mischarged",
    ):
        _verify(synthetic_inventory, forged_routes)

    transplanted_arm = _unsafe_clone(
        synthetic_bundle,
        arm="MATCHED_DIRECT_GROUND",
    )
    with pytest.raises(
        independent.V072ColdH2IndependentVerificationViolation,
        match="arm/consumer profile",
    ):
        _verify(synthetic_inventory, transplanted_arm)


def test_matched_direct_arm_has_no_quotient_charge(
    synthetic_inventory,
) -> None:
    bundle = closure.freeze_v072_cold_h2_closure_v1(
        public_graph=BuilderSyntheticPublicGraph(),
        row_evidence=synthetic_inventory,
        logical_occurrence_id=_id("matched-direct-logical-occurrence"),
        arm="MATCHED_DIRECT_GROUND",
        cap_evidence=_synthetic_cap(),
    )
    assert bundle.consumer_profile.consumer_routes == ("DIRECT",)
    assert bundle.shared_charge.consumer_routes == ("DIRECT",)
    assert bundle.shared_charge.native_physical_charge_count == 1
    assert _verify(synthetic_inventory, bundle).valid


@pytest.mark.parametrize(
    ("context_key", "rejected_total"),
    (
        ("heldout_graph_w7_confirmatory_v1", 49),
        ("heldout_graph_k7_confirmatory_v1", 97),
        ("heldout_graph_k7_minus_two_confirmatory_v1", 97),
    ),
)
def test_registered_context_total_row_cap_attacks_are_rejected(
    context_key,
    rejected_total,
) -> None:
    registry = closure.registered_confirmatory_cold_h2_cap_registry_v1()
    evidence = next(
        item
        for item in registry.context_cap_evidence
        if item.context_key == context_key
    )
    closure.verify_total_physical_row_cap_v1(
        evidence,
        evidence.total_physical_row_cap,
    )
    with pytest.raises(
        closure.V072ColdH2ClosureInvariantViolation,
        match="context total cap",
    ):
        closure.verify_total_physical_row_cap_v1(
            evidence,
            rejected_total,
        )


def test_total_cap_is_checked_only_after_complete_inventory(
    synthetic_inventory,
) -> None:
    with pytest.raises(
        closure.V072ColdH2ClosureInvariantViolation,
        match="context total cap",
    ):
        closure.freeze_v072_cold_h2_closure_v1(
            public_graph=BuilderSyntheticPublicGraph(),
            row_evidence=synthetic_inventory,
            logical_occurrence_id=_id("total-cap-four-occurrence"),
            arm="NO_PRIOR",
            cap_evidence=_synthetic_cap(4),
        )


def test_cap_context_transplant_and_synthetic_impersonation_are_rejected(
    synthetic_inventory,
) -> None:
    registry = closure.registered_confirmatory_cold_h2_cap_registry_v1()
    w7 = next(
        item
        for item in registry.context_cap_evidence
        if item.context_key == "heldout_graph_w7_confirmatory_v1"
    )
    with pytest.raises(
        closure.V072ColdH2ClosureInvariantViolation,
        match="transplanted across contexts",
    ):
        closure.freeze_v072_cold_h2_closure_v1(
            public_graph=BuilderSyntheticPublicGraph(),
            row_evidence=synthetic_inventory,
            logical_occurrence_id=_id("cap-context-transplant"),
            arm="NO_PRIOR",
            cap_evidence=w7,
        )
    with pytest.raises(
        closure.V072ColdH2ClosureInvariantViolation,
        match="confirmatory total-row cap",
    ):
        closure.ColdH2ContextTotalRowCapEvidenceV1(
            CONTEXT_ID,
            CONTEXT_KEY,
            8,
            closure.ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED,
            prereg.CONFIRMATORY_FAMILY_GENERATION,
            _id("forged-source-cap-binding"),
            _id("forged-context-cap-key"),
            None,
        )


def test_cap_registry_matches_confidence_authority_without_hidden_law(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("hidden-law/preregistration freeze was called")

    monkeypatch.setattr(
        prereg,
        "freeze_transfer_guided_acquisition_preregistration_v1",
        forbidden,
    )
    monkeypatch.setattr(
        prereg,
        "frozen_heldout_environment_manifest_v1",
        forbidden,
    )
    registry = closure.registered_confirmatory_cold_h2_cap_registry_v1()
    assert tuple(
        item.total_physical_row_cap
        for item in registry.context_cap_evidence
    ) == (96, 48, 96)
    assert registry.total_physical_row_cap_sum == 240
    assert registry.maximum_confidence_epochs_per_physical_row == 3
    assert registry.maximum_promotions_per_physical_row == 2
    assert registry.maximum_promotion_authorities_per_context == 2
    assert registry.maximum_row_epoch_authorities_per_arm == 480
    assert (
        registry.confidence_authority_row_epoch_cap_per_arm
        == confidence_v2.MAX_ARM_ROW_EPOCH_AUTHORITIES
        == prereg.MAX_ROW_EPOCH_AUTHORITIES_PER_ARM
    )
    assert registry.maximum_initial_accepted_draw_cap_per_arm == (
        240 * (64 + 2_048)
    )
    expected = registry.context_cap_evidence[0]

    class PublicCapBinding:
        context_id = expected.context_id
        context_key = expected.context_key
        total_physical_row_cap = expected.total_physical_row_cap
        confirmatory_family_generation = (
            expected.confirmatory_family_generation
        )
        authority_class = "CONFIRMATORY_REGISTERED_PUBLIC_ONLY"
        context_specific_total_row_cap_key = (
            expected.context_specific_total_row_cap_key
        )
        total_row_cap_binding_id = (
            expected.source_total_row_cap_binding_id
        )

    assert (
        closure.bind_cold_h2_total_row_cap_protocol_v1(
            PublicCapBinding()
        )
        == expected
    )


def test_registered_target_acquisition_api_remains_locked() -> None:
    with pytest.raises(row_adapter.RegisteredTargetRowAcquisitionLockedV2):
        row_adapter.acquire_registered_target_row_v2()
