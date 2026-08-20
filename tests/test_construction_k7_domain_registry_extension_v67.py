from acfqp import construction_k7_domain_registry_extension_v67 as domains


def test_v67_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V67) == 5
    assert all(tag.endswith(":v67") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V67)
    domain = domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_CAMPAIGN_V67_DOMAIN
    assert domains.extension_content_id_v67(domain, {"x": 1}) == domains.extension_content_id_v67(
        domain, {"x": 1}
    )
