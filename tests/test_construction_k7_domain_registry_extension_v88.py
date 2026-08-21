from acfqp import construction_k7_domain_registry_extension_v88 as domains


def test_v88_domains_are_unique_and_additive():
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V88
    assert len(registry) == 5
    assert len(set(registry.values())) == 5
    assert all(value.endswith(":v88") for value in registry.values())
