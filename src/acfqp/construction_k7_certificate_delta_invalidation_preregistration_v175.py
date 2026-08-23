"""Outcome-free preregistration for V175 certificate-delta invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v175 as domains
from acfqp.certificate_delta_invalidation_campaign_core_v175 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    certificate_delta_invalidation_campaign_config_v175,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("f697b09",)
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_139_851),
    (PACKET_FAMILY, 1_139_852),
    (RESERVOIR_FAMILY, 1_149_851),
    (RESERVOIR_FAMILY, 1_149_852),
)
TARGET_EPISODE_INDICES = (1_041, 1_042, 1_043, 1_044)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v175.py",
        1_783,
        "ac90f2093883d6ab61703861caa89d23e88916e8165cfd1794e2eb0b0e3d0036",
    ),
    (
        "src/acfqp/certificate_delta_driven_invalidation_sequence_v175.py",
        19_395,
        "278e61002fb1fe0b3a490b5cccd3574b9eaddd45ac4e6274c6428c78ee2e695b",
    ),
    (
        "src/acfqp/certificate_delta_invalidation_campaign_core_v175.py",
        17_855,
        "4324ba7f41d0129b547fe5a76cc83f4019aabdfc638c3f39f7af41976f7300c2",
    ),
)
FROZEN_PREDECESSORS = (
    (
        "v174_receipt_driven_invalidation_campaign.json",
        54_036_308,
        "23453500dd9b80213fb01b657eba323a957ef8063503f756bf6df82463754d9a",
        "campaign_id",
        "0e5c03c7252ea5b11e5819cbe0b11917ac90722f988969a8b55ef6f446c123ec",
    ),
    (
        "v174_receipt_driven_invalidation_verification.json",
        2_617,
        "64e01b82ff142a5ed784cb170b73bb016f98949939139ac6e4d339fa3039f0a0",
        "verification_id",
        "3fbd91146f5eacd92ec309a88634071ea983699ea1efe2d40bd5c078b60593ae",
    ),
)
PREREGISTRATION_ID = "40d357786fc0f8921c76198c868b6b497fe066791edea086a4a0c1920399a076"
EXPECTED_CANONICAL_BYTE_COUNT = 3_625
EXPECTED_CANONICAL_SHA256 = "c1631d6259e1ee5978b4cf0b6c098f0d8ecd3331fe3b85709df8ac8b030cac1b"


class ConstructionK7CertificateDeltaInvalidationPreregistrationV175Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateDeltaInvalidationPreregistrationV175Error(
        message
    )


def campaign_config_v175():
    config = certificate_delta_invalidation_campaign_config_v175()
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
        _fail(f"V175 frozen predecessor changed: {name}")
    return document


def build_certificate_delta_invalidation_preregistration_v175():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V175 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessors = [_frozen_predecessor(row) for row in FROZEN_PREDECESSORS]
    if not (
        predecessors[0]["registered_gate"]["passed"] is True
        and predecessors[1]["producer_free_minimal_invalidation_reconstruction"]
        is True
        and predecessors[1][
            "producer_free_incremental_revalidation_chain_reconstruction"
        ]
        is True
    ):
        _fail("V175 predecessor gate changed")
    config = campaign_config_v175()
    payload = {
        "schema": "acfqp.certificate_delta_invalidation_preregistration.v175",
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
        "registered_delta_dependency_roles": {
            PACKET_FAMILY: "DELTA_GRAPH_AND_COMPILED_INVALIDATION",
            RESERVOIR_FAMILY: "DELTA_RETENTION_AND_INCREMENTAL_REVALIDATION",
        },
        "registered_gate": {
            "fresh_cross_family_identities_fixed_before_outcomes": True,
            "certificate_delta_required_for_every_episode": True,
            "delta_transition_join_required_for_every_nonterminal_epoch": True,
            "zero_serialized_full_graph_scan_on_decision_path_required": True,
            "delta_frontier_must_match_uncharged_full_diff_control": True,
            "positive_full_graph_diff_compute_removal_required": True,
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
            "certificate_delta_driven_invalidation_observed": False,
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
        "preregistration_id": domains.extension_content_id_v175(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V175_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateDeltaInvalidationPreregistrationV175:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_certificate_delta_invalidation_preregistration_v175():
    document = build_certificate_delta_invalidation_preregistration_v175()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V175 frozen preregistration changed")
    return CertificateDeltaInvalidationPreregistrationV175(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v175",
    "freeze_certificate_delta_invalidation_preregistration_v175",
)
