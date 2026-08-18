import os

import pytest

from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
)
from acfqp.residual_factor_sample_tax_campaign_core_v63 import (
    build_residual_factor_sample_tax_campaign_document_v63,
)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V63_CORE") != "1",
    reason="explicit development-only V63 core replay",
)
def test_v63_core_development_run_keeps_claims_locked():
    from acfqp import construction_k7_domain_registry_extension_v63 as domains

    config = pre.campaign_config_v59()
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", tuple(range(590_741, 590_745))),
        ("COUPLED_EXCHANGE", tuple(range(590_751, 590_755))),
        ("MAINTENANCE_CASCADE", tuple(range(590_761, 590_765))),
    ):
        config["families"][family]["target_seeds"] = seeds
    config["worker_count"] = 4
    config["maximum_partial_abstract_depth"] = 12
    config["maximum_partial_execution_steps"] = 96
    config["residual_confidence_denominator"] = 64
    config["v63_domains"] = {
        "raw_query_pool": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_RAW_QUERY_POOL_V63_DOMAIN,
        "acquisition": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_ACQUISITION_V63_DOMAIN,
        "safety_episode": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_SAFETY_EPISODE_V63_DOMAIN,
        "summary": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_SUMMARY_V63_DOMAIN,
        "campaign": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63_DOMAIN,
    }
    result = build_residual_factor_sample_tax_campaign_document_v63(
        config,
        "d" * 64,
        pre.previous.previous.FACTOR_LIBRARY,
        freeze_residual_factor_library_v62().to_document(),
    )
    assert result["sample_tax"]["target_residual_label_reduction"] > 0
    assert result["official_execution_allowed"] is False
    assert result["official_N_break_even"] is None
    assert result["statistical_residual_proposal_used_as_safety_authority"] is False
