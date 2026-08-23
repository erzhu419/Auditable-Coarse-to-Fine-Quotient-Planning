"""Outcome-free preregistration for V176 verifier-deferred controls."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v176 as domains
from acfqp.certificate_delta_only_invalidation_campaign_core_v176 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    certificate_delta_only_invalidation_campaign_config_v176,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("db5cb2b",)
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_159_851),
    (PACKET_FAMILY, 1_159_852),
    (RESERVOIR_FAMILY, 1_169_851),
    (RESERVOIR_FAMILY, 1_169_852),
)
TARGET_EPISODE_INDICES = (1_049, 1_050, 1_051, 1_052)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v176.py",
        1_732,
        "e92e9dfc3788434786e07c07954bc3919824a3a1c13455f44112372eff58300c",
    ),
    (
        "src/acfqp/certificate_delta_only_invalidation_sequence_v176.py",
        16_157,
        "481c7c6eefdac868f445afe137dcfd3360cb153e33e86fe0b843fda3b4140cd6",
    ),
    (
        "src/acfqp/certificate_delta_only_invalidation_campaign_core_v176.py",
        15_544,
        "9d6a9e75826ad5a32029def5955ad9275c9ca9f18f106fcf221d87b63924c0a1",
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
        "v175r1_certificate_delta_invalidation_campaign.json",
        59_473_200,
        "31f4846627ed9750401b13a906dbc91b3242506c43e7df61fc3a14b7e4b2edf2",
        "campaign_id",
        "6552685740a9244d3a9b77c3bfdf78ce065cc98bbc8f2348cf0826c247c72f63",
    ),
    (
        "v175r1_certificate_delta_invalidation_verification.json",
        2_978,
        "31470c5194dac8c59086b86a6e269a7a555746895b4d61239ae34024f3ebf85c",
        "verification_id",
        "bd5276748e2e136381c2058ff5c9f95c6ca55e4a1faf03cf43adbb48878240c0",
    ),
)
PREREGISTRATION_ID = "17ae62ef1856f0cec6ea2c342d03e61fea3f7f6cb4b49e05b104c2d8b3cd0ac0"
EXPECTED_CANONICAL_BYTE_COUNT = 4_069
EXPECTED_CANONICAL_SHA256 = "eccdf3750fe6f647ea029371f07fd18c04ed11f3edb8b91f783c36c9852d7769"


class ConstructionK7CertificateDeltaOnlyInvalidationPreregistrationV176Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateDeltaOnlyInvalidationPreregistrationV176Error(
        message
    )


def campaign_config_v176():
    config = certificate_delta_only_invalidation_campaign_config_v176()
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
        _fail(f"V176 frozen input changed: {name}")
    return document


def build_certificate_delta_only_invalidation_preregistration_v176():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V176 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    inputs = [_frozen_input(row) for row in FROZEN_INPUTS]
    classifier, bank, bank_verification, predecessor, verification = inputs
    if not (
        classifier["schema"] == "acfqp.paid_path_prefix_classifier_receipt.v161"
        and bank_verification["bank_id"] == bank["bank_id"]
        and predecessor["registered_gate"]["passed"] is True
        and predecessor["accounting"]["full_graph_control_checks"] > 0
    ):
        _fail("V176 frozen input boundary changed")
    if not (
        verification["producer_free_certificate_delta_reconstruction"] is True
        and verification[
            "delta_frontier_full_diff_control_equality_independently_verified"
        ]
        is True
    ):
        _fail("V176 predecessor verification boundary changed")
    config = campaign_config_v176()
    payload = {
        "schema": "acfqp.certificate_delta_only_invalidation_preregistration.v176",
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
            "producer_free_full_graph_diff_control_required": True,
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
            "certificate_delta_only_invalidation_observed": False,
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
        "preregistration_id": domains.extension_content_id_v176(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V176_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateDeltaOnlyInvalidationPreregistrationV176:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_certificate_delta_only_invalidation_preregistration_v176():
    document = build_certificate_delta_only_invalidation_preregistration_v176()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V176 frozen preregistration changed")
    return CertificateDeltaOnlyInvalidationPreregistrationV176(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v176",
    "freeze_certificate_delta_only_invalidation_preregistration_v176",
)
