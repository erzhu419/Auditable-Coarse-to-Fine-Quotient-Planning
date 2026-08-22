"""Producer-free verification of the frozen V155 guarded campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType, SimpleNamespace
import copy
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v150 as domains_v150
from acfqp import construction_k7_domain_registry_extension_v154 as domains_v154
from acfqp import construction_k7_domain_registry_extension_v155 as domains
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY,
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "8e624c5e4fc054956e9c624d8612c016f91daf46a6d9991e07074b60ca2c4780"
CAMPAIGN_BYTE_COUNT = 8_411_353
CAMPAIGN_SHA256 = "2a0fba2417762da1c3e52357e4da484d93e798c4214d28366e9fef7c9e4ee08d"
PREREGISTRATION_ID = "4799e536dab144b074b7f865144247cd20f1dcd17c0e8ccfa117f1168a58386f"
PREREGISTRATION_BYTE_COUNT = 5_142
PREREGISTRATION_SHA256 = "cce7d3df166005eabed9a8cdc1a2d546cee34200f2db84c7c40d31f42d70d2b0"
GUARD_RECEIPT_ID = "61394b986763ef65e12cd21a15940fe01c61bbca3e403c669c39cf8a8ebb6871"
GUARD_RECEIPT_BYTE_COUNT = 1_746
GUARD_RECEIPT_SHA256 = "15a0ef806ccb819c4123d6d9d85a3ed33707ffcfdbf1d344b283a6decea6c0e2"
V153_CAMPAIGN_ID = "47028757be59d7b6617d01411d5e0b580944df931ecb82bcdcea27f98fccee27"
V153_CAMPAIGN_BYTE_COUNT = 7_167_903
V153_CAMPAIGN_SHA256 = "b85a19614111542a7cb1cd150019c7bf6775e15fc2cd4a8f6d2e8ec7c6c4f61d"
V153_VERIFICATION_ID = "edeec1a912c6ff4da374490fd53a1ab8eb84d0d70ef4492f8d00b367f51128ef"
V153_VERIFICATION_BYTE_COUNT = 10_351
V153_VERIFICATION_SHA256 = "ccc9b46543e592d238a79cefbd8f7241631f8771bf297580cd265af291628c18"
V154_CAMPAIGN_ID = "b6ecf976d4261f8753f9653d9b0aaa3c2c75c618ecae21d3602ae0a81f9b71f1"
V154_CAMPAIGN_BYTE_COUNT = 4_129_436
V154_CAMPAIGN_SHA256 = "9d4147d843f0f6c59c2e8efad6d917e25bbecd6563359ab785ed08c6915b3ef7"
V154_FAILURE_BYTE_COUNT = 3_309
V154_FAILURE_SHA256 = "7bb3f3cfb23ed848b6e5bd4e15ebe3a067fcdcfb2aa34cc6e903109dbd384894"
BANK_ID = v151.BANK_ID
BANK_VERIFICATION_ID = v151.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_611, 1_047_615))
EXPECTED_EPISODES = (681, 682, 683, 684)
EXPECTED_SIGNATURE = ((1, 4), (2, 2), (2, 2), (2, 4), (4, 4), (4, 16))
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_V106_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"
_V154_SEQUENCE_ADDITIONS = {
    "v115_memoized_compiled_program_plan_receipt_count",
    "v115_memoized_compiled_program_plan_receipts_consumed",
    "memoized_plan_revalidated_before_v109_execution_receipt",
    "memoized_plan_used_only_for_ordering",
}
_V155_ACQUISITION_ADDITIONS = {
    "source_v148_acquisition_id",
    "guard_receipt_id",
    "anonymous_initial_action_support_signature",
    "guard_decision",
    "positive_signature_match",
    "failed_signature_match",
    "unknown_signature_defaults_to_safe_fallback",
    "guard_accessed_ground_successor_outcomes",
    "guard_changes_query_order_not_hypothesis_pool_or_stop_rule",
    "guard_is_model_planning_or_certificate_authority",
}
_V115_KEYS = {
    "abstract_support_branch_evaluations", "agreement_shield_receipt", "cache_reused_only_under_identical_compiled_successor_state",
    "cached_program_ordering_used_as_safety_authority", "complete_ground_world_model_claimed", "current_successor_state_id",
    "exact_legal_action_keys_at_initial_state", "ground_legality_used_only_after_existing_support_or_failed_certificate",
    "ground_transition_accessed_during_program_memo_reuse", "initial_action_key", "initial_illegal_actions_forbidden_in_reused_order",
    "legality_conditioned_quotient_plan_id", "legality_failure_index", "legality_support_source", "partial_candidate_id", "planning_source",
    "projected_action_path", "projected_state_and_exact_legal_set_cache_keyed", "query_local_exact_overlay_remains_only_safety_authority",
    "quotient_graph_id", "schema", "source_compiled_factor_program_plan", "source_compiled_factor_program_plan_id",
    "source_successor_state_id", "terminal_projection_rule_sha256",
}


class ConstructionK7StructuralSignatureGuardedIndependentVerifierV155Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralSignatureGuardedIndependentVerifierV155Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    _require(document.get(key) == _content_id(domain, {name: value for name, value in document.items() if name != key}), f"V155 {key} changed")


def _campaign_config():
    config = relation_fanout_routing_config_v154()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


def _signature(adapter):
    keys = tuple(adapter.action_key(action) for action in adapter.actions(adapter.initial()))
    return tuple(sorted((len({adapter.catalogue[key].fields[field] for key in keys}), len({action.fields[field] for action in adapter.catalogue})) for field in range(len(adapter.catalogue[0].fields))))


def _normalized_acquisition(recorded):
    _verify_id(recorded, "acquisition_id", domains.CONSTRUCTION_K7_ACQUISITION_V155_DOMAIN)
    _require(
        recorded.get("schema") == "acfqp.structural_signature_guarded_acquisition_arm.v155"
        and recorded.get("guard_receipt_id") == GUARD_RECEIPT_ID
        and tuple(tuple(pair) for pair in recorded.get("anonymous_initial_action_support_signature", ())) == EXPECTED_SIGNATURE
        and recorded.get("guard_decision") == "PATH_FIRST_SAFE_FALLBACK"
        and recorded.get("positive_signature_match") is False
        and recorded.get("failed_signature_match") is True
        and recorded.get("unknown_signature_defaults_to_safe_fallback") is False
        and recorded.get("guard_accessed_ground_successor_outcomes") is False
        and recorded.get("guard_changes_query_order_not_hypothesis_pool_or_stop_rule") is True
        and recorded.get("guard_is_model_planning_or_certificate_authority") is False,
        "V155 guarded acquisition boundary changed",
    )
    normalized = {key: copy.deepcopy(value) for key, value in recorded.items() if key not in _V155_ACQUISITION_ADDITIONS and key != "acquisition_id"}
    normalized["schema"] = "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148"
    normalized["acquisition_id"] = recorded["source_v148_acquisition_id"]
    return normalized


_MODEL_PROXY = SimpleNamespace(**v151.previous.base.previous.base.model.__dict__)
_MODEL_PROXY._project = v151._project_allow_nonaccepting_novel_delta
_ROBUST_BASE_PROXY = SimpleNamespace(**v151.previous.base.previous.base.__dict__)
_ROBUST_BASE_PROXY.model = _MODEL_PROXY
_V145_PROXY = SimpleNamespace(**v151.previous.base.previous.__dict__)
_V145_PROXY.base = _ROBUST_BASE_PROXY
_BASE_SEQUENCE_GLOBALS = dict(v151.previous.base.__dict__)
_BASE_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, FAMILY=FAMILY, previous=_V145_PROXY, _fail=_fail, _require=_require)
_BASE_VERIFY_SEQUENCE = FunctionType(v151.previous.base._verify_sequence.__code__, _BASE_SEQUENCE_GLOBALS, name=v151.previous.base._verify_sequence.__name__)
_SEQUENCE_GLOBALS = dict(v151.__dict__)
_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, _BASE_VERIFY_SEQUENCE=_BASE_VERIFY_SEQUENCE, _fail=_fail, _require=_require)
_VERIFY_V150_SEQUENCE = FunctionType(v151._verify_sequence.__code__, _SEQUENCE_GLOBALS, name=v151._verify_sequence.__name__)


def _verify_v115_plan(plan):
    _require(type(plan) is dict and set(plan) == _V115_KEYS and plan.get("schema") == "acfqp.generic_projected_program_memo_plan.v115", "V155 V115 plan schema changed")
    _verify_id(plan, "legality_conditioned_quotient_plan_id", domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN)
    source = plan["source_compiled_factor_program_plan"]
    source_payload = {key: value for key, value in source.items() if key != "legality_conditioned_quotient_plan_id"}
    _require(
        source.get("schema") == "acfqp.generic_legality_conditioned_quotient_plan.v106"
        and source.get("legality_conditioned_quotient_plan_id") == hashlib.sha256(_V106_PLAN_DOMAIN + canonical_json_bytes(source_payload)).hexdigest()
        and plan["source_compiled_factor_program_plan_id"] == source["legality_conditioned_quotient_plan_id"]
        and plan["partial_candidate_id"] == source["partial_candidate_id"]
        and plan["initial_action_key"] == source["initial_action_key"]
        and plan["projected_action_path"] == source["projected_action_path"]
        and plan["source_successor_state_id"] == plan["current_successor_state_id"]
        and plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        and plan["abstract_support_branch_evaluations"] == 0
        and plan["initial_action_key"] in plan["exact_legal_action_keys_at_initial_state"]
        and plan["projected_state_and_exact_legal_set_cache_keyed"] is True
        and plan["cache_reused_only_under_identical_compiled_successor_state"] is True
        and plan["initial_illegal_actions_forbidden_in_reused_order"] is True
        and plan["ground_legality_used_only_after_existing_support_or_failed_certificate"] is True
        and plan["cached_program_ordering_used_as_safety_authority"] is False
        and plan["ground_transition_accessed_during_program_memo_reuse"] is False
        and plan["query_local_exact_overlay_remains_only_safety_authority"] is True
        and plan["complete_ground_world_model_claimed"] is False,
        "V155 V115 memo plan semantics changed",
    )


def _verify_sequence(sequence, candidate, rows, *, family, seed):
    _verify_id(sequence, "sequence_id", domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN)
    memoized = 0
    for episode in sequence["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            if wrapper["abstract_plan"].get("schema") == "acfqp.generic_projected_program_memo_plan.v115":
                _verify_v115_plan(wrapper["abstract_plan"])
                memoized += 1
    _require(
        sequence.get("schema") == "acfqp.certified_memoized_planner_sequence.v154"
        and sequence.get("family") == family
        and tuple(sequence.get("episode_indices", ())) == EXPECTED_EPISODES
        and sequence.get("v115_memoized_compiled_program_plan_receipt_count") == memoized
        and sequence.get("v115_memoized_compiled_program_plan_receipts_consumed") is (memoized > 0)
        and sequence.get("memoized_plan_revalidated_before_v109_execution_receipt") is True
        and sequence.get("memoized_plan_used_only_for_ordering") is True,
        "V155 V154 sequence boundary changed",
    )
    normalized = {key: copy.deepcopy(value) for key, value in sequence.items() if key not in _V154_SEQUENCE_ADDITIONS and key != "sequence_id"}
    normalized["schema"] = "acfqp.certified_planner_abstention_sequence.v150"
    normalized["sequence_id"] = _content_id(domains_v150.CONSTRUCTION_K7_SEQUENCE_V150_DOMAIN, normalized)
    return _VERIFY_V150_SEQUENCE(normalized, candidate, rows, family=family, seed=seed)


def _has_positive_initial_relation(adapter, observations) -> bool:
    """Independently replay the anonymous V153 initial-relation predicate."""

    for field in range(len(adapter.catalogue[0].fields)):
        for coordinate in range(len(observations[0][1][0].pre)):
            relation = {}
            valid = True
            for key, batch in observations:
                value = adapter.catalogue[key].fields[field]
                deltas = {row.post[coordinate] - row.pre[coordinate] for row in batch}
                if len(deltas) != 1 or (value in relation and relation[value] != next(iter(deltas))):
                    valid = False
                    break
                relation[value] = next(iter(deltas))
            values = tuple(relation.values())
            if (
                valid
                and len(relation) == len(observations)
                and set(relation) == {action.fields[field] for action in adapter.catalogue}
                and len(set(values)) == len(values)
                and min(values) > 0
            ):
                return True
    return False


def _rebuild_ood(seed: int, config: Mapping[str, Any]) -> dict[str, Any]:
    adapter = build_relation_fanout_routing_adapter_v154(seed, config, incompatible=True)
    initial = adapter.initial()
    observations = []
    batches = []
    transition_index = 0
    for action in adapter.actions(initial):
        key = adapter.action_key(action)
        batch = ground._transition_batch(adapter, initial, key, transition_index)  # noqa: SLF001
        transition_index += len(batch)
        observations.append((key, batch))
        batches.append(batch)
    _require(not _has_positive_initial_relation(adapter, observations), "V155 OOD relation rejection changed")
    rows = tuple(row for batch in batches for row in batch)
    documents = [row.to_document() for row in rows]
    payload = {
        "schema": "acfqp.nonrelational_ood_control.v154",
        "family": adapter.family,
        "seed": seed,
        "observation_batch_count": len(batches),
        "raw_transition_count": len(rows),
        "raw_transition_documents": documents,
        "raw_transition_sha256": hashlib.sha256(canonical_json_bytes(documents)).hexdigest(),
        "relation_discovery_error": "V153 raw initial observations exposed no positive relation coverage",
        "no_exact_positive_one_to_one_descriptor_delta_relation": True,
        "factor_bank_bytes_supplied_to_ood_control": False,
        "factor_prior_instantiation_attempted": False,
        "operator_transfer_rejected_before_bank_access": True,
        "ground_observations_used_only_for_ood_compatibility_check": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
    }
    _require(len(batches) == 4 and len(rows) == 8, "V155 OOD observation inventory changed")
    return {**payload, "ood_control_id": _content_id(domains_v154.CONSTRUCTION_K7_OOD_CONTROL_V154_DOMAIN, payload)}


def _verify_occurrence(args: tuple[Mapping[str, Any], Mapping[str, Any]]) -> dict[str, Any]:
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema") == "acfqp.structural_signature_guarded_occurrence.v155"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V155 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V155_DOMAIN)
    config = _campaign_config()
    adapter = build_relation_fanout_routing_adapter_v154(seed, config)
    _require(_signature(adapter) == EXPECTED_SIGNATURE, "V155 structural signature reconstruction changed")
    prior_doc = row["anonymous_relational_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = v151.previous.base.previous.base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(prior_doc), adapter, bank, batches, enabled=True, config=config
    )
    strict_candidate, strict_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(strict_doc), adapter, bank, batches, enabled=False, config=config
    )
    prior_sequence = _verify_sequence(
        row["anonymous_relational_factor_prior_owned_sequence"], prior_candidate, prior_rows, family=family, seed=seed
    )
    strict_sequence = _verify_sequence(
        row["strict_no_prior_owned_sequence"], strict_candidate, strict_rows, family=family, seed=seed
    )
    legacy = row["legacy_path_first_prior_acquisition_summary"]
    expected_legacy = {
        "acquisition_id": prior_doc["source_v148_acquisition_id"],
        "ground_support_labels": prior_doc["ground_support_labels"],
        "first_accepting_observation_label": prior_doc["first_accepting_observation_label"],
        "raw_transition_sha256": prior_doc["raw_transition_sha256"],
        "relational_artifact_expression_selected_count": prior_doc["relational_artifact_expression_selected_count"],
    }
    _require(legacy == expected_legacy, "V155 exact path-first fallback changed")
    ood = _rebuild_ood(seed + 3_000_000, config)
    _require(row["nonrelational_ood_control"] == ood, "V155 OOD control reconstruction changed")
    guard_reduction = legacy["ground_support_labels"] - prior_doc["ground_support_labels"]
    factor_reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    expected_accounting = {
        "anonymous_relational_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_anonymous_relational_prior": factor_reduction,
        "anonymous_relational_prior_certificate_local_labels": prior_sequence["certificate_local_labels"],
        "strict_no_prior_certificate_local_labels": strict_sequence["certificate_local_labels"],
        "anonymous_relational_prior_lifetime_target_labels": prior_doc["ground_support_labels"] + prior_sequence["certificate_local_labels"],
        "strict_no_prior_lifetime_target_labels": strict_doc["ground_support_labels"] + strict_sequence["certificate_local_labels"],
        "anonymous_relational_prior_execution_steps": prior_sequence["execution_steps"],
        "strict_no_prior_execution_steps": strict_sequence["execution_steps"],
        "anonymous_relational_prior_derivation_compute_events": prior_doc["derivation_compute_events"],
        "strict_no_prior_derivation_compute_events": strict_doc["derivation_compute_events"],
        "anonymous_relational_prior_binding_compute_events": prior_doc["template_binding_evaluation_events"],
        "strict_no_prior_binding_compute_events": strict_doc["template_binding_evaluation_events"],
        "anonymous_relational_prior_planning_compute_events": prior_sequence["planning_compute_events"],
        "strict_no_prior_planning_compute_events": strict_sequence["planning_compute_events"],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
        "legacy_path_first_prior_acquisition_labels": legacy["ground_support_labels"],
        "labels_avoided_by_structural_guard_vs_legacy_prior": guard_reduction,
        "labels_avoided_by_factor_prior_within_guarded_operator": factor_reduction,
        "nonrelational_ood_compatibility_observation_labels": ood["observation_batch_count"],
    }
    sequences = (
        row["anonymous_relational_factor_prior_owned_sequence"],
        row["strict_no_prior_owned_sequence"],
    )
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(0 < doc["ground_support_labels"] <= 1_536 for doc in (prior_doc, strict_doc)),
        # Both reconstructions above consume prefixes of this one independently
        # generated path-first batch stream.
        "same_raw_transition_prefix_through_common_label": True,
        "same_synthesizer_representation_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "binding_derived_from_current_raw_prefix_in_both_arms",
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "only_arm_switch_is_anonymous_relational_prior": prior_doc["only_arm_switch_is_anonymous_relational_prior"] is True and strict_doc["only_arm_switch_is_anonymous_relational_prior"] is True,
        "v146_source_family_absent_from_target_domain": True,
        "anonymous_relational_instantiation_present_both_arms": all(doc["anonymous_relational_instantiation"]["exact_relational_instantiation_count"] > 0 for doc in (prior_doc, strict_doc)),
        "at_least_one_bank_template_selected_in_prior_arm": prior_doc["artifact_expression_selected_count"] > 0,
        "both_arm_receding_episodes_succeed": all(episode["success"] for sequence in sequences for episode in sequence["episodes"]),
        "certificate_failure_only_local_ground_distinctions": all(sequence["every_new_ground_query_followed_a_failed_certificate"] for sequence in sequences),
        "planner_consumes_compiled_model_without_raw_rows": all(sequence["planner_consumed_compiled_successor_without_raw_transition_argument"] for sequence in sequences),
        "sound_certificate_local_recovery_union": all(
            sequence["source_partial_program_mutated_after_certificate_failure"] is False
            and sequence["every_uncompiled_edge_is_certificate_local"] is True
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in sequences
        ),
        "guard_receipt_frozen_before_target_outcomes": True,
        "failed_structural_signature_selected_exact_path_first_fallback": legacy == expected_legacy,
        "guard_introduced_no_sample_regression": guard_reduction == 0,
        "factor_prior_noninferior_within_same_guarded_policy": factor_reduction >= 0,
        "relation_template_selected_in_prior_arm": prior_doc["relational_artifact_expression_selected_count"] > 0,
        "same_relation_available_in_strict_pool": strict_doc["relational_artifact_expression_selected_count"] > 0,
        "v115_memoized_plan_receipt_consumed_both_arms": all(sequence["v115_memoized_compiled_program_plan_receipts_consumed"] for sequence in sequences),
        "nonrelational_ood_rejected_before_bank_access": ood["operator_transfer_rejected_before_bank_access"] and ood["factor_bank_bytes_supplied_to_ood_control"] is False,
        "v154_failed_identity_preserved": True,
    }
    gate["passed"] = all(gate.values())
    _require(
        row["guard_receipt_id"] == GUARD_RECEIPT_ID
        and row["v146_factor_bank_id"] == BANK_ID
        and row["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and row["accounting"] == expected_accounting
        and row["registered_gate"] == gate
        and row["paired_label_reduction"] == factor_reduction
        and row["sample_efficiency_direction"] == ("POSITIVE" if factor_reduction > 0 else "NEGATIVE" if factor_reduction < 0 else "ZERO")
        and row["registered_workload_sample_efficiency_improvement_observed"] is (factor_reduction > 0)
        and row["relational_instantiation_present_but_relational_template_selection_not_required"] is True
        and row["guard_sample_reduction_vs_legacy_prior"] == guard_reduction
        and row["factor_prior_sample_reduction_within_guarded_operator"] == factor_reduction
        and row["sample_tax_guard_claim_scope"] == "ONLY_REGISTERED_ANONYMOUS_STRUCTURAL_SIGNATURES_WITH_UNKNOWN_SAFE_FALLBACK"
        and row["guard_is_planning_or_certificate_authority"] is False
        and row["v153_success_and_v154_failure_preserved"] is True
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["official_N_break_even"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V155 occurrence evidence changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "guard_decision": prior_doc["guard_decision"],
        "structural_signature": [list(pair) for pair in EXPECTED_SIGNATURE],
        "prior_labels": prior_doc["ground_support_labels"],
        "strict_labels": strict_doc["ground_support_labels"],
        "guard_labels_avoided": guard_reduction,
        "factor_prior_labels_avoided": factor_reduction,
        "memoized_plan_receipt_count": sum(sequence["v115_memoized_compiled_program_plan_receipt_count"] for sequence in sequences),
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": expected_accounting,
    }


def _verify_frozen_bytes(raw: bytes, document: Mapping[str, Any], *, count: int, digest: str, key: str, identity: str, label: str) -> None:
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V155 frozen {label} identity changed",
    )


def _expected_guard_receipt() -> dict[str, Any]:
    positive = (
        ((1, 4), (1, 4), (1, 4), (2, 3), (4, 4), (4, 16)),
        ((1, 4), (1, 4), (1, 4), (3, 3), (4, 4), (4, 16)),
    )
    payload = {
        "schema": "acfqp.structural_signature_query_guard_receipt.v155",
        "positive_source_campaign_id": V153_CAMPAIGN_ID,
        "positive_source_verification_id": V153_VERIFICATION_ID,
        "failed_source_campaign_id": V154_CAMPAIGN_ID,
        "failed_source_record_sha256": V154_FAILURE_SHA256,
        "positive_source_operator_sample_reduction": 345,
        "failed_source_operator_sample_reduction": -8,
        "signature_schema": "SORTED_PER_ANONYMOUS_FIELD_PAIR_OF_INITIAL_LEGAL_SUPPORT_CARDINALITY_AND_FULL_CATALOGUE_SUPPORT_CARDINALITY",
        "positive_relation_coverage_signatures": [[list(pair) for pair in signature] for signature in positive],
        "path_first_fallback_signatures": [[list(pair) for pair in EXPECTED_SIGNATURE]],
        "selection_rule": {
            "exact_positive_signature": "V153_RELATION_COVERAGE_THEN_DEDUPLICATED_PATH_BACKTRACKING",
            "exact_failed_or_unknown_signature": "WITNESS_BLIND_PATH_FIRST_BACKTRACKING",
            "signature_uses_action_metadata_and_initial_legality_only": True,
            "ground_successor_outcomes_accessed_by_guard": False,
            "semantic_names_used": False,
            "unknown_signature_defaults_to_safe_fallback": True,
        },
        "guard_frozen_before_v155_target_outcomes": True,
        "guard_is_query_order_meta_prior_not_model_or_certificate_authority": True,
        "v154_failed_identity_preserved": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "guard_receipt_id": _content_id(domains.CONSTRUCTION_K7_GUARD_RECEIPT_V155_DOMAIN, payload)}


def freeze_structural_signature_guarded_verification_v155(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    guard_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v153_campaign_raw: bytes,
    v153_verification_raw: bytes,
    v154_campaign_raw: bytes,
    v154_failure_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    guard = loads_canonical_json(guard_receipt_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    v153_campaign = loads_canonical_json(v153_campaign_raw)
    v153_verification = loads_canonical_json(v153_verification_raw)
    v154_campaign = loads_canonical_json(v154_campaign_raw)
    v154_failure = loads_canonical_json(v154_failure_raw)

    _verify_frozen_bytes(
        campaign_raw, campaign, count=CAMPAIGN_BYTE_COUNT, digest=CAMPAIGN_SHA256,
        key="campaign_id", identity=CAMPAIGN_ID, label="campaign",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V155_DOMAIN)
    _verify_frozen_bytes(
        preregistration_raw, registration, count=PREREGISTRATION_BYTE_COUNT, digest=PREREGISTRATION_SHA256,
        key="preregistration_id", identity=PREREGISTRATION_ID, label="preregistration",
    )
    _verify_id(registration, "preregistration_id", domains.CONSTRUCTION_K7_PREREGISTRATION_V155_DOMAIN)
    _verify_frozen_bytes(
        guard_receipt_raw, guard, count=GUARD_RECEIPT_BYTE_COUNT, digest=GUARD_RECEIPT_SHA256,
        key="guard_receipt_id", identity=GUARD_RECEIPT_ID, label="guard receipt",
    )
    _require(guard == _expected_guard_receipt(), "V155 independently reconstructed guard receipt changed")
    _verify_frozen_bytes(
        v153_campaign_raw, v153_campaign, count=V153_CAMPAIGN_BYTE_COUNT, digest=V153_CAMPAIGN_SHA256,
        key="campaign_id", identity=V153_CAMPAIGN_ID, label="V153 campaign",
    )
    _verify_frozen_bytes(
        v153_verification_raw, v153_verification, count=V153_VERIFICATION_BYTE_COUNT, digest=V153_VERIFICATION_SHA256,
        key="verification_id", identity=V153_VERIFICATION_ID, label="V153 verification",
    )
    _verify_frozen_bytes(
        v154_campaign_raw, v154_campaign, count=V154_CAMPAIGN_BYTE_COUNT, digest=V154_CAMPAIGN_SHA256,
        key="campaign_id", identity=V154_CAMPAIGN_ID, label="V154 failed campaign",
    )
    _verify_id(v154_campaign, "campaign_id", domains_v154.CONSTRUCTION_K7_CAMPAIGN_V154_DOMAIN)
    _require(
        canonical_json_bytes(v154_failure) == v154_failure_raw
        and len(v154_failure_raw) == V154_FAILURE_BYTE_COUNT
        and hashlib.sha256(v154_failure_raw).hexdigest() == V154_FAILURE_SHA256
        and v153_campaign["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] == 345
        and v153_verification["registered_operator_sample_tax_reduction_independently_verified"] is True
        and v153_verification["campaign_id"] == V153_CAMPAIGN_ID
        and v154_campaign["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] == -8
        and v154_campaign["registered_gate"]["passed"] is False
        and v154_failure["campaign_id"] == V154_CAMPAIGN_ID
        and v154_failure["campaign_sha256"] == V154_CAMPAIGN_SHA256
        and v154_failure["same_identity_rerun_forbidden"] is True
        and v154_failure["fresh_successor_identity_required_for_any_correction"] is True
        and sum(row["operator_sample_reduction_vs_legacy_prior"] for row in v154_failure["per_occurrence_reductions"]) == -8,
        "V155 positive-success or preserved-failure evidence changed",
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == BANK_ID
        and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id") == BANK_VERIFICATION_ID
        and len(bank_verification_raw) == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest() == v151.previous.base.BANK_VERIFICATION_SHA256,
        "V155 frozen factor bank changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"] and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V155 frozen source closure changed",
        )
    expected_claim_boundary = {
        "target_outcomes_accessed": False,
        "guard_prevented_v154_sample_regression_observed": False,
        "guard_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    _require(
        registration["frozen_guard_receipt"] == guard
        and registration["target_occurrences"] == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 4
        and registration["maximum_acquisition_labels"] == 1_536
        and registration["claim_boundary"] == expected_claim_boundary
        and all(registration["registered_gate"].values()),
        "V155 registered contract changed",
    )

    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(executor.map(_verify_occurrence, ((row, bank) for row in campaign["target_occurrences"])))
    _require(
        tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V155 target occurrence inventory changed",
    )
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    factor_reductions = tuple(row["factor_prior_labels_avoided"] for row in rows)
    guard_reductions = tuple(row["guard_labels_avoided"] for row in rows)
    family_reductions = {FAMILY: sum(factor_reductions)}
    local_labels = accounting["anonymous_relational_prior_certificate_local_labels"] + accounting["strict_no_prior_certificate_local_labels"]
    base_gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(campaign_row["registered_gate"]["passed"] for campaign_row in campaign["target_occurrences"]),
        "required_target_family_count": 1,
        "observed_target_family_count": len({row["family"] for row in rows}),
        "aggregate_paired_acquisition_label_reduction": sum(factor_reductions),
        "aggregate_positive_label_reduction": sum(factor_reductions) > 0,
        "positive_reduction_occurrence_count": sum(value > 0 for value in factor_reductions),
        "zero_reduction_occurrence_count": sum(value == 0 for value in factor_reductions),
        "negative_reduction_occurrence_count": sum(value < 0 for value in factor_reductions),
        "family_aggregate_reductions": family_reductions,
        "every_family_has_positive_aggregate_reduction": all(value > 0 for value in family_reductions.values()),
        "same_synthesizer_and_stop_rule_everywhere": all(row["registered_gate"]["same_synthesizer_representation_and_stop_rule"] for row in campaign["target_occurrences"]),
        "anonymous_relational_instantiation_present_everywhere": all(row["registered_gate"]["anonymous_relational_instantiation_present_both_arms"] for row in campaign["target_occurrences"]),
        "both_arm_receding_episodes_succeed_everywhere": all(row["registered_gate"]["both_arm_receding_episodes_succeed"] for row in campaign["target_occurrences"]),
        "certificate_failure_local_recovery_exercised_at_least_once": local_labels > 0,
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()["strict_ood_no_transfer"],
    }
    base_gate["passed"] = (
        len(rows) == 4
        and base_gate["passed_target_occurrence_count"] == 4
        and base_gate["observed_target_family_count"] == 1
        and base_gate["aggregate_positive_label_reduction"]
        and base_gate["every_family_has_positive_aggregate_reduction"]
        and sum(base_gate[key] for key in ("positive_reduction_occurrence_count", "zero_reduction_occurrence_count", "negative_reduction_occurrence_count")) == 4
        and base_gate["same_synthesizer_and_stop_rule_everywhere"]
        and base_gate["anonymous_relational_instantiation_present_everywhere"]
        and base_gate["both_arm_receding_episodes_succeed_everywhere"]
        and base_gate["certificate_failure_local_recovery_exercised_at_least_once"]
        and base_gate["strict_incompatible_schema_no_transfer_verified"]
    )
    gate = {
        **base_gate,
        "guard_receipt_id": GUARD_RECEIPT_ID,
        "aggregate_guard_sample_reduction_vs_legacy_prior": sum(guard_reductions),
        "aggregate_factor_prior_reduction_within_guarded_operator": sum(factor_reductions),
        "zero_guard_regression_everywhere": all(value == 0 for value in guard_reductions),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factor_reductions),
        "factor_prior_positive_in_aggregate": sum(factor_reductions) > 0,
        "inherited_verified_relation_coverage_reduction": 345,
        "guarded_registered_context_net_reduction": 345 + sum(guard_reductions),
        "guarded_registered_context_net_reduction_positive": 345 + sum(guard_reductions) > 0,
        "memoized_plan_receipt_consumed_everywhere": all(row["registered_gate"]["v115_memoized_plan_receipt_consumed_both_arms"] for row in campaign["target_occurrences"]),
        "nonrelational_ood_rejected_everywhere": all(row["registered_gate"]["nonrelational_ood_rejected_before_bank_access"] for row in campaign["target_occurrences"]),
        "v154_failed_identity_preserved": True,
    }
    gate["passed"] = (
        base_gate["passed"]
        and gate["zero_guard_regression_everywhere"]
        and gate["factor_prior_noninferior_everywhere"]
        and gate["factor_prior_positive_in_aggregate"]
        and gate["guarded_registered_context_net_reduction_positive"]
        and gate["memoized_plan_receipt_consumed_everywhere"]
        and gate["nonrelational_ood_rejected_everywhere"]
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["guard_receipt_id"] == GUARD_RECEIPT_ID
        and campaign["v146_factor_bank_id"] == BANK_ID
        and campaign["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and campaign["incompatible_schema_no_transfer_control"] == incompatible_schema_no_transfer_control_v99()
        and campaign["accounting"] == accounting
        and campaign["registered_gate"] == gate
        and gate["passed"] is True
        and sum(guard_reductions) == 0
        and sum(factor_reductions) == 10
        and campaign["registered_workload_sample_efficiency_improvement_observed"] is True
        and campaign["sample_efficiency_improvement_claim_scope"] == "ONLY_THE_PREREGISTERED_V149_FOUR_FAMILY_CROSS_DOMAIN_COHORT"
        and campaign["relational_template_selection_itself_claimed_cross_domain"] is False
        and campaign["structural_signature_guard_prevented_v154_sample_regression"] is True
        and campaign["sample_tax_reduction_claim_scope"] == "ONLY_THE_REGISTERED_V153_POSITIVE_AND_V155_GUARDED_SIGNATURE_COHORTS"
        and campaign["guard_is_model_planning_or_certificate_authority"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V155 aggregate evidence changed",
    )
    payload = {
        "schema": "acfqp.structural_signature_guarded_verification.v155",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "guard_receipt_id": GUARD_RECEIPT_ID,
        "preserved_v153_campaign_id": V153_CAMPAIGN_ID,
        "preserved_v153_verification_id": V153_VERIFICATION_ID,
        "preserved_v154_failed_campaign_id": V154_CAMPAIGN_ID,
        "preserved_v154_failure_sha256": V154_FAILURE_SHA256,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_structural_signature_guard_and_fallback_reconstruction": True,
        "producer_free_matched_prior_and_strict_acquisition_reconstruction": True,
        "producer_free_v115_memoized_plan_and_v109_execution_receipt_reconstruction": True,
        "producer_free_abstract_planning_and_certificate_local_recovery_reconstruction": True,
        "producer_free_nonrelational_ood_rejection_reconstruction": True,
        "registered_structural_guard_prevented_regression_independently_verified": True,
        "guard_sample_reduction_vs_legacy_prior": sum(guard_reductions),
        "factor_prior_sample_reduction_within_guarded_operator": sum(factor_reductions),
        "inherited_verified_relation_coverage_reduction": 345,
        "sample_tax_reduction_claim_scope": campaign["sample_tax_reduction_claim_scope"],
        "guard_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": _content_id(domains.CONSTRUCTION_K7_VERIFICATION_V155_DOMAIN, payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V155 frozen verification changed",
        )
    return raw


__all__ = ("VERIFICATION_ID", "freeze_structural_signature_guarded_verification_v155")
