from functools import lru_cache

from acfqp import construction_k7_domain_registry_extension_v89 as domains
from acfqp import construction_k7_permutation_matched_sample_tax_preregistration_v89 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.generic_projected_low_label_applicability_v76 import (
    acquire_projected_low_label_applicability_v76,
)
from acfqp.generic_projected_persistent_sequence_v78 import (
    run_projected_persistent_sequence_v78,
)
from acfqp.generic_projected_total_label_ablation_v77 import (
    run_projected_total_label_ablation_v77,
)


@lru_cache(maxsize=1)
def _development_result():
    config = pre.campaign_config_v89()
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "BALANCED_BATCH_REFINEMENT", 929_101, config
    )
    model = load_projected_model_artifact_v86()[
        "projected_disagreement_successor_model"
    ]
    applicability = load_action_applicability_model_v87()[
        "action_applicability_program"
    ]
    shared = {
        "maximum_ground_support_labels": 40,
        "confidence_denominator": 4,
        "minimum_factor_assignment_count": config[
            "minimum_reusable_factor_count"
        ],
        "layout_domain": config["generic_domains"]["layout"],
        "acquisition_domain": (
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_OCCURRENCE_V89_DOMAIN
        ),
        "content_id": domains.extension_content_id_v89,
    }
    meta = acquire_projected_low_label_applicability_v76(
        adapter, model, applicability, source_meta_prior_odds=16, **shared
    )
    no_prior = acquire_projected_low_label_applicability_v76(
        adapter, model, applicability, source_meta_prior_odds=1, **shared
    )
    sequence_shared = {
        "model_source_episode_index": 0,
        "episode_indices": (13, 14),
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
        "maximum_abstract_support_branch_evaluations": config[
            "maximum_relational_support_branch_evaluations"
        ],
        "abstract_support_feasible_beam_width": config[
            "relational_support_feasible_beam_width"
        ],
    }
    meta_sequence = run_projected_persistent_sequence_v78(
        adapter,
        meta["candidate"],
        meta["rows"],
        meta["document"]["ground_support_labels"],
        model,
        applicability,
        **sequence_shared,
    )
    no_prior_sequence = run_projected_persistent_sequence_v78(
        adapter,
        no_prior["candidate"],
        no_prior["rows"],
        no_prior["document"]["ground_support_labels"],
        model,
        applicability,
        **sequence_shared,
    )
    single = run_projected_total_label_ablation_v77(
        adapter,
        meta["candidate"],
        meta["rows"],
        meta["document"]["ground_support_labels"],
        model,
        applicability,
        model_source_episode_index=0,
        episode_index=13,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
        maximum_abstract_support_branch_evaluations=config[
            "maximum_relational_support_branch_evaluations"
        ],
        abstract_support_feasible_beam_width=config[
            "relational_support_feasible_beam_width"
        ],
    )
    return meta, no_prior, meta_sequence, no_prior_sequence, single


def test_v76_same_rule_meta_prior_reduces_applicability_labels():
    meta, no_prior, _meta_sequence, _no_prior_sequence, _single = (
        _development_result()
    )
    assert meta["document"]["ground_support_labels"] == 14
    assert no_prior["document"]["ground_support_labels"] == 29
    assert meta["document"]["target_predictive_confirmation_count"] == 0
    assert no_prior["document"]["target_predictive_confirmation_count"] == 8
    assert meta["document"][
        "same_constructor_projection_replay_and_stopping_rule_in_prior_on_off_arms"
    ] is True
    assert meta["document"]["proposal_used_as_safety_authority"] is False


def test_v77_single_query_preserves_measured_sample_tax_failure():
    _meta, _no_prior, _meta_sequence, _no_prior_sequence, single = (
        _development_result()
    )
    assert single["transfer_total_target_ground_support_labels"] == 71
    assert single["strict_total_target_ground_support_labels"] == 65
    assert single["total_target_sample_reduction_observed"] is False
    assert single["query_local_exact_overlay_exclusively_used_for_safety"] is True


def test_v78_persistent_overlay_amortizes_tax_without_repeated_ground_queries():
    _meta, _no_prior, meta_sequence, no_prior_sequence, _single = (
        _development_result()
    )
    assert meta_sequence[
        "transfer_lifetime_unique_target_ground_support_labels"
    ] == 71
    assert no_prior_sequence[
        "transfer_lifetime_unique_target_ground_support_labels"
    ] == 76
    assert meta_sequence[
        "strict_cold_direct_lifetime_target_ground_support_labels"
    ] == 130
    assert [
        row["new_certificate_labels_charged_this_episode"]
        for row in meta_sequence["transfer_episodes"]
    ] == [57, 0]
    assert meta_sequence["lifetime_target_sample_reduction_observed"] is True
    assert meta_sequence[
        "acquisition_and_certificate_rows_immutable_and_reused_across_queries"
    ] is True
    assert meta_sequence["no_ground_query_repeated_across_transfer_episodes"] is True
    assert meta_sequence["official_execution_allowed"] is False
    assert meta_sequence["official_scalar_cost"] is None
    assert meta_sequence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
