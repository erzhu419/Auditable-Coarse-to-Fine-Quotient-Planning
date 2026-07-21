from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.observation_partial_rapm_v1 as partial_model_module
import acfqp.partial_sound_audit_v1 as audit_module
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    PlanningKind,
    RewardFeatureCapV1,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanAssignmentV1,
    ContingentPlanStageV1,
    FailedProofReason,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    RegisteredReturnBoundProofV1,
    canonical_lmb_n6_return_bound_proof_v1,
    PartialAuditOutcome,
    PartialFailedProofFrontierV1,
    PartialSoundAuditInvariantViolation,
    PartialSoundAuditResultV1,
    RewardWeightV1,
    audit_partial_fixed_plan_v1,
    verify_partial_fixed_plan_audit_v1,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _active_cells(model):
    return tuple(
        sorted(
            (
                item
                for item in model.cells
                if item.planning_kind is PlanningKind.ACTIVE
            ),
            key=lambda item: item.cell_id,
        )
    )


def _plan(model, horizon: int) -> FrozenContingentAbstractPlanV1:
    actions_by_cell = {item.cell_id: [] for item in _active_cells(model)}
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
                        if action.label_values == (True,)
                    ),
                    actions_by_cell[cell.cell_id][0].semantic_action_id,
                ),
            )
            for cell in _active_cells(model)
        )
    )
    return FrozenContingentAbstractPlanV1(
        model.model_id,
        horizon,
        tuple(ContingentPlanStageV1(index, assignments) for index in range(horizon)),
    )


def _thresholds(
    model,
    initial_state_id: str,
    *,
    horizon: int,
    normalized_regret_tolerance: Fraction = Fraction(0),
    risk_tolerance: Fraction = Fraction(0),
) -> FrozenPartialAuditThresholdsV1:
    return FrozenPartialAuditThresholdsV1(
        model.model_id,
        horizon,
        (InitialStateMassV1(initial_state_id, Fraction(1)),),
        tuple(
            RewardWeightV1(item.name, Fraction(1))
            for item in model.reward_feature_caps
        ),
        normalized_regret_tolerance,
        risk_tolerance,
        canonical_lmb_n6_return_bound_proof_v1(),
    )


def _run(contract, thresholds, plan):
    return audit_partial_fixed_plan_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        thresholds,
        plan,
    )


@pytest.fixture(scope="module")
def audit_contract():
    contract = observation_contract_fixture.__wrapped__()
    model = contract["result"].model
    initial_state_id = contract["observed_by_ground"][contract["initial"]].state_id
    initial_cell = next(
        item for item in model.cells if initial_state_id in item.member_state_ids
    )
    missing_state_id = contract["observed_by_ground"][contract["extra"]].state_id
    missing_cell = next(
        item for item in model.cells if missing_state_id in item.member_state_ids
    )
    positive_plan = _plan(model, 3)
    positive_thresholds = _thresholds(
        model, initial_state_id, horizon=3
    )
    positive_result = _run(contract, positive_thresholds, positive_plan)
    return {
        **contract,
        "model": model,
        "initial_cell": initial_cell,
        "initial_state_id": initial_state_id,
        "missing_cell": missing_cell,
        "missing_state_id": missing_state_id,
        "positive_plan": positive_plan,
        "positive_thresholds": positive_thresholds,
        "positive_result": positive_result,
    }


def test_observed_policy_path_certifies_exactly_and_ignores_unrelated_missing_rows(
    audit_contract,
) -> None:
    contract = audit_contract
    model = contract["model"]
    result = contract["positive_result"]
    bounds = result.robust_bounds

    assert model.coverage.missing_ground_row_ids
    assert result.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert result.certificate is not None
    assert result.failed_proof_frontier is None
    assert bounds.unrestricted_reward_upper == 4
    assert bounds.policy_reward_lower == bounds.policy_reward_upper == 4
    assert bounds.raw_distribution_regret == 0
    assert bounds.policy_failure_lower == bounds.policy_failure_upper == 0
    assert len(bounds.unrestricted_rows) == 33
    assert all(
        row.reward_lower == row.reward_upper
        and row.failure_lower == row.failure_upper
        for row in bounds.rows
        if (row.time_index, row.cell_id)
        in {
            (item.time_index, item.cell_id) for item in result.proof_obligations
        }
    )
    missing_cell_id = contract["missing_cell"].cell_id
    assert all(item.cell_id != missing_cell_id for item in result.proof_obligations)
    assert result.external_transition_authority_calls == 0
    assert result.ground_search_calls == 0
    assert result.optimality_claimed is False
    assert result.infeasibility_claimed is False

    replayed = verify_partial_fixed_plan_audit_v1(
        contract["log"],
        contract["proposal"],
        contract["profile"],
        contract["authority"],
        contract["result"],
        contract["positive_thresholds"],
        contract["positive_plan"],
        result,
    )
    assert replayed.to_document() == result.to_document()


def test_registered_missing_policy_path_emits_earliest_frontier_not_infeasible(
    audit_contract,
) -> None:
    contract = audit_contract
    model = contract["model"]
    plan = _plan(model, 1)
    thresholds = _thresholds(
        model, contract["missing_state_id"], horizon=1
    )
    result = _run(contract, thresholds, plan)

    assert result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert result.certificate is None
    frontier = result.failed_proof_frontier
    assert frontier is not None
    assert frontier.earliest_time_index == 0
    assert frontier.remaining_horizon == 1
    assert frontier.reason is FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    assert frontier.unresolved_exposure_sum == 1
    assert frontier.infeasibility_claimed is False
    assert result.infeasibility_claimed is False
    assert result.robust_bounds.policy_failure_upper == 1
    assert result.robust_bounds.policy_reward_lower == 0
    assert result.robust_bounds.unrestricted_reward_upper == 3
    assert result.robust_bounds.external_coverage_certified is True
    assert result.robust_bounds.external_escape_obligation_ids == ()
    assert all(item.shared_unknown_mass == 1 for item in frontier.obligations)
    assert all(item.missing_ground_row_ids for item in frontier.obligations)


def _modified_row_deletion(contract):
    model = contract["model"]
    plan = contract["positive_plan"]
    selected_pairs = {
        (assignment.cell_id, assignment.semantic_action_id)
        for stage in plan.stages
        for assignment in stage.assignments
    }
    ground_row_by_id = {item.ground_row_id: item for item in model.ground_rows}
    realization = next(
        item
        for item in sorted(
            model.semantic_realizations,
            key=lambda candidate: (candidate.state_id, candidate.semantic_action_id),
        )
        if (item.cell_id, item.semantic_action_id) in selected_pairs
        and len(item.support_ground_row_ids) > 1
        and all(
            ground_row_by_id[row_id].status
            is AmbiguityRowStatus.OBSERVED_SINGLETON
            for row_id in item.support_ground_row_ids
        )
    )
    deleted_row_id = realization.support_ground_row_ids[0]
    vacuous = partial_model_module._ambiguity_payload(
        known_reward={},
        known_successor={},
        known_failure=Fraction(0),
        known_terminal=Fraction(0),
        unknown_mass=Fraction(1),
        destinations=realization.ambiguity.unknown_successor_destination_ids,
        external_boundary_id=realization.ambiguity.external_boundary_id,
        caps=model.reward_feature_caps,
    )
    changed_ground_rows = tuple(
        sorted(
            (
                replace(
                    item,
                    status=AmbiguityRowStatus.MISSING_VACUOUS,
                    observation_ids=(),
                    ambiguity=vacuous,
                )
                if item.ground_row_id == deleted_row_id
                else item
                for item in model.ground_rows
            ),
            key=lambda item: item.ground_row_id,
        )
    )
    changed_ground_row_by_action = {
        item.ground_action_id: item for item in changed_ground_rows
    }
    concretizer = next(
        item
        for item in model.concretizer_rows
        if item.state_id == realization.state_id
        and item.semantic_action_id == realization.semantic_action_id
    )
    known_reward: dict[str, Fraction] = {}
    known_successor: dict[str, Fraction] = {}
    known_failure = Fraction(0)
    known_terminal = Fraction(0)
    unknown_mass = Fraction(0)
    observed_row_ids: list[str] = []
    missing_row_ids: list[str] = []
    for ground_action_id, weight in concretizer.support:
        row = changed_ground_row_by_action[ground_action_id]
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS:
            missing_row_ids.append(row.ground_row_id)
            unknown_mass += weight
            continue
        observed_row_ids.append(row.ground_row_id)
        for name, value in row.ambiguity.known_reward_features:
            known_reward[name] = known_reward.get(name, Fraction(0)) + weight * value
        for destination_id, mass in row.ambiguity.known_successor_masses:
            known_successor[destination_id] = (
                known_successor.get(destination_id, Fraction(0)) + weight * mass
            )
        known_failure += weight * row.ambiguity.known_failure_mass
        known_terminal += weight * row.ambiguity.known_terminal_mass
    aggregate_ambiguity = partial_model_module._ambiguity_payload(
        known_reward=known_reward,
        known_successor=known_successor,
        known_failure=known_failure,
        known_terminal=known_terminal,
        unknown_mass=unknown_mass,
        destinations=realization.ambiguity.unknown_successor_destination_ids,
        external_boundary_id=realization.ambiguity.external_boundary_id,
        caps=model.reward_feature_caps,
    )
    changed_realizations = tuple(
        sorted(
            (
                replace(
                    item,
                    observed_ground_row_ids=tuple(sorted(observed_row_ids)),
                    missing_ground_row_ids=tuple(sorted(missing_row_ids)),
                    ambiguity=aggregate_ambiguity,
                )
                if item.state_id == realization.state_id
                and item.semantic_action_id == realization.semantic_action_id
                else item
                for item in model.semantic_realizations
            ),
            key=lambda item: (item.state_id, item.semantic_action_id),
        )
    )
    changed_coverage = replace(
        model.coverage,
        observed_ground_row_ids=tuple(
            item
            for item in model.coverage.observed_ground_row_ids
            if item != deleted_row_id
        ),
        missing_ground_row_ids=tuple(
            sorted((*model.coverage.missing_ground_row_ids, deleted_row_id))
        ),
    )
    changed_model = replace(
        model,
        coverage=changed_coverage,
        ground_rows=changed_ground_rows,
        semantic_realizations=changed_realizations,
    )
    return replace(
        contract["result"],
        model=changed_model,
        observed_ground_row_count=contract["result"].observed_ground_row_count - 1,
        missing_ground_row_count=contract["result"].missing_ground_row_count + 1,
    )


def test_modified_policy_row_is_rejected_before_planning(
    audit_contract,
) -> None:
    modified_build = _modified_row_deletion(audit_contract)
    modified_model = modified_build.model
    plan = _plan(modified_model, 3)
    thresholds = _thresholds(
        modified_model, audit_contract["initial_state_id"], horizon=3
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="source graph failed trusted reconstruction",
    ):
        audit_partial_fixed_plan_v1(
            audit_contract["log"],
            audit_contract["proposal"],
            audit_contract["profile"],
            audit_contract["authority"],
            modified_build,
            thresholds,
            plan,
        )


def test_bounds_frontier_and_zero_unknown_content_consistency_negative_regressions(
    audit_contract,
) -> None:
    contract = audit_contract
    positive = contract["positive_result"]
    original_upper_row = positive.robust_bounds.unrestricted_rows[0]
    modified_upper_row = replace(
        original_upper_row,
        reward_upper=original_upper_row.reward_upper + 1,
    )
    modified_upper_rows = (
        modified_upper_row,
        *positive.robust_bounds.unrestricted_rows[1:],
    )
    modified_bounds = replace(
        positive.robust_bounds,
        unrestricted_rows=modified_upper_rows,
    )
    modified_certificate = replace(
        positive.certificate,
        bounds_id=modified_bounds.bounds_id,
    )
    altered_result = replace(
        positive,
        robust_bounds=modified_bounds,
        certificate=modified_certificate,
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="trusted exact replay"
    ):
        verify_partial_fixed_plan_audit_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
            contract["positive_thresholds"],
            contract["positive_plan"],
            altered_result,
        )

    missing_plan = _plan(contract["model"], 1)
    missing_thresholds = _thresholds(
        contract["model"], contract["missing_state_id"], horizon=1
    )
    failed = _run(contract, missing_thresholds, missing_plan)
    original = failed.failed_proof_frontier.obligations[0]
    modified_obligation = replace(
        original,
        observed_ground_row_ids=original.support_ground_row_ids,
        missing_ground_row_ids=(),
        shared_unknown_mass=Fraction(0),
        reachable_unknown_mass_upper=Fraction(0),
        realization_singleton=True,
    )
    modified_frontier = PartialFailedProofFrontierV1(
        failed.partial_model_id,
        failed.thresholds_id,
        failed.contingent_plan_id,
        failed.robust_bounds.bounds_id,
        0,
        1,
        (modified_obligation,),
        Fraction(0),
        True,
        True,
        False,
        FailedProofReason.KNOWN_FIXED_PLAN_THRESHOLD_FAILURE,
    )
    altered_failed = replace(
        failed,
        proof_obligations=(modified_obligation,),
        failed_proof_frontier=modified_frontier,
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="trusted exact replay"
    ):
        verify_partial_fixed_plan_audit_v1(
            contract["log"],
            contract["proposal"],
            contract["profile"],
            contract["authority"],
            contract["result"],
            missing_thresholds,
            missing_plan,
            altered_failed,
        )


def test_joint_simplex_unknown_is_charged_once_and_failure_is_terminal() -> None:
    destination_a = _hash("joint-destination-a")
    destination_b = _hash("joint-destination-b")
    external = _hash("joint-external")
    destinations = tuple(sorted((destination_a, destination_b, external)))
    caps = (RewardFeatureCapV1("reward", Fraction(0), Fraction(0)),)
    ambiguity = partial_model_module._ambiguity_payload(
        known_reward={},
        known_successor={destination_a: Fraction(1, 2)},
        known_failure=Fraction(0),
        known_terminal=Fraction(0),
        unknown_mass=Fraction(1, 2),
        destinations=destinations,
        external_boundary_id=external,
        caps=caps,
    )
    next_bounds = {
        destination_a: audit_module._Bound(10, 10, 0, 0),
        destination_b: audit_module._Bound(20, 20, 0, 0),
    }
    bound = audit_module._realization_bound(
        ambiguity,
        next_bounds,
        (destination_a, destination_b),
        external,
        audit_module._Bound(0, 0, 0, 0),
        {"reward": Fraction(1)},
        Fraction(100),
    )
    assert bound.reward_lower == 5
    assert bound.reward_upper == 15
    assert bound.failure_lower == 0
    assert bound.failure_upper == Fraction(1, 2)

    failure_half = partial_model_module._ambiguity_payload(
        known_reward={},
        known_successor={},
        known_failure=Fraction(1, 2),
        known_terminal=Fraction(1, 2),
        unknown_mass=Fraction(1, 2),
        destinations=destinations,
        external_boundary_id=external,
        caps=caps,
    )
    failure_bound = audit_module._realization_bound(
        failure_half,
        next_bounds,
        (destination_a, destination_b),
        external,
        audit_module._Bound(0, 0, 0, 0),
        {"reward": Fraction(1)},
        Fraction(100),
    )
    assert failure_bound.failure_lower == Fraction(1, 2)
    assert failure_bound.failure_upper == 1


def test_source_api_is_kernel_query_and_ground_solver_blind(audit_contract) -> None:
    audit_signature = inspect.signature(audit_partial_fixed_plan_v1)
    assert tuple(audit_signature.parameters) == (
        "observation_log",
        "coordinate_proposal",
        "semantics_profile",
        "observation_authority",
        "partial_build_result",
        "thresholds",
        "contingent_plan",
    )
    verifier_signature = inspect.signature(verify_partial_fixed_plan_audit_v1)
    assert tuple(verifier_signature.parameters) == (
        "observation_log",
        "coordinate_proposal",
        "semantics_profile",
        "observation_authority",
        "partial_build_result",
        "thresholds",
        "contingent_plan",
        "claimed_result",
    )
    imports = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(audit_module)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "fractions",
        "typing",
        "acfqp.observation_partial_rapm_v1",
        "acfqp.phase3e_ids",
    }
    assert not any(module.startswith("acfqp.domains") for module in imports)
    assert not any(module.startswith("acfqp.planning") for module in imports)

    assert "kernel" not in audit_contract
    replayed = _run(
        audit_contract,
        audit_contract["positive_thresholds"],
        audit_contract["positive_plan"],
    )
    assert replayed.result_id == audit_contract["positive_result"].result_id
    with pytest.raises(TypeError):
        audit_partial_fixed_plan_v1(
            audit_contract["log"],
            audit_contract["proposal"],
            audit_contract["profile"],
            audit_contract["authority"],
            audit_contract["result"],
            audit_contract["positive_thresholds"],
            audit_contract["positive_plan"],
            query={"leak": True},  # type: ignore[call-arg]
        )


def test_strict_types_horizon_plan_chain_and_content_ids(audit_contract) -> None:
    model = audit_contract["model"]
    with pytest.raises(PartialSoundAuditInvariantViolation, match="contiguous"):
        FrozenContingentAbstractPlanV1(
            model.model_id,
            2,
            (
                audit_contract["positive_plan"].stages[0],
                replace(audit_contract["positive_plan"].stages[1], time_index=2),
            ),
        )
    long_plan = _plan(model, model.semantics_horizon_cap + 1)
    long_thresholds = _thresholds(
        model,
        audit_contract["initial_state_id"],
        horizon=model.semantics_horizon_cap + 1,
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="horizon-scope mismatch"
    ):
        _run(audit_contract, long_thresholds, long_plan)
    modified_plan = replace(
        audit_contract["positive_plan"], partial_model_id=_hash("foreign-model")
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="identity or horizon-scope"
    ):
        _run(audit_contract, audit_contract["positive_thresholds"], modified_plan)
    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="duck result"
    ):
        verify_partial_fixed_plan_audit_v1(
            audit_contract["log"],
            audit_contract["proposal"],
            audit_contract["profile"],
            audit_contract["authority"],
            audit_contract["result"],
            audit_contract["positive_thresholds"],
            audit_contract["positive_plan"],
            object(),  # type: ignore[arg-type]
        )
    result = audit_contract["positive_result"]
    assert len(result.result_id) == 64
    assert len(result.robust_bounds.bounds_id) == 64
    assert len(result.certificate.certificate_id) == 64
    assert result.to_document() == _run(
        audit_contract,
        audit_contract["positive_thresholds"],
        audit_contract["positive_plan"],
    ).to_document()


def _mixed_thresholds(
    contract,
    *,
    horizon: int,
    normalized_regret_tolerance: Fraction = Fraction(1, 20),
    risk_tolerance: Fraction = Fraction(1, 20),
) -> FrozenPartialAuditThresholdsV1:
    return FrozenPartialAuditThresholdsV1(
        contract["model"].model_id,
        horizon,
        tuple(
            sorted(
                (
                    InitialStateMassV1(
                        contract["initial_state_id"], Fraction(99, 100)
                    ),
                    InitialStateMassV1(
                        contract["missing_state_id"], Fraction(1, 100)
                    ),
                )
            )
        ),
        (
            RewardWeightV1("match", Fraction(1)),
            RewardWeightV1("terminal_clear", Fraction(1)),
        ),
        normalized_regret_tolerance,
        risk_tolerance,
        canonical_lmb_n6_return_bound_proof_v1(),
    )


def _nonmatching_plan(model, horizon: int) -> FrozenContingentAbstractPlanV1:
    actions_by_cell = {item.cell_id: [] for item in _active_cells(model)}
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
            for cell in _active_cells(model)
        )
    )
    return FrozenContingentAbstractPlanV1(
        model.model_id,
        horizon,
        tuple(ContingentPlanStageV1(index, assignments) for index in range(horizon)),
    )


def test_registered_return_scale_and_exact_state_support_are_mandatory(
    audit_contract,
) -> None:
    contract = audit_contract
    proof = canonical_lmb_n6_return_bound_proof_v1()
    assert (
        proof.proof_id
        == "6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98"
    )
    bounds = contract["positive_result"].robust_bounds

    assert proof.return_upper == 4
    assert contract["positive_thresholds"].goal_id == "default"
    assert contract["positive_thresholds"].to_document()["goal_id"] == "default"
    assert proof.proof_id == bounds.return_bound_proof_id
    assert bounds.return_upper == 4
    assert bounds.raw_distribution_regret == 0
    assert bounds.normalized_distribution_regret == 0
    assert bounds.maximum_support_point_normalized_regret == 0
    assert len(bounds.support_point_regret_rows) == 1
    assert bounds.support_point_regret_rows[0].state_id == contract["initial_state_id"]
    assert contract["positive_result"].certificate.return_bound_proof_id == proof.proof_id

    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="goal_id=default",
    ):
        replace(contract["positive_thresholds"], goal_id="foreign")

    class DuckGoal:
        def __str__(self) -> str:
            return "default"

    for invalid_goal in (1, DuckGoal()):
        with pytest.raises(
            PartialSoundAuditInvariantViolation,
            match="goal_id=default",
        ):
            replace(contract["positive_thresholds"], goal_id=invalid_goal)

    cell_as_state = _thresholds(
        contract["model"], contract["initial_cell"].cell_id, horizon=1
    )
    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="non-active or unknown ground state",
    ):
        _run(contract, cell_as_state, _plan(contract["model"], 1))


def test_support_rows_must_match_enclosing_return_scale_and_tolerance(
    audit_contract,
) -> None:
    bounds = audit_contract["positive_result"].robust_bounds
    support_row = bounds.support_point_regret_rows[0]

    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="enclosing scale/tolerance",
    ):
        replace(
            bounds,
            support_point_regret_rows=(
                replace(support_row, return_upper=Fraction(5)),
            ),
        )

    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="enclosing scale/tolerance",
    ):
        replace(
            bounds,
            support_point_regret_rows=(
                replace(
                    support_row,
                    normalized_regret_tolerance=Fraction(1, 20),
                ),
            ),
        )


def test_return_scale_weight_and_threshold_registry_negative_regressions(
    audit_contract,
) -> None:
    contract = audit_contract
    proof = canonical_lmb_n6_return_bound_proof_v1()
    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="canonical nonnegative LMB N=6 bound",
    ):
        replace(proof, return_upper=Fraction(5))

    unregistered = replace(proof, structural_id=_hash("other-structural-contract"))
    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="matching registered return-bound proof",
    ):
        FrozenPartialAuditThresholdsV1(
            contract["model"].model_id,
            1,
            (InitialStateMassV1(contract["initial_state_id"], Fraction(1)),),
            proof.reward_weights,
            Fraction(0),
            Fraction(0),
            unregistered,
        )

    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="matching registered return-bound proof",
    ):
        FrozenPartialAuditThresholdsV1(
            contract["model"].model_id,
            1,
            (InitialStateMassV1(contract["initial_state_id"], Fraction(1)),),
            (
                RewardWeightV1("match", Fraction(-1)),
                RewardWeightV1("terminal_clear", Fraction(1)),
            ),
            Fraction(0),
            Fraction(0),
            proof,
        )

    with pytest.raises(
        PartialSoundAuditInvariantViolation,
        match="V0 registry",
    ):
        FrozenPartialAuditThresholdsV1(
            contract["model"].model_id,
            1,
            (InitialStateMassV1(contract["initial_state_id"], Fraction(1)),),
            proof.reward_weights,
            Fraction(1, 2),
            Fraction(0),
            proof,
        )


def test_low_mass_bad_support_cannot_be_hidden_by_distribution_averaging(
    audit_contract,
) -> None:
    contract = audit_contract
    thresholds = _mixed_thresholds(contract, horizon=1)
    result = _run(contract, thresholds, _plan(contract["model"], 1))
    bounds = result.robust_bounds

    assert result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert bounds.raw_distribution_regret == Fraction(3, 100)
    assert bounds.normalized_distribution_regret == Fraction(3, 400)
    assert bounds.normalized_distribution_regret < Fraction(1, 20)
    assert bounds.policy_failure_upper == Fraction(1, 100)
    assert bounds.risk_obligation_certified is True
    assert bounds.maximum_support_point_normalized_regret == Fraction(3, 4)
    assert bounds.reward_obligation_certified is False
    bad = next(
        item
        for item in bounds.support_point_regret_rows
        if item.state_id == contract["missing_state_id"]
    )
    assert bad.initial_probability == Fraction(1, 100)
    assert bad.raw_regret_upper == 3
    assert bad.normalized_regret_upper == Fraction(3, 4)
    assert bad.obligation_certified is False
    assert result.failed_hint_authorizes_local_recovery is False
    assert result.failed_proof_frontier.local_recovery_authorized is False


def test_reachable_external_escape_blocks_certificate_and_never_authorizes_local(
    audit_contract,
) -> None:
    contract = audit_contract
    thresholds = _mixed_thresholds(contract, horizon=2)
    result = _run(contract, thresholds, _plan(contract["model"], 2))
    bounds = result.robust_bounds

    assert bounds.normalized_distribution_regret == Fraction(1, 100)
    assert bounds.policy_failure_upper == Fraction(1, 100)
    assert bounds.risk_obligation_certified is True
    assert bounds.external_coverage_certified is False
    assert bounds.external_escape_obligation_ids
    assert all(row.reward_upper <= 4 for row in bounds.unrestricted_rows)
    assert result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert (
        result.failed_proof_frontier.reason
        is FailedProofReason.EXTERNAL_COVERAGE_ESCAPE
    )
    assert result.failed_proof_frontier.external_coverage_failed is True
    assert result.failed_proof_frontier.local_recovery_authorized is False
    assert result.failed_proof_frontier.causal_necessity_claimed is False
    assert result.failed_proof_frontier.causal_sufficiency_claimed is False


def test_selected_singleton_with_unselected_missing_rows_is_only_a_hint(
    audit_contract,
) -> None:
    contract = audit_contract
    result = _run(
        contract,
        _thresholds(contract["model"], contract["initial_state_id"], horizon=3),
        _nonmatching_plan(contract["model"], 3),
    )

    assert contract["model"].coverage.missing_ground_row_ids
    assert all(not item.missing_ground_row_ids for item in result.proof_obligations)
    assert result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert (
        result.failed_proof_frontier.reason
        is FailedProofReason.KNOWN_FIXED_PLAN_THRESHOLD_FAILURE
    )
    assert result.failed_proof_frontier.local_recovery_authorized is False
    assert result.failed_hint_authorizes_local_recovery is False
    assert result.causal_necessity_claimed is False
    assert result.causal_sufficiency_claimed is False


def test_mutable_and_side_effect_nested_inputs_fail_before_iteration(
    audit_contract,
) -> None:
    touched: list[str] = []

    class SideEffectIterable:
        def __iter__(self):
            touched.append("iterated")
            yield _hash("side-effect-id")

    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="exact tuple"
    ):
        audit_module._sorted_ids(SideEffectIterable(), "negative regression")
    assert touched == []

    mutable_assignments = list(audit_contract["positive_plan"].stages[0].assignments)
    with pytest.raises(
        PartialSoundAuditInvariantViolation, match="duck assignments"
    ):
        ContingentPlanStageV1(0, mutable_assignments)  # type: ignore[arg-type]
    mutable_assignments.append(mutable_assignments[0])
    assert len(mutable_assignments) > 1
