"""Outcome-free preregistration for V87r1 coordinate-aligned transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_applicability_target_preregistration_v87 as previous
from acfqp import construction_k7_domain_registry_extension_v87r1 as domains
from acfqp.construction_k7_action_applicability_model_v87 import (
    MODEL_ARTIFACT_ID as APPLICABILITY_MODEL_ARTIFACT_ID,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    MODEL_ARTIFACT_ID as PROJECTED_MODEL_ARTIFACT_ID,
)
from acfqp.coordinate_aligned_target_campaign_core_v87r1 import (
    build_coordinate_aligned_target_campaign_document_v87r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "2cd55d7"
PREREGISTRATION_ID = "dca32845cd12818f18f5fd463c61c9244c9591317a03590dfa23358e4c74660f"
EXPECTED_CANONICAL_BYTE_COUNT = 6_769
EXPECTED_CANONICAL_SHA256 = "a450272dad6644d5b248692c60af56ba1cedd33f6b41e5177069870e38c066ef"
V87_FAILED_CAMPAIGN_ID = (
    "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
)
V87_FAILURE_VERIFICATION_ID = (
    "d8af2766c723c1b42895f9c4b5d85e2557c366af2ab6473f19516c9b54fe19d5"
)
TARGET_FAMILY = "BALANCED_BATCH_REFINEMENT"
TARGET_SEEDS = (909_101, 909_102, 909_103, 909_104, 909_105, 909_106)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 10
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MINIMUM_ALIGNED_COMPLETED_TARGET_COUNT = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v86_projected_disagreement_model.json",
    "artifacts/world_model/v87_action_applicability_model.json",
    "src/acfqp/construction_k7_domain_registry_extension_v87r1.py",
    "src/acfqp/construction_k7_projected_model_artifact_v86.py",
    "src/acfqp/construction_k7_action_applicability_model_v87.py",
    "src/acfqp/generic_coordinate_alignment_v60.py",
    "src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py",
    "src/acfqp/generic_applicability_conditioned_planner_v58.py",
    "src/acfqp/generic_applicability_certificate_planner_v59.py",
    "src/acfqp/coordinate_aligned_target_campaign_core_v87r1.py",
    "src/acfqp/construction_k7_coordinate_aligned_target_campaign_v87r1.py",
)
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v86_projected_disagreement_model.json", 136251, "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"),
    ("artifacts/world_model/v87_action_applicability_model.json", 2978, "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"),
    ("src/acfqp/construction_k7_domain_registry_extension_v87r1.py", 1624, "63746595802f44aacb3a2839299e3ddb648a67c62422837feec5c0fe9a99ba8a"),
    ("src/acfqp/construction_k7_projected_model_artifact_v86.py", 2816, "9ce071589f9fa60bf6cc32f56518e88316152827832206654e96c78754f0b5e2"),
    ("src/acfqp/construction_k7_action_applicability_model_v87.py", 4079, "e72edc8c42ca31f5c8a4aeaf339dff9bdc47d5264df251f0fd84d4d0f52066d5"),
    ("src/acfqp/generic_coordinate_alignment_v60.py", 17009, "f424ddf0ef853beaed91db0c5106ce8b04cb45f4a26ddf9467c251f9ca08b6bf"),
    ("src/acfqp/generic_coordinate_aligned_certificate_planner_v60.py", 9546, "ec3fad926bf3ec9eba6f3fb94ffb32f787849558b5fc212b88a798500acda30e"),
    ("src/acfqp/generic_applicability_conditioned_planner_v58.py", 14772, "afd72df879951c941cee9b2dbb59b4eb9847d69e1cacc17c166b3b8ae93a20a6"),
    ("src/acfqp/generic_applicability_certificate_planner_v59.py", 16867, "60e56328833716aca9a7dea64af7caba02cd2c345b67ffe313b398e200359566"),
    ("src/acfqp/coordinate_aligned_target_campaign_core_v87r1.py", 16493, "45d02f28b3a44f1dd5cfe52a735b691e75b786186798ad11465bb24b680db7c8"),
    ("src/acfqp/construction_k7_coordinate_aligned_target_campaign_v87r1.py", 4534, "6c2346240f8358a5599767ad92206de6fdafb77155f381ca2f225d9cfffbb5b3"),
)


class ConstructionK7CoordinateAlignedTargetPreregistrationV87R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CoordinateAlignedTargetPreregistrationV87R1Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v87r1() -> dict[str, Any]:
    config = previous.campaign_config_v87()
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        minimum_aligned_completed_target_count=(
            MINIMUM_ALIGNED_COMPLETED_TARGET_COUNT
        ),
        v87_failed_campaign_id=V87_FAILED_CAMPAIGN_ID,
        v87_failure_verification_id=V87_FAILURE_VERIFICATION_ID,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.coordinate_aligned_target_preregistration.v87r1",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v87_failed_campaign_id": V87_FAILED_CAMPAIGN_ID,
            "v87_failure_verification_id": V87_FAILURE_VERIFICATION_ID,
            "v87_preregistration_id": previous.PREREGISTRATION_ID,
            "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
            "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v87r1_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V87R1),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_coordinate_aligned_target_campaign_document_v87r1
            ),
            "frozen_before_any_registered_v87r1_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v87_structural_incompatibility_failure_preserved": True,
            "blind_seed_substitution_or_posthoc_target_selection_used": False,
            "fresh_v87r1_identities_disjoint_from_v87": True,
            "exact_structural_color_equality_removed": True,
            "structural_schema_signature_still_required": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_v87": min(TARGET_SEEDS)
            > max(previous.TARGET_SEEDS),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
            "source_and_target_episode_indices_disjoint": True,
        },
        "construction_contract": {
            "coordinate_and_action_field_projection_derived_from_target_common_partial_raw_transitions": True,
            "finite_type_compatible_bijection_grammar_used": True,
            "frozen_source_applicability_relation_instantiated_not_refit": True,
            "every_retained_projection_must_replay_partial_residual_and_terminal_evidence": True,
            "exactly_one_projection_required_before_target_episode": True,
            "target_episode_outcomes_cannot_select_alignment_or_refit_models": True,
            "same_exact_certificate_engine_in_both_arms": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "minimum_aligned_completed_target_count": (
                MINIMUM_ALIGNED_COMPLETED_TARGET_COUNT
            ),
            "every_eligible_target_must_complete_both_arms": True,
            "unique_alignment_required_on_every_completed_target": True,
            "every_successful_abstract_output_must_be_accepted_as_legal": True,
            "accepted_abstract_orderings_must_cover_every_execution_step": True,
            "applicability_filter_must_avoid_inapplicable_branches": True,
            "certificate_failure_only_ground_discipline_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "target_sample_reduction_required": False,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "maximum_target_ground_support_labels_per_arm": 100_000,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "source_physical_labels_separate": True,
            "source_derived_classifications_not_physical_labels": True,
            "target_common_partial_labels_separate": True,
            "alignment_relation_and_replay_compute_not_physical_labels": True,
            "derived_and_strict_certificate_labels_separate": True,
            "execution_steps_separate": True,
            "abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v87r1_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_abstract_ordering_primary_observed": False,
            "multi_step_planning_primarily_in_abstract_model_claimed": False,
            "sample_tax_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v87r1_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v87r1(
            domains.CONSTRUCTION_K7_COORDINATE_ALIGNED_PREREGISTRATION_V87R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CoordinateAlignedTargetPreregistrationV87R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v87r1(
                domains.CONSTRUCTION_K7_COORDINATE_ALIGNED_PREREGISTRATION_V87R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V87r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CoordinateAlignedTargetPreregistrationV87R1 | None = None


def freeze_coordinate_aligned_target_preregistration_v87r1(
) -> CoordinateAlignedTargetPreregistrationV87R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V87r1 preregistration changed")
    _CACHE = CoordinateAlignedTargetPreregistrationV87R1(_ISSUER, raw, identity)
    return _CACHE


def verify_coordinate_aligned_target_preregistration_v87r1(
    value: Any,
) -> CoordinateAlignedTargetPreregistrationV87R1:
    if type(value) is not CoordinateAlignedTargetPreregistrationV87R1:
        _fail("V87r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_coordinate_aligned_target_preregistration_v87r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V87r1 preregistration differs from frozen bytes")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v87r1",
    "freeze_coordinate_aligned_target_preregistration_v87r1",
    "verify_coordinate_aligned_target_preregistration_v87r1",
)
