from __future__ import annotations

import hashlib
import inspect

import pytest

from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as prep_v1
from acfqp import v075_k7_production_role_manifest_v1 as manifest_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _successor_request
from tests.test_v075_k7_outer_attempt_broker_preparation_v1 import _fake_lease


def _prepared(tmp_path, monkeypatch, label):
    context = _fake_lease(tmp_path, monkeypatch, label)
    lease, request, *_rest = context.__enter__()
    session = prep_v1.K7OuterAttemptBrokerPreparationServiceV1().prepare(lease)
    return context, request, session


def test_profile_freezes_two_roles_author_vector_and_all_formal_locks() -> None:
    profile = (
        manifest_v1.official_v075_k7_production_role_manifest_profile_v1()
    )
    document = profile.to_document()
    assert manifest_v1.PROPOSED_CONTRACT_VERSION == "2.0.7"
    assert document["role_order"] == ["WORKER", "BUSINESS"]
    assert document["cgroup_names"] == ["worker", "business"]
    assert document["frame_author_vector"] == [
        {"frame_role": frame, "author_role": author}
        for frame, author in manifest_v1.FRAME_AUTHOR_VECTOR
    ]
    assert tuple(frame for frame, _author in manifest_v1.FRAME_AUTHOR_VECTOR) == tuple(
        role.value for role in ipc_v1.FRAME_ROLES
    )
    assert tuple(author for _frame, author in manifest_v1.FRAME_AUTHOR_VECTOR) == (
        "WORKER",
        "WORKER",
        "BUSINESS",
        "WORKER",
        "WORKER",
    )
    assert document["caller_program_selection_allowed"] is False
    assert document["caller_argv_selection_allowed"] is False
    assert document["caller_environment_selection_allowed"] is False
    assert document["caller_fd_role_selection_allowed"] is False
    assert document["caller_cgroup_selection_allowed"] is False
    assert set(document["formal_locks"].values()) == {False}
    assert manifest_v1.LOCAL_DOMAIN_TAGS == {
        "acfqp:v075-k7-production-role-manifest-profile:v1",
        "acfqp:v075-k7-production-role-spec:v1",
        "acfqp:v075-k7-production-role-manifest:v1",
    }
    assert manifest_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS == (
        "V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN",
        "V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN",
        "V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN",
    )
    with pytest.raises(
        manifest_v1.V075K7ProductionRoleManifestV1Error,
        match="issuer-owned",
    ):
        manifest_v1.K7ProductionRoleManifestProfileV1(object())


def test_manifest_derives_request_session_source_interpreter_and_role_contracts(
    tmp_path, monkeypatch
) -> None:
    context, request, session = _prepared(tmp_path, monkeypatch, "role-manifest-main")
    try:
        value = manifest_v1.freeze_v075_k7_production_role_manifest_v1(
            request=request,
            prepared_session=session,
        )
        value.assert_current(request=request, prepared_session=session)
        transport = request.profile.accounted_profile.transport_profile
        runtime = transport.runtime_document
        assert value.request_id == request.request_id
        assert value.prepared_session_id == session.session_id
        assert value.broker_execution_spec_id == session.execution_spec.spec_id
        assert value.source_snapshot_id == transport.source_snapshot_id
        assert value.source_archive_sha256 == transport.source_archive_sha256
        assert value.source_archive_byte_count == transport.source_archive_byte_count
        assert value.interpreter_sha256 == runtime["executable_sha256"]
        assert value.interpreter_byte_count == runtime["executable_byte_count"]
        assert value.worker_dispatch_sha256 == hashlib.sha256(
            manifest_v1.WORKER_ENTRY_SOURCE.encode("utf-8")
        ).hexdigest()
        assert value.business_dispatch_sha256 == hashlib.sha256(
            manifest_v1.BUSINESS_ENTRY_SOURCE.encode("utf-8")
        ).hexdigest()

        worker = value.assert_role_binding(
            manifest_v1.K7ProductionBrokerRoleV1.WORKER,
            request_id=value.request_id,
            prepared_session_id=value.prepared_session_id,
            broker_execution_spec_id=value.broker_execution_spec_id,
            source_archive_sha256=value.source_archive_sha256,
            interpreter_sha256=value.interpreter_sha256,
            dispatch_sha256=value.worker_dispatch_sha256,
        )
        business = value.assert_role_binding(
            manifest_v1.K7ProductionBrokerRoleV1.BUSINESS,
            request_id=value.request_id,
            prepared_session_id=value.prepared_session_id,
            broker_execution_spec_id=value.broker_execution_spec_id,
            source_archive_sha256=value.source_archive_sha256,
            interpreter_sha256=value.interpreter_sha256,
            dispatch_sha256=value.business_dispatch_sha256,
        )
        assert worker is value.worker_role
        assert business is value.business_role
        assert worker.cgroup_name == "worker"
        assert business.cgroup_name == "business"
        assert dict(worker.cgroup_descriptor_identity) == dict(
            session.execution_spec.worker_identity
        )
        assert dict(business.cgroup_descriptor_identity) == dict(
            session.execution_spec.business_identity
        )
        assert worker.argv == manifest_v1.WORKER_ARGV
        assert business.argv == manifest_v1.BUSINESS_ARGV
        assert dict(worker.base_environment) == dict(manifest_v1.BASE_ENVIRONMENT)
        assert dict(business.base_environment) == dict(manifest_v1.BASE_ENVIRONMENT)
        assert worker.inherited_fd_roles == manifest_v1.WORKER_INHERITED_FD_ROLES
        assert business.inherited_fd_roles == manifest_v1.BUSINESS_INHERITED_FD_ROLES
        assert worker.writable_fd_roles == ("OUTPUT_DIRECTORY",)
        assert business.writable_fd_roles == ("BUSINESS_RESULT_WRITABLE",)
        assert worker.entry_source_path == manifest_v1.WORKER_ENTRY_SOURCE_PATH
        assert business.entry_source_path == manifest_v1.BUSINESS_ENTRY_SOURCE_PATH
        assert worker.entry_source_present is False
        assert business.entry_source_present is False
        assert worker.entry_source_sha256 is None
        assert business.entry_source_sha256 is None
        assert "LIFECYCLE_SECRET" not in worker.sealed_input_roles
        assert "LIFECYCLE_SECRET" in business.sealed_input_roles
        assert "BUSINESS_RESULT_WRITABLE" not in worker.inherited_fd_roles
        assert "OUTPUT_DIRECTORY" not in business.inherited_fd_roles
        manifest_document = value.to_document()
        assert set(manifest_document["formal_locks"].values()) == {False}
        assert set(manifest_document["worker_role"]["formal_locks"].values()) == {
            False
        }
        assert set(manifest_document["business_role"]["formal_locks"].values()) == {
            False
        }

        raw = value.canonical_bytes
        assert canonical_json_bytes(loads_canonical_json(raw)) == raw
        assert (
            manifest_v1.verify_v075_k7_production_role_manifest_bytes_v1(
                raw=raw,
                expected=value,
            )
            is value
        )
    finally:
        if not session.guardian.closed:
            session.close_prelaunch()
        context.__exit__(None, None, None)


def test_caller_mint_cross_binding_and_byte_mutation_fail_closed(
    tmp_path, monkeypatch
) -> None:
    context, request, session = _prepared(tmp_path, monkeypatch, "role-manifest-attacks")
    try:
        value = manifest_v1.freeze_v075_k7_production_role_manifest_v1(
            request=request,
            prepared_session=session,
        )
        with pytest.raises(
            manifest_v1.V075K7ProductionRoleManifestV1Error,
            match="caller-minted",
        ):
            manifest_v1.K7ProductionRoleManifestV1(
                object(),
                value.request,
                value.prepared_session,
                value.worker_role,
                value.business_role,
                value.source_snapshot_id,
                value.source_archive_sha256,
                value.source_archive_byte_count,
                value.transport_profile_id,
                value.runtime_id,
                value.interpreter_sha256,
                value.interpreter_byte_count,
            )
        worker = value.worker_role
        with pytest.raises(
            manifest_v1.V075K7ProductionRoleManifestV1Error,
            match="issuer-owned",
        ):
            manifest_v1.K7ProductionRoleSpecV1(
                object(),
                worker.role,
                worker.ordinal,
                worker.cgroup_name,
                worker.cgroup_descriptor_identity,
                worker.entry_module,
                worker.entry_symbol,
                worker.dispatch_sha256,
                worker.entry_source_path,
                worker.entry_source_sha256,
                worker.entry_source_byte_count,
                worker.entry_source_present,
                worker.argv,
                worker.base_environment,
                worker.runtime_environment_contract,
                worker.sealed_input_roles,
                worker.inherited_fd_roles,
                worker.writable_fd_roles,
                worker.authored_frame_roles,
            )

        foreign_request = _successor_request("role-manifest-foreign")
        with pytest.raises(
            manifest_v1.V075K7ProductionRoleManifestV1Error,
            match="crossed request/session/route",
        ):
            manifest_v1.freeze_v075_k7_production_role_manifest_v1(
                request=foreign_request,
                prepared_session=session,
            )
        with pytest.raises(
            manifest_v1.V075K7ProductionRoleManifestV1Error,
            match="foreign request object",
        ):
            value.assert_current(request=foreign_request)

        correct = {
            "request_id": value.request_id,
            "prepared_session_id": value.prepared_session_id,
            "broker_execution_spec_id": value.broker_execution_spec_id,
            "source_archive_sha256": value.source_archive_sha256,
            "interpreter_sha256": value.interpreter_sha256,
            "dispatch_sha256": value.worker_dispatch_sha256,
        }
        for field in tuple(correct):
            crossed = dict(correct)
            crossed[field] = "0" * 64
            with pytest.raises(
                manifest_v1.V075K7ProductionRoleManifestV1Error,
                match="crossed its manifest binding",
            ):
                value.assert_role_binding(
                    manifest_v1.K7ProductionBrokerRoleV1.WORKER,
                    **crossed,
                )

        document = loads_canonical_json(value.canonical_bytes)
        assert type(document) is dict
        document["worker_role"]["argv"][-1] += " "
        attacked = canonical_json_bytes(document)
        with pytest.raises(
            manifest_v1.V075K7ProductionRoleManifestV1Error,
            match="crossed or changed",
        ):
            manifest_v1.verify_v075_k7_production_role_manifest_bytes_v1(
                raw=attacked,
                expected=value,
            )

        parameters = inspect.signature(
            manifest_v1.freeze_v075_k7_production_role_manifest_v1
        ).parameters
        assert tuple(parameters) == ("request", "prepared_session")
        assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters.values())

        transport = request.profile.accounted_profile.transport_profile
        original_archive = transport._archive_bytes  # noqa: SLF001
        object.__setattr__(transport, "_archive_bytes", original_archive + b"x")
        try:
            with pytest.raises(
                manifest_v1.V075K7ProductionRoleManifestV1Error,
                match="retained authority is stale",
            ):
                value.assert_role_binding(
                    manifest_v1.K7ProductionBrokerRoleV1.WORKER,
                    **correct,
                )
        finally:
            object.__setattr__(transport, "_archive_bytes", original_archive)

        original_owner_pid = session.guardian._owner_pid  # noqa: SLF001
        session.guardian._owner_pid = original_owner_pid + 1  # noqa: SLF001
        try:
            with pytest.raises(
                manifest_v1.V075K7ProductionRoleManifestV1Error,
                match="retained authority is stale",
            ):
                value.assert_current()
        finally:
            session.guardian._owner_pid = original_owner_pid  # noqa: SLF001

        session.close_prelaunch()
        with pytest.raises(
            manifest_v1.V075K7ProductionRoleManifestV1Error,
            match="retained authority is stale",
        ):
            value.assert_role_binding(
                manifest_v1.K7ProductionBrokerRoleV1.WORKER,
                **correct,
            )
    finally:
        if not session.guardian.closed:
            session.close_prelaunch()
        context.__exit__(None, None, None)
