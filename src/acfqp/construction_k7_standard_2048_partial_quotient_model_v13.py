"""Source-only partial quotient dynamics for an observation-derived 2048 basis.

The model stores only transition conditions observed in the source archive.
Validation rows audit covered conditions but never add rows.  Missing
conditions and all unobserved mass remain explicit; consequently this model is
guidance for planning and acquisition, not a sound certificate authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_coordinate_basis_v13 as basis_v13
from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as prereg_v13
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "13.0.0"
PROFILE_KEY = "construction_k7_standard_2048_partial_quotient_model_v13"
PARTIAL_QUOTIENT_MODEL_ID = "9534055b61a93984f8066e3eee2dc0018847c6b3ca4c946ac731ab86ef94f081"


class ConstructionK7Standard2048PartialQuotientModelV13Error(ValueError):
    """The selected basis, source-only rows, or held-out audit changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048PartialQuotientModelV13Error(message)


def _transition_documents(row: dict[str, Any], keys: tuple[str, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    state, action, cell, rank, successor, merge_score = basis_v13._normalized_transition(row)
    condition = {
        "coordinate": [basis_v13._coordinate_value(key, state) for key in keys],
        "action": action,
        "spawned_cell_in_canonical_prestate_frame": cell,
        "spawned_rank": rank,
    }
    result = {
        "successor_coordinate": [
            basis_v13._coordinate_value(key, successor) for key in keys
        ],
        "successor_status": successor.status.value,
        "merge_score": merge_score,
    }
    return condition, result


def _model_document(
    basis: basis_v13.Standard2048CoordinateBasisEvidenceV13,
) -> dict[str, Any]:
    basis_v13.verify_standard_2048_coordinate_basis_v13(basis)
    evidence = basis.to_document()
    basis_document = evidence["basis"]
    if basis_document["heldout_validation_passed"] is not True:
        _fail("negative coordinate synthesis cannot construct a positive model")
    keys = tuple(basis_document["selected_candidate_keys"])
    if keys != basis_v13.SELECTED_COORDINATE_KEYS:
        _fail("selected coordinate basis changed")

    grouped: dict[bytes, dict[str, Any]] = {}
    for row in evidence["source_archive"]["rows"]:
        condition, result = _transition_documents(row, keys)
        condition_bytes = canonical_json_bytes(condition)
        result_bytes = canonical_json_bytes(result)
        existing = grouped.get(condition_bytes)
        if existing is None:
            grouped[condition_bytes] = {
                "condition": condition,
                "observed_result": result,
                "source_observation_indices": [row["observation_index"]],
            }
        else:
            if canonical_json_bytes(existing["observed_result"]) != result_bytes:
                _fail("source-selected basis contains a transition contradiction")
            existing["source_observation_indices"].append(row["observation_index"])

    rows: list[dict[str, Any]] = []
    for ordinal, condition_bytes in enumerate(sorted(grouped)):
        row = grouped[condition_bytes]
        row_payload = {
            "row_ordinal": ordinal,
            "condition": row["condition"],
            "observed_result": row["observed_result"],
            "source_observation_indices": row["source_observation_indices"],
            "source_observation_count": len(row["source_observation_indices"]),
            "unobserved_successor_mass_retained_as_unknown": True,
            "probability_assignment_present": False,
            "sound_certificate_authority_present": False,
        }
        rows.append(row_payload)

    covered_validation = 0
    matching_validation = 0
    conflicting_validation = 0
    for row in evidence["validation_archive"]["rows"]:
        condition, result = _transition_documents(row, keys)
        existing = grouped.get(canonical_json_bytes(condition))
        if existing is None:
            continue
        covered_validation += 1
        if canonical_json_bytes(existing["observed_result"]) == canonical_json_bytes(result):
            matching_validation += 1
        else:
            conflicting_validation += 1

    unique_coordinates = {
        canonical_json_bytes(row["condition"]["coordinate"]) for row in rows
    }
    source_observation_count = len(evidence["source_archive"]["rows"])
    validation_observation_count = len(evidence["validation_archive"]["rows"])
    payload = {
        "schema": "acfqp.standard_2048_partial_quotient_model.v13",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "coordinate_preregistration_id": prereg_v13.PREREGISTRATION_ID,
        "coordinate_basis_id": basis.coordinate_basis_id,
        "source_observation_archive_id": basis.source_archive_id,
        "validation_observation_archive_id": basis.validation_archive_id,
        "selected_candidate_keys": list(keys),
        "row_condition_schema": [
            "coordinate",
            "action",
            "spawned_cell_in_canonical_prestate_frame",
            "spawned_rank",
        ],
        "rows": rows,
        "partial_row_count": len(rows),
        "represented_coordinate_count": len(unique_coordinates),
        "source_observation_count": source_observation_count,
        "source_duplicate_condition_observation_count": (
            source_observation_count - len(rows)
        ),
        "source_transition_congruence_contradiction_count": 0,
        "validation_observation_count": validation_observation_count,
        "validation_covered_condition_count": covered_validation,
        "validation_matching_covered_condition_count": matching_validation,
        "validation_conflicting_covered_condition_count": conflicting_validation,
        "validation_uncovered_condition_count": (
            validation_observation_count - covered_validation
        ),
        "validation_coverage_fraction": {
            "numerator": covered_validation,
            "denominator": validation_observation_count,
        },
        "source_rows_only_construct_model": True,
        "validation_rows_added_to_model": False,
        "target_episode_or_reward_value_policy_read_during_construction": False,
        "unknown_conditions_retained_as_unknown": True,
        "unobserved_successor_mass_retained_as_unknown": True,
        "model_can_guide_planning_and_acquisition": True,
        "model_can_issue_sound_plan_certificate": False,
        "exact_local_obligation_closure_still_required": True,
        "finite_heldout_coverage_is_not_global_lumpability": True,
        "target_execution_performed": False,
        "local_ground_refinement_performed": False,
        "sample_tax_reduction_claimed": False,
        "broad_world_model_synthesis_claimed": False,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    return {
        **payload,
        "partial_quotient_model_id": content_id(
            prereg_v13.FUTURE_DOMAINS["partial_model"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048PartialQuotientModelV13:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    partial_quotient_model_id: str
    coordinate_basis_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("partial quotient model is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("partial_quotient_model_id")
            != self.partial_quotient_model_id
            or document.get("coordinate_basis_id") != self.coordinate_basis_id
        ):
            _fail("partial quotient model bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "partial_quotient_model_id"
        }
        if content_id(prereg_v13.FUTURE_DOMAINS["partial_model"], payload) != self.partial_quotient_model_id:
            _fail("partial quotient model identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("partial quotient model is not an object")
        return document


def build_standard_2048_partial_quotient_model_v13(
    basis: basis_v13.Standard2048CoordinateBasisEvidenceV13 | None = None,
) -> Standard2048PartialQuotientModelV13:
    if basis is None:
        basis = basis_v13.build_standard_2048_coordinate_basis_v13()
    document = _model_document(basis)
    if document["partial_quotient_model_id"] != PARTIAL_QUOTIENT_MODEL_ID:
        _fail("frozen partial quotient model identity changed")
    return Standard2048PartialQuotientModelV13(
        _ISSUER,
        canonical_json_bytes(document),
        document["partial_quotient_model_id"],
        document["coordinate_basis_id"],
    )


def verify_standard_2048_partial_quotient_model_v13(
    model: Standard2048PartialQuotientModelV13,
) -> Standard2048PartialQuotientModelV13:
    if type(model) is not Standard2048PartialQuotientModelV13:
        _fail("partial quotient model verifier rejects foreign values")
    model.__post_init__()
    expected = build_standard_2048_partial_quotient_model_v13()
    if model.canonical_bytes != expected.canonical_bytes:
        _fail("partial quotient model differs from source-only replay")
    return model


__all__ = (
    "ConstructionK7Standard2048PartialQuotientModelV13Error",
    "PROFILE_KEY",
    "PARTIAL_QUOTIENT_MODEL_ID",
    "SCHEMA_VERSION",
    "Standard2048PartialQuotientModelV13",
    "build_standard_2048_partial_quotient_model_v13",
    "verify_standard_2048_partial_quotient_model_v13",
)
