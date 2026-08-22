from acfqp import construction_k7_domain_registry_extension_v170 as domains


def test_v170_domains_are_additive_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V170) == 5
    assert all(tag.endswith(":v170") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V170)


def test_v170_rejects_unregistered_domain():
    try:
        domains.extension_content_id_v170("acfqp:forged:v170", {})
    except ValueError as error:
        assert "absent" in str(error)
    else:
        raise AssertionError("unregistered V170 domain accepted")
