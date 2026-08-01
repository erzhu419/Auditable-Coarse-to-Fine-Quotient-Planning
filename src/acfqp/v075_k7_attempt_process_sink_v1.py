"""Process-local launch-event sink for the V0-075 K7 attempt window.

The runtime hook is intentionally a zero-argument edge emitter.  Only the
fixed atomic-pidfd runtime function may report that one native process launch
just happened; even code running inside an active window cannot invoke the
hook from another call site.  The fixed site cannot inject a count, totals
dictionary, CounterRecord, or WorkVector.  With no active supervisor session
the hook is a no-op returning ``False``; an installed but stale, cross-thread,
or otherwise crossed binding fails closed.

This module owns only the process/context-local transport capability.  The
mutable attempt session and immutable raw journal live in
``v075_k7_attempt_process_supervisor_v1``.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import InitVar, dataclass
import hashlib
import os
from pathlib import Path
import sys
from threading import RLock, get_ident
from typing import Any, Iterator, NoReturn
import weakref


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_k7_attempt_process_sink_v1"

_BINDING_ISSUER = object()
_EVENT_ISSUER = object()
_REGISTRY_LOCK = RLock()
_CALLSITE_LOCK = RLock()


class V075K7AttemptProcessSinkV1Error(ValueError):
    """The launch sink was nested, crossed, stale, or otherwise misused."""


def _fail(message: str) -> NoReturn:
    raise V075K7AttemptProcessSinkV1Error(message)


@dataclass(frozen=True, slots=True)
class _AttemptProcessSinkBindingV1:
    """Opaque registration issued only to the attempt supervisor."""

    _issuer: InitVar[object]
    receiver_id: int
    owner_process_id: int
    owner_thread_id: int
    _receiver_ref: weakref.ReferenceType[Any]

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BINDING_ISSUER
            or type(self.receiver_id) is not int
            or self.receiver_id <= 0
            or type(self.owner_process_id) is not int
            or self.owner_process_id <= 0
            or type(self.owner_thread_id) is not int
            or self.owner_thread_id <= 0
            or type(self._receiver_ref) is not weakref.ReferenceType
        ):
            _fail("attempt-process sink binding is caller-minted or malformed")


@dataclass(frozen=True, slots=True)
class _PinnedRuntimeCallsiteV1:
    _issuer: InitVar[object]
    function: Any
    code: Any
    globals_mapping: dict[str, Any]
    module_name: str
    function_name: str
    source_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BINDING_ISSUER
            or not callable(self.function)
            or self.code is not self.function.__code__
            or self.globals_mapping is not self.function.__globals__
            or self.module_name != "acfqp.v075_k7_atomic_pidfd_runtime_v1"
            or self.function_name != "run_v075_k7_atomic_pidfd_runtime_v1"
            or self.function.__module__ != self.module_name
            or self.function.__name__ != self.function_name
            or type(self.source_path) is not str
            or not self.source_path
            or type(self.source_sha256) is not str
            or len(self.source_sha256) != 64
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
        ):
            _fail("attempt-process runtime callsite pin is malformed")

    def provenance(self) -> dict[str, Any]:
        return {
            "runtime_source_module": self.module_name,
            "runtime_source_symbol": self.function_name,
            "runtime_source_path": self.source_path,
            "runtime_source_sha256": self.source_sha256,
            "runtime_source_byte_count": self.source_byte_count,
            "runtime_code_object_pinned": True,
            "runtime_globals_mapping_pinned": True,
        }


_REGISTERED: dict[int, _AttemptProcessSinkBindingV1] = {}
_PINNED_RUNTIME_CALLSITE: _PinnedRuntimeCallsiteV1 | None = None
_ACTIVE_SINK: ContextVar[_AttemptProcessSinkBindingV1 | None] = ContextVar(
    "acfqp_v075_k7_attempt_process_sink_v1",
    default=None,
)


def _register_v075_k7_attempt_process_receiver_v1(
    receiver: object,
) -> _AttemptProcessSinkBindingV1:
    """Register one supervisor-owned receiver.

    This private API is deliberately separate from the runtime-facing hook.
    The receiver must remain alive and expose the supervisor's private event
    method.  Registration itself emits no launch event.
    """

    method = getattr(receiver, "_record_process_launch_from_sink_v1", None)
    if not callable(method):
        _fail("attempt-process receiver lacks the exact sink event method")
    try:
        receiver_ref = weakref.ref(receiver)
    except TypeError as error:
        raise V075K7AttemptProcessSinkV1Error(
            "attempt-process receiver must support weak references"
        ) from error
    receiver_id = id(receiver)
    with _REGISTRY_LOCK:
        current = _REGISTERED.get(receiver_id)
        if current is not None and current._receiver_ref() is not None:
            _fail("attempt-process receiver is already registered")
        binding = _AttemptProcessSinkBindingV1(
            _BINDING_ISSUER,
            receiver_id,
            os.getpid(),
            get_ident(),
            receiver_ref,
        )
        _REGISTERED[receiver_id] = binding
    return binding


def _register_v075_k7_attempt_process_runtime_callsite_v1(
    function: Any,
) -> None:
    """Pin the original runtime function exactly once during module import."""

    global _PINNED_RUNTIME_CALLSITE
    if (
        not callable(function)
        or getattr(function, "__module__", None)
        != "acfqp.v075_k7_atomic_pidfd_runtime_v1"
        or getattr(function, "__name__", None)
        != "run_v075_k7_atomic_pidfd_runtime_v1"
    ):
        _fail("foreign function cannot register as the runtime launch site")
    globals_mapping = function.__globals__
    if (
        globals_mapping.get("__name__") != function.__module__
        or globals_mapping.get("run_v075_k7_atomic_pidfd_runtime_v1")
        is not function
    ):
        _fail("runtime launch-site registration is not module-initialization exact")
    source_path_value = globals_mapping.get("__file__")
    if type(source_path_value) is not str or not source_path_value:
        _fail("runtime launch-site registration lacks a source path")
    source_path = Path(source_path_value).resolve()
    try:
        raw = source_path.read_bytes()
    except OSError as error:
        raise V075K7AttemptProcessSinkV1Error(
            "runtime launch-site source snapshot is unreadable"
        ) from error
    candidate = _PinnedRuntimeCallsiteV1(
        _BINDING_ISSUER,
        function,
        function.__code__,
        globals_mapping,
        function.__module__,
        function.__name__,
        str(source_path),
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )
    with _CALLSITE_LOCK:
        if _PINNED_RUNTIME_CALLSITE is not None:
            _fail("runtime launch site was already pinned")
        _PINNED_RUNTIME_CALLSITE = candidate


def _unregister_v075_k7_attempt_process_receiver_v1(
    binding: _AttemptProcessSinkBindingV1,
) -> None:
    if type(binding) is not _AttemptProcessSinkBindingV1:
        _fail("attempt-process unregister requires the issued binding")
    with _REGISTRY_LOCK:
        if _REGISTERED.get(binding.receiver_id) is not binding:
            _fail("attempt-process receiver binding is stale")
        del _REGISTERED[binding.receiver_id]


def _assert_live_binding(
    binding: _AttemptProcessSinkBindingV1,
) -> object:
    if type(binding) is not _AttemptProcessSinkBindingV1:
        _fail("attempt-process activation requires the issued binding")
    if os.getpid() != binding.owner_process_id:
        _fail("attempt-process sink activation crossed a process boundary")
    if get_ident() != binding.owner_thread_id:
        _fail("attempt-process sink activation crossed a thread boundary")
    with _REGISTRY_LOCK:
        if _REGISTERED.get(binding.receiver_id) is not binding:
            _fail("attempt-process sink binding is closed or stale")
        receiver = binding._receiver_ref()
    if receiver is None or id(receiver) != binding.receiver_id:
        _fail("attempt-process sink receiver no longer exists")
    return receiver


@contextmanager
def activate_v075_k7_attempt_process_sink_v1(
    binding: _AttemptProcessSinkBindingV1,
) -> Iterator[None]:
    """Install exactly one attempt launch sink in the current context."""

    _assert_live_binding(binding)
    if _ACTIVE_SINK.get() is not None:
        _fail("nested attempt-process sink activation is forbidden")
    token = _ACTIVE_SINK.set(binding)
    try:
        yield
    finally:
        _ACTIVE_SINK.reset(token)


def record_v075_k7_attempt_process_launch_v1() -> bool:
    """Emit one native process-launch edge into the active attempt session.

    ``False`` means that this runtime is executing outside an accounted attempt
    window.  A fork-inherited context is also treated as inactive: the child
    may never mutate the parent's journal.  Other crossed/stale active bindings
    indicate a protocol error and raise.
    """

    binding = _ACTIVE_SINK.get()
    if binding is None:
        return False
    if os.getpid() != binding.owner_process_id:
        return False
    caller = sys._getframe(1)  # noqa: SLF001 - deliberate call-site authority
    with _CALLSITE_LOCK:
        runtime_callsite = _PINNED_RUNTIME_CALLSITE
    if (
        runtime_callsite is None
        or caller.f_code is not runtime_callsite.code
        or caller.f_globals is not runtime_callsite.globals_mapping
        or caller.f_globals.get("__name__") != runtime_callsite.module_name
    ):
        _fail("attempt-process launch emission came from a foreign call site")
    if get_ident() != binding.owner_thread_id:
        _fail("attempt-process launch emission crossed a thread boundary")
    receiver = _assert_live_binding(binding)
    method = getattr(receiver, "_record_process_launch_from_sink_v1", None)
    if not callable(method):  # pragma: no cover - guarded at registration
        _fail("attempt-process receiver event method disappeared")
    method(_EVENT_ISSUER, runtime_callsite)
    return True


__all__ = (
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V075K7AttemptProcessSinkV1Error",
    "activate_v075_k7_attempt_process_sink_v1",
    "record_v075_k7_attempt_process_launch_v1",
)
