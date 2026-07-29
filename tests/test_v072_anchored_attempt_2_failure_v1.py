from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from acfqp import v072_anchored_attempt_2_failure_v1 as failure


ROOT = Path(__file__).resolve().parents[1]


def test_tracked_attempt_2_failure_is_canonical_and_exact() -> None:
    document = failure.load_anchored_attempt_2_failure_record_v1(ROOT)

    assert document == failure.anchored_attempt_2_failure_document_v1()
    assert document["record_id"] == (
        "cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e"
    )
    assert document["execution"]["completed_occurrence_count"] == 4
    assert document["execution"]["registered_occurrence_denominator"] == 15
    assert document["failure"]["terminal_code"] == "PROTOCOL_FAILURE"
    assert document["execution"]["result_artifact_written"] is False
    assert document["execution"]["result_artifact_id"] is None
    assert document["execution"]["endpoint_evaluated"] is False
    assert document["execution"]["registered_endpoint_outcome"] is None
    assert (
        document["execution"]["unknown_tail_work"]["kind"]
        == "UNKNOWN_AFTER_LAST_DURABLE_BOUNDARY"
    )
    assert (
        document["execution"]["unknown_tail_work"]
        ["must_not_be_interpreted_as_zero"]
        is True
    )
    assert (
        document["disposition"]["same_authority_chain_attempts_remaining"]
        == 0
    )
    assert (
        document["disposition"]["same_authority_chain_retry_allowed"]
        is False
    )
    assert (
        document["disposition"]
        ["new_confirmatory_validation_requires_fresh_heldout_identities"]
        is True
    )


def test_attempt_2_git_authority_replays_frozen_triple() -> None:
    assert failure.verify_anchored_attempt_2_git_authority_v1(ROOT) == (
        failure.SOURCE_RECIPE_ID,
        failure.MANIFEST_ID,
        failure.FINAL_PREREGISTRATION_ID,
    )


def test_attempt_2_journal_identity_and_live_evidence_are_exact() -> None:
    identity = failure.expected_attempt_2_journal_identity_v1()

    assert identity.attempt_id == failure.ATTEMPT_ID
    assert identity.anchor_commit_id == failure.ANCHOR_COMMIT_ID
    assert identity.anchor_id == failure.REMOTE_MAIN_ANCHOR_ID
    attempt_directory = (
        ROOT
        / "artifacts/v072_attempt_journals"
        / failure.ATTEMPT_ID
    )
    if not attempt_directory.exists():
        pytest.skip("ignored historical journal is not present in this clone")

    verification = (
        failure.verify_anchored_attempt_2_journal_evidence_v1(ROOT)
    )
    assert verification.event_ids == failure.EVENT_IDS
    assert verification.object_ids == failure.OBJECT_IDS
    assert verification.completed_occurrence_count == 4
    assert verification.valid_hash_chain is True


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    (
        ("execution", "completed_occurrence_count", 0),
        ("execution", "registered_occurrence_denominator", 4),
        ("execution", "result_artifact_written", True),
        ("execution", "result_artifact_id", "0" * 64),
        ("execution", "endpoint_evaluated", True),
        ("execution", "registered_endpoint_outcome", "PASS"),
        ("failure", "terminal_code", "PLAN_CERTIFICATE"),
        ("disposition", "same_authority_chain_attempts_remaining", 1),
        ("disposition", "same_authority_chain_retry_allowed", True),
        ("claim_boundary", "sample_efficiency_claimed", True),
    ),
)
def test_attempt_2_reclassification_is_rejected(
    section: str,
    field: str,
    replacement: object,
) -> None:
    document = deepcopy(
        failure.anchored_attempt_2_failure_document_v1()
    )
    document[section][field] = replacement

    with pytest.raises(
        failure.V072AnchoredAttempt2FailureInvariantViolation,
        match="semantics changed",
    ):
        failure.verify_anchored_attempt_2_failure_document_v1(document)


def test_attempt_2_unknown_tail_cannot_be_zeroed() -> None:
    document = deepcopy(
        failure.anchored_attempt_2_failure_document_v1()
    )
    document["execution"]["unknown_tail_work"] = 0

    with pytest.raises(
        failure.V072AnchoredAttempt2FailureInvariantViolation,
        match="semantics changed",
    ):
        failure.verify_anchored_attempt_2_failure_document_v1(document)


def test_attempt_2_journal_or_anchor_substitution_is_rejected() -> None:
    document = deepcopy(
        failure.anchored_attempt_2_failure_document_v1()
    )
    document["journal_evidence"]["terminal_event_id"] = "0" * 64

    with pytest.raises(
        failure.V072AnchoredAttempt2FailureInvariantViolation,
        match="semantics changed",
    ):
        failure.verify_anchored_attempt_2_failure_document_v1(document)


def test_attempt_2_record_id_substitution_is_rejected() -> None:
    document = failure.anchored_attempt_2_failure_document_v1()
    document["record_id"] = "0" * 64

    with pytest.raises(
        failure.V072AnchoredAttempt2FailureInvariantViolation,
        match="content identity changed",
    ):
        failure.verify_anchored_attempt_2_failure_document_v1(document)
