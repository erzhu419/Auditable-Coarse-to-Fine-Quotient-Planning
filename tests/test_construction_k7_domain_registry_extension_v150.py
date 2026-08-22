from acfqp import construction_k7_domain_registry_extension_v150 as domains


def test_v150_domains_are_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V150) == 5
    assert all(tag.endswith(":v150") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V150)
