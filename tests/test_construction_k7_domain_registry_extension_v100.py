from acfqp import construction_k7_domain_registry_extension_v100 as domains


def test_v100_domain_registry_is_fresh_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V100) == 4
    assert all(value.endswith(":v100") for value in domains.K7_DOMAIN_TAG_EXTENSION_V100)
    payload = {"registered_before_outcomes": True}
    left = domains.extension_content_id_v100(
        domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_PREREGISTRATION_V100_DOMAIN,
        payload,
    )
    right = domains.extension_content_id_v100(
        domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_CAMPAIGN_V100_DOMAIN,
        payload,
    )
    assert len(left) == 64
    assert left != right
