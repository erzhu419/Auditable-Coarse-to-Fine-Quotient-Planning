"""V0-046 certificate-triggered query-local evidence/refinement regressions."""

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.query_local_refinement_v1 as refinement_module
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    EvidenceClass,
    EvidenceLane,
    QueryScopedPartialRAPMV2,
    SuccessorKind,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    PartialModelPlannerSelectionMode,
    propose_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    PartialAuditOutcome,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
)
from acfqp.query_local_refinement_v1 import (
    QueryLocalRefinementInvariantViolation,
    QueryLocalRefinementStatus,
    acquire_lmb_query_local_evidence_v1,
    authorize_minimal_query_local_evidence_v1,
    canonical_lmb_query_kernel_authority_v1,
    canonical_lmb_query_kernel_v1,
    run_lmb_h1_query_local_refinement_v1,
    verify_lmb_h1_query_local_refinement_v1,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)
from tests.test_partial_sound_audit_v1 import _thresholds


@pytest.fixture(scope="module")
def refinement_contract():
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    base_model = synthesis.partial_build_result.model
    missing_state_id = source["observed_by_ground"][source["extra"]].state_id
    thresholds = _thresholds(base_model, missing_state_id, horizon=1)
    base_proposal = propose_partial_model_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
    )
    assert base_proposal.selected_plan is not None
    failed_audit = audit_partial_fixed_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal.selected_plan,
    )
    assert failed_audit.audit_result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    base_document_before = base_model.to_document()
    kernel = canonical_lmb_query_kernel_v1()
    result = run_lmb_h1_query_local_refinement_v1(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal,
        failed_audit,
        kernel,
    )
    return {
        **source,
        "synthesis": synthesis,
        "base_model": base_model,
        "base_document_before": base_document_before,
        "thresholds": thresholds,
        "base_proposal": base_proposal,
        "failed_audit": failed_audit,
        "kernel": kernel,
        "result": result,
    }


def test_public_authority_surface_has_no_caller_selected_row_scope_or_cap() -> None:
    assert tuple(inspect.signature(authorize_minimal_query_local_evidence_v1).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
    )
    assert tuple(inspect.signature(acquire_lmb_query_local_evidence_v1).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
        "request",
        "kernel",
    )
    assert tuple(inspect.signature(run_lmb_h1_query_local_refinement_v1).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
        "kernel",
    )


def test_failed_certificate_authorizes_exactly_four_individually_necessary_rows(
    refinement_contract,
) -> None:
    contract = refinement_contract
    request = contract["result"].request
    frontier = contract["failed_audit"].audit_result.failed_proof_frontier
    assert frontier is not None

    assert request.observed_synthesis_result_id == contract["synthesis"].result_id
    assert request.base_model_id == contract["base_model"].model_id
    assert request.source_thresholds_id == contract["thresholds"].thresholds_id
    assert request.base_plan_proposal_result_id == contract["base_proposal"].result_id
    assert request.source_plan_id == contract["base_proposal"].selected_plan.plan_id
    assert request.failed_typed_audit_result_id == contract["failed_audit"].result_id
    assert request.failed_frontier_id == frontier.frontier_id
    assert request.requested_ground_row_ids == (
        contract["base_model"].coverage.missing_ground_row_ids
    )
    assert len(request.row_proofs) == request.maximum_exact_kernel_queries == 4
    assert request.frontier_obligation_count == 1
    assert request.request_preparation_kernel_calls == 0
    assert request.request_preparation_ground_search_calls == 0
    assert request.local_access_authorized is True
    assert request.global_minimum_claimed is False
    assert request.request_id == (
        "1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c"
    )
    for proof in request.row_proofs:
        assert proof.concretizer_probability == Fraction(1, 4)
        assert proof.reachable_state_mass_upper == 1
        assert proof.unresolved_failure_exposure == Fraction(1, 4)
        assert proof.leave_one_out_failure_upper == Fraction(1, 4)
        assert proof.risk_tolerance == 0
        assert proof.individually_required is True


def test_acquisition_is_exactly_the_authorized_operational_four_row_bundle(
    refinement_contract,
) -> None:
    bundle = refinement_contract["result"].evidence_bundle
    request = refinement_contract["result"].request
    authority = canonical_lmb_query_kernel_authority_v1()

    assert bundle.request_id == request.request_id
    assert bundle.kernel_authority_id == authority.authority_id
    assert authority.authority_id == (
        "2bb62669839fbde2cb4703c1ff71b71eb95cddcfdba5b3102a1833c5258164a0"
    )
    assert bundle.bundle_id == (
        "17c8783b3ab489322359bb9ed7e463c4540e9ed1d4d6036d639c1cc9a6bc8543"
    )
    assert bundle.requested_ground_row_ids == request.requested_ground_row_ids
    assert bundle.exact_kernel_query_count == 4
    assert bundle.positive_outcome_row_count == 4
    assert bundle.environment_interaction_count == 0
    assert bundle.generative_sample_count == 0
    assert bundle.synthetic_rollout_count == 0
    assert bundle.extra_ground_row_access_count == 0
    assert sum(
        item.successor.kind is SuccessorKind.REGISTERED_STATE
        for item in bundle.evidence
    ) == 1
    assert sum(
        item.successor.kind is SuccessorKind.EXTERNAL_STATE
        for item in bundle.evidence
    ) == 3
    assert all(item.reward_features == () for item in bundle.evidence)
    assert all(item.failure is False for item in bundle.evidence)
    assert all(item.terminal is False for item in bundle.evidence)
    assert all(
        item.evidence_class is EvidenceClass.EXACT_KERNEL_QUERY
        and item.evidence_lane is EvidenceLane.OPERATIONAL_QUERY
        for item in bundle.evidence
    )


def test_overlay_is_query_owned_immutable_and_closes_the_h1_rows(
    refinement_contract,
) -> None:
    contract = refinement_contract
    result = contract["result"]
    build = result.overlay_build
    model = build.model
    base = contract["base_model"]

    assert type(model) is QueryScopedPartialRAPMV2
    assert model.base_model_id == base.model_id
    assert model.model_id != base.model_id
    assert model.model_id == (
        "7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df"
    )
    assert build.result_id == (
        "90d236e9a91d852fb90891d01481e189f58739c13f8620273b860dd1628ed8fd"
    )
    assert build.build_epoch.build_epoch_id == (
        "ff0a14c296c8d5d122ff0f635ad8909dcfd2294274c99c3ac1da0412e8d947d2"
    )
    assert model.query_neutral is False
    assert model.acquisition_query_neutral_attested is False
    assert model.base_model_mutated is False
    assert model.promotion_authorized is False
    assert build.replaced_ground_row_ids == result.request.requested_ground_row_ids
    assert build.remaining_missing_ground_row_ids == ()
    assert model.coverage.missing_ground_row_ids == ()
    assert len(model.coverage.observed_ground_row_ids) == 11
    assert all(
        row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
        for row in model.ground_rows
    )
    assert build.context.evidence_request_id == result.request.request_id
    assert build.context.evidence_bundle_id == result.evidence_bundle.bundle_id
    assert build.build_epoch.parent_model_id == base.model_id
    assert build.build_epoch.child_model_id == model.model_id
    assert build.build_kernel_calls == 0
    assert base.to_document() == contract["base_document_before"]
    assert len(base.coverage.missing_ground_row_ids) == 4


def test_overlay_replanning_and_independent_audit_certify_without_more_kernel_calls(
    refinement_contract,
) -> None:
    result = refinement_contract["result"]
    proposal = result.plan_proposal
    audit = result.independent_audit.audit_result

    assert result.threshold_rebase.source_thresholds_id == (
        refinement_contract["thresholds"].thresholds_id
    )
    assert result.threshold_rebase.target_model_id == result.overlay_build.model.model_id
    assert proposal.candidate_count == proposal.fixed_plan_audit_count == 2
    assert proposal.planner_kernel_calls == 0
    assert proposal.overlay_reconstruction_count == 1
    assert (
        proposal.selection_mode
        is PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
    )
    assert audit.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert audit.robust_bounds.policy_reward_lower == 0
    assert audit.robust_bounds.policy_reward_upper == 0
    assert audit.robust_bounds.policy_failure_lower == 0
    assert audit.robust_bounds.policy_failure_upper == 0
    assert audit.robust_bounds.raw_distribution_regret == 0
    assert audit.robust_bounds.normalized_distribution_regret == 0
    assert audit.certificate is not None
    assert result.status is QueryLocalRefinementStatus.QUERY_LOCAL_PLAN_CERTIFIED
    assert result.operational_exact_kernel_queries == 4
    assert result.sample_efficiency_claimed is False
    assert result.official_execution_claimed is False
    assert result.base_model_id_before == result.base_model_id_after
    assert result.promotion.local_reuse_allowed is True
    assert result.promotion.base_promotion_authorized is False
    assert proposal.result_id == (
        "9a408b15377b10bf6450d91c0e1e26d9e7dd9ac129abc7462ce15ca69187ad3c"
    )
    assert result.independent_audit.result_id == (
        "ca91ce1aa12c701f48a19ddedd0a6cb048a27746399476912c7ca8a2ba71b8b1"
    )
    assert audit.certificate.certificate_id == (
        "ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303"
    )
    assert result.result_id == (
        "8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057"
    )


def test_scoped_chain_rejects_row_omission_bare_frontier_and_wrong_kernel(
    refinement_contract,
) -> None:
    contract = refinement_contract
    result = contract["result"]

    with pytest.raises(
        QueryLocalRefinementInvariantViolation,
        match="requested rows differ",
    ):
        replace(
            result.request,
            requested_ground_row_ids=result.request.requested_ground_row_ids[:-1],
        )

    frontier = contract["failed_audit"].audit_result.failed_proof_frontier
    assert frontier is not None
    with pytest.raises(
        QueryLocalRefinementInvariantViolation,
        match="exact typed V0-044",
    ):
        run_lmb_h1_query_local_refinement_v1(
            contract["log"],
            contract["profile"],
            contract["authority"],
            contract["synthesis"],
            contract["thresholds"],
            frontier,  # type: ignore[arg-type]
            contract["failed_audit"],
            contract["kernel"],
        )

    wrong_kernel = replace(contract["kernel"], capacity=4)
    with pytest.raises(
        QueryLocalRefinementInvariantViolation,
        match="runtime kernel differs",
    ):
        refinement_module._acquire_from_authorized(
            contract["log"], result.request, wrong_kernel
        )


def test_independent_verifier_replays_the_full_evidence_overlay_and_plan_chain(
    refinement_contract,
) -> None:
    contract = refinement_contract
    replayed = verify_lmb_h1_query_local_refinement_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        contract["thresholds"],
        contract["base_proposal"],
        contract["failed_audit"],
        contract["kernel"],
        contract["result"],
    )
    assert replayed.to_document() == contract["result"].to_document()

    with pytest.raises(
        QueryLocalRefinementInvariantViolation,
        match="status, work, base immutability, or claims",
    ):
        replace(contract["result"], operational_exact_kernel_queries=3)
