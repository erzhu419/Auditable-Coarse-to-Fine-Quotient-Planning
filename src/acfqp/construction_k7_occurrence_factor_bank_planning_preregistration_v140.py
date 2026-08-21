"""Outcome-free preregistration for the V140 occurrence factor bank planner campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v140 as domains
from acfqp.occurrence_factor_bank_v139 import (
    BANK_ID as V139_BANK_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V139_BANK_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V139_BANK_SHA256,
)
from acfqp.construction_k7_occurrence_factor_bank_independent_verifier_v139 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V139_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V139_VERIFICATION_SHA256,
    VERIFICATION_ID as V139_VERIFICATION_ID,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("3903572776c58aae3513c1386b63962c33ab54ad",)
V139_FINAL_COMMIT = "116db3d"
PREREGISTRATION_ID = "a70ca4992729a9d583f747ab766a3fc258ff4bde799415464638dbb960a8122d"
EXPECTED_CANONICAL_BYTE_COUNT = 14_527
EXPECTED_CANONICAL_SHA256 = (
    "ff5d1b3c9471e101d5ec963776176f800faed80fa54ca3f1baf055b4af68b3dc"
)
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_171),
    (DUAL, 1_047_172),
    (MODULAR, 1_047_173),
    (PACKET, 1_047_174),
)
TARGET_EPISODE_INDICES = (399, 400)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 384
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v140.py",
        1_839,
        "e97c3901e4c672823240ec2d8ae6f7707731d3b8de5bc7189b4f07d929d7679f",
    ),
    (
        "src/acfqp/occurrence_factor_bank_acquisition_v140.py",
        10_994,
        "f6c402a9c87e8e393ad684a5410f6aac047edd03ff8b4dcc45a5172858c06d62",
    ),
    (
        "src/acfqp/occurrence_factor_bank_planning_campaign_core_v140.py",
        12_727,
        "9443f9b5ddb9c7649b9afd06191fb8fa2ee60fb5053ce21712dc1193964c4b6f",
    ),
)


class ConstructionK7OccurrenceFactorBankPlanningPreregistrationV140Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankPlanningPreregistrationV140Error(message)


def campaign_config_v140() -> dict[str, Any]:
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


def _document(dictionary_raw: bytes, verification_raw: bytes) -> dict[str, Any]:
    dictionary = loads_canonical_json(dictionary_raw)
    verification = loads_canonical_json(verification_raw)
    if (
        canonical_json_bytes(dictionary) != dictionary_raw
        or len(dictionary_raw) != V139_BANK_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V139_BANK_SHA256
        or dictionary.get("bank_id") != V139_BANK_ID
        or dictionary.get("source_occurrence_archive_cardinality") != 12
        or dictionary.get("selected_minimum_distinct_occurrence_support") != 7
        or dictionary.get("selected_template_count") != 5
        or dictionary.get("robust_candidate_schema_decoded") is not True
        or dictionary.get("new_target_outcomes_accessed") is not False
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V139_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V139_VERIFICATION_SHA256
        or verification.get("verification_id") != V139_VERIFICATION_ID
        or verification.get("bank_id") != V139_BANK_ID
        or verification.get(
            "producer_free_campaign_occurrence_candidate_reconstruction"
        ) is not True
        or verification.get(
            "producer_free_support_threshold_and_factor_bank_reconstruction"
        ) is not True
    ):
        _fail("V140 frozen V139 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V140 frozen implementation source changed")
    config = campaign_config_v140()
    payload = {
        "schema": "acfqp.occurrence_factor_bank_planning_preregistration.v140",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v139_final_commit_precedes_v140_target_execution": V139_FINAL_COMMIT,
        "frozen_implementation_source_facts": source_facts,
        "frozen_v139_factor_bank": dictionary,
        "frozen_v139_independent_verification": verification,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v139_occurrence_factor_bank_receipt_precedes_target_outcomes": True,
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
            "registered_v140_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v140(
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_PREREGISTRATION_V140_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankPlanningPreregistrationV140:
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
            or domains.extension_content_id_v140(
                domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_PREREGISTRATION_V140_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V140 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_occurrence_factor_bank_planning_preregistration_v140(
    dictionary_raw: bytes, verification_raw: bytes
) -> OccurrenceFactorBankPlanningPreregistrationV140:
    document = _document(dictionary_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V140 frozen preregistration changed")
    return OccurrenceFactorBankPlanningPreregistrationV140(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v140",
    "freeze_occurrence_factor_bank_planning_preregistration_v140",
)
