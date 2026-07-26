"""V0-055 two-generation durable action-local recovery control.

The control deliberately composes existing narrow authorities instead of
retroactively changing them:

* a root-free first proof checkpoint is committed and consumed by a fresh
  model-only process;
* only after the failed result is replayed by the host is the exact,
  source-pinned V0-054B runner invoked;
* its single owner-bound ``M`` row is projected as non-authorizing durable
  provenance;
* a second fresh model-only process restores the verified first lower graph,
  performs the exact 10/8 continuation, and emits the strict ``N -> M``
  certificate;
* a 28-entry/18-active/root-free child checkpoint is committed and consumed
  by a third fresh process.

Detached bytes never become ground-transition authority.  Semantic replay,
durable loading, operational ground work, and evaluation replay remain
separate accounting lanes.  This registered construction makes no generic
persistence, sample-efficiency, total-work, or economics claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path
import tempfile
import threading
from typing import Any, Mapping

import acfqp.h2_action_local_semantic_switch_v1 as action_local
import acfqp.h2_durable_action_switch_transport_v1 as transport
from acfqp.h2_durable_action_local_recovery_pins_v1 import (
    EXPECTED_B_MODULE_SHA256,
    EXPECTED_B_RUNNER_SOURCE_SHA256,
    EXPECTED_CANONICAL_IDS,
    EXPECTED_ORCHESTRATOR_MODULE_SHA256,
    EXPECTED_TRANSPORT_MODULE_SHA256,
)
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
)
from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.19.0"
PROFILE_KEY = "lmb_h2_two_generation_durable_action_local_recovery_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_H2_TWO_GENERATION_DURABLE_"
    "ACTION_LOCAL_RECOVERY_CONTROL"
)

DOMAIN_TAGS = {
    "snapshot": "acfqp:h2-durable-action-local-directory-snapshot:v1",
    "failed_verification": (
        "acfqp:h2-durable-action-local-failed-proof-verification:v1"
    ),
    "ground_authorization": (
        "acfqp:h2-durable-action-local-ground-authorization:v1"
    ),
    "trace": "acfqp:h2-durable-action-local-recovery-trace:v1",
    "result": "acfqp:h2-durable-action-local-recovery-result:v1",
    "verification": (
        "acfqp:h2-durable-action-local-recovery-verification:v1"
    ),
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-055 content domains must be unique")

EXPECTED_EVENTS = (
    "PREGROUND_GUARD_INSTALLED",
    "C1_COMMITTED",
    "P1_FRESH_FAILED_PROOF_HOST_VERIFIED",
    "PREGROUND_GUARD_CLOSED_ZERO_CALLS",
    "GROUND_AUTHORIZATION_FROZEN",
    "SOURCE_PINNED_V0054B_STARTED",
    "SOURCE_OWNER_BOUND_ONE_ROW_COMPLETED",
    "OVERLAY_PROJECTION_COMMITTED",
    "P2_FRESH_FINAL_CONTINUATION_HOST_VERIFIED",
    "C2_COMMITTED",
    "P3_FRESH_C2_HOST_VERIFIED",
)

_RESULT_ISSUER = object()
_VERIFICATION_ISSUER = object()
_CANONICAL_B_RUNNER = (
    action_local.run_registered_h2_action_local_semantic_switch_v1
)
_CANONICAL_ACTION_LOCAL_REQUIRE = (
    action_local.require_action_local_semantic_switch_result_v1
)
_CANONICAL_BIND_RUNTIME_AUTHORITY = bind_runtime_authority_v1
_CANONICAL_REQUIRE_RUNTIME_AUTHORITY = require_runtime_authority_v1
_CANONICAL_LMB_STEP = action_local._CANONICAL_LMB_STEP
_CANONICAL_TRANSPORT_WRITE_C1 = (
    transport.write_durable_action_switch_c1_v1
)
_CANONICAL_TRANSPORT_LOAD_C1 = (
    transport.load_verified_durable_action_switch_c1_v1
)
_CANONICAL_TRANSPORT_RUN_P1 = (
    transport.run_durable_action_switch_p1_fresh_worker_v1
)
_CANONICAL_TRANSPORT_FREEZE_OVERLAY = (
    transport.freeze_durable_action_switch_overlay_projection_v1
)
_CANONICAL_TRANSPORT_WRITE_OVERLAY = (
    transport.write_durable_action_switch_overlay_projection_v1
)
_CANONICAL_TRANSPORT_LOAD_OVERLAY = (
    transport.load_durable_action_switch_overlay_projection_v1
)
_CANONICAL_TRANSPORT_RUN_P2 = (
    transport.run_durable_action_switch_p2_fresh_worker_v1
)
_CANONICAL_TRANSPORT_WRITE_C2 = (
    transport.write_durable_action_switch_c2_v1
)
_CANONICAL_TRANSPORT_LOAD_C2 = (
    transport.load_verified_durable_action_switch_c2_v1
)
_CANONICAL_TRANSPORT_RUN_P3 = (
    transport.run_durable_action_switch_c2_fresh_worker_v1
)
_CANONICAL_TRANSPORT_LAUNCH_WORKER = transport._launch_worker
_CANONICAL_TRANSPORT_WORKER_COMMAND = transport._worker_command
_CANONICAL_TRANSPORT_POPEN = transport.subprocess.Popen
_CANONICAL_TRANSPORT_BOUNDARY_ASSERT = (
    transport._assert_model_only_import_boundary
)
_CANONICAL_TRANSPORT_BOUNDARY_ALIAS = (
    transport._CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT
)
_CANONICAL_TRANSPORT_INTERNAL_AUTHORITIES = (
    transport._TRANSPORT_INTERNAL_AUTHORITIES
)
_CANONICAL_ACTION_INDEXED_SOURCE_SHA256 = (
    transport.EXPECTED_ACTION_INDEXED_SOURCE_SHA256
)
_TRANSPORT_AUTHORITIES = (
    (
        "write_durable_action_switch_c1_v1",
        _CANONICAL_TRANSPORT_WRITE_C1,
    ),
    (
        "load_verified_durable_action_switch_c1_v1",
        _CANONICAL_TRANSPORT_LOAD_C1,
    ),
    (
        "run_durable_action_switch_p1_fresh_worker_v1",
        _CANONICAL_TRANSPORT_RUN_P1,
    ),
    (
        "freeze_durable_action_switch_overlay_projection_v1",
        _CANONICAL_TRANSPORT_FREEZE_OVERLAY,
    ),
    (
        "write_durable_action_switch_overlay_projection_v1",
        _CANONICAL_TRANSPORT_WRITE_OVERLAY,
    ),
    (
        "load_durable_action_switch_overlay_projection_v1",
        _CANONICAL_TRANSPORT_LOAD_OVERLAY,
    ),
    (
        "run_durable_action_switch_p2_fresh_worker_v1",
        _CANONICAL_TRANSPORT_RUN_P2,
    ),
    (
        "write_durable_action_switch_c2_v1",
        _CANONICAL_TRANSPORT_WRITE_C2,
    ),
    (
        "load_verified_durable_action_switch_c2_v1",
        _CANONICAL_TRANSPORT_LOAD_C2,
    ),
    (
        "run_durable_action_switch_c2_fresh_worker_v1",
        _CANONICAL_TRANSPORT_RUN_P3,
    ),
    ("_launch_worker", _CANONICAL_TRANSPORT_LAUNCH_WORKER),
    ("_worker_command", _CANONICAL_TRANSPORT_WORKER_COMMAND),
    (
        "_assert_model_only_import_boundary",
        _CANONICAL_TRANSPORT_BOUNDARY_ASSERT,
    ),
    (
        "_CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT",
        _CANONICAL_TRANSPORT_BOUNDARY_ALIAS,
    ),
)
_PREGROUND_LOCK = threading.Lock()


class DurableActionLocalRecoveryInvariantViolation(ValueError):
    """The durable chain, live ordering, source, or claim boundary is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise DurableActionLocalRecoveryInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DurableActionLocalRecoveryInvariantViolation(
            f"{name} must be a full content ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DurableActionLocalRecoveryInvariantViolation(
            f"{name} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise DurableActionLocalRecoveryInvariantViolation(
            f"{name} must be exact"
        )
    return Fraction(value)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _file_sha256(path: Path) -> str:
    try:
        if not path.is_file() or path.is_symlink():
            raise OSError("not a regular source file")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise DurableActionLocalRecoveryInvariantViolation(
            "registered source cannot be read"
        ) from error


def _module_sha256(module: Any) -> str:
    source = Path(getattr(module, "__file__", "")).resolve()
    if source.suffix != ".py":
        raise DurableActionLocalRecoveryInvariantViolation(
            "registered module source path changed"
        )
    return _file_sha256(source)


def _callable_sha256(function: Any) -> str:
    try:
        return hashlib.sha256(
            inspect.getsource(function).encode("utf-8")
        ).hexdigest()
    except (OSError, TypeError) as error:
        raise DurableActionLocalRecoveryInvariantViolation(
            "registered callable source cannot be inspected"
        ) from error


def _assert_source_pins() -> None:
    try:
        runner_file = Path(
            inspect.getsourcefile(_CANONICAL_B_RUNNER) or ""
        ).resolve()
        module_file = Path(action_local.__file__).resolve()
    except (OSError, TypeError) as error:
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-054B runner source cannot be inspected"
        ) from error
    transport_authorities_changed = any(
        getattr(transport, name, None) is not authority
        or getattr(authority, "__module__", None)
        != "acfqp.h2_durable_action_switch_transport_v1"
        or Path(inspect.getsourcefile(authority) or "").resolve()
        != Path(transport.__file__).resolve()
        for name, authority in _TRANSPORT_AUTHORITIES
    )
    local_transport_authorities = (
        _CANONICAL_TRANSPORT_WRITE_C1,
        _CANONICAL_TRANSPORT_LOAD_C1,
        _CANONICAL_TRANSPORT_RUN_P1,
        _CANONICAL_TRANSPORT_FREEZE_OVERLAY,
        _CANONICAL_TRANSPORT_WRITE_OVERLAY,
        _CANONICAL_TRANSPORT_LOAD_OVERLAY,
        _CANONICAL_TRANSPORT_RUN_P2,
        _CANONICAL_TRANSPORT_WRITE_C2,
        _CANONICAL_TRANSPORT_LOAD_C2,
        _CANONICAL_TRANSPORT_RUN_P3,
        _CANONICAL_TRANSPORT_LAUNCH_WORKER,
        _CANONICAL_TRANSPORT_WORKER_COMMAND,
        _CANONICAL_TRANSPORT_BOUNDARY_ASSERT,
        _CANONICAL_TRANSPORT_BOUNDARY_ALIAS,
    )
    guard_authorities = globals().get("_GUARD_AUTHORITIES", ())
    orchestrator_authorities = globals().get(
        "_ORCHESTRATOR_INTERNAL_AUTHORITIES",
        (),
    )
    local_guard_authorities = (
        globals().get("_CANONICAL_GUARD_INSTALL"),
        globals().get("_CANONICAL_GUARD_CLOSE"),
        globals().get("_CANONICAL_GUARD_ABORT"),
    )
    if (
        action_local.run_registered_h2_action_local_semantic_switch_v1
        is not _CANONICAL_B_RUNNER
        or action_local.require_action_local_semantic_switch_result_v1
        is not _CANONICAL_ACTION_LOCAL_REQUIRE
        or getattr(_CANONICAL_B_RUNNER, "__module__", None)
        != "acfqp.h2_action_local_semantic_switch_v1"
        or getattr(_CANONICAL_B_RUNNER, "__qualname__", None)
        != "run_registered_h2_action_local_semantic_switch_v1"
        or runner_file != module_file
        or _callable_sha256(_CANONICAL_B_RUNNER)
        != EXPECTED_B_RUNNER_SOURCE_SHA256
        or _module_sha256(action_local) != EXPECTED_B_MODULE_SHA256
        or _module_sha256(transport) != EXPECTED_TRANSPORT_MODULE_SHA256
        or _file_sha256(Path(__file__).resolve())
        != EXPECTED_ORCHESTRATOR_MODULE_SHA256
        or transport_authorities_changed
        or local_transport_authorities
        != tuple(item[1] for item in _TRANSPORT_AUTHORITIES)
        or not guard_authorities
        or any(
            getattr(_PreGroundGuardV1, name, None) is not authority
            for name, authority in guard_authorities
        )
        or local_guard_authorities
        != tuple(item[1] for item in guard_authorities)
        or not orchestrator_authorities
        or any(
            globals().get(name) is not authority
            for name, authority in orchestrator_authorities
        )
        or transport.subprocess.Popen is not _CANONICAL_TRANSPORT_POPEN
        or transport._TRANSPORT_INTERNAL_AUTHORITIES
        is not _CANONICAL_TRANSPORT_INTERNAL_AUTHORITIES
        or transport.EXPECTED_ACTION_INDEXED_SOURCE_SHA256
        != _CANONICAL_ACTION_INDEXED_SOURCE_SHA256
        or globals().get("_assert_source_pins")
        is not globals().get("_CANONICAL_SOURCE_PIN_ASSERT")
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "registered V0-054B/transport source identity changed"
        )


_CANONICAL_SOURCE_PIN_ASSERT = _assert_source_pins


def _snapshot_id(root: Path, role: str) -> str:
    if not isinstance(root, Path) or not root.is_dir() or root.is_symlink():
        raise DurableActionLocalRecoveryInvariantViolation(
            f"{role} snapshot root is invalid"
        )
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise DurableActionLocalRecoveryInvariantViolation(
                f"{role} snapshot contains a symlink"
            )
        if path.is_dir():
            continue
        stat = path.stat()
        if not path.is_file() or stat.st_nlink != 1:
            raise DurableActionLocalRecoveryInvariantViolation(
                f"{role} snapshot contains a non-unique regular file"
            )
        payload = path.read_bytes()
        after = path.stat()
        if (stat.st_ino, stat.st_size, stat.st_mtime_ns) != (
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                f"{role} snapshot changed while being read"
            )
        rows.append(
            {
                "path": relative,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    if not rows:
        raise DurableActionLocalRecoveryInvariantViolation(
            f"{role} snapshot cannot be empty"
        )
    return _content_id(
        "snapshot",
        {
            "schema": "acfqp.h2_durable_action_local_directory_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "files": rows,
        },
    )


class _PreGroundGuardV1:
    """Reject every host ground transition before P1 is host-verified."""

    __slots__ = (
        "_installed",
        "_owns_lock",
        "_guard",
        "_attempted_calls",
    )

    def __init__(self) -> None:
        self._installed = False
        self._owns_lock = False
        self._guard: Any = None
        self._attempted_calls = 0

    @property
    def attempted_calls(self) -> int:
        return self._attempted_calls

    def install(self) -> None:
        if self._installed or not _PREGROUND_LOCK.acquire(blocking=False):
            raise DurableActionLocalRecoveryInvariantViolation(
                "pre-ground guard is concurrent or reentrant"
            )
        self._owns_lock = True
        try:
            action_local._assert_canonical_step_callable()
            if LMBKernel.step is not _CANONICAL_LMB_STEP:
                raise DurableActionLocalRecoveryInvariantViolation(
                    "ground step changed before C1"
                )

            def forbidden_step(
                _kernel: LMBKernel,
                _state: LMBState,
                _action: LMBAction,
            ) -> Any:
                self._attempted_calls += 1
                raise DurableActionLocalRecoveryInvariantViolation(
                    "ground transition attempted before failed-proof verification"
                )

            self._guard = forbidden_step
            LMBKernel.step = forbidden_step  # type: ignore[method-assign]
            self._installed = True
        except BaseException:
            self._owns_lock = False
            _PREGROUND_LOCK.release()
            raise

    def close_verified_zero(self) -> None:
        substitution = False
        if self._installed:
            substitution = LMBKernel.step is not self._guard
            LMBKernel.step = _CANONICAL_LMB_STEP  # type: ignore[method-assign]
            self._installed = False
        if self._owns_lock:
            self._owns_lock = False
            _PREGROUND_LOCK.release()
        if substitution or self._attempted_calls != 0:
            raise DurableActionLocalRecoveryInvariantViolation(
                "pre-ground guard observed a call or substitution"
            )

    def abort(self) -> None:
        if self._installed:
            LMBKernel.step = _CANONICAL_LMB_STEP  # type: ignore[method-assign]
            self._installed = False
        if self._owns_lock:
            self._owns_lock = False
            _PREGROUND_LOCK.release()


_CANONICAL_GUARD_INSTALL = _PreGroundGuardV1.install
_CANONICAL_GUARD_CLOSE = _PreGroundGuardV1.close_verified_zero
_CANONICAL_GUARD_ABORT = _PreGroundGuardV1.abort
_GUARD_AUTHORITIES = (
    ("install", _CANONICAL_GUARD_INSTALL),
    ("close_verified_zero", _CANONICAL_GUARD_CLOSE),
    ("abort", _CANONICAL_GUARD_ABORT),
)


@dataclass(frozen=True, slots=True)
class DurableFailedProofVerificationV1:
    protocol_id: str
    c1_commit_id: str
    c1_snapshot_id: str
    p1_attestation_id: str
    first_model_id: str
    query_id: str
    first_execution_id: str
    selected_action: str
    normalized_regret: Fraction
    certified: bool
    exact_host_replay: bool
    preground_transition_calls: int

    def __post_init__(self) -> None:
        for value in (
            self.protocol_id,
            self.c1_commit_id,
            self.c1_snapshot_id,
            self.p1_attestation_id,
            self.first_model_id,
            self.query_id,
            self.first_execution_id,
        ):
            _cid(value, "failed-proof verification identity")
        object.__setattr__(
            self,
            "normalized_regret",
            _fraction(self.normalized_regret, "failed normalized regret"),
        )
        if (
            self.selected_action != "N"
            or self.normalized_regret != Fraction(3, 4)
            or self.certified is not False
            or self.exact_host_replay is not True
            or self.preground_transition_calls != 0
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "host failed-proof verification changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_failed_proof_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "c1_commit_id": self.c1_commit_id,
            "c1_snapshot_id": self.c1_snapshot_id,
            "p1_attestation_id": self.p1_attestation_id,
            "first_model_id": self.first_model_id,
            "query_id": self.query_id,
            "first_execution_id": self.first_execution_id,
            "selected_action": self.selected_action,
            "normalized_regret": _fdoc(self.normalized_regret),
            "certified": self.certified,
            "exact_host_replay": self.exact_host_replay,
            "preground_transition_calls": self.preground_transition_calls,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("failed_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class DurableGroundAuthorizationV1:
    failed_verification_id: str
    c1_commit_id: str
    p1_attestation_id: str
    expected_first_execution_id: str
    expected_source_result_id: str
    target_state_id: str
    target_action_id: str
    target_ground_row_id: str
    b_runner_source_sha256: str
    b_module_sha256: str
    transport_module_sha256: str
    max_operational_ground_transition_calls: int = 1

    def __post_init__(self) -> None:
        for value in (
            self.failed_verification_id,
            self.c1_commit_id,
            self.p1_attestation_id,
            self.expected_first_execution_id,
            self.expected_source_result_id,
            self.target_state_id,
            self.target_action_id,
            self.target_ground_row_id,
            self.b_runner_source_sha256,
            self.b_module_sha256,
            self.transport_module_sha256,
        ):
            _cid(value, "durable ground authorization identity")
        if (
            self.expected_first_execution_id
            != action_local.EXPECTED_CANONICAL_IDS["first_execution"]
            or self.expected_source_result_id
            != action_local.EXPECTED_CANONICAL_IDS["result"]
            or self.target_state_id != action_local.EXPECTED_X1_STATE_ID
            or self.target_action_id
            != action_local.EXPECTED_GROUND_ACTION_IDS[
                action_local.GroundRowName.M
            ]
            or self.target_ground_row_id
            != action_local.EXPECTED_GROUND_ROW_IDS[
                action_local.GroundRowName.M
            ]
            or self.b_runner_source_sha256
            != EXPECTED_B_RUNNER_SOURCE_SHA256
            or self.b_module_sha256 != EXPECTED_B_MODULE_SHA256
            or self.transport_module_sha256
            != EXPECTED_TRANSPORT_MODULE_SHA256
            or self.max_operational_ground_transition_calls != 1
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "durable ground authorization changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_ground_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "failed_verification_id": self.failed_verification_id,
            "c1_commit_id": self.c1_commit_id,
            "p1_attestation_id": self.p1_attestation_id,
            "expected_first_execution_id": self.expected_first_execution_id,
            "expected_source_result_id": self.expected_source_result_id,
            "target_state_id": self.target_state_id,
            "target_action_id": self.target_action_id,
            "target_ground_row_id": self.target_ground_row_id,
            "b_runner_source_sha256": self.b_runner_source_sha256,
            "b_module_sha256": self.b_module_sha256,
            "transport_module_sha256": self.transport_module_sha256,
            "max_operational_ground_transition_calls": (
                self.max_operational_ground_transition_calls
            ),
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("ground_authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authorization_id": self.authorization_id}


@dataclass(frozen=True, slots=True)
class DurableRecoveryTraceV1:
    events: tuple[str, ...]
    failed_verification_id: str
    ground_authorization_id: str
    source_access_trace_id: str
    p1_attestation_id: str
    p2_continuation_id: str
    p3_attestation_id: str
    process_launches: int = 3
    preground_transition_calls: int = 0
    operational_ground_transition_calls: int = 1
    model_only_worker_ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.failed_verification_id,
            self.ground_authorization_id,
            self.source_access_trace_id,
            self.p1_attestation_id,
            self.p2_continuation_id,
            self.p3_attestation_id,
        ):
            _cid(value, "durable recovery trace identity")
        if (
            self.events != EXPECTED_EVENTS
            or self.process_launches != 3
            or self.preground_transition_calls != 0
            or self.operational_ground_transition_calls != 1
            or self.model_only_worker_ground_transition_calls != 0
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "durable recovery sequence changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_local_recovery_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "events": list(self.events),
            "failed_verification_id": self.failed_verification_id,
            "ground_authorization_id": self.ground_authorization_id,
            "source_access_trace_id": self.source_access_trace_id,
            "p1_attestation_id": self.p1_attestation_id,
            "p2_continuation_id": self.p2_continuation_id,
            "p3_attestation_id": self.p3_attestation_id,
            "process_launches": self.process_launches,
            "preground_transition_calls": self.preground_transition_calls,
            "operational_ground_transition_calls": (
                self.operational_ground_transition_calls
            ),
            "model_only_worker_ground_transition_calls": (
                self.model_only_worker_ground_transition_calls
            ),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class DurableRecoveryClaimLocksV1:
    registered_h2_two_generation_durable_action_local_recovery_claimed: bool = True
    root_free_lower_checkpoint_claimed: bool = True
    fresh_model_only_process_continuation_claimed: bool = True
    strict_policy_switch_preserved_claimed: bool = True
    detached_checkpoint_ground_provenance_claimed: bool = False
    v0054b_request_embeds_p1_attestation_claimed: bool = False
    generic_durable_persistence_claimed: bool = False
    crash_recovery_claimed: bool = False
    hostile_worker_security_claimed: bool = False
    cross_query_reuse_claimed: bool = False
    generic_h_gt_1_claimed: bool = False
    horizon_greater_than_two_claimed: bool = False
    generic_action_local_minimality_claimed: bool = False
    automatic_coordinate_invention_claimed: bool = False
    partial_dynamics_claimed: bool = False
    learned_dynamics_claimed: bool = False
    sample_efficiency_claimed: bool = False
    byte_savings_claimed: bool = False
    cpu_savings_claimed: bool = False
    wall_clock_savings_claimed: bool = False
    total_work_savings_claimed: bool = False
    native_compute_event_accounting_claimed: bool = False
    independent_algorithm_verifier_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    sample_efficiency_gate: str = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

    def __post_init__(self) -> None:
        if (
            self.registered_h2_two_generation_durable_action_local_recovery_claimed
            is not True
            or self.root_free_lower_checkpoint_claimed is not True
            or self.fresh_model_only_process_continuation_claimed is not True
            or self.strict_policy_switch_preserved_claimed is not True
            or any(
                value is not False
                for value in (
                    self.detached_checkpoint_ground_provenance_claimed,
                    self.v0054b_request_embeds_p1_attestation_claimed,
                    self.generic_durable_persistence_claimed,
                    self.crash_recovery_claimed,
                    self.hostile_worker_security_claimed,
                    self.cross_query_reuse_claimed,
                    self.generic_h_gt_1_claimed,
                    self.horizon_greater_than_two_claimed,
                    self.generic_action_local_minimality_claimed,
                    self.automatic_coordinate_invention_claimed,
                    self.partial_dynamics_claimed,
                    self.learned_dynamics_claimed,
                    self.sample_efficiency_claimed,
                    self.byte_savings_claimed,
                    self.cpu_savings_claimed,
                    self.wall_clock_savings_claimed,
                    self.total_work_savings_claimed,
                    self.native_compute_event_accounting_claimed,
                    self.independent_algorithm_verifier_claimed,
                    self.official_execution_allowed,
                )
            )
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate
            != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.sample_efficiency_gate != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "V0-055 claim locks changed"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            row: getattr(self, row)
            for row in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True)
class DurableActionLocalRecoveryResultV1:
    protocol: transport.DurableActionSwitchProtocolV1
    c1_commit_id: str
    c1_payload_id: str
    c1_snapshot_id: str
    p1_attestation: transport.DurableActionSwitchP1AttestationV1
    failed_verification: DurableFailedProofVerificationV1
    ground_authorization: DurableGroundAuthorizationV1
    source_result_id: str
    source_evidence_bundle_id: str
    source_overlay_build_id: str
    overlay_projection_id: str
    overlay_snapshot_id: str
    p2_continuation: transport.DurableActionSwitchP2ContinuationV1
    c2_commit_id: str
    c2_payload_id: str
    c2_snapshot_id: str
    p3_attestation: transport.DurableActionSwitchC2AttestationV1
    trace: DurableRecoveryTraceV1
    claim_locks: DurableRecoveryClaimLocksV1
    status: str = SUCCESS_STATUS
    _source_result: Any = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        exact_types = (
            (self.protocol, transport.DurableActionSwitchProtocolV1),
            (self.p1_attestation, transport.DurableActionSwitchP1AttestationV1),
            (self.failed_verification, DurableFailedProofVerificationV1),
            (self.ground_authorization, DurableGroundAuthorizationV1),
            (self.p2_continuation, transport.DurableActionSwitchP2ContinuationV1),
            (self.p3_attestation, transport.DurableActionSwitchC2AttestationV1),
            (self.trace, DurableRecoveryTraceV1),
            (self.claim_locks, DurableRecoveryClaimLocksV1),
        )
        if any(type(value) is not expected for value, expected in exact_types):
            raise DurableActionLocalRecoveryInvariantViolation(
                "V0-055 result rejects substituted artifacts"
            )
        self.protocol.__post_init__()
        self.p1_attestation.warm_replay.__post_init__()
        self.p1_attestation.__post_init__()
        self.failed_verification.__post_init__()
        self.ground_authorization.__post_init__()
        self.p2_continuation.__post_init__()
        self.p3_attestation.warm_replay.__post_init__()
        self.p3_attestation.__post_init__()
        self.trace.__post_init__()
        self.claim_locks.__post_init__()
        for value in (
            self.c1_commit_id,
            self.c1_payload_id,
            self.c1_snapshot_id,
            self.source_result_id,
            self.source_evidence_bundle_id,
            self.source_overlay_build_id,
            self.overlay_projection_id,
            self.overlay_snapshot_id,
            self.c2_commit_id,
            self.c2_payload_id,
            self.c2_snapshot_id,
        ):
            _cid(value, "V0-055 result identity")
        if type(self._source_result) is not action_local.ActionLocalSemanticSwitchResultV1:
            raise DurableActionLocalRecoveryInvariantViolation(
                "V0-055 result lost its live V0-054B source"
            )
        _CANONICAL_ACTION_LOCAL_REQUIRE(
            self._source_result
        )
        if (
            self.status != SUCCESS_STATUS
            or self.protocol.protocol_id
            != self.failed_verification.protocol_id
            or self.c1_commit_id != self.p1_attestation.c1_commit_id
            or self.c1_payload_id != self.p1_attestation.c1_payload_id
            or self.c1_snapshot_id
            != self.failed_verification.c1_snapshot_id
            or self.failed_verification.p1_attestation_id
            != self.p1_attestation.attestation_id
            or self.ground_authorization.failed_verification_id
            != self.failed_verification.verification_id
            or self.ground_authorization.c1_commit_id != self.c1_commit_id
            or self.ground_authorization.p1_attestation_id
            != self.p1_attestation.attestation_id
            or self.ground_authorization.expected_first_execution_id
            != self.p1_attestation.first_execution_id
            or self.ground_authorization.expected_source_result_id
            != self.source_result_id
            or self.source_result_id != self._source_result.result_id
            or self.source_result_id
            != self.p2_continuation.overlay_source_result_id
            or self.source_evidence_bundle_id
            != self._source_result.evidence_bundle.bundle_id
            or self.source_overlay_build_id
            != self._source_result.overlay_build.build_id
            or self.p1_attestation.first_execution_id
            != self._source_result.first_execution.execution_id
            or self.overlay_projection_id
            != self.p2_continuation.overlay_projection_id
            or self.p2_continuation.c1_commit_id != self.c1_commit_id
            or self.p2_continuation.first_action != "N"
            or self.p2_continuation.final_action != "M"
            or self.p2_continuation.final_certified is not True
            or self.p2_continuation.final_execution_document
            != self._source_result.final_execution.to_document()
            or self.p2_continuation.delta_document
            != self._source_result.overlay_build.action_indexed_delta.to_document()
            or self.p2_continuation.preexecution_invalidation_document
            != self._source_result.preexecution_invalidation.to_document()
            or self.p2_continuation.invalidation_document
            != self._source_result.invalidation.to_document()
            or self.p3_attestation.c2_commit_id != self.c2_commit_id
            or self.p3_attestation.warm_replay.payload_id
            != self.c2_payload_id
            or self.p3_attestation.c1_commit_id != self.c1_commit_id
            or self.p3_attestation.overlay_projection_id
            != self.overlay_projection_id
            or self.p3_attestation.continuation_id
            != self.p2_continuation.continuation_id
            or self.p3_attestation.selected_action != "M"
            or self.p3_attestation.final_certified is not True
            or self.trace.failed_verification_id
            != self.failed_verification.verification_id
            or self.trace.ground_authorization_id
            != self.ground_authorization.authorization_id
            or self.trace.p1_attestation_id
            != self.p1_attestation.attestation_id
            or self.trace.p2_continuation_id
            != self.p2_continuation.continuation_id
            or self.trace.p3_attestation_id
            != self.p3_attestation.attestation_id
            or self.trace.source_access_trace_id
            != self._source_result.access_trace.trace_id
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "V0-055 result chain changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_local_recovery_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status,
            "protocol": self.protocol.to_document(),
            "c1_commit_id": self.c1_commit_id,
            "c1_payload_id": self.c1_payload_id,
            "c1_snapshot_id": self.c1_snapshot_id,
            "p1_attestation": self.p1_attestation.to_document(),
            "failed_verification": self.failed_verification.to_document(),
            "ground_authorization": self.ground_authorization.to_document(),
            "source_result_id": self.source_result_id,
            "source_evidence_bundle_id": self.source_evidence_bundle_id,
            "source_overlay_build_id": self.source_overlay_build_id,
            "overlay_projection_id": self.overlay_projection_id,
            "overlay_snapshot_id": self.overlay_snapshot_id,
            "p2_continuation": self.p2_continuation.to_document(),
            "c2_commit_id": self.c2_commit_id,
            "c2_payload_id": self.c2_payload_id,
            "c2_snapshot_id": self.c2_snapshot_id,
            "p3_attestation": self.p3_attestation.to_document(),
            "trace": self.trace.to_document(),
            "claim_locks": self.claim_locks.to_document(),
        }

    @property
    def result_id(self) -> str:
        _CANONICAL_RESULT_REQUIRE(self)
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        _CANONICAL_RESULT_REQUIRE(self)
        return {**self._payload(), "result_id": self.result_id}


def require_durable_action_local_recovery_result_v1(
    result: DurableActionLocalRecoveryResultV1,
) -> DurableActionLocalRecoveryResultV1:
    if type(result) is not DurableActionLocalRecoveryResultV1:
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-055 result rejects substituted types"
        )
    try:
        _CANONICAL_REQUIRE_RUNTIME_AUTHORITY(
            result,
            issuer=_RESULT_ISSUER,
        )
    except ValueError as error:
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-055 result lacks its live runner authority"
        ) from error
    _CANONICAL_ACTION_LOCAL_REQUIRE(
        result._source_result
    )
    result.__post_init__()
    _assert_canonical_result_ids(result)
    return result


def _visible_canonical_result_ids(
    result: DurableActionLocalRecoveryResultV1,
) -> dict[str, str]:
    return {
        "protocol": result.protocol.protocol_id,
        "c1_payload": result.c1_payload_id,
        "c1_commit": result.c1_commit_id,
        "c1_snapshot": result.c1_snapshot_id,
        "p1_root_replay": (
            result.p1_attestation.warm_replay.restored_root_replay_id
        ),
        "p1_attestation": result.p1_attestation.attestation_id,
        "failed_proof_verification": (
            result.failed_verification.verification_id
        ),
        "ground_authorization": (
            result.ground_authorization.authorization_id
        ),
        "source_v0054b_result": result.source_result_id,
        "source_evidence_bundle": result.source_evidence_bundle_id,
        "source_overlay_build": result.source_overlay_build_id,
        "overlay_projection": result.overlay_projection_id,
        "overlay_snapshot": result.overlay_snapshot_id,
        "p2_continuation": result.p2_continuation.continuation_id,
        "c2_payload": result.c2_payload_id,
        "c2_commit": result.c2_commit_id,
        "c2_snapshot": result.c2_snapshot_id,
        "p3_root_replay": (
            result.p3_attestation.warm_replay.restored_root_replay_id
        ),
        "p3_attestation": result.p3_attestation.attestation_id,
        "recovery_trace": result.trace.trace_id,
        "campaign_result": _content_id("result", result._payload()),
    }


def _assert_canonical_result_ids(
    result: DurableActionLocalRecoveryResultV1,
) -> None:
    """Reject registered-fixture drift after literal IDs are frozen."""

    if not EXPECTED_CANONICAL_IDS:
        return
    actual = _visible_canonical_result_ids(result)
    missing = set(actual) - set(EXPECTED_CANONICAL_IDS)
    if missing or any(
        EXPECTED_CANONICAL_IDS[name] != value
        for name, value in actual.items()
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "registered V0-055 canonical result identities changed"
        )


_CANONICAL_RESULT_REQUIRE = (
    require_durable_action_local_recovery_result_v1
)


def _assert_source_matches_durable_prefix(
    source: action_local.ActionLocalSemanticSwitchResultV1,
    lease: transport.VerifiedDurableActionSwitchC1LeaseV1,
) -> None:
    _CANONICAL_ACTION_LOCAL_REQUIRE(source)
    if (
        source.first_model.dag_model.to_document()
        != lease.first_model.to_document()
        or source.query.to_document() != lease.query.to_document()
        or source.first_execution.to_document()
        != lease.first_execution.to_document()
        or source.first_execution.execution_id
        != action_local.EXPECTED_CANONICAL_IDS["first_execution"]
        or source.access_trace.total_ground_transition_calls != 1
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-054B source prefix/ground trace differs from verified C1"
        )


def _freeze_projection(
    source: action_local.ActionLocalSemanticSwitchResultV1,
) -> transport.DurableActionSwitchOverlayProjectionV1:
    row = source.evidence_bundle.row_evidence
    return _CANONICAL_TRANSPORT_FREEZE_OVERLAY(
        source_result_id=source.result_id,
        fixture_id=source.fixture.fixture_id,
        evidence_bundle_id=source.evidence_bundle.bundle_id,
        row_evidence_id=row.evidence_id,
        overlay_build_id=source.overlay_build.build_id,
        first_query_local_model_id=source.first_model.model_id,
        final_query_local_model_id=source.final_model.model_id,
        m_ground_row_id=row.ground_row_id,
        m_state_id=row.state_id,
        m_action_id=row.action_id,
    )


def _assert_projection_matches_live_source(
    projection: transport.DurableActionSwitchOverlayProjectionV1,
    source: action_local.ActionLocalSemanticSwitchResultV1,
    authorization: DurableGroundAuthorizationV1,
) -> None:
    if (
        type(projection)
        is not transport.DurableActionSwitchOverlayProjectionV1
        or type(source)
        is not action_local.ActionLocalSemanticSwitchResultV1
        or type(authorization) is not DurableGroundAuthorizationV1
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "overlay projection requires exact live authorities"
        )
    _CANONICAL_ACTION_LOCAL_REQUIRE(source)
    projection.__post_init__()
    authorization.__post_init__()
    row = source.evidence_bundle.row_evidence
    if (
        projection.source_result_id != source.result_id
        or projection.fixture_id != source.fixture.fixture_id
        or projection.evidence_bundle_id
        != source.evidence_bundle.bundle_id
        or projection.row_evidence_id != row.evidence_id
        or projection.overlay_build_id != source.overlay_build.build_id
        or projection.first_query_local_model_id
        != source.first_model.model_id
        or projection.final_query_local_model_id
        != source.final_model.model_id
        or projection.m_ground_row_id != row.ground_row_id
        or projection.m_ground_row_id
        != authorization.target_ground_row_id
        or projection.m_state_id != row.state_id
        or projection.m_state_id != authorization.target_state_id
        or projection.m_action_id != row.action_id
        or projection.m_action_id != authorization.target_action_id
        or projection.m_row_document
        != source.final_model.dag_model.row(
            action_local.GroundRowName.M
        ).to_document()
        or projection.exact_projected_row_count != 1
        or projection.source_ground_transition_calls != 1
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "durable projection differs from its live ground authority"
        )


def _run_registered_h2_durable_action_local_recovery_v1(
    store_root: Path,
) -> DurableActionLocalRecoveryResultV1:
    if not isinstance(store_root, Path):
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-055 store root must be a Path"
        )
    if store_root.exists():
        if (
            store_root.is_symlink()
            or not store_root.is_dir()
            or any(store_root.iterdir())
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "V0-055 requires a fresh empty store root"
            )
    else:
        store_root.mkdir(parents=True)
    c1_root = store_root / "c1"
    overlay_root = store_root / "overlay"
    c2_root = store_root / "c2"
    events: list[str] = []
    guard = _PreGroundGuardV1()
    source: action_local.ActionLocalSemanticSwitchResultV1 | None = None
    try:
        _CANONICAL_SOURCE_PIN_ASSERT()
        _CANONICAL_GUARD_INSTALL(guard)
        events.append("PREGROUND_GUARD_INSTALLED")
        c1_commit = _CANONICAL_TRANSPORT_WRITE_C1(c1_root)
        c1_lease = _CANONICAL_TRANSPORT_LOAD_C1(
            c1_root,
            c1_commit.commit_id,
        )
        c1_snapshot = _snapshot_id(c1_root, "C1")
        events.append("C1_COMMITTED")
        p1 = _CANONICAL_TRANSPORT_RUN_P1(
            c1_root,
            c1_commit.commit_id,
        )
        if _snapshot_id(c1_root, "C1") != c1_snapshot:
            raise DurableActionLocalRecoveryInvariantViolation(
                "C1 bytes changed during P1"
            )
        failed = DurableFailedProofVerificationV1(
            c1_lease.payload.protocol.protocol_id,
            c1_commit.commit_id,
            c1_snapshot,
            p1.attestation_id,
            p1.model_id,
            p1.query_id,
            p1.first_execution_id,
            p1.selected_action,
            p1.normalized_regret,
            p1.certified,
            True,
            guard.attempted_calls,
        )
        events.append("P1_FRESH_FAILED_PROOF_HOST_VERIFIED")
        _CANONICAL_GUARD_CLOSE(guard)
        events.append("PREGROUND_GUARD_CLOSED_ZERO_CALLS")
        _CANONICAL_SOURCE_PIN_ASSERT()
        ground_authorization = DurableGroundAuthorizationV1(
            failed.verification_id,
            c1_commit.commit_id,
            p1.attestation_id,
            p1.first_execution_id,
            action_local.EXPECTED_CANONICAL_IDS["result"],
            action_local.EXPECTED_X1_STATE_ID,
            action_local.EXPECTED_GROUND_ACTION_IDS[
                action_local.GroundRowName.M
            ],
            action_local.EXPECTED_GROUND_ROW_IDS[
                action_local.GroundRowName.M
            ],
            EXPECTED_B_RUNNER_SOURCE_SHA256,
            EXPECTED_B_MODULE_SHA256,
            EXPECTED_TRANSPORT_MODULE_SHA256,
        )
        events.append("GROUND_AUTHORIZATION_FROZEN")
        events.append("SOURCE_PINNED_V0054B_STARTED")
        source = _CANONICAL_B_RUNNER()
        _CANONICAL_ACTION_LOCAL_REQUIRE(source)
        _assert_source_matches_durable_prefix(source, c1_lease)
        events.append("SOURCE_OWNER_BOUND_ONE_ROW_COMPLETED")
        projection = _freeze_projection(source)
        _assert_projection_matches_live_source(
            projection,
            source,
            ground_authorization,
        )
        projection_id = (
            _CANONICAL_TRANSPORT_WRITE_OVERLAY(
                projection,
                overlay_root,
            )
        )
        overlay_snapshot = _snapshot_id(overlay_root, "OVERLAY")
        events.append("OVERLAY_PROJECTION_COMMITTED")
        p2 = _CANONICAL_TRANSPORT_RUN_P2(
            c1_root,
            c1_commit.commit_id,
            overlay_root,
            projection_id,
        )
        if (
            p2.final_execution_document
            != source.final_execution.to_document()
            or p2.delta_document
            != source.overlay_build.action_indexed_delta.to_document()
            or p2.preexecution_invalidation_document
            != source.preexecution_invalidation.to_document()
            or p2.invalidation_document != source.invalidation.to_document()
            or _snapshot_id(c1_root, "C1") != c1_snapshot
            or _snapshot_id(overlay_root, "OVERLAY") != overlay_snapshot
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "P2 continuation differs from live source or mutated inputs"
            )
        events.append("P2_FRESH_FINAL_CONTINUATION_HOST_VERIFIED")
        c2_commit = _CANONICAL_TRANSPORT_WRITE_C2(
            c1_lease,
            projection,
            p2,
            c2_root,
        )
        c2_lease = _CANONICAL_TRANSPORT_LOAD_C2(
            c2_root,
            c2_commit.commit_id,
            c1_lease,
            projection,
        )
        c2_snapshot = _snapshot_id(c2_root, "C2")
        events.append("C2_COMMITTED")
        p3 = _CANONICAL_TRANSPORT_RUN_P3(
            c1_root,
            c1_commit.commit_id,
            overlay_root,
            projection_id,
            c2_root,
            c2_commit.commit_id,
        )
        if (
            p3.c2_commit_id != c2_lease.commit.commit_id
            or _snapshot_id(c1_root, "C1") != c1_snapshot
            or _snapshot_id(overlay_root, "OVERLAY") != overlay_snapshot
            or _snapshot_id(c2_root, "C2") != c2_snapshot
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "P3 differs from C2 or mutated durable bytes"
            )
        events.append("P3_FRESH_C2_HOST_VERIFIED")
        trace = DurableRecoveryTraceV1(
            tuple(events),
            failed.verification_id,
            ground_authorization.authorization_id,
            source.access_trace.trace_id,
            p1.attestation_id,
            p2.continuation_id,
            p3.attestation_id,
        )
        result = DurableActionLocalRecoveryResultV1(
            c1_lease.payload.protocol,
            c1_commit.commit_id,
            c1_lease.payload.payload_id,
            c1_snapshot,
            p1,
            failed,
            ground_authorization,
            source.result_id,
            source.evidence_bundle.bundle_id,
            source.overlay_build.build_id,
            projection_id,
            overlay_snapshot,
            p2,
            c2_commit.commit_id,
            c2_lease.payload.payload_id,
            c2_snapshot,
            p3,
            trace,
            DurableRecoveryClaimLocksV1(),
            _source_result=source,
        )
        bound = _CANONICAL_BIND_RUNTIME_AUTHORITY(
            result,
            issuer=_RESULT_ISSUER,
        )
        _assert_canonical_result_ids(bound)
        if EXPECTED_CANONICAL_IDS and (
            EXPECTED_CANONICAL_IDS.get("c1_manifest")
            != c1_lease.manifest.manifest_id
            or EXPECTED_CANONICAL_IDS.get("c2_manifest")
            != c2_lease.manifest.manifest_id
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "registered V0-055 checkpoint manifest identities changed"
            )
        return bound
    except BaseException:
        _CANONICAL_GUARD_ABORT(guard)
        raise


_CANONICAL_ORCHESTRATOR_PRODUCER = (
    _run_registered_h2_durable_action_local_recovery_v1
)


def run_registered_h2_durable_action_local_recovery_v1(
    store_root: Path,
) -> DurableActionLocalRecoveryResultV1:
    """Run the exact C1/P1/ground/P2/C2/P3 V0-055 control."""

    _CANONICAL_SOURCE_PIN_ASSERT()
    return _CANONICAL_ORCHESTRATOR_PRODUCER(store_root)


@dataclass(frozen=True, slots=True)
class DurableActionLocalRecoveryVerificationV1:
    claimed_result_id: str
    replayed_result_id: str
    exact_document_match: bool
    original_store_unchanged: bool
    evaluation_lane_only: bool
    included_in_operational_work: bool
    same_implementation_replay: bool
    independent_algorithm: bool
    evaluation_ground_transition_calls: int
    evaluation_process_launches: int
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        _cid(self.claimed_result_id, "verification claimed result")
        _cid(self.replayed_result_id, "verification replayed result")
        if (
            self.claimed_result_id != self.replayed_result_id
            or self.exact_document_match is not True
            or self.original_store_unchanged is not True
            or self.evaluation_lane_only is not True
            or self.included_in_operational_work is not False
            or self.same_implementation_replay is not True
            or self.independent_algorithm is not False
            or self.evaluation_ground_transition_calls != 1
            or self.evaluation_process_launches != 3
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "V0-055 verification classification changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_local_recovery_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_result_id": self.claimed_result_id,
            "replayed_result_id": self.replayed_result_id,
            "exact_document_match": self.exact_document_match,
            "original_store_unchanged": self.original_store_unchanged,
            "evaluation_lane_only": self.evaluation_lane_only,
            "included_in_operational_work": self.included_in_operational_work,
            "same_implementation_replay": self.same_implementation_replay,
            "independent_algorithm": self.independent_algorithm,
            "evaluation_ground_transition_calls": (
                self.evaluation_ground_transition_calls
            ),
            "evaluation_process_launches": self.evaluation_process_launches,
        }

    @property
    def report_id(self) -> str:
        _CANONICAL_VERIFICATION_REQUIRE(self)
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        _CANONICAL_VERIFICATION_REQUIRE(self)
        return {**self._payload(), "report_id": self.report_id}


def require_durable_action_local_recovery_verification_v1(
    report: DurableActionLocalRecoveryVerificationV1,
) -> DurableActionLocalRecoveryVerificationV1:
    """Require the exact verifier-minted, owner-bound report."""

    if type(report) is not DurableActionLocalRecoveryVerificationV1:
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-055 verification rejects substituted types"
        )
    try:
        _CANONICAL_REQUIRE_RUNTIME_AUTHORITY(
            report,
            issuer=_VERIFICATION_ISSUER,
        )
    except ValueError as error:
        raise DurableActionLocalRecoveryInvariantViolation(
            "V0-055 verification lacks its live verifier authority"
        ) from error
    report.__post_init__()
    if (
        EXPECTED_CANONICAL_IDS
        and EXPECTED_CANONICAL_IDS.get("evaluation_replay_report")
        != _content_id("verification", report._payload())
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "registered V0-055 verification identity changed"
        )
    return report


_CANONICAL_VERIFICATION_REQUIRE = (
    require_durable_action_local_recovery_verification_v1
)


def verify_registered_h2_durable_action_local_recovery_v1(
    store_root: Path,
    claimed: DurableActionLocalRecoveryResultV1,
) -> DurableActionLocalRecoveryVerificationV1:
    """Verify original bytes, then rerun the whole chain in evaluation lane."""

    _CANONICAL_SOURCE_PIN_ASSERT()
    _CANONICAL_RESULT_REQUIRE(claimed)
    c1_root = store_root / "c1"
    overlay_root = store_root / "overlay"
    c2_root = store_root / "c2"
    original = (
        _snapshot_id(c1_root, "C1"),
        _snapshot_id(overlay_root, "OVERLAY"),
        _snapshot_id(c2_root, "C2"),
    )
    if original != (
        claimed.c1_snapshot_id,
        claimed.overlay_snapshot_id,
        claimed.c2_snapshot_id,
    ):
        raise DurableActionLocalRecoveryInvariantViolation(
            "claimed result differs from original durable bytes"
        )
    c1 = _CANONICAL_TRANSPORT_LOAD_C1(
        c1_root,
        claimed.c1_commit_id,
    )
    projection = _CANONICAL_TRANSPORT_LOAD_OVERLAY(
        overlay_root,
        claimed.overlay_projection_id,
    )
    _assert_projection_matches_live_source(
        projection,
        claimed._source_result,
        claimed.ground_authorization,
    )
    _CANONICAL_TRANSPORT_LOAD_C2(
        c2_root,
        claimed.c2_commit_id,
        c1,
        projection,
    )
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v0055-verifier-"
    ) as directory:
        replay_store = Path(directory) / "store"
        replayed = _CANONICAL_ORCHESTRATOR_PRODUCER(
            replay_store
        )
        replay_c1 = _CANONICAL_TRANSPORT_LOAD_C1(
            replay_store / "c1",
            replayed.c1_commit_id,
        )
        replay_projection = _CANONICAL_TRANSPORT_LOAD_OVERLAY(
            replay_store / "overlay",
            replayed.overlay_projection_id,
        )
        _CANONICAL_TRANSPORT_LOAD_C2(
            replay_store / "c2",
            replayed.c2_commit_id,
            replay_c1,
            replay_projection,
        )
        _assert_projection_matches_live_source(
            replay_projection,
            replayed._source_result,
            replayed.ground_authorization,
        )
        if (
            _snapshot_id(replay_store / "c1", "C1")
            != replayed.c1_snapshot_id
            or _snapshot_id(replay_store / "overlay", "OVERLAY")
            != replayed.overlay_snapshot_id
            or _snapshot_id(replay_store / "c2", "C2")
            != replayed.c2_snapshot_id
        ):
            raise DurableActionLocalRecoveryInvariantViolation(
                "evaluation replay did not materialize its claimed store"
            )
    after = (
        _snapshot_id(c1_root, "C1"),
        _snapshot_id(overlay_root, "OVERLAY"),
        _snapshot_id(c2_root, "C2"),
    )
    exact = replayed.to_document() == claimed.to_document()
    report = DurableActionLocalRecoveryVerificationV1(
        claimed.result_id,
        replayed.result_id,
        exact,
        after == original,
        True,
        False,
        True,
        False,
        1,
        3,
    )
    return _CANONICAL_BIND_RUNTIME_AUTHORITY(
        report,
        issuer=_VERIFICATION_ISSUER,
    )


_ORCHESTRATOR_INTERNAL_AUTHORITIES = (
    ("bind_runtime_authority_v1", bind_runtime_authority_v1),
    ("require_runtime_authority_v1", require_runtime_authority_v1),
    (
        "_CANONICAL_BIND_RUNTIME_AUTHORITY",
        _CANONICAL_BIND_RUNTIME_AUTHORITY,
    ),
    (
        "_CANONICAL_REQUIRE_RUNTIME_AUTHORITY",
        _CANONICAL_REQUIRE_RUNTIME_AUTHORITY,
    ),
    (
        "_CANONICAL_ACTION_LOCAL_REQUIRE",
        _CANONICAL_ACTION_LOCAL_REQUIRE,
    ),
    ("_content_id", _content_id),
    ("_file_sha256", _file_sha256),
    ("_module_sha256", _module_sha256),
    ("_callable_sha256", _callable_sha256),
    ("_assert_source_pins", _assert_source_pins),
    ("_CANONICAL_SOURCE_PIN_ASSERT", _CANONICAL_SOURCE_PIN_ASSERT),
    ("_snapshot_id", _snapshot_id),
    (
        "_assert_source_matches_durable_prefix",
        _assert_source_matches_durable_prefix,
    ),
    ("_freeze_projection", _freeze_projection),
    (
        "_assert_projection_matches_live_source",
        _assert_projection_matches_live_source,
    ),
    ("_visible_canonical_result_ids", _visible_canonical_result_ids),
    ("_assert_canonical_result_ids", _assert_canonical_result_ids),
    (
        "require_durable_action_local_recovery_result_v1",
        require_durable_action_local_recovery_result_v1,
    ),
    ("_CANONICAL_RESULT_REQUIRE", _CANONICAL_RESULT_REQUIRE),
    (
        "require_durable_action_local_recovery_verification_v1",
        require_durable_action_local_recovery_verification_v1,
    ),
    (
        "_CANONICAL_VERIFICATION_REQUIRE",
        _CANONICAL_VERIFICATION_REQUIRE,
    ),
    (
        "_run_registered_h2_durable_action_local_recovery_v1",
        _run_registered_h2_durable_action_local_recovery_v1,
    ),
    (
        "_CANONICAL_ORCHESTRATOR_PRODUCER",
        _CANONICAL_ORCHESTRATOR_PRODUCER,
    ),
)


__all__ = [
    "CONTRACT_VERSION",
    "DurableActionLocalRecoveryInvariantViolation",
    "DurableActionLocalRecoveryResultV1",
    "DurableActionLocalRecoveryVerificationV1",
    "DurableFailedProofVerificationV1",
    "DurableGroundAuthorizationV1",
    "DurableRecoveryClaimLocksV1",
    "DurableRecoveryTraceV1",
    "EXPECTED_B_MODULE_SHA256",
    "EXPECTED_B_RUNNER_SOURCE_SHA256",
    "EXPECTED_CANONICAL_IDS",
    "EXPECTED_ORCHESTRATOR_MODULE_SHA256",
    "EXPECTED_TRANSPORT_MODULE_SHA256",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "require_durable_action_local_recovery_result_v1",
    "require_durable_action_local_recovery_verification_v1",
    "run_registered_h2_durable_action_local_recovery_v1",
    "verify_registered_h2_durable_action_local_recovery_v1",
]
