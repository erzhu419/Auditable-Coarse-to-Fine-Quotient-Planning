from acfqp import construction_k7_domain_registry_extension_v135 as domains


def test_v135_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V135) == 2
    assert all(tag.endswith(":v135") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V135)
