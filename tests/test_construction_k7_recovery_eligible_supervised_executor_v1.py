from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_recovery_eligible_accounted_runtime_v1 as runtime_v1
from acfqp import construction_k7_recovery_eligible_supervised_executor_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_public_surface_and_operational_no_full_replay_are_frozen() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleSupervisedExecutorV1Error",
        "DEFAULT_TIMEOUT_SECONDS",
        "EXPECTED_CHILD_INTEGRITY_OBLIGATIONS",
        "EXPECTED_CHILD_PROTOCOL_OBLIGATIONS",
        "INPUT_ROLES",
        "LOCAL_DOMAINS",
        "PARENT_INTEGRITY_OBLIGATIONS",
        "PARENT_PROTOCOL_OBLIGATIONS",
        "PRE_OUTPUT_SHARED_PATHS",
        "RecoveryEligiblePreOutputMeasurementV1",
        "RecoveryEligibleRuntimePreparationV1",
        "SupervisedRecoveryEligibleExecutionV1",
        "execute_recovery_eligible_accounted_v1",
        "prepare_recovery_eligible_accounted_runtime_v1",
        "require_supervised_recovery_eligible_execution_v1",
    }
    source = inspect.getsource(runtime_v1.main)
    assert "verify_recovery_eligible_native_accounting_v1" not in source
    assert "verify_recovery_eligible_world_model_loop_v1" not in source
    assert "execute_recovery_eligible_native_accounted_occurrence_v1" in source


def test_runtime_preparation_freezes_the_new_worker(tmp_path: Path) -> None:
    preparation = subject.prepare_recovery_eligible_accounted_runtime_v1(
        repository_root=Path(__file__).parents[1],
        runtime_cas_root=tmp_path / "cas",
    )
    document = preparation.to_document()
    assert (
        "acfqp.construction_k7_recovery_eligible_accounted_runtime_v1"
        in preparation.source_closure.root_modules
    )
    assert document["runtime_entrypoint"].endswith(
        "construction_k7_recovery_eligible_accounted_runtime_v1.py"
    )
    assert document["runtime_tree_build_charged_to_occurrence"] is False
    assert document["official_execution_allowed"] is False


@pytest.fixture(scope="module")
def real_supervised_execution(tmp_path_factory):
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    if (
        os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") != "1"
        or not retained
    ):
        pytest.skip("real recovery supervised execution is disabled")
    retained_root = Path(retained)
    root = tmp_path_factory.mktemp("recovery-supervised")
    preparation = subject.prepare_recovery_eligible_accounted_runtime_v1(
        repository_root=Path(__file__).parents[1],
        runtime_cas_root=root / "cas",
    )
    trace = root / "operational-trace.json"
    result = subject.execute_recovery_eligible_accounted_v1(
        preparation,
        binding_bytes=(retained_root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(retained_root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(
            retained_root / "PROOF_DEPENDENCY_TRANSITION.json"
        ).read_bytes(),
        logical_occurrence_id=_fresh_id("recovery-supervised-occurrence-1"),
        query_ordinal=4,
        trace_output_path=trace,
    )
    return result, trace


def test_real_fresh_worker_closes_eight_preoutput_paths(
    real_supervised_execution,
) -> None:
    result, trace = real_supervised_execution
    verified = subject.require_supervised_recovery_eligible_execution_v1(result)
    measurement = verified.measurement
    assert trace.read_bytes() == result.trace_raw
    assert len(result.recorded_stages) == 3
    assert set(measurement.fixed_values) == set(subject.PRE_OUTPUT_SHARED_PATHS) - {
        "io.mounted_bytes_peak"
    }
    assert all(value > 0 for value in measurement.fixed_values.values())
    assert measurement.fixed_values["process.launches"] == 1
    assert measurement.pre_output_mounted_bytes_peak > 0
    assert measurement.mounted_bytes_peak(0) == measurement.pre_output_mounted_bytes_peak


def test_real_science_and_no_replay_boundary_are_preserved(
    real_supervised_execution,
) -> None:
    result, _trace = real_supervised_execution
    science = result.science_summary
    assert science["proof_node_reuse_count"] == 41
    assert science["requested_frontier_row_count"] == 6
    assert science["local_ground_draw_count"] == 12_672
    assert science["changed_abstract_row_count"] == 6
    assert science["fallback_ground_steps"] == 96
    assert science["terminal_class"] == "PLAN_CERTIFICATE"
    assert science["terminal_code"] == "FULL_GROUND_FALLBACK"
    assert result.trace_document["full_planner_replayed_for_operational_validation"] is False
    assert result.trace_document["standalone_verifier_work_included"] is False


def test_supervised_execution_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7RecoveryEligibleSupervisedExecutorV1Error
    ):
        subject.require_supervised_recovery_eligible_execution_v1(object())  # type: ignore[arg-type]
