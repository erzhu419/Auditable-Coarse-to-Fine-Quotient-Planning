"""Outcome-free preregistration for the V136 auto-calibrated archive planner campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v136 as domains
from acfqp.auto_calibrated_archive_dictionary_v135 import (
    DICTIONARY_ID as V135_DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V135_DICTIONARY_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V135_DICTIONARY_SHA256,
)
from acfqp.construction_k7_auto_calibrated_archive_independent_verifier_v135 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V135_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V135_VERIFICATION_SHA256,
    VERIFICATION_ID as V135_VERIFICATION_ID,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("07b993672ca8509774c6b022171d069c24439904",)
V135_FINAL_COMMIT = "c50ae96"
PREREGISTRATION_ID = "03cde19bbf8aec77fda4dafc34e21a041de926d7fa881bd97c6158741ed3d5cb"
EXPECTED_CANONICAL_BYTE_COUNT = 12_840
EXPECTED_CANONICAL_SHA256 = (
    "4a661baa7adca745b4a2d3d5cb741fdd6bde091d5c5ffc991cb5a8d88094b08d"
)
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_151),
    (DUAL, 1_047_152),
    (MODULAR, 1_047_153),
    (PACKET, 1_047_154),
)
TARGET_EPISODE_INDICES = (383, 384)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 384
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v136.py",
        1_850,
        "e52d8af71e8870a89a0cf570c285ca774d0a54950ccf5deceb66bbd1ddf8f11d",
    ),
    (
        "src/acfqp/auto_calibrated_archive_factor_acquisition_v136.py",
        11_259,
        "58bf56f27aa5590efbc4ba5a25b3fe2ecc8223e4ff395e311b1889bd98ccbfa0",
    ),
    (
        "src/acfqp/auto_calibrated_archive_planning_campaign_core_v136.py",
        12_711,
        "38d2e22a22f201e0de54f8c2d2f79d87407c618ffd7df554242ed3f9108a7cde",
    ),
)


class ConstructionK7AutoCalibratedArchivePlanningPreregistrationV136Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AutoCalibratedArchivePlanningPreregistrationV136Error(message)


def campaign_config_v136() -> dict[str, Any]:
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
        or len(dictionary_raw) != V135_DICTIONARY_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V135_DICTIONARY_SHA256
        or dictionary.get("dictionary_id") != V135_DICTIONARY_ID
        or dictionary.get("support_thresholds_supplied_by_caller") is not False
        or dictionary.get("target_outcomes_accessed") is not False
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V135_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V135_VERIFICATION_SHA256
        or verification.get("verification_id") != V135_VERIFICATION_ID
        or verification.get("dictionary_id") != V135_DICTIONARY_ID
        or verification.get("producer_free_threshold_grid_reconstruction") is not True
        or verification.get("producer_free_dictionary_reconstruction") is not True
    ):
        _fail("V136 frozen V135 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V136 frozen implementation source changed")
    config = campaign_config_v136()
    payload = {
        "schema": "acfqp.auto_calibrated_archive_planning_preregistration.v136",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v135_final_commit_precedes_v136_target_execution": V135_FINAL_COMMIT,
        "frozen_implementation_source_facts": source_facts,
        "frozen_v135_dictionary": dictionary,
        "frozen_v135_independent_verification": verification,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v135_auto_calibrated_receipt_precedes_target_outcomes": True,
            "support_thresholds_not_supplied_by_v136": True,
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
            "registered_v136_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v136(
        domains.CONSTRUCTION_K7_AUTO_CALIBRATED_ARCHIVE_PREREGISTRATION_V136_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AutoCalibratedArchivePlanningPreregistrationV136:
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
            or domains.extension_content_id_v136(
                domains.CONSTRUCTION_K7_AUTO_CALIBRATED_ARCHIVE_PREREGISTRATION_V136_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V136 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_auto_calibrated_archive_planning_preregistration_v136(
    dictionary_raw: bytes, verification_raw: bytes
) -> AutoCalibratedArchivePlanningPreregistrationV136:
    document = _document(dictionary_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V136 frozen preregistration changed")
    return AutoCalibratedArchivePlanningPreregistrationV136(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v136",
    "freeze_auto_calibrated_archive_planning_preregistration_v136",
)
