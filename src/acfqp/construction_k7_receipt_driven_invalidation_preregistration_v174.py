"""Outcome-free preregistration for V174 receipt-driven invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v174 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.receipt_driven_invalidation_campaign_core_v174 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    receipt_driven_invalidation_campaign_config_v174,
)


IMPLEMENTATION_COMMITS = ("7cbac32", "f7e8558")
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_119_851),
    (PACKET_FAMILY, 1_119_852),
    (RESERVOIR_FAMILY, 1_129_851),
    (RESERVOIR_FAMILY, 1_129_852),
)
TARGET_EPISODE_INDICES = (1_033, 1_034, 1_035, 1_036)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v174.py",
        1_958,
        "93aed044c0d29a64c6ab95b3a655fe61ad3008e2fb9e757f0ceb40181015bb25",
    ),
    (
        "src/acfqp/receipt_driven_minimal_invalidation_sequence_v174.py",
        33_348,
        "c6e435d5a9529481bd66814e350222105a7ff1f37c8886d5ddeba11aed763e37",
    ),
    (
        "src/acfqp/receipt_driven_invalidation_campaign_core_v174.py",
        17_714,
        "2ae0d45037c791516c60d2ab68767354af8445c9614c8da8010904bbdcf3906d",
    ),
)
FROZEN_PREDECESSORS = (
    (
        "v173r1_cross_family_branch_complete_campaign.json",
        37_582_314,
        "ab871f3c8ecb6a19a8876458bb7c7e68737e7493489b89723191587d8219be46",
        "campaign_id",
        "418dc59c44243cb96e275539f564b1cd651664c9af19538d75f675093b8f2840",
    ),
    (
        "v173r1_cross_family_branch_complete_verification.json",
        2_012,
        "bf07867857aea2089def3b57ff99b068a9152ef92c1e8a6d03df284be79faf8f",
        "verification_id",
        "223891b22ccd29e9fb8386b182e6ee1226933b33e5d9e00defe8acf8bdd7a125",
    ),
)
PREREGISTRATION_ID = "ca6f465efb4c9c33424aeb66b6957d58384d0e46324934fd88ac1e6bf6628705"
EXPECTED_CANONICAL_BYTE_COUNT = 3_413
EXPECTED_CANONICAL_SHA256 = "798702f1b75dd3d39be72ee11eeb6e57b64fb6f4f3ba6bc391aeefd9e7582559"


class ConstructionK7ReceiptDrivenInvalidationPreregistrationV174Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReceiptDrivenInvalidationPreregistrationV174Error(
        message
    )


def campaign_config_v174():
    config = receipt_driven_invalidation_campaign_config_v174()
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


def _frozen_predecessor(row):
    name, count, digest, identity_key, identity = row
    raw = (ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V174 frozen predecessor changed: {name}")
    return document


def build_receipt_driven_invalidation_preregistration_v174():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V174 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessors = [_frozen_predecessor(row) for row in FROZEN_PREDECESSORS]
    if not (
        predecessors[0]["registered_gate"]["passed"] is True
        and predecessors[1][
            "producer_free_all_four_online_sources_reconstructed"
        ]
        is True
        and predecessors[1][
            "factor_prior_sample_tax_reduction_independently_verified"
        ]
        is True
    ):
        _fail("V174 predecessor gate changed")
    config = campaign_config_v174()
    payload = {
        "schema": "acfqp.receipt_driven_invalidation_preregistration.v174",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_predecessors": [
            {
                "name": row[0],
                "byte_count": row[1],
                "sha256": row[2],
                row[3]: row[4],
            }
            for row in FROZEN_PREDECESSORS
        ],
        "target_occurrences": [
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": len(TARGET_OCCURRENCES),
        "registered_dependency_roles": {
            PACKET_FAMILY: "GRAPH_AND_COMPILED_DEPENDENCY_INVALIDATION",
            RESERVOIR_FAMILY: "UNAFFECTED_DEPENDENCY_RETENTION_AND_REVALIDATION",
        },
        "registered_gate": {
            "fresh_cross_family_identities_fixed_before_outcomes": True,
            "every_plan_requires_pre_return_dependency_projection": True,
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
            "receipt_driven_minimal_invalidation_observed": False,
            "factor_prior_sample_tax_reduction_observed": False,
            "receipt_dependency_lifecycle_changes_selected_action_order": False,
            "receipt_dependency_lifecycle_is_model_or_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v174(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V174_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReceiptDrivenInvalidationPreregistrationV174:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_receipt_driven_invalidation_preregistration_v174():
    document = build_receipt_driven_invalidation_preregistration_v174()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V174 frozen preregistration changed")
    return ReceiptDrivenInvalidationPreregistrationV174(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v174",
    "freeze_receipt_driven_invalidation_preregistration_v174",
)
