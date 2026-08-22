"""Outcome-free preregistration for the V168 receipt-totalized fifth family."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v168 as domains
from acfqp.fifth_family_total_plan_receipt_set_campaign_core_v168 import (
    PACKET_BATCHING_FAMILY,
    V166_FAILURE_ID,
    V167_CAMPAIGN_BYTE_COUNT,
    V167_CAMPAIGN_ID,
    V167_CAMPAIGN_SHA256,
    fifth_family_total_plan_receipt_set_campaign_config_v168,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("9d91f7c",)
TARGET_OCCURRENCES = (
    (PACKET_BATCHING_FAMILY, 1_049_851),
    (PACKET_BATCHING_FAMILY, 1_049_852),
)
TARGET_EPISODE_INDICES = (953, 954, 955, 956)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
V167_VERIFICATION_ID = (
    "c45e31ec1b25c87398361fedd04d5c96d9b05a95d465592a85bef7d2af4b6dd8"
)
V167_VERIFICATION_BYTE_COUNT = 28_646
V167_VERIFICATION_SHA256 = (
    "f850ae07d362acceb59732ce2fe4a163e86aa5e4d1071c4aa2a7b6683fbf9a6f"
)
PREREGISTRATION_ID = (
    "0857616c9066fef7c2502827b8ffb337848dbf230d61aa436555b3c0dde2bc89"
)
EXPECTED_CANONICAL_BYTE_COUNT = 3_041
EXPECTED_CANONICAL_SHA256 = (
    "a6896bcca48ec67c3ed8963dab50f552da9f42c81343c280b16a7c7174f76f9c"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/fifth_family_total_plan_receipt_set_campaign_core_v168.py",
        15_057,
        "1c54ea87e9f8d05617af584ab6dc81e333d9ea5f3d8e489bbe2fc4c68d818a70",
    ),
    (
        "src/acfqp/applicable_plan_receipt_set_sequence_v168.py",
        6_316,
        "96c80840af2bd548492c23df06605703ea4ac6b037696dff9d3ec5e88e48a637",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v168.py",
        1_703,
        "af6e7524e1720e4b845a6fd30a42138555a726237d523d2eaeceb287ccacb738",
    ),
)


class ConstructionK7FifthFamilyTotalPlanReceiptSetPreregistrationV168Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyTotalPlanReceiptSetPreregistrationV168Error(
        message
    )


def campaign_config_v168():
    config = fifth_family_total_plan_receipt_set_campaign_config_v168()
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _frozen(name, *, count, digest, identity_key, identity):
    raw = (SOURCE_ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail("V168 frozen V167 predecessor changed")
    return document


def _document():
    source_facts = []
    for path, count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V168 implementation changed before target outcomes")
        source_facts.append(
            {"relative_path": path, "byte_count": count, "sha256": digest}
        )
    predecessor = _frozen(
        "v167_fourth_family_plan_mode_set_campaign.json",
        count=V167_CAMPAIGN_BYTE_COUNT,
        digest=V167_CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=V167_CAMPAIGN_ID,
    )
    verification = _frozen(
        "v167_fourth_family_plan_mode_set_verification.json",
        count=V167_VERIFICATION_BYTE_COUNT,
        digest=V167_VERIFICATION_SHA256,
        identity_key="verification_id",
        identity=V167_VERIFICATION_ID,
    )
    if not (
        predecessor["registered_gate"]["passed"] is True
        and verification[
            "fourth_family_factor_prior_sample_tax_transfer_independently_verified"
        ]
        is True
        and predecessor["failed_v166_attempt_id"] == V166_FAILURE_ID
    ):
        _fail("V168 predecessor claim boundary changed")
    config = campaign_config_v168()
    payload = {
        "schema": "acfqp.fifth_family_total_plan_receipt_set_preregistration.v168",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_v167_campaign": {
            "campaign_id": V167_CAMPAIGN_ID,
            "byte_count": V167_CAMPAIGN_BYTE_COUNT,
            "sha256": V167_CAMPAIGN_SHA256,
        },
        "frozen_v167_independent_verification": {
            "verification_id": V167_VERIFICATION_ID,
            "byte_count": V167_VERIFICATION_BYTE_COUNT,
            "sha256": V167_VERIFICATION_SHA256,
        },
        "receipt_set_totalization": {
            "finite_classes": ["DIRECT_ONLY", "MEMOIZED_ONLY", "MIXED", "NONE"],
            "mixed_semantics": "TEMPORALLY_DISTINCT_RECEIPTS_NOT_COMPETING_ACTIONS",
            "none_semantics": "NO_REGISTERED_COMPILED_PROGRAM_RECEIPT_V109_AND_QUERY_LOCAL_CERTIFICATE_REMAIN_REQUIRED",
            "empty_set_is_failure": False,
            "planner_dynamics_changed": False,
            "execution_policy_changed": False,
            "v109_and_certificate_safety_boundary_changed": False,
        },
        "target_occurrences": [
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": config["families"][
            PACKET_BATCHING_FAMILY
        ]["maximum_acquisition_labels"],
        "registered_gate": {
            "fresh_target_identities_fixed_before_target_outcomes": True,
            "frozen_v167_campaign_and_verification_preserved": True,
            "exactly_two_fresh_packet_batching_occurrences_required": True,
            "direct_memoized_mixed_and_none_receipt_sets_admissible": True,
            "none_requires_v109_receipts_and_query_local_certificate": True,
            "all_executed_actions_require_v109_receipts": True,
            "receipt_set_annotation_is_not_model_planning_or_certificate_authority": True,
            "query_policy_and_factor_prior_noninferior_required": True,
            "both_arm_receding_planning_and_certificate_local_recovery_required": True,
            "sample_execution_derivation_and_planning_axes_separate": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "v168_fifth_family_transfer_observed": False,
            "mixed_or_none_frequency_claimed_before_outcomes": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v168(
            domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V168_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyTotalPlanReceiptSetPreregistrationV168:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_fifth_family_total_plan_receipt_set_preregistration_v168():
    document = _document()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and not (
        document["preregistration_id"] == PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V168 frozen target preregistration changed")
    return FifthFamilyTotalPlanReceiptSetPreregistrationV168(
        _ISSUER, raw, document["preregistration_id"]
    )


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_OCCURRENCES",
    "campaign_config_v168",
    "freeze_fifth_family_total_plan_receipt_set_preregistration_v168",
)
