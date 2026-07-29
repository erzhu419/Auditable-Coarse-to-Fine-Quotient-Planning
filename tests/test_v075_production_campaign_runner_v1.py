from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import threading
import time

import pytest

from acfqp import v075_production_campaign_runner_v1 as runner
from acfqp import v075_production_occurrence_authority_v1 as occurrence
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_public_campaign_authority_v1 as public
from tests import (
    test_v075_production_complete_bundle_endpoint_v1 as endpoint_fixture,
)
from tests import test_v075_production_occurrence_plan_v1 as plan_fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-production-runner-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def frozen_graph() -> tuple[
    public.V075PublicTargetTapeNamespaceV1,
    occurrence_plan.V075ProductionOccurrencePlanV1,
    occurrence_plan.V075ProductionOccurrencePlanVerificationV1,
]:
    namespace = plan_fixture._namespace("production-runner")
    plan = occurrence_plan.freeze_v075_production_occurrence_plan_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
    )
    replayed, verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            raw=plan.canonical_bytes,
        )
    )
    assert replayed == plan
    return namespace, plan, verification


def _issuer_inaccessible_input_standins(
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
) -> tuple[runner.V075AuthorizedOccurrenceExecutionInputV1, ...]:
    """Exact-type test stand-ins; never accepted without validator patching."""

    values = []
    for entry in plan.entries:
        value = object.__new__(
            runner.V075AuthorizedOccurrenceExecutionInputV1
        )
        for name, item in {
            "_issuer": object(),
            "plan": plan,
            "entry": entry,
            "controller": None,
            "ipc_profile": None,
            "authority": None,
            "private_salt": b"",
            "private_environment": None,
            "_binding_id": _id(f"input-{entry.entry_id}"),
        }.items():
            object.__setattr__(value, name, item)
        values.append(value)
    return tuple(values)


def _patch_construction_boundary(
    monkeypatch: pytest.MonkeyPatch,
    *,
    barrier: threading.Barrier | None = None,
) -> set[int]:
    thread_ids: set[int] = set()
    lock = threading.Lock()

    def boundary(entry):
        with lock:
            thread_ids.add(threading.get_ident())
        if barrier is not None:
            barrier.wait(timeout=10)
            time.sleep((14 - entry.scientific_ordinal) / 10_000)
        return runner.issue_v075_construction_campaign_runner_boundary_result_v1(
            entry=entry,
            marker_id=_id(f"marker-{entry.scientific_ordinal}"),
        )

    monkeypatch.setattr(
        runner,
        "_execute_v075_production_occurrence_boundary_v1",
        boundary,
    )
    return thread_ids


def test_fixed_parallel_profile_and_production_api_are_narrow() -> None:
    profile = runner.freeze_v075_production_campaign_runner_profile_v1()
    assert profile.max_workers == 15
    assert profile.to_document()["accuracy_reduction_allowed"] is False
    assert profile.to_document()["one_fresh_ipc_child_per_occurrence"] is True
    assert runner.PRODUCTION_CAMPAIGN_RUNNER_READY is True
    assert runner.TARGET_EXECUTION_OPENED is False
    assert runner.TARGET_AUTHORITY_CREATED is False
    assert runner.PRIVATE_LAW_DERIVATION_ALLOWED is False
    assert runner.SECRET_GENERATION_ALLOWED is False
    assert runner.OFFICIAL_EXECUTION_ALLOWED is False
    assert runner.OFFICIAL_SCALAR_COST is None
    assert runner.OFFICIAL_N_BREAK_EVEN is None
    assert runner.WORKLOAD_ECONOMICS_GATE_STATUS == "NOT_RUN"
    assert runner.COUNTER_COMPLETENESS_GATE_STATUS == "NOT_RUN"

    assert tuple(
        inspect.signature(
            runner.freeze_v075_production_campaign_runner_profile_v1
        ).parameters
    ) == ()
    signature = inspect.signature(runner.run_v075_production_campaign_v1)
    assert "callback" not in signature.parameters
    assert "target_law" not in signature.parameters
    assert "secret_generation_seed" not in signature.parameters
    assert (
        runner.bind_v075_production_occurrence_execution_input_v1
        is not None
    )


def test_construction_fixture_proves_concurrency_and_restores_order(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _namespace, plan, _verification = frozen_graph
    barrier = threading.Barrier(15)
    thread_ids = _patch_construction_boundary(
        monkeypatch,
        barrier=barrier,
    )
    evidence = (
        runner.execute_v075_construction_campaign_runner_fixture_v1(
            profile=(
                runner.freeze_v075_production_campaign_runner_profile_v1()
            ),
            plan=plan,
        )
    )
    assert evidence.peak_active_tasks == 15
    assert len(thread_ids) == 15
    assert tuple(item.scientific_ordinal for item in evidence.results) == (
        tuple(range(15))
    )
    assert set(evidence.completion_ordinals) == set(range(15))
    assert evidence.to_document()["scientific_order_restored"] is True
    assert evidence.to_document()["production_evidence"] is False
    assert evidence.to_document()["target_opened"] is False


def test_construction_fixture_requires_explicit_boundary_monkeypatch(
    frozen_graph,
) -> None:
    _namespace, plan, _verification = frozen_graph
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner.execute_v075_construction_campaign_runner_fixture_v1(
            profile=(
                runner.freeze_v075_production_campaign_runner_profile_v1()
            ),
            plan=plan,
        )


def test_thread_exception_fails_closed_and_retains_public_work(
    frozen_graph,
) -> None:
    _namespace, plan, plan_verification = frozen_graph
    results, _verifications = endpoint_fixture._semantic_standins(
        plan,
        plan_verification,
    )

    def boundary(entry):
        if entry.scientific_ordinal == 7:
            raise RuntimeError("private-salt-should-never-escape")
        return results[entry.scientific_ordinal]

    profile = runner.freeze_v075_production_campaign_runner_profile_v1()
    with pytest.raises(
        runner.V075ProductionCampaignRunnerProtocolOrIntegrityFailure
    ) as caught:
        runner._run_parallel_schedule_v1(
            values=plan.entries,
            max_workers=profile.max_workers,
            boundary=boundary,
            production_failure_context=(profile, plan),
        )
    error = caught.value
    assert error.failed_scientific_ordinals == (7,)
    assert "private-salt-should-never-escape" not in str(error)
    artifact = error.failure_artifact
    assert type(artifact) is runner.V075ProductionCampaignRunFailureV1
    document = artifact.to_document()
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["terminal_code"] == "RUNNER_THREAD_EXCEPTION"
    assert document["scientific_verdict"] is None
    assert document["eligible_for_reconciliation"] is False
    assert document["eligible_for_scientific_endpoint"] is False
    assert document["can_be_relabelled_scientific_pass_or_fail"] is False
    assert document["completed_slot_ordinals"] == [
        index for index in range(15) if index != 7
    ]
    assert document["failed_ordinals"] == [7]
    assert len(document["completion_ordinals"]) == 15
    assert document["future_submissions"] == 15
    assert document["future_completions"] == 15


def test_missing_duplicate_and_reordered_inputs_fail_before_execution(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace, plan, plan_verification = frozen_graph
    profile = runner.freeze_v075_production_campaign_runner_profile_v1()

    def forbidden(_value):
        raise AssertionError("execution boundary must not be reached")

    monkeypatch.setattr(
        runner,
        "_execute_v075_production_occurrence_boundary_v1",
        forbidden,
    )
    common = {
        "repository_root": REPOSITORY_ROOT,
        "namespace": namespace,
        "profile": profile,
        "plan": plan,
        "plan_verification": plan_verification,
    }
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner.run_v075_production_campaign_v1(
            **common,
            execution_inputs=(),
        )

    standins = _issuer_inaccessible_input_standins(plan)
    duplicated = (standins[0],) * 15
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner.run_v075_production_campaign_v1(
            **common,
            execution_inputs=duplicated,
        )
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner.run_v075_production_campaign_v1(
            **common,
            execution_inputs=tuple(reversed(standins)),
        )


@pytest.fixture()
def standin_production_graph(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
):
    namespace, plan, plan_verification = frozen_graph
    results, verifications = endpoint_fixture._semantic_standins(
        plan,
        plan_verification,
    )
    expected = {
        item.result_id: verification
        for item, verification in zip(
            results,
            verifications,
            strict=True,
        )
    }
    inputs = _issuer_inaccessible_input_standins(plan)

    def validate_inputs(*, plan, execution_inputs):
        assert plan == frozen_graph[1]
        assert execution_inputs == inputs
        assert all(
            type(item)
            is runner.V075AuthorizedOccurrenceExecutionInputV1
            for item in execution_inputs
        )

    def boundary(value):
        return results[value.entry.scientific_ordinal]

    def verify_result(*, repository_root, namespace, claimed):
        assert Path(repository_root).resolve() == REPOSITORY_ROOT
        assert namespace == frozen_graph[0]
        return expected[claimed.result_id]

    monkeypatch.setattr(
        runner,
        "_validate_production_execution_inputs_v1",
        validate_inputs,
    )
    monkeypatch.setattr(
        runner,
        "_execute_v075_production_occurrence_boundary_v1",
        boundary,
    )
    monkeypatch.setattr(
        occurrence,
        "verify_v075_production_occurrence_authority_result_v1",
        verify_result,
    )
    return (
        namespace,
        plan,
        plan_verification,
        inputs,
        results,
        verifications,
    )


def test_full_runner_reconciles_endpoint_and_verifies_without_reordering(
    standin_production_graph,
) -> None:
    (
        namespace,
        plan,
        plan_verification,
        inputs,
        results,
        _verifications,
    ) = standin_production_graph
    value = runner.run_v075_production_campaign_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        profile=runner.freeze_v075_production_campaign_runner_profile_v1(),
        plan=plan,
        plan_verification=plan_verification,
        execution_inputs=inputs,
    )
    assert value.occurrence_results == results
    assert tuple(
        item.plan_entry.scientific_ordinal
        for item in value.occurrence_results
    ) == tuple(range(15))
    assert value.reconciliation.plan_certificate_count == 15
    assert value.endpoint_verification.verdict.value == "PASS"
    assert value.runner_work.future_submissions == 15
    assert value.runner_work.future_completions == 15
    assert value.runner_work.scientific_result_slot_writes == 15
    assert (
        value.runner_work
        .coordinated_occurrence_process_launches_reference_only
        == 15
    )
    assert value.runner_work.runner_os_process_launches == 0
    assert set(value.runner_work.completion_ordinals) == set(range(15))
    assert 1 <= value.runner_work.peak_active_tasks <= 15
    document = value.to_document()
    assert document["target_execution_opened_by_runner"] is False
    assert document["target_authority_created_by_runner"] is False
    assert document["private_law_derived_by_runner"] is False
    assert document["scientific_order_restored"] is True
    assert (
        document["completion_order_not_used_as_scientific_order"]
        is True
    )
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None

    verified = runner.verify_v075_production_campaign_run_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        claimed=value,
    )
    assert verified.run_id == value.run_id
    assert verified.replayed_run_id == value.run_id
    assert verified.scientific_verdict.value == "PASS"


def test_reordered_boundary_output_is_non_scientific_protocol_failure(
    standin_production_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        namespace,
        plan,
        plan_verification,
        inputs,
        results,
        _verifications,
    ) = standin_production_graph

    def shifted(value):
        return results[(value.entry.scientific_ordinal + 1) % 15]

    monkeypatch.setattr(
        runner,
        "_execute_v075_production_occurrence_boundary_v1",
        shifted,
    )
    with pytest.raises(
        runner.V075ProductionCampaignRunnerProtocolOrIntegrityFailure
    ) as caught:
        runner.run_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            profile=(
                runner.freeze_v075_production_campaign_runner_profile_v1()
            ),
            plan=plan,
            plan_verification=plan_verification,
            execution_inputs=inputs,
        )
    artifact = caught.value.failure_artifact
    assert type(artifact) is runner.V075ProductionCampaignRunFailureV1
    assert (
        artifact.failure_code
        is runner.V075ProductionCampaignRunFailureCodeV1
        .OCCURRENCE_OUTPUT_IDENTITY_FAILURE
    )
    assert artifact.to_document()["scientific_verdict"] is None
    assert artifact.to_document()["reconciliation_id"] is None
    assert artifact.to_document()["endpoint_verification_id"] is None


def test_private_material_scan_rejects_raw_or_positive_leak_claims() -> None:
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner._assert_no_private_material_serialized_v1(
            {"private_salt": "forbidden"}
        )
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner._assert_no_private_material_serialized_v1(
            {"private_law_serialized": True}
        )
    with pytest.raises(
        runner.V075ProductionCampaignRunnerInvariantViolation
    ):
        runner._assert_no_private_material_serialized_v1(b"secret")
