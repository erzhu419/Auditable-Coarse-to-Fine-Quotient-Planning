from __future__ import annotations

import hashlib
from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.phase3b as phase3b
import acfqp.portable_planner as portable_planner
from acfqp.portable import canonical_json, logical_id
from acfqp.portable_planner import PortableParetoPoint, PortablePlanResult
from acfqp.portable_planner import PortableRewardUpperProof, PortableRewardUpperRow


@pytest.fixture(scope="module")
def operational_case() -> tuple[
    phase3b.PortableProposal,
    phase3b.FrozenPortableRewardUpperEvidence,
]:
    domains = phase3b._construct_domains()
    domain = replace(
        domains[0],
        campaign_queries=(domains[0].campaign_queries[0],),
    )
    portable_query = domain.portable.query_from_spec(
        domain.campaign_queries[0].query
    )
    # The sound upper is frozen before the isolated planner result exists.
    evidence = phase3b.freeze_portable_reward_upper_evidence(
        domain,
        portable_query,
    )
    proposals = phase3b._fresh_process_proposals((domain,))
    assert len(proposals) == 1
    assert proposals[0].portable_query.query_id == evidence.query_id
    return proposals[0], evidence


@pytest.fixture(scope="module")
def fresh_portable_proposal(
    operational_case: tuple[
        phase3b.PortableProposal,
        phase3b.FrozenPortableRewardUpperEvidence,
    ],
) -> phase3b.PortableProposal:
    return operational_case[0]


@pytest.fixture(scope="module")
def frozen_reward_upper_evidence(
    operational_case: tuple[
        phase3b.PortableProposal,
        phase3b.FrozenPortableRewardUpperEvidence,
    ],
) -> phase3b.FrozenPortableRewardUpperEvidence:
    return operational_case[1]


def _must_not_run(*args: object, **kwargs: object) -> object:
    raise AssertionError("full host replay crossed the operational boundary")


def _serialized_sha256(document: dict) -> str:
    return hashlib.sha256(
        (canonical_json(document) + "\n").encode("utf-8")
    ).hexdigest()


def test_operational_validation_calls_no_host_planner_ground_audit_lift_or_j0(
    fresh_portable_proposal: phase3b.PortableProposal,
    frozen_reward_upper_evidence: phase3b.FrozenPortableRewardUpperEvidence,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(phase3b, "audit_abstract_policy", _must_not_run)
    monkeypatch.setattr(phase3b, "lift_semantic_policy", _must_not_run)
    monkeypatch.setattr(phase3b, "solve_ground_pareto", _must_not_run)
    monkeypatch.setattr(phase3b, "audit_exact_portable_policy", _must_not_run)
    monkeypatch.setattr(
        phase3b, "build_portable_reward_upper_proof", _must_not_run
    )
    monkeypatch.setattr(
        portable_planner,
        "solve_portable_pareto",
        _must_not_run,
    )

    validation = phase3b.validate_portable_proposal_operational_no_full_replay(
        fresh_portable_proposal,
        upper_evidence=frozen_reward_upper_evidence,
    )

    assert validation.execution_lane == "operational"
    assert validation.execution_mode == "operational_no_full_replay"
    assert validation.full_replay_performed is False
    assert validation.model_id == fresh_portable_proposal.portable_query.model_id
    assert validation.query_id == fresh_portable_proposal.portable_query.query_id
    assert validation.result_id == fresh_portable_proposal.result.result_id
    assert (
        validation.reward_upper_evidence_id
        == frozen_reward_upper_evidence.evidence_id
    )
    assert validation.selected_audit.certified
    assert validation.selected_audit.regret_upper == 0


def test_operational_validation_rejects_coordinated_false_result_bounds(
    fresh_portable_proposal: phase3b.PortableProposal,
    frozen_reward_upper_evidence: phase3b.FrozenPortableRewardUpperEvidence,
) -> None:
    result = fresh_portable_proposal.result
    assert len(result.frontier) == 1
    point = result.frontier[0]
    false_point = PortableParetoPoint(
        point.expected_reward + Fraction(1, 64),
        point.failure_probability,
        point.policy,
    )
    false_result = PortablePlanResult(
        result.model_id,
        result.query_id,
        (false_point,),
        false_point,
        result.composed_candidate_count,
    )
    attestation = dict(fresh_portable_proposal.runtime_attestation)
    attestation["result_id"] = false_result.result_id
    attestation["output_sha256"] = _serialized_sha256(false_result.to_dict())
    payload = dict(attestation)
    payload.pop("attestation_id")
    attestation["attestation_id"] = logical_id("runtime-attestation", payload)
    forged = replace(
        fresh_portable_proposal,
        result=false_result,
        runtime_attestation=attestation,
    )

    with pytest.raises(
        phase3b.Phase3BInvariantViolation,
        match="disagrees with the exact envelope",
    ):
        phase3b.validate_portable_proposal_operational_no_full_replay(
            forged,
            upper_evidence=frozen_reward_upper_evidence,
        )


def test_operational_validation_rejects_isolation_attestation_rebinding(
    fresh_portable_proposal: phase3b.PortableProposal,
    frozen_reward_upper_evidence: phase3b.FrozenPortableRewardUpperEvidence,
) -> None:
    attestation = dict(fresh_portable_proposal.runtime_attestation)
    attestation["runtime_source_sha256"] = dict(
        attestation["runtime_source_sha256"]
    )
    attestation["runtime_source_sha256"]["acfqp.portable_planner"] = "0" * 64
    payload = dict(attestation)
    payload.pop("attestation_id")
    attestation["attestation_id"] = logical_id("runtime-attestation", payload)
    forged = replace(
        fresh_portable_proposal,
        runtime_attestation=attestation,
    )

    with pytest.raises(
        phase3b.Phase3BInvariantViolation,
        match="isolation/binding validation failed",
    ):
        phase3b.validate_portable_proposal_operational_no_full_replay(
            forged,
            upper_evidence=frozen_reward_upper_evidence,
        )


def test_operational_validation_fails_closed_without_frozen_upper(
    fresh_portable_proposal: phase3b.PortableProposal,
) -> None:
    with pytest.raises(
        phase3b.Phase3BInvariantViolation,
        match="requires frozen reward-upper evidence",
    ):
        phase3b.validate_portable_proposal_operational_no_full_replay(
            fresh_portable_proposal
        )


def test_omitted_frontier_cannot_self_authorize_an_understated_upper(
    fresh_portable_proposal: phase3b.PortableProposal,
    frozen_reward_upper_evidence: phase3b.FrozenPortableRewardUpperEvidence,
) -> None:
    """A freshly rehashed self-upper still fails scalar Bellman replay."""

    proof = frozen_reward_upper_evidence.proof
    query = fresh_portable_proposal.portable_query
    initial_cells = {
        row["cell_id"] for row in query.to_dict()["initial_distribution"]
    }
    rows = list(proof.rows)
    changed = False
    for index, row in enumerate(rows):
        if row.remaining == query.horizon and row.cell_id in initial_cells:
            rows[index] = PortableRewardUpperRow(
                row.remaining,
                row.cell_id,
                row.reward_upper - Fraction(1, 64),
            )
            changed = True
            break
    assert changed
    self_upper = PortableRewardUpperProof(
        proof.model_id,
        proof.query_id,
        tuple(rows),
        proof.root_upper - Fraction(1, 64),
    )
    rehashed = phase3b.FrozenPortableRewardUpperEvidence(
        frozen_reward_upper_evidence.model_id,
        frozen_reward_upper_evidence.query_id,
        frozen_reward_upper_evidence.build_epoch_id,
        frozen_reward_upper_evidence.threshold_profile_id,
        self_upper,
    )
    assert rehashed.evidence_id != frozen_reward_upper_evidence.evidence_id

    with pytest.raises(
        phase3b.Phase3BInvariantViolation,
        match="Bellman proof is false or incomplete",
    ):
        phase3b.validate_portable_proposal_operational_no_full_replay(
            fresh_portable_proposal,
            upper_evidence=rehashed,
        )


@pytest.mark.parametrize("field", ["build_epoch_id", "threshold_profile_id"])
def test_reward_upper_evidence_rejects_stale_epoch_or_threshold(
    field: str,
    fresh_portable_proposal: phase3b.PortableProposal,
    frozen_reward_upper_evidence: phase3b.FrozenPortableRewardUpperEvidence,
) -> None:
    stale = replace(frozen_reward_upper_evidence, **{field: f"stale-{field}"})
    with pytest.raises(
        phase3b.Phase3BInvariantViolation,
        match="evidence identity binding changed",
    ):
        phase3b.validate_portable_proposal_operational_no_full_replay(
            fresh_portable_proposal,
            upper_evidence=stale,
        )
