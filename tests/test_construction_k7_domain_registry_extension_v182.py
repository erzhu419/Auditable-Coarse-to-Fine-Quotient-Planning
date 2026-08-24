from acfqp import construction_k7_domain_registry_extension_v182 as domains


def test_v182_domains_are_exact_and_separated() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182) == 6
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V182) == 6
    assert all(value.endswith(":v182") for value in domains.K7_DOMAIN_TAG_EXTENSION_V182)
    payload = {"same": "payload"}
    assert len(
        {
            domains.extension_content_id_v182(domain, payload)
            for domain in domains.K7_DOMAIN_TAG_EXTENSION_V182
        }
    ) == 6
