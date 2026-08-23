from acfqp import construction_k7_domain_registry_extension_v173r1 as domains


def test_v173r1_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V173R1) == 5
    assert all(
        tag.endswith(":v173r1")
        for tag in domains.K7_DOMAIN_TAG_EXTENSION_V173R1
    )


def test_v173r1_rejects_unknown_domain():
    try:
        domains.extension_content_id_v173r1("acfqp:forged:v173r1", {})
    except ValueError:
        pass
    else:
        raise AssertionError("V173r1 accepted an unknown domain")
