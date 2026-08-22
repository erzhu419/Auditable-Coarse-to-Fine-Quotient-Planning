from pathlib import Path

from acfqp.anonymous_query_classifier_receipt_v158 import (
    SOURCE_FAILED_SIGNATURES,
    SOURCE_POSITIVE_SIGNATURES,
    evaluate_classifier_expression_v158,
    freeze_anonymous_query_classifier_receipt_v158,
    synthesize_anonymous_query_classifier_v158,
)
from acfqp.generic_novel_signature_adapters_v158 import build_novel_fallback_signature_adapter_v158, build_novel_positive_signature_adapter_v158
from acfqp.structural_margin_guarded_acquisition_operator_v156 import anonymous_initial_action_support_signature_v156
from acfqp.structural_margin_guarded_campaign_core_v156 import structural_margin_campaign_config_v156


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v158_classifier_is_exact_mdl_synthesized_not_hand_selected_at_application():
    expression, _mdl, evaluated, separating = synthesize_anonymous_query_classifier_v158()
    assert expression == {
        "kind": "COUNT_PREDICATE_GREATER_THAN",
        "predicate_field": "INITIAL_SUPPORT",
        "predicate_comparator": "EQUAL",
        "predicate_value": 1,
        "count_threshold": 1,
    }
    assert evaluated == 448
    assert separating > 0
    assert all(evaluate_classifier_expression_v158(expression, signature)[0] for signature in SOURCE_POSITIVE_SIGNATURES)
    assert not any(evaluate_classifier_expression_v158(expression, signature)[0] for signature in SOURCE_FAILED_SIGNATURES)


def test_v158_fresh_adapters_have_unseen_exact_signatures_on_both_classifier_sides():
    config = structural_margin_campaign_config_v156()
    positive = anonymous_initial_action_support_signature_v156(build_novel_positive_signature_adapter_v158(1_047_901, config))
    fallback = anonymous_initial_action_support_signature_v156(build_novel_fallback_signature_adapter_v158(1_047_911, config))
    expression, *_ = synthesize_anonymous_query_classifier_v158()
    sources = set(SOURCE_POSITIVE_SIGNATURES + SOURCE_FAILED_SIGNATURES)
    assert positive not in sources and fallback not in sources
    assert evaluate_classifier_expression_v158(expression, positive)[0] is True
    assert evaluate_classifier_expression_v158(expression, fallback)[0] is False


def test_v158_receipt_is_frozen_before_new_target_outcomes():
    receipt = freeze_anonymous_query_classifier_receipt_v158(
        (ROOT / "v157_plan_mode_margin_campaign.json").read_bytes(),
        (ROOT / "v157_plan_mode_margin_verification.json").read_bytes(),
    ).to_document()
    assert receipt["fresh_v158_target_outcomes_accessed"] is False
    assert receipt["exact_signature_registry_consulted_at_application"] is False
    assert receipt["selected_expression"]["predicate_field"] == "INITIAL_SUPPORT"
