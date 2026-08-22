"""Producer-free verification of V143r1 acquisition, models, receipts, and plans."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v143r1 as domains
from acfqp import construction_k7_occurrence_factor_bank_update_independent_verifier_v141 as v141
from acfqp import construction_k7_robust_factor_dictionary_independent_verifier_v131r2 as base
from acfqp.generic_dual_budget_adapter_v119 import FAMILY as DUAL
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import FAMILY as MODULAR
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    build_packet_batching_adapter_v134,
    packet_batching_config_v134,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "5f284a0639c7812c5ac99b96250c4a91f90d957b8392e556acc46a2d2d7f45d8"
CAMPAIGN_BYTE_COUNT = 20_483_141
CAMPAIGN_SHA256 = "6982abdcd2bcb19e7b6c6ba800161bfbe4bb7c79aa4e017f92e0e5461e4b7cf8"
PREREGISTRATION_ID = "8794fa232f13e89bd29049302b6bee6859489a7949de6f52e78c9efdfd665004"
PREREGISTRATION_BYTE_COUNT = 22_794
PREREGISTRATION_SHA256 = "9fac88b8c47fff2b49536ec0fd079d2e1c2e7812f48d31b8222aa3d15845de5a"
V140_FAILURE_BYTE_COUNT = 1_107
V140_FAILURE_SHA256 = (
    "3123b0babe9b11a732bb565c855cbc852ec16998d0aa36bbc18cbf10f279af02"
)
V142_FAILURE_BYTE_COUNT = 1_486
V142_FAILURE_SHA256 = (
    "b6782177e8bfabd9d8b4d7f0a9d12f4c54aba03a613bf8f0a4d18896229c7085"
)
V143_FAILURE_BYTE_COUNT = 1_931
V143_FAILURE_SHA256 = (
    "15b157c5301a650603a6d131e5c6feb6d35481be1aaf4be2f537bd7fd30163de"
)
EXPECTED_OCCURRENCES = (
    (INVENTORY, 1_047_231),
    (INVENTORY, 1_047_232),
    (INVENTORY, 1_047_233),
    (DUAL, 1_047_234),
    (DUAL, 1_047_235),
    (DUAL, 1_047_236),
    (MODULAR, 1_047_237),
    (MODULAR, 1_047_238),
    (MODULAR, 1_047_239),
    (PACKET, 1_047_240),
    (PACKET, 1_047_241),
    (PACKET, 1_047_242),
)
EXPECTED_EPISODES = (439, 440)
VERIFICATION_ID = "2742300da785107979ed114e874e44eb75c347312de59b3dc6160d659461a70c"
EXPECTED_CANONICAL_BYTE_COUNT = 20_715
EXPECTED_CANONICAL_SHA256 = (
    "06584f11561e7fe9aed9e6aecf27adc473245fb538bc5a4d94986d1c823cb2f8"
)

_BUILDERS = {
    **base._BUILDERS,  # noqa: SLF001
    PACKET: build_packet_batching_adapter_v134,
}


class ConstructionK7OccurrenceFactorBankUpdatePlanningIndependentVerifierV143r1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankUpdatePlanningIndependentVerifierV143r1Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V143r1 {key} changed")


def _legacy_acquisition_document(recorded: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in recorded.items()
        if key
        not in {
            "acquisition_id",
            "v141_factor_bank_id",
            "v141_independent_verification_id",
            "occurrence_granular_robust_factor_bank_selected_source_only",
            "verified_factor_bank_receipt_consumed_before_target_outcomes",
            "candidate_replay_error_count",
        }
    }
    payload["schema"] = "acfqp.robust_dictionary_factor_acquisition_arm.v131r2"
    if payload["arm"] == "OCCURRENCE_FACTOR_BANK_UPDATE_FACTOR_PRIOR_ON":
        payload["arm"] = "NORMALIZED_FACTOR_PRIOR_ON"
    return {
        **payload,
        "acquisition_id": base._content_id(  # noqa: SLF001
            base._DOMAINS["acquisition"], payload  # noqa: SLF001
        ),
    }


def _verify_sequence(
    sequence: Mapping[str, Any],
    candidate: Mapping[str, Any],
    acquisition_rows: tuple[Any, ...],
    *,
    family: str,
    seed: int,
) -> dict[str, int]:
    base._verify_id(sequence, "sequence_id", base._DOMAINS["sequence"])  # noqa: SLF001
    _require(
        sequence["schema"] == "acfqp.standalone_generic_owned_sequence.v126"
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and sequence["family"] == family
        and sequence["seed"] == seed
        and tuple(sequence["episode_indices"]) == EXPECTED_EPISODES,
        "V143r1 owned sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"]
        == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate["candidate_id"]
        and dependency["compiled_factor_assignments"]
        == candidate["compiled_factor_assignments"],
        "V143r1 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    persistent = sequence["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == sequence["persistent_exact_overlay_sha256"],
        "V143r1 persistent evidence hash changed",
    )
    acquisition_documents = [row.to_document() for row in acquisition_rows]
    acquisition_unique = {
        base.model._raw_key(raw): raw for raw in acquisition_documents  # noqa: SLF001
    }
    initial_documents = tuple(
        acquisition_unique[key] for key in sorted(acquisition_unique)
    )
    current = {
        base.model._raw_key(raw): raw for raw in initial_documents  # noqa: SLF001
    }
    initial_rows = tuple(current.values())
    facts = base.model._project(initial_rows, candidate, actions)  # noqa: SLF001
    _require(
        facts["model"] == sequence["quotient_models_before_each_episode"][0]
        and base.model._bootstrap_receipt(initial_rows, facts)  # noqa: SLF001
        == sequence["bootstrap_receipt"]
        and base.model._match_receipt(facts, initial_rows, None)  # noqa: SLF001
        == sequence["bootstrap_full_rebuild_match"],
        "V143r1 bootstrap reconstruction changed",
    )
    updates = sequence["standalone_model_update_receipts"]
    matches = sequence["standalone_full_rebuild_match_receipts"]
    _require(
        len(sequence["episodes"])
        == len(updates)
        == len(matches)
        == len(EXPECTED_EPISODES),
        "V143r1 episode/receipt cardinality changed",
    )
    rebuilt_models = []
    path_checks = direct = reused = 0
    all_plans = []
    for index, episode in enumerate(sequence["episodes"]):
        before = base.model._project(  # noqa: SLF001
            tuple(current.values()), candidate, actions
        )
        _require(
            before["model"] == sequence["quotient_models_before_each_episode"][index]
            and episode["quotient_graph_before_episode"] == before["model"]
            and episode["standalone_model_state_id_before_episode"]
            == before["state_id"]
            and updates[index]["previous_successor_state_id"] == before["state_id"],
            "V143r1 before-model reconstruction changed",
        )
        rebuilt_models.append(before["model"])
        for wrapper in episode["abstract_plan_receipts"]:
            plan = wrapper["abstract_plan"]
            all_plans.append(plan)
            source = plan["planning_source"]
            if source in {
                "OBSERVATION_QUOTIENT_GRAPH",
                "COMPILED_FACTOR_PROGRAM_FALLBACK",
            }:
                base._verify_id(  # noqa: SLF001
                    plan,
                    "legality_conditioned_quotient_plan_id",
                    base._DOMAINS["plan"],  # noqa: SLF001
                )
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"])
                    == before["rules"],
                    "V143r1 terminal projection rule changed",
                )
                path_checks += base.generic._verify_plan(  # noqa: SLF001
                    plan,
                    wrapper["raw_state"],
                    candidate,
                    actions,
                    before["model"],
                    before["rules"],
                )
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["generic_factor_program_execution_adapter_used"] is True
                        and plan[
                            "legacy_shape_specific_planner_execution_adapter_called"
                        ]
                        is False,
                        "V143r1 direct generic plan changed",
                    )
            elif source in {
                "COMPILED_FACTOR_PROGRAM_MEMOIZED",
                "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
            }:
                reused += 1
                if source == "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER":
                    _require(
                        plan["cached_ordering_used_as_safety_authority"] is False
                        and plan["dependency_revalidation"]["current_quotient_graph_id"]
                        == before["model"]["quotient_graph_id"],
                        "V143r1 dependency reuse changed",
                    )
            else:
                _fail("V143r1 unknown planning source")
        delta_rows = tuple(episode["raw_incremental_transition_rows"])
        novel_rows = tuple(
            raw
            for raw in delta_rows
            if base.model._raw_key(raw) not in current  # noqa: SLF001
        )
        novel = (
            base.model._project(novel_rows, candidate, actions)  # noqa: SLF001
            if novel_rows
            else {"raw_keys": frozenset(), "checks": 0}
        )
        for raw in delta_rows:
            current[base.model._raw_key(raw)] = raw  # noqa: SLF001
        after = base.model._project(  # noqa: SLF001
            tuple(current.values()), candidate, actions
        )
        expected_update = base.model._update_receipt(  # noqa: SLF001
            before, after, delta_rows, novel
        )
        expected_match = base.model._match_receipt(  # noqa: SLF001
            after, tuple(current.values()), expected_update
        )
        _require(
            expected_update == updates[index]
            and expected_match == matches[index]
            and episode["standalone_model_update_after_episode"] == expected_update
            and episode["standalone_full_rebuild_match_after_episode"]
            == expected_match
            and episode["quotient_graph_after_episode"] == after["model"]
            and episode["standalone_model_state_id_after_episode"] == after["state_id"]
            and after["model"] == sequence["quotient_models_after_each_episode"][index],
            "V143r1 update/full-match reconstruction changed",
        )
        rebuilt_models.append(after["model"])
        _require(
            episode["success"] is True
            and episode[
                "all_incremental_ground_queries_followed_failed_certificates"
            ]
            is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V143r1 certificate discipline changed",
        )
    _require(
        [current[key] for key in sorted(current)] == list(persistent),
        "V143r1 persistent inventory changed",
    )
    actual_compute = sum(
        episode["abstract_planning_compute_events"] for episode in sequence["episodes"]
    )
    uncached_compute = sum(
        plan.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            plan["abstract_support_branch_evaluations"],
        )
        for plan in all_plans
    )
    dependency_compute = len(EXPECTED_EPISODES) * (
        len(dependency["compiled_factor_assignments"])
        + len(dependency["canonical_action_catalogue"])
    )
    _require(
        sequence["dependency_receipt_rederivation_count"] == len(EXPECTED_EPISODES)
        and sequence["dependency_derivation_compute_events"] == dependency_compute
        and sequence["actual_new_abstract_planning_compute_events"] == actual_compute
        and sequence["matched_uncached_abstract_planning_compute_events"]
        == uncached_compute
        and sequence["planning_compute_events_avoided_against_uncached"]
        == uncached_compute - actual_compute
        and sequence["direct_generic_factor_program_plan_count"] == direct
        and sequence["owned_episode_loop_implementation_present"] is True
        and sequence["standalone_v125_state_carrier_verified"] is True
        and sequence["retained_v113_state_carrier_present"] is False
        and sequence["retained_v113_sequence_orchestration_present"] is False
        and sequence["retained_v119_sequence_orchestration_present"] is False
        and sequence["compiled_model_cache_or_receipt_used_as_safety_authority"]
        is False,
        "V143r1 sequence accounting/claim boundary changed",
    )
    return {
        "model_epoch_count": len(rebuilt_models),
        "receipt_count": 2 + 2 * len(sequence["episodes"]),
        "plan_path_support_checks": path_checks,
        "reused_plan_count": reused,
        "direct_plan_count": direct,
    }


def _rebuild_acquisition(
    recorded: Mapping[str, Any],
    adapter: Any,
    projection: Mapping[str, Any],
    batches: tuple[tuple[Any, ...], ...],
    *,
    enabled: bool,
    config: Mapping[str, Any],
) -> tuple[Any, tuple[Any, ...]]:
    _verify_id(
        recorded,
        "acquisition_id",
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_ACQUISITION_V143R1_DOMAIN,
    )
    _require(
        recorded["v141_factor_bank_id"] == v141.FROZEN_BANK_ID
        and recorded["v141_independent_verification_id"] == v141.VERIFICATION_ID
        and recorded["occurrence_granular_robust_factor_bank_selected_source_only"]
        is True
        and recorded[
            "verified_factor_bank_receipt_consumed_before_target_outcomes"
        ]
        is True,
        "V143r1 acquisition receipt binding changed",
    )
    _require(
        recorded["candidate_replay_error_count"] == 0,
        "V143r1 production acquisition unexpectedly used replay-error recovery",
    )
    transformed = _legacy_acquisition_document(recorded)
    candidate, rows = base._rebuild_acquisition(  # noqa: SLF001
        transformed,
        adapter,
        projection,
        batches,
        enabled=enabled,
        config=config,
    )
    _require(
        transformed["candidate"] == recorded["candidate"]
        and transformed["terminal_stop_update"] == recorded["terminal_stop_update"],
        "V143r1 low-level acquisition projection changed",
    )
    return candidate, rows


def _verify_occurrence(
    row: Mapping[str, Any], projection: Mapping[str, Any]
) -> dict[str, Any]:
    family = row["target_family"]
    seed = row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row["schema"] == "acfqp.occurrence_factor_bank_update_planning_occurrence.v143r1"
        and tuple(row["episode_indices"]) == EXPECTED_EPISODES,
        "V143r1 occurrence identity changed",
    )
    _verify_id(
        row,
        "occurrence_id",
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_OCCURRENCE_V143R1_DOMAIN,
    )
    config = packet_batching_config_v134()
    for configured_family in _BUILDERS:
        config["families"][configured_family]["maximum_acquisition_labels"] = 1_536
    adapter = _BUILDERS[family](seed, config)
    prior_doc = row["occurrence_factor_bank_update_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    strict_labels = strict_doc["ground_support_labels"]
    stream = base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_labels))
    prior_candidate, prior_rows = _rebuild_acquisition(
        prior_doc,
        adapter,
        projection,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = _rebuild_acquisition(
        strict_doc,
        adapter,
        projection,
        batches,
        enabled=False,
        config=config,
    )
    prior_sequence_doc = row["occurrence_factor_bank_update_factor_prior_owned_sequence"]
    strict_sequence_doc = row["strict_no_prior_owned_sequence"]
    prior_sequence = _verify_sequence(
        prior_sequence_doc,
        prior_candidate.public_document,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence = _verify_sequence(
        strict_sequence_doc,
        strict_candidate.public_document,
        strict_rows,
        family=family,
        seed=seed,
    )
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "occurrence_factor_bank_update_factor_prior_ground_support_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_occurrence_factor_bank_update_prior": reduction,
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_rows
        == strict_rows[: len(prior_rows)],
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "verified_v141_factor_bank_is_the_only_structural_prior_input": True,
        "fixed_source_inventory_reintroduced": False,
        "sample_labels_and_derivation_compute_separate": True,
    }
    accounting = {
        "occurrence_factor_bank_update_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior": reduction,
        "occurrence_factor_bank_update_prior_certificate_local_labels": prior_sequence_doc[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence_doc[
            "certificate_ground_support_labels_paid_once"
        ],
        "occurrence_factor_bank_update_prior_lifetime_target_labels": prior_sequence_doc[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_sequence_doc[
            "lifetime_target_ground_support_labels"
        ],
        "occurrence_factor_bank_update_prior_execution_steps": prior_sequence_doc[
            "execution_step_count"
        ],
        "strict_no_prior_execution_steps": strict_sequence_doc["execution_step_count"],
        "occurrence_factor_bank_update_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "occurrence_factor_bank_update_prior_candidate_replay_errors": prior_doc[
            "candidate_replay_error_count"
        ],
        "strict_no_prior_candidate_replay_errors": strict_doc[
            "candidate_replay_error_count"
        ],
        "occurrence_factor_bank_update_prior_planning_compute_events": prior_sequence_doc[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence_doc[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(
            0 < document["ground_support_labels"] <= 1_536
            for document in (prior_doc, strict_doc)
        ),
        "same_raw_transition_prefix_through_common_label": True,
        "same_synthesizer_representation_and_stop_rule": True,
        "verified_v141_factor_bank_receipt_consumed": True,
        "both_arm_receding_episodes_succeed": True,
        "certificate_failure_only_local_ground_distinctions": True,
        "planner_consumes_compiled_model_without_raw_rows": True,
    }
    gate["passed"] = all(gate.values())
    _require(
        row["v141_factor_bank_id"] == v141.FROZEN_BANK_ID
        and row["v141_independent_verification_id"] == v141.VERIFICATION_ID
        and row["sample_tax_comparison"] == sample_tax
        and row["accounting"] == accounting
        and row["registered_gate"] == gate
        and row["paired_label_reduction"] == reduction
        and row["sample_efficiency_direction"]
        == ("POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO")
        and row["registered_workload_sample_efficiency_improvement_observed"]
        is (reduction > 0)
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["official_N_break_even"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V143r1 occurrence Gate/accounting changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "occurrence_factor_bank_update_prior_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "occurrence_factor_bank_update_prior_sequence": prior_sequence,
        "strict_no_prior_sequence": strict_sequence,
        "accounting": accounting,
    }


def freeze_occurrence_factor_bank_update_planning_verification_v143r1(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    dictionary_raw: bytes,
    dictionary_verification_raw: bytes,
    v140_failure_raw: bytes,
    v142_failure_raw: bytes,
    v143_failure_raw: bytes,
    source_campaign_bytes: Iterable[bytes],
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V143r1 frozen campaign identity/bytes changed",
    )
    _verify_id(
        campaign,
        "campaign_id",
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_CAMPAIGN_V143R1_DOMAIN,
    )
    registration = loads_canonical_json(preregistration_raw)
    _require(
        canonical_json_bytes(registration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256
        and registration.get("preregistration_id") == PREREGISTRATION_ID,
        "V143r1 frozen preregistration identity/bytes changed",
    )
    _verify_id(
        registration,
        "preregistration_id",
        domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_PREREGISTRATION_V143R1_DOMAIN,
    )
    sources = tuple(source_campaign_bytes)
    reconstructed_dictionary = v141._derive_occurrence_factor_bank_update_independent_v141(  # noqa: SLF001
        sources
    )
    _require(
        canonical_json_bytes(reconstructed_dictionary) == dictionary_raw
        and v141.freeze_occurrence_factor_bank_update_verification_v141(
            dictionary_raw, sources
        )
        == dictionary_verification_raw,
        "V143r1 producer-free V141 receipt reconstruction changed",
    )
    dictionary = loads_canonical_json(dictionary_raw)
    dictionary_verification = loads_canonical_json(dictionary_verification_raw)
    v140_failure = loads_canonical_json(v140_failure_raw)
    v142_failure = loads_canonical_json(v142_failure_raw)
    v143_failure = loads_canonical_json(v143_failure_raw)
    _require(
        registration["frozen_v141_factor_bank"] == dictionary
        and registration["frozen_v141_independent_verification"]
        == dictionary_verification
        and registration["frozen_v140_failed_predecessor"] == v140_failure
        and canonical_json_bytes(v140_failure) == v140_failure_raw
        and len(v140_failure_raw) == V140_FAILURE_BYTE_COUNT
        and hashlib.sha256(v140_failure_raw).hexdigest() == V140_FAILURE_SHA256
        and v140_failure["outcome_kind"] == "PREREGISTERED_RESOURCE_CAP_FAILURE"
        and v140_failure["failed_seed"] == 1_047_172
        and v140_failure["same_identity_rerun_forbidden"] is True
        and registration["frozen_v142_failed_predecessor"] == v142_failure
        and canonical_json_bytes(v142_failure) == v142_failure_raw
        and len(v142_failure_raw) == V142_FAILURE_BYTE_COUNT
        and hashlib.sha256(v142_failure_raw).hexdigest() == V142_FAILURE_SHA256
        and v142_failure["outcome_kind"]
        == "PREREGISTERED_CAUSAL_OPCODE_EVALUATOR_FAILURE"
        and v142_failure["error_type"]
        == "GenericArtifactSubprogramInstantiatorV121Error"
        and v142_failure["same_identity_rerun_forbidden"] is True
        and registration["frozen_v143_failed_predecessor"] == v143_failure
        and canonical_json_bytes(v143_failure) == v143_failure_raw
        and len(v143_failure_raw) == V143_FAILURE_BYTE_COUNT
        and hashlib.sha256(v143_failure_raw).hexdigest() == V143_FAILURE_SHA256
        and v143_failure["outcome_kind"] == "PREREGISTERED_RESOURCE_CAP_FAILURE"
        and v143_failure["failed_family"] == DUAL
        and v143_failure["failed_seed"] == 1_047_215
        and v143_failure["frozen_maximum_acquisition_labels"] == 768
        and v143_failure["same_identity_rerun_forbidden"] is True
        and registration["target_occurrences"]
        == [
            {"family": family, "seed": seed}
            for family, seed in EXPECTED_OCCURRENCES
        ]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 12
        and registration["maximum_acquisition_labels"] == 1_536
        and registration["registered_gate"][
            "robust_candidate_schema_is_explicitly_decoded"
        ]
        is True
        and registration["registered_gate"][
            "occurrence_support_replaces_campaign_container_support"
        ]
        is True
        and registration["claim_boundary"]["target_outcomes_accessed"] is False
        and registration["claim_boundary"][
            "registered_v143r1_target_outcome_observed"
        ]
        is False
        and registration["registered_gate"][
            "aggregate_positive_reduction_is_primary_gate"
        ]
        is True
        and registration["registered_gate"][
            "strict_positive_reduction_required_each_occurrence"
        ]
        is False
        and registration["registered_gate"][
            "zero_and_negative_occurrences_must_be_preserved"
        ]
        is True,
        "V143r1 preregistered receipt/target contract changed",
    )
    projection = dictionary["v15_partial_synthesizer_projection"]
    rows = tuple(
        _verify_occurrence(row, projection) for row in campaign["target_occurrences"]
    )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V143r1 target occurrence identities changed",
    )
    ood = campaign["incompatible_schema_no_transfer_control"]
    _require(
        ood["control_id"]
        == base._content_id(  # noqa: SLF001
            base._DOMAINS["ood"],  # noqa: SLF001
            {key: value for key, value in ood.items() if key != "control_id"},
        )
        and ood["strict_ood_no_transfer"] is True
        and ood["learned_structure_prior_delivered"] is False
        and ood["target_outcomes_accessed"] is False,
        "V143r1 strict OOD control changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    reductions = tuple(row["labels_avoided"] for row in rows)
    positive_count = sum(value > 0 for value in reductions)
    zero_count = sum(value == 0 for value in reductions)
    negative_count = sum(value < 0 for value in reductions)
    aggregate_reduction = accounting[
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior"
    ]
    gate = {
        "required_target_occurrence_count": 12,
        "passed_target_occurrence_count": 12,
        "aggregate_paired_acquisition_label_reduction": aggregate_reduction,
        "aggregate_positive_label_reduction": aggregate_reduction > 0,
        "per_occurrence_positive_reduction_required": False,
        "zero_or_negative_occurrences_preserved_without_selection": True,
        "positive_reduction_occurrence_count": positive_count,
        "zero_reduction_occurrence_count": zero_count,
        "negative_reduction_occurrence_count": negative_count,
        "verified_v141_factor_bank_receipt_consumed_everywhere": True,
        "same_synthesizer_representation_and_stop_rule_everywhere": True,
        "both_arm_receding_episodes_succeed_everywhere": True,
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": True,
    }
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v141_factor_bank_id"] == v141.FROZEN_BANK_ID
        and campaign["v141_independent_verification_id"] == v141.VERIFICATION_ID
        and campaign["accounting"] == accounting
        and campaign["registered_gate"] == gate
        and campaign[
            "registered_workload_sample_efficiency_improvement_observed"
        ]
        is True
        and campaign["sample_efficiency_improvement_claim_scope"]
        == "ONLY_THE_PREREGISTERED_V143R1_TWELVE_OCCURRENCE_FOUR_FAMILY_WORKLOAD"
        and campaign["fixed_source_campaign_inventory_reintroduced"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V143r1 campaign Gate/accounting changed",
    )
    payload = {
        "schema": "acfqp.occurrence_factor_bank_update_planning_verification.v143r1",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v141_factor_bank_id": v141.FROZEN_BANK_ID,
        "v141_independent_verification_id": v141.VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_v141_occurrence_factor_bank_update_reconstruction": True,
        "producer_free_v140_failed_predecessor_preservation_verified": True,
        "producer_free_v142_failed_predecessor_preservation_verified": True,
        "producer_free_v143_failed_predecessor_preservation_verified": True,
        "production_candidate_replay_error_count": 0,
        "producer_free_path_first_acquisition_reconstruction": True,
        "producer_free_model_epoch_receipt_and_plan_reconstruction": True,
        "verified_factor_bank_receipt_reaches_compiled_planner": True,
        "registered_workload_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V143R1_TWELVE_OCCURRENCE_FOUR_FAMILY_WORKLOAD"
        ),
        "fixed_source_campaign_inventory_reintroduced": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v143r1(
            domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_VERIFICATION_V143R1_DOMAIN,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V143r1 frozen independent verification changed",
        )
    return raw


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_occurrence_factor_bank_update_planning_verification_v143r1",
)
