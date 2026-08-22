from acfqp import construction_k7_domain_registry_extension_v144r1 as domains


def test_v144r1_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V144R1) == 10
    assert all(tag.endswith(":v144r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V144R1)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V144R1.isdisjoint(
        {
            "acfqp:construction-k7-fifth-family-factor-bank-transfer-campaign:v144",
            "acfqp:construction-k7-relational-factor-execution-projection:v144",
        }
    )
