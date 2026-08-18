from acfqp import construction_k7_domain_registry_extension_v63r1 as domains


def test_v63r1_domains_are_fresh_and_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V63R1) == 7
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V63R1) == 7
