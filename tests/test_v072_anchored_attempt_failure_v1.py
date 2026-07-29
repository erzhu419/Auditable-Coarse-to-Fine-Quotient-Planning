from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from acfqp import v072_anchored_attempt_failure_v1 as failure


ROOT = Path(__file__).resolve().parents[1]


def test_tracked_attempt_failure_is_canonical_and_exact() -> None:
    document = failure.load_anchored_attempt_1_failure_record_v1(ROOT)

    assert document == failure.anchored_attempt_1_failure_document_v1()
    assert document["execution"]["registered_occurrence_denominator"] == 15
    assert (
        document["execution"]["target_draws_and_native_work"]["kind"]
        == "UNKNOWN_NOT_DURABLY_PERSISTED"
    )
    assert (
        document["execution"]["target_draws_and_native_work"]
        ["must_not_be_interpreted_as_zero"]
        is True
    )
    assert document["failure"]["plan_or_infeasibility_credit_allowed"] is False
    assert document["failure"]["scientific_endpoint_read_allowed"] is False
    assert (
        document["disposition"]["old_target_tape_or_evidence_reuse_allowed"]
        is False
    )
    assert (
        document["disposition"]
        ["replacement_attempt_must_restart_all_15_occurrences"]
        is True
    )
    assert failure.verify_anchored_attempt_1_git_authority_v1(ROOT) == (
        failure.SOURCE_RECIPE_ID,
        failure.MANIFEST_ID,
        failure.FINAL_PREREGISTRATION_ID,
    )


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (
            ("execution", "target_draws_and_native_work"),
            0,
        ),
        (
            ("failure", "classification"),
            "PLAN_CERTIFICATE",
        ),
        (
            ("disposition", "old_target_tape_or_evidence_reuse_allowed"),
            True,
        ),
        (
            ("disposition", "scientific_parameters_changed"),
            True,
        ),
    ),
)
def test_failure_semantic_reclassification_is_rejected(
    path: tuple[str, str],
    replacement: object,
) -> None:
    document = deepcopy(
        failure.anchored_attempt_1_failure_document_v1()
    )
    document[path[0]][path[1]] = replacement

    with pytest.raises(
        failure.V072AnchoredAttemptFailureInvariantViolation,
        match="semantics changed",
    ):
        failure.verify_anchored_attempt_1_failure_document_v1(document)


def test_failure_record_id_substitution_is_rejected() -> None:
    document = failure.anchored_attempt_1_failure_document_v1()
    document["record_id"] = "0" * 64

    with pytest.raises(
        failure.V072AnchoredAttemptFailureInvariantViolation,
        match="content identity changed",
    ):
        failure.verify_anchored_attempt_1_failure_document_v1(document)
