from __future__ import annotations

from fractions import Fraction
import hashlib
import inspect
from types import SimpleNamespace

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import v072_registered_target_confidence_accumulator_v1 as accumulator
from acfqp import v072_registered_target_selector_v1 as selector
from acfqp import (
    v072_registered_target_selector_independent_verifier_v1 as independent,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _candidate(
    label: str,
    *,
    depth: int = 0,
    weight: Fraction = Fraction(1),
    draws: int = 16,
    source_midrank: Fraction | None = None,
    sound: bool = True,
    cap: bool = True,
) -> selector.GenericBoundaryCandidateV1:
    return selector.GenericBoundaryCandidateV1(
        _id(f"generic-candidate:{label}"),
        depth,
        (_id(f"generic-row:{label}"),),
        weight,
        draws,
        source_midrank,
        sound,
        cap,
    )


def _ordered(
    *items: selector.GenericBoundaryCandidateV1,
) -> tuple[selector.GenericBoundaryCandidateV1, ...]:
    return tuple(sorted(items, key=lambda item: item.candidate_id))


def _select(
    candidates: tuple[selector.GenericBoundaryCandidateV1, ...],
    arm: str,
    *,
    cap: int = 1_000,
) -> selector.GenericBoundarySelectionDecisionV1:
    claimed = selector.select_generic_boundary_candidate_core_v1(
        candidates=candidates,
        arm=arm,
        remaining_draw_cap=cap,
    )
    replayed = (
        independent.replay_generic_boundary_selection_independently_v1(
            candidates=candidates,
            arm=arm,
            remaining_draw_cap=cap,
            claimed=claimed,
        )
    )
    assert replayed.decision_id == claimed.decision_id
    return claimed


def test_all_four_adaptive_arms_have_frozen_independently_replayed_orders(
) -> None:
    high = _candidate("high-q", source_midrank=Fraction(3, 4))
    low = _candidate("low-q", source_midrank=Fraction(1, 4))
    candidates = _ordered(high, low)
    source = _select(candidates, "SOURCE_CONSENSUS_PRIOR")
    wrong = _select(candidates, "WRONG_CONSENSUS_PRIOR")
    no_prior = _select(candidates, "NO_PRIOR")
    ood = _select(candidates, "OOD_ABSTENTION")
    assert source.selected_candidate_id == high.candidate_id
    assert wrong.selected_candidate_id == low.candidate_id
    assert no_prior.ordered_eligible_candidate_ids == (
        ood.ordered_eligible_candidate_ids
    )
    assert no_prior.selected_candidate_id == min(
        high.candidate_id,
        low.candidate_id,
    )
    assert source.candidate_ids == wrong.candidate_ids
    assert source.candidate_ids == no_prior.candidate_ids
    assert source.candidate_ids == ood.candidate_ids


def test_earliest_failed_boundary_precedes_source_score() -> None:
    earliest = _candidate(
        "earliest",
        depth=0,
        weight=Fraction(1, 100),
        source_midrank=Fraction(0),
    )
    later = _candidate(
        "later",
        depth=1,
        weight=Fraction(100),
        source_midrank=Fraction(1),
    )
    decision = _select(
        _ordered(earliest, later),
        "SOURCE_CONSENSUS_PRIOR",
    )
    assert decision.selected_candidate_id == earliest.candidate_id


def test_no_sound_cover_and_cap_exhaustion_are_typed_closures() -> None:
    unsound = _candidate("unsound", sound=False)
    no_cover = _select(_ordered(unsound), "NO_PRIOR")
    assert (
        no_cover.outcome
        is selector.RegisteredSelectorOutcomeV1.NO_SOUND_COVER
    )
    assert no_cover.selected_candidate_id is None
    expensive = _candidate("expensive", draws=64)
    exhausted = _select(_ordered(expensive), "NO_PRIOR", cap=63)
    assert (
        exhausted.outcome
        is selector.RegisteredSelectorOutcomeV1.CAP_EXHAUSTED
    )
    assert exhausted.selected_candidate_id is None


def test_cold_failure_can_select_round_one_then_fresh_round_two_without_replacement(
) -> None:
    first = _candidate("round-1")
    second = _candidate("round-2")
    cold_failure = _select(_ordered(first, second), "NO_PRIOR")
    assert cold_failure.outcome is selector.RegisteredSelectorOutcomeV1.SELECTED
    selected_round_one = cold_failure.selected_candidate_id
    remaining = tuple(
        item
        for item in (first, second)
        if item.candidate_id != selected_round_one
    )
    round_one_failure = _select(_ordered(*remaining), "NO_PRIOR")
    assert round_one_failure.outcome is selector.RegisteredSelectorOutcomeV1.SELECTED
    assert round_one_failure.selected_candidate_id != selected_round_one
    assert set(cold_failure.candidate_ids) > set(round_one_failure.candidate_ids)


def test_source_quantities_change_order_only_not_candidate_authority() -> None:
    high = _candidate("source-separation-high", source_midrank=Fraction(9, 10))
    low = _candidate("source-separation-low", source_midrank=Fraction(1, 10))
    candidates = _ordered(high, low)
    decisions = tuple(
        _select(candidates, arm)
        for arm in (
            "SOURCE_CONSENSUS_PRIOR",
            "NO_PRIOR",
            "WRONG_CONSENSUS_PRIOR",
            "OOD_ABSTENTION",
        )
    )
    assert all(item.candidate_ids == decisions[0].candidate_ids for item in decisions)
    assert all(
        candidate.sound_cover
        and candidate.cap_eligible
        and candidate.causal_weight == Fraction(1)
        and candidate.physical_row_binding_ids
        for candidate in candidates
    )
    authority_payload_source = inspect.getsource(
        accumulator.RegisteredAcquisitionSelectionAuthorityV1._payload
    )
    assert '"source_quantities_serialized_in_authority": False' in (
        authority_payload_source
    )
    assert '"source_prior_used_in_causal_evidence": False' in (
        authority_payload_source
    )
    candidate_payload_source = inspect.getsource(
        selector.RegisteredBoundaryCandidateV1._payload
    )
    assert '"source_midrank"' not in candidate_payload_source
    assert '"source_quantity_serialized": False' in candidate_payload_source


def test_source_midrank_reads_the_canonical_compact_recipe_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_id = _id("selector-compact-recipe")
    feature_id = _id("selector-compact-feature")

    class CompactRecipe:
        def __init__(self) -> None:
            self.recipe_id = recipe_id

        def to_document(self) -> dict[str, object]:
            return {
                "compact_derived_artifacts": {
                    "source_archive": {
                        "consensus": [
                            {
                                "disposition": "APPLIED",
                                "feature_key": feature_id,
                                "mean_midrank": {
                                    "numerator": 3,
                                    "denominator": 5,
                                },
                            }
                        ]
                    }
                }
            }

    monkeypatch.setattr(
        selector.source_recipe,
        "load_source_reconstruction_recipe_v1",
        lambda _path: CompactRecipe(),
    )
    monkeypatch.setattr(
        independent.source_recipe,
        "load_source_reconstruction_recipe_v1",
        lambda _path: CompactRecipe(),
    )
    chain = SimpleNamespace(
        repository_root="/registered",
        remote_main_anchor=SimpleNamespace(
            claim=SimpleNamespace(
                source_reconstruction_recipe_repository_path=(
                    "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
                ),
                source_reconstruction_recipe_id=recipe_id,
            )
        ),
    )
    assert selector._source_midrank_by_feature(  # type: ignore[arg-type]
        chain,
        "SOURCE_CONSENSUS_PRIOR",
    ) == (recipe_id, {feature_id: Fraction(3, 5)})
    assert independent._source_q(  # type: ignore[arg-type]
        chain,
        "SOURCE_CONSENSUS_PRIOR",
    ) == (recipe_id, {feature_id: Fraction(3, 5)})


def test_production_entry_accepts_no_caller_candidate_or_status() -> None:
    signature = inspect.signature(
        selector.prepare_registered_acquisition_frontier_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "failed_audit",
        "model_pair",
        "model_replay_attestation",
        "acquisitions",
        "round_index",
        "predecessor_frontier",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    assert {
        "candidate",
        "candidates",
        "selected_rows",
        "causal_id",
        "status",
        "source_prior",
        "observations",
        "law",
        "seed",
    }.isdisjoint(signature.parameters)


def test_foreign_inputs_fail_before_observer_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden_open(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls.append("open")
        raise AssertionError("selector must not open a target stream")

    monkeypatch.setattr(
        observer,
        "open_heldout_target_transition_stream_v2",
        forbidden_open,
    )
    with pytest.raises(selector.RegisteredSelectorGateLockedV1) as caught:
        selector.prepare_registered_acquisition_frontier_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            failed_audit=object(),  # type: ignore[arg-type]
            model_pair=object(),  # type: ignore[arg-type]
            model_replay_attestation=object(),  # type: ignore[arg-type]
            acquisitions=object(),  # type: ignore[arg-type]
            round_index=1,
        )
    assert calls == []
    assert caught.value.observer_stream_opens == 0
    assert caught.value.observer_draw_calls == 0
    with pytest.raises(
        independent.RegisteredSelectorIndependentGateLockedV1
    ) as replay_caught:
        independent.verify_registered_selector_independently_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            failed_audit=object(),  # type: ignore[arg-type]
            model_pair=object(),  # type: ignore[arg-type]
            model_replay_attestation=object(),  # type: ignore[arg-type]
            acquisitions=object(),  # type: ignore[arg-type]
            round_index=1,
            predecessor_frontier=None,
            claimed=object(),  # type: ignore[arg-type]
        )
    assert calls == []
    assert replay_caught.value.observer_stream_opens == 0
    assert replay_caught.value.observer_draw_calls == 0


def test_selection_authority_and_independent_attestation_are_not_caller_mintable(
) -> None:
    identity = _id("private-selector-identity")
    with pytest.raises(
        accumulator.V072RegisteredTargetConfidenceAccumulatorViolation
    ):
        accumulator.RegisteredAcquisitionSelectionAuthorityV1(
            object(),
            identity,
            identity,
            identity,
            "NO_PRIOR",
            1,
            None,
            identity,
            identity,
            identity,
            identity,
            identity,
            identity,
            identity,
            (identity,),
            (identity,),
            identity,
            (),
            (identity,),
            2_048,
            2_048,
            identity,
        )
    with pytest.raises(
        independent.V072RegisteredSelectorIndependentVerificationFailure
    ):
        independent.RegisteredSelectorIndependentAttestationV1(
            _minting_capability=object(),
            authority_chain_id=identity,
            anchor_id=identity,
            occurrence_id=identity,
            context_id=identity,
            arm="NO_PRIOR",
            round_index=1,
            predecessor_frontier_id=None,
            failed_audit_id=identity,
            model_pair_id=identity,
            model_replay_attestation_id=identity,
            candidate_inventory_id=identity,
            proposal_order_id=identity,
            causal_evidence_id=identity,
            claim_id=identity,
            outcome=selector.RegisteredSelectorOutcomeV1.SELECTED,
            selected_candidate_id=identity,
            supporting_acquisition_ids=(identity,),
            supporting_row_binding_ids=(identity,),
            promotion_row_binding_id=identity,
            new_child_row_binding_ids=(),
            selected_row_binding_ids=(identity,),
            selected_draw_upper=2_048,
            cumulative_draw_upper=2_048,
        )
    with pytest.raises(accumulator.RegisteredTargetAcquisitionGateLockedV1):
        accumulator.mint_registered_acquisition_selection_authority_v1(
            selector_attestation=object(),
            supporting_acquisitions=(),
        )


def test_independent_production_replay_does_not_call_producer_selection() -> None:
    source = inspect.getsource(independent)
    assert "selector._build_claim" not in source
    assert "selector.select_generic_boundary_candidate_core_v1" not in source
    assert "open_heldout_target_transition_stream_v2" not in source
    assert "source_used_in_confidence_or_certificate" in source
