"""Classify and certify the actually exercised abstract-plan receipt mode."""

from __future__ import annotations

from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v154 as domains_v154
from acfqp import construction_k7_domain_registry_extension_v157 as domains
from acfqp.phase3e_ids import canonical_json_bytes


def _content_id(domain: str, payload: Any) -> str:
    import hashlib

    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def annotate_applicable_plan_mode_sequence_v157(sequence: Mapping[str, Any]):
    if sequence.get("sequence_id") != _content_id(
        domains_v154.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN,
        {key: value for key, value in sequence.items() if key != "sequence_id"},
    ):
        raise ValueError("V157 source V154 sequence changed")
    memoized = sequence["v115_memoized_compiled_program_plan_receipt_count"]
    direct = sequence["direct_generic_factor_program_plan_count"]
    if memoized > 0 and direct == 0:
        mode = "V115_MEMOIZED_COMPILED_PROGRAM"
    elif direct > 0 and memoized == 0:
        mode = "DIRECT_GENERIC_FACTOR_PROGRAM"
    else:
        raise ValueError("V157 expected exactly one applicable plan mode")
    payload = {
        **{key: value for key, value in sequence.items() if key not in {"schema", "sequence_id"}},
        "schema": "acfqp.applicable_plan_mode_sequence.v157",
        "source_v154_sequence_id": sequence["sequence_id"],
        "applicable_plan_receipt_mode": mode,
        "exactly_one_registered_plan_mode_exercised": True,
        "every_emitted_v115_plan_revalidated_before_v109_execution_receipt": sequence["memoized_plan_revalidated_before_v109_execution_receipt"] is True,
        "direct_generic_plan_path_covered_by_actual_v109_receipts": direct == 0 or sequence["actual_legality_conditioned_execution_receipt_count"] > 0,
        "all_executed_actions_have_v109_receipts": len(sequence["all_actual_legality_conditioned_execution_receipts"]) == sequence["actual_legality_conditioned_execution_receipt_count"] == sequence["execution_step_count"],
        "zero_v115_receipts_not_misclassified_when_direct_generic_plan_present": mode != "DIRECT_GENERIC_FACTOR_PROGRAM" or memoized == 0,
        "plan_mode_annotation_changes_planning_or_execution": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_synthesized": False,
    }
    return {**payload, "sequence_id": domains.extension_content_id_v157(domains.CONSTRUCTION_K7_SEQUENCE_V157_DOMAIN, payload)}


__all__ = ("annotate_applicable_plan_mode_sequence_v157",)
