from acfqp import construction_k7_domain_registry_extension_v174 as domains


def test_v174_domains_are_additive_and_closed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V174) == 11
    assert all(tag.endswith(":v174") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V174)


def test_v174_rejects_unknown_domain():
    try:
        domains.extension_content_id_v174("acfqp:forged:v174", {})
    except ValueError:
        pass
    else:
        raise AssertionError("V174 accepted an unknown domain")
