"""Producer-free verification of the frozen V151 relation-keyed campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_certified_planner_abstention_independent_verifier_v150 as previous
from acfqp import construction_k7_domain_registry_extension_v151 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_relation_keyed_workflow_adapter_v151 import (
    FAMILY,
    build_relation_keyed_workflow_adapter_v151,
    relation_keyed_workflow_config_v151,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "da305e55c00ff69b3aa240f2536a511eec6d6c3ee07f1418f80281f9ffa64cb0"
CAMPAIGN_BYTE_COUNT = 25_536_677
CAMPAIGN_SHA256 = "df3c508a7aa9fb8b0fecebb07530b21288818ebf993cf2e1f8b4407e79568a68"
PREREGISTRATION_ID = "78628783f9f922fc4ad866eb341463f68d367e4196e4c82c849e1a45902b148b"
PREREGISTRATION_BYTE_COUNT = 3_635
PREREGISTRATION_SHA256 = "86237f02e95663ca69358133237dd0cfe3f6262d57b4f0c8444f1aa1b4a5c486"
V150_CAMPAIGN_ID = previous.CAMPAIGN_ID
V150_CAMPAIGN_BYTE_COUNT = previous.CAMPAIGN_BYTE_COUNT
V150_CAMPAIGN_SHA256 = previous.CAMPAIGN_SHA256
V150_VERIFICATION_ID = previous.VERIFICATION_ID
V150_VERIFICATION_BYTE_COUNT = previous.EXPECTED_CANONICAL_BYTE_COUNT
V150_VERIFICATION_SHA256 = previous.EXPECTED_CANONICAL_SHA256
BANK_ID = previous.BANK_ID
BANK_VERIFICATION_ID = previous.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_371, 1_047_377))
EXPECTED_EPISODES = (601, 602, 603, 604)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ConstructionK7RelationKeyedBankIndependentVerifierV151Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationKeyedBankIndependentVerifierV151Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V151 {key} changed")


def _campaign_config() -> dict[str, Any]:
    config = relation_keyed_workflow_config_v151()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


_SEQUENCE_GLOBALS = dict(previous.__dict__)
_SEQUENCE_GLOBALS.update(EXPECTED_EPISODES=EXPECTED_EPISODES, _fail=_fail, _require=_require)
_VERIFY_SEQUENCE = FunctionType(
    previous._verify_sequence.__code__,  # noqa: SLF001
    _SEQUENCE_GLOBALS,
    name=previous._verify_sequence.__name__,  # noqa: SLF001
)


def _verify_occurrence(args: tuple[Mapping[str, Any], Mapping[str, Any]]) -> dict[str, Any]:
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema") == "acfqp.relation_keyed_relational_bank_occurrence.v151"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V151 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V151_DOMAIN)
    config = _campaign_config()
    adapter = build_relation_keyed_workflow_adapter_v151(seed, config)
    prior_doc = row["anonymous_relational_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = previous.base.previous.base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = previous.base._rebuild_acquisition(  # noqa: SLF001
        prior_doc, adapter, bank, batches, enabled=True, config=config
    )
    strict_candidate, strict_rows = previous.base._rebuild_acquisition(  # noqa: SLF001
        strict_doc, adapter, bank, batches, enabled=False, config=config
    )
    prior_sequence = _VERIFY_SEQUENCE(
        row["anonymous_relational_factor_prior_owned_sequence"],
        prior_candidate,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence = _VERIFY_SEQUENCE(
        row["strict_no_prior_owned_sequence"],
        strict_candidate,
        strict_rows,
        family=family,
        seed=seed,
    )
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    expected_accounting = {
        "anonymous_relational_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_anonymous_relational_prior": reduction,
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
    }
    sequences = (
        row["anonymous_relational_factor_prior_owned_sequence"],
        row["strict_no_prior_owned_sequence"],
    )
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(0 < doc["ground_support_labels"] <= 1_536 for doc in (prior_doc, strict_doc)),
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
        "relational_artifact_selected_in_prior_arm": prior_doc["relational_artifact_expression_selected_count"] > 0,
        "same_relational_expression_available_in_strict_pool": strict_doc["relational_artifact_expression_selected_count"] > 0,
    }
    gate["passed"] = all(gate.values())
    abstentions = sum(sequence["incomplete_abstract_plan_abstention_count"] for sequence in sequences)
    _require(
        row["accounting"] == expected_accounting
        and row["registered_gate"] == gate
        and row["paired_label_reduction"] == reduction
        and row["sample_efficiency_direction"] == ("POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO")
        and row["relation_binding_derived_from_raw_transition_deltas"] is True
        and row["direct_numeric_increment_field_present"] is False
        and row["relational_template_selection_itself_observed"] is True
        and row["v150_cross_domain_campaign_preserved"] is True
        and row["incomplete_abstract_path_never_used_as_execution_authority"] is True
        and row["incomplete_abstract_plan_abstention_count"] == abstentions
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V151 occurrence evidence changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "prior_labels": prior_doc["ground_support_labels"],
        "strict_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "prior_relational_expression_selected_count": prior_doc["relational_artifact_expression_selected_count"],
        "strict_relational_expression_selected_count": strict_doc["relational_artifact_expression_selected_count"],
        "incomplete_abstract_plan_abstention_count": abstentions,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": expected_accounting,
    }


def freeze_relation_keyed_bank_verification_v151(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    v150_campaign_raw: bytes,
    v150_verification_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    predecessor = loads_canonical_json(v150_campaign_raw)
    predecessor_verification = loads_canonical_json(v150_verification_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V151 frozen campaign identity changed",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V151_DOMAIN)
    _require(
        canonical_json_bytes(registration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256
        and registration.get("preregistration_id") == PREREGISTRATION_ID,
        "V151 frozen preregistration identity changed",
    )
    _verify_id(registration, "preregistration_id", domains.CONSTRUCTION_K7_PREREGISTRATION_V151_DOMAIN)
    _require(
        canonical_json_bytes(predecessor) == v150_campaign_raw
        and len(v150_campaign_raw) == V150_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v150_campaign_raw).hexdigest() == V150_CAMPAIGN_SHA256
        and predecessor.get("campaign_id") == V150_CAMPAIGN_ID
        and canonical_json_bytes(predecessor_verification) == v150_verification_raw
        and len(v150_verification_raw) == V150_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(v150_verification_raw).hexdigest() == V150_VERIFICATION_SHA256
        and predecessor_verification.get("verification_id") == V150_VERIFICATION_ID
        and registration["frozen_v150_predecessor"]["v150_campaign_id"] == V150_CAMPAIGN_ID
        and registration["frozen_v150_predecessor"]["v150_verification_id"] == V150_VERIFICATION_ID,
        "V151 preserved V150 predecessor changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(len(raw) == fact["byte_count"] and hashlib.sha256(raw).hexdigest() == fact["sha256"], "V151 frozen source fact changed")
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == BANK_ID
        and len(bank_raw) == previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id") == BANK_VERIFICATION_ID
        and len(bank_verification_raw) == previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest() == previous.base.BANK_VERIFICATION_SHA256
        and registration["target_occurrences"] == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V151 frozen bank or registered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(executor.map(_verify_occurrence, ((row, bank) for row in campaign["target_occurrences"])))
    _require(
        tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V151 occurrence inventory changed",
    )
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(sample_labels_execution_steps_derivation_and_planning_compute_separate=True, scalar_cost_aggregation_performed=False)
    reductions = tuple(row["labels_avoided"] for row in rows)
    family_reductions = {FAMILY: sum(reductions)}
    local_labels = accounting["anonymous_relational_prior_certificate_local_labels"] + accounting["strict_no_prior_certificate_local_labels"]
    gate = campaign["registered_gate"]
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["accounting"] == accounting
        and campaign["incompatible_schema_no_transfer_control"] == incompatible_schema_no_transfer_control_v99()
        and gate["passed"] is True
        and gate["aggregate_paired_acquisition_label_reduction"] == sum(reductions) == 48
        and gate["positive_reduction_occurrence_count"] == 6
        and gate["zero_reduction_occurrence_count"] == 0
        and gate["negative_reduction_occurrence_count"] == 0
        and gate["family_aggregate_reductions"] == family_reductions
        and gate["relational_artifact_selected_in_prior_everywhere"] is True
        and all(row["prior_relational_expression_selected_count"] > 0 and row["strict_relational_expression_selected_count"] > 0 for row in rows)
        and gate["certificate_failure_local_recovery_exercised_at_least_once"] is (local_labels > 0)
        and campaign["registered_workload_sample_efficiency_improvement_observed"] is True
        and campaign["relational_template_selection_itself_claimed_cross_domain"] is True
        and campaign["relational_template_selection_claim_scope"] == "ONLY_THE_PREREGISTERED_V151_RELATION_KEYED_WORKFLOW_COHORT"
        and campaign["v150_campaign_and_verification_preserved"] is True
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V151 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.relation_keyed_bank_verification.v151",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "preserved_v150_campaign_id": V150_CAMPAIGN_ID,
        "preserved_v150_verification_id": V150_VERIFICATION_ID,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "verified_family_aggregate_reductions": family_reductions,
        "producer_free_raw_delta_relation_binding_reconstruction": True,
        "producer_free_relational_template_selection_reconstruction": True,
        "producer_free_matched_candidate_and_stop_reconstruction": True,
        "producer_free_model_epoch_and_certificate_local_recovery_reconstruction": True,
        "producer_free_abstract_plan_support_reconstruction": True,
        "registered_relation_keyed_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": campaign["sample_efficiency_improvement_claim_scope"],
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": domains.extension_content_id_v151(domains.CONSTRUCTION_K7_VERIFICATION_V151_DOMAIN, payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V151 frozen verification changed",
        )
    return raw


__all__ = ("VERIFICATION_ID", "freeze_relation_keyed_bank_verification_v151")
