from acfqp import construction_k7_domain_registry_extension_v144 as domains


def test_v144_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V144) == 6
    assert all(tag.endswith(":v144") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V144)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V144.isdisjoint(
        {
            "acfqp:construction-k7-occurrence-factor-bank-update:v141",
            "acfqp:construction-k7-occurrence-factor-bank-update-campaign:v140",
            "acfqp:construction-k7-fifth-family-factor-bank-transfer-campaign:v143r1",
        }
    )
