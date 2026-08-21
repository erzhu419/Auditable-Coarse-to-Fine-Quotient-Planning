from acfqp import construction_k7_domain_registry_extension_v119 as domains


def test_v119_domain_registry_is_additive_and_exact():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V119) == 7
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V119.values()) == set(
        domains.K7_DOMAIN_TAG_EXTENSION_V119
    )
    assert all(value.endswith(":v119") for value in domains.K7_DOMAIN_TAG_EXTENSION_V119)
