from acfqp import construction_k7_domain_registry_extension_v70 as v70


def test_v70_domains_are_disjoint_and_content_addressed():
    assert len(v70.K7_DOMAIN_TAG_EXTENSION_V70) == 6
    assert len(v70.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V70) == 6
    domain = v70.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_LIBRARY_V70_DOMAIN
    assert v70.extension_content_id_v70(domain, {"x": 1}) == v70.extension_content_id_v70(
        domain, {"x": 1}
    )

