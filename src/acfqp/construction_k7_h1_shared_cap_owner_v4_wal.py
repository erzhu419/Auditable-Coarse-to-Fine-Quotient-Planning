"""Pending-payload WAL successor for the construction H1 shared-cap Owner.

Owner V3 intentionally remains the historical settlement authority.  This
module upgrades an individual runtime with an inode-bound, mandatory payload
WAL.  The exact next record bytes are fsynced before the high-water pending
cursor is published, so a crash cannot leave only an unreconstructable content
ID.  The wrapper delegates the established V3 semantic replay after requiring
that durable binding; it does not promote the caller-provided native values or
issue production, accounting, terminal, or route authority.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import InitVar, dataclass
import hmac
import os
from pathlib import Path
from typing import Any, Iterator, NoReturn

from acfqp import construction_k7_h1_attempt_rejection_gate_v1 as rejection_v1
from acfqp import construction_k7_h1_shared_cap_owner_v3 as owner_v3
from acfqp.phase3e_ids import parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-A"
PROFILE_KEY = "construction_k7_h1_shared_cap_owner_v4_wal"

PENDING_PAYLOAD_WAL_REQUIRED = True
HISTORICAL_V3_CLAIM_RELABELLED = False
NO_EVENT_RECOVERY_COMPLETE = False
CLEANUP_EXECUTION_AUTHORITY_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORD_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

_HANDLE_ISSUER = object()


class ConstructionK7H1SharedCapOwnerV4WalError(ValueError):
    """A WAL successor handle or its durable binding failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1SharedCapOwnerV4WalError(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedCapOwnerV4WalError(
            f"{label} must be one exact lowercase content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class H1SharedCapOwnerV4WalHandle:
    _issuer: InitVar[object]
    owner: owner_v3.H1SharedCapOwnerV3Handle
    binding_id: str

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _HANDLE_ISSUER
            or type(self.owner) is not owner_v3.H1SharedCapOwnerV3Handle
            or self.owner.pending_payload_wal_directory is None
            or self.owner.pending_payload_wal_binding_id is None
            or not hmac.compare_digest(
                _cid(self.binding_id, "V4 WAL binding"),
                _cid(
                    self.owner.pending_payload_wal_binding_id,
                    "Owner V4 WAL binding",
                ),
            )
        ):
            _fail("V4 WAL handle is caller-minted, incomplete, or crossed")

    @property
    def runtime_id(self) -> str:
        return self.owner.runtime_id

    @property
    def owner_directory(self) -> str:
        return self.owner.owner_directory

    @property
    def gate_directory(self) -> str:
        return self.owner.gate_directory

    @property
    def profile(self) -> owner_v3.H1SharedCapProfileCoreV3:
        return self.owner.profile

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_shared_cap_owner_v4_wal_handle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_shared_cap_owner_v3_runtime_id": self.runtime_id,
            "h1_shared_cap_owner_v4_wal_binding_id": self.binding_id,
            "pending_payload_wal_required": True,
            "historical_v3_claim_relabelled": False,
            "no_event_recovery_complete": False,
            "cleanup_execution_authority_present": False,
            "production_execution_authority_present": False,
            "formal_counter_record_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
        }


def _wrap(
    owner: owner_v3.H1SharedCapOwnerV3Handle,
) -> H1SharedCapOwnerV4WalHandle:
    if (
        type(owner) is not owner_v3.H1SharedCapOwnerV3Handle
        or owner.pending_payload_wal_binding_id is None
        or owner.pending_payload_wal_directory is None
    ):
        _fail("Owner runtime does not have the mandatory V4 payload WAL")
    replay = owner_v3.replay_h1_shared_cap_owner_v3(owner)
    if replay["pending_cursor"]["kind"] != "NOT_APPLICABLE":
        _fail("V4 WAL wrapper opened with an unresolved pending cursor")
    return H1SharedCapOwnerV4WalHandle(
        _HANDLE_ISSUER,
        owner,
        owner.pending_payload_wal_binding_id,
    )


def initialize_h1_shared_cap_owner_v4_wal(
    base_directory: str | Path,
    *,
    profile: owner_v3.H1SharedCapProfileCoreV3,
    source_manifest: owner_v3.H1SharedCapOwnerV3SourceManifest,
    rejection_gate: rejection_v1.H1AttemptRejectionGateHandleV1,
) -> H1SharedCapOwnerV4WalHandle:
    try:
        historical = owner_v3.initialize_h1_shared_cap_owner_v3(
            base_directory,
            profile=profile,
            source_manifest=source_manifest,
            rejection_gate=rejection_gate,
        )
    except owner_v3.H1SharedCapOwnerV3ProtocolFailure:
        # A prior V4 initializer may have durably created its WAL namespace
        # and control intent but crashed before publishing the root binding.
        # V3 correctly refuses that half-activated runtime, so derive the exact
        # runtime identity and enter the already-audited activation recovery
        # path.  Absence of that exact namespace preserves the original V3
        # failure rather than broadening public initialization into a repair
        # primitive for unrelated corruption.
        try:
            root_path, root_fd = owner_v3._resolve_owner_root(
                base_directory,
                create=False,
            )
        except (OSError, owner_v3.ConstructionK7H1SharedCapOwnerV3Error):
            raise
        try:
            root_metadata = os.fstat(root_fd)
            runtime = owner_v3._runtime_document(
                profile,
                source_manifest,
                rejection_gate.spec.gate_id,
                owner_root_realpath=str(root_path),
                owner_root_device=root_metadata.st_dev,
                owner_root_inode=root_metadata.st_ino,
            )
            runtime_id = runtime["h1_shared_cap_owner_v3_runtime_id"]
            activation_exists = (
                owner_v3._v4_wal_namespace_metadata(root_fd, runtime_id)
                is not None
            )
        finally:
            os.close(root_fd)
        if not activation_exists:
            raise
        historical = owner_v3.open_h1_shared_cap_owner_v3(
            root_path / runtime_id,
            expected_runtime_id=runtime_id,
            gate_directory=rejection_gate.gate_directory,
            _allow_v4_activation_recovery=True,
        )
    upgraded = owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(
        historical
    )
    return _wrap(upgraded)


def open_h1_shared_cap_owner_v4_wal(
    owner_directory: str | Path,
    *,
    expected_runtime_id: str,
    gate_directory: str | Path,
) -> H1SharedCapOwnerV4WalHandle:
    opened = owner_v3.open_h1_shared_cap_owner_v3(
        owner_directory,
        expected_runtime_id=expected_runtime_id,
        gate_directory=gate_directory,
        _allow_v4_activation_recovery=True,
    )
    activation_namespace = Path(opened.owner_root_realpath) / (
        owner_v3._v4_wal_directory_name(opened.runtime_id)
    )
    if (
        opened.pending_payload_wal_directory is None
        and not activation_namespace.exists()
    ):
        _fail("historical V3 runtime has no durable V4 WAL activation")
    return _wrap(
        owner_v3._enable_h1_shared_cap_owner_v4_pending_payload_wal(opened)
    )


def replay_h1_shared_cap_owner_v4_wal(
    handle: H1SharedCapOwnerV4WalHandle,
) -> dict[str, Any]:
    if type(handle) is not H1SharedCapOwnerV4WalHandle:
        _fail("V4 WAL replay requires one exact issuer-owned handle")
    result = dict(owner_v3.replay_h1_shared_cap_owner_v3(handle.owner))
    if result["pending_cursor"]["kind"] != "NOT_APPLICABLE":
        _fail("V4 WAL replay failed to converge its pending cursor")
    result.update(
        {
            "h1_shared_cap_owner_v4_wal_binding_id": handle.binding_id,
            "pending_payload_wal_required": True,
            "pending_payload_wal_replay_converged": True,
            "historical_v3_claim_relabelled": False,
            "no_event_recovery_complete": False,
            "production_execution_authority_present": False,
            "official_execution_allowed": False,
        }
    )
    return result


def reserve_h1_shared_cap_owner_v4_wal(
    handle: H1SharedCapOwnerV4WalHandle,
    **kwargs: Any,
) -> owner_v3.H1SharedReservationV3:
    if type(handle) is not H1SharedCapOwnerV4WalHandle:
        _fail("V4 WAL reservation requires one exact handle")
    return owner_v3.reserve_h1_shared_cap_owner_v3(handle.owner, **kwargs)


@contextmanager
def hold_h1_shared_cap_owner_v4_wal_side_effect(
    handle: H1SharedCapOwnerV4WalHandle,
    reservation: owner_v3.H1SharedReservationV3,
) -> Iterator[owner_v3.H1SharedSideEffectStartV3]:
    if type(handle) is not H1SharedCapOwnerV4WalHandle:
        _fail("V4 WAL side-effect guard requires one exact handle")
    with owner_v3.hold_h1_shared_cap_owner_v3_side_effect(
        handle.owner,
        reservation,
    ) as start:
        yield start


def settle_h1_shared_cap_owner_v4_wal(
    handle: H1SharedCapOwnerV4WalHandle,
    reservation: owner_v3.H1SharedReservationV3,
    **kwargs: Any,
) -> owner_v3.H1SharedSettlementResultV3:
    if type(handle) is not H1SharedCapOwnerV4WalHandle:
        _fail("V4 WAL settlement requires one exact handle")
    return owner_v3.settle_h1_shared_cap_owner_v3(
        handle.owner,
        reservation,
        **kwargs,
    )


__all__ = (
    "ConstructionK7H1SharedCapOwnerV4WalError",
    "H1SharedCapOwnerV4WalHandle",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PENDING_PAYLOAD_WAL_REQUIRED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "hold_h1_shared_cap_owner_v4_wal_side_effect",
    "initialize_h1_shared_cap_owner_v4_wal",
    "open_h1_shared_cap_owner_v4_wal",
    "replay_h1_shared_cap_owner_v4_wal",
    "reserve_h1_shared_cap_owner_v4_wal",
    "settle_h1_shared_cap_owner_v4_wal",
)
