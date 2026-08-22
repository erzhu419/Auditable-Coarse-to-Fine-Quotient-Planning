from pathlib import Path

from acfqp.generic_ternary_relation_workflow_adapter_v152 import FAMILY, ternary_relation_workflow_config_v152
from acfqp.ternary_relational_transfer_campaign_core_v152 import build_ternary_relational_transfer_occurrence_v152


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v152_development_occurrence_transfers_relation_across_cardinality():
    row = build_ternary_relational_transfer_occurrence_v152(
        ternary_relation_workflow_config_v152(),
        family=FAMILY,
        seed=1_047_002,
        episode_indices=(611, 612),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"]["three_key_relation_instantiated_from_two_key_source_template"] is True
    assert row["paired_label_reduction"] == 8
    assert row["source_relation_key_cardinality"] == 2
    assert row["target_relation_key_cardinality"] == 3
    assert row["relation_cardinality_supplied_by_prior"] is False
    assert row["official_scalar_cost"] is None
