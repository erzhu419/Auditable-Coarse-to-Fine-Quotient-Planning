from acfqp import construction_k7_domain_registry_extension_v144r2 as domains


def test_v144r2_domains_are_additive_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V144R2) == 4
    assert all(value.endswith(":v144r2") for value in domains.K7_DOMAIN_TAG_EXTENSION_V144R2)
    payload = {"fresh": True, "outcome_free": True}
    domain = domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_PREREGISTRATION_V144R2_DOMAIN
    assert domains.extension_content_id_v144r2(domain, payload) == domains.extension_content_id_v144r2(domain, payload)
