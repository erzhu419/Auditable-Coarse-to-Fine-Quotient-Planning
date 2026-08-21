from acfqp import construction_k7_domain_registry_extension_v131r2 as domains


def test_v131r2_domains_are_additive_and_dictionary_domain_is_distinct():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V131R2) == 7
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131R2.values())) == 7
    assert (
        domains.CONSTRUCTION_K7_ROBUST_FACTOR_DICTIONARY_V131R2_DOMAIN
        in domains.K7_DOMAIN_TAG_EXTENSION_V131R2
    )
    assert all(value.endswith(":v131r2") for value in domains.K7_DOMAIN_TAG_EXTENSION_V131R2)
