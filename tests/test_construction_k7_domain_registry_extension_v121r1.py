from acfqp import construction_k7_domain_registry_extension_v121r1 as domains


def test_v121r1_domain_registry_is_additive_and_exact():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V121R1) == 4
    assert all(value.endswith(":v121r1") for value in domains.K7_DOMAIN_TAG_EXTENSION_V121R1)
