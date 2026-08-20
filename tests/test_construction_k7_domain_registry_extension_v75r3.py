from acfqp import construction_k7_domain_registry_extension_v75r3 as domains


def test_v75r3_domains_are_unique_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V75R3) == 3
    domain = domains.CONSTRUCTION_K7_FAIL_CLOSED_PRIORITY_CAMPAIGN_V75R3_DOMAIN
    assert domains.extension_content_id_v75r3(domain, {"a": 1}) != (
        domains.extension_content_id_v75r3(domain, {"a": 2})
    )
