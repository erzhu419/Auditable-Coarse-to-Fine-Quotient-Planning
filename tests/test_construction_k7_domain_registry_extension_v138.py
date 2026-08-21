from acfqp import construction_k7_domain_registry_extension_v138 as domains


def test_v138_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V138) == 5
    assert all(tag.endswith(":v138") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V138)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V138.isdisjoint(
        {"acfqp:construction-k7-heterogeneous-archive-dictionary:v137"}
    )
