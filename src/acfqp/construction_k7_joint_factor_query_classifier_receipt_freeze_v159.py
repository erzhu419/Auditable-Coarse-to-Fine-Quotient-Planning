"""Terminal successor lock for the source-closed V159 classifier receipt.

The pre-execution producer bytes remain unchanged because they are themselves
part of the preregistered source closure.  All later construction imports this
terminal verifier, never the producer entry point.
"""

from __future__ import annotations

import hashlib
from typing import NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CLASSIFIER_RECEIPT_ID = "464febb181620c04c171817ca1b934b3014e7fcc48cdc5a8162bfd5ba23e954a"
EXPECTED_CANONICAL_BYTE_COUNT = 10_690
EXPECTED_CANONICAL_SHA256 = "cff14491ae87b69ef853cbf55109be0b0122ead9b9045fe3c4407bc574794317"
SOURCE_PREREGISTRATION_ID = "1557a40366dc59e928e265891599fa23299f3384c6eeffab79c47f488c46f295"
SOURCE_ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS_BY_SUCCESSOR_LOCK"
SAME_IDENTITY_RERUN_FORBIDDEN = True


class ConstructionK7JointFactorQueryClassifierReceiptFreezeV159Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorQueryClassifierReceiptFreezeV159Error(message)


def verify_frozen_joint_factor_query_classifier_receipt_v159(raw: bytes):
    document = loads_canonical_json(raw)
    observations = document.get("source_modular_factorization_observations", ())
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
        and document.get("classifier_receipt_id") == CLASSIFIER_RECEIPT_ID
        and document.get("source_preregistration_id") == SOURCE_PREREGISTRATION_ID
        and len(observations) == 4
        and all(
            row.get("positive_factorization_relation_present") is False
            and row.get("factorization_relation_candidate_count") == 0
            and row.get("fresh_v159_target_outcomes_accessed") is False
            for row in observations
        )
        and document.get("offline_source_observation_labels") == 8
        and document.get("fresh_v159_target_labels") == 0
        and document.get("fresh_v159_target_outcomes_accessed") is False
        and document.get("query_policy_classifier_is_meta_prior_only") is True
        and document.get(
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        )
        is False
        and document.get("official_scalar_cost") is None
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
    ):
        _fail("V159 frozen joint factor/query receipt changed")
    return document


__all__ = (
    "CLASSIFIER_RECEIPT_ID",
    "SAME_IDENTITY_RERUN_FORBIDDEN",
    "SOURCE_ATTEMPT_TERMINAL_STATE",
    "verify_frozen_joint_factor_query_classifier_receipt_v159",
)
