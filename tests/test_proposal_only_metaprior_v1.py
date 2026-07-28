from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.proposal_only_metaprior_v1 as meta


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:test:proposal-only-metaprior:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def artifacts():
    role_schema_id = _id("role-schema")
    capabilities = {
        "adjacency": _id("capability:adjacency"),
        "cardinality": _id("capability:cardinality"),
    }
    candidate_rows = (
        meta.ProposalCandidateV1(
            "predicate:linked-cardinality",
            meta.ProposalCandidateKind.PREDICATE,
            _id("semantics:predicate"),
            tuple(sorted(capabilities.values())),
            1,
        ),
        meta.ProposalCandidateV1(
            "support:selected-proof-cone",
            meta.ProposalCandidateKind.SUPPORT,
            _id("semantics:support"),
            (capabilities["adjacency"],),
            2,
        ),
        meta.ProposalCandidateV1(
            "refinement:restore-linked-geometry",
            meta.ProposalCandidateKind.REFINEMENT,
            _id("semantics:refinement"),
            (capabilities["cardinality"],),
            3,
        ),
    )
    registry = meta.build_proposal_candidate_registry_v1(
        role_schema_id,
        candidate_rows,
    )
    by_kind = {item.kind: item for item in registry.candidates}
    source_families = tuple(
        sorted((_id("source-family:a"), _id("source-family:b")))
    )
    target_family_id = _id("target-family:heldout")
    target_adapter_id = _id("target-adapter:heldout")
    envelope = meta.ProposalTransferEnvelopeV1(
        registry.registry_id,
        role_schema_id,
        source_families,
        (target_family_id,),
        (target_adapter_id,),
    )
    source_contexts = (
        (_id("source-context:a"), source_families[0]),
        (_id("source-context:b"), source_families[1]),
    )
    scores = {
        source_contexts[0][0]: {
            meta.ProposalCandidateKind.SUPPORT: Fraction(10),
            meta.ProposalCandidateKind.PREDICATE: Fraction(8),
            meta.ProposalCandidateKind.REFINEMENT: Fraction(2),
        },
        source_contexts[1][0]: {
            meta.ProposalCandidateKind.SUPPORT: Fraction(6),
            meta.ProposalCandidateKind.PREDICATE: Fraction(10),
            meta.ProposalCandidateKind.REFINEMENT: Fraction(8),
        },
    }
    observations = tuple(
        meta.SourceProposalObservationV1(
            source_context_id=context_id,
            source_family_id=family_id,
            candidate_id=candidate.candidate_id,
            proposal_score=scores[context_id][candidate.kind],
            logged_observation_count=2,
            generative_draw_count=10,
            environment_interaction_count=1,
            exact_kernel_call_count=0,
        )
        for context_id, family_id in source_contexts
        for candidate in registry.candidates
    )
    source_log = meta.build_source_proposal_observation_log_v1(
        registry,
        envelope,
        observations,
    )
    prior = meta.build_source_consensus_metaprior_v1(
        registry,
        envelope,
        source_log,
    )
    target = meta.TargetProposalApplicabilityV1(
        target_context_id=_id("target-context"),
        target_family_id=target_family_id,
        target_adapter_id=target_adapter_id,
        role_schema_id=role_schema_id,
        candidate_registry_id=registry.registry_id,
        query_id=_id("target-query"),
        build_epoch_id=_id("target-epoch"),
        frontier_snapshot_id=_id("target-frontier"),
        structural_observation_ids=tuple(
            sorted(
                (
                    _id("target-structure-observation:0"),
                    _id("target-structure-observation:1"),
                )
            )
        ),
        available_capability_ids=tuple(
            sorted(capabilities.values())
        ),
        online_accounting=meta.OnlineTargetContextAccountingV1(2),
    )
    request = meta.TargetProposalRequestV1(
        prior.prior_id,
        target.applicability_id,
        tuple(
            sorted(
                tuple(meta.ProposalCandidateKind),
                key=lambda item: item.value,
            )
        ),
        2,
    )
    proposal = meta.rank_target_proposals_v1(
        registry,
        envelope,
        prior,
        target,
        request,
    )
    verification = meta.verify_proposal_only_metaprior_v1(
        registry,
        envelope,
        source_log,
        prior,
        target,
        request,
        proposal,
    )
    return {
        "role_schema_id": role_schema_id,
        "capabilities": capabilities,
        "registry": registry,
        "by_kind": by_kind,
        "source_families": source_families,
        "target_family_id": target_family_id,
        "target_adapter_id": target_adapter_id,
        "envelope": envelope,
        "source_log": source_log,
        "prior": prior,
        "target": target,
        "request": request,
        "proposal": proposal,
        "verification": verification,
    }


def _request_for(
    artifacts,
    target: meta.TargetProposalApplicabilityV1,
    *,
    kinds: tuple[meta.ProposalCandidateKind, ...] | None = None,
    maximum: int = 2,
) -> meta.TargetProposalRequestV1:
    return meta.TargetProposalRequestV1(
        artifacts["prior"].prior_id,
        target.applicability_id,
        kinds or artifacts["request"].allowed_kinds,
        maximum,
    )


def test_source_consensus_uses_exact_cross_context_ranks(
    artifacts,
) -> None:
    prior = artifacts["prior"]
    by_kind = artifacts["by_kind"]
    assert meta.PROFILE_KEY == (
        "v0067_proposal_only_source_consensus_metaprior_v0"
    )
    assert prior.ranked_candidate_ids == (
        by_kind[meta.ProposalCandidateKind.PREDICATE].candidate_id,
        by_kind[meta.ProposalCandidateKind.SUPPORT].candidate_id,
        by_kind[meta.ProposalCandidateKind.REFINEMENT].candidate_id,
    )
    scores = {
        item.candidate_id: item for item in prior.scores
    }
    predicate = scores[
        by_kind[meta.ProposalCandidateKind.PREDICATE].candidate_id
    ]
    support = scores[
        by_kind[meta.ProposalCandidateKind.SUPPORT].candidate_id
    ]
    refinement = scores[
        by_kind[meta.ProposalCandidateKind.REFINEMENT].candidate_id
    ]
    assert (
        predicate.mean_rank,
        predicate.worst_rank,
        predicate.rank_span,
    ) == (Fraction(3, 2), Fraction(2), Fraction(1))
    assert (
        support.mean_rank,
        support.worst_rank,
        support.rank_span,
    ) == (Fraction(2), Fraction(3), Fraction(2))
    assert (
        refinement.mean_rank,
        refinement.worst_rank,
        refinement.rank_span,
    ) == (Fraction(5, 2), Fraction(3), Fraction(1))
    assert prior.target_context_ids_seen == ()
    assert prior.target_observation_ids_seen == ()


def test_ready_result_is_bounded_proposal_only_and_never_a_certificate(
    artifacts,
) -> None:
    result = artifacts["proposal"]
    by_kind = artifacts["by_kind"]
    assert result.status is meta.ProposalStatus.PROPOSAL_READY
    assert result.eligible_ranked_candidate_ids == (
        by_kind[meta.ProposalCandidateKind.PREDICATE].candidate_id,
        by_kind[meta.ProposalCandidateKind.SUPPORT].candidate_id,
        by_kind[meta.ProposalCandidateKind.REFINEMENT].candidate_id,
    )
    assert result.selected_candidate_ids == (
        by_kind[meta.ProposalCandidateKind.PREDICATE].candidate_id,
        by_kind[meta.ProposalCandidateKind.SUPPORT].candidate_id,
    )
    assert result.proposal_only
    assert not result.may_certify
    assert not result.may_narrow_target_envelopes
    assert result.target_local_acquisition_required
    assert result.target_local_certificate_required
    assert result.certificate_authority == "NONE"
    assert not result.official_execution_allowed
    assert not result.sample_efficiency_claimed
    assert artifacts["verification"].certificate_verified is False


def test_offline_source_and_online_target_accounting_remain_separate(
    artifacts,
) -> None:
    result = artifacts["proposal"]
    offline = result.offline_accounting
    online = result.online_accounting
    assert offline.lane == "OFFLINE_SOURCE"
    assert offline.source_context_count == 2
    assert offline.candidate_observation_count == 6
    assert offline.logged_observation_count == 12
    assert offline.generative_draw_count == 60
    assert offline.environment_interaction_count == 6
    assert offline.exact_kernel_call_count == 0
    assert online.lane == "ONLINE_TARGET_APPLICABILITY"
    assert online.structural_observation_count == 2
    assert online.generative_draw_count == 0
    assert online.environment_interaction_count == 0
    assert online.exact_kernel_call_count == 0
    assert online.dynamics_outcome_count == 0
    assert online.reward_label_count == 0
    assert online.certificate_label_count == 0
    document = result.to_document()
    assert "offline_accounting" in document
    assert "online_accounting" in document
    assert "total_observations" not in document
    assert "scalar_cost" not in document


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("target_family_id", _id("ood-family")),
        ("target_adapter_id", _id("ood-adapter")),
    ),
)
def test_ood_family_or_adapter_fails_closed(
    artifacts,
    field: str,
    replacement: str,
) -> None:
    target = replace(artifacts["target"], **{field: replacement})
    request = _request_for(artifacts, target)
    result = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        target,
        request,
    )
    assert result.status is meta.ProposalStatus.OOD_TARGET_REFUSED
    assert result.eligible_ranked_candidate_ids == ()
    assert result.selected_candidate_ids == ()
    assert result.certificate_authority == "NONE"


def test_source_context_cannot_be_reintroduced_as_a_target(
    artifacts,
) -> None:
    target = replace(
        artifacts["target"],
        target_context_id=artifacts["prior"].source_context_ids[0],
    )
    request = _request_for(artifacts, target)
    result = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        target,
        request,
    )

    assert result.status is meta.ProposalStatus.OOD_TARGET_REFUSED
    assert result.eligible_ranked_candidate_ids == ()
    assert result.selected_candidate_ids == ()


def test_stale_frontier_request_and_wrong_registry_fail_closed(
    artifacts,
) -> None:
    stale_target = replace(
        artifacts["target"],
        frontier_snapshot_id=_id("new-frontier"),
    )
    stale = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        stale_target,
        artifacts["request"],
    )
    assert stale.status is meta.ProposalStatus.IDENTITY_MISMATCH_REFUSED
    assert stale.selected_candidate_ids == ()

    wrong_target = replace(
        artifacts["target"],
        candidate_registry_id=_id("wrong-registry"),
    )
    wrong_request = _request_for(artifacts, wrong_target)
    wrong = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        wrong_target,
        wrong_request,
    )
    assert wrong.status is meta.ProposalStatus.IDENTITY_MISMATCH_REFUSED
    assert wrong.selected_candidate_ids == ()


def test_missing_target_capability_fails_closed(
    artifacts,
) -> None:
    target = replace(
        artifacts["target"],
        available_capability_ids=(_id("unregistered-capability"),),
    )
    request = _request_for(artifacts, target)
    result = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        target,
        request,
    )
    assert result.status is meta.ProposalStatus.MISSING_CAPABILITY_REFUSED
    assert result.selected_candidate_ids == ()
    assert result.target_local_acquisition_required
    assert result.target_local_certificate_required


def test_kind_filter_and_selection_budget_are_enforced(
    artifacts,
) -> None:
    target = artifacts["target"]
    request = _request_for(
        artifacts,
        target,
        kinds=(meta.ProposalCandidateKind.REFINEMENT,),
        maximum=1,
    )
    result = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        target,
        request,
    )
    assert result.status is meta.ProposalStatus.PROPOSAL_READY
    assert result.eligible_ranked_candidate_ids == (
        artifacts["by_kind"][
            meta.ProposalCandidateKind.REFINEMENT
        ].candidate_id,
    )
    assert result.selected_candidate_ids == (
        artifacts["by_kind"][
            meta.ProposalCandidateKind.REFINEMENT
        ].candidate_id,
    )
    with pytest.raises(meta.ProposalOnlyMetaPriorInvariantViolation):
        replace(request, maximum_proposals=9)


def test_target_outcome_reward_and_certificate_channels_are_rejected(
    artifacts,
) -> None:
    with pytest.raises(
        meta.ProposalOnlyMetaPriorInvariantViolation,
        match="structural observations only",
    ):
        replace(
            artifacts["target"].online_accounting,
            dynamics_outcome_count=1,
        )
    with pytest.raises(
        meta.ProposalOnlyMetaPriorInvariantViolation,
        match="leaked outcomes",
    ):
        replace(artifacts["target"], target_rewards_used=True)
    source_row = artifacts["source_log"].observations[0]
    with pytest.raises(
        meta.ProposalOnlyMetaPriorInvariantViolation,
        match="leaked an oracle",
    ):
        replace(source_row, source_oracle_aided=True)


def test_production_ranking_api_has_no_planner_or_certificate_channel(
    artifacts,
) -> None:
    parameters = set(
        inspect.signature(meta.rank_target_proposals_v1).parameters
    )
    forbidden = {
        "kernel",
        "transition",
        "outcomes",
        "rewards",
        "plan",
        "policy",
        "value",
        "risk",
        "audit",
        "certificate",
        "j0",
    }
    assert not parameters & forbidden
    replay = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        artifacts["target"],
        artifacts["request"],
    )
    assert replay.proposal_id == artifacts["proposal"].proposal_id


def test_frontier_and_source_evidence_changes_invalidate_identities(
    artifacts,
) -> None:
    target = replace(
        artifacts["target"],
        frontier_snapshot_id=_id("changed-frontier"),
    )
    request = _request_for(artifacts, target)
    result = meta.rank_target_proposals_v1(
        artifacts["registry"],
        artifacts["envelope"],
        artifacts["prior"],
        target,
        request,
    )
    assert target.applicability_id != artifacts["target"].applicability_id
    assert request.request_id != artifacts["request"].request_id
    assert result.proposal_id != artifacts["proposal"].proposal_id

    rows = list(artifacts["source_log"].observations)
    rows[0] = replace(
        rows[0],
        proposal_score=rows[0].proposal_score + 1,
    )
    changed_log = meta.build_source_proposal_observation_log_v1(
        artifacts["registry"],
        artifacts["envelope"],
        rows,
    )
    changed_prior = meta.build_source_consensus_metaprior_v1(
        artifacts["registry"],
        artifacts["envelope"],
        changed_log,
    )
    assert changed_log.source_log_id != artifacts["source_log"].source_log_id
    assert changed_prior.prior_id != artifacts["prior"].prior_id


def test_verifier_rejects_coherently_typed_ranking_tampering(
    artifacts,
) -> None:
    tampered = replace(
        artifacts["proposal"],
        selected_candidate_ids=(
            artifacts["proposal"].selected_candidate_ids[0],
        ),
    )
    with pytest.raises(
        meta.ProposalOnlyMetaPriorInvariantViolation,
        match="ranking replay mismatch",
    ):
        meta.verify_proposal_only_metaprior_v1(
            artifacts["registry"],
            artifacts["envelope"],
            artifacts["source_log"],
            artifacts["prior"],
            artifacts["target"],
            artifacts["request"],
            tampered,
        )
