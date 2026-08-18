from acfqp import construction_k7_domain_registry_extension_v61 as domains


def test_v61_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V61) == 10
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V61) == 10
    payload = {"schema": "test.v61", "value": 1}
    identifiers = {
        domains.extension_content_id_v61(domain, payload)
        for domain in domains.K7_DOMAIN_TAG_EXTENSION_V61
    }
    assert len(identifiers) == 10
