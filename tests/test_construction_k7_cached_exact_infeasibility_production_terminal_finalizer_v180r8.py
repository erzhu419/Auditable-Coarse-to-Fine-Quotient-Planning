from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_finalizer_v180r8 as finalizer
from acfqp.accounting_v1 import WorkVectorV1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
HELPER = Path(__file__).with_name("_cached_exact_v180r8_subprocess.py")


def _run(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(HELPER), str(tmp_path / "run")],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    summary = json.loads(completed.stdout)
    document = loads_canonical_json(Path(summary["terminal_path"]).read_bytes())
    assert type(document) is dict
    return document


@pytest.fixture(scope="module")
def cached_terminal(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run(tmp_path_factory.mktemp("v180r8-cached-terminal"))


def test_v180r8_fresh_cache_path_has_durable_match_and_complete_v9_chain(
    cached_terminal: dict,
) -> None:
    document = cached_terminal
    registry = registry_v9.official_counter_registry_v9()
    vector = WorkVectorV1.from_dict(document["terminal_work_vector"], registry)

    assert document["terminal_code"] == "CACHED_EXACT_INFEASIBLE"
    assert document["terminal_class"] == "INFEASIBILITY_CERTIFICATE"
    assert document["durable_independent_verification"]["outcome"] == "IDENTICAL_MATCH"
    assert document["durable_cache_consumption"]["outcome"] == "IDENTICAL_MATCH"
    assert len(vector.records) == 269
    assert vector.values["common.abstract_subproof_cache_lookups"] == 1
    assert vector.values["route.attempts"] == 1
    assert vector.values["route.successes"] == 1
    assert vector.values["route.failures"] == 0
    assert vector.values["io.output_bytes"] == document["output_bytes_fixed_point"]
    assert document["output_bytes_fixed_point"] == len(canonical_json_bytes(document))


def test_v180r8_shared_receipts_are_exactly_nine_and_claims_remain_locked(
    cached_terminal: dict,
) -> None:
    document = cached_terminal
    receipt_set = document["shared_resource_receipt_set"]
    rows = receipt_set["receipts"]
    assert receipt_set["ordered_paths"] == list(finalizer.SHARED_RESOURCE_PATHS)
    assert [row["path"] for row in rows] == list(finalizer.SHARED_RESOURCE_PATHS)
    assert len(rows) == 9
    assert all(row["complete_through_terminal_cutoff"] is True for row in rows)
    assert document["ground_solver_called_in_online_window"] is False
    assert document["planner_called_in_online_window"] is False
    assert document["proof_producer_called_in_online_window"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_v180r8_online_source_is_pinned_and_plan_is_fresh(
    cached_terminal: dict,
) -> None:
    document = cached_terminal
    assert document["source_receipt"]["canonical_byte_count"] == (
        finalizer.EXPECTED_DURABLE_PROOF_BYTE_COUNT
    )
    assert document["source_receipt"]["canonical_sha256"] == (
        finalizer.EXPECTED_DURABLE_PROOF_SHA256
    )
    assert document["source_receipt"]["durable_exact_infeasibility_proof_id"] == (
        finalizer.EXPECTED_DURABLE_PROOF_ID
    )
    assert document["logical_occurrence_id"] == finalizer.LOGICAL_OCCURRENCE_ID
    assert document["selected_plan_id"] == finalizer.SELECTED_PLAN_ID
    assert document["historical_summary_translation_used"] is False
    assert document["development_fixture_only"] is False
