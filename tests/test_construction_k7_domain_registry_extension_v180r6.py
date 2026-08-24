from acfqp import construction_k7_domain_registry_extension_v180r6 as domains


def test_v180r6_domain_registry_is_additive_and_exact() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R6) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R6) == 5
    assert all(tag.endswith(":v180r6") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V180R6)
