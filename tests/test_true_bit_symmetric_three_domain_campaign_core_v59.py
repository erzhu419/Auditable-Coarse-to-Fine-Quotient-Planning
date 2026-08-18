from acfqp import construction_k7_domain_registry_extension_v59 as domains
from acfqp import construction_k7_universal_mixture_preregistration_v58 as base
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as subject
from acfqp import universal_mixture_three_domain_campaign_core_v58 as ground


def _config():
    config = base.campaign_config_v58()
    config["successor_domains"] = {
        "acquisition": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
        "certificate": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CERTIFICATE_V59_DOMAIN,
        "distinction": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_DISTINCTION_V59_DOMAIN,
        "episode": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_EPISODE_V59_DOMAIN,
        "sample_tax": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_SAMPLE_TAX_V59_DOMAIN,
        "campaign": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CAMPAIGN_V59_DOMAIN,
    }
    for spec in config["families"].values():
        spec["maximum_acquisition_labels"] = 160
    return config


def test_v59_accepts_either_arm_stopping_first_on_development_seeds():
    config = _config()
    cases = (
        ("BALANCED_BATCH_REFINEMENT", 590_101, "ANONYMOUS_FACTOR_PRIOR_ON"),
        ("MAINTENANCE_CASCADE", 589_931, "STRICT_NO_PRIOR"),
    )
    for family, seed, expected_first in cases:
        adapter = ground.prior_ground._adapter(family, seed, config)
        result = subject.acquire_matched_true_bit_models_v59(
            adapter, base.FACTOR_LIBRARY, config
        )
        labels = {
            arm: row["document"]["ground_support_labels"]
            for arm, row in result.items()
        }
        assert labels[expected_first] == min(labels.values())
        assert all(
            row["document"]["symmetric_minimum_common_prefix_post_audit"]
            for row in result.values()
        )
