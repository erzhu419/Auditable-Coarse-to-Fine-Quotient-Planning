"""Terminal successor lock for the successful V161 source calibration."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CLASSIFIER_RECEIPT_ID = "893a5b0597fe2c9d0544defcf3655ce6e186950e7c1342a7a7502de0d4f1378d"
EXPECTED_CANONICAL_BYTE_COUNT = 383_778
EXPECTED_CANONICAL_SHA256 = "ac6ae1dfe458cd4d818f4acb3c9ba77f829787ee1f57c8fdcd8e379c118267df"
SOURCE_PREREGISTRATION_ID = "f3625303bb54a6354afc7bac8aaf36a87259501f8eb8fff3ecceb83ec72849c7"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS_BY_SUCCESSOR_LOCK"
SAME_IDENTITY_RERUN_FORBIDDEN = True


class ConstructionK7PaidPathPrefixClassifierReceiptFreezeV161Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPathPrefixClassifierReceiptFreezeV161Error(message)


def verify_frozen_paid_path_prefix_classifier_receipt_v161(raw: bytes):
    document: dict[str, Any] = loads_canonical_json(raw)
    expression = document.get("selected_expression", {})
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
        and document.get("classifier_receipt_id") == CLASSIFIER_RECEIPT_ID
        and document.get("source_preregistration_id") == SOURCE_PREREGISTRATION_ID
        and document.get("schema") == "acfqp.paid_path_prefix_classifier_receipt.v161"
        and document.get("offline_source_observation_labels") == 96
        and document.get("fresh_v161_target_labels") == 0
        and document.get("fresh_v161_target_outcomes_accessed") is False
        and document.get("safe_fallback_resumes_same_path_first_generator") is True
        and document.get("classifier_inserts_no_sibling_probe_before_fallback")
        is True
        and document.get("v160_failure_preserved_not_reclassified") is True
        and expression.get("stable_prefix_observation_count") == 7
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
        _fail("V161 frozen classifier receipt changed")
    return document


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CLASSIFIER_RECEIPT_ID",
    "SAME_IDENTITY_RERUN_FORBIDDEN",
    "verify_frozen_paid_path_prefix_classifier_receipt_v161",
)
