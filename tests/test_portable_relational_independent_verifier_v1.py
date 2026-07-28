from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

import acfqp.portable_relational_skeleton_v1 as producer
from acfqp.portable_relational_independent_verifier_v1 import (
    PortableRelationalIndependentVerificationFailure,
    SUCCESS_STATUS,
    verify_portable_relational_source_documents_v1,
)
from acfqp.portable_relational_skeleton_v1 import (
    AnonymousRelationalObservationLogV1,
    PortableRelationalRoleSchemaV1,
    RelationalActionSlotV1,
    RelationalObservedRowV1,
    RelationalOutcomeIRV1,
    RelationalStateIRV1,
)


CONTEXT_ID = "1" * 64
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
                RelationalActionSlotV1(key, anchor)
                for key, anchor in specifications
            ),
            key=lambda item: item.action_slot_id,
        )
    )


def _active_state(
    resource_count: int,
    active_count: int,
    action_specs: tuple[tuple[str, int], ...],
    linked_pairs: tuple[tuple[int, int], ...],
) -> RelationalStateIRV1:
    return RelationalStateIRV1(
        CONTEXT_ID,
        1,
        tuple(range(resource_count)),
        tuple(range(active_count)),
        tuple(sorted(linked_pairs)),
        _actions(action_specs),
    )


def _terminal_state(resource_count: int) -> RelationalStateIRV1:
    return RelationalStateIRV1(
        CONTEXT_ID,
        0,
        tuple(range(resource_count)),
        (),
        (),
        (),
        "SUCCESS",
    )


def _frozen_documents() -> tuple[dict[str, object], dict[str, object]]:
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
            resource_count,
            active_count,
            action_specs,
            linked_pairs,
        )
        for action in state.legal_actions:
            active_link_count = sum(
                relation_anchor == action.anchor
                and relation_resource in state.active_resources
                for relation_anchor, relation_resource in state.linked_pairs
            )
            reward = {
                (2, 1): Fraction(0),
                (2, 2): Fraction(1),
                (1, 1): Fraction(1),
            }[(len(state.legal_actions), active_link_count)]
            outcome = RelationalOutcomeIRV1(
                _terminal_state(resource_count),
                Fraction(1),
                reward,
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
    log = AnonymousRelationalObservationLogV1(
        PortableRelationalRoleSchemaV1(),
        tuple(sorted(rows, key=lambda item: item.observed_row_id)),
    )
    skeleton = producer.synthesize_portable_relational_skeleton_v1(log)
    return log.to_document(), skeleton.to_document()


def test_independent_verifier_reconstructs_complete_selection() -> None:
    log_document, skeleton_document = _frozen_documents()
    verification = verify_portable_relational_source_documents_v1(
        log_document,
        skeleton_document,
    )
    assert verification.status == SUCCESS_STATUS
    assert verification.independent_implementation is True
    assert verification.producer_imported is False
    assert verification.syntactic_program_count == 86
    assert verification.semantic_program_count_by_depth == (5, 7, 11)
    assert verification.evaluated_candidate_count == 10
    assert verification.admissible_candidate_count == 5
    assert verification.selected_state_program == EXPECTED_STATE_PROGRAM
    assert verification.selected_action_program == EXPECTED_ACTION_PROGRAM
    assert verification.source_observation_log_id == (
        log_document["observation_log_id"]
    )
    assert verification.skeleton_id == skeleton_document["skeleton_id"]
    assert len(verification.verification_id) == 64


def test_verifier_source_has_a_static_import_disjoint_boundary() -> None:
    module_path = (
        Path(__file__).parents[1]
        / "src"
        / "acfqp"
        / "portable_relational_independent_verifier_v1.py"
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
    assert "acfqp.portable_relational_skeleton_v1" not in imported_modules
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


def test_frozen_documents_verify_when_every_producer_entry_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_document, skeleton_document = _frozen_documents()

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("independent verifier called producer code")

    for name in (
        "synthesize_portable_relational_skeleton_v1",
        "generate_portable_relational_program_registry_v1",
        "syntactic_portable_program_closure_v1",
        "evaluate_portable_state_program_v1",
        "evaluate_portable_action_program_v1",
    ):
        monkeypatch.setattr(producer, name, forbidden)
    verification = verify_portable_relational_source_documents_v1(
        log_document,
        skeleton_document,
    )
    assert verification.status == SUCCESS_STATUS


def test_raw_source_tamper_is_rejected_before_semantic_replay() -> None:
    log_document, skeleton_document = _frozen_documents()
    tampered = deepcopy(log_document)
    reward = tampered["rows"][0]["outcomes"][0]["normalized_reward"]
    reward["numerator"] = 1 - reward["numerator"]
    with pytest.raises(
        PortableRelationalIndependentVerificationFailure,
        match="content ID mismatch",
    ):
        verify_portable_relational_source_documents_v1(
            tampered,
            skeleton_document,
        )


def test_proposal_hash_tamper_is_rejected() -> None:
    log_document, skeleton_document = _frozen_documents()
    tampered = deepcopy(skeleton_document)
    original = tampered["skeleton_id"]
    tampered["skeleton_id"] = (
        ("0" if original[0] != "0" else "1") + original[1:]
    )
    with pytest.raises(
        PortableRelationalIndependentVerificationFailure,
        match="content ID mismatch",
    ):
        verify_portable_relational_source_documents_v1(
            log_document,
            tampered,
        )


def test_coherently_resigned_wrong_coordinate_pair_is_rejected() -> None:
    log_document, _ = _frozen_documents()
    # Recreate typed producer objects only to manufacture a fully re-signed
    # attack.  The verifier receives mappings and does not import the producer.
    rows = tuple(
        producer.RelationalObservedRowV1(
            producer.RelationalStateIRV1(
                row["state"]["structural_context_id"],
                row["state"]["remaining_horizon"],
                tuple(row["state"]["resource_attributes"]),
                tuple(row["state"]["active_resources"]),
                tuple(tuple(item) for item in row["state"]["linked_pairs"]),
                tuple(
                    producer.RelationalActionSlotV1(
                        item["opaque_action_key"],
                        item["anchor"],
                    )
                    for item in row["state"]["legal_actions"]
                ),
                row["state"]["terminal_kind"],
            ),
            producer.RelationalActionSlotV1(
                row["action"]["opaque_action_key"],
                row["action"]["anchor"],
            ),
            tuple(
                producer.RelationalOutcomeIRV1(
                    producer.RelationalStateIRV1(
                        outcome["next_state"]["structural_context_id"],
                        outcome["next_state"]["remaining_horizon"],
                        tuple(outcome["next_state"]["resource_attributes"]),
                        tuple(outcome["next_state"]["active_resources"]),
                        tuple(
                            tuple(item)
                            for item in outcome["next_state"]["linked_pairs"]
                        ),
                        (),
                        outcome["next_state"]["terminal_kind"],
                    ),
                    Fraction(
                        outcome["probability"]["numerator"],
                        outcome["probability"]["denominator"],
                    ),
                    Fraction(
                        outcome["normalized_reward"]["numerator"],
                        outcome["normalized_reward"]["denominator"],
                    ),
                    outcome["failure"],
                    outcome["terminal"],
                )
                for outcome in row["outcomes"]
            ),
        )
        for row in log_document["rows"]
    )
    typed_log = producer.AnonymousRelationalObservationLogV1(
        producer.PortableRelationalRoleSchemaV1(),
        rows,
    )
    canonical = producer.synthesize_portable_relational_skeleton_v1(
        typed_log
    )
    registry = producer.generate_portable_relational_program_registry_v1(
        typed_log
    )
    wrong_state_program = next(
        item
        for item in registry.programs
        if item.rendered == "cardinality_resources(active_resources)"
    )
    forged = replace(
        canonical,
        state_program=wrong_state_program,
    ).to_document()
    # Every nested AST and the top-level skeleton hash are coherent.
    assert forged["skeleton_id"] != canonical.skeleton_id
    with pytest.raises(
        PortableRelationalIndependentVerificationFailure,
        match="not the exact selected coordinate pair",
    ):
        verify_portable_relational_source_documents_v1(
            typed_log.to_document(),
            forged,
        )


def test_noncanonical_or_open_mappings_fail_closed() -> None:
    log_document, skeleton_document = _frozen_documents()
    extra = deepcopy(skeleton_document)
    extra["unexpected"] = True
    with pytest.raises(
        PortableRelationalIndependentVerificationFailure,
        match="closed mapping",
    ):
        verify_portable_relational_source_documents_v1(
            log_document,
            extra,
        )

    class MappingSubstitution(dict[str, object]):
        pass

    with pytest.raises(
        PortableRelationalIndependentVerificationFailure,
        match="closed mapping",
    ):
        verify_portable_relational_source_documents_v1(
            MappingSubstitution(log_document),
            skeleton_document,
        )
