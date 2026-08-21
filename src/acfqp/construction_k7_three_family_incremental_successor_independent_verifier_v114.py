"""Producer-free reconstruction of the V114 three-family campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v114 as domains
from acfqp import construction_k7_incremental_abstract_successor_independent_verifier_v113 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0daf03f1891ed225b2221d61fa3780c1f0a84d2506ce8d2bff8164df1153c3a8"
CAMPAIGN_BYTE_COUNT = 33_074_844
CAMPAIGN_SHA256 = "819e551fcbac840826b01deef9072d67055922e8d1b310949752886418cc7b7d"
PREREGISTRATION_ID = "a638782c5108b33039f48a23c0f2dfbc32bc1ebb158d4e19afbdf1f982398433"
V113_CAMPAIGN_ID = "eb59e83d53b6ebcf104ece21a60a99371ac15516f3e5629a604290142411b13a"
V113_VERIFICATION_ID = "128f50e0ca172a50aa118e5e6670b3bf2398e2d22cfd00262e8888d55d14bed4"
V113_VERIFIER_SOURCE_SHA256 = "e263d896a02984c3377c9dc2106e04e2e86ddefea060e6ff9dcead488feb02c2"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_026_101),
    ("BALANCED_BATCH_REFINEMENT", 1_026_102),
    ("COUPLED_EXCHANGE", 1_026_201),
    ("COUPLED_EXCHANGE", 1_026_202),
    ("MAINTENANCE_CASCADE", 1_026_301),
    ("MAINTENANCE_CASCADE", 1_026_302),
)
EPISODES = (231, 232, 233)
REQUIRED_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "COUPLED_EXCHANGE",
    "MAINTENANCE_CASCADE",
)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7ThreeFamilyIncrementalSuccessorIndependentVerifierV114Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThreeFamilyIncrementalSuccessorIndependentVerifierV114Error(
        message
    )


def _content(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V114 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v114(domain, payload):
        _fail(f"V114 {key} changed")


def _v113_namespace() -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest()
        != V113_VERIFIER_SOURCE_SHA256
        or previous.EPISODES != (221, 222, 223)
        or previous.CAMPAIGN_ID != V113_CAMPAIGN_ID
        or previous.VERIFICATION_ID != V113_VERIFICATION_ID
    ):
        _fail("V114 frozen producer-free V113 verifier changed")
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
    try:
        matched_namespace = namespace["_v111_namespace"]()
    except previous.ConstructionK7IncrementalAbstractSuccessorIndependentVerifierV113Error as exc:
        _fail(f"V114 producer-free matched verifier setup failed: {exc}")
    return namespace, matched_namespace


def _occurrence(
    document: Any,
    family: str,
    seed: int,
    v113: Mapping[str, Any],
    matched: Mapping[str, Any],
) -> dict[str, Any]:
    _content(
        document,
        "occurrence_id",
        domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_OCCURRENCE_V114_DOMAIN,
    )
    nested = document.get("v113_incremental_successor_occurrence")
    if (
        document.get("schema")
        != "acfqp.three_family_incremental_successor_occurrence.v114"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or type(nested) is not dict
        or document.get("v113_incremental_successor_occurrence_id")
        != nested.get("occurrence_id")
    ):
        _fail("V114 occurrence identity changed")
    try:
        replay = v113["_occurrence"](nested, family, seed, matched)
    except previous.ConstructionK7IncrementalAbstractSuccessorIndependentVerifierV113Error as exc:
        _fail(f"V114 nested V113 reconstruction failed: {exc}")
    accounting = {
        key: value
        for key, value in replay.items()
        if key not in ("target_family", "seed", "gate_passed")
    }
    nested_gate = nested["registered_gate"]
    gate = {
        "unchanged_v113_incremental_successor_gate_passed": replay[
            "gate_passed"
        ],
        "incremental_execution_exactly_matches_full_rebuild": nested_gate[
            "incremental_and_full_rebuild_actions_plans_receipts_labels_steps_equal"
        ],
        "incremental_model_exactly_matches_full_v105_rebuild": nested_gate[
            "every_incremental_model_exactly_matches_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": nested_gate[
            "planner_consumes_compiled_model_without_raw_transition_argument"
        ],
        "incremental_compilation_strictly_below_full_rebuild": accounting[
            "incremental_model_update_compilation_events"
        ]
        < accounting["matched_full_rebuild_update_compilation_events"],
        "certificate_failure_only_query_discipline_clean": nested_gate[
            "certificate_failure_only_query_discipline_clean"
        ],
        "quotient_labels_strictly_below_cold_direct": accounting[
            "incremental_quotient_lifetime_target_labels"
        ]
        < accounting["cold_direct_lifetime_target_labels"],
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get(
            "unchanged_incremental_compiler_and_planner_verified_on_target_family"
        )
        != gate["passed"]
        or document.get("compiled_model_used_as_safety_authority") is not False
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V114 occurrence accounting, Gate, or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "gate_passed": gate["passed"],
        **accounting,
    }


def verify_three_family_incremental_successor_campaign_bytes_v114(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V114 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V114 campaign is noncanonical")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_CAMPAIGN_V114_DOMAIN,
    )
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("schema")
        != "acfqp.three_family_incremental_successor_campaign.v114"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v113_success_campaign_id") != V113_CAMPAIGN_ID
        or document.get("v113_success_verification_id") != V113_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V114 campaign inventory changed")
    v113, matched = _v113_namespace()
    replay = [
        _occurrence(row, family, seed, v113, matched)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    accounting_keys = tuple(
        key
        for key, value in replay[0].items()
        if type(value) is int and key not in ("seed", "gate_passed")
    )
    numeric = {
        key: sum(row[key] for row in replay) for key in accounting_keys
    }
    accounting = {
        **numeric,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    family_counts = {
        family: sum(row["target_family"] == family for row in replay)
        for family in REQUIRED_FAMILIES
    }
    try:
        ood = matched["v106"].v105._ood(  # noqa: SLF001
            document["incompatible_schema_no_transfer_control"]
        )
    except Exception as exc:
        _fail(f"V114 OOD control reconstruction failed: {exc}")
    passed = (
        all(row["gate_passed"] for row in replay)
        and set(family_counts) == set(REQUIRED_FAMILIES)
        and all(count > 0 for count in family_counts.values())
        and numeric["incremental_model_update_compilation_events"]
        < numeric["matched_full_rebuild_update_compilation_events"]
        and numeric["incremental_quotient_lifetime_target_labels"]
        < numeric["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": len(TARGETS),
        "passed_target_occurrence_count": sum(
            row["gate_passed"] for row in replay
        ),
        "required_target_family_counts": family_counts,
        "all_three_registered_structural_families_present": set(family_counts)
        == set(REQUIRED_FAMILIES)
        and all(count > 0 for count in family_counts.values()),
        "every_occurrence_unchanged_v113_gate_passed": all(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_exactly_matches_full_rebuild": all(
            row["incremental_quotient_lifetime_target_labels"]
            == row["matched_full_rebuild_quotient_lifetime_target_labels"]
            and row["incremental_new_planning_compute_events"]
            == row["matched_full_rebuild_new_planning_compute_events"]
            and row["incremental_dependency_maintenance_events"]
            == row["matched_full_rebuild_dependency_maintenance_events"]
            for row in replay
        ),
        "every_occurrence_incremental_compilation_below_full_rebuild": all(
            row["incremental_model_update_compilation_events"]
            < row["matched_full_rebuild_update_compilation_events"]
            for row in replay
        ),
        "aggregate_incremental_compilation_below_full_rebuild": numeric[
            "incremental_model_update_compilation_events"
        ]
        < numeric["matched_full_rebuild_update_compilation_events"],
        "aggregate_quotient_labels_below_cold_direct": numeric[
            "incremental_quotient_lifetime_target_labels"
        ]
        < numeric["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    if (
        document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get(
            "registered_three_family_incremental_successor_transfer_verified"
        )
        != passed
        or document.get(
            "ground_distinctions_acquired_only_after_certificate_failure_verified"
        )
        != passed
        or document.get("algorithm_changed_from_v113") is not False
        or document.get("compiled_model_used_as_safety_authority") is not False
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V114 campaign accounting, Gate, or claim boundary changed")
    return {
        "schema": "acfqp.three_family_incremental_successor_verification.v114",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v113_success_verification_id": V113_VERIFICATION_ID,
        "verification_status": "REGISTERED_V114_THREE_FAMILY_INCREMENTAL_SUCCESSOR_VERIFIED",
        "producer_free_nested_v113_execution_reconstruction": True,
        "producer_free_incremental_model_and_terminal_rule_reconstruction": True,
        "producer_free_delta_receipt_and_compilation_accounting_reconstruction": True,
        "producer_free_compiled_planner_output_equality_reconstruction": True,
        "producer_summary_counts_not_used": True,
        "verified_target_family_counts": family_counts,
        "verified_occurrences": replay,
        "verified_accounting": accounting,
        "registered_gate_independently_verified": passed,
        "compiled_model_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_three_family_incremental_successor_verification_v114(
    raw: bytes,
) -> bytes:
    payload = verify_three_family_incremental_successor_campaign_bytes_v114(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v114(
            domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_VERIFICATION_V114_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V114 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_three_family_incremental_successor_verification_v114",
    "verify_three_family_incremental_successor_campaign_bytes_v114",
)
