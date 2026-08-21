from acfqp import construction_k7_domain_registry_extension_v121 as domains


def test_v121_domain_registry_is_additive_and_exact():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V121) == 6
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V121.values()) == set(
        domains.K7_DOMAIN_TAG_EXTENSION_V121
    )
    assert all(value.endswith(":v121") for value in domains.K7_DOMAIN_TAG_EXTENSION_V121)
