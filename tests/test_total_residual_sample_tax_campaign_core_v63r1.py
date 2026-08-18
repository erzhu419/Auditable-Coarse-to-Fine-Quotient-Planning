import os

import pytest

from acfqp import construction_k7_domain_registry_extension_v63r1 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
)
from acfqp.total_residual_sample_tax_campaign_core_v63r1 import (
    build_total_residual_sample_tax_campaign_document_v63r1,
)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V63R1_CORE") != "1",
    reason="explicit development-only V63r1 core replay",
)
def test_v63r1_development_core_retains_abstentions_and_reduces_aggregate_labels():
    config = pre.campaign_config_v59()
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", tuple(range(590_841, 590_845))),
        ("COUPLED_EXCHANGE", tuple(range(590_851, 590_855))),
        ("MAINTENANCE_CASCADE", tuple(range(590_861, 590_865))),
    ):
        config["families"][family]["target_seeds"] = seeds
    config.update(
        worker_count=4,
        maximum_partial_abstract_depth=12,
        maximum_partial_execution_steps=96,
        residual_confidence_denominator=64,
        v63r1_domains={
            "raw_query_pool": domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_RAW_QUERY_POOL_V63R1_DOMAIN,
            "acquisition": domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_ACQUISITION_V63R1_DOMAIN,
            "safety_episode": domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SAFETY_EPISODE_V63R1_DOMAIN,
            "summary": domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SUMMARY_V63R1_DOMAIN,
            "campaign": domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63R1_DOMAIN,
        },
    )
    result = build_total_residual_sample_tax_campaign_document_v63r1(
        config,
        "e" * 64,
        "f" * 64,
        pre.previous.previous.FACTOR_LIBRARY,
        freeze_residual_factor_library_v62().to_document(),
    )
    assert result["sample_tax"]["target_residual_label_reduction"] > 0
    assert result["all_registered_occurrences_retained_including_abstentions"] is True
    assert result["official_N_break_even"] is None
