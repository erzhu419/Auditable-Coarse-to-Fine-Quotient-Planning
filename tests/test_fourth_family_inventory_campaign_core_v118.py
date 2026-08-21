from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.fourth_family_inventory_campaign_core_v118 import (
    build_fourth_family_inventory_campaign_document_v118,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY,
    inventory_assembly_config_v118,
)


def test_v118_development_fourth_family_gate_retains_unfavourable_sample_delta():
    config = inventory_assembly_config_v118()
    config.update(
        target_occurrences=[{"family": FAMILY, "seed": 1_030_001}],
        target_episode_indices=(257, 258, 259),
        target_worker_count=1,
        required_target_occurrence_count=1,
    )
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_fourth_family_inventory_campaign_document_v118(
        config,
        preregistration_id="development-only",
        v117_campaign_id="development-v117",
        v117_verification_id="development-v117-verification",
        factor_library=factor_library,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["prior_minus_no_prior_acquisition_labels"] == 1
    assert document["accounting"]["sample_efficiency_improvement_claimed"] is False
    assert document["arbitrary_unseen_domain_transfer_claimed"] is False
    assert document["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
