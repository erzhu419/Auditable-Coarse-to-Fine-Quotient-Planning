from acfqp import construction_k7_domain_registry_extension_v137 as domains


def test_v137_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V137) == 2
    assert all(tag.endswith(":v137") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V137)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V137.isdisjoint(
        {"acfqp:construction-k7-auto-calibrated-archive-dictionary:v135"}
    )
