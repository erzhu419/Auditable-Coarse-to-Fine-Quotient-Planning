from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path

import pytest

from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import v075_k7_causal_promotion_complete_bundle_independent_verifier_v1 as independent_v1
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
    assert document["semantic_terminal_artifact_issued"] is True
    assert document["semantic_terminal_scope"] == "ROUTE_ATTEMPT"
    assert document["semantic_terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["semantic_terminal_code"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert document["generic_trusted_budget_replay_v1_implemented"] is False
    assert document["logical_occurrence_closed"] is False
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


def test_real_complete_bundle_is_independently_replayed(real_bundle) -> None:
    bundle, output = real_bundle
    verification = (
        independent_v1
        .verify_v075_k7_causal_promotion_complete_bundle_directory_v1(output)
    )

    assert verification.occurrence_id == bundle.work_vector.subject_id
    assert verification.work_vector_id == bundle.work_vector.work_vector_id
    assert verification.comparison_vector_id == (
        bundle.comparison_vector.comparison_vector_id
    )
    assert verification.projection_proof_id == (
        bundle.actual_projection_proof.actual_projection_proof_id
    )
    assert verification.output_bytes == bundle.fixed_point.output_bytes
    document = verification.to_document()
    assert document["all_eight_canonical_roles_replayed"] is True
    assert document["all_202_counter_records_reconstructed"] is True
    assert document["all_182_operational_leaves_projected_exactly_once"] is True
    assert document["typed_attempt_budget_terminal_reconstructed"] is True
    assert document["verification_lane"] == "EVALUATION"
    assert document["logical_occurrence_closed"] is False
    assert document["official_execution_allowed"] is False

    role_bytes = {
        role: (output / f"{role}.json").read_bytes()
        for role in independent_v1.REQUIRED_ROLES
    }

    budget = loads_canonical_json(role_bytes["OPERATIONAL_TRACE"])[
        "budget_replay_attestation"
    ]
    cap = budget["budget_closure"]["cap_profile"]
    cap["profile_kez"] = cap.pop("profile_key")
    with pytest.raises(
        independent_v1
        .V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error
    ):
        independent_v1._verify_budget_attestation(budget)  # noqa: SLF001

    changed = loads_canonical_json(role_bytes["WORK_VECTOR"])
    changed["work_vector"]["work_vector_id"] = (
        "0" if changed["work_vector"]["work_vector_id"][0] != "0" else "1"
    ) + changed["work_vector"]["work_vector_id"][1:]
    role_bytes["WORK_VECTOR"] = canonical_json_bytes(changed)
    manifest = loads_canonical_json(role_bytes["OUTPUT_MANIFEST"])
    manifest_row = next(
        row
        for row in manifest["ordered_preceding_roles"]
        if row["artifact_role"] == "WORK_VECTOR"
    )
    assert manifest_row["byte_count"] == len(role_bytes["WORK_VECTOR"])
    manifest_row["bytes_sha256"] = hashlib.sha256(
        role_bytes["WORK_VECTOR"]
    ).hexdigest()
    role_bytes["OUTPUT_MANIFEST"] = canonical_json_bytes(manifest)
    with pytest.raises(
        independent_v1
        .V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error
    ):
        independent_v1.verify_v075_k7_causal_promotion_complete_bundle_bytes_v1(
            role_bytes
        )

    terminal_roles = {
        role: (output / f"{role}.json").read_bytes()
        for role in independent_v1.REQUIRED_ROLES
    }
    terminal = loads_canonical_json(terminal_roles["TERMINAL_ARTIFACT"])
    context = terminal["route_decision_context"]
    context["route_kond"] = context.pop("route_kind")
    terminal_roles["TERMINAL_ARTIFACT"] = canonical_json_bytes(terminal)
    manifest = loads_canonical_json(terminal_roles["OUTPUT_MANIFEST"])
    manifest_row = next(
        row
        for row in manifest["ordered_preceding_roles"]
        if row["artifact_role"] == "TERMINAL_ARTIFACT"
    )
    assert manifest_row["byte_count"] == len(
        terminal_roles["TERMINAL_ARTIFACT"]
    )
    manifest_row["bytes_sha256"] = hashlib.sha256(
        terminal_roles["TERMINAL_ARTIFACT"]
    ).hexdigest()
    terminal_roles["OUTPUT_MANIFEST"] = canonical_json_bytes(manifest)
    with pytest.raises(
        independent_v1
        .V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error
    ):
        independent_v1.verify_v075_k7_causal_promotion_complete_bundle_bytes_v1(
            terminal_roles
        )
