from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

import acfqp.partial_model_planner_v1 as planner_module
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    PRODUCTION_CANDIDATE_CAP,
    PartialModelPlannerInvariantViolation,
    PartialModelPlannerOutcome,
    PartialModelPlannerSelectionMode,
    TypedPartialModelPlanProposalResultV2,
    propose_partial_model_plan_from_observed_synthesis_v2,
    verify_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    FailedProofReason,
    PartialAuditOutcome,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)
from tests.test_partial_sound_audit_v1 import _thresholds


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def typed_planner_contract():
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    model = synthesis.partial_build_result.model
    initial_state_id = source["observed_by_ground"][source["initial"]].state_id
    missing_state_id = source["observed_by_ground"][source["extra"]].state_id
    h3_thresholds = _thresholds(model, initial_state_id, horizon=3)
    h3_result = propose_partial_model_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        h3_thresholds,
    )
    return {
        **source,
        "synthesis": synthesis,
        "model": model,
        "initial_state_id": initial_state_id,
        "missing_state_id": missing_state_id,
        "h3_thresholds": h3_thresholds,
        "h3_result": h3_result,
    }


def test_typed_planner_has_one_closed_source_surface(typed_planner_contract) -> None:
    assert tuple(
        inspect.signature(
            propose_partial_model_plan_from_observed_synthesis_v2
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
    )
    assert tuple(
        inspect.signature(
            verify_partial_model_plan_from_observed_synthesis_v2
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "claimed_result",
    )
    with pytest.raises(TypeError):
        propose_partial_model_plan_from_observed_synthesis_v2(
            typed_planner_contract["log"],
            typed_planner_contract["profile"],
            typed_planner_contract["authority"],
            typed_planner_contract["synthesis"],
            typed_planner_contract["h3_thresholds"],
            model=typed_planner_contract["model"],  # type: ignore[call-arg]
        )
    function_source = inspect.getsource(
        planner_module.propose_partial_model_plan_from_observed_synthesis_v2
    )
    assert "_audit_verified_partial_model_v1" in function_source
    assert "audit_partial_fixed_plan_from_observed_synthesis_v2" not in function_source


def test_h3_typed_source_enumerates_and_selects_a_certifiable_plan(
    typed_planner_contract,
) -> None:
    result = typed_planner_contract["h3_result"]
    assert type(result) is TypedPartialModelPlanProposalResultV2
    trace = result.trace
    synthesis = typed_planner_contract["synthesis"]

    assert trace.observed_synthesis_result_id == synthesis.result_id
    assert (
        trace.observed_synthesis_certificate_id
        == synthesis.certificate.certificate_id
    )
    assert trace.coordinate_proposal_id == synthesis.coordinate_proposal.proposal_id
    assert trace.partial_build_result_id == synthesis.partial_build_result.result_id
    assert trace.partial_model_id == synthesis.partial_build_result.model.model_id
    assert trace.outcome is PartialModelPlannerOutcome.PLAN_PROPOSED
    assert trace.candidate_cap == PRODUCTION_CANDIDATE_CAP
    assert trace.per_stage_assignment_count == 2
    assert trace.candidate_count == trace.candidate_evaluated_count == 8
    assert trace.fixed_plan_audit_count == 8
    assert trace.retained_v0045_full_replay_count == 1
    assert trace.internal_audit_source_replay_count == 0
    assert (
        trace.selection_mode
        is PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
    )
    assert result.selected_plan is not None
    assert trace.trace_id == (
        "e43977eb1550ef061b7757d3ac36dd640ce9ebc09cb53943925bfb9e03a22616"
    )
    assert result.result_id == (
        "4201c591132a6245df3a4989c7d9c9a9c2b9bab67132e679762b31ef2b1d3b6f"
    )
    assert result.selected_plan.plan_id == (
        "5397faf055fefeaaca2415f07ca2783c1ce580d719d20cea6befa3172dc53ace"
    )

    selected = next(
        item
        for item in trace.candidate_summaries
        if item.contingent_plan_id == result.selected_plan.plan_id
    )
    assert selected.policy_reward_lower == selected.policy_reward_upper == 4
    assert selected.policy_failure_lower == selected.policy_failure_upper == 0
    assert selected.maximum_support_point_normalized_regret == 0
    assert selected.audit_outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN

    independent = audit_partial_fixed_plan_from_observed_synthesis_v2(
        typed_planner_contract["log"],
        typed_planner_contract["profile"],
        typed_planner_contract["authority"],
        synthesis,
        typed_planner_contract["h3_thresholds"],
        result.selected_plan,
    )
    assert independent.audit_result.result_id == selected.audit_result_id
    assert independent.audit_result.certificate is not None
    assert result.proposal_is_certificate_authority is False
    assert result.selected_plan_requires_independent_typed_v0043_audit is True


def test_h1_typed_source_remains_nonauthorizing(typed_planner_contract) -> None:
    thresholds = _thresholds(
        typed_planner_contract["model"],
        typed_planner_contract["missing_state_id"],
        horizon=1,
    )
    result = propose_partial_model_plan_from_observed_synthesis_v2(
        typed_planner_contract["log"],
        typed_planner_contract["profile"],
        typed_planner_contract["authority"],
        typed_planner_contract["synthesis"],
        thresholds,
    )
    trace = result.trace
    assert trace.candidate_count == trace.candidate_evaluated_count == 2
    assert result.trace.fixed_plan_audit_count == 2
    assert result.trace.retained_v0045_full_replay_count == 1
    assert result.trace.internal_audit_source_replay_count == 0
    assert (
        trace.selection_mode
        is PartialModelPlannerSelectionMode.MIN_FAILURE_RISK_FALLBACK
    )
    assert result.selected_plan is not None
    assert trace.trace_id == (
        "ae96bb8fd9a813a66eca182191efefcb9b3780a9430dbbbccc15ef68155d9a41"
    )
    assert result.result_id == (
        "f9006103939f33ee744fd994e00240018ab445c75df1c4c23fba82d479bc6513"
    )
    assert result.selected_plan.plan_id == (
        "a199aa4177a5926a5b02947f9fd2b3cb48e92943476dea0463e2e5aeda66dde3"
    )
    selected = next(
        item
        for item in trace.candidate_summaries
        if item.contingent_plan_id == result.selected_plan.plan_id
    )
    assert selected.policy_reward_lower == 0
    assert selected.policy_reward_upper == 3
    assert selected.policy_failure_upper == 1
    assert selected.risk_feasible is False
    assert selected.audit_outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER

    independent_typed = audit_partial_fixed_plan_from_observed_synthesis_v2(
        typed_planner_contract["log"],
        typed_planner_contract["profile"],
        typed_planner_contract["authority"],
        typed_planner_contract["synthesis"],
        thresholds,
        result.selected_plan,
    )
    assert independent_typed.result_id == (
        "5974cd305c6532b6e7d6888be1ce009a119f9b37b9a39a626210466bb8c96dff"
    )
    independent = independent_typed.audit_result
    assert independent.result_id == (
        "010630bbb3692f6f555c9345835efa36078f5284ca2480c75f284a3ba44e8f42"
    )
    assert independent.failed_proof_frontier is not None
    assert independent.failed_proof_frontier.frontier_id == (
        "9d6f0803f365643d623368cdfed6b6666c5c8a00e3fd77fbdf41b00d1f354cab"
    )
    assert independent.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert (
        independent.failed_proof_frontier.reason
        is FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    )
    assert independent.failed_proof_frontier.local_recovery_authorized is False


def test_typed_verifier_replays_all_source_audits_and_rejects_substitution(
    typed_planner_contract,
) -> None:
    result = typed_planner_contract["h3_result"]
    replayed = verify_partial_model_plan_from_observed_synthesis_v2(
        typed_planner_contract["log"],
        typed_planner_contract["profile"],
        typed_planner_contract["authority"],
        typed_planner_contract["synthesis"],
        typed_planner_contract["h3_thresholds"],
        result,
    )
    assert replayed.to_document() == result.to_document()

    changed_trace = replace(
        result.trace,
        observed_synthesis_certificate_id=_hash("foreign-synthesis-certificate"),
    )
    changed = replace(result, trace=changed_trace)
    with pytest.raises(
        PartialModelPlannerInvariantViolation,
        match="differs from retained full-chain replay",
    ):
        verify_partial_model_plan_from_observed_synthesis_v2(
            typed_planner_contract["log"],
            typed_planner_contract["profile"],
            typed_planner_contract["authority"],
            typed_planner_contract["synthesis"],
            typed_planner_contract["h3_thresholds"],
            changed,
        )


def test_typed_planner_rejects_duck_synthesis_before_property_access(
    typed_planner_contract,
) -> None:
    class UnexpectedSynthesis:
        @property
        def partial_build_result(self):
            raise AssertionError("unexpected synthesis property was accessed")

    with pytest.raises(
        PartialModelPlannerInvariantViolation,
        match="duck V0-045 synthesis",
    ):
        propose_partial_model_plan_from_observed_synthesis_v2(
            typed_planner_contract["log"],
            typed_planner_contract["profile"],
            typed_planner_contract["authority"],
            UnexpectedSynthesis(),  # type: ignore[arg-type]
            typed_planner_contract["h3_thresholds"],
        )
