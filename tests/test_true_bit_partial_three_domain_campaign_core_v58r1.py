from acfqp import construction_k7_domain_registry_extension_v58r1 as domains
from acfqp import construction_k7_universal_mixture_preregistration_v58 as predecessor
from acfqp import true_bit_partial_three_domain_campaign_core_v58r1 as subject
from acfqp import universal_mixture_three_domain_campaign_core_v58 as ground


def _config():
    config = predecessor.campaign_config_v58()
    config["successor_domains"] = {
        "acquisition": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_ACQUISITION_V58R1_DOMAIN,
        "certificate": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_CERTIFICATE_V58R1_DOMAIN,
        "distinction": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_DISTINCTION_V58R1_DOMAIN,
        "episode": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_EPISODE_V58R1_DOMAIN,
        "sample_tax": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_SAMPLE_TAX_V58R1_DOMAIN,
        "campaign": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_CAMPAIGN_V58R1_DOMAIN,
    }
    for spec in config["families"].values():
        spec["maximum_acquisition_labels"] = 160
    return config


def test_development_seeds_close_without_frontier_exhaustion_and_reduce_labels():
    config = _config()
    cases = (
        ("BALANCED_BATCH_REFINEMENT", 590_101),
        ("COUPLED_EXCHANGE", 590_201),
        ("MAINTENANCE_CASCADE", 590_301),
    )
    for family, seed in cases:
        adapter = ground.prior_ground._adapter(family, seed, config)
        acquisitions = subject.acquire_matched_true_bit_models_v58r1(
            adapter, predecessor.FACTOR_LIBRARY, config
        )
        prior = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]["document"]
        strict = acquisitions["STRICT_NO_PRIOR"]["document"]
        assert prior["ground_support_labels"] < strict["ground_support_labels"]
        assert prior["reachable_frontier_exhaustion_input_consumed"] is False
        assert strict["reachable_frontier_exhaustion_input_consumed"] is False
        assert prior["terminal_stop_update"][
            "heuristic_mdl_information_units_consumed"
        ] is False
        assert strict["terminal_stop_update"][
            "predictive_evidence_to_mdl_credit_consumed"
        ] is False
