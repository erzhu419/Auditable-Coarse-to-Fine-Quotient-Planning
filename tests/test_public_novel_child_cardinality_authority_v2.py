from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import public_novel_child_cardinality_authority_v2 as authority
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _context(key: str = "K7"):
    registered_key = {
        "K7": "heldout_graph_k7_confirmatory_v1",
        "W7": "heldout_graph_w7_confirmatory_v1",
    }[key]
    return next(
        item
        for item in prereg.registered_heldout_public_contexts_v2()
        if item.context_key == registered_key
    )


def _reward() -> Fraction:
    return Fraction(2 ** 2, 2 ** (prereg.RANK_CAP + 1)) / 2


def _descriptor(
    ranks: tuple[int, ...],
    label: str,
) -> authority.RecordedDescriptorEvidenceV2:
    descriptor = authority.RecordedTransitionDescriptorV2(
        observer.HeldoutSymbolicGraphStateV2(ranks),
        _reward(),
        False,
        False,
    )
    return authority.RecordedDescriptorEvidenceV2(
        descriptor,
        (_id(f"synthetic-nonconfirmatory-observation:{label}"),),
    )


def _gain(
    evidence: authority.PublicNovelChildCardinalityEvidenceV2,
    *,
    positive: bool = True,
) -> selector.OneRowCounterfactualGainV2:
    current = Fraction(1, 10)
    counterfactual = Fraction(1, 5) if positive else current
    return selector.derive_evidence_first_one_row_counterfactual_gain_v2(
        cardinality_evidence=evidence,
        current_slack=current,
        counterfactual_slack=counterfactual,
        zero_other_model_id=_id(f"zero-other-model:{evidence.model_id}"),
    )


def _parent(
    *,
    label: str,
    novel_ranks: tuple[tuple[int, ...], ...],
    model_id: str | None = None,
    action_index: int = 0,
) -> tuple[
    prereg.HeldoutPublicGraphContextV2,
    authority.VerifiedParentObservationValidationArtifactV2,
    observer.HeldoutLegalActionCatalogueV2,
]:
    context = _context()
    root = observer.root_state_v2(context)
    catalogue = observer.legal_action_catalogue_v2(context, root, 2)
    action = catalogue.actions[action_index]
    row_binding = observer.observation_row_binding_v2(
        context,
        catalogue,
        action,
    )
    old = _descriptor((2, 0, 2, 1, 0, 0, 0), f"{label}:old")
    novel = tuple(
        sorted(
            (
                _descriptor(ranks, f"{label}:novel:{index}")
                for index, ranks in enumerate(novel_ranks)
            ),
            key=lambda item: item.evidence_id,
        )
    )
    arm = "NO_PRIOR"
    bootstrap = observer.support_epoch_identity_v2(
        context,
        row_binding,
        arm,
        0,
    )
    validation = observer.support_epoch_identity_v2(
        context,
        row_binding,
        arm,
        1,
        (old.descriptor.descriptor_id,),
        bootstrap,
    )
    chain = observer.support_epoch_chain_v2(
        context,
        row_binding,
        arm,
        (bootstrap, validation),
    )
    parent = authority.VerifiedParentObservationValidationArtifactV2(
        _id("logical-occurrence"),
        _id(f"model:{label}") if model_id is None else model_id,
        _id(f"audit:{label}"),
        _id(f"frontier:{label}"),
        _id("threshold"),
        _id(f"candidate:{label}"),
        _id(f"planner-row:{label}"),
        _id(f"synthetic-parent-verification:{label}"),
        authority.ParentEvidenceRoleV2.SYNTHETIC_NONCONFIRMATORY_CONTROL,
        catalogue,
        row_binding,
        chain,
        (old,),
        novel,
    )
    return context, parent, observer.legal_action_catalogue_v2(
        context,
        old.descriptor.next_state,
        1,
    )


def _valid(
    *,
    label: str = "round1",
    include_novel_in_closure: bool = False,
) -> tuple[
    prereg.HeldoutPublicGraphContextV2,
    authority.VerifiedParentObservationValidationArtifactV2,
    authority.CurrentPublicH1RowClosureV2,
    selector.OneRowCounterfactualGainV2,
    authority.PublicNovelChildCardinalityAuthorityV2,
]:
    context, parent, old_catalogue = _parent(
        label=label,
        novel_ranks=(
            (2, 0, 2, 0, 1, 0, 0),
            (2, 0, 2, 0, 0, 1, 0),
        ),
    )
    catalogues = [old_catalogue]
    if include_novel_in_closure:
        catalogues.extend(
            observer.legal_action_catalogue_v2(
                context,
                evidence.descriptor.next_state,
                1,
            )
            for evidence in parent.novel_evidence
        )
    canonical_catalogues = tuple(
        sorted(
            {item.catalogue_id: item for item in catalogues}.values(),
            key=lambda item: item.catalogue_id,
        )
    )
    closure = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=parent.model_id,
        catalogues=canonical_catalogues,
    )
    evidence = (
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=parent,
            current_h1_closure=closure,
        )
    )
    gain = _gain(evidence)
    claim = authority.authorize_public_novel_child_rows_v2(
        parent=parent,
        cardinality_evidence=evidence,
        selector_gain=gain,
    )
    return context, parent, closure, gain, claim


def test_authority_derives_all_absent_rows_and_exact_nonresetting_formula() -> None:
    _context_value, parent, _closure, gain, claim = _valid()
    assert parent.evidence_role is (
        authority.ParentEvidenceRoleV2.SYNTHETIC_NONCONFIRMATORY_CONTROL
    )
    assert claim.new_child_row_count == 4
    assert claim.exact_round_draw_upper == 2_048 + 4 * 8_256
    assert claim.cumulative_draw_upper == 2_048 + 4 * 8_256
    assert claim.promoted_support_descriptor_ids == tuple(
        sorted(
            {
                *parent.old_support_descriptor_ids,
                *parent.novel_descriptor_ids,
            }
        )
    )
    assert claim.selector_counterfactual_id == gain.counterfactual_id
    assert claim.environment_law_queries == 0
    assert claim.outcome_enumeration_calls == 0
    assert claim.new_draw_calls == 0
    document = claim.to_document()
    evidence_document = document["cardinality_evidence"]
    assert evidence_document["caller_supplied_mapping"] is False
    assert evidence_document["caller_supplied_count"] is False


def test_evidence_first_selector_never_calls_legacy_mapping_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_legacy_path(*_args, **_kwargs):
        raise AssertionError("legacy caller-mapping metadata was called")

    monkeypatch.setattr(
        selector,
        "freeze_public_frontier_action_metadata_v2",
        forbidden_legacy_path,
    )
    monkeypatch.setattr(
        selector,
        "exact_preexecution_draw_upper_v2",
        forbidden_legacy_path,
    )
    _context_value, _parent_value, _closure, gain, claim = _valid(
        label="evidence-first-no-legacy",
    )
    assert gain.cardinality_evidence_id == (
        claim.cardinality_evidence.evidence_id
    )
    assert gain.base == gain.gain / claim.exact_round_draw_upper
    assert (
        gain.to_document()["cardinality_evidence"]["kind"]
        == "PUBLIC_NOVEL_CHILD_FULL_ROW_LIST"
    )
    alternate_evidence = replace(
        claim.cardinality_evidence,
        selected_candidate_id=_id("evidence-first-alternate-candidate"),
        selected_planner_row_id=_id(
            "evidence-first-alternate-planner-row"
        ),
    )
    alternate_gain = (
        selector.derive_evidence_first_one_row_counterfactual_gain_v2(
            cardinality_evidence=alternate_evidence,
            current_slack=Fraction(0),
            counterfactual_slack=Fraction(1, 5),
            zero_other_model_id=_id(
                "evidence-first-alternate-zero-other"
            ),
        )
    )
    ranking = selector.rank_evidence_first_no_prior_gains_v2(
        (gain, alternate_gain)
    )
    assert ranking[0] == alternate_gain
    assert ranking[0].base > ranking[1].base


def test_builder_has_no_caller_mapping_or_count_and_rejects_count_forgery() -> None:
    parameters = inspect.signature(
        authority.derive_public_novel_child_cardinality_evidence_v2
    ).parameters
    assert not {
        "n",
        "count",
        "n_new_child_actions",
        "new_child_rows_by_state",
        "newly_reachable_child_catalogues_by_row",
    } & set(parameters)
    _context_value, _parent_value, _closure, _gain_value, claim = _valid()
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation
    ):
        replace(
            claim.cardinality_evidence,
            new_child_row_count=claim.new_child_row_count + 1,
        )


def test_final_authority_rejects_legacy_metadata_ids_as_evidence() -> None:
    from tests.test_target_preauthorization_selector_v2 import _fixture

    _model, _audit, _threshold, legacy_metadata = _fixture()
    _context_value, parent, _closure, gain, claim = _valid(
        label="reject-legacy-metadata",
    )
    for legacy_id in (
        legacy_metadata.public_metadata_id,
        legacy_metadata.rows[0].metadata_id,
    ):
        with pytest.raises(
            authority.PublicNovelChildCardinalityV2InvariantViolation,
            match="stale parent/cardinality evidence",
        ):
            authority.authorize_public_novel_child_rows_v2(
                parent=parent,
                cardinality_evidence=legacy_id,  # type: ignore[arg-type]
                selector_gain=gain,
            )
    assert claim.cardinality_evidence.evidence_id not in {
        legacy_metadata.public_metadata_id,
        legacy_metadata.rows[0].metadata_id,
    }


def test_empty_novel_and_nonpositive_selector_gain_fail_closed() -> None:
    context, parent, old_catalogue = _parent(
        label="empty",
        novel_ranks=(),
    )
    closure = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=parent.model_id,
        catalogues=(old_catalogue,),
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="nonempty novel evidence",
    ):
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=parent,
            current_h1_closure=closure,
        )

    _context_value, parent, _closure, _positive, claim = _valid(
        label="zero-gain",
    )
    zero = _gain(
        claim.cardinality_evidence,
        positive=False,
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="positive gain",
    ):
        authority.authorize_public_novel_child_rows_v2(
            parent=parent,
            cardinality_evidence=claim.cardinality_evidence,
            selector_gain=zero,
        )


def test_current_closure_rejects_incomplete_catalogue_and_row_omission() -> None:
    context, parent, old_catalogue = _parent(
        label="incomplete",
        novel_ranks=((2, 0, 2, 0, 1, 0, 0),),
    )
    incomplete = observer.HeldoutLegalActionCatalogueV2(
        context.context_id,
        old_catalogue.state,
        1,
        old_catalogue.actions[:-1],
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="incomplete",
    ):
        authority.freeze_current_public_h1_row_closure_v2(
            context=context,
            model_id=parent.model_id,
            catalogues=(incomplete,),
        )
    closure = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=parent.model_id,
        catalogues=(old_catalogue,),
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="omits or invents",
    ):
        authority.CurrentPublicH1RowClosureV2(
            closure.context_id,
            closure.model_id,
            closure.catalogues,
            closure.rows[:-1],
        )


def test_duplicate_and_foreign_physical_rows_are_rejected() -> None:
    _context_value, _parent_value, _closure, _gain_value, claim = _valid()
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="sorted and distinct",
    ):
        replace(
            claim.cardinality_evidence,
            rows_to_acquire=tuple(
                sorted(
                    (*claim.rows_to_acquire, claim.rows_to_acquire[0]),
                    key=lambda item: item.physical_row_id,
                )
            ),
            new_child_row_count=claim.new_child_row_count + 1,
            exact_round_draw_upper=(
                claim.exact_round_draw_upper
                + authority.CHILD_ROW_DRAWS
            ),
        )
    foreign_context = _context("W7")
    foreign_state = observer.HeldoutSymbolicGraphStateV2(
        (2, 2, 0, 0, 1, 0, 0)
    )
    foreign_catalogue = observer.legal_action_catalogue_v2(
        foreign_context,
        foreign_state,
        1,
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="foreign binding",
    ):
        replace(
            claim.cardinality_evidence,
            induced_child_catalogues=tuple(
                sorted(
                    (*claim.induced_child_catalogues, foreign_catalogue),
                    key=lambda item: item.catalogue_id,
                )
            ),
        )


def test_already_present_rows_are_excluded_from_charge_and_acquisition() -> None:
    _context_value, _parent_value, closure, gain, claim = _valid(
        label="present",
        include_novel_in_closure=True,
    )
    assert claim.induced_rows
    assert claim.rows_to_acquire == ()
    assert {
        item.physical_row_id for item in claim.already_present_rows
    } == {
        item.physical_row_id for item in claim.induced_rows
    }
    assert set(claim.induced_rows).issubset(set(closure.rows))
    assert gain.exact_draw_upper == 2_048
    assert claim.new_child_row_count == 0
    assert claim.exact_round_draw_upper == 2_048


def test_round_two_requires_materialized_predecessor_and_never_resets_budget() -> None:
    context, _parent1, closure1, gain1, first = _valid(
        label="first",
    )
    first_catalogues = tuple(
        sorted(
            {
                item.catalogue_id: item
                for item in (
                    *closure1.catalogues,
                    *first.induced_child_catalogues,
                )
            }.values(),
            key=lambda item: item.catalogue_id,
        )
    )
    context2, parent2, old2 = _parent(
        label="second",
        novel_ranks=((2, 0, 2, 0, 0, 0, 1),),
        action_index=1,
    )
    assert context2 == context
    closure2 = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=parent2.model_id,
        catalogues=tuple(
            sorted(
                {
                    item.catalogue_id: item
                    for item in (*first_catalogues, old2)
                }.values(),
                key=lambda item: item.catalogue_id,
            )
        ),
    )
    evidence2 = (
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=parent2,
            current_h1_closure=closure2,
            previous_evidence=first.cardinality_evidence,
        )
    )
    gain2 = _gain(evidence2)
    second = authority.authorize_public_novel_child_rows_v2(
        parent=parent2,
        cardinality_evidence=evidence2,
        selector_gain=gain2,
    )
    assert second.round_index == 2
    assert second.previous_evidence_id == (
        first.cardinality_evidence.evidence_id
    )
    assert second.cumulative_child_row_count == (
        first.cumulative_child_row_count
        + second.new_child_row_count
    )
    assert second.cumulative_draw_upper == (
        2 * 2_048
        + 8_256 * second.cumulative_child_row_count
    )

    stale_closure = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=parent2.model_id,
        catalogues=(old2,),
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="did not advance",
    ):
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=parent2,
            current_h1_closure=stale_closure,
            previous_evidence=first.cardinality_evidence,
        )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="did not advance",
    ):
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=parent2,
            current_h1_closure=closure2,
            previous_evidence=second.cardinality_evidence,
        )


def test_round_two_rejects_same_parent_resigned_under_new_model_ids() -> None:
    context, parent, closure, _gain_value, first = _valid(
        label="resigned-first",
    )
    resigned = replace(
        parent,
        model_id=_id("resigned-model"),
        audit_id=_id("resigned-audit"),
        frontier_id=_id("resigned-frontier"),
        selected_candidate_id=_id("resigned-candidate"),
        selected_planner_row_id=_id("resigned-planner-row"),
        upstream_verification_attestation_id=_id(
            "resigned-parent-attestation"
        ),
    )
    rebuilt_catalogues = tuple(
        sorted(
            {
                item.catalogue_id: item
                for item in (
                    *closure.catalogues,
                    *first.induced_child_catalogues,
                )
            }.values(),
            key=lambda item: item.catalogue_id,
        )
    )
    rebuilt_closure = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=resigned.model_id,
        catalogues=rebuilt_catalogues,
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="did not advance",
    ):
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=resigned,
            current_h1_closure=rebuilt_closure,
            previous_evidence=first.cardinality_evidence,
        )


def test_epoch_two_parent_is_never_authorizable_for_forbidden_epoch_three() -> None:
    context, parent, _old_catalogue = _parent(
        label="epoch-two-parent",
        novel_ranks=((2, 0, 2, 0, 1, 0, 0),),
    )
    epoch_two = observer.support_epoch_identity_v2(
        context,
        parent.parent_row_binding,
        parent.arm,
        2,
        parent.old_support_descriptor_ids,
        parent.support_epoch_chain.leaf,
    )
    epoch_two_chain = observer.support_epoch_chain_v2(
        context,
        parent.parent_row_binding,
        parent.arm,
        (*parent.support_epoch_chain.epochs, epoch_two),
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="incomplete or stale",
    ):
        replace(parent, support_epoch_chain=epoch_two_chain)


def test_nineteen_row_and_160960_caps_fail_closed_without_borrowing() -> None:
    rank_two_spawn_states = tuple(
        tuple(
            2 if index in (0, 2, spawn) else 0
            for index in range(7)
        )
        for spawn in (3, 4, 5, 6)
    )
    context, parent, old_catalogue = _parent(
        label="cap",
        novel_ranks=rank_two_spawn_states,
    )
    closure = authority.freeze_current_public_h1_row_closure_v2(
        context=context,
        model_id=parent.model_id,
        catalogues=(old_catalogue,),
    )
    induced = sum(
        len(
            observer.legal_action_catalogue_v2(
                context,
                evidence.descriptor.next_state,
                1,
            ).actions
        )
        for evidence in parent.novel_evidence
    )
    assert induced == 24
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="exceeds nineteen",
    ):
        authority.derive_public_novel_child_cardinality_evidence_v2(
            context=context,
            parent=parent,
            current_h1_closure=closure,
        )


def test_module_exposes_no_sampler_law_or_outcome_enumerator() -> None:
    source = inspect.getsource(authority)
    assert "open_heldout_transition_stream_v2" not in source
    assert "frozen_heldout_environment_manifest_v1" not in source
    assert "sample_" not in source
