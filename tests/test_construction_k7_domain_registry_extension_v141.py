from acfqp import construction_k7_domain_registry_extension_v141 as domains


def test_v141_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V141) == 2
    assert all(tag.endswith(":v141") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V141)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V141.isdisjoint(
        {"acfqp:construction-k7-heterogeneous-archive-dictionary:v137"}
    )
