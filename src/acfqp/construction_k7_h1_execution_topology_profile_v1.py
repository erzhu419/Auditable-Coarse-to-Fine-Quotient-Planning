"""Construction-only H1 BROKER/WORKER/BUSINESS execution topology.

Contract 2.0.55 freezes descriptor and capability separation before a live
launcher exists.  It neither opens descriptors nor launches a process.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_EXECUTION_TOPOLOGY_PROFILE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.55"
PROFILE_KEY = "construction_k7_h1_execution_topology_profile_v1"
CONSTRUCTION_ONLY = True
OFFICIAL_EXECUTION_ALLOWED = False
PROCESS_LAUNCHES_AUTHORIZED = False
EXPECTED_CHILD_PROCESS_LAUNCHES = 2

DOMAIN = CONSTRUCTION_K7_H1_EXECUTION_TOPOLOGY_PROFILE_V1_DOMAIN
if DOMAIN not in PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("H1 execution-topology domain is not registered")

_ISSUER = object()
WORKER_CHANNEL_PAIR_ID = content_id(
    DOMAIN,
    {"schema": "acfqp.h1_socketpair_identity.v1", "channel": "BROKER_WORKER"},
)
BUSINESS_CHANNEL_PAIR_ID = content_id(
    DOMAIN,
    {"schema": "acfqp.h1_socketpair_identity.v1", "channel": "BROKER_BUSINESS"},
)


class ConstructionK7H1ExecutionTopologyProfileV1Error(ValueError):
    """The frozen H1 role/descriptor topology is malformed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ExecutionTopologyProfileV1Error(message)


class H1ExecutionRoleV1(str, Enum):
    BROKER = "BROKER"
    WORKER = "WORKER"
    BUSINESS = "BUSINESS"


class H1FDAccessV1(str, Enum):
    READ_ONLY = "READ_ONLY"
    READ_WRITE = "READ_WRITE"


class H1FDOriginV1(str, Enum):
    BROKER_PREOPENED = "BROKER_PREOPENED"
    CLONE3_PIDFD_RESULT = "CLONE3_PIDFD_RESULT"
    CHILD_INHERITED_FIXED_FD = "CHILD_INHERITED_FIXED_FD"


@dataclass(frozen=True, slots=True)
class H1SealedInputGrantV1:
    role: H1ExecutionRoleV1
    fd_number: int
    input_role: str
    close_after_lifecycle_step: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "role", H1ExecutionRoleV1(self.role))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExecutionTopologyProfileV1Error(
                "H1 sealed-input role is invalid"
            ) from error
        if (
            self.role is H1ExecutionRoleV1.BROKER
            or type(self.fd_number) is not int
            or self.fd_number < 10
            or type(self.input_role) is not str
            or not self.input_role
            or type(self.close_after_lifecycle_step) is not str
            or not self.close_after_lifecycle_step
        ):
            _fail("H1 sealed input must be one fixed child-only FD")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "fd_number": self.fd_number,
            "input_role": self.input_role,
            "object_kind": "SEALED_READ_ONLY_MEMFD",
            "access": H1FDAccessV1.READ_ONLY.value,
            "origin": H1FDOriginV1.CHILD_INHERITED_FIXED_FD.value,
            "close_after_lifecycle_step": self.close_after_lifecycle_step,
            "ambient_path_fallback_allowed": False,
            "scm_rights_delivery_allowed": False,
        }


@dataclass(frozen=True, slots=True)
class H1LifecycleStepV1:
    ordinal: int
    step: str
    owner: H1ExecutionRoleV1

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "owner", H1ExecutionRoleV1(self.owner))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExecutionTopologyProfileV1Error(
                "H1 lifecycle owner is invalid"
            ) from error
        if (
            type(self.ordinal) is not int
            or self.ordinal <= 0
            or type(self.step) is not str
            or not self.step
        ):
            _fail("H1 lifecycle step is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "step": self.step,
            "owner": self.owner.value,
            "runtime_implemented": False,
        }


@dataclass(frozen=True, slots=True)
class H1FDGrantV1:
    role: H1ExecutionRoleV1
    fd_number: int
    descriptor_role: str
    object_kind: str
    access: H1FDAccessV1
    physical_object: str
    open_file_description: str
    origin: H1FDOriginV1
    channel_pair_id: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "role", H1ExecutionRoleV1(self.role))
            object.__setattr__(self, "access", H1FDAccessV1(self.access))
            object.__setattr__(self, "origin", H1FDOriginV1(self.origin))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExecutionTopologyProfileV1Error(
                "H1 FD grant role/access is invalid"
            ) from error
        if (
            type(self.fd_number) is not int
            or self.fd_number < 0
            or any(
                type(value) is not str or not value
                for value in (
                    self.descriptor_role,
                    self.object_kind,
                    self.physical_object,
                    self.open_file_description,
                )
            )
        ):
            _fail("H1 FD grant is malformed")
        child = self.role in {H1ExecutionRoleV1.WORKER, H1ExecutionRoleV1.BUSINESS}
        if child != (self.origin is H1FDOriginV1.CHILD_INHERITED_FIXED_FD):
            _fail("only child descriptors may be inherited at fresh exec")
        if (self.object_kind == "PIDFD") != (
            self.origin is H1FDOriginV1.CLONE3_PIDFD_RESULT
        ):
            _fail("pidfds must be clone3 results and cannot be inherited")
        if self.object_kind == "SOCK_SEQPACKET":
            if self.channel_pair_id not in {
                WORKER_CHANNEL_PAIR_ID,
                BUSINESS_CHANNEL_PAIR_ID,
            }:
                _fail("H1 socket endpoint lacks its exact shared channel-pair ID")
        elif self.channel_pair_id is not None:
            _fail("only socket endpoints may bind a channel-pair ID")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "fd_number": self.fd_number,
            "descriptor_role": self.descriptor_role,
            "object_kind": self.object_kind,
            "access": self.access.value,
            "physical_object": self.physical_object,
            "open_file_description": self.open_file_description,
            "origin": self.origin.value,
            "channel_pair_id": self.channel_pair_id,
            "inherited_at_fresh_exec": (
                self.origin is H1FDOriginV1.CHILD_INHERITED_FIXED_FD
            ),
        }


@dataclass(frozen=True, slots=True)
class H1RoleCapabilityV1:
    role: H1ExecutionRoleV1
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "role", H1ExecutionRoleV1(self.role))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ExecutionTopologyProfileV1Error(
                "H1 capability role is invalid"
            ) from error
        for values in (self.allowed, self.forbidden):
            if (
                type(values) is not tuple
                or not values
                or len(values) != len(set(values))
                or any(type(value) is not str or not value for value in values)
            ):
                _fail("H1 role capabilities must be nonempty unique tuples")
        if set(self.allowed) & set(self.forbidden):
            _fail("H1 role capability is simultaneously allowed and forbidden")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "allowed": list(self.allowed),
            "forbidden": list(self.forbidden),
        }


def _fd_grants() -> tuple[H1FDGrantV1, ...]:
    R = H1FDAccessV1.READ_ONLY
    RW = H1FDAccessV1.READ_WRITE
    B = H1ExecutionRoleV1.BROKER
    W = H1ExecutionRoleV1.WORKER
    X = H1ExecutionRoleV1.BUSINESS
    P = H1FDOriginV1.BROKER_PREOPENED
    C = H1FDOriginV1.CLONE3_PIDFD_RESULT
    I = H1FDOriginV1.CHILD_INHERITED_FIXED_FD
    return (
        H1FDGrantV1(B, 101, "worker_channel", "SOCK_SEQPACKET", RW, "broker_worker_channel_broker_endpoint", "broker_worker_ofd", P, WORKER_CHANNEL_PAIR_ID),
        H1FDGrantV1(B, 102, "business_channel", "SOCK_SEQPACKET", RW, "broker_business_channel_broker_endpoint", "broker_business_ofd", P, BUSINESS_CHANNEL_PAIR_ID),
        H1FDGrantV1(B, 103, "business_result", "O_TMPFILE_REGULAR_FILE", R, "business_result_inode", "broker_result_ro_ofd", P),
        H1FDGrantV1(B, 104, "output_directory", "DIRECTORY", RW, "attempt_output_directory", "broker_output_dir_ofd", P),
        H1FDGrantV1(B, 105, "parent_cgroup_control", "CGROUP_DIRECTORY", RW, "outer_cgroup", "broker_outer_cgroup_ofd", P),
        H1FDGrantV1(B, 106, "worker_cgroup_control", "CGROUP_DIRECTORY", RW, "worker_cgroup", "broker_worker_cgroup_ofd", P),
        H1FDGrantV1(B, 107, "business_cgroup_control", "CGROUP_DIRECTORY", RW, "business_cgroup", "broker_business_cgroup_ofd", P),
        H1FDGrantV1(B, 108, "worker_pidfd", "PIDFD", R, "worker_process", "worker_pidfd_ofd", C),
        H1FDGrantV1(B, 109, "business_pidfd", "PIDFD", R, "business_process", "business_pidfd_ofd", C),
        H1FDGrantV1(B, 110, "memory_peak", "CGROUP_FILE", R, "outer_memory_peak", "retained_memory_peak_ofd", P),
        H1FDGrantV1(W, 3, "broker_channel", "SOCK_SEQPACKET", RW, "broker_worker_channel_worker_endpoint", "worker_channel_ofd", I, WORKER_CHANNEL_PAIR_ID),
        H1FDGrantV1(W, 4, "business_result", "O_TMPFILE_REGULAR_FILE", R, "business_result_inode", "worker_result_ro_ofd", I),
        H1FDGrantV1(X, 3, "broker_channel", "SOCK_SEQPACKET", RW, "broker_business_channel_business_endpoint", "business_channel_ofd", I, BUSINESS_CHANNEL_PAIR_ID),
        H1FDGrantV1(X, 4, "business_result", "O_TMPFILE_REGULAR_FILE", RW, "business_result_inode", "business_result_rw_ofd", I),
        H1FDGrantV1(X, 5, "output_directory", "DIRECTORY", RW, "attempt_output_directory", "business_output_dir_ofd", I),
    )


def _sealed_inputs() -> tuple[H1SealedInputGrantV1, ...]:
    W = H1ExecutionRoleV1.WORKER
    B = H1ExecutionRoleV1.BUSINESS
    return (
        H1SealedInputGrantV1(W, 10, "sealed_runtime_archive", "WORKER_ENTRY_LOADED"),
        H1SealedInputGrantV1(W, 11, "ipc_binding_candidate", "WORKER_BINDING_REPLAYED"),
        H1SealedInputGrantV1(W, 12, "execution_topology_profile", "WORKER_BINDING_REPLAYED"),
        H1SealedInputGrantV1(B, 10, "sealed_runtime_archive", "BUSINESS_ENTRY_LOADED"),
        H1SealedInputGrantV1(B, 11, "business_request_candidate", "BUSINESS_REQUEST_REPLAYED"),
        H1SealedInputGrantV1(B, 12, "owned_engine_source", "OWNED_ENGINE_AUTHORITY_REPLAYED"),
        H1SealedInputGrantV1(B, 13, "owned_engine_authority_document", "OWNED_ENGINE_AUTHORITY_REPLAYED"),
        H1SealedInputGrantV1(B, 14, "kernel_replay_document", "BUSINESS_RESULT_COMMITTED"),
        H1SealedInputGrantV1(B, 15, "query_replay_document", "BUSINESS_RESULT_COMMITTED"),
        H1SealedInputGrantV1(B, 16, "fallback_cap_profile", "BUSINESS_RESULT_COMMITTED"),
    )


def _lifecycle() -> tuple[H1LifecycleStepV1, ...]:
    B = H1ExecutionRoleV1.BROKER
    W = H1ExecutionRoleV1.WORKER
    X = H1ExecutionRoleV1.BUSINESS
    rows = (
        ("PREDECISION_INPUTS_FROZEN", B),
        ("FORMAL_DECISION_VERIFIED", B),
        ("ROUTE_DECISION_FROZEN", B),
        ("REQUEST_CANDIDATE_SERIALIZED_AND_SEALED", B),
        ("WORKER_LAUNCHED", B),
        ("WORKER_ENTRY_LOADED", W),
        ("WORKER_BINDING_REPLAYED", W),
        ("WORKER_READY_AND_BUSINESS_REQUEST_SIGNAL", W),
        ("BUSINESS_LAUNCHED", B),
        ("BUSINESS_ENTRY_LOADED", X),
        ("BUSINESS_REQUEST_REPLAYED", X),
        ("OWNED_ENGINE_AUTHORITY_REPLAYED", X),
        ("OWNED_SEARCH_FINISHED", X),
        ("BUSINESS_RESULT_COMMITTED", X),
        ("BUSINESS_EXITED_AND_REAPED_RESULT_PINNED", B),
        ("BUSINESS_RESULT_RELAYED_AND_WORKER_ACKED", W),
        ("WORKER_EOF_OBSERVED", B),
        ("WORKER_REAPED", B),
        ("BROKER_SUFFIX_COMMITTED", B),
        ("SHARED_RECEIPTS_SETTLED", B),
        ("FORMAL_ACCOUNTING_CLOSED", B),
    )
    return tuple(
        H1LifecycleStepV1(index, step, owner)
        for index, (step, owner) in enumerate(rows, start=1)
    )


def _capabilities() -> tuple[H1RoleCapabilityV1, ...]:
    return (
        H1RoleCapabilityV1(
            H1ExecutionRoleV1.BROKER,
            (
                "launch_worker_then_business",
                "authenticate_and_relay_frames",
                "read_and_pin_business_result",
                "reap_both_children_by_pidfd",
                "read_retained_memory_peak",
                "render_broker_owned_output_suffix",
            ),
            (
                "run_ground_fallback_search",
                "write_business_result",
                "author_business_result_frame",
            ),
        ),
        H1RoleCapabilityV1(
            H1ExecutionRoleV1.WORKER,
            (
                "author_worker_ready",
                "verify_read_only_business_result",
                "author_worker_ack",
                "author_worker_eof",
            ),
            (
                "run_ground_fallback_search",
                "write_any_output",
                "launch_or_reap_process",
                "access_repository_or_private_key",
            ),
        ),
        H1RoleCapabilityV1(
            H1ExecutionRoleV1.BUSINESS,
            (
                "consume_frozen_h1_request",
                "run_owned_ground_fallback_search",
                "write_fsync_linkat_rename_noreplace_and_reread_business_result",
                "author_business_result_frame",
            ),
            (
                "launch_or_reap_process",
                "render_broker_owned_output_suffix",
                "access_ambient_repository",
                "access_private_key",
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class H1ExecutionTopologyProfileV1:
    _issuer: InitVar[object]
    fd_grants: tuple[H1FDGrantV1, ...]
    sealed_inputs: tuple[H1SealedInputGrantV1, ...]
    lifecycle: tuple[H1LifecycleStepV1, ...]
    capabilities: tuple[H1RoleCapabilityV1, ...]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or self.fd_grants != _fd_grants()
            or self.sealed_inputs != _sealed_inputs()
            or self.lifecycle != _lifecycle()
            or self.capabilities != _capabilities()
        ):
            _fail("H1 execution topology is issuer-owned and exact")
        pairs = tuple((row.role, row.fd_number) for row in self.fd_grants)
        if len(pairs) != len(set(pairs)):
            _fail("H1 role FD numbers are not unique within a process")
        worker = tuple(row.descriptor_role for row in self.fd_grants if row.role is H1ExecutionRoleV1.WORKER)
        business = tuple(row.descriptor_role for row in self.fd_grants if row.role is H1ExecutionRoleV1.BUSINESS)
        if worker != ("broker_channel", "business_result") or business != ("broker_channel", "business_result", "output_directory"):
            _fail("H1 child descriptor separation changed")
        channel_rows = {
            pair_id: tuple(
                row for row in self.fd_grants if row.channel_pair_id == pair_id
            )
            for pair_id in (WORKER_CHANNEL_PAIR_ID, BUSINESS_CHANNEL_PAIR_ID)
        }
        if any(
            len(rows) != 2
            or rows[0].role is not H1ExecutionRoleV1.BROKER
            or rows[1].role is H1ExecutionRoleV1.BROKER
            or len({row.physical_object for row in rows}) != 2
            or len({row.open_file_description for row in rows}) != 2
            for rows in channel_rows.values()
        ):
            _fail("H1 socketpair endpoints or shared pair identities changed")
        sealed_pairs = tuple(
            (row.role, row.fd_number) for row in self.sealed_inputs
        )
        if (
            len(sealed_pairs) != len(set(sealed_pairs))
            or any(pair in pairs for pair in sealed_pairs)
            or tuple(row.ordinal for row in self.lifecycle)
            != tuple(range(1, len(self.lifecycle) + 1))
            or len({row.step for row in self.lifecycle}) != len(self.lifecycle)
            or any(
                row.close_after_lifecycle_step
                not in {step.step for step in self.lifecycle}
                for row in self.sealed_inputs
            )
        ):
            _fail("H1 sealed-input or lifecycle topology changed")
        result = tuple(row for row in self.fd_grants if row.physical_object == "business_result_inode")
        if (
            tuple(row.role for row in result) != (
                H1ExecutionRoleV1.BROKER,
                H1ExecutionRoleV1.WORKER,
                H1ExecutionRoleV1.BUSINESS,
            )
            or tuple(row.access for row in result) != (
                H1FDAccessV1.READ_ONLY,
                H1FDAccessV1.READ_ONLY,
                H1FDAccessV1.READ_WRITE,
            )
            or len({row.open_file_description for row in result}) != 3
        ):
            _fail("H1 result inode must use distinct BROKER/WORKER/BUSINESS OFDs")
        object.__setattr__(self, "_profile_id", content_id(DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_execution_topology_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "process_roles": [role.value for role in H1ExecutionRoleV1],
            "broker_is_parent_not_launched_child": True,
            "child_launch_order": ["WORKER", "BUSINESS"],
            "expected_child_process_launches": EXPECTED_CHILD_PROCESS_LAUNCHES,
            "fd_grants": [row.to_document() for row in self.fd_grants],
            "sealed_input_grants": [
                row.to_document() for row in self.sealed_inputs
            ],
            "lifecycle": [row.to_document() for row in self.lifecycle],
            "capabilities": [row.to_document() for row in self.capabilities],
            "fixed_inherited_fd_numbers": True,
            "broker_descriptors_are_not_fresh_exec_inherited": True,
            "pidfds_are_clone3_results": True,
            "business_request_delivered_by_sealed_inherited_fd": True,
            "sealed_inputs_are_not_active_role_capabilities": True,
            "sealed_inputs_closed_at_registered_lifecycle_steps": True,
            "lifecycle_runtime_implemented": False,
            "same_result_inode_distinct_open_file_descriptions": True,
            "socketpair_endpoints_are_distinct_physical_objects": True,
            "socketpair_endpoints_bind_shared_pair_ids": True,
            "business_result_object_kind": "O_TMPFILE_REGULAR_FILE",
            "business_result_commit_strategy": (
                "WRITE_FSYNC_LINKAT_RENAME_NOREPLACE_DIRECTORY_FSYNC_REREAD_"
                "BUSINESS_EXIT_REAP_BEFORE_RELAY"
            ),
            "scm_rights_allowed": False,
            "ambient_repository_allowed": False,
            "ambient_private_key_allowed": False,
            "worker_result_write_access": False,
            "broker_result_write_access": False,
            "business_result_write_access": True,
            "process_launches_authorized": False,
            "live_fd_binding_present": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def profile_id(self) -> str:
        if content_id(DOMAIN, self._payload()) != self._profile_id:
            _fail("H1 execution topology changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_execution_topology_profile_id": self.profile_id}


_OFFICIAL_PROFILE = H1ExecutionTopologyProfileV1(
    _ISSUER,
    _fd_grants(),
    _sealed_inputs(),
    _lifecycle(),
    _capabilities(),
)


def official_h1_execution_topology_profile_v1() -> H1ExecutionTopologyProfileV1:
    return _OFFICIAL_PROFILE


__all__ = (
    "BUSINESS_CHANNEL_PAIR_ID",
    "CONSTRUCTION_ONLY",
    "EXPECTED_CHILD_PROCESS_LAUNCHES",
    "H1ExecutionRoleV1",
    "H1ExecutionTopologyProfileV1",
    "H1FDAccessV1",
    "H1FDGrantV1",
    "H1FDOriginV1",
    "H1LifecycleStepV1",
    "H1RoleCapabilityV1",
    "H1SealedInputGrantV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROCESS_LAUNCHES_AUTHORIZED",
    "PROPOSED_CONTRACT_VERSION",
    "ConstructionK7H1ExecutionTopologyProfileV1Error",
    "official_h1_execution_topology_profile_v1",
    "WORKER_CHANNEL_PAIR_ID",
)
