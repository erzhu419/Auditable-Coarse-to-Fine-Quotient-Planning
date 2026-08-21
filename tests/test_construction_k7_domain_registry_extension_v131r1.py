from acfqp import construction_k7_domain_registry_extension_v131r1 as domains


def test_v131r1_domains_are_additive_successor_domains():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V131R1) == 4
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131R1.values())) == 4
    assert all(value.endswith(":v131r1") for value in domains.K7_DOMAIN_TAG_EXTENSION_V131R1)
