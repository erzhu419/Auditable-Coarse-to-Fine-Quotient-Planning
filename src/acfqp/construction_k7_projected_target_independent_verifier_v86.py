"""Producer-free verification of the frozen V86 target-transfer evidence."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v86 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "7e40be0ebf5f68c42f050e5cd441ba1d81dca603328fda380de6fe01d52f7cae"
CAMPAIGN_BYTE_COUNT = 595_978
CAMPAIGN_SHA256 = "39ab8fb785c063a764fc8348ec3e583626e7d0309250c6e77d9fa2414aad6fd1"
PREREGISTRATION_ID = "aa34820576e1f935782ec6d3be5151be4cda750e33e7b523eccd209c7dc4bb78"
MODEL_ARTIFACT_ID = "c069fb2a39fee3b9dc7dc847fef15369cf8d65c5d6322bbaae1bbceb924a476e"
SOURCE_MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
V85R1_CAMPAIGN_ID = "da749b6ad8996aba86896476fd7293540cca77cd1b4db7145b9bf4fe2759ec70"
V85R1_VERIFICATION_ID = "391038636f3b1744112f1a4a08b9d4acb5d32f8d19c27af603e69431cd40ad0f"
TARGET_SEEDS = (889_101, 889_102, 889_103, 889_104, 889_105, 889_106)
VERIFICATION_ID = "407284fb94ab6c2431bc99d9f7b706b84efdaac5f8f319209e6fb5596cebe0d0"
EXPECTED_CANONICAL_BYTE_COUNT = 1_874
EXPECTED_CANONICAL_SHA256 = "b785d73d7f145b95d63eedb868bcc77bcd93ec074acd668593973ed4d19bfdd6"

_V59_ACQUISITION_DOMAIN = (
    "acfqp:construction-k7-true-bit-symmetric-acquisition:v59"
)
_EPISODE_DOMAIN = b"acfqp:generic-projected-disagreement-certificate-episode:v57\x00"
_ABLATION_DOMAIN = b"acfqp:generic-projected-disagreement-ablation:v57\x00"

_TOP_KEYS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "accounting",
    "arbitrary_domain_transfer_claimed",
    "campaign_id",
    "certificate_failure_only_local_ground_recovery_observed",
    "complete_world_model_synthesized",
    "global_exact_dynamics_claimed",
    "model_artifact_id",
    "model_frozen_before_all_target_outcomes",
    "multi_step_planning_primarily_in_abstract_model_claimed",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "preregistration_id",
    "producer_free_verification_present",
    "query_local_exact_overlay_only_safety_authority",
    "registered_gate",
    "sample_tax_measurement",
    "schema",
    "source_model_id",
    "target_occurrences",
    "target_outcomes_used_to_refit_source_model",
    "v85r1_campaign_id",
    "v85r1_verification_id",
}
_OCCURRENCE_KEYS = {
    "certificate_failure_only_local_ground_distinctions",
    "failure_reason",
    "family",
    "incompatible_schema_ood_control",
    "matched_ablation",
    "model_frozen_before_target_occurrence",
    "occurrence_id",
    "official_execution_allowed",
    "query_local_exact_overlay_only_safety_authority",
    "schema",
    "source_model_id",
    "status",
    "target_common_partial_acquisition",
    "target_common_partial_ground_support_labels",
    "target_episode_index",
    "target_outcomes_used_to_select_or_refit_model",
    "target_seed",
    "target_structurally_compatible",
}
_EPISODE_KEYS = {
    "abstract_model_ordering_accepted_count",
    "abstract_plan_abstention_count",
    "abstract_plan_attempt_count",
    "abstract_plan_success_count",
    "abstract_planning_compute_events",
    "action_keys",
    "all_ground_queries_followed_failed_certificates",
    "arm",
    "complete_world_model_synthesized",
    "empirical_version_space_promoted_to_global_exact_dynamics",
    "episode_id",
    "episode_index",
    "execution_steps",
    "failed_certificates",
    "family",
    "local_distinctions",
    "maximum_target_ground_support_labels",
    "model_source_episode_index",
    "outcome_tape_sha256",
    "partial_candidate_id",
    "projected_disagreement_successor_model_id",
    "queried_state_action_count",
    "query_local_exact_overlay_exclusively_used_for_safety",
    "raw_local_transition_rows",
    "reusable_abstract_model_used_as_safety_authority",
    "reusable_model_frozen_before_target_episode",
    "same_exact_query_local_certificate_engine",
    "schema",
    "seed",
    "success",
    "target_certificate_local_ground_support_labels",
    "target_outcomes_used_to_refit_reusable_model",
}
_ABLATION_KEYS = {
    "WORKLOAD_ECONOMICS_GATE",
    "ablation_id",
    "abstract_model_safety_authority_present",
    "actual_target_sample_reduction_observed",
    "all_ground_queries_followed_failed_certificates",
    "arms",
    "derived_minus_strict_target_labels",
    "derived_target_certificate_local_ground_support_labels",
    "execution_steps_and_planning_compute_separate_from_labels",
    "family",
    "model_source_episode_index",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "offline_source_labels_and_target_labels_separate",
    "only_reusable_model_availability_differs_between_arms",
    "projected_disagreement_successor_model_id",
    "query_local_exact_overlay_exclusively_used_for_safety",
    "same_adapter_kernel_seed_and_target_episode",
    "same_exact_certificate_engine_and_stopping_rule",
    "schema",
    "seed",
    "strict_target_certificate_local_ground_support_labels",
    "target_episode_index",
}


class ConstructionK7ProjectedTargetIndependentVerifierV86Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedTargetIndependentVerifierV86Error(message)


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"V86 {label} schema changed")
    return value


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _v59_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _V59_ACQUISITION_DOMAIN.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _content(value: Mapping[str, Any], key: str, domain: bytes, label: str) -> None:
    payload = {name: row for name, row in value.items() if name != key}
    if value.get(key) != _generic_id(domain, payload):
        _fail(f"V86 {label} content identity changed")


def _verify_partial_acquisition(
    acquisition: Any, seed: int, occurrence_labels: int
) -> str:
    if type(acquisition) is not dict:
        _fail("V86 target acquisition changed")
    required = {
        "acquisition_id",
        "arm",
        "candidate",
        "candidate_epoch",
        "candidate_issued_at_support_label",
        "candidate_program_disagreement_count",
        "complete_world_model_claimed",
        "factor_prior_enabled",
        "family",
        "first_accepting_observation_label",
        "ground_support_labels",
        "heuristic_mdl_information_units_consumed",
        "invalidated_candidate_count",
        "partial_prediction_scope_only",
        "post_issuance_exact_prediction_success_count",
        "predictive_evidence_to_mdl_credit_consumed",
        "raw_transition_count",
        "raw_transition_sha256",
        "reachable_frontier_exhaustion_input_consumed",
        "schema",
        "seed",
        "stopping_history",
        "symmetric_minimum_common_prefix_post_audit",
        "terminal_observation_required_for_planning_objective",
        "terminal_stop_update",
        "unknown_residual_outputs_claimed",
    }
    _exact_keys(acquisition, required, "target acquisition")
    payload = {key: value for key, value in acquisition.items() if key != "acquisition_id"}
    if acquisition["acquisition_id"] != _v59_id(payload):
        _fail("V86 acquisition content identity changed")
    candidate = acquisition["candidate"]
    if type(candidate) is not dict or "candidate_id" not in candidate:
        _fail("V86 target candidate changed")
    candidate_payload = {
        key: value for key, value in candidate.items() if key != "candidate_id"
    }
    if candidate["candidate_id"] != _v59_id(candidate_payload):
        _fail("V86 target candidate identity changed")
    exact = {
        "schema": "acfqp.true_bit_partial_acquisition.v59",
        "arm": "ANONYMOUS_FACTOR_PRIOR_ON",
        "family": "BALANCED_BATCH_REFINEMENT",
        "seed": seed,
        "factor_prior_enabled": True,
        "ground_support_labels": occurrence_labels,
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
        _fail("V86 target acquisition contract changed")
    if (
        candidate.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or candidate.get("complete_world_model_claimed") is not False
        or candidate.get("planning_authority_present") is not False
        or candidate.get("target_bindings_derived_from_raw_observations") is not True
        or candidate.get("target_slot_inventory_supplied_by_prior") is not False
        or candidate.get("semantic_names_used") is not False
    ):
        _fail("V86 target partial candidate claim boundary changed")
    if acquisition.get("candidate_issued_at_support_label") != candidate.get(
        "support_label_count_at_issuance"
    ):
        _fail("V86 target candidate issuance accounting changed")
    return candidate["candidate_id"]


def _verify_transition_row(row: Any) -> None:
    expected = {
        "legal_action_keys_after",
        "legal_action_keys_before",
        "occurrence",
        "outcome_tape_sha256",
        "post_vector",
        "pre_vector",
        "selected_action",
        "terminal_acceptance_after",
        "transition_index",
    }
    _exact_keys(row, expected, "local transition row")
    action = row["selected_action"]
    _exact_keys(action, {"action_key", "anonymous_fields"}, "local transition action")
    if (
        row["occurrence"] != 0
        or type(row["transition_index"]) is not int
        or type(row["pre_vector"]) is not list
        or type(row["post_vector"]) is not list
        or len(row["pre_vector"]) != len(row["post_vector"])
        or any(type(value) is not int for value in (*row["pre_vector"], *row["post_vector"]))
        or type(action["action_key"]) is not int
        or type(action["anonymous_fields"]) is not list
        or any(type(value) is not int for value in action["anonymous_fields"])
    ):
        _fail("V86 local transition row semantics changed")


def _verify_episode(episode: Any, arm: str, seed: int, candidate_id: str) -> None:
    _exact_keys(episode, _EPISODE_KEYS, "target episode")
    _content(episode, "episode_id", _EPISODE_DOMAIN, "target episode")
    expected_model = SOURCE_MODEL_ID if arm == "PROJECTED_DISAGREEMENT_WORLD_MODEL" else None
    if (
        episode.get("schema")
        != "acfqp.generic_projected_disagreement_certificate_episode.v57"
        or episode.get("arm") != arm
        or episode.get("family") != "BALANCED_BATCH_REFINEMENT"
        or episode.get("seed") != seed
        or episode.get("episode_index") != 7
        or episode.get("model_source_episode_index") != 0
        or episode.get("partial_candidate_id") != candidate_id
        or episode.get("projected_disagreement_successor_model_id") != expected_model
        or episode.get("success") is not True
        or episode.get("same_exact_query_local_certificate_engine") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        or episode.get("reusable_abstract_model_used_as_safety_authority") is not False
        or episode.get("target_outcomes_used_to_refit_reusable_model") is not False
        or episode.get("empirical_version_space_promoted_to_global_exact_dynamics") is not False
        or episode.get("complete_world_model_synthesized") is not False
    ):
        _fail("V86 target episode contract changed")
    actions = episode["action_keys"]
    tapes = episode["outcome_tape_sha256"]
    if (
        type(actions) is not list
        or type(tapes) is not list
        or len(actions) != len(tapes) != 0
        or episode["execution_steps"] != len(actions)
        or any(type(value) is not int for value in actions)
        or any(type(value) is not str or len(value) != 64 for value in tapes)
    ):
        _fail("V86 target execution trace changed")
    failures = episode["failed_certificates"]
    distinctions = episode["local_distinctions"]
    if type(failures) is not list or type(distinctions) is not list or len(failures) != len(distinctions):
        _fail("V86 certificate-local trace cardinality changed")
    flattened = []
    labels = 0
    transition_queries = 0
    for index, (failure, distinction) in enumerate(zip(failures, distinctions)):
        _exact_keys(
            failure,
            {
                "action_key",
                "failure_index",
                "failure_kind",
                "ground_query_performed_before_failure",
                "raw_state",
            },
            "failed certificate",
        )
        if (
            failure["failure_index"] != index
            or failure["ground_query_performed_before_failure"] is not False
            or distinction.get("failure_index") != index
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("raw_state") != failure["raw_state"]
            or distinction.get("ground_support_labels") != 1
        ):
            _fail("V86 ground query preceded its failed certificate")
        labels += 1
        kind = distinction.get("distinction_kind")
        if kind == "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            expected_keys = {
                "action_key",
                "distinction_kind",
                "failure_index",
                "ground_support_labels",
                "query_after_failed_certificate",
                "raw_state",
                "raw_transition_rows",
            }
            _exact_keys(distinction, expected_keys, "transition distinction")
            if distinction["action_key"] != failure["action_key"]:
                _fail("V86 transition distinction action changed")
            rows = distinction["raw_transition_rows"]
            if type(rows) is not list or not rows:
                _fail("V86 transition distinction support changed")
            for row in rows:
                _verify_transition_row(row)
                if row["pre_vector"] != failure["raw_state"] or row["selected_action"]["action_key"] != failure["action_key"]:
                    _fail("V86 local transition support join changed")
            flattened.extend(rows)
            transition_queries += 1
        elif kind == "QUERY_LOCAL_LEGAL_ACTION_SET":
            _exact_keys(
                distinction,
                {
                    "distinction_kind",
                    "failure_index",
                    "ground_support_labels",
                    "legal_action_keys",
                    "query_after_failed_certificate",
                    "raw_state",
                },
                "legality distinction",
            )
            if failure["action_key"] is not None:
                _fail("V86 legality distinction action changed")
        else:
            _fail("V86 distinction kind changed")
    if (
        labels != episode["target_certificate_local_ground_support_labels"]
        or flattened != episode["raw_local_transition_rows"]
        or transition_queries != episode["queried_state_action_count"]
    ):
        _fail("V86 certificate-local accounting changed")
    if arm == "PROJECTED_DISAGREEMENT_WORLD_MODEL":
        if (
            episode["reusable_model_frozen_before_target_episode"] is not True
            or episode["abstract_plan_attempt_count"] <= 0
            or episode["abstract_plan_success_count"] <= 0
            or episode["abstract_model_ordering_accepted_count"] <= 0
            or episode["abstract_planning_compute_events"] <= 0
        ):
            _fail("V86 abstract model was not used to order the target plan")
    elif (
        episode["reusable_model_frozen_before_target_episode"] is not False
        or any(
            episode[key] != 0
            for key in (
                "abstract_plan_attempt_count",
                "abstract_plan_success_count",
                "abstract_plan_abstention_count",
                "abstract_model_ordering_accepted_count",
                "abstract_planning_compute_events",
            )
        )
    ):
        _fail("V86 strict arm consumed abstract-model planning")


def _verify_ablation(ablation: Any, seed: int, candidate_id: str) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    _exact_keys(ablation, _ABLATION_KEYS, "matched ablation")
    _content(ablation, "ablation_id", _ABLATION_DOMAIN, "matched ablation")
    arms = ablation["arms"]
    _exact_keys(
        arms,
        {"PROJECTED_DISAGREEMENT_WORLD_MODEL", "STRICT_NO_REUSABLE_MODEL"},
        "matched arms",
    )
    derived = arms["PROJECTED_DISAGREEMENT_WORLD_MODEL"]
    strict = arms["STRICT_NO_REUSABLE_MODEL"]
    _verify_episode(derived, "PROJECTED_DISAGREEMENT_WORLD_MODEL", seed, candidate_id)
    _verify_episode(strict, "STRICT_NO_REUSABLE_MODEL", seed, candidate_id)
    paired = (
        "family",
        "seed",
        "episode_index",
        "model_source_episode_index",
        "partial_candidate_id",
        "action_keys",
        "outcome_tape_sha256",
        "execution_steps",
        "target_certificate_local_ground_support_labels",
        "queried_state_action_count",
        "failed_certificates",
        "local_distinctions",
        "raw_local_transition_rows",
    )
    if any(derived[key] != strict[key] for key in paired):
        _fail("V86 matched arms changed an input or exact certificate engine result")
    derived_labels = derived["target_certificate_local_ground_support_labels"]
    strict_labels = strict["target_certificate_local_ground_support_labels"]
    exact = {
        "schema": "acfqp.generic_projected_disagreement_ablation.v57",
        "family": "BALANCED_BATCH_REFINEMENT",
        "seed": seed,
        "model_source_episode_index": 0,
        "target_episode_index": 7,
        "projected_disagreement_successor_model_id": SOURCE_MODEL_ID,
        "derived_target_certificate_local_ground_support_labels": derived_labels,
        "strict_target_certificate_local_ground_support_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "same_adapter_kernel_seed_and_target_episode": True,
        "same_exact_certificate_engine_and_stopping_rule": True,
        "only_reusable_model_availability_differs_between_arms": True,
        "offline_source_labels_and_target_labels_separate": True,
        "execution_steps_and_planning_compute_separate_from_labels": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "abstract_model_safety_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }
    if any(ablation.get(key) != value for key, value in exact.items()):
        _fail("V86 matched ablation contract changed")
    return derived, strict


def verify_projected_target_campaign_bytes_v86(raw: bytes) -> bytes:
    if type(raw) is not bytes or len(raw) != CAMPAIGN_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256:
        _fail("V86 campaign bytes changed")
    document = loads_canonical_json(raw)
    _exact_keys(document, _TOP_KEYS, "campaign")
    if canonical_json_bytes(document) != raw:
        _fail("V86 campaign is not canonical")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if (
        document["campaign_id"] != CAMPAIGN_ID
        or domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_TARGET_CAMPAIGN_V86_DOMAIN, payload
        )
        != CAMPAIGN_ID
    ):
        _fail("V86 campaign content identity changed")
    fixed = {
        "schema": "acfqp.projected_disagreement_target_campaign.v86",
        "preregistration_id": PREREGISTRATION_ID,
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "v85r1_campaign_id": V85R1_CAMPAIGN_ID,
        "v85r1_verification_id": V85R1_VERIFICATION_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "model_frozen_before_all_target_outcomes": True,
        "target_outcomes_used_to_refit_source_model": False,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "certificate_failure_only_local_ground_recovery_observed": True,
        "query_local_exact_overlay_only_safety_authority": True,
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
        _fail("V86 campaign claim boundary changed")
    occurrences = document["target_occurrences"]
    if type(occurrences) is not list or [row.get("target_seed") for row in occurrences] != list(TARGET_SEEDS):
        _fail("V86 registered target identities changed")
    compatible = []
    completed = []
    derived_episodes = []
    strict_episodes = []
    for row in occurrences:
        _exact_keys(row, _OCCURRENCE_KEYS, "target occurrence")
        occurrence_payload = {key: value for key, value in row.items() if key != "occurrence_id"}
        if row["occurrence_id"] != domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_TARGET_OCCURRENCE_V86_DOMAIN,
            occurrence_payload,
        ):
            _fail("V86 target occurrence identity changed")
        if (
            row["schema"] != "acfqp.projected_disagreement_target_occurrence.v86"
            or row["family"] != "BALANCED_BATCH_REFINEMENT"
            or row["target_episode_index"] != 7
            or row["source_model_id"] != SOURCE_MODEL_ID
            or row["model_frozen_before_target_occurrence"] is not True
            or row["target_outcomes_used_to_select_or_refit_model"] is not False
            or row["certificate_failure_only_local_ground_distinctions"] is not True
            or row["query_local_exact_overlay_only_safety_authority"] is not True
            or row["official_execution_allowed"] is not False
        ):
            _fail("V86 target occurrence contract changed")
        candidate_id = _verify_partial_acquisition(
            row["target_common_partial_acquisition"],
            row["target_seed"],
            row["target_common_partial_ground_support_labels"],
        )
        if row["target_structurally_compatible"] is True:
            compatible.append(row)
            if (
                row["status"] != "TARGET_MATCHED_EPISODES_COMPLETED"
                or row["failure_reason"] is not None
                or type(row["incompatible_schema_ood_control"]) is not dict
                or row["incompatible_schema_ood_control"]
                != {
                    "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH",
                    "reason": "V54 target occurrence is not structurally compatible with the model",
                    "ground_transition_accessed": False,
                }
            ):
                _fail("V86 compatible target completion or OOD control changed")
            derived, strict = _verify_ablation(
                row["matched_ablation"], row["target_seed"], candidate_id
            )
            completed.append(row)
            derived_episodes.append(derived)
            strict_episodes.append(strict)
        elif (
            row["status"]
            != "TARGET_STRUCTURALLY_INCOMPATIBLE_NO_TRANSFER_NO_EPISODE"
            or row["failure_reason"] is not None
            or row["matched_ablation"] is not None
            or row["incompatible_schema_ood_control"] is not None
        ):
            _fail("V86 structurally incompatible target was not rejected")
    derived_labels = sum(row["target_certificate_local_ground_support_labels"] for row in derived_episodes)
    strict_labels = sum(row["target_certificate_local_ground_support_labels"] for row in strict_episodes)
    gate = {
        "required_target_occurrence_count": 6,
        "actual_target_occurrence_count": len(occurrences),
        "minimum_compatible_completed_target_count": 2,
        "actual_structurally_compatible_target_count": len(compatible),
        "actual_completed_matched_target_count": len(completed),
        "every_compatible_target_completed": len(completed) == len(compatible),
        "certificate_failure_only_ground_discipline_clean": True,
        "abstract_world_model_ordering_used_on_every_completed_target": bool(derived_episodes)
        and all(row["abstract_plan_success_count"] > 0 and row["abstract_model_ordering_accepted_count"] > 0 for row in derived_episodes),
        "strict_incompatible_schema_no_transfer_verified": bool(completed),
        "passed": len(occurrences) == 6 and len(completed) >= 2 and len(completed) == len(compatible),
    }
    if document["registered_gate"] != gate or gate["passed"] is not True:
        _fail("V86 registered Gate did not reconstruct")
    sample = {
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "reduction_required_for_this_transfer_gate": False,
    }
    if document["sample_tax_measurement"] != sample:
        _fail("V86 sample-tax measurement changed")
    accounting = {
        "offline_v85r1_template_source_labels": 515,
        "offline_residual_library_labels": 204,
        "offline_v85r1_source_common_partial_labels": 170,
        "offline_v85r1_source_certificate_local_labels": 318,
        "offline_v85r1_group_query_counts_not_physical_labels": 266,
        "target_common_partial_labels": sum(row["target_common_partial_ground_support_labels"] for row in occurrences),
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_target_execution_steps": sum(row["execution_steps"] for row in derived_episodes),
        "strict_target_execution_steps": sum(row["execution_steps"] for row in strict_episodes),
        "derived_abstract_planning_compute_events": sum(row["abstract_planning_compute_events"] for row in derived_episodes),
        "strict_abstract_planning_compute_events": sum(row["abstract_planning_compute_events"] for row in strict_episodes),
        "all_axes_separate": True,
    }
    if document["accounting"] != accounting:
        _fail("V86 accounting axes changed")
    verification_payload = {
        "schema": "acfqp.projected_disagreement_target_independent_verification.v86",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "target_occurrence_ids": [row["occurrence_id"] for row in occurrences],
        "target_occurrence_count": len(occurrences),
        "structurally_compatible_target_count": len(compatible),
        "completed_matched_target_count": len(completed),
        "failed_certificate_count_replayed": sum(len(row["failed_certificates"]) for row in (*derived_episodes, *strict_episodes)),
        "local_distinction_count_replayed": sum(len(row["local_distinctions"]) for row in (*derived_episodes, *strict_episodes)),
        "abstract_planning_compute_events_recomputed": accounting["derived_abstract_planning_compute_events"],
        "target_label_axes_recomputed": True,
        "matched_certificate_traces_replayed": True,
        "strict_ood_no_transfer_replayed": True,
        "registered_target_gate_verified": True,
        "actual_target_sample_reduction_observed": sample["actual_target_sample_reduction_observed"],
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "sample_tax_reduction_verified": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_TARGET_VERIFICATION_V86_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V86 independent verification changed")
    return result


__all__ = ("verify_projected_target_campaign_bytes_v86",)
