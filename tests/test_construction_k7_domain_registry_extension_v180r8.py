from acfqp import construction_k7_domain_registry_extension_v180r8 as domains


def test_v180r8_domain_registry_is_additive_and_exact() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R8) == 6
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R8) == 6
    assert all(tag.endswith(":v180r8") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V180R8)


def test_v180r8_roles_are_domain_separated() -> None:
    payload = {"same": "payload"}
    identifiers = {
        domains.extension_content_id_v180r8(tag, payload)
        for tag in domains.K7_DOMAIN_TAG_EXTENSION_V180R8
    }
    assert len(identifiers) == 6
