"""Compile the V96 failure into a reusable anonymous dependency structure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v97 as domains
from acfqp import construction_k7_persistent_multi_residual_independent_verifier_v96 as v96
from acfqp.generic_post_dependency_residual_v97 import (
    POST_DEPENDENCY_GRAMMAR_V97,
    synthesize_post_dependency_multi_residual_v97,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
EXPECTED_CANONICAL_BYTE_COUNT = 4_521
EXPECTED_CANONICAL_SHA256 = "27d9aeee2e2feb132cb9fc59369a43d9968b7039e3f50f2d17e4c68c042e9450"
V96_VERIFICATION_ID = "ce1a04b45959e2d34d2ad31b8e84630796dc377c24b7190e74f72e8faed20fca"
V96_VERIFICATION_BYTE_COUNT = 1_127
V96_VERIFICATION_SHA256 = "c4aaf1a8ec47d82d1486f00965e7960a06fe46654f8562a1ce730954c43ee722"
_STRUCTURE_LIBRARY_DOMAIN = b"acfqp:post-dependency-structure-library:v97\x00"


class ConstructionK7PostDependencySourceLibraryV97Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PostDependencySourceLibraryV97Error(message)


def _structure_library() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.post_dependency_structure_library.v97",
        "normalized_structure": [
            "PD03",
            ["PD00", "DRIVER_POST_COLUMN"],
            ["PD01", "LOWER_THRESHOLD"],
            ["PD01", "UPPER_THRESHOLD"],
            ["PD02", "FINITE_LEAF_SUPPORTS"],
        ],
        "generic_opcode_inventory": list(POST_DEPENDENCY_GRAMMAR_V97),
        "minimum_source_occurrence_support": 2,
        "source_target_columns_transferred": False,
        "source_driver_columns_transferred": False,
        "source_thresholds_transferred": False,
        "source_leaf_values_transferred": False,
        "target_bindings_must_be_derived_from_target_raw_transitions": True,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "source_library_id": hashlib.sha256(
            _STRUCTURE_LIBRARY_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _document(v96_campaign_raw: bytes, v96_verification_raw: bytes) -> dict[str, Any]:
    if (
        type(v96_verification_raw) is not bytes
        or len(v96_verification_raw) != V96_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v96_verification_raw).hexdigest()
        != V96_VERIFICATION_SHA256
    ):
        _fail("V97 V96 verification predecessor bytes changed")
    verification = loads_canonical_json(v96_verification_raw)
    if (
        verification.get("verification_id") != V96_VERIFICATION_ID
        or verification.get("campaign_id") != v96.CAMPAIGN_ID
        or verification.get("verification_status")
        != "REGISTERED_PERSISTENT_MULTI_RESIDUAL_GATE_FAILURE_VERIFIED"
    ):
        _fail("V97 V96 verification predecessor identity changed")
    v96.verify_persistent_multi_residual_campaign_bytes_v96(v96_campaign_raw)
    campaign = loads_canonical_json(v96_campaign_raw)
    sources = []
    offline_labels = 0
    for occurrence in campaign["target_occurrences"]:
        sequence = occurrence["meta_prior_persistent_sequence"]
        first = sequence["first_online_multi_residual_episode"]
        base = first["final_multi_residual_acquisition"]
        rows = first["raw_local_transition_rows"]
        evidence = {
            "layout": occurrence["meta_prior_partial_acquisition"]["candidate"][
                "layout"
            ],
            "unknown_residual_target_columns": base[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": rows,
        }
        acquisition = synthesize_post_dependency_multi_residual_v97(
            evidence, base, structural_prior_library=None
        )
        candidates = acquisition["retrospective_post_dependency_candidates"]
        if len(candidates) != 1 or acquisition[
            "all_residual_targets_have_compilable_proposals"
        ] is not True:
            _fail("V97 source failure did not expose one dependency completion")
        candidate = candidates[0]
        offline_labels += acquisition["shared_physical_ground_support_labels"]
        sources.append(
            {
                "seed": occurrence["seed"],
                "v96_occurrence_id": occurrence["occurrence_id"],
                "base_multi_residual_acquisition_id": base[
                    "multi_residual_acquisition_id"
                ],
                "raw_transition_row_count": len(rows),
                "raw_transition_sha256": hashlib.sha256(
                    canonical_json_bytes(rows)
                ).hexdigest(),
                "physical_ground_support_labels": acquisition[
                    "shared_physical_ground_support_labels"
                ],
                "dependency_candidate": candidate,
                "target_column": candidate["target_column"],
                "driver_post_column": candidate["driver_post_column"],
                "source_specific_thresholds": [
                    candidate["lower_inclusive_threshold"],
                    candidate["upper_inclusive_threshold"],
                ],
                "source_specific_leaf_supports": candidate["leaf_supports"],
                "source_specific_bindings_not_transferred": True,
            }
        )
    library = _structure_library()
    payload = {
        "schema": "acfqp.post_dependency_source_library_artifact.v97",
        "v96_campaign_id": v96.CAMPAIGN_ID,
        "v96_verification_id": V96_VERIFICATION_ID,
        "source_occurrences": sources,
        "compiled_structure_library": library,
        "source_occurrence_support_count": len(sources),
        "accounting": {
            "offline_source_physical_ground_support_labels": offline_labels,
            "target_labels": 0,
            "source_labels_and_future_target_labels_separate": True,
            "candidate_binding_evaluations": sum(
                synthesize_post_dependency_multi_residual_v97(
                    {
                        "layout": occurrence["meta_prior_partial_acquisition"][
                            "candidate"
                        ]["layout"],
                        "unknown_residual_target_columns": occurrence[
                            "meta_prior_persistent_sequence"
                        ]["first_online_multi_residual_episode"][
                            "final_multi_residual_acquisition"
                        ]["unknown_residual_target_columns"],
                        "raw_transition_rows": occurrence[
                            "meta_prior_persistent_sequence"
                        ]["first_online_multi_residual_episode"][
                            "raw_local_transition_rows"
                        ],
                    },
                    occurrence["meta_prior_persistent_sequence"][
                        "first_online_multi_residual_episode"
                    ]["final_multi_residual_acquisition"],
                    structural_prior_library=None,
                )["post_dependency_candidate_binding_evaluation_count"]
                for occurrence in campaign["target_occurrences"]
            ),
            "planning_compute_events": 0,
            "all_axes_separate": True,
        },
        "evidence_boundary": {
            "source_is_preserved_registered_failure": True,
            "structure_not_column_threshold_or_value_binding_transferred": True,
            "fresh_target_outcomes_observed": False,
            "future_prediction_authority_present": False,
            "proposal_only_not_safety_authority": True,
        },
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "source_library_artifact_id": domains.extension_content_id_v97(
            domains.CONSTRUCTION_K7_POST_DEPENDENCY_SOURCE_LIBRARY_V97_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PostDependencySourceLibraryArtifactV97:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_library_artifact_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "source_library_artifact_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("source_library_artifact_id")
            != self.source_library_artifact_id
            or domains.extension_content_id_v97(
                domains.CONSTRUCTION_K7_POST_DEPENDENCY_SOURCE_LIBRARY_V97_DOMAIN,
                payload,
            )
            != self.source_library_artifact_id
        ):
            _fail("V97 source library bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: PostDependencySourceLibraryArtifactV97 | None = None


def freeze_post_dependency_source_library_v97(
    v96_campaign_raw: bytes,
    v96_verification_raw: bytes,
) -> PostDependencySourceLibraryArtifactV97:
    global _CACHE
    if _CACHE is None:
        document = _document(v96_campaign_raw, v96_verification_raw)
        raw = canonical_json_bytes(document)
        identity = document["source_library_artifact_id"]
        if SOURCE_LIBRARY_ARTIFACT_ID != "0" * 64 and (
            identity != SOURCE_LIBRARY_ARTIFACT_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V97 frozen source library changed")
        _CACHE = PostDependencySourceLibraryArtifactV97(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "SOURCE_LIBRARY_ARTIFACT_ID",
    "freeze_post_dependency_source_library_v97",
)
