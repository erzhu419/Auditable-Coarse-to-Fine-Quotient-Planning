from acfqp import construction_k7_query_local_preregistration_v60 as previous
from acfqp import construction_k7_domain_registry_extension_v61 as domains
from acfqp.persistent_overlay_campaign_core_v61 import _run_occurrence


def test_v61_development_occurrence_reuses_overlay_without_later_ground_queries():
    config = previous.campaign_config_v60()
    config["worker_count"] = 1
    config["episode_indices"] = [0, 1, 2]
    config["v61_domains"] = {
        "raw_evidence": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_RAW_EVIDENCE_V61_DOMAIN,
        "acquisition": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_ACQUISITION_V61_DOMAIN,
        "certificate": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_CERTIFICATE_V61_DOMAIN,
        "distinction": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_DISTINCTION_V61_DOMAIN,
        "episode": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_EPISODE_V61_DOMAIN,
        "run": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_RUN_V61_DOMAIN,
        "sample_tax": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_SAMPLE_TAX_V61_DOMAIN,
        "campaign": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_CAMPAIGN_V61_DOMAIN,
        "verification": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_VERIFICATION_V61_DOMAIN,
    }
    row = _run_occurrence(
        (
            "COUPLED_EXCHANGE",
            590_402,
            previous.previous.previous.previous.FACTOR_LIBRARY,
            config,
        )
    )
    run = row["run"]
    assert run["success"] is True
    assert run["persistent_local_ground_support_labels"] > 0
    assert run["cold_restart_local_ground_support_labels"] > run["persistent_local_ground_support_labels"]
    assert run["later_episode_ground_query_count"] == 0
    assert run["matched_action_and_outcome_tapes"] is True
    assert run["occurrence_identity_bound"] is True
    assert run["cross_occurrence_ground_fact_reuse_allowed"] is False
