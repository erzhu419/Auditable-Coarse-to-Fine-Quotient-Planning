from acfqp import construction_k7_domain_registry_extension_v134 as domains


def test_v134_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V134) == 4
    assert all(tag.endswith(":v134") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V134)
    assert len(domains.extension_content_id_v134(
        domains.CONSTRUCTION_K7_PACKET_BATCHING_TRANSFER_CAMPAIGN_V134_DOMAIN,
        {"schema": "test"},
    )) == 64
