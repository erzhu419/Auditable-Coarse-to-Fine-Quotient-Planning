from acfqp import construction_k7_domain_registry_extension_v176 as domains


def test_v176_domains_are_fresh_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V176) == 9
    assert all(tag.endswith(":v176") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V176)
    assert domains.extension_content_id_v176(
        domains.CONSTRUCTION_K7_SEQUENCE_V176_DOMAIN, {"x": 1}
    ) != domains.extension_content_id_v176(
        domains.CONSTRUCTION_K7_SEQUENCE_V176_DOMAIN, {"x": 2}
    )
