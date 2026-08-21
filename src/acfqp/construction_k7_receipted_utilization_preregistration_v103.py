"""Outcome-free preregistration for receipt-complete utilization V103."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v103 as domains
from acfqp import construction_k7_family_wide_utilization_preregistration_v102 as previous
from acfqp.construction_k7_family_wide_utilization_campaign_v102 import (
    CAMPAIGN_ID as V102_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V102_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_family_wide_utilization_independent_verifier_v102 import (
    EXPECTED_CANONICAL_SHA256 as V102_VERIFICATION_SHA256,
    VERIFICATION_ID as V102_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

IMPLEMENTATION_COMMITS = ("5564c66", "4bcbad0", "1910932")
PREREGISTRATION_ID = "ac9d7759187a8d97edeeab924210dc066dc47f5dc6eff144954ecc1cf25516c3"
EXPECTED_CANONICAL_BYTE_COUNT = 8_637
EXPECTED_CANONICAL_SHA256 = "61c311e40c49ecbd1a47ed58a7836faa641a55a3c7a0ef3d091088894f02e8eb"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_015_101),
    ("BALANCED_BATCH_REFINEMENT", 1_015_102),
    ("MAINTENANCE_CASCADE", 1_015_103),
    ("MAINTENANCE_CASCADE", 1_015_104),
)
TARGET_EPISODE_INDICES = (121, 122, 123)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v103.py",
        1406,
        "d2fa267a99b043e5b84ef492363e5f81b9dd930444a0585e9de0475eab94c413",
    ),
    (
        "src/acfqp/generic_abstract_execution_receipt_v103.py",
        4047,
        "260ebd31e62eb136d44d59a953b80b3549153ef3da85479b4f67e6fe7b528634",
    ),
    (
        "src/acfqp/generic_receipted_online_certificate_planner_v103.py",
        20161,
        "0cb516df70f5a54ce0ee40c71cb4fa21cc30b56c1a8f82c2a16edac3556bf846",
    ),
    (
        "src/acfqp/generic_receipted_preloaded_certificate_engine_v103.py",
        13798,
        "dde7a1bfee12e67b9426f68d44e4a67e83f8249fb1a4b871bfe7888accb812c5",
    ),
    (
        "src/acfqp/generic_persistent_receipted_sequence_v103.py",
        15161,
        "0cbc0d6523e01993e2a0905c3c40b60656ab585af402195b7b3665007f630104",
    ),
    (
        "src/acfqp/receipted_abstract_utilization_campaign_core_v103.py",
        11863,
        "d6e0742cdc8bcfb2844056ac3e30511b2d95e385835d534a45d44ab7a6ad3313",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7ReceiptedUtilizationPreregistrationV103Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReceiptedUtilizationPreregistrationV103Error(message)


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v103() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v102())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        required_target_families=REQUIRED_TARGET_FAMILIES,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.receipted_utilization_preregistration.v103",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v102_campaign_id": V102_CAMPAIGN_ID,
            "v102_campaign_sha256": V102_CAMPAIGN_SHA256,
            "v102_verification_id": V102_VERIFICATION_ID,
            "v102_verification_sha256": V102_VERIFICATION_SHA256,
            "v102_campaign_declared_gate_passed": True,
            "v102_gate_independently_verified": False,
            "v102_evidence_gap_retained_without_correction": True,
            "source_library_artifact_id": previous.previous.previous.SOURCE_LIBRARY_ARTIFACT_ID,
            "v62_residual_library_id": previous.previous.previous.V62_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v103_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V103),
            "frozen_before_any_registered_v103_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v103()["target_occurrences"],
            "target_seeds_unique": len({seed for _family, seed in TARGET_OCCURRENCES})
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "v103_changes_measurement_evidence_not_planning_policy": True,
            "every_executed_action_requires_an_independent_receipt": True,
            "receipt_binds_episode_decision_state_action_proposal_and_shield": True,
            "utilization_must_be_rederived_without_producer_summary_counts": True,
            "every_occurrence_requires_receipted_abstract_execution_strict_majority": True,
            "every_family_requires_both_accept_and_disagreement_paths": True,
            "exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_action_receipt_replays_independently": True,
            "every_occurrence_receipted_abstract_matches_strict_majority": True,
            "every_target_family_exercises_both_shield_paths": True,
            "aggregate_activation_sample_tax_strictly_reduced": True,
            "aggregate_meta_task_labels_not_above_no_prior": True,
            "aggregate_meta_task_labels_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count_per_arm": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "activation_labels_use_right_censoring": True,
            "meta_no_prior_and_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_shield_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v103_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_multistep_execution_primarily_abstract_ordered_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v103(
            domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_PREREGISTRATION_V103_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReceiptedUtilizationPreregistrationV103:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v103(
                domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_PREREGISTRATION_V103_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V103 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ReceiptedUtilizationPreregistrationV103 | None = None


def freeze_receipted_utilization_preregistration_v103() -> ReceiptedUtilizationPreregistrationV103:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V103 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V103 frozen preregistration changed")
        _CACHE = ReceiptedUtilizationPreregistrationV103(_ISSUER, raw, identity)
    return _CACHE


def verify_receipted_utilization_preregistration_v103(
    value: Any,
) -> ReceiptedUtilizationPreregistrationV103:
    if type(value) is not ReceiptedUtilizationPreregistrationV103:
        _fail("V103 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_receipted_utilization_preregistration_v103()
    if value is not expected:
        _fail("V103 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v103",
    "freeze_receipted_utilization_preregistration_v103",
    "verify_receipted_utilization_preregistration_v103",
)
