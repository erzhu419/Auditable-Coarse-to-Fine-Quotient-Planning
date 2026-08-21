from acfqp import construction_k7_occurrence_balanced_source_failure_v91r1 as failure


def test_v91r1_registered_failure_is_frozen_and_typed():
    raw = failure.freeze_occurrence_balanced_source_failure_v91r1()
    document = failure.verify_occurrence_balanced_source_failure_bytes_v91r1(raw)
    assert document["failure_id"] == failure.FAILURE_ID
    assert document["failed_source_seed"] == 931101
    assert document["failed_before_occurrence_balanced_query_scheduling"] is True
    assert document["registered_campaign_document_produced"] is False
    assert document["typed_result"] == "SOURCE_MEMBER_CAP_FAILURE_NONCERTIFICATE"
    assert document["official_scalar_cost"] is None
