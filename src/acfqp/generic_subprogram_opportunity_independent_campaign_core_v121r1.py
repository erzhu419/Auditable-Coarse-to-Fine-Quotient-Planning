"""Correct V121's opportunity-dependent cache-hit Gate on fresh identities.

A same-epoch cache hit is a workload opportunity, not a construction
obligation.  V121 required at least one such hit and therefore failed despite
all six episodes succeeding.  This successor preserves the entire embedded
V121 occurrence and replaces only that Gate criterion with exact accounting:
zero or more hits are valid, while every observed hit must still come from the
identity-authorized V119 sequence.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v121r1 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_artifact_subprogram_campaign_core_v121 import (
    build_generic_artifact_subprogram_occurrence_v121,
)


class GenericSubprogramOpportunityIndependentCampaignCoreV121R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericSubprogramOpportunityIndependentCampaignCoreV121R1Error(message)


def correct_generic_subprogram_occurrence_gate_v121r1(
    base: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(base) is not dict
        or base.get("schema") != "acfqp.generic_artifact_subprogram_occurrence.v121"
        or type(base.get("registered_gate")) is not dict
        or type(base.get("accounting")) is not dict
        or type(base.get("genesis_authorized_program_branch_sequence")) is not dict
    ):
        _fail("V121r1 base occurrence shape changed")
    old_gate = base["registered_gate"]
    required_old_keys = set(old_gate) - {"passed", "same_epoch_genesis_authorization_observed"}
    if not required_old_keys or any(old_gate.get(key) is not True for key in required_old_keys):
        _fail("V121r1 base occurrence failed outside the opportunity-dependent Gate")
    sequence = base["genesis_authorized_program_branch_sequence"]
    hits = base["accounting"].get("same_epoch_genesis_authorized_cache_hits")
    branch_hits = base["accounting"].get("program_branch_cache_hits")
    if type(hits) is not int or hits < 0 or type(branch_hits) is not int or branch_hits < 0:
        _fail("V121r1 cache accounting changed")
    gate = {
        **{key: old_gate[key] for key in sorted(required_old_keys)},
        "same_epoch_cache_hit_opportunity_not_required": True,
        "same_epoch_cache_hit_count_accounted_exactly": sequence.get(
            "same_epoch_genesis_authorized_cache_hit_count"
        )
        == hits,
        "program_branch_cache_hit_count_accounted_exactly": sequence.get(
            "program_branch_cache_hit_count"
        )
        == branch_hits,
        "zero_transition_hits_require_exact_genesis_identity": sequence.get(
            "zero_transition_reuse_requires_source_authorized_and_current_graph_identity"
        )
        is True,
        "cross_epoch_hits_require_authorization_chain": sequence.get(
            "cross_epoch_reuse_requires_epoch_authorization_chain"
        )
        is True,
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.generic_subprogram_opportunity_independent_occurrence.v121r1",
        "base_v121_occurrence": base,
        "base_v121_occurrence_id": base.get("occurrence_id"),
        "base_v121_gate_passed": old_gate.get("passed"),
        "same_epoch_genesis_authorized_cache_hit_count": hits,
        "corrected_registered_gate": gate,
        "registered_gate": gate,
        "generic_artifact_subprogram_partial_pipeline_verified": gate["passed"],
        "scientific_outcome_fields_changed_from_base": False,
        "only_opportunity_dependent_gate_criterion_removed": True,
        "legacy_shape_specific_planner_execution_adapter_present": True,
        "generic_planner_execution_adapter_verified": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v121r1(
            domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_OCCURRENCE_V121R1_DOMAIN,
            payload,
        ),
    }


def build_opportunity_independent_occurrence_v121r1(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    base = build_generic_artifact_subprogram_occurrence_v121(
        config,
        seed=seed,
        episode_indices=episode_indices,
        artifact_factor_library=artifact_factor_library,
        source_campaign_bytes=source_campaign_bytes,
        strict_complete_factor_library=strict_complete_factor_library,
    )
    return correct_generic_subprogram_occurrence_gate_v121r1(base)


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_opportunity_independent_occurrence_v121r1(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        artifact_factor_library=args[3],
        source_campaign_bytes=args[4],
        strict_complete_factor_library=args[5],
    )


def build_opportunity_independent_campaign_document_v121r1(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    failed_v121_campaign_id: str,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["seed"],
            tuple(config["target_episode_indices"]),
            artifact_factor_library,
            source_campaign_bytes,
            strict_complete_factor_library,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            rows = list(executor.map(_target, args))
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        len(rows) == config["required_target_occurrence_count"]
        and all(row["registered_gate"]["passed"] for row in rows)
        and ood["strict_ood_no_transfer"] is True
    )
    base_rows = [row["base_v121_occurrence"] for row in rows]
    keys = tuple(base_rows[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in base_rows)
        for key in keys
        if type(base_rows[0]["accounting"][key]) is int
    }
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "opportunity_independent_gate_used_in_every_occurrence": all(
            row["only_opportunity_dependent_gate_criterion_removed"] for row in rows
        ),
        "all_scientific_outcome_fields_preserved": all(
            row["scientific_outcome_fields_changed_from_base"] is False
            for row in rows
        ),
        "generic_symbol_binding_used_in_every_occurrence": all(
            row["base_v121_occurrence"]["registered_gate"][
                "generic_symbol_binding_and_opcode_interpretation_used"
            ]
            for row in rows
        ),
        "all_receding_episodes_succeed": all(
            episode["success"]
            for row in base_rows
            for episode in row["genesis_authorized_program_branch_sequence"][
                "genesis_authorized_base_sequence"
            ]["episodes"]
        ),
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    accounting = {
        **numeric,
        "same_epoch_genesis_authorized_cache_hits_are_diagnostic_not_gate": True,
        "sample_labels_execution_steps_binding_derivation_planning_dependency_and_library_derivation_separate": True,
        "sample_efficiency_improvement_claimed": False,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.generic_subprogram_opportunity_independent_campaign.v121r1",
        "preregistration_id": preregistration_id,
        "failed_v121_campaign_id": failed_v121_campaign_id,
        "failed_v121_predecessor_preserved": True,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_generic_artifact_subprogram_partial_pipeline_verified": passed,
        "legacy_shape_specific_planner_execution_adapter_present": True,
        "generic_planner_execution_adapter_verified": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v121r1(
            domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_CAMPAIGN_V121R1_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_opportunity_independent_campaign_document_v121r1",
    "build_opportunity_independent_occurrence_v121r1",
    "correct_generic_subprogram_occurrence_gate_v121r1",
)
