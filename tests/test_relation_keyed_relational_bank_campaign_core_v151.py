from pathlib import Path

from acfqp.generic_relation_keyed_workflow_adapter_v151 import (
    FAMILY,
    relation_keyed_workflow_config_v151,
)
from acfqp.relation_keyed_relational_bank_campaign_core_v151 import (
    build_relation_keyed_relational_bank_occurrence_v151,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v151_development_occurrence_uses_relational_template_and_plans():
    row = build_relation_keyed_relational_bank_occurrence_v151(
        relation_keyed_workflow_config_v151(),
        family=FAMILY,
        seed=1_047_001,
        episode_indices=(591, 592),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            ROOT / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"]["relational_artifact_selected_in_prior_arm"] is True
    assert row["paired_label_reduction"] == 8
    assert row["relational_template_selection_itself_observed"] is True
    assert row["direct_numeric_increment_field_present"] is False
    assert row["official_scalar_cost"] is None
