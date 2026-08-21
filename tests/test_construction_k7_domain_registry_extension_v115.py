from acfqp import construction_k7_domain_registry_extension_v115 as domains


def test_v115_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V115) == 6
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V115) == 6
    assert all(tag.endswith(":v115") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V115)
    domain = domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_CAMPAIGN_V115_DOMAIN
    assert domains.extension_content_id_v115(domain, {"x": 1}) == domains.extension_content_id_v115(
        domain, {"x": 1}
    )
