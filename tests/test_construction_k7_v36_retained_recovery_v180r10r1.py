import os
from pathlib import Path

import pytest

from acfqp import construction_k7_v36_retained_recovery_independent_verifier_v180r10r1 as verifier
from acfqp import construction_k7_v36_retained_recovery_terminal_v180r10r1 as producer
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "exact-freeze" / "v180r10_v36_resource_successor_output"


def test_v180r10r1_terminal_is_retained_finish_forward_only() -> None:
    terminal = producer.finish_forward_retained_v36_occurrence_v180r10r1(
        RETAINED, recovery_authorization_id="f" * 64
    )
    document = terminal.to_document()
    assert document["terminal_code"] == "LOCAL_GROUND_RECOVERY"
    assert document["scientific_occurrence_rerun_by_successor"] is False
    assert document["terminal_predicate_source_field"] == "operational_target_probability_label_query_count"
    assert document["operational_lane_literal_repaired"] == "OPERATIONAL"
    assert document["retained_occurrence_receipt"]["source_operational_work_vector_count"] == 15


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V180R10R1_REPLAY") != "1",
    reason="producer-free V35/V36 semantic replay is retained-real scope",
)
def test_v180r10r1_full_producer_free_replay() -> None:
    terminal = producer.finish_forward_retained_v36_occurrence_v180r10r1(
        RETAINED, recovery_authorization_id="e" * 64
    )
    replay = verifier.verify_v36_retained_recovery_bytes_independently_v180r10r1(
        terminal.canonical_bytes,
        RETAINED,
        recovery_authorization_id="e" * 64,
    )
    assert replay["source_v36_semantics_replayed_producer_free"] is True
    assert replay["certificate_failure_then_local_recovery_verified"] is True
    assert replay["scientific_occurrence_rerun"] is False
    assert replay["all_ten_paths_verified"] is False


def test_v180r10r1_rejects_terminal_tamper_before_semantic_replay() -> None:
    terminal = producer.finish_forward_retained_v36_occurrence_v180r10r1(
        RETAINED, recovery_authorization_id="d" * 64
    )
    document = terminal.to_document()
    document["scientific_occurrence_rerun_by_successor"] = True
    with pytest.raises(
        verifier.ConstructionK7V36RetainedRecoveryIndependentVerifierV180r10r1Error
    ):
        verifier.verify_v36_retained_recovery_bytes_independently_v180r10r1(
            canonical_json_bytes(document),
            RETAINED,
            recovery_authorization_id="d" * 64,
        )

