from __future__ import annotations

import copy

import pytest

import acfqp.phase3e_terminal_shape as terminal_shape
from acfqp.auditable_router import (
    ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
    FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
    FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
    INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
    LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
    PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
    REBUILD_REQUIRED_ATTEMPT_TERMINAL,
)
from acfqp.phase3e_predecision_acceptance import Phase3EPredecisionOutcome
from acfqp.phase3e_terminal_shape import (
    CARDINALITY_FRONTIER_BINDING_NOT_FROZEN,
    COMBINED_CAP_PROFILE_NOT_FROZEN,
    INFEASIBILITY_TERMINAL_SHAPE_ONLY,
    NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE,
    PLAN_TERMINAL_SHAPE_ONLY,
    SEMANTIC_EVIDENCE_GATE_NOT_RUN,
    Phase3ETerminalShapeClassification,
    TerminalShapeError,
)
from acfqp.route_protocol_guard import (
    ATTEMPT_CLOSURE_NONCERTIFICATE,
    INFEASIBILITY_CERTIFICATE_CANDIDATE,
    PLAN_CERTIFICATE_CANDIDATE,
)


def _outcome(final_state: str, outcome_kind: str) -> Phase3EPredecisionOutcome:
    return Phase3EPredecisionOutcome(
        context_id="context",
        envelope_id="envelope",
        catalog_id="catalog",
        guard_commitment_id="commitment",
        semantic_verification_ids=(),
        decision_binding_ids=(),
        final_state=final_state,
        accumulated_work_vector_id="work",
        outcome_kind=outcome_kind,
    )


@pytest.mark.parametrize(
    ("final_state", "source_kind", "expected"),
    [
        (
            ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
            PLAN_CERTIFICATE_CANDIDATE,
            PLAN_TERMINAL_SHAPE_ONLY,
        ),
        (
            LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
            PLAN_CERTIFICATE_CANDIDATE,
            PLAN_TERMINAL_SHAPE_ONLY,
        ),
        (
            FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
            PLAN_CERTIFICATE_CANDIDATE,
            PLAN_TERMINAL_SHAPE_ONLY,
        ),
        (
            INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
            INFEASIBILITY_CERTIFICATE_CANDIDATE,
            INFEASIBILITY_TERMINAL_SHAPE_ONLY,
        ),
        (
            PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
            ATTEMPT_CLOSURE_NONCERTIFICATE,
            NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE,
        ),
        (
            REBUILD_REQUIRED_ATTEMPT_TERMINAL,
            ATTEMPT_CLOSURE_NONCERTIFICATE,
            NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE,
        ),
        (
            FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
            ATTEMPT_CLOSURE_NONCERTIFICATE,
            NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE,
        ),
    ],
)
def test_verified_source_states_are_only_shape_classified(
    final_state: str, source_kind: str, expected: str
) -> None:
    classification = terminal_shape._classify_verified_predecision_outcome(
        _outcome(final_state, source_kind)
    )

    assert classification.classification == expected
    artifact = classification.to_dict()
    assert artifact["official"] is False
    assert artifact["official_scalar_cost"] is None
    assert artifact["official_n_break_even"] is None
    assert artifact["semantic_evidence_gate_status"] == SEMANTIC_EVIDENCE_GATE_NOT_RUN
    assert artifact["combined_cap_profile_status"] == COMBINED_CAP_PROFILE_NOT_FROZEN
    assert (
        artifact["cardinality_frontier_binding_status"]
        == CARDINALITY_FRONTIER_BINDING_NOT_FROZEN
    )
    assert "outcome_kind" not in artifact
    assert not any("certificate" in key.lower() for key in artifact)


@pytest.mark.parametrize(
    ("final_state", "forged_kind"),
    [
        (ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL, ATTEMPT_CLOSURE_NONCERTIFICATE),
        (PROTOCOL_FAILURE_ATTEMPT_TERMINAL, PLAN_CERTIFICATE_CANDIDATE),
        (
            INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
            PLAN_CERTIFICATE_CANDIDATE,
        ),
    ],
)
def test_malformed_source_outcome_cannot_be_laundered(
    final_state: str, forged_kind: str
) -> None:
    with pytest.raises(TerminalShapeError, match="source terminal state"):
        terminal_shape._classify_verified_predecision_outcome(
            _outcome(final_state, forged_kind)
        )


def test_terminal_module_does_not_reexport_predecision_acceptance() -> None:
    assert not hasattr(terminal_shape, "accept_phase3e_predecision_mechanics")
    assert not hasattr(terminal_shape, "Phase3EPredecisionOutcome")
    assert "evaluate_phase3e_terminal_shape" in terminal_shape.__all__


def test_direct_constructor_rejects_mismatched_classification() -> None:
    with pytest.raises(TerminalShapeError, match="disagree"):
        Phase3ETerminalShapeClassification(
            source_predecision_outcome_id="outcome",
            context_id="context",
            envelope_id="envelope",
            final_state=PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
            classification=PLAN_TERMINAL_SHAPE_ONLY,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("semantic_evidence_gate_status", "PASS", "semantic evidence"),
        ("combined_cap_profile_status", "FROZEN", "combined cap"),
        ("cardinality_frontier_binding_status", "FROZEN", "cardinality/frontier"),
        ("official", True, "cannot be official"),
    ],
)
def test_gate_or_official_promotion_is_rejected(
    field: str, value: object, message: str
) -> None:
    kwargs = {
        "source_predecision_outcome_id": "outcome",
        "context_id": "context",
        "envelope_id": "envelope",
        "final_state": ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        "classification": PLAN_TERMINAL_SHAPE_ONLY,
        field: value,
    }
    with pytest.raises(TerminalShapeError, match=message):
        Phase3ETerminalShapeClassification(**kwargs)


def test_strict_artifact_round_trip_and_content_id_check() -> None:
    original = Phase3ETerminalShapeClassification(
        source_predecision_outcome_id="outcome",
        context_id="context",
        envelope_id="envelope",
        final_state=ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        classification=PLAN_TERMINAL_SHAPE_ONLY,
    )
    payload = original.to_dict()
    assert Phase3ETerminalShapeClassification.from_dict(payload) == original

    tampered = copy.deepcopy(payload)
    tampered["classification_id"] = "forged"
    with pytest.raises(TerminalShapeError, match="content ID"):
        Phase3ETerminalShapeClassification.from_dict(tampered)


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_strict_artifact_parser_rejects_field_set_changes(mutation: str) -> None:
    payload = Phase3ETerminalShapeClassification(
        source_predecision_outcome_id="outcome",
        context_id="context",
        envelope_id="envelope",
        final_state=ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        classification=PLAN_TERMINAL_SHAPE_ONLY,
    ).to_dict()
    if mutation == "missing":
        payload.pop("context_id")
    else:
        payload["unexpected"] = 1
    with pytest.raises(TerminalShapeError, match="fields differ"):
        Phase3ETerminalShapeClassification.from_dict(payload)
