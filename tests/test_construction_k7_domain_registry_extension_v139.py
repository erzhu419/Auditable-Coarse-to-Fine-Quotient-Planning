from acfqp import construction_k7_domain_registry_extension_v139 as domains


def test_v139_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V139) == 2
    assert all(tag.endswith(":v139") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V139)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V139.isdisjoint(
        {"acfqp:construction-k7-heterogeneous-archive-dictionary:v137"}
    )
