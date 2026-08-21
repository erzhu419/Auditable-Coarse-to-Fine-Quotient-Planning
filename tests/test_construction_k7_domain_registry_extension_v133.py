from acfqp import construction_k7_domain_registry_extension_v133 as domains


def test_v133_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V133) == 5
    assert all(tag.endswith(":v133") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V133)
    assert len(domains.extension_content_id_v133(
        domains.CONSTRUCTION_K7_OPAQUE_ARCHIVE_PLANNING_CAMPAIGN_V133_DOMAIN,
        {"schema": "test"},
    )) == 64
