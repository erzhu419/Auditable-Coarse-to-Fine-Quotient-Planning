"""Outcome-free preregistration for the V142 occurrence factor bank update planner campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v142 as domains
from acfqp.occurrence_factor_bank_update_v141 import (
    BANK_ID as V141_BANK_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V141_BANK_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V141_BANK_SHA256,
)
from acfqp.construction_k7_occurrence_factor_bank_update_independent_verifier_v141 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V141_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V141_VERIFICATION_SHA256,
    VERIFICATION_ID as V141_VERIFICATION_ID,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("b860cb865aa607bdedb91f688f858cd4789e8210",)
V141_FINAL_COMMIT = "99e814d"
V140_FAILED_PREREGISTRATION_ID = (
    "a70ca4992729a9d583f747ab766a3fc258ff4bde799415464638dbb960a8122d"
)
V140_FAILURE_BYTE_COUNT = 1_107
V140_FAILURE_SHA256 = (
    "3123b0babe9b11a732bb565c855cbc852ec16998d0aa36bbc18cbf10f279af02"
)
PREREGISTRATION_ID = "b650f33fb02988b64cd583300c5138d79b5c2c29dd7a1e4d523abca503cb4712"
EXPECTED_CANONICAL_BYTE_COUNT = 18_447
EXPECTED_CANONICAL_SHA256 = (
    "97afffec285ace10f6cb7b4135caf1bfd52de0b85b476d21f67e720546fa9a30"
)
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_191),
    (DUAL, 1_047_192),
    (MODULAR, 1_047_193),
    (PACKET, 1_047_194),
)
TARGET_EPISODE_INDICES = (415, 416)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 768
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v142.py",
        1_916,
        "4d35000b425f57e34229345c88a21a9ed079b5e83ba53c79000056b681568ed6",
    ),
    (
        "src/acfqp/occurrence_factor_bank_update_acquisition_v142.py",
        11_077,
        "5cddbff287afd816e36f1b6ef3103def800ab7d4143fc5d27c783a5adc6ffe6d",
    ),
    (
        "src/acfqp/occurrence_factor_bank_update_planning_campaign_core_v142.py",
        12_923,
        "7b61ee22406569d737940e4f9bae946524e05f1b29a4c2f6b57a8633a157c7a2",
    ),
)


class ConstructionK7OccurrenceFactorBankUpdatePlanningPreregistrationV142Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankUpdatePlanningPreregistrationV142Error(message)


def campaign_config_v142() -> dict[str, Any]:
    config = packet_batching_config_v134()
    for family in (INVENTORY, DUAL, MODULAR, PACKET):
        config["families"][family]["maximum_acquisition_labels"] = (
            MAXIMUM_ACQUISITION_LABELS
        )
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _document(
    dictionary_raw: bytes, verification_raw: bytes, v140_failure_raw: bytes
) -> dict[str, Any]:
    dictionary = loads_canonical_json(dictionary_raw)
    verification = loads_canonical_json(verification_raw)
    v140_failure = loads_canonical_json(v140_failure_raw)
    if (
        canonical_json_bytes(dictionary) != dictionary_raw
        or len(dictionary_raw) != V141_BANK_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V141_BANK_SHA256
        or dictionary.get("bank_id") != V141_BANK_ID
        or dictionary.get("source_occurrence_archive_cardinality") != 16
        or dictionary.get("selected_minimum_distinct_occurrence_support") != 9
        or dictionary.get("selected_template_count") != 5
        or dictionary.get("robust_candidate_schema_decoded") is not True
        or dictionary.get("new_target_outcomes_accessed") is not False
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V141_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V141_VERIFICATION_SHA256
        or verification.get("verification_id") != V141_VERIFICATION_ID
        or verification.get("bank_id") != V141_BANK_ID
        or verification.get(
            "producer_free_campaign_occurrence_candidate_reconstruction"
        ) is not True
        or verification.get(
            "producer_free_support_threshold_and_factor_bank_reconstruction"
        ) is not True
        or canonical_json_bytes(v140_failure) != v140_failure_raw
        or len(v140_failure_raw) != V140_FAILURE_BYTE_COUNT
        or hashlib.sha256(v140_failure_raw).hexdigest() != V140_FAILURE_SHA256
        or v140_failure.get("preregistration_id")
        != V140_FAILED_PREREGISTRATION_ID
        or v140_failure.get("outcome_kind")
        != "PREREGISTERED_RESOURCE_CAP_FAILURE"
        or v140_failure.get("failed_seed") != 1_047_172
        or v140_failure.get("frozen_maximum_acquisition_labels") != 384
        or v140_failure.get("same_identity_rerun_forbidden") is not True
    ):
        _fail("V142 frozen V141 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V142 frozen implementation source changed")
    config = campaign_config_v142()
    payload = {
        "schema": "acfqp.occurrence_factor_bank_update_planning_preregistration.v142",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v141_final_commit_precedes_v142_target_execution": V141_FINAL_COMMIT,
        "frozen_implementation_source_facts": source_facts,
        "frozen_v141_factor_bank": dictionary,
        "frozen_v141_independent_verification": verification,
        "frozen_v140_failed_predecessor": v140_failure,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v141_occurrence_factor_bank_update_receipt_precedes_target_outcomes": True,
            "v140_preregistered_resource_cap_failure_preserved": True,
            "v140_identity_not_rerun": True,
            "fresh_successor_resource_schedule": True,
            "robust_candidate_schema_is_explicitly_decoded": True,
            "occurrence_support_replaces_campaign_container_support": True,
            "fresh_target_occurrence_identities": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_factor_prior": True,
            "strict_positive_reduction_required_each_occurrence": True,
            "both_arm_receding_episodes_required": True,
            "certificate_failure_only_ground_recovery_required": True,
            "compiled_world_model_only_planning_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v142_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v142(
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_PREREGISTRATION_V142_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankUpdatePlanningPreregistrationV142:
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
            or domains.extension_content_id_v142(
                domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_PREREGISTRATION_V142_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V142 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_occurrence_factor_bank_update_planning_preregistration_v142(
    dictionary_raw: bytes, verification_raw: bytes, v140_failure_raw: bytes
) -> OccurrenceFactorBankUpdatePlanningPreregistrationV142:
    document = _document(dictionary_raw, verification_raw, v140_failure_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V142 frozen preregistration changed")
    return OccurrenceFactorBankUpdatePlanningPreregistrationV142(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v142",
    "freeze_occurrence_factor_bank_update_planning_preregistration_v142",
)
