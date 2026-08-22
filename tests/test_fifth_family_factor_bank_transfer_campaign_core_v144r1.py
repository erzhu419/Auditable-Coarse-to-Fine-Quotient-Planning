from functools import lru_cache
from pathlib import Path

from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144r1 import (
    build_fifth_family_factor_bank_transfer_occurrence_v144r1,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    maintenance_cascade_config_v144,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@lru_cache(maxsize=1)
def _occurrence():
    return build_fifth_family_factor_bank_transfer_occurrence_v144r1(
        maintenance_cascade_config_v144(),
        family=FAMILY,
        seed=1_044_004,
        episode_indices=(461, 462),
        dictionary=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes()
        ),
        dictionary_verification=loads_canonical_json(
            (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes()
        ),
    )


def test_v144r1_runs_relational_overlay_capable_owned_sequence():
    occurrence = _occurrence()
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["registered_gate"][
        "certificate_local_relational_overlay_pipeline_present"
    ] is True
    assert occurrence["registered_gate"][
        "planner_consumes_lowered_relational_execution_projection"
    ] is True
    assert occurrence[
        "v144_preregistered_incremental_relational_projection_failure_preserved"
    ] is True
    for key in (
        "occurrence_factor_bank_update_prior_query_local_overlay_edges",
        "strict_no_prior_query_local_overlay_edges",
    ):
        assert occurrence["accounting"][key] >= 0


def test_v144r1_keeps_overlay_and_cost_claims_bounded():
    occurrence = _occurrence()
    assert occurrence[
        "query_local_relational_overlay_used_only_after_certificate_failure"
    ] is True
    assert occurrence["complete_ground_world_model_synthesized"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
