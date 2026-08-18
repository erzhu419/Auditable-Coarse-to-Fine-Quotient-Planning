from acfqp import construction_k7_domain_registry_extension_v66 as domains


def test_v66_domain_extension_is_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V66) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V66) == 5
