from pathlib import Path

import pytest

from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY as INVENTORY
from acfqp.generic_modular_routing_adapter_v128 import modular_routing_config_v128
from acfqp.opaque_archive_planning_campaign_core_v133 import (
    build_opaque_archive_planning_occurrence_v133,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@pytest.fixture(scope="module")
def occurrence():
    config = modular_routing_config_v128()
    config["families"][INVENTORY]["maximum_acquisition_labels"] = 320
    return build_opaque_archive_planning_occurrence_v133(
        config,
        family=INVENTORY,
        seed=1_033_201,
        episode_indices=(401, 402),
        dictionary=loads_canonical_json(
            (ROOT / "v132_opaque_source_archive_dictionary.json").read_bytes()
        ),
        dictionary_verification=loads_canonical_json(
            (ROOT / "v132_opaque_source_archive_verification.json").read_bytes()
        ),
    )


def test_v133_verified_receipt_reaches_compiled_planner(occurrence):
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["registered_gate"]["verified_v132_receipt_consumed"] is True
    assert occurrence["registered_gate"][
        "planner_consumes_compiled_model_without_raw_rows"
    ] is True
    assert occurrence["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert occurrence["accounting"][
        "acquisition_labels_avoided_by_opaque_archive_prior"
    ] > 0


def test_v133_keeps_sample_and_compute_axes_separate(occurrence):
    accounting = occurrence["accounting"]
    assert accounting[
        "sample_labels_execution_steps_derivation_and_planning_compute_separate"
    ] is True
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
