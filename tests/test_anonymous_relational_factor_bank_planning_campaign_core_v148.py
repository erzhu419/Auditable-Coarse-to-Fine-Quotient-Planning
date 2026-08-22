from pathlib import Path

from acfqp.anonymous_relational_factor_bank_planning_campaign_core_v148 import (
    build_anonymous_relational_factor_bank_occurrence_v148,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    maintenance_cascade_config_v144,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v148_relational_prior_receipt_reaches_receding_planner_on_frozen_source():
    source = loads_canonical_json(
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes()
    )["target_occurrences"][0]
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_024
    row = build_anonymous_relational_factor_bank_occurrence_v148(
        config,
        family=FAMILY,
        seed=source["seed"],
        episode_indices=(601, 602),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            ROOT / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["paired_label_reduction"] > 0
    assert row["registered_gate"][
        "planner_consumes_lowered_relational_execution_projection"
    ] is True
    assert row["registered_gate"]["sound_certificate_local_recovery_union"] is True
    assert row["complete_ground_world_model_synthesized"] is False
    assert row["official_scalar_cost"] is None
