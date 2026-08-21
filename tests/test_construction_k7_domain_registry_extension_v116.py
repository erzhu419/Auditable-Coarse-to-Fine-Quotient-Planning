from acfqp import construction_k7_domain_registry_extension_v116 as domains


def test_v116_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V116) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V116) == 5
    assert all(tag.endswith(":v116") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V116)
    domain = domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_CAMPAIGN_V116_DOMAIN
    assert domains.extension_content_id_v116(domain, {"x": 1}) == domains.extension_content_id_v116(
        domain, {"x": 1}
    )
