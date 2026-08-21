"""Outcome-free preregistration for the V97 post-dependency campaign."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v97 as domains
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as previous
from acfqp.construction_k7_persistent_multi_residual_campaign_v96 import (
    CAMPAIGN_ID as V96_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V96_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_persistent_multi_residual_independent_verifier_v96 import (
    EXPECTED_CANONICAL_SHA256 as V96_VERIFICATION_SHA256,
    VERIFICATION_ID as V96_VERIFICATION_ID,
)
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    EXPECTED_CANONICAL_SHA256 as SOURCE_LIBRARY_SHA256,
    SOURCE_LIBRARY_ARTIFACT_ID,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    EXPECTED_CANONICAL_SHA256 as V62_LIBRARY_SHA256,
    LIBRARY_ARTIFACT_ID as V62_LIBRARY_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("3999557", "0183627")
PREREGISTRATION_ID = "99c6ae8e5c71ea1f5b92fc01117d979772d0958a255926beb81d032837b008fa"
EXPECTED_CANONICAL_BYTE_COUNT = 6_260
EXPECTED_CANONICAL_SHA256 = "756b67bf9a9827f007f9d8cb6a05181ac68d35ea95de9ab16f5e3fd2a05531f2"
TARGET_FAMILY = "COUPLED_EXCHANGE"
TARGET_SEEDS = (999_101, 999_102, 999_103, 999_104)
TARGET_EPISODE_INDICES = (41, 42, 43)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v97.py", 1773, "a49bce60ae18dbc269aeefe60974561cf327ddc0bdc2f85ad674483a6d0af243"),
    ("src/acfqp/generic_post_dependency_residual_v97.py", 20112, "03d476fd8a354de13dbcfa9b70bf2fe0ca9c20e67b861e9dd2c62f9f9df48111"),
    ("src/acfqp/construction_k7_post_dependency_source_library_v97.py", 10639, "672c5d0c48d4ed0489e4dace9d9dd78b3f85328f473a7c6c5a3bd9ae8324e6c0"),
    ("src/acfqp/generic_persistent_post_dependency_sequence_v97.py", 14193, "ed031c40263ad703caecf94443e036379d18adc0db28707d910726d5b69521ce"),
    ("src/acfqp/post_dependency_campaign_core_v97.py", 12991, "c76751f76d8399b7e7a83959d04f869afb93b2f83def2a6b2ca78ded81a4274b"),
    ("src/acfqp/generic_multi_residual_certificate_planner_v26.py", 15056, "3f60bad172f0199160ab629b2369c6252f8d76d822150c05df6690c5e3c13e40"),
    ("src/acfqp/generic_preloaded_certificate_receding_engine_v74.py", 12503, "a470ec2d750353c7d951d7d82494b307be61fb99eb3ca3bd8b2023880d7392c3"),
    ("src/acfqp/construction_k7_residual_factor_library_v62.py", 10225, "6fbe73b77d7e806d04a3163c7010a83ef82b11c52b2e169bdec239a28d836881"),
    ("src/acfqp/construction_k7_persistent_multi_residual_independent_verifier_v96.py", 14786, "de2bf54058017cd73a09d24cb32f5a46b7af7df1e0e4331d7db4ded87d3a27fd"),
    ("src/acfqp/construction_k7_persistent_multi_residual_preregistration_v96.py", 12201, "bcb0cb0cec939d055475092ebf767907561b35d392dfa845baa85a8118e182ba"),
    ("src/acfqp/phase3e_ids.py", 414040, "afc1431487eb6aab76bf2fa2e234afa8498d69f37757abd700001538c097e888"),
)


class ConstructionK7PostDependencyPreregistrationV97Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PostDependencyPreregistrationV97Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative, _count, _digest in FROZEN_SOURCE_FACTS:
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


def campaign_config_v97() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v96())
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.post_dependency_preregistration.v97",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v96_failed_campaign_id": V96_CAMPAIGN_ID,
            "v96_failed_campaign_sha256": V96_CAMPAIGN_SHA256,
            "v96_failure_verification_id": V96_VERIFICATION_ID,
            "v96_failure_verification_sha256": V96_VERIFICATION_SHA256,
            "post_dependency_source_library_artifact_id": SOURCE_LIBRARY_ARTIFACT_ID,
            "post_dependency_source_library_sha256": SOURCE_LIBRARY_SHA256,
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v62_residual_library_sha256": V62_LIBRARY_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v97_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V97),
            "frozen_before_any_registered_v97_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "target_episode_indices_unique": (
                len(set(TARGET_EPISODE_INDICES))
                == len(TARGET_EPISODE_INDICES)
            ),
        },
        "construction_contract": {
            "source_prior_contains_only_anonymous_three_band_dependency_structure": True,
            "source_target_driver_threshold_and_leaf_bindings_not_transferred": True,
            "target_bindings_derived_from_target_raw_state_action_successor_differences": True,
            "same_finite_grammar_binding_search_partial_candidate_and_first_episode_between_arms": True,
            "only_switched_variable": "POST_DEPENDENCY_STRUCTURE_PRIOR_CODE_LENGTH",
            "joint_successor_compiles_partial_ordinary_and_post_dependency_factors": True,
            "joint_successor_retained_across_later_queries_as_fallible_heuristic": True,
            "persistent_exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
            "strict_cold_direct_restarts_without_free_rows_each_episode": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_joint_successor_must_cover_every_residual_target": True,
            "every_target_must_use_joint_abstract_planning": True,
            "at_least_one_target_must_discover_and_use_post_dependency_program": True,
            "meta_lifetime_labels_must_not_exceed_no_structure_prior": True,
            "meta_lifetime_labels_must_be_strictly_below_cold_direct_in_aggregate": True,
            "certificate_failure_only_query_discipline_required": True,
            "zero_later_labels_not_required_because_local_recovery_is_permitted": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_joint_support_branch_evaluations": campaign_config_v97()[
                "maximum_joint_support_branch_evaluations"
            ],
            "joint_support_feasible_beam_width": campaign_config_v97()[
                "joint_support_feasible_beam_width"
            ],
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_separate": True,
            "target_acquisition_and_certificate_labels_separate": True,
            "meta_no_structure_prior_and_cold_direct_labels_separate": True,
            "execution_steps_separate": True,
            "dependency_derivation_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v97_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "post_dependency_joint_successor_verified": False,
            "structural_prior_sample_tax_advantage_over_same_synthesizer_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v97(
            domains.CONSTRUCTION_K7_POST_DEPENDENCY_PREREGISTRATION_V97_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PostDependencyPreregistrationV97:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v97(
                domains.CONSTRUCTION_K7_POST_DEPENDENCY_PREREGISTRATION_V97_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V97 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: PostDependencyPreregistrationV97 | None = None


def freeze_post_dependency_preregistration_v97() -> PostDependencyPreregistrationV97:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V97 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V97 frozen preregistration changed")
        _CACHE = PostDependencyPreregistrationV97(_ISSUER, raw, identity)
    return _CACHE


def verify_post_dependency_preregistration_v97(
    value: Any,
) -> PostDependencyPreregistrationV97:
    if type(value) is not PostDependencyPreregistrationV97:
        _fail("V97 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_post_dependency_preregistration_v97()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V97 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v97",
    "freeze_post_dependency_preregistration_v97",
    "verify_post_dependency_preregistration_v97",
)
