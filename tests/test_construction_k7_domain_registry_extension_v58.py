from acfqp import construction_k7_domain_registry_extension_v58 as v58


def test_v58_domain_registry_is_additive_and_unique():
    assert len(v58.K7_DOMAIN_TAG_EXTENSION_V58) == 5
    assert len(v58.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V58) == 5
    assert all(tag.endswith(":v58") for tag in v58.K7_DOMAIN_TAG_EXTENSION_V58)


def test_v58_content_ids_are_domain_separated():
    tags = tuple(v58.K7_DOMAIN_TAG_EXTENSION_V58)
    assert len({v58.extension_content_id_v58(tag, {"x": 1}) for tag in tags}) == 5
