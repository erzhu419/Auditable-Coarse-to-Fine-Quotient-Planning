from __future__ import annotations

import json
from pathlib import Path

from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as previous
from acfqp.version_space_target_campaign_core_v92 import (
    build_version_space_target_campaign_document_v92,
)


def test_v92_development_campaign_closes_two_target_gate():
    acceptance = json.loads(
        Path(".tmp/exact-freeze/v91r3_source_model_acceptance.json").read_text()
    )
    source = json.loads(
        Path(
            ".tmp/exact-freeze/v91r2_prior_only_occurrence_source_campaign.json"
        ).read_text()
    )
    config = previous.campaign_config_v91r2()
    config.update(
        target_family="COUPLED_EXCHANGE",
        target_seeds=(941_101, 941_102),
        target_episode_index=1,
        target_worker_count=1,
        required_target_occurrence_count=2,
        target_partial_acquisition_maximum_ground_labels=160,
        maximum_robust_state_depth_evaluations=1,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=8,
        maximum_target_ground_support_labels=10_000,
        maximum_abstract_depth=5,
        maximum_execution_steps=12,
    )
    campaign = build_version_space_target_campaign_document_v92(
        config,
        preregistration_id="p" * 64,
        source_acceptance_id=acceptance["acceptance_id"],
        source_acceptance_verification_id="v" * 64,
        source_campaign_id=source["campaign_id"],
        source_campaign_verification_id="w" * 64,
        source_accounting=source["accounting"],
        model=acceptance["accepted_joint_successor_version_space_model"],
    )
    assert campaign["registered_gate"]["passed"] is True
    assert campaign["registered_gate"][
        "multi_step_abstract_proposal_primary_on_every_target"
    ] is True
    assert campaign["registered_gate"][
        "complete_actual_version_space_jointly_propagated"
    ] is True
    assert campaign["registered_gate"][
        "aggregate_target_certificate_label_reduction_observed"
    ] is True
    assert campaign["official_execution_allowed"] is False
    assert campaign["official_scalar_cost"] is None
    assert campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
