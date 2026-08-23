"""Outcome-free fresh successor preregistration for V175r1."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v175r1 as domains
from acfqp.certificate_delta_invalidation_campaign_core_v175r1 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    certificate_delta_invalidation_campaign_config_v175r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("8054c7a",)
TARGET_OCCURRENCES = (
    (PACKET_FAMILY, 1_139_861),
    (PACKET_FAMILY, 1_139_862),
    (RESERVOIR_FAMILY, 1_149_861),
    (RESERVOIR_FAMILY, 1_149_862),
)
TARGET_EPISODE_INDICES = (1_045, 1_046, 1_047, 1_048)
TARGET_WORKER_COUNT = 2
ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v175r1.py",
        1_541,
        "b3caa7634c15c31da0494962da7b49af44da372d63b5712546e2de5c6408884c",
    ),
    (
        "src/acfqp/certificate_delta_invalidation_campaign_core_v175r1.py",
        4_088,
        "7760e145368e6e89d7546f070476868d51e78404bad96d7a7777a66cc439fa43",
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
    (
        "v175_certificate_delta_invalidation_preregistration.json",
        3_625,
        "c1631d6259e1ee5978b4cf0b6c098f0d8ecd3331fe3b85709df8ac8b030cac1b",
        "preregistration_id",
        "40d357786fc0f8921c76198c868b6b497fe066791edea086a4a0c1920399a076",
    ),
    (
        "v175_certificate_delta_invalidation_failure.json",
        1_812,
        "323f55deb1287dacff7df3759a54be54b5325d0fecf9715189b5f6ae15140dcd",
        "failure_id",
        "431ac86701677586b6b8a95a75a7b9153941a75f7581703edec1637da8e0e476",
    ),
)
PREREGISTRATION_ID = "6c0a89a8267f87ed18e2e898c74eb94c6f4e5c3b0f98f5090c4e48cb23b00ff8"
EXPECTED_CANONICAL_BYTE_COUNT = 4_894
EXPECTED_CANONICAL_SHA256 = "90020a85870fcdb960613daccab47790964814fc927d632c95099577d600a691"


class ConstructionK7CertificateDeltaInvalidationPreregistrationV175R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateDeltaInvalidationPreregistrationV175R1Error(
        message
    )


def campaign_config_v175r1():
    config = certificate_delta_invalidation_campaign_config_v175r1()
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
        _fail(f"V175r1 frozen input changed: {name}")
    return document


def build_certificate_delta_invalidation_preregistration_v175r1():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail(f"V175r1 implementation changed before outcomes: {path}")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    inputs = [_frozen_input(row) for row in FROZEN_INPUTS]
    classifier, _, bank_verification, v174, v174_verification, v175_pre, failure = inputs
    if not (
        classifier["schema"] == "acfqp.paid_path_prefix_classifier_receipt.v161"
        and bank_verification["bank_id"] == inputs[1]["bank_id"]
        and v174["registered_gate"]["passed"] is True
        and v174_verification["producer_free_minimal_invalidation_reconstruction"]
        is True
        and failure["preregistration_id"] == v175_pre["preregistration_id"]
        and failure["same_preregistration_identity_may_be_rerun"] is False
        and failure["fresh_successor_identity_required"] is True
        and failure["target_outcomes_accessed"] is False
    ):
        _fail("V175r1 frozen successor boundary changed")
    config = campaign_config_v175r1()
    payload = {
        "schema": "acfqp.certificate_delta_invalidation_preregistration.v175r1",
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
        "corrected_classifier_receipt": {
            "schema": classifier["schema"],
            "classifier_receipt_id": classifier["classifier_receipt_id"],
        },
        "preserved_failed_v175": {
            "preregistration_id": v175_pre["preregistration_id"],
            "failure_id": failure["failure_id"],
            "same_identity_rerun_forbidden": True,
        },
        "target_occurrences": [
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": len(TARGET_OCCURRENCES),
        "registered_gate": {
            "correct_v161_classifier_fixed_before_target_outcomes": True,
            "fresh_successor_identity_after_v175_failure": True,
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
        "preregistration_id": domains.extension_content_id_v175r1(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V175R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateDeltaInvalidationPreregistrationV175R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_certificate_delta_invalidation_preregistration_v175r1():
    document = build_certificate_delta_invalidation_preregistration_v175r1()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V175r1 frozen preregistration changed")
    return CertificateDeltaInvalidationPreregistrationV175R1(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v175r1",
    "freeze_certificate_delta_invalidation_preregistration_v175r1",
)
