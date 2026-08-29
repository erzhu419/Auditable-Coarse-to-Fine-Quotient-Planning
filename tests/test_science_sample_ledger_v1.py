from __future__ import annotations

import copy

import pytest

from acfqp.science.sample_ledger_v1 import (
    EvidenceClass,
    EvidenceLane,
    SampleLedgerV1,
    SampleLedgerV1Error,
)


def test_all_evidence_classes_and_lanes_are_materialized_including_zeros() -> None:
    ledger = SampleLedgerV1()
    ledger.charge(
        EvidenceClass.ENVIRONMENT_INTERACTION,
        EvidenceLane.ONLINE_TARGET,
        17,
    )
    ledger.increment_diagnostic("replay_buffer_draws", 128)
    document = ledger.to_document()

    assert document["evidence_row_count"] == 20
    assert len(document["evidence_rows"]) == 20
    assert sum(row["count"] for row in document["evidence_rows"]) == 17
    assert sum(row["native_zero"] for row in document["evidence_rows"]) == 19
    assert document["diagnostic_counters"]["replay_buffer_draws"] == 128
    assert SampleLedgerV1.from_document(document).to_document() == document


def test_replay_work_does_not_increase_environment_interactions() -> None:
    ledger = SampleLedgerV1()
    ledger.increment_diagnostic("replay_buffer_draws", 1024)
    ledger.increment_diagnostic("gradient_updates", 4)

    assert (
        ledger.evidence_count(
            EvidenceClass.ENVIRONMENT_INTERACTION,
            EvidenceLane.ONLINE_TARGET,
        )
        == 0
    )


@pytest.mark.parametrize(
    "mutation",
    ("missing_row", "duplicate_row", "negative_count", "bad_native_zero"),
)
def test_malformed_or_incomplete_evidence_matrix_is_rejected(mutation: str) -> None:
    document = SampleLedgerV1().to_document()
    if mutation == "missing_row":
        document["evidence_rows"].pop()
    elif mutation == "duplicate_row":
        document["evidence_rows"][-1] = copy.deepcopy(document["evidence_rows"][0])
    elif mutation == "negative_count":
        document["evidence_rows"][0]["count"] = -1
    else:
        document["evidence_rows"][0]["native_zero"] = False

    with pytest.raises(SampleLedgerV1Error):
        SampleLedgerV1.from_document(document)
