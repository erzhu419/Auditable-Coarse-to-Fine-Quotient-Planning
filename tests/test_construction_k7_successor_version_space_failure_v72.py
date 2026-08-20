from acfqp.construction_k7_successor_version_space_failure_v72 import (
    FAILURE_ID,
    REGISTERED_V72_FAILURE,
)


def test_v72_registered_failure_is_retained_and_forbids_same_identity_rerun():
    assert len(FAILURE_ID) == 64
    assert REGISTERED_V72_FAILURE["failure_phase"] == "POST_WORKER_OCCURRENCE_AGGREGATION"
    assert REGISTERED_V72_FAILURE["exception_type"] == "KeyError"
    assert REGISTERED_V72_FAILURE["campaign_document_constructed"] is False
    assert REGISTERED_V72_FAILURE["partial_occurrence_artifact_bytes_persisted"] is False
    assert REGISTERED_V72_FAILURE["same_preregistration_identity_rerun_allowed"] is False
    assert REGISTERED_V72_FAILURE["official_scalar_cost"] is None
