from __future__ import annotations

import ast
import copy
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import (
    v072_registered_incremental_epoch_independent_verifier_v1 as verifier,
)
from acfqp import (
    v072_registered_incremental_epoch_materializer_v1 as materializer,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _cold(
) -> materializer.RegistrationDisjointIncrementalEpochV1:
    return materializer.freeze_registration_disjoint_cold_epoch_v1(
        cold_acquisitions=tuple(
            materializer.RegistrationDisjointIncrementalAcquisitionV1(
                _id(f"verifier-row-{label}"),
                0,
                materializer.RegistrationDisjointAcquisitionKindV1.COLD,
            )
            for label in ("A", "B", "C")
        )
    )


def _history_ids(
    value: materializer.RegistrationDisjointIncrementalEpochV1,
) -> tuple[str, ...]:
    return tuple(
        item.acquisition_id for item in value.acquisition_history
    )


def _row(
    value: materializer.RegistrationDisjointIncrementalEpochV1,
    label: str,
    *,
    latest: bool = True,
) -> materializer.RegistrationDisjointIncrementalAcquisitionV1:
    rows = tuple(
        item
        for item in value.acquisition_history
        if item.row_binding_id == _id(f"verifier-row-{label}")
    )
    assert rows
    return (
        max(rows, key=lambda item: item.round_index)
        if latest
        else min(rows, key=lambda item: item.round_index)
    )


def _selector(
    prior: materializer.RegistrationDisjointIncrementalEpochV1,
    *,
    parent_label: str,
    children: tuple[str, ...],
    latest_parent: bool = True,
) -> materializer.RegistrationDisjointSelectorClosureV1:
    parent = _row(prior, parent_label, latest=latest_parent)
    return materializer.RegistrationDisjointSelectorClosureV1(
        prior.round_index + 1,
        prior.epoch_id,
        prior.frontier_id,
        _history_ids(prior),
        parent.acquisition_id,
        parent.row_binding_id,
        tuple(
            sorted(_id(f"verifier-row-{label}") for label in children)
        ),
    )


def _round_one(
) -> tuple[
    materializer.RegistrationDisjointIncrementalEpochV1,
    materializer.RegistrationDisjointSelectorClosureV1,
    materializer.RegistrationDisjointIncrementalEpochV1,
]:
    cold = _cold()
    selected = _selector(
        cold,
        parent_label="A",
        children=("D", "E"),
    )
    claimed = (
        materializer
        .materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=cold,
            selector_closure=selected,
        )
    )
    return cold, selected, claimed


def _rehash_synthetic_epoch(
    value: materializer.RegistrationDisjointIncrementalEpochV1,
) -> None:
    object.__setattr__(
        value,
        "_epoch_id",
        materializer._content_id(  # type: ignore[attr-defined]
            "synthetic_epoch",
            value._payload(),  # type: ignore[attr-defined]
        ),
    )


def test_production_verifier_api_has_no_counts_status_rows_or_callbacks() -> None:
    signature = inspect.signature(
        verifier
        .verify_registered_incremental_h2_model_epoch_independently_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
        "prior_epoch",
        "selector_closure",
        "claimed",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    assert {
        "rows",
        "observations",
        "law",
        "seed",
        "counts",
        "status",
        "callback",
        "online_evidence",
    }.isdisjoint(signature.parameters)


def test_verifier_never_calls_materializer_acquisition_or_target_stream() -> None:
    path = Path(verifier.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "materialize_registered_incremental_h2_model_epoch_v1",
        "materialize_registration_disjoint_incremental_epoch_v1",
        "acquire_registered_target_row_v1",
        "verify_registered_target_confidence_independently_v1",
        "open_heldout_target_transition_stream_v2",
        "evaluation_only_exact_atoms_v2",
        "draw",
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }
    assert forbidden.isdisjoint(called)


def test_invalid_production_gate_fails_with_zero_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("TARGET_ACCESS")
        raise AssertionError("independent verifier touched target")

    for module, name in (
        (observer, "_environment_law"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
        (observer.AnchorGatedHeldoutTransitionStreamV2, "draw"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(
        verifier.RegisteredIncrementalEpochIndependentVerifierLockedV1
    ) as captured:
        verifier.verify_registered_incremental_h2_model_epoch_independently_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            context=object(),  # type: ignore[arg-type]
            prior_epoch=object(),  # type: ignore[arg-type]
            selector_closure=object(),  # type: ignore[arg-type]
            claimed=object(),  # type: ignore[arg-type]
        )
    assert captured.value.access_audit == verifier.ZERO_ACCESS_AUDIT
    assert captured.value.access_audit.target_access_started is False
    assert calls == []


def test_round_one_whole_epoch_replay_is_exact_and_offline() -> None:
    cold, selected, claimed = _round_one()
    attestation = (
        verifier
        .verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=cold,
            selector_closure=selected,
            claimed=claimed,
        )
    )
    expected = (
        prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
        + 2
        * (
            prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )
    )
    assert attestation.round_index == 1
    assert attestation.prior_epoch_id == cold.epoch_id
    assert attestation.selector_closure_id == selected.closure_id
    assert attestation.claimed_epoch_id == claimed.epoch_id
    assert attestation.historical_acquisition_ids == _history_ids(claimed)
    assert attestation.active_acquisition_ids == (
        claimed.active_acquisition_ids
    )
    assert attestation.producer_draws == expected
    assert attestation.independent_replay_draws == expected
    assert attestation.registered_target_accesses == 0
    assert len(attestation.verification_id) == 64


def test_round_two_replay_requires_dependent_latest_parent() -> None:
    _cold_epoch, _first_selector, first = _round_one()
    selected = _selector(
        first,
        parent_label="D",
        children=("F",),
    )
    second = (
        materializer
        .materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=first,
            selector_closure=selected,
        )
    )
    attestation = (
        verifier
        .verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=first,
            selector_closure=selected,
            claimed=second,
        )
    )
    assert attestation.round_index == 2
    assert attestation.prior_epoch_id == first.epoch_id
    assert set(_history_ids(first)) < set(_history_ids(second))
    assert len(second.active_acquisition_ids) == 6
    assert attestation.registered_target_accesses == 0


@pytest.mark.parametrize(
    "attack",
    ("dropped_history", "superseded_active", "reordered_history"),
)
def test_history_attacks_fail_even_when_outer_epoch_is_rehashed(
    attack: str,
) -> None:
    cold, selected, claimed = _round_one()
    attacked = copy.deepcopy(claimed)
    if attack == "dropped_history":
        object.__setattr__(
            attacked,
            "acquisition_history",
            attacked.acquisition_history[1:],
        )
    elif attack == "superseded_active":
        old = _row(attacked, "A", latest=False)
        latest = _row(attacked, "A", latest=True)
        object.__setattr__(
            attacked,
            "active_acquisition_ids",
            tuple(
                sorted(
                    old.acquisition_id
                    if item == latest.acquisition_id
                    else item
                    for item in attacked.active_acquisition_ids
                )
            ),
        )
    else:
        object.__setattr__(
            attacked,
            "acquisition_history",
            tuple(reversed(attacked.acquisition_history)),
        )
    _rehash_synthetic_epoch(attacked)
    with pytest.raises(
        verifier.V072RegisteredIncrementalEpochIndependentVerificationFailure
    ):
        verifier.verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=cold,
            selector_closure=selected,
            claimed=attacked,
        )


def test_missing_selected_child_fails_after_outer_rehash() -> None:
    cold, selected, claimed = _round_one()
    attacked = copy.deepcopy(claimed)
    object.__setattr__(
        attacked,
        "new_acquisition_ids",
        attacked.new_acquisition_ids[:-1],
    )
    _rehash_synthetic_epoch(attacked)
    with pytest.raises(
        verifier.V072RegisteredIncrementalEpochIndependentVerificationFailure,
        match="selected child",
    ):
        verifier.verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=cold,
            selector_closure=selected,
            claimed=attacked,
        )


def test_replay_substitution_fails_after_outer_rehash() -> None:
    cold, selected, claimed = _round_one()
    attacked = copy.deepcopy(claimed)
    first, second = attacked.acquisition_history[:2]
    object.__setattr__(first, "_replay_id", second.replay_id)
    _rehash_synthetic_epoch(attacked)
    with pytest.raises(
        verifier.V072RegisteredIncrementalEpochIndependentVerificationFailure,
        match="producer/replay",
    ):
        verifier.verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=cold,
            selector_closure=selected,
            claimed=attacked,
        )


def test_source_quantity_cannot_enter_confidence_replay() -> None:
    cold, selected, claimed = _round_one()
    attacked = copy.deepcopy(claimed)
    target = attacked.acquisition_history[-1]
    source_tainted_replay_id = verifier._hash(  # type: ignore[attr-defined]
        materializer.DOMAIN_TAGS["synthetic_replay"],
        {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_replay.v1"
            ),
            "schema_version": materializer.SCHEMA_VERSION,
            "acquisition_id": target.acquisition_id,
            "producer_draws": target.producer_draws,
            "independent_replay_draws": target.producer_draws,
            "source_prior_used_in_confidence": True,
            "registered_target_accesses": 0,
        },
    )
    object.__setattr__(target, "_replay_id", source_tainted_replay_id)
    _rehash_synthetic_epoch(attacked)
    with pytest.raises(
        verifier.V072RegisteredIncrementalEpochIndependentVerificationFailure,
        match="confidence origin",
    ):
        verifier.verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=cold,
            selector_closure=selected,
            claimed=attacked,
        )


def test_round_two_stale_parent_fails_closed() -> None:
    _cold_epoch, _first_selector, first = _round_one()
    valid = _selector(
        first,
        parent_label="A",
        children=("F",),
    )
    second = (
        materializer
        .materialize_registration_disjoint_incremental_epoch_v1(
            prior_epoch=first,
            selector_closure=valid,
        )
    )
    stale = _selector(
        first,
        parent_label="A",
        children=("F",),
        latest_parent=False,
    )
    attacked = copy.deepcopy(second)
    object.__setattr__(attacked, "frontier_id", stale.frontier_id)
    _rehash_synthetic_epoch(attacked)
    with pytest.raises(
        verifier.V072RegisteredIncrementalEpochIndependentVerificationFailure,
        match="stale or superseded",
    ):
        verifier.verify_registration_disjoint_incremental_epoch_independently_v1(
            prior_epoch=first,
            selector_closure=stale,
            claimed=attacked,
        )


def test_offline_replay_draws_are_not_online_sample_evidence() -> None:
    audit = verifier.RegisteredIncrementalEpochVerifierAccessAuditV1(
        producer_artifact_replays=7,
        confidence_bundle_replays=7,
    )
    assert audit.target_access_started is False
    assert audit.observer_stream_opens == 0
    assert audit.observer_draw_calls == 0
    assert "unique_online_sample_evidence_draws" not in audit.to_document()
