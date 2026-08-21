"""Producer-free verification of V119 source-unseen residual evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains59
from acfqp import construction_k7_domain_registry_extension_v119 as domains
from acfqp import construction_k7_dependency_derived_program_branch_independent_verifier_v117 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "611c995b93af4016bb85e070f5c1f263d6028ec424cc860e2b67da2bb9aeb3d4"
CAMPAIGN_BYTE_COUNT = 4_479_714
CAMPAIGN_SHA256 = "22565e57114973fbf1c2fc16d11785eb67c9aebcb5df2c61dc39cc0ba64e301e"
PREREGISTRATION_ID = "4f29a2060a9eaecd4f072d245b7f0dd1af8168b4ae005b268ec3c52510fac929"
V118_CAMPAIGN_ID = "0ab03c02a8b5b795860c5c96943204f8553fc6836e7dab92ef753c1fe6d86df1"
V118_VERIFICATION_ID = "a5cfca977eaf84e21ce57e81ac49c6dd71f8bc9db180acadece8af1cc03af51d"
V117_VERIFIER_SOURCE_SHA256 = "4ee4caa5e7a667d66944d34d1a37c10def49e0381d05fb86553109581e476bde"
V117_CAMPAIGN_ID = "5817b88896699206fcb08ed64111fc993691515fd0461e518c956a04de283b9d"
V117_VERIFICATION_ID = "c8a9d342192a29d50e299121b7e1d35784cd3c8219e1e99757a111174ff829ef"
FAMILY = "STOCHASTIC_DUAL_BUDGET_COMPOSITION"
TARGETS = ((FAMILY, 1_031_101), (FAMILY, 1_031_102))
EPISODES = (263, 264, 265)
SOURCE_FACTOR_LIBRARY_ID = "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
GENERIC_ATOMIC_OPCODE_NAMES = [f"E{index:02d}" for index in range(14)]
VERIFICATION_ID = "2a9569ea23d23ee1f69219b36c03dd8a6f8b827a7f9f5b6c77f62587380e2e70"
EXPECTED_CANONICAL_BYTE_COUNT = 3_870
EXPECTED_CANONICAL_SHA256 = "3c6bfafd726854246c39fb27c8ca9b5ab8f058436c724e9703854aad19f171e4"


class ConstructionK7SourceUnseenResidualIndependentVerifierV119Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceUnseenResidualIndependentVerifierV119Error(message)


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V119 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v119(domain, payload):
        _fail(f"V119 {key} changed")


def _v117_namespace() -> dict[str, Any]:
    if (
        hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest()
        != V117_VERIFIER_SOURCE_SHA256
        or previous.CAMPAIGN_ID != V117_CAMPAIGN_ID
        or previous.VERIFICATION_ID != V117_VERIFICATION_ID
    ):
        _fail("V119 frozen producer-free V117 verifier changed")
    namespace = dict(previous.__dict__)
    namespace["EPISODES"] = EPISODES
    originals = {
        name: value
        for name, value in previous.__dict__.items()
        if type(value) is FunctionType and value.__module__ == previous.__name__
    }
    for name, value in originals.items():
        clone = FunctionType(
            value.__code__,
            namespace,
            name=value.__name__,
            argdefs=value.__defaults__,
            closure=value.__closure__,
        )
        clone.__kwdefaults__ = value.__kwdefaults__
        namespace[name] = clone
    return namespace


def _candidate(document: Any) -> dict[str, int]:
    if type(document) is not dict:
        _fail("V119 partial candidate type changed")
    payload = {key: value for key, value in document.items() if key != "candidate_id"}
    assignments = document.get("compiled_factor_assignments")
    unknown = document.get("unknown_residual_target_columns")
    if (
        document.get("candidate_id")
        != domains59.extension_content_id_v59(
            domains59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or document.get("source_factor_library_id") != SOURCE_FACTOR_LIBRARY_ID
        or type(assignments) is not list
        or len(assignments) < 3
        or any(
            type(row) is not dict
            or type(row.get("target_column")) is not int
            or row.get("result_type") not in {"INT", "FINITE_INT_SUPPORT"}
            or type(row.get("expression")) is not list
            for row in assignments
        )
        or type(unknown) is not list
        or not unknown
        or sorted(set(unknown)) != unknown
        or set(unknown) & {row["target_column"] for row in assignments}
        or document.get("target_slot_inventory_supplied_by_prior") is not False
        or document.get("target_bindings_derived_from_raw_observations") is not True
        or document.get("semantic_names_used") is not False
        or document.get("complete_world_model_claimed") is not False
        or document.get("planning_authority_present") is not False
    ):
        _fail("V119 partial candidate identity or boundary changed")
    return {
        "compiled_factor_assignment_count": len(assignments),
        "unknown_residual_target_column_count": len(unknown),
    }


def _acquisition(document: Any, family: str, seed: int) -> dict[str, int]:
    _content(
        document,
        "acquisition_id",
        domains.CONSTRUCTION_K7_SOURCE_UNSEEN_PARTIAL_ACQUISITION_V119_DOMAIN,
    )
    counts = _candidate(document.get("candidate"))
    labels = document.get("ground_support_labels")
    rows = document.get("raw_transition_count")
    stop = document.get("terminal_stop_update")
    if (
        document.get("schema") != "acfqp.source_unseen_partial_acquisition.v119"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("arm") != "ANONYMOUS_FACTOR_PRIOR_ON"
        or document.get("factor_prior_enabled") is not True
        or type(labels) is not int
        or labels <= 0
        or type(rows) is not int
        or rows <= 0
        or type(document.get("raw_transition_sha256")) is not str
        or len(document["raw_transition_sha256"]) != 64
        or type(stop) is not dict
        or stop.get("stopped") is not True
        or document.get("same_witness_blind_raw_prefix_as_strict_control") is not True
        or document.get("domain_source_available_to_synthesizer") is not False
        or document.get("partial_prediction_scope_only") is not True
        or document.get("unknown_residual_outputs_claimed") is not False
        or document.get("complete_world_model_claimed") is not False
        or document.get("planning_authority_present") is not False
        or document.get("reachable_frontier_exhaustion_input_consumed") is not False
        or document.get("heuristic_mdl_information_units_consumed") is not False
        or document.get("predictive_evidence_to_mdl_credit_consumed") is not False
    ):
        _fail("V119 partial acquisition semantics changed")
    return {**counts, "ground_support_labels": labels, "raw_transition_count": rows}


def _strict_control(
    document: Any,
    partial: Mapping[str, Any],
    family: str,
    seed: int,
) -> None:
    _content(
        document,
        "strict_control_id",
        domains.CONSTRUCTION_K7_SOURCE_UNSEEN_STRICT_CONTROL_V119_DOMAIN,
    )
    if (
        document.get("schema")
        != "acfqp.source_unseen_strict_complete_model_control.v119"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("arm") != "STRICT_NO_PRIOR_SINGLE_MATCHED_PREFIX_ATTEMPT"
        or document.get("factor_prior_enabled") is not False
        or document.get("ground_support_labels")
        != partial.get("ground_support_labels")
        or document.get("raw_transition_count") != partial.get("raw_transition_count")
        or document.get("raw_transition_sha256")
        != partial.get("raw_transition_sha256")
        or document.get("matched_partial_acquisition_id")
        != partial.get("acquisition_id")
        or document.get("generic_atomic_composition_max_depth") != 3
        or document.get("generic_atomic_opcode_names") != GENERIC_ATOMIC_OPCODE_NAMES
        or document.get("attempt_count") != 1
        or document.get("outcome_kind")
        != "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR"
        or document.get("complete_candidate") is not None
        or document.get("constructor_error_type")
        != "GenericAtomicExpressionWorldModelV4Error"
        or document.get("typed_rejection_is_not_domain_infeasibility") is not True
        or document.get("typed_rejection_is_not_planning_failure") is not True
        or document.get("strict_control_used_for_safety_authority") is not False
        or document.get("sample_efficiency_sign_claimed") is not False
    ):
        _fail("V119 strict matched-prefix control changed")


def _sequence(
    document: Any,
    candidate: Mapping[str, Any],
    namespace: Mapping[str, Any],
) -> dict[str, int]:
    _content(
        document,
        "sequence_id",
        domains.CONSTRUCTION_K7_GENESIS_AUTHORIZED_BRANCH_SEQUENCE_V119_DOMAIN,
    )
    base = document.get("genesis_authorized_base_sequence")
    if (
        document.get("schema")
        != "acfqp.generic_genesis_authorized_program_branch_sequence.v119"
        or document.get("episode_indices") != list(EPISODES)
        or type(base) is not dict
        or document.get("genesis_authorized_base_sequence_id")
        != base.get("sequence_id")
    ):
        _fail("V119 sequence wrapper changed")
    try:
        namespace["_v115_namespace"]()["_sequence"](base)
    except Exception as exc:
        if not type(exc).__module__.startswith("acfqp"):
            raise
        _fail(f"V119 base sequence reconstruction failed: {exc}")
    receipt_counts = namespace["_receipt"](
        document.get("program_branch_dependency_receipt"), candidate, base
    )
    receipt = document["program_branch_dependency_receipt"]
    plan = namespace["_plan_accounting"](base)
    genesis_hits = sum(
        row["abstract_plan"].get("planning_source")
        == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        and row["abstract_plan"].get("source_successor_state_id")
        == row["abstract_plan"].get("current_successor_state_id")
        for episode in base["episodes"]
        for row in episode["abstract_plan_receipts"]
    )
    dependency_compute = len(EPISODES) * (
        receipt_counts["compiled_factor_assignment_count"]
        + receipt_counts["canonical_action_catalogue_count"]
    )
    if (
        document.get("program_branch_dependency_receipt_id")
        != receipt.get("dependency_receipt_id")
        or document.get("dependency_receipt_rederivation_count") != len(EPISODES)
        or document.get("dependency_derivation_compute_events") != dependency_compute
        or document.get("same_epoch_genesis_authorized_cache_hit_count")
        != genesis_hits
        or genesis_hits <= 0
        or document.get("program_branch_cache_hit_count") != plan["branch_hits"]
        or document.get("actual_new_abstract_planning_compute_events")
        != plan["planning_compute"]
        or document.get("matched_uncached_abstract_planning_compute_events")
        != plan["uncached_compute"]
        or document.get("planning_compute_events_avoided_against_uncached")
        != plan["uncached_compute"] - plan["planning_compute"]
        or document.get(
            "zero_transition_reuse_requires_source_authorized_and_current_graph_identity"
        )
        is not True
        or document.get("cross_epoch_reuse_requires_epoch_authorization_chain")
        is not True
        or document.get("dependency_receipt_stable_across_model_epochs") is not True
        or document.get("ground_transition_accessed_during_dependency_derivation")
        is not False
        or document.get("query_local_exact_overlay_exclusively_discharges_safety")
        is not True
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("V119 sequence accounting or claim boundary changed")
    return {
        **receipt_counts,
        "dependency_derivation_compute_events": dependency_compute,
        "same_epoch_genesis_authorized_cache_hits": genesis_hits,
        "planning_compute": plan["planning_compute"],
        "uncached_compute": plan["uncached_compute"],
        "branch_hits": plan["branch_hits"],
    }


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    namespace: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_OCCURRENCE_V119_DOMAIN,
    )
    partial = document.get("partial_prior_acquisition")
    strict = document.get("strict_no_prior_complete_model_control")
    sequence = document.get("genesis_authorized_program_branch_sequence")
    if (
        document.get("schema") != "acfqp.source_unseen_residual_occurrence.v119"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(partial) is not dict
        or type(strict) is not dict
        or type(sequence) is not dict
    ):
        _fail("V119 occurrence identity changed")
    candidate_counts = _acquisition(partial, family, seed)
    _strict_control(strict, partial, family, seed)
    sequence_counts = _sequence(sequence, partial["candidate"], namespace)
    base = sequence["genesis_authorized_base_sequence"]
    accounting = {
        "partial_prior_acquisition_labels": partial["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base[
            "certificate_ground_support_labels_paid_once"
        ],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": sequence_counts["planning_compute"],
        "matched_uncached_planning_compute_events": sequence_counts[
            "uncached_compute"
        ],
        "planning_compute_events_avoided_against_uncached": sequence_counts[
            "uncached_compute"
        ]
        - sequence_counts["planning_compute"],
        "dependency_derivation_compute_events": sequence_counts[
            "dependency_derivation_compute_events"
        ],
        "same_epoch_genesis_authorized_cache_hits": sequence_counts[
            "same_epoch_genesis_authorized_cache_hits"
        ],
        "program_branch_cache_hits": sequence_counts["branch_hits"],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "source_unseen_dual_budget_family_present": True,
        "historical_factor_library_identity_frozen": True,
        "target_domain_source_absent_from_factor_library_source_closure": True,
        "partial_candidate_retains_unknown_higher_order_residual": candidate_counts[
            "unknown_residual_target_column_count"
        ]
        > 0,
        "minimum_reusable_factor_count_derived": candidate_counts[
            "compiled_factor_assignment_count"
        ]
        >= 3,
        "strict_control_uses_exact_partial_raw_prefix": True,
        "strict_control_outcome_retained_without_selection": True,
        "same_epoch_genesis_authorization_observed": sequence_counts[
            "same_epoch_genesis_authorized_cache_hits"
        ]
        > 0,
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in base["episodes"]
        ),
        "certificate_failure_only_query_discipline_clean": base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_matches_full_v105_rebuild": base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("genesis_authorized_program_branch_sequence_id")
        != sequence.get("sequence_id")
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("source_unseen_partial_world_model_pipeline_verified")
        != gate["passed"]
        or document.get("strict_complete_model_required_for_planning") is not False
        or document.get("strict_control_outcome_used_for_gate_selection") is not False
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get(
            "target_domain_source_absent_from_factor_library_source_closure"
        )
        is not True
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V119 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **candidate_counts,
        **accounting,
    }


def verify_source_unseen_residual_campaign_bytes_v119(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V119 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V119 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_CAMPAIGN_V119_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.source_unseen_residual_campaign.v119"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v118_success_campaign_id") != V118_CAMPAIGN_ID
        or document.get("v118_success_verification_id") != V118_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V119 campaign inventory changed")
    namespace = _v117_namespace()
    replay = [
        _occurrence(row, family, seed, namespace)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    accounting_keys = tuple(rows[0]["accounting"])
    accounting = {
        **{
            key: sum(row["accounting"][key] for row in rows)
            for key in accounting_keys
            if type(rows[0]["accounting"][key]) is int
        },
        "offline_factor_library_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "sample_efficiency_improvement_claimed": False,
        "scalar_cost_aggregation_performed": False,
    }
    ood = document.get("incompatible_schema_no_transfer_control")
    strict_ood = (
        type(ood) is dict
        and ood.get("exact_interface_match") is False
        and ood.get("learned_structure_prior_delivered") is False
        and ood.get("strict_ood_no_transfer") is True
    )
    passed = all(row["gate_passed"] for row in replay) and strict_ood
    gate = {
        "required_target_occurrence_count": len(TARGETS),
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "source_unseen_higher_order_residual_family_present": all(
            row["target_family"] == FAMILY for row in replay
        ),
        "every_occurrence_retains_unknown_residual_and_completes_planning": all(
            row["unknown_residual_target_column_count"] > 0
            and row["gate_passed"]
            for row in replay
        ),
        "same_epoch_genesis_authorization_verified": all(
            row["same_epoch_genesis_authorized_cache_hits"] > 0 for row in replay
        ),
        "strict_control_outcomes_retained_without_gate_selection": True,
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("target_occurrence_ids")
        != [row["occurrence_id"] for row in rows]
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get(
            "registered_source_unseen_partial_world_model_pipeline_verified"
        )
        != passed
        or document.get(
            "target_domain_source_absent_from_factor_library_source_closure"
        )
        is not True
        or document.get("strict_complete_model_required_for_planning") is not False
        or document.get("strict_control_outcome_used_for_gate_selection") is not False
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V119 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.source_unseen_residual_verification.v119",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v118_success_verification_id": V118_VERIFICATION_ID,
        "verification_status": "REGISTERED_V119_SOURCE_UNSEEN_PARTIAL_PIPELINE_VERIFIED",
        "producer_free_v119_content_graph_reconstruction": True,
        "producer_free_v113_sequence_and_v117_dependency_reconstruction": True,
        "producer_free_genesis_authorization_and_accounting_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_v119_full_ground_dynamics_rederivation_performed": False,
        "target_domain_source_absent_from_factor_library_source_closure": True,
        "strict_complete_model_required_for_planning": False,
        "strict_control_outcome_used_for_gate_selection": False,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "sample_efficiency_improvement_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
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


def freeze_source_unseen_residual_verification_v119(raw: bytes) -> bytes:
    payload = verify_source_unseen_residual_campaign_bytes_v119(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v119(
            domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_VERIFICATION_V119_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V119 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_source_unseen_residual_verification_v119",
    "verify_source_unseen_residual_campaign_bytes_v119",
)
