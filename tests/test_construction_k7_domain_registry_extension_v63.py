from acfqp import construction_k7_domain_registry_extension_v63 as domains


def test_v63_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V63) == 7
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V63) == 7
    assert domains.extension_content_id_v63(
        domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63_DOMAIN, {"x": 1}
    ) != domains.extension_content_id_v63(
        domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_SUMMARY_V63_DOMAIN, {"x": 1}
    )
