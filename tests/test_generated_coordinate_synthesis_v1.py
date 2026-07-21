from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.generated_coordinate_synthesis_v1 as generated_module
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains.matching_buffer import LMBState, LMBStatus, generate_solvable_lmb
from acfqp.generated_coordinate_synthesis_v1 import (
    GeneratedCoordinateInvariantViolation,
    GeneratedCoordinateStatus,
    GeneratedDSLRegistryV1,
    GeneratedExpressionV1,
    run_generated_lmb_control_v1,
    synthesize_generated_lmb_homomorphism_v1,
    verify_generated_lmb_homomorphism_v1,
)


@pytest.fixture(scope="module")
def generated_contract():
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    support = (
        (11, (1, 2)),
        (13, (2, 1)),
        (19, (1, 2)),
        (21, (2, 1)),
        (25, (1, 2)),
        (35, (2, 1)),
        (41, (2, 1)),
        (49, (2, 1)),
        (7, (2, 1)),
    )
    query = QuerySpec(
        tuple(
            (
                Fraction(1, len(support)),
                LMBState(mask, buffer, LMBStatus.ACTIVE),
            )
            for mask, buffer in support
        ),
        horizon=3,
        reward_weights=(
            ("match", Fraction(1)),
            ("terminal_clear", Fraction(1)),
        ),
        goal="default",
        delta=Fraction(1, 20),
        normalizer=Fraction(4),
        normalizer_proof_id="lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    )
    coverage = SuiteBuildCoverage.from_queries(kernel, (query,))
    assert len(coverage.covered_states) == 25
    return kernel, coverage, query


@pytest.fixture(scope="module")
def generated_result(generated_contract):
    kernel, coverage, _ = generated_contract
    return synthesize_generated_lmb_homomorphism_v1(kernel, coverage)


def _assert_state_program_ast(expression: GeneratedExpressionV1) -> None:
    assert expression.operation == "cardinality"
    assert len(expression.arguments) == 1
    assert expression.arguments[0].operation == "legal_actions"


def _assert_action_program_ast(expression: GeneratedExpressionV1) -> None:
    assert expression.operation == "buffer_at_type"
    buffer, tile_type = expression.arguments
    assert buffer.operation == "buffer_counts"
    assert tile_type.operation == "selected_tile_type"


def test_production_api_has_no_query_target_or_named_feature_channel(
    generated_contract,
) -> None:
    kernel, _, query = generated_contract
    signature = inspect.signature(synthesize_generated_lmb_homomorphism_v1)
    assert tuple(signature.parameters) == ("kernel", "coverage")
    with pytest.raises(GeneratedCoordinateInvariantViolation, match="SuiteBuildCoverage"):
        synthesize_generated_lmb_homomorphism_v1(kernel, query)  # type: ignore[arg-type]

    source = inspect.getsource(generated_module)
    banned_named_features = ("action" + "_count", "completes" + "_match")
    assert not any(name in source for name in banned_named_features)
    registry_document = generated_module.generated_dsl_registry_v1().to_document()
    assert not any(name in repr(registry_document) for name in banned_named_features)

    imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.core" not in imports
    assert "acfqp.feature_synthesis" not in imports
    assert "acfqp.abstraction.behavioral" not in imports
    assert not any(module.startswith("acfqp.planning") for module in imports)


def test_generated_program_golden_complete_trace_and_exact_model(
    generated_result,
) -> None:
    result = generated_result
    certificate = result.certificate
    assert result.status is GeneratedCoordinateStatus.EXACT_GENERATED_HOMOMORPHISM
    assert result.trace.required_candidate_count == 4096
    assert result.trace.evaluated_candidate_count == 4096
    assert len(result.trace.candidates) == 4096
    assert certificate.complete_candidate_trace is True
    assert len(certificate.selected_state_program_asts) == 1
    assert len(certificate.selected_action_program_asts) == 1
    _assert_state_program_ast(certificate.selected_state_program_asts[0])
    _assert_action_program_ast(certificate.selected_action_program_asts[0])
    assert (
        certificate.ground_state_count,
        certificate.active_ground_state_count,
        certificate.quotient_cell_count,
        certificate.active_quotient_cell_count,
        certificate.abstract_entry_count,
    ) == (25, 18, 5, 3, 4)
    assert len(result.quotient_models.envelope.entries) == 4
    assert all(
        len(
            {
                (
                    realization.reward_features,
                    realization.successor_probabilities,
                    realization.failure_probability,
                    realization.termination_probability,
                )
                for realization in entry.realizations
            }
        )
        == 1
        for entry in result.quotient_models.envelope.entries
    )
    selected = next(
        item
        for item in result.trace.candidates
        if item.candidate_id == result.trace.selected_candidate_id
    )
    state_by_id = {
        item.expression_id: item for item in result.registry.state_programs
    }
    action_by_id = {
        item.expression_id: item for item in result.registry.action_programs
    }
    assert selected == min(
        (item for item in result.trace.candidates if item.exact_homomorphism),
        key=lambda item: generated_module._candidate_selection_key(
            item, state_by_id, action_by_id
        ),
    )


def test_registry_transport_and_independent_full_rebuild(
    generated_contract,
    generated_result,
) -> None:
    registry = GeneratedDSLRegistryV1.from_document(
        generated_result.registry.to_document()
    )
    assert registry == generated_result.registry
    kernel, coverage, _ = generated_contract
    assert verify_generated_lmb_homomorphism_v1(
        kernel, coverage, generated_result
    ) == ()


def test_no_exact_and_cap_controls_publish_no_model(generated_contract) -> None:
    kernel, coverage, _ = generated_contract
    cap = run_generated_lmb_control_v1(
        kernel, coverage, control="candidate_cap_one"
    )
    assert cap.status is GeneratedCoordinateStatus.CANDIDATE_CAP_EXHAUSTED
    assert cap.trace.required_candidate_count == 4096
    assert cap.trace.evaluated_candidate_count == 0
    assert cap.trace.witnesses[0].witness_kind == "CANDIDATE_CAP_INSUFFICIENT"
    assert cap.certificate is None and cap.portable_build is None

    no_action = run_generated_lmb_control_v1(
        kernel, coverage, control="state_only_no_action_programs"
    )
    assert no_action.status is GeneratedCoordinateStatus.NO_EXACT_GENERATED_HOMOMORPHISM
    assert no_action.trace.required_candidate_count == 256
    assert no_action.trace.evaluated_candidate_count == 256
    assert no_action.certificate is None and no_action.portable_build is None
    assert {item.witness_kind for item in no_action.trace.witnesses} == {
        "WITHIN_STATE_ACTION_ALIAS"
    }


def test_forged_ast_evaluator_duck_and_trace_attacks_are_rejected(
    generated_contract,
    generated_result,
    monkeypatch,
) -> None:
    expression_document = generated_result.registry.state_programs[0].to_document()
    expression_document["operation"] = "selected_tile_type"
    expression_document["result_type"] = "TILE_TYPE"
    expression_document["context"] = "STATE_ACTION"
    payload = dict(expression_document)
    payload.pop("expression_id")
    expression_document["expression_id"] = generated_module._content_id(
        generated_module.EXPRESSION_DOMAIN, payload
    )
    with pytest.raises(GeneratedCoordinateInvariantViolation, match="primitive"):
        GeneratedExpressionV1.from_document(expression_document)

    class DuckResult:
        pass

    kernel, coverage, _ = generated_contract
    with pytest.raises(GeneratedCoordinateInvariantViolation, match="duck"):
        verify_generated_lmb_homomorphism_v1(
            kernel, coverage, DuckResult()  # type: ignore[arg-type]
        )

    forged_trace = replace(
        generated_result.trace,
        required_candidate_count=4095,
        evaluated_candidate_count=4095,
        candidates=generated_result.trace.candidates[1:],
    )
    forged_certificate = replace(
        generated_result.certificate,
        trace_id=forged_trace.trace_id,
    )
    forged_result = replace(
        generated_result,
        trace=forged_trace,
        certificate=forged_certificate,
    )
    failures = verify_generated_lmb_homomorphism_v1(
        kernel, coverage, forged_result
    )
    assert "TRACE_MISMATCH" in failures
    assert "CERTIFICATE_MISMATCH" in failures

    original_getsource = generated_module.inspect.getsource
    monkeypatch.setattr(
        generated_module.inspect,
        "getsource",
        lambda target: (
            "tampered evaluator"
            if target is generated_module._eval_expression
            else original_getsource(target)
        ),
    )
    with pytest.raises(GeneratedCoordinateInvariantViolation, match="frozen authority"):
        synthesize_generated_lmb_homomorphism_v1(kernel, coverage)


def test_claim_remains_narrow_and_all_unrun_gates_stay_locked(
    generated_result,
) -> None:
    certificate = generated_result.certificate
    assert certificate.official_execution_allowed is False
    assert certificate.official_scalar_cost is None
    assert certificate.official_N_break_even is None
    assert certificate.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert certificate.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert certificate.sample_efficiency_gate == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    for excluded in (
        "unknown-semantic invention",
        "neural learning",
        "partial dynamics",
        "sample-efficiency",
        "scale",
        "cross-domain generalisation",
    ):
        assert excluded in certificate.claim_scope
