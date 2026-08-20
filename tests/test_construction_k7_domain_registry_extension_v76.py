from acfqp import construction_k7_domain_registry_extension_v76 as domains


def test_v76_domains_are_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V76) == 5
