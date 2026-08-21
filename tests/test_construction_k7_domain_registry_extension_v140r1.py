from acfqp import construction_k7_domain_registry_extension_v140r1 as domains


def test_v140r1_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V140r1) == 5
    assert all(tag.endswith(":v140r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V140r1)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V140r1.isdisjoint(
        {
            "acfqp:construction-k7-occurrence-factor-bank:v139",
            "acfqp:construction-k7-occurrence-factor-bank-campaign:v140",
        }
    )
