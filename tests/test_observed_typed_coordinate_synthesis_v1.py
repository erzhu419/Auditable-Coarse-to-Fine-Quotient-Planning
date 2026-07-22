from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.observation_partial_rapm_v1 as partial_module
import acfqp.observed_typed_coordinate_synthesis_v1 as synthesis_module
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.generated_coordinate_synthesis_v1 import generated_dsl_registry_v1
from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
)
from acfqp.observation_partial_rapm_v1 import (
    FrozenTypedActionCoordinateAtomV2,
    FrozenTypedCoordinateProposalV2,
    ObservationPartialRAPMInvariantViolation,
    PartialSemanticActionV1,
    TypedActionAtomKind,
    build_observation_partial_rapm_from_typed_values_v2,
    validate_preregistered_observation_source_graph_v1,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    CandidateEntryClass,
    ObservedTypedCoordinateInvariantViolation,
    REQUIRED_CANDIDATE_COUNT,
    SUCCESS_STATUS,
    synthesize_observed_lmb_partial_rapm_cap_control_v1,
    synthesize_observed_lmb_partial_rapm_v1,
    verify_observed_lmb_partial_rapm_v1,
)

import test_observation_partial_rapm_v1 as observation_fixture_module


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def synthesis_contract():
    source = observation_fixture_module.observation_contract.__wrapped__()
    result = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    return {**source, "synthesis": result}


def test_production_api_has_exactly_three_source_inputs(synthesis_contract) -> None:
    assert tuple(inspect.signature(synthesize_observed_lmb_partial_rapm_v1).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
    )
    assert tuple(inspect.signature(verify_observed_lmb_partial_rapm_v1).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "claimed_result",
    )
    assert "build_observation_partial_rapm_from_typed_values_v2" not in partial_module.__all__
    assert "verify_observation_partial_rapm_from_typed_values_v2" not in partial_module.__all__
    with pytest.raises(TypeError):
        synthesize_observed_lmb_partial_rapm_v1(
            synthesis_contract["log"],
            synthesis_contract["profile"],
            synthesis_contract["authority"],
            query={"forbidden": True},  # type: ignore[call-arg]
        )


def test_all_4096_candidates_are_traced_before_selection(synthesis_contract) -> None:
    result = synthesis_contract["synthesis"]
    assert result.status == SUCCESS_STATUS
    assert result.candidate_trace.required_candidate_count == REQUIRED_CANDIDATE_COUNT
    assert result.candidate_trace.evaluated_candidate_count == REQUIRED_CANDIDATE_COUNT
    assert len(result.candidate_trace.candidates) == REQUIRED_CANDIDATE_COUNT
    assert tuple(item.candidate_index for item in result.candidate_trace.candidates) == tuple(
        range(1, REQUIRED_CANDIDATE_COUNT + 1)
    )
    assert result.candidate_trace.candidates[0].state_mask == 0
    assert result.candidate_trace.candidates[0].action_mask == 0
    assert not result.candidate_trace.candidates[0].admissible
    assert result.result_id == (
        "4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2"
    )
    assert result.certificate.certificate_id == (
        "6b63e89ef44d5b8fe286db2168e595d1ddec9ac296845311f1e7bf5dbce22e84"
    )
    assert result.candidate_trace.trace_id == (
        "4737d3fe32b7db8490f6903331e0ca11411d94b7b6bae3fe1afcbdf653582ebc"
    )


def test_selected_programs_are_observation_only_and_nonvacuous(synthesis_contract) -> None:
    result = synthesis_contract["synthesis"]
    selected = result.selected_candidate
    program_by_id = {
        item.expression_id: item
        for item in (*result.dsl_registry.state_programs, *result.dsl_registry.action_programs)
    }
    state = tuple(program_by_id[item] for item in selected.state_expression_ids)
    action = tuple(program_by_id[item] for item in selected.action_expression_ids)
    assert len(state) == 1
    assert state[0].operation == "cardinality"
    assert state[0].arguments[0].operation == "legal_actions"
    assert len(action) == 1
    assert action[0].operation == "buffer_at_type"
    assert selected.point_identified_registered_rows == 7
    assert selected.partial_unknown_registered_rows == 0
    assert selected.observed_equal_alias_pair_count == 3
    assert selected.separated_null_conflict_pair_count == 18
    assert selected.nontrivial_point_entry_count == 3
    assert selected.availability_violation_count == 0
    assert selected.contradiction_entry_count == 0
    assert selected.total_cell_count == 6
    assert selected.abstract_entry_count == 5
    assert selected.candidate_id == (
        "33051de900a743d03250477a6627b55e18d3c23277d67198760e03fb0e528ba3"
    )
    assert selected.action_partition_id == (
        "0214cc53bef2bfd693cb14090d14ccc80665d4ff142cbe2fabbeb4d00cfe1ef7"
    )
    assert result.coordinate_proposal.proposal_id == (
        "cee1e3393a7686059e2f7d24647c5d3b906c9c9c0eff01683c116684b6c63123"
    )
    assert result.partial_build_result.result_id == (
        "7e3845fb4d92047c1bedf8cefb07504b2c5653250547e49cc8984502d84c7d2c"
    )
    assert result.partial_build_result.model.model_id == (
        "1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18"
    )


def test_integer_action_program_compiles_to_closed_boolean_midpoint_atom(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    atoms = result.coordinate_proposal.action_atoms
    assert len(atoms) == 1
    assert atoms[0].kind is TypedActionAtomKind.INTEGER_LEQ
    assert atoms[0].threshold == Fraction(3, 2)
    assert atoms[0].source_expression_id == result.selected_candidate.action_expression_ids[0]
    assert result.selected_candidate.action_atom_ids == (atoms[0].atom_id,)
    assert all(
        action.label_values
        and all(type(value) is bool for value in action.label_values)
        for action in result.partial_build_result.model.semantic_actions
    )
    with pytest.raises(ObservationPartialRAPMInvariantViolation):
        PartialSemanticActionV1(_hash("cell"), ())


def test_value_table_covers_all_source_rows_and_missing_is_not_evidence(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    table = result.value_table
    assert len(table.state_rows) == 8
    assert len(table.action_rows) == 11
    assert len(table.state_expression_ids) == 8
    assert len(table.action_expression_ids) == 4
    selected = result.selected_candidate
    classes = [item.classification for item in selected.entry_evidence]
    assert classes.count(CandidateEntryClass.POINT_IDENTIFIED) == 4
    assert classes.count(CandidateEntryClass.UNOBSERVED_UNKNOWN) == 1
    unknown = next(
        item
        for item in selected.entry_evidence
        if item.classification is CandidateEntryClass.UNOBSERVED_UNKNOWN
    )
    assert len(unknown.support_ground_row_ids) == 4
    assert unknown.observed_ground_row_ids == ()
    assert unknown.missing_ground_row_ids == unknown.support_ground_row_ids
    assert result.telemetry.missing_rows_status_inspections == 4 * 4096


def test_same_portable_partial_schema_preserves_observed_missing_and_simplex(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    model = result.partial_build_result.model
    assert result.partial_build_result.observed_ground_row_count == 7
    assert result.partial_build_result.missing_ground_row_count == 4
    assert len(model.coverage.registered_ground_row_ids) == 11
    assert len(model.cells) == 6
    assert len(model.semantic_actions) == 5
    assert len(model.semantic_realizations) == 6
    assert model.semantics_horizon_cap == 6
    assert model.query_neutral is True
    assert model.transition_closure_claimed is False
    assert model.exact_quotient_claimed is False
    for row in model.ground_rows:
        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON:
            assert row.ambiguity.unknown_mass == 0
            assert row.ambiguity.is_singleton
        else:
            assert row.ambiguity.unknown_mass == 1
            assert row.ambiguity.joint_simplex_constraint.unknown_atom_mass_sum == 1
            assert row.ambiguity.joint_simplex_constraint.independent_marginal_box_forbidden


def test_fixed_ast_documents_match_v0041_language_without_runtime_authority_reuse(
    synthesis_contract,
) -> None:
    observed = synthesis_contract["synthesis"].dsl_registry
    exact = generated_dsl_registry_v1()
    assert [item.to_document() for item in observed.state_programs] == [
        item.to_document() for item in exact.state_programs
    ]
    assert [item.to_document() for item in observed.action_programs] == [
        item.to_document() for item in exact.action_programs
    ]
    assert observed.registry_id != exact.registry_id
    source = inspect.getsource(synthesis_module)
    assert "generated_coordinate_synthesis_v1" not in source
    assert "LMBKernel" not in source


def test_runtime_source_digest_detects_unregistered_implementation_change(
    synthesis_contract,
    monkeypatch,
) -> None:
    original = synthesis_module._eval_expression

    def changed_evaluator(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(synthesis_module, "_eval_expression", changed_evaluator)
    with pytest.raises(
        ObservedTypedCoordinateInvariantViolation,
        match="runtime evaluator implementation differs from frozen authority",
    ):
        synthesize_observed_lmb_partial_rapm_v1(
            synthesis_contract["log"],
            synthesis_contract["profile"],
            synthesis_contract["authority"],
        )


def test_synthesizer_is_kernel_blind_under_local_unreachable_channel_check(
    synthesis_contract, monkeypatch
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("ground kernel channel must remain unreachable")

    monkeypatch.setattr(LMBKernel, "step", forbidden)
    monkeypatch.setattr(LMBKernel, "actions", forbidden)
    rebuilt = synthesize_observed_lmb_partial_rapm_v1(
        synthesis_contract["log"],
        synthesis_contract["profile"],
        synthesis_contract["authority"],
    )
    assert rebuilt.result_id == synthesis_contract["synthesis"].result_id
    imports = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(synthesis_module)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(item.startswith("acfqp.domains") for item in imports)
    assert "acfqp.generated_coordinate_synthesis_v1" not in imports


def test_retained_runtime_verifier_replays_source_candidates_and_model(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    assert verify_observed_lmb_partial_rapm_v1(
        synthesis_contract["log"],
        synthesis_contract["profile"],
        synthesis_contract["authority"],
        result,
    ) == ()


def test_compiled_atom_substitution_fails_v0042_pure_builder_replay(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    original = result.coordinate_proposal
    changed_atom = FrozenTypedActionCoordinateAtomV2(
        TypedActionAtomKind.INTEGER_LEQ,
        original.action_atoms[0].source_expression_id,
        Fraction(1, 2),
    )
    changed = FrozenTypedCoordinateProposalV2(
        original.state_expression_ids,
        original.action_expression_ids,
        (changed_atom,),
        original.dsl_registry_id,
        original.structural_binding_id,
        original.value_table_id,
        original.synthesis_spec_id,
        original.selected_candidate_id,
        original.candidate_trace_id,
        original.observation_log_id,
        original.semantics_profile_id,
        original.observation_authority_id,
        original.acquisition_manifest_id,
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="midpoint/identity compilation",
    ):
        build_observation_partial_rapm_from_typed_values_v2(
            synthesis_contract["log"],
            changed,
            result.value_table,
            synthesis_contract["profile"],
            synthesis_contract["authority"],
        )


def test_typed_pure_builder_rejects_partial_action_label_availability(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    coarse_state_proposal = replace(
        result.coordinate_proposal,
        state_expression_ids=(),
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="exactly the same semantic label set",
    ):
        build_observation_partial_rapm_from_typed_values_v2(
            synthesis_contract["log"],
            coarse_state_proposal,
            result.value_table,
            synthesis_contract["profile"],
            synthesis_contract["authority"],
        )


def test_public_source_replay_checks_nested_types_before_content_properties(
    synthesis_contract,
) -> None:
    touched: list[str] = []

    class UnexpectedNestedValue:
        @property
        def state_id(self):
            touched.append("state_id")
            raise AssertionError("nested property must remain unreachable")

        def to_document(self):
            touched.append("to_document")
            raise AssertionError("nested serializer must remain unreachable")

    changed_log = replace(synthesis_contract["log"])
    object.__setattr__(changed_log, "states", (UnexpectedNestedValue(),))
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="nested state substitutions before canonical access",
    ):
        validate_preregistered_observation_source_graph_v1(
            changed_log,
            synthesis_contract["profile"],
            synthesis_contract["authority"],
        )
    assert touched == []

    changed_counter = replace(synthesis_contract["log"].evidence_ledger.counters[0])
    object.__setattr__(changed_counter, "lane", UnexpectedNestedValue())
    changed_ledger = replace(synthesis_contract["log"].evidence_ledger)
    object.__setattr__(
        changed_ledger,
        "counters",
        (changed_counter, *synthesis_contract["log"].evidence_ledger.counters[1:]),
    )
    changed_log = replace(synthesis_contract["log"])
    object.__setattr__(changed_log, "evidence_ledger", changed_ledger)
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="malformed evidence counter.lane before canonical access",
    ):
        validate_preregistered_observation_source_graph_v1(
            changed_log,
            synthesis_contract["profile"],
            synthesis_contract["authority"],
        )
    assert touched == []


def test_retained_verifier_rejects_nested_result_substitution_before_access(
    synthesis_contract,
) -> None:
    touched: list[str] = []

    class UnexpectedNestedValue:
        @property
        def trace_id(self):
            touched.append("trace_id")
            raise AssertionError("nested property must remain unreachable")

    changed = replace(synthesis_contract["synthesis"])
    object.__setattr__(changed, "candidate_trace", UnexpectedNestedValue())
    with pytest.raises(
        ObservedTypedCoordinateInvariantViolation,
        match="nested runtime-type substitution",
    ):
        verify_observed_lmb_partial_rapm_v1(
            synthesis_contract["log"],
            synthesis_contract["profile"],
            synthesis_contract["authority"],
            changed,
        )
    assert touched == []


def test_typed_builder_checks_nested_v2_shape_before_content_properties(
    synthesis_contract,
) -> None:
    touched: list[str] = []

    class UnexpectedNestedValue:
        @property
        def atom_id(self):
            touched.append("atom_id")
            raise AssertionError("nested property must remain unreachable")

        def to_document(self):
            touched.append("to_document")
            raise AssertionError("nested serializer must remain unreachable")

    result = synthesis_contract["synthesis"]
    changed_proposal = replace(result.coordinate_proposal)
    object.__setattr__(
        changed_proposal,
        "action_atoms",
        (UnexpectedNestedValue(),),
    )
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="nested action-atom substitutions before canonical access",
    ):
        build_observation_partial_rapm_from_typed_values_v2(
            synthesis_contract["log"],
            changed_proposal,
            result.value_table,
            synthesis_contract["profile"],
            synthesis_contract["authority"],
        )
    assert touched == []


def test_unallowlisted_authority_substitution_fails_before_synthesis(
    synthesis_contract,
) -> None:
    with pytest.raises(
        ObservationPartialRAPMInvariantViolation,
        match="trust-root profile",
    ):
        replace(
            synthesis_contract["authority"],
            trusted_observer_id=_hash("unregistered-observer"),
        )


def test_nested_result_substitution_is_rejected_before_property_access(
    synthesis_contract,
) -> None:
    class UnexpectedAuthority:
        @property
        def candidate_trace(self):
            raise AssertionError("unexpected authority callback was reached")

    with pytest.raises(
        ObservedTypedCoordinateInvariantViolation,
        match="duck result",
    ):
        verify_observed_lmb_partial_rapm_v1(
            synthesis_contract["log"],
            synthesis_contract["profile"],
            synthesis_contract["authority"],
            UnexpectedAuthority(),  # type: ignore[arg-type]
        )


def test_postfreeze_h3_h1_reuse_prerequisites_and_missing_grouping(
    synthesis_contract,
) -> None:
    result = synthesis_contract["synthesis"]
    model = result.partial_build_result.model
    initial_id = synthesis_contract["observed_by_ground"][synthesis_contract["initial"]].state_id
    missing_id = synthesis_contract["observed_by_ground"][synthesis_contract["extra"]].state_id
    model.validate_registered_support((initial_id,))
    model.validate_registered_support((missing_id,))
    assert model.semantics_horizon_cap >= 3
    initial = tuple(item for item in model.semantic_realizations if item.state_id == initial_id)
    assert sorted((len(item.support_ground_row_ids), item.ambiguity.unknown_mass) for item in initial) == [
        (1, Fraction(0)),
        (2, Fraction(0)),
    ]
    missing = tuple(item for item in model.semantic_realizations if item.state_id == missing_id)
    assert len(missing) == 1
    assert len(missing[0].support_ground_row_ids) == 4
    assert missing[0].observed_ground_row_ids == ()
    assert len(missing[0].missing_ground_row_ids) == 4
    assert missing[0].ambiguity.unknown_mass == 1


def test_sample_tax_telemetry_remains_nonblocking_and_makes_no_saving_claim(
    synthesis_contract,
) -> None:
    telemetry = synthesis_contract["synthesis"].telemetry
    assert telemetry.new_environment_interactions_during_synthesis == 0
    assert telemetry.new_generative_oracle_samples_during_synthesis == 0
    assert telemetry.new_exact_kernel_queries_during_synthesis == 0
    assert telemetry.new_synthetic_model_rollouts_during_synthesis == 0
    assert telemetry.query_inputs_during_synthesis == 0
    document = telemetry.to_document()
    assert document["sample_efficiency_gate_status"] == "NOT_RUN"
    assert document["sample_efficiency_gate_blocks_mainline"] is False
    assert synthesis_contract["synthesis"].certificate.sample_efficiency_claimed is False

def test_separately_named_cap_control_publishes_no_model_or_certificate(
    synthesis_contract,
) -> None:
    outcome = synthesize_observed_lmb_partial_rapm_cap_control_v1(
        synthesis_contract["log"],
        synthesis_contract["profile"],
        synthesis_contract["authority"],
        candidate_cap=4095,
    )
    assert outcome.status == "CANDIDATE_CAP_EXHAUSTED"
    assert outcome.required_candidate_count == 4096
    assert outcome.evaluated_candidate_count == 0
    assert outcome.production_certificate_published is False
    assert outcome.model_id is None
    assert outcome.certificate_id is None
