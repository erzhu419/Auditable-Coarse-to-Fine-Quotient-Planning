from acfqp import construction_k7_domain_registry_extension_v122 as domains


def test_v122_domains_are_unique_and_content_addressed():
    registry = dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V122)
    assert len(registry) == 5
    assert len(set(registry.values())) == len(registry)
    assert set(registry.values()).isdisjoint(
        {
            "acfqp:construction-k7-generic-artifact-subprogram-campaign:v121",
            "acfqp:construction-k7-generic-subprogram-opportunity-independent-campaign:v121r1",
        }
    )
    domain = domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_SEQUENCE_V122_DOMAIN
    assert domains.extension_content_id_v122(domain, {"a": 1}) == (
        domains.extension_content_id_v122(domain, {"a": 1})
    )
