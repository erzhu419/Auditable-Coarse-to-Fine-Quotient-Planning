from acfqp import construction_k7_domain_registry_extension_v173 as domains


def test_v173_domains_are_additive_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V173) == 5
    assert all(tag.endswith(":v173") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V173)


def test_v173_rejects_unknown_domain():
    try:
        domains.extension_content_id_v173("acfqp:forged:v173", {})
    except ValueError:
        pass
    else:
        raise AssertionError("V173 accepted an unregistered domain")
