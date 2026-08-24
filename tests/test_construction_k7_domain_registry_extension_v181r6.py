from acfqp import construction_k7_domain_registry_extension_v181r6 as domains


def test_v181r6_domains_are_fresh_and_complete() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V181R6) == 9
    assert all(
        value.endswith(":v181r6")
        for value in domains.K7_DOMAIN_TAG_EXTENSION_V181R6
    )
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V181R6.values())) == 9


def test_v181r6_content_ids_are_domain_separated() -> None:
    payload = {"schema": "test", "value": 1}
    ids = {
        domains.extension_content_id_v181r6(domain, payload)
        for domain in domains.K7_DOMAIN_TAG_EXTENSION_V181R6
    }
    assert len(ids) == 9
