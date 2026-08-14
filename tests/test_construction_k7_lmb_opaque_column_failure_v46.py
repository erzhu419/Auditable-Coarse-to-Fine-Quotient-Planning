from __future__ import annotations

import hashlib

from acfqp import construction_k7_lmb_opaque_column_failed_attempt_v46 as attempt
from acfqp import construction_k7_lmb_opaque_column_failure_v46 as failure
from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as pre


def test_v46_attempt_bytes_are_frozen_but_not_promotable() -> None:
    frozen = attempt.freeze_lmb_opaque_column_failed_attempt_v46()
    assert attempt.ATTEMPT_VALID is False
    assert frozen.attempted_campaign_id == attempt.EXPECTED_ATTEMPTED_CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == attempt.EXPECTED_ATTEMPTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        attempt.EXPECTED_ATTEMPTED_CANONICAL_SHA256
    )


def test_v46_failure_preserves_exact_out_of_grammar_reason() -> None:
    frozen = failure.freeze_lmb_opaque_column_failure_v46()
    assert frozen.failure_id == failure.FAILURE_ID
    assert len(frozen.canonical_bytes) == failure.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        failure.EXPECTED_CANONICAL_SHA256
    )
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["attempted_campaign_id"] == attempt.EXPECTED_ATTEMPTED_CAMPAIGN_ID
    assert document["unregistered_constructor_names"] == [
        "ADD_ONE",
        "ALL_ACTION_IDS_INSERTED",
        "MODULO",
        "RELATION_VECTOR_AT",
        "RELATION_VECTOR_UPDATE",
    ]
    assert document["failure_code"] == (
        "COMPILED_PROGRAM_USES_UNREGISTERED_RELATION_CONSTRUCTORS"
    )
    assert document["attempt_valid"] is False
    assert document["attempt_may_not_be_promoted_to_campaign_evidence"] is True
    assert document["same_identity_corrected_rerun_allowed"] is False
    assert document["successor_requires_fresh_preregistration_and_outcome_identities"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
