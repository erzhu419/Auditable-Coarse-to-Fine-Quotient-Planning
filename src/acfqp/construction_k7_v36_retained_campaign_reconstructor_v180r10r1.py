"""Reconstruct exact V35/V36 bytes from the retained V180r10 bundle tree.

This successor never calls either campaign producer and never executes a new
scientific occurrence.  It derives the semantic campaign and the accounted
campaign from the already frozen native V9 bundle evidence.  The optional
semantic replay is delegated only to the producer-free V36 verifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_v36_resource_successor_failure_freeze_v180r10 as failure
from acfqp import construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36 as v36_verifier
from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as v36_pre
from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as v35_verifier
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35_pre
from acfqp.accounting_v1 import SHARED_AXES, WorkVectorV1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


V35_CAMPAIGN_ID = "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
V35_CAMPAIGN_BYTE_COUNT = 2_295_086
V35_CAMPAIGN_SHA256 = "a68782308b14b76d8261f233d8a576b7c148e5f2134b0097af482aed772db050"
V35_VERIFICATION_ID = "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
V35_VERIFICATION_BYTE_COUNT = 2_052
V35_VERIFICATION_SHA256 = "6835ac89b3b01beb93a0c34ef7f543a85ae17316b11c82a229326dc0a307ca5d"
V36_CAMPAIGN_ID = "758f01ac78789d25512b218ed16b8ca4bfaa95a08dc52e81fc15601b42662693"
V36_CAMPAIGN_BYTE_COUNT = 250_414
V36_CAMPAIGN_SHA256 = "da3432bf18e4aa94091456f9ab09b1809258fa60dae9cd89aec93daa5dee6030"
V36_VERIFICATION_ID = "ed3354625ab6c3e8928bdf0b0807ee7e7c47a2c5c84a0e364916fc1ac2e94c14"
V36_VERIFICATION_BYTE_COUNT = 2_457
V36_VERIFICATION_SHA256 = "e3656a5ac5aa9572670b4fd382dd8b08fc32d1c1ba1eebbcf142e751ad68ef52"

_V34_CAMPAIGN_ID = "f5e83e7cb6eaee01d35b325e83e6b50676843a32af40c21aae237144b5784f05"
_V34_VERIFICATION_ID = "40baaf3c66d42ebc53e686f9dc91ae96ee92ebda442a176ac4db32c75cbc421a"
_V35_REGISTERED_V34_PREREGISTRATION_ID = "9a02a999b32b3753c4cbfc9dde0baf7b783f661e696875d5bbf97d986bbc3fc5"
_EXECUTED_V34R1_PREREGISTRATION_ID = "4546af82f1f4e6429c83148b0f37f9a3995b80e9a0bb4abc2971ada13b115920"

_MODEL_FILES = (
    "model/operational-failure-frontier.json",
    "model/operational-acquisition.json",
    "model/operational-proposal.json",
    "model/operational-proof.json",
    "model/operational-overlay.json",
)
_MODEL_PATHS = (
    "model.structural_context_rows_frozen",
    "model.structural_expression_value_evaluations",
    "model.expression_candidates_materialized",
    "model.candidate_label_consistency_checks",
    "model.active_query_partition_evaluations",
    "model.target_probability_labels_acquired",
    "model.exact_program_proof_rows_evaluated",
    "model.world_model_freezes",
)


class ConstructionK7V36RetainedCampaignReconstructorV180r10r1Error(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V36RetainedCampaignReconstructorV180r10r1Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _load(root: Path, relative_path: str) -> tuple[bytes, dict[str, Any]]:
    raw = (root / relative_path).read_bytes()
    return raw, _object(raw, relative_path)


def _summary(root: Path, relative_path: str) -> dict[str, Any]:
    raw, document = _load(root, relative_path)
    comparison = document["comparison_vector"]
    return {
        "counter_bundle_id": document["adaptive_accounting_counter_bundle_id"],
        "output_key": relative_path,
        "canonical_byte_count": len(raw),
        "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        "subject_id": document["work_vector"]["subject_id"],
        "work_vector_id": document["work_vector"]["work_vector_id"],
        "comparison_vector_id": (
            None if comparison is None else comparison["comparison_vector_id"]
        ),
        "lane": document["measurement"]["lane"],
    }


def _model_counts(root: Path) -> dict[str, int]:
    registry = registry_v9.official_counter_registry_v9()
    totals = {path: 0 for path in _MODEL_PATHS}
    for relative_path in _MODEL_FILES:
        _, document = _load(root, relative_path)
        vector = WorkVectorV1.from_dict(document["work_vector"], registry)
        for path in totals:
            totals[path] += vector.value(path)
    return totals


def _v35_campaign(root: Path) -> tuple[bytes, dict[str, Any]]:
    failure_evidence = _load(root, _MODEL_FILES[0])[1]["evidence"]
    acquisitions = _load(root, _MODEL_FILES[1])[1]["evidence"][
        "expression_acquisitions"
    ]
    proposal = _load(root, _MODEL_FILES[2])[1]["evidence"]
    proof = _load(root, _MODEL_FILES[3])[1]["evidence"]
    overlay = _load(root, _MODEL_FILES[4])[1]["evidence"]
    control = _load(root, "model/evaluation-no-prior-control.json")[1]["evidence"]
    episodes = [
        _load(root, f"episodes/episode-{index:04d}-planning-operational.json")[1][
            "evidence"
        ]["worker_reply"]["episode"]
        for index in range(4)
    ]
    episodes.sort(key=lambda row: row["episode_index"])
    decisions = [row for episode in episodes for row in episode["decisions"]]
    checkpoints = [
        row for row in decisions if row["cold_target_checkpoint"] is not None
    ]
    adaptive_labels = len(acquisitions)
    control_labels = control["distinct_context_probability_label_count"]
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_campaign.v35",
        "schema_version": v35_pre.SCHEMA_VERSION,
        "proposed_contract_version": v35_pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": "construction_k7_standard_2048_adaptive_expression_campaign_v35",
        "adaptive_expression_preregistration": v35_pre.freeze_standard_2048_adaptive_expression_preregistration_v35().to_document(),
        "additive_role_domains": {
            "proposal": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN,
            "proof": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN,
            "roles_are_not_reused_as_overlay_or_plan_certificate": True,
        },
        "preexecution_v34_accounting_binding": {
            "v35_registered_v34_preregistration_id": _V35_REGISTERED_V34_PREREGISTRATION_ID,
            "executed_v34r1_preregistration_id": _EXECUTED_V34R1_PREREGISTRATION_ID,
            "v34_accounted_campaign_id": _V34_CAMPAIGN_ID,
            "v34_accounting_verification_id": _V34_VERIFICATION_ID,
            "failed_v34_predecessor_preserved": True,
            "resource_cap_successor_preserves_scientific_workload": True,
            "partial_failed_predecessor_bundles_reused": False,
            "verified_before_first_target_probability_query": True,
        },
        "certificate_failure": failure_evidence,
        "expression_acquisitions": acquisitions,
        "expression_proposal": proposal,
        "expression_proof": proof,
        "expression_overlay": overlay,
        "matched_no_prior_first_frontier_control": control,
        "episodes": episodes,
        "episode_count": len(episodes),
        "decision_count": len(decisions),
        "model_certificate_count": len(decisions),
        "certificate_failure_count": 1,
        "ground_distinction_query_count": adaptive_labels,
        "first_frontier_no_prior_label_count": control_labels,
        "ground_distinction_label_reduction": control_labels - adaptive_labels,
        "adaptive_label_fraction_of_no_prior": Fraction(adaptive_labels, control_labels),
        "certified_decisions_per_ground_distinction_label": Fraction(len(decisions), adaptive_labels),
        "candidate_universe_count": proposal["candidate_universe_count"],
        "final_candidate_count": proposal["remaining_candidate_count"],
        "overlay_freeze_count": 1,
        "operational_target_probability_query_count_after_overlay_freeze": 0,
        "online_target_transition_observation_count": len(decisions),
        "cold_evaluation_checkpoint_count": len(checkpoints),
        "all_checkpoint_root_values_and_actions_exactly_equal": all(
            row["checkpoint_root_values_and_action_exactly_equal"]
            for row in checkpoints
        ),
        "model_operational_counter_values": _model_counts(root),
        "planning_factored_action_row_evaluation_count": sum(
            row["factored_action_row_evaluation_count"] for row in episodes
        ),
        "planning_factored_support_outcome_evaluation_count": sum(
            row["factored_support_outcome_evaluation_count"] for row in episodes
        ),
        "planning_subproof_cache_hit_count": sum(
            row["subproof_cache_hit_count"] for row in episodes
        ),
        "planning_subproof_cache_miss_count": sum(
            row["subproof_cache_miss_count"] for row in episodes
        ),
        "planning_cross_decision_subproof_cache_hit_count": sum(
            row["cross_decision_subproof_cache_hit_count"] for row in episodes
        ),
        "evaluation_no_prior_probability_label_count": control_labels,
        "evaluation_cold_target_ground_state_action_row_count": sum(
            row["cold_target_checkpoint"]["ground_state_action_row_count"]
            for row in checkpoints
        ),
        "evaluation_cold_target_ground_outcome_count": sum(
            row["cold_target_checkpoint"]["ground_outcome_count"]
            for row in checkpoints
        ),
        "sample_tax_reduced_on_registered_first_failure_label_axis": True,
        "all_plans_after_repair_use_proved_reusable_expression_model": True,
        "target_queries_restricted_to_previously_failed_frontier": True,
        "matched_control_labels_excluded_from_operational_overlay": True,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "formal_native_accounting_successor_required": True,
        "full_standard_2048_game_claimed": False,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "adaptive_expression_campaign_id": content_id(
            v35_pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }
    raw = canonical_json_bytes(document)
    if not (
        document["adaptive_expression_campaign_id"] == V35_CAMPAIGN_ID
        and len(raw) == V35_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == V35_CAMPAIGN_SHA256
    ):
        _fail("retained V35 campaign reconstruction changed")
    return raw, document


def _v35_verification(campaign: Mapping[str, Any]) -> bytes:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_expression_independent_verification.v35",
        "schema_version": v35_pre.SCHEMA_VERSION,
        "adaptive_expression_preregistration_id": v35_pre.PREREGISTRATION_ID,
        "adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
        "v34_accounted_campaign_id": _V34_CAMPAIGN_ID,
        "v34_accounting_verification_id": _V34_VERIFICATION_ID,
        "certificate_failure_id": campaign["certificate_failure"]["adaptive_expression_failure_id"],
        "adaptive_expression_proposal_id": campaign["expression_proposal"]["adaptive_expression_proposal_id"],
        "adaptive_expression_proof_id": campaign["expression_proof"]["adaptive_expression_proof_id"],
        "adaptive_expression_overlay_id": campaign["expression_overlay"]["adaptive_expression_overlay_id"],
        "episode_count": campaign["episode_count"],
        "decision_count": campaign["decision_count"],
        "ground_distinction_query_count": campaign["ground_distinction_query_count"],
        "first_frontier_no_prior_label_count": campaign["first_frontier_no_prior_label_count"],
        "adaptive_label_fraction_of_no_prior": campaign["adaptive_label_fraction_of_no_prior"],
        "cold_evaluation_checkpoint_count": campaign["cold_evaluation_checkpoint_count"],
        "failure_frontier_acquisition_and_candidate_elimination_replayed": True,
        "selected_expression_exact_proof_replayed": True,
        "every_h3_plan_certificate_replayed": True,
        "every_seeded_execution_transition_replayed": True,
        "persistent_cross_decision_cache_counters_replayed": True,
        "matched_first_frontier_no_prior_control_replayed": True,
        "cold_ground_checkpoints_replayed": True,
        "campaign_replay_result": "PASS",
        "counter_records_issued": False,
        "formal_native_accounting_successor_required": True,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(v35_pre.FUTURE_DOMAINS["verification"], payload)
    raw = canonical_json_bytes(
        {**payload, "adaptive_expression_verification_id": verification_id}
    )
    if not (
        verification_id == V35_VERIFICATION_ID
        and len(raw) == V35_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == V35_VERIFICATION_SHA256
    ):
        _fail("retained V35 verification reconstruction changed")
    return raw


def _accumulate(total: dict[str, int], values: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    result = dict(total)
    for row in values:
        axis, value = row["axis"], row["value"]
        if axis in {"peak_mounted_bytes", "peak_working_bytes"}:
            result[axis] = max(result[axis], value)
        else:
            result[axis] += value
    return result


def _prefix(root: Path, summaries: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    totals = {axis: 0 for axis in SHARED_AXES}
    rows = []
    for sequence_index, summary in enumerate(summaries):
        _, document = _load(root, summary["output_key"])
        totals = _accumulate(totals, document["comparison_vector"]["values"])
        rows.append(
            {
                "sequence_index": sequence_index,
                "work_vector_id": document["work_vector"]["work_vector_id"],
                "comparison_vector_id": document["comparison_vector"]["comparison_vector_id"],
                "subject_id": document["work_vector"]["subject_id"],
                "route_kind": document["work_vector"]["route_kind"],
                "cumulative_axis_values": [
                    {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
                ],
            }
        )
    return rows, totals


def _v36_campaign(root: Path, v35_campaign: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]:
    model = [_summary(root, path) for path in _MODEL_FILES]
    control = _summary(root, "model/evaluation-no-prior-control.json")
    operational = list(model)
    evaluation = [control]
    episodes = []
    for index in range(4):
        planning_path = f"episodes/episode-{index:04d}-planning-operational.json"
        execution_path = f"episodes/episode-{index:04d}-execution-operational.json"
        evaluation_path = f"episodes/episode-{index:04d}-evaluation.json"
        planning = _summary(root, planning_path)
        execution = _summary(root, execution_path)
        cold = _summary(root, evaluation_path)
        episode = _load(root, planning_path)[1]["evidence"]["worker_reply"]["episode"]
        operational.extend((planning, execution))
        evaluation.append(cold)
        episodes.append(
            {
                "episode_index": index,
                "v35_episode_id": episode["adaptive_expression_episode_id"],
                "decision_count": episode["decision_count"],
                "closure_reason": episode["closure_reason"],
                "final_state": episode["final_state"],
                "planning_operational_bundle": planning,
                "execution_operational_bundle": execution,
                "evaluation_bundle": cold,
            }
        )
    process = _summary(root, "process-supervision.json")
    campaign_bundle = _summary(root, "campaign-aggregation.json")
    operational.extend((process, campaign_bundle))
    prefix, totals = _prefix(root, operational)
    profiles = registry_v9.freeze_construction_accounting_registry_v9()
    payload = {
        "schema": "acfqp.standard_2048_adaptive_accounted_campaign.v36",
        "schema_version": v36_pre.SCHEMA_VERSION,
        "proposed_contract_version": v36_pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": "construction_k7_standard_2048_adaptive_expression_accounted_campaign_v36",
        "adaptive_accounting_preregistration": v36_pre.freeze_standard_2048_adaptive_accounting_preregistration_v36().to_document(),
        "v35_adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
        "v35_adaptive_expression_verification_id": V35_VERIFICATION_ID,
        "v35_native_replay_campaign_id": V35_CAMPAIGN_ID,
        "counter_registry_id": profiles["counter_registry"]["counter_registry_id"],
        "stage_profile_id": profiles["stage_profile"]["stage_profile_id"],
        "comparison_profile_id": profiles["comparison_profile"]["comparison_profile_id"],
        "actual_projection_profile_id": profiles["actual_projection_profile"]["actual_projection_profile_id"],
        "model_stage_bundles": model,
        "matched_no_prior_control_bundle": control,
        "episode_rows": episodes,
        "process_supervision_bundle": process,
        "campaign_aggregation_bundle": campaign_bundle,
        "operational_work_vector_count": len(operational),
        "evaluation_work_vector_count": len(evaluation),
        "vector_prefix_totals": prefix,
        "final_operational_comparison_totals": [
            {"axis": axis, "value": totals[axis]} for axis in SHARED_AXES
        ],
        "logical_occurrence_count": len(episodes),
        "complete_decision_count": v35_campaign["decision_count"],
        "model_certificate_count": v35_campaign["model_certificate_count"],
        "certificate_failure_count": v35_campaign["certificate_failure_count"],
        "operational_target_probability_label_query_count": v35_campaign["ground_distinction_query_count"],
        "evaluation_no_prior_probability_label_count": v35_campaign["first_frontier_no_prior_label_count"],
        "adaptive_label_fraction_of_no_prior": v35_campaign["adaptive_label_fraction_of_no_prior"],
        "cold_evaluation_checkpoint_count": v35_campaign["cold_evaluation_checkpoint_count"],
        "all_checkpoint_root_values_and_actions_exactly_equal": v35_campaign["all_checkpoint_root_values_and_actions_exactly_equal"],
        "all_required_counter_leaves_have_explicit_native_records": True,
        "all_nine_shared_resource_paths_have_measurement_receipts": True,
        "evaluation_replay_excluded_from_operational_comparison": True,
        "summary_to_counter_translation_used": False,
        "every_worker_process_executes_exactly_one_occurrence": True,
        "sample_tax_reduced_on_registered_first_failure_label_axis": True,
        "formal_counter_completeness_candidate": True,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    document = {
        **payload,
        "adaptive_accounted_campaign_id": content_id(
            v36_pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }
    raw = canonical_json_bytes(document)
    if not (
        document["adaptive_accounted_campaign_id"] == V36_CAMPAIGN_ID
        and len(raw) == V36_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == V36_CAMPAIGN_SHA256
    ):
        _fail(
            "retained V36 campaign reconstruction changed: "
            f"{document['adaptive_accounted_campaign_id']} "
            f"{len(raw)} {hashlib.sha256(raw).hexdigest()}"
        )
    return raw, document


def _v36_verification(campaign: Mapping[str, Any]) -> bytes:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_accounted_independent_verification.v36",
        "schema_version": v36_pre.SCHEMA_VERSION,
        "adaptive_accounting_preregistration_id": v36_pre.PREREGISTRATION_ID,
        "adaptive_accounted_campaign_id": V36_CAMPAIGN_ID,
        "v35_adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
        "v35_adaptive_expression_verification_id": V35_VERIFICATION_ID,
        "counter_registry_id": campaign["counter_registry_id"],
        "stage_profile_id": campaign["stage_profile_id"],
        "comparison_profile_id": campaign["comparison_profile_id"],
        "actual_projection_profile_id": campaign["actual_projection_profile_id"],
        "operational_work_vector_count": 15,
        "evaluation_work_vector_count": 5,
        "counter_record_count": 20 * len(registry_v9.official_counter_registry_v9().leaves),
        "complete_decision_count": campaign["complete_decision_count"],
        "cold_evaluation_checkpoint_count": campaign["cold_evaluation_checkpoint_count"],
        "operational_target_probability_label_query_count": campaign["operational_target_probability_label_query_count"],
        "evaluation_no_prior_probability_label_count": campaign["evaluation_no_prior_probability_label_count"],
        "every_counter_record_and_native_zero_replayed": True,
        "every_operational_comparison_recomputed": True,
        "every_output_byte_fixed_point_replayed": True,
        "all_nine_shared_resource_receipts_replayed": True,
        "V35_semantic_campaign_replayed_before_accounting": True,
        "failure_acquisition_proposal_proof_overlay_planning_and_execution_separate": True,
        "evaluation_excluded_from_operational_comparison": True,
        "final_operational_comparison_totals": campaign["final_operational_comparison_totals"],
        "registered_first_failure_label_axis_sample_tax_reduction_replayed": True,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(v36_pre.FUTURE_DOMAINS["verification"], payload)
    raw = canonical_json_bytes(
        {**payload, "adaptive_accounting_verification_id": verification_id}
    )
    if not (
        verification_id == V36_VERIFICATION_ID
        and len(raw) == V36_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == V36_VERIFICATION_SHA256
    ):
        _fail("retained V36 verification reconstruction changed")
    return raw


@dataclass(frozen=True, slots=True)
class ReconstructedV36CampaignV180r10r1:
    v35_campaign_bytes: bytes
    v35_verification_bytes: bytes
    v36_campaign_bytes: bytes
    v36_verification_bytes: bytes
    semantic_replay_performed: bool

    @property
    def campaign_id(self) -> str:
        return V36_CAMPAIGN_ID

    @property
    def verification_id(self) -> str:
        return V36_VERIFICATION_ID

    def to_document(self) -> dict[str, Any]:
        return _object(self.v36_campaign_bytes, "reconstructed V36 campaign")


def reconstruct_retained_v36_campaign_v180r10r1(
    output_root: Path,
    *,
    verify_semantics: bool = False,
) -> ReconstructedV36CampaignV180r10r1:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("retained V36 output root is absent")
    expected_root = (
        Path(__file__).resolve().parents[2]
        / ".tmp"
        / "exact-freeze"
        / "v180r10_v36_resource_successor_output"
    )
    frozen = failure.load_frozen_v36_resource_successor_failure_v180r10()
    if output_root.resolve() != expected_root.resolve() or len(frozen.output_facts) != 20:
        _fail("retained V36 reconstruction crossed the frozen output tree")
    v35_bytes, v35_document = _v35_campaign(output_root)
    v35_verification_bytes = _v35_verification(v35_document)
    v36_bytes, v36_document = _v36_campaign(output_root, v35_document)
    v36_verification_bytes = _v36_verification(v36_document)
    if verify_semantics:
        replay = v36_verifier.verify_standard_2048_adaptive_accounting_bytes_independently_v36(
            campaign_bytes=v36_bytes,
            output_root=output_root,
            v35_campaign_bytes=v35_bytes,
            v35_verification_bytes=v35_verification_bytes,
        )
        if replay.canonical_bytes != v36_verification_bytes:
            _fail("producer-free V36 replay differs from reconstructed verification")
    return ReconstructedV36CampaignV180r10r1(
        v35_bytes,
        v35_verification_bytes,
        v36_bytes,
        v36_verification_bytes,
        verify_semantics,
    )


__all__ = (
    "ConstructionK7V36RetainedCampaignReconstructorV180r10r1Error",
    "ReconstructedV36CampaignV180r10r1",
    "V35_CAMPAIGN_ID",
    "V35_VERIFICATION_ID",
    "V36_CAMPAIGN_ID",
    "V36_VERIFICATION_ID",
    "reconstruct_retained_v36_campaign_v180r10r1",
)
