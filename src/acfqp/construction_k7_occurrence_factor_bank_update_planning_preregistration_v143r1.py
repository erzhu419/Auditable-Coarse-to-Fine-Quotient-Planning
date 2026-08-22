"""Outcome-free preregistration for the V143R1 occurrence factor bank update planner campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v143r1 as domains
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


IMPLEMENTATION_COMMITS = ("38e881eaa05fd3e66b1291d6be31dc08fae6dadf",)
V141_FINAL_COMMIT = "99e814d"
V140_FAILED_PREREGISTRATION_ID = (
    "a70ca4992729a9d583f747ab766a3fc258ff4bde799415464638dbb960a8122d"
)
V140_FAILURE_BYTE_COUNT = 1_107
V140_FAILURE_SHA256 = (
    "3123b0babe9b11a732bb565c855cbc852ec16998d0aa36bbc18cbf10f279af02"
)
V142_FAILED_PREREGISTRATION_ID = (
    "b650f33fb02988b64cd583300c5138d79b5c2c29dd7a1e4d523abca503cb4712"
)
V142_FAILURE_BYTE_COUNT = 1_486
V142_FAILURE_SHA256 = (
    "b6782177e8bfabd9d8b4d7f0a9d12f4c54aba03a613bf8f0a4d18896229c7085"
)
V143_FAILED_PREREGISTRATION_ID = (
    "8a49412db7846d894b3ea03a0b00716d978978514a52507f8fa002b39ed39246"
)
V143_FAILURE_BYTE_COUNT = 1_931
V143_FAILURE_SHA256 = (
    "15b157c5301a650603a6d131e5c6feb6d35481be1aaf4be2f537bd7fd30163de"
)
PREREGISTRATION_ID = "8794fa232f13e89bd29049302b6bee6859489a7949de6f52e78c9efdfd665004"
EXPECTED_CANONICAL_BYTE_COUNT = 22_794
EXPECTED_CANONICAL_SHA256 = (
    "9fac88b8c47fff2b49536ec0fd079d2e1c2e7812f48d31b8222aa3d15845de5a"
)
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_231),
    (INVENTORY, 1_047_232),
    (INVENTORY, 1_047_233),
    (DUAL, 1_047_234),
    (DUAL, 1_047_235),
    (DUAL, 1_047_236),
    (MODULAR, 1_047_237),
    (MODULAR, 1_047_238),
    (MODULAR, 1_047_239),
    (PACKET, 1_047_240),
    (PACKET, 1_047_241),
    (PACKET, 1_047_242),
)
TARGET_EPISODE_INDICES = (439, 440)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 12
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v143r1.py",
        1_954,
        "5dcb657eb600fae1a5a48539b8c7008f7c0b41ef9c0ae6856fc8600dd70e0a50",
    ),
    (
        "src/acfqp/occurrence_factor_bank_update_acquisition_v143r1.py",
        12_954,
        "2d6356a280c34801ae0046493ad098d0d21a1b763e8928b2594968a27719aec4",
    ),
    (
        "src/acfqp/occurrence_factor_bank_update_planning_campaign_core_v143r1.py",
        14_676,
        "ce9ec9ace5be3e99ded3ef7d55b4de5722c27ebe645504180896c8f77cd001d8",
    ),
)


class ConstructionK7OccurrenceFactorBankUpdatePlanningPreregistrationV143R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankUpdatePlanningPreregistrationV143R1Error(message)


def campaign_config_v143r1() -> dict[str, Any]:
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
    dictionary_raw: bytes,
    verification_raw: bytes,
    v140_failure_raw: bytes,
    v142_failure_raw: bytes,
    v143_failure_raw: bytes,
) -> dict[str, Any]:
    dictionary = loads_canonical_json(dictionary_raw)
    verification = loads_canonical_json(verification_raw)
    v140_failure = loads_canonical_json(v140_failure_raw)
    v142_failure = loads_canonical_json(v142_failure_raw)
    v143_failure = loads_canonical_json(v143_failure_raw)
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
        or canonical_json_bytes(v142_failure) != v142_failure_raw
        or len(v142_failure_raw) != V142_FAILURE_BYTE_COUNT
        or hashlib.sha256(v142_failure_raw).hexdigest() != V142_FAILURE_SHA256
        or v142_failure.get("preregistration_id")
        != V142_FAILED_PREREGISTRATION_ID
        or v142_failure.get("outcome_kind")
        != "PREREGISTERED_CAUSAL_OPCODE_EVALUATOR_FAILURE"
        or v142_failure.get("error_type")
        != "GenericArtifactSubprogramInstantiatorV121Error"
        or v142_failure.get("same_identity_rerun_forbidden") is not True
        or canonical_json_bytes(v143_failure) != v143_failure_raw
        or len(v143_failure_raw) != V143_FAILURE_BYTE_COUNT
        or hashlib.sha256(v143_failure_raw).hexdigest() != V143_FAILURE_SHA256
        or v143_failure.get("preregistration_id")
        != V143_FAILED_PREREGISTRATION_ID
        or v143_failure.get("outcome_kind")
        != "PREREGISTERED_RESOURCE_CAP_FAILURE"
        or v143_failure.get("failed_family") != DUAL
        or v143_failure.get("failed_seed") != 1_047_215
        or v143_failure.get("frozen_maximum_acquisition_labels") != 768
        or v143_failure.get("same_identity_rerun_forbidden") is not True
    ):
        _fail("V143R1 frozen V141 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V143R1 frozen implementation source changed")
    config = campaign_config_v143r1()
    payload = {
        "schema": "acfqp.occurrence_factor_bank_update_planning_preregistration.v143r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v141_final_commit_precedes_v143r1_target_execution": V141_FINAL_COMMIT,
        "frozen_implementation_source_facts": source_facts,
        "frozen_v141_factor_bank": dictionary,
        "frozen_v141_independent_verification": verification,
        "frozen_v140_failed_predecessor": v140_failure,
        "frozen_v142_failed_predecessor": v142_failure,
        "frozen_v143_failed_predecessor": v143_failure,
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
            "v142_causal_opcode_evaluator_failure_preserved": True,
            "v142_identity_not_rerun": True,
            "v143_preregistered_resource_cap_failure_preserved": True,
            "v143_identity_not_rerun": True,
            "unreplayable_candidates_are_invalidated_before_stop": True,
            "fresh_successor_resource_schedule": True,
            "robust_candidate_schema_is_explicitly_decoded": True,
            "occurrence_support_replaces_campaign_container_support": True,
            "fresh_target_occurrence_identities": True,
            "same_synthesizer_and_stop_rule_both_arms": True,
            "only_arm_switch_is_factor_prior": True,
            "aggregate_positive_reduction_is_primary_gate": True,
            "strict_positive_reduction_required_each_occurrence": False,
            "zero_and_negative_occurrences_must_be_preserved": True,
            "both_arm_receding_episodes_required": True,
            "certificate_failure_only_ground_recovery_required": True,
            "compiled_world_model_only_planning_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "registered_v143r1_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v143r1(
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_PREREGISTRATION_V143R1_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankUpdatePlanningPreregistrationV143R1:
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
            or domains.extension_content_id_v143r1(
                domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_PREREGISTRATION_V143R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V143R1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_occurrence_factor_bank_update_planning_preregistration_v143r1(
    dictionary_raw: bytes,
    verification_raw: bytes,
    v140_failure_raw: bytes,
    v142_failure_raw: bytes,
    v143_failure_raw: bytes,
) -> OccurrenceFactorBankUpdatePlanningPreregistrationV143R1:
    document = _document(
        dictionary_raw,
        verification_raw,
        v140_failure_raw,
        v142_failure_raw,
        v143_failure_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V143R1 frozen preregistration changed")
    return OccurrenceFactorBankUpdatePlanningPreregistrationV143R1(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v143r1",
    "freeze_occurrence_factor_bank_update_planning_preregistration_v143r1",
)
