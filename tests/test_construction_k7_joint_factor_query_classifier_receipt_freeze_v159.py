from pathlib import Path

from acfqp.construction_k7_joint_factor_query_classifier_receipt_freeze_v159 import (
    CLASSIFIER_RECEIPT_ID,
    SAME_IDENTITY_RERUN_FORBIDDEN,
    SOURCE_ATTEMPT_TERMINAL_STATE,
    verify_frozen_joint_factor_query_classifier_receipt_v159,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v159_source_receipt_is_terminal_without_rewriting_preregistered_source():
    document = verify_frozen_joint_factor_query_classifier_receipt_v159(
        (FREEZE / "v159_joint_factor_query_classifier_receipt.json").read_bytes()
    )
    assert document["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
    assert SOURCE_ATTEMPT_TERMINAL_STATE == "FROZEN_SUCCESS_BY_SUCCESSOR_LOCK"
    assert SAME_IDENTITY_RERUN_FORBIDDEN is True
    assert document["offline_source_observation_labels"] == 8
    assert document["fresh_v159_target_labels"] == 0
