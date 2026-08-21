"""Outcome-free preregistration for the V133 opaque-dictionary planner campaign."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v133 as domains
from acfqp.construction_k7_opaque_source_archive_independent_verifier_v132 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V132_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V132_VERIFICATION_SHA256,
    VERIFICATION_ID as V132_VERIFICATION_ID,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    modular_routing_config_v128,
)
from acfqp.opaque_source_archive_dictionary_v132 import (
    DICTIONARY_ID as V132_DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V132_DICTIONARY_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V132_DICTIONARY_SHA256,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("8c375dc77aeed1a8dca5e92a42d11e741d36d308",)
PREREGISTRATION_ID = "c5f46ae0981a0cd321befd8842d613141a45cf78eb7a138f5390ed0c50eb4b93"
EXPECTED_CANONICAL_BYTE_COUNT = 11_152
EXPECTED_CANONICAL_SHA256 = "24b0b8bfc9708707c303e26f887897ce8535de094aa8219d099001426513d3a0"
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_131),
    (INVENTORY, 1_047_132),
    (DUAL, 1_047_133),
    (DUAL, 1_047_134),
    (MODULAR, 1_047_135),
    (MODULAR, 1_047_136),
)
TARGET_EPISODE_INDICES = (365, 366, 367)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MAXIMUM_ACQUISITION_LABELS = 320
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v133.py",
        1_851,
        "b75792b446af377db105c5ba25dba6bd06bc15f722fe412d0f6a0654db6d03a2",
    ),
    (
        "src/acfqp/opaque_archive_factor_acquisition_v133.py",
        10_871,
        "c46dd530738ff072769981a91f3ed13ff11485bfe3b5029307f784962e1bf760",
    ),
    (
        "src/acfqp/opaque_archive_planning_campaign_core_v133.py",
        12_284,
        "d5796e7c7a34c7621d28558b90e9bbfbca619168bd6a94bb7188efb1bda7db8e",
    ),
)


class ConstructionK7OpaqueArchivePlanningPreregistrationV133Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OpaqueArchivePlanningPreregistrationV133Error(message)


def campaign_config_v133() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    for family in (INVENTORY, DUAL, MODULAR):
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
        or len(dictionary_raw) != V132_DICTIONARY_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V132_DICTIONARY_SHA256
        or dictionary.get("dictionary_id") != V132_DICTIONARY_ID
        or dictionary.get("target_outcomes_accessed") is not False
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V132_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V132_VERIFICATION_SHA256
        or verification.get("verification_id") != V132_VERIFICATION_ID
        or verification.get("dictionary_id") != V132_DICTIONARY_ID
        or verification.get("producer_free_dictionary_reconstruction") is not True
    ):
        _fail("V133 frozen V132 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V133 frozen implementation source changed")
    config = campaign_config_v133()
    payload = {
        "schema": "acfqp.opaque_archive_planning_preregistration.v133",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v132_dictionary": dictionary,
        "frozen_v132_independent_verification": verification,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v132_dictionary_receipt_precedes_target_outcomes": True,
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
            "registered_v133_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v133(
        domains.CONSTRUCTION_K7_OPAQUE_ARCHIVE_PLANNING_PREREGISTRATION_V133_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpaqueArchivePlanningPreregistrationV133:
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
            or domains.extension_content_id_v133(
                domains.CONSTRUCTION_K7_OPAQUE_ARCHIVE_PLANNING_PREREGISTRATION_V133_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V133 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_opaque_archive_planning_preregistration_v133(
    dictionary_raw: bytes, verification_raw: bytes
) -> OpaqueArchivePlanningPreregistrationV133:
    document = _document(dictionary_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V133 frozen preregistration changed")
    return OpaqueArchivePlanningPreregistrationV133(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v133",
    "freeze_opaque_archive_planning_preregistration_v133",
)
