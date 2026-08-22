from acfqp import construction_k7_domain_registry_extension_v145 as domains


def test_v145_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V145) == 4
    assert all(value.endswith(":v145") for value in domains.K7_DOMAIN_TAG_EXTENSION_V145)
    domain = domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_CAMPAIGN_V145_DOMAIN
    assert domains.extension_content_id_v145(domain, {"a": 1}) != domains.extension_content_id_v145(domain, {"a": 2})
