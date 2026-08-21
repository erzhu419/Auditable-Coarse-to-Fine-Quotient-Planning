from acfqp import construction_k7_domain_registry_extension_v90 as domains


def test_v90_domains_are_unique_and_additive():
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V90
    assert len(registry) == 4
    assert len(set(registry.values())) == 4
    assert all(value.endswith(":v90") for value in registry.values())
