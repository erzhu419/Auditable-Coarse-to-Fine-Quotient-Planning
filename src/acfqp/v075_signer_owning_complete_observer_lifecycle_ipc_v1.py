"""Signer-owning complete observer lifecycle for one synthetic root K7 fixture.

Contract 1.71 Stage B runs one complete construction lifecycle in a single
fresh sealed-source child:

    load non-exportable production signer
    -> derive the registered synthetic private environment
    -> issue the public reveal attestation
    -> open the observer session
    -> observe and append the fixed root-only K7 batch plan
    -> close the signed batch journal
    -> perform exact private replay
    -> create the observer-signed B3 attestation

The caller supplies only a public fixture intent, public signer registry,
public opaque commitment, occurrence/session identities, and a nonce.
Private generation seed and salt arrive through a distinct sealed descriptor.
There is no request field for a signer, private verification, old closure,
old B3, observation result, or caller-generated session.

This is a small *synthetic registered fixture*, not the production campaign
authority.  It does not access fresh held-out observations and it does not
close source/code provenance or the portable semantic registry.  Therefore
every production, scientific, and certificate lock remains false even when
the child completes and its public artifacts replay exactly.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
from types import MappingProxyType
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_confirmatory_manifest_preregistration_v2 as manifest
from acfqp import v075_observer_signed_private_replay_attestation_v2 as b3
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_production_campaign_profile_v2 as campaign_profile
from acfqp import v075_production_private_signer_runtime_v1 as signer_runtime
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from acfqp import v075_reveal_verifying_attestation_authority_v2 as reveal
from acfqp import v075_signer_owning_sealed_observer_ipc_v1 as stage_a


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.71.0"
PROFILE_KEY = "v075_signer_owning_complete_observer_lifecycle_ipc_v1"
FIXTURE_KEY = "SYNTHETIC_REGISTERED_ROOT_ONLY_K7_V1"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
SYNTHETIC_ROOT_LIFECYCLE_IMPLEMENTED = True

TERMINAL_SCOPE = (
    "CONSTRUCTION_SIGNER_OWNING_SYNTHETIC_ROOT_K7_LIFECYCLE_ONLY"
)
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
COMPLETE_TERMINAL_CODE = "COMPLETE_LIFECYCLE_CONSTRUCTION_NONCERTIFICATE"

MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_CHILD_RESULT_BYTES = stage_a.MAX_CHILD_RESULT_BYTES
MAX_RESULT_BYTES = 16 * 1024 * 1024
MAX_SECRET_BYTES = stage_a.MAX_PRIVATE_MATERIAL_BYTES
_CHILD_TERMINAL_CODES = frozenset(
    {
        COMPLETE_TERMINAL_CODE,
        "SECRET_MATERIAL_INVALID",
        "SECRET_COMMITMENT_MISMATCH",
        "SIGNER_LOAD_FAILED",
        "LIFECYCLE_EXECUTION_FAILED",
        "CHILD_PROTOCOL_FAILURE",
    }
)
_NO_CHILD_TERMINAL_CODES = frozenset(
    {
        "NONCE_REPLAY_REJECTED",
        "SOURCE_ARCHIVE_STAGING_FAILED",
        "PROCESS_LAUNCH_FAILED",
        "PROCESS_IDENTITY_CAPTURE_FAILED",
        "SUPERVISOR_PROTOCOL_FAILURE",
        "CHILD_RESULT_VALIDATION_FAILED",
        "CHILD_TIMEOUT",
        "CHILD_CRASH",
        "CHILD_FRAME_INVALID",
        "CHILD_EXTRA_OUTPUT",
        "CHILD_OUTPUT_CAP_EXCEEDED",
        "CHILD_STDERR_CAP_EXCEEDED",
        "CHILD_STDERR_FORBIDDEN",
    }
)
_ALLOWED_TERMINAL_CODES = _CHILD_TERMINAL_CODES | _NO_CHILD_TERMINAL_CODES
_PRELAUNCH_TERMINAL_CODES = frozenset(
    {
        "NONCE_REPLAY_REJECTED",
        "SOURCE_ARCHIVE_STAGING_FAILED",
        "PROCESS_LAUNCH_FAILED",
    }
)
_MODULE_NAME = (
    "acfqp.v075_signer_owning_complete_observer_lifecycle_ipc_v1"
)

_REGISTERED_BATCH_PLAN = (
    {
        "arm": public.ARM_ORDER[0],
        "accepted_draw_start": 1,
        "accepted_draw_count": 2,
        "accepted_draw_cap": 2,
    },
    {
        "arm": public.ARM_ORDER[1],
        "accepted_draw_start": 1,
        "accepted_draw_count": 3,
        "accepted_draw_cap": 3,
    },
)

_DOMAINS = MappingProxyType(
    {
        "program": (
            "acfqp:v075-signer-owning-complete-lifecycle-program:v1"
        ),
        "profile": (
            "acfqp:v075-signer-owning-complete-lifecycle-profile:v1"
        ),
        "request": (
            "acfqp:v075-signer-owning-complete-lifecycle-request:v1"
        ),
        "secret": (
            "acfqp:v075-signer-owning-complete-lifecycle-secret:v1"
        ),
        "fixture": (
            "acfqp:v075-synthetic-registered-root-k7-fixture:v1"
        ),
        "child_result": (
            "acfqp:v075-signer-owning-complete-lifecycle-child-result:v1"
        ),
        "journal_entry": (
            "acfqp:v075-signer-owning-complete-lifecycle-journal-entry:v1"
        ),
        "journal": (
            "acfqp:v075-signer-owning-complete-lifecycle-journal:v1"
        ),
        "invalid_child_payload": (
            "acfqp:v075-signer-owning-complete-lifecycle-invalid-child:"
            "v1"
        ),
        "supervisor": (
            "acfqp:v075-signer-owning-complete-lifecycle-supervisor:v1"
        ),
        "work": "acfqp:v075-signer-owning-complete-lifecycle-work:v1",
        "result": "acfqp:v075-signer-owning-complete-lifecycle-result:v1",
    }
)


class V075SignerOwningCompleteLifecycleV1InvariantViolation(ValueError):
    """A fixture, request, child lifecycle, artifact, or identity failed."""


class V075SignerOwningCompleteLifecycleProductionV1NotReady(RuntimeError):
    """The synthetic construction fixture cannot authorize production."""


def _fail(message: str) -> NoReturn:
    raise V075SignerOwningCompleteLifecycleV1InvariantViolation(message)


def _canonical(value: Any) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            str(error)
        ) from error


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("lifecycle JSON contains a duplicate key")
        result[key] = value
    return result


def _load(raw: bytes, *, label: str, cap: int) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{label} is empty, mistyped, or over cap")
    try:
        item = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: _fail(
                f"{label} contains non-finite {token}"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        if isinstance(
            error,
            V075SignerOwningCompleteLifecycleV1InvariantViolation,
        ):
            raise
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(item) is not dict or _canonical(item) != raw:
        _fail(f"{label} is not one canonical object")
    return item


def _exact(
    value: Any,
    keys: set[str] | frozenset[str],
    *,
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        _fail(f"{label} fields are missing, hidden, or malformed")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _DOMAINS[role]
    except KeyError as error:  # pragma: no cover
        raise RuntimeError("unknown lifecycle domain") from error
    return hashlib.sha256(
        domain.encode() + b"\x00" + _canonical(dict(payload))
    ).hexdigest()


def _sid(label: str, *bindings: str) -> str:
    return hashlib.sha256(
        _DOMAINS["fixture"].encode()
        + b"\x00"
        + label.encode()
        + b"\x00"
        + b"\x00".join(value.encode() for value in bindings)
    ).hexdigest()


def _oid(label: str, *bindings: str) -> str:
    return hashlib.sha1(
        _DOMAINS["fixture"].encode()
        + b"\x00git\x00"
        + label.encode()
        + b"\x00"
        + b"\x00".join(value.encode() for value in bindings)
    ).hexdigest()


def _typed_null(reason: str) -> dict[str, str]:
    if type(reason) is not str or not reason:
        _fail("lifecycle typed-null reason is empty")
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _require_typed_null(
    value: Any,
    *,
    reason: str,
    label: str,
) -> dict[str, str]:
    expected = _typed_null(reason)
    if type(value) is not dict or value != expected:
        _fail(f"{label} typed-null reason or fields changed")
    return value


def _locks() -> dict[str, bool]:
    return {
        "source_authority_complete": False,
        "code_provenance_complete": False,
        "portable_semantic_registry_complete": False,
        "fresh_heldout_accessed": False,
        "official_execution_allowed": False,
        "production_authorizing": False,
        "scientific_endpoint_credit_allowed": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "private_material_serialized": False,
    }


def _program_payload(
    *,
    source_snapshot_id: str,
    runtime_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_complete_observer_lifecycle_program.v1",
        "schema_version": SCHEMA_VERSION,
        "module": _MODULE_NAME,
        "child_callable": "_sealed_child_main",
        "bootstrap_sha256": _BOOTSTRAP_SHA256,
        "source_snapshot_id": source_snapshot_id,
        "runtime_id": runtime_id,
        "input_frame_count": 1,
        "output_frame_count": 1,
        "one_fresh_child_owns_complete_session": True,
        "caller_closure_input_allowed": False,
        "caller_b3_input_allowed": False,
        "caller_private_verification_input_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class V075CompleteObserverLifecycleProfileV1:
    transport_profile: (
        stage_a.V075SignerOwningSealedObserverServiceProfileV1
    ) = field(repr=False, compare=False)
    _program_id: str = field(init=False, repr=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.transport_profile)
            is not stage_a.V075SignerOwningSealedObserverServiceProfileV1
        ):
            _fail("lifecycle profile lacks one sealed transport profile")
        self.transport_profile._assert_current()  # noqa: SLF001
        program_id = _hash(
            "program",
            _program_payload(
                source_snapshot_id=(
                    self.transport_profile.source_snapshot_id
                ),
                runtime_id=self.transport_profile.runtime_id,
            ),
        )
        object.__setattr__(self, "_program_id", program_id)
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )
        self._assert_current()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_complete_observer_lifecycle_profile.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "fixture_key": FIXTURE_KEY,
            "sealed_transport_profile_id": (
                self.transport_profile.profile_id
            ),
            "source_snapshot_id": (
                self.transport_profile.source_snapshot_id
            ),
            "runtime_id": self.transport_profile.runtime_id,
            "program": {
                **_program_payload(
                    source_snapshot_id=(
                        self.transport_profile.source_snapshot_id
                    ),
                    runtime_id=self.transport_profile.runtime_id,
                ),
                "program_id": self._program_id,
            },
            "program_id": self._program_id,
            "timeout_milliseconds": (
                self.transport_profile.timeout_milliseconds
            ),
            "registered_context_index": 0,
            "registered_root_action_index": 0,
            "registered_support_epoch_index": 0,
            "registered_batch_plan": [
                dict(item) for item in _REGISTERED_BATCH_PLAN
            ],
            "synthetic_registered_fixture": True,
            "independent_remote_main_authority": False,
            "fresh_heldout_access_allowed": False,
            "complete_child_lifecycle_required": True,
            **_locks(),
        }

    def _assert_current(self) -> None:
        self.transport_profile._assert_current()  # noqa: SLF001
        if (
            _hash(
                "program",
                _program_payload(
                    source_snapshot_id=(
                        self.transport_profile.source_snapshot_id
                    ),
                    runtime_id=self.transport_profile.runtime_id,
                ),
            )
            != self._program_id
            or _hash("profile", self._payload()) != self._profile_id
        ):
            _fail("complete lifecycle profile identity is stale")

    @property
    def program_id(self) -> str:
        self._assert_current()
        return self._program_id

    @property
    def profile_id(self) -> str:
        self._assert_current()
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "profile_id": self._profile_id}


def freeze_v075_complete_observer_lifecycle_profile_v1(
    *,
    timeout_milliseconds: int = 10_000,
) -> V075CompleteObserverLifecycleProfileV1:
    return V075CompleteObserverLifecycleProfileV1(
        stage_a.freeze_v075_signer_owning_sealed_observer_service_profile_v1(
            timeout_milliseconds=timeout_milliseconds
        )
    )


_REQUEST_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "profile_id",
        "program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_nonce",
        "fixture_key",
        "occurrence_id",
        "session_external_id",
        "opaque_environment_commitment_id",
        "signer_registry",
        "signer_registry_id",
        "observer_evidence_key_id",
        "context_index",
        "root_action_index",
        "support_epoch_index",
        "batch_plan",
        "caller_supplied_signer",
        "caller_supplied_private_verification",
        "caller_supplied_private_material",
        "caller_supplied_session",
        "caller_supplied_closure",
        "caller_supplied_b3",
        "caller_supplied_observation_result",
        "request_id",
    }
)


def _request_payload(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
    request_nonce: str,
    occurrence_id: str,
    session_external_id: str,
    opaque_environment_commitment_id: str,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> dict[str, Any]:
    for value, label in (
        (request_nonce, "lifecycle nonce"),
        (occurrence_id, "lifecycle occurrence"),
        (session_external_id, "lifecycle session external identity"),
        (
            opaque_environment_commitment_id,
            "lifecycle environment commitment",
        ),
    ):
        _cid(value, label)
    if type(signer_registry) is not public.V075TrustedSignerRegistryV1:
        _fail("lifecycle request signer registry is untyped")
    return {
        "schema": "acfqp.v075_complete_observer_lifecycle_request.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "profile_id": profile.profile_id,
        "program_id": profile.program_id,
        "source_snapshot_id": (
            profile.transport_profile.source_snapshot_id
        ),
        "runtime_id": profile.transport_profile.runtime_id,
        "request_nonce": request_nonce,
        "fixture_key": FIXTURE_KEY,
        "occurrence_id": occurrence_id,
        "session_external_id": session_external_id,
        "opaque_environment_commitment_id": (
            opaque_environment_commitment_id
        ),
        "signer_registry": signer_registry.to_document(),
        "signer_registry_id": signer_registry.registry_id,
        "observer_evidence_key_id": (
            signer_registry.observer_evidence_key.key_id
        ),
        "context_index": 0,
        "root_action_index": 0,
        "support_epoch_index": 0,
        "batch_plan": [dict(item) for item in _REGISTERED_BATCH_PLAN],
        "caller_supplied_signer": False,
        "caller_supplied_private_verification": False,
        "caller_supplied_private_material": False,
        "caller_supplied_session": False,
        "caller_supplied_closure": False,
        "caller_supplied_b3": False,
        "caller_supplied_observation_result": False,
    }


def _validate_request(document: dict[str, Any]) -> dict[str, Any]:
    item = _exact(document, _REQUEST_KEYS, label="lifecycle request")
    registered_plan = [dict(value) for value in _REGISTERED_BATCH_PLAN]
    numeric_plan_fields = (
        "accepted_draw_start",
        "accepted_draw_count",
        "accepted_draw_cap",
    )
    forbidden = (
        "caller_supplied_signer",
        "caller_supplied_private_verification",
        "caller_supplied_private_material",
        "caller_supplied_session",
        "caller_supplied_closure",
        "caller_supplied_b3",
        "caller_supplied_observation_result",
    )
    if (
        item["schema"]
        != "acfqp.v075_complete_observer_lifecycle_request.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["fixture_key"] != FIXTURE_KEY
        or type(item["context_index"]) is not int
        or item["context_index"] != 0
        or type(item["root_action_index"]) is not int
        or item["root_action_index"] != 0
        or type(item["support_epoch_index"]) is not int
        or item["support_epoch_index"] != 0
        or type(item["batch_plan"]) is not list
        or any(
            type(plan) is not dict
            or type(plan.get("arm")) is not str
            or any(type(plan.get(key)) is not int for key in numeric_plan_fields)
            for plan in item["batch_plan"]
        )
        or item["batch_plan"] != registered_plan
        or any(item[key] is not False for key in forbidden)
    ):
        _fail("lifecycle request changed the registered public-only intent")
    for key in (
        "profile_id",
        "program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_nonce",
        "occurrence_id",
        "session_external_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "request_id",
    ):
        _cid(item[key], f"lifecycle request {key}")
    try:
        registry = stage_a._registry_from_document(  # noqa: SLF001
            item["signer_registry"]
        )
    except Exception as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            "lifecycle signer registry failed public replay"
        ) from error
    if (
        registry.registry_id != item["signer_registry_id"]
        or registry.observer_evidence_key.key_id
        != item["observer_evidence_key_id"]
    ):
        _fail("lifecycle request signer registry was transplanted")
    payload = {key: value for key, value in item.items() if key != "request_id"}
    if _hash("request", payload) != item["request_id"]:
        _fail("lifecycle request identity changed")
    return item


@dataclass(frozen=True, slots=True)
class V075CompleteObserverLifecycleRequestV1:
    _raw: bytes = field(repr=False)

    def __post_init__(self) -> None:
        document = _validate_request(
            _load(self._raw, label="lifecycle request", cap=MAX_REQUEST_BYTES)
        )
        raw = _canonical(document)
        if raw != self._raw:
            _fail("lifecycle request cached bytes changed")
        object.__setattr__(self, "_raw", raw)

    @property
    def request_id(self) -> str:
        return self.to_document()["request_id"]

    @property
    def request_nonce(self) -> str:
        return self.to_document()["request_nonce"]

    @property
    def canonical_bytes(self) -> bytes:
        self.to_document()
        return self._raw

    def to_document(self) -> dict[str, Any]:
        return _validate_request(
            _load(self._raw, label="lifecycle request", cap=MAX_REQUEST_BYTES)
        )


def freeze_v075_complete_observer_lifecycle_request_v1(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
    request_nonce: str,
    occurrence_id: str,
    session_external_id: str,
    opaque_environment_commitment_id: str,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> V075CompleteObserverLifecycleRequestV1:
    if type(profile) is not V075CompleteObserverLifecycleProfileV1:
        _fail("lifecycle request profile is untyped")
    profile._assert_current()
    payload = _request_payload(
        profile=profile,
        request_nonce=request_nonce,
        occurrence_id=occurrence_id,
        session_external_id=session_external_id,
        opaque_environment_commitment_id=(
            opaque_environment_commitment_id
        ),
        signer_registry=signer_registry,
    )
    return V075CompleteObserverLifecycleRequestV1(
        _canonical({**payload, "request_id": _hash("request", payload)})
    )


def verify_v075_complete_observer_lifecycle_request_bytes_v1(
    raw: bytes,
) -> V075CompleteObserverLifecycleRequestV1:
    return V075CompleteObserverLifecycleRequestV1(raw)


_SECRET_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "generation_seed_hex",
        "private_salt_hex",
        "secret_material_id",
    }
)


def _secret_payload(
    *,
    generation_seed_hex: str,
    private_salt_hex: str,
) -> dict[str, Any]:
    for value, label, minimum in (
        (generation_seed_hex, "generation seed", 64),
        (private_salt_hex, "private salt", 64),
    ):
        if (
            type(value) is not str
            or len(value) < minimum
            or len(value) % 2
            or any(character not in "0123456789abcdef" for character in value)
        ):
            _fail(f"{label} is not canonical bounded secret hex")
    return {
        "schema": "acfqp.v075_complete_observer_lifecycle_secret.v1",
        "schema_version": SCHEMA_VERSION,
        "generation_seed_hex": generation_seed_hex,
        "private_salt_hex": private_salt_hex,
    }


def _secret_raw_for_testing(
    *,
    generation_seed: bytes,
    private_salt: bytes,
) -> bytes:
    payload = _secret_payload(
        generation_seed_hex=generation_seed.hex(),
        private_salt_hex=private_salt.hex(),
    )
    return _canonical(
        {**payload, "secret_material_id": _hash("secret", payload)}
    )


def _load_secret(
    raw: bytes,
) -> tuple[
    private_env.V075PrivateGeneratedEnvironmentV1,
    bytes,
    public.V075OpaqueEnvironmentCommitmentV1,
]:
    item = _exact(
        _load(raw, label="lifecycle secret", cap=MAX_SECRET_BYTES),
        _SECRET_KEYS,
        label="lifecycle secret",
    )
    payload = _secret_payload(
        generation_seed_hex=item["generation_seed_hex"],
        private_salt_hex=item["private_salt_hex"],
    )
    if (
        item["schema"] != payload["schema"]
        or item["schema_version"] != SCHEMA_VERSION
        or _cid(item["secret_material_id"], "lifecycle secret")
        != _hash("secret", payload)
    ):
        _fail("lifecycle secret identity changed")
    seed = bytes.fromhex(item["generation_seed_hex"])
    salt = bytes.fromhex(item["private_salt_hex"])
    try:
        generated = private_env.generate_v075_private_environment_v1(
            profile=(
                private_env
                .freeze_v075_private_environment_generation_profile_v1()
            ),
            secret_generation_seed=seed,
        )
        commitment = (
            private_env
            .seal_v075_generated_private_environment_commitment_v1(
                generated_environment=generated,
                secret_salt=salt,
            )
        )
    except Exception as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            "lifecycle secret failed synthetic environment generation"
        ) from error
    return generated, salt, commitment


def _stage_secret_for_testing(raw: bytes) -> int:
    _load_secret(raw)
    return stage_a._stage_sealed_bytes(  # noqa: SLF001
        raw,
        name="acfqp-v075-complete-lifecycle-secret",
        cap=MAX_SECRET_BYTES,
    )


@dataclass(frozen=True, slots=True)
class _FixtureBase:
    commitment: public.V075OpaqueEnvironmentCommitmentV1
    anchor: remote.V075RemoteMainAnchorAttestationV2
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2
    tracked: preopen.V075TrackedPreopenBlobClosureV2
    fixture_id: str


def _fixture_base(
    *,
    commitment: public.V075OpaqueEnvironmentCommitmentV1,
    signer_registry: public.V075TrustedSignerRegistryV1,
) -> _FixtureBase:
    if (
        type(commitment) is not public.V075OpaqueEnvironmentCommitmentV1
        or type(signer_registry) is not public.V075TrustedSignerRegistryV1
    ):
        _fail("synthetic lifecycle fixture inputs are untyped")
    workload = manifest.freeze_v075_confirmatory_public_workload_v2()
    runner = campaign_profile.freeze_v075_production_campaign_profile_v2()
    bindings = (commitment.commitment_id, signer_registry.registry_id)
    anchor = remote.V075RemoteMainAnchorAttestationV2(
        remote._ANCHOR_ISSUER,  # noqa: SLF001
        _oid("commit", *bindings),
        _oid("tree", *bindings),
        (_oid("parent", *bindings),),
        _oid("manifest-blob", *bindings),
        _oid("final-blob", *bindings),
        _sid("manifest", *bindings),
        _sid("final", *bindings),
        _sid("component-registry", *bindings),
        _sid("semantic-registry-binding", *bindings),
        _sid("semantic-artifact-replay", *bindings),
        workload.workload_id,
        runner.profile_id,
        commitment.family.generation_id,
        commitment.commitment_id,
        signer_registry,
    )
    namespace = namespace_v2.V075PublicTargetTapeNamespaceV2(
        namespace_v2._NAMESPACE_ISSUER,  # noqa: SLF001
        anchor,
        workload,
        commitment.family,
        runner,
        commitment,
        signer_registry,
    )
    tracked = preopen.V075TrackedPreopenBlobClosureV2(
        preopen._BLOB_CLOSURE_ISSUER,  # noqa: SLF001
        anchor,
        _sid("manifest-bytes", *bindings),
        _sid("final-bytes", *bindings),
    )
    fixture_payload = {
        "schema": "acfqp.v075_synthetic_registered_root_k7_fixture.v1",
        "schema_version": SCHEMA_VERSION,
        "fixture_key": FIXTURE_KEY,
        "remote_main_anchor_id": anchor.anchor_id,
        "target_tape_namespace_id": namespace.target_tape_namespace_id,
        "opaque_environment_commitment_id": commitment.commitment_id,
        "signer_registry_id": signer_registry.registry_id,
        "context_index": 0,
        "root_action_index": 0,
        "support_epoch_index": 0,
        "batch_plan": [dict(value) for value in _REGISTERED_BATCH_PLAN],
        "synthetic_registered_fixture": True,
        "fresh_heldout_accessed": False,
    }
    return _FixtureBase(
        commitment,
        anchor,
        namespace,
        tracked,
        _hash("fixture", fixture_payload),
    )


def _root_streams(
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> graph.V075FiveArmStreamSetV1:
    if graph.validate_v075_public_graph_namespace_v2(namespace) is not namespace:
        _fail("synthetic lifecycle namespace failed graph validation")
    context = namespace.family.replicate_contexts[0]
    if context.topology.vertex_count != 7 or len(context.topology.edges) != 21:
        _fail("synthetic lifecycle fixture is not root-only K7")
    catalogue = graph.root_catalogue_v1(context)
    row = graph.observation_row_binding_v1(
        context,
        catalogue,
        catalogue.actions[0],
    )
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.freeze_five_arm_stream_set_v1(pairing)


def _authorization(
    *,
    base: _FixtureBase,
    private_reveal: preopen.V075PrivateRevealAttestationV2,
) -> preopen.V075ObserverOpenAuthorizationV2:
    return preopen.V075ObserverOpenAuthorizationV2(
        preopen._AUTHORIZATION_ISSUER,  # noqa: SLF001
        base.anchor,
        base.tracked,
        base.namespace.signer_registry,
        base.commitment,
        private_reveal,
    )


def _expected_session_public_id(
    *,
    binding: observer.V075ObserverOpenAuthorityBindingV2,
    session_external_id: str,
) -> str:
    return observer._hash(  # noqa: SLF001
        "session",
        {
            "schema": (
                "acfqp.v075_private_observer_session_public_identity.v2"
            ),
            "schema_version": observer.SCHEMA_VERSION,
            "observer_open_binding_id": binding.binding_id,
            "observer_open_authorization_id": binding.authorization_id,
            "private_reveal_attestation_id": (
                binding.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": binding.remote_main_anchor_id,
            "target_tape_namespace_id": (
                binding.namespace.target_tape_namespace_id
            ),
            "environment_commitment_id": (
                binding.namespace.environment_commitment.commitment_id
            ),
            "signer_registry_id": (
                binding.namespace.signer_registry.registry_id
            ),
            "observer_signer_key_id": (
                binding.namespace.signer_registry.observer_evidence_key.key_id
            ),
            "session_external_id": session_external_id,
            "authority_version": "V2",
            "namespace_version": "V2",
            "private_material_serialized": False,
        },
    )


def _lifecycle_work(
    *,
    secret_verified: int,
    signer_load_attempts: int,
    signer_load_successes: int,
    reveal_signatures: int,
    session_open_calls: int,
    batch_observe_calls: int,
    accepted_draws: int,
    journal_append_calls: int,
    closure_calls: int,
    private_replay_calls: int,
    b3_sign_calls: int,
    public_replay_calls: int,
) -> dict[str, int]:
    return {
        "secret_fd_read_calls": 1,
        "secret_commitment_checks": secret_verified,
        "production_signer_load_attempts": signer_load_attempts,
        "production_signer_load_successes": signer_load_successes,
        "signer_load_challenge_signatures": signer_load_successes,
        "reveal_attestation_signatures": reveal_signatures,
        "observer_session_open_calls": session_open_calls,
        "batch_observe_calls": batch_observe_calls,
        "accepted_draws": accepted_draws,
        "journal_append_calls": journal_append_calls,
        "batch_closure_calls": closure_calls,
        "private_replay_calls": private_replay_calls,
        "b3_sign_calls": b3_sign_calls,
        "public_artifact_replay_calls_child": public_replay_calls,
        "old_closure_upgrade_calls": 0,
        "old_b3_upgrade_calls": 0,
    }


def _child_failure(
    *,
    request: Mapping[str, Any],
    code: str,
    work: Mapping[str, int],
) -> bytes:
    payload = {
        "schema": "acfqp.v075_complete_observer_lifecycle_child_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": code,
        "profile_id": request["profile_id"],
        "program_id": request["program_id"],
        "source_snapshot_id": request["source_snapshot_id"],
        "runtime_id": request["runtime_id"],
        "request_id": request["request_id"],
        "request_nonce": request["request_nonce"],
        "fixture_key": request["fixture_key"],
        "occurrence_id": request["occurrence_id"],
        "session_external_id": request["session_external_id"],
        "opaque_environment_commitment_id": (
            request["opaque_environment_commitment_id"]
        ),
        "signer_registry_id": request["signer_registry_id"],
        "observer_evidence_key_id": request["observer_evidence_key_id"],
        "lifecycle_status": "FAILED_BEFORE_COMPLETE_LIFECYCLE",
        "fixture_id": _typed_null(code),
        "observer_session_public_id": _typed_null(code),
        "public_fixture": _typed_null(code),
        "signed_batch_journal_closure": _typed_null(code),
        "signed_batch_journal_closure_id": _typed_null(code),
        "b3_attestation": _typed_null(code),
        "b3_attestation_id": _typed_null(code),
        "complete_observer_lifecycle": False,
        "private_replay_performed": False,
        "b3_sign_performed": False,
        "child_work": dict(work),
        **_locks(),
    }
    return _canonical(
        {**payload, "child_result_id": _hash("child_result", payload)}
    )


def _complete_child_result(
    *,
    request: Mapping[str, Any],
    base: _FixtureBase,
    private_reveal: preopen.V075PrivateRevealAttestationV2,
    authorization: preopen.V075ObserverOpenAuthorizationV2,
    binding: observer.V075ObserverOpenAuthorityBindingV2,
    streams: graph.V075FiveArmStreamSetV1,
    closure: observer.V075ObserverBatchJournalClosureV2,
    attestation: b3.V075ObserverSignedPrivateReplayAttestationV2,
    work: Mapping[str, int],
) -> bytes:
    public_fixture = {
        "fixture_id": base.fixture_id,
        "opaque_environment_commitment": base.commitment.to_document(),
        "remote_main_anchor": base.anchor.to_document(),
        "target_tape_namespace": base.namespace.to_document(),
        "tracked_blob_closure": base.tracked.to_document(),
        "private_reveal_attestation": private_reveal.to_document(),
        "observer_open_authorization": authorization.to_document(),
        "observer_open_binding": binding.to_document(),
        "streams": [item.to_document() for item in streams.streams],
        "stream_ids": [item.stream_id for item in streams.streams],
        "root_context_id": (
            base.namespace.family.replicate_contexts[0].context_id
        ),
        "root_topology_id": (
            base.namespace.family.replicate_contexts[0].topology.topology_id
        ),
        "synthetic_registered_fixture": True,
        "fresh_heldout_accessed": False,
    }
    payload = {
        "schema": "acfqp.v075_complete_observer_lifecycle_child_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": COMPLETE_TERMINAL_CODE,
        "profile_id": request["profile_id"],
        "program_id": request["program_id"],
        "source_snapshot_id": request["source_snapshot_id"],
        "runtime_id": request["runtime_id"],
        "request_id": request["request_id"],
        "request_nonce": request["request_nonce"],
        "fixture_key": request["fixture_key"],
        "occurrence_id": request["occurrence_id"],
        "session_external_id": request["session_external_id"],
        "opaque_environment_commitment_id": (
            request["opaque_environment_commitment_id"]
        ),
        "signer_registry_id": request["signer_registry_id"],
        "observer_evidence_key_id": request["observer_evidence_key_id"],
        "lifecycle_status": (
            "OPEN_OBSERVE_APPEND_CLOSE_PRIVATE_REPLAY_B3_COMPLETE"
        ),
        "fixture_id": base.fixture_id,
        "observer_session_public_id": closure.session_public_id,
        "public_fixture": public_fixture,
        "signed_batch_journal_closure": closure.to_document(),
        "signed_batch_journal_closure_id": closure.closure_id,
        "b3_attestation": attestation.to_document(),
        "b3_attestation_id": attestation.attestation_id,
        "complete_observer_lifecycle": True,
        "private_replay_performed": True,
        "b3_sign_performed": True,
        "child_work": dict(work),
        **_locks(),
    }
    return _canonical(
        {**payload, "child_result_id": _hash("child_result", payload)}
    )


def _sealed_child_main(
    *,
    archive_fd: int,
    secret_fd: int,
    expected_source_snapshot_id: str,
    expected_archive_sha256: str,
    expected_archive_size: int,
    expected_runtime_id: str,
    expected_program_id: str,
    repository_root: str,
    signer_private_root: str,
    signer_private_key_path: str,
) -> int:
    request: dict[str, Any] | None = None
    work = _lifecycle_work(
        secret_verified=0,
        signer_load_attempts=0,
        signer_load_successes=0,
        reveal_signatures=0,
        session_open_calls=0,
        batch_observe_calls=0,
        accepted_draws=0,
        journal_append_calls=0,
        closure_calls=0,
        private_replay_calls=0,
        b3_sign_calls=0,
        public_replay_calls=0,
    )
    try:
        stage_a._assert_child_runtime(  # noqa: SLF001
            expected_runtime_id=expected_runtime_id,
            expected_source_snapshot_id=expected_source_snapshot_id,
            expected_archive_sha256=expected_archive_sha256,
            expected_archive_size=expected_archive_size,
            archive_fd=archive_fd,
        )
        archive_origin = f"/proc/self/fd/{archive_fd}"
        if not __file__.startswith(archive_origin):
            _fail("complete lifecycle child imported live workspace source")
        request_raw = stage_a._read_child_frame(  # noqa: SLF001
            sys.stdin.buffer,
            cap=MAX_REQUEST_BYTES,
        )
        request = (
            verify_v075_complete_observer_lifecycle_request_bytes_v1(
                request_raw
            ).to_document()
        )
        actual_program_id = _hash(
            "program",
            _program_payload(
                source_snapshot_id=expected_source_snapshot_id,
                runtime_id=expected_runtime_id,
            ),
        )
        if (
            request["source_snapshot_id"] != expected_source_snapshot_id
            or request["runtime_id"] != expected_runtime_id
            or request["program_id"] != expected_program_id
            or actual_program_id != expected_program_id
        ):
            _fail("complete lifecycle child crossed program identities")
        secret_raw = stage_a._read_sealed_fd(  # noqa: SLF001
            secret_fd,
            cap=MAX_SECRET_BYTES,
        )
        try:
            generated, salt, commitment = _load_secret(secret_raw)
        except Exception:
            result = _child_failure(
                request=request,
                code="SECRET_MATERIAL_INVALID",
                work=work,
            )
            stage_a._write_child_frame(  # noqa: SLF001
                sys.stdout.buffer,
                result,
                cap=MAX_CHILD_RESULT_BYTES,
            )
            return 0
        if (
            commitment.commitment_id
            != request["opaque_environment_commitment_id"]
        ):
            result = _child_failure(
                request=request,
                code="SECRET_COMMITMENT_MISMATCH",
                work=work,
            )
            stage_a._write_child_frame(  # noqa: SLF001
                sys.stdout.buffer,
                result,
                cap=MAX_CHILD_RESULT_BYTES,
            )
            return 0
        work["secret_commitment_checks"] = 1
        registry = stage_a._registry_from_document(  # noqa: SLF001
            request["signer_registry"]
        )
        work["production_signer_load_attempts"] = 1
        try:
            signer = (
                signer_runtime
                .load_v075_production_observer_evidence_signer_v1(
                    repository_root=Path(repository_root),
                    private_root=Path(signer_private_root),
                    private_key_path=Path(signer_private_key_path),
                    signer_registry=registry,
                )
            )
        except Exception:
            result = _child_failure(
                request=request,
                code="SIGNER_LOAD_FAILED",
                work=work,
            )
            stage_a._write_child_frame(  # noqa: SLF001
                sys.stdout.buffer,
                result,
                cap=MAX_CHILD_RESULT_BYTES,
            )
            return 0
        work["production_signer_load_successes"] = 1
        work["signer_load_challenge_signatures"] = 1
        try:
            base = _fixture_base(
                commitment=commitment,
                signer_registry=registry,
            )
            private_reveal = (
                reveal.issue_v075_reveal_verified_private_attestation_v2(
                    anchor=base.anchor,
                    commitment=base.commitment,
                    generated_environment=generated,
                    secret_salt=salt,
                    signer_registry=registry,
                    observer_signer=signer,
                )
            )
            work["reveal_attestation_signatures"] = 1
            authorization = _authorization(
                base=base,
                private_reveal=private_reveal,
            )
            binding = observer._require_exact_v2_binding(  # noqa: SLF001
                authority=authorization,
                namespace=base.namespace,
            )
            streams = _root_streams(base.namespace)
            session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
                authority=authorization,
                namespace=base.namespace,
                binding=binding,
                private_salt=salt,
                private_environment=(
                    generated.secret_laws_for_commitment()
                ),
                observer_signer=signer,
                session_external_id=request["session_external_id"],
            )
            work["observer_session_open_calls"] = 1
            streams_by_arm = {item.arm: item for item in streams.streams}
            for plan in _REGISTERED_BATCH_PLAN:
                session.observe_batch_v2(
                    occurrence_id=request["occurrence_id"],
                    stream_identity=streams_by_arm[plan["arm"]],
                    accepted_draw_start=plan["accepted_draw_start"],
                    accepted_draw_count=plan["accepted_draw_count"],
                    accepted_draw_cap=plan["accepted_draw_cap"],
                )
                work["batch_observe_calls"] += 1
                work["accepted_draws"] += plan["accepted_draw_count"]
                work["journal_append_calls"] += 1
            closure = session.close_batch_v2()
            work["batch_closure_calls"] = 1
            attestation = (
                b3.freeze_v075_observer_signed_private_replay_attestation_v2(
                    authority=authorization,
                    namespace=base.namespace,
                    closure=closure,
                    authority_binding=binding,
                    used_stream_identities=tuple(
                        streams_by_arm[plan["arm"]]
                        for plan in _REGISTERED_BATCH_PLAN
                    ),
                    private_salt=salt,
                    private_environment=(
                        generated.secret_laws_for_commitment()
                    ),
                    observer_signer=signer,
                )
            )
            work["private_replay_calls"] = 1
            work["b3_sign_calls"] = 1
            _replay_complete_child_public_artifacts(
                request=request,
                child_document=_load(
                    _complete_child_result(
                        request=request,
                        base=base,
                        private_reveal=private_reveal,
                        authorization=authorization,
                        binding=binding,
                        streams=streams,
                        closure=closure,
                        attestation=attestation,
                        work=work,
                    ),
                    label="child self-replay",
                    cap=MAX_CHILD_RESULT_BYTES,
                ),
            )
            work["public_artifact_replay_calls_child"] = 1
            result = _complete_child_result(
                request=request,
                base=base,
                private_reveal=private_reveal,
                authorization=authorization,
                binding=binding,
                streams=streams,
                closure=closure,
                attestation=attestation,
                work=work,
            )
        except Exception:
            result = _child_failure(
                request=request,
                code="LIFECYCLE_EXECUTION_FAILED",
                work=work,
            )
        stage_a._write_child_frame(  # noqa: SLF001
            sys.stdout.buffer,
            result,
            cap=MAX_CHILD_RESULT_BYTES,
        )
        return 0
    except BaseException:
        if request is None:
            return 91
        try:
            result = _child_failure(
                request=request,
                code="CHILD_PROTOCOL_FAILURE",
                work=work,
            )
            stage_a._write_child_frame(  # noqa: SLF001
                sys.stdout.buffer,
                result,
                cap=MAX_CHILD_RESULT_BYTES,
            )
            return 0
        except BaseException:
            return 92


_BOOTSTRAP_SOURCE = r"""
import fcntl
import hashlib
import importlib
import os
import sys

archive_fd = int(sys.argv[1])
secret_fd = int(sys.argv[2])
archive_sha256 = sys.argv[3]
archive_size = int(sys.argv[4])
source_id = sys.argv[5]
runtime_id = sys.argv[6]
program_id = sys.argv[7]
repository_root = sys.argv[8]
private_root = sys.argv[9]
private_key_path = sys.argv[10]
required_seals = 0x0008 | 0x0004 | 0x0002 | 0x0001
if fcntl.fcntl(archive_fd, 1034) & required_seals != required_seals:
    raise SystemExit(71)
status = os.fstat(archive_fd)
if status.st_size != archive_size:
    raise SystemExit(72)
digest = hashlib.sha256()
offset = 0
while offset < status.st_size:
    chunk = os.pread(
        archive_fd,
        min(1024 * 1024, status.st_size - offset),
        offset,
    )
    if not chunk:
        raise SystemExit(73)
    digest.update(chunk)
    offset += len(chunk)
if digest.hexdigest() != archive_sha256:
    raise SystemExit(74)
archive_path = "/proc/self/fd/" + str(archive_fd)
sys.path.insert(0, archive_path)
module = importlib.import_module(
    "acfqp.v075_signer_owning_complete_observer_lifecycle_ipc_v1"
)
raise SystemExit(
    module._sealed_child_main(
        archive_fd=archive_fd,
        secret_fd=secret_fd,
        expected_source_snapshot_id=source_id,
        expected_archive_sha256=archive_sha256,
        expected_archive_size=archive_size,
        expected_runtime_id=runtime_id,
        expected_program_id=program_id,
        repository_root=repository_root,
        signer_private_root=private_root,
        signer_private_key_path=private_key_path,
    )
)
""".strip()
_BOOTSTRAP_SHA256 = hashlib.sha256(
    _BOOTSTRAP_SOURCE.encode()
).hexdigest()


def _child_argv(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
    archive_fd: int,
    secret_fd: int,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
) -> list[str]:
    transport = profile.transport_profile
    return [
        sys.executable,
        "-I",
        "-S",
        "-c",
        _BOOTSTRAP_SOURCE,
        str(archive_fd),
        str(secret_fd),
        transport.source_archive_sha256,
        str(transport.source_archive_byte_count),
        transport.source_snapshot_id,
        transport.runtime_id,
        profile.program_id,
        os.fspath(repository_root),
        os.fspath(signer_private_root),
        os.fspath(signer_private_key_path),
    ]


def _commitment_from_document(
    value: Any,
) -> public.V075OpaqueEnvironmentCommitmentV1:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "family_generation_id",
            "context_ids",
            "commitment_digest",
            "commitment_scheme",
            "minimum_secret_salt_bytes",
            "secret_salt_serialized",
            "secret_environment_serialized",
            "production_law_serialized",
            "commitment_id",
        },
        label="public environment commitment",
    )
    try:
        commitment = public.V075OpaqueEnvironmentCommitmentV1(
            public.freeze_v075_public_family_generation_v1(),
            item["commitment_digest"],
        )
    except Exception as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            "public environment commitment failed replay"
        ) from error
    if commitment.to_document() != item:
        _fail("public environment commitment identity changed")
    return commitment


_PUBLIC_FIXTURE_KEYS = frozenset(
    {
        "fixture_id",
        "opaque_environment_commitment",
        "remote_main_anchor",
        "target_tape_namespace",
        "tracked_blob_closure",
        "private_reveal_attestation",
        "observer_open_authorization",
        "observer_open_binding",
        "streams",
        "stream_ids",
        "root_context_id",
        "root_topology_id",
        "synthetic_registered_fixture",
        "fresh_heldout_accessed",
    }
)


def _replay_complete_child_public_artifacts(
    *,
    request: Mapping[str, Any],
    child_document: Mapping[str, Any],
) -> tuple[
    observer.V075ObserverBatchJournalClosureV2,
    b3.V075ObserverSignedPrivateReplayAttestationV2,
]:
    fixture = _exact(
        child_document["public_fixture"],
        _PUBLIC_FIXTURE_KEYS,
        label="complete child public fixture",
    )
    registry = stage_a._registry_from_document(  # noqa: SLF001
        request["signer_registry"]
    )
    commitment = _commitment_from_document(
        fixture["opaque_environment_commitment"]
    )
    if (
        commitment.commitment_id
        != request["opaque_environment_commitment_id"]
    ):
        _fail("complete child commitment crossed its request")
    base = _fixture_base(
        commitment=commitment,
        signer_registry=registry,
    )
    if (
        fixture["fixture_id"] != base.fixture_id
        or child_document["fixture_id"] != base.fixture_id
        or fixture["remote_main_anchor"] != base.anchor.to_document()
        or fixture["target_tape_namespace"]
        != base.namespace.to_document()
        or fixture["tracked_blob_closure"] != base.tracked.to_document()
        or fixture["root_context_id"]
        != base.namespace.family.replicate_contexts[0].context_id
        or fixture["root_topology_id"]
        != base.namespace.family.replicate_contexts[0].topology.topology_id
        or fixture["synthetic_registered_fixture"] is not True
        or fixture["fresh_heldout_accessed"] is not False
    ):
        _fail("complete child public fixture identity changed")
    try:
        private_reveal = (
            reveal.load_and_verify_v075_reveal_verified_attestation_v2(
                raw=_canonical(fixture["private_reveal_attestation"]),
                anchor=base.anchor,
                commitment=commitment,
                signer_registry=registry,
            )
        )
    except Exception as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            "complete child reveal attestation failed public replay"
        ) from error
    authorization = _authorization(
        base=base,
        private_reveal=private_reveal,
    )
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=base.namespace,
    )
    streams = _root_streams(base.namespace)
    if (
        fixture["observer_open_authorization"]
        != authorization.to_document()
        or fixture["observer_open_binding"] != binding.to_document()
        or fixture["streams"]
        != [item.to_document() for item in streams.streams]
        or fixture["stream_ids"]
        != [item.stream_id for item in streams.streams]
    ):
        _fail("complete child authorization, binding, or streams changed")
    streams_by_arm = {item.arm: item for item in streams.streams}
    used_streams = tuple(
        streams_by_arm[plan["arm"]] for plan in _REGISTERED_BATCH_PLAN
    )
    try:
        closure = observer.load_observer_batch_journal_closure_bytes_v2(
            raw=_canonical(
                child_document["signed_batch_journal_closure"]
            ),
            authority_binding=binding,
            known_stream_identities=used_streams,
        )
        attestation = (
            b3.verify_v075_observer_signed_private_replay_attestation_bytes_v2(
                raw=_canonical(child_document["b3_attestation"]),
                closure=closure,
                authority_binding=binding,
                used_stream_identities=used_streams,
            )
        )
    except Exception as error:
        raise V075SignerOwningCompleteLifecycleV1InvariantViolation(
            "complete child closure or B3 failed public replay"
        ) from error
    expected_session = _expected_session_public_id(
        binding=binding,
        session_external_id=request["session_external_id"],
    )
    if (
        closure.occurrence_id != request["occurrence_id"]
        or closure.session_public_id != expected_session
        or child_document["observer_session_public_id"] != expected_session
        or child_document["signed_batch_journal_closure_id"]
        != closure.closure_id
        or child_document["b3_attestation_id"]
        != attestation.attestation_id
        or tuple(
            (
                entry.batch.request.stream_identity.arm,
                entry.batch.request.accepted_draw_start,
                entry.batch.request.accepted_draw_count,
                entry.batch.request.accepted_draw_cap,
            )
            for entry in closure.entries
        )
        != tuple(
            (
                plan["arm"],
                plan["accepted_draw_start"],
                plan["accepted_draw_count"],
                plan["accepted_draw_cap"],
            )
            for plan in _REGISTERED_BATCH_PLAN
        )
    ):
        _fail("complete child session, plan, closure, or B3 was transplanted")
    return closure, attestation


_CHILD_COMMON_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "terminal_scope",
        "terminal_class",
        "terminal_code",
        "profile_id",
        "program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_id",
        "request_nonce",
        "fixture_key",
        "occurrence_id",
        "session_external_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "lifecycle_status",
        "fixture_id",
        "observer_session_public_id",
        "public_fixture",
        "signed_batch_journal_closure",
        "signed_batch_journal_closure_id",
        "b3_attestation",
        "b3_attestation_id",
        "complete_observer_lifecycle",
        "private_replay_performed",
        "b3_sign_performed",
        "child_work",
        *set(_locks()),
        "child_result_id",
    }
)


def _validate_child_work(
    value: Any,
    *,
    terminal_code: str,
) -> dict[str, int]:
    expected_keys = set(
        _lifecycle_work(
            secret_verified=0,
            signer_load_attempts=0,
            signer_load_successes=0,
            reveal_signatures=0,
            session_open_calls=0,
            batch_observe_calls=0,
            accepted_draws=0,
            journal_append_calls=0,
            closure_calls=0,
            private_replay_calls=0,
            b3_sign_calls=0,
            public_replay_calls=0,
        )
    )
    if (
        type(value) is not dict
        or set(value) != expected_keys
        or any(type(item) is not int or item < 0 for item in value.values())
        or value["secret_fd_read_calls"] != 1
        or value["secret_commitment_checks"] not in {0, 1}
        or value["production_signer_load_attempts"] not in {0, 1}
        or value["production_signer_load_successes"] not in {0, 1}
        or value["production_signer_load_successes"]
        > value["production_signer_load_attempts"]
        or value["signer_load_challenge_signatures"]
        != value["production_signer_load_successes"]
        or value["reveal_attestation_signatures"] not in {0, 1}
        or value["reveal_attestation_signatures"]
        > value["production_signer_load_successes"]
        or value["observer_session_open_calls"] not in {0, 1}
        or value["observer_session_open_calls"]
        > value["reveal_attestation_signatures"]
        or value["batch_observe_calls"] not in {
            0,
            1,
            len(_REGISTERED_BATCH_PLAN),
        }
        or (
            value["batch_observe_calls"]
            and value["observer_session_open_calls"] != 1
        )
        or value["journal_append_calls"] != value["batch_observe_calls"]
        or value["accepted_draws"]
        != sum(
            plan["accepted_draw_count"]
            for plan in _REGISTERED_BATCH_PLAN[
                : value["batch_observe_calls"]
            ]
        )
        or value["batch_closure_calls"] not in {0, 1}
        or (
            value["batch_closure_calls"]
            and value["batch_observe_calls"] != len(_REGISTERED_BATCH_PLAN)
        )
        or value["private_replay_calls"] not in {0, 1}
        or value["private_replay_calls"] > value["batch_closure_calls"]
        or value["b3_sign_calls"] not in {0, 1}
        or value["b3_sign_calls"] != value["private_replay_calls"]
        or value["public_artifact_replay_calls_child"] not in {0, 1}
        or value["public_artifact_replay_calls_child"]
        > value["b3_sign_calls"]
        or value["old_closure_upgrade_calls"] != 0
        or value["old_b3_upgrade_calls"] != 0
    ):
        _fail("lifecycle child work is incomplete or causally inconsistent")
    zero_after_secret = {
        key: 0
        for key in expected_keys
        if key
        not in {
            "secret_fd_read_calls",
            "old_closure_upgrade_calls",
            "old_b3_upgrade_calls",
        }
    }
    if terminal_code == "SECRET_MATERIAL_INVALID" and any(
        value[key] != expected for key, expected in zero_after_secret.items()
    ):
        _fail("invalid secret child work crossed the secret boundary")
    if terminal_code == "SECRET_COMMITMENT_MISMATCH":
        expected = _lifecycle_work(
            secret_verified=0,
            signer_load_attempts=0,
            signer_load_successes=0,
            reveal_signatures=0,
            session_open_calls=0,
            batch_observe_calls=0,
            accepted_draws=0,
            journal_append_calls=0,
            closure_calls=0,
            private_replay_calls=0,
            b3_sign_calls=0,
            public_replay_calls=0,
        )
        if value != expected:
            _fail("commitment mismatch child work crossed into signer load")
    if terminal_code == "SIGNER_LOAD_FAILED":
        expected = _lifecycle_work(
            secret_verified=1,
            signer_load_attempts=1,
            signer_load_successes=0,
            reveal_signatures=0,
            session_open_calls=0,
            batch_observe_calls=0,
            accepted_draws=0,
            journal_append_calls=0,
            closure_calls=0,
            private_replay_calls=0,
            b3_sign_calls=0,
            public_replay_calls=0,
        )
        if value != expected:
            _fail("signer failure child work crossed into observer lifecycle")
    if terminal_code == "LIFECYCLE_EXECUTION_FAILED" and (
        value["secret_commitment_checks"] != 1
        or value["production_signer_load_attempts"] != 1
        or value["production_signer_load_successes"] != 1
    ):
        _fail("lifecycle failure work did not reach signer-owned execution")
    return value


def _validate_child_result(
    raw: bytes,
    *,
    request: Mapping[str, Any],
    replay_public_artifacts: bool = True,
) -> dict[str, Any]:
    item = _exact(
        _load(raw, label="lifecycle child result", cap=MAX_CHILD_RESULT_BYTES),
        _CHILD_COMMON_KEYS,
        label="lifecycle child result",
    )
    for key in (
        "profile_id",
        "program_id",
        "source_snapshot_id",
        "runtime_id",
        "request_id",
        "request_nonce",
        "fixture_key",
        "occurrence_id",
        "session_external_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
    ):
        if item[key] != request[key]:
            _fail("lifecycle child result crossed request identities")
    if (
        item["schema"]
        != "acfqp.v075_complete_observer_lifecycle_child_result.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["terminal_scope"] != TERMINAL_SCOPE
        or item["terminal_class"] != TERMINAL_CLASS
        or item["terminal_code"] not in _CHILD_TERMINAL_CODES
        or any(item[key] is not False for key in _locks())
    ):
        _fail("lifecycle child result schema or locks changed")
    _cid(item["child_result_id"], "lifecycle child result")
    _validate_child_work(
        item["child_work"],
        terminal_code=item["terminal_code"],
    )
    if item["terminal_code"] == COMPLETE_TERMINAL_CODE:
        if (
            item["lifecycle_status"]
            != "OPEN_OBSERVE_APPEND_CLOSE_PRIVATE_REPLAY_B3_COMPLETE"
            or item["complete_observer_lifecycle"] is not True
            or item["private_replay_performed"] is not True
            or item["b3_sign_performed"] is not True
        ):
            _fail("complete lifecycle child omitted a required stage")
        _cid(item["fixture_id"], "complete lifecycle fixture")
        _cid(
            item["observer_session_public_id"],
            "complete lifecycle session",
        )
        _cid(
            item["signed_batch_journal_closure_id"],
            "complete lifecycle closure",
        )
        _cid(item["b3_attestation_id"], "complete lifecycle B3")
        if replay_public_artifacts:
            _replay_complete_child_public_artifacts(
                request=request,
                child_document=item,
            )
        expected = _lifecycle_work(
            secret_verified=1,
            signer_load_attempts=1,
            signer_load_successes=1,
            reveal_signatures=1,
            session_open_calls=1,
            batch_observe_calls=len(_REGISTERED_BATCH_PLAN),
            accepted_draws=sum(
                value["accepted_draw_count"]
                for value in _REGISTERED_BATCH_PLAN
            ),
            journal_append_calls=len(_REGISTERED_BATCH_PLAN),
            closure_calls=1,
            private_replay_calls=1,
            b3_sign_calls=1,
            public_replay_calls=1,
        )
        if item["child_work"] != expected:
            _fail("complete lifecycle work differs from exact plan")
    else:
        if (
            item["lifecycle_status"] != "FAILED_BEFORE_COMPLETE_LIFECYCLE"
            or item["complete_observer_lifecycle"] is not False
            or item["private_replay_performed"] is not False
            or item["b3_sign_performed"] is not False
        ):
            _fail("failed lifecycle child emitted completion claims")
        for key in (
            "fixture_id",
            "observer_session_public_id",
            "public_fixture",
            "signed_batch_journal_closure",
            "signed_batch_journal_closure_id",
            "b3_attestation",
            "b3_attestation_id",
        ):
            _require_typed_null(
                item[key],
                reason=item["terminal_code"],
                label=f"failed lifecycle child {key}",
            )
    payload = {key: value for key, value in item.items() if key != "child_result_id"}
    if _hash("child_result", payload) != item["child_result_id"]:
        _fail("lifecycle child result identity changed")
    return item


@dataclass(slots=True)
class _TransportWork:
    source_archive_stage_attempts: int = 0
    process_launch_attempts: int = 0
    process_identity_capture_attempts: int = 0
    process_launches: int = 0
    process_exit_successes: int = 0
    process_exit_failures: int = 0
    parent_to_child_frames: int = 0
    child_to_parent_frames: int = 0
    parent_to_child_payload_bytes: int = 0
    child_to_parent_payload_bytes: int = 0
    framing_bytes: int = 0
    source_archive_staged_bytes: int = 0
    source_archive_seal_checks: int = 0
    secret_fd_seal_checks_parent: int = 0
    process_identity_checks: int = 0
    request_raw_replay_calls_parent: int = 0
    child_result_raw_replay_calls_parent: int = 0
    supervisor_checks: int = 0
    nonce_rejections: int = 0
    source_archive_staging_failure_events: int = 0
    process_launch_failure_events: int = 0
    process_identity_capture_failure_events: int = 0
    supervisor_protocol_failure_events: int = 0
    child_result_validation_failure_events: int = 0
    timeout_events: int = 0
    crash_events: int = 0
    stderr_bytes: int = 0

    def document(self, *, profile_id: str, request_id: str) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.v075_complete_observer_lifecycle_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": profile_id,
            "request_id": request_id,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "native_zero_required": True,
            "failure_path_work_retained": True,
        }
        return {**payload, "work_id": _hash("work", payload)}


def _validate_work_document(value: Any) -> dict[str, Any]:
    expected_counters = set(_TransportWork.__dataclass_fields__)
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "profile_id",
            "request_id",
            *expected_counters,
            "native_zero_required",
            "failure_path_work_retained",
            "work_id",
        },
        label="lifecycle transport work",
    )
    if (
        item["schema"]
        != "acfqp.v075_complete_observer_lifecycle_work.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["native_zero_required"] is not True
        or item["failure_path_work_retained"] is not True
        or any(
            type(item[key]) is not int or item[key] < 0
            for key in expected_counters
        )
        or item["process_launches"] not in {0, 1}
        or item["process_exit_successes"] not in {0, 1}
        or item["process_exit_failures"] not in {0, 1}
        or item["process_exit_successes"] + item["process_exit_failures"]
        != item["process_launches"]
        or item["parent_to_child_frames"] not in {0, 1}
        or item["child_to_parent_frames"] not in {0, 1}
    ):
        _fail("lifecycle transport work is malformed")
    _cid(item["profile_id"], "lifecycle work profile")
    _cid(item["request_id"], "lifecycle work request")
    _cid(item["work_id"], "lifecycle work")
    payload = {key: child for key, child in item.items() if key != "work_id"}
    if _hash("work", payload) != item["work_id"]:
        _fail("lifecycle transport work identity changed")
    return item


def _invalid_child_payload_id(
    *,
    payload_sha256: str,
    payload_byte_count: int,
) -> str:
    _cid(payload_sha256, "invalid lifecycle child payload digest")
    if type(payload_byte_count) is not int or payload_byte_count <= 0:
        _fail("invalid lifecycle child payload byte count is malformed")
    return _hash(
        "invalid_child_payload",
        {
            "schema": (
                "acfqp.v075_complete_observer_lifecycle_invalid_child.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "payload_sha256": payload_sha256,
            "payload_byte_count": payload_byte_count,
            "raw_payload_serialized": False,
        },
    )


def _journal_from_specs(
    specs: list[tuple[str, str, str, str, int]],
) -> dict[str, Any]:
    entries = []
    prior = hashlib.sha256(
        b"acfqp:v075-complete-observer-lifecycle-journal-initial:v1"
    ).hexdigest()
    for index, (
        direction,
        kind,
        message_id,
        payload_sha256,
        payload_byte_count,
    ) in enumerate(specs):
        payload = {
            "schema": (
                "acfqp.v075_complete_observer_lifecycle_journal_entry.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "index": index,
            "direction": direction,
            "message_kind": kind,
            "message_id": message_id,
            "payload_sha256": payload_sha256,
            "payload_byte_count": payload_byte_count,
            "prior_entry_id": prior,
        }
        entry = {
            **payload,
            "journal_entry_id": _hash("journal_entry", payload),
        }
        entries.append(entry)
        prior = entry["journal_entry_id"]
    payload = {
        "schema": "acfqp.v075_complete_observer_lifecycle_journal.v1",
        "schema_version": SCHEMA_VERSION,
        "entries": entries,
        "entry_count": len(entries),
        "head_id": prior,
        "exact_protocol_order": True,
    }
    return {**payload, "journal_id": _hash("journal", payload)}


def _journal(
    *,
    request_raw: bytes,
    request_id: str,
    child_raw: bytes | None,
    child_id: str | None,
    sent: bool,
) -> dict[str, Any]:
    if (
        type(request_raw) is not bytes
        or not request_raw
        or type(sent) is not bool
        or (child_id is not None and child_raw is None)
        or (child_raw is not None and not sent)
    ):
        _fail("lifecycle journal source messages are malformed")
    specs = [
        (
            "PARENT_TO_CHILD" if sent else "PARENT_VALIDATION",
            (
                "PUBLIC_LIFECYCLE_INTENT"
                if sent
                else "REJECTED_LIFECYCLE_REQUEST"
            ),
            request_id,
            hashlib.sha256(request_raw).hexdigest(),
            len(request_raw),
        )
    ]
    if child_raw is not None:
        child_digest = hashlib.sha256(child_raw).hexdigest()
        child_size = len(child_raw)
        if child_id is None:
            child_kind = "UNTYPED_INVALID_CHILD_RESULT"
            message_id = _invalid_child_payload_id(
                payload_sha256=child_digest,
                payload_byte_count=child_size,
            )
        else:
            child_document = _load(
                child_raw,
                label="typed lifecycle journal child",
                cap=MAX_CHILD_RESULT_BYTES,
            )
            terminal_code = child_document.get("terminal_code")
            if terminal_code == COMPLETE_TERMINAL_CODE:
                child_kind = "COMPLETE_LIFECYCLE_CONSTRUCTION_RESULT"
            elif terminal_code in _CHILD_TERMINAL_CODES:
                child_kind = "TYPED_LIFECYCLE_CONSTRUCTION_FAILURE"
            else:
                _fail("typed lifecycle journal child has no valid outcome")
            message_id = child_id
        specs.append(
            (
                "CHILD_TO_PARENT",
                child_kind,
                message_id,
                child_digest,
                child_size,
            )
        )
    return _journal_from_specs(specs)


def _invalid_child_journal_from_metadata(
    *,
    request_raw: bytes,
    request_id: str,
    payload_sha256: str,
    payload_byte_count: int,
) -> dict[str, Any]:
    return _journal_from_specs(
        [
            (
                "PARENT_TO_CHILD",
                "PUBLIC_LIFECYCLE_INTENT",
                request_id,
                hashlib.sha256(request_raw).hexdigest(),
                len(request_raw),
            ),
            (
                "CHILD_TO_PARENT",
                "UNTYPED_INVALID_CHILD_RESULT",
                _invalid_child_payload_id(
                    payload_sha256=payload_sha256,
                    payload_byte_count=payload_byte_count,
                ),
                payload_sha256,
                payload_byte_count,
            ),
        ]
    )


def _validate_journal_document(value: Any) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "entries",
            "entry_count",
            "head_id",
            "exact_protocol_order",
            "journal_id",
        },
        label="lifecycle journal",
    )
    if (
        item["schema"]
        != "acfqp.v075_complete_observer_lifecycle_journal.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or type(item["entries"]) is not list
        or not item["entries"]
        or item["entry_count"] != len(item["entries"])
        or item["entry_count"] not in {1, 2}
        or item["exact_protocol_order"] is not True
    ):
        _fail("lifecycle journal is malformed")
    prior = hashlib.sha256(
        b"acfqp:v075-complete-observer-lifecycle-journal-initial:v1"
    ).hexdigest()
    for index, value in enumerate(item["entries"]):
        entry = _exact(
            value,
            {
                "schema",
                "schema_version",
                "index",
                "direction",
                "message_kind",
                "message_id",
                "payload_sha256",
                "payload_byte_count",
                "prior_entry_id",
                "journal_entry_id",
            },
            label="lifecycle journal entry",
        )
        payload = {
            key: child
            for key, child in entry.items()
            if key != "journal_entry_id"
        }
        if (
            entry["schema"]
            != "acfqp.v075_complete_observer_lifecycle_journal_entry.v1"
            or entry["schema_version"] != SCHEMA_VERSION
            or entry["index"] != index
            or entry["prior_entry_id"] != prior
            or type(entry["payload_byte_count"]) is not int
            or entry["payload_byte_count"] <= 0
            or _cid(entry["message_id"], "lifecycle journal message")
            != entry["message_id"]
            or _cid(entry["payload_sha256"], "lifecycle journal payload")
            != entry["payload_sha256"]
            or _hash("journal_entry", payload)
            != entry["journal_entry_id"]
        ):
            _fail("lifecycle journal entry is malformed or stale")
        if index == 0:
            if (
                entry["direction"],
                entry["message_kind"],
            ) not in {
                ("PARENT_TO_CHILD", "PUBLIC_LIFECYCLE_INTENT"),
                ("PARENT_VALIDATION", "REJECTED_LIFECYCLE_REQUEST"),
            }:
                _fail("lifecycle request journal kind is unregistered")
        elif (
            entry["direction"] != "CHILD_TO_PARENT"
            or entry["message_kind"]
            not in {
                "COMPLETE_LIFECYCLE_CONSTRUCTION_RESULT",
                "TYPED_LIFECYCLE_CONSTRUCTION_FAILURE",
                "UNTYPED_INVALID_CHILD_RESULT",
            }
        ):
            _fail("lifecycle child journal kind is unregistered")
        if (
            entry["message_kind"] == "UNTYPED_INVALID_CHILD_RESULT"
            and entry["message_id"]
            != _invalid_child_payload_id(
                payload_sha256=entry["payload_sha256"],
                payload_byte_count=entry["payload_byte_count"],
            )
        ):
            _fail("invalid lifecycle child journal identity changed")
        prior = entry["journal_entry_id"]
    payload = {
        key: child for key, child in item.items() if key != "journal_id"
    }
    if (
        item["head_id"] != prior
        or _hash("journal", payload) != item["journal_id"]
        or (
            item["entries"][0]["direction"] == "PARENT_VALIDATION"
            and item["entry_count"] != 1
        )
        or (
            item["entry_count"] == 2
            and item["entries"][0]["direction"] != "PARENT_TO_CHILD"
        )
    ):
        _fail("lifecycle journal chain or identity changed")
    return item


def _supervisor_document(
    *,
    profile_id: str,
    request_id: str,
    process_id: str,
    child_result_id: str | None,
    outcome: str,
    nonce: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_complete_observer_lifecycle_supervisor.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "request_id": request_id,
        "process_id": process_id,
        "child_result_id": (
            child_result_id
            if child_result_id is not None
            else _typed_null("NO_VALID_CHILD_RESULT")
        ),
        "supervisor_nonce": nonce,
        "outcome": outcome,
        "local_process_attestation_only": True,
        "cryptographic_process_provenance": False,
        "os_sandbox_claimed": False,
    }
    return {**payload, "supervisor_id": _hash("supervisor", payload)}


def _validate_supervisor_document(value: Any) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "schema_version",
            "profile_id",
            "request_id",
            "process_id",
            "child_result_id",
            "supervisor_nonce",
            "outcome",
            "local_process_attestation_only",
            "cryptographic_process_provenance",
            "os_sandbox_claimed",
            "supervisor_id",
        },
        label="lifecycle supervisor",
    )
    for key in (
        "profile_id",
        "request_id",
        "process_id",
        "supervisor_nonce",
        "supervisor_id",
    ):
        _cid(item[key], f"lifecycle supervisor {key}")
    if (
        item["schema"]
        != "acfqp.v075_complete_observer_lifecycle_supervisor.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["outcome"] not in _ALLOWED_TERMINAL_CODES
        or item["local_process_attestation_only"] is not True
        or item["cryptographic_process_provenance"] is not False
        or item["os_sandbox_claimed"] is not False
        or type(item["child_result_id"]) not in {str, dict}
    ):
        _fail("lifecycle supervisor overclaims or is malformed")
    if type(item["child_result_id"]) is str:
        _cid(item["child_result_id"], "lifecycle supervisor child result")
    else:
        _require_typed_null(
            item["child_result_id"],
            reason="NO_VALID_CHILD_RESULT",
            label="lifecycle supervisor child result",
        )
    payload = {
        key: child
        for key, child in item.items()
        if key != "supervisor_id"
    }
    if _hash("supervisor", payload) != item["supervisor_id"]:
        _fail("lifecycle supervisor identity changed")
    return item


def _result_payload(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
    request: Mapping[str, Any],
    request_raw: bytes,
    terminal_code: str,
    child: Mapping[str, Any] | None,
    process: Mapping[str, Any],
    supervisor: Mapping[str, Any],
    journal: Mapping[str, Any],
    work: Mapping[str, Any],
    stderr: bytes,
) -> dict[str, Any]:
    complete = child is not None and terminal_code == COMPLETE_TERMINAL_CODE
    return {
        "schema": "acfqp.v075_complete_observer_lifecycle_ipc_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": terminal_code,
        "profile_id": profile.profile_id,
        "program_id": profile.program_id,
        "sealed_transport_profile_id": (
            profile.transport_profile.profile_id
        ),
        "source_snapshot_id": (
            profile.transport_profile.source_snapshot_id
        ),
        "runtime": {
            **deepcopy(dict(profile.transport_profile.runtime_document)),
            "runtime_id": profile.transport_profile.runtime_id,
        },
        "runtime_id": profile.transport_profile.runtime_id,
        "request_id": request["request_id"],
        "request_nonce": request["request_nonce"],
        "fixture_key": request["fixture_key"],
        "occurrence_id": request["occurrence_id"],
        "session_external_id": request["session_external_id"],
        "opaque_environment_commitment_id": (
            request["opaque_environment_commitment_id"]
        ),
        "signer_registry_id": request["signer_registry_id"],
        "observer_evidence_key_id": request["observer_evidence_key_id"],
        "request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "request_byte_count": len(request_raw),
        "child_result": (
            dict(child)
            if child is not None
            else _typed_null("NO_VALID_CHILD_RESULT")
        ),
        "child_result_id": (
            child["child_result_id"]
            if child is not None
            else _typed_null("NO_VALID_CHILD_RESULT")
        ),
        "observer_session_public_id": (
            child["observer_session_public_id"]
            if complete
            else _typed_null(terminal_code)
        ),
        "signed_batch_journal_closure_id": (
            child["signed_batch_journal_closure_id"]
            if complete
            else _typed_null(terminal_code)
        ),
        "b3_attestation_id": (
            child["b3_attestation_id"]
            if complete
            else _typed_null(terminal_code)
        ),
        "complete_observer_lifecycle": complete,
        "private_replay_performed": complete,
        "b3_sign_performed": complete,
        "synthetic_registered_fixture": True,
        "independent_remote_main_authority": False,
        "public_verifier_proves_public_bytes_only": True,
        "public_verifier_private_replay_performed": False,
        "cryptographic_process_provenance": False,
        "process": dict(process),
        "process_id": process["process_id"],
        "supervisor": dict(supervisor),
        "supervisor_id": supervisor["supervisor_id"],
        "journal": dict(journal),
        "journal_id": journal["journal_id"],
        "work": dict(work),
        "work_id": work["work_id"],
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stderr_byte_count": len(stderr),
        **_locks(),
    }


@dataclass(frozen=True, slots=True)
class V075CompleteObserverLifecycleIPCResultV1:
    _raw: bytes = field(repr=False)

    def __post_init__(self) -> None:
        document = _validate_result(
            _load(self._raw, label="lifecycle result", cap=MAX_RESULT_BYTES)
        )
        raw = _canonical(document)
        if raw != self._raw:
            _fail("lifecycle result cached bytes changed")
        object.__setattr__(self, "_raw", raw)

    @property
    def result_id(self) -> str:
        return self.to_document()["result_id"]

    @property
    def terminal_code(self) -> str:
        return self.to_document()["terminal_code"]

    @property
    def canonical_bytes(self) -> bytes:
        self.to_document()
        return self._raw

    def to_document(self) -> dict[str, Any]:
        return _validate_result(
            _load(self._raw, label="lifecycle result", cap=MAX_RESULT_BYTES)
        )


def _validate_result(document: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "terminal_scope",
        "terminal_class",
        "terminal_code",
        "profile_id",
        "program_id",
        "sealed_transport_profile_id",
        "source_snapshot_id",
        "runtime",
        "runtime_id",
        "request_id",
        "request_nonce",
        "fixture_key",
        "occurrence_id",
        "session_external_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "request_sha256",
        "request_byte_count",
        "child_result",
        "child_result_id",
        "observer_session_public_id",
        "signed_batch_journal_closure_id",
        "b3_attestation_id",
        "complete_observer_lifecycle",
        "private_replay_performed",
        "b3_sign_performed",
        "synthetic_registered_fixture",
        "independent_remote_main_authority",
        "public_verifier_proves_public_bytes_only",
        "public_verifier_private_replay_performed",
        "cryptographic_process_provenance",
        "process",
        "process_id",
        "supervisor",
        "supervisor_id",
        "journal",
        "journal_id",
        "work",
        "work_id",
        "stderr_sha256",
        "stderr_byte_count",
        *set(_locks()),
        "result_id",
    }
    item = _exact(document, required, label="lifecycle result")
    if (
        item["schema"]
        != "acfqp.v075_complete_observer_lifecycle_ipc_result.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["terminal_scope"] != TERMINAL_SCOPE
        or item["terminal_class"] != TERMINAL_CLASS
        or item["terminal_code"] not in _ALLOWED_TERMINAL_CODES
        or item["fixture_key"] != FIXTURE_KEY
        or item["synthetic_registered_fixture"] is not True
        or item["independent_remote_main_authority"] is not False
        or item["public_verifier_proves_public_bytes_only"] is not True
        or item["public_verifier_private_replay_performed"] is not False
        or item["cryptographic_process_provenance"] is not False
        or any(item[key] is not False for key in _locks())
    ):
        _fail("lifecycle result schema or locks changed")
    runtime = stage_a._validate_runtime_document(  # noqa: SLF001
        item["runtime"]
    )
    process = stage_a._validate_process_document(  # noqa: SLF001
        item["process"]
    )
    supervisor = _validate_supervisor_document(item["supervisor"])
    journal = _validate_journal_document(item["journal"])
    work = _validate_work_document(item["work"])
    if (
        runtime["runtime_id"] != item["runtime_id"]
        or process["process_id"] != item["process_id"]
        or supervisor["supervisor_id"] != item["supervisor_id"]
        or journal["journal_id"] != item["journal_id"]
        or work["work_id"] != item["work_id"]
        or supervisor["process_id"] != item["process_id"]
        or supervisor["request_id"] != item["request_id"]
        or supervisor["profile_id"] != item["profile_id"]
        or supervisor["outcome"] != item["terminal_code"]
        or work["profile_id"] != item["profile_id"]
        or work["request_id"] != item["request_id"]
        or work["process_launches"] != int(process["launched"])
        or work["process_identity_checks"]
        != int(process["identity_capture_complete"])
        or type(item["request_byte_count"]) is not int
        or item["request_byte_count"] <= 0
        or type(item["stderr_byte_count"]) is not int
        or item["stderr_byte_count"] < 0
        or work["stderr_bytes"] != item["stderr_byte_count"]
    ):
        _fail("lifecycle result nested transport identities changed")
    if (
        process["launched"]
        and process["identity_capture_complete"]
        and (
            process["executable_sha256"] != runtime["executable_sha256"]
            or process["executable_byte_count"]
            != runtime["executable_byte_count"]
        )
    ):
        _fail("lifecycle child executable differs from frozen runtime")
    terminal = item["terminal_code"]
    if (
        terminal in _PRELAUNCH_TERMINAL_CODES
        and process["launched"]
    ) or (
        terminal not in _PRELAUNCH_TERMINAL_CODES
        and not process["launched"]
    ):
        _fail("lifecycle process state disagrees with terminal outcome")
    child_present = (
        type(item["child_result"]) is dict
        and "child_result_id" in item["child_result"]
    )
    if child_present:
        projection = {
            key: item[key]
            for key in (
                "profile_id",
                "program_id",
                "source_snapshot_id",
                "runtime_id",
                "request_id",
                "request_nonce",
                "fixture_key",
                "occurrence_id",
                "session_external_id",
                "opaque_environment_commitment_id",
                "signer_registry_id",
                "observer_evidence_key_id",
            )
        }
        child_raw = _canonical(item["child_result"])
        child = _validate_child_result(
            child_raw,
            request=projection,
            replay_public_artifacts=False,
        )
        if (
            child["child_result_id"] != item["child_result_id"]
            or child["terminal_code"] != terminal
            or supervisor["child_result_id"] != child["child_result_id"]
            or journal["entry_count"] != 2
            or journal["entries"][1]["message_kind"]
            != (
                "COMPLETE_LIFECYCLE_CONSTRUCTION_RESULT"
                if terminal == COMPLETE_TERMINAL_CODE
                else "TYPED_LIFECYCLE_CONSTRUCTION_FAILURE"
            )
            or journal["entries"][1]["message_id"]
            != child["child_result_id"]
            or journal["entries"][1]["payload_sha256"]
            != hashlib.sha256(child_raw).hexdigest()
            or journal["entries"][1]["payload_byte_count"] != len(child_raw)
        ):
            _fail("lifecycle child result identity changed")
    else:
        _require_typed_null(
            item["child_result"],
            reason="NO_VALID_CHILD_RESULT",
            label="lifecycle missing child result",
        )
        top_null = _require_typed_null(
            item["child_result_id"],
            reason="NO_VALID_CHILD_RESULT",
            label="lifecycle missing child identity",
        )
        supervisor_null = _require_typed_null(
            supervisor["child_result_id"],
            reason="NO_VALID_CHILD_RESULT",
            label="lifecycle supervisor missing child identity",
        )
        if top_null != supervisor_null:
            _fail("lifecycle missing child identities differ")
        if terminal == "CHILD_RESULT_VALIDATION_FAILED":
            if (
                journal["entry_count"] != 2
                or journal["entries"][1]["message_kind"]
                != "UNTYPED_INVALID_CHILD_RESULT"
                or work["child_to_parent_payload_bytes"]
                != journal["entries"][1]["payload_byte_count"]
            ):
                _fail("invalid lifecycle child evidence is incomplete")
        elif (
            terminal not in _NO_CHILD_TERMINAL_CODES
            or journal["entry_count"] != 1
        ):
            _fail("lifecycle result lacks its mandatory child")
    complete = terminal == COMPLETE_TERMINAL_CODE
    if (
        (complete and not child_present)
        or item["complete_observer_lifecycle"] is not complete
        or item["private_replay_performed"] is not complete
        or item["b3_sign_performed"] is not complete
    ):
        _fail("lifecycle aggregate completion matrix changed")
    if complete:
        child = item["child_result"]
        for key in (
            "observer_session_public_id",
            "signed_batch_journal_closure_id",
            "b3_attestation_id",
        ):
            _cid(item[key], f"complete lifecycle result {key}")
            if item[key] != child[key]:
                _fail("complete lifecycle outer artifact identity changed")
    else:
        for key in (
            "observer_session_public_id",
            "signed_batch_journal_closure_id",
            "b3_attestation_id",
        ):
            _require_typed_null(
                item[key],
                reason=terminal,
                label=f"incomplete lifecycle result {key}",
            )
    request_entry = journal["entries"][0]
    sent = int(process["identity_capture_complete"])
    expected_child_frame = int(
        terminal in _CHILD_TERMINAL_CODES
        or terminal == "CHILD_RESULT_VALIDATION_FAILED"
    )
    expected_events = {
        "nonce_rejections": int(terminal == "NONCE_REPLAY_REJECTED"),
        "source_archive_staging_failure_events": int(
            terminal == "SOURCE_ARCHIVE_STAGING_FAILED"
        ),
        "process_launch_failure_events": int(
            terminal == "PROCESS_LAUNCH_FAILED"
        ),
        "process_identity_capture_failure_events": int(
            terminal == "PROCESS_IDENTITY_CAPTURE_FAILED"
        ),
        "supervisor_protocol_failure_events": int(
            terminal == "SUPERVISOR_PROTOCOL_FAILURE"
        ),
        "child_result_validation_failure_events": int(
            terminal == "CHILD_RESULT_VALIDATION_FAILED"
        ),
        "timeout_events": int(terminal == "CHILD_TIMEOUT"),
        "crash_events": int(
            terminal
            in {
                "CHILD_CRASH",
                "CHILD_FRAME_INVALID",
                "CHILD_EXTRA_OUTPUT",
                "CHILD_OUTPUT_CAP_EXCEEDED",
                "CHILD_STDERR_CAP_EXCEEDED",
                "CHILD_STDERR_FORBIDDEN",
            }
        ),
    }
    if (
        request_entry["message_id"] != item["request_id"]
        or request_entry["payload_sha256"] != item["request_sha256"]
        or request_entry["payload_byte_count"] != item["request_byte_count"]
        or request_entry["direction"]
        != ("PARENT_TO_CHILD" if sent else "PARENT_VALIDATION")
        or work["source_archive_stage_attempts"]
        != int(terminal != "NONCE_REPLAY_REJECTED")
        or work["process_launch_attempts"]
        != int(
            terminal
            not in {
                "NONCE_REPLAY_REJECTED",
                "SOURCE_ARCHIVE_STAGING_FAILED",
            }
        )
        or work["process_identity_capture_attempts"]
        != int(process["launched"])
        or work["parent_to_child_frames"] != sent
        or work["child_to_parent_frames"] != expected_child_frame
        or work["parent_to_child_payload_bytes"]
        != (item["request_byte_count"] if sent else 0)
        or work["framing_bytes"]
        != stage_a._FRAME_WIDTH * (sent + expected_child_frame)  # noqa: SLF001
        or work["secret_fd_seal_checks_parent"] != 1
        or work["request_raw_replay_calls_parent"] != 1
        or work["child_result_raw_replay_calls_parent"]
        != expected_child_frame
        or work["supervisor_checks"] != 1
        or any(work[key] != value for key, value in expected_events.items())
    ):
        _fail("lifecycle outcome, journal, and work disagree")
    for key in (
        "profile_id",
        "program_id",
        "sealed_transport_profile_id",
        "source_snapshot_id",
        "runtime_id",
        "request_id",
        "request_nonce",
        "occurrence_id",
        "session_external_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "request_sha256",
        "stderr_sha256",
        "result_id",
    ):
        _cid(item[key], f"lifecycle result {key}")
    payload = {key: value for key, value in item.items() if key != "result_id"}
    if _hash("result", payload) != item["result_id"]:
        _fail("lifecycle result identity changed")
    return item


class V075CompleteObserverLifecycleServiceV1:
    __slots__ = ("profile", "_nonces", "_lock")

    def __init__(self, profile: V075CompleteObserverLifecycleProfileV1) -> None:
        if type(profile) is not V075CompleteObserverLifecycleProfileV1:
            _fail("complete lifecycle service profile is untyped")
        profile._assert_current()
        self.profile = profile
        self._nonces: set[str] = set()
        self._lock = threading.Lock()

    def consume(self, nonce: str) -> bool:
        _cid(nonce, "complete lifecycle nonce")
        with self._lock:
            if nonce in self._nonces:
                return False
            self._nonces.add(nonce)
            return True

    def __reduce__(self) -> NoReturn:
        raise TypeError("complete lifecycle services are process-local")


def start_v075_complete_observer_lifecycle_service_v1(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
) -> V075CompleteObserverLifecycleServiceV1:
    return V075CompleteObserverLifecycleServiceV1(profile)


def _freeze_result(
    payload: Mapping[str, Any],
) -> V075CompleteObserverLifecycleIPCResultV1:
    result_payload = dict(payload)
    return V075CompleteObserverLifecycleIPCResultV1(
        _canonical(
            {
                **result_payload,
                "result_id": _hash("result", result_payload),
            }
        )
    )


def _prelaunch_nonce_result(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
    request: Mapping[str, Any],
    request_raw: bytes,
) -> V075CompleteObserverLifecycleIPCResultV1:
    process = stage_a._process_document(  # noqa: SLF001
        start=None,
        exit_code=None,
        launched=False,
        reaped=True,
    )
    journal = _journal(
        request_raw=request_raw,
        request_id=request["request_id"],
        child_raw=None,
        child_id=None,
        sent=False,
    )
    work = _TransportWork(
        secret_fd_seal_checks_parent=1,
        request_raw_replay_calls_parent=1,
        supervisor_checks=1,
        nonce_rejections=1,
    ).document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
    )
    supervisor = _supervisor_document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
        process_id=process["process_id"],
        child_result_id=None,
        outcome="NONCE_REPLAY_REJECTED",
        nonce=hashlib.sha256(os.urandom(32)).hexdigest(),
    )
    return _freeze_result(
        _result_payload(
            profile=profile,
            request=request,
            request_raw=request_raw,
            terminal_code="NONCE_REPLAY_REJECTED",
            child=None,
            process=process,
            supervisor=supervisor,
            journal=journal,
            work=work,
            stderr=b"",
        )
    )


def _close_supervisor_result(
    *,
    profile: V075CompleteObserverLifecycleProfileV1,
    request: Mapping[str, Any],
    request_raw: bytes,
    outcome: str,
    recorder: _TransportWork,
    process: subprocess.Popen[bytes] | None,
    start: Mapping[str, Any] | None,
    child: Mapping[str, Any] | None,
    child_raw: bytes | None,
    stderr: bytes,
    exit_code: int | None,
) -> V075CompleteObserverLifecycleIPCResultV1:
    launched = process is not None
    if launched and process.poll() is None:
        stage_a._terminate(process)  # noqa: SLF001
    if launched:
        exit_code = process.poll()
        if type(exit_code) is not int:
            _fail("complete lifecycle child could not be reaped")
    process_document = stage_a._process_document(  # noqa: SLF001
        start=start,
        exit_code=exit_code,
        launched=launched,
        reaped=(not launched or process.poll() is not None),
    )
    sent = recorder.parent_to_child_frames == 1
    journal_child_raw = (
        child_raw
        if child is not None or outcome == "CHILD_RESULT_VALIDATION_FAILED"
        else None
    )
    journal = _journal(
        request_raw=request_raw,
        request_id=request["request_id"],
        child_raw=journal_child_raw,
        child_id=None if child is None else child["child_result_id"],
        sent=sent,
    )
    recorder.supervisor_checks = 1
    work = recorder.document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
    )
    supervisor = _supervisor_document(
        profile_id=profile.profile_id,
        request_id=request["request_id"],
        process_id=process_document["process_id"],
        child_result_id=None if child is None else child["child_result_id"],
        outcome=outcome,
        nonce=hashlib.sha256(os.urandom(32)).hexdigest(),
    )
    return _freeze_result(
        _result_payload(
            profile=profile,
            request=request,
            request_raw=request_raw,
            terminal_code=outcome,
            child=child,
            process=process_document,
            supervisor=supervisor,
            journal=journal,
            work=work,
            stderr=stderr,
        )
    )


def execute_v075_complete_observer_lifecycle_v1(
    *,
    service: V075CompleteObserverLifecycleServiceV1,
    request_bytes: bytes,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
    sealed_secret_fd: int,
) -> V075CompleteObserverLifecycleIPCResultV1:
    if type(service) is not V075CompleteObserverLifecycleServiceV1:
        _fail("complete lifecycle execute received a foreign service")
    profile = service.profile
    profile._assert_current()
    request = verify_v075_complete_observer_lifecycle_request_bytes_v1(
        request_bytes
    ).to_document()
    transport = profile.transport_profile
    if (
        request["profile_id"] != profile.profile_id
        or request["program_id"] != profile.program_id
        or request["source_snapshot_id"] != transport.source_snapshot_id
        or request["runtime_id"] != transport.runtime_id
    ):
        _fail("complete lifecycle request was profile-transplanted")
    for value, label in (
        (repository_root, "repository root"),
        (signer_private_root, "private signer root"),
        (signer_private_key_path, "private signer key path"),
    ):
        if not isinstance(value, Path) or not value.is_absolute():
            _fail(f"{label} must be one absolute pathlib.Path")
    stage_a._verify_sealed_fd(  # noqa: SLF001
        sealed_secret_fd,
        cap=MAX_SECRET_BYTES,
    )
    if not service.consume(request["request_nonce"]):
        return _prelaunch_nonce_result(
            profile=profile,
            request=request,
            request_raw=request_bytes,
        )
    recorder = _TransportWork(
        secret_fd_seal_checks_parent=1,
        request_raw_replay_calls_parent=1,
    )
    archive_fd: int | None = None
    process: subprocess.Popen[bytes] | None = None
    start: dict[str, Any] | None = None
    child_raw: bytes | None = None
    child: dict[str, Any] | None = None
    stderr = b""
    exit_code: int | None = None
    failure: str | None = None
    operation_stage = "SOURCE_ARCHIVE_STAGING"
    try:
        recorder.source_archive_stage_attempts = 1
        archive_fd = stage_a._stage_sealed_bytes(  # noqa: SLF001
            transport._archive_bytes,  # noqa: SLF001
            name=f"acfqp-v075-stage-b-{profile.profile_id[:12]}",
            cap=stage_a.MAX_SOURCE_ARCHIVE_BYTES,
        )
        recorder.source_archive_staged_bytes = (
            transport.source_archive_byte_count
        )
        recorder.source_archive_seal_checks = 1
        operation_stage = "PROCESS_LAUNCH"
        recorder.process_launch_attempts = 1
        with tempfile.TemporaryDirectory(
            prefix="acfqp-v075-complete-observer-lifecycle-"
        ) as sandbox:
            process = subprocess.Popen(
                _child_argv(
                    profile=profile,
                    archive_fd=archive_fd,
                    secret_fd=sealed_secret_fd,
                    repository_root=repository_root,
                    signer_private_root=signer_private_root,
                    signer_private_key_path=signer_private_key_path,
                ),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox,
                env={
                    "LC_ALL": "C.UTF-8",
                    "LANG": "C.UTF-8",
                    "TZ": "UTC",
                    "PYTHONHASHSEED": "0",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                close_fds=True,
                pass_fds=(archive_fd, sealed_secret_fd),
                start_new_session=True,
            )
            recorder.process_launches = 1
            operation_stage = "PROCESS_IDENTITY_CAPTURE"
            recorder.process_identity_capture_attempts = 1
            start = stage_a._capture_start(process)  # noqa: SLF001
            recorder.process_identity_checks = 1
            operation_stage = "SUPERVISOR_PROTOCOL"
            recorder.parent_to_child_frames = 1
            recorder.parent_to_child_payload_bytes = len(request_bytes)
            recorder.framing_bytes = stage_a._FRAME_WIDTH  # noqa: SLF001
            child_raw, stderr, exit_code, failure = stage_a._exchange(  # noqa: SLF001
                process,
                request_raw=request_bytes,
                deadline=(
                    time.monotonic()
                    + transport.timeout_milliseconds / 1000
                ),
            )
            stage_a._terminate(process)  # noqa: SLF001
            recorder.stderr_bytes = len(stderr)
            if child_raw is not None:
                recorder.child_to_parent_frames = 1
                recorder.child_to_parent_payload_bytes = len(child_raw)
                recorder.framing_bytes += stage_a._FRAME_WIDTH  # noqa: SLF001
                recorder.child_result_raw_replay_calls_parent = 1
                operation_stage = "CHILD_RESULT_VALIDATION"
                child = _validate_child_result(
                    child_raw,
                    request=request,
                )
            if failure == "CHILD_TIMEOUT":
                recorder.timeout_events = 1
            elif failure is not None:
                recorder.crash_events = 1
    except BaseException:
        if process is not None:
            stage_a._terminate(process)  # noqa: SLF001
        failure = {
            "SOURCE_ARCHIVE_STAGING": "SOURCE_ARCHIVE_STAGING_FAILED",
            "PROCESS_LAUNCH": "PROCESS_LAUNCH_FAILED",
            "PROCESS_IDENTITY_CAPTURE": (
                "PROCESS_IDENTITY_CAPTURE_FAILED"
            ),
            "SUPERVISOR_PROTOCOL": "SUPERVISOR_PROTOCOL_FAILURE",
            "CHILD_RESULT_VALIDATION": "CHILD_RESULT_VALIDATION_FAILED",
        }[operation_stage]
        if failure == "SOURCE_ARCHIVE_STAGING_FAILED":
            recorder.source_archive_staging_failure_events = 1
        elif failure == "PROCESS_LAUNCH_FAILED":
            recorder.process_launch_failure_events = 1
        elif failure == "PROCESS_IDENTITY_CAPTURE_FAILED":
            recorder.process_identity_capture_failure_events = 1
        elif failure == "CHILD_RESULT_VALIDATION_FAILED":
            recorder.child_result_validation_failure_events = 1
            child = None
        else:
            recorder.supervisor_protocol_failure_events = 1
            child = None
    finally:
        if process is not None:
            stage_a._terminate(process)  # noqa: SLF001
            exit_code = process.poll()
            if type(exit_code) is int and exit_code == 0:
                recorder.process_exit_successes = 1
            else:
                recorder.process_exit_failures = 1
        if archive_fd is not None:
            try:
                os.close(archive_fd)
            except OSError:
                pass
    outcome = (
        child["terminal_code"]
        if child is not None
        else failure or "CHILD_CRASH"
    )
    return _close_supervisor_result(
        profile=profile,
        request=request,
        request_raw=request_bytes,
        outcome=outcome,
        recorder=recorder,
        process=process,
        start=start,
        child=child,
        child_raw=child_raw,
        stderr=stderr,
        exit_code=exit_code,
    )


def verify_v075_complete_observer_lifecycle_result_bytes_v1(
    *,
    raw: bytes,
    request_bytes: bytes,
    profile: V075CompleteObserverLifecycleProfileV1,
) -> V075CompleteObserverLifecycleIPCResultV1:
    if type(profile) is not V075CompleteObserverLifecycleProfileV1:
        _fail("complete lifecycle verifier profile is untyped")
    profile._assert_current()
    request = verify_v075_complete_observer_lifecycle_request_bytes_v1(
        request_bytes
    ).to_document()
    result = V075CompleteObserverLifecycleIPCResultV1(raw)
    document = result.to_document()
    transport = profile.transport_profile
    expected_runtime = {
        **deepcopy(dict(transport.runtime_document)),
        "runtime_id": transport.runtime_id,
    }
    for key, expected in (
        ("profile_id", profile.profile_id),
        ("program_id", profile.program_id),
        ("sealed_transport_profile_id", transport.profile_id),
        ("source_snapshot_id", transport.source_snapshot_id),
        ("runtime_id", transport.runtime_id),
        ("request_id", request["request_id"]),
        ("request_nonce", request["request_nonce"]),
        ("fixture_key", request["fixture_key"]),
        ("occurrence_id", request["occurrence_id"]),
        ("session_external_id", request["session_external_id"]),
        (
            "opaque_environment_commitment_id",
            request["opaque_environment_commitment_id"],
        ),
        ("signer_registry_id", request["signer_registry_id"]),
        ("observer_evidence_key_id", request["observer_evidence_key_id"]),
    ):
        if document[key] != expected:
            _fail("complete lifecycle result was request-transplanted")
    if (
        document["runtime"] != expected_runtime
        or
        document["request_sha256"]
        != hashlib.sha256(request_bytes).hexdigest()
        or document["request_byte_count"] != len(request_bytes)
    ):
        _fail("complete lifecycle request bytes changed")
    child = document["child_result"]
    process = document["process"]
    if type(child) is dict and "child_result_id" in child:
        child_raw = _canonical(child)
        replayed = _validate_child_result(child_raw, request=request)
        if replayed != child:
            _fail("complete lifecycle child replay changed")
        expected_journal = _journal(
            request_raw=request_bytes,
            request_id=request["request_id"],
            child_raw=child_raw,
            child_id=child["child_result_id"],
            sent=True,
        )
    elif document["terminal_code"] == "CHILD_RESULT_VALIDATION_FAILED":
        invalid_entry = document["journal"]["entries"][1]
        expected_journal = _invalid_child_journal_from_metadata(
            request_raw=request_bytes,
            request_id=request["request_id"],
            payload_sha256=invalid_entry["payload_sha256"],
            payload_byte_count=invalid_entry["payload_byte_count"],
        )
    else:
        expected_journal = _journal(
            request_raw=request_bytes,
            request_id=request["request_id"],
            child_raw=None,
            child_id=None,
            sent=bool(process["launched"]),
        )
    if document["journal"] != expected_journal:
        _fail("complete lifecycle journal differs from exact replay")
    work = document["work"]
    child_present = type(child) is dict and "child_result_id" in child
    child_frame = child_present or (
        document["terminal_code"] == "CHILD_RESULT_VALIDATION_FAILED"
    )
    if (
        work["source_archive_staged_bytes"]
        != (
            transport.source_archive_byte_count
            if work["source_archive_seal_checks"]
            else 0
        )
        or work["source_archive_seal_checks"]
        != int(
            document["terminal_code"]
            not in {
                "NONCE_REPLAY_REJECTED",
                "SOURCE_ARCHIVE_STAGING_FAILED",
            }
        )
        or work["child_to_parent_payload_bytes"]
        != (
            len(_canonical(child))
            if child_present
            else (
                document["journal"]["entries"][1]["payload_byte_count"]
                if child_frame
                else 0
            )
        )
        or work["process_exit_successes"]
        != int(
            process["launched"]
            and type(process["exit_code"]) is int
            and process["exit_code"] == 0
        )
        or work["process_exit_failures"]
        != int(
            process["launched"]
            and type(process["exit_code"]) is int
            and process["exit_code"] != 0
        )
    ):
        _fail("complete lifecycle work differs from public protocol replay")
    return result


def open_v075_complete_observer_lifecycle_production_v1() -> NoReturn:
    raise V075SignerOwningCompleteLifecycleProductionV1NotReady(
        "contract-1.71 completes one synthetic registered root-only K7 "
        "observer lifecycle, but independent source/code authority, portable "
        "registry closure, fresh-held-out campaign integration, and external "
        "audit remain incomplete"
    )


__all__ = [
    "CODE_PROVENANCE_COMPLETE",
    "COMPLETE_TERMINAL_CODE",
    "FIXTURE_KEY",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "SYNTHETIC_ROOT_LIFECYCLE_IMPLEMENTED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075CompleteObserverLifecycleIPCResultV1",
    "V075CompleteObserverLifecycleProfileV1",
    "V075CompleteObserverLifecycleRequestV1",
    "V075CompleteObserverLifecycleServiceV1",
    "V075SignerOwningCompleteLifecycleProductionV1NotReady",
    "V075SignerOwningCompleteLifecycleV1InvariantViolation",
    "execute_v075_complete_observer_lifecycle_v1",
    "freeze_v075_complete_observer_lifecycle_profile_v1",
    "freeze_v075_complete_observer_lifecycle_request_v1",
    "open_v075_complete_observer_lifecycle_production_v1",
    "start_v075_complete_observer_lifecycle_service_v1",
    "verify_v075_complete_observer_lifecycle_request_bytes_v1",
    "verify_v075_complete_observer_lifecycle_result_bytes_v1",
]
