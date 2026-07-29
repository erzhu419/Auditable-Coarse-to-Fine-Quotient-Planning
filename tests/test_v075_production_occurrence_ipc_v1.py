from __future__ import annotations

from dataclasses import replace
import ast
import inspect

import pytest

from acfqp import v075_production_occurrence_ipc_v1 as ipc
from tests.test_v075_integrated_occurrence_pipeline_v1 import _open


def _profile(
    marker: str,
    ordinal: int,
    *,
    behavior: ipc.V075ProductionIPCBehaviorV1 = (
        ipc.V075ProductionIPCBehaviorV1.HONEST
    ),
):
    (
        namespace,
        context,
        arm,
        identity,
        authority,
        replay_environment,
        controller,
    ) = _open(marker, occurrence_ordinal=ordinal)
    profile = ipc.freeze_v075_production_occurrence_ipc_profile_v1(
        occurrence_identity=identity,
        open_lifecycle_binding=controller.open_binding,
        context=context,
        process_timeout_seconds=600,
        behavior=behavior,
    )
    return (
        namespace,
        context,
        arm,
        identity,
        authority,
        replay_environment,
        controller,
        profile,
    )


@pytest.fixture(scope="module")
def completed_occurrence():
    values = _profile("production-ipc-positive", 9_101)
    controller = values[-2]
    profile = values[-1]
    result = ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
        profile=profile,
        controller=controller,
    )
    return (*values, result)


def test_registered_child_and_profile_freeze_public_only_contract() -> None:
    registration = (
        ipc.registered_v075_production_occurrence_child_program_v1()
    )
    document = registration.to_document()
    assert document["one_fresh_process_per_occurrence"] is True
    assert document["canonical_json_frames_only"] is True
    assert document["pickle_transport_allowed"] is False
    assert document["arbitrary_callback_allowed"] is False
    assert document["private_observer_in_child"] is False
    assert document["production_transport_ready"] is True
    assert ipc.PRODUCTION_TRANSPORT_READY is True
    assert ipc.TARGET_EXECUTION_OPENED is False
    assert ipc.PRIVATE_MATERIAL_TRANSPORT_ALLOWED is False
    assert ipc.PICKLE_TRANSPORT_ALLOWED is False
    assert ipc.HOST_OPERATIONAL_FULL_PLANNER_REPLAY_ALLOWED is False


def test_operational_parent_source_has_no_backend_or_planner_replay() -> None:
    source = inspect.getsource(
        ipc.execute_v075_production_adaptive_occurrence_ipc_v1
    )
    tree = ast.parse(source)
    attribute_names = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    assert "compile_v075_batch_native_statistical_backend_v1" not in (
        attribute_names
    )
    assert "plan_v075_batch_native_route_v1" not in attribute_names
    assert "verify_v075_occurrence_ipc_result_standalone_v1" not in (
        attribute_names
    )


def test_one_fresh_child_runs_real_adaptive_backend_and_planner(
    completed_occurrence,
) -> None:
    controller = completed_occurrence[-3]
    profile = completed_occurrence[-2]
    result = completed_occurrence[-1]
    assert result.status == "PASS"
    assert result.terminal_code == "CHILD_SCIENTIFIC_RESULT_READY"
    assert result.profile_id == profile.profile_id
    assert result.observed_batches == controller.batches
    assert result.child_result is not None
    child = result.child_result
    assert child["public_backend_computed_in_child"] is True
    assert child["public_planner_computed_in_child"] is True
    assert child["host_operational_full_planner_replay_required"] is False
    assert child["terminal_code"] == "ADAPTIVE_ROUND_LIMIT_REACHED"
    assert len(child["rounds"]) == 2
    assert child["batch_ids"] == sorted(
        item.batch_id for item in result.observed_batches
    )
    assert child["observation_order_batch_ids"] == [
        item.batch_id for item in result.observed_batches
    ]
    assert result.actual_work.process_launches == 1
    assert result.actual_work.host_operational_planner_replays == 0
    assert result.actual_work.batch_intents == len(result.observed_batches)
    assert result.actual_work.support_freeze_intents > 0
    assert result.actual_work.round_begin_intents == 2
    assert result.actual_work.accepted_draws <= (
        2 * 64
        + 2 * 2_048
        + 160_960
    )
    assert result.stderr_byte_count == 0
    assert result.to_document()["scientific_plan_certificate"] is False
    assert result.to_document()["target_execution_opened"] is False


def test_evaluation_only_replay_matches_without_charging_operational_work(
    completed_occurrence,
) -> None:
    profile = completed_occurrence[-2]
    result = completed_occurrence[-1]
    verification = (
        ipc.verify_v075_occurrence_ipc_result_standalone_v1(
            profile=profile,
            claimed=result,
        )
    )
    assert verification.result_id == result.result_id
    assert verification.child_result_id == result.child_result_id
    assert verification.replayed_batch_count == len(result.observed_batches)
    assert verification.evaluation_planner_replays == 1
    assert verification.operational_work_charged is False
    assert result.actual_work.host_operational_planner_replays == 0


@pytest.mark.parametrize(
    ("behavior", "ordinal"),
    (
        (ipc.V075ProductionIPCBehaviorV1.ATTACK_SEQUENCE_GAP, 9_201),
        (ipc.V075ProductionIPCBehaviorV1.ATTACK_UNKNOWN_FIELD, 9_202),
        (ipc.V075ProductionIPCBehaviorV1.ATTACK_TRANSPLANT_STREAM, 9_203),
    ),
)
def test_reorder_unknown_field_and_stream_transplant_fail_closed(
    behavior,
    ordinal,
) -> None:
    values = _profile(
        f"production-ipc-{behavior.value.lower()}",
        ordinal,
        behavior=behavior,
    )
    controller = values[-2]
    profile = values[-1]
    result = ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
        profile=profile,
        controller=controller,
    )
    assert result.status == "FAILED"
    assert result.terminal_code == "PROTOCOL_FAILURE"
    assert result.child_result is None
    assert result.actual_work.host_operational_planner_replays == 0
    assert result.to_document()["scientific_plan_certificate"] is False


def test_missing_extra_or_content_id_tamper_is_rejected_before_use(
    completed_occurrence,
) -> None:
    profile = completed_occurrence[-2]
    result = completed_occurrence[-1]
    assert result.child_result is not None
    honest = result.child_result

    missing = dict(honest)
    missing.pop("final_planner_result")
    with pytest.raises(ipc.V075ProductionOccurrenceIPCInvariantViolation):
        ipc._validate_child_result_operationally(
            raw=ipc._canonical_bytes(missing),
            profile=profile,
            observed_batches=result.observed_batches,
            active_round=2,
        )

    extra = dict(honest)
    extra["unknown"] = 1
    with pytest.raises(ipc.V075ProductionOccurrenceIPCInvariantViolation):
        ipc._validate_child_result_operationally(
            raw=ipc._canonical_bytes(extra),
            profile=profile,
            observed_batches=result.observed_batches,
            active_round=2,
        )

    tampered = dict(honest)
    tampered["terminal_code"] = "NO_UNCERTAIN_PROOF_FRONTIER"
    with pytest.raises(ipc.V075ProductionOccurrenceIPCInvariantViolation):
        ipc._validate_child_result_operationally(
            raw=ipc._canonical_bytes(tampered),
            profile=profile,
            observed_batches=result.observed_batches,
            active_round=2,
        )


def test_profile_rejects_occurrence_or_program_transplant() -> None:
    first = _profile("production-ipc-profile-first", 9_301)
    second = _profile("production-ipc-profile-second", 9_302)
    with pytest.raises(ipc.V075ProductionOccurrenceIPCInvariantViolation):
        ipc.freeze_v075_production_occurrence_ipc_profile_v1(
            occurrence_identity=first[3],
            open_lifecycle_binding=second[-2].open_binding,
            context=first[1],
        )
    registration = (
        ipc.registered_v075_production_occurrence_child_program_v1()
    )
    with pytest.raises(ipc.V075ProductionOccurrenceIPCInvariantViolation):
        replace(registration, module_sha256="0" * 64)
