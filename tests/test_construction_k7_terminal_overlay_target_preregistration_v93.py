import hashlib

from acfqp import construction_k7_terminal_overlay_target_preregistration_v93 as pre


def test_v93_preregistration_is_frozen_before_fresh_target_outcomes():
    value = pre.verify_terminal_overlay_target_preregistration_v93(
        pre.freeze_terminal_overlay_target_preregistration_v93()
    )
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert (
        hashlib.sha256(value.canonical_bytes).hexdigest()
        == pre.EXPECTED_CANONICAL_SHA256
    )
    assert document["identity_contract"]["target_seeds"] == [961_101, 961_102]
    assert document["identity_contract"][
        "target_identities_cannot_be_selected_after_outcomes"
    ] is True
    assert document["construction_contract"][
        "no_fixed_label_floor_or_confirmation_block"
    ] is True
    assert document["registered_gate"][
        "every_target_strict_certificate_labels_must_exceed_model_labels"
    ] is True
    assert document["claim_boundary"]["registered_v93_target_outcome_observed"] is False
    assert document["claim_boundary"]["complete_world_model_synthesized"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
