from acfqp import construction_k7_domain_registry_extension_v149 as domains


def test_v149_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V149) == 4
    assert all(tag.endswith(":v149") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V149)
