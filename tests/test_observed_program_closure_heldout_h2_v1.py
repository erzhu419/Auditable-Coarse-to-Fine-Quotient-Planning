from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.observed_program_closure_synthesis_v1 as closure_module
import acfqp.observed_program_closure_heldout_h2_v1 as heldout_module
from acfqp.observation_partial_rapm_v1 import AmbiguityRowStatus
from acfqp.partial_sound_audit_v1 import (
    FailedProofReason,
    PartialAuditOutcome,
)
from acfqp.query_local_refinement_v1 import canonical_lmb_query_kernel_v1
from acfqp.observed_program_closure_heldout_h2_v1 import (
    ProgramClosureHeldOutH2InvariantViolation,
    SOURCE_SUCCESSOR_GROUND_STATE,
    TARGET_GROUND_STATE,
    preregister_lmb_program_closure_heldout_h2_v1,
    run_lmb_program_closure_heldout_h2_v1,
    verify_lmb_program_closure_heldout_h2_v1,
)
from acfqp.observed_program_closure_synthesis_v1 import (
    ACTION_COORDINATE_REPRESENTATIVE_COUNT,
    REQUIRED_ADMISSIBLE_CANDIDATE_COUNT,
    REQUIRED_CANDIDATE_COUNT,
    REQUIRED_SELECTED_CANDIDATE_INDEX,
    SEMANTIC_REPRESENTATIVE_COUNT,
    STATE_COORDINATE_REPRESENTATIVE_COUNT,
    ObservedProgramClosureInvariantViolation,
    synthesize_observed_lmb_program_closure_cap_control_v1,
    synthesize_observed_lmb_program_closure_partial_rapm_v1,
    verify_observed_lmb_program_closure_partial_rapm_v1,
)

import test_observation_partial_rapm_v1 as observation_fixture_module


@pytest.fixture(scope="module")
def closure_contract():
    source = observation_fixture_module.observation_contract.__wrapped__()
    result = synthesize_observed_lmb_program_closure_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    return {**source, "closure": result}


@pytest.fixture(scope="module")
def heldout_contract(closure_contract):
    preregistration = preregister_lmb_program_closure_heldout_h2_v1(
        closure_contract["log"],
        closure_contract["profile"],
        closure_contract["authority"],
    )
    kernel = canonical_lmb_query_kernel_v1()
    result = run_lmb_program_closure_heldout_h2_v1(
        closure_contract["log"],
        closure_contract["profile"],
        closure_contract["authority"],
        preregistration,
        closure_contract["closure"],
        kernel,
    )
    return {
        **closure_contract,
        "preregistration": preregistration,
        "kernel": kernel,
        "heldout": result,
    }


def test_program_closure_public_api_has_no_target_or_candidate_control(
    closure_contract,
) -> None:
    assert tuple(
        inspect.signature(
            synthesize_observed_lmb_program_closure_partial_rapm_v1
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
    )
    assert tuple(
        inspect.signature(
            verify_observed_lmb_program_closure_partial_rapm_v1
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "claimed_result",
    )
    with pytest.raises(TypeError):
        synthesize_observed_lmb_program_closure_partial_rapm_v1(
            closure_contract["log"],
            closure_contract["profile"],
            closure_contract["authority"],
            query={"forbidden": True},  # type: ignore[call-arg]
        )
    source = inspect.getsource(closure_module)
    assert "LMBKernel" not in source
    assert "QuerySpec" not in tuple(
        inspect.signature(
            synthesize_observed_lmb_program_closure_partial_rapm_v1
        ).parameters
    )


def test_bottom_up_closure_is_complete_and_semantically_deduplicated(
    closure_contract,
) -> None:
    registry = closure_contract["closure"].program_registry
    assert tuple(
        (
            item.raw_syntactic_expression_count,
            item.new_semantic_signature_count,
            item.cumulative_semantic_representative_count,
        )
        for item in registry.depth_summaries
    ) == (
        (8, 8, 8),
        (41, 13, 21),
        (429, 194, 215),
    )
    assert len(registry.semantic_representatives) == SEMANTIC_REPRESENTATIVE_COUNT
    assert (
        len(registry.state_coordinate_expression_ids)
        == STATE_COORDINATE_REPRESENTATIVE_COUNT
        == 174
    )
    assert (
        len(registry.action_coordinate_expression_ids)
        == ACTION_COORDINATE_REPRESENTATIVE_COUNT
        == 37
    )
    assert len(
        {item.semantic_signature_id for item in registry.semantic_representatives}
    ) == len(registry.semantic_representatives)
    assert all(item.expression.depth <= 2 for item in registry.semantic_representatives)


def test_semantic_dedup_keeps_boolean_and_integer_types_distinct(
    closure_contract,
) -> None:
    representatives = closure_contract["closure"].program_registry.semantic_representatives
    constant_one = next(
        item
        for item in representatives
        if item.expression.operation == "integer_literal"
        and item.expression.literal == 1
    )
    constant_true = next(
        item
        for item in representatives
        if item.expression.operation == "equals"
        and item.expression.context.value == "STATE"
        and item.expression.result_type.value == "BOOLEAN"
        and item.expression.expression_id
        in closure_contract["closure"].program_registry.state_coordinate_expression_ids
        and all(
            row.values[
                closure_contract["closure"].value_table.state_expression_ids.index(
                    item.expression.expression_id
                )
            ]
            == 1
            for row in closure_contract["closure"].value_table.state_rows
        )
    )
    assert constant_one.expression.result_type.value == "INTEGER"
    assert constant_true.expression.result_type.value == "BOOLEAN"
    assert constant_one.semantic_signature_id != constant_true.semantic_signature_id


def test_all_bounded_shape_candidates_are_audited_before_selection(
    closure_contract,
) -> None:
    trace = closure_contract["closure"].candidate_trace
    assert REQUIRED_CANDIDATE_COUNT == (174 + 1) * (37 + 1) == 6650
    assert trace.required_candidate_count == REQUIRED_CANDIDATE_COUNT
    assert trace.evaluated_candidate_count == REQUIRED_CANDIDATE_COUNT
    assert len(trace.candidates) == REQUIRED_CANDIDATE_COUNT
    assert tuple(item.candidate_index for item in trace.candidates) == tuple(
        range(1, REQUIRED_CANDIDATE_COUNT + 1)
    )
    assert (
        trace.admissible_candidate_count
        == REQUIRED_ADMISSIBLE_CANDIDATE_COUNT
        == 1384
    )
    assert trace.candidates[0].state_expression_id is None
    assert trace.candidates[0].action_expression_id is None
    assert not trace.candidates[0].admissible


def test_selected_programs_are_generated_and_reproduce_partial_model(
    closure_contract,
) -> None:
    result = closure_contract["closure"]
    selected = result.selected_candidate
    expression_by_id = {
        item.expression.expression_id: item.expression
        for item in result.program_registry.semantic_representatives
    }
    state = expression_by_id[selected.state_expression_id]
    action = expression_by_id[selected.action_expression_id]
    assert selected.candidate_index == REQUIRED_SELECTED_CANDIDATE_INDEX == 4013
    assert state.operation == "cardinality"
    assert state.arguments[0].operation == "legal_actions"
    assert action.operation == "buffer_at_type"
    assert tuple(item.operation for item in action.arguments) == (
        "buffer_counts",
        "selected_tile_type",
    )
    assert len(result.coordinate_proposal.action_atoms) == 1
    assert result.coordinate_proposal.action_atoms[0].threshold == Fraction(3, 2)
    assert (
        selected.point_identified_registered_rows,
        selected.observed_equal_alias_pair_count,
        selected.partial_unknown_registered_rows,
        selected.abstract_entry_count,
        selected.active_cell_count,
        selected.total_cell_count,
        selected.separated_null_conflict_pair_count,
        selected.nontrivial_point_entry_count,
        selected.availability_violation_count,
        selected.contradiction_entry_count,
    ) == (7, 3, 0, 5, 4, 6, 18, 3, 0, 0)

    model = result.partial_build_result.model
    assert len(model.coverage.registered_ground_row_ids) == 11
    assert len(model.coverage.observed_ground_row_ids) == 7
    assert len(model.coverage.missing_ground_row_ids) == 4
    assert sum(
        row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
        for row in model.ground_rows
    ) == 7
    assert sum(
        row.status is AmbiguityRowStatus.MISSING_VACUOUS
        for row in model.ground_rows
    ) == 4
    assert all(
        row.ambiguity.unknown_mass == 1
        for row in model.ground_rows
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    )


def test_certificate_claims_only_composition_inside_frozen_vocabulary(
    closure_contract,
) -> None:
    certificate = closure_contract["closure"].certificate
    assert certificate.automatic_compositional_program_generation_claimed
    assert certificate.frozen_human_primitive_operator_vocabulary
    assert not certificate.primitive_invention_claimed
    assert not certificate.operator_invention_claimed
    assert not certificate.raw_symbolization_claimed
    assert not certificate.learned_dynamics_claimed
    assert not certificate.statistical_generalization_claimed
    assert not certificate.held_out_generalization_claimed
    assert not certificate.exact_quotient_claimed
    assert not certificate.plan_certificate_claimed
    assert not certificate.sample_efficiency_claimed


def test_cap_control_stops_before_any_candidate_and_cannot_publish_model(
    closure_contract,
) -> None:
    control = synthesize_observed_lmb_program_closure_cap_control_v1(
        closure_contract["log"],
        closure_contract["profile"],
        closure_contract["authority"],
        candidate_cap=6649,
    )
    assert control.status == "CANDIDATE_CAP_EXHAUSTED"
    assert control.required_candidate_count == 6650
    assert control.evaluated_candidate_count == 0
    assert control.model_id is None
    assert control.certificate_id is None
    assert not control.production_certificate_published


def test_full_retained_replay_is_deterministic(closure_contract) -> None:
    result = closure_contract["closure"]
    assert (
        verify_observed_lmb_program_closure_partial_rapm_v1(
            closure_contract["log"],
            closure_contract["profile"],
            closure_contract["authority"],
            result,
        )
        == ()
    )
    replay = synthesize_observed_lmb_program_closure_partial_rapm_v1(
        closure_contract["log"],
        closure_contract["profile"],
        closure_contract["authority"],
    )
    assert replay.to_document() == result.to_document()
    assert replay.result_id == result.result_id


def test_runtime_implementation_change_and_overclaim_fail_closed(
    closure_contract, monkeypatch
) -> None:
    original = closure_module._base_programs

    def changed_base_programs():
        return original()

    monkeypatch.setattr(closure_module, "_base_programs", changed_base_programs)
    with pytest.raises(
        ObservedProgramClosureInvariantViolation,
        match="runtime program closure implementation differs",
    ):
        synthesize_observed_lmb_program_closure_partial_rapm_v1(
            closure_contract["log"],
            closure_contract["profile"],
            closure_contract["authority"],
        )
    with pytest.raises(ObservedProgramClosureInvariantViolation):
        replace(
            closure_contract["closure"].certificate,
            learned_dynamics_claimed=True,
        )


def test_heldout_public_api_freezes_query_before_synthesis_and_target_access(
    heldout_contract,
) -> None:
    assert tuple(
        inspect.signature(
            preregister_lmb_program_closure_heldout_h2_v1
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
    )
    assert tuple(
        inspect.signature(run_lmb_program_closure_heldout_h2_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "preregistration",
        "synthesis_result",
        "kernel",
    )
    preregistration = heldout_contract["preregistration"]
    assert preregistration.registered_before_synthesis
    assert preregistration.kernel_input_count == 0
    assert preregistration.query.horizon == 2
    assert preregistration.query.target_state.state_id not in set(
        preregistration.source_state_ids
    )
    assert (
        set(preregistration.source_ground_row_ids)
        & set(heldout_contract["heldout"].initial_epoch.target_ground_row_ids)
        == set()
    )


def test_initial_epoch_keeps_all_target_rows_vacuous_until_proof_failure(
    heldout_contract,
) -> None:
    result = heldout_contract["heldout"]
    epoch = result.initial_epoch
    audit = result.initial_selected_audit.audit_result
    assert (
        epoch.observed_ground_row_count,
        epoch.missing_ground_row_count,
        epoch.exact_transition_query_count,
    ) == (7, 7, 0)
    assert set(epoch.target_ground_row_ids) <= set(
        epoch.planning_view.coverage.missing_ground_row_ids
    )
    assert audit.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert audit.failed_proof_frontier is not None
    assert (
        audit.failed_proof_frontier.reason
        is FailedProofReason.EXTERNAL_COVERAGE_ESCAPE
    )
    bounds = audit.robust_bounds
    assert (
        bounds.policy_reward_lower,
        bounds.policy_reward_upper,
        bounds.policy_failure_lower,
        bounds.policy_failure_upper,
        bounds.unrestricted_reward_upper,
        bounds.normalized_distribution_regret,
        bounds.external_coverage_certified,
    ) == (
        Fraction(0),
        Fraction(4),
        Fraction(0),
        Fraction(1),
        Fraction(4),
        Fraction(1),
        False,
    )


def test_failed_certificate_authorizes_exactly_the_three_target_rows(
    heldout_contract,
) -> None:
    result = heldout_contract["heldout"]
    authorization = result.authorization
    assert (
        authorization.selected_plan_risk_row_count,
        authorization.unrestricted_value_challenger_row_count,
        authorization.distinct_requested_row_count,
    ) == (1, 3, 3)
    assert authorization.requested_ground_row_ids == tuple(
        sorted(result.initial_epoch.target_ground_row_ids)
    )
    assert sum(
        item.selected_plan_risk_support
        for item in authorization.row_causes
    ) == 1
    assert all(
        item.unrestricted_value_challenger
        for item in authorization.row_causes
    )
    assert authorization.request_preparation_kernel_calls == 0
    assert not authorization.global_minimum_claimed


def test_exact_target_rows_are_single_use_and_do_not_expand_successors(
    heldout_contract,
) -> None:
    result = heldout_contract["heldout"]
    bundle = result.evidence_bundle
    assert (
        bundle.exact_transition_query_count,
        bundle.step_internal_legality_check_count,
        bundle.successor_catalogue_query_count,
        bundle.extra_ground_row_access_count,
        bundle.ground_search_count,
    ) == (3, 3, 0, 0, 0)
    by_tile = {
        int(
            next(
                action.action_key
                for action in result.catalogue.actions
                if action.action_id == item.ground_action_id
            ).removeprefix("tile=")
        ): item
        for item in bundle.evidence
    }
    assert tuple(sorted(by_tile)) == (2, 3, 4)
    assert by_tile[2].reward_features == (("match", Fraction(1)),)
    assert not by_tile[2].failure
    assert by_tile[2].successor_state.removed_mask == (
        SOURCE_SUCCESSOR_GROUND_STATE.removed_mask
    )
    assert by_tile[3].failure and by_tile[4].failure
    assert result.successor_catalogue_query_count == 0
    assert result.successor_transition_query_count == 0


def test_final_epoch_preserves_source_unknowns_and_certifies_after_replanning(
    heldout_contract,
) -> None:
    result = heldout_contract["heldout"]
    epoch = result.final_epoch
    audit = result.final_selected_audit.audit_result
    assert (
        epoch.observed_ground_row_count,
        epoch.missing_ground_row_count,
        epoch.exact_transition_query_count,
    ) == (10, 4, 3)
    assert set(epoch.source_missing_ground_row_ids) == set(
        epoch.planning_view.coverage.missing_ground_row_ids
    )
    assert set(epoch.target_ground_row_ids) <= set(
        epoch.planning_view.coverage.observed_ground_row_ids
    )
    initial_rows = {
        item.ground_row_id: item.to_document()
        for item in result.initial_epoch.planning_view.ground_rows
    }
    final_rows = {
        item.ground_row_id: item.to_document()
        for item in epoch.planning_view.ground_rows
    }
    assert all(
        initial_rows[row_id] == final_rows[row_id]
        for row_id in epoch.source_ground_row_ids
    )
    assert audit.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert audit.certificate is not None
    bounds = audit.robust_bounds
    assert (
        bounds.policy_reward_lower,
        bounds.policy_reward_upper,
        bounds.policy_failure_lower,
        bounds.policy_failure_upper,
        bounds.unrestricted_reward_upper,
        bounds.normalized_distribution_regret,
        bounds.external_coverage_certified,
    ) == (
        Fraction(1),
        Fraction(1),
        Fraction(0),
        Fraction(0),
        Fraction(1),
        Fraction(0),
        True,
    )
    assert result.initial_proposal.selected_semantic_key == (
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
    )
    assert result.final_proposal.selected_semantic_key == (
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
    )


def test_coordinate_transfer_reuses_source_dynamics_without_filling_unknowns(
    heldout_contract,
) -> None:
    transfer = heldout_contract["heldout"].coordinate_transfer
    assert transfer.shared_coordinate_values == (3,)
    assert transfer.semantic_labels == ((False,), (True,))
    assert transfer.source_support_cardinalities == (1, 2)
    assert transfer.heldout_support_cardinalities == (1, 2)
    assert transfer.abstract_realizations_equal == (True, True)
    assert transfer.compared_after_target_evidence
    assert not transfer.used_to_fill_missing_target_rows
    assert not transfer.coordinate_invention_claimed
    assert not transfer.statistical_generalization_claimed


def test_heldout_result_retains_narrow_claims_and_complete_work_counts(
    heldout_contract,
) -> None:
    result = heldout_contract["heldout"]
    assert (
        result.source_synthesis_full_replay_count,
        result.target_catalogue_query_count,
        result.exact_target_transition_query_count,
        result.candidate_plan_count,
        result.candidate_audit_count,
        result.independent_selected_audit_count,
    ) == (1, 1, 3, 8, 8, 2)
    assert result.query_local_model_only
    assert result.automatic_program_proposal_within_frozen_grammar_claimed
    assert not result.coordinate_invention_claimed
    assert not result.learned_dynamics_claimed
    assert not result.statistical_generalization_claimed
    assert not result.sample_efficiency_claimed
    assert not result.workload_economics_claimed
    assert not result.official_execution_allowed


def test_v0058_canonical_principal_ids_are_frozen(heldout_contract) -> None:
    closure = heldout_contract["closure"]
    result = heldout_contract["heldout"]
    assert {
        "program_registry_id": closure.program_registry.registry_id,
        "candidate_trace_id": closure.candidate_trace.trace_id,
        "selected_candidate_id": closure.selected_candidate.candidate_id,
        "coordinate_proposal_id": closure.coordinate_proposal.proposal_id,
        "source_partial_model_id": (
            closure.partial_build_result.model.model_id
        ),
        "synthesis_result_id": closure.result_id,
        "preregistration_id": (
            heldout_contract["preregistration"].preregistration_id
        ),
        "initial_epoch_id": result.initial_epoch.epoch_id,
        "authorization_id": result.authorization.authorization_id,
        "evidence_bundle_id": result.evidence_bundle.bundle_id,
        "final_epoch_id": result.final_epoch.epoch_id,
        "final_selected_audit_id": result.final_selected_audit.audit_id,
        "coordinate_transfer_id": result.coordinate_transfer.transfer_id,
        "heldout_result_id": result.result_id,
    } == {
        "program_registry_id": (
            "1331c29c9f23390b296d3be3777b99cda7eba915755bbd7d92808b411df1a9b0"
        ),
        "candidate_trace_id": (
            "a2addf7fc8a78889793d0fa381041e9e12f41e010d51f21580040108e938281a"
        ),
        "selected_candidate_id": (
            "aa9c34b68073c1869f8103183fb00df5a792b4c75c56d106088bf65e2abb7356"
        ),
        "coordinate_proposal_id": (
            "1afa79feca7d6ea93f687f5fe9386427b1d79bce7848f19fad98ddcccc3669b1"
        ),
        "source_partial_model_id": (
            "a3a03c8c31adc8236c549fd311ace906e3af5331937d0f8537ff220d75785f4f"
        ),
        "synthesis_result_id": (
            "f4b4904a5d1944e97dcf4dfc8e2fd7620b74dedf32f60ee2dd94e41f7b22666f"
        ),
        "preregistration_id": (
            "3389cec70655a35e69a606c2ef72daca00c5c6362f780fe78bb4218911d3dcd5"
        ),
        "initial_epoch_id": (
            "027abab818aae2bd0469f5ab4f45197457bcc08a66700c434a87799a708f40f1"
        ),
        "authorization_id": (
            "b30d795691a056c08ead4a003e187d7b57ed8ad2829f73c5a4a2c190065614aa"
        ),
        "evidence_bundle_id": (
            "5269dd0c8675201b637cf274d570225463885a9ffc0ce9336f53e9d4345eb5a3"
        ),
        "final_epoch_id": (
            "b835afe210574787aa668640d12500d7829268c1d041e521defdaaa687792efe"
        ),
        "final_selected_audit_id": (
            "d09b1882d41234bd930ea6702d1ca620b6f7c7afec6967a83e34578005a93d96"
        ),
        "coordinate_transfer_id": (
            "fe3656299154cd6b79fd3e2ba102fa997bfc1857ec15eebf086261a631e32f8b"
        ),
        "heldout_result_id": (
            "f70cbc1c48645c071ab842c0ec328d22157a61458b72a17933daf82e9ae7efdd"
        ),
    }


def test_heldout_complete_replay_is_deterministic(heldout_contract) -> None:
    assert (
        verify_lmb_program_closure_heldout_h2_v1(
            heldout_contract["log"],
            heldout_contract["profile"],
            heldout_contract["authority"],
            heldout_contract["preregistration"],
            heldout_contract["closure"],
            heldout_contract["kernel"],
            heldout_contract["heldout"],
        )
        == ()
    )


def test_heldout_runtime_change_and_overclaim_fail_closed(
    heldout_contract, monkeypatch
) -> None:
    original = heldout_module._assemble_planning_view

    def changed_assemble(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(
        heldout_module, "_assemble_planning_view", changed_assemble
    )
    with pytest.raises(
        ProgramClosureHeldOutH2InvariantViolation,
        match="runtime held-out H2 implementation differs",
    ):
        run_lmb_program_closure_heldout_h2_v1(
            heldout_contract["log"],
            heldout_contract["profile"],
            heldout_contract["authority"],
            heldout_contract["preregistration"],
            heldout_contract["closure"],
            heldout_contract["kernel"],
        )
    with pytest.raises(ProgramClosureHeldOutH2InvariantViolation):
        replace(
            heldout_contract["heldout"],
            statistical_generalization_claimed=True,
        )
