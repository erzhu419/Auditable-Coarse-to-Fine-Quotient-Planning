from __future__ import annotations

import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, content_id
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as overlay
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned_runner
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


REPOSITORY_ROOT = (
    "/home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning"
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-execution-identity-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _schedule(namespace, context_index: int):
    context = namespace.family.replicate_contexts[context_index]
    arm = worker.V075WorkerArmV1.NO_PRIOR
    occurrence = (
        backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=(
                context_index * len(acquisition.ARM_ORDER)
                + acquisition.ARM_ORDER.index(arm)
            ),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    claimed = acquisition.freeze_v075_occurrence_initial_acquisition_schedule_v2(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        occurrence=occurrence,
    )
    slot = claimed.profile.occurrence_slot_for(
        context_id=context.context_id,
        arm=arm,
    )
    replayed, verification = (
        acquisition.verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            expected_slot=slot,
            occurrence_identity_bytes=canonical_json_bytes(
                occurrence.to_document()
            ),
            raw=claimed.canonical_bytes,
        )
    )
    return replayed, verification


@pytest.fixture(scope="module")
def identity_fixture():
    generated, salt, namespace, authority, signer = observer_fixture._fixture(  # noqa: SLF001
        "k7-execution-identity"
    )
    schedules = tuple(_schedule(namespace, index) for index in range(3))
    return generated, salt, namespace, authority, signer, schedules


def test_profile_separates_historical_boundary_and_v075_execution_identity() -> None:
    profile = overlay.official_v075_k7_root_cap_execution_identity_profile_v1()
    manifest = boundary.official_k7_root_cap_operation_boundary_manifest_v3()
    document = profile.to_document()
    payload = dict(document)
    payload.pop("execution_profile_id")
    assert profile.profile_id == content_id(
        overlay.EXECUTION_PROFILE_DOMAIN,
        payload,
    )
    assert profile.boundary_manifest_id == manifest.manifest_id
    assert profile.boundary_manifest_context_key == (
        "heldout_graph_k7_confirmatory_v1"
    )
    assert profile.execution_context_key == (
        "heldout_graph_k7_production_replication_v075_1"
    )
    assert profile.execution_context_id == (
        "e8f5b54c9b31814d3a971f7223d3eeadc5dd8063b96faa0c1780f306869c255a"
    )
    assert profile.execution_topology_id == (
        "c4ad4934340b4fe0854a7f85d778a6ebec9a52337da6577426d5585a155a7b21"
    )
    assert document["boundary_semantics_reused"] is True
    assert document["boundary_execution_identity_reused"] is False
    assert document["construction_fixture_only"] is True
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["target_observation_reuse_allowed"] is False


def test_exact_v075_k7_no_prior_schedule_matches_profile(identity_fixture) -> None:
    _generated, _salt, namespace, _authority, _signer, schedules = (
        identity_fixture
    )
    profile = overlay.official_v075_k7_root_cap_execution_identity_profile_v1()
    assert (
        overlay.validate_v075_k7_root_cap_execution_identity_v1(
            profile=profile,
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            schedule=schedules[0][0],
            schedule_verification=schedules[0][1],
        )
        is profile
    )


@pytest.mark.parametrize("context_index", (1, 2))
def test_w7_and_k7_minus_two_fail_before_cache_or_accounting_activation(
    identity_fixture,
    monkeypatch,
    context_index,
) -> None:
    generated, salt, namespace, authority, signer, schedules = identity_fixture

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cache/accounting side effect ran before rejection")

    monkeypatch.setattr(
        owned_runner.bernoulli,
        "clear_exact_bernoulli_math_cache_v1",
        forbidden,
    )
    monkeypatch.setattr(
        owned_runner.accounting_runtime,
        "activate_owned_construction_accounting_v1",
        forbidden,
    )
    schedule, verification = schedules[context_index]
    with pytest.raises(
        owned_runner.V075K7RootCapOwnedPartialRunnerV1Error,
        match="execution identity rejected",
    ) as caught:
        owned_runner.run_v075_k7_root_cap_owned_partial_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=verification,
            authority=authority,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id(f"wrong-context-{context_index}"),
        )
    assert caught.value.aborted_transcript is None


def test_foreign_namespace_schedule_fails_before_side_effect(
    identity_fixture,
    monkeypatch,
) -> None:
    generated, salt, namespace, authority, signer, _schedules = identity_fixture
    (
        _foreign_generated,
        _foreign_salt,
        foreign_namespace,
        _foreign_authority,
        _foreign_signer,
    ) = observer_fixture._fixture("foreign-k7-execution-identity")  # noqa: SLF001
    foreign_schedule, foreign_verification = _schedule(foreign_namespace, 0)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cache/accounting side effect ran before rejection")

    monkeypatch.setattr(
        owned_runner.bernoulli,
        "clear_exact_bernoulli_math_cache_v1",
        forbidden,
    )
    monkeypatch.setattr(
        owned_runner.accounting_runtime,
        "activate_owned_construction_accounting_v1",
        forbidden,
    )
    with pytest.raises(
        owned_runner.V075K7RootCapOwnedPartialRunnerV1Error,
        match="execution identity rejected",
    ) as caught:
        owned_runner.run_v075_k7_root_cap_owned_partial_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            schedule=foreign_schedule,
            schedule_verification=foreign_verification,
            authority=authority,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("foreign-schedule"),
        )
    assert caught.value.aborted_transcript is None
