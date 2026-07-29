from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import ast
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_operational_planner_transport_v1 as transport
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_production_occurrence_authority_v1 as occurrence
from acfqp import v075_production_occurrence_ipc_v1 as ipc
from acfqp import v075_production_occurrence_plan_v1 as production_plan
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_batch_native_statistical_backend_v1 as fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-production-occurrence-authority-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _open(
    marker: str,
    *,
    scientific_ordinal: int,
    private_laws=None,
    private_salt: bytes | None = None,
):
    private_laws = (
        fixture._synthetic_environment()
        if private_laws is None
        else private_laws
    )
    private_salt = (
        fixture._salt("occurrence-authority-" + marker)
        if private_salt is None
        else private_salt
    )
    if private_laws == fixture._synthetic_environment():
        namespace = fixture._namespace("occurrence-authority-" + marker)
    else:
        family = public.freeze_v075_public_family_generation_v1()
        commitment = public.seal_opaque_environment_commitment_v1(
            family=family,
            secret_salt=private_salt,
            secret_laws=private_laws,
        )
        registry = public.V075TrustedSignerRegistryV1(
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
            external_id = _id(marker + "-" + role.value)
            claims.append(
                public.V075SignedExternalAuthorityClaimV1(
                    registry,
                    role,
                    external_id,
                    fixture._sign(
                        fixture._CAMPAIGN_TEST_KEY,
                        public.external_authority_claim_signing_bytes_v1(
                            signer_registry=registry,
                            role=role,
                            external_id=external_id,
                        ),
                    ),
                )
            )
        namespace = public.derive_public_target_tape_namespace_v1(
            family=family,
            environment_commitment=commitment,
            signer_registry=registry,
            claimed_final_preregistration_registry_id=registry.registry_id,
            remote_main_anchor=claims[0],
            final_preregistration=claims[1],
            observer_profile=claims[2],
        )
    plan = production_plan.freeze_v075_production_occurrence_plan_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
    )
    entry = plan.entries[scientific_ordinal]
    context = namespace.family.replicate_contexts[entry.context_ordinal]
    authority = fixture._fixture(
        namespace,
        "occurrence-authority-" + marker,
    )
    session = observer.open_construction_private_observer_fixture_v1(
        authority=authority,
        private_salt=private_salt,
        private_environment=private_laws,
        observer_signer=fixture._ConstructionSigner(),
        session_external_id=_id("session-" + marker),
    )
    controller = lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
        batched_session=(
            batched.wrap_v075_construction_batched_observer_session_v1(
                session
            )
        ),
        occurrence_id=entry.occurrence_id,
        context_id=entry.context_id,
        arm=entry.arm,
        route_cap_profile=plan.cap_profile,
    )
    replay_environment = (
        batched.issue_v075_construction_batch_replay_environment_fixture_v1(
            namespace=namespace,
            private_salt=private_salt,
            private_environment=private_laws,
        )
    )
    profile = ipc.freeze_v075_production_occurrence_ipc_profile_v1(
        occurrence_identity=entry.occurrence_identity,
        open_lifecycle_binding=controller.open_binding,
        context=context,
        source_prior_transport=(
            plan.source_prior_transport
            if entry.arm
            is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            else None
        ),
        process_timeout_seconds=600,
    )
    return (
        namespace,
        plan,
        entry,
        authority,
        replay_environment,
        controller,
        profile,
    )


@pytest.fixture(scope="module")
def adaptive_noncertificate():
    values = _open(
        "adaptive-noncertificate",
        scientific_ordinal=1,
    )
    result = occurrence.execute_v075_construction_occurrence_fixture_v1(
        repository_root=REPOSITORY_ROOT,
        plan=values[1],
        entry=values[2],
        authority=values[3],
        private_environment=values[4],
        controller=values[5],
        ipc_profile=values[6],
    )
    return (*values, result)


def test_authority_does_not_open_target_or_replay_host_search() -> None:
    assert occurrence.TARGET_EXECUTION_OPENED is False
    assert occurrence.HOST_MODEL_COMPILATION_ALLOWED is False
    assert occurrence.HOST_PLANNER_EXECUTION_ALLOWED is False
    assert occurrence.HOST_SOLVER_OR_SEARCH_ALLOWED is False
    source = inspect.getsource(occurrence)
    tree = ast.parse(source)
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert "open_production_private_observer_v1" not in calls
    assert "compile_v075_batch_native_statistical_backend_v1" not in calls
    assert "plan_v075_batch_native_route_v1" not in calls


@pytest.mark.parametrize(
    ("status", "terminal_class", "terminal_code"),
    (
        (
            total_lift.V075BatchTotalLiftProductionStatusV1
            .EXACT_POSITIVE_PRODUCTION_CANDIDATE,
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .PLAN_CERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE,
        ),
        (
            total_lift.V075BatchTotalLiftProductionStatusV1
            .EXACT_GROUND_QUERY_INFEASIBLE,
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .INFEASIBILITY_CERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_INFEASIBILITY_CERTIFICATE,
        ),
        (
            total_lift.V075BatchTotalLiftProductionStatusV1
            .EXACT_POLICY_RISK_FAILURE,
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_POLICY_RISK_FAILURE,
        ),
        (
            total_lift.V075BatchTotalLiftProductionStatusV1
            .EXACT_POLICY_REGRET_FAILURE,
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_POLICY_REGRET_FAILURE,
        ),
        (
            total_lift.V075BatchTotalLiftProductionStatusV1
            .STATISTICAL_ENVELOPE_MISS,
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .STATISTICAL_ENVELOPE_MISS,
        ),
    ),
)
def test_exact_terminal_classification_never_promotes_a_failed_lift(
    status,
    terminal_class,
    terminal_code,
) -> None:
    assert occurrence._candidate_terminal(status) == (
        terminal_class,
        terminal_code,
    )


def test_real_adaptive_noncertificate_closes_and_retains_exact_work(
    adaptive_noncertificate,
) -> None:
    namespace = adaptive_noncertificate[0]
    entry = adaptive_noncertificate[2]
    controller = adaptive_noncertificate[5]
    result = adaptive_noncertificate[-1]
    assert result.occurrence_id == entry.occurrence_id
    assert result.authority_scope is (
        lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
    )
    assert result.terminal_class is (
        occurrence.V075ProductionOccurrenceTerminalClassV1
        .ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    assert result.terminal_code is (
        occurrence.V075ProductionOccurrenceTerminalCodeV1
        .ADAPTIVE_ROUND_LIMIT_REACHED
    )
    assert result.operational_load is not None
    assert result.sealed_lifecycle is not None
    assert result.sealed_failure_lifecycle is None
    assert result.lineage is None
    assert result.exact_replay is None
    assert result.total_lift_candidate is None
    assert result.total_lift_verification is None
    assert result.ipc_result.observed_batches == controller.batches
    assert result.accepted_draw_count == sum(
        item.request.accepted_draw_count
        for item in result.ipc_result.observed_batches
    )
    assert result.online_work_id == result.ipc_result.actual_work.work_id
    assert result.process_launch_count == 1
    assert (
        result.sealed_lifecycle.closure.accepted_draw_count
        == result.accepted_draw_count
    )
    assert result.sealed_lifecycle.closure.process_launches == 1
    document = result.to_document()
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["terminal_code"] == "ADAPTIVE_ROUND_LIMIT_REACHED"
    assert document["host_model_compiler_calls"] == 0
    assert document["host_planner_calls"] == 0
    assert document["host_solver_or_search_calls"] == 0
    assert document["private_law_serialized"] is False
    assert document["private_salt_serialized"] is False
    assert document["private_kernel_serialized"] is False
    assert fixture._salt(
        "occurrence-authority-adaptive-noncertificate"
    ).hex() not in result.canonical_bytes.decode("utf-8")
    assert (
        document["plan_entry"]["target_tape_namespace_id"]
        == namespace.target_tape_namespace_id
    )


def test_public_verifier_reloads_transport_without_compiler_or_search(
    adaptive_noncertificate,
    monkeypatch,
) -> None:
    namespace = adaptive_noncertificate[0]
    result = adaptive_noncertificate[-1]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("verifier attempted host compiler/planner replay")

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
    verification = (
        occurrence.verify_v075_production_occurrence_authority_result_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            claimed=result,
        )
    )
    work = result.ipc_result.actual_work
    assert verification.result_id == result.result_id
    assert verification.occurrence_id == result.occurrence_id
    assert verification.ipc_actual_work_id == work.work_id
    assert verification.accepted_draw_count == work.accepted_draws
    assert verification.outcome_aggregate_count == work.outcome_aggregates
    assert verification.process_launch_count == work.process_launches
    assert verification.child_message_count == work.child_messages
    assert verification.parent_message_count == work.parent_messages
    assert verification.child_bytes_read == work.child_bytes_read
    assert verification.parent_bytes_written == work.parent_bytes_written
    assert verification.protocol_check_count == work.protocol_checks
    assert verification.batch_intent_count == work.batch_intents
    assert (
        verification.support_freeze_intent_count
        == work.support_freeze_intents
    )
    assert verification.round_begin_intent_count == work.round_begin_intents
    assert verification.host_operational_planner_replay_count == 0
    assert verification.child_exit_code == work.child_exit_code
    assert (
        verification.stderr_byte_count
        == result.ipc_result.stderr_byte_count
    )
    assert verification.operational_transport_present is True
    assert verification.to_document()[
        "operational_transport_reloaded_without_search"
    ] is True
    assert verification.to_document()[
        "operational_transport_absence_validated"
    ] is False
    assert verification.exact_chain_present is False
    assert verification.to_document()[
        "total_lift_candidate_independently_recomputed"
    ] is False
    assert verification.to_document()["exact_chain_absence_validated"] is True


def test_plan_entry_ipc_and_transport_transplants_fail_closed(
    adaptive_noncertificate,
) -> None:
    result = adaptive_noncertificate[-1]
    foreign_namespace = fixture._namespace(
        "occurrence-authority-foreign-plan"
    )
    foreign_plan = production_plan.freeze_v075_production_occurrence_plan_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=foreign_namespace,
    )
    with pytest.raises(
        occurrence.V075ProductionOccurrenceAuthorityInvariantViolation
    ):
        replace(result, plan=foreign_plan)
    with pytest.raises(
        occurrence.V075ProductionOccurrenceAuthorityInvariantViolation
    ):
        replace(result, plan_entry=result.plan.entries[0])
    with pytest.raises(
        ipc.V075ProductionOccurrenceIPCInvariantViolation
    ):
        replace(
            result.ipc_result,
            occurrence_id="0" * 64,
        )
    assert result.operational_load is not None
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation
    ):
        replace(
            result.operational_load.transport,
            occurrence_id="0" * 64,
        )


def test_direct_root_cap_uses_typed_failure_lifecycle() -> None:
    direct_laws = tuple(
        tuple((rank, Fraction(1, 6)) for rank in range(1, 7))
        for _ in range(3)
    )
    values = _open(
        "direct-cap",
        scientific_ordinal=9,
        private_laws=direct_laws,
        private_salt=hashlib.sha512(
            b"acfqp-v075-occurrence-authority-direct-cap"
        ).digest(),
    )
    result = occurrence.execute_v075_construction_occurrence_fixture_v1(
        repository_root=REPOSITORY_ROOT,
        plan=values[1],
        entry=values[2],
        authority=values[3],
        private_environment=values[4],
        controller=values[5],
        ipc_profile=values[6],
    )
    assert result.plan_entry.arm is (
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    )
    assert result.terminal_class is (
        occurrence.V075ProductionOccurrenceTerminalClassV1
        .ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    assert result.terminal_code is (
        occurrence.V075ProductionOccurrenceTerminalCodeV1
        .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
    )
    assert result.sealed_lifecycle is None
    assert result.sealed_failure_lifecycle is not None
    assert result.operational_load is None
    assert result.ipc_result.actual_work.accepted_draws == 2 * 64
    assert (
        result.sealed_failure_lifecycle.closure.execution_evidence
        .actual_work.accepted_draws
        == result.ipc_result.actual_work.accepted_draws
    )
    verification = (
        occurrence.verify_v075_production_occurrence_authority_result_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=values[0],
            claimed=result,
        )
    )
    assert verification.result_id == result.result_id
    assert verification.terminal_code is result.terminal_code
    assert verification.operational_transport_present is False
    assert verification.to_document()[
        "operational_transport_reloaded_without_search"
    ] is False
    assert verification.to_document()[
        "operational_transport_absence_validated"
    ] is True


def test_production_executor_is_typed_but_never_opened_in_tests() -> None:
    signature = inspect.signature(
        occurrence.execute_v075_production_occurrence_v1
    )
    assert tuple(signature.parameters) == (
        "repository_root",
        "plan",
        "entry",
        "controller",
        "ipc_profile",
        "authority",
        "private_salt",
        "private_environment",
    )
    assert occurrence.TARGET_EXECUTION_OPENED is False
