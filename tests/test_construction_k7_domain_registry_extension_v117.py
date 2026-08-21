from acfqp import construction_k7_domain_registry_extension_v117 as domains


def test_v117_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V117) == 6
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V117.values())) == 6
    payload = {"schema": "test.v117", "value": 1}
    values = {
        domains.extension_content_id_v117(domain, payload)
        for domain in domains.K7_DOMAIN_TAG_EXTENSION_V117
    }
    assert len(values) == 6
