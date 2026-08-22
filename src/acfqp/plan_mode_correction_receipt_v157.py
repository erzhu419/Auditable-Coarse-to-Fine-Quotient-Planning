"""Outcome-free correction of the over-strong V156 receipt-consumption Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v157 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V156_CAMPAIGN_ID = "eddffbb380f9ea6e084515f622b81bce993b4e5b209bac2375417b1946dc6eb3"
V156_CAMPAIGN_BYTE_COUNT = 14_015_131
V156_CAMPAIGN_SHA256 = "15758409c83b82f2720529b5e0e80917077472bbe6664e5e2204704e3684788e"
V156_FAILURE_BYTE_COUNT = 5_207
V156_FAILURE_SHA256 = "5bd68c477d98231ddbc4bcd7361ad18f2ba1a89fc12b6ced7796da617791e881"
CORRECTION_RECEIPT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class PlanModeCorrectionReceiptV157Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise PlanModeCorrectionReceiptV157Error(message)


def _document(v156_campaign_raw: bytes, v156_failure_raw: bytes):
    campaign = loads_canonical_json(v156_campaign_raw)
    failure = loads_canonical_json(v156_failure_raw)
    if not (
        canonical_json_bytes(campaign) == v156_campaign_raw
        and len(v156_campaign_raw) == V156_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v156_campaign_raw).hexdigest() == V156_CAMPAIGN_SHA256
        and campaign.get("campaign_id") == V156_CAMPAIGN_ID
        and canonical_json_bytes(failure) == v156_failure_raw
        and len(v156_failure_raw) == V156_FAILURE_BYTE_COUNT
        and hashlib.sha256(v156_failure_raw).hexdigest() == V156_FAILURE_SHA256
        and failure.get("campaign_id") == V156_CAMPAIGN_ID
        and failure.get("same_identity_rerun_forbidden") is True
    ):
        _fail("V157 frozen V156 failure changed")
    rows = campaign["target_occurrences"]
    direct_rows = [row for row in rows if all(sequence["direct_generic_factor_program_plan_count"] > 0 and sequence["v115_memoized_compiled_program_plan_receipt_count"] == 0 for sequence in (row["anonymous_relational_factor_prior_owned_sequence"], row["strict_no_prior_owned_sequence"]))]
    memo_rows = [row for row in rows if all(sequence["v115_memoized_compiled_program_plan_receipt_count"] > 0 and sequence["direct_generic_factor_program_plan_count"] == 0 for sequence in (row["anonymous_relational_factor_prior_owned_sequence"], row["strict_no_prior_owned_sequence"]))]
    if len(direct_rows) != 4 or len(memo_rows) != 4:
        _fail("V157 observed V156 plan modes changed")
    payload = {
        "schema": "acfqp.plan_mode_correction_receipt.v157",
        "failed_v156_campaign_id": V156_CAMPAIGN_ID,
        "failed_v156_record_sha256": V156_FAILURE_SHA256,
        "v156_failure_reason": failure["failure_reason"],
        "observed_direct_generic_occurrence_count": len(direct_rows),
        "observed_v115_memoized_occurrence_count": len(memo_rows),
        "corrected_registered_invariant": {
            "every_emitted_v115_plan_must_be_revalidated_before_v109_execution_receipt": True,
            "direct_generic_factor_program_plan_is_a_valid_nonmemoized_plan_mode": True,
            "each_arm_must_exercise_exactly_one_registered_plan_mode": True,
            "every_executed_action_still_requires_v109_legality_conditioned_execution_receipt": True,
            "absence_of_v115_receipt_is_not_failure_when_direct_generic_plan_is_present": True,
        },
        "correction_changes_evidence_gate_not_planner_dynamics_or_query_policy": True,
        "fresh_v157_target_outcomes_accessed": False,
        "v156_failed_identity_preserved": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "correction_receipt_id": domains.extension_content_id_v157(domains.CONSTRUCTION_K7_CORRECTION_RECEIPT_V157_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PlanModeCorrectionReceiptV157:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    correction_receipt_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_plan_mode_correction_receipt_v157(v156_campaign_raw: bytes, v156_failure_raw: bytes):
    document = _document(v156_campaign_raw, v156_failure_raw)
    raw = canonical_json_bytes(document)
    if CORRECTION_RECEIPT_ID != "0" * 64 and (
        document["correction_receipt_id"] != CORRECTION_RECEIPT_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V157 correction receipt changed")
    return PlanModeCorrectionReceiptV157(_ISSUER, raw, document["correction_receipt_id"])


__all__ = ("CORRECTION_RECEIPT_ID", "freeze_plan_mode_correction_receipt_v157")
