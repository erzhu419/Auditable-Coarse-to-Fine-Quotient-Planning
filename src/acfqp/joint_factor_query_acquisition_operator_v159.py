"""Apply the V159 factorization-labelled query-policy meta-prior."""

from __future__ import annotations

from types import FunctionType

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v159 as domains
from acfqp.construction_k7_joint_factor_query_classifier_receipt_freeze_v159 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_joint_factor_query_classifier_receipt_v159,
)
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.joint_factor_query_classifier_core_v159 import (
    anonymous_initial_support_signature_v159,
    evaluate_joint_factor_query_expression_v159,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    relation_coverage_then_path_stream_v153,
)


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def joint_factor_query_stream_v159(adapter, expression):
    signature = anonymous_initial_support_signature_v159(adapter)
    selected, _count = evaluate_joint_factor_query_expression_v159(
        expression, signature
    )
    if selected:
        yield from relation_coverage_then_path_stream_v153(adapter)
        return
    yield from fair_witness_blind_path_first_stream_v129r1(adapter)


def acquire_matched_joint_factor_query_arms_v159(
    adapter, bank_raw, verification_raw, classifier_receipt_raw, config
):
    classifier = verify_frozen_joint_factor_query_classifier_receipt_v159(
        classifier_receipt_raw
    )
    expression = classifier["selected_expression"]
    signature = anonymous_initial_support_signature_v159(adapter)
    selected, count = evaluate_joint_factor_query_expression_v159(
        expression, signature
    )
    v158_counterfactual_count = sum(pair[0] == 1 for pair in signature)
    run_globals = dict(v148.__dict__)

    def stream(current_adapter):
        yield from joint_factor_query_stream_v159(current_adapter, expression)

    run_globals["fair_witness_blind_path_first_stream_v129r1"] = stream
    run = _clone(
        v148.acquire_matched_anonymous_relational_factor_bank_arms_v148,
        run_globals,
    )
    arms = run(adapter, bank_raw, verification_raw, config)
    wrapped = {}
    for name, arm in arms.items():
        source = arm["document"]
        payload = {
            **{
                key: value
                for key, value in source.items()
                if key not in {"schema", "acquisition_id"}
            },
            "schema": "acfqp.joint_factor_query_acquisition_arm.v159",
            "source_v148_acquisition_id": source["acquisition_id"],
            "joint_factor_query_classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
            "anonymous_initial_action_support_signature": [
                list(pair) for pair in signature
            ],
            "selected_classifier_expression": expression,
            "selected_predicate_match_count": count,
            "query_policy_decision": (
                "RELATION_COVERAGE" if selected else "PATH_FIRST_SAFE_FALLBACK"
            ),
            "v158_metadata_classifier_counterfactual_match_count": v158_counterfactual_count,
            "v158_metadata_classifier_counterfactual_decision": (
                "RELATION_COVERAGE"
                if v158_counterfactual_count > 1
                else "PATH_FIRST_SAFE_FALLBACK"
            ),
            "source_labels_derived_from_raw_factorization_differences": True,
            "target_factorization_probe_labels_added_by_classifier": 0,
            "exact_signature_registry_consulted": False,
            "classifier_accessed_target_ground_successor_outcomes": False,
            "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule": True,
            "classifier_is_model_planning_or_certificate_authority": False,
        }
        wrapped[name] = {
            **arm,
            "document": {
                **payload,
                "acquisition_id": domains.extension_content_id_v159(
                    domains.CONSTRUCTION_K7_ACQUISITION_V159_DOMAIN, payload
                ),
            },
        }
    return wrapped


__all__ = (
    "acquire_matched_joint_factor_query_arms_v159",
    "joint_factor_query_stream_v159",
)
