from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import ast
import hashlib
import inspect
import os

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_integrated_direct_occurrence_pipeline_v1 as direct
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_production_occurrence_ipc_v1 as ipc
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batch_native_statistical_backend_v1 as fixture
from tests import (
    test_v075_integrated_direct_occurrence_pipeline_v1 as direct_fixture,
)
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


def _direct_cap_profile(
    marker: str,
    ordinal: int,
    *,
    behavior: ipc.V075ProductionIPCBehaviorV1 = (
        ipc.V075ProductionIPCBehaviorV1.HONEST
    ),
):
    laws = tuple(
        tuple((rank, Fraction(1, 6)) for rank in range(1, 7))
        for _ in range(3)
    )
    salt = hashlib.sha512(
        ("acfqp-v075-production-ipc-direct-cap-" + marker).encode()
    ).digest()
    family = public.freeze_v075_public_family_generation_v1()
    commitment = public.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=salt,
        secret_laws=laws,
    )
    signer_registry = public.V075TrustedSignerRegistryV1(
        fixture._public_key(
            "CAMPAIGN_AUTHORITY",
            fixture._CAMPAIGN_TEST_KEY,
        ),
        fixture._public_key(
            "OBSERVER_EVIDENCE",
            fixture._OBSERVER_TEST_KEY,
        ),
    )
    claims = []
    for role in public.V075ExternalAuthorityRoleV1:
        external_id = fixture._id(
            "production-ipc-direct-cap-" + marker + "-" + role.value
        )
        claims.append(
            public.V075SignedExternalAuthorityClaimV1(
                signer_registry,
                role,
                external_id,
                fixture._sign(
                    fixture._CAMPAIGN_TEST_KEY,
                    public.external_authority_claim_signing_bytes_v1(
                        signer_registry=signer_registry,
                        role=role,
                        external_id=external_id,
                    ),
                ),
            )
        )
    namespace = public.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=signer_registry,
        claimed_final_preregistration_registry_id=(
            signer_registry.registry_id
        ),
        remote_main_anchor=claims[0],
        final_preregistration=claims[1],
        observer_profile=claims[2],
    )
    context = namespace.family.replicate_contexts[1]
    arm = worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    caps = worker.V075WorkerCapProfileV1()
    identity = backend.freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=ordinal,
        threshold_profile=worker.V075WorkerThresholdProfileV1(),
        cap_profile=caps,
        source_prior_transport=None,
    )
    authority = observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
        namespace,
        fixture._id("direct-cap-authority-" + marker),
    )
    session = observer.open_construction_private_observer_fixture_v1(
        authority=authority,
        private_salt=salt,
        private_environment=laws,
        observer_signer=fixture._ConstructionSigner(),
        session_external_id=fixture._id("direct-cap-session-" + marker),
    )
    controller = lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
        batched_session=(
            batched.wrap_v075_construction_batched_observer_session_v1(
                session
            )
        ),
        occurrence_id=identity.occurrence_id,
        context_id=context.context_id,
        arm=arm,
        route_cap_profile=caps,
    )
    profile = ipc.freeze_v075_production_occurrence_ipc_profile_v1(
        occurrence_identity=identity,
        open_lifecycle_binding=controller.open_binding,
        context=context,
        process_timeout_seconds=600,
        behavior=behavior,
    )
    return identity, controller, profile


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
    assert ipc.MATCHED_DIRECT_HANDLER_READY is True
    assert ipc.PRODUCTION_OCCURRENCE_WORKER_COMPLETE is False
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
    assert child["operational_planner_transport_id"] == (
        child["operational_planner_transport"]["transport_id"]
    )
    assert bytes.fromhex(
        child["operational_planner_transport_bytes_hex"]
    )
    assert child["ipc_module_opened_observer"] is False
    assert child["production_target_observation_accessed"] is False
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
    assert result.to_document()["ipc_module_opened_observer"] is False
    assert result.to_document()[
        "production_target_observation_accessed"
    ] is False


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
    assert verification.route == "ADAPTIVE_QUOTIENT"
    assert verification.replayed_batch_count == len(result.observed_batches)
    assert verification.replayed_checkpoint_count == 1
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


def test_operational_transport_byte_tamper_fails_before_parent_use(
    completed_occurrence,
) -> None:
    profile = completed_occurrence[-2]
    result = completed_occurrence[-1]
    assert result.child_result is not None
    payload = dict(result.child_result)
    payload.pop("child_result_id")
    encoded = payload["operational_planner_transport_bytes_hex"]
    payload["operational_planner_transport_bytes_hex"] = (
        ("0" if encoded[0] != "0" else "1") + encoded[1:]
    )
    attacked = ipc._message_id(
        role="child_result",
        payload=payload,
        id_field="child_result_id",
    )
    with pytest.raises(
        ipc.V075ProductionOccurrenceIPCInvariantViolation,
        match="operational planner transport",
    ):
        ipc._validate_child_result_operationally(
            raw=ipc._canonical_bytes(attacked),
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


def test_fresh_child_runs_real_direct_physical_cap_noncertificate() -> None:
    identity, controller, profile = _direct_cap_profile(
        "honest",
        9_401,
    )
    result = ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
        profile=profile,
        controller=controller,
    )
    assert result.route == "MATCHED_DIRECT_GROUND"
    assert result.status == "NONCERTIFICATE"
    assert result.terminal_code == "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    assert result.child_result is not None
    child = result.child_result
    assert child["occurrence_id"] == identity.occurrence_id
    assert child["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert child["terminal_code"] == "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    assert child["lifecycle_close_requires_failure_authority"] is True
    assert child["root_work_retained"] is True
    assert child["direct_physical_cap_failure"]["root_work_retained"] is True
    assert child["direct_checkpoint_history"] == []
    assert child["direct_work"] is None
    assert child["operational_planner_transport"] is None
    assert child["scientific_plan_certificate"] is False
    assert result.actual_work.process_launches == 1
    assert result.actual_work.batch_intents == 2
    assert result.actual_work.accepted_draws == 2 * 64
    assert result.actual_work.support_freeze_intents == 0
    assert controller.aggregate_support_evidence == ()
    assert result.to_document()["ipc_module_opened_observer"] is False
    assert result.to_document()[
        "production_target_observation_accessed"
    ] is False
    verification = ipc.verify_v075_occurrence_ipc_result_standalone_v1(
        profile=profile,
        claimed=result,
    )
    assert verification.route == "MATCHED_DIRECT_GROUND"
    assert verification.terminal_code == (
        "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    )
    assert verification.final_backend_result_id is None
    assert verification.final_planner_result_id is None
    assert verification.replayed_checkpoint_count == 0
    assert verification.evaluation_planner_replays == 0


def test_direct_child_protocol_attack_still_fails_closed() -> None:
    _identity, controller, profile = _direct_cap_profile(
        "sequence-gap",
        9_402,
        behavior=ipc.V075ProductionIPCBehaviorV1.ATTACK_SEQUENCE_GAP,
    )
    result = ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
        profile=profile,
        controller=controller,
    )
    assert result.status == "FAILED"
    assert result.terminal_code == "PROTOCOL_FAILURE"
    assert result.child_result is None
    assert result.actual_work.process_launches == 1
    assert result.actual_work.host_operational_planner_replays == 0


def test_direct_normal_child_mechanics_and_zero_search_parent_load(
    monkeypatch,
) -> None:
    _namespace, context, identity, controller = direct_fixture._open(
        "production-ipc-normal-mechanics",
        9_403,
    )
    profile = ipc.freeze_v075_production_occurrence_ipc_profile_v1(
        occurrence_identity=identity,
        open_lifecycle_binding=controller.open_binding,
        context=context,
        process_timeout_seconds=600,
    )

    class LoopbackProtocol:
        def __init__(self, _launch):
            self.batches = []
            self.aggregate_support_evidence = []

        def request_batch(
            self,
            *,
            stream,
            accepted_draw_start,
            accepted_draw_count,
            accepted_draw_cap,
            **_metadata,
        ):
            result = controller.execute_batch_v1(
                stream_identity=stream,
                accepted_draw_start=accepted_draw_start,
                accepted_draw_count=accepted_draw_count,
                accepted_draw_cap=accepted_draw_cap,
            )
            self.batches.append(result)
            return result

        def freeze_support(
            self,
            *,
            discovery_batch,
            root_epoch,
            **_metadata,
        ):
            evidence = controller.freeze_aggregate_support_evidence_v1(
                discovery_batch=discovery_batch,
                selected_outcome_ids=ipc._support_outcome_ids(
                    discovery_batch
                ),
            )
            self.aggregate_support_evidence.extend(evidence)
            row = discovery_batch.request.stream_identity.row_binding
            stream = ipc._validation_stream(
                controller.open_binding.namespace,
                row,
                root_epoch,
                evidence,
                identity.arm,
            )
            controller.register_validation_support_epoch_v1(
                stream_identity=stream
            )
            return stream

    monkeypatch.setattr(ipc, "_ChildProtocolV1", LoopbackProtocol)
    monkeypatch.setattr(
        backend,
        "_cached_checkpoint",
        direct_fixture._point_checkpoint,
    )
    monkeypatch.setattr(
        backend,
        "plan_v075_batch_native_route_v1",
        direct_fixture._typed_mechanics_ready_planner,
    )
    launch = ipc._load_launch(
        ipc._canonical_bytes(ipc._launch_document(profile))
    )
    child = ipc._child_matched_direct_run(launch)
    assert child["terminal_code"] == "READY_FOR_EXACT_TOTAL_LIFT"
    assert child["ready_for_exact_total_lift"] is True
    assert len(child["direct_checkpoint_history"]) == 1
    assert child["direct_checkpoint_history"][0]["checkpoint"] == 2_048
    assert child["direct_work"][
        "counters"
    ][-1]["path"] == "planning.ready_checkpoint_count"
    assert child["direct_work"]["counters"][-1]["value"] == 1
    assert child["operational_planner_transport_id"] == (
        child["operational_planner_transport"]["transport_id"]
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("operational parent attempted compiler/search")

    monkeypatch.setattr(
        backend,
        "compile_v075_batch_native_statistical_backend_v1",
        forbidden,
    )
    monkeypatch.setattr(
        backend,
        "plan_v075_batch_native_route_v1",
        forbidden,
    )
    validated = ipc._validate_child_result_operationally(
        raw=ipc._canonical_bytes(child),
        profile=profile,
        observed_batches=controller.batches,
        active_round=0,
    )
    assert validated["child_result_id"] == child["child_result_id"]
    assert validated["host_operational_full_planner_replay_required"] is False


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_V075_PRODUCTION_IPC_DIRECT_REAL") != "1",
    reason=(
        "canonical confidence + exact direct planner in a fresh -I child "
        "is an opt-in scientific smoke"
    ),
)
def test_opt_in_fresh_child_real_direct_ready_or_registered_cap() -> None:
    _namespace, context, identity, controller = direct_fixture._open(
        "production-ipc-real-direct",
        9_499,
    )
    profile = ipc.freeze_v075_production_occurrence_ipc_profile_v1(
        occurrence_identity=identity,
        open_lifecycle_binding=controller.open_binding,
        context=context,
        process_timeout_seconds=21_600,
    )
    result = ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
        profile=profile,
        controller=controller,
    )
    assert result.status == "PASS"
    assert result.route == "MATCHED_DIRECT_GROUND"
    assert result.child_result is not None
    assert result.child_result["terminal_code"] in {
        "READY_FOR_EXACT_TOTAL_LIFT",
        "DIRECT_CHECKPOINT_CAP_EXHAUSTED",
    }
    assert result.child_result["direct_checkpoint_history"]
    assert result.actual_work.process_launches == 1
    assert result.actual_work.host_operational_planner_replays == 0
