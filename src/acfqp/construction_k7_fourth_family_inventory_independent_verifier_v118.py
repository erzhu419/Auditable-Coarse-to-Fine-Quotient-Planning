"""Producer-free verification of V118 fourth-family inventory evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains59
from acfqp import construction_k7_domain_registry_extension_v116 as domains116
from acfqp import construction_k7_domain_registry_extension_v117 as domains117
from acfqp import construction_k7_domain_registry_extension_v118 as domains
from acfqp import construction_k7_dependency_derived_program_branch_independent_verifier_v117 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0ab03c02a8b5b795860c5c96943204f8553fc6836e7dab92ef753c1fe6d86df1"
CAMPAIGN_BYTE_COUNT = 2_986_273
CAMPAIGN_SHA256 = "9afbade52f4b553ad5696e769ba6f8f1faced07fbb11b07b0f8a59991961e19d"
PREREGISTRATION_ID = "6bfe911dc767829058fe00b5887ce6394aeea40baec7cbfbedb3c56ad97affa7"
V117_CAMPAIGN_ID = "5817b88896699206fcb08ed64111fc993691515fd0461e518c956a04de283b9d"
V117_VERIFICATION_ID = "c8a9d342192a29d50e299121b7e1d35784cd3c8219e1e99757a111174ff829ef"
V117_VERIFIER_SOURCE_SHA256 = "4ee4caa5e7a667d66944d34d1a37c10def49e0381d05fb86553109581e476bde"
FAMILY = "STOCHASTIC_INVENTORY_ASSEMBLY"
TARGETS = ((FAMILY, 1_030_101), (FAMILY, 1_030_102))
EPISODES = (257, 258, 259)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7FourthFamilyInventoryIndependentVerifierV118Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilyInventoryIndependentVerifierV118Error(message)


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V118 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v118(domain, payload):
        _fail(f"V118 {key} changed")


def _v117_namespace() -> dict[str, Any]:
    if (
        hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest()
        != V117_VERIFIER_SOURCE_SHA256
        or previous.EPISODES != (254, 255, 256)
        or previous.CAMPAIGN_ID != V117_CAMPAIGN_ID
        or previous.VERIFICATION_ID != V117_VERIFICATION_ID
    ):
        _fail("V118 frozen producer-free V117 verifier changed")
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


def _acquisition(document: Any, *, arm: str, family: str, seed: int) -> None:
    if type(document) is not dict:
        _fail("V118 acquisition document type changed")
    payload = {
        key: value for key, value in document.items() if key != "acquisition_id"
    }
    expected_schema = (
        "acfqp.true_bit_partial_acquisition.v59"
        if arm == "ANONYMOUS_FACTOR_PRIOR_ON"
        else "acfqp.true_bit_complete_acquisition.v59"
    )
    if (
        document.get("acquisition_id")
        != domains59.extension_content_id_v59(
            domains59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
            payload,
        )
        or document.get("schema") != expected_schema
        or document.get("arm") != arm
        or document.get("factor_prior_enabled")
        is not (arm == "ANONYMOUS_FACTOR_PRIOR_ON")
        or document.get("family") != family
        or document.get("seed") != seed
        or type(document.get("ground_support_labels")) is not int
        or document["ground_support_labels"] <= 0
        or type(document.get("raw_transition_count")) is not int
        or document["raw_transition_count"] <= 0
        or type(document.get("raw_transition_sha256")) is not str
        or len(document["raw_transition_sha256"]) != 64
        or document.get("symmetric_minimum_common_prefix_post_audit") is not True
        or document.get("reachable_frontier_exhaustion_input_consumed") is not False
        or document.get("heuristic_mdl_information_units_consumed") is not False
        or document.get("predictive_evidence_to_mdl_credit_consumed") is not False
        or type(document.get("candidate")) is not dict
    ):
        _fail("V118 acquisition identity or stopping boundary changed")


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    namespace: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_OCCURRENCE_V118_DOMAIN,
    )
    prior = document.get("prior_on_partial_acquisition")
    no_prior = document.get("strict_no_prior_acquisition")
    derived = document.get("dependency_derived_program_branch_sequence")
    matched = document.get("matched_v116_cross_epoch_sequence")
    if (
        document.get("schema") != "acfqp.fourth_family_inventory_occurrence.v118"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(derived) is not dict
        or type(matched) is not dict
    ):
        _fail("V118 occurrence identity changed")
    _acquisition(prior, arm="ANONYMOUS_FACTOR_PRIOR_ON", family=family, seed=seed)
    _acquisition(no_prior, arm="STRICT_NO_PRIOR", family=family, seed=seed)
    derived_payload = {
        key: value for key, value in derived.items() if key != "sequence_id"
    }
    matched_payload = {
        key: value for key, value in matched.items() if key != "sequence_id"
    }
    if (
        derived.get("sequence_id")
        != domains117.extension_content_id_v117(
            domains117.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_SEQUENCE_V117_DOMAIN,
            derived_payload,
        )
        or matched.get("sequence_id")
        != domains116.extension_content_id_v116(
            domains116.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_SEQUENCE_V116_DOMAIN,
            matched_payload,
        )
        or document.get("dependency_derived_program_branch_sequence_id")
        != derived.get("sequence_id")
        or document.get("matched_v116_cross_epoch_sequence_id")
        != matched.get("sequence_id")
    ):
        _fail("V118 sequence wrapper join changed")
    derived_base = derived["dependency_derived_program_branch_base_sequence"]
    matched_base = matched["cross_epoch_program_branch_base_sequence"]
    if (
        derived.get("dependency_derived_program_branch_base_sequence_id")
        != derived_base.get("sequence_id")
        or matched.get("cross_epoch_program_branch_base_sequence_id")
        != matched_base.get("sequence_id")
    ):
        _fail("V118 base sequence join changed")
    v115 = namespace["_v115_namespace"]()
    try:
        v115["_sequence"](derived_base)
        v115["_sequence"](matched_base)
    except Exception as exc:
        if not type(exc).__module__.startswith("acfqp"):
            raise
        _fail(f"V118 embedded sequence reconstruction failed: {exc}")
    if derived_base != matched_base:
        _fail("V118 dependency-derived sequence differs from matched V116")
    receipt_counts = namespace["_receipt"](
        derived.get("program_branch_dependency_receipt"),
        prior["candidate"],
        derived_base,
    )
    plan = namespace["_plan_accounting"](derived_base)
    dependency_compute = len(EPISODES) * (
        receipt_counts["compiled_factor_assignment_count"]
        + receipt_counts["canonical_action_catalogue_count"]
    )
    if (
        derived.get("program_branch_dependency_receipt_id")
        != derived["program_branch_dependency_receipt"]["dependency_receipt_id"]
        or derived.get("dependency_receipt_rederivation_count") != len(EPISODES)
        or derived.get("dependency_derivation_compute_events") != dependency_compute
        or derived.get("program_branch_cache_hit_count") != plan["branch_hits"]
        or derived.get("actual_new_abstract_planning_compute_events")
        != plan["planning_compute"]
        or derived.get("matched_uncached_abstract_planning_compute_events")
        != plan["uncached_compute"]
    ):
        _fail("V118 dependency or planning reconstruction changed")
    prior_labels = prior["ground_support_labels"]
    no_prior_labels = no_prior["ground_support_labels"]
    accounting = {
        "prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "prior_minus_no_prior_acquisition_labels": prior_labels - no_prior_labels,
        "certificate_local_labels": derived_base[
            "certificate_ground_support_labels_paid_once"
        ],
        "lifetime_target_labels": derived_base[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": derived_base["execution_step_count"],
        "abstract_planning_compute_events": plan["planning_compute"],
        "matched_uncached_planning_compute_events": plan["uncached_compute"],
        "planning_compute_events_avoided_against_uncached": plan[
            "uncached_compute"
        ]
        - plan["planning_compute"],
        "dependency_derivation_compute_events": dependency_compute,
        "program_branch_cache_hits": plan["branch_hits"],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_inventory_family_not_in_v117_three_family_campaign": True,
        "matched_prior_and_no_prior_use_identical_witness_blind_prefix": True,
        "both_acquisition_arms_terminate_with_candidates": True,
        "dependency_derived_and_v116_sequences_byte_exact": True,
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in derived_base["episodes"]
        ),
        "certificate_failure_only_query_discipline_clean": derived_base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_matches_full_v105_rebuild": derived_base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": derived_base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
        "sample_tax_sign_excluded_from_construction_gate": True,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("fourth_family_abstract_world_model_pipeline_verified")
        != gate["passed"]
        or document.get("sample_efficiency_improvement_claimed") is not False
        or document.get("factor_library_contains_historical_related_schema_sources")
        is not True
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V118 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **receipt_counts,
        **accounting,
    }


def verify_fourth_family_inventory_campaign_bytes_v118(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V118 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V118 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_CAMPAIGN_V118_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema") != "acfqp.fourth_family_inventory_campaign.v118"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v117_success_campaign_id") != V117_CAMPAIGN_ID
        or document.get("v117_success_verification_id") != V117_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V118 campaign inventory changed")
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
        "fresh_inventory_family_present": all(
            row["target_family"] == FAMILY for row in replay
        ),
        "every_occurrence_completes_receding_abstract_planning": all(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_matches_dependency_guarded_and_v116_sequences": all(
            row["gate_passed"] for row in replay
        ),
        "sample_tax_sign_excluded_and_reported_without_selection": True,
        "strict_incompatible_schema_no_transfer_verified": strict_ood,
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("registered_fourth_family_abstract_world_model_pipeline_verified")
        != passed
        or document.get("factor_library_contains_historical_related_schema_sources")
        is not True
        or document.get("arbitrary_unseen_domain_transfer_claimed") is not False
        or document.get("compiled_model_cache_or_receipt_used_as_safety_authority")
        is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V118 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.fourth_family_inventory_verification.v118",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v117_success_verification_id": V117_VERIFICATION_ID,
        "verification_status": "REGISTERED_V118_FOURTH_FAMILY_INVENTORY_PIPELINE_VERIFIED",
        "producer_free_v118_content_graph_reconstruction": True,
        "producer_free_compiled_sequence_and_dependency_reconstruction": True,
        "producer_free_acquisition_identity_and_accounting_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "fresh_v118_full_ground_dynamics_rederivation_performed": False,
        "factor_library_contains_historical_related_schema_sources": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "sample_efficiency_improvement_claimed": False,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_fourth_family_inventory_verification_v118(raw: bytes) -> bytes:
    payload = verify_fourth_family_inventory_campaign_bytes_v118(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v118(
            domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_VERIFICATION_V118_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V118 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_fourth_family_inventory_verification_v118",
    "verify_fourth_family_inventory_campaign_bytes_v118",
)
