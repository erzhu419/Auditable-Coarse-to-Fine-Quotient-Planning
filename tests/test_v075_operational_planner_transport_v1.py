from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_integrated_direct_occurrence_pipeline_v1 as direct
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_operational_planner_transport_v1 as transport
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import (
    test_v075_integrated_direct_occurrence_pipeline_v1 as direct_fixture,
)
from tests import test_v075_batch_native_total_lift_e2e_v1 as e2e_fixture


@pytest.fixture(scope="module")
def transported_child_result():
    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        backend,
        "_cached_checkpoint",
        direct_fixture._point_checkpoint,
    )
    patcher.setattr(
        backend,
        "plan_v075_batch_native_route_v1",
        direct_fixture._typed_mechanics_ready_planner,
    )
    try:
        _namespace, _context, identity, controller = direct_fixture._open(
            "operational-transport",
            75_701,
        )
        child = (
            direct.execute_v075_integrated_direct_occurrence_preclose_v1(
                occurrence_identity=identity,
                observer_lifecycle=controller,
            )
        )
        artifact = transport.freeze_v075_operational_planner_transport_v1(
            occurrence_identity=identity,
            backend_result=child.final_backend_result,
            planner_result=child.final_planner_result,
        )
    finally:
        patcher.undo()
    return identity, child, artifact


@pytest.fixture(scope="module")
def transported_adaptive_child_result():
    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        backend,
        "_cached_checkpoint",
        direct_fixture._point_checkpoint,
    )
    try:
        namespace = e2e_fixture._namespace()
        context = namespace.family.replicate_contexts[1]
        arm = worker.V075WorkerArmV1.NO_PRIOR
        caps = worker.V075WorkerCapProfileV1()
        authority = (
            observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1(
                namespace,
                e2e_fixture._id("transport-adaptive-authority"),
            )
        )
        session = observer.open_construction_private_observer_fixture_v1(
            authority=authority,
            private_salt=e2e_fixture._salt(),
            private_environment=e2e_fixture._construction_environment(),
            observer_signer=e2e_fixture._ConstructionSigner(),
            session_external_id=e2e_fixture._id(
                "transport-adaptive-session"
            ),
        )
        wrapped = (
            batched.wrap_v075_construction_batched_observer_session_v1(
                session
            )
        )
        identity = backend.freeze_v075_batch_native_occurrence_identity_v1(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=75_702,
            threshold_profile=worker.V075WorkerThresholdProfileV1(),
            cap_profile=caps,
            source_prior_transport=None,
        )
        controller = (
            lifecycle.open_v075_parent_owned_multistage_lifecycle_v1(
                batched_session=wrapped,
                occurrence_id=identity.occurrence_id,
                context_id=context.context_id,
                arm=arm,
                route_cap_profile=caps,
            )
        )
        root_discoveries = e2e_fixture._discover_all_rows(
            controller=controller,
            namespace=namespace,
            catalogues=(graph.root_catalogue_v1(context),),
        )
        root_supports = e2e_fixture._freeze_all_row_supports(
            controller=controller,
            namespace=namespace,
            discoveries=root_discoveries,
        )
        e2e_fixture._validate_all_rows(
            controller=controller,
            validations=root_supports,
            caps=caps,
        )
        child_catalogues = e2e_fixture._child_catalogues(
            context=context,
            root_supports=root_supports,
        )
        controller.start_adaptive_round_v1(1)
        child_discoveries = e2e_fixture._discover_all_rows(
            controller=controller,
            namespace=namespace,
            catalogues=child_catalogues,
        )
        child_supports = e2e_fixture._freeze_all_row_supports(
            controller=controller,
            namespace=namespace,
            discoveries=child_discoveries,
        )
        e2e_fixture._validate_all_rows(
            controller=controller,
            validations=child_supports,
            caps=caps,
        )
        request = backend.freeze_v075_batch_native_backend_request_v1(
            arm=arm,
            occurrence_ordinal=identity.occurrence_ordinal,
            batches=controller.batches,
            occurrence_identity=identity,
        )
        backend_result = (
            backend.compile_v075_batch_native_statistical_backend_v1(
                request
            )
        )
        planner_result = backend.plan_v075_batch_native_route_v1(
            backend_result
        )
        artifact = transport.freeze_v075_operational_planner_transport_v1(
            occurrence_identity=identity,
            backend_result=backend_result,
            planner_result=planner_result,
        )
    finally:
        patcher.undo()
    return identity, backend_result, planner_result, artifact


def _raise_if_called(*_args, **_kwargs):
    raise AssertionError("compiler/planner/search was invoked by loader")


def _repack(
    artifact: transport.V075OperationalPlannerTransportV1,
    *,
    child_role: str | None = None,
    mutate=None,
) -> bytes:
    envelope = loads_canonical_json(artifact.canonical_bytes)
    assert type(envelope) is dict
    if child_role is None:
        assert mutate is not None
        mutate(envelope)
    else:
        raw = bytes.fromhex(envelope[f"{child_role}_bytes_hex"])
        child = loads_canonical_json(raw)
        assert type(child) is dict
        assert mutate is not None
        mutate(child)
        raw = canonical_json_bytes(child)
        envelope[f"{child_role}_bytes_hex"] = raw.hex()
        envelope[f"{child_role}_bytes_sha256"] = hashlib.sha256(
            raw
        ).hexdigest()
    payload = dict(envelope)
    payload.pop("transport_id", None)
    envelope["transport_id"] = transport._hash("transport", payload)
    return canonical_json_bytes(envelope)


def _load(
    identity,
    child,
    raw: bytes,
):
    return transport.load_v075_operational_planner_transport_v1(
        occurrence_identity=identity,
        batches=child.final_backend_result.request.batches,
        source_prior_transport=None,
        claimed_bytes=raw,
    )


def test_loader_recovers_exact_existing_types_with_all_search_disabled(
    transported_child_result,
    monkeypatch,
) -> None:
    identity, child, artifact = transported_child_result
    for module, name in (
        (
            backend,
            "compile_v075_batch_native_statistical_backend_v1",
        ),
        (backend, "compile_v075_batch_native_support_graph_v1"),
        (backend, "plan_v075_batch_native_route_v1"),
        (planners, "compile_v075_learned_support_graph_v1"),
        (planners, "plan_v075_exact_h2_matched_direct_ground_v1"),
        (planners, "plan_v075_exact_h2_abstract_v1"),
        (planners, "_solve"),
    ):
        monkeypatch.setattr(module, name, _raise_if_called)
    loaded = _load(identity, child, artifact.canonical_bytes)
    assert type(loaded.backend_result) is (
        backend.V075BatchNativeBackendResultV1
    )
    assert type(loaded.planner_result) is planners.V075SupportPlannerResultV1
    assert loaded.backend_result == child.final_backend_result
    assert loaded.planner_result == child.final_planner_result
    assert loaded.planner_result.graph.backend_result == (
        loaded.backend_result.route_native_result
    )
    document = loaded.to_document()
    assert document["total_lift_lineage_input_compatible"] is True
    assert document["model_compiler_calls"] == 0
    assert document["planner_calls"] == 0
    assert document["solver_or_search_calls"] == 0


def test_adaptive_roundtrip_also_runs_with_all_search_disabled(
    transported_adaptive_child_result,
    monkeypatch,
) -> None:
    identity, backend_result, planner_result, artifact = (
        transported_adaptive_child_result
    )
    for module, name in (
        (
            backend,
            "compile_v075_batch_native_statistical_backend_v1",
        ),
        (backend, "compile_v075_batch_native_support_graph_v1"),
        (backend, "plan_v075_batch_native_route_v1"),
        (planners, "compile_v075_learned_support_graph_v1"),
        (planners, "plan_v075_exact_h2_matched_direct_ground_v1"),
        (planners, "plan_v075_exact_h2_abstract_v1"),
        (planners, "_solve"),
    ):
        monkeypatch.setattr(module, name, _raise_if_called)
    loaded = transport.load_v075_operational_planner_transport_v1(
        occurrence_identity=identity,
        batches=backend_result.request.batches,
        source_prior_transport=None,
        claimed_bytes=artifact.canonical_bytes,
    )
    assert loaded.backend_result == backend_result
    assert loaded.planner_result == planner_result
    assert loaded.planner_result.route is (
        planners.V075PlannerRouteV1.ADAPTIVE_QUOTIENT
    )
    assert loaded.planner_result.quotient is not None
    assert loaded.planner_result.graph.backend_result == (
        loaded.backend_result.route_native_result
    )


def test_exact_fractions_and_public_only_transport_are_preserved(
    transported_child_result,
) -> None:
    identity, child, artifact = transported_child_result
    loaded = _load(identity, child, artifact.canonical_bytes)
    original_interval = (
        child.final_backend_result.route_native_result.model.rows[0]
        .intervals[0]
    )
    loaded_interval = (
        loaded.backend_result.route_native_result.model.rows[0]
        .intervals[0]
    )
    assert type(loaded_interval.lower_probability) is Fraction
    assert type(loaded_interval.upper_probability) is Fraction
    assert loaded_interval == original_interval
    assert loaded.planner_result.envelope is not None
    assert child.final_planner_result.envelope is not None
    assert type(
        loaded.planner_result.envelope.selected_failure_upper
    ) is Fraction
    assert loaded.planner_result.envelope == (
        child.final_planner_result.envelope
    )
    document = artifact.to_document()
    assert document["signed_batches_embedded"] is False
    assert document["private_material_serialized"] is False
    assert document["per_draw_capabilities_materialized"] == 0
    assert document["model_compiler_calls"] == 0
    assert document["planner_calls"] == 0
    assert document["solver_or_search_calls"] == 0


@pytest.mark.parametrize(
    "child_role,mutate",
    (
        (
            "backend",
            lambda item: item["route_native_result"]["model"]["rows"][
                0
            ].__setitem__("action", [99, 100, 99]),
        ),
        (
            "planner",
            lambda item: item["policy"]["decisions"][0][
                "state_choices"
            ][0]["row_ids"].__setitem__(0, "0" * 64),
        ),
        (
            "planner",
            lambda item: item["envelope"].__setitem__(
                "selected_failure_upper",
                Fraction(1),
            ),
        ),
        (
            "planner",
            lambda item: item["work"]["counters"][0].__setitem__(
                "value",
                item["work"]["counters"][0]["value"] + 1,
            ),
        ),
    ),
    ids=(
        "nested-row",
        "nested-policy",
        "nested-envelope",
        "nested-counter",
    ),
)
def test_nested_child_tampering_is_rejected(
    transported_child_result,
    child_role,
    mutate,
) -> None:
    identity, child, artifact = transported_child_result
    attacked = _repack(
        artifact,
        child_role=child_role,
        mutate=mutate,
    )
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation
    ):
        _load(identity, child, attacked)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda item: item["route_native_result"].__setitem__(
            "occurrence_id",
            "1" * 64,
        ),
        lambda item: item["route_native_result"].__setitem__(
            "arm",
            "NO_PRIOR",
        ),
    ),
    ids=("wrong-backend-occurrence", "wrong-backend-arm"),
)
def test_backend_identity_or_arm_tampering_is_rejected(
    transported_child_result,
    mutate,
) -> None:
    identity, child, artifact = transported_child_result
    attacked = _repack(
        artifact,
        child_role="backend",
        mutate=mutate,
    )
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation
    ):
        _load(identity, child, attacked)


def test_wrong_parent_occurrence_identity_is_rejected(
    transported_child_result,
) -> None:
    identity, child, artifact = transported_child_result
    foreign_identity = replace(
        identity,
        occurrence_ordinal=identity.occurrence_ordinal + 1,
    )
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation,
        match="parent-owned typed inputs",
    ):
        _load(foreign_identity, child, artifact.canonical_bytes)


@pytest.mark.parametrize("kind", ("missing", "unknown"))
def test_missing_and_unknown_transport_fields_are_rejected(
    transported_child_result,
    kind: str,
) -> None:
    identity, child, artifact = transported_child_result

    def mutate(item):
        if kind == "missing":
            item.pop("planner_bytes_sha256")
        else:
            item["unknown_child_claim"] = True

    attacked = _repack(artifact, mutate=mutate)
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation
    ):
        _load(identity, child, attacked)


def test_unknown_nested_field_is_rejected(
    transported_child_result,
) -> None:
    identity, child, artifact = transported_child_result
    attacked = _repack(
        artifact,
        child_role="planner",
        mutate=lambda item: item["envelope"].__setitem__(
            "unknown_bound",
            Fraction(0),
        ),
    )
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation,
        match="unknown",
    ):
        _load(identity, child, attacked)


@pytest.mark.parametrize(
    "attack",
    (
        lambda raw: raw + b"\n",
        lambda raw: b" " + raw,
    ),
    ids=("trailing-newline", "leading-space"),
)
def test_noncanonical_transport_bytes_are_rejected(
    transported_child_result,
    attack,
) -> None:
    identity, child, artifact = transported_child_result
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation
    ):
        _load(identity, child, attack(artifact.canonical_bytes))


def test_transport_freeze_rejects_crossed_backend_and_planner(
    transported_child_result,
) -> None:
    identity, child, _artifact = transported_child_result
    foreign_identity = replace(
        identity,
        occurrence_ordinal=identity.occurrence_ordinal + 9,
    )
    with pytest.raises(
        transport.V075OperationalPlannerTransportInvariantViolation,
        match="exact child identity graph",
    ):
        transport.freeze_v075_operational_planner_transport_v1(
            occurrence_identity=foreign_identity,
            backend_result=child.final_backend_result,
            planner_result=child.final_planner_result,
        )
