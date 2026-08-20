from acfqp import construction_k7_domain_registry_extension_v68 as v68


def test_v68_domains_are_disjoint_and_content_addressed():
    assert len(v68.K7_DOMAIN_TAG_EXTENSION_V68) == 5
    assert len(v68.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V68) == 5
    domain = v68.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_PREREGISTRATION_V68_DOMAIN
    assert v68.extension_content_id_v68(domain, {"x": 1}) == v68.extension_content_id_v68(
        domain, {"x": 1}
    )

