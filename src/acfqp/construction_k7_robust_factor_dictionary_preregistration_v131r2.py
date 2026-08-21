"""Outcome-free preregistration for robust leave-one-source dictionary V131R2."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v131r2 as domains
from acfqp import (
    construction_k7_automatic_factor_dictionary_preregistration_v131r1 as previous,
)
from acfqp.construction_k7_automatic_factor_dictionary_campaign_v131r1 import (
    CAMPAIGN_ID as V131R1_FAILED_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V131R1_FAILED_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V131R1_FAILED_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_normalized_mixture_factor_prior_campaign_v130 import (
    CAMPAIGN_ID as V130_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V130_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V130_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_normalized_mixture_factor_prior_independent_verifier_v130 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V130_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V130_VERIFICATION_SHA256,
    VERIFICATION_ID as V130_VERIFICATION_ID,
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
from acfqp.robust_factor_dictionary_acquisition_v131r2 import (
    derive_robust_dictionary_calibration_v131r2,
)
from acfqp.robust_automatic_factor_dictionary_v131r2 import (
    derive_robust_automatic_factor_dictionary_v131r2,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "31f526635f25af2c267b01f04f6b317e9901c2d9",
    "cce225b3480844412125fe5494beddd1807a3b8b",
    "55b98010a40aabd58cb47d1fe9e2bdcd1a3df5a0",
    "9650ff1050c66ca1249dbddd6d188fecc973cdc6",
)
PREREGISTRATION_ID = "2ded6e06afbe8653a3486a51c32707ef457d3791baec34e48e32d3553b03d0cf"
EXPECTED_CANONICAL_BYTE_COUNT = 64_370
EXPECTED_CANONICAL_SHA256 = "1e301e165eb5b00b26fdeb0a3d4917ba3d2f17a777d78f9296945c7cc3149000"
V131R1_PREREGISTRATION_ID = previous.PREREGISTRATION_ID
V131R1_PREREGISTRATION_BYTE_COUNT = previous.EXPECTED_CANONICAL_BYTE_COUNT
V131R1_PREREGISTRATION_SHA256 = previous.EXPECTED_CANONICAL_SHA256
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_121),
    (INVENTORY, 1_047_122),
    (DUAL, 1_047_123),
    (DUAL, 1_047_124),
    (MODULAR, 1_047_125),
    (MODULAR, 1_047_126),
)
TARGET_EPISODE_INDICES = (356, 357, 358)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 320
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v131r2.py",
        1_857,
        "f8a5753d2ba89add6a1599829dd65fabf08fae64b14428e57ac06e1d1d798fa0",
    ),
    (
        "src/acfqp/robust_automatic_factor_dictionary_v131r2.py",
        7_530,
        "d12f4b2c5008ad95b15af2e53d7a1090fa79742ef6bce90eabf0c459576ed83b",
    ),
    (
        "src/acfqp/robust_factor_dictionary_acquisition_v131r2.py",
        24_750,
        "dcbf08dedb43d43f30bed48dd4212587166901f148a55a2724d06a3ed54a8a81",
    ),
    (
        "src/acfqp/robust_factor_dictionary_campaign_core_v131r2.py",
        14_185,
        "ec33eaa382a200767d2d8aee611edc7f04d875f8c4b5390c28a208b3243d1f33",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7RobustFactorDictionaryPreregistrationV131R2Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RobustFactorDictionaryPreregistrationV131R2Error(message)


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


def campaign_config_v131r2() -> dict[str, Any]:
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
    v130_campaign_raw: bytes,
    v130_verification_raw: bytes,
    v131r1_preregistration_raw: bytes,
    v131r1_failed_campaign_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v130_campaign_raw)
    verification = loads_canonical_json(v130_verification_raw)
    if (
        len(v130_campaign_raw) != V130_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v130_campaign_raw).hexdigest()
        != V130_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V130_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v130_verification_raw) != V130_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v130_verification_raw).hexdigest()
        != V130_VERIFICATION_SHA256
        or verification.get("verification_id") != V130_VERIFICATION_ID
        or verification.get(
            "registered_workload_sample_efficiency_improvement_independently_verified"
        )
        is not True
    ):
        _fail("V131R2 frozen V130 predecessor changed")
    prior_registration = loads_canonical_json(v131r1_preregistration_raw)
    if (
        canonical_json_bytes(prior_registration) != v131r1_preregistration_raw
        or len(v131r1_preregistration_raw) != V131R1_PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(v131r1_preregistration_raw).hexdigest()
        != V131R1_PREREGISTRATION_SHA256
        or prior_registration.get("preregistration_id") != V131R1_PREREGISTRATION_ID
        or prior_registration.get("claim_boundary", {}).get(
            "registered_v131r1_target_outcome_observed"
        )
        is not False
    ):
        _fail("V131R2 frozen V131r1 preregistration changed")
    failed_campaign = loads_canonical_json(v131r1_failed_campaign_raw)
    if (
        canonical_json_bytes(failed_campaign) != v131r1_failed_campaign_raw
        or len(v131r1_failed_campaign_raw) != V131R1_FAILED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v131r1_failed_campaign_raw).hexdigest()
        != V131R1_FAILED_CAMPAIGN_SHA256
        or failed_campaign.get("campaign_id") != V131R1_FAILED_CAMPAIGN_ID
        or failed_campaign.get("registered_gate", {}).get("passed") is not False
        or failed_campaign.get("registered_gate", {}).get(
            "passed_target_occurrence_count"
        )
        != 5
        or sum(
            row["accounting"][
                "acquisition_labels_avoided_by_normalized_factor_prior"
            ]
            == 0
            for row in failed_campaign.get("target_occurrences", ())
        )
        != 1
    ):
        _fail("V131R2 frozen V131r1 failure changed")
    source_library = derive_artifact_factor_projection_v120(
        dict(source_campaign_bytes)
    )
    dictionary = derive_robust_automatic_factor_dictionary_v131r2(
        source_library, source_campaign_bytes
    )
    projection = dictionary["v15_partial_synthesizer_projection"]
    calibration = derive_robust_dictionary_calibration_v131r2(projection)
    if (
        calibration["fixed_mixture_weight_supplied_by_target"] is not False
        or calibration["target_outcomes_accessed"] is not False
        or calibration[
            "prior_odds_derived_from_prefix_codelength_difference"
        ]
        is not True
    ):
        _fail("V131R2 normalized prior calibration changed")
    config = campaign_config_v131r2()
    payload = {
        "schema": "acfqp.robust_factor_dictionary_preregistration.v131r2",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v130_campaign_id": V130_CAMPAIGN_ID,
            "v130_campaign_byte_count": V130_CAMPAIGN_BYTE_COUNT,
            "v130_campaign_sha256": V130_CAMPAIGN_SHA256,
            "v130_verification_id": V130_VERIFICATION_ID,
            "v130_verification_byte_count": V130_VERIFICATION_BYTE_COUNT,
            "v130_verification_sha256": V130_VERIFICATION_SHA256,
        },
        "frozen_failed_predecessor": {
            "v131r1_preregistration_id": V131R1_PREREGISTRATION_ID,
            "v131r1_preregistration_byte_count": V131R1_PREREGISTRATION_BYTE_COUNT,
            "v131r1_preregistration_sha256": V131R1_PREREGISTRATION_SHA256,
            "v131r1_failed_campaign_id": V131R1_FAILED_CAMPAIGN_ID,
            "v131r1_failed_campaign_byte_count": V131R1_FAILED_CAMPAIGN_BYTE_COUNT,
            "v131r1_failed_campaign_sha256": V131R1_FAILED_CAMPAIGN_SHA256,
            "failure_reason": "ONE_REGISTERED_OCCURRENCE_HAD_ZERO_LABEL_REDUCTION",
            "passed_occurrence_count": 5,
            "failed_occurrence_count": 1,
            "same_identity_rerun_forbidden": True,
        },
        "source_artifact_factor_library": source_library,
        "source_artifact_factor_library_id": source_library["factor_library_id"],
        "robust_factor_dictionary": dictionary,
        "robust_factor_dictionary_id": dictionary["dictionary_id"],
        "robust_dictionary_calibration": calibration,
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v131r2_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131R2),
            "frozen_before_any_registered_v131r2_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": config["target_occurrences"],
            "target_families": [INVENTORY, DUAL, MODULAR],
            "two_fresh_occurrences_per_family": True,
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "successful_development_identities": [
                1_031_101,
                1_031_102,
                1_031_103,
                1_031_104,
                1_031_111,
                1_031_201,
                1_031_202,
                1_031_203,
                1_031_204,
            ],
            "discarded_development_identities_not_reused": [],
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
            "robust_dictionary_selected_before_targets": True,
            "dictionary_cardinality_selected_by_leave_one_source_positive_gain": True,
            "leave_one_source_campaign_reconstruction_required": True,
            "fixed_template_cardinality_supplied": False,
            "strictly_positive_acquisition_label_reduction_required_in_every_occurrence": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_has_strictly_positive_label_reduction": True,
            "fixed_two_to_library_cardinality_prior_multiplier_absent_everywhere": True,
            "robust_dictionary_selected_before_target_outcomes": True,
            "leave_one_source_campaign_reconstruction_verified": True,
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
            "registered_v131r2_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v131r2(
            domains.CONSTRUCTION_K7_ROBUST_DICTIONARY_FACTOR_PRIOR_PREREGISTRATION_V131R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RobustFactorDictionaryPreregistrationV131R2:
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
            or domains.extension_content_id_v131r2(
                domains.CONSTRUCTION_K7_ROBUST_DICTIONARY_FACTOR_PRIOR_PREREGISTRATION_V131R2_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V131R2 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: RobustFactorDictionaryPreregistrationV131R2 | None = None


def freeze_robust_factor_dictionary_preregistration_v131r2(
    source_campaign_bytes: Mapping[str, bytes],
    v130_campaign_raw: bytes,
    v130_verification_raw: bytes,
    v131r1_preregistration_raw: bytes,
    v131r1_failed_campaign_raw: bytes,
) -> RobustFactorDictionaryPreregistrationV131R2:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V131R2 source closure changed before registration")
    document = _document(
        source_campaign_bytes,
        v130_campaign_raw,
        v130_verification_raw,
        v131r1_preregistration_raw,
        v131r1_failed_campaign_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V131R2 preregistration changed")
    _CACHE = RobustFactorDictionaryPreregistrationV131R2(
        _ISSUER, raw, identity
    )
    return _CACHE


__all__ = (
    "FROZEN_SOURCE_FACTS",
    "PREREGISTRATION_ID",
    "TARGET_EPISODE_INDICES",
    "TARGET_OCCURRENCES",
    "V130_CAMPAIGN_ID",
    "V130_VERIFICATION_ID",
    "campaign_config_v131r2",
    "freeze_robust_factor_dictionary_preregistration_v131r2",
)
