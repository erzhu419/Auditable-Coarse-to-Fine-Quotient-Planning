from acfqp import construction_k7_domain_registry_extension_v69 as v69


def test_v69_domains_are_disjoint_and_content_addressed():
    assert len(v69.K7_DOMAIN_TAG_EXTENSION_V69) == 5
    assert len(v69.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V69) == 5
    domain = v69.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_PREREGISTRATION_V69_DOMAIN
    assert v69.extension_content_id_v69(domain, {"x": 1}) == v69.extension_content_id_v69(
        domain, {"x": 1}
    )

