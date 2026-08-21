import hashlib

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre


def test_v96_preregistration_freezes_joint_successor_persistence_gate():
    value = pre.verify_persistent_multi_residual_preregistration_v96(
        pre.freeze_persistent_multi_residual_preregistration_v96()
    )
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert document["identity_contract"]["target_seeds"] == [997_101, 997_102]
    assert document["identity_contract"]["target_episode_indices"] == [21, 22, 23]
    assert document["construction_contract"][
        "joint_successor_retained_across_later_queries_as_fallible_heuristic"
    ] is True
    assert document["claim_boundary"][
        "persistent_joint_residual_integration_verified"
    ] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
