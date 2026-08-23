"""Outcome-free preregistration for V178 indexed lazy invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v178 as domains
from acfqp.indexed_lazy_invalidation_campaign_core_v178 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    indexed_lazy_invalidation_campaign_config_v178,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("ad433be",)
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_180_851),
    (PACKET_FAMILY, 1_180_852),
    (RESERVOIR_FAMILY, 1_190_851),
    (RESERVOIR_FAMILY, 1_190_852),
)
TARGET_EPISODE_INDICES = (1_063, 1_064, 1_065, 1_066)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v178.py",
        1_954,
        "5772ad01e1cbba0b122259843c5f5be58c65ca60041a424d10f040076964fa99",
    ),
    (
        "src/acfqp/indexed_lazy_invalidation_sequence_v178.py",
        25_687,
        "2f5663a73dd256df6a2458b695e1ee103e9f2fc24d06010b38b8612b3b888d31",
    ),
    (
        "src/acfqp/indexed_lazy_invalidation_campaign_core_v178.py",
        18_576,
        "695dad02f320fff608df69e67d84d48e5f7fef6d85083084c83284cc1abd7398",
    ),
)
FROZEN_INPUTS = (
    (
        "v161_paid_path_prefix_classifier_receipt.json",
        383_778,
        "ac6ae1dfe458cd4d818f4acb3c9ba77f829787ee1f57c8fdcd8e379c118267df",
        "classifier_receipt_id",
        "893a5b0597fe2c9d0544defcf3655ce6e186950e7c1342a7a7502de0d4f1378d",
    ),
    (
        "v146_anonymous_relational_factor_bank.json",
        4_033,
        "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6",
        "bank_id",
        "78bb4dae4682ed0cedb7a7781caca4af04986f0db86d7086a0786166d07020b5",
    ),
    (
        "v146_anonymous_relational_factor_bank_verification.json",
        1_028,
        "891b48ce7d035ea8e56f68a3e3dc6a8838cbd62dfabf7af6a86a5d81f14a7e80",
        "verification_id",
        "7531dcc153b64ba8c23ae70fce84650b0be0550acaf3db915b106adf2bd6e63b",
    ),
    (
        "v177_reverse_index_only_invalidation_campaign.json",
        51_141_161,
        "0eb4c40eac1869ba85b24bb578eb746a37ae56d1f170ad21876bdeb8413dd478",
        "campaign_id",
        "cf9e0bf64ba285d3b1873e5d48636a4de0e68006d7c3e43d761ebbf4a9d5f985",
    ),
    (
        "v177_reverse_index_only_invalidation_verification.json",
        3_611,
        "2d63f83a8ce12a200721107692768ff1e49f96d479e7d2809d35d9c4e8f1180d",
        "verification_id",
        "1f062589b9db53758691431dec327c0d303f20d06bd6b44c647eca02a11c76dd",
    ),
)
PREREGISTRATION_ID = "da7939cef8c26aa65e89de68d2114b76328f54bd4a5a2c2c80caeea213e9fd8a"
EXPECTED_CANONICAL_BYTE_COUNT = 4_349
EXPECTED_CANONICAL_SHA256 = "5743505ac94e7c3564ea81d402fc282e32a078b17991cba591db1db4c307ab04"


class ConstructionK7IndexedLazyInvalidationPreregistrationV178Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7IndexedLazyInvalidationPreregistrationV178Error(message)


def campaign_config_v178():
    config = indexed_lazy_invalidation_campaign_config_v178()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=len(TARGET_OCCURRENCES),
    )
    return config


def _frozen_input(row):
    name, count, digest, identity_key, identity = row
    raw = (ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V178 frozen input changed: {name}")
    return document


def build_indexed_lazy_invalidation_preregistration_v178():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V178 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    classifier, bank, bank_verification, predecessor, verification = [
        _frozen_input(row) for row in FROZEN_INPUTS
    ]
    if not (
        classifier["schema"] == "acfqp.paid_path_prefix_classifier_receipt.v161"
        and bank_verification["bank_id"] == bank["bank_id"]
        and predecessor["registered_gate"]["passed"] is True
        and predecessor["accounting"]["production_full_graph_diff_checks"] == 0
        and predecessor["accounting"][
            "production_live_dependency_projection_scan_count"
        ]
        == 0
        and predecessor["accounting"]["production_prior_receipt_event_scan_count"]
        > 0
        and predecessor["accounting"]["retained_authorization_metadata_updates"]
        > 0
    ):
        _fail("V178 frozen input boundary changed")
    if not (
        verification["campaign_id"] == predecessor["campaign_id"]
        and verification["verified_production_full_graph_diff_checks"] == 0
        and verification["verified_production_live_dependency_projection_scan_count"]
        == 0
        and verification["producer_free_reverse_dependency_index_reconstruction"]
        is True
    ):
        _fail("V178 predecessor verification boundary changed")
    config = campaign_config_v178()
    payload = {
        "schema": "acfqp.indexed_lazy_invalidation_preregistration.v178",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_input_facts": [
            {
                "name": row[0],
                "byte_count": row[1],
                "sha256": row[2],
                row[3]: row[4],
            }
            for row in FROZEN_INPUTS
        ],
        "target_occurrences": [
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": len(TARGET_OCCURRENCES),
        "registered_gate": {
            "certificate_delta_required_for_every_episode": True,
            "delta_transition_join_required_for_every_nonterminal_epoch": True,
            "zero_serialized_full_graph_scan_on_decision_path_required": True,
            "zero_production_full_graph_diff_control_required": True,
            "zero_production_live_dependency_projection_scan_required": True,
            "zero_production_prior_receipt_event_scan_required": True,
            "zero_eager_retained_authorization_update_required": True,
            "lazy_authorization_receipt_and_issuance_join_required": True,
            "graph_and_program_receipt_reverse_indices_required": True,
            "producer_free_dependency_and_full_graph_controls_required": True,
            "selective_graph_invalidation_required": True,
            "unaffected_graph_dependency_retention_required": True,
            "exact_compiled_state_invalidation_required": True,
            "incremental_revalidation_without_per_hit_rescan_required": True,
            "all_four_online_plan_sources_required": True,
            "every_execution_joined_to_prior_online_receipt_required": True,
            "factor_prior_strict_label_reduction_each_occurrence_required": True,
            "query_policy_noninferiority_each_occurrence_required": True,
            "certificate_failure_only_local_ground_distinctions_required": True,
            "producer_free_reconstruction_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "indexed_lazy_invalidation_observed": False,
            "factor_prior_sample_tax_reduction_observed": False,
            "indexed_lazy_invalidation_changes_selected_action_order": False,
            "indexed_lazy_invalidation_is_model_or_safety_authority": False,
            "query_local_exact_overlay_remains_only_safety_authority": True,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "maximum_acquisition_labels_by_family": {
            family: config["families"][family]["maximum_acquisition_labels"]
            for family in (PACKET_FAMILY, RESERVOIR_FAMILY)
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v178(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V178_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class IndexedLazyInvalidationPreregistrationV178:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_indexed_lazy_invalidation_preregistration_v178():
    document = build_indexed_lazy_invalidation_preregistration_v178()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V178 frozen preregistration changed")
    return IndexedLazyInvalidationPreregistrationV178(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v178",
    "freeze_indexed_lazy_invalidation_preregistration_v178",
)
