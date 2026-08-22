"""Anonymous max-margin guard around the V153 relation query heuristic."""

from __future__ import annotations

from types import FunctionType
from typing import Any

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v156 as domains
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import fair_witness_blind_path_first_stream_v129r1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_acquisition_operator_v153 import relation_coverage_then_path_stream_v153
from acfqp.structural_margin_query_guard_receipt_v156 import DECISION_BOUNDARY, GUARD_RECEIPT_ID


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def anonymous_initial_action_support_signature_v156(adapter: Any):
    keys = tuple(adapter.action_key(action) for action in adapter.actions(adapter.initial()))
    if not keys or not adapter.catalogue:
        raise ValueError("V156 anonymous initial action inventory changed")
    return tuple(
        sorted(
            (
                len({adapter.catalogue[key].fields[field] for key in keys}),
                len({action.fields[field] for action in adapter.catalogue}),
            )
            for field in range(len(adapter.catalogue[0].fields))
        )
    )


def anonymous_relation_coverage_margin_score_v156(signature):
    return sum(initial_support == 1 and catalogue_support >= 3 for initial_support, catalogue_support in signature)


def structural_margin_guarded_stream_v156(adapter: Any):
    signature = anonymous_initial_action_support_signature_v156(adapter)
    score = anonymous_relation_coverage_margin_score_v156(signature)
    if score > DECISION_BOUNDARY:
        yield from relation_coverage_then_path_stream_v153(adapter)
        return
    yield from fair_witness_blind_path_first_stream_v129r1(adapter)


_RUN_GLOBALS = dict(v148.__dict__)
_RUN_GLOBALS["fair_witness_blind_path_first_stream_v129r1"] = structural_margin_guarded_stream_v156
_RUN = _clone(v148.acquire_matched_anonymous_relational_factor_bank_arms_v148, _RUN_GLOBALS)


def acquire_matched_structural_margin_guarded_arms_v156(adapter, bank_raw, verification_raw, config):
    receipt_raw = bytes.fromhex(config.get("_v156_guard_receipt_hex", ""))
    receipt = loads_canonical_json(receipt_raw)
    if (
        canonical_json_bytes(receipt) != receipt_raw
        or receipt.get("guard_receipt_id") != GUARD_RECEIPT_ID
        or receipt.get("guard_frozen_before_v156_target_outcomes") is not True
        or receipt.get("max_margin_decision_boundary") != DECISION_BOUNDARY
    ):
        raise ValueError("V156 guard receipt changed")
    signature = anonymous_initial_action_support_signature_v156(adapter)
    score = anonymous_relation_coverage_margin_score_v156(signature)
    decision = "RELATION_COVERAGE" if score > DECISION_BOUNDARY else "PATH_FIRST_SAFE_FALLBACK"
    arms = _RUN(adapter, bank_raw, verification_raw, config)
    wrapped = {}
    for name, arm in arms.items():
        source = arm["document"]
        payload = {
            **{key: value for key, value in source.items() if key not in {"schema", "acquisition_id"}},
            "schema": "acfqp.structural_margin_guarded_acquisition_arm.v156",
            "source_v148_acquisition_id": source["acquisition_id"],
            "guard_receipt_id": GUARD_RECEIPT_ID,
            "anonymous_initial_action_support_signature": [list(pair) for pair in signature],
            "anonymous_relation_coverage_margin_score": score,
            "max_margin_decision_boundary": DECISION_BOUNDARY,
            "decision_margin": score - DECISION_BOUNDARY,
            "guard_decision": decision,
            "exact_signature_registry_consulted": False,
            "boundary_or_unknown_score_defaults_to_safe_fallback": score <= DECISION_BOUNDARY,
            "guard_accessed_ground_successor_outcomes": False,
            "guard_changes_query_order_not_hypothesis_pool_or_stop_rule": True,
            "guard_is_model_planning_or_certificate_authority": False,
        }
        wrapped[name] = {
            **arm,
            "document": {
                **payload,
                "acquisition_id": domains.extension_content_id_v156(domains.CONSTRUCTION_K7_ACQUISITION_V156_DOMAIN, payload),
            },
        }
    return wrapped


__all__ = (
    "acquire_matched_structural_margin_guarded_arms_v156",
    "anonymous_initial_action_support_signature_v156",
    "anonymous_relation_coverage_margin_score_v156",
    "structural_margin_guarded_stream_v156",
)
