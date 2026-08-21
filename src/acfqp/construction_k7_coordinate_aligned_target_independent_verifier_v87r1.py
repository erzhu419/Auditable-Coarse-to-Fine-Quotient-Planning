"""Producer-free verification of frozen V87r1 coordinate-transfer evidence."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v87r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739"
CAMPAIGN_BYTE_COUNT = 2_439_114
CAMPAIGN_SHA256 = "a0c033bd300584b9bda88520d7fdacc410970ee101c70e406387f122efec9937"
PREREGISTRATION_ID = "dca32845cd12818f18f5fd463c61c9244c9591317a03590dfa23358e4c74660f"
V87_FAILED_CAMPAIGN_ID = "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
V87_FAILURE_VERIFICATION_ID = "d8af2766c723c1b42895f9c4b5d85e2557c366af2ab6473f19516c9b54fe19d5"
PROJECTED_MODEL_ARTIFACT_ID = "c069fb2a39fee3b9dc7dc847fef15369cf8d65c5d6322bbaae1bbceb924a476e"
APPLICABILITY_MODEL_ARTIFACT_ID = "07ee765058797bc083db3180bb26952a79a224f8e8aef2f8f284237f87137f77"
SOURCE_MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
APPLICABILITY_PROGRAM_ID = "956edacfc94e1312a3a6efa42e0fc2b91bf3266f61a06b3a3a5b8a1f03d38ef0"
TARGET_SEEDS = (909_101, 909_102, 909_103, 909_104, 909_105, 909_106)
VERIFICATION_ID = "9a5fdb135fcebe2e4a31077e7a542d9af2338ecb1c2d76eda1e3f4f72eedd29d"
EXPECTED_CANONICAL_BYTE_COUNT = 2_396
EXPECTED_CANONICAL_SHA256 = "9096794ddb3742b2f7ff5dd9bc103d09ab5b43f2a30830068e2bafede64364fd"

_V59_ACQUISITION_DOMAIN = b"acfqp:construction-k7-true-bit-symmetric-acquisition:v59\x00"
_ALIGNMENT_DOMAIN = b"acfqp:generic-coordinate-alignment:v60\x00"
_OUTER_ABLATION_DOMAIN = b"acfqp:generic-coordinate-aligned-ablation:v60\x00"
_INNER_ABLATION_DOMAIN = b"acfqp:generic-applicability-ablation:v59\x00"
_EPISODE_DOMAIN = b"acfqp:generic-applicability-certificate-episode:v59\x00"


class ConstructionK7CoordinateAlignedTargetIndependentVerifierV87R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CoordinateAlignedTargetIndependentVerifierV87R1Error(message)


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"V87r1 {label} schema changed")
    return value


def _content(
    value: Mapping[str, Any], key: str, domain: bytes, label: str
) -> None:
    payload = {name: row for name, row in value.items() if name != key}
    if value.get(key) != hashlib.sha256(
        domain + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V87r1 {label} content identity changed")


def _v59_id(value: Mapping[str, Any], key: str) -> None:
    payload = {name: row for name, row in value.items() if name != key}
    if value.get(key) != hashlib.sha256(
        _V59_ACQUISITION_DOMAIN + canonical_json_bytes(payload)
    ).hexdigest():
        _fail(f"V87r1 {key} changed")


def _verify_partial(acquisition: Any, seed: int, labels: int) -> tuple[str, str, int]:
    required = {
        "acquisition_id", "arm", "candidate", "candidate_epoch",
        "candidate_issued_at_support_label", "candidate_program_disagreement_count",
        "complete_world_model_claimed", "factor_prior_enabled", "family",
        "first_accepting_observation_label", "ground_support_labels",
        "heuristic_mdl_information_units_consumed", "invalidated_candidate_count",
        "partial_prediction_scope_only", "post_issuance_exact_prediction_success_count",
        "predictive_evidence_to_mdl_credit_consumed", "raw_transition_count",
        "raw_transition_sha256", "reachable_frontier_exhaustion_input_consumed",
        "schema", "seed", "stopping_history", "symmetric_minimum_common_prefix_post_audit",
        "terminal_observation_required_for_planning_objective", "terminal_stop_update",
        "unknown_residual_outputs_claimed",
    }
    _exact_keys(acquisition, required, "partial acquisition")
    _v59_id(acquisition, "acquisition_id")
    candidate = acquisition["candidate"]
    if type(candidate) is not dict or "candidate_id" not in candidate:
        _fail("V87r1 target candidate changed")
    _v59_id(candidate, "candidate_id")
    exact = {
        "schema": "acfqp.true_bit_partial_acquisition.v59",
        "arm": "ANONYMOUS_FACTOR_PRIOR_ON",
        "family": "BALANCED_BATCH_REFINEMENT",
        "seed": seed,
        "factor_prior_enabled": True,
        "ground_support_labels": labels,
        "complete_world_model_claimed": False,
        "partial_prediction_scope_only": True,
        "unknown_residual_outputs_claimed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "symmetric_minimum_common_prefix_post_audit": True,
        "terminal_observation_required_for_planning_objective": True,
    }
    if any(acquisition.get(key) != value for key, value in exact.items()):
        _fail("V87r1 partial acquisition contract changed")
    if (
        candidate.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or candidate.get("target_bindings_derived_from_raw_observations") is not True
        or candidate.get("target_slot_inventory_supplied_by_prior") is not False
        or candidate.get("semantic_names_used") is not False
        or candidate.get("complete_world_model_claimed") is not False
        or candidate.get("planning_authority_present") is not False
    ):
        _fail("V87r1 partial candidate claim boundary changed")
    return (
        candidate["candidate_id"],
        acquisition["raw_transition_sha256"],
        acquisition["raw_transition_count"],
    )


def _verify_alignment(
    alignment: Any, candidate_id: str, raw_sha: str, raw_count: int
) -> None:
    required = {
        "action_field_width", "alignment_derived_only_from_target_common_partial_observations",
        "alignment_used_as_safety_authority", "complete_world_model_claimed",
        "coordinate_alignment_id", "exact_full_model_projection_count",
        "full_model_replay_row_evaluations", "schema", "semantic_names_used",
        "source_action_to_target_canonical", "source_applicability_program_id",
        "source_applicability_relation_opcode", "source_model_id",
        "source_model_or_applicability_refit", "source_state_to_target_canonical",
        "state_width", "target_applicability_action_field",
        "target_applicability_relation_evaluations", "target_applicability_state_column",
        "target_episode_outcomes_used", "target_exact_applicability_binding_count",
        "target_partial_candidate_id", "target_raw_transition_count",
        "target_raw_transition_sha256", "type_compatible_action_mapping_candidate_count",
        "type_compatible_state_mapping_candidate_count",
    }
    _exact_keys(alignment, required, "coordinate alignment")
    _content(alignment, "coordinate_alignment_id", _ALIGNMENT_DOMAIN, "alignment")
    state_mapping = alignment["source_state_to_target_canonical"]
    action_mapping = alignment["source_action_to_target_canonical"]
    if (
        alignment["schema"] != "acfqp.generic_coordinate_alignment.v60"
        or alignment["source_model_id"] != SOURCE_MODEL_ID
        or alignment["source_applicability_program_id"] != APPLICABILITY_PROGRAM_ID
        or alignment["target_partial_candidate_id"] != candidate_id
        or alignment["target_raw_transition_sha256"] != raw_sha
        or alignment["target_raw_transition_count"] != raw_count
        or alignment["state_width"] != 6
        or alignment["action_field_width"] != 5
        or sorted(state_mapping) != list(range(6))
        or sorted(action_mapping) != list(range(5))
        or alignment["source_applicability_relation_opcode"] != "EQ"
        or alignment["target_exact_applicability_binding_count"] < 1
        or alignment["exact_full_model_projection_count"] != 1
        or alignment["alignment_derived_only_from_target_common_partial_observations"] is not True
        or alignment["target_episode_outcomes_used"] is not False
        or alignment["source_model_or_applicability_refit"] is not False
        or alignment["semantic_names_used"] is not False
        or alignment["alignment_used_as_safety_authority"] is not False
        or alignment["complete_world_model_claimed"] is not False
    ):
        _fail("V87r1 coordinate alignment boundary changed")


def _verify_transition(row: Any) -> None:
    required = {
        "legal_action_keys_after", "legal_action_keys_before", "occurrence",
        "outcome_tape_sha256", "post_vector", "pre_vector", "selected_action",
        "terminal_acceptance_after", "transition_index",
    }
    _exact_keys(row, required, "local transition")
    action = _exact_keys(
        row["selected_action"], {"action_key", "anonymous_fields"}, "local action"
    )
    if (
        row["occurrence"] != 0
        or type(row["pre_vector"]) is not list
        or type(row["post_vector"]) is not list
        or len(row["pre_vector"]) != len(row["post_vector"]) != 0
        or type(action["action_key"]) is not int
        or type(action["anonymous_fields"]) is not list
    ):
        _fail("V87r1 local transition semantics changed")


def _verify_episode(
    episode: Any, arm: str, seed: int, projected_candidate_id: str
) -> None:
    required = {
        "abstract_model_ordering_accepted_count", "abstract_plan_abstention_count",
        "abstract_plan_attempt_count", "abstract_plan_success_count",
        "abstract_planning_compute_events", "action_applicability_program_id",
        "action_keys", "all_ground_queries_followed_failed_certificates",
        "applicability_relation_evaluations", "arm", "complete_world_model_synthesized",
        "empirical_version_space_promoted_to_global_exact_dynamics", "episode_id",
        "episode_index", "execution_steps", "failed_certificates", "family",
        "inapplicable_action_branch_evaluations_avoided", "local_distinctions",
        "maximum_target_ground_support_labels", "model_source_episode_index",
        "outcome_tape_sha256", "partial_candidate_id",
        "projected_disagreement_successor_model_id", "queried_state_action_count",
        "query_local_exact_overlay_exclusively_used_for_safety", "raw_local_transition_rows",
        "reusable_abstract_model_or_applicability_used_as_safety_authority",
        "reusable_model_and_applicability_frozen_before_target_episode",
        "same_exact_query_local_certificate_engine", "schema", "seed", "success",
        "target_certificate_local_ground_support_labels",
        "target_outcomes_used_to_refit_reusable_model_or_applicability",
    }
    _exact_keys(episode, required, "episode")
    _content(episode, "episode_id", _EPISODE_DOMAIN, "episode")
    derived = arm == "APPLICABILITY_CONDITIONED_WORLD_MODEL"
    if (
        episode["schema"] != "acfqp.generic_applicability_certificate_episode.v59"
        or episode["arm"] != arm
        or episode["family"] != "BALANCED_BATCH_REFINEMENT"
        or episode["seed"] != seed
        or episode["episode_index"] != 10
        or episode["model_source_episode_index"] != 0
        or episode["partial_candidate_id"] != projected_candidate_id
        or episode["projected_disagreement_successor_model_id"]
        != (SOURCE_MODEL_ID if derived else None)
        or episode["action_applicability_program_id"]
        != (APPLICABILITY_PROGRAM_ID if derived else None)
        or episode["success"] is not True
        or episode["same_exact_query_local_certificate_engine"] is not True
        or episode["all_ground_queries_followed_failed_certificates"] is not True
        or episode["query_local_exact_overlay_exclusively_used_for_safety"] is not True
        or episode["reusable_abstract_model_or_applicability_used_as_safety_authority"] is not False
        or episode["target_outcomes_used_to_refit_reusable_model_or_applicability"] is not False
        or episode["complete_world_model_synthesized"] is not False
    ):
        _fail("V87r1 episode contract changed")
    actions = episode["action_keys"]
    tapes = episode["outcome_tape_sha256"]
    if (
        type(actions) is not list
        or type(tapes) is not list
        or len(actions) != len(tapes)
        or episode["execution_steps"] != len(actions)
        or len(actions) <= 1
    ):
        _fail("V87r1 execution trace changed")
    failures = episode["failed_certificates"]
    distinctions = episode["local_distinctions"]
    if type(failures) is not list or type(distinctions) is not list or len(failures) != len(distinctions):
        _fail("V87r1 certificate trace cardinality changed")
    labels = 0
    transitions = []
    transition_queries = 0
    for index, (failure, distinction) in enumerate(zip(failures, distinctions, strict=True)):
        if (
            failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("raw_state") != failure.get("raw_state")
            or distinction.get("ground_support_labels") != 1
        ):
            _fail("V87r1 ground query preceded failed certificate")
        labels += 1
        if distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            rows = distinction.get("raw_transition_rows")
            if type(rows) is not list or not rows or distinction.get("action_key") != failure.get("action_key"):
                _fail("V87r1 transition distinction changed")
            for row in rows:
                _verify_transition(row)
                if row["pre_vector"] != failure["raw_state"]:
                    _fail("V87r1 local transition state join changed")
            transitions.extend(rows)
            transition_queries += 1
        elif distinction.get("distinction_kind") == "QUERY_LOCAL_LEGAL_ACTION_SET":
            if failure.get("action_key") is not None:
                _fail("V87r1 legality distinction action changed")
        else:
            _fail("V87r1 distinction kind changed")
    if (
        labels != episode["target_certificate_local_ground_support_labels"]
        or transitions != episode["raw_local_transition_rows"]
        or transition_queries != episode["queried_state_action_count"]
    ):
        _fail("V87r1 certificate-local accounting changed")
    if derived:
        if (
            episode["abstract_plan_attempt_count"] <= 0
            or episode["abstract_plan_success_count"]
            != episode["abstract_plan_attempt_count"]
            or episode["abstract_plan_abstention_count"] != 0
            or episode["abstract_model_ordering_accepted_count"]
            != episode["abstract_plan_success_count"]
            or episode["abstract_model_ordering_accepted_count"]
            < episode["execution_steps"]
            or episode["applicability_relation_evaluations"] <= 0
            or episode["inapplicable_action_branch_evaluations_avoided"] <= 0
        ):
            _fail("V87r1 abstract ordering evidence changed")
    elif any(
        episode[key] != 0
        for key in (
            "abstract_plan_attempt_count", "abstract_plan_success_count",
            "abstract_plan_abstention_count", "abstract_model_ordering_accepted_count",
            "abstract_planning_compute_events", "applicability_relation_evaluations",
            "inapplicable_action_branch_evaluations_avoided",
        )
    ):
        _fail("V87r1 strict arm consumed abstract planning")


def _verify_ablation(
    ablation: Any, seed: int, candidate_id: str, alignment: Mapping[str, Any]
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    _content(ablation, "ablation_id", _OUTER_ABLATION_DOMAIN, "outer ablation")
    if (
        ablation.get("schema")
        != "acfqp.generic_coordinate_aligned_applicability_ablation.v60"
        or ablation.get("family") != "BALANCED_BATCH_REFINEMENT"
        or ablation.get("seed") != seed
        or ablation.get("target_partial_candidate_id") != candidate_id
        or ablation.get("coordinate_alignment") != alignment
        or ablation.get("coordinate_alignment_id")
        != alignment["coordinate_alignment_id"]
        or ablation.get("alignment_frozen_before_target_episode") is not True
        or ablation.get("target_episode_outcomes_used_to_select_alignment") is not False
        or ablation.get("all_ground_queries_followed_failed_certificates") is not True
        or ablation.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        or ablation.get("coordinate_alignment_or_model_used_as_safety_authority") is not False
        or ablation.get("multi_step_planning_primarily_in_abstract_model_claimed") is not False
        or ablation.get("complete_world_model_synthesized") is not False
        or ablation.get("official_scalar_cost") is not None
    ):
        _fail("V87r1 outer ablation contract changed")
    inner = ablation.get("underlying_matched_ablation")
    if type(inner) is not dict:
        _fail("V87r1 underlying ablation changed")
    _content(inner, "ablation_id", _INNER_ABLATION_DOMAIN, "inner ablation")
    if ablation.get("arms") != inner.get("arms"):
        _fail("V87r1 outer/inner arm join changed")
    arms = inner["arms"]
    _exact_keys(
        arms,
        {"APPLICABILITY_CONDITIONED_WORLD_MODEL", "STRICT_NO_REUSABLE_MODEL"},
        "matched arms",
    )
    derived = arms["APPLICABILITY_CONDITIONED_WORLD_MODEL"]
    strict = arms["STRICT_NO_REUSABLE_MODEL"]
    projected_candidate_id = ablation["projected_partial_candidate_id"]
    _verify_episode(derived, "APPLICABILITY_CONDITIONED_WORLD_MODEL", seed, projected_candidate_id)
    _verify_episode(strict, "STRICT_NO_REUSABLE_MODEL", seed, projected_candidate_id)
    paired = (
        "family", "seed", "episode_index", "model_source_episode_index",
        "partial_candidate_id", "action_keys", "outcome_tape_sha256", "execution_steps",
        "target_certificate_local_ground_support_labels", "queried_state_action_count",
        "failed_certificates", "local_distinctions", "raw_local_transition_rows",
    )
    if any(derived[key] != strict[key] for key in paired):
        _fail("V87r1 matched arms changed exact certificate result")
    derived_labels = derived["target_certificate_local_ground_support_labels"]
    strict_labels = strict["target_certificate_local_ground_support_labels"]
    if (
        ablation["derived_target_certificate_local_ground_support_labels"] != derived_labels
        or ablation["strict_target_certificate_local_ground_support_labels"] != strict_labels
        or ablation["derived_minus_strict_target_labels"] != derived_labels - strict_labels
        or ablation["actual_target_sample_reduction_observed"] != (derived_labels < strict_labels)
        or inner["derived_target_certificate_local_ground_support_labels"] != derived_labels
        or inner["strict_target_certificate_local_ground_support_labels"] != strict_labels
    ):
        _fail("V87r1 matched label comparison changed")
    return derived, strict


def verify_coordinate_aligned_target_campaign_bytes_v87r1(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V87r1 campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V87r1 campaign canonical form changed")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or domains.extension_content_id_v87r1(
            domains.CONSTRUCTION_K7_COORDINATE_ALIGNED_CAMPAIGN_V87R1_DOMAIN,
            payload,
        )
        != CAMPAIGN_ID
    ):
        _fail("V87r1 campaign content identity changed")
    fixed = {
        "schema": "acfqp.coordinate_aligned_target_campaign.v87r1",
        "preregistration_id": PREREGISTRATION_ID,
        "v87_failed_campaign_id": V87_FAILED_CAMPAIGN_ID,
        "v87_failure_verification_id": V87_FAILURE_VERIFICATION_ID,
        "projected_model_artifact_id": PROJECTED_MODEL_ARTIFACT_ID,
        "applicability_model_artifact_id": APPLICABILITY_MODEL_ARTIFACT_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "action_applicability_program_id": APPLICABILITY_PROGRAM_ID,
        "v87_failure_preserved_and_not_overwritten": True,
        "alignment_and_models_frozen_before_every_target_episode": True,
        "target_episode_outcomes_used_to_select_alignment_or_refit_models": False,
        "multi_step_abstract_ordering_primary_observed": True,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "certificate_failure_only_local_ground_recovery_observed": True,
        "query_local_exact_overlay_only_safety_authority": True,
        "sample_tax_reduction_verified": False,
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
    if any(document.get(key) != value for key, value in fixed.items()):
        _fail("V87r1 campaign claim boundary changed")
    occurrences = document.get("target_occurrences")
    if type(occurrences) is not list or [row.get("target_seed") for row in occurrences] != list(TARGET_SEEDS):
        _fail("V87r1 registered target identities changed")
    derived_rows = []
    strict_rows = []
    alignments = []
    occurrence_ids = []
    candidate_ids = []
    common_labels = 0
    for row in occurrences:
        occurrence_payload = {key: value for key, value in row.items() if key != "occurrence_id"}
        if row.get("occurrence_id") != domains.extension_content_id_v87r1(
            domains.CONSTRUCTION_K7_COORDINATE_ALIGNED_OCCURRENCE_V87R1_DOMAIN,
            occurrence_payload,
        ):
            _fail("V87r1 occurrence identity changed")
        if (
            row.get("schema") != "acfqp.coordinate_aligned_target_occurrence.v87r1"
            or row.get("family") != "BALANCED_BATCH_REFINEMENT"
            or row.get("target_episode_index") != 10
            or row.get("v87_failed_campaign_id") != V87_FAILED_CAMPAIGN_ID
            or row.get("target_structural_schema_family_eligible") is not True
            or row.get("status")
            != "TARGET_COORDINATE_ALIGNED_MATCHED_EPISODES_COMPLETED"
            or row.get("failure_reason") is not None
            or row.get("alignment_and_models_frozen_before_target_episode") is not True
            or row.get("target_episode_outcomes_used_to_select_alignment_or_refit_models") is not False
            or row.get("certificate_failure_only_local_ground_distinctions") is not True
            or row.get("query_local_exact_overlay_only_safety_authority") is not True
            or row.get("official_execution_allowed") is not False
        ):
            _fail("V87r1 occurrence contract changed")
        candidate_id, raw_sha, raw_count = _verify_partial(
            row["target_common_partial_acquisition"],
            row["target_seed"],
            row["target_common_partial_ground_support_labels"],
        )
        alignment = row["coordinate_alignment"]
        _verify_alignment(alignment, candidate_id, raw_sha, raw_count)
        if row["coordinate_alignment_id"] != alignment["coordinate_alignment_id"]:
            _fail("V87r1 occurrence alignment join changed")
        expected_ood = {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_SEARCH",
            "reason": "V60 target is not in the registered structural schema family",
            "ground_transition_accessed_beyond_registered_partial_prefix": False,
        }
        if row.get("incompatible_schema_ood_control") != expected_ood:
            _fail("V87r1 OOD control changed")
        derived, strict = _verify_ablation(
            row["matched_ablation"], row["target_seed"], candidate_id, alignment
        )
        derived_rows.append(derived)
        strict_rows.append(strict)
        alignments.append(alignment)
        occurrence_ids.append(row["occurrence_id"])
        candidate_ids.append(candidate_id)
        common_labels += row["target_common_partial_ground_support_labels"]
    derived_labels = sum(row["target_certificate_local_ground_support_labels"] for row in derived_rows)
    strict_labels = sum(row["target_certificate_local_ground_support_labels"] for row in strict_rows)
    gate = {
        "required_target_occurrence_count": 6,
        "actual_target_occurrence_count": 6,
        "minimum_aligned_completed_target_count": 4,
        "actual_structural_schema_family_eligible_count": 6,
        "actual_coordinate_aligned_completed_target_count": 6,
        "every_eligible_target_completed": True,
        "unique_observation_derived_alignment_on_every_completed_target": True,
        "certificate_failure_only_ground_discipline_clean": True,
        "every_successful_abstract_output_accepted_as_legal": True,
        "multi_step_abstract_ordering_coverage_on_every_completed_target": True,
        "applicability_filter_effective_on_every_completed_target": True,
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": True,
    }
    if document.get("registered_gate") != gate:
        _fail("V87r1 registered Gate changed")
    sample = {
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "reduction_required_for_this_gate": False,
    }
    if document.get("sample_tax_measurement") != sample:
        _fail("V87r1 sample-tax measurement changed")
    accounting = {
        "offline_v85r1_template_source_labels": 515,
        "offline_residual_library_labels": 204,
        "offline_v85r1_source_common_partial_labels": 170,
        "offline_v85r1_source_certificate_local_labels": 318,
        "offline_v85r1_group_query_counts_not_physical_labels": 266,
        "offline_applicability_state_action_classifications_not_physical_labels": 4260,
        "target_common_partial_labels": common_labels,
        "target_alignment_relation_evaluations_not_physical_labels": sum(row["target_applicability_relation_evaluations"] for row in alignments),
        "target_alignment_model_replay_row_evaluations_not_physical_labels": sum(row["full_model_replay_row_evaluations"] for row in alignments),
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_target_execution_steps": sum(row["execution_steps"] for row in derived_rows),
        "strict_target_execution_steps": sum(row["execution_steps"] for row in strict_rows),
        "derived_abstract_planning_compute_events": sum(row["abstract_planning_compute_events"] for row in derived_rows),
        "derived_applicability_relation_evaluations": sum(row["applicability_relation_evaluations"] for row in derived_rows),
        "derived_inapplicable_action_branch_evaluations_avoided": sum(row["inapplicable_action_branch_evaluations_avoided"] for row in derived_rows),
        "strict_abstract_planning_compute_events": sum(row["abstract_planning_compute_events"] for row in strict_rows),
        "all_axes_separate": True,
    }
    if document.get("accounting") != accounting:
        _fail("V87r1 accounting changed")
    verification_payload = {
        "schema": "acfqp.coordinate_aligned_target_independent_verification.v87r1",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "target_occurrence_ids": occurrence_ids,
        "target_candidate_ids": candidate_ids,
        "coordinate_alignment_ids": [row["coordinate_alignment_id"] for row in alignments],
        "target_occurrence_count": 6,
        "coordinate_aligned_completed_target_count": 6,
        "failed_certificate_count_replayed": sum(len(row["failed_certificates"]) for row in (*derived_rows, *strict_rows)),
        "local_distinction_count_replayed": sum(len(row["local_distinctions"]) for row in (*derived_rows, *strict_rows)),
        "alignment_content_id_and_input_hash_replayed": True,
        "alignment_rederived_from_embedded_raw_rows": False,
        "matched_certificate_traces_replayed": True,
        "registered_target_gate_verified": True,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "sample_tax_reduction_verified": False,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v87r1(
            domains.CONSTRUCTION_K7_COORDINATE_ALIGNED_VERIFICATION_V87R1_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V87r1 independent verification changed")
    return result


__all__ = ("verify_coordinate_aligned_target_campaign_bytes_v87r1",)
