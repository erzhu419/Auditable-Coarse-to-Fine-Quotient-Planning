from __future__ import annotations

import copy
import json
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v92 as v92
from acfqp import construction_k7_domain_registry_extension_v93 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre
from acfqp.terminal_overlay_target_campaign_core_v93 import (
    build_terminal_overlay_target_campaign_document_v93,
)


def test_v93_domains_are_fresh_and_disjoint_from_v92():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V93) == 6
    assert domains.K7_DOMAIN_TAG_EXTENSION_V93.isdisjoint(
        v92.K7_DOMAIN_TAG_EXTENSION_V92
    )


def test_v93_development_gate_closes_without_upgrading_claims():
    config = copy.deepcopy(pre.campaign_config_v91r2())
    config.update(
        target_family="COUPLED_EXCHANGE",
        target_seeds=(941_101,),
        target_episode_index=2,
        target_worker_count=1,
        required_target_occurrence_count=1,
        target_joint_acquisition_maximum_ground_labels=160,
        terminal_confidence_denominator=4,
        maximum_terminal_program_candidates=128,
        maximum_target_ground_support_labels=10_000,
        maximum_abstract_depth=5,
        maximum_execution_steps=12,
        maximum_robust_state_depth_evaluations=1,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=8,
    )
    model = json.loads(
        Path(".tmp/exact-freeze/v91r3_source_model_acceptance.json").read_text()
    )["accepted_joint_successor_version_space_model"]
    document = build_terminal_overlay_target_campaign_document_v93(
        config,
        preregistration_id="1" * 64,
        source_acceptance_id="2" * 64,
        source_acceptance_verification_id="3" * 64,
        source_campaign_id="4" * 64,
        source_campaign_verification_id="5" * 64,
        v92_failed_campaign_id="6" * 64,
        v92_failed_verification_id="7" * 64,
        source_accounting={"source_labels": 1},
        model=model,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "every_target_certificate_label_reduction_observed"
    ] is True
    occurrence = document["target_occurrences"][0]
    assert occurrence["target_joint_acquisition"]["raw_transition_rows"]
    assert occurrence["target_joint_acquisition"]["action_catalogue"]
    assert document["producer_free_verification_present"] is False
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
