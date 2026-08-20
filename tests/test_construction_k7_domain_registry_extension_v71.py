from acfqp import construction_k7_domain_registry_extension_v71 as v71


def test_v71_domains_are_fresh_and_content_addressed():
    assert len(v71.K7_DOMAIN_TAG_EXTENSION_V71) == 5
    assert len(v71.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V71) == 5
    domain = v71.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_CAMPAIGN_V71_DOMAIN
    assert v71.extension_content_id_v71(domain, {"value": 1}) != v71.extension_content_id_v71(
        domain, {"value": 2}
    )
