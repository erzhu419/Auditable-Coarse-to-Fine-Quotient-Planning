from acfqp import construction_k7_domain_registry_extension_v120 as domains


def test_v120_domain_registry_is_additive_and_exact():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V120) == 7
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V120.values()) == set(
        domains.K7_DOMAIN_TAG_EXTENSION_V120
    )
    assert all(value.endswith(":v120") for value in domains.K7_DOMAIN_TAG_EXTENSION_V120)
