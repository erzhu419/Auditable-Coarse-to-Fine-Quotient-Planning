from __future__ import annotations

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp.universal_mixture_three_domain_campaign_core_v58 import (
    build_universal_mixture_three_domain_campaign_document_v58,
)


def _config():
    config = v57.campaign_config_v57()
    config["successor_domains"] = {
        "acquisition": (
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        "sample_tax": (
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_SAMPLE_TAX_V58_DOMAIN
        ),
        "campaign": (
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_CAMPAIGN_V58_DOMAIN
        ),
    }
    config["v57_campaign_id"] = (
        "744e764a35cb7ba4955852fa62c30978b7aac35d0761b7054cb64298be1fd92b"
    )
    config["v57_verification_id"] = (
        "f38218a0a527dd4411bf1d105162f563eae1800d68bab6d9b821cb0e693d1469"
    )
    config["worker_count"] = 2
    config["require_lifetime_sample_tax_gate"] = False
    config["families"]["BALANCED_BATCH_REFINEMENT"].update(
        target_seeds=(589_910, 589_911),
        planning_seed_count=1,
        maximum_acquisition_labels=192,
    )
    config["families"]["COUPLED_EXCHANGE"].update(
        target_seeds=(589_920, 589_921),
        planning_seed_count=1,
        maximum_acquisition_labels=224,
    )
    config["families"]["MAINTENANCE_CASCADE"].update(
        target_seeds=(589_930, 589_931),
        planning_seed_count=1,
        maximum_acquisition_labels=288,
    )
    return config


def test_v58_development_three_domain_campaign_removes_tuned_evidence_scaffold():
    document = build_universal_mixture_three_domain_campaign_document_v58(
        _config(), "d" * 64, v57.FACTOR_LIBRARY
    )
    assert document["families"] == [
        "BALANCED_BATCH_REFINEMENT",
        "COUPLED_EXCHANGE",
        "MAINTENANCE_CASCADE",
    ]
    assert document["betting_fraction_selected"] is False
    assert document["success_evalue_multiplier_selected"] is False
    assert document["epoch_spending_base_selected"] is False
    assert document["predictive_evidence_to_mdl_credit_selected"] is True
    assert document["predictive_evidence_to_mdl_credit_inherited_from_v57"] is True
    assert document["reachable_frontier_exhaustion_stop_consumed"] is False
    assert document["sample_tax"]["incremental_acquisition_label_reduction"] > 0
    assert document["sample_tax"]["online_label_reduction_including_local_recovery"] > 0
    assert document["sample_tax"]["lifetime_sample_tax_gate_enforced"] is False
    assert all(
        row["terminal_stop_update"]["universal_mixture_evalue_threshold_met"]
        and row["terminal_stop_update"]["combined_mdl_predictive_margin_units"]
        >= 0
        for rows in document["acquisitions"].values()
        for row in rows
    )
    assert len(document["episodes"]["ANONYMOUS_FACTOR_PRIOR_ON"]) == 3
    assert len(document["episodes"]["STRICT_NO_PRIOR"]) == 3
    assert len(document["episodes"]["STRICT_EXACT_CONTEXT"]) == 3
    assert all(
        row["success"]
        for rows in document["episodes"].values()
        for row in rows
    )
    assert document["ood_rejection"]["prior_transfer_attempted"] is False
    assert document["accounting"]["all_axes_separate"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
