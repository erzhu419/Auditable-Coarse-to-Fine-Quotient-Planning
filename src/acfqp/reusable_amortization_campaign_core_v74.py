"""Multi-episode amortization of a frozen reusable successor model.

V74 deterministically reconstructs the frozen V73 source construction on the
same registered occurrence identities, then freezes that model across a
preregistered sequence of new episode identities.  Each episode starts with an
empty exact overlay and runs the same V43 matched target arms.  The campaign
computes the first episode prefix whose accumulated target-label savings repays
only the *incremental certificate-local source-model labels*.  Shared partial
acquisition, offline libraries, compute, and official economics remain separate
and are not hidden inside this break-even number.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v74 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    compile_joint_successor_version_space_model_v42,
)
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    GenericReusableVersionSpaceCertificatePlannerV43Error,
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class ReusableAmortizationCampaignCoreV74Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ReusableAmortizationCampaignCoreV74Error(message)


def _target(
    adapter: Any,
    candidate: Any,
    rows: tuple[Any, ...],
    model: Mapping[str, Any] | None,
    episode_index: int,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return run_reusable_version_space_certificate_episode_v43(
            adapter,
            candidate,
            rows,
            reusable_model=model,
            model_source_episode_index=config["source_episode_index"],
            episode_index=episode_index,
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            maximum_target_ground_support_labels=config[
                "maximum_target_ground_support_labels"
            ],
            maximum_abstract_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            abstract_support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
            ],
        )
    except GenericReusableVersionSpaceCertificatePlannerV43Error as error:
        return {
            "schema": "acfqp.generic_reusable_version_space_certificate_failure.v43",
            "status": "TARGET_CERTIFICATE_EPISODE_FAILED_NONCERTIFICATE",
            "reason": str(error),
            "reusable_model_present": model is not None,
            "episode_index": episode_index,
            "official_execution_allowed": False,
        }


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, template_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    envelope = run_source_complete_relational_world_model_episode_v31(
        adapter,
        partial["candidate"],
        partial["rows"],
        residual_prior_library=residual_library,
        episode_index=config["source_episode_index"],
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_terminal_program_candidates_to_try=config[
            "maximum_terminal_program_candidates_to_try"
        ],
        maximum_relational_support_branch_evaluations=config[
            "maximum_relational_support_branch_evaluations"
        ],
        relational_support_feasible_beam_width=config[
            "relational_support_feasible_beam_width"
        ],
    )
    retained = envelope["terminal_program_source_evidence"]
    source = {
        "layout": retained["layout"],
        "unknown_residual_target_columns": retained[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": retained["raw_transition_rows"],
    }
    acquisition = run_relation_covering_learned_successor_acquisition_v41(
        source,
        role_free_template_library=template_library,
        successor_prior_library=residual_library,
        maximum_exact_instantiations=config[
            "maximum_terminal_program_candidates_to_try"
        ],
        confidence_denominator=config["prequential_confidence_denominator"],
        successor_confidence_denominator=config[
            "successor_confidence_denominator"
        ],
        maximum_successor_support_states=config[
            "maximum_successor_support_states"
        ],
    )
    learned = acquisition["learned_successor_acquisition"]
    model = None
    status = "SOURCE_ACQUISITION_ABSTAINED_NO_TARGET_EXECUTION"
    reason = None
    if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        try:
            model = compile_joint_successor_version_space_model_v42(
                partial["candidate"], source, acquisition
            )
        except GenericJointSuccessorVersionSpacePlannerV42Error as error:
            status = "SOURCE_MODEL_COMPILATION_ABSTAINED_NONCERTIFICATE"
            reason = str(error)
        else:
            status = "REUSABLE_MODEL_FROZEN_FOR_MULTI_EPISODE_TARGETS"
    targets = []
    if model is not None:
        for episode_index in config["amortization_target_episode_indices"]:
            targets.append(
                {
                    "target_episode_index": episode_index,
                    "arms": {
                        "REUSABLE_JOINT_VERSION_SPACE_MODEL": _target(
                            adapter,
                            partial["candidate"],
                            partial["rows"],
                            model,
                            episode_index,
                            config,
                        ),
                        "STRICT_NO_REUSABLE_MODEL": _target(
                            adapter,
                            partial["candidate"],
                            partial["rows"],
                            None,
                            episode_index,
                            config,
                        ),
                    },
                }
            )
    payload = {
        "schema": "acfqp.reusable_amortization_occurrence.v74",
        "family": family,
        "seed": seed,
        "source_episode_index": config["source_episode_index"],
        "target_episode_indices": list(config["amortization_target_episode_indices"]),
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "source_complete_episode": envelope,
        "retained_source_evidence": source,
        "source_relation_covering_acquisition": acquisition,
        "source_model_status": status,
        "source_model_compilation_reason": reason,
        "reusable_joint_successor_version_space_model": model,
        "target_episode_ablations": targets,
        "source_model_frozen_once_before_all_target_episodes": model is not None,
        "fresh_exact_overlay_for_every_arm_episode": model is not None,
        "target_outcomes_used_to_refit_reusable_model": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v74(
            domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_OCCURRENCE_V74_DOMAIN,
            payload,
        ),
    }


def build_reusable_amortization_campaign_document_v74(
    config: Mapping[str, Any],
    preregistration_id: str,
    v73_campaign_id: str,
    v73_verification_id: str,
    template_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    arguments = [
        (family, seed, factor_library, residual_library, template_library, config)
        for family, seeds in config["target_seeds"].items()
        for seed in seeds
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    if len(occurrences) != config["target_occurrence_count"]:
        _fail("V74 occurrence inventory changed")
    compiled = [
        row for row in occurrences
        if row["reusable_joint_successor_version_space_model"] is not None
    ]
    source_failed = sum(
        row["source_relation_covering_acquisition"]["learned_successor_acquisition"][
            "status"
        ]
        == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        for row in occurrences
    )
    target_failures = sum(
        arm.get("success") is not True
        for row in compiled
        for episode in row["target_episode_ablations"]
        for arm in episode["arms"].values()
    )
    expected_target_count = len(compiled) * len(
        config["amortization_target_episode_indices"]
    )
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_abstract_model_used_as_safety_authority"] is False
        for row in compiled
        for episode in row["target_episode_ablations"]
        for arm in episode["arms"].values()
        if arm.get("success") is True
    )
    source_investment = sum(
        row["source_complete_episode"]["predecessor_v30_episode"][
            "local_ground_support_labels"
        ]
        for row in compiled
    )
    episode_rows = []
    cumulative = 0
    break_even = None
    for ordinal, episode_index in enumerate(
        config["amortization_target_episode_indices"], 1
    ):
        matching = [
            episode
            for row in compiled
            for episode in row["target_episode_ablations"]
            if episode["target_episode_index"] == episode_index
        ]
        derived = sum(
            episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "target_certificate_local_ground_support_labels"
            ]
            for episode in matching
            if episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"].get("success")
            is True
        )
        strict = sum(
            episode["arms"]["STRICT_NO_REUSABLE_MODEL"][
                "target_certificate_local_ground_support_labels"
            ]
            for episode in matching
            if episode["arms"]["STRICT_NO_REUSABLE_MODEL"].get("success") is True
        )
        savings = strict - derived
        cumulative += savings
        if break_even is None and cumulative >= source_investment:
            break_even = ordinal
        episode_rows.append(
            {
                "episode_ordinal": ordinal,
                "target_episode_index": episode_index,
                "matched_compiled_occurrence_count": len(matching),
                "derived_target_labels": derived,
                "strict_target_labels": strict,
                "episode_label_savings": savings,
                "cumulative_target_label_savings": cumulative,
                "incremental_source_model_label_investment": source_investment,
                "incremental_source_investment_repaid": cumulative
                >= source_investment,
            }
        )
    positive_each = bool(episode_rows) and all(
        row["episode_label_savings"] > 0 for row in episode_rows
    )
    gate_passed = (
        source_failed == 0
        and len(compiled) >= config["minimum_compiled_occurrence_count"]
        and target_failures == 0
        and sum(len(row["target_episode_ablations"]) for row in compiled)
        == expected_target_count
        and certificate_clean
        and positive_each
        and break_even is not None
    )
    source_episodes = [
        row["source_complete_episode"]["predecessor_v30_episode"]
        for row in occurrences
    ]
    payload = {
        "schema": "acfqp.reusable_amortization_campaign.v74",
        "preregistration_id": preregistration_id,
        "v73_campaign_id": v73_campaign_id,
        "v73_verification_id": v73_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "occurrences": occurrences,
        "incremental_sample_amortization": {
            "incremental_source_model_label_investment": source_investment,
            "target_episode_rows": episode_rows,
            "target_episode_count": len(episode_rows),
            "every_target_episode_has_positive_aggregate_savings": positive_each,
            "empirical_incremental_break_even_episode_ordinal": break_even,
            "incremental_break_even_observed_within_registered_horizon": (
                break_even is not None
            ),
            "shared_partial_acquisition_cost_excluded_as_common_to_both_arms": True,
            "offline_prior_library_cost_excluded": True,
            "planning_compute_excluded_from_sample_break_even": True,
            "official_N_break_even_claimed": False,
            "economics_claimed": False,
        },
        "accounting": {
            "offline_template_source_labels": offline_template_source_labels,
            "offline_residual_library_labels": config["offline_library_labels"],
            "source_common_partial_labels": sum(
                row["common_partial_ground_support_labels"] for row in occurrences
            ),
            "source_certificate_local_labels_all_occurrences": sum(
                row["local_ground_support_labels"] for row in source_episodes
            ),
            "incremental_source_model_labels_compiled_occurrences": source_investment,
            "source_execution_steps": sum(
                row["execution_steps"] for row in source_episodes
            ),
            "source_relational_planning_compute_events": sum(
                row["relational_abstract_support_branch_evaluations"]
                for row in source_episodes
            ),
            "target_derived_certificate_local_labels": sum(
                row["derived_target_labels"] for row in episode_rows
            ),
            "target_strict_certificate_local_labels": sum(
                row["strict_target_labels"] for row in episode_rows
            ),
            "target_derived_execution_steps": sum(
                episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                    "execution_steps"
                ]
                for row in compiled
                for episode in row["target_episode_ablations"]
            ),
            "target_strict_execution_steps": sum(
                episode["arms"]["STRICT_NO_REUSABLE_MODEL"]["execution_steps"]
                for row in compiled
                for episode in row["target_episode_ablations"]
            ),
            "target_derived_abstract_planning_compute_events": sum(
                episode["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                    "abstract_planning_compute_events"
                ]
                for row in compiled
                for episode in row["target_episode_ablations"]
            ),
            "target_strict_abstract_planning_compute_events": 0,
            "all_axes_separate": True,
        },
        "registered_gate": {
            "source_heldout_failed_noncertificate_count": source_failed,
            "compiled_occurrence_count": len(compiled),
            "required_minimum_compiled_occurrence_count": config[
                "minimum_compiled_occurrence_count"
            ],
            "expected_matched_target_episode_count": expected_target_count,
            "actual_matched_target_episode_count": sum(
                len(row["target_episode_ablations"]) for row in compiled
            ),
            "target_arm_failure_count": target_failures,
            "certificate_discipline_clean": certificate_clean,
            "positive_aggregate_savings_required_in_every_target_episode": True,
            "positive_aggregate_savings_observed_in_every_target_episode": positive_each,
            "incremental_break_even_required_within_registered_horizon": True,
            "incremental_break_even_observed_within_registered_horizon": (
                break_even is not None
            ),
            "passed": gate_passed,
        },
        "source_model_frozen_once_before_all_target_episodes": True,
        "fresh_exact_overlay_for_every_arm_episode": True,
        "all_ground_queries_followed_failed_certificates": certificate_clean,
        "query_local_exact_overlay_exclusively_used_for_safety": certificate_clean,
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
        "campaign_id": domains.extension_content_id_v74(
            domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_CAMPAIGN_V74_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "ReusableAmortizationCampaignCoreV74Error",
    "build_reusable_amortization_campaign_document_v74",
)
