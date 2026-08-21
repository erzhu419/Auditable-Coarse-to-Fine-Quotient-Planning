from pathlib import Path

import pytest

from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134
from acfqp.occurrence_factor_bank_update_planning_campaign_core_v142 import (
    build_occurrence_factor_bank_update_planning_occurrence_v142,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@pytest.fixture(scope="module")
def occurrence():
    config = packet_batching_config_v134()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 384
    return build_occurrence_factor_bank_update_planning_occurrence_v142(
        config,
        family=FAMILY,
        seed=1_038_101,
        episode_indices=(431, 432),
        dictionary=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes()
        ),
        dictionary_verification=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes()
        ),
    )


def test_v142_occurrence_factor_bank_update_reaches_compiled_planner(occurrence):
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["registered_gate"][
        "verified_v141_factor_bank_receipt_consumed"
    ] is True
    assert occurrence["registered_gate"][
        "planner_consumes_compiled_model_without_raw_rows"
    ] is True
    assert occurrence["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert occurrence["accounting"][
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior"
    ] > 0


def test_v142_keeps_cost_axes_and_claims_separate(occurrence):
    accounting = occurrence["accounting"]
    assert accounting[
        "sample_labels_execution_steps_derivation_and_planning_compute_separate"
    ] is True
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["complete_ground_world_model_synthesized"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
