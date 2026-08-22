from acfqp import construction_k7_domain_registry_extension_v146 as domains


def test_v146_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V146) == 2
    assert all(value.endswith(":v146") for value in domains.K7_DOMAIN_TAG_EXTENSION_V146)
