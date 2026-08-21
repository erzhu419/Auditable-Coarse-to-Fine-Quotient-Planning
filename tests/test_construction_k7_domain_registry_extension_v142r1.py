from acfqp import construction_k7_domain_registry_extension_v142r1 as domains


def test_v142r1_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V142r1) == 5
    assert all(tag.endswith(":v142r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V142r1)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V142r1.isdisjoint(
        {
            "acfqp:construction-k7-occurrence-factor-bank-update:v141",
            "acfqp:construction-k7-occurrence-factor-bank-update-campaign:v140",
        }
    )
