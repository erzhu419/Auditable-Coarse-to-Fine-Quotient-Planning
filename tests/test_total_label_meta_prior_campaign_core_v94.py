from __future__ import annotations

import copy
import json
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v93 as v93
from acfqp import construction_k7_domain_registry_extension_v94 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre
from acfqp.total_label_meta_prior_campaign_core_v94 import (
    build_total_label_meta_prior_campaign_document_v94,
)


def test_v94_domains_are_fresh_and_disjoint_from_v93():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V94) == 6
    assert domains.K7_DOMAIN_TAG_EXTENSION_V94.isdisjoint(
        v93.K7_DOMAIN_TAG_EXTENSION_V93
    )


def test_v94_development_gate_counts_all_target_labels_and_closes():
    config = copy.deepcopy(pre.campaign_config_v91r2())
    config.update(
        target_family="COUPLED_EXCHANGE",
        target_seeds=(961_101, 961_102),
        target_episode_index=3,
        target_worker_count=1,
        required_target_occurrence_count=2,
        source_meta_prior_odds=16,
        confidence_denominator=4,
        maximum_applicability_ground_support_labels=40,
        maximum_incremental_certificate_ground_support_labels=10_000,
        maximum_abstract_depth=5,
        maximum_execution_steps=12,
        maximum_robust_state_depth_evaluations=1,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=8,
    )
    model = json.loads(
        Path(".tmp/exact-freeze/v91r3_source_model_acceptance.json").read_text()
    )["accepted_joint_successor_version_space_model"]
    document = build_total_label_meta_prior_campaign_document_v94(
        config,
        preregistration_id="1" * 64,
        source_acceptance_id="2" * 64,
        source_acceptance_verification_id="3" * 64,
        source_campaign_id="4" * 64,
        source_campaign_verification_id="5" * 64,
        v93_failed_campaign_id="6" * 64,
        v93_failed_verification_id="7" * 64,
        source_accounting={"source_labels": 1},
        model=model,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["meta_prior_total_target_labels"] == 14
    assert document["accounting"]["no_prior_total_target_labels"] == 20
    assert document["accounting"]["strict_cold_direct_labels"] == 16
    assert document["registered_gate"][
        "meta_prior_total_labels_noninferior_to_direct_on_every_target"
    ] is True
    assert document["sample_tax_reduction_verified_on_registered_target_workload"] is True
    assert document["sample_tax_reduction_generalized_beyond_registered_workload"] is False
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
