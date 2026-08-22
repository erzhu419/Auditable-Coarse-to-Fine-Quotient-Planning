from acfqp import construction_k7_domain_registry_extension_v169 as domains


def test_v169_domains_are_additive_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V169) == 3
    assert all(tag.endswith(":v169") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V169)


def test_v169_rejects_unregistered_domain():
    try:
        domains.extension_content_id_v169("acfqp:forged:v169", {})
    except ValueError as error:
        assert "absent" in str(error)
    else:
        raise AssertionError("unregistered V169 domain accepted")
