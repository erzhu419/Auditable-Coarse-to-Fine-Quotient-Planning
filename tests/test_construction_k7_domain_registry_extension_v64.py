from acfqp import construction_k7_domain_registry_extension_v64 as domains


def test_v64_domains_are_fresh_and_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V64) == 3
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V64) == 3
