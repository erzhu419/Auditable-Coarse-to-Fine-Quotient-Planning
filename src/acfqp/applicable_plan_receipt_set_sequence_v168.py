"""Totalize the registered plan-receipt inventory over DIRECT/MEMOIZED/MIXED/NONE.

The annotation is observational.  In particular, ``NONE`` means that no
registered compiled-program receipt occurred in the sequence; it does not
mean that an executed action lacked its V109 receipt or exact certificate.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v154 as domains_v154
from acfqp import construction_k7_domain_registry_extension_v168 as domains
from acfqp.phase3e_ids import canonical_json_bytes


DIRECT_MODE = "DIRECT_GENERIC_FACTOR_PROGRAM"
MEMOIZED_MODE = "V115_MEMOIZED_COMPILED_PROGRAM"
REGISTERED_MODES = (DIRECT_MODE, MEMOIZED_MODE)
DIRECT_ONLY = "DIRECT_ONLY"
MEMOIZED_ONLY = "MEMOIZED_ONLY"
MIXED = "MIXED"
NONE = "NONE"


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _mode(plan: Mapping[str, Any]) -> str | None:
    if plan.get("schema") == "acfqp.generic_projected_program_memo_plan.v115":
        return MEMOIZED_MODE
    if plan.get("planning_source") == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        return DIRECT_MODE
    return None


def _set_class(modes: tuple[str, ...]) -> str:
    if not modes:
        return NONE
    if modes == (DIRECT_MODE,):
        return DIRECT_ONLY
    if modes == (MEMOIZED_MODE,):
        return MEMOIZED_ONLY
    if modes == REGISTERED_MODES:
        return MIXED
    raise ValueError("V168 registered receipt set escaped the finite totalization")


def annotate_applicable_plan_receipt_set_sequence_v168(
    sequence: Mapping[str, Any],
) -> dict[str, Any]:
    if sequence.get("sequence_id") != _content_id(
        domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN,
        {key: value for key, value in sequence.items() if key != "sequence_id"},
    ):
        raise ValueError("V168 source V154 sequence changed")

    wrappers = [
        wrapper
        for episode in sequence["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
    ]
    if any(
        type(wrapper) is not dict
        or type(wrapper.get("abstract_plan")) is not dict
        for wrapper in wrappers
    ):
        raise ValueError("V168 abstract plan receipt inventory changed")
    counted = {mode: 0 for mode in REGISTERED_MODES}
    for wrapper in wrappers:
        mode = _mode(wrapper["abstract_plan"])
        if mode is not None:
            counted[mode] += 1
    expected = {
        DIRECT_MODE: sequence["direct_generic_factor_program_plan_count"],
        MEMOIZED_MODE: sequence[
            "v115_memoized_compiled_program_plan_receipt_count"
        ],
    }
    if counted != expected:
        raise ValueError("V168 registered plan receipt counts changed")

    modes = tuple(mode for mode in REGISTERED_MODES if counted[mode] > 0)
    receipt_set_class = _set_class(modes)
    actual = sequence["all_actual_legality_conditioned_execution_receipts"]
    if not (
        type(actual) is list
        and len(actual)
        == sequence["actual_legality_conditioned_execution_receipt_count"]
        == sequence["execution_step_count"]
        and all(
            type(receipt) is dict
            and receipt.get("schema")
            == "acfqp.generic_dependency_revalidated_execution_receipt.v109"
            and receipt.get("receipt_is_observation_not_safety_authority") is True
            and receipt.get("query_local_exact_overlay_remains_only_safety_authority")
            is True
            for receipt in actual
        )
    ):
        raise ValueError("V168 actual V109 execution receipt inventory changed")

    actual_counts = {mode: 0 for mode in REGISTERED_MODES}
    for receipt in actual:
        wrapper = receipt.get("quotient_plan_receipt")
        if wrapper is None:
            continue
        if type(wrapper) is not dict or type(wrapper.get("abstract_plan")) is not dict:
            raise ValueError("V168 V109 plan join changed")
        mode = _mode(wrapper["abstract_plan"])
        if mode is not None:
            actual_counts[mode] += 1
    if any(actual_counts[mode] > counted[mode] for mode in REGISTERED_MODES):
        raise ValueError("V168 actual receipt mode escaped abstract inventory")

    payload = {
        **{
            key: value
            for key, value in sequence.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.applicable_plan_receipt_set_sequence.v168",
        "source_v154_sequence_id": sequence["sequence_id"],
        "applicable_plan_receipt_mode": (
            "NO_REGISTERED_COMPILED_PROGRAM_PLAN_RECEIPT"
            if receipt_set_class == NONE
            else "REGISTERED_COMPILED_PROGRAM_PLAN_MODE_SET"
        ),
        "applicable_plan_receipt_modes": list(modes),
        "registered_plan_receipt_set_class": receipt_set_class,
        "abstract_plan_receipt_count_by_registered_mode": counted,
        "actual_v109_receipt_count_by_registered_mode": actual_counts,
        "registered_plan_receipt_set_totalized": True,
        "at_least_one_registered_plan_mode_exercised": bool(modes),
        "mixed_registered_plan_mode_sequence": receipt_set_class == MIXED,
        "empty_registered_plan_mode_set_is_failure": False,
        "none_path_defers_to_v109_and_query_local_certificate": receipt_set_class
        == NONE,
        "each_abstract_receipt_contains_one_concrete_plan_document": True,
        "multiple_registered_modes_mean_temporal_receipt_use_not_action_competition": True,
        "all_executed_actions_have_v109_receipts": True,
        "registered_plan_mode_set_changes_planning_or_execution": False,
        "registered_plan_mode_set_is_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_synthesized": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v168(
            domains.CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN, payload
        ),
    }


__all__ = (
    "DIRECT_MODE",
    "MEMOIZED_MODE",
    "DIRECT_ONLY",
    "MEMOIZED_ONLY",
    "MIXED",
    "NONE",
    "REGISTERED_MODES",
    "annotate_applicable_plan_receipt_set_sequence_v168",
)
