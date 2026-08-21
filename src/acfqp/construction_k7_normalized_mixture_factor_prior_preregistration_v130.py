"""Outcome-free preregistration for normalized prefix-mixture V130."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v130 as domains
from acfqp import (
    construction_k7_fair_unified_factor_prior_ablation_preregistration_v129r1 as previous,
)
from acfqp.construction_k7_fair_unified_factor_prior_ablation_campaign_v129r1 import (
    CAMPAIGN_ID as V129R1_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V129R1_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V129R1_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_fair_unified_factor_prior_ablation_independent_verifier_v129r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V129R1_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V129R1_VERIFICATION_SHA256,
    VERIFICATION_ID as V129R1_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    modular_routing_config_v128,
)
from acfqp.normalized_mixture_factor_prior_acquisition_v130 import (
    derive_normalized_mixture_calibration_v130,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("fec5c316eb06fc5a684d6b4afec84a5408f73d65",)
PREREGISTRATION_ID = "ed61ef6b5c0a0cf93d9ebccd34c6e172bf1f32a4709b893c1b8116497e6ce063"
EXPECTED_CANONICAL_BYTE_COUNT = 54_971
EXPECTED_CANONICAL_SHA256 = "e3c0e97029104081f3f5d2c9741350ea092af19d933ea21d2291ae99d675d264"
TARGET_OCCURRENCES = (
    (INVENTORY, 1_046_101),
    (INVENTORY, 1_046_102),
    (DUAL, 1_046_103),
    (DUAL, 1_046_104),
    (MODULAR, 1_046_105),
    (MODULAR, 1_046_106),
)
TARGET_EPISODE_INDICES = (335, 336, 337)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 320
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v130.py",
        1_765,
        "fad2cdd6ec5bc7ebd52037f0eefafd22824544ec98126c44a8afb2c6ceebe430",
    ),
    (
        "src/acfqp/normalized_mixture_factor_prior_acquisition_v130.py",
        24_328,
        "34eeb6e7b6815fa8ffc976f9bd142c6b6c98f3232d93919f6f352fb9031366d5",
    ),
    (
        "src/acfqp/normalized_mixture_factor_prior_campaign_core_v130.py",
        12_831,
        "0b572f2682ad9623aa1eb4107818145d24cbcfd3f51d0b4feb2d19c8900c7fcc",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7NormalizedMixtureFactorPriorPreregistrationV130Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7NormalizedMixtureFactorPriorPreregistrationV130Error(message)


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for path, _count, _digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        result.append(
            {
                "relative_path": path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def campaign_config_v130() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    for family in (INVENTORY, DUAL, MODULAR):
        config["families"][family][
            "maximum_acquisition_labels"
        ] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v129r1_campaign_raw: bytes,
    v129r1_verification_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v129r1_campaign_raw)
    verification = loads_canonical_json(v129r1_verification_raw)
    if (
        len(v129r1_campaign_raw) != V129R1_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v129r1_campaign_raw).hexdigest()
        != V129R1_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V129R1_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v129r1_verification_raw) != V129R1_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v129r1_verification_raw).hexdigest()
        != V129R1_VERIFICATION_SHA256
        or verification.get("verification_id") != V129R1_VERIFICATION_ID
        or verification.get(
            "registered_workload_sample_efficiency_improvement_independently_verified"
        )
        is not True
    ):
        _fail("V130 frozen V129r1 predecessor changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    projection = library["v15_partial_synthesizer_projection"]
    calibration = derive_normalized_mixture_calibration_v130(projection)
    if (
        calibration["fixed_mixture_weight_supplied_by_target"] is not False
        or calibration["target_outcomes_accessed"] is not False
        or calibration[
            "prior_odds_derived_from_prefix_codelength_difference"
        ]
        is not True
    ):
        _fail("V130 normalized prior calibration changed")
    config = campaign_config_v130()
    payload = {
        "schema": "acfqp.normalized_mixture_factor_prior_preregistration.v130",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v129r1_campaign_id": V129R1_CAMPAIGN_ID,
            "v129r1_campaign_byte_count": V129R1_CAMPAIGN_BYTE_COUNT,
            "v129r1_campaign_sha256": V129R1_CAMPAIGN_SHA256,
            "v129r1_verification_id": V129R1_VERIFICATION_ID,
            "v129r1_verification_byte_count": V129R1_VERIFICATION_BYTE_COUNT,
            "v129r1_verification_sha256": V129R1_VERIFICATION_SHA256,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "normalized_mixture_calibration": calibration,
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v130_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V130),
            "frozen_before_any_registered_v130_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": config["target_occurrences"],
            "target_families": [INVENTORY, DUAL, MODULAR],
            "two_fresh_occurrences_per_family": True,
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "successful_development_identities": [
                1_030_107,
                1_030_108,
                1_030_109,
                1_030_110,
            ],
            "discarded_development_identities_not_reused": [
                1_030_101,
                1_030_102,
                1_030_103,
                1_030_104,
                1_030_105,
                1_030_106,
            ],
            "development_identities_excluded_from_registered_gate": True,
        },
        "matched_ablation_contract": {
            "same_fair_witness_blind_path_first_backtracking_policy": True,
            "same_raw_transition_prefix_through_common_label": True,
            "same_generic_atomic_hypothesis_pool": True,
            "same_candidate_carrier_and_schema": True,
            "same_candidate_replay_function": True,
            "same_stopping_rule_function": True,
            "only_arm_switch_is_normalized_factor_prior": True,
            "fixed_two_to_library_cardinality_prior_multiplier_present": False,
            "normalized_prefix_code_prior_calibration_frozen_before_targets": True,
            "strictly_positive_acquisition_label_reduction_required_in_every_occurrence": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_has_strictly_positive_label_reduction": True,
            "fixed_two_to_library_cardinality_prior_multiplier_absent_everywhere": True,
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
            "registered_v130_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v130(
            domains.CONSTRUCTION_K7_NORMALIZED_MIXTURE_FACTOR_PRIOR_PREREGISTRATION_V130_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class NormalizedMixtureFactorPriorPreregistrationV130:
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
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v130(
                domains.CONSTRUCTION_K7_NORMALIZED_MIXTURE_FACTOR_PRIOR_PREREGISTRATION_V130_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V130 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: NormalizedMixtureFactorPriorPreregistrationV130 | None = None


def freeze_normalized_mixture_factor_prior_preregistration_v130(
    source_campaign_bytes: Mapping[str, bytes],
    v129r1_campaign_raw: bytes,
    v129r1_verification_raw: bytes,
) -> NormalizedMixtureFactorPriorPreregistrationV130:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V130 source closure changed before registration")
    document = _document(
        source_campaign_bytes, v129r1_campaign_raw, v129r1_verification_raw
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V130 preregistration changed")
    _CACHE = NormalizedMixtureFactorPriorPreregistrationV130(
        _ISSUER, raw, identity
    )
    return _CACHE


__all__ = (
    "FROZEN_SOURCE_FACTS",
    "PREREGISTRATION_ID",
    "TARGET_EPISODE_INDICES",
    "TARGET_OCCURRENCES",
    "V129R1_CAMPAIGN_ID",
    "V129R1_VERIFICATION_ID",
    "campaign_config_v130",
    "freeze_normalized_mixture_factor_prior_preregistration_v130",
)
