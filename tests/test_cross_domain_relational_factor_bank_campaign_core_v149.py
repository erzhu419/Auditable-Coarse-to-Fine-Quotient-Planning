from pathlib import Path

from acfqp.cross_domain_relational_factor_bank_campaign_core_v149 import (
    build_cross_domain_relational_factor_bank_occurrence_v149,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY,
    inventory_assembly_config_v118,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v149_cross_domain_historical_negative_control_reaches_planner():
    config = inventory_assembly_config_v118()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_536
    row = build_cross_domain_relational_factor_bank_occurrence_v149(
        config,
        family=FAMILY,
        seed=1_047_231,
        episode_indices=(561, 562),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            ROOT / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["paired_label_reduction"] > 0
    assert row["registered_gate"][
        "anonymous_relational_instantiation_present_both_arms"
    ] is True
    assert row[
        "relational_instantiation_present_but_relational_template_selection_not_required"
    ] is True
    assert row["complete_ground_world_model_synthesized"] is False
    assert row["official_scalar_cost"] is None
