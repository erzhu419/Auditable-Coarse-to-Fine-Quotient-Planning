from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path

import pytest

from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import v075_k7_causal_promotion_occurrence_accounting_v1 as subject


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_accounting_domains_are_central_and_claims_remain_bounded() -> None:
    assert {
        subject.BUNDLE_DOMAIN,
        subject.OUTPUT_COMMIT_DOMAIN,
        subject.PATH_AGGREGATION_DOMAIN,
        subject.RENDERER_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)
    assert subject.EXPECTED_REQUIRED_PATH_COUNT == 202
    assert subject.EXPECTED_SHARED_PATH_COUNT == 9
    assert subject.SHARED_PATHS == (
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.mounted_bytes_peak",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "memory.working_bytes_peak",
        "process.launches",
    )


@pytest.fixture(scope="module")
def real_bundle(tmp_path_factory: pytest.TempPathFactory):
    if os.environ.get("ACFQP_RUN_REAL_K7_CAUSAL_ACCOUNTING") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_CAUSAL_ACCOUNTING=1")
    root = tmp_path_factory.mktemp("k7-causal-accounting")
    output = root / "output"
    bundle = subject.run_v075_causal_promotion_occurrence_accounting_v1(
        repository_root=REPOSITORY_ROOT,
        runtime_cas_root=root / "runtime-cas",
        output_directory=output,
        construction_fixture_marker="real-accounting-gate",
        timeout_seconds=3_600,
    )
    return bundle, output


def test_real_supervised_nine_path_chain_and_output_commit(real_bundle) -> None:
    bundle, output = real_bundle
    subject.verify_v075_causal_promotion_occurrence_accounting_v1(bundle)
    values = bundle.work_vector.values
    measurement = bundle.supervised_execution.measurement

    assert len(bundle.supervised_execution.recorded_stages) == 12
    assert sum(
        len(row.work_vector.records)
        for row in bundle.supervised_execution.recorded_stages
    ) == 2_424
    assert len(bundle.path_aggregations) == 202
    assert len(bundle.work_vector.records) == 202
    assert bundle.actual_projection_proof.projection_term_count == 182
    assert values["io.output_bytes"] == bundle.fixed_point.output_bytes
    assert values["io.output_bytes"] == sum(
        path.stat().st_size for path in output.iterdir()
    )
    assert values["io.mounted_bytes_peak"] == max(
        measurement.pre_output_mounted_bytes_peak,
        values["io.output_bytes"],
    )
    assert values["process.launches"] == 1
    assert values["process.exit_successes"] == 1
    assert values["process.exit_failures"] == 0
    assert values["route.attempts"] == 1
    assert values["route.successes"] == 0
    assert values["route.failures"] == 1
    assert values["solver.attempts"] == 0
    assert values["solver.successes"] == 0
    assert values["solver.failures"] == 0
    assert values["common.hash_invocations"] > 0
    assert values["common.integrity_checks"] > 0
    assert values["common.protocol_checks"] > 0
    assert values["io.read_bytes"] > 0
    assert values["io.staged_bytes"] > 0
    assert values["memory.working_bytes_peak"] > 0

    expected_names = {
        f"{role}.json"
        for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    }
    assert {path.name for path in output.iterdir()} == expected_names
    assert tuple(row.artifact_role for row in bundle.output_commit.role_commits) == (
        fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    )
    for row in bundle.output_commit.role_commits:
        raw = (output / row.filename).read_bytes()
        assert len(raw) == row.byte_count
        assert hashlib.sha256(raw).hexdigest() == row.bytes_sha256

    document = bundle.to_document()
    assert document["shared_resource_measurement_complete"] is True
    assert document["complete_202_counter_record_chain_present"] is True
    assert document["all_182_operational_leaves_projected_exactly_once"] is True
    assert document["eight_operational_roles_committed_once"] is True
    assert document["semantic_terminal_artifact_issued"] is False
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_real_bundle_rejects_crossed_commit_and_counter_mutations(real_bundle) -> None:
    bundle, _output = real_bundle
    first = bundle.output_commit.role_commits[0]
    with pytest.raises(subject.V075K7CausalPromotionOccurrenceAccountingV1Error):
        replace(
            bundle.output_commit,
            role_commits=(replace(first, byte_count=first.byte_count + 1),)
            + bundle.output_commit.role_commits[1:],
        )

    changed = replace(
        bundle.path_aggregations[0],
        value=bundle.path_aggregations[0].value + 1,
    )
    forged = replace(
        bundle,
        path_aggregations=(changed,) + bundle.path_aggregations[1:],
    )
    with pytest.raises(subject.V075K7CausalPromotionOccurrenceAccountingV1Error):
        subject.verify_v075_causal_promotion_occurrence_accounting_v1(forged)
