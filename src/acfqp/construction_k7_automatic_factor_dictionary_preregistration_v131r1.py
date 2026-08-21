"""Outcome-free preregistration for automatic minimal-dictionary V131R1."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v131r1 as domains
from acfqp import (
    construction_k7_automatic_factor_dictionary_preregistration_v131 as previous,
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
from acfqp.automatic_factor_dictionary_acquisition_v131 import (
    derive_automatic_dictionary_calibration_v131,
)
from acfqp.automatic_minimal_factor_dictionary_v131 import (
    derive_automatic_minimal_factor_dictionary_v131,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "31f526635f25af2c267b01f04f6b317e9901c2d9",
    "cce225b3480844412125fe5494beddd1807a3b8b",
    "55b98010a40aabd58cb47d1fe9e2bdcd1a3df5a0",
)
PREREGISTRATION_ID = "334e4235c604aab1e5d1122cf5daf4d3a69ddef60ce579901ffaf4a272051011"
EXPECTED_CANONICAL_BYTE_COUNT = 62_158
EXPECTED_CANONICAL_SHA256 = "f78a4e5c56130d96e24654f3af52d7ca1c2023e514562cc99e73622912e18d4d"
V131_WITHDRAWN_PREREGISTRATION_ID = previous.PREREGISTRATION_ID
V131_WITHDRAWN_PREREGISTRATION_BYTE_COUNT = previous.EXPECTED_CANONICAL_BYTE_COUNT
V131_WITHDRAWN_PREREGISTRATION_SHA256 = previous.EXPECTED_CANONICAL_SHA256
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_111),
    (INVENTORY, 1_047_112),
    (DUAL, 1_047_113),
    (DUAL, 1_047_114),
    (MODULAR, 1_047_115),
    (MODULAR, 1_047_116),
)
TARGET_EPISODE_INDICES = (350, 351, 352)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 320
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v131r1.py",
        1_617,
        "72d9cfb55dc5035c750d0545024ca9eb61181dd9a1e660a11bf9b0892dc335eb",
    ),
    (
        "src/acfqp/automatic_factor_dictionary_campaign_core_v131r1.py",
        14_239,
        "8629463f0b859e0e1e35ae101cc54352a32670214ed800302c982e58d4fa5528",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7AutomaticFactorDictionaryPreregistrationV131R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AutomaticFactorDictionaryPreregistrationV131R1Error(message)


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


def campaign_config_v131r1() -> dict[str, Any]:
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
    v131_preregistration_raw: bytes,
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
        _fail("V131R1 frozen V130 predecessor changed")
    withdrawn = loads_canonical_json(v131_preregistration_raw)
    if (
        canonical_json_bytes(withdrawn) != v131_preregistration_raw
        or len(v131_preregistration_raw) != V131_WITHDRAWN_PREREGISTRATION_BYTE_COUNT
        or hashlib.sha256(v131_preregistration_raw).hexdigest()
        != V131_WITHDRAWN_PREREGISTRATION_SHA256
        or withdrawn.get("preregistration_id") != V131_WITHDRAWN_PREREGISTRATION_ID
        or withdrawn.get("claim_boundary", {}).get(
            "registered_v131_target_outcome_observed"
        )
        is not False
    ):
        _fail("V131R1 frozen pre-outcome V131 withdrawal changed")
    source_library = derive_artifact_factor_projection_v120(
        dict(source_campaign_bytes)
    )
    dictionary = derive_automatic_minimal_factor_dictionary_v131(
        source_library, source_campaign_bytes
    )
    projection = dictionary["v15_partial_synthesizer_projection"]
    calibration = derive_automatic_dictionary_calibration_v131(projection)
    if (
        calibration["fixed_mixture_weight_supplied_by_target"] is not False
        or calibration["target_outcomes_accessed"] is not False
        or calibration[
            "prior_odds_derived_from_prefix_codelength_difference"
        ]
        is not True
    ):
        _fail("V131R1 normalized prior calibration changed")
    config = campaign_config_v131r1()
    payload = {
        "schema": "acfqp.automatic_factor_dictionary_preregistration.v131r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v130_campaign_id": V130_CAMPAIGN_ID,
            "v130_campaign_byte_count": V130_CAMPAIGN_BYTE_COUNT,
            "v130_campaign_sha256": V130_CAMPAIGN_SHA256,
            "v130_verification_id": V130_VERIFICATION_ID,
            "v130_verification_byte_count": V130_VERIFICATION_BYTE_COUNT,
            "v130_verification_sha256": V130_VERIFICATION_SHA256,
        },
        "frozen_pre_outcome_withdrawn_predecessor": {
            "v131_preregistration_id": V131_WITHDRAWN_PREREGISTRATION_ID,
            "v131_preregistration_byte_count": V131_WITHDRAWN_PREREGISTRATION_BYTE_COUNT,
            "v131_preregistration_sha256": V131_WITHDRAWN_PREREGISTRATION_SHA256,
            "withdrawal_reason": "STALE_V129R1_PREDECESSOR_FIELD_NAMES_IN_CAMPAIGN_CORE",
            "registered_target_outcome_executed": False,
            "same_identity_rerun_forbidden": True,
        },
        "source_artifact_factor_library": source_library,
        "source_artifact_factor_library_id": source_library["factor_library_id"],
        "automatic_factor_dictionary": dictionary,
        "automatic_factor_dictionary_id": dictionary["dictionary_id"],
        "automatic_dictionary_calibration": calibration,
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v131r1_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131R1),
            "frozen_before_any_registered_v131r1_target_outcome": True,
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
            "automatic_dictionary_selected_before_targets": True,
            "dictionary_cardinality_selected_by_exact_source_code": True,
            "leave_one_source_campaign_reconstruction_required": True,
            "fixed_template_cardinality_supplied": False,
            "strictly_positive_acquisition_label_reduction_required_in_every_occurrence": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_occurrence_has_strictly_positive_label_reduction": True,
            "fixed_two_to_library_cardinality_prior_multiplier_absent_everywhere": True,
            "automatic_dictionary_selected_before_target_outcomes": True,
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
            "registered_v131r1_target_outcome_observed": False,
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
        "preregistration_id": domains.extension_content_id_v131r1(
            domains.CONSTRUCTION_K7_AUTOMATIC_DICTIONARY_FACTOR_PRIOR_PREREGISTRATION_V131R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AutomaticFactorDictionaryPreregistrationV131R1:
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
            or domains.extension_content_id_v131r1(
                domains.CONSTRUCTION_K7_AUTOMATIC_DICTIONARY_FACTOR_PRIOR_PREREGISTRATION_V131R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V131R1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: AutomaticFactorDictionaryPreregistrationV131R1 | None = None


def freeze_automatic_factor_dictionary_preregistration_v131r1(
    source_campaign_bytes: Mapping[str, bytes],
    v130_campaign_raw: bytes,
    v130_verification_raw: bytes,
    v131_preregistration_raw: bytes,
) -> AutomaticFactorDictionaryPreregistrationV131R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V131R1 source closure changed before registration")
    document = _document(
        source_campaign_bytes,
        v130_campaign_raw,
        v130_verification_raw,
        v131_preregistration_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V131R1 preregistration changed")
    _CACHE = AutomaticFactorDictionaryPreregistrationV131R1(
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
    "campaign_config_v131r1",
    "freeze_automatic_factor_dictionary_preregistration_v131r1",
)
