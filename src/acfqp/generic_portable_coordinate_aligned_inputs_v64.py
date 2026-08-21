"""Reconstruct coordinate-aligned planner inputs from portable observation bytes."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_coordinate_alignment_v60 import aligned_source_views_v60
from acfqp.generic_layout_factorized_world_model_v5 import DiscoveredLayoutV5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


_PROJECTED_CANDIDATE_DOMAIN = b"acfqp:generic-coordinate-aligned-candidate:v60\x00"


class GenericPortableCoordinateAlignedInputsV64Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPortableCoordinateAlignedInputsV64Error(message)


def _layout(document: Any) -> DiscoveredLayoutV5:
    if type(document) is not dict:
        _fail("V64 portable layout changed")
    required = {
        "schema",
        "state_canonical_to_raw",
        "action_canonical_to_raw",
        "state_structural_colors",
        "action_structural_colors",
        "schema_signature",
        "refinement_rounds",
        "relation_evaluations",
        "reference_layout_id",
        "graph_edit_score",
        "cross_occurrence_value_overlap",
        "semantic_names_available",
        "predeclared_layout_or_factor_roles",
        "layout_id",
    }
    if (
        set(document) != required
        or document.get("schema") != "acfqp.generic_layout_factorization.v5"
        or document.get("semantic_names_available") is not False
        or document.get("predeclared_layout_or_factor_roles") != []
    ):
        _fail("V64 portable layout schema changed")
    result = DiscoveredLayoutV5(
        tuple(document["state_canonical_to_raw"]),
        tuple(document["action_canonical_to_raw"]),
        tuple(document["state_structural_colors"]),
        tuple(document["action_structural_colors"]),
        document["schema_signature"],
        document["refinement_rounds"],
        document["relation_evaluations"],
        document["layout_id"],
        document["reference_layout_id"],
        document["graph_edit_score"],
        document["cross_occurrence_value_overlap"],
    )
    if result.to_document() != document:
        _fail("V64 portable layout reconstruction diverged")
    return result


def _actions(documents: Any) -> tuple[FlatRawActionV4, ...]:
    if type(documents) is not list or not documents:
        _fail("V64 portable action catalogue changed")
    result = tuple(
        FlatRawActionV4(row["action_key"], tuple(row["anonymous_fields"]))
        for row in documents
        if type(row) is dict
        and set(row) == {"action_key", "anonymous_fields"}
    )
    if (
        len(result) != len(documents)
        or tuple(row.key for row in result) != tuple(range(len(result)))
        or [row.to_document() for row in result] != documents
    ):
        _fail("V64 portable action reconstruction diverged")
    return result


def _rows(
    documents: Any, catalogue: tuple[FlatRawActionV4, ...]
) -> tuple[FlatRawTransitionV4, ...]:
    if type(documents) is not list or not documents:
        _fail("V64 portable transition inventory changed")
    result = []
    for document in documents:
        if type(document) is not dict:
            _fail("V64 portable transition changed")
        action_document = document.get("selected_action")
        key = action_document.get("action_key") if type(action_document) is dict else None
        if type(key) is not int or not 0 <= key < len(catalogue):
            _fail("V64 portable selected action changed")
        row = FlatRawTransitionV4(
            document["occurrence"],
            document["transition_index"],
            tuple(document["pre_vector"]),
            tuple(document["legal_action_keys_before"]),
            catalogue[key],
            tuple(document["post_vector"]),
            tuple(document["legal_action_keys_after"]),
            document["terminal_acceptance_after"],
            document["outcome_tape_sha256"],
        )
        if row.to_document() != document:
            _fail("V64 portable transition reconstruction diverged")
        result.append(row)
    return tuple(result)


def reconstruct_coordinate_aligned_planning_inputs_v64(
    model: Mapping[str, Any],
    alignment: Mapping[str, Any],
    target_candidate_document: Mapping[str, Any],
    raw_transition_documents: list[dict[str, Any]],
    raw_action_catalogue_documents: list[dict[str, Any]],
) -> tuple[
    PartialFactorCandidateV15,
    tuple[FlatRawTransitionV4, ...],
    tuple[FlatRawActionV4, ...],
]:
    if (
        type(model) is not dict
        or type(alignment) is not dict
        or type(target_candidate_document) is not dict
        or target_candidate_document.get("schema")
        != "acfqp.generic_partial_factor_candidate.v15"
        or alignment.get("source_model_id")
        != model.get("projected_disagreement_successor_model_id")
        or alignment.get("target_partial_candidate_id")
        != target_candidate_document.get("candidate_id")
    ):
        _fail("V64 portable alignment binding changed")
    catalogue = _actions(raw_action_catalogue_documents)
    rows = _rows(raw_transition_documents, catalogue)
    target_layout = _layout(target_candidate_document.get("layout"))
    target_candidate = PartialFactorCandidateV15(
        target_candidate_document,
        target_layout,
        tuple(target_candidate_document["compiled_factor_assignments"]),
        rows,
    )
    transformed_rows, transformed_catalogue = aligned_source_views_v60(
        alignment, target_candidate, rows, catalogue
    )
    source_layout = model["source_layout"]
    state_width = model["state_width"]
    action_width = model["action_field_width"]
    identity_layout = DiscoveredLayoutV5(
        tuple(range(state_width)),
        tuple(range(action_width)),
        tuple(source_layout["state_structural_colors"]),
        tuple(source_layout["action_structural_colors"]),
        source_layout["schema_signature"],
        source_layout["refinement_rounds"],
        source_layout["relation_evaluations"],
        hashlib.sha256(
            b"acfqp:generic-coordinate-aligned-layout:v60\x00"
            + canonical_json_bytes(
                {
                    "coordinate_alignment_id": alignment["coordinate_alignment_id"],
                    "state_order": list(range(state_width)),
                    "action_order": list(range(action_width)),
                }
            )
        ).hexdigest(),
    )
    payload = {
        "schema": "acfqp.generic_coordinate_aligned_partial_candidate.v60",
        "source_factor_library_id": target_candidate_document[
            "source_factor_library_id"
        ],
        "target_partial_candidate_id": target_candidate_document["candidate_id"],
        "coordinate_alignment_id": alignment["coordinate_alignment_id"],
        "layout": identity_layout.to_document(),
        "state_width": state_width,
        "action_field_width": action_width,
        "compiled_factor_assignments": model["known_partial_factor_assignments"],
        "unknown_residual_target_columns": model["unknown_residual_target_columns"],
        "transformed_observation_count": len(transformed_rows),
        "transformed_observation_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in transformed_rows])
        ).hexdigest(),
        "source_model_refit": False,
        "semantic_names_used": False,
        "planning_authority_present": False,
        "complete_world_model_claimed": False,
    }
    document = {
        **payload,
        "candidate_id": hashlib.sha256(
            _PROJECTED_CANDIDATE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    candidate = PartialFactorCandidateV15(
        document,
        identity_layout,
        tuple(model["known_partial_factor_assignments"]),
        transformed_rows,
    )
    return candidate, transformed_rows, transformed_catalogue


__all__ = ("reconstruct_coordinate_aligned_planning_inputs_v64",)
