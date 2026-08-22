from acfqp import construction_k7_domain_registry_extension_v171 as domains


def test_v171_domains_are_additive_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V171) == 8
    assert all(tag.endswith(":v171") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V171)


def test_v171_rejects_unregistered_domain():
    try:
        domains.extension_content_id_v171("acfqp:forged:v171", {})
    except ValueError as error:
        assert "absent" in str(error)
    else:
        raise AssertionError("unregistered V171 domain accepted")
