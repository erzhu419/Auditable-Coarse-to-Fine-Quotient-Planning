"""Cross-occurrence reuse of source-built abstract successor models.

Each family-level source model is built once from a frozen V73 source identity.
Fresh target seeds acquire only their common partial candidate, then run matched
V43 arms with and without the source model.  Compatibility is checked before
abstract search; every ground query still follows an explicit certificate
failure and only the target-local exact overlay carries safety authority.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    compile_joint_successor_version_space_model_v42,
    plan_joint_successor_version_space_v42,
)
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    GenericReusableVersionSpaceCertificatePlannerV43Error,
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class CrossOccurrenceReusableModelCampaignCoreV75Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CrossOccurrenceReusableModelCampaignCoreV75Error(message)


def _build_source(args: tuple[Any, ...]) -> dict[str, Any]:
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
    status = "SOURCE_ACQUISITION_ABSTAINED_NONCERTIFICATE"
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
            status = "SOURCE_MODEL_FROZEN_FOR_CROSS_OCCURRENCE_TRANSFER"
    payload = {
        "schema": "acfqp.cross_occurrence_reuse_source.v75",
        "family": family,
        "source_seed": seed,
        "source_episode_index": config["source_episode_index"],
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
        "target_outcomes_used_to_select_or_refit_source_model": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "source_id": domains.extension_content_id_v75(
            domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_SOURCE_V75_DOMAIN,
            payload,
        ),
    }


def _target_arm(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    model: Mapping[str, Any] | None,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return run_reusable_version_space_certificate_episode_v43(
            adapter,
            candidate,
            rows,
            reusable_model=model,
            model_source_episode_index=config["source_episode_index"],
            episode_index=config["target_episode_index"],
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
            "official_execution_allowed": False,
        }


def _ood_control(
    model: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    adapter: Any,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    foreign_document = copy.deepcopy(candidate.public_document)
    foreign_document["state_width"] += 1
    foreign_document["unknown_residual_target_columns"] = sorted(
        [
            *foreign_document["unknown_residual_target_columns"],
            foreign_document["state_width"] - 1,
        ]
    )
    foreign_document["layout"]["state_canonical_to_raw"].append(
        foreign_document["state_width"] - 1
    )
    foreign_document["layout"]["state_structural_colors"].append(
        "V75_STRICT_INCOMPATIBLE_EXTRA_COORDINATE"
    )
    foreign = PartialFactorCandidateV15(
        foreign_document,
        candidate.layout,
        candidate.assignments,
        candidate.issuance_rows,
    )
    try:
        plan_joint_successor_version_space_v42(
            model,
            foreign,
            adapter.catalogue,
            (*adapter.encode(adapter.initial()), 0),
            maximum_depth=config["maximum_abstract_depth"],
            maximum_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
            ],
        )
    except GenericJointSuccessorVersionSpacePlannerV42Error as error:
        return {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH",
            "reason": str(error),
            "ground_transition_accessed": False,
        }
    _fail("V75 incompatible schema received a reusable-model plan")


def _run_target(args: tuple[Any, ...]) -> dict[str, Any]:
    source, target_seed, factor_library, config = args
    family = source["family"]
    model = source["reusable_joint_successor_version_space_model"]
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, target_seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    arms = {
        "CROSS_OCCURRENCE_REUSABLE_MODEL": _target_arm(
            adapter, partial["candidate"], partial["rows"], model, config
        ),
        "STRICT_NO_REUSABLE_MODEL": _target_arm(
            adapter, partial["candidate"], partial["rows"], None, config
        ),
    }
    ood = _ood_control(model, partial["candidate"], adapter, config)
    payload = {
        "schema": "acfqp.cross_occurrence_reuse_target.v75",
        "family": family,
        "source_id": source["source_id"],
        "source_seed": source["source_seed"],
        "target_seed": target_seed,
        "source_episode_index": config["source_episode_index"],
        "target_episode_index": config["target_episode_index"],
        "source_and_target_occurrence_identities_disjoint": (
            source["source_seed"] != target_seed
        ),
        "target_common_partial_acquisition_id": partial["document"][
            "acquisition_id"
        ],
        "target_common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_arms": arms,
        "incompatible_schema_ood_control": ood,
        "source_model_frozen_before_target_occurrence": True,
        "target_outcomes_used_to_refit_source_model": False,
        "same_target_adapter_kernel_seed_episode_in_both_arms": True,
        "same_exact_query_local_certificate_engine_in_both_arms": True,
        "only_source_model_availability_differs_between_target_arms": True,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "target_id": domains.extension_content_id_v75(
            domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_TARGET_V75_DOMAIN,
            payload,
        ),
    }


def build_cross_occurrence_reuse_campaign_document_v75(
    config: Mapping[str, Any],
    preregistration_id: str,
    v74_campaign_id: str,
    v74_verification_id: str,
    template_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    source_args = [
        (
            family,
            seed,
            factor_library,
            residual_library,
            template_library,
            config,
        )
        for family, seed in config["source_seed_by_family"].items()
    ]
    with ProcessPoolExecutor(max_workers=config["source_worker_count"]) as executor:
        sources = list(executor.map(_build_source, source_args))
    if len(sources) != len(config["source_seed_by_family"]):
        _fail("V75 source inventory changed")
    source_by_family = {row["family"]: row for row in sources}
    if set(source_by_family) != set(config["source_seed_by_family"]):
        _fail("V75 source-family inventory changed")
    compiled = [
        row
        for row in sources
        if row["reusable_joint_successor_version_space_model"] is not None
    ]
    source_failed = sum(
        row["source_relation_covering_acquisition"]["learned_successor_acquisition"][
            "status"
        ]
        == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        for row in sources
    )
    target_args = [
        (source_by_family[family], seed, factor_library, config)
        for family, seeds in config["fresh_target_seeds"].items()
        for seed in seeds
        if source_by_family[family]["reusable_joint_successor_version_space_model"]
        is not None
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        targets = list(executor.map(_run_target, target_args))
    expected_targets = sum(
        len(config["fresh_target_seeds"][source["family"]])
        for source in compiled
    )
    if len(targets) != expected_targets:
        _fail("V75 target inventory changed")
    target_failures = sum(
        arm.get("success") is not True
        for row in targets
        for arm in row["target_arms"].values()
    )
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_abstract_model_used_as_safety_authority"] is False
        for row in targets
        for arm in row["target_arms"].values()
        if arm.get("success") is True
    )
    derived_labels = sum(
        row["target_arms"]["CROSS_OCCURRENCE_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in targets
        if all(arm.get("success") is True for arm in row["target_arms"].values())
    )
    strict_labels = sum(
        row["target_arms"]["STRICT_NO_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in targets
        if all(arm.get("success") is True for arm in row["target_arms"].values())
    )
    reduced_count = sum(
        row["target_arms"]["CROSS_OCCURRENCE_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        < row["target_arms"]["STRICT_NO_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in targets
        if all(arm.get("success") is True for arm in row["target_arms"].values())
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH"
        for row in targets
    )
    gate_passed = (
        source_failed == 0
        and len(compiled) == config["required_compiled_source_count"]
        and len(targets) == config["fresh_target_occurrence_count"]
        and target_failures == 0
        and certificate_clean
        and ood_rejections == len(targets)
        and derived_labels < strict_labels
        and reduced_count >= config["minimum_reduced_target_occurrence_count"]
    )
    source_episodes = [
        row["source_complete_episode"]["predecessor_v30_episode"]
        for row in sources
    ]
    payload = {
        "schema": "acfqp.cross_occurrence_reuse_campaign.v75",
        "preregistration_id": preregistration_id,
        "v74_campaign_id": v74_campaign_id,
        "v74_verification_id": v74_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "sources": sources,
        "targets": targets,
        "sample_tax_comparison": {
            "fresh_cross_occurrence_target_count": len(targets),
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_minus_strict_target_labels": derived_labels - strict_labels,
            "reduced_target_occurrence_count": reduced_count,
            "cross_occurrence_actual_target_sample_reduction_observed": (
                bool(targets) and derived_labels < strict_labels
            ),
            "v74_incremental_amortization_identity_retained": True,
            "new_cross_occurrence_economics_claimed": False,
        },
        "accounting": {
            "offline_template_source_labels": offline_template_source_labels,
            "offline_residual_library_labels": config["offline_library_labels"],
            "source_common_partial_labels": sum(
                row["common_partial_ground_support_labels"] for row in sources
            ),
            "source_certificate_local_labels": sum(
                row["local_ground_support_labels"] for row in source_episodes
            ),
            "source_execution_steps": sum(
                row["execution_steps"] for row in source_episodes
            ),
            "source_relational_planning_compute_events": sum(
                row["relational_abstract_support_branch_evaluations"]
                for row in source_episodes
            ),
            "target_common_partial_labels": sum(
                row["target_common_partial_ground_support_labels"] for row in targets
            ),
            "target_derived_certificate_local_labels": derived_labels,
            "target_strict_certificate_local_labels": strict_labels,
            "target_derived_execution_steps": sum(
                row["target_arms"]["CROSS_OCCURRENCE_REUSABLE_MODEL"][
                    "execution_steps"
                ]
                for row in targets
            ),
            "target_strict_execution_steps": sum(
                row["target_arms"]["STRICT_NO_REUSABLE_MODEL"]["execution_steps"]
                for row in targets
            ),
            "target_derived_abstract_planning_compute_events": sum(
                row["target_arms"]["CROSS_OCCURRENCE_REUSABLE_MODEL"][
                    "abstract_planning_compute_events"
                ]
                for row in targets
            ),
            "target_strict_abstract_planning_compute_events": 0,
            "all_axes_separate": True,
        },
        "registered_gate": {
            "source_heldout_failed_noncertificate_count": source_failed,
            "compiled_source_count": len(compiled),
            "required_compiled_source_count": config[
                "required_compiled_source_count"
            ],
            "fresh_target_occurrence_count": len(targets),
            "required_fresh_target_occurrence_count": config[
                "fresh_target_occurrence_count"
            ],
            "target_arm_failure_count": target_failures,
            "certificate_discipline_clean": certificate_clean,
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_incompatible_schema_ood_rejection_count": len(targets),
            "aggregate_cross_occurrence_target_reduction_required": True,
            "aggregate_cross_occurrence_target_reduction_observed": (
                bool(targets) and derived_labels < strict_labels
            ),
            "minimum_reduced_target_occurrence_count": config[
                "minimum_reduced_target_occurrence_count"
            ],
            "actual_reduced_target_occurrence_count": reduced_count,
            "passed": gate_passed,
        },
        "source_models_frozen_before_fresh_target_occurrences": True,
        "source_and_target_seed_identities_disjoint": all(
            row["source_and_target_occurrence_identities_disjoint"] is True
            for row in targets
        ),
        "target_outcomes_used_to_refit_source_models": False,
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
        "campaign_id": domains.extension_content_id_v75(
            domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_CAMPAIGN_V75_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "CrossOccurrenceReusableModelCampaignCoreV75Error",
    "build_cross_occurrence_reuse_campaign_document_v75",
)
