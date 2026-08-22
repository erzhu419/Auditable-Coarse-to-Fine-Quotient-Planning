from acfqp import construction_k7_domain_registry_extension_v147 as domains


def test_v147_domain_is_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V147) == 1
    assert next(iter(domains.K7_DOMAIN_TAG_EXTENSION_V147)).endswith(":v147")
