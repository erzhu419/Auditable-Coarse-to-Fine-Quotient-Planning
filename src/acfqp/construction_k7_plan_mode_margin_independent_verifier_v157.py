"""Producer-free verification of the frozen V157 plan-mode campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType, SimpleNamespace
import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v150 as domains_v150
from acfqp import construction_k7_domain_registry_extension_v154 as domains_v154
from acfqp import construction_k7_domain_registry_extension_v156 as domains_v156
from acfqp import construction_k7_domain_registry_extension_v157 as domains
from acfqp import construction_k7_relation_coverage_independent_verifier_v153 as v153
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp import construction_k7_structural_signature_guarded_independent_verifier_v155 as v155
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import FAMILY as POSITIVE_FAMILY, build_quaternary_relation_workflow_adapter_v153
from acfqp.generic_relation_fanout_routing_adapter_v154 import FAMILY as FALLBACK_FAMILY, build_relation_fanout_routing_adapter_v154, relation_fanout_routing_config_v154
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "51810176bf2ab9d4e51f11cf8a4f73b04bfb76bef116b8ebfce9d08f3fe1ed79"
CAMPAIGN_BYTE_COUNT = 13_671_890
CAMPAIGN_SHA256 = "8674649d85d991d8625d43104cd4a5e07fa75ccd4ffb88236e767cba11ea5284"
PREREGISTRATION_ID = "ad8bf229ddf8ac19f3364da5b5d385e125e44d878880785ee91150fa7c4ec985"
PREREGISTRATION_BYTE_COUNT = 6_862
PREREGISTRATION_SHA256 = "414cfff5081cdafcd7e79ac86ce143291df6d2aa75890b44b3387d2654c00f1f"
CORRECTION_RECEIPT_ID = "c7d45ca2ad56810103eee785d162524c65a1d53e4646b46b77e4a00d0ed5014e"
CORRECTION_RECEIPT_BYTE_COUNT = 1_372
CORRECTION_RECEIPT_SHA256 = "7bd71c91f14fece71973fe27bda76b54072ab564678ba84526baa7f9686d1364"
GUARD_RECEIPT_ID = "ce0cb66a507748cd7b6a69cd0de7a45efe1cc23c9616582fbc81ec3c27e1ab49"
GUARD_RECEIPT_BYTE_COUNT = 1_729
GUARD_RECEIPT_SHA256 = "2bf639742179fce7b0685ba95e2133064cbce7a35d4e0f06ac7b5ead34054776"
V156_CAMPAIGN_ID = "eddffbb380f9ea6e084515f622b81bce993b4e5b209bac2375417b1946dc6eb3"
V156_CAMPAIGN_BYTE_COUNT = 14_015_131
V156_CAMPAIGN_SHA256 = "15758409c83b82f2720529b5e0e80917077472bbe6664e5e2204704e3684788e"
V156_FAILURE_BYTE_COUNT = 5_207
V156_FAILURE_SHA256 = "5bd68c477d98231ddbc4bcd7361ad18f2ba1a89fc12b6ced7796da617791e881"
BANK_ID = v151.BANK_ID
BANK_VERIFICATION_ID = v151.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = tuple(
    [(POSITIVE_FAMILY, seed) for seed in range(1_047_811, 1_047_815)]
    + [(FALLBACK_FAMILY, seed) for seed in range(1_047_821, 1_047_825)]
)
EXPECTED_EPISODES = (721, 722, 723, 724)
VERIFICATION_ID = "61332d6b56b476d960915b182eff944c0a5e67a6dcf8b4782d798b0e46a6d59d"
EXPECTED_CANONICAL_BYTE_COUNT = 17_545
EXPECTED_CANONICAL_SHA256 = "fae743f81b19b45e85c5a96a1ffcf2bcbeee405e8a4651aa937169c635bcb9d4"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_V106_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"
_V156_ACQUISITION_ADDITIONS = {
    "source_v148_acquisition_id", "guard_receipt_id", "anonymous_initial_action_support_signature",
    "anonymous_relation_coverage_margin_score", "max_margin_decision_boundary", "decision_margin",
    "guard_decision", "exact_signature_registry_consulted", "boundary_or_unknown_score_defaults_to_safe_fallback",
    "guard_accessed_ground_successor_outcomes", "guard_changes_query_order_not_hypothesis_pool_or_stop_rule",
    "guard_is_model_planning_or_certificate_authority",
}
_V154_SEQUENCE_ADDITIONS = {
    "v115_memoized_compiled_program_plan_receipt_count", "v115_memoized_compiled_program_plan_receipts_consumed",
    "memoized_plan_revalidated_before_v109_execution_receipt", "memoized_plan_used_only_for_ordering",
}
_V157_SEQUENCE_ADDITIONS = {
    "source_v154_sequence_id", "applicable_plan_receipt_mode", "exactly_one_registered_plan_mode_exercised",
    "every_emitted_v115_plan_revalidated_before_v109_execution_receipt", "direct_generic_plan_path_covered_by_actual_v109_receipts",
    "all_executed_actions_have_v109_receipts", "zero_v115_receipts_not_misclassified_when_direct_generic_plan_present",
    "plan_mode_annotation_changes_planning_or_execution",
}
_V115_KEYS = v155._V115_KEYS  # noqa: SLF001


class ConstructionK7PlanModeMarginIndependentVerifierV157Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PlanModeMarginIndependentVerifierV157Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    _require(document.get(key) == _content_id(domain, {name: value for name, value in document.items() if name != key}), f"V157 {key} changed")


def _config():
    config = relation_fanout_routing_config_v154()
    config["families"][POSITIVE_FAMILY] = {"stage_count": 5, "maximum_acquisition_labels": 1_536}
    config["families"][FALLBACK_FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


def _builder(family):
    return build_quaternary_relation_workflow_adapter_v153 if family == POSITIVE_FAMILY else build_relation_fanout_routing_adapter_v154


def _signature(adapter):
    keys = tuple(adapter.action_key(action) for action in adapter.actions(adapter.initial()))
    return tuple(sorted((len({adapter.catalogue[key].fields[field] for key in keys}), len({action.fields[field] for action in adapter.catalogue})) for field in range(len(adapter.catalogue[0].fields))))


def _score(signature):
    return sum(initial == 1 and catalogue >= 3 for initial, catalogue in signature)


def _normalized_acquisition(recorded, *, expected_score):
    _verify_id(recorded, "acquisition_id", domains_v156.CONSTRUCTION_K7_ACQUISITION_V156_DOMAIN)
    expected_decision = "RELATION_COVERAGE" if expected_score > 2 else "PATH_FIRST_SAFE_FALLBACK"
    _require(
        recorded.get("schema") == "acfqp.structural_margin_guarded_acquisition_arm.v156"
        and recorded.get("guard_receipt_id") == GUARD_RECEIPT_ID
        and recorded.get("anonymous_relation_coverage_margin_score") == expected_score
        and recorded.get("max_margin_decision_boundary") == 2
        and recorded.get("decision_margin") == expected_score - 2
        and recorded.get("guard_decision") == expected_decision
        and recorded.get("exact_signature_registry_consulted") is False
        and recorded.get("boundary_or_unknown_score_defaults_to_safe_fallback") is (expected_score <= 2)
        and recorded.get("guard_accessed_ground_successor_outcomes") is False
        and recorded.get("guard_changes_query_order_not_hypothesis_pool_or_stop_rule") is True
        and recorded.get("guard_is_model_planning_or_certificate_authority") is False,
        "V157 V156 acquisition wrapper changed",
    )
    normalized = {key: copy.deepcopy(value) for key, value in recorded.items() if key not in _V156_ACQUISITION_ADDITIONS and key != "acquisition_id"}
    normalized["schema"] = "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148"
    normalized["acquisition_id"] = recorded["source_v148_acquisition_id"]
    return normalized


def _verify_v115_plan(plan):
    _require(type(plan) is dict and set(plan) == _V115_KEYS and plan.get("schema") == "acfqp.generic_projected_program_memo_plan.v115", "V157 V115 plan schema changed")
    _verify_id(plan, "legality_conditioned_quotient_plan_id", domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN)
    source = plan["source_compiled_factor_program_plan"]
    _require(
        source.get("legality_conditioned_quotient_plan_id") == hashlib.sha256(_V106_PLAN_DOMAIN + canonical_json_bytes({key: value for key, value in source.items() if key != "legality_conditioned_quotient_plan_id"})).hexdigest()
        and plan["source_compiled_factor_program_plan_id"] == source["legality_conditioned_quotient_plan_id"]
        and plan["partial_candidate_id"] == source["partial_candidate_id"]
        and plan["initial_action_key"] == source["initial_action_key"]
        and plan["projected_action_path"] == source["projected_action_path"]
        and plan["source_successor_state_id"] == plan["current_successor_state_id"]
        and plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        and plan["abstract_support_branch_evaluations"] == 0
        and plan["cached_program_ordering_used_as_safety_authority"] is False
        and plan["ground_transition_accessed_during_program_memo_reuse"] is False
        and plan["query_local_exact_overlay_remains_only_safety_authority"] is True
        and plan["complete_ground_world_model_claimed"] is False,
        "V157 V115 memo plan changed",
    )


def _v150_sequence_verifier(family):
    model_proxy = SimpleNamespace(**v151.previous.base.previous.base.model.__dict__)
    model_proxy._project = v151._project_allow_nonaccepting_novel_delta
    robust_proxy = SimpleNamespace(**v151.previous.base.previous.base.__dict__)
    robust_proxy.model = model_proxy
    v145_proxy = SimpleNamespace(**v151.previous.base.previous.__dict__)
    v145_proxy.base = robust_proxy
    base_globals = dict(v151.previous.base.__dict__)
    base_globals.update(EXPECTED_EPISODES=EXPECTED_EPISODES, FAMILY=family, previous=v145_proxy, _fail=_fail, _require=_require)
    base_verify = FunctionType(v151.previous.base._verify_sequence.__code__, base_globals, name=v151.previous.base._verify_sequence.__name__)
    sequence_globals = dict(v151.__dict__)
    sequence_globals.update(EXPECTED_EPISODES=EXPECTED_EPISODES, _BASE_VERIFY_SEQUENCE=base_verify, _fail=_fail, _require=_require)
    return FunctionType(v151._verify_sequence.__code__, sequence_globals, name=v151._verify_sequence.__name__)


def _verify_sequence(sequence, candidate, rows, *, family, seed):
    _verify_id(sequence, "sequence_id", domains.CONSTRUCTION_K7_SEQUENCE_V157_DOMAIN)
    memoized = sequence["v115_memoized_compiled_program_plan_receipt_count"]
    direct = sequence["direct_generic_factor_program_plan_count"]
    expected_mode = "V115_MEMOIZED_COMPILED_PROGRAM" if memoized > 0 and direct == 0 else "DIRECT_GENERIC_FACTOR_PROGRAM" if direct > 0 and memoized == 0 else None
    _require(
        sequence.get("schema") == "acfqp.applicable_plan_mode_sequence.v157"
        and expected_mode is not None
        and sequence.get("applicable_plan_receipt_mode") == expected_mode
        and sequence.get("exactly_one_registered_plan_mode_exercised") is True
        and sequence.get("every_emitted_v115_plan_revalidated_before_v109_execution_receipt") is True
        and sequence.get("direct_generic_plan_path_covered_by_actual_v109_receipts") is True
        and sequence.get("all_executed_actions_have_v109_receipts") is True
        and sequence.get("zero_v115_receipts_not_misclassified_when_direct_generic_plan_present") is True
        and sequence.get("plan_mode_annotation_changes_planning_or_execution") is False,
        "V157 plan-mode annotation changed",
    )
    normalized_v154 = {key: copy.deepcopy(value) for key, value in sequence.items() if key not in _V157_SEQUENCE_ADDITIONS and key != "sequence_id"}
    normalized_v154["schema"] = "acfqp.certified_memoized_planner_sequence.v154"
    normalized_v154["sequence_id"] = sequence["source_v154_sequence_id"]
    _verify_id(normalized_v154, "sequence_id", domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN)
    counted = 0
    for episode in normalized_v154["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            if wrapper["abstract_plan"].get("schema") == "acfqp.generic_projected_program_memo_plan.v115":
                _verify_v115_plan(wrapper["abstract_plan"])
                counted += 1
    _require(counted == memoized and normalized_v154["v115_memoized_compiled_program_plan_receipts_consumed"] is (memoized > 0), "V157 memo receipt inventory changed")
    normalized_v150 = {key: copy.deepcopy(value) for key, value in normalized_v154.items() if key not in _V154_SEQUENCE_ADDITIONS and key != "sequence_id"}
    normalized_v150["schema"] = "acfqp.certified_planner_abstention_sequence.v150"
    normalized_v150["sequence_id"] = _content_id(domains_v150.CONSTRUCTION_K7_SEQUENCE_V150_DOMAIN, normalized_v150)
    return _v150_sequence_verifier(family)(normalized_v150, candidate, rows, family=family, seed=seed), expected_mode


def _legacy(adapter, bank, prior, *, config, score):
    recorded = prior["legacy_path_first_prior_acquisition_summary"]
    if score <= 2:
        return {
            "ground_support_labels": prior["anonymous_relational_factor_prior_acquisition"]["ground_support_labels"],
            "first_accepting_observation_label": prior["anonymous_relational_factor_prior_acquisition"]["first_accepting_observation_label"],
            "raw_transition_sha256": prior["anonymous_relational_factor_prior_acquisition"]["raw_transition_sha256"],
            "relational_artifact_expression_selected_count": prior["anonymous_relational_factor_prior_acquisition"]["relational_artifact_expression_selected_count"],
        }
    return v153._legacy_summary(adapter, bank, target=recorded["ground_support_labels"], config=config)  # noqa: SLF001


def _verify_occurrence(args):
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require((family, seed) in EXPECTED_OCCURRENCES and row.get("schema") == "acfqp.plan_mode_margin_occurrence.v157" and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES, "V157 occurrence identity changed")
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V157_DOMAIN)
    config = _config()
    adapter = _builder(family)(seed, config)
    signature = _signature(adapter)
    score = _score(signature)
    expected_score = 3 if family == POSITIVE_FAMILY else 1
    _require(score == expected_score, "V157 anonymous margin score changed")
    prior_doc = row["anonymous_relational_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = v153._adaptive_stream(adapter) if score > 2 else v151.previous.base.previous.base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = v151.previous.base._rebuild_acquisition(_normalized_acquisition(prior_doc, expected_score=score), adapter, bank, batches, enabled=True, config=config)  # noqa: SLF001
    strict_candidate, strict_rows = v151.previous.base._rebuild_acquisition(_normalized_acquisition(strict_doc, expected_score=score), adapter, bank, batches, enabled=False, config=config)  # noqa: SLF001
    prior_sequence, prior_mode = _verify_sequence(row["anonymous_relational_factor_prior_owned_sequence"], prior_candidate, prior_rows, family=family, seed=seed)
    strict_sequence, strict_mode = _verify_sequence(row["strict_no_prior_owned_sequence"], strict_candidate, strict_rows, family=family, seed=seed)
    expected_mode = "DIRECT_GENERIC_FACTOR_PROGRAM" if family == POSITIVE_FAMILY else "V115_MEMOIZED_COMPILED_PROGRAM"
    _require(prior_mode == strict_mode == expected_mode == row["applicable_plan_receipt_mode"], "V157 occurrence plan mode changed")
    legacy = _legacy(adapter, bank, row, config=config, score=score)
    recorded_legacy = row["legacy_path_first_prior_acquisition_summary"]
    _require(legacy == {key: recorded_legacy[key] for key in legacy} and type(recorded_legacy.get("acquisition_id")) is str and len(recorded_legacy["acquisition_id"]) == 64, "V157 legacy reconstruction changed")
    ood = v155._rebuild_ood(seed + 4_000_000, config)  # noqa: SLF001
    _require(row["nonrelational_ood_control"] == ood, "V157 OOD reconstruction changed")
    guard_reduction = legacy["ground_support_labels"] - prior_doc["ground_support_labels"]
    factor_reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    accounting = {
        "anonymous_relational_prior_acquisition_labels": prior_doc["ground_support_labels"], "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_anonymous_relational_prior": factor_reduction,
        "anonymous_relational_prior_certificate_local_labels": prior_sequence["certificate_local_labels"], "strict_no_prior_certificate_local_labels": strict_sequence["certificate_local_labels"],
        "anonymous_relational_prior_lifetime_target_labels": prior_doc["ground_support_labels"] + prior_sequence["certificate_local_labels"], "strict_no_prior_lifetime_target_labels": strict_doc["ground_support_labels"] + strict_sequence["certificate_local_labels"],
        "anonymous_relational_prior_execution_steps": prior_sequence["execution_steps"], "strict_no_prior_execution_steps": strict_sequence["execution_steps"],
        "anonymous_relational_prior_derivation_compute_events": prior_doc["derivation_compute_events"], "strict_no_prior_derivation_compute_events": strict_doc["derivation_compute_events"],
        "anonymous_relational_prior_binding_compute_events": prior_doc["template_binding_evaluation_events"], "strict_no_prior_binding_compute_events": strict_doc["template_binding_evaluation_events"],
        "anonymous_relational_prior_planning_compute_events": prior_sequence["planning_compute_events"], "strict_no_prior_planning_compute_events": strict_sequence["planning_compute_events"],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True, "scalar_cost_aggregation_performed": False,
        "legacy_path_first_prior_acquisition_labels": legacy["ground_support_labels"], "labels_avoided_by_structural_margin_guard_vs_legacy_prior": guard_reduction,
        "labels_avoided_by_factor_prior_within_margin_guarded_operator": factor_reduction, "nonrelational_ood_compatibility_observation_labels": ood["observation_batch_count"],
    }
    source_sequences = (row["anonymous_relational_factor_prior_owned_sequence"], row["strict_no_prior_owned_sequence"])
    base_gate = {
        "matched_acquisition_completed_within_registered_cap": all(0 < doc["ground_support_labels"] <= 1_536 for doc in (prior_doc, strict_doc)),
        "same_raw_transition_prefix_through_common_label": True,
        "same_synthesizer_representation_and_stop_rule": all(prior_doc[key] is True and strict_doc[key] is True for key in ("binding_derived_from_current_raw_prefix_in_both_arms", "same_generic_atomic_hypothesis_pool", "same_candidate_carrier_and_schema", "same_candidate_replay_function", "same_stopping_rule_function")),
        "only_arm_switch_is_anonymous_relational_prior": prior_doc["only_arm_switch_is_anonymous_relational_prior"] is True and strict_doc["only_arm_switch_is_anonymous_relational_prior"] is True,
        "v146_source_family_absent_from_target_domain": True,
        "anonymous_relational_instantiation_present_both_arms": all(doc["anonymous_relational_instantiation"]["exact_relational_instantiation_count"] > 0 for doc in (prior_doc, strict_doc)),
        "at_least_one_bank_template_selected_in_prior_arm": prior_doc["artifact_expression_selected_count"] > 0,
        "both_arm_receding_episodes_succeed": all(episode["success"] for sequence in source_sequences for episode in sequence["episodes"]),
        "certificate_failure_only_local_ground_distinctions": all(sequence["every_new_ground_query_followed_a_failed_certificate"] for sequence in source_sequences),
        "planner_consumes_compiled_model_without_raw_rows": all(sequence["planner_consumed_compiled_successor_without_raw_transition_argument"] for sequence in source_sequences),
        "sound_certificate_local_recovery_union": all(sequence["source_partial_program_mutated_after_certificate_failure"] is False and sequence["every_uncompiled_edge_is_certificate_local"] is True and sequence["overlay_promoted_to_global_dynamics"] is False and sequence["query_local_overlay_used_as_safety_authority"] is False for sequence in source_sequences),
        "guard_receipt_frozen_before_target_outcomes": True, "exact_signature_registry_not_consulted": True,
        "anonymous_margin_decision_matches_registered_family_cohort": (prior_doc["guard_decision"] == "RELATION_COVERAGE") is (family == POSITIVE_FAMILY),
        "positive_margin_relation_coverage_noninferior": guard_reduction >= 0 if family == POSITIVE_FAMILY else True,
        "fallback_margin_selected_exact_path_first": legacy["raw_transition_sha256"] == prior_doc["raw_transition_sha256"] if family == FALLBACK_FAMILY else True,
        "guard_introduced_no_sample_regression": guard_reduction >= 0, "factor_prior_noninferior_within_same_guarded_policy": factor_reduction >= 0,
        "relation_template_selected_in_prior_arm": prior_doc["relational_artifact_expression_selected_count"] > 0, "same_relation_available_in_strict_pool": strict_doc["relational_artifact_expression_selected_count"] > 0,
        "nonrelational_ood_rejected_before_bank_access": ood["operator_transfer_rejected_before_bank_access"] and ood["factor_bank_bytes_supplied_to_ood_control"] is False,
        "v154_failed_identity_preserved": True,
        "correction_receipt_frozen_before_target_outcomes": True, "applicable_plan_receipt_path_exercised_both_arms": True,
        "registered_family_plan_mode_observed_both_arms": True, "every_emitted_v115_plan_revalidated_before_v109_receipt": True,
        "direct_generic_plan_path_covered_by_v109_receipts": True, "all_executed_actions_have_v109_receipts": True, "v156_failed_identity_preserved": True,
    }
    base_gate["passed"] = all(base_gate.values())
    _require(
        row["guard_receipt_id"] == GUARD_RECEIPT_ID and row["correction_receipt_id"] == CORRECTION_RECEIPT_ID
        and row["v146_factor_bank_id"] == BANK_ID and row["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and row["accounting"] == accounting and row["registered_gate"] == base_gate
        and row["paired_label_reduction"] == factor_reduction and row["guard_sample_reduction_vs_legacy_prior"] == guard_reduction
        and row["factor_prior_sample_reduction_within_guarded_operator"] == factor_reduction
        and row["v156_failure_preserved_not_reclassified"] is True and row["guard_is_planning_or_certificate_authority"] is False
        and row["complete_ground_world_model_synthesized"] is False and row["official_execution_allowed"] is False and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN" and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V157 occurrence evidence changed",
    )
    return {"occurrence_id": row["occurrence_id"], "family": family, "seed": seed, "score": score, "plan_mode": expected_mode, "guard_labels_avoided": guard_reduction, "factor_prior_labels_avoided": factor_reduction, "prior_sequence": prior_sequence, "strict_sequence": strict_sequence, "accounting": accounting}


def _frozen(raw, document, *, count, digest, key, identity, label):
    _require(canonical_json_bytes(document) == raw and len(raw) == count and hashlib.sha256(raw).hexdigest() == digest and document.get(key) == identity, f"V157 frozen {label} changed")


def freeze_plan_mode_margin_verification_v157(campaign_raw: bytes, preregistration_raw: bytes, guard_receipt_raw: bytes, correction_receipt_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes, v156_campaign_raw: bytes, v156_failure_raw: bytes) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    guard = loads_canonical_json(guard_receipt_raw)
    correction = loads_canonical_json(correction_receipt_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    v156_campaign = loads_canonical_json(v156_campaign_raw)
    v156_failure = loads_canonical_json(v156_failure_raw)
    _frozen(campaign_raw, campaign, count=CAMPAIGN_BYTE_COUNT, digest=CAMPAIGN_SHA256, key="campaign_id", identity=CAMPAIGN_ID, label="campaign")
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V157_DOMAIN)
    _frozen(preregistration_raw, registration, count=PREREGISTRATION_BYTE_COUNT, digest=PREREGISTRATION_SHA256, key="preregistration_id", identity=PREREGISTRATION_ID, label="preregistration")
    _verify_id(registration, "preregistration_id", domains.CONSTRUCTION_K7_PREREGISTRATION_V157_DOMAIN)
    _frozen(guard_receipt_raw, guard, count=GUARD_RECEIPT_BYTE_COUNT, digest=GUARD_RECEIPT_SHA256, key="guard_receipt_id", identity=GUARD_RECEIPT_ID, label="margin guard receipt")
    _frozen(correction_receipt_raw, correction, count=CORRECTION_RECEIPT_BYTE_COUNT, digest=CORRECTION_RECEIPT_SHA256, key="correction_receipt_id", identity=CORRECTION_RECEIPT_ID, label="correction receipt")
    _verify_id(correction, "correction_receipt_id", domains.CONSTRUCTION_K7_CORRECTION_RECEIPT_V157_DOMAIN)
    _frozen(v156_campaign_raw, v156_campaign, count=V156_CAMPAIGN_BYTE_COUNT, digest=V156_CAMPAIGN_SHA256, key="campaign_id", identity=V156_CAMPAIGN_ID, label="V156 campaign")
    _verify_id(v156_campaign, "campaign_id", domains_v156.CONSTRUCTION_K7_CAMPAIGN_V156_DOMAIN)
    _require(
        canonical_json_bytes(v156_failure) == v156_failure_raw and len(v156_failure_raw) == V156_FAILURE_BYTE_COUNT and hashlib.sha256(v156_failure_raw).hexdigest() == V156_FAILURE_SHA256
        and v156_failure["campaign_id"] == V156_CAMPAIGN_ID and v156_failure["same_identity_rerun_forbidden"] is True
        and correction["failed_v156_campaign_id"] == V156_CAMPAIGN_ID and correction["failed_v156_record_sha256"] == V156_FAILURE_SHA256
        and correction["observed_direct_generic_occurrence_count"] == 4 and correction["observed_v115_memoized_occurrence_count"] == 4
        and all(correction["corrected_registered_invariant"].values()) and correction["fresh_v157_target_outcomes_accessed"] is False
        and correction["v156_failed_identity_preserved"] is True,
        "V157 corrected failure evidence changed",
    )
    _require(
        canonical_json_bytes(bank) == bank_raw and bank.get("bank_id") == BANK_ID and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw and bank_verification.get("verification_id") == BANK_VERIFICATION_ID and len(bank_verification_raw) == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT and hashlib.sha256(bank_verification_raw).hexdigest() == v151.previous.base.BANK_VERIFICATION_SHA256,
        "V157 frozen factor bank changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(len(raw) == fact["byte_count"] and hashlib.sha256(raw).hexdigest() == fact["sha256"], "V157 source closure changed")
    _require(
        registration["frozen_guard_receipt"] == guard and registration["frozen_correction_receipt"] == correction
        and registration["target_occurrences"] == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 8 and registration["maximum_acquisition_labels"] == 1_536
        and all(registration["registered_gate"].values()) and registration["claim_boundary"]["target_outcomes_accessed"] is False
        and registration["claim_boundary"]["v156_failure_reclassified"] is False and registration["claim_boundary"]["official_scalar_cost"] is None,
        "V157 registered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(executor.map(_verify_occurrence, ((row, bank) for row in campaign["target_occurrences"])))
    _require(tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows], "V157 occurrence inventory changed")
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(sample_labels_execution_steps_derivation_and_planning_compute_separate=True, scalar_cost_aggregation_performed=False)
    factors = tuple(row["factor_prior_labels_avoided"] for row in rows)
    guards = tuple(row["guard_labels_avoided"] for row in rows)
    positive_rows = tuple(row for row in rows if row["family"] == POSITIVE_FAMILY)
    fallback_rows = tuple(row for row in rows if row["family"] == FALLBACK_FAMILY)
    family_reductions = {family: sum(row["factor_prior_labels_avoided"] for row in rows if row["family"] == family) for family in (POSITIVE_FAMILY, FALLBACK_FAMILY)}
    local_labels = accounting["anonymous_relational_prior_certificate_local_labels"] + accounting["strict_no_prior_certificate_local_labels"]
    gate = {
        "required_target_occurrence_count": 8, "passed_target_occurrence_count": 8, "required_target_family_count": 2, "observed_target_family_count": 2,
        "aggregate_paired_acquisition_label_reduction": sum(factors), "aggregate_positive_label_reduction": sum(factors) > 0,
        "positive_reduction_occurrence_count": sum(value > 0 for value in factors), "zero_reduction_occurrence_count": sum(value == 0 for value in factors), "negative_reduction_occurrence_count": sum(value < 0 for value in factors),
        "family_aggregate_reductions": family_reductions, "every_family_has_positive_aggregate_reduction": all(value > 0 for value in family_reductions.values()),
        "same_synthesizer_and_stop_rule_everywhere": all(row["registered_gate"]["same_synthesizer_representation_and_stop_rule"] for row in campaign["target_occurrences"]),
        "anonymous_relational_instantiation_present_everywhere": all(row["registered_gate"]["anonymous_relational_instantiation_present_both_arms"] for row in campaign["target_occurrences"]),
        "both_arm_receding_episodes_succeed_everywhere": all(row["registered_gate"]["both_arm_receding_episodes_succeed"] for row in campaign["target_occurrences"]),
        "certificate_failure_local_recovery_exercised_at_least_once": local_labels > 0, "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()["strict_ood_no_transfer"],
    }
    gate["passed"] = all((len(rows) == 8, gate["aggregate_positive_label_reduction"], gate["every_family_has_positive_aggregate_reduction"], gate["same_synthesizer_and_stop_rule_everywhere"], gate["anonymous_relational_instantiation_present_everywhere"], gate["both_arm_receding_episodes_succeed_everywhere"], gate["certificate_failure_local_recovery_exercised_at_least_once"], gate["strict_incompatible_schema_no_transfer_verified"]))
    gate.update(
        guard_receipt_id=GUARD_RECEIPT_ID, correction_receipt_id=CORRECTION_RECEIPT_ID,
        aggregate_guard_sample_reduction_vs_legacy_prior=sum(guards), positive_margin_cohort_guard_reduction=sum(row["guard_labels_avoided"] for row in positive_rows), fallback_margin_cohort_guard_reduction=sum(row["guard_labels_avoided"] for row in fallback_rows), aggregate_factor_prior_reduction_within_guarded_operator=sum(factors),
        positive_margin_relation_coverage_positive_in_aggregate=sum(row["guard_labels_avoided"] for row in positive_rows) > 0,
        fallback_margin_zero_regression_everywhere=all(row["guard_labels_avoided"] == 0 for row in fallback_rows), guard_noninferior_everywhere=all(value >= 0 for value in guards), factor_prior_noninferior_everywhere=all(value >= 0 for value in factors), factor_prior_positive_in_aggregate=sum(factors) > 0,
        both_margin_sides_observed=bool(positive_rows) and bool(fallback_rows), exact_signature_registry_absent_everywhere=True, applicable_plan_receipt_path_exercised_everywhere=True,
        both_registered_plan_modes_observed={row["plan_mode"] for row in rows} == {"DIRECT_GENERIC_FACTOR_PROGRAM", "V115_MEMOIZED_COMPILED_PROGRAM"}, nonrelational_ood_rejected_everywhere=True, v156_failed_identity_preserved=True,
    )
    gate["passed"] = gate["passed"] and all(gate[key] for key in ("positive_margin_relation_coverage_positive_in_aggregate", "fallback_margin_zero_regression_everywhere", "guard_noninferior_everywhere", "factor_prior_noninferior_everywhere", "factor_prior_positive_in_aggregate", "both_margin_sides_observed", "exact_signature_registry_absent_everywhere", "applicable_plan_receipt_path_exercised_everywhere", "both_registered_plan_modes_observed", "nonrelational_ood_rejected_everywhere"))
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID and campaign["guard_receipt_id"] == GUARD_RECEIPT_ID and campaign["correction_receipt_id"] == CORRECTION_RECEIPT_ID
        and campaign["v146_factor_bank_id"] == BANK_ID and campaign["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and campaign["incompatible_schema_no_transfer_control"] == incompatible_schema_no_transfer_control_v99() and campaign["accounting"] == accounting and campaign["registered_gate"] == gate
        and gate["passed"] is True and sum(guards) == 383 and sum(factors) == 20
        and campaign["plan_mode_corrected_structural_margin_evidence_observed"] is True and campaign["v156_failure_preserved_not_reclassified"] is True
        and campaign["sample_tax_reduction_claim_scope"] == "ONLY_THE_PREREGISTERED_V157_TWO_FAMILY_PLAN_MODE_COHORT" and campaign["guard_is_model_planning_or_certificate_authority"] is False
        and campaign["complete_ground_world_model_synthesized"] is False and campaign["complete_world_model_synthesized"] is False and campaign["official_execution_allowed"] is False and campaign["official_scalar_cost"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN" and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V157 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.plan_mode_margin_verification.v157", "campaign_id": CAMPAIGN_ID, "preregistration_id": PREREGISTRATION_ID,
        "guard_receipt_id": GUARD_RECEIPT_ID, "correction_receipt_id": CORRECTION_RECEIPT_ID, "preserved_v156_failed_campaign_id": V156_CAMPAIGN_ID, "preserved_v156_failure_sha256": V156_FAILURE_SHA256,
        "v146_factor_bank_id": BANK_ID, "v146_independent_verification_id": BANK_VERIFICATION_ID, "verified_occurrences": list(rows), "verified_accounting": accounting,
        "producer_free_anonymous_margin_score_and_query_policy_reconstruction": True, "producer_free_prior_strict_and_legacy_acquisition_reconstruction": True,
        "producer_free_applicable_direct_and_memoized_plan_mode_reconstruction": True, "producer_free_v115_and_v109_receipt_chain_reconstruction": True,
        "producer_free_abstract_planning_certificate_recovery_and_ood_reconstruction": True, "registered_plan_mode_corrected_margin_evidence_independently_verified": True,
        "guard_sample_reduction_vs_legacy_prior": sum(guards), "factor_prior_sample_reduction_within_guarded_operator": sum(factors),
        "sample_tax_reduction_claim_scope": campaign["sample_tax_reduction_claim_scope"], "guard_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False, "arbitrary_unseen_domain_transfer_claimed": False, "official_execution_allowed": False, "official_scalar_cost": None, "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": _content_id(domains.CONSTRUCTION_K7_VERIFICATION_V157_DOMAIN, payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(document["verification_id"] == VERIFICATION_ID and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256, "V157 frozen verification changed")
    return raw


__all__ = ("VERIFICATION_ID", "freeze_plan_mode_margin_verification_v157")
