"""Process-isolated, parent-owned batched-observer transport for V0-075.

The private observer and its signing authority remain in the parent.  One
fresh, isolated Python process is launched per logical occurrence.  The child
receives framed canonical public JSON only and can ask for observations only
by issuing a typed batch intent against a frozen row catalogue.  The parent
validates the intent, advances the exact batched observer, and returns the
canonical signed public aggregate.

This module deliberately has a stdlib-only import surface.  Parent-only
authorities are imported lazily after the child entrypoint has been ruled out.
Consequently ``python -I <this-file> --acfqp-v075-child`` does not import a
kernel, observer session, private environment, signer, or historical runtime.

Only a construction program is registered here.  A later production planner
must receive a new, content-addressed registration; arbitrary callbacks,
pickled callables, and caller-selected commands are never accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_parent_owned_batched_observer_ipc_v1"
PRODUCTION_EXECUTION_STATUS = (
    "NOT_READY_REAL_ROUTE_NATIVE_PLANNER_AND_PRODUCTION_BINDINGS_ABSENT"
)
CONSTRUCTION_FIXTURE_ONLY = True

MAX_FRAME_BYTES = 16 * 1024 * 1024
MAX_CHILD_STDERR_BYTES = 256 * 1024
MAX_ROWS = 65_536
MAX_BATCHES = 65_536
MAX_DRAW_CAP = 25_000_000
DEFAULT_PROCESS_TIMEOUT_SECONDS = 60

_FRAME_WIDTH = 8
_CHILD_ARG = "--acfqp-v075-child"

_DOMAINS = {
    "program": "acfqp:v075-ipc-child-program-registration:v1",
    "row": "acfqp:v075-ipc-row-catalogue-entry:v1",
    "profile": "acfqp:v075-ipc-occurrence-profile:v1",
    "launch": "acfqp:v075-ipc-public-launch:v1",
    "intent": "acfqp:v075-ipc-batch-intent:v1",
    "response": "acfqp:v075-ipc-batch-response:v1",
    "journal_entry": "acfqp:v075-ipc-journal-entry:v1",
    "journal": "acfqp:v075-ipc-journal:v1",
    "batch_closure": "acfqp:v075-ipc-signed-batch-occurrence-closure:v1",
    "batch_closure_verification": (
        "acfqp:v075-ipc-batch-occurrence-closure-verification:v1"
    ),
    "scientific": "acfqp:v075-ipc-scientific-payload:v1",
    "work": "acfqp:v075-ipc-actual-work:v1",
    "result": "acfqp:v075-ipc-occurrence-result:v1",
}

_INITIAL_JOURNAL_HASH = hashlib.sha256(
    b"acfqp:v075-ipc-journal-initial:v1"
).hexdigest()
_BATCH_CLOSURE_SIGNING_DOMAIN = (
    b"acfqp:v075-ipc-batch-occurrence-closure-signing:v1"
)


class V075BatchedObserverIPCInvariantViolation(ValueError):
    """A transport, identity, catalogue, accounting, or payload invariant failed."""


def _fail(message: str) -> None:
    raise V075BatchedObserverIPCInvariantViolation(message)


def _canonical_bytes(value: Any) -> bytes:
    """Serialize the deliberately small IPC JSON value language."""

    def validate(item: Any) -> None:
        if item is None or type(item) in {bool, int, str}:
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                _fail("canonical IPC objects require string keys")
            for child in item.values():
                validate(child)
            return
        _fail("IPC payload contains a non-JSON runtime object")

    validate(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V075BatchedObserverIPCInvariantViolation(str(error)) from error


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("canonical IPC JSON contains a duplicate key")
        result[key] = value
    return result


def _load_canonical(raw: bytes, *, field_name: str) -> Any:
    if type(raw) is not bytes or not raw or len(raw) > MAX_FRAME_BYTES:
        _fail(f"{field_name} is empty, mistyped, or over the frame cap")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: _fail(
                f"non-finite JSON constant {token!r} is forbidden"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        if isinstance(error, V075BatchedObserverIPCInvariantViolation):
            raise
        raise V075BatchedObserverIPCInvariantViolation(
            f"{field_name} is not canonical JSON: {error}"
        ) from error
    if _canonical_bytes(value) != raw:
        _fail(f"{field_name} is not canonical JSON")
    return value


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _DOMAINS[role].encode("utf-8")
    except KeyError as error:  # pragma: no cover - internal programming error
        raise RuntimeError("unknown V0-075 IPC content domain") from error
    return hashlib.sha256(
        domain + b"\x00" + _canonical_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field_name} must be one lowercase SHA-256 content ID")
    return value


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or any(
            not (
                character.isupper()
                or character.isdigit()
                or character == "_"
            )
            for character in value
        )
    ):
        _fail(f"{field_name} must be one bounded uppercase token")
    return value


def _exact_mapping(
    value: Any,
    keys: set[str],
    *,
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field_name} fields are missing, unknown, or malformed")
    return value


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("IPC accounting requires exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _parse_fraction(value: Any, field_name: str) -> Fraction:
    item = _exact_mapping(
        value,
        {"numerator", "denominator"},
        field_name=field_name,
    )
    if (
        type(item["numerator"]) is not int
        or type(item["denominator"]) is not int
        or item["denominator"] <= 0
    ):
        _fail(f"{field_name} is not an exact rational")
    result = Fraction(item["numerator"], item["denominator"])
    if _fraction_document(result) != item:
        _fail(f"{field_name} is not reduced")
    return result


class V075IPCChildProgramV1(str, Enum):
    CONSTRUCTION_SCRIPTED_AGGREGATE = (
        "CONSTRUCTION_SCRIPTED_AGGREGATE_V1"
    )


class V075IPCConstructionBehaviorV1(str, Enum):
    HONEST = "HONEST"
    GAP_FIRST_INTENT = "ATTACK_GAP_FIRST_INTENT"
    REPLAY_FIRST_INTENT = "ATTACK_REPLAY_FIRST_INTENT"
    TRANSPLANT_FIRST_INTENT = "ATTACK_TRANSPLANT_FIRST_INTENT"
    TAMPER_FINAL_PAYLOAD = "ATTACK_TAMPER_FINAL_PAYLOAD"
    CRASH_BEFORE_INTENT = "ATTACK_CRASH_BEFORE_INTENT"


@dataclass(frozen=True, slots=True)
class V075IPCChildProgramRegistrationV1:
    program: V075IPCChildProgramV1
    module_sha256: str
    argv: tuple[str, ...]
    construction_only: bool = True
    arbitrary_callback_allowed: bool = False
    pickle_transport_allowed: bool = False
    _registration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.module_sha256, "IPC child module digest")
        if (
            type(self.program) is not V075IPCChildProgramV1
            or self.argv != (_CHILD_ARG,)
            or self.construction_only is not True
            or self.arbitrary_callback_allowed is not False
            or self.pickle_transport_allowed is not False
        ):
            _fail("IPC child program registration is not the frozen allowlist")
        object.__setattr__(
            self,
            "_registration_id",
            _hash("program", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_ipc_child_program_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "program": self.program.value,
            "module_sha256": self.module_sha256,
            "argv": list(self.argv),
            "construction_only": self.construction_only,
            "arbitrary_callback_allowed": self.arbitrary_callback_allowed,
            "pickle_transport_allowed": self.pickle_transport_allowed,
            "production_ready": False,
        }

    @property
    def registration_id(self) -> str:
        return self._registration_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registration_id": self.registration_id}


def registered_v075_ipc_child_program_v1(
) -> V075IPCChildProgramRegistrationV1:
    module_bytes = Path(__file__).read_bytes()
    return V075IPCChildProgramRegistrationV1(
        V075IPCChildProgramV1.CONSTRUCTION_SCRIPTED_AGGREGATE,
        hashlib.sha256(module_bytes).hexdigest(),
        (_CHILD_ARG,),
    )


@dataclass(frozen=True, slots=True)
class V075IPCRowCatalogueEntryV1:
    stream_identity: Any = field(repr=False)
    accepted_draw_cap: int
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Exact-type validation is parent-only and lazily imports public,
        # law-free graph identity code.  The child path never executes this.
        from acfqp import v075_public_graph_semantics_v1 as graph

        if (
            type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or type(self.accepted_draw_cap) is not int
            or not 0 < self.accepted_draw_cap <= MAX_DRAW_CAP
        ):
            _fail("IPC row catalogue entry is foreign or over cap")
        object.__setattr__(
            self,
            "_entry_id",
            _hash("row", self._payload()),
        )

    @property
    def stream_id(self) -> str:
        return self.stream_identity.stream_id

    def _payload(self) -> dict[str, Any]:
        stream = self.stream_identity
        return {
            "schema": "acfqp.v075_ipc_row_catalogue_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": stream.target_tape_namespace_id,
            "context_id": stream.context_id,
            "row_binding_id": stream.row_binding_id,
            "catalogue_id": stream.catalogue_id,
            "stream_id": stream.stream_id,
            "support_epoch_id": stream.support_epoch_id,
            "observer_epoch_index": stream.observer_epoch_index,
            "lane": stream.lane.value,
            "arm": stream.arm,
            "accepted_draw_cap": self.accepted_draw_cap,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stream_identity": self.stream_identity.to_document(),
            "entry_id": self.entry_id,
        }


@dataclass(frozen=True, slots=True)
class V075IPCScriptStepV1:
    stream_id: str
    accepted_draw_count: int

    def __post_init__(self) -> None:
        _cid(self.stream_id, "IPC script stream")
        if (
            type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
            or self.accepted_draw_count > MAX_DRAW_CAP
        ):
            _fail("IPC script draw count is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "accepted_draw_count": self.accepted_draw_count,
        }


@dataclass(frozen=True, slots=True)
class V075IPCOccurrenceProfileV1:
    occurrence_id: str
    context_id: str
    arm: str
    row_catalogue: tuple[V075IPCRowCatalogueEntryV1, ...]
    script: tuple[V075IPCScriptStepV1, ...]
    program_registration: V075IPCChildProgramRegistrationV1
    behavior: V075IPCConstructionBehaviorV1
    max_batches: int
    max_total_accepted_draws: int
    process_timeout_seconds: int
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "IPC occurrence")
        _cid(self.context_id, "IPC context")
        _token(self.arm, "IPC arm")
        if (
            type(self.row_catalogue) is not tuple
            or not self.row_catalogue
            or len(self.row_catalogue) > MAX_ROWS
            or any(
                type(entry) is not V075IPCRowCatalogueEntryV1
                for entry in self.row_catalogue
            )
            or len({entry.stream_id for entry in self.row_catalogue})
            != len(self.row_catalogue)
            or any(
                entry.stream_identity.context_id != self.context_id
                or entry.stream_identity.arm != self.arm
                for entry in self.row_catalogue
            )
            or len(
                {
                    (
                        entry.stream_identity.target_tape_namespace_id,
                        entry.stream_identity.support_epoch_id,
                        entry.stream_identity.observer_epoch_index,
                        entry.stream_identity.lane.value,
                    )
                    for entry in self.row_catalogue
                }
            )
            != 1
            or type(self.script) is not tuple
            or not self.script
            or len(self.script) > MAX_BATCHES
            or any(type(step) is not V075IPCScriptStepV1 for step in self.script)
            or type(self.program_registration)
            is not V075IPCChildProgramRegistrationV1
            or self.program_registration
            != registered_v075_ipc_child_program_v1()
            or type(self.behavior) is not V075IPCConstructionBehaviorV1
            or type(self.max_batches) is not int
            or not 0 < len(self.script) <= self.max_batches <= MAX_BATCHES
            or type(self.max_total_accepted_draws) is not int
            or not 0 < self.max_total_accepted_draws <= MAX_DRAW_CAP
            or type(self.process_timeout_seconds) is not int
            or not 0 < self.process_timeout_seconds <= 3_600
        ):
            _fail("IPC occurrence profile is malformed or authority-mixed")
        catalogue = {entry.stream_id: entry for entry in self.row_catalogue}
        totals: dict[str, int] = {}
        for step in self.script:
            if step.stream_id not in catalogue:
                _fail("IPC script references a stream outside the row catalogue")
            totals[step.stream_id] = (
                totals.get(step.stream_id, 0) + step.accepted_draw_count
            )
        if (
            sum(totals.values()) > self.max_total_accepted_draws
            or any(
                count > catalogue[stream_id].accepted_draw_cap
                for stream_id, count in totals.items()
            )
        ):
            _fail("IPC script exceeds a frozen stream or occurrence cap")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        first = self.row_catalogue[0].stream_identity
        return {
            "schema": "acfqp.v075_ipc_occurrence_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": first.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "support_epoch_id": first.support_epoch_id,
            "observer_epoch_index": first.observer_epoch_index,
            "lane": first.lane.value,
            "row_entry_ids": [entry.entry_id for entry in self.row_catalogue],
            "script": [step.to_document() for step in self.script],
            "program_registration_id": (
                self.program_registration.registration_id
            ),
            "construction_behavior": self.behavior.value,
            "max_batches": self.max_batches,
            "max_total_accepted_draws": self.max_total_accepted_draws,
            "process_timeout_seconds": self.process_timeout_seconds,
            "one_fresh_process_per_occurrence": True,
            "parent_owns_observer_and_signer": True,
            "canonical_bytes_only": True,
            "pickle_transport_allowed": False,
            "arbitrary_callback_allowed": False,
            "production_ready": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_catalogue": [
                entry.to_document() for entry in self.row_catalogue
            ],
            "program_registration": (
                self.program_registration.to_document()
            ),
            "profile_id": self.profile_id,
        }


def freeze_v075_construction_ipc_occurrence_profile_v1(
    *,
    occurrence_id: str,
    streams: Iterable[Any],
    script: Iterable[tuple[str, int]],
    accepted_draw_cap_by_stream: Mapping[str, int],
    behavior: V075IPCConstructionBehaviorV1 = (
        V075IPCConstructionBehaviorV1.HONEST
    ),
    max_batches: int = MAX_BATCHES,
    max_total_accepted_draws: int = MAX_DRAW_CAP,
    process_timeout_seconds: int = DEFAULT_PROCESS_TIMEOUT_SECONDS,
) -> V075IPCOccurrenceProfileV1:
    from acfqp import v075_public_graph_semantics_v1 as graph

    stream_tuple = tuple(streams)
    if (
        not stream_tuple
        or any(
            type(stream) is not graph.V075TransitionStreamIdentityV1
            for stream in stream_tuple
        )
        or type(accepted_draw_cap_by_stream) is not dict
        or set(accepted_draw_cap_by_stream)
        != {stream.stream_id for stream in stream_tuple}
    ):
        _fail("construction IPC profile requires one exact capped stream set")
    entries = tuple(
        V075IPCRowCatalogueEntryV1(
            stream,
            accepted_draw_cap_by_stream[stream.stream_id],
        )
        for stream in stream_tuple
    )
    steps = tuple(V075IPCScriptStepV1(*item) for item in script)
    return V075IPCOccurrenceProfileV1(
        occurrence_id,
        stream_tuple[0].context_id,
        stream_tuple[0].arm,
        entries,
        steps,
        registered_v075_ipc_child_program_v1(),
        behavior,
        max_batches,
        max_total_accepted_draws,
        process_timeout_seconds,
    )


def _launch_document(profile: V075IPCOccurrenceProfileV1) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_ipc_public_launch.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile.profile_id,
        "occurrence_id": profile.occurrence_id,
        "context_id": profile.context_id,
        "arm": profile.arm,
        "program": profile.program_registration.program.value,
        "construction_behavior": profile.behavior.value,
        "row_catalogue": [
            {
                "entry_id": entry.entry_id,
                **entry._payload(),
            }
            for entry in profile.row_catalogue
        ],
        "script": [step.to_document() for step in profile.script],
        "max_batches": profile.max_batches,
        "max_total_accepted_draws": profile.max_total_accepted_draws,
        "private_session_serialized": False,
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_signer_serialized": False,
        "private_kernel_serialized": False,
        "callback_serialized": False,
        "pickle_transport_used": False,
    }
    return {**payload, "launch_id": _hash("launch", payload)}


def _intent_payload(
    *,
    profile: Mapping[str, Any],
    sequence: int,
    stream: Mapping[str, Any],
    accepted_draw_start: int,
    accepted_draw_count: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_ipc_batch_intent.v1",
        "schema_version": SCHEMA_VERSION,
        "sequence": sequence,
        "profile_id": profile["profile_id"],
        "occurrence_id": profile["occurrence_id"],
        "context_id": profile["context_id"],
        "arm": profile["arm"],
        "row_entry_id": stream["entry_id"],
        "row_binding_id": stream["row_binding_id"],
        "catalogue_id": stream["catalogue_id"],
        "stream_id": stream["stream_id"],
        "support_epoch_id": stream["support_epoch_id"],
        "observer_epoch_index": stream["observer_epoch_index"],
        "lane": stream["lane"],
        "accepted_draw_start": accepted_draw_start,
        "accepted_draw_count": accepted_draw_count,
        "accepted_draw_cap": stream["accepted_draw_cap"],
        "request_nonce_present": False,
        "private_material_present": False,
    }


def _make_intent(
    *,
    launch: Mapping[str, Any],
    sequence: int,
    stream: Mapping[str, Any],
    accepted_draw_start: int,
    accepted_draw_count: int,
) -> dict[str, Any]:
    payload = _intent_payload(
        profile=launch,
        sequence=sequence,
        stream=stream,
        accepted_draw_start=accepted_draw_start,
        accepted_draw_count=accepted_draw_count,
    )
    return {**payload, "intent_id": _hash("intent", payload)}


def _validate_intent(
    *,
    raw: bytes,
    profile: V075IPCOccurrenceProfileV1,
    expected_sequence: int,
    next_start_by_stream: Mapping[str, int],
    total_draws: int,
) -> tuple[dict[str, Any], V075IPCRowCatalogueEntryV1]:
    item = _exact_mapping(
        _load_canonical(raw, field_name="child batch intent"),
        {
            "schema",
            "schema_version",
            "sequence",
            "profile_id",
            "occurrence_id",
            "context_id",
            "arm",
            "row_entry_id",
            "row_binding_id",
            "catalogue_id",
            "stream_id",
            "support_epoch_id",
            "observer_epoch_index",
            "lane",
            "accepted_draw_start",
            "accepted_draw_count",
            "accepted_draw_cap",
            "request_nonce_present",
            "private_material_present",
            "intent_id",
        },
        field_name="child batch intent",
    )
    if (
        item["schema"] != "acfqp.v075_ipc_batch_intent.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["sequence"] != expected_sequence
        or item["profile_id"] != profile.profile_id
        or item["occurrence_id"] != profile.occurrence_id
        or item["context_id"] != profile.context_id
        or item["arm"] != profile.arm
        or item["request_nonce_present"] is not False
        or item["private_material_present"] is not False
    ):
        _fail("child intent is stale, transplanted, nonmonotonic, or private")
    catalogue = {entry.stream_id: entry for entry in profile.row_catalogue}
    entry = catalogue.get(item["stream_id"])
    if entry is None:
        _fail("child intent references an unregistered stream")
    stream = entry.stream_identity
    expected_fields = {
        "row_entry_id": entry.entry_id,
        "row_binding_id": stream.row_binding_id,
        "catalogue_id": stream.catalogue_id,
        "support_epoch_id": stream.support_epoch_id,
        "observer_epoch_index": stream.observer_epoch_index,
        "lane": stream.lane.value,
        "accepted_draw_cap": entry.accepted_draw_cap,
    }
    if any(item[key] != value for key, value in expected_fields.items()):
        _fail("child intent changed its row, support epoch, lane, or cap")
    payload = dict(item)
    claimed_id = payload.pop("intent_id")
    if _cid(claimed_id, "child intent") != _hash("intent", payload):
        _fail("child intent content identity does not replay")
    expected_start = next_start_by_stream.get(entry.stream_id, 1)
    count = item["accepted_draw_count"]
    if (
        type(item["accepted_draw_start"]) is not int
        or item["accepted_draw_start"] != expected_start
        or type(count) is not int
        or count <= 0
        or item["accepted_draw_start"] + count - 1
        > entry.accepted_draw_cap
        or total_draws + count > profile.max_total_accepted_draws
    ):
        _fail("child intent is gapped, overlapping, replayed, or over cap")
    return item, entry


def _response_document(
    *,
    sequence: int,
    intent_id: str,
    batch_document: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_ipc_batch_response.v1",
        "schema_version": SCHEMA_VERSION,
        "sequence": sequence,
        "intent_id": intent_id,
        "request_id": batch_document["request_id"],
        "batch_id": batch_document["batch_id"],
        "signed_public_batch": dict(batch_document),
        "private_session_serialized": False,
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_signer_serialized": False,
        "private_kernel_serialized": False,
        "pickle_transport_used": False,
    }
    return {**payload, "response_id": _hash("response", payload)}


def _validate_child_batch_response(
    *,
    raw: bytes,
    intent: Mapping[str, Any],
    expected_sequence: int,
) -> dict[str, Any]:
    item = _exact_mapping(
        _load_canonical(raw, field_name="parent batch response"),
        {
            "schema",
            "schema_version",
            "sequence",
            "intent_id",
            "request_id",
            "batch_id",
            "signed_public_batch",
            "private_session_serialized",
            "private_law_serialized",
            "private_salt_serialized",
            "private_signer_serialized",
            "private_kernel_serialized",
            "pickle_transport_used",
            "response_id",
        },
        field_name="parent batch response",
    )
    payload = dict(item)
    claimed_id = payload.pop("response_id")
    if (
        item["schema"] != "acfqp.v075_ipc_batch_response.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["sequence"] != expected_sequence
        or item["intent_id"] != intent["intent_id"]
        or any(
            item[key] is not False
            for key in (
                "private_session_serialized",
                "private_law_serialized",
                "private_salt_serialized",
                "private_signer_serialized",
                "private_kernel_serialized",
                "pickle_transport_used",
            )
        )
        or _cid(claimed_id, "IPC batch response") != _hash("response", payload)
    ):
        _fail("parent batch response is stale, private, or identity-invalid")
    batch = item["signed_public_batch"]
    if type(batch) is not dict:
        _fail("parent response lacks one signed public batch")
    for key, expected in (
        ("request_id", item["request_id"]),
        ("batch_id", item["batch_id"]),
        ("context_id", intent["context_id"]),
        ("arm", intent["arm"]),
        ("row_binding_id", intent["row_binding_id"]),
        ("stream_id", intent["stream_id"]),
        ("observer_epoch_index", intent["observer_epoch_index"]),
        ("accepted_draw_start", intent["accepted_draw_start"]),
        ("accepted_draw_count", intent["accepted_draw_count"]),
        ("accepted_draw_cap", intent["accepted_draw_cap"]),
    ):
        if batch.get(key) != expected:
            _fail("signed public batch differs from the frozen child intent")
    outcomes = batch.get("outcomes")
    if type(outcomes) is not list or not outcomes:
        _fail("signed public batch has no outcome aggregates")
    total_count = 0
    failure_count = 0
    terminal_count = 0
    reward_sum = Fraction(0)
    prior_outcome_id = ""
    for outcome in outcomes:
        if type(outcome) is not dict:
            _fail("signed public batch outcome is not an object")
        outcome_id = _cid(outcome.get("outcome_id"), "public outcome")
        count = outcome.get("count")
        if (
            outcome_id <= prior_outcome_id
            or type(count) is not int
            or count <= 0
        ):
            _fail("public outcome ordering/count is invalid")
        prior_outcome_id = outcome_id
        item_reward = _parse_fraction(
            outcome.get("reward_sum"),
            "public outcome reward sum",
        )
        total_count += count
        reward_sum += item_reward
        failure_count += count if outcome.get("failure") is True else 0
        terminal_count += count if outcome.get("terminal") is True else 0
    if (
        total_count != intent["accepted_draw_count"]
        or failure_count != batch.get("failure_count")
        or terminal_count != batch.get("terminal_count")
        or reward_sum
        != _parse_fraction(batch.get("reward_sum"), "public batch reward sum")
        or batch.get("private_law_serialized") is not False
        or batch.get("private_salt_serialized") is not False
        or batch.get("private_kernel_serialized") is not False
        or batch.get("individual_random_words_serialized") is not False
    ):
        _fail("signed public aggregate does not reconcile")
    return item


def _aggregate_scientific_payload(
    *,
    profile_id: str,
    occurrence_id: str,
    context_id: str,
    arm: str,
    batch_documents: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    batches = tuple(batch_documents)
    outcomes: dict[str, dict[str, Any]] = {}
    reward = Fraction(0)
    failures = 0
    terminals = 0
    draws = 0
    for batch in batches:
        draws += batch["accepted_draw_count"]
        failures += batch["failure_count"]
        terminals += batch["terminal_count"]
        reward += _parse_fraction(batch["reward_sum"], "batch reward")
        for outcome in batch["outcomes"]:
            key = outcome["outcome_id"]
            prior = outcomes.get(key)
            if prior is None:
                prior = {
                    "outcome_id": key,
                    "next_ranks": outcome["next_ranks"],
                    "failure": outcome["failure"],
                    "terminal": outcome["terminal"],
                    "spawn_cell": outcome["spawn_cell"],
                    "spawn_rank": outcome["spawn_rank"],
                    "realized_row_reward": outcome[
                        "realized_row_reward"
                    ],
                    "count": 0,
                    "reward_sum": Fraction(0),
                }
                outcomes[key] = prior
            prior["count"] += outcome["count"]
            prior["reward_sum"] += _parse_fraction(
                outcome["reward_sum"],
                "outcome reward",
            )
    aggregate_outcomes = []
    for key in sorted(outcomes):
        item = dict(outcomes[key])
        item["reward_sum"] = _fraction_document(item["reward_sum"])
        aggregate_outcomes.append(item)
    payload = {
        "schema": "acfqp.v075_ipc_scientific_payload.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "context_id": context_id,
        "arm": arm,
        "completed_batch_count": len(batches),
        "accepted_draw_count": draws,
        "batch_ids": [batch["batch_id"] for batch in batches],
        "aggregate_outcomes": aggregate_outcomes,
        "reward_sum": _fraction_document(reward),
        "failure_count": failures,
        "terminal_count": terminals,
        "scientific_payload_excludes_transport_diagnostics": True,
    }
    return {**payload, "scientific_payload_id": _hash("scientific", payload)}


def _write_frame(stream: Any, raw: bytes) -> None:
    if type(raw) is not bytes or not raw or len(raw) > MAX_FRAME_BYTES:
        _fail("outgoing IPC frame is empty, mistyped, or over cap")
    stream.write(len(raw).to_bytes(_FRAME_WIDTH, "big") + raw)
    stream.flush()


def _read_exact_fd(fd: int, count: int, deadline: float) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        timeout = deadline - time.monotonic()
        if timeout <= 0:
            _fail("child IPC frame timed out")
        readable, _, _ = select.select([fd], [], [], timeout)
        if not readable:
            _fail("child IPC frame timed out")
        chunk = os.read(fd, remaining)
        if not chunk:
            _fail("child IPC stream closed before a complete frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_frame_fd(fd: int, deadline: float) -> bytes:
    header = _read_exact_fd(fd, _FRAME_WIDTH, deadline)
    size = int.from_bytes(header, "big")
    if not 0 < size <= MAX_FRAME_BYTES:
        _fail("child IPC frame length is zero or over cap")
    return _read_exact_fd(fd, size, deadline)


def _read_frame_child(stream: Any) -> bytes:
    header = stream.read(_FRAME_WIDTH)
    if len(header) != _FRAME_WIDTH:
        _fail("parent IPC stream closed before one frame header")
    size = int.from_bytes(header, "big")
    if not 0 < size <= MAX_FRAME_BYTES:
        _fail("parent IPC frame length is zero or over cap")
    raw = stream.read(size)
    if len(raw) != size:
        _fail("parent IPC stream closed before one complete frame")
    return raw


def _journal_append(
    entries: list["V075IPCJournalEntryV1"],
    *,
    direction: str,
    message_kind: str,
    raw: bytes,
    message_id: str,
) -> None:
    prior = entries[-1].entry_hash if entries else _INITIAL_JOURNAL_HASH
    entries.append(
        V075IPCJournalEntryV1(
            len(entries) + 1,
            direction,
            message_kind,
            _cid(message_id, "journal message"),
            hashlib.sha256(raw).hexdigest(),
            len(raw),
            prior,
        )
    )


@dataclass(frozen=True, slots=True)
class V075IPCJournalEntryV1:
    sequence: int
    direction: str
    message_kind: str
    message_id: str
    message_sha256: str
    byte_count: int
    prior_entry_hash: str
    _entry_hash: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.message_id, "journal message"),
            (self.message_sha256, "journal message bytes"),
            (self.prior_entry_hash, "prior journal entry"),
        ):
            _cid(value, name)
        if (
            type(self.sequence) is not int
            or self.sequence <= 0
            or self.direction not in {"CHILD_TO_PARENT", "PARENT_TO_CHILD"}
            or self.message_kind not in {
                "BATCH_INTENT",
                "BATCH_RESPONSE",
                "FINAL_SCIENTIFIC_PAYLOAD",
            }
            or type(self.byte_count) is not int
            or not 0 < self.byte_count <= MAX_FRAME_BYTES
        ):
            _fail("IPC journal entry is malformed")
        object.__setattr__(
            self,
            "_entry_hash",
            _hash("journal_entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_ipc_journal_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "sequence": self.sequence,
            "direction": self.direction,
            "message_kind": self.message_kind,
            "message_id": self.message_id,
            "message_sha256": self.message_sha256,
            "byte_count": self.byte_count,
            "prior_entry_hash": self.prior_entry_hash,
        }

    @property
    def entry_hash(self) -> str:
        return self._entry_hash

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_hash": self.entry_hash}


def _journal_payload(
    *,
    profile_id: str,
    occurrence_id: str,
    entries: tuple[V075IPCJournalEntryV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_ipc_journal.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "entry_hashes": [entry.entry_hash for entry in entries],
        "entry_count": len(entries),
        "final_entry_hash": (
            entries[-1].entry_hash if entries else _INITIAL_JOURNAL_HASH
        ),
    }


def _batch_closure_payload(
    *,
    profile_id: str,
    occurrence_id: str,
    context_id: str,
    arm: str,
    session_public_id: str,
    authority_binding_id: str,
    underlying_session_closure_id: str,
    terminal_code: str,
    scientific_payload_id: str | None,
    journal_id: str,
    final_journal_entry_hash: str,
    batch_ids: tuple[str, ...],
    request_ids: tuple[str, ...],
    stream_ids: tuple[str, ...],
    sequence_verification_ids: tuple[str, ...],
    public_verification_ids: tuple[str, ...],
    private_replay_verification_ids: tuple[str, ...],
    accepted_draw_count: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_ipc_signed_batch_occurrence_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "context_id": context_id,
        "arm": arm,
        "observer_session_public_id": session_public_id,
        "observer_open_binding_id": authority_binding_id,
        "underlying_session_closure_id": underlying_session_closure_id,
        "underlying_per_draw_record_count": 0,
        "batched_closure_is_authoritative": True,
        "terminal_code": terminal_code,
        "scientific_payload_id": scientific_payload_id,
        "ipc_journal_id": journal_id,
        "final_ipc_journal_entry_hash": final_journal_entry_hash,
        "batch_ids": list(batch_ids),
        "request_ids": list(request_ids),
        "stream_ids": list(stream_ids),
        "sequence_verification_ids": list(sequence_verification_ids),
        "public_verification_ids": list(public_verification_ids),
        "private_replay_verification_ids": list(
            private_replay_verification_ids
        ),
        "batch_count": len(batch_ids),
        "accepted_draw_count": accepted_draw_count,
        "all_batches_publicly_verified": True,
        "all_stream_prefixes_contiguous": True,
        "every_batch_private_replayed": True,
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_kernel_serialized": False,
    }


@dataclass(frozen=True, slots=True)
class V075SignedBatchOccurrenceClosureV1:
    profile_id: str
    occurrence_id: str
    context_id: str
    arm: str
    authority_binding: Any = field(repr=False)
    session_public_id: str
    underlying_session_closure_id: str
    terminal_code: str
    scientific_payload_id: str | None
    journal_id: str
    final_journal_entry_hash: str
    batch_ids: tuple[str, ...]
    request_ids: tuple[str, ...]
    stream_ids: tuple[str, ...]
    sequence_verification_ids: tuple[str, ...]
    public_verification_ids: tuple[str, ...]
    private_replay_verification_ids: tuple[str, ...]
    accepted_draw_count: int
    observer_signature_hex: str
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import v075_private_observer_boundary_v1 as observer
        from acfqp import v075_public_campaign_authority_v1 as public

        for value, name in (
            (self.profile_id, "batch closure profile"),
            (self.occurrence_id, "batch closure occurrence"),
            (self.context_id, "batch closure context"),
            (self.session_public_id, "batch closure session"),
            (
                self.underlying_session_closure_id,
                "underlying session closure",
            ),
            (self.journal_id, "batch closure IPC journal"),
            (self.final_journal_entry_hash, "final IPC journal entry"),
        ):
            _cid(value, name)
        if self.scientific_payload_id is not None:
            _cid(self.scientific_payload_id, "batch closure scientific payload")
        for values, name in (
            (self.batch_ids, "batch closure batch"),
            (self.request_ids, "batch closure request"),
            (self.stream_ids, "batch closure stream"),
            (
                self.sequence_verification_ids,
                "batch closure sequence verification",
            ),
            (
                self.public_verification_ids,
                "batch closure public verification",
            ),
            (
                self.private_replay_verification_ids,
                "batch closure private replay",
            ),
        ):
            if type(values) is not tuple:
                _fail(f"{name} identities are not one tuple")
            for value in values:
                _cid(value, name)
        if (
            type(self.authority_binding)
            is not observer.V075ObserverOpenAuthorityBindingV1
            or self.authority_binding.scope
            is not observer.V075ObserverOpenAuthorityScopeV1.CONSTRUCTION_ONLY
            or self.terminal_code
            not in {
                "CONSTRUCTION_FIXTURE_PASS",
                "PROTOCOL_FAILURE",
                "PROCESS_FAILURE",
            }
            or (self.terminal_code == "CONSTRUCTION_FIXTURE_PASS")
            != (self.scientific_payload_id is not None)
            or len(self.batch_ids) != len(self.request_ids)
            or len(self.batch_ids) != len(self.public_verification_ids)
            or len(self.batch_ids)
            != len(self.private_replay_verification_ids)
            or len(set(self.batch_ids)) != len(self.batch_ids)
            or len(set(self.request_ids)) != len(self.request_ids)
            or len(self.stream_ids) != len(self.sequence_verification_ids)
            or len(set(self.stream_ids)) != len(self.stream_ids)
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count < 0
            or type(self.observer_signature_hex) is not str
            or not self.observer_signature_hex
        ):
            _fail("signed batch occurrence closure is malformed")
        message = (
            _BATCH_CLOSURE_SIGNING_DOMAIN
            + b"\x00"
            + _canonical_bytes(self._payload())
        )
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                self.authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
            signature_hex=self.observer_signature_hex,
        ):
            _fail("batch occurrence closure signature is invalid")
        object.__setattr__(
            self,
            "_closure_id",
            _hash(
                "batch_closure",
                {
                    **self._payload(),
                    "observer_signature_hex": self.observer_signature_hex,
                    "observer_signature_verified": True,
                },
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return _batch_closure_payload(
            profile_id=self.profile_id,
            occurrence_id=self.occurrence_id,
            context_id=self.context_id,
            arm=self.arm,
            session_public_id=self.session_public_id,
            authority_binding_id=self.authority_binding.binding_id,
            underlying_session_closure_id=(
                self.underlying_session_closure_id
            ),
            terminal_code=self.terminal_code,
            scientific_payload_id=self.scientific_payload_id,
            journal_id=self.journal_id,
            final_journal_entry_hash=self.final_journal_entry_hash,
            batch_ids=self.batch_ids,
            request_ids=self.request_ids,
            stream_ids=self.stream_ids,
            sequence_verification_ids=self.sequence_verification_ids,
            public_verification_ids=self.public_verification_ids,
            private_replay_verification_ids=(
                self.private_replay_verification_ids
            ),
            accepted_draw_count=self.accepted_draw_count,
        )

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observer_open_binding": self.authority_binding.to_document(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "closure_id": self.closure_id,
        }


_BATCH_CLOSURE_VERIFIER_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOccurrenceClosureVerificationV1:
    _issuer: object = field(repr=False)
    closure_id: str
    profile_id: str
    occurrence_id: str
    replayed_batch_count: int
    replayed_stream_count: int
    replayed_private_verification_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.closure_id, "verified batch closure"),
            (self.profile_id, "verified batch closure profile"),
            (self.occurrence_id, "verified batch closure occurrence"),
        ):
            _cid(value, name)
        if any(
            type(value) is not int or value < 0
            for value in (
                self.replayed_batch_count,
                self.replayed_stream_count,
                self.replayed_private_verification_count,
            )
        ) or self._issuer is not _BATCH_CLOSURE_VERIFIER_ISSUER:
            _fail("batch closure verification counts are malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("batch_closure_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_ipc_batch_occurrence_closure_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "profile_id": self.profile_id,
            "occurrence_id": self.occurrence_id,
            "replayed_batch_count": self.replayed_batch_count,
            "replayed_stream_count": self.replayed_stream_count,
            "replayed_private_verification_count": (
                self.replayed_private_verification_count
            ),
            "verification_result": (
                "SIGNED_COMPLETE_BATCH_LINEAGE_VERIFIED"
            ),
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _public_verification_id_from_private_replayed_batch(
    item: Any,
) -> str:
    """Recover the public-verifier ID already exercised by private replay.

    ``verify_*_private_replay`` invokes the public semantic verifier before it
    mints its stronger replay attestation.  Recomputing this small identity
    avoids serializing the deeply nested stream document a second time.
    """

    from acfqp import v075_batched_observer_authority_v1 as batch_authority

    if type(item) is not batch_authority.V075SignedBatchedObservationV1:
        _fail("public verification identity requires one exact signed batch")
    return batch_authority._hash(
        "public_verification",
        {
            "schema": (
                "acfqp.v075_batched_observation_public_verification.v1"
            ),
            "schema_version": batch_authority.SCHEMA_VERSION,
            "request_id": item.request.request_id,
            "batch_id": item.batch_id,
            "observer_open_binding_id": (
                item.request.observer_open_binding.binding_id
            ),
            "accepted_draw_count": item.request.accepted_draw_count,
            "verification_result": (
                "SIGNATURE_AND_INTERNAL_RECONCILIATION_VERIFIED"
            ),
            "private_replay_claimed": False,
            "private_material_serialized": False,
        },
    )


def verify_v075_signed_batch_occurrence_closure_v1(
    *,
    closure: V075SignedBatchOccurrenceClosureV1,
    profile: V075IPCOccurrenceProfileV1,
    journal_entries: tuple[V075IPCJournalEntryV1, ...],
    batches: tuple[Any, ...],
    private_replays: tuple[Any, ...],
) -> V075BatchOccurrenceClosureVerificationV1:
    """Replay all public, sequence, IPC, and private-replay closure bindings."""

    from acfqp import v075_batched_observer_authority_v1 as batch_authority

    if (
        type(closure) is not V075SignedBatchOccurrenceClosureV1
        or type(profile) is not V075IPCOccurrenceProfileV1
        or type(journal_entries) is not tuple
        or type(batches) is not tuple
        or any(
            type(item) is not batch_authority.V075SignedBatchedObservationV1
            for item in batches
        )
        or type(private_replays) is not tuple
        or any(
            type(item)
            is not batch_authority.V075BatchedObservationPrivateReplayVerificationV1
            for item in private_replays
        )
    ):
        _fail("batch closure verifier rejects duck or incomplete inputs")
    journal_payload = _journal_payload(
        profile_id=profile.profile_id,
        occurrence_id=profile.occurrence_id,
        entries=journal_entries,
    )
    public_verification_ids = tuple(
        _public_verification_id_from_private_replayed_batch(item)
        for item in batches
    )
    grouped: dict[str, list[Any]] = {}
    for item in batches:
        grouped.setdefault(item.request.stream_identity.stream_id, []).append(
            item
        )
    sequences = tuple(
        batch_authority.verify_v075_batched_observation_sequence_v1(
            tuple(grouped[stream_id])
        )
        for stream_id in sorted(grouped)
    )
    if (
        closure.profile_id != profile.profile_id
        or closure.occurrence_id != profile.occurrence_id
        or closure.context_id != profile.context_id
        or closure.arm != profile.arm
        or closure.journal_id != _hash("journal", journal_payload)
        or closure.final_journal_entry_hash
        != journal_payload["final_entry_hash"]
        or closure.batch_ids != tuple(item.batch_id for item in batches)
        or closure.request_ids
        != tuple(item.request.request_id for item in batches)
        or closure.stream_ids != tuple(sorted(grouped))
        or closure.sequence_verification_ids
        != tuple(item.verification_id for item in sequences)
        or closure.public_verification_ids
        != public_verification_ids
        or closure.private_replay_verification_ids
        != tuple(item.verification_id for item in private_replays)
        or any(
            replay.batch_id != item.batch_id
            for replay, item in zip(private_replays, batches, strict=True)
        )
        or closure.accepted_draw_count
        != sum(item.request.accepted_draw_count for item in batches)
    ):
        _fail("signed batch occurrence closure lineage does not replay")
    return V075BatchOccurrenceClosureVerificationV1(
        _BATCH_CLOSURE_VERIFIER_ISSUER,
        closure.closure_id,
        closure.profile_id,
        closure.occurrence_id,
        len(batches),
        len(sequences),
        len(private_replays),
    )


@dataclass(frozen=True, slots=True)
class V075IPCActualWorkV1:
    process_launches: int
    child_intents_received: int
    parent_batches_issued: int
    observer_accepted_draws: int
    observer_random_words: int
    observer_rejections: int
    observer_outcome_rows: int
    private_replay_batches: int
    child_to_parent_bytes: int
    parent_to_child_bytes: int
    protocol_checks: int
    process_exit_code: int | None
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = (
            self.process_launches,
            self.child_intents_received,
            self.parent_batches_issued,
            self.observer_accepted_draws,
            self.observer_random_words,
            self.observer_rejections,
            self.observer_outcome_rows,
            self.private_replay_batches,
            self.child_to_parent_bytes,
            self.parent_to_child_bytes,
            self.protocol_checks,
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.process_launches != 1
            or (
                self.process_exit_code is not None
                and type(self.process_exit_code) is not int
            )
        ):
            _fail("IPC actual work is malformed")
        object.__setattr__(self, "_work_id", _hash("work", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_ipc_actual_work.v1",
            "schema_version": SCHEMA_VERSION,
            "process_launches": self.process_launches,
            "child_intents_received": self.child_intents_received,
            "parent_batches_issued": self.parent_batches_issued,
            "observer_accepted_draws": self.observer_accepted_draws,
            "observer_random_words": self.observer_random_words,
            "observer_rejections": self.observer_rejections,
            "observer_outcome_rows": self.observer_outcome_rows,
            "private_replay_batches": self.private_replay_batches,
            "child_to_parent_bytes": self.child_to_parent_bytes,
            "parent_to_child_bytes": self.parent_to_child_bytes,
            "protocol_checks": self.protocol_checks,
            "process_exit_code": self.process_exit_code,
            "native_actual_not_upper_bound": True,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _seal_batch_occurrence_closure(
    *,
    profile: V075IPCOccurrenceProfileV1,
    batched_session: Any,
    terminal_code: str,
    scientific_payload: dict[str, Any] | None,
    journal_entries: tuple[V075IPCJournalEntryV1, ...],
    batches: tuple[Any, ...],
    private_replays: tuple[Any, ...],
    underlying_session_closure: Any,
) -> tuple[
    V075SignedBatchOccurrenceClosureV1,
    V075BatchOccurrenceClosureVerificationV1,
]:
    from acfqp import v075_batched_observer_authority_v1 as batch_authority
    from acfqp import v075_private_observer_boundary_v1 as observer

    underlying_session = getattr(batched_session, "_session", None)
    if (
        type(batched_session)
        is not batch_authority.V075PrivateBatchedObserverSessionV1
        or type(underlying_session)
        is not observer.V075PrivateObserverSessionV1
        or type(underlying_session_closure)
        is not observer.V075ObserverJournalClosureV1
        or underlying_session_closure.entries
        or underlying_session_closure.session_public_id
        != batched_session.session_public_id
        or len(private_replays) != len(batches)
    ):
        _fail("batch occurrence closure lacks one closed exact parent session")
    public_verification_ids = tuple(
        _public_verification_id_from_private_replayed_batch(item)
        for item in batches
    )
    grouped: dict[str, list[Any]] = {}
    for item in batches:
        grouped.setdefault(item.request.stream_identity.stream_id, []).append(
            item
        )
    sequence_verifications = tuple(
        batch_authority.verify_v075_batched_observation_sequence_v1(
            tuple(grouped[stream_id])
        )
        for stream_id in sorted(grouped)
    )
    journal_payload = _journal_payload(
        profile_id=profile.profile_id,
        occurrence_id=profile.occurrence_id,
        entries=journal_entries,
    )
    kwargs = {
        "profile_id": profile.profile_id,
        "occurrence_id": profile.occurrence_id,
        "context_id": profile.context_id,
        "arm": profile.arm,
        "session_public_id": batched_session.session_public_id,
        "authority_binding_id": (
            underlying_session.authority_binding.binding_id
        ),
        "underlying_session_closure_id": (
            underlying_session_closure.closure_id
        ),
        "terminal_code": terminal_code,
        "scientific_payload_id": (
            None
            if scientific_payload is None
            else scientific_payload["scientific_payload_id"]
        ),
        "journal_id": _hash("journal", journal_payload),
        "final_journal_entry_hash": journal_payload["final_entry_hash"],
        "batch_ids": tuple(item.batch_id for item in batches),
        "request_ids": tuple(item.request.request_id for item in batches),
        "stream_ids": tuple(sorted(grouped)),
        "sequence_verification_ids": tuple(
            item.verification_id for item in sequence_verifications
        ),
        "public_verification_ids": tuple(
            public_verification_ids
        ),
        "private_replay_verification_ids": tuple(
            item.verification_id for item in private_replays
        ),
        "accepted_draw_count": sum(
            item.request.accepted_draw_count for item in batches
        ),
    }
    payload = _batch_closure_payload(**kwargs)
    try:
        signature = observer._sign(
            signer=getattr(underlying_session, "_signer", None),
            expected_key=(
                underlying_session.authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=(
                _BATCH_CLOSURE_SIGNING_DOMAIN
                + b"\x00"
                + _canonical_bytes(payload)
            ),
        )
    except observer.V075PrivateObserverBoundaryInvariantViolation as error:
        raise V075BatchedObserverIPCInvariantViolation(str(error)) from error
    closure = V075SignedBatchOccurrenceClosureV1(
        profile.profile_id,
        profile.occurrence_id,
        profile.context_id,
        profile.arm,
        underlying_session.authority_binding,
        batched_session.session_public_id,
        underlying_session_closure.closure_id,
        terminal_code,
        kwargs["scientific_payload_id"],
        kwargs["journal_id"],
        kwargs["final_journal_entry_hash"],
        kwargs["batch_ids"],
        kwargs["request_ids"],
        kwargs["stream_ids"],
        kwargs["sequence_verification_ids"],
        kwargs["public_verification_ids"],
        kwargs["private_replay_verification_ids"],
        kwargs["accepted_draw_count"],
        signature,
    )
    return (
        closure,
        V075BatchOccurrenceClosureVerificationV1(
            _BATCH_CLOSURE_VERIFIER_ISSUER,
            closure.closure_id,
            closure.profile_id,
            closure.occurrence_id,
            len(batches),
            len(sequence_verifications),
            len(private_replays),
        ),
    )


@dataclass(frozen=True, slots=True)
class V075IPCOccurrenceExecutionResultV1:
    profile_id: str
    occurrence_id: str
    status: str
    terminal_code: str
    scientific_payload: dict[str, Any] | None
    batch_occurrence_closure: V075SignedBatchOccurrenceClosureV1
    batch_occurrence_closure_verification: (
        V075BatchOccurrenceClosureVerificationV1
    )
    observed_batches: tuple[Any, ...] = field(repr=False)
    private_replay_verifications: tuple[Any, ...] = field(repr=False)
    journal_entries: tuple[V075IPCJournalEntryV1, ...]
    actual_work: V075IPCActualWorkV1
    stderr_sha256: str
    stderr_byte_count: int
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import v075_batched_observer_authority_v1 as batch_authority

        _cid(self.profile_id, "IPC result profile")
        _cid(self.occurrence_id, "IPC result occurrence")
        _cid(self.stderr_sha256, "IPC child stderr")
        if (
            self.status not in {"PASS", "FAILED"}
            or self.terminal_code
            not in {
                "CONSTRUCTION_FIXTURE_PASS",
                "PROTOCOL_FAILURE",
                "PROCESS_FAILURE",
            }
            or (self.status == "PASS")
            != (self.terminal_code == "CONSTRUCTION_FIXTURE_PASS")
            or (self.status == "PASS") != (self.scientific_payload is not None)
            or type(self.batch_occurrence_closure)
            is not V075SignedBatchOccurrenceClosureV1
            or type(self.batch_occurrence_closure_verification)
            is not V075BatchOccurrenceClosureVerificationV1
            or self.batch_occurrence_closure.profile_id != self.profile_id
            or self.batch_occurrence_closure.occurrence_id
            != self.occurrence_id
            or self.batch_occurrence_closure.terminal_code
            != self.terminal_code
            or self.batch_occurrence_closure_verification.closure_id
            != self.batch_occurrence_closure.closure_id
            or type(self.observed_batches) is not tuple
            or any(
                type(item)
                is not batch_authority.V075SignedBatchedObservationV1
                for item in self.observed_batches
            )
            or type(self.private_replay_verifications) is not tuple
            or any(
                type(item)
                is not batch_authority.V075BatchedObservationPrivateReplayVerificationV1
                for item in self.private_replay_verifications
            )
            or self.batch_occurrence_closure.batch_ids
            != tuple(item.batch_id for item in self.observed_batches)
            or self.batch_occurrence_closure.private_replay_verification_ids
            != tuple(
                item.verification_id
                for item in self.private_replay_verifications
            )
            or type(self.journal_entries) is not tuple
            or any(
                type(entry) is not V075IPCJournalEntryV1
                for entry in self.journal_entries
            )
            or any(
                entry.sequence != index
                or entry.prior_entry_hash
                != (
                    _INITIAL_JOURNAL_HASH
                    if index == 1
                    else self.journal_entries[index - 2].entry_hash
                )
                for index, entry in enumerate(self.journal_entries, start=1)
            )
            or type(self.actual_work) is not V075IPCActualWorkV1
            or type(self.stderr_byte_count) is not int
            or self.stderr_byte_count < 0
            or self.stderr_byte_count > MAX_CHILD_STDERR_BYTES
        ):
            _fail("IPC occurrence result is malformed")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    @property
    def scientific_payload_id(self) -> str | None:
        if self.scientific_payload is None:
            return None
        return self.scientific_payload["scientific_payload_id"]

    @property
    def canonical_scientific_bytes(self) -> bytes | None:
        if self.scientific_payload is None:
            return None
        return _canonical_bytes(self.scientific_payload)

    def _payload(self) -> dict[str, Any]:
        journal_payload = _journal_payload(
            profile_id=self.profile_id,
            occurrence_id=self.occurrence_id,
            entries=self.journal_entries,
        )
        journal_id = _hash("journal", journal_payload)
        return {
            "schema": "acfqp.v075_ipc_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "occurrence_id": self.occurrence_id,
            "status": self.status,
            "terminal_code": self.terminal_code,
            "scientific_payload_id": self.scientific_payload_id,
            "journal_id": journal_id,
            "batch_occurrence_closure_id": (
                self.batch_occurrence_closure.closure_id
            ),
            "batch_occurrence_closure_verification_id": (
                self.batch_occurrence_closure_verification.verification_id
            ),
            "actual_work_id": self.actual_work.work_id,
            "stderr_sha256": self.stderr_sha256,
            "stderr_byte_count": self.stderr_byte_count,
            "diagnostics_excluded_from_scientific_payload": True,
            "construction_fixture_only": True,
            "production_ready": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "scientific_payload": self.scientific_payload,
            "batch_occurrence_closure": (
                self.batch_occurrence_closure.to_document()
            ),
            "batch_occurrence_closure_verification": (
                self.batch_occurrence_closure_verification.to_document()
            ),
            "signed_batches": [
                item.to_document() for item in self.observed_batches
            ],
            "private_replay_verifications": [
                item.to_document()
                for item in self.private_replay_verifications
            ],
            "journal_entries": [
                entry.to_document() for entry in self.journal_entries
            ],
            "actual_work": self.actual_work.to_document(),
            "result_id": self.result_id,
        }


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover - Windows fallback
            process.kill()
    except (ProcessLookupError, PermissionError):
        process.kill()


def execute_v075_construction_ipc_occurrence_v1(
    *,
    profile: V075IPCOccurrenceProfileV1,
    batched_session: Any,
    private_replay_authority: Any,
    private_replay_environment: Any,
) -> V075IPCOccurrenceExecutionResultV1:
    """Run exactly one fresh construction child and retain all actual work."""

    from acfqp import v075_batched_observer_authority_v1 as batch_authority
    from acfqp import v075_private_observer_boundary_v1 as observer

    if (
        type(profile) is not V075IPCOccurrenceProfileV1
        or type(batched_session)
        is not batch_authority.V075PrivateBatchedObserverSessionV1
        or batched_session.authority_scope
        is not batch_authority.V075BatchAuthorityScopeV1.CONSTRUCTION_ONLY
        or type(private_replay_authority)
        is not observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
        or type(private_replay_environment)
        is not batch_authority.V075ConstructionBatchReplayEnvironmentFixtureV1
    ):
        _fail("construction IPC execution requires exact disjoint authorities")
    # The profile may not transplant streams from another observer namespace.
    session_binding = getattr(
        getattr(batched_session, "_session", None),
        "authority_binding",
        None,
    )
    if (
        session_binding is None
        or any(
            entry.stream_identity.namespace != session_binding.namespace
            for entry in profile.row_catalogue
        )
    ):
        _fail("IPC profile streams do not belong to the parent observer")

    launch_raw = _canonical_bytes(_launch_document(profile))
    entries: list[V075IPCJournalEntryV1] = []
    batches: list[Any] = []
    private_replays: list[Any] = []
    next_start: dict[str, int] = {}
    total_draws = 0
    child_bytes = 0
    parent_bytes = len(launch_raw)
    checks = 1
    terminal = "PROTOCOL_FAILURE"
    scientific: dict[str, Any] | None = None
    process: subprocess.Popen[bytes] | None = None
    stderr = b""
    exit_code: int | None = None

    with tempfile.TemporaryDirectory(prefix="acfqp-v075-ipc-") as sandbox:
        environment = {
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    str(Path(__file__).resolve()),
                    *profile.program_registration.argv,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox,
                env=environment,
                close_fds=True,
                start_new_session=True,
            )
            if process.stdin is None or process.stdout is None:
                _fail("fresh child process lacks isolated protocol pipes")
            _write_frame(process.stdin, launch_raw)
            deadline = time.monotonic() + profile.process_timeout_seconds
            # One final scientific frame is allowed after the last permitted
            # batch intent, including when the script uses the exact cap.
            for message_index in range(1, profile.max_batches + 2):
                raw = _read_frame_fd(process.stdout.fileno(), deadline)
                child_bytes += len(raw)
                document = _load_canonical(raw, field_name="child message")
                schema = document.get("schema") if type(document) is dict else None
                if schema == "acfqp.v075_ipc_scientific_payload.v1":
                    expected = _aggregate_scientific_payload(
                        profile_id=profile.profile_id,
                        occurrence_id=profile.occurrence_id,
                        context_id=profile.context_id,
                        arm=profile.arm,
                        batch_documents=(
                            item.to_document() for item in batches
                        ),
                    )
                    checks += 1
                    if document != expected or raw != _canonical_bytes(expected):
                        _fail("child final scientific payload is not replayable")
                    _journal_append(
                        entries,
                        direction="CHILD_TO_PARENT",
                        message_kind="FINAL_SCIENTIFIC_PAYLOAD",
                        raw=raw,
                        message_id=expected["scientific_payload_id"],
                    )
                    scientific = expected
                    break
                if schema != "acfqp.v075_ipc_batch_intent.v1":
                    _fail("child emitted an unknown protocol message")
                batch_index = len(batches) + 1
                if (
                    batch_index > profile.max_batches
                    or batch_index > len(profile.script)
                ):
                    _fail("child requested more batches than preregistered")
                intent, entry = _validate_intent(
                    raw=raw,
                    profile=profile,
                    expected_sequence=batch_index,
                    next_start_by_stream=next_start,
                    total_draws=total_draws,
                )
                checks += 1
                _journal_append(
                    entries,
                    direction="CHILD_TO_PARENT",
                    message_kind="BATCH_INTENT",
                    raw=raw,
                    message_id=intent["intent_id"],
                )
                request = batched_session.issue_request_v1(
                    stream_identity=entry.stream_identity,
                    accepted_draw_start=intent["accepted_draw_start"],
                    accepted_draw_count=intent["accepted_draw_count"],
                    accepted_draw_cap=intent["accepted_draw_cap"],
                )
                observed = batched_session.execute_request_v1(request)
                private_replays.append(
                    batch_authority.verify_v075_construction_batched_observation_private_replay_v1(
                        claimed=observed,
                        authority=private_replay_authority,
                        private_environment=private_replay_environment,
                    )
                )
                batches.append(observed)
                next_start[entry.stream_id] = (
                    intent["accepted_draw_start"]
                    + intent["accepted_draw_count"]
                )
                total_draws += intent["accepted_draw_count"]
                response = _response_document(
                    sequence=batch_index,
                    intent_id=intent["intent_id"],
                    batch_document=observed.to_document(),
                )
                response_raw = _canonical_bytes(response)
                checks += 1
                _journal_append(
                    entries,
                    direction="PARENT_TO_CHILD",
                    message_kind="BATCH_RESPONSE",
                    raw=response_raw,
                    message_id=response["response_id"],
                )
                _write_frame(process.stdin, response_raw)
                parent_bytes += len(response_raw)
            else:
                _fail("child did not close before the frozen batch cap")
            if scientific is None:
                _fail("child closed without one scientific payload")
            process.stdin.close()
            remaining = max(0.001, deadline - time.monotonic())
            exit_code = process.wait(timeout=remaining)
            if exit_code != 0:
                terminal = "PROCESS_FAILURE"
                scientific = None
            else:
                terminal = "CONSTRUCTION_FIXTURE_PASS"
        except (
            V075BatchedObserverIPCInvariantViolation,
            ValueError,
            BrokenPipeError,
            OSError,
            subprocess.SubprocessError,
        ) as error:
            if isinstance(error, (BrokenPipeError, OSError, subprocess.SubprocessError)):
                terminal = "PROCESS_FAILURE"
            elif process is not None:
                try:
                    observed_exit = process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    observed_exit = None
                if observed_exit not in {None, 0}:
                    terminal = "PROCESS_FAILURE"
            scientific = None
            _terminate_process(process) if process is not None else None
            if process is not None:
                try:
                    exit_code = process.wait(timeout=5)
                except subprocess.SubprocessError:
                    exit_code = None
        finally:
            if process is not None:
                _terminate_process(process)
                if process.stderr is not None:
                    stderr = process.stderr.read(MAX_CHILD_STDERR_BYTES + 1)
                    if len(stderr) > MAX_CHILD_STDERR_BYTES:
                        stderr = stderr[:MAX_CHILD_STDERR_BYTES]
                if exit_code is None:
                    exit_code = process.poll()

    underlying_session = getattr(batched_session, "_session", None)
    try:
        underlying_closure = underlying_session.close_v1()
    except (AttributeError, ValueError) as error:
        raise V075BatchedObserverIPCInvariantViolation(
            "parent observer session could not close after IPC execution"
        ) from error
    journal_tuple = tuple(entries)
    batch_tuple = tuple(batches)
    replay_tuple = tuple(private_replays)
    (
        batch_closure,
        batch_closure_verification,
    ) = _seal_batch_occurrence_closure(
        profile=profile,
        batched_session=batched_session,
        terminal_code=terminal,
        scientific_payload=scientific,
        journal_entries=journal_tuple,
        batches=batch_tuple,
        private_replays=replay_tuple,
        underlying_session_closure=underlying_closure,
    )
    work = V075IPCActualWorkV1(
        1,
        sum(
            entry.message_kind == "BATCH_INTENT"
            for entry in entries
        ),
        len(batches),
        sum(item.request.accepted_draw_count for item in batches),
        sum(item.random_word_count for item in batches),
        sum(item.rejection_count for item in batches),
        sum(len(item.outcomes) for item in batches),
        len(private_replays),
        child_bytes,
        parent_bytes,
        checks,
        exit_code,
    )
    return V075IPCOccurrenceExecutionResultV1(
        profile.profile_id,
        profile.occurrence_id,
        "PASS" if terminal == "CONSTRUCTION_FIXTURE_PASS" else "FAILED",
        terminal,
        scientific,
        batch_closure,
        batch_closure_verification,
        batch_tuple,
        replay_tuple,
        journal_tuple,
        work,
        hashlib.sha256(stderr).hexdigest(),
        len(stderr),
    )


def _child_main() -> int:
    try:
        launch_raw = _read_frame_child(sys.stdin.buffer)
        launch = _exact_mapping(
            _load_canonical(launch_raw, field_name="public launch"),
            {
                "schema",
                "schema_version",
                "profile_id",
                "occurrence_id",
                "context_id",
                "arm",
                "program",
                "construction_behavior",
                "row_catalogue",
                "script",
                "max_batches",
                "max_total_accepted_draws",
                "private_session_serialized",
                "private_law_serialized",
                "private_salt_serialized",
                "private_signer_serialized",
                "private_kernel_serialized",
                "callback_serialized",
                "pickle_transport_used",
                "launch_id",
            },
            field_name="public launch",
        )
        launch_payload = dict(launch)
        claimed_launch_id = launch_payload.pop("launch_id")
        if (
            launch["schema"] != "acfqp.v075_ipc_public_launch.v1"
            or launch["schema_version"] != SCHEMA_VERSION
            or launch["program"]
            != V075IPCChildProgramV1.CONSTRUCTION_SCRIPTED_AGGREGATE.value
            or any(
                launch[key] is not False
                for key in (
                    "private_session_serialized",
                    "private_law_serialized",
                    "private_salt_serialized",
                    "private_signer_serialized",
                    "private_kernel_serialized",
                    "callback_serialized",
                    "pickle_transport_used",
                )
            )
            or _cid(claimed_launch_id, "public launch")
            != _hash("launch", launch_payload)
        ):
            _fail("public launch is stale, private, or unregistered")
        behavior = V075IPCConstructionBehaviorV1(
            launch["construction_behavior"]
        )
        if behavior is V075IPCConstructionBehaviorV1.CRASH_BEFORE_INTENT:
            return 73
        catalogue = {
            entry["stream_id"]: entry for entry in launch["row_catalogue"]
        }
        next_start: dict[str, int] = {}
        batch_documents: list[dict[str, Any]] = []
        first_raw: bytes | None = None
        for sequence, step in enumerate(launch["script"], start=1):
            stream = catalogue[step["stream_id"]]
            start = next_start.get(step["stream_id"], 1)
            if (
                behavior
                is V075IPCConstructionBehaviorV1.GAP_FIRST_INTENT
                and sequence == 1
            ):
                start += 1
            intent = _make_intent(
                launch=launch,
                sequence=sequence,
                stream=stream,
                accepted_draw_start=start,
                accepted_draw_count=step["accepted_draw_count"],
            )
            if (
                behavior
                is V075IPCConstructionBehaviorV1.TRANSPLANT_FIRST_INTENT
                and sequence == 1
            ):
                intent["context_id"] = hashlib.sha256(
                    b"transplanted-context"
                ).hexdigest()
                payload = dict(intent)
                payload.pop("intent_id")
                intent["intent_id"] = _hash("intent", payload)
            raw = _canonical_bytes(intent)
            if (
                behavior
                is V075IPCConstructionBehaviorV1.REPLAY_FIRST_INTENT
                and sequence == 2
                and first_raw is not None
            ):
                raw = first_raw
                intent = _load_canonical(raw, field_name="replayed intent")
            if first_raw is None:
                first_raw = raw
            _write_frame(sys.stdout.buffer, raw)
            response_raw = _read_frame_child(sys.stdin.buffer)
            response = _validate_child_batch_response(
                raw=response_raw,
                intent=intent,
                expected_sequence=sequence,
            )
            batch_documents.append(response["signed_public_batch"])
            next_start[step["stream_id"]] = (
                start + step["accepted_draw_count"]
            )
        scientific = _aggregate_scientific_payload(
            profile_id=launch["profile_id"],
            occurrence_id=launch["occurrence_id"],
            context_id=launch["context_id"],
            arm=launch["arm"],
            batch_documents=batch_documents,
        )
        if (
            behavior
            is V075IPCConstructionBehaviorV1.TAMPER_FINAL_PAYLOAD
        ):
            scientific["failure_count"] += 1
        _write_frame(sys.stdout.buffer, _canonical_bytes(scientific))
        return 0
    except BaseException as error:
        # No exception repr: a future child must never echo private values.
        sys.stderr.write(type(error).__name__ + "\n")
        return 74


if __name__ == "__main__":
    if sys.argv == [str(Path(__file__).resolve()), _CHILD_ARG] or (
        len(sys.argv) == 2 and sys.argv[1] == _CHILD_ARG
    ):
        raise SystemExit(_child_main())
    raise SystemExit(64)


__all__ = [
    "CONSTRUCTION_FIXTURE_ONLY",
    "PRODUCTION_EXECUTION_STATUS",
    "V075BatchedObserverIPCInvariantViolation",
    "V075BatchOccurrenceClosureVerificationV1",
    "V075IPCActualWorkV1",
    "V075IPCChildProgramRegistrationV1",
    "V075IPCChildProgramV1",
    "V075IPCConstructionBehaviorV1",
    "V075IPCOccurrenceExecutionResultV1",
    "V075IPCOccurrenceProfileV1",
    "V075IPCRowCatalogueEntryV1",
    "V075IPCScriptStepV1",
    "V075SignedBatchOccurrenceClosureV1",
    "execute_v075_construction_ipc_occurrence_v1",
    "freeze_v075_construction_ipc_occurrence_profile_v1",
    "registered_v075_ipc_child_program_v1",
    "verify_v075_signed_batch_occurrence_closure_v1",
]
