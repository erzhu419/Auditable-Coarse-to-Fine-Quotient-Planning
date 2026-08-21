from acfqp import construction_k7_domain_registry_extension_v131 as domains


def test_v131_domains_are_additive_and_dictionary_domain_is_distinct():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V131) == 7
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131.values())) == 7
    assert (
        domains.CONSTRUCTION_K7_AUTOMATIC_FACTOR_DICTIONARY_V131_DOMAIN
        in domains.K7_DOMAIN_TAG_EXTENSION_V131
    )
    assert all(value.endswith(":v131") for value in domains.K7_DOMAIN_TAG_EXTENSION_V131)
