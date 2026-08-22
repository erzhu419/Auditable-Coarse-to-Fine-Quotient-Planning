from acfqp import construction_k7_domain_registry_extension_v143r1 as domains


def test_v143r1_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V143R1) == 5
    assert all(tag.endswith(":v143r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V143R1)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V143R1.isdisjoint(
        {
            "acfqp:construction-k7-occurrence-factor-bank-update:v141",
            "acfqp:construction-k7-occurrence-factor-bank-update-campaign:v140",
        }
    )
