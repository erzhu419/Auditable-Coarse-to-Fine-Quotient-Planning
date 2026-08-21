"""Outcome-free preregistration for the V140r1 occurrence factor bank planner campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v140r1 as domains
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


IMPLEMENTATION_COMMITS = ("e7b42501fea19e36ba4d1f111733b892e4c5f7b0",)
V139_FINAL_COMMIT = "116db3d"
V140_FAILED_PREREGISTRATION_ID = (
    "a70ca4992729a9d583f747ab766a3fc258ff4bde799415464638dbb960a8122d"
)
V140_FAILURE_BYTE_COUNT = 1_107
V140_FAILURE_SHA256 = (
    "3123b0babe9b11a732bb565c855cbc852ec16998d0aa36bbc18cbf10f279af02"
)
PREREGISTRATION_ID = "9169ce3e104c939e1cfb6a928952d80bf319b6374860889506ea85785ca71dbd"
EXPECTED_CANONICAL_BYTE_COUNT = 15_809
EXPECTED_CANONICAL_SHA256 = (
    "aee69c0fdb70b26f31319b9e682cd1b66262bc9e6bf6a2535f4fa5ebc82cecdd"
)
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_181),
    (DUAL, 1_047_182),
    (MODULAR, 1_047_183),
    (PACKET, 1_047_184),
)
TARGET_EPISODE_INDICES = (407, 408)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 768
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v140r1.py",
        1_877,
        "525d4522933752d3c5cc2226c5b3e543e6ceb082d4fad76644025454f65a1c20",
    ),
    (
        "src/acfqp/occurrence_factor_bank_acquisition_v140r1.py",
        11_024,
        "d9085622f555b1d39cf41aaba7ce54a681c13242dc8250ad2a643927e9d5f038",
    ),
    (
        "src/acfqp/occurrence_factor_bank_planning_campaign_core_v140r1.py",
        12_763,
        "76ae343a552e19e646eee7a3252ad7bc8df830fcb901dbbcaedc24fe3dc3d6ba",
    ),
)


class ConstructionK7OccurrenceFactorBankPlanningPreregistrationV140r1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankPlanningPreregistrationV140r1Error(message)


def campaign_config_v140r1() -> dict[str, Any]:
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
        _fail("V140r1 frozen V139 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V140r1 frozen implementation source changed")
    config = campaign_config_v140r1()
    payload = {
        "schema": "acfqp.occurrence_factor_bank_planning_preregistration.v140r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v139_final_commit_precedes_v140r1_target_execution": V139_FINAL_COMMIT,
        "frozen_implementation_source_facts": source_facts,
        "frozen_v139_factor_bank": dictionary,
        "frozen_v139_independent_verification": verification,
        "frozen_v140_failed_predecessor": v140_failure,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v139_occurrence_factor_bank_receipt_precedes_target_outcomes": True,
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
            "registered_v140r1_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v140r1(
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_PREREGISTRATION_V140R1_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankPlanningPreregistrationV140r1:
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
            or domains.extension_content_id_v140r1(
                domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_PREREGISTRATION_V140R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V140r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_occurrence_factor_bank_planning_preregistration_v140r1(
    dictionary_raw: bytes, verification_raw: bytes, v140_failure_raw: bytes
) -> OccurrenceFactorBankPlanningPreregistrationV140r1:
    document = _document(dictionary_raw, verification_raw, v140_failure_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V140r1 frozen preregistration changed")
    return OccurrenceFactorBankPlanningPreregistrationV140r1(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v140r1",
    "freeze_occurrence_factor_bank_planning_preregistration_v140r1",
)
