"""Outcome-free preregistration for the fresh V157 plan-mode campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v157 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.plan_mode_correction_receipt_v157 import (
    CORRECTION_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CORRECTION_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CORRECTION_RECEIPT_SHA256,
)
from acfqp.plan_mode_margin_campaign_core_v157 import FALLBACK_FAMILY, POSITIVE_FAMILY, structural_margin_campaign_config_v156
from acfqp.structural_margin_query_guard_receipt_v156 import (
    EXPECTED_CANONICAL_BYTE_COUNT as GUARD_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as GUARD_RECEIPT_SHA256,
    GUARD_RECEIPT_ID,
)


IMPLEMENTATION_COMMITS = (
    "c0e69a9c16bb71577a5714ebccd834d649c04922",
    "5a09de69e73bc62334b7130c51388d7cc6d8f8d2",
)
PREREGISTRATION_ID = "ad8bf229ddf8ac19f3364da5b5d385e125e44d878880785ee91150fa7c4ec985"
EXPECTED_CANONICAL_BYTE_COUNT = 6_862
EXPECTED_CANONICAL_SHA256 = "414cfff5081cdafcd7e79ac86ce143291df6d2aa75890b44b3387d2654c00f1f"
TARGET_OCCURRENCES = tuple(
    [(POSITIVE_FAMILY, seed) for seed in range(1_047_811, 1_047_815)]
    + [(FALLBACK_FAMILY, seed) for seed in range(1_047_821, 1_047_825)]
)
TARGET_EPISODE_INDICES = (721, 722, 723, 724)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 8
MAXIMUM_ACQUISITION_LABELS = 1_536
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v157.py", 1_550, "b2ac088ebce123cdb272b60613bbe444201cdd15926ba5193b2ae8b6685be58f"),
    ("src/acfqp/plan_mode_correction_receipt_v157.py", 5_203, "cac277a6a20861ddf9c6a26b407d189ba0ff81d3be147fc46a3c8be959a1aa7a"),
    ("src/acfqp/applicable_plan_mode_sequence_v157.py", 2_671, "7040847c5dc63741ee6eb0c17facdb0473c12423c0a1bbb2193149ae1a3ce40b"),
    ("src/acfqp/plan_mode_margin_campaign_core_v157.py", 10_405, "5cd44303a9f67e125603c5e5a8e56cb7a68a07f4967d077abbf5c0b4bf2631d3"),
    ("src/acfqp/structural_margin_guarded_campaign_core_v156.py", 13_039, "fbce837bb5487e6308f906df19867507d67bc57ad993c2bd3e592550ed593b41"),
    ("src/acfqp/structural_margin_guarded_acquisition_operator_v156.py", 4_788, "da7fc3ad2b96cb83d06aa83d909d66d594f16f2df0397d5f63523e71fa1e5e98"),
    ("src/acfqp/structural_margin_query_guard_receipt_v156.py", 6_823, "e24d6cc84f55bca4f35301e58cf0b6b6d79f0b2dd57e92c0267edcfd23220cca"),
    ("src/acfqp/certified_memoized_planner_sequence_v154.py", 6_600, "60c6b6409bf604385c6fc3f90182841485bd1561b4e06766fda2858154db5cfb"),
)


class ConstructionK7PlanModeMarginPreregistrationV157Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PlanModeMarginPreregistrationV157Error(message)


def campaign_config_v157():
    config = structural_margin_campaign_config_v156()
    for family, _seed in TARGET_OCCURRENCES:
        config["families"][family]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _frozen(raw: bytes, *, count: int, digest: str, key: str, identity: str, label: str):
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw or len(raw) != count or hashlib.sha256(raw).hexdigest() != digest or document.get(key) != identity:
        _fail(f"V157 frozen {label} changed")
    return document


def _document(guard_receipt_raw: bytes, correction_receipt_raw: bytes):
    guard = _frozen(guard_receipt_raw, count=GUARD_RECEIPT_BYTE_COUNT, digest=GUARD_RECEIPT_SHA256, key="guard_receipt_id", identity=GUARD_RECEIPT_ID, label="guard receipt")
    correction = _frozen(correction_receipt_raw, count=CORRECTION_RECEIPT_BYTE_COUNT, digest=CORRECTION_RECEIPT_SHA256, key="correction_receipt_id", identity=CORRECTION_RECEIPT_ID, label="correction receipt")
    source_facts = [
        {"relative_path": path, "byte_count": len(raw := (SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256(raw).hexdigest()}
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]
    if source_facts != [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]:
        _fail("V157 frozen implementation source changed")
    config = campaign_config_v157()
    payload = {
        "schema": "acfqp.plan_mode_margin_preregistration.v157",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "frozen_guard_receipt": guard,
        "frozen_correction_receipt": correction,
        "target_occurrences": config["target_occurrences"],
        "target_episode_indices": list(TARGET_EPISODE_INDICES),
        "target_worker_count": TARGET_WORKER_COUNT,
        "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "registered_gate": {
            "fresh_successor_identities_after_frozen_v156_failure": True,
            "guard_and_correction_receipts_frozen_before_target_outcomes": True,
            "exact_signature_registry_must_remain_absent": True,
            "positive_margin_gain_and_fallback_zero_regression_required": True,
            "factor_prior_noninferior_everywhere_and_positive_in_aggregate": True,
            "each_arm_must_exercise_exactly_one_applicable_plan_mode": True,
            "both_direct_generic_and_v115_memoized_modes_must_be_observed": True,
            "every_emitted_v115_plan_must_be_revalidated_before_v109_receipt": True,
            "every_executed_action_must_have_v109_receipt": True,
            "both_arms_receding_planning_and_certificate_recovery_required": True,
            "nonrelational_ood_rejection_before_bank_access_required": True,
            "producer_free_verification_required": True,
            "frozen_two_worker_resource_schedule": True,
        },
        "claim_boundary": {
            "target_outcomes_accessed": False,
            "plan_mode_corrected_structural_margin_evidence_observed": False,
            "v156_failure_reclassified": False,
            "guard_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v157(domains.CONSTRUCTION_K7_PREREGISTRATION_V157_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PlanModeMarginPreregistrationV157:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_plan_mode_margin_preregistration_v157(guard_receipt_raw: bytes, correction_receipt_raw: bytes):
    document = _document(guard_receipt_raw, correction_receipt_raw)
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and (
        document["preregistration_id"] != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V157 frozen preregistration changed")
    return PlanModeMarginPreregistrationV157(_ISSUER, raw, document["preregistration_id"])


__all__ = ("PREREGISTRATION_ID", "campaign_config_v157", "freeze_plan_mode_margin_preregistration_v157")
