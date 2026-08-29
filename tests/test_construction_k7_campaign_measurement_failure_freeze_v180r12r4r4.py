from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r4 as freeze,
)


def test_ordinal9_failure_freeze_separates_ownership_from_conformance() -> None:
    frozen = freeze.freeze_ordinal9_failure_v180r12r4r4()
    contract = frozen.to_contract()

    assert frozen.freeze_id == freeze.ORDINAL9_FAILURE_FREEZE_ID
    assert contract["campaign_attempt_artifact_present"] is False
    assert contract["campaign_started"] is False
    assert contract["campaign_ledger_event_count"] == 0
    assert contract["outer_service_unit_ownership_acquired"] is True
    assert contract["full_source_conformance"] is False
    assert contract["runtime_full_property_diagnostic_recorded"] is False
    assert contract["postmortem_full_property_diagnostic_recorded"] is True
    assert contract["source_conformance_diagnostic"]["mismatch_fields"] == [
        "mode"
    ]
    assert contract["source_conformance_diagnostic"]["expected"]["mode"] == 0o644
    assert (
        contract["source_conformance_diagnostic"]["failed_source_snapshot"][
            "before"
        ]["mode"]
        == 0o664
    )
    assert contract["counter_records_issued"] is False
    assert contract["work_vectors_issued"] is False
    assert contract["comparison_vectors_issued"] is False
    assert set(contract["gate_statuses"].values()) == {"NOT_RUN"}
    assert contract["same_identity_rerun_forbidden"] is True
    assert contract["fresh_successor_identity_required"] is True


def test_ordinal9_failure_freeze_rejects_raw_artifact_drift(tmp_path: Path) -> None:
    retained = Path(freeze._DEFAULT_RETAINED_ROOT)
    candidate = tmp_path / "ordinal9"
    shutil.copytree(retained, candidate)
    target = candidate / "raw/inner_launch_failure.json"
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        freeze.Ordinal9FailureFreezeV180r12r4r4Error,
        match="inner_launch_failure raw bytes changed",
    ):
        freeze.freeze_ordinal9_failure_v180r12r4r4(candidate)
