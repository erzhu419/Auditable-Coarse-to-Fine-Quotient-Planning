from acfqp import construction_k7_domain_registry_extension_v65 as domains


def test_v65_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V65) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V65) == 5
    payload = {"schema": "test.v65", "value": 1}
    domain = next(iter(domains.K7_DOMAIN_TAG_EXTENSION_V65))
    first = domains.extension_content_id_v65(domain, payload)
    assert first == domains.extension_content_id_v65(domain, payload)
    assert len(first) == 64
