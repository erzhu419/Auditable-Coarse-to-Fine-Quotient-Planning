from __future__ import annotations

import copy
import dataclasses
import hashlib
from pathlib import Path

import pytest

import acfqp.construction_k7_direct_fallback_exact_infeasibility_readiness_v1 as readiness
import acfqp.phase3e_exact_infeasibility_durable_proof_v1 as durable
from acfqp.phase05 import _fixture
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackOutcome,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def proof_bytes() -> bytes:
    return durable.issue_phase3e_exact_infeasibility_durable_proof_v1(
        CANONICAL_BUNDLE
    )


@pytest.fixture(scope="module")
def proof_document(proof_bytes: bytes) -> dict:
    document = loads_canonical_json(proof_bytes)
    assert type(document) is dict
    return document


def _cap(*, max_actions: int = 100, max_composed: int = 1_000):
    return GroundFallbackCapProfileV1(
        max_states_expanded=100,
        max_actions_evaluated=max_actions,
        max_ground_steps=max_actions,
        max_outcome_rows=max(6, 6 * max_actions),
        max_bellman_backups=max_composed,
        max_composed_candidates=max_composed,
        max_cap_checks=2_000,
        max_positive_outcomes_per_step=6,
    )


def _execution(proof_document: dict, *, capped: bool = False):
    fixture = _fixture("g2048")
    return run_ground_fallback_search_v1(
        fixture.kernel,
        fixture.query,
        route_decision_context_id=_id("k7-infeasible:context"),
        decision_point_id=_id("k7-infeasible:decision-point"),
        route_decision_id=_id("k7-infeasible:route-decision"),
        selected_upper_id=_id("k7-infeasible:selected-upper"),
        route_attempt_id=_id("k7-infeasible:route-attempt"),
        query_id=proof_document["identity"]["query_id"],
        cap_profile=(
            _cap(max_actions=1, max_composed=10)
            if capped
            else _cap()
        ),
    )


@pytest.fixture(scope="module")
def exact_execution(proof_document: dict):
    execution = _execution(proof_document)
    assert execution.result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    return execution


def _codes(assessment) -> set[str]:
    return {row.code.value for row in assessment.blockers}


def test_real_identical_query_fallback_is_exact_but_not_a_k7_202_occurrence(
    proof_bytes: bytes,
    proof_document: dict,
    exact_execution,
) -> None:
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=exact_execution,
    )
    document = result.to_document()

    assert result.outcome is readiness.DirectFallbackReadinessOutcomeV1.BLOCKED
    assert result.durable_proof_outcome == "IDENTICAL_MATCH"
    assert result.fallback_query_id == proof_document["identity"]["query_id"]
    assert result.fallback_outcome == "INFEASIBLE_CERTIFIED"
    assert result.fallback_v1_counter_record_count == 42
    assert result.fallback_v1_counter_record_count != 202
    assert len(result.evidence_role_dispositions) == 11  # ten FQ9 roles + proof
    states = {row.role: row.state.value for row in result.evidence_role_dispositions}
    assert states["EXACT_GROUND_INFEASIBILITY_PROOF"] == (
        "EVALUATION_VERIFIED_IDENTITY_MATCH_NOT_OPERATIONAL"
    )
    assert document["required_k7_counter_record_count"] == 202
    assert document["required_comparison_axis_count"] == 8
    assert document["ground_solver_called_by_assessment"] is False
    assert document["counter_records_issued"] == 0
    assert document["work_vectors_issued"] == 0
    assert document["comparison_vectors_issued"] == 0
    assert document["terminal_artifact_issued"] is False
    assert document["logical_occurrence_closure_issued"] is False
    assert document["formal_terminal_authorized"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert all(
        value == 0
        for path, value in exact_execution.work_vector.values.items()
        if path.startswith("local.") or path.startswith("rebuild.")
    )
    assert _codes(result) >= {
        "FALLBACK_SEARCH_COMPLETENESS_NOT_DURABLE",
        "FALLBACK_V1_WORK_VECTOR_NOT_K7_202_COUNTER_RECORDS",
        "COUNTER_RECORD_SET_AUTHORITY_MISSING",
        "SHARED_RESOURCE_RECEIPT_SET_AUTHORITY_MISSING",
        "DIRECT_FALLBACK_FORMAL_MATERIALIZER_MISSING",
        "DIRECT_FALLBACK_COMPLETE_BUNDLE_VERIFIER_MISSING",
        "EXACT_INFEASIBILITY_TERMINAL_AUTHORITY_MISSING",
        "LOGICAL_OCCURRENCE_CLOSURE_MISSING",
    }
    assert "FALLBACK_QUERY_ID_NOT_IDENTICAL" not in _codes(result)


def test_assessment_never_replays_the_operational_ground_solver(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    exact_execution,
) -> None:
    import acfqp.phase3e_fallback_v1 as fallback

    def forbidden(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("assessment called the operational ground solver")

    monkeypatch.setattr(fallback, "run_ground_fallback_search_v1", forbidden)
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=exact_execution,
    )
    assert result.to_document()["durable_proof_lane"] == "EVALUATION"
    assert result.to_document()["durable_proof_charged_as_operational_route_work"] is False


def test_missing_execution_is_an_explicit_blocker_not_a_proof_only_terminal(
    proof_bytes: bytes,
) -> None:
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes
    )
    assert "FALLBACK_EXECUTION_ABSENT" in _codes(result)
    assert result.fallback_result_id is None
    assert result.fallback_work_vector_id is None
    assert result.to_document()["formal_terminal_authorized"] is False


def test_cap_exhaustion_remains_a_noncertificate_even_with_matching_query(
    proof_bytes: bytes,
    proof_document: dict,
) -> None:
    execution = _execution(proof_document, capped=True)
    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=execution,
    )
    assert "FALLBACK_CAP_EXHAUSTED_NONCERTIFICATE" in _codes(result)
    assert "FALLBACK_SEARCH_COMPLETENESS_NOT_DURABLE" not in _codes(result)
    states = {row.role: row.state.value for row in result.evidence_role_dispositions}
    assert states["GROUND_FALLBACK"] == "CAP_EXHAUSTED_NONCERTIFICATE"
    assert result.to_document()["terminal_artifact_issued"] is False


def test_valid_proof_for_another_identity_is_no_match_and_cannot_close(
    proof_bytes: bytes,
    proof_document: dict,
    exact_execution,
) -> None:
    identity = dataclasses.replace(
        durable.DurableExactInfeasibilityIdentityV1.from_dict(
            proof_document["identity"]
        ),
        query_id=_id("different-query"),
    )
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=exact_execution,
        current_identity=identity,
    )
    assert result.durable_proof_outcome == "NO_MATCH"
    assert "DURABLE_PROOF_IDENTITY_MISMATCH" in _codes(result)
    states = {row.role: row.state.value for row in result.evidence_role_dispositions}
    assert states["EXACT_GROUND_INFEASIBILITY_PROOF"] == (
        "EVALUATION_INVALID_OR_IDENTITY_MISMATCH"
    )
    assert result.to_document()["formal_terminal_authorized"] is False


@pytest.mark.parametrize(
    "attack",
    (
        "claim_ready",
        "claim_202",
        "claim_terminal",
        "drop_blockers",
        "change_proof_lane",
        "change_digest",
    ),
)
def test_independent_document_replay_rejects_every_overclaim(
    proof_bytes: bytes,
    exact_execution,
    attack: str,
) -> None:
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=exact_execution,
    )
    document = copy.deepcopy(result.to_document())
    if attack == "claim_ready":
        document["outcome"] = "READY"
    elif attack == "claim_202":
        document["fallback_v1_counter_record_count"] = 202
    elif attack == "claim_terminal":
        document["terminal_artifact_issued"] = True
        document["formal_terminal_authorized"] = True
    elif attack == "drop_blockers":
        document["blockers"] = []
    elif attack == "change_proof_lane":
        document["durable_proof_lane"] = "OPERATIONAL"
        document["durable_proof_charged_as_operational_route_work"] = True
    else:
        document["readiness_document_sha256"] = _id("forged-digest")
    with pytest.raises(
        readiness.ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error,
        match="differs from independent replay",
    ):
        readiness.verify_construction_k7_direct_fallback_exact_infeasibility_readiness_document_v1(
            document,
            proof_bytes,
            fallback_execution=exact_execution,
        )


def test_exact_source_archive_mutation_blocks_before_any_accounting_claim(
    proof_bytes: bytes,
    exact_execution,
) -> None:
    import acfqp.construction_k7_all_path_operation_boundary_manifest_v1 as boundary

    archive = boundary.load_official_operation_boundary_source_archive_v1()
    changed = dict(archive)
    key = "acfqp.phase3e_fallback_v1"
    changed[key] = changed[key] + b"\n# changed\n"
    with pytest.raises(
        readiness.ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error,
        match="source replay is blocked",
    ):
        readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
            proof_bytes,
            fallback_execution=exact_execution,
            source_archive=changed,
        )


def test_callers_cannot_construct_a_ready_assessment(
    proof_bytes: bytes,
    exact_execution,
) -> None:
    result = readiness.assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=exact_execution,
    )
    with pytest.raises(
        readiness.ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error,
        match="outcome must remain BLOCKED|readiness outcome",
    ):
        dataclasses.replace(result, outcome="READY")
