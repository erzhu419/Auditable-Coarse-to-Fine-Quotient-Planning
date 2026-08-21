from acfqp import construction_k7_domain_registry_extension_v142 as domains


def test_v142_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V142) == 5
    assert all(tag.endswith(":v142") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V142)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V142.isdisjoint(
        {
            "acfqp:construction-k7-occurrence-factor-bank-update:v141",
            "acfqp:construction-k7-occurrence-factor-bank-update-campaign:v140",
        }
    )
