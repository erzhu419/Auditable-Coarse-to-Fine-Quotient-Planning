"""Apply the V158 synthesized classifier to matched acquisition arms."""

from __future__ import annotations

from types import FunctionType

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v158 as domains
from acfqp.anonymous_query_classifier_receipt_v158 import CLASSIFIER_RECEIPT_ID, evaluate_classifier_expression_v158
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import fair_witness_blind_path_first_stream_v129r1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_acquisition_operator_v153 import relation_coverage_then_path_stream_v153
from acfqp.structural_margin_guarded_acquisition_operator_v156 import anonymous_initial_action_support_signature_v156


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _classifier(config):
    raw = bytes.fromhex(config.get("_v158_classifier_receipt_hex", ""))
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or document.get("classifier_receipt_id") != CLASSIFIER_RECEIPT_ID
        or document.get("fresh_v158_target_outcomes_accessed") is not False
        or document.get("exact_signature_registry_consulted_at_application") is not False
    ):
        raise ValueError("V158 classifier receipt changed")
    return document


def classifier_guarded_stream_v158(adapter, expression):
    signature = anonymous_initial_action_support_signature_v156(adapter)
    selected, _count = evaluate_classifier_expression_v158(expression, signature)
    if selected:
        yield from relation_coverage_then_path_stream_v153(adapter)
        return
    yield from fair_witness_blind_path_first_stream_v129r1(adapter)


def acquire_matched_classifier_guarded_arms_v158(adapter, bank_raw, verification_raw, config):
    classifier = _classifier(config)
    expression = classifier["selected_expression"]
    signature = anonymous_initial_action_support_signature_v156(adapter)
    selected, count = evaluate_classifier_expression_v158(expression, signature)
    run_globals = dict(v148.__dict__)

    def stream(current_adapter):
        yield from classifier_guarded_stream_v158(current_adapter, expression)

    run_globals["fair_witness_blind_path_first_stream_v129r1"] = stream
    run = _clone(v148.acquire_matched_anonymous_relational_factor_bank_arms_v148, run_globals)
    arms = run(adapter, bank_raw, verification_raw, config)
    wrapped = {}
    for name, arm in arms.items():
        source = arm["document"]
        payload = {
            **{key: value for key, value in source.items() if key not in {"schema", "acquisition_id"}},
            "schema": "acfqp.classifier_guarded_acquisition_arm.v158",
            "source_v148_acquisition_id": source["acquisition_id"],
            "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
            "anonymous_initial_action_support_signature": [list(pair) for pair in signature],
            "selected_classifier_expression": expression,
            "selected_predicate_match_count": count,
            "guard_decision": "RELATION_COVERAGE" if selected else "PATH_FIRST_SAFE_FALLBACK",
            "exact_signature_registry_consulted": False,
            "classifier_accessed_ground_successor_outcomes": False,
            "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule": True,
            "classifier_is_model_planning_or_certificate_authority": False,
        }
        wrapped[name] = {
            **arm,
            "document": {**payload, "acquisition_id": domains.extension_content_id_v158(domains.CONSTRUCTION_K7_ACQUISITION_V158_DOMAIN, payload)},
        }
    return wrapped


__all__ = ("acquire_matched_classifier_guarded_arms_v158", "classifier_guarded_stream_v158")
