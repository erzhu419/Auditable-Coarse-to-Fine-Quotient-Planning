from acfqp import construction_k7_domain_registry_extension_v140 as domains


def test_v140_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V140) == 5
    assert all(tag.endswith(":v140") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V140)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V140.isdisjoint(
        {"acfqp:construction-k7-occurrence-factor-bank:v139"}
    )
