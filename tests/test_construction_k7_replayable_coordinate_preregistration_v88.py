from acfqp.construction_k7_replayable_coordinate_preregistration_v88 import (
    PREREGISTRATION_ID,
    freeze_replayable_coordinate_preregistration_v88,
)


def test_v88_preregistration_requires_embedded_raw_reconstruction_inputs():
    document = freeze_replayable_coordinate_preregistration_v88().to_document()
    assert document["fresh_registered_v88_execution_performed"] is False
    assert document["construction_contract"][
        "independent_replayer_must_rederive_exact_alignment_from_embedded_bytes"
    ] is True
    assert document["registered_gate"]["target_sample_reduction_required"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v88_preregistration_identity_is_frozen():
    assert PREREGISTRATION_ID == (
        "1deb31c178a6cbda3dcaf2db4a969662119bb064a60c3e4aebef5724359821c8"
    )
