from acfqp import construction_k7_domain_registry_extension_v168 as domains


def test_v168_domains_are_additive_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V168) == 6
    assert all(tag.endswith(":v168") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V168)


def test_v168_content_id_rejects_unregistered_domain():
    try:
        domains.extension_content_id_v168("acfqp:forged:v168", {})
    except ValueError as error:
        assert "absent" in str(error)
    else:
        raise AssertionError("unregistered V168 domain accepted")
