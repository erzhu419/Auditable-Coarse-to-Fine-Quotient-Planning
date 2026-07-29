from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.partial_support_confidence_v1 as row_confidence
import acfqp.partial_support_family_confidence_v1 as family
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _replay(
    row: acquisition.GraphPartialSupportRowV1,
) -> acquisition.GraphPartialSupportReplayVerificationV1:
    authority = row.confidence_authority
    epoch = row.support_epoch
    confidence_verification = (
        row_confidence.PartialSupportConfidenceVerificationV1(
            authority_id=authority.authority_id,
            support_epoch_id=epoch.support_epoch_id,
            validation_evidence_id=(
                authority.validation_evidence.validation_evidence_id
            ),
            joint_simplex_id=authority.joint_simplex.joint_simplex_id,
            event_count=epoch.event_count,
            per_event_alpha=epoch.per_event_alpha,
            row_epoch_beta=epoch.row_epoch_beta,
        )
    )
    return acquisition.GraphPartialSupportReplayVerificationV1(
        partial_row_id=row.partial_row_id,
        physical_evidence_id=row.physical_evidence_id,
        confidence_verification_id=(
            confidence_verification.verification_id
        ),
        replayed_support_epoch_index=row.support_epoch_index,
        replayed_observer_draws=row.counters.total_observer_draws,
        replayed_random_word_calls=row.counters.total_random_word_calls,
        replayed_rejections=row.counters.total_rejections,
    )


@pytest.fixture(scope="module")
def row_family() -> tuple[
    acquisition.GraphPartialSupportRowV1,
    acquisition.GraphPartialSupportRowV1,
    family.PartialSupportRowEpochEvidenceV1,
    family.PartialSupportRowEpochEvidenceV1,
]:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    root = observer.root_state_v1(context)
    catalogue = observer.legal_action_catalogue_v1(context, root, 2)
    action = catalogue.actions[0]
    acquisition.acquire_graph_partial_support_row_v1.cache_clear()
    initial = acquisition.acquire_graph_partial_support_row_v1(
        context,
        catalogue,
        action,
        2_048,
    )
    second = acquisition.acquire_graph_partial_support_row_v1(
        context,
        catalogue,
        catalogue.actions[1],
        2_048,
    )
    return (
        initial,
        second,
        family.bind_partial_support_row_epoch_evidence_v1(
            initial,
            _replay(initial),
        ),
        family.bind_partial_support_row_epoch_evidence_v1(
            second,
            _replay(second),
        ),
    )


def _manifest(
    rows_and_consumers: tuple[
        tuple[
            acquisition.GraphPartialSupportRowV1,
            family.PlanningConsumerKindV1,
            str,
        ],
        ...,
    ],
    trace_label: str = "family-trace",
) -> family.PlanningRowEpochManifestV1:
    trace_id = _id(trace_label)
    considerations = tuple(
        family.bind_planning_row_epoch_consideration_v1(
            planning_trace_id=trace_id,
            sequence_index=index,
            logical_consumer_id=_id(consumer),
            consumer_kind=kind,
            row=row,
        )
        for index, (row, kind, consumer) in enumerate(
            rows_and_consumers
        )
    )
    return family.freeze_planning_row_epoch_manifest_v1(
        trace_id,
        considerations,
    )


def test_preregistered_family_budget_uses_cap_not_realized_count(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, _, evidence, _ = row_family
    manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.QUOTIENT,
                "quotient",
            ),
        )
    )
    authority = family.build_partial_support_family_confidence_v1(
        manifest,
        (evidence,),
    )
    assert type(authority) is family.PartialSupportFamilyConfidenceAuthorityV1
    assert family.MAX_UNIQUE_ROW_EPOCHS == 512
    assert family.ROW_EPOCH_TAIL_UPPER == Fraction(1, 64_000)
    assert authority.realized_unique_row_epoch_count == 1
    assert (
        authority.realized_family_tail_diagnostic
        == Fraction(1, 64_000)
    )
    assert authority.family_tail_upper == Fraction(512, 64_000)
    assert authority.family_tail_upper == Fraction(1, 125)
    assert authority.family_confidence_lower == Fraction(124, 125)
    assert (
        authority.family_status
        is (
            family.PartialSupportFamilyStatusV1
            .CONDITIONAL_STATISTICAL_CERTIFIED
        )
    )
    assert (
        authority.randomness_implementation
        == observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
    )
    assert authority.exact_iid_implementation_claimed is False
    assert (
        authority.statistical_claim_scope
        == observer.STATISTICAL_CLAIM_SCOPE
    )
    assert authority.formal_exact_iid_plan_certificate is False
    assert (
        authority.family_tail_upper
        != authority.realized_family_tail_diagnostic
    )


def test_direct_and_quotient_share_one_physical_authority_charge(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, _, evidence, _ = row_family
    manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.QUOTIENT,
                "quotient",
            ),
            (
                initial,
                family.PlanningConsumerKindV1.DIRECT,
                "direct",
            ),
        ),
        "shared-trace",
    )
    assert len(manifest.considerations) == 2
    assert manifest.unique_row_epoch_count == 1
    authority = family.build_partial_support_family_confidence_v1(
        manifest,
        (evidence, evidence),
    )
    assert type(authority) is family.PartialSupportFamilyConfidenceAuthorityV1
    assert len(authority.unique_evidences) == 1
    assert authority.realized_unique_row_epoch_count == 1


def test_full_manifest_is_required_and_selected_only_rows_are_rejected(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, second, initial_evidence, second_evidence = row_family
    manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.PLANNER_AUDIT,
                "first-row",
            ),
            (
                second,
                family.PlanningConsumerKindV1.QUOTIENT,
                "selected-row",
            ),
        ),
        "all-considered",
    )
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation,
        match="omits considered rows",
    ):
        family.build_partial_support_family_confidence_v1(
            manifest,
            (second_evidence,),
        )
    authority = family.build_partial_support_family_confidence_v1(
        manifest,
        (second_evidence, initial_evidence),
    )
    assert type(authority) is family.PartialSupportFamilyConfidenceAuthorityV1
    verification = (
        family.verify_partial_support_family_confidence_v1(
            authority,
            manifest,
            (initial_evidence, second_evidence),
        )
    )
    assert verification.realized_unique_row_epoch_count == 2
    assert verification.exact_iid_implementation_claimed is False
    assert verification.formal_exact_iid_plan_certificate is False
    assert set(verification.rebuilt_row_authority_ids) == {
        initial.confidence_authority.authority_id,
        second.confidence_authority.authority_id,
    }
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation
    ):
        family.verify_partial_support_family_confidence_v1(
            authority,
            manifest,
            (second_evidence,),
        )


def test_bare_row_confidence_authority_is_not_family_evidence(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, _, _, _ = row_family
    manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.QUOTIENT,
                "quotient",
            ),
        ),
        "bare-authority",
    )
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation,
        match="forbids bare confidence authorities",
    ):
        family.build_partial_support_family_confidence_v1(
            manifest,
            (initial.confidence_authority,),  # type: ignore[arg-type]
        )


def test_duplicate_identity_with_a_changed_document_fails_closed(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, _, evidence, _ = row_family
    manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.QUOTIENT,
                "quotient",
            ),
        ),
        "changed-document",
    )
    forged = replace(evidence)
    object.__setattr__(forged, "row_document_id", _id("different-doc"))
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation,
        match="changed after construction",
    ):
        family.build_partial_support_family_confidence_v1(
            manifest,
            (evidence, forged),
        )


def test_replay_must_attest_the_exact_row(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, _, evidence, _ = row_family
    changed = replace(
        evidence.replay,
        replayed_observer_draws=(
            evidence.replay.replayed_observer_draws + 1
        ),
        replayed_random_word_calls=(
            evidence.replay.replayed_random_word_calls + 1
        ),
    )
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation,
        match="does not attest",
    ):
        family.bind_partial_support_row_epoch_evidence_v1(
            initial,
            changed,
        )


def test_cap_exhaustion_is_typed_and_cannot_be_signed() -> None:
    trace_id = _id("over-cap-trace")
    considerations = tuple(
        family.PlanningRowEpochConsiderationV1(
            planning_trace_id=trace_id,
            sequence_index=index,
            logical_consumer_id=_id(f"consumer-{index}"),
            consumer_kind=family.PlanningConsumerKindV1.PLANNER_AUDIT,
            row_epoch_identity=family.PartialSupportRowEpochIdentityV1(
                context_id=_id(f"context-{index}"),
                row_id=_id(f"row-{index}"),
                support_epoch_id=_id(f"epoch-{index}"),
                confidence_authority_id=_id(f"authority-{index}"),
            ),
        )
        for index in range(family.MAX_UNIQUE_ROW_EPOCHS + 1)
    )
    manifest = family.freeze_planning_row_epoch_manifest_v1(
        trace_id,
        considerations,
    )
    result = family.build_partial_support_family_confidence_v1(
        manifest,
        (),
    )
    assert type(result) is family.PartialSupportFamilyCapExhaustedV1
    assert (
        result.family_status
        is family.PartialSupportFamilyStatusV1.CAP_EXHAUSTED
    )
    assert result.realized_unique_row_epoch_count == 513
    assert result.realized_family_tail_diagnostic == Fraction(513, 64_000)
    assert result.family_tail_upper == Fraction(512, 64_000)
    assert result.certification_allowed is False
    assert result.exact_iid_implementation_claimed is False
    assert result.formal_exact_iid_plan_certificate is False
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation
    ):
        family.verify_partial_support_family_confidence_v1(
            result,  # type: ignore[arg-type]
            manifest,
            (),
        )


def test_manifest_and_authority_identities_are_content_bound(
    row_family: tuple[
        acquisition.GraphPartialSupportRowV1,
        acquisition.GraphPartialSupportRowV1,
        family.PartialSupportRowEpochEvidenceV1,
        family.PartialSupportRowEpochEvidenceV1,
    ],
) -> None:
    initial, _, evidence, _ = row_family
    manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.QUOTIENT,
                "quotient",
            ),
        ),
        "identity-a",
    )
    authority = family.build_partial_support_family_confidence_v1(
        manifest,
        (evidence,),
    )
    assert type(authority) is family.PartialSupportFamilyConfidenceAuthorityV1
    changed_manifest = _manifest(
        (
            (
                initial,
                family.PlanningConsumerKindV1.QUOTIENT,
                "quotient",
            ),
        ),
        "identity-b",
    )
    assert changed_manifest.manifest_id != manifest.manifest_id
    with pytest.raises(
        family.PartialSupportFamilyConfidenceInvariantViolation
    ):
        family.verify_partial_support_family_confidence_v1(
            authority,
            changed_manifest,
            (evidence,),
        )
