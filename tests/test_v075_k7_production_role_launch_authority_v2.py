from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import pickle
import socket
import sys
from typing import Iterator

import pytest

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_broker_resource_session_v2 as resource_v2
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_launch_authority_v2 as launch_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp.phase3e_ids import canonical_json_bytes
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _id, _successor_request


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def frozen_manifest(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[
    object,
    manifest_v2.K7ProductionRoleManifestV2,
    Path,
    Path,
]:
    root = tmp_path_factory.mktemp("production-launch-authority-v2")
    private_root = (root / "private").resolve()
    private_root.mkdir(mode=0o700)
    private_key = (private_root / "observer-key.json").resolve()
    private_key.write_bytes(b"production-launch-authority-v2-static-key")
    private_key.chmod(0o600)
    request = _successor_request("production-launch-authority-v2-base")
    manifest = manifest_v2.freeze_v075_k7_production_role_manifest_v2(
        request=request,
        repository_root=REPOSITORY_ROOT,
        signer_private_root=private_root,
        signer_private_key_path=private_key,
    )
    return request, manifest, private_root, private_key


def _sealed_readonly(raw: bytes, label: str) -> int:
    writable = runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=raw,
        name=f"acfqp-launch-v2-{label}",
    )
    try:
        return os.open(
            f"/proc/self/fd/{writable}",
            os.O_RDONLY | os.O_CLOEXEC,
        )
    finally:
        os.close(writable)


@dataclass
class _LaunchFixture:
    request: object
    manifest: manifest_v2.K7ProductionRoleManifestV2
    private_root: Path
    private_key: Path
    session: resource_v2.K7BrokerResourceSessionV2
    worker_context: manifest_v2.K7ProductionRoleLaunchContextV2
    business_context: manifest_v2.K7ProductionRoleLaunchContextV2
    worker_public_fds: dict[str, int]
    business_public_fds: dict[str, int]
    secret_fd: int
    interpreter_fd: int
    output_parent: Path

    def authority(
        self,
        role: manifest_v2.K7ProductionBrokerRoleV2,
        **overrides: object,
    ) -> launch_v2.K7ProductionRoleLaunchAuthorityV2:
        worker = role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
        arguments: dict[str, object] = {
            "manifest": self.manifest,
            "launch_context": (
                self.worker_context if worker else self.business_context
            ),
            "capability_bundle": (
                self.session.worker_capabilities
                if worker
                else self.session.business_capabilities
            ),
            "public_sealed_input_fds": (
                self.worker_public_fds if worker else self.business_public_fds
            ),
            "interpreter_fd": self.interpreter_fd,
            "repository_root": REPOSITORY_ROOT,
            "lifecycle_secret_fd": None if worker else self.secret_fd,
            "signer_private_root": None if worker else self.private_root,
            "signer_private_key_path": None if worker else self.private_key,
        }
        arguments.update(overrides)
        return launch_v2.freeze_v075_k7_production_role_launch_authority_v2(
            **arguments  # type: ignore[arg-type]
        )

    @property
    def public_fds(self) -> dict[str, int]:
        """Compatibility shorthand for worker-focused attack checks."""

        return self.worker_public_fds


@contextmanager
def _launch_fixture(
    tmp_path: Path,
    frozen_manifest: tuple[
        object,
        manifest_v2.K7ProductionRoleManifestV2,
        Path,
        Path,
    ],
    label: str,
) -> Iterator[_LaunchFixture]:
    request, manifest, private_root, private_key = frozen_manifest
    binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        request.request_id,
        request.route_identity.route_identity_id,
        _id(f"launch-v2-spec-{label}"),
        _id(f"launch-v2-nonce-{label}"),
    )
    worker_context = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
        manifest=manifest,
        binding=binding,
        role=manifest_v2.K7ProductionBrokerRoleV2.WORKER,
    )
    business_context = manifest_v2.freeze_v075_k7_production_role_launch_context_v2(
        manifest=manifest,
        binding=binding,
        role=manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
    )
    output_parent = (tmp_path / f"output-parent-{label}").resolve()
    output_parent.mkdir(mode=0o700)
    parent_fd = os.open(
        output_parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        session = resource_v2.prepare_v075_k7_broker_resource_session_v2(
            manifest=manifest,
            worker_context=worker_context,
            business_context=business_context,
            output_parent_fd=parent_fd,
        )
    finally:
        os.close(parent_fd)
    worker_expected = launch_v2.derive_v075_k7_production_role_public_input_bytes_v2(
        manifest=manifest,
        launch_context=worker_context,
    )
    business_expected = launch_v2.derive_v075_k7_production_role_public_input_bytes_v2(
        manifest=manifest,
        launch_context=business_context,
    )
    worker_public_fds = {
        role: _sealed_readonly(raw, f"{label}-worker-{index}")
        for index, (role, raw) in enumerate(worker_expected.items())
    }
    business_public_fds = {
        role: _sealed_readonly(raw, f"{label}-business-{index}")
        for index, (role, raw) in enumerate(business_expected.items())
    }
    secret_fd = _sealed_readonly(
        b"private-lifecycle-secret-for-launch-authority-v2",
        f"{label}-secret",
    )
    interpreter_fd = os.open(
        Path(sys.executable).resolve(strict=True),
        os.O_RDONLY | os.O_CLOEXEC,
    )
    fixture = _LaunchFixture(
        request,
        manifest,
        private_root,
        private_key,
        session,
        worker_context,
        business_context,
        worker_public_fds,
        business_public_fds,
        secret_fd,
        interpreter_fd,
        output_parent,
    )
    try:
        yield fixture
    finally:
        for descriptor in (
            *worker_public_fds.values(),
            *business_public_fds.values(),
            secret_fd,
            interpreter_fd,
        ):
            try:
                os.close(descriptor)
            except OSError:
                pass
        session.close()
        assert list(output_parent.iterdir()) == []


def test_worker_authority_freezes_exact_record_and_consumes_once(
    tmp_path: Path,
    frozen_manifest: tuple[
        object,
        manifest_v2.K7ProductionRoleManifestV2,
        Path,
        Path,
    ],
) -> None:
    with _launch_fixture(tmp_path, frozen_manifest, "worker") as fixture:
        authority = fixture.authority(
            manifest_v2.K7ProductionBrokerRoleV2.WORKER
        )
        authority.assert_current()
        document = authority.to_document()
        assert authority.role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
        assert authority.sealed_input_roles == bootstrap_v2.WORKER_SEALED_INPUT_ROLES
        assert authority.capability_roles == bootstrap_v2.WORKER_CAPABILITY_ROLES
        assert document["raw_descriptor_numbers_serialized"] is False
        assert document["private_locator_serialized"] is False
        assert document["processes_launched"] == 0
        assert all(value is False for value in document["formal_locks"].values())
        raw_document = canonical_json_bytes(document)
        assert os.fsencode(fixture.private_root) not in raw_document
        assert os.fsencode(fixture.private_key) not in raw_document
        with pytest.raises(TypeError, match="process-local"):
            pickle.dumps(authority)

        executable, sealed, capabilities, argv, environment_rows = authority.consume()
        environment = dict(environment_rows)
        assert executable == fixture.interpreter_fd
        assert sealed == tuple(fixture.public_fds.values())
        assert capabilities == tuple(
            fixture.session.worker_capabilities.descriptor(role)
            for role in bootstrap_v2.WORKER_CAPABILITY_ROLES
        )
        assert argv[1:6] == ("-I", "-S", "-B", "-c", bootstrap_v2.WORKER_BOOTSTRAP_SOURCE)
        assert argv[11:13] == ("NOT_APPLICABLE", "NOT_APPLICABLE")
        assert environment[bootstrap_v2.ROLE_ENV] == "WORKER"
        assert environment[bootstrap_v2.SEALED_FD_ENV] == ",".join(map(str, sealed))
        assert bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV in environment
        assert authority.consumed is True
        with pytest.raises(
            launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error,
            match="already consumed",
        ):
            authority.consume()


def test_business_secret_is_metadata_only_and_private_paths_never_serialize(
    tmp_path: Path,
    frozen_manifest: tuple[
        object,
        manifest_v2.K7ProductionRoleManifestV2,
        Path,
        Path,
    ],
) -> None:
    with _launch_fixture(tmp_path, frozen_manifest, "business") as fixture:
        authority = fixture.authority(
            manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
        )
        document = authority.to_document()
        assert authority.sealed_input_roles == bootstrap_v2.BUSINESS_SEALED_INPUT_ROLES
        assert authority.capability_roles == bootstrap_v2.BUSINESS_CAPABILITY_ROLES
        secret = document["sealed_inputs"][-1]
        assert secret["role"] == "LIFECYCLE_SECRET"
        assert secret["sha256"] is None
        assert secret["content_read_by_authority"] is False
        assert document[
            "lifecycle_secret_content_verification_deferred_to_business_core"
        ] is True
        raw_document = canonical_json_bytes(document)
        assert os.fsencode(fixture.private_root) not in raw_document
        assert os.fsencode(fixture.private_key) not in raw_document

        _executable, sealed, capabilities, argv, environment_rows = authority.consume()
        environment = dict(environment_rows)
        assert sealed[-1] == fixture.secret_fd
        assert capabilities == tuple(
            fixture.session.business_capabilities.descriptor(role)
            for role in bootstrap_v2.BUSINESS_CAPABILITY_ROLES
        )
        assert argv[5] == bootstrap_v2.BUSINESS_BOOTSTRAP_SOURCE
        assert argv[11:13] == (
            os.fspath(fixture.private_root),
            os.fspath(fixture.private_key),
        )
        assert environment[bootstrap_v2.ROLE_ENV] == "BUSINESS"
        assert bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV not in environment


def test_crossed_roles_swapped_inputs_and_capability_masquerade_fail_closed(
    tmp_path: Path,
    frozen_manifest: tuple[
        object,
        manifest_v2.K7ProductionRoleManifestV2,
        Path,
        Path,
    ],
) -> None:
    with _launch_fixture(tmp_path, frozen_manifest, "attacks") as fixture:
        with pytest.raises(launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error):
            fixture.authority(
                manifest_v2.K7ProductionBrokerRoleV2.WORKER,
                capability_bundle=fixture.session.business_capabilities,
            )
        swapped = dict(fixture.public_fds)
        swapped["SOURCE_ARCHIVE"], swapped["TRANSPORT_PROFILE"] = (
            swapped["TRANSPORT_PROFILE"],
            swapped["SOURCE_ARCHIVE"],
        )
        with pytest.raises(launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error):
            fixture.authority(
                manifest_v2.K7ProductionBrokerRoleV2.WORKER,
                public_sealed_input_fds=swapped,
            )
        masquerade = dict(fixture.public_fds)
        masquerade["SOURCE_ARCHIVE"] = (
            fixture.session.worker_capabilities.descriptor(
                "BUSINESS_RESULT_READONLY"
            )
        )
        with pytest.raises(launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error):
            fixture.authority(
                manifest_v2.K7ProductionBrokerRoleV2.WORKER,
                public_sealed_input_fds=masquerade,
            )
        with pytest.raises(launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error):
            fixture.authority(
                manifest_v2.K7ProductionBrokerRoleV2.WORKER,
                signer_private_root=fixture.private_root,
            )

        authority = fixture.authority(
            manifest_v2.K7ProductionBrokerRoleV2.WORKER
        )
        assert authority.consumed is False


def test_readwrite_public_input_and_postfreeze_fd_tamper_are_rejected(
    tmp_path: Path,
    frozen_manifest: tuple[
        object,
        manifest_v2.K7ProductionRoleManifestV2,
        Path,
        Path,
    ],
) -> None:
    with _launch_fixture(tmp_path, frozen_manifest, "fd-attacks") as fixture:
        expected = launch_v2.derive_v075_k7_production_role_public_input_bytes_v2(
            manifest=fixture.manifest,
            launch_context=fixture.worker_context,
        )
        readwrite = runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
            raw=expected["SOURCE_ARCHIVE"],
            name="acfqp-launch-v2-readwrite-attack",
        )
        try:
            attacked = dict(fixture.public_fds)
            attacked["SOURCE_ARCHIVE"] = readwrite
            with pytest.raises(
                launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error,
                match="read-only access",
            ):
                fixture.authority(
                    manifest_v2.K7ProductionBrokerRoleV2.WORKER,
                    public_sealed_input_fds=attacked,
                )
        finally:
            os.close(readwrite)

        authority = fixture.authority(
            manifest_v2.K7ProductionBrokerRoleV2.WORKER
        )
        archive_fd = fixture.public_fds["SOURCE_ARCHIVE"]
        os.set_inheritable(archive_fd, True)
        try:
            with pytest.raises(
                launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error
            ):
                authority.consume()
        finally:
            os.set_inheritable(archive_fd, False)
        record = authority.consume()
        assert record[1][0] == archive_fd


def test_profile_is_nonformal_and_caller_cannot_mint_it() -> None:
    profile = launch_v2.official_v075_k7_production_role_launch_authority_profile_v2()
    document = profile.to_document()
    assert document["central_domain_registration_pending_merge"] is False
    assert document["private_locator_serialized"] is False
    assert all(value is False for value in document["formal_locks"].values())
    with pytest.raises(
        launch_v2.V075K7ProductionRoleLaunchAuthorityV2Error,
        match="issuer-owned",
    ):
        launch_v2.K7ProductionRoleLaunchAuthorityProfileV2(object())
