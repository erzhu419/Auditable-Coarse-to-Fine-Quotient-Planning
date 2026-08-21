"""Producer-free verification of V117 dependency-derived branch retention."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v115 as domains115
from acfqp import construction_k7_domain_registry_extension_v116 as domains116
from acfqp import construction_k7_domain_registry_extension_v117 as domains
from acfqp import construction_k7_projected_program_memo_independent_verifier_v115 as base_verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "5817b88896699206fcb08ed64111fc993691515fd0461e518c956a04de283b9d"
CAMPAIGN_BYTE_COUNT = 7_794_238
CAMPAIGN_SHA256 = "061a653cf1048fe01420a3159d4389b9b81eb573f97c5acfbd66fcf618d60039"
PREREGISTRATION_ID = "9aafb1d13daba2078511556de4f7f6b1f12f3519a93100e6c9ebc11d4b957240"
V116_CAMPAIGN_ID = "2ffeebf8f989a944afce3144aeed8aeba4eda529bce3f3bfe7be19cea4a8e406"
V116_VERIFICATION_ID = "3dff7bec35c6428e7463571b53be48166cf550e624bc36e2223c84a511a06d30"
V115_VERIFIER_SOURCE_SHA256 = "c00a56add0fd915420d8f18ec92b79a4d4fa8420647719c522e51cd4eacfa6f2"
V115_CAMPAIGN_ID = "d2d061867f8bfc3d2c1abe439537ad0a1432738bf2db4242ef4d35f2c41dfcfe"
V115_VERIFICATION_ID = "3cf6f79e13fdfa3a83f7e837106f2247659e5f1c6cb0e2b9d67fd2023e25d8f9"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_029_101),
    ("COUPLED_EXCHANGE", 1_029_201),
    ("MAINTENANCE_CASCADE", 1_029_301),
)
EPISODES = (254, 255, 256)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7DependencyDerivedProgramBranchIndependentVerifierV117Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DependencyDerivedProgramBranchIndependentVerifierV117Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V117 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v117(domain, payload):
        _fail(f"V117 {key} changed")


def _v115_namespace() -> dict[str, Any]:
    if (
        hashlib.sha256(Path(base_verifier.__file__).read_bytes()).hexdigest()
        != V115_VERIFIER_SOURCE_SHA256
        or base_verifier.EPISODES != (241, 242, 243)
        or base_verifier.CAMPAIGN_ID != V115_CAMPAIGN_ID
        or base_verifier.VERIFICATION_ID != V115_VERIFICATION_ID
    ):
        _fail("V117 frozen producer-free V115 verifier changed")
    namespace = dict(base_verifier.__dict__)
    namespace["EPISODES"] = EPISODES
    originals = {
        name: value
        for name, value in base_verifier.__dict__.items()
        if type(value) is FunctionType and value.__module__ == base_verifier.__name__
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


def _receipt(
    receipt: Any,
    candidate: Mapping[str, Any],
    base: Mapping[str, Any],
) -> dict[str, int]:
    keys = {
        "schema",
        "partial_candidate_id",
        "layout_id",
        "compiled_factor_assignments",
        "canonical_action_catalogue",
        "successor_operator",
        "minimal_semantic_dependencies",
        "excluded_model_epoch_fields",
        "dependency_set_derived_from_compiled_operator_arguments",
        "model_epoch_identity_used_as_dependency",
        "ground_transition_rows_used_as_dependency",
        "cache_or_receipt_used_as_safety_authority",
        "dependency_receipt_id",
    }
    if type(receipt) is not dict or set(receipt) != keys:
        _fail("V117 dependency receipt schema changed")
    payload = {
        key: value for key, value in receipt.items() if key != "dependency_receipt_id"
    }
    if (
        receipt.get("schema") != "acfqp.program_branch_dependency_receipt.v117"
        or receipt.get("dependency_receipt_id")
        != domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_PROGRAM_BRANCH_DEPENDENCY_RECEIPT_V117_DOMAIN,
            payload,
        )
        or receipt.get("partial_candidate_id") != candidate.get("candidate_id")
        or receipt.get("layout_id") != candidate.get("layout", {}).get("layout_id")
        or receipt.get("compiled_factor_assignments")
        != candidate.get("compiled_factor_assignments")
        or receipt.get("successor_operator")
        != "PARTIAL_FACTOR_SUCCESSOR_PROJECTIONS_V15"
        or receipt.get("minimal_semantic_dependencies")
        != [
            "COMPILED_FACTOR_ASSIGNMENTS",
            "CANONICAL_ACTION_FIELDS",
            "PROJECTED_STATE",
            "ACTION_KEY",
        ]
        or receipt.get("excluded_model_epoch_fields")
        != [
            "OBSERVATION_QUOTIENT_GRAPH_ID",
            "RAW_ROW_IDENTITY_SHA256",
            "TERMINAL_PROJECTION_RULE",
        ]
        or receipt.get("dependency_set_derived_from_compiled_operator_arguments")
        is not True
        or receipt.get("model_epoch_identity_used_as_dependency") is not False
        or receipt.get("ground_transition_rows_used_as_dependency") is not False
        or receipt.get("cache_or_receipt_used_as_safety_authority") is not False
    ):
        _fail("V117 dependency receipt semantics changed")
    catalogue = receipt.get("canonical_action_catalogue")
    if (
        type(catalogue) is not list
        or not catalogue
        or any(
            type(row) is not dict
            or set(row) != {"action_key", "canonical_anonymous_fields"}
            or type(row["action_key"]) is not int
            or type(row["canonical_anonymous_fields"]) is not list
            or not row["canonical_anonymous_fields"]
            or any(type(value) is not int for value in row["canonical_anonymous_fields"])
            for row in catalogue
        )
        or [row["action_key"] for row in catalogue]
        != sorted({row["action_key"] for row in catalogue})
    ):
        _fail("V117 canonical action dependency inventory changed")
    by_key = {row["action_key"]: row["canonical_anonymous_fields"] for row in catalogue}
    mapping = candidate["layout"]["action_canonical_to_raw"]
    observed: dict[int, list[int]] = {}
    rows = list(base["persistent_exact_overlay_rows"])
    for episode in base["episodes"]:
        rows.extend(episode["raw_incremental_transition_rows"])
    for row in rows:
        action = row["selected_action"]
        canonical = [action["anonymous_fields"][index] for index in mapping]
        prior = observed.setdefault(action["action_key"], canonical)
        if prior != canonical or by_key.get(action["action_key"]) != canonical:
            _fail("V117 observed action does not join dependency catalogue")
    if not observed:
        _fail("V117 dependency receipt lacks observed action join")
    return {
        "compiled_factor_assignment_count": len(
            receipt["compiled_factor_assignments"]
        ),
        "canonical_action_catalogue_count": len(catalogue),
        "observed_action_catalogue_join_count": len(observed),
    }


def _plan_accounting(base: Mapping[str, Any]) -> dict[str, int]:
    plans = [
        row["abstract_plan"]
        for episode in base["episodes"]
        for row in episode["abstract_plan_receipts"]
    ]
    return {
        "planning_compute": sum(
            row["abstract_support_branch_evaluations"] for row in plans
        ),
        "branch_hits": sum(
            row.get("embedded_projected_plan", {}).get(
                "projected_branch_cache_hit_count", 0
            )
            for row in plans
        ),
        "uncached_compute": sum(
            row.get("embedded_projected_plan", {}).get(
                "matched_uncached_projected_planning_compute_events",
                row["abstract_support_branch_evaluations"],
            )
            for row in plans
        ),
    }


def _negative_control(receipt: Mapping[str, Any]) -> dict[str, Any]:
    changed = copy.deepcopy(dict(receipt))
    payload = {
        key: value for key, value in changed.items() if key != "dependency_receipt_id"
    }
    payload["canonical_action_catalogue"][0]["canonical_anonymous_fields"][0] += 1
    changed_id = domains.extension_content_id_v117(
        domains.CONSTRUCTION_K7_PROGRAM_BRANCH_DEPENDENCY_RECEIPT_V117_DOMAIN,
        payload,
    )
    return {
        "schema": "acfqp.program_branch_dependency_change_control.v117",
        "changed_dependency_receipt_id": changed_id,
        "different_from_observed_receipt": changed_id
        != receipt["dependency_receipt_id"],
        "cache_retention_authorized": False,
        "cache_invalidation_required": True,
        "ground_outcome_executed_for_negative_control": False,
    }


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    verifier: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_OCCURRENCE_V117_DOMAIN,
    )
    derived = document.get("dependency_derived_program_branch_sequence")
    matched = document.get("matched_v116_cross_epoch_sequence")
    if (
        document.get("schema")
        != "acfqp.dependency_derived_program_branch_occurrence.v117"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(derived) is not dict
        or type(matched) is not dict
    ):
        _fail("V117 occurrence identity changed")
    _content(
        derived,
        "sequence_id",
        domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_SEQUENCE_V117_DOMAIN,
    )
    matched_payload = {key: value for key, value in matched.items() if key != "sequence_id"}
    if matched.get("sequence_id") != domains116.extension_content_id_v116(
        domains116.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_SEQUENCE_V116_DOMAIN,
        matched_payload,
    ):
        _fail("V117 embedded V116 sequence wrapper changed")
    derived_base = derived["dependency_derived_program_branch_base_sequence"]
    matched_base = matched["cross_epoch_program_branch_base_sequence"]
    if (
        derived.get("dependency_derived_program_branch_base_sequence_id")
        != derived_base.get("sequence_id")
        or matched.get("cross_epoch_program_branch_base_sequence_id")
        != matched_base.get("sequence_id")
        or document.get("dependency_derived_program_branch_sequence_id")
        != derived.get("sequence_id")
        or document.get("matched_v116_cross_epoch_sequence_id")
        != matched.get("sequence_id")
    ):
        _fail("V117 sequence join changed")
    try:
        verifier["_sequence"](derived_base)
        verifier["_sequence"](matched_base)
    except base_verifier.ConstructionK7ProjectedProgramMemoIndependentVerifierV115Error as exc:
        _fail(f"V117 embedded sequence reconstruction failed: {exc}")
    if derived_base != matched_base:
        _fail("V117 dependency-derived sequence differs from matched V116")
    candidate = document.get("partial_acquisition", {}).get("candidate")
    if type(candidate) is not dict:
        _fail("V117 candidate evidence changed")
    receipt_counts = _receipt(
        derived.get("program_branch_dependency_receipt"), candidate, derived_base
    )
    receipt = derived["program_branch_dependency_receipt"]
    if (
        derived.get("program_branch_dependency_receipt_id")
        != receipt["dependency_receipt_id"]
        or document.get("dependency_change_no_outcome_control")
        != _negative_control(receipt)
    ):
        _fail("V117 dependency receipt or negative control join changed")
    plan = _plan_accounting(derived_base)
    dependency_compute = len(EPISODES) * (
        receipt_counts["compiled_factor_assignment_count"]
        + receipt_counts["canonical_action_catalogue_count"]
    )
    if (
        derived.get("dependency_receipt_rederivation_count") != len(EPISODES)
        or derived.get("dependency_derivation_compute_events") != dependency_compute
        or derived.get("model_epoch_transition_count")
        != len(derived_base["model_epoch_transition_receipts"])
        or derived.get("dependency_receipt_stable_across_model_epochs") is not True
        or derived.get("program_branch_cache_retained_only_after_exact_dependency_match")
        is not True
        or derived.get("program_branch_cache_hit_count") != plan["branch_hits"]
        or derived.get("actual_new_abstract_planning_compute_events")
        != plan["planning_compute"]
        or derived.get("matched_uncached_abstract_planning_compute_events")
        != plan["uncached_compute"]
        or derived.get("planning_compute_events_avoided_against_uncached")
        != plan["uncached_compute"] - plan["planning_compute"]
    ):
        _fail("V117 sequence dependency or planning accounting changed")
    accounting = {
        "initial_acquisition_labels": derived_base[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": derived_base[
            "certificate_ground_support_labels_paid_once"
        ],
        "dependency_derived_lifetime_target_labels": derived_base[
            "lifetime_target_ground_support_labels"
        ],
        "matched_v116_lifetime_target_labels": matched_base[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": derived_base["execution_step_count"],
        "dependency_derived_planning_compute_events": plan["planning_compute"],
        "matched_v116_planning_compute_events": plan["planning_compute"],
        "matched_uncached_v113_planning_compute_events": plan["uncached_compute"],
        "planning_compute_events_avoided_against_uncached_v113": plan[
            "uncached_compute"
        ]
        - plan["planning_compute"],
        "dependency_derived_program_branch_cache_hits": plan["branch_hits"],
        "matched_v116_program_branch_cache_hits": plan["branch_hits"],
        "dependency_receipt_rederivation_count": len(EPISODES),
        "dependency_derivation_compute_events": dependency_compute,
        "model_epoch_transition_count": len(
            derived_base["model_epoch_transition_receipts"]
        ),
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "dependency_derived_and_v116_sequences_byte_exact": True,
        "dependency_derived_and_v116_target_labels_equal": True,
        "dependency_derived_and_v116_planning_compute_equal": True,
        "dependency_receipt_rederived_at_every_episode": True,
        "dependency_receipt_stable_across_model_epochs": True,
        "changed_dependency_forces_cache_invalidation_without_outcome_execution": True,
        "certificate_failure_only_query_discipline_clean": derived_base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_still_matches_full_v105_rebuild": derived_base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_still_consumes_compiled_model_without_raw_rows": derived_base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("dependency_derived_branch_retention_verified")
        != gate["passed"]
        or document.get("ground_distinctions_only_after_certificate_failure_verified")
        != gate["passed"]
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V117 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **receipt_counts,
        **accounting,
    }


def verify_dependency_derived_program_branch_campaign_bytes_v117(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V117 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V117 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_CAMPAIGN_V117_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema")
        != "acfqp.dependency_derived_program_branch_campaign.v117"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v116_success_campaign_id") != V116_CAMPAIGN_ID
        or document.get("v116_success_verification_id") != V116_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V117 campaign inventory changed")
    verifier = _v115_namespace()
    replay = [
        _occurrence(row, family, seed, verifier)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    numeric_keys = tuple(
        key
        for key, value in replay[0].items()
        if type(value) is int and key not in ("seed", "gate_passed")
    )
    numeric = {key: sum(row[key] for row in replay) for key in numeric_keys}
    accounting_keys = tuple(rows[0]["accounting"])
    accounting = {
        **{
            key: sum(row["accounting"][key] for row in rows)
            for key in accounting_keys
            if type(rows[0]["accounting"][key]) is int
        },
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    family_counts = {
        family: sum(row["target_family"] == family for row in replay)
        for family, _seed in TARGETS
    }
    ood = document.get("incompatible_schema_no_transfer_control")
    strict_ood = (
        type(ood) is dict
        and ood.get("exact_interface_match") is False
        and ood.get("learned_structure_prior_delivered") is False
        and ood.get("strict_ood_no_transfer") is True
    )
    passed = (
        all(row["gate_passed"] for row in replay)
        and all(family_counts.values())
        and accounting["dependency_derived_planning_compute_events"]
        == accounting["matched_v116_planning_compute_events"]
        and strict_ood
    )
    gate = {
        "required_target_occurrence_count": len(TARGETS),
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "required_target_family_counts": family_counts,
        "all_three_registered_structural_families_present": all(
            family_counts.values()
        ),
        "every_occurrence_matches_v116_sequence_bytes_and_compute": all(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_rederives_exact_dependency_and_rejects_changed_dependency": all(
            row["gate_passed"] for row in replay
        ),
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("registered_dependency_derived_branch_retention_verified")
        != passed
        or document.get("ground_distinctions_only_after_certificate_failure_verified")
        != passed
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V117 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.dependency_derived_program_branch_verification.v117",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v116_success_verification_id": V116_VERIFICATION_ID,
        "verification_status": "REGISTERED_V117_DEPENDENCY_DERIVED_BRANCH_RETENTION_VERIFIED",
        "producer_free_v117_content_graph_reconstruction": True,
        "producer_free_v115_sequence_semantic_reconstruction": True,
        "producer_free_dependency_receipt_content_and_observed_action_join": True,
        "producer_free_negative_dependency_control_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_v117_full_dynamics_rederivation_performed": False,
        "frozen_v116_delta_verification_remains_predecessor": True,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "verified_dependency_receipt_assignment_count": numeric[
            "compiled_factor_assignment_count"
        ],
        "verified_dependency_receipt_action_count": numeric[
            "canonical_action_catalogue_count"
        ],
        "verified_observed_action_join_count": numeric[
            "observed_action_catalogue_join_count"
        ],
        "registered_gate_independently_verified": passed,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_dependency_derived_program_branch_verification_v117(raw: bytes) -> bytes:
    payload = verify_dependency_derived_program_branch_campaign_bytes_v117(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_VERIFICATION_V117_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V117 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_dependency_derived_program_branch_verification_v117",
    "verify_dependency_derived_program_branch_campaign_bytes_v117",
)
