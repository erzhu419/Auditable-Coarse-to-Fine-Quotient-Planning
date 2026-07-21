from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.partial_model_planner_v1 as planner_module
from acfqp.partial_model_planner_v1 import (
    PRODUCTION_CANDIDATE_CAP,
    PRODUCTION_CAP_PROFILE_ID,
    PartialModelPlanProposalResultV1,
    PartialModelPlannerExecutionProfile,
    PartialModelPlannerInvariantViolation,
    PartialModelPlannerOutcome,
    PartialModelPlannerSelectionMode,
    PartialModelPlannerTraceV1,
    PartialPlannerCellActionDomainV1,
    propose_partial_model_plan_v1,
    verify_partial_model_plan_proposal_v1,
)
from acfqp.partial_sound_audit_v1 import (
    FailedProofReason,
    PartialAuditOutcome,
    audit_partial_fixed_plan_v1,
)
from tests.test_partial_sound_audit_v1 import (
    _modified_row_deletion,
    _nonmatching_plan,
    _thresholds,
    audit_contract as audit_contract_fixture,
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _propose(contract, thresholds):
    return propose_partial_model_plan_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        thresholds,
    )


@pytest.fixture(scope="module")
def planner_contract():
    contract = audit_contract_fixture.__wrapped__()
    proposal_result = _propose(contract, contract["positive_thresholds"])
    return {**contract, "proposal_result": proposal_result}


def test_h3_enumerates_all_eight_plans_and_proposes_exact_four_reward(
    planner_contract,
) -> None:
    contract = planner_contract
    result = contract["proposal_result"]
    trace = result.trace

    assert trace.outcome is PartialModelPlannerOutcome.PLAN_PROPOSED
    assert trace.execution_profile is PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL
    assert trace.candidate_cap == PRODUCTION_CANDIDATE_CAP == 65536
    assert trace.cap_profile_id == PRODUCTION_CAP_PROFILE_ID
    assert trace.per_stage_assignment_count == 2
    assert trace.candidate_count == trace.candidate_evaluated_count == 8
    assert trace.source_graph_reconstruction_count == 9
    assert trace.fixed_plan_audit_count == 8
    assert trace.work_economics_claimed is False
    assert trace.enumeration_complete is True
    assert trace.selection_mode is PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
    assert result.selected_plan is not None
    assert result.selected_plan.plan_id == trace.selected_plan_id
    assert (
        result.selected_plan.plan_id
        == "1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc"
    )
    selected = next(
        item
        for item in trace.candidate_summaries
        if item.contingent_plan_id == trace.selected_plan_id
    )
    assert selected.policy_reward_lower == selected.policy_reward_upper == 4
    assert selected.policy_failure_lower == selected.policy_failure_upper == 0
    assert selected.raw_distribution_regret == 0
    assert selected.normalized_distribution_regret == 0
    assert selected.maximum_support_point_normalized_regret == 0
    assert selected.risk_feasible is True
    assert selected.audit_outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert result.proposal_is_certificate_authority is False
    assert result.selected_plan_requires_independent_v0043_audit is True
    assert result.feasible_plan_claimed is False
    assert result.infeasible_query_claimed is False
    assert result.optimal_ground_policy_claimed is False

    independent = audit_partial_fixed_plan_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        contract["positive_thresholds"],
        result.selected_plan,
    )
    assert independent.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert independent.result_id == selected.audit_result_id
    assert independent.certificate is not None


def test_independent_verifier_reconstructs_enumerates_audits_and_selects(
    planner_contract,
) -> None:
    contract = planner_contract
    replayed = verify_partial_model_plan_proposal_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        contract["positive_thresholds"],
        contract["proposal_result"],
    )
    assert replayed.to_document() == contract["proposal_result"].to_document()


def test_h1_missing_state_reuses_model_and_proposes_frontier_plan(
    planner_contract,
) -> None:
    contract = planner_contract
    thresholds = _thresholds(
        contract["model"], contract["missing_state_id"], horizon=1
    )
    result = _propose(contract, thresholds)

    assert result.trace.partial_model_id == contract["proposal_result"].trace.partial_model_id
    assert result.trace.thresholds_id != contract["proposal_result"].trace.thresholds_id
    assert result.trace.candidate_count == 2
    assert result.trace.selection_mode is PartialModelPlannerSelectionMode.MIN_FAILURE_RISK_FALLBACK
    assert result.selected_plan is not None
    selected = next(
        item
        for item in result.trace.candidate_summaries
        if item.contingent_plan_id == result.selected_plan.plan_id
    )
    assert selected.policy_reward_lower == 0
    assert selected.policy_reward_upper == 3
    assert selected.policy_failure_upper == 1
    assert selected.risk_feasible is False
    assert selected.audit_outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER

    independent = audit_partial_fixed_plan_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        thresholds,
        result.selected_plan,
    )
    assert independent.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert (
        independent.failed_proof_frontier.reason
        is FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    )
    assert independent.failed_proof_frontier.local_recovery_authorized is False
    assert result.proposal_is_certificate_authority is False


def test_selection_rule_and_plan_identity_are_structural_invariants(
    planner_contract,
) -> None:
    result = planner_contract["proposal_result"]
    trace = result.trace
    certified = tuple(
        item
        for item in trace.candidate_summaries
        if item.audit_outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    )
    expected = min(
        certified,
        key=lambda item: (
            -item.policy_reward_lower,
            item.policy_failure_upper,
            item.contingent_plan_id,
        ),
    )
    assert trace.selected_plan_id == expected.contingent_plan_id

    uncertified = next(
        item
        for item in trace.candidate_summaries
        if item.audit_outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    )
    risk_feasible_but_uncertified = replace(
        uncertified,
        policy_reward_lower=Fraction(4),
        policy_reward_upper=Fraction(4),
        policy_failure_lower=Fraction(0),
        policy_failure_upper=Fraction(0),
        risk_feasible=True,
    )
    tier_mode, tier_selected = planner_module._selected_summary(
        tuple(
            sorted(
                (expected, risk_feasible_but_uncertified),
                key=lambda item: item.contingent_plan_id,
            )
        )
    )
    assert (
        tier_mode
        is PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
    )
    assert tier_selected.contingent_plan_id == expected.contingent_plan_id

    other = next(
        item
        for item in trace.candidate_summaries
        if item.contingent_plan_id != trace.selected_plan_id
    )
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="canonical constrained rule"
    ):
        replace(trace, selected_plan_id=other.contingent_plan_id)
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="plan-ID sorted"
    ):
        replace(trace, candidate_summaries=tuple(reversed(trace.candidate_summaries)))

    different_plan = _nonmatching_plan(planner_contract["model"], 3)
    assert different_plan.plan_id != result.selected_plan.plan_id
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="selected plan"
    ):
        replace(result, selected_plan=different_plan)


def test_fixed_cap_and_named_nonproduction_cap_control_are_separate(
    planner_contract,
) -> None:
    contract = planner_contract
    production_profile = planner_module._cap_profile_payload(
        PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL,
        PRODUCTION_CANDIDATE_CAP,
    )
    control_profile = planner_module._cap_profile_payload(
        PartialModelPlannerExecutionProfile.NONPRODUCTION_CAP_CONTROL,
        4,
    )
    assert PRODUCTION_CANDIDATE_CAP == 65536
    assert (
        PRODUCTION_CAP_PROFILE_ID
        == "9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b"
    )
    assert production_profile["candidate_cap"] == PRODUCTION_CANDIDATE_CAP
    assert production_profile["caller_cap_allowed"] is False
    assert production_profile["production_claimed"] is True
    assert (
        control_profile["execution_profile"]
        == PartialModelPlannerExecutionProfile.NONPRODUCTION_CAP_CONTROL.value
    )
    assert control_profile["candidate_cap"] == 4
    assert control_profile["caller_cap_allowed"] is True
    assert control_profile["production_claimed"] is False

    capped = planner_module._propose_partial_model_plan_nonproduction_cap_control_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        contract["positive_thresholds"],
        candidate_cap=4,
    )

    assert capped.trace.outcome is PartialModelPlannerOutcome.CAP_EXHAUSTED
    assert capped.trace.candidate_count == 8
    assert capped.trace.candidate_cap == 4
    assert capped.trace.candidate_evaluated_count == 0
    assert capped.trace.source_graph_reconstruction_count == 1
    assert capped.trace.fixed_plan_audit_count == 0
    assert capped.trace.work_economics_claimed is False
    assert capped.trace.candidate_summaries == ()
    assert capped.trace.selection_mode is PartialModelPlannerSelectionMode.NOT_APPLICABLE
    assert capped.trace.production_profile is False
    assert capped.trace.enumeration_complete is False
    assert capped.selected_plan is None
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="production proposals only"
    ):
        verify_partial_model_plan_proposal_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
            contract["positive_thresholds"],
            capped,
        )
    with pytest.raises(TypeError):
        propose_partial_model_plan_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
            contract["positive_thresholds"],
            candidate_cap=4,  # type: ignore[call-arg]
        )


def test_source_graph_reconstruction_precedes_threshold_access(
    planner_contract,
) -> None:
    contract = planner_contract
    modified_build = _modified_row_deletion(contract)
    touched: list[str] = []

    class ThresholdWithSideEffects:
        def __getattribute__(self, name):
            touched.append(name)
            raise AssertionError("threshold accessed before reconstruction")

    with pytest.raises(
        PartialModelPlannerInvariantViolation,
        match="source graph failed trusted reconstruction",
    ):
        propose_partial_model_plan_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            modified_build,
            ThresholdWithSideEffects(),  # type: ignore[arg-type]
        )
    assert touched == []


def test_api_and_import_graph_are_transition_and_ground_solver_blind_with_one_threshold_input(
    planner_contract,
) -> None:
    assert tuple(inspect.signature(propose_partial_model_plan_v1).parameters) == (
        "observation_log",
        "coordinate_proposal",
        "semantics_profile",
        "observation_authority",
        "partial_build_result",
        "thresholds",
    )
    assert tuple(
        inspect.signature(verify_partial_model_plan_proposal_v1).parameters
    ) == (
        "observation_log",
        "coordinate_proposal",
        "semantics_profile",
        "observation_authority",
        "partial_build_result",
        "thresholds",
        "claimed_result",
    )
    imports = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(planner_module)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "fractions",
        "itertools",
        "typing",
        "acfqp.observation_partial_rapm_v1",
        "acfqp.partial_sound_audit_v1",
        "acfqp.phase3e_ids",
    }
    assert not any(item.startswith("acfqp.domains") for item in imports)
    assert not any(item.startswith("acfqp.planning") for item in imports)
    with pytest.raises(TypeError):
        propose_partial_model_plan_v1(
            planner_contract["log"],
            planner_contract["proposal"],
            planner_contract["profile"],
            planner_contract["authority"],
            planner_contract["result"],
            planner_contract["positive_thresholds"],
            kernel=object(),  # type: ignore[call-arg]
        )
    with pytest.raises(TypeError):
        propose_partial_model_plan_v1(
            planner_contract["log"],
            planner_contract["proposal"],
            planner_contract["profile"],
            planner_contract["authority"],
            planner_contract["result"],
            planner_contract["positive_thresholds"],
            query=object(),  # type: ignore[call-arg]
        )


def test_content_consistency_and_strict_nested_type_regressions(
    planner_contract,
) -> None:
    contract = planner_contract
    result = contract["proposal_result"]
    trace = result.trace
    first = trace.candidate_summaries[0]
    modified_first = replace(first, audit_result_id=_hash("modified-audit-result"))
    modified_summaries = tuple(
        modified_first if item is first else item
        for item in trace.candidate_summaries
    )
    modified_trace = replace(trace, candidate_summaries=modified_summaries)
    modified_result = replace(result, trace=modified_trace)
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="full deterministic replay"
    ):
        verify_partial_model_plan_proposal_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
            contract["positive_thresholds"],
            modified_result,
        )
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="duck result"
    ):
        verify_partial_model_plan_proposal_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
            contract["positive_thresholds"],
            object(),  # type: ignore[arg-type]
        )

    touched: list[str] = []

    class SideEffectIterable:
        def __iter__(self):
            touched.append("iterated")
            yield _hash("semantic-action")

    cell_id = trace.action_domains[0].cell_id
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="exact tuple"
    ):
        PartialPlannerCellActionDomainV1(
            cell_id, SideEffectIterable()  # type: ignore[arg-type]
        )
    assert touched == []
    with pytest.raises(
        PartialModelPlannerInvariantViolation, match="duck candidate summaries"
    ):
        replace(trace, candidate_summaries=list(trace.candidate_summaries))


def test_content_ids_are_stable_and_bound_to_both_queries(planner_contract) -> None:
    contract = planner_contract
    first = contract["proposal_result"]
    second_thresholds = _thresholds(
        contract["model"], contract["missing_state_id"], horizon=1
    )
    second = _propose(contract, second_thresholds)

    assert len(first.result_id) == len(first.trace.trace_id) == 64
    assert len(second.result_id) == len(second.trace.trace_id) == 64
    assert first.trace.partial_model_id == second.trace.partial_model_id
    assert first.trace.partial_build_result_id == second.trace.partial_build_result_id
    assert first.trace.thresholds_id != second.trace.thresholds_id
    assert first.result_id != second.result_id
    assert first.to_document() == _propose(
        contract, contract["positive_thresholds"]
    ).to_document()
