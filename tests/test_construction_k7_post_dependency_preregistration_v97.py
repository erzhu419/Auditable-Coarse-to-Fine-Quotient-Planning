import hashlib

from acfqp import construction_k7_post_dependency_preregistration_v97 as pre


def test_v97_preregistration_freezes_fresh_dependency_joint_gate():
    value = pre.verify_post_dependency_preregistration_v97(
        pre.freeze_post_dependency_preregistration_v97()
    )
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert document["identity_contract"]["target_seeds"] == [
        999_101,
        999_102,
        999_103,
        999_104,
    ]
    assert document["identity_contract"]["target_episode_indices"] == [41, 42, 43]
    assert document["registered_gate"][
        "at_least_one_target_must_discover_and_use_post_dependency_program"
    ] is True
    assert document["registered_gate"][
        "zero_later_labels_not_required_because_local_recovery_is_permitted"
    ] is True
    assert document["claim_boundary"]["post_dependency_joint_successor_verified"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
