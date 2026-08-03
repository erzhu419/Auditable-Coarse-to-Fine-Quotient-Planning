from __future__ import annotations

import dataclasses
from functools import cache
from pathlib import Path

import pytest

from acfqp import construction_k7_h1_branch_aware_output_contract_v1 as output_v1
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


@cache
def _recipe_inputs() -> tuple[bytes, recipe_v1.H1DirectFallbackTwoRoleRecipeV1]:
    proof = issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof)["identity"]
    )
    current = acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )
    candidate = acquisition_v1.replay_canonical_direct_fallback_preexecution_candidate_v1(
        proof,
        current_identity=current,
    )
    preexecution = canonical_json_bytes(candidate.to_document())
    return (
        preexecution,
        recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
            preexecution_candidate_bytes=preexecution
        ),
    )


def _input(case: output_v1.H1OutputCaseV1) -> output_v1.H1OutputStructuralInputV1:
    _, recipe = _recipe_inputs()
    row = output_v1.presence_row_for_case_v1(case)
    broker = output_v1.issue_h1_broker_output_fixture_v1(case=case, recipe=recipe)
    business = (
        output_v1.issue_h1_business_result_fixture_v1(
            outcome=output_v1.business_outcome_for_case_v1(case), recipe=recipe
        )
        if row.business_result_committed
        else None
    )
    return output_v1.freeze_h1_output_structural_input_v1(
        case=case,
        recipe=recipe,
        broker_fixture=broker,
        business_fixture=business,
    )


def test_contract_locks_exact_roles_and_central_domains() -> None:
    assert output_v1.PROPOSED_CONTRACT_VERSION == "2.0.51"
    assert output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES == (
        "BUSINESS_RESULT",
        "OPERATIONAL_TRACE",
        "TERMINAL_ARTIFACT",
        "COUNTER_RECORD_SET",
        "WORK_VECTOR",
        "COMPARISON_VECTOR",
        "ACTUAL_PROJECTION_PROOF",
        "OUTPUT_MANIFEST",
    )
    assert len(set(output_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 8
    assert set(output_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert output_v1.CONSTRUCTION_ONLY is True
    assert output_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert output_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert output_v1.NUMERIC_AGGREGATE_CANDIDATE_ISSUED is False
    assert output_v1.COUNTER_COMPLETENESS_GATE_RUN is False
    assert output_v1.WORKLOAD_ECONOMICS_GATE_RUN is False
    assert output_v1.OFFICIAL_SCALAR_COST is None
    assert output_v1.OFFICIAL_N_BREAK_EVEN is None
    profile = output_v1.freeze_h1_branch_aware_output_profile_v1()
    document = profile.to_document()
    assert document["phase_split_placeholder_allowed"] is False
    assert document["opaque_renderer_callback_allowed"] is False
    assert document["unregistered_ninth_output_allowed"] is False
    assert document["production_semantic_inputs_present"] is False


def test_branch_matrix_is_complete_and_uses_exact_prefixes() -> None:
    matrix = output_v1.BRANCH_PRESENCE_MATRIX
    assert len(matrix) == len(output_v1.H1OutputCaseV1) == 72
    assert tuple(row.case for row in matrix) == tuple(output_v1.H1OutputCaseV1)
    assert all("PHASE_SPLIT" not in row.commit_phase.value for row in matrix)

    full = output_v1.presence_row_for_case_v1(
        output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS
    )
    assert full.present_roles == output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
    assert full.absent_roles == ()

    early = output_v1.presence_row_for_case_v1(
        output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7
    )
    assert early.present_roles == output_v1.BROKER_OUTPUT_ROLE_ORDER
    assert early.absent_roles == (output_v1.BUSINESS_RESULT_ROLE,)

    for branch, business_phases in output_v1._FAILURE_REACHABILITY:
        for business_phase in business_phases:
            committed = business_phase == "POST_BUSINESS"
            for prefix in range(8):
                case = output_v1.H1OutputCaseV1[
                    f"{branch.value}_{business_phase}_P{prefix}"
                ]
                row = output_v1.presence_row_for_case_v1(case)
                expected = (
                    ((output_v1.BUSINESS_RESULT_ROLE,) if committed else ())
                    + output_v1.BROKER_OUTPUT_ROLE_ORDER[:prefix]
                )
                expected = tuple(
                    role
                    for role in output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
                    if role in expected
                )
                assert row.branch is branch
                assert row.present_roles == expected
                assert row.broker_prefix_count == prefix
                assert row.output_finalization_failed is (prefix < 7)
                assert row.invalidates_official_run is True
            closure_case = output_v1.H1OutputCaseV1[
                f"{branch.value}_{business_phase}_P7_CLOSURE_FAILURE"
            ]
            closure = output_v1.presence_row_for_case_v1(closure_case)
            assert closure.branch is branch
            assert closure.broker_prefix_count == 7
            assert closure.output_finalization_failed is True
            assert closure.invalidates_official_run is True
    for branch in (
        output_v1.H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS,
        output_v1.H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED,
    ):
        for prefix in range(8):
            case = output_v1.H1OutputCaseV1[
                f"{branch.value}_OUTPUT_FINALIZATION_FAILURE_P{prefix}"
            ]
            row = output_v1.presence_row_for_case_v1(case)
            assert row.branch is branch
            assert row.business_result_committed is True
            assert row.broker_prefix_count == prefix
            assert row.output_finalization_failed is True
            assert row.invalidates_official_run is True


def test_typed_owner_handles_reject_fabrication_and_cross_branch() -> None:
    _, recipe = _recipe_inputs()
    absent_case = output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7
    present_case = output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_POST_BUSINESS_P7
    present_business = output_v1.issue_h1_business_result_fixture_v1(
        outcome=output_v1.business_outcome_for_case_v1(present_case), recipe=recipe
    )
    absent_broker = output_v1.issue_h1_broker_output_fixture_v1(
        case=absent_case, recipe=recipe
    )
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.freeze_h1_output_structural_input_v1(
            case=absent_case,
            recipe=recipe,
            broker_fixture=absent_broker,
            business_fixture=present_business,
        )

    wrong_business = output_v1.issue_h1_business_result_fixture_v1(
        outcome=output_v1.H1BusinessOutcomeV1.EXACT_INFEASIBILITY_RESULT,
        recipe=recipe,
    )
    present_broker = output_v1.issue_h1_broker_output_fixture_v1(
        case=present_case, recipe=recipe
    )
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.freeze_h1_output_structural_input_v1(
            case=present_case,
            recipe=recipe,
            broker_fixture=present_broker,
            business_fixture=wrong_business,
        )

    wrong_broker = output_v1.issue_h1_broker_output_fixture_v1(
        case=output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_POST_BUSINESS_P7,
        recipe=recipe,
    )
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.freeze_h1_output_structural_input_v1(
            case=present_case,
            recipe=recipe,
            broker_fixture=wrong_broker,
            business_fixture=present_business,
        )

    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.H1BrokerOutputFixtureV1(
            case=absent_case,
            recipe=recipe,
            fixture_id="0" * 64,
            issuer=object(),
        )


def test_profile_input_and_fixtures_bind_exact_recipe_route_context() -> None:
    preexecution, recipe = _recipe_inputs()
    profile = output_v1.freeze_h1_branch_aware_output_profile_v1().to_document()
    assert profile["required_upstream_h1_recipe_profile_id"] == (
        recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().profile_id
    )
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    context = source._payload()["recipe_context"]
    assert context["upstream_h1_recipe_id"] == recipe.recipe_id
    assert context["RouteDecisionContext_id"] == recipe.source.route_decision_context_id
    assert context["logical_occurrence_id"] == recipe.source.logical_occurrence_id
    assert context["route_attempt_id"] == recipe.source.route_attempt_id

    transplanted_recipe = recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution
    )
    broker = output_v1.issue_h1_broker_output_fixture_v1(
        case=output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7,
        recipe=transplanted_recipe,
    )
    object.__setattr__(
        transplanted_recipe.source, "logical_occurrence_id", "0" * 64
    )
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.freeze_h1_output_structural_input_v1(
            case=output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7,
            recipe=recipe,
            broker_fixture=broker,
        )


def test_committed_business_and_broker_prefix_bytes_are_future_stable() -> None:
    _, recipe = _recipe_inputs()
    business = output_v1.issue_h1_business_result_fixture_v1(
        outcome=output_v1.H1BusinessOutcomeV1.COMMITTED_BEFORE_LATER_FAILURE,
        recipe=recipe,
    )
    business_bytes = business.raw_bytes
    for prefix in range(8):
        case = output_v1.H1OutputCaseV1[
            f"PROTOCOL_FAILURE_POST_BUSINESS_P{prefix}"
        ]
        broker = output_v1.issue_h1_broker_output_fixture_v1(
            case=case, recipe=recipe
        )
        source = output_v1.freeze_h1_output_structural_input_v1(
            case=case,
            recipe=recipe,
            broker_fixture=broker,
            business_fixture=business,
        )
        assert source.business_fixture is business
        assert source.business_fixture.raw_bytes == business_bytes

    for branch, outcome in (
        (
            output_v1.H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS,
            output_v1.H1BusinessOutcomeV1.EXACT_INFEASIBILITY_RESULT,
        ),
        (
            output_v1.H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED,
            output_v1.H1BusinessOutcomeV1.FALLBACK_CAP_EXHAUSTED_RESULT,
        ),
    ):
        stable_business = output_v1.issue_h1_business_result_fixture_v1(
            outcome=outcome, recipe=recipe
        )
        stable_bytes = stable_business.raw_bytes
        for prefix in range(8):
            case = output_v1.H1OutputCaseV1[
                f"{branch.value}_OUTPUT_FINALIZATION_FAILURE_P{prefix}"
            ]
            broker = output_v1.issue_h1_broker_output_fixture_v1(
                case=case, recipe=recipe
            )
            source = output_v1.freeze_h1_output_structural_input_v1(
                case=case,
                recipe=recipe,
                broker_fixture=broker,
                business_fixture=stable_business,
            )
            assert source.business_fixture is stable_business
            assert source.business_fixture.raw_bytes == stable_bytes

    rendered_by_prefix = []
    for prefix in range(1, 8):
        case = output_v1.H1OutputCaseV1[
            f"PROTOCOL_FAILURE_PRE_BUSINESS_P{prefix}"
        ]
        rendered_by_prefix.append(
            output_v1._render_candidate_once_v1(_input(case), 0)
        )
    for earlier, later in zip(rendered_by_prefix, rendered_by_prefix[1:]):
        common_count = len(earlier.artifacts)
        assert tuple(item.raw_bytes for item in earlier.artifacts) == tuple(
            item.raw_bytes for item in later.artifacts[:common_count]
        )
        assert tuple(item.descriptor() for item in earlier.artifacts) == tuple(
            item.descriptor() for item in later.artifacts[:common_count]
        )

    for finalized_case, closure_case in (
        (
            output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS,
            output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS_OUTPUT_FINALIZATION_FAILURE_P7,
        ),
        (
            output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7,
            output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7_CLOSURE_FAILURE,
        ),
        (
            output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_POST_BUSINESS_P7,
            output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_POST_BUSINESS_P7_CLOSURE_FAILURE,
        ),
    ):
        finalized = output_v1._render_candidate_once_v1(_input(finalized_case), 0)
        closure = output_v1._render_candidate_once_v1(_input(closure_case), 0)
        assert tuple(item.raw_bytes for item in finalized.artifacts) == tuple(
            item.raw_bytes for item in closure.artifacts
        )
        assert tuple(item.descriptor() for item in finalized.artifacts) == tuple(
            item.descriptor() for item in closure.artifacts
        )


@pytest.mark.parametrize(
    "case",
    [
        output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS,
        output_v1.H1OutputCaseV1.FALLBACK_CAP_EXHAUSTED,
        output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7,
        output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_POST_BUSINESS_P7,
    ],
)
def test_fixed_point_exact_roles_manifest_and_replay(
    case: output_v1.H1OutputCaseV1,
) -> None:
    source = _input(case)
    row = output_v1.presence_row_for_case_v1(case)
    result = output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)
    final = result.final_artifact_set
    assert tuple(item.role for item in final.artifacts) == row.present_roles
    assert tuple(item.role for item in final.absences) == row.absent_roles
    assert final.candidate_output_bytes == final.actual_output_bytes
    assert final.actual_output_bytes == sum(item.byte_count for item in final.artifacts)
    assert len(final.artifacts) <= 8
    assert result.exact_fixed_point is True
    assert (
        output_v1.replay_h1_branch_aware_output_fixed_point_v1(result).result_id
        == result.result_id
    )

    manifest = output_v1.parse_output_manifest_v1(
        final.artifacts[-1], expected_recipe=_recipe_inputs()[1]
    )
    assert manifest["candidate_output_bytes"] == final.actual_output_bytes
    assert manifest["present_non_manifest_roles"] == [
        item.descriptor() for item in final.artifacts[:-1]
    ]
    assert manifest["absent_roles"] == [
        item.to_document() for item in final.absences
    ]
    assert manifest["manifest_self_identity_fields_present"] is False
    assert manifest["unregistered_ninth_output_present"] is False
    assert not {
        "output_manifest_id",
        "manifest_id",
        "manifest_sha256",
        "own_artifact_id",
    } & set(manifest)


def test_all_failure_causes_and_prefixes_preserve_exact_committed_subset() -> None:
    representative_cases = (
        output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P0,
        output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_POST_BUSINESS_P3,
        output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_PRE_BUSINESS_P2,
        output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_POST_BUSINESS_P7,
        output_v1.H1OutputCaseV1.AMBIGUOUS_NATIVE_LAUNCH_PRE_BUSINESS_P1,
        output_v1.H1OutputCaseV1.H1_BUSINESS_ADAPTER_FAILURE_PRE_BUSINESS_P7,
        output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS_OUTPUT_FINALIZATION_FAILURE_P0,
        output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS_OUTPUT_FINALIZATION_FAILURE_P7,
        output_v1.H1OutputCaseV1.FALLBACK_CAP_EXHAUSTED_OUTPUT_FINALIZATION_FAILURE_P4,
        output_v1.H1OutputCaseV1.FALLBACK_CAP_EXHAUSTED_OUTPUT_FINALIZATION_FAILURE_P7,
    )
    for case in representative_cases:
        source = _input(case)
        row = output_v1.presence_row_for_case_v1(case)
        result = output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)
        final = result.final_artifact_set
        assert tuple(item.role for item in final.artifacts) == row.present_roles
        assert tuple(item.role for item in final.absences) == row.absent_roles
        assert result._payload()["invalidates_official_run"] is True
        if row.broker_prefix_count < len(output_v1.BROKER_OUTPUT_ROLE_ORDER):
            assert output_v1.OUTPUT_MANIFEST_ROLE in row.absent_roles
        else:
            manifest = output_v1.parse_output_manifest_v1(
                final.artifacts[-1], expected_recipe=_recipe_inputs()[1]
            )
            assert manifest["absent_roles"] == [
                item.to_document() for item in final.absences
            ]


def test_independent_raw_byte_set_verifier_reconstructs_recipe_and_fixed_point() -> None:
    preexecution, recipe = _recipe_inputs()
    for case in (
        output_v1.H1OutputCaseV1.INTEGRITY_FAILURE_POST_BUSINESS_P7,
        output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P3,
    ):
        result = output_v1.solve_h1_branch_aware_output_fixed_point_v1(_input(case))
        ordered = tuple(
            (item.role, item.raw_bytes) for item in result.final_artifact_set.artifacts
        )
        replay = output_v1.verify_h1_output_role_bytes_v1(
            recipe_bytes=recipe.canonical_bytes,
            preexecution_candidate_bytes=preexecution,
            case=case,
            ordered_role_bytes=ordered,
        )
        assert replay.artifact_set_id == result.final_artifact_set.artifact_set_id
        if case.value.endswith("_P3"):
            assert output_v1.OUTPUT_MANIFEST_ROLE not in dict(ordered)

        with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
            output_v1.verify_h1_output_role_bytes_v1(
                recipe_bytes=recipe.canonical_bytes,
                preexecution_candidate_bytes=preexecution,
                case=case,
                ordered_role_bytes=tuple(reversed(ordered)),
            )


def test_artifact_set_candidate_above_cap_fails_even_with_recomputed_id() -> None:
    case = output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P1
    result = output_v1.solve_h1_branch_aware_output_fixed_point_v1(_input(case))
    final = result.final_artifact_set
    object.__setattr__(
        final,
        "candidate_output_bytes",
        final.structural_input.profile.total_byte_cap + 1,
    )
    object.__setattr__(final, "artifact_set_id", output_v1._artifact_set_identity(final))
    with pytest.raises(
        output_v1.ConstructionK7H1BranchAwareOutputContractV1Error,
        match="candidate exceeds",
    ):
        output_v1.verify_h1_rendered_artifact_set_v1(final)


def test_exact_bytes_and_exact_integer_attacks_fail_closed() -> None:
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    business = source.business_fixture
    assert business is not None
    object.__setattr__(business, "raw_bytes", bytearray(business.raw_bytes))
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)

    empty = output_v1.solve_h1_branch_aware_output_fixed_point_v1(
        _input(output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P0)
    ).final_artifact_set
    object.__setattr__(empty, "actual_output_bytes", False)
    object.__setattr__(empty, "artifact_set_id", output_v1._artifact_set_identity(empty))
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.verify_h1_rendered_artifact_set_v1(empty)


def test_checked_manifest_parser_rejects_ninth_output_flag_mutation() -> None:
    final = output_v1.solve_h1_branch_aware_output_fixed_point_v1(
        _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    ).final_artifact_set
    manifest = final.artifacts[-1]
    document = loads_canonical_json(manifest.raw_bytes)
    document["unregistered_ninth_output_present"] = True
    object.__setattr__(manifest, "raw_bytes", canonical_json_bytes(document))
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.parse_output_manifest_v1(
            manifest, expected_recipe=_recipe_inputs()[1]
        )

    original = final.artifacts[-1]
    context_attack = loads_canonical_json(original.raw_bytes)
    context_attack["recipe_context"] = {}
    reissued_attack = output_v1._freeze_artifact(
        output_v1.OUTPUT_MANIFEST_ROLE,
        canonical_json_bytes(context_attack),
    )
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.parse_output_manifest_v1(
            reissued_attack, expected_recipe=_recipe_inputs()[1]
        )


@pytest.mark.parametrize("attack", ["reorder", "missing", "ninth", "wrong_prefix"])
def test_artifact_role_set_attacks_fail_closed(attack: str) -> None:
    result = output_v1.solve_h1_branch_aware_output_fixed_point_v1(
        _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    )
    final = result.final_artifact_set
    original = final.artifacts
    if attack == "reorder":
        attacked = (original[1], original[0], *original[2:])
    elif attack == "missing":
        attacked = original[:-1]
    elif attack == "ninth":
        attacked = (*original, original[-1])
    else:
        attacked = (original[0], *original[2:])
    object.__setattr__(final, "artifacts", tuple(attacked))
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.verify_h1_rendered_artifact_set_v1(final)


def test_manifest_self_reference_attack_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    original = output_v1._serialize_output_manifest_v1

    def self_referencing(*args: object, **kwargs: object) -> bytes:
        document = output_v1.loads_canonical_json(original(*args, **kwargs))
        document["own_sha256"] = "0" * 64
        return canonical_json_bytes(document)

    monkeypatch.setattr(output_v1, "_serialize_output_manifest_v1", self_referencing)
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)


def test_nondeterministic_serializer_attack_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    original = output_v1._serialize_broker_role_v1
    call_count = 0

    def alternating(source_arg: object, role: str) -> bytes:
        nonlocal call_count
        call_count += 1
        document = output_v1.loads_canonical_json(original(source_arg, role))
        document["attack_nonce"] = call_count
        return canonical_json_bytes(document)

    monkeypatch.setattr(output_v1, "_serialize_broker_role_v1", alternating)
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)


def test_iteration_cap_and_role_byte_cap_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(output_v1, "MAX_FIXED_POINT_ITERATIONS", 1)
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    with pytest.raises(
        output_v1.ConstructionK7H1BranchAwareOutputContractV1Error,
        match="did not converge",
    ):
        output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)

    monkeypatch.setattr(output_v1, "MAX_FIXED_POINT_ITERATIONS", 32)
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    original = output_v1._serialize_broker_role_v1

    def oversized(source_arg: object, role: str) -> bytes:
        document = output_v1.loads_canonical_json(original(source_arg, role))
        document["oversized"] = "x" * output_v1.MAX_ROLE_BYTES
        return canonical_json_bytes(document)

    monkeypatch.setattr(output_v1, "_serialize_broker_role_v1", oversized)
    with pytest.raises(
        output_v1.ConstructionK7H1BranchAwareOutputContractV1Error,
        match="role cap",
    ):
        output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)


def test_input_and_result_identity_mutations_fail_closed() -> None:
    source = _input(output_v1.H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS)
    result = output_v1.solve_h1_branch_aware_output_fixed_point_v1(source)
    object.__setattr__(source, "structural_input_id", "0" * 64)
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        output_v1.replay_h1_branch_aware_output_fixed_point_v1(result)


def test_dataclass_replacement_cannot_mint_authority() -> None:
    _, recipe = _recipe_inputs()
    fixture = output_v1.issue_h1_broker_output_fixture_v1(
        case=output_v1.H1OutputCaseV1.PROTOCOL_FAILURE_PRE_BUSINESS_P7,
        recipe=recipe,
    )
    with pytest.raises(output_v1.ConstructionK7H1BranchAwareOutputContractV1Error):
        dataclasses.replace(fixture, fixture_id="0" * 64, issuer=object())
