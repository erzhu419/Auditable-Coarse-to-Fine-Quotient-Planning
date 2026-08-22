"""Terminal successor lock for the successful V160 source calibration."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CLASSIFIER_RECEIPT_ID = "27b256a9a26ae86e49214932b77b2e507f34ff87bc3470ba42275330e48a9a12"
EXPECTED_CANONICAL_BYTE_COUNT = 100_085
EXPECTED_CANONICAL_SHA256 = "e4335b07345c44cbc07d51ebce33a41c9d23fe7e0b27495350ea8a19403b749d"
SOURCE_PREREGISTRATION_ID = "91622dda2410f0aa2b9444b0efbff4735486dab273b995a4171d2643d8210699"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS_BY_SUCCESSOR_LOCK"
SAME_IDENTITY_RERUN_FORBIDDEN = True


class ConstructionK7ProgressiveRawPrefixClassifierReceiptFreezeV160Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProgressiveRawPrefixClassifierReceiptFreezeV160Error(message)


def verify_frozen_progressive_raw_prefix_classifier_receipt_v160(raw: bytes):
    document: dict[str, Any] = loads_canonical_json(raw)
    expression = document.get("selected_expression", {})
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
        and document.get("classifier_receipt_id") == CLASSIFIER_RECEIPT_ID
        and document.get("source_preregistration_id") == SOURCE_PREREGISTRATION_ID
        and document.get("schema")
        == "acfqp.progressive_raw_prefix_classifier_receipt.v160"
        and document.get("offline_source_observation_labels") == 40
        and document.get("fresh_v160_target_labels") == 0
        and document.get("fresh_v160_target_outcomes_accessed") is False
        and document.get("no_named_initial_or_catalogue_support_primitive") is True
        and document.get("full_initial_action_frontier_required_for_decision")
        is False
        and expression.get("stable_prefix_observation_count") == 2
        and expression.get("kind")
        == "COUNT_ANONYMOUS_RAW_DELTA_ROWS_WITH_RELATION_AND_LITERAL_GREATER_THAN"
        and document.get("query_policy_classifier_is_meta_prior_only") is True
        and document.get(
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        )
        is False
        and document.get("complete_world_model_claimed") is False
        and document.get("arbitrary_unseen_domain_transfer_claimed") is False
        and document.get("official_execution_allowed") is False
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
    ):
        _fail("V160 frozen classifier receipt changed")
    return document


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CLASSIFIER_RECEIPT_ID",
    "SAME_IDENTITY_RERUN_FORBIDDEN",
    "verify_frozen_progressive_raw_prefix_classifier_receipt_v160",
)
