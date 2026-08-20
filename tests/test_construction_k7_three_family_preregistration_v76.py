from acfqp.construction_k7_three_family_preregistration_v76 import (
    FRESH_TARGET_SEEDS,
    SOURCE_SEED_BY_FAMILY,
    freeze_three_family_preregistration_v76,
)


def test_v76_preregistration_freezes_three_family_extension():
    document = freeze_three_family_preregistration_v76().to_document()
    assert set(SOURCE_SEED_BY_FAMILY) == {
        "BALANCED_BATCH_REFINEMENT",
        "COUPLED_EXCHANGE",
        "MAINTENANCE_CASCADE",
    }
    assert sum(len(values) for values in FRESH_TARGET_SEEDS.values()) == 6
    assert document["extension_contract"]["cross_family_model_transfer_claimed"] is False
    assert document["fresh_registered_v76_execution_performed"] is False
