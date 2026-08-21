"""Fresh second-domain replication of persistent sample-tax reduction."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v95 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_action_key_permutation_adapter_v62 import (
    permute_adapter_action_keys_v62,
)
from acfqp.generic_projected_low_label_applicability_v76 import (
    acquire_projected_low_label_applicability_v76,
)
from acfqp.generic_projected_persistent_sequence_v78 import (
    run_projected_persistent_sequence_v78,
)


class PersistentSecondDomainCampaignCoreV95Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise PersistentSecondDomainCampaignCoreV95Error(message)


def _acquire(
    adapter: Any,
    model: Mapping[str, Any],
    applicability: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    odds: int,
    domain: str,
) -> dict[str, Any]:
    return acquire_projected_low_label_applicability_v76(
        adapter,
        model,
        applicability,
        maximum_ground_support_labels=config[
            "maximum_applicability_ground_support_labels"
        ],
        confidence_denominator=config["confidence_denominator"],
        source_meta_prior_odds=odds,
        minimum_factor_assignment_count=config[
            "minimum_reusable_factor_count"
        ],
        layout_domain=config["generic_domains"]["layout"],
        acquisition_domain=domain,
        content_id=domains.extension_content_id_v95,
    )


def _sequence(
    adapter: Any,
    acquisition: Mapping[str, Any],
    model: Mapping[str, Any],
    applicability: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    return run_projected_persistent_sequence_v78(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        model,
        applicability,
        model_source_episode_index=config["source_episode_index"],
        episode_indices=tuple(config["target_episode_indices"]),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=config[
            "maximum_incremental_certificate_ground_support_labels"
        ],
        maximum_abstract_support_branch_evaluations=config[
            "maximum_relational_support_branch_evaluations"
        ],
        abstract_support_feasible_beam_width=config[
            "relational_support_feasible_beam_width"
        ],
    )


def _strict_projection(sequence: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in episode.items()
            if key not in {"episode_id", "target_candidate_id"}
        }
        for episode in sequence["strict_cold_direct_episodes"]
    ]


def _ood(
    adapter: Any,
    model: Mapping[str, Any],
    applicability: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    forged = copy.deepcopy(dict(model))
    forged["state_width"] += 1
    try:
        _acquire(
            adapter,
            forged,
            applicability,
            config,
            odds=config["source_meta_prior_odds"],
            domain=(
                domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_META_ACQUISITION_V95_DOMAIN
            ),
        )
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        return {
            "status": "INCOMPATIBLE_MODEL_REJECTED_BEFORE_TARGET_OBSERVATION",
            "reason": str(error),
            "target_ground_support_labels_consumed": 0,
            "target_episode_executed": False,
        }
    _fail("V95 incompatible model received target observations")


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    seed, model, applicability, config = args
    original = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    adapter, permutation = permute_adapter_action_keys_v62(original)
    meta = None
    no_prior = None
    meta_sequence = None
    no_prior_sequence = None
    ood = None
    reason = None
    status = "TARGET_FAILED_BEFORE_MATCHED_ACQUISITIONS_NONCERTIFICATE"
    try:
        meta = _acquire(
            adapter,
            model,
            applicability,
            config,
            odds=config["source_meta_prior_odds"],
            domain=(
                domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_META_ACQUISITION_V95_DOMAIN
            ),
        )
        no_prior = _acquire(
            adapter,
            model,
            applicability,
            config,
            odds=1,
            domain=(
                domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_NO_PRIOR_ACQUISITION_V95_DOMAIN
            ),
        )
        meta_sequence = _sequence(adapter, meta, model, applicability, config)
        no_prior_sequence = _sequence(
            adapter, no_prior, model, applicability, config
        )
        if _strict_projection(meta_sequence) != _strict_projection(
            no_prior_sequence
        ):
            _fail("V95 repeated strict cold-direct sequence changed")
        ood = _ood(adapter, model, applicability, config)
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        reason = str(error)
        status = "TARGET_ACQUISITION_OR_SEQUENCE_FAILED_NONCERTIFICATE"
    else:
        status = "TARGET_PERSISTENT_META_NO_PRIOR_AND_DIRECT_SEQUENCES_COMPLETED"
    payload = {
        "schema": "acfqp.persistent_second_domain_occurrence.v95",
        "family": config["target_family"],
        "target_seed": seed,
        "target_episode_indices": list(config["target_episode_indices"]),
        "source_model_id": model[
            "projected_disagreement_successor_model_id"
        ],
        "source_applicability_program_id": applicability[
            "action_applicability_program_id"
        ],
        "outcome_blind_action_key_permutation": permutation,
        "meta_prior_acquisition": None if meta is None else meta["document"],
        "no_prior_acquisition": None
        if no_prior is None
        else no_prior["document"],
        "meta_prior_persistent_sequence": meta_sequence,
        "no_prior_persistent_sequence": no_prior_sequence,
        "strict_incompatible_model_ood_control": ood,
        "status": status,
        "failure_reason": reason,
        "same_constructor_projection_stop_rule_query_identities_and_exact_engine": (
            meta is not None and no_prior is not None
        ),
        "only_source_meta_prior_odds_differs_between_acquisition_arms": True,
        "persistent_exact_overlay_shared_only_within_each_arm_not_across_arms": True,
        "source_prior_model_alignment_and_applicability_used_as_safety_authority": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v95(
            domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_OCCURRENCE_V95_DOMAIN,
            payload,
        ),
    }


def build_persistent_second_domain_campaign_document_v95(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v94_campaign_id: str,
    v94_verification_id: str,
    projected_model_artifact_id: str,
    applicability_model_artifact_id: str,
    model: Mapping[str, Any],
    applicability: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [
        (seed, model, applicability, config) for seed in config["target_seeds"]
    ]
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in arguments]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            occurrences = list(executor.map(_target, arguments))
    completed = [
        row
        for row in occurrences
        if row["status"]
        == "TARGET_PERSISTENT_META_NO_PRIOR_AND_DIRECT_SEQUENCES_COMPLETED"
    ]
    meta_acquisitions = [row["meta_prior_acquisition"] for row in completed]
    no_prior_acquisitions = [row["no_prior_acquisition"] for row in completed]
    meta_sequences = [row["meta_prior_persistent_sequence"] for row in completed]
    no_prior_sequences = [row["no_prior_persistent_sequence"] for row in completed]
    strict_totals = [
        row["strict_cold_direct_lifetime_target_ground_support_labels"]
        for row in meta_sequences
    ]
    meta_totals = [
        row["transfer_lifetime_unique_target_ground_support_labels"]
        for row in meta_sequences
    ]
    no_prior_totals = [
        row["transfer_lifetime_unique_target_ground_support_labels"]
        for row in no_prior_sequences
    ]
    acquisition_clean = bool(completed) and all(
        meta["source_meta_prior_odds"] == config["source_meta_prior_odds"]
        and meta["source_meta_prior_enabled"] is True
        and no_prior["source_meta_prior_odds"] == 1
        and no_prior["source_meta_prior_enabled"] is False
        and meta[
            "same_constructor_projection_replay_and_stopping_rule_in_prior_on_off_arms"
        ]
        is True
        and no_prior[
            "same_constructor_projection_replay_and_stopping_rule_in_prior_on_off_arms"
        ]
        is True
        and meta["fixed_label_floor_used"] is False
        and no_prior["fixed_label_floor_used"] is False
        for meta, no_prior in zip(
            meta_acquisitions, no_prior_acquisitions, strict=True
        )
    )
    persistent_clean = bool(meta_sequences) and all(
        row[
            "acquisition_and_certificate_rows_immutable_and_reused_across_queries"
        ]
        is True
        and row["every_new_ground_query_followed_a_failed_certificate"] is True
        and row["no_ground_query_repeated_across_transfer_episodes"] is True
        and row["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and row["transfer_episodes"][1][
            "new_certificate_labels_charged_this_episode"
        ]
        == 0
        for row in (*meta_sequences, *no_prior_sequences)
    )
    abstract_primary = bool(meta_sequences) and all(
        all(
            episode["execution_steps"] >= 2
            and episode["abstract_plan_success_count"] > 0
            and episode["execution_action_matches_abstract_proposal_count"] >= 2
            and 2 * episode["execution_action_matches_abstract_proposal_count"]
            >= episode["execution_steps"]
            for episode in row["transfer_episodes"]
        )
        for row in meta_sequences
    )
    meta_fewer_acquisition = bool(completed) and all(
        meta["ground_support_labels"] < no_prior["ground_support_labels"]
        for meta, no_prior in zip(
            meta_acquisitions, no_prior_acquisitions, strict=True
        )
    )
    no_regressions = bool(meta_totals) and all(
        meta <= no_prior and meta <= strict
        for meta, no_prior, strict in zip(
            meta_totals, no_prior_totals, strict_totals, strict=True
        )
    )
    aggregate_reduction = (
        no_regressions
        and sum(meta_totals) < sum(no_prior_totals)
        and sum(meta_totals) < sum(strict_totals)
    )
    ood_clean = bool(completed) and all(
        row["strict_incompatible_model_ood_control"]["status"]
        == "INCOMPATIBLE_MODEL_REJECTED_BEFORE_TARGET_OBSERVATION"
        and row["strict_incompatible_model_ood_control"][
            "target_ground_support_labels_consumed"
        ]
        == 0
        for row in completed
    )
    passed = (
        len(completed) == config["required_target_occurrence_count"]
        and acquisition_clean
        and persistent_clean
        and abstract_primary
        and meta_fewer_acquisition
        and no_regressions
        and aggregate_reduction
        and ood_clean
    )
    accounting = {
        "meta_prior_target_acquisition_labels": sum(
            row["ground_support_labels"] for row in meta_acquisitions
        ),
        "no_prior_target_acquisition_labels": sum(
            row["ground_support_labels"] for row in no_prior_acquisitions
        ),
        "meta_prior_persistent_certificate_labels": sum(
            row["persistent_certificate_ground_support_labels_paid_once"]
            for row in meta_sequences
        ),
        "no_prior_persistent_certificate_labels": sum(
            row["persistent_certificate_ground_support_labels_paid_once"]
            for row in no_prior_sequences
        ),
        "meta_prior_lifetime_unique_target_labels": sum(meta_totals),
        "no_prior_lifetime_unique_target_labels": sum(no_prior_totals),
        "strict_cold_direct_lifetime_target_labels": sum(strict_totals),
        "strict_minus_meta_prior_lifetime_target_labels": (
            sum(strict_totals) - sum(meta_totals)
        ),
        "no_prior_minus_meta_prior_lifetime_target_labels": (
            sum(no_prior_totals) - sum(meta_totals)
        ),
        "meta_prior_execution_steps": sum(
            episode["execution_steps"]
            for sequence in meta_sequences
            for episode in sequence["transfer_episodes"]
        ),
        "no_prior_execution_steps": sum(
            episode["execution_steps"]
            for sequence in no_prior_sequences
            for episode in sequence["transfer_episodes"]
        ),
        "strict_execution_steps": sum(
            episode["execution_steps"]
            for sequence in meta_sequences
            for episode in sequence["strict_cold_direct_episodes"]
        ),
        "meta_prior_projection_derivation_compute_events": sum(
            row["projection_derivation_compute_events"]
            for row in meta_acquisitions
        ),
        "no_prior_projection_derivation_compute_events": sum(
            row["projection_derivation_compute_events"]
            for row in no_prior_acquisitions
        ),
        "meta_prior_abstract_planning_compute_events": sum(
            episode["abstract_planning_compute_events"]
            for sequence in meta_sequences
            for episode in sequence["transfer_episodes"]
        ),
        "no_prior_abstract_planning_compute_events": sum(
            episode["abstract_planning_compute_events"]
            for sequence in no_prior_sequences
            for episode in sequence["transfer_episodes"]
        ),
        "strict_abstract_planning_compute_events": 0,
        "source_target_labels_execution_derivation_certificate_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.persistent_second_domain_campaign.v95",
        "preregistration_id": preregistration_id,
        "v94_campaign_id": v94_campaign_id,
        "v94_verification_id": v94_verification_id,
        "projected_model_artifact_id": projected_model_artifact_id,
        "applicability_model_artifact_id": applicability_model_artifact_id,
        "source_model_id": model[
            "projected_disagreement_successor_model_id"
        ],
        "source_applicability_program_id": applicability[
            "action_applicability_program_id"
        ],
        "target_occurrences": occurrences,
        "accounting": accounting,
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "completed_target_occurrence_count": len(completed),
            "matched_same_constructor_prior_on_off_acquisition_clean": (
                acquisition_clean
            ),
            "persistent_exact_overlay_reuse_clean": persistent_clean,
            "multi_step_abstract_proposal_primary_on_every_target_query": (
                abstract_primary
            ),
            "meta_prior_acquisition_labels_strictly_lower_on_every_target": (
                meta_fewer_acquisition
            ),
            "meta_prior_lifetime_labels_noninferior_to_no_prior_and_direct_on_every_target": (
                no_regressions
            ),
            "meta_prior_lifetime_labels_strictly_better_than_no_prior_and_direct_in_aggregate": (
                aggregate_reduction
            ),
            "strict_incompatible_model_no_transfer_clean": ood_clean,
            "passed": passed,
        },
        "fresh_target_identities_executed_without_selection": True,
        "v94_identity_preserved": True,
        "sample_tax_reduction_replicated_in_second_registered_domain": passed,
        "sample_tax_reduction_generalized_beyond_two_registered_domain_families": False,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v95(
            domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_CAMPAIGN_V95_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_persistent_second_domain_campaign_document_v95",)
