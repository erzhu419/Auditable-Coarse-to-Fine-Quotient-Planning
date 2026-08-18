from acfqp import construction_k7_domain_registry_extension_v62 as domains


def test_v62_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V62) == 3
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V62) == 3
    first = domains.extension_content_id_v62(
        domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_LIBRARY_V62_DOMAIN, {"a": 1}
    )
    second = domains.extension_content_id_v62(
        domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_SOURCE_V62_DOMAIN, {"a": 1}
    )
    assert first != second
