from __future__ import annotations

import os
from pathlib import Path

import pytest

from acfqp import construction_k7_all_path_production_terminal_finalizer_v180r3 as finalizer


def test_v34_production_adapter_refuses_a_preexisting_output_tree(tmp_path: Path) -> None:
    root = tmp_path / "already-present"
    root.mkdir()
    with pytest.raises(
        finalizer.ConstructionK7AllPathProductionTerminalFinalizerV180r3Error,
        match="new absent Path",
    ):
        finalizer.run_v34_abstract_certified_production_occurrence_v180r3(root)


def test_absent_platform_path_reaches_the_frozen_site_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "absent-output"

    def reached(_root: Path) -> None:
        assert _root == root
        raise RuntimeError("site boundary reached")

    monkeypatch.setattr(
        finalizer.v34_campaign,
        "run_standard_2048_expression_full_accounted_campaign_v34",
        reached,
    )
    with pytest.raises(RuntimeError, match="site boundary reached"):
        finalizer.run_v34_abstract_certified_production_occurrence_v180r3(root)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_V180R3_V34_PRODUCTION") != "1",
    reason="requires the preregistered fresh V34 production occurrence",
)
def test_fresh_v34_site_materializes_one_v180r3_terminal_bundle(
    tmp_path: Path,
) -> None:
    result = finalizer.run_v34_abstract_certified_production_occurrence_v180r3(
        tmp_path / "v34-production-output"
    )
    document = result.to_document()
    assert document["terminal_code"] == "ABSTRACT_CERTIFIED"
    assert document["fresh_v180r3_observed_occurrence_present"] is True
    assert document["historical_summary_translation_used"] is False
    assert document["development_fixture_only"] is False
    assert document["production_occurrence_receipt"][
        "source_operational_work_vector_count"
    ] == 45
    assert document["output_bytes_fixed_point"] == (
        document["source_output_bytes"] + len(result.canonical_bytes)
    )
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
