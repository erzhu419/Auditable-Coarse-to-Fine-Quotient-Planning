from acfqp import construction_k7_domain_registry_extension_v148 as domains


def test_v148_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V148) == 7
    assert all(tag.endswith(":v148") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V148)
