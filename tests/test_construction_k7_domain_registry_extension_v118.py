from acfqp import construction_k7_domain_registry_extension_v118 as domains


def test_v118_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V118) == 4
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V118.values())) == 4
    payload = {"schema": "test.v118", "value": 1}
    assert len(
        {
            domains.extension_content_id_v118(domain, payload)
            for domain in domains.K7_DOMAIN_TAG_EXTENSION_V118
        }
    ) == 4
