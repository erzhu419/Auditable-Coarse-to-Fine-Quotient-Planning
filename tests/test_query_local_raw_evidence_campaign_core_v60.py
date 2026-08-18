from acfqp import construction_k7_domain_registry_extension_v60 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as base
from acfqp import query_local_raw_evidence_campaign_core_v60 as subject


def test_v60_development_occurrence_embeds_replayable_raw_prefixes():
    config = base.campaign_config_v59()
    config["v60_domains"] = {
        "acquisition": domains.CONSTRUCTION_K7_QUERY_LOCAL_ACQUISITION_V60_DOMAIN,
        "raw_evidence": domains.CONSTRUCTION_K7_QUERY_LOCAL_RAW_EVIDENCE_V60_DOMAIN,
        "certificate": domains.CONSTRUCTION_K7_QUERY_LOCAL_CERTIFICATE_V60_DOMAIN,
        "distinction": domains.CONSTRUCTION_K7_QUERY_LOCAL_DISTINCTION_V60_DOMAIN,
        "episode": domains.CONSTRUCTION_K7_QUERY_LOCAL_EPISODE_V60_DOMAIN,
        "sample_tax": domains.CONSTRUCTION_K7_QUERY_LOCAL_SAMPLE_TAX_V60_DOMAIN,
        "campaign": domains.CONSTRUCTION_K7_QUERY_LOCAL_CAMPAIGN_V60_DOMAIN,
    }
    adapter = subject.predecessor.predecessor.predecessor.prior_ground._adapter(
        "MAINTENANCE_CASCADE", 590_301, config
    )
    result = subject.acquire_query_local_raw_evidence_v60(
        adapter, base.previous.previous.FACTOR_LIBRARY, config
    )
    assert result["raw_evidence"]["symmetric_common_prefix_reconstructible_from_bytes"] is True
    for acquisition in result["acquisitions"].values():
        document = acquisition["document"]
        assert len(document["raw_transition_batches"]) == document["ground_support_labels"]
        assert document["producer_free_raw_prefix_replay_enabled"] is True
