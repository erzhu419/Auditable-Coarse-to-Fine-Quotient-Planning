from acfqp.construction_k7_three_family_preregistration_v77 import (
    SOURCE_SEED_BY_FAMILY,
    freeze_three_family_preregistration_v77,
)


def test_v77_preregistration_freezes_fresh_fail_closed_successor():
    document = freeze_three_family_preregistration_v77().to_document()
    assert SOURCE_SEED_BY_FAMILY["BALANCED_BATCH_REFINEMENT"] == 751_101
    assert document["failure_driven_successor_contract"][
        "v76_source_abstention_failure_preserved"
    ] is True
    assert document["failure_driven_successor_contract"][
        "source_abstention_is_typed_and_never_dereferenced"
    ] is True
    assert document["fresh_registered_v77_execution_performed"] is False
