from acfqp import construction_k7_domain_registry_extension_v75r5 as domains


def test_v75r5_domains_are_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V75R5) == 5
