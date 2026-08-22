from acfqp import construction_k7_domain_registry_extension_v172 as domains


def test_v172_domains_are_additive_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V172) == 8
    assert all(tag.endswith(":v172") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V172)


def test_v172_rejects_unregistered_domain():
    try:
        domains.extension_content_id_v172("acfqp:forged:v172", {})
    except ValueError as error:
        assert "absent" in str(error)
    else:
        raise AssertionError("unregistered V172 domain accepted")
