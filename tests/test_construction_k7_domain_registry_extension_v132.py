from acfqp import construction_k7_domain_registry_extension_v132 as domains


def test_v132_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V132) == 2
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V132.values())) == 2
    assert all(value.endswith(":v132") for value in domains.K7_DOMAIN_TAG_EXTENSION_V132)
