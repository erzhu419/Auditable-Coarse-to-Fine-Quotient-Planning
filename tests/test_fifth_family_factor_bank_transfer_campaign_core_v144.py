from pathlib import Path
from functools import lru_cache

from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    maintenance_cascade_config_v144,
)
from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144 import (
    build_fifth_family_factor_bank_transfer_occurrence_v144,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@lru_cache(maxsize=1)
def _occurrence():
    config = maintenance_cascade_config_v144()
    return build_fifth_family_factor_bank_transfer_occurrence_v144(
        config,
        family=FAMILY,
        seed=1_044_003,
        episode_indices=(451, 452),
        dictionary=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes()
        ),
        dictionary_verification=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes()
        ),
    )


def test_v144_occurrence_factor_bank_update_reaches_compiled_planner():
    occurrence = _occurrence()
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["registered_gate"][
        "verified_v141_factor_bank_receipt_consumed"
    ] is True
    assert occurrence["registered_gate"][
        "planner_consumes_compiled_model_without_raw_rows"
    ] is True
    assert occurrence["registered_gate"][
        "planner_consumes_lowered_relational_execution_projection"
    ] is True
    assert occurrence["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert occurrence[
        "target_family_absent_from_v141_source_occurrence_archive"
    ] is True
    assert occurrence["sample_efficiency_direction"] in {"POSITIVE", "ZERO", "NEGATIVE"}
    assert occurrence["paired_label_reduction"] == occurrence["accounting"][
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior"
    ]


def test_v144_keeps_cost_axes_and_claims_separate():
    occurrence = _occurrence()
    accounting = occurrence["accounting"]
    assert accounting[
        "sample_labels_execution_steps_derivation_and_planning_compute_separate"
    ] is True
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["complete_ground_world_model_synthesized"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
