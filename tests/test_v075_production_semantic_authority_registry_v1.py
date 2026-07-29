from __future__ import annotations

import ast
import hashlib
import inspect
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_campaign_reconciliation_v1 as reconciliation
from acfqp import v075_complete_bundle_endpoint_verifier_v1 as endpoint
from acfqp import v075_private_environment_generation_profile_v1 as private
from acfqp import v075_production_semantic_authority_registry_v1 as semantic
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend
from acfqp import v075_total_lift_authority_v1 as lift
from tests import test_v075_registered_occurrence_worker_v1 as worker_test
from tests import test_v075_total_lift_authority_v1 as lift_test


def _rehash(
    document: dict[str, Any],
    *,
    domain: str,
    id_field: str,
) -> bytes:
    payload = dict(document)
    payload.pop(id_field)
    payload[id_field] = hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return canonical_json_bytes(payload)


def test_registry_freezes_unique_typed_role_domain_dependency_graph() -> None:
    registry = (
        semantic.freeze_v075_production_semantic_authority_registry_v1()
    )
    assert tuple(item.role for item in registry.role_specs) == tuple(
        semantic.V075SemanticAuthorityRoleV1
    )
    assert len(registry.role_specs) == 6
    assert len(
        {
            domain
            for item in registry.role_specs
            for domain in item.artifact_domains
        }
    ) == sum(len(item.artifact_domains) for item in registry.role_specs)
    assert len(
        {
            schema
            for item in registry.role_specs
            for schema in item.artifact_schemas
        }
    ) == sum(len(item.artifact_schemas) for item in registry.role_specs)
    seen = set()
    for item in registry.role_specs:
        assert set(item.prerequisite_roles) <= seen
        seen.add(item.role)
    document = registry.to_document()
    assert document["status_strings_are_evidence"] is False
    assert document["claimed_content_ids_are_evidence"] is False
    assert document["production_ready_claimed"] is False
    assert semantic.COMMITTED_ARTIFACT_PATH_REPLAY_IMPLEMENTED is False


def test_registry_module_has_no_top_level_component_or_legacy_import() -> None:
    tree = ast.parse(inspect.getsource(semantic))
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            if node.module == "acfqp":
                imports.extend(
                    f"acfqp.{item.name}" for item in node.names
                )
    forbidden = (
        "v075_registered_occurrence_worker",
        "v075_route_native_backend",
        "v075_private_environment_generation",
        "v075_total_lift",
        "v075_campaign_reconciliation",
        "v075_complete_bundle",
        "v072",
    )
    assert not any(
        fragment in imported
        for imported in imports
        for fragment in forbidden
    )


def test_private_generation_profile_is_exactly_replayed_not_id_trusted() -> None:
    profile = private.freeze_v075_private_environment_generation_profile_v1()
    verified = (
        semantic.verify_v075_private_generation_profile_artifact_v1(
            canonical_json_bytes(profile.to_document())
        )
    )
    assert verified.role is (
        semantic.V075SemanticAuthorityRoleV1
        .PRIVATE_ENVIRONMENT_GENERATION_PROFILE
    )
    assert verified.artifact_id == profile.profile_id
    assert verified.production_authorizing is False

    forged = dict(profile.to_document())
    forged["target_execution_allowed"] = True
    forged_bytes = _rehash(
        forged,
        domain=private.PROFILE_DOMAIN,
        id_field="profile_id",
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityInvariantViolation
    ):
        semantic.verify_v075_private_generation_profile_artifact_v1(
            forged_bytes
        )


def test_worker_registry_replays_nested_arm_ids_and_rejects_rehashed_status() -> None:
    registry = worker.freeze_v075_worker_registry_draft_v1()
    verified = semantic.verify_v075_worker_registry_artifact_v1(
        canonical_json_bytes(registry.to_document())
    )
    assert verified.artifact_id == registry.registry_id
    assert verified.blockers == (
        semantic.V075ProductionReadinessBlockerV1
        .WORKER_REGISTRY_DRAFT_ONLY,
    )

    forged = loads_canonical_json(
        canonical_json_bytes(registry.to_document())
    )
    forged["production_execution_status"] = "READY"
    forged_without_nested = {
        key: value
        for key, value in forged.items()
        if key != "registrations"
    }
    forged["registry_id"] = loads_canonical_json(
        _rehash(
            forged_without_nested,
            domain=worker.DOMAIN_TAGS["worker_registry"],
            id_field="registry_id",
        )
    )["registry_id"]
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityInvariantViolation
    ):
        semantic.verify_v075_worker_registry_artifact_v1(
            canonical_json_bytes(forged)
        )


def test_dependency_closure_is_clean_on_target_side_and_exposes_legacy_host() -> None:
    worker_closure = semantic.audit_v075_semantic_dependency_closure_v1(
        semantic.V075SemanticAuthorityRoleV1
        .REGISTERED_OCCURRENCE_WORKER_REGISTRY
    )
    backend_closure = semantic.audit_v075_semantic_dependency_closure_v1(
        semantic.V075SemanticAuthorityRoleV1
        .ROUTE_NATIVE_BACKEND_RESULT
    )
    total_lift_closure = semantic.audit_v075_semantic_dependency_closure_v1(
        semantic.V075SemanticAuthorityRoleV1.TOTAL_LIFT_RESULT
    )
    reconciliation_closure = (
        semantic.audit_v075_semantic_dependency_closure_v1(
            semantic.V075SemanticAuthorityRoleV1
            .CAMPAIGN_RECONCILIATION_READINESS
        )
    )
    endpoint_closure = semantic.audit_v075_semantic_dependency_closure_v1(
        semantic.V075SemanticAuthorityRoleV1
        .COMPLETE_BUNDLE_ENDPOINT_READINESS
    )
    assert worker_closure.production_dependency_clean is True
    assert backend_closure.production_dependency_clean is True
    assert total_lift_closure.production_dependency_clean is True
    assert reconciliation_closure.production_dependency_clean is True
    assert endpoint_closure.production_dependency_clean is True
    assert worker_closure.target_process_forbidden_modules == ()
    assert backend_closure.target_process_forbidden_modules == ()
    assert reconciliation_closure.legacy_v072_modules == ()
    assert endpoint_closure.legacy_v072_modules == ()
    assert "v075_public_source_work_authority_v1" in (
        reconciliation_closure.local_modules
    )
    assert "v075_source_offline_work_materializer_v1" not in (
        reconciliation_closure.local_modules
    )


@pytest.fixture(scope="module")
def route_fixture():
    refs = worker_test.capability_refs.__wrapped__()
    transport = worker_test.source_transport.__wrapped__()
    request = worker_test._request(
        worker.V075WorkerArmV1.NO_PRIOR,
        refs,
        transport,
    )
    result = backend.execute_v075_route_native_backend_core_v1(
        request.canonical_bytes
    )
    return request, result


def test_route_result_is_recomputed_and_exactly_context_bound(
    route_fixture,
) -> None:
    request, result = route_fixture
    verified = semantic.verify_v075_route_native_backend_artifact_v1(
        request_bytes=request.canonical_bytes,
        result_bytes=result.canonical_bytes,
        expected_target_tape_namespace_id=request.target_tape_namespace_id,
        expected_context_id=request.context_id,
        expected_occurrence_id=request.occurrence_id,
        expected_arm=request.arm.value,
    )
    assert verified.artifact_id == result.result_id
    assert verified.context_id == request.context_id
    assert verified.occurrence_id == request.occurrence_id
    assert verified.production_authorizing is False
    assert (
        semantic.V075ProductionReadinessBlockerV1
        .ROUTE_NATIVE_BACKEND_NONAUTHORIZING
        in verified.blockers
    )

    other_context = request.registry  # retain a typed unrelated object
    del other_context
    family = (
        private.freeze_v075_private_environment_generation_profile_v1()
        .family
    )
    transplanted_context = next(
        item.context_id
        for item in family.replicate_contexts
        if item.context_id != request.context_id
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityInvariantViolation
    ):
        semantic.verify_v075_route_native_backend_artifact_v1(
            request_bytes=request.canonical_bytes,
            result_bytes=result.canonical_bytes,
            expected_target_tape_namespace_id=(
                request.target_tape_namespace_id
            ),
            expected_context_id=transplanted_context,
            expected_occurrence_id=request.occurrence_id,
            expected_arm=request.arm.value,
        )


def test_route_result_rejects_rehashed_terminal_status(route_fixture) -> None:
    request, result = route_fixture
    forged = loads_canonical_json(result.canonical_bytes)
    forged["terminal_code"] = "PLAN_CERTIFICATE"
    summary = {
        key: value
        for key, value in forged.items()
        if key
        not in {
            "schedule",
            "proposal",
            "model",
            "policy",
            "envelope",
            "total_lift_input",
            "work",
        }
    }
    forged["result_id"] = loads_canonical_json(
        _rehash(
            summary,
            domain=backend.DOMAIN_TAGS["result"],
            id_field="result_id",
        )
    )["result_id"]
    with pytest.raises(
        (
            backend.V075RouteNativeBackendInvariantViolation,
            semantic.V075ProductionSemanticAuthorityInvariantViolation,
        )
    ):
        semantic.verify_v075_route_native_backend_artifact_v1(
            request_bytes=request.canonical_bytes,
            result_bytes=canonical_json_bytes(forged),
            expected_target_tape_namespace_id=(
                request.target_tape_namespace_id
            ),
            expected_context_id=request.context_id,
            expected_occurrence_id=request.occurrence_id,
            expected_arm=request.arm.value,
        )


@pytest.fixture(scope="module")
def total_lift_fixture():
    return lift_test.positive_fixture.__wrapped__()


def test_total_lift_result_is_exactly_replayed_and_construction_blocked(
    total_lift_fixture,
) -> None:
    outcome = lift.evaluate_total_lift_v1(
        envelope=total_lift_fixture.envelope,
        exact_replay=total_lift_fixture.boundary,
    )
    occurrence = total_lift_fixture.boundary.occurrence
    verified = semantic.verify_v075_total_lift_artifact_v1(
        envelope=total_lift_fixture.envelope,
        exact_replay=total_lift_fixture.boundary,
        claimed_outcome=outcome,
        expected_target_tape_namespace_id=(
            occurrence.namespace.target_tape_namespace_id
        ),
        expected_context_id=occurrence.context.context_id,
        expected_occurrence_id=occurrence.occurrence_id,
    )
    assert verified.artifact_id == outcome.endpoint_id
    assert verified.production_authorizing is False
    assert set(verified.blockers) == {
        semantic.V075ProductionReadinessBlockerV1
        .CONSTRUCTION_SCOPE_ONLY,
        semantic.V075ProductionReadinessBlockerV1
        .TOTAL_LIFT_EXECUTION_LOCKED,
    }

    forged_status = lift.V075TotalLiftEndpointV1(
        outcome.candidate,
        lift.V075TotalLiftEndpointStatusV1.EXACT_POLICY_RISK_FAILURE,
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityInvariantViolation
    ):
        semantic.verify_v075_total_lift_artifact_v1(
            envelope=total_lift_fixture.envelope,
            exact_replay=total_lift_fixture.boundary,
            claimed_outcome=forged_status,
            expected_target_tape_namespace_id=(
                occurrence.namespace.target_tape_namespace_id
            ),
            expected_context_id=occurrence.context.context_id,
            expected_occurrence_id=occurrence.occurrence_id,
        )


@pytest.mark.parametrize(
    ("role", "document", "verifier", "domain"),
    (
        (
            semantic.V075SemanticAuthorityRoleV1
            .CAMPAIGN_RECONCILIATION_READINESS,
            reconciliation.v075_production_reconciliation_readiness_v1(),
            semantic.verify_v075_reconciliation_readiness_artifact_v1,
            reconciliation.DOMAIN_TAGS["production_readiness"],
        ),
        (
            semantic.V075SemanticAuthorityRoleV1
            .COMPLETE_BUNDLE_ENDPOINT_READINESS,
            endpoint
            .v075_production_complete_bundle_endpoint_readiness_v1(),
            semantic.verify_v075_complete_bundle_readiness_artifact_v1,
            endpoint.DOMAIN_TAGS["production_readiness"],
        ),
    ),
)
def test_readiness_artifacts_require_executable_semantic_replay(
    role,
    document,
    verifier,
    domain,
) -> None:
    verified = verifier(canonical_json_bytes(document.to_document()))
    assert verified.role is role
    assert verified.production_authorizing is False
    assert (
        semantic.V075ProductionReadinessBlockerV1
        .LEGACY_V072_RUNTIME_IN_PRODUCTION_DEPENDENCY_CLOSURE
        not in verified.blockers
    )

    forged = loads_canonical_json(
        canonical_json_bytes(document.to_document())
    )
    forged["official_execution_allowed"] = True
    forged_bytes = _rehash(
        forged,
        domain=domain,
        id_field="status_id",
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityInvariantViolation
    ):
        verifier(forged_bytes)


def test_global_readiness_recomputes_all_p0_blockers_and_fails_closed() -> None:
    audit = semantic.audit_v075_production_semantic_readiness_v1()
    assert audit.production_ready is False
    assert audit.registered_target_ready is False
    assert audit.official_economics_ready is False
    expected = {
        semantic.V075ProductionReadinessBlockerV1
        .WORKER_REGISTRY_DRAFT_ONLY,
        semantic.V075ProductionReadinessBlockerV1
        .ROUTE_NATIVE_BACKEND_NONAUTHORIZING,
        semantic.V075ProductionReadinessBlockerV1
        .TOTAL_LIFT_EXECUTION_LOCKED,
        semantic.V075ProductionReadinessBlockerV1
        .BATCHED_OBSERVER_TOTAL_LIFT_LINEAGE_UNBOUND,
        semantic.V075ProductionReadinessBlockerV1
        .RECONCILIATION_PROTOCOL_NOT_READY,
        semantic.V075ProductionReadinessBlockerV1
        .COMPLETE_BUNDLE_ENDPOINT_NOT_READY,
        semantic.V075ProductionReadinessBlockerV1
        .OFFICIAL_EXECUTION_LOCKED,
        semantic.V075ProductionReadinessBlockerV1
        .WORKLOAD_ECONOMICS_GATE_NOT_RUN,
        semantic.V075ProductionReadinessBlockerV1
        .COUNTER_COMPLETENESS_GATE_NOT_RUN,
    }
    assert set(audit.blockers) == expected
    assert (
        semantic.V075ProductionReadinessBlockerV1
        .TARGET_PROCESS_DEPENDENCY_BOUNDARY_VIOLATION
        not in audit.blockers
    )
    assert audit.to_document()["claimed_status_strings_accepted"] is False
    assert audit.to_document()["registered_target_ready"] is False
    assert audit.to_document()["official_economics_ready"] is False
    assert (
        audit.to_document()["committed_artifact_path_replay_implemented"]
        is False
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityNotReady
    ) as error:
        semantic.require_v075_production_semantic_readiness_v1()
    assert (
        "BATCHED_OBSERVER_TOTAL_LIFT_LINEAGE_UNBOUND"
        in str(error.value)
    )
