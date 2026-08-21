from acfqp import construction_k7_domain_registry_extension_v101 as domains


def test_v101_domains_are_fresh_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V101) == 4
    assert all(value.endswith(":v101") for value in domains.K7_DOMAIN_TAG_EXTENSION_V101)
    assert len(
        {
            domains.extension_content_id_v101(domain, {"x": 1})
            for domain in domains.K7_DOMAIN_TAG_EXTENSION_V101
        }
    ) == 4
