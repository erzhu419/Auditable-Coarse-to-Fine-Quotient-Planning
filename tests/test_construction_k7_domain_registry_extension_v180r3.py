from acfqp import construction_k7_domain_registry_extension_v180r3 as domains


def test_v180r3_domains_are_unique_and_content_addressed() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R3) == 11
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R3) == 11
    values = set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R3.values())
    assert values == set(domains.K7_DOMAIN_TAG_EXTENSION_V180R3)
    first = domains.extension_content_id_v180r3(
        domains.CONSTRUCTION_K7_PRODUCTION_EXECUTION_PROTOCOL_V180R3_DOMAIN,
        {"value": 1},
    )
    second = domains.extension_content_id_v180r3(
        domains.CONSTRUCTION_K7_PRODUCTION_EXECUTION_SLOT_V180R3_DOMAIN,
        {"value": 1},
    )
    assert first != second
