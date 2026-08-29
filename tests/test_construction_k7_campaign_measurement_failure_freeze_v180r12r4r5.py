from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r5 as freeze,
)


def test_ordinal10_failure_freeze_separates_source_t1_and_runtime_facts() -> None:
    frozen = freeze.freeze_ordinal10_failure_v180r12r4r5()
    contract = frozen.to_contract()

    assert frozen.freeze_id == freeze.ORDINAL10_FAILURE_FREEZE_ID
    assert frozen.freeze_id == freeze.EXPECTED_ORDINAL10_FAILURE_FREEZE_ID
    assert contract["prelaunch_materialization_succeeded"] is True
    assert contract["source_root_count"] == 24
    assert contract["full_source_conformance"] is True
    assert contract["source_conformance_mismatch_count"] == 0
    assert contract["source_conformance_cause"] is None
    assert contract["source_conformance_full_property_snapshots_recorded"] is True
    assert len(contract["source_conformance_diagnostic"]["snapshots"]) == 24
    assert contract["outer_service_unit_ownership_acquired"] is True
    assert contract["production_runtime_placement_t1_complete"] is True
    assert contract["production_runtime_placement_t2_complete"] is False
    assert contract["runtime_failure_generic_cause_recorded"] is True
    assert contract["runtime_failure_property_snapshots_recorded"] is False
    assert contract["runtime_failure_per_field_mismatch_recorded"] is False
    assert contract["runtime_failure_exact_cause_dimension_recorded"] is False
    assert contract["postmortem_delegate_diagnostic_consumed"] is False
    assert contract["campaign_attempt_artifact_present"] is False
    assert contract["campaign_started"] is False
    assert contract["campaign_ledger_event_count"] == 0
    assert contract["campaign_artifacts_absent"] is True
    assert contract["counter_records_issued"] is False
    assert contract["work_vectors_issued"] is False
    assert contract["comparison_vectors_issued"] is False
    assert set(contract["gate_statuses"].values()) == {"NOT_RUN"}
    assert contract["official_execution_allowed"] is False
    assert contract["independent_replay_present"] is False
    assert contract["same_identity_rerun_forbidden"] is True
    assert contract["fresh_successor_identity_required"] is True


def test_ordinal10_failure_freeze_rejects_raw_artifact_drift(
    tmp_path: Path,
) -> None:
    retained = Path(freeze._DEFAULT_RETAINED_ROOT)
    candidate = tmp_path / "ordinal10"
    shutil.copytree(retained, candidate)
    target = candidate / "raw/inner_launch_failure.json"
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        freeze.Ordinal10FailureFreezeV180r12r4r5Error,
        match="inner_launch_failure raw bytes changed",
    ):
        freeze.freeze_ordinal10_failure_v180r12r4r5(candidate)
