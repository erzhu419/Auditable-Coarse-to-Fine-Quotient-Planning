from acfqp import construction_k7_domain_registry_extension_v181r4 as domains


def test_v181r4_domains_are_fresh_and_complete() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V181R4) == 8
    assert all(value.endswith(":v181r4") for value in domains.K7_DOMAIN_TAG_EXTENSION_V181R4)
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V181R4.values())) == 8
