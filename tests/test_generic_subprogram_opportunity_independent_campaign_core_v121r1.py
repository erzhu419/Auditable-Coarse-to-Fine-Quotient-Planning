from pathlib import Path

from acfqp.generic_subprogram_opportunity_independent_campaign_core_v121r1 import (
    correct_generic_subprogram_occurrence_gate_v121r1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v121r1_corrects_only_the_opportunity_dependent_failed_gate():
    failed = loads_canonical_json(
        (ROOT / "v121_generic_artifact_subprogram_campaign.json").read_bytes()
    )
    base = failed["target_occurrences"][1]
    assert base["registered_gate"]["passed"] is False
    assert base["registered_gate"]["same_epoch_genesis_authorization_observed"] is False
    corrected = correct_generic_subprogram_occurrence_gate_v121r1(base)
    assert corrected["base_v121_occurrence"] == base
    assert corrected["base_v121_gate_passed"] is False
    assert corrected["same_epoch_genesis_authorized_cache_hit_count"] == 0
    assert corrected["registered_gate"]["passed"] is True
    assert corrected["scientific_outcome_fields_changed_from_base"] is False
    assert corrected["official_scalar_cost"] is None
