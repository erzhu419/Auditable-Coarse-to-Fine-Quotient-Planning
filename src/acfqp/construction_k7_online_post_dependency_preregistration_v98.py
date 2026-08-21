"""Outcome-free preregistration for online dependency activation V98."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v98 as domains
from acfqp import construction_k7_post_dependency_preregistration_v97 as previous
from acfqp.construction_k7_post_dependency_campaign_v97 import (
    CAMPAIGN_ID as V97_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V97_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_post_dependency_independent_verifier_v97 import (
    EXPECTED_CANONICAL_SHA256 as V97_VERIFICATION_SHA256,
    VERIFICATION_ID as V97_VERIFICATION_ID,
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


IMPLEMENTATION_COMMITS = ("ac0124e", "66505f7", "7cd3395")
PREREGISTRATION_ID = "81b87ce48c3b4159e4e0e869228dbb34b02d06adf1b5ad7c2359ef2c8fa0e452"
EXPECTED_CANONICAL_BYTE_COUNT = 5_935
EXPECTED_CANONICAL_SHA256 = "954748fcc279bedc21b9fe597d3d8d1269a550c68fdf5229fc80dc91d13901e8"
TARGET_FAMILY = "COUPLED_EXCHANGE"
TARGET_SEEDS = (1_003_101, 1_003_102, 1_003_103, 1_003_104)
TARGET_EPISODE_INDICES = (61, 62, 63)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v98.py", 1720, "0e0b7cd479f7c17461b8326eb78ff9b5eeb154be0d9cb6eed72ffeca0da53495"),
    ("src/acfqp/generic_online_post_dependency_certificate_planner_v98.py", 18654, "b205ba721dc2ea31e4c00b91f17afdcc7c94cee96e2edce5c350c347fad658b6"),
    ("src/acfqp/generic_persistent_online_post_dependency_sequence_v98.py", 12926, "25b674f48db4d8f88ca293641b595b79e6de44aea6d06b00edb880e2a6221555"),
    ("src/acfqp/online_post_dependency_campaign_core_v98.py", 14053, "fb2895038aa2d73c5e32079246b53e7aff61a436a130fb1025752c019032f510"),
    ("src/acfqp/generic_post_dependency_residual_v97.py", 20112, "03d476fd8a354de13dbcfa9b70bf2fe0ca9c20e67b861e9dd2c62f9f9df48111"),
    ("src/acfqp/generic_preloaded_certificate_receding_engine_v74.py", 12503, "a470ec2d750353c7d951d7d82494b307be61fb99eb3ca3bd8b2023880d7392c3"),
    ("src/acfqp/construction_k7_post_dependency_source_library_v97.py", 10639, "672c5d0c48d4ed0489e4dace9d9dd78b3f85328f473a7c6c5a3bd9ae8324e6c0"),
    ("src/acfqp/construction_k7_residual_factor_library_v62.py", 10225, "6fbe73b77d7e806d04a3163c7010a83ef82b11c52b2e169bdec239a28d836881"),
    ("src/acfqp/phase3e_ids.py", 414040, "afc1431487eb6aab76bf2fa2e234afa8498d69f37757abd700001538c097e888"),
)


class ConstructionK7OnlinePostDependencyPreregistrationV98Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlinePostDependencyPreregistrationV98Error(message)


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


def campaign_config_v98() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v97())
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
        "schema": "acfqp.online_post_dependency_preregistration.v98",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v97_campaign_id": V97_CAMPAIGN_ID,
            "v97_campaign_sha256": V97_CAMPAIGN_SHA256,
            "v97_verification_id": V97_VERIFICATION_ID,
            "v97_verification_sha256": V97_VERIFICATION_SHA256,
            "post_dependency_source_library_artifact_id": SOURCE_LIBRARY_ARTIFACT_ID,
            "post_dependency_source_library_sha256": SOURCE_LIBRARY_SHA256,
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v62_residual_library_sha256": V62_LIBRARY_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v98_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V98),
            "frozen_before_any_registered_v98_target_outcome": True,
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
            "online_post_dependency_synthesis_occurs_inside_first_certificate_search": True,
            "same_partial_candidate_rows_residual_prior_outcome_schedule_synthesizer_and_stopping_rule_between_arms": True,
            "only_switched_variable": "POST_DEPENDENCY_STRUCTURE_DESCRIPTION_CODE_UNITS",
            "source_prior_contains_no_target_column_driver_threshold_or_leaf_binding": True,
            "mdl_confidence_rule_uses_target_model_evidence_labels": True,
            "activation_is_fallible_and_candidate_revisions_are_allowed": True,
            "activated_model_retained_for_later_receding_abstract_planning": True,
            "persistent_exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
            "strict_cold_direct_restarts_without_free_rows_each_episode": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_target_meta_model_must_activate_and_cover_every_residual": True,
            "every_target_must_use_retained_abstract_model": True,
            "at_least_one_target_must_have_post_dependency_candidate": True,
            "all_post_dependency_targets_must_strictly_reduce_activation_labels": True,
            "aggregate_activation_labels_must_be_strictly_below_no_prior": True,
            "meta_lifetime_task_labels_must_not_exceed_no_prior": True,
            "meta_lifetime_task_labels_must_be_strictly_below_cold_direct": True,
            "certificate_failure_only_query_discipline_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_joint_support_branch_evaluations": campaign_config_v98()[
                "maximum_joint_support_branch_evaluations"
            ],
            "joint_support_feasible_beam_width": campaign_config_v98()[
                "joint_support_feasible_beam_width"
            ],
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged_to_target": True,
            "partial_acquisition_and_certificate_labels_separate": True,
            "activation_labels_use_explicit_right_censoring": True,
            "meta_no_prior_and_cold_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "synthesis_and_abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v98_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "structural_prior_model_activation_sample_tax_advantage_verified": False,
            "structural_prior_total_task_label_advantage_verified": False,
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
        "preregistration_id": domains.extension_content_id_v98(
            domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_PREREGISTRATION_V98_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OnlinePostDependencyPreregistrationV98:
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
            or domains.extension_content_id_v98(
                domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_PREREGISTRATION_V98_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V98 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: OnlinePostDependencyPreregistrationV98 | None = None


def freeze_online_post_dependency_preregistration_v98(
) -> OnlinePostDependencyPreregistrationV98:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V98 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V98 frozen preregistration changed")
        _CACHE = OnlinePostDependencyPreregistrationV98(_ISSUER, raw, identity)
    return _CACHE


def verify_online_post_dependency_preregistration_v98(
    value: Any,
) -> OnlinePostDependencyPreregistrationV98:
    if type(value) is not OnlinePostDependencyPreregistrationV98:
        _fail("V98 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_online_post_dependency_preregistration_v98()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V98 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v98",
    "freeze_online_post_dependency_preregistration_v98",
    "verify_online_post_dependency_preregistration_v98",
)
