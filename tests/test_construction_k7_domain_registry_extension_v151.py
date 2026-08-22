from acfqp import construction_k7_domain_registry_extension_v151 as domains


def test_v151_domains_are_unique():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V151) == 4
    assert all(tag.endswith(":v151") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V151)
