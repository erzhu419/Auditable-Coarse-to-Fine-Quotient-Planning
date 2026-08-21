"""Outcome-free preregistration for the V138 heterogeneous cohort planner campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v138 as domains
from acfqp.heterogeneous_archive_cohort_dictionary_v137 import (
    DICTIONARY_ID as V137_DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V137_DICTIONARY_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V137_DICTIONARY_SHA256,
)
from acfqp.construction_k7_heterogeneous_archive_independent_verifier_v137 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V137_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V137_VERIFICATION_SHA256,
    VERIFICATION_ID as V137_VERIFICATION_ID,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("f0a8383833d777486c0d65dbdaaec2d0f057c3fd",)
V137_FINAL_COMMIT = "255e974"
PREREGISTRATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
TARGET_OCCURRENCES = (
    (INVENTORY, 1_047_161),
    (DUAL, 1_047_162),
    (MODULAR, 1_047_163),
    (PACKET, 1_047_164),
)
TARGET_EPISODE_INDICES = (391, 392)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
MAXIMUM_ACQUISITION_LABELS = 384
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v138.py",
        1_817,
        "ed1a0af491cf28de366504cb3697d41ea47cf40642301b7fda5e9c2f38b121df",
    ),
    (
        "src/acfqp/heterogeneous_cohort_factor_acquisition_v138.py",
        11_106,
        "3ff7aa0fbd9790d75ebf9f6ebe52ae0997e2c63fa34e2d36262e2f02a3882991",
    ),
    (
        "src/acfqp/heterogeneous_cohort_planning_campaign_core_v138.py",
        12_635,
        "85fe8fd4876ca9e6970a7e84d048f1259c6764a387c5724843de4f4c955d730b",
    ),
)


class ConstructionK7HeterogeneousCohortPlanningPreregistrationV138Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeterogeneousCohortPlanningPreregistrationV138Error(message)


def campaign_config_v138() -> dict[str, Any]:
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
        or len(dictionary_raw) != V137_DICTIONARY_BYTE_COUNT
        or hashlib.sha256(dictionary_raw).hexdigest() != V137_DICTIONARY_SHA256
        or dictionary.get("dictionary_id") != V137_DICTIONARY_ID
        or dictionary.get("complete_source_archive_cardinality") != 5
        or dictionary.get("selected_cohort_cardinality") != 4
        or dictionary.get("target_outcomes_accessed") is not False
        or canonical_json_bytes(verification) != verification_raw
        or len(verification_raw) != V137_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V137_VERIFICATION_SHA256
        or verification.get("verification_id") != V137_VERIFICATION_ID
        or verification.get("dictionary_id") != V137_DICTIONARY_ID
        or verification.get("producer_free_full_and_leave_one_cohort_search")
        is not True
        or verification.get("producer_free_auto_calibration_reconstruction")
        is not True
    ):
        _fail("V138 frozen V137 receipt changed")
    source_facts = _source_facts()
    expected_facts = [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != expected_facts:
        _fail("V138 frozen implementation source changed")
    config = campaign_config_v138()
    payload = {
        "schema": "acfqp.heterogeneous_cohort_planning_preregistration.v138",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "v137_final_commit_precedes_v138_target_execution": V137_FINAL_COMMIT,
        "frozen_implementation_source_facts": source_facts,
        "frozen_v137_dictionary": dictionary,
        "frozen_v137_independent_verification": verification,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(config["target_episode_indices"]),
        "target_worker_count": config["target_worker_count"],
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "v137_heterogeneous_cohort_receipt_precedes_target_outcomes": True,
            "incompatible_source_remains_explicitly_excluded": True,
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
            "registered_v138_target_outcome_observed": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    preregistration_id = domains.extension_content_id_v138(
        domains.CONSTRUCTION_K7_HETEROGENEOUS_COHORT_PREREGISTRATION_V138_DOMAIN,
        payload,
    )
    return {**payload, "preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class HeterogeneousCohortPlanningPreregistrationV138:
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
            or domains.extension_content_id_v138(
                domains.CONSTRUCTION_K7_HETEROGENEOUS_COHORT_PREREGISTRATION_V138_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V138 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_heterogeneous_cohort_planning_preregistration_v138(
    dictionary_raw: bytes, verification_raw: bytes
) -> HeterogeneousCohortPlanningPreregistrationV138:
    document = _document(dictionary_raw, verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V138 frozen preregistration changed")
    return HeterogeneousCohortPlanningPreregistrationV138(_ISSUER, raw, identity)


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v138",
    "freeze_heterogeneous_cohort_planning_preregistration_v138",
)
