"""Outcome-free preregistration for V177 reverse-index invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v177 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.reverse_index_only_invalidation_campaign_core_v177 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    reverse_index_only_invalidation_campaign_config_v177,
)


IMPLEMENTATION_COMMITS = ("42e19e7",)
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_179_851),
    (PACKET_FAMILY, 1_179_852),
    (RESERVOIR_FAMILY, 1_189_851),
    (RESERVOIR_FAMILY, 1_189_852),
)
TARGET_EPISODE_INDICES = (1_053, 1_054, 1_055, 1_056)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v177.py",
        1_748,
        "68320aa541a4c85d6f33391cae962c8282aec97834868260760d11de9840491e",
    ),
    (
        "src/acfqp/reverse_index_only_invalidation_sequence_v177.py",
        13_623,
        "364d26d87085699b968f57b72e4438a081d772be5a4abe4e8872e2bf16fe6479",
    ),
    (
        "src/acfqp/reverse_index_only_invalidation_campaign_core_v177.py",
        16_524,
        "db45048068700729169584d3632dc06fd802b95c48dd5bb78a1becb44a178407",
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
        "v176_certificate_delta_only_invalidation_campaign.json",
        54_909_728,
        "c3f26e3508600ccef9f92d7461316e951aa3ae15d30bba89911a8c4353fcbffc",
        "campaign_id",
        "8d6d1348e67084b449debf5671cb568eb6b048eb56358bf3bbe20c4161255953",
    ),
    (
        "v176_certificate_delta_only_invalidation_verification.json",
        3_240,
        "58673e7b2ee7578a4ded651bbb46d9f9f2aa25a14dba37d4e8430663418107a4",
        "verification_id",
        "ac6b3a604c49423cbac35154bf1a0dbea15b65e6723e9471bd9990822de1968f",
    ),
)
PREREGISTRATION_ID = "cf84908966e68f5cb8f7a344aa44521564a0d8231b6e588c9f3c621adc2e9414"
EXPECTED_CANONICAL_BYTE_COUNT = 4_260
EXPECTED_CANONICAL_SHA256 = "2348808e08169b9a7c0369633b7d2e37d47a7fe725993ee3769b4134b00311a3"


class ConstructionK7ReverseIndexOnlyInvalidationPreregistrationV177Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReverseIndexOnlyInvalidationPreregistrationV177Error(
        message
    )


def campaign_config_v177():
    config = reverse_index_only_invalidation_campaign_config_v177()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
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
        _fail(f"V177 frozen input changed: {name}")
    return document


def build_reverse_index_only_invalidation_preregistration_v177():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V177 implementation changed before outcomes: {path}")
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
    ):
        _fail("V177 frozen input boundary changed")
    if not (
        verification["verified_production_full_graph_diff_checks"] == 0
        and verification["verified_producer_free_full_graph_diff_control_checks"]
        > 0
        and verification[
            "delta_frontier_full_diff_control_equality_independently_verified"
        ]
        is True
    ):
        _fail("V177 predecessor verification boundary changed")
    config = campaign_config_v177()
    payload = {
        "schema": "acfqp.reverse_index_only_invalidation_preregistration.v177",
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
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
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
            "reverse_index_only_invalidation_selection_required": True,
            "retained_authorization_metadata_updates_separately_accounted": True,
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
            "reverse_index_only_invalidation_observed": False,
            "factor_prior_sample_tax_reduction_observed": False,
            "delta_invalidation_changes_selected_action_order": False,
            "delta_invalidation_is_model_or_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v177(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V177_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReverseIndexOnlyInvalidationPreregistrationV177:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_reverse_index_only_invalidation_preregistration_v177():
    document = build_reverse_index_only_invalidation_preregistration_v177()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V177 frozen preregistration changed")
    return ReverseIndexOnlyInvalidationPreregistrationV177(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v177",
    "freeze_reverse_index_only_invalidation_preregistration_v177",
)
