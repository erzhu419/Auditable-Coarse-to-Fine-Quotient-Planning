from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v155 as v155
from acfqp import construction_k7_domain_registry_extension_v156 as v156
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import build_quaternary_relation_workflow_adapter_v153
from acfqp.generic_relation_fanout_routing_adapter_v154 import build_relation_fanout_routing_adapter_v154
from acfqp.structural_margin_guarded_acquisition_operator_v156 import (
    anonymous_initial_action_support_signature_v156,
    anonymous_relation_coverage_margin_score_v156,
)
from acfqp.structural_margin_guarded_campaign_core_v156 import structural_margin_campaign_config_v156
from acfqp.structural_margin_query_guard_receipt_v156 import freeze_structural_margin_query_guard_receipt_v156


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v156_domains_are_additive_and_disjoint():
    assert len(v156.K7_DOMAIN_TAG_EXTENSION_V156) == 6
    assert v156.K7_DOMAIN_TAG_EXTENSION_V156.isdisjoint(v155.K7_DOMAIN_TAG_EXTENSION_V155)


def test_v156_anonymous_margin_separates_frozen_source_structures_without_outcomes():
    config = structural_margin_campaign_config_v156()
    positive = build_quaternary_relation_workflow_adapter_v153(1_047_711, config)
    fallback = build_relation_fanout_routing_adapter_v154(1_047_721, config)
    positive_signature = anonymous_initial_action_support_signature_v156(positive)
    fallback_signature = anonymous_initial_action_support_signature_v156(fallback)
    assert anonymous_relation_coverage_margin_score_v156(positive_signature) == 3
    assert anonymous_relation_coverage_margin_score_v156(fallback_signature) == 1
    assert positive_signature != fallback_signature


def test_v156_guard_receipt_is_derived_only_from_frozen_predecessors():
    receipt = freeze_structural_margin_query_guard_receipt_v156(
        (ROOT / "v153_relation_coverage_campaign.json").read_bytes(),
        (ROOT / "v154_relation_coverage_cross_structure_campaign.json").read_bytes(),
        (ROOT / "v154_relation_coverage_cross_structure_failure.json").read_bytes(),
        (ROOT / "v155_structural_signature_guarded_campaign.json").read_bytes(),
        (ROOT / "v155_structural_signature_guarded_verification.json").read_bytes(),
    ).to_document()
    assert receipt["minimum_positive_score"] == 3
    assert receipt["maximum_failed_score"] == 1
    assert receipt["max_margin_decision_boundary"] == 2
    assert receipt["selection_rule"]["exact_signature_registry_consulted"] is False
    assert receipt["guard_frozen_before_v156_target_outcomes"] is True
