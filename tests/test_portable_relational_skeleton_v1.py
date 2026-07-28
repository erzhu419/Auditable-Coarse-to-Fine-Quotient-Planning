from __future__ import annotations

import ast
from collections import Counter
from dataclasses import replace
from fractions import Fraction
import inspect
import json
from pathlib import Path

import pytest

from acfqp.portable_relational_skeleton_v1 import (
    AnonymousRelationalObservationLogV1,
    FailedRelationalProofRefV1,
    PortableRelationalInvariantViolation,
    PortableRelationalProgramV1,
    PortableRelationalRoleSchemaV1,
    PortableRelationalSkeletonV1,
    RelationalActionSlotV1,
    RelationalObservedRowV1,
    RelationalOutcomeIRV1,
    RelationalProgramContext,
    RelationalProgramType,
    RelationalStateIRV1,
    evaluate_portable_action_program_v1,
    evaluate_portable_state_program_v1,
    generate_portable_relational_program_registry_v1,
    generate_target_relational_programs_v1,
    portable_relational_synthesis_metrics_v1,
    synthesize_portable_relational_skeleton_v1,
    syntactic_portable_program_closure_v1,
    verify_portable_relational_skeleton_v1,
)


SOURCE_CONTEXT_ID = "1" * 64
TARGET_CONTEXT_ID = "2" * 64
MODEL_EPOCH_ID = "3" * 64
FAILED_AUDIT_ID = "4" * 64

EXPECTED_STATE_PROGRAM = "cardinality_actions(legal_actions)"
EXPECTED_ACTION_PROGRAM = (
    "cardinality_resources("
    "linked_filter(action_anchor,active_resources))"
)


def _actions(
    specifications: tuple[tuple[str, int], ...],
) -> tuple[RelationalActionSlotV1, ...]:
    return tuple(
        sorted(
            (
                RelationalActionSlotV1(action_key, anchor)
                for action_key, anchor in specifications
            ),
            key=lambda item: item.action_slot_id,
        )
    )


def _active_state(
    *,
    context_id: str,
    resource_count: int,
    active_count: int,
    action_specs: tuple[tuple[str, int], ...],
    linked_pairs: tuple[tuple[int, int], ...],
) -> RelationalStateIRV1:
    return RelationalStateIRV1(
        context_id,
        1,
        tuple(range(resource_count)),
        tuple(range(active_count)),
        tuple(sorted(linked_pairs)),
        _actions(action_specs),
    )


def _terminal_state(
    *,
    context_id: str,
    resource_count: int,
) -> RelationalStateIRV1:
    return RelationalStateIRV1(
        context_id,
        0,
        tuple(range(resource_count)),
        (),
        (),
        (),
        "SUCCESS",
    )


def _anonymous_log(
    context_id: str = SOURCE_CONTEXT_ID,
) -> AnonymousRelationalObservationLogV1:
    """A domain-free exact log with one uniquely best coordinate pair."""

    specifications = (
        (
            5,
            3,
            (("a0", 0), ("a1", 1)),
            ((0, 1), (0, 3), (1, 0), (1, 2), (1, 3)),
        ),
        (
            6,
            4,
            (("b0", 0), ("b1", 1)),
            ((0, 1), (1, 0), (1, 2), (1, 4), (1, 5)),
        ),
        (
            5,
            3,
            (("c0", 0),),
            ((0, 1), (0, 3)),
        ),
        (
            6,
            4,
            (("d0", 0),),
            ((0, 1), (0, 4), (0, 5)),
        ),
    )
    rows: list[RelationalObservedRowV1] = []
    for resource_count, active_count, action_specs, linked_pairs in specifications:
        state = _active_state(
            context_id=context_id,
            resource_count=resource_count,
            active_count=active_count,
            action_specs=action_specs,
            linked_pairs=linked_pairs,
        )
        for action in state.legal_actions:
            active_link_count = sum(
                relation_anchor == action.anchor
                and relation_resource in state.active_resources
                for relation_anchor, relation_resource in state.linked_pairs
            )
            normalized_reward = {
                (2, 1): Fraction(0),
                (2, 2): Fraction(1),
                (1, 1): Fraction(1),
            }[(len(state.legal_actions), active_link_count)]
            outcome = RelationalOutcomeIRV1(
                _terminal_state(
                    context_id=context_id,
                    resource_count=resource_count,
                ),
                Fraction(1),
                normalized_reward,
                False,
                True,
            )
            rows.append(
                RelationalObservedRowV1(
                    state,
                    action,
                    (outcome,),
                )
            )
    return AnonymousRelationalObservationLogV1(
        PortableRelationalRoleSchemaV1(),
        tuple(sorted(rows, key=lambda item: item.observed_row_id)),
    )


def _renamed_state(
    state: RelationalStateIRV1,
) -> RelationalStateIRV1:
    resource_count = len(state.resource_attributes)
    permutation = {
        resource: resource_count - 1 - resource
        for resource in range(resource_count)
    }
    attributes = [0] * resource_count
    for old_resource, attribute in enumerate(state.resource_attributes):
        attributes[permutation[old_resource]] = attribute
    actions = tuple(
        sorted(
            (
                RelationalActionSlotV1(
                    f"renamed:{item.opaque_action_key}",
                    permutation[item.anchor],
                )
                for item in state.legal_actions
            ),
            key=lambda item: item.action_slot_id,
        )
    )
    return RelationalStateIRV1(
        state.structural_context_id,
        state.remaining_horizon,
        tuple(attributes),
        tuple(sorted(permutation[item] for item in state.active_resources)),
        tuple(
            sorted(
                (
                    permutation[relation_anchor],
                    permutation[relation_resource],
                )
                for relation_anchor, relation_resource in state.linked_pairs
            )
        ),
        actions,
        state.terminal_kind,
    )


def _permuted_log(
    log: AnonymousRelationalObservationLogV1,
) -> AnonymousRelationalObservationLogV1:
    state_cache: dict[str, RelationalStateIRV1] = {}

    def renamed(state: RelationalStateIRV1) -> RelationalStateIRV1:
        return state_cache.setdefault(state.state_ir_id, _renamed_state(state))

    rows: list[RelationalObservedRowV1] = []
    for row in log.rows:
        state = renamed(row.state)
        action = next(
            item
            for item in state.legal_actions
            if item.opaque_action_key
            == f"renamed:{row.action.opaque_action_key}"
        )
        outcomes = tuple(
            sorted(
                (
                    RelationalOutcomeIRV1(
                        renamed(item.next_state),
                        item.probability,
                        item.normalized_reward,
                        item.failure,
                        item.terminal,
                    )
                    for item in row.outcomes
                ),
                key=lambda item: item.outcome_ir_id,
            )
        )
        rows.append(RelationalObservedRowV1(state, action, outcomes))
    return AnonymousRelationalObservationLogV1(
        log.role_schema,
        tuple(sorted(rows, key=lambda item: item.observed_row_id)),
    )


def _semantic_values(
    program: PortableRelationalProgramV1,
    log: AnonymousRelationalObservationLogV1,
) -> tuple[object, ...]:
    if program.context is RelationalProgramContext.STATE:
        states = {
            row.state.state_ir_id: row.state
            for row in log.rows
        }
        for row in log.rows:
            for outcome in row.outcomes:
                states[outcome.next_state.state_ir_id] = outcome.next_state
        return tuple(
            evaluate_portable_state_program_v1(program, state)
            for _, state in sorted(states.items())
        )
    return tuple(
        evaluate_portable_action_program_v1(
            program,
            row.state,
            row.action,
        )
        for row in log.rows
    )


def test_portable_module_has_no_domain_or_campaign_import() -> None:
    module_path = (
        Path(__file__).parents[1]
        / "src"
        / "acfqp"
        / "portable_relational_skeleton_v1.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(
        forbidden in module_name
        for module_name in imported_modules
        for forbidden in (
            "acfqp.domains",
            "graph",
            "matching",
            "campaign",
        )
    )
    assert tuple(
        inspect.signature(
            synthesize_portable_relational_skeleton_v1
        ).parameters
    ) == ("source_log",)


def test_depth_two_syntactic_closure_is_complete_and_deterministic() -> None:
    programs = syntactic_portable_program_closure_v1()
    assert len(programs) == 86
    assert Counter(item.depth for item in programs) == {
        0: 5,
        1: 9,
        2: 72,
    }
    assert len({item.program_id for item in programs}) == len(programs)
    assert all(item.depth <= 2 for item in programs)
    rendered = {item.rendered for item in programs}
    assert EXPECTED_STATE_PROGRAM in rendered
    assert EXPECTED_ACTION_PROGRAM in rendered


def test_semantic_registry_deduplicates_complete_closure() -> None:
    log = _anonymous_log()
    registry = generate_portable_relational_program_registry_v1(log)
    assert registry.syntactic_program_count == 86
    assert len(registry.programs) == 23
    assert registry.semantic_program_count_by_depth == (5, 7, 11)
    signatures = {
        (
            item.context,
            item.result_type,
            _semantic_values(item, log),
        )
        for item in registry.programs
    }
    assert len(signatures) == len(registry.programs)
    assert len(registry.programs) < registry.syntactic_program_count


def test_source_only_search_selects_required_relational_coordinates() -> None:
    log = _anonymous_log()
    skeleton = synthesize_portable_relational_skeleton_v1(log)
    metrics = portable_relational_synthesis_metrics_v1(log, skeleton)
    assert skeleton.state_program.rendered == EXPECTED_STATE_PROGRAM
    assert skeleton.action_program.rendered == EXPECTED_ACTION_PROGRAM
    assert metrics.syntactic_program_count == 86
    assert metrics.semantic_program_count_by_depth == (5, 7, 11)
    assert metrics.state_integer_program_count == 5
    assert metrics.action_integer_program_count == 2
    assert metrics.evaluated_candidate_count == 10
    assert metrics.admissible_candidate_count > 1
    assert (
        metrics.ground_state_count,
        metrics.ground_row_count,
        metrics.abstract_state_count,
        metrics.abstract_support_count,
    ) == (4, 6, 2, 3)
    assert metrics.transition_alias_width == 0
    assert metrics.reward_alias_width == 0
    assert verify_portable_relational_skeleton_v1(log, skeleton)


def test_exported_skeleton_contains_only_ast_schema_and_provenance() -> None:
    document = synthesize_portable_relational_skeleton_v1(
        _anonymous_log()
    ).to_document()
    assert set(document) == {
        "schema",
        "schema_version",
        "profile_key",
        "role_schema_id",
        "source_observation_log_id",
        "state_program",
        "action_program",
        "support_schema",
        "skeleton_id",
    }
    encoded = json.dumps(document, sort_keys=True).lower()
    for forbidden in (
        "dynamics",
        "outcome",
        "reward",
        "failure",
        "policy",
        "target",
        "query",
        "optional",
        "registry",
    ):
        assert forbidden not in encoded


def test_resource_and_action_renaming_preserve_selected_programs() -> None:
    log = _anonymous_log()
    renamed_log = _permuted_log(log)
    original = synthesize_portable_relational_skeleton_v1(log)
    renamed = synthesize_portable_relational_skeleton_v1(renamed_log)
    original_metrics = portable_relational_synthesis_metrics_v1(log, original)
    renamed_metrics = portable_relational_synthesis_metrics_v1(
        renamed_log,
        renamed,
    )
    assert renamed_log.observation_log_id != log.observation_log_id
    assert renamed.skeleton_id != original.skeleton_id
    assert renamed.state_program.program_id == original.state_program.program_id
    assert renamed.action_program.program_id == original.action_program.program_id
    assert (
        renamed_metrics.syntactic_program_count,
        renamed_metrics.semantic_program_count_by_depth,
        renamed_metrics.evaluated_candidate_count,
        renamed_metrics.admissible_candidate_count,
        renamed_metrics.abstract_state_count,
        renamed_metrics.abstract_support_count,
        renamed_metrics.transition_alias_width,
        renamed_metrics.reward_alias_width,
    ) == (
        original_metrics.syntactic_program_count,
        original_metrics.semantic_program_count_by_depth,
        original_metrics.evaluated_candidate_count,
        original_metrics.admissible_candidate_count,
        original_metrics.abstract_state_count,
        original_metrics.abstract_support_count,
        original_metrics.transition_alias_width,
        original_metrics.reward_alias_width,
    )


def test_source_synthesis_rejects_incomplete_action_row_coverage() -> None:
    complete = _anonymous_log()
    incomplete = AnonymousRelationalObservationLogV1(
        complete.role_schema,
        complete.rows[:-1],
    )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="complete exact action-row coverage",
    ):
        synthesize_portable_relational_skeleton_v1(incomplete)


def test_semantic_tamper_fails_complete_source_replay() -> None:
    log = _anonymous_log()
    skeleton = synthesize_portable_relational_skeleton_v1(log)
    registry = generate_portable_relational_program_registry_v1(log)
    alternative_state_program = next(
        item
        for item in registry.programs
        if item.rendered == "cardinality_resources(active_resources)"
    )
    forged = replace(skeleton, state_program=alternative_state_program)
    assert forged.skeleton_id != skeleton.skeleton_id
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="complete source replay",
    ):
        verify_portable_relational_skeleton_v1(log, forged)


def test_runtime_substitutions_and_invalid_relations_fail_closed() -> None:
    class ActionSubstitution(RelationalActionSlotV1):
        pass

    class ProgramSubstitution(PortableRelationalProgramV1):
        pass

    substituted_action = ActionSubstitution("substituted", 0)
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="state IR is invalid",
    ):
        RelationalStateIRV1(
            SOURCE_CONTEXT_ID,
            1,
            (0, 1),
            (0,),
            ((0, 1),),
            (substituted_action,),
        )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="state IR is invalid",
    ):
        RelationalStateIRV1(
            SOURCE_CONTEXT_ID,
            1,
            (0, 1),
            (0,),
            ((2, 1),),
            _actions((("a", 0),)),
        )

    skeleton = synthesize_portable_relational_skeleton_v1(_anonymous_log())
    substituted_program = ProgramSubstitution(
        skeleton.state_program.operation,
        skeleton.state_program.result_type,
        skeleton.state_program.context,
        skeleton.state_program.arguments,
    )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="source-only boundary",
    ):
        replace(skeleton, state_program=substituted_program)


def test_outcome_order_and_exact_runtime_types_are_canonical() -> None:
    state = _active_state(
        context_id=SOURCE_CONTEXT_ID,
        resource_count=3,
        active_count=2,
        action_specs=(("a", 0),),
        linked_pairs=((0, 1),),
    )
    success = RelationalOutcomeIRV1(
        _terminal_state(
            context_id=SOURCE_CONTEXT_ID,
            resource_count=3,
        ),
        Fraction(1, 2),
        Fraction(1),
        False,
        True,
    )
    failed_state = RelationalStateIRV1(
        SOURCE_CONTEXT_ID,
        0,
        (0, 1, 2),
        (),
        (),
        (),
        "FAILURE",
    )
    failure = RelationalOutcomeIRV1(
        failed_state,
        Fraction(1, 2),
        Fraction(0),
        True,
        True,
    )
    reversed_outcomes = tuple(
        reversed(
            sorted(
                (success, failure),
                key=lambda item: item.outcome_ir_id,
            )
        )
    )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="observed row is invalid",
    ):
        RelationalObservedRowV1(
            state,
            state.legal_actions[0],
            reversed_outcomes,
        )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="outcome IR is invalid",
    ):
        RelationalOutcomeIRV1(
            failed_state,
            1,  # type: ignore[arg-type]
            Fraction(0),
            True,
            True,
        )


def test_target_closure_is_fresh_and_has_no_source_registry_parameter() -> None:
    source_log = _anonymous_log()
    target_log = _anonymous_log(TARGET_CONTEXT_ID)
    skeleton = synthesize_portable_relational_skeleton_v1(source_log)
    failed_proof = FailedRelationalProofRefV1(
        TARGET_CONTEXT_ID,
        MODEL_EPOCH_ID,
        FAILED_AUDIT_ID,
        "ALIAS_WIDTH",
    )
    signature = inspect.signature(generate_target_relational_programs_v1)
    assert tuple(signature.parameters) == (
        "skeleton",
        "failed_proof",
        "authorized_target_log",
    )
    assert all(
        "source_registry" not in name
        for name in signature.parameters
    )
    generation = generate_target_relational_programs_v1(
        skeleton,
        failed_proof,
        target_log,
    )
    source_registry = generate_portable_relational_program_registry_v1(
        source_log
    )
    assert generation.registry.observation_log_id == (
        target_log.observation_log_id
    )
    assert generation.registry.registry_id != source_registry.registry_id
    assert generation.source_registry_access_count == 0
    assert generation.source_candidate_metric_access_count == 0
    assert generation.primitive_invention_count == 0
    assert generation.target_program_generation_count == 86
    assert set(generation.generated_program_ids) == {
        item.program_id for item in generation.registry.programs
    }


def test_target_generation_rejects_source_reuse_and_cross_context_rows() -> None:
    source_log = _anonymous_log()
    skeleton = synthesize_portable_relational_skeleton_v1(source_log)
    failed_proof = FailedRelationalProofRefV1(
        SOURCE_CONTEXT_ID,
        MODEL_EPOCH_ID,
        FAILED_AUDIT_ID,
        "RISK_OR_REGRET",
    )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="binding is invalid",
    ):
        generate_target_relational_programs_v1(
            skeleton,
            failed_proof,
            source_log,
        )

    target_log = _anonymous_log(TARGET_CONTEXT_ID)
    mixed_rows = tuple(
        sorted(
            (source_log.rows[0], *target_log.rows),
            key=lambda item: item.observed_row_id,
        )
    )
    mixed_log = AnonymousRelationalObservationLogV1(
        target_log.role_schema,
        mixed_rows,
    )
    target_failed_proof = replace(
        failed_proof,
        target_context_id=TARGET_CONTEXT_ID,
    )
    with pytest.raises(
        PortableRelationalInvariantViolation,
        match="binding is invalid",
    ):
        generate_target_relational_programs_v1(
            skeleton,
            target_failed_proof,
            mixed_log,
        )
