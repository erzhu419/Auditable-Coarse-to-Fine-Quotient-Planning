"""Outcome-free preregistration for the V129 matched sample-tax ablation."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v129 as domains
from acfqp import construction_k7_third_family_owned_sequence_preregistration_v128 as previous
from acfqp.construction_k7_third_family_owned_sequence_campaign_v128 import (
    CAMPAIGN_ID as V128_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V128_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V128_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_third_family_owned_sequence_independent_verifier_v128 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V128_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V128_VERIFICATION_SHA256,
    VERIFICATION_ID as V128_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR, modular_routing_config_v128
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("406c0d2413b6f6f2ac018bdb1af9b67ee8f34b00",)
V128_CAMPAIGN_COMMIT = "00ea1dd"
V128_VERIFICATION_COMMIT = "2ba5567"
PREREGISTRATION_ID = "2057f4bc9b8ba3ad78ef56a63cc7fcdb814b36ce55be51e4e036086d5112bf9c"
EXPECTED_CANONICAL_BYTE_COUNT = 53_425
EXPECTED_CANONICAL_SHA256 = "7b4de6a596366bb47471b4892d427b4c860ecc1007aca1c63776e00f81e05362"
TARGET_OCCURRENCES = (
    (INVENTORY, 1_044_101),
    (INVENTORY, 1_044_102),
    (DUAL, 1_044_103),
    (DUAL, 1_044_104),
    (MODULAR, 1_044_105),
    (MODULAR, 1_044_106),
)
TARGET_EPISODE_INDICES = (323, 324, 325)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 2_048
REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER = 8
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v129.py", 1_739, "f336d29b3a9dc77a99b174380e2a3316cbcf0bbb55c64e4c6b5878ad2a779d42"),
    ("src/acfqp/unified_factor_prior_ablation_acquisition_v129.py", 17_905, "b12c5e8ae23d8d215b1d7ae531a2751230bb80aec2b740da67317146beb5a4ff"),
    ("src/acfqp/unified_factor_prior_ablation_campaign_core_v129.py", 11_843, "86eec61aa0b2230c2ba5213699ef4265f6c663d13da5751aded9b30547d542df"),
    ("src/acfqp/construction_k7_third_family_owned_sequence_campaign_v128.py", 3_746, "3cb572d680785db5d80f2b695de5faac8ed40fe813b4261a0f1efc4219e8c7bd"),
    ("src/acfqp/construction_k7_third_family_owned_sequence_independent_verifier_v128.py", 21_400, "852cf430d7787332016f9ce068cc67d2274aed617fbed7bbbff1334480a052c7"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7UnifiedFactorPriorAblationPreregistrationV129Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7UnifiedFactorPriorAblationPreregistrationV129Error(message)


def _frozen_source_facts():
    return [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]


def _source_facts():
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v129() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    for family in (INVENTORY, DUAL, MODULAR):
        config["families"][family]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(source_campaign_bytes: Mapping[str, bytes], v128_campaign_raw: bytes, v128_verification_raw: bytes):
    campaign = loads_canonical_json(v128_campaign_raw)
    verification = loads_canonical_json(v128_verification_raw)
    if (
        len(v128_campaign_raw) != V128_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v128_campaign_raw).hexdigest() != V128_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V128_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v128_verification_raw) != V128_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v128_verification_raw).hexdigest() != V128_VERIFICATION_SHA256
        or verification.get("verification_id") != V128_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
    ):
        _fail("V129 frozen V128 predecessor changed")
    source = dict(source_campaign_bytes)
    library = derive_artifact_factor_projection_v120(source)
    if len(library["derived_subprograms"]) != 3 or 2 ** len(library["derived_subprograms"]) != REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER:
        _fail("V129 registered finite factor-prior mass changed")
    payload = {
        "schema": "acfqp.unified_factor_prior_ablation_preregistration.v129",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v128_campaign_id": V128_CAMPAIGN_ID,
            "v128_campaign_byte_count": V128_CAMPAIGN_BYTE_COUNT,
            "v128_campaign_sha256": V128_CAMPAIGN_SHA256,
            "v128_campaign_commit": V128_CAMPAIGN_COMMIT,
            "v128_verification_id": V128_VERIFICATION_ID,
            "v128_verification_byte_count": V128_VERIFICATION_BYTE_COUNT,
            "v128_verification_sha256": V128_VERIFICATION_SHA256,
            "v128_verification_commit": V128_VERIFICATION_COMMIT,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v129_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V129),
            "frozen_before_any_registered_v129_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v129()["target_occurrences"],
            "target_families": [INVENTORY, DUAL, MODULAR],
            "two_fresh_occurrences_per_family": True,
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_identities": [
                {"family": INVENTORY, "seed": 1_030_007},
                {"family": DUAL, "seed": 1_030_008},
                {"family": MODULAR, "seed": 1_030_009},
            ],
            "development_identities_excluded_from_registered_gate": True,
        },
        "matched_ablation_contract": {
            "same_witness_blind_acquisition_policy": True,
            "same_raw_transition_prefix_through_common_label": True,
            "same_generic_atomic_hypothesis_pool": True,
            "same_candidate_carrier_and_schema": True,
            "same_candidate_replay_function": True,
            "same_stopping_rule_function": True,
            "only_arm_switch_is_registered_factor_prior": True,
            "registered_factor_prior_mass_multiplier": REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER,
            "factor_prior_mass_derived_as_two_to_artifact_subprogram_count": True,
            "strictly_positive_acquisition_label_reduction_required_in_every_occurrence": True,
        },
        "development_evidence_retained_before_registration": {
            "inventory_prior_vs_no_prior_labels": [13, 17],
            "dual_budget_prior_vs_no_prior_labels": [45, 49],
            "modular_routing_prior_vs_no_prior_labels": [19, 23],
            "all_development_differences_are_four_labels": True,
            "not_part_of_registered_gate": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_has_strictly_positive_label_reduction": True,
            "same_synthesizer_representation_and_stop_rule_in_every_occurrence": True,
            "both_arm_receding_episodes_succeed_everywhere": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "maximum_acquisition_labels_per_arm": MAXIMUM_ACQUISITION_LABELS,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
            "unused_resource_headroom_not_counted_as_sample_labels": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v129_target_outcome_observed": False,
            "registered_workload_sample_efficiency_improvement_observed": False,
            "producer_free_verification_present": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v129(
            domains.CONSTRUCTION_K7_UNIFIED_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V129_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class UnifiedFactorPriorAblationPreregistrationV129:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v129(
                domains.CONSTRUCTION_K7_UNIFIED_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V129_DOMAIN,
                payload,
            ) != self.preregistration_id
        ):
            _fail("V129 preregistration bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def freeze_unified_factor_prior_ablation_preregistration_v129(
    source_campaign_bytes: Mapping[str, bytes],
    v128_campaign_raw: bytes,
    v128_verification_raw: bytes,
) -> UnifiedFactorPriorAblationPreregistrationV129:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V129 source closure changed before registration")
    document = _document(source_campaign_bytes, v128_campaign_raw, v128_verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V129 preregistration changed")
    _CACHE = UnifiedFactorPriorAblationPreregistrationV129(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "FROZEN_SOURCE_FACTS",
    "PREREGISTRATION_ID",
    "REGISTERED_FACTOR_PRIOR_MASS_MULTIPLIER",
    "TARGET_EPISODE_INDICES",
    "TARGET_OCCURRENCES",
    "V128_CAMPAIGN_ID",
    "V128_VERIFICATION_ID",
    "campaign_config_v129",
    "freeze_unified_factor_prior_ablation_preregistration_v129",
)
