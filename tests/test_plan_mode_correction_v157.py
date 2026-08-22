from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v156 as v156
from acfqp import construction_k7_domain_registry_extension_v157 as v157
from acfqp.applicable_plan_mode_sequence_v157 import annotate_applicable_plan_mode_sequence_v157
from acfqp.phase3e_ids import loads_canonical_json
from acfqp.plan_mode_correction_receipt_v157 import freeze_plan_mode_correction_receipt_v157


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v157_domains_are_additive_and_disjoint():
    assert len(v157.K7_DOMAIN_TAG_EXTENSION_V157) == 6
    assert v157.K7_DOMAIN_TAG_EXTENSION_V157.isdisjoint(v156.K7_DOMAIN_TAG_EXTENSION_V156)


def test_v157_correction_receipt_preserves_failed_v156_identity():
    receipt = freeze_plan_mode_correction_receipt_v157(
        (ROOT / "v156_structural_margin_guarded_campaign.json").read_bytes(),
        (ROOT / "v156_structural_margin_guarded_failure.json").read_bytes(),
    ).to_document()
    assert receipt["observed_direct_generic_occurrence_count"] == 4
    assert receipt["observed_v115_memoized_occurrence_count"] == 4
    assert receipt["fresh_v157_target_outcomes_accessed"] is False
    assert receipt["v156_failed_identity_preserved"] is True


def test_v157_sequence_classifies_both_observed_plan_modes_without_changing_execution():
    campaign = loads_canonical_json((ROOT / "v156_structural_margin_guarded_campaign.json").read_bytes())
    direct_source = campaign["target_occurrences"][0]["anonymous_relational_factor_prior_owned_sequence"]
    memo_source = campaign["target_occurrences"][4]["anonymous_relational_factor_prior_owned_sequence"]
    direct = annotate_applicable_plan_mode_sequence_v157(direct_source)
    memo = annotate_applicable_plan_mode_sequence_v157(memo_source)
    assert direct["applicable_plan_receipt_mode"] == "DIRECT_GENERIC_FACTOR_PROGRAM"
    assert memo["applicable_plan_receipt_mode"] == "V115_MEMOIZED_COMPILED_PROGRAM"
    assert direct["source_v154_sequence_id"] == direct_source["sequence_id"]
    assert memo["source_v154_sequence_id"] == memo_source["sequence_id"]
    assert direct["plan_mode_annotation_changes_planning_or_execution"] is False
    assert memo["all_executed_actions_have_v109_receipts"] is True
