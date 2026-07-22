from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

from acfqp.observation_partial_rapm_v1 import PlanningKind
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanAssignmentV1,
    ContingentPlanStageV1,
    FailedProofReason,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    PartialAuditOutcome,
    PartialSoundAuditInvariantViolation,
    RewardWeightV1,
    TypedPartialSoundAuditResultV2,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
    canonical_lmb_n6_return_bound_proof_v1,
    verify_partial_fixed_plan_audit_from_observed_synthesis_v2,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)


def _plan(model, horizon: int) -> FrozenContingentAbstractPlanV1:
    active_cells = tuple(
        sorted(
            (
                cell
                for cell in model.cells
                if cell.planning_kind is PlanningKind.ACTIVE
            ),
            key=lambda cell: cell.cell_id,
        )
    )
    actions_by_cell = {cell.cell_id: [] for cell in active_cells}
    for action in model.semantic_actions:
        actions_by_cell[action.cell_id].append(action)
    assignments = tuple(
        sorted(
            ContingentPlanAssignmentV1(
                cell.cell_id,
                next(
                    (
                        action.semantic_action_id
                        for action in actions_by_cell[cell.cell_id]
                        if action.label_values == (False,)
                    ),
                    actions_by_cell[cell.cell_id][0].semantic_action_id,
                ),
            )
            for cell in active_cells
        )
    )
    return FrozenContingentAbstractPlanV1(
        model.model_id,
        horizon,
        tuple(
            ContingentPlanStageV1(time_index, assignments)
            for time_index in range(horizon)
        ),
    )


def _thresholds(model, state_id: str, horizon: int) -> FrozenPartialAuditThresholdsV1:
    return FrozenPartialAuditThresholdsV1(
        model.model_id,
        horizon,
        (InitialStateMassV1(state_id, Fraction(1)),),
        tuple(
            RewardWeightV1(item.name, Fraction(1))
            for item in model.reward_feature_caps
        ),
        Fraction(0),
        Fraction(0),
        canonical_lmb_n6_return_bound_proof_v1(),
    )


@pytest.fixture(scope="module")
def typed_audit_contract():
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    model = synthesis.partial_build_result.model
    initial_state_id = source["observed_by_ground"][source["initial"]].state_id
    missing_state_id = source["observed_by_ground"][source["extra"]].state_id
    return {
        **source,
        "synthesis": synthesis,
        "model": model,
        "initial_state_id": initial_state_id,
        "missing_state_id": missing_state_id,
    }


def test_typed_public_boundary_accepts_only_the_full_v0045_result() -> None:
    assert tuple(
        inspect.signature(
            audit_partial_fixed_plan_from_observed_synthesis_v2
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "contingent_plan",
    )
    assert tuple(
        inspect.signature(
            verify_partial_fixed_plan_audit_from_observed_synthesis_v2
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "contingent_plan",
        "claimed_result",
    )


def test_h3_typed_model_certifies_and_binds_the_complete_source_chain(
    typed_audit_contract,
) -> None:
    contract = typed_audit_contract
    synthesis = contract["synthesis"]
    thresholds = _thresholds(
        contract["model"], contract["initial_state_id"], 3
    )
    plan = _plan(contract["model"], 3)
    result = audit_partial_fixed_plan_from_observed_synthesis_v2(
        contract["log"],
        contract["profile"],
        contract["authority"],
        synthesis,
        thresholds,
        plan,
    )

    assert type(result) is TypedPartialSoundAuditResultV2
    assert result.observed_synthesis_result_id == synthesis.result_id
    assert (
        result.observed_synthesis_certificate_id
        == synthesis.certificate.certificate_id
    )
    assert result.coordinate_proposal_id == synthesis.coordinate_proposal.proposal_id
    assert result.partial_build_result_id == synthesis.partial_build_result.result_id
    assert result.partial_model_id == contract["model"].model_id
    assert result.audit_result.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert result.audit_result.robust_bounds.policy_reward_lower == 4
    assert result.audit_result.robust_bounds.policy_failure_upper == 0
    assert result.result_id == (
        "24f4c930b0349fd90fc636efc787f5f39115abaf8e2824ebcced68473b917a87"
    )
    assert result.audit_result.result_id == (
        "90a0125eae078656e10c5d51ee4a8e56386d1d8e455951be2f21db2dc0e6439b"
    )
    assert result.audit_result.certificate is not None
    assert result.audit_result.certificate.certificate_id == (
        "9e6750611397da8c2685480bc2de09e27fd79fe59c66009b0548cbd707de3ba0"
    )

    replayed = verify_partial_fixed_plan_audit_from_observed_synthesis_v2(
        contract["log"],
        contract["profile"],
        contract["authority"],
        synthesis,
        thresholds,
        plan,
        result,
    )
    assert replayed.to_document() == result.to_document()


def test_h1_all_missing_typed_cell_emits_nonauthorizing_frontier(
    typed_audit_contract,
) -> None:
    contract = typed_audit_contract
    thresholds = _thresholds(
        contract["model"], contract["missing_state_id"], 1
    )
    plan = _plan(contract["model"], 1)
    result = audit_partial_fixed_plan_from_observed_synthesis_v2(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        thresholds,
        plan,
    )

    inner = result.audit_result
    assert inner.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert inner.certificate is None
    assert inner.failed_proof_frontier is not None
    assert (
        inner.failed_proof_frontier.reason
        is FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    )
    assert inner.failed_proof_frontier.local_recovery_authorized is False
    assert inner.failed_proof_frontier.infeasibility_claimed is False
    assert inner.robust_bounds.policy_failure_upper == 1
    assert result.result_id == (
        "6bc6cb9242b8122e3482f2150dc410bc0eeccd22d659a4d0531be3d535c64295"
    )
    assert inner.result_id == (
        "07e12504e8b7c5edd3720fb1797975f6419b0851c94948be405bad9e5bd40b72"
    )
    assert inner.failed_proof_frontier.frontier_id == (
        "51abd3a3c470e7dce39d197c2a45072e990dae12dc571967df63c1d37cdfb5c3"
    )


def test_typed_verifier_rejects_a_self_consistent_wrapper_id_substitution(
    typed_audit_contract,
) -> None:
    contract = typed_audit_contract
    thresholds = _thresholds(
        contract["model"], contract["initial_state_id"], 3
    )
    plan = _plan(contract["model"], 3)
    result = audit_partial_fixed_plan_from_observed_synthesis_v2(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        thresholds,
        plan,
    )
    changed = replace(
        result,
        partial_build_result_id=("0" * 64),
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="differs from retained full-chain replay",
    ):
        verify_partial_fixed_plan_audit_from_observed_synthesis_v2(
            contract["log"],
            contract["profile"],
            contract["authority"],
            contract["synthesis"],
            thresholds,
            plan,
            changed,
        )


def test_typed_audit_rejects_a_bare_partial_build_result(
    typed_audit_contract,
) -> None:
    contract = typed_audit_contract
    thresholds = _thresholds(
        contract["model"], contract["initial_state_id"], 3
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="duck V0-045 synthesis results",
    ):
        audit_partial_fixed_plan_from_observed_synthesis_v2(
            contract["log"],
            contract["profile"],
            contract["authority"],
            contract["synthesis"].partial_build_result,  # type: ignore[arg-type]
            thresholds,
            _plan(contract["model"], 3),
        )
