from __future__ import annotations

import json
from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_low_label_residual_applicability_v73 import (
    acquire_low_label_residual_applicability_v73,
)
from acfqp.generic_total_label_residual_transfer_ablation_v75 import (
    run_total_label_residual_transfer_ablation_v75,
)


@pytest.fixture(scope="module")
def matched_development_results():
    config = pre.campaign_config_v91r2()
    model = json.loads(
        Path(".tmp/exact-freeze/v91r3_source_model_acceptance.json").read_text()
    )["accepted_joint_successor_version_space_model"]
    result = []
    for seed in (961_101, 961_102):
        rows = {}
        for name, odds in (("META_PRIOR", 16), ("NO_PRIOR", 1)):
            adapter = v59.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
                "COUPLED_EXCHANGE", seed, config
            )
            acquisition = acquire_low_label_residual_applicability_v73(
                adapter,
                model,
                maximum_ground_support_labels=40,
                confidence_denominator=4,
                source_meta_prior_odds=odds,
                layout_domain=config["generic_domains"]["layout"],
                applicability_domain=(
                    domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_MEMBER_V91R2_DOMAIN
                ),
                content_id=domains.extension_content_id_v91r2,
            )
            ablation = run_total_label_residual_transfer_ablation_v75(
                acquisition["projected_adapter"],
                acquisition["candidate"],
                acquisition["aligned_rows"],
                acquisition["document"]["ground_support_labels"],
                model,
                episode_index=3,
                maximum_abstract_depth=5,
                maximum_execution_steps=12,
                maximum_incremental_certificate_ground_support_labels=10_000,
                maximum_robust_state_depth_evaluations=1,
                maximum_abstract_support_branch_evaluations=1_000_000,
                abstract_support_feasible_beam_width=8,
            )
            rows[name] = (acquisition, ablation)
        result.append((seed, rows))
    return result


def test_empirical_meta_prior_reduces_acquisition_without_authority(
    matched_development_results,
):
    prior_labels = []
    no_prior_labels = []
    for _seed, rows in matched_development_results:
        prior = rows["META_PRIOR"][0]["document"]
        no_prior = rows["NO_PRIOR"][0]["document"]
        prior_labels.append(prior["ground_support_labels"])
        no_prior_labels.append(no_prior["ground_support_labels"])
        assert prior["source_meta_prior_only_stop_at_issuance"] is True
        assert prior["target_predictive_confirmation_count"] == 0
        assert prior["residual_applicability_promoted_to_global_fact"] is False
        assert prior["proposal_used_as_safety_authority"] is False
        assert no_prior["source_meta_prior_only_stop_at_issuance"] is False
    assert prior_labels == [1, 2]
    assert no_prior_labels == [6, 7]


def test_total_label_accounting_beats_no_prior_and_cold_direct_in_aggregate(
    matched_development_results,
):
    prior_totals = []
    no_prior_totals = []
    strict_totals = []
    for _seed, rows in matched_development_results:
        prior = rows["META_PRIOR"][1]
        no_prior = rows["NO_PRIOR"][1]
        prior_episode = prior["arms"]["LOW_LABEL_RESIDUAL_TRANSFER"]
        no_prior_episode = no_prior["arms"]["LOW_LABEL_RESIDUAL_TRANSFER"]
        strict_episode = prior["arms"]["STRICT_COLD_DIRECT_GROUND"]
        prior_totals.append(prior_episode["total_target_ground_support_labels"])
        no_prior_totals.append(
            no_prior_episode["total_target_ground_support_labels"]
        )
        strict_totals.append(strict_episode["total_target_ground_support_labels"])
        assert prior_episode["total_target_ground_support_labels"] <= strict_episode[
            "total_target_ground_support_labels"
        ]
        assert prior_episode["all_incremental_ground_queries_followed_failed_certificates"] is True
        assert prior_episode["model_or_alignment_used_as_safety_authority"] is False
        assert prior_episode["execution_action_matches_abstract_proposal_count"] >= 2
    assert prior_totals == [6, 8]
    assert no_prior_totals == [10, 10]
    assert strict_totals == [8, 8]
    assert sum(prior_totals) < sum(strict_totals) < sum(no_prior_totals)
