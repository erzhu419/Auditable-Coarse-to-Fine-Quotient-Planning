from acfqp import construction_k7_domain_registry_extension_v152 as domains


def test_v152_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V152) == 4
    assert all(tag.endswith(":v152") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V152)
    assert domains.extension_content_id_v152(domains.CONSTRUCTION_K7_CAMPAIGN_V152_DOMAIN, {"x": 1}) != domains.extension_content_id_v152(domains.CONSTRUCTION_K7_OCCURRENCE_V152_DOMAIN, {"x": 1})
