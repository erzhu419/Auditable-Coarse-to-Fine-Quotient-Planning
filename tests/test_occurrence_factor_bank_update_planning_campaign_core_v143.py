from pathlib import Path

import pytest

from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134
from acfqp.occurrence_factor_bank_update_planning_campaign_core_v143 import (
    build_occurrence_factor_bank_update_planning_occurrence_v143,
)
from acfqp.phase3e_ids import loads_canonical_json
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    GenericArtifactSubprogramInstantiatorV121Error,
)
from acfqp import occurrence_factor_bank_update_acquisition_v143 as acquisition


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@pytest.fixture(scope="module")
def occurrence():
    config = packet_batching_config_v134()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 384
    return build_occurrence_factor_bank_update_planning_occurrence_v143(
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


def test_v143_occurrence_factor_bank_update_reaches_compiled_planner(occurrence):
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
    assert occurrence["sample_efficiency_direction"] in {"POSITIVE", "ZERO", "NEGATIVE"}
    assert occurrence["paired_label_reduction"] == occurrence["accounting"][
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior"
    ]


def test_v143_keeps_cost_axes_and_claims_separate(occurrence):
    accounting = occurrence["accounting"]
    assert accounting[
        "sample_labels_execution_steps_derivation_and_planning_compute_separate"
    ] is True
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["complete_ground_world_model_synthesized"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v143_invalidates_unreplayable_candidate_without_aborting_campaign(
    monkeypatch,
):
    original = acquisition.robust_dictionary_factor_stop_update_v131r2
    injected = {"done": False}

    def once(*args, **kwargs):
        if injected["done"] is False:
            injected["done"] = True
            raise GenericArtifactSubprogramInstantiatorV121Error("injected")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        acquisition, "robust_dictionary_factor_stop_update_v131r2", once
    )
    config = packet_batching_config_v134()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 384
    result = build_occurrence_factor_bank_update_planning_occurrence_v143(
        config,
        family=FAMILY,
        seed=1_038_102,
        episode_indices=(433, 434),
        dictionary=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes()
        ),
        dictionary_verification=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes()
        ),
    )
    replay_errors = sum(
        result[key]["candidate_replay_error_count"]
        for key in (
            "occurrence_factor_bank_update_factor_prior_acquisition",
            "strict_no_prior_acquisition",
        )
    )
    assert replay_errors == 1
    assert result["registered_gate"]["passed"] is True
