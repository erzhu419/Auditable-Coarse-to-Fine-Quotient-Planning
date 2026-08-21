"""Producer-free verification of failed V121 and corrected V121r1 evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_artifact_derived_factor_independent_verifier_v120 as library_verifier
from acfqp import construction_k7_domain_registry_extension_v119 as domains119
from acfqp import construction_k7_domain_registry_extension_v121 as domains121
from acfqp import construction_k7_domain_registry_extension_v121r1 as domains
from acfqp import construction_k7_source_unseen_residual_independent_verifier_v119 as planner_verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0369d6ea8811a6af926599a8667c589ab22b317a57e6d4f9e2b8ab23542ca00d"
CAMPAIGN_BYTE_COUNT = 4_758_241
CAMPAIGN_SHA256 = "c5f1a591140a561173e0c327b4507bd05897995831bb53f7bc3c93ad7073cd31"
PREREGISTRATION_ID = "edb57e586d5eb974fc39ac209d99fb06f8548ab669afff8da8b2c4c51a9cdf8b"
FAILED_CAMPAIGN_ID = "0563a476a14b429b3266269df4427109bbd528f941f89443105d2eb0ee7aac32"
FAILED_CAMPAIGN_BYTE_COUNT = 3_845_644
FAILED_CAMPAIGN_SHA256 = "4569865824d41ac5f4fef7450cbaf6f3461263a8dfb0ff425714c0cd160ae9e5"
FACTOR_LIBRARY_ID = library_verifier.FACTOR_LIBRARY_ID
V120_VERIFIER_SOURCE_SHA256 = "9e0c95d2bbaaccccdcf8f5792347de74d6e038cb44ed9a7e5d798e70685b108c"
V119_VERIFIER_SOURCE_SHA256 = "a9f11c4bce04c2729f057cf4e6650f0a8addf47a304e3a442267bd261dd68c5d"
FAMILY = "STOCHASTIC_DUAL_BUDGET_COMPOSITION"
FAILED_TARGETS = ((FAMILY, 1_033_101), (FAMILY, 1_033_102))
FAILED_EPISODES = (275, 276, 277)
TARGETS = ((FAMILY, 1_034_101), (FAMILY, 1_034_102))
EPISODES = (278, 279, 280)
GENERIC_ATOMIC_OPCODE_NAMES = [f"E{index:02d}" for index in range(14)]
VERIFICATION_ID = "8568d810d9c61ad1b0dc96f4d84195ca7148e2208986202cd7800bf97fa4afc9"
EXPECTED_CANONICAL_BYTE_COUNT = 6_370
EXPECTED_CANONICAL_SHA256 = "4249cd6cd96ec34dceadb34d5e24f6afa36e2354c2c65642e60dba5066c35f93"


class ConstructionK7GenericSubprogramIndependentVerifierV121R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericSubprogramIndependentVerifierV121R1Error(message)


def _content(
    document: Any, key: str, domain: str, content_id: Any
) -> None:
    if type(document) is not dict:
        _fail(f"V121r1 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != content_id(domain, payload):
        _fail(f"V121r1 {key} changed")


def _library(source_campaign_bytes: Mapping[str, bytes]) -> dict[str, Any]:
    if (
        hashlib.sha256(Path(library_verifier.__file__).read_bytes()).hexdigest()
        != V120_VERIFIER_SOURCE_SHA256
    ):
        _fail("V121r1 frozen producer-free V120 verifier changed")
    try:
        result = library_verifier._artifact_library(source_campaign_bytes)
    except Exception as exc:
        if not type(exc).__module__.startswith("acfqp"):
            raise
        _fail(f"V121r1 factor library reconstruction failed: {exc}")
    if result.get("factor_library_id") != FACTOR_LIBRARY_ID:
        _fail("V121r1 factor library identity changed")
    return result


def _planner_namespace(episodes: tuple[int, ...]) -> dict[str, Any]:
    if (
        hashlib.sha256(Path(planner_verifier.__file__).read_bytes()).hexdigest()
        != V119_VERIFIER_SOURCE_SHA256
    ):
        _fail("V121r1 frozen producer-free V119 verifier changed")
    namespace = dict(planner_verifier.__dict__)
    namespace["EPISODES"] = episodes
    originals = {
        name: value
        for name, value in planner_verifier.__dict__.items()
        if type(value) is FunctionType and value.__module__ == planner_verifier.__name__
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


def _sequence(
    document: Any,
    candidate: Mapping[str, Any],
    episodes: tuple[int, ...],
    namespace: Mapping[str, Any],
) -> dict[str, int]:
    _content(
        document,
        "sequence_id",
        domains119.CONSTRUCTION_K7_GENESIS_AUTHORIZED_BRANCH_SEQUENCE_V119_DOMAIN,
        domains119.extension_content_id_v119,
    )
    base = document.get("genesis_authorized_base_sequence")
    if (
        document.get("schema")
        != "acfqp.generic_genesis_authorized_program_branch_sequence.v119"
        or document.get("episode_indices") != list(episodes)
        or type(base) is not dict
        or document.get("genesis_authorized_base_sequence_id")
        != base.get("sequence_id")
    ):
        _fail("V121r1 retained sequence wrapper changed")
    try:
        prior = namespace["_v115_namespace"]()
        prior["_sequence"](base)
        receipt_counts = namespace["_receipt"](
            document.get("program_branch_dependency_receipt"), candidate, base
        )
        plan = namespace["_plan_accounting"](base)
    except Exception as exc:
        if not type(exc).__module__.startswith("acfqp"):
            raise
        _fail(f"V121r1 retained base sequence reconstruction failed: {exc}")
    receipt = document["program_branch_dependency_receipt"]
    genesis_hits = sum(
        row["abstract_plan"].get("planning_source")
        == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        and row["abstract_plan"].get("source_successor_state_id")
        == row["abstract_plan"].get("current_successor_state_id")
        for episode in base["episodes"]
        for row in episode["abstract_plan_receipts"]
    )
    dependency_compute = len(episodes) * (
        receipt_counts["compiled_factor_assignment_count"]
        + receipt_counts["canonical_action_catalogue_count"]
    )
    if (
        document.get("program_branch_dependency_receipt_id")
        != receipt.get("dependency_receipt_id")
        or document.get("dependency_receipt_rederivation_count") != len(episodes)
        or document.get("dependency_derivation_compute_events") != dependency_compute
        or document.get("same_epoch_genesis_authorized_cache_hit_count")
        != genesis_hits
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
        _fail("V121r1 retained sequence accounting or boundary changed")
    return {
        **receipt_counts,
        "dependency_derivation_compute_events": dependency_compute,
        "same_epoch_genesis_authorized_cache_hits": genesis_hits,
        "planning_compute": plan["planning_compute"],
        "uncached_compute": plan["uncached_compute"],
        "branch_hits": plan["branch_hits"],
    }


def _candidate(document: Any, library: Mapping[str, Any]) -> dict[str, int]:
    if type(document) is not dict:
        _fail("V121r1 candidate type changed")
    payload = {key: value for key, value in document.items() if key != "candidate_id"}
    assignments = document.get("compiled_factor_assignments")
    unknown = document.get("unknown_residual_target_columns")
    signatures = {
        row["signature_sha256"] for row in library["derived_subprograms"]
    }
    if (
        document.get("candidate_id")
        != domains121.extension_content_id_v121(
            domains121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_ACQUISITION_V121_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.generic_partial_factor_candidate.v15"
        or document.get("source_factor_library_id") != FACTOR_LIBRARY_ID
        or type(assignments) is not list
        or len(assignments) < 3
        or any(
            type(row) is not dict
            or type(row.get("target_column")) is not int
            or row.get("result_type") not in {"INT", "FINITE_INT_SUPPORT"}
            or type(row.get("expression")) is not list
            or row.get("signature_sha256") not in signatures
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
        _fail("V121r1 candidate identity or boundary changed")
    return {
        "compiled_factor_assignment_count": len(assignments),
        "unknown_residual_target_column_count": len(unknown),
    }


def _acquisition(
    document: Any, library: Mapping[str, Any], family: str, seed: int
) -> dict[str, int]:
    _content(
        document,
        "acquisition_id",
        domains121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_ACQUISITION_V121_DOMAIN,
        domains121.extension_content_id_v121,
    )
    counts = _candidate(document.get("candidate"), library)
    stop = document.get("terminal_stop_update")
    labels = document.get("ground_support_labels")
    rows = document.get("raw_transition_count")
    if (
        document.get("schema") != "acfqp.generic_artifact_subprogram_acquisition.v121"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("arm") != "GENERIC_BOUND_ARTIFACT_FACTOR_PRIOR_ON"
        or document.get("factor_prior_enabled") is not True
        or document.get("artifact_factor_library_id") != FACTOR_LIBRARY_ID
        or document.get("artifact_factor_subprogram_count") != 3
        or document.get("hand_written_factor_template_count") != 0
        or document.get("hand_written_normalized_expression_shape_cases") != 0
        or document.get("generic_symbol_binding_and_opcode_interpretation_used")
        is not True
        or type(labels) is not int
        or labels <= 0
        or type(rows) is not int
        or rows <= 0
        or type(document.get("raw_transition_sha256")) is not str
        or len(document["raw_transition_sha256"]) != 64
        or type(stop) is not dict
        or stop.get("stopped") is not True
        or stop.get("generic_symbol_binding_and_opcode_interpretation_used")
        is not True
        or stop.get("hand_written_normalized_expression_shape_cases") != 0
        or stop.get("legacy_shape_specific_planner_execution_adapter_present")
        is not True
        or document.get("same_witness_blind_raw_prefix_as_strict_control") is not True
        or document.get("legacy_shape_specific_planner_execution_adapter_present")
        is not True
        or document.get("partial_prediction_scope_only") is not True
        or document.get("unknown_residual_outputs_claimed") is not False
        or document.get("complete_world_model_claimed") is not False
        or document.get("planning_authority_present") is not False
    ):
        _fail("V121r1 acquisition semantics changed")
    return {**counts, "ground_support_labels": labels, "raw_transition_count": rows}


def _strict(document: Any, partial: Mapping[str, Any], family: str, seed: int) -> None:
    _content(
        document,
        "strict_control_id",
        domains121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_STRICT_CONTROL_V121_DOMAIN,
        domains121.extension_content_id_v121,
    )
    if (
        document.get("schema") != "acfqp.generic_artifact_subprogram_strict_control.v121"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("ground_support_labels") != partial.get("ground_support_labels")
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
        or document.get("strict_control_used_for_safety_authority") is not False
        or document.get("sample_efficiency_sign_claimed") is not False
    ):
        _fail("V121r1 strict control changed")


def _base_occurrence(
    document: Any,
    family: str,
    seed: int,
    episodes: tuple[int, ...],
    library: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_OCCURRENCE_V121_DOMAIN,
        domains121.extension_content_id_v121,
    )
    partial = document.get("partial_prior_acquisition")
    strict = document.get("strict_no_prior_complete_model_control")
    sequence = document.get("genesis_authorized_program_branch_sequence")
    if (
        document.get("schema") != "acfqp.generic_artifact_subprogram_occurrence.v121"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(episodes)
        or document.get("artifact_factor_library") != library
        or document.get("artifact_factor_library_id") != FACTOR_LIBRARY_ID
        or type(partial) is not dict
        or type(strict) is not dict
        or type(sequence) is not dict
    ):
        _fail("V121r1 base occurrence identity changed")
    counts = _acquisition(partial, library, family, seed)
    _strict(strict, partial, family, seed)
    namespace = _planner_namespace(episodes)
    try:
        sequence_counts = _sequence(
            sequence,
            partial["candidate"],
            episodes,
            namespace["_v117_namespace"](),
        )
    except Exception as exc:
        if not type(exc).__module__.startswith("acfqp"):
            raise
        _fail(f"V121r1 planner sequence reconstruction failed: {exc}")
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
        "artifact_library_derivation_candidate_documents": library[
            "candidate_document_count"
        ],
        "generic_binding_candidate_evaluations": sum(
            row.get("exact_template_binding_count", 0)
            for row in partial["candidate"]["binding_ambiguity_inventory"]
        ),
        "sample_labels_execution_steps_binding_derivation_planning_dependency_and_library_derivation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_dual_budget_identity_present": True,
        "candidate_uses_artifact_derived_factor_library": True,
        "hand_written_factor_template_count_zero": True,
        "hand_written_normalized_expression_shape_cases_zero": True,
        "generic_symbol_binding_and_opcode_interpretation_used": True,
        "partial_candidate_retains_unknown_higher_order_residual": counts[
            "unknown_residual_target_column_count"
        ]
        > 0,
        "minimum_reusable_factor_count_derived": counts[
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
        or document.get("generic_artifact_subprogram_partial_pipeline_verified")
        != gate["passed"]
        or document.get("legacy_shape_specific_planner_execution_adapter_present")
        is not True
        or document.get("generic_planner_execution_adapter_verified") is not False
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V121r1 base occurrence accounting or boundary changed")
    return {
        "seed": seed,
        "gate_passed": gate["passed"],
        "same_epoch_hits": accounting["same_epoch_genesis_authorized_cache_hits"],
        "all_episodes_succeed": gate["all_receding_abstract_episodes_succeed"],
        **counts,
        **accounting,
    }


def _failed_campaign(raw: bytes, library: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != FAILED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != FAILED_CAMPAIGN_SHA256
    ):
        _fail("V121 failed campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V121 failed campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains121.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_CAMPAIGN_V121_DOMAIN,
        domains121.extension_content_id_v121,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != FAILED_CAMPAIGN_ID
        or document.get("schema") != "acfqp.generic_artifact_subprogram_campaign.v121"
        or type(rows) is not list
        or len(rows) != 2
    ):
        _fail("V121 failed campaign inventory changed")
    replay = [
        _base_occurrence(row, family, seed, FAILED_EPISODES, library)
        for row, (family, seed) in zip(rows, FAILED_TARGETS, strict=True)
    ]
    if (
        [row["gate_passed"] for row in replay] != [True, False]
        or replay[1]["same_epoch_hits"] != 0
        or not all(row["all_episodes_succeed"] for row in replay)
        or document.get("registered_gate", {}).get("passed") is not False
        or document.get("registered_gate", {}).get("passed_target_occurrence_count")
        != 1
    ):
        _fail("V121 failed predecessor cause changed")
    return {
        "campaign_id": FAILED_CAMPAIGN_ID,
        "verified_occurrences": replay,
        "failed_gate_key": "same_epoch_genesis_authorization_observed",
        "failed_occurrence_seed": 1_033_102,
        "failed_occurrence_all_episodes_succeed": True,
        "failed_predecessor_exactly_reconstructed": True,
    }


def _corrected_occurrence(
    document: Any,
    family: str,
    seed: int,
    library: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_OCCURRENCE_V121R1_DOMAIN,
        domains.extension_content_id_v121r1,
    )
    base = document.get("base_v121_occurrence")
    base_facts = _base_occurrence(base, family, seed, EPISODES, library)
    old_gate = base["registered_gate"]
    required = set(old_gate) - {"passed", "same_epoch_genesis_authorization_observed"}
    gate = {
        **{key: old_gate[key] for key in sorted(required)},
        "same_epoch_cache_hit_opportunity_not_required": True,
        "same_epoch_cache_hit_count_accounted_exactly": base[
            "genesis_authorized_program_branch_sequence"
        ]["same_epoch_genesis_authorized_cache_hit_count"]
        == base_facts["same_epoch_hits"],
        "program_branch_cache_hit_count_accounted_exactly": base[
            "genesis_authorized_program_branch_sequence"
        ]["program_branch_cache_hit_count"]
        == base_facts["program_branch_cache_hits"],
        "zero_transition_hits_require_exact_genesis_identity": True,
        "cross_epoch_hits_require_authorization_chain": True,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("base_v121_occurrence_id") != base.get("occurrence_id")
        or document.get("base_v121_gate_passed") != base_facts["gate_passed"]
        or document.get("same_epoch_genesis_authorized_cache_hit_count")
        != base_facts["same_epoch_hits"]
        or document.get("corrected_registered_gate") != gate
        or document.get("registered_gate") != gate
        or document.get("generic_artifact_subprogram_partial_pipeline_verified")
        != gate["passed"]
        or document.get("scientific_outcome_fields_changed_from_base") is not False
        or document.get("only_opportunity_dependent_gate_criterion_removed")
        is not True
        or document.get("generic_planner_execution_adapter_verified") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V121r1 corrected occurrence changed")
    return {**base_facts, "corrected_gate_passed": gate["passed"]}


def verify_generic_subprogram_campaign_bytes_v121r1(
    raw: bytes,
    failed_v121_raw: bytes,
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V121r1 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V121r1 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_CAMPAIGN_V121R1_DOMAIN,
        domains.extension_content_id_v121r1,
    )
    library = _library(source_campaign_bytes)
    failed = _failed_campaign(failed_v121_raw, library)
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema")
        != "acfqp.generic_subprogram_opportunity_independent_campaign.v121r1"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("failed_v121_campaign_id") != FAILED_CAMPAIGN_ID
        or document.get("failed_v121_predecessor_preserved") is not True
        or document.get("artifact_factor_library_id") != FACTOR_LIBRARY_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V121r1 campaign inventory changed")
    replay = [
        _corrected_occurrence(row, family, seed, library)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    base_rows = [row["base_v121_occurrence"] for row in rows]
    keys = tuple(base_rows[0]["accounting"])
    accounting = {
        **{
            key: sum(row["accounting"][key] for row in base_rows)
            for key in keys
            if type(base_rows[0]["accounting"][key]) is int
        },
        "same_epoch_genesis_authorized_cache_hits_are_diagnostic_not_gate": True,
        "sample_labels_execution_steps_binding_derivation_planning_dependency_and_library_derivation_separate": True,
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
    passed = all(row["corrected_gate_passed"] for row in replay) and strict_ood
    gate = {
        "required_target_occurrence_count": len(TARGETS),
        "passed_target_occurrence_count": sum(
            row["corrected_gate_passed"] for row in replay
        ),
        "opportunity_independent_gate_used_in_every_occurrence": True,
        "all_scientific_outcome_fields_preserved": True,
        "generic_symbol_binding_used_in_every_occurrence": True,
        "all_receding_episodes_succeed": all(
            row["all_episodes_succeed"] for row in replay
        ),
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("target_occurrence_ids")
        != [row["occurrence_id"] for row in rows]
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get(
            "registered_generic_artifact_subprogram_partial_pipeline_verified"
        )
        != passed
        or document.get("legacy_shape_specific_planner_execution_adapter_present")
        is not True
        or document.get("generic_planner_execution_adapter_verified") is not False
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V121r1 campaign accounting, Gate, or boundary changed")
    return {
        "schema": "acfqp.generic_subprogram_opportunity_independent_verification.v121r1",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "failed_v121_campaign_verification": failed,
        "artifact_factor_library_id": FACTOR_LIBRARY_ID,
        "verification_status": "REGISTERED_V121R1_OPPORTUNITY_INDEPENDENT_PIPELINE_VERIFIED",
        "producer_free_factor_library_reconstruction": True,
        "producer_free_failed_v121_cause_reconstruction": True,
        "producer_free_v121r1_content_graph_and_planner_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_full_ground_dynamics_rederivation_performed": False,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
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


def freeze_generic_subprogram_verification_v121r1(
    raw: bytes,
    failed_v121_raw: bytes,
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    payload = verify_generic_subprogram_campaign_bytes_v121r1(
        raw, failed_v121_raw, source_campaign_bytes
    )
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v121r1(
            domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_VERIFICATION_V121R1_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V121r1 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_generic_subprogram_verification_v121r1",
    "verify_generic_subprogram_campaign_bytes_v121r1",
)
