from acfqp.construction_k7_cross_occurrence_reuse_failure_v75 import (
    freeze_cross_occurrence_reuse_failure_v75,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v75_failure_is_typed_and_preserves_every_target_row():
    document = loads_canonical_json(freeze_cross_occurrence_reuse_failure_v75())
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["derived_minus_strict_target_labels"] == 0
    assert len(document["target_rows"]) == 4
    assert all(row["derived_labels"] == row["strict_labels"] for row in document["target_rows"])
    assert document["same_identity_rerun_or_gate_relaxation_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
