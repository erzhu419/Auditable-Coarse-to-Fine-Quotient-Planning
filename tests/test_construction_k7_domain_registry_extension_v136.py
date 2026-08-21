from acfqp import construction_k7_domain_registry_extension_v136 as domains


def test_v136_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V136) == 5
    assert all(tag.endswith(":v136") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V136)
    assert domains.K7_DOMAIN_TAG_EXTENSION_V136.isdisjoint(
        {
            "acfqp:construction-k7-auto-calibrated-archive-dictionary:v135",
            "acfqp:construction-k7-auto-calibrated-archive-verification:v135",
        }
    )
    domain = domains.CONSTRUCTION_K7_AUTO_CALIBRATED_ARCHIVE_CAMPAIGN_V136_DOMAIN
    assert domains.extension_content_id_v136(domain, {"x": 1}) == domains.extension_content_id_v136(
        domain, {"x": 1}
    )
