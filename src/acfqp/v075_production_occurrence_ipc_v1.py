"""Isolated, parent-owned adaptive occurrence IPC for production V0-075.

The mutable observer, hidden law, reveal salt, signing key, and exact kernels
remain in the parent.  One fresh ``python -I`` child is launched for exactly
one logical occurrence.  The only bytes crossing the process boundary are
strict canonical JSON frames.

The child reconstructs the public occurrence graph, source-prior transport,
signed aggregate batches, batch-native statistical backend, learned-support
planner, and failed-proof acquisition authority.  It emits content-addressed
batch/support/round intents.  The parent validates the public capability
surface and caps, executes only those intents through its already-open
parent-owned observer lifecycle, and returns signed public aggregate bytes.

The operational parent deliberately does not replay the backend or planner.
``verify_v075_occurrence_ipc_result_standalone_v1`` is a separate,
evaluation-only full replay API.

This component opens no target authority.  Construction sessions are accepted
only to exercise the exact process boundary before the final production
preregistration exists; construction and production scopes remain explicit in
every launch and result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_production_occurrence_ipc_v1"

PRODUCTION_TRANSPORT_READY = True
PRODUCTION_OCCURRENCE_WORKER_COMPLETE = False
MATCHED_DIRECT_HANDLER_READY = False
TARGET_EXECUTION_OPENED = False
PRIVATE_MATERIAL_TRANSPORT_ALLOWED = False
PICKLE_TRANSPORT_ALLOWED = False
HOST_OPERATIONAL_FULL_PLANNER_REPLAY_ALLOWED = False

MAX_FRAME_BYTES = 16 * 1024 * 1024
MAX_CHILD_STDERR_BYTES = 256 * 1024
MAX_PROTOCOL_MESSAGES = 65_536
MAX_BATCH_INTENTS = 65_536
DEFAULT_PROCESS_TIMEOUT_SECONDS = 3_600
MAX_PROCESS_TIMEOUT_SECONDS = 21_600

_FRAME_WIDTH = 8
_CHILD_ARG = "--acfqp-v075-production-occurrence-child"

_DOMAINS = {
    "program": "acfqp:v075-production-occurrence-child-program:v1",
    "profile": "acfqp:v075-production-occurrence-ipc-profile:v1",
    "launch": "acfqp:v075-production-occurrence-ipc-launch:v1",
    "batch_intent": "acfqp:v075-production-occurrence-batch-intent:v1",
    "batch_response": "acfqp:v075-production-occurrence-batch-response:v1",
    "support_intent": "acfqp:v075-production-occurrence-support-intent:v1",
    "support_response": "acfqp:v075-production-occurrence-support-response:v1",
    "round_begin": "acfqp:v075-production-occurrence-round-begin:v1",
    "round_ack": "acfqp:v075-production-occurrence-round-ack:v1",
    "child_result": "acfqp:v075-production-occurrence-child-result:v1",
    "journal_entry": "acfqp:v075-production-occurrence-ipc-journal-entry:v1",
    "journal": "acfqp:v075-production-occurrence-ipc-journal:v1",
    "work": "acfqp:v075-production-occurrence-ipc-work:v1",
    "result": "acfqp:v075-production-occurrence-ipc-result:v1",
    "standalone_verification": (
        "acfqp:v075-production-occurrence-ipc-standalone-verification:v1"
    ),
}

if len(_DOMAINS) != len(set(_DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 production occurrence IPC domains must be unique")

_INITIAL_JOURNAL_HASH = hashlib.sha256(
    b"acfqp:v075-production-occurrence-ipc-journal-initial:v1"
).hexdigest()


class V075ProductionOccurrenceIPCInvariantViolation(ValueError):
    """A public identity, protocol, cap, sequence, or process invariant failed."""


def _fail(message: str) -> None:
    raise V075ProductionOccurrenceIPCInvariantViolation(message)


def _canonical_bytes(value: Any) -> bytes:
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
        raise V075ProductionOccurrenceIPCInvariantViolation(
            str(error)
        ) from error


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("canonical IPC JSON contains a duplicate key")
        result[key] = value
    return result


def _load_canonical(raw: bytes, *, field_name: str) -> Any:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_FRAME_BYTES
    ):
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
        if isinstance(error, V075ProductionOccurrenceIPCInvariantViolation):
            raise
        raise V075ProductionOccurrenceIPCInvariantViolation(
            f"{field_name} is not canonical JSON: {error}"
        ) from error
    if _canonical_bytes(value) != raw:
        _fail(f"{field_name} is not canonical JSON")
    return value


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _DOMAINS[role].encode("utf-8")
    except KeyError as error:  # pragma: no cover
        raise RuntimeError("unknown V0-075 production IPC domain") from error
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


def _same_document(claimed: Any, expected: Any, field_name: str) -> None:
    if (
        type(claimed) is not dict
        or claimed != expected
        or _canonical_bytes(claimed) != _canonical_bytes(expected)
    ):
        _fail(f"{field_name} differs from exact public reconstruction")


def _module_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class V075ProductionIPCBehaviorV1(str, Enum):
    HONEST = "HONEST"
    ATTACK_SEQUENCE_GAP = "ATTACK_SEQUENCE_GAP"
    ATTACK_UNKNOWN_FIELD = "ATTACK_UNKNOWN_FIELD"
    ATTACK_TRANSPLANT_STREAM = "ATTACK_TRANSPLANT_STREAM"
    ATTACK_EXTRA_BATCH_INTENT = "ATTACK_EXTRA_BATCH_INTENT"


@dataclass(frozen=True, slots=True)
class V075ProductionIPCChildProgramRegistrationV1:
    module_sha256: str
    argv: tuple[str, ...] = (_CHILD_ARG,)
    _registration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.module_sha256, "production child module digest")
        if (
            self.argv != (_CHILD_ARG,)
            or self.module_sha256 != _module_digest()
        ):
            _fail("production child program registration is stale")
        object.__setattr__(
            self,
            "_registration_id",
            _hash("program", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_occurrence_child_program.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "module_sha256": self.module_sha256,
            "argv": list(self.argv),
            "one_fresh_process_per_occurrence": True,
            "canonical_json_frames_only": True,
            "pickle_transport_allowed": False,
            "arbitrary_callback_allowed": False,
            "private_observer_in_child": False,
            "production_transport_ready": True,
        }

    @property
    def registration_id(self) -> str:
        return self._registration_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registration_id": self.registration_id}


def registered_v075_production_occurrence_child_program_v1(
) -> V075ProductionIPCChildProgramRegistrationV1:
    return V075ProductionIPCChildProgramRegistrationV1(_module_digest())


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrenceIPCProfileV1:
    occurrence_identity: Any = field(repr=False)
    open_lifecycle_binding: Any = field(repr=False)
    context: Any = field(repr=False)
    source_prior_transport: Any | None = field(default=None, repr=False)
    process_timeout_seconds: int = DEFAULT_PROCESS_TIMEOUT_SECONDS
    behavior: V075ProductionIPCBehaviorV1 = (
        V075ProductionIPCBehaviorV1.HONEST
    )
    program_registration: V075ProductionIPCChildProgramRegistrationV1 = field(
        default_factory=registered_v075_production_occurrence_child_program_v1
    )
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import v075_batch_native_statistical_backend_v1 as backend
        from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
        from acfqp import v075_public_campaign_authority_v1 as public
        from acfqp import v075_registered_occurrence_worker_v1 as worker

        if (
            type(self.occurrence_identity)
            is not backend.V075BatchNativeOccurrenceIdentityV1
            or type(self.open_lifecycle_binding)
            is not lifecycle.V075OpenMultistageLifecycleBindingV1
            or type(self.context) is not public.V075PublicReplicateContextV1
            or type(self.behavior) is not V075ProductionIPCBehaviorV1
            or type(self.program_registration)
            is not V075ProductionIPCChildProgramRegistrationV1
            or self.program_registration
            != registered_v075_production_occurrence_child_program_v1()
            or type(self.process_timeout_seconds) is not int
            or not 0 < self.process_timeout_seconds
            <= MAX_PROCESS_TIMEOUT_SECONDS
        ):
            _fail("production occurrence IPC profile is untyped or over cap")
        identity = self.occurrence_identity
        binding = self.open_lifecycle_binding
        if (
            binding.occurrence_id != identity.occurrence_id
            or binding.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or binding.context_id != identity.context_id
            or binding.context_id != self.context.context_id
            or binding.arm is not identity.arm
            or binding.route_cap_profile_id != identity.cap_profile_id
            or self.context not in binding.namespace.family.replicate_contexts
            or (
                self.source_prior_transport is not None
                and type(self.source_prior_transport)
                is not worker.V075SourcePriorTransportV1
            )
            or (
                self.source_prior_transport is not None
            )
            != (
                identity.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            )
            or identity.source_transport_id
            != (
                None
                if self.source_prior_transport is None
                else self.source_prior_transport.transport_id
            )
        ):
            _fail("IPC profile is occurrence, context, arm, or source transplanted")
        if (
            binding.authority_scope.value == "PRODUCTION_OPEN"
            and self.behavior is not V075ProductionIPCBehaviorV1.HONEST
        ):
            _fail("production authority rejects construction attack behavior")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        identity = self.occurrence_identity
        binding = self.open_lifecycle_binding
        route = (
            "MATCHED_DIRECT_GROUND"
            if identity.arm.value == "MATCHED_DIRECT_GROUND"
            else "ADAPTIVE_QUOTIENT"
        )
        return {
            "schema": "acfqp.v075_production_occurrence_ipc_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": identity.occurrence_id,
            "target_tape_namespace_id": identity.target_tape_namespace_id,
            "context_id": identity.context_id,
            "arm": identity.arm.value,
            "route": route,
            "occurrence_ordinal": identity.occurrence_ordinal,
            "authority_scope": binding.authority_scope.value,
            "observer_open_binding_id": binding.observer_open_binding_id,
            "session_public_id": binding.session_public_id,
            "threshold_profile_id": identity.threshold_profile_id,
            "cap_profile_id": identity.cap_profile_id,
            "source_transport_id": identity.source_transport_id,
            "program_registration_id": (
                self.program_registration.registration_id
            ),
            "process_timeout_seconds": self.process_timeout_seconds,
            "max_protocol_messages": MAX_PROTOCOL_MESSAGES,
            "max_batch_intents": MAX_BATCH_INTENTS,
            "behavior": self.behavior.value,
            "one_fresh_process_per_occurrence": True,
            "parent_owns_private_observer": True,
            "canonical_json_frames_only": True,
            "pickle_transport_allowed": False,
            "host_operational_full_planner_replay_allowed": False,
            "target_execution_opened": False,
            "production_occurrence_worker_complete": False,
            "matched_direct_handler_ready": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_identity": self.occurrence_identity.to_document(),
            "open_lifecycle_binding": (
                self.open_lifecycle_binding.to_document()
            ),
            "context": self.context.to_document(),
            "source_prior_transport": (
                None
                if self.source_prior_transport is None
                else self.source_prior_transport.to_document()
            ),
            "program_registration": self.program_registration.to_document(),
            "profile_id": self.profile_id,
        }


def freeze_v075_production_occurrence_ipc_profile_v1(
    *,
    occurrence_identity: Any,
    open_lifecycle_binding: Any,
    context: Any,
    source_prior_transport: Any | None = None,
    process_timeout_seconds: int = DEFAULT_PROCESS_TIMEOUT_SECONDS,
    behavior: V075ProductionIPCBehaviorV1 = (
        V075ProductionIPCBehaviorV1.HONEST
    ),
) -> V075ProductionOccurrenceIPCProfileV1:
    return V075ProductionOccurrenceIPCProfileV1(
        occurrence_identity,
        open_lifecycle_binding,
        context,
        source_prior_transport,
        process_timeout_seconds,
        behavior,
    )


def _launch_document(
    profile: V075ProductionOccurrenceIPCProfileV1,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_ipc_launch.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile.profile_id,
        "program_registration_id": (
            profile.program_registration.registration_id
        ),
        "program_module_sha256": profile.program_registration.module_sha256,
        "occurrence_identity": profile.occurrence_identity.to_document(),
        "open_lifecycle_binding": (
            profile.open_lifecycle_binding.to_document()
        ),
        "namespace": (
            profile.open_lifecycle_binding.namespace.to_document()
        ),
        "context": profile.context.to_document(),
        "source_prior_transport": (
            None
            if profile.source_prior_transport is None
            else profile.source_prior_transport.to_document()
        ),
        "threshold_profile": (
            __import__(
                "acfqp.v075_registered_occurrence_worker_v1",
                fromlist=["V075WorkerThresholdProfileV1"],
            )
            .V075WorkerThresholdProfileV1()
            .to_document()
        ),
        "cap_profile": (
            profile.open_lifecycle_binding.route_cap_profile.to_document()
        ),
        "process_timeout_seconds": profile.process_timeout_seconds,
        "max_protocol_messages": MAX_PROTOCOL_MESSAGES,
        "max_batch_intents": MAX_BATCH_INTENTS,
        "behavior": profile.behavior.value,
        "parent_private_session_serialized": False,
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_signer_serialized": False,
        "private_kernel_serialized": False,
        "callback_serialized": False,
        "pickle_transport_used": False,
        "target_execution_opened": False,
    }
    return {**payload, "launch_id": _hash("launch", payload)}


# ---------------------------------------------------------------------------
# Strict public reconstruction used inside the isolated child and standalone
# verifier.  Every accepted nested document is compared to the complete
# canonical document regenerated from typed public constructors.
# ---------------------------------------------------------------------------


def _load_public_key(document: Any) -> Any:
    from acfqp import v075_public_campaign_authority_v1 as public

    item = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "key_role",
            "algorithm",
            "modulus_hex",
            "public_exponent",
            "minimum_modulus_bits",
            "private_key_serialized",
            "key_id",
        },
        field_name="public verification key",
    )
    if (
        item["schema"] != "acfqp.v075_rsa_public_verification_key.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["algorithm"] != "RSASSA-PKCS1-v1_5-SHA256"
        or type(item["modulus_hex"]) is not str
        or not item["modulus_hex"]
    ):
        _fail("public verification key contract changed")
    try:
        result = public.V075RSAPublicVerificationKeyV1(
            item["key_role"],
            int(item["modulus_hex"], 16),
            item["public_exponent"],
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "public verification key is invalid"
        ) from error
    _same_document(item, result.to_document(), "public verification key")
    return result


def _load_namespace(document: Any) -> Any:
    from acfqp import v075_public_campaign_authority_v1 as public

    if type(document) is not dict:
        _fail("target namespace is not one canonical object")
    family = public.freeze_v075_public_family_generation_v1()
    _same_document(document.get("family"), family.to_document(), "public family")
    registry_doc = document.get("signer_registry")
    if type(registry_doc) is not dict:
        _fail("target namespace signer registry is malformed")
    campaign_key = _load_public_key(registry_doc.get("campaign_authority_key"))
    observer_key = _load_public_key(registry_doc.get("observer_evidence_key"))
    registry = public.V075TrustedSignerRegistryV1(
        campaign_key,
        observer_key,
    )
    _same_document(
        registry_doc,
        registry.to_document(),
        "target namespace signer registry",
    )
    commitment_doc = document.get("environment_commitment")
    if type(commitment_doc) is not dict:
        _fail("target namespace commitment is malformed")
    commitment = public.V075OpaqueEnvironmentCommitmentV1(
        family,
        commitment_doc.get("commitment_digest"),
    )
    _same_document(
        commitment_doc,
        commitment.to_document(),
        "target namespace commitment",
    )

    def claim(name: str, role: Any) -> Any:
        value = document.get(name)
        if type(value) is not dict:
            _fail(f"target namespace {name} claim is malformed")
        result = public.V075SignedExternalAuthorityClaimV1(
            registry,
            role,
            value.get("external_id"),
            value.get("signature_hex"),
        )
        _same_document(value, result.to_document(), f"target namespace {name}")
        return result

    role = public.V075ExternalAuthorityRoleV1
    result = public.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=(
            document.get("claimed_final_preregistration_registry_id")
        ),
        remote_main_anchor=claim(
            "remote_main_anchor",
            role.REMOTE_MAIN_ANCHOR,
        ),
        final_preregistration=claim(
            "final_preregistration",
            role.FINAL_PREREGISTRATION,
        ),
        observer_profile=claim(
            "observer_profile",
            role.OBSERVER_PROFILE,
        ),
    )
    _same_document(document, result.to_document(), "target namespace")
    return result


def _load_context(document: Any, namespace: Any) -> Any:
    from acfqp import v075_public_campaign_authority_v1 as public

    if type(document) is not dict:
        _fail("public context is not one object")
    try:
        result = public.registered_public_context_v1(
            public.V075PublicReplicateContextV1(
                document.get("replicate_ordinal")
            )
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "public context is not registered"
        ) from error
    if result not in namespace.family.replicate_contexts:
        _fail("public context escaped the target namespace")
    _same_document(document, result.to_document(), "public context")
    return result


def _load_observer_binding(document: Any, namespace: Any) -> Any:
    from acfqp import v075_private_observer_boundary_v1 as observer

    if type(document) is not dict:
        _fail("observer-open binding is malformed")
    try:
        result = observer.V075ObserverOpenAuthorityBindingV1(
            namespace,
            document.get("upstream_authority_id"),
            document.get("verification_attestation_id"),
            observer.V075ObserverOpenAuthorityScopeV1(
                document.get("scope")
            ),
            document.get("independent_final_authority_verified"),
            document.get("observer_open_authorized"),
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "observer-open binding reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "observer-open binding")
    return result


def _load_state(document: Any, context: Any) -> Any:
    from acfqp import v075_public_graph_semantics_v1 as graph

    if type(document) is not dict:
        _fail("symbolic state is malformed")
    _same_document(document.get("context"), context.to_document(), "state context")
    try:
        result = graph.V075SymbolicGraphStateV1(
            context,
            tuple(document.get("ranks", ())),
            document.get("failure"),
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "symbolic state reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "symbolic state")
    return result


def _load_catalogue(document: Any, context: Any) -> Any:
    from acfqp import v075_public_graph_semantics_v1 as graph

    if type(document) is not dict:
        _fail("legal-action catalogue is malformed")
    _same_document(
        document.get("context"),
        context.to_document(),
        "catalogue context",
    )
    state = _load_state(document.get("state"), context)
    try:
        actions = tuple(
            tuple(action) for action in document.get("actions", ())
        )
        result = graph.V075LegalActionCatalogueV1(
            context,
            state,
            document.get("remaining_horizon"),
            actions,
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "legal-action catalogue reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "legal-action catalogue")
    return result


def _load_row(document: Any, context: Any) -> Any:
    from acfqp import v075_public_graph_semantics_v1 as graph

    if type(document) is not dict:
        _fail("row binding is malformed")
    _same_document(document.get("context"), context.to_document(), "row context")
    catalogue = _load_catalogue(document.get("catalogue"), context)
    try:
        result = graph.observation_row_binding_v1(
            context,
            catalogue,
            tuple(document.get("action", ())),
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "row binding reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "row binding")
    return result


def _load_support_evidence(
    document: Any,
    *,
    namespace: Any,
    row: Any,
    context: Any,
) -> Any:
    from acfqp import v075_public_graph_semantics_v1 as graph

    if type(document) is not dict:
        _fail("support evidence is malformed")
    _same_document(
        document.get("namespace"),
        namespace.to_document(),
        "support evidence namespace",
    )
    _same_document(
        document.get("row_binding"),
        row.to_document(),
        "support evidence row",
    )
    state = _load_state(document.get("observed_state"), context)
    schema = document.get("schema")
    try:
        if schema == "acfqp.v075_batch_aggregate_support_evidence.v1":
            result = graph.bind_batch_aggregate_support_evidence_v1(
                namespace=namespace,
                row_binding=row,
                observed_state=state,
                source_observer_epoch_index=(
                    document.get("source_observer_epoch_index")
                ),
                discovery_request_id=document.get("discovery_request_id"),
                discovery_batch_id=document.get("discovery_batch_id"),
                discovery_outcome_id=document.get("discovery_outcome_id"),
                discovery_outcome_count=(
                    document.get("discovery_outcome_count")
                ),
                observer_signature_hex=(
                    document.get("observer_signature_hex")
                ),
            )
        elif schema == "acfqp.v075_heldout_support_evidence.v2":
            result = graph.bind_support_evidence_v1(
                namespace=namespace,
                row_binding=row,
                observed_state=state,
                source_observer_epoch_index=(
                    document.get("source_observer_epoch_index")
                ),
                accepted_draw_index=document.get("accepted_draw_index"),
                observer_signature_hex=(
                    document.get("observer_signature_hex")
                ),
            )
        else:
            _fail("support evidence schema is unknown")
    except (TypeError, ValueError) as error:
        if isinstance(error, V075ProductionOccurrenceIPCInvariantViolation):
            raise
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "support evidence reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "support evidence")
    return result


def _load_stream(document: Any, namespace: Any, context: Any) -> Any:
    from acfqp import v075_public_graph_semantics_v1 as graph

    if type(document) is not dict:
        _fail("stream identity is malformed")
    pairing_document = document.get("pairing_authority")
    if type(pairing_document) is not dict:
        _fail("stream pairing authority is malformed")
    _same_document(
        pairing_document.get("namespace"),
        namespace.to_document(),
        "stream namespace",
    )
    row = _load_row(pairing_document.get("row_binding"), context)
    chain_document = pairing_document.get("support_chain")
    if type(chain_document) is not dict:
        _fail("stream support chain is malformed")
    _same_document(
        chain_document.get("namespace"),
        namespace.to_document(),
        "support chain namespace",
    )
    _same_document(
        chain_document.get("row_binding"),
        row.to_document(),
        "support chain row",
    )
    epoch_documents = chain_document.get("epochs")
    if type(epoch_documents) is not list or not epoch_documents:
        _fail("support chain epochs are empty or malformed")
    epochs: list[Any] = []
    for expected_index, epoch_document in enumerate(epoch_documents):
        if type(epoch_document) is not dict:
            _fail("support epoch is malformed")
        _same_document(
            epoch_document.get("namespace"),
            namespace.to_document(),
            "support epoch namespace",
        )
        _same_document(
            epoch_document.get("row_binding"),
            row.to_document(),
            "support epoch row",
        )
        evidence_documents = epoch_document.get("evidence")
        if type(evidence_documents) is not list:
            _fail("support epoch evidence registry is malformed")
        evidence = tuple(
            _load_support_evidence(
                value,
                namespace=namespace,
                row=row,
                context=context,
            )
            for value in evidence_documents
        )
        epoch = graph.derive_shared_support_epoch_v1(
            namespace=namespace,
            row_binding=row,
            epoch_index=expected_index,
            evidence=evidence,
            parent=None if not epochs else epochs[-1],
        )
        _same_document(epoch_document, epoch.to_document(), "support epoch")
        epochs.append(epoch)
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=tuple(epochs),
    )
    _same_document(chain_document, chain.to_document(), "support chain")
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    _same_document(
        pairing_document,
        pairing.to_document(),
        "stream pairing authority",
    )
    try:
        stream = graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=document.get("arm"),
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "stream identity reconstruction failed"
        ) from error
    _same_document(document, stream.to_document(), "stream identity")
    return stream


def _load_request(
    document: Any,
    *,
    namespace: Any,
    context: Any,
    observer_binding: Any,
    session_public_id: str,
) -> Any:
    from acfqp import v075_batched_observer_authority_v1 as batched

    if type(document) is not dict:
        _fail("signed-batch request is malformed")
    _same_document(
        document.get("observer_open_binding"),
        observer_binding.to_document(),
        "request observer binding",
    )
    stream = _load_stream(
        document.get("stream_identity"),
        namespace,
        context,
    )
    try:
        result = batched.V075BatchedObservationRequestV1(
            batched._REQUEST_ISSUER,
            session_public_id,
            observer_binding,
            stream,
            batched.V075BatchAuthorityScopeV1(
                document.get("authority_scope")
            ),
            document.get("accepted_draw_start"),
            document.get("accepted_draw_count"),
            document.get("accepted_draw_cap"),
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "signed-batch request reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "signed-batch request")
    return result


def _load_signed_batch(
    document: Any,
    *,
    namespace: Any,
    context: Any,
    observer_binding: Any,
    session_public_id: str,
) -> Any:
    from acfqp import v075_batched_observer_authority_v1 as batched

    if type(document) is not dict:
        _fail("signed public batch is malformed")
    request = _load_request(
        document.get("request"),
        namespace=namespace,
        context=context,
        observer_binding=observer_binding,
        session_public_id=session_public_id,
    )
    try:
        result = batched.load_v075_signed_batched_observation_v1(
            raw=_canonical_bytes(document),
            request=request,
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "signed public batch reconstruction failed"
        ) from error
    return result


def _load_source_transport(document: Any) -> Any | None:
    from acfqp import v075_registered_occurrence_worker_v1 as worker

    if document is None:
        return None
    if type(document) is not dict:
        _fail("source-prior transport is malformed")
    try:
        result = worker._source_transport_from_document(document)
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "source-prior transport reconstruction failed"
        ) from error
    _same_document(document, result.to_document(), "source-prior transport")
    return result


def _load_launch(raw: bytes) -> dict[str, Any]:
    from acfqp import v075_batch_native_statistical_backend_v1 as backend
    from acfqp import v075_registered_occurrence_worker_v1 as worker

    item = _exact_mapping(
        _load_canonical(raw, field_name="production child launch"),
        {
            "schema",
            "schema_version",
            "profile_id",
            "program_registration_id",
            "program_module_sha256",
            "occurrence_identity",
            "open_lifecycle_binding",
            "namespace",
            "context",
            "source_prior_transport",
            "threshold_profile",
            "cap_profile",
            "process_timeout_seconds",
            "max_protocol_messages",
            "max_batch_intents",
            "behavior",
            "parent_private_session_serialized",
            "private_law_serialized",
            "private_salt_serialized",
            "private_signer_serialized",
            "private_kernel_serialized",
            "callback_serialized",
            "pickle_transport_used",
            "target_execution_opened",
            "launch_id",
        },
        field_name="production child launch",
    )
    payload = dict(item)
    claimed_launch_id = payload.pop("launch_id")
    registration = registered_v075_production_occurrence_child_program_v1()
    if (
        item["schema"]
        != "acfqp.v075_production_occurrence_ipc_launch.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["program_registration_id"] != registration.registration_id
        or item["program_module_sha256"] != registration.module_sha256
        or item["max_protocol_messages"] != MAX_PROTOCOL_MESSAGES
        or item["max_batch_intents"] != MAX_BATCH_INTENTS
        or type(item["process_timeout_seconds"]) is not int
        or not 0 < item["process_timeout_seconds"]
        <= MAX_PROCESS_TIMEOUT_SECONDS
        or any(
            item[key] is not False
            for key in (
                "parent_private_session_serialized",
                "private_law_serialized",
                "private_salt_serialized",
                "private_signer_serialized",
                "private_kernel_serialized",
                "callback_serialized",
                "pickle_transport_used",
                "target_execution_opened",
            )
        )
        or _cid(claimed_launch_id, "production launch")
        != _hash("launch", payload)
    ):
        _fail("production child launch is stale, private, or unregistered")
    namespace = _load_namespace(item["namespace"])
    context = _load_context(item["context"], namespace)
    open_document = item["open_lifecycle_binding"]
    if type(open_document) is not dict:
        _fail("open lifecycle binding is malformed")
    observer_binding = _load_observer_binding(
        open_document.get("observer_open_binding"),
        namespace,
    )
    source_transport = _load_source_transport(item["source_prior_transport"])
    threshold = worker.V075WorkerThresholdProfileV1()
    caps = worker.V075WorkerCapProfileV1()
    _same_document(
        item["threshold_profile"],
        threshold.to_document(),
        "worker threshold profile",
    )
    _same_document(
        item["cap_profile"],
        caps.to_document(),
        "worker cap profile",
    )
    identity_document = item["occurrence_identity"]
    if type(identity_document) is not dict:
        _fail("occurrence identity is malformed")
    try:
        arm = worker.V075WorkerArmV1(identity_document.get("arm"))
        identity = backend.freeze_v075_batch_native_occurrence_identity_v1(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=identity_document.get("occurrence_ordinal"),
            threshold_profile=threshold,
            cap_profile=caps,
            source_prior_transport=source_transport,
        )
    except (TypeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "occurrence identity reconstruction failed"
        ) from error
    _same_document(
        identity_document,
        identity.to_document(),
        "occurrence identity",
    )
    if (
        open_document.get("occurrence_id") != identity.occurrence_id
        or open_document.get("context_id") != context.context_id
        or open_document.get("arm") != arm.value
        or open_document.get("route_cap_profile_id")
        != caps.cap_profile_id
        or open_document.get("namespace") != namespace.to_document()
        or open_document.get("observer_open_binding")
        != observer_binding.to_document()
        or open_document.get("target_tape_namespace_id")
        != namespace.target_tape_namespace_id
        or item["profile_id"]
        != _hash(
            "profile",
            {
                "schema": (
                    "acfqp.v075_production_occurrence_ipc_profile.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "occurrence_id": identity.occurrence_id,
                "target_tape_namespace_id": identity.target_tape_namespace_id,
                "context_id": identity.context_id,
                "arm": identity.arm.value,
                "route": (
                    "MATCHED_DIRECT_GROUND"
                    if identity.arm.value == "MATCHED_DIRECT_GROUND"
                    else "ADAPTIVE_QUOTIENT"
                ),
                "occurrence_ordinal": identity.occurrence_ordinal,
                "authority_scope": open_document.get("authority_scope"),
                "observer_open_binding_id": (
                    observer_binding.binding_id
                ),
                "session_public_id": open_document.get("session_public_id"),
                "threshold_profile_id": identity.threshold_profile_id,
                "cap_profile_id": identity.cap_profile_id,
                "source_transport_id": identity.source_transport_id,
                "program_registration_id": registration.registration_id,
                "process_timeout_seconds": item["process_timeout_seconds"],
                "max_protocol_messages": MAX_PROTOCOL_MESSAGES,
                "max_batch_intents": MAX_BATCH_INTENTS,
                "behavior": item["behavior"],
                "one_fresh_process_per_occurrence": True,
                "parent_owns_private_observer": True,
                "canonical_json_frames_only": True,
                "pickle_transport_allowed": False,
                "host_operational_full_planner_replay_allowed": False,
                "target_execution_opened": False,
                "production_occurrence_worker_complete": False,
                "matched_direct_handler_ready": False,
            },
        )
    ):
        _fail("production child launch identity graph is inconsistent")
    try:
        behavior = V075ProductionIPCBehaviorV1(item["behavior"])
    except ValueError as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "production child behavior is unknown"
        ) from error
    if (
        open_document.get("authority_scope") == "PRODUCTION_OPEN"
        and behavior is not V075ProductionIPCBehaviorV1.HONEST
    ):
        _fail("production-open child rejects attack behavior")
    return {
        **item,
        "_namespace": namespace,
        "_context": context,
        "_observer_binding": observer_binding,
        "_source_transport": source_transport,
        "_threshold": threshold,
        "_caps": caps,
        "_identity": identity,
        "_arm": arm,
        "_behavior": behavior,
    }


def _write_frame(stream: Any, raw: bytes) -> None:
    if type(raw) is not bytes or not raw or len(raw) > MAX_FRAME_BYTES:
        _fail("IPC frame is empty, mistyped, or over cap")
    header = f"{len(raw):0{_FRAME_WIDTH}x}".encode("ascii")
    try:
        stream.write(header + raw)
        stream.flush()
    except (BrokenPipeError, OSError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "IPC frame write failed"
        ) from error


def _read_exact_fd(fd: int, count: int, deadline: float) -> bytes:
    result = bytearray()
    while len(result) < count:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _fail("production occurrence child exceeded its frozen timeout")
        ready, _, _ = select.select([fd], [], [], remaining)
        if not ready:
            _fail("production occurrence child exceeded its frozen timeout")
        chunk = os.read(fd, count - len(result))
        if not chunk:
            _fail("production occurrence child closed a partial frame")
        result.extend(chunk)
    return bytes(result)


def _read_frame_fd(fd: int, deadline: float) -> bytes:
    header = _read_exact_fd(fd, _FRAME_WIDTH, deadline)
    try:
        length = int(header.decode("ascii"), 16)
    except (UnicodeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "IPC frame header is malformed"
        ) from error
    if not 0 < length <= MAX_FRAME_BYTES:
        _fail("IPC frame length is outside its cap")
    return _read_exact_fd(fd, length, deadline)


def _read_frame_child(stream: Any) -> bytes:
    header = stream.read(_FRAME_WIDTH)
    if type(header) is not bytes or len(header) != _FRAME_WIDTH:
        _fail("child received a truncated frame header")
    try:
        length = int(header.decode("ascii"), 16)
    except (UnicodeError, ValueError) as error:
        raise V075ProductionOccurrenceIPCInvariantViolation(
            "child frame header is malformed"
        ) from error
    if not 0 < length <= MAX_FRAME_BYTES:
        _fail("child frame length is outside its cap")
    raw = stream.read(length)
    if type(raw) is not bytes or len(raw) != length:
        _fail("child received a truncated frame")
    return raw


def _message_id(
    *,
    role: str,
    payload: dict[str, Any],
    id_field: str,
) -> dict[str, Any]:
    if id_field in payload:
        _fail("protocol payload attempted to prefill its content ID")
    return {**payload, id_field: _hash(role, payload)}


def _batch_intent_document(
    *,
    profile_id: str,
    occurrence_id: str,
    sequence_number: int,
    phase: str,
    round_index: int,
    intent_kind: str,
    scientific_intent_id: str,
    authorization_id: str | None,
    stream: Any,
    accepted_draw_start: int,
    accepted_draw_count: int,
    accepted_draw_cap: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_batch_intent.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "sequence_number": sequence_number,
        "phase": phase,
        "round_index": round_index,
        "intent_kind": intent_kind,
        "scientific_intent_id": scientific_intent_id,
        "authorization_id": authorization_id,
        "target_tape_namespace_id": stream.target_tape_namespace_id,
        "context_id": stream.context_id,
        "row_binding_id": stream.row_binding_id,
        "stream_id": stream.stream_id,
        "lane": stream.lane.value,
        "arm": stream.arm,
        "observer_epoch_index": stream.observer_epoch_index,
        "accepted_draw_start": accepted_draw_start,
        "accepted_draw_count": accepted_draw_count,
        "accepted_draw_end": accepted_draw_start + accepted_draw_count - 1,
        "accepted_draw_cap": accepted_draw_cap,
        "stream_identity": stream.to_document(),
        "private_material_serialized": False,
    }
    return _message_id(
        role="batch_intent",
        payload=payload,
        id_field="intent_id",
    )


def _support_intent_document(
    *,
    profile_id: str,
    occurrence_id: str,
    sequence_number: int,
    phase: str,
    round_index: int,
    scientific_intent_id: str,
    authorization_id: str | None,
    discovery_batch: Any,
    selected_outcome_ids: tuple[str, ...],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_support_intent.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "sequence_number": sequence_number,
        "phase": phase,
        "round_index": round_index,
        "scientific_intent_id": scientific_intent_id,
        "authorization_id": authorization_id,
        "discovery_request_id": discovery_batch.request.request_id,
        "discovery_batch_id": discovery_batch.batch_id,
        "row_binding_id": (
            discovery_batch.request.stream_identity.row_binding_id
        ),
        "selected_outcome_ids": list(selected_outcome_ids),
        "private_material_serialized": False,
    }
    return _message_id(
        role="support_intent",
        payload=payload,
        id_field="support_intent_id",
    )


def _round_begin_document(
    *,
    profile_id: str,
    occurrence_id: str,
    sequence_number: int,
    round_index: int,
    prior_backend_result_id: str,
    prior_planner_result_id: str,
    frontier: Any,
    authorization: Any,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_round_begin.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "sequence_number": sequence_number,
        "round_index": round_index,
        "prior_backend_result_id": prior_backend_result_id,
        "prior_planner_result_id": prior_planner_result_id,
        "frontier_id": frontier.frontier_id,
        "authorization_id": authorization.authorization_id,
        "authorization_status": authorization.status.value,
        "scientific_intent_ids": [
            item.intent_id for item in authorization.intents
        ],
        "frontier": frontier.to_document(),
        "authorization": authorization.to_document(),
        "private_material_serialized": False,
    }
    return _message_id(
        role="round_begin",
        payload=payload,
        id_field="round_begin_id",
    )


def _response_document(
    *,
    profile_id: str,
    occurrence_id: str,
    sequence_number: int,
    request_message_id: str,
    signed_batch: Any,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_batch_response.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "sequence_number": sequence_number,
        "request_message_id": request_message_id,
        "request_id": signed_batch.request.request_id,
        "batch_id": signed_batch.batch_id,
        "signed_public_batch": signed_batch.to_document(),
        "private_replay_serialized": False,
        "private_material_serialized": False,
    }
    return _message_id(
        role="batch_response",
        payload=payload,
        id_field="response_id",
    )


def _support_response_document(
    *,
    profile_id: str,
    occurrence_id: str,
    sequence_number: int,
    support_intent_id: str,
    evidence: tuple[Any, ...],
    validation_stream: Any,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_support_response.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "sequence_number": sequence_number,
        "support_intent_id": support_intent_id,
        "evidence_ids": [item.evidence_id for item in evidence],
        "evidence": [item.to_document() for item in evidence],
        "validation_stream_id": validation_stream.stream_id,
        "validation_stream_identity": validation_stream.to_document(),
        "private_material_serialized": False,
    }
    return _message_id(
        role="support_response",
        payload=payload,
        id_field="response_id",
    )


def _round_ack_document(
    *,
    profile_id: str,
    occurrence_id: str,
    sequence_number: int,
    round_begin_id: str,
    round_index: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_production_occurrence_round_ack.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "occurrence_id": occurrence_id,
        "sequence_number": sequence_number,
        "round_begin_id": round_begin_id,
        "round_index": round_index,
        "parent_lifecycle_round_started": True,
    }
    return _message_id(
        role="round_ack",
        payload=payload,
        id_field="ack_id",
    )


def _strip_id_and_verify(
    document: dict[str, Any],
    *,
    role: str,
    id_field: str,
    field_name: str,
) -> None:
    claimed = _cid(document.get(id_field), field_name)
    payload = dict(document)
    payload.pop(id_field, None)
    if claimed != _hash(role, payload):
        _fail(f"{field_name} content identity mismatch")


def _support_outcome_ids(discovery_batch: Any) -> tuple[str, ...]:
    from acfqp import v075_public_graph_semantics_v1 as graph

    row = discovery_batch.request.stream_identity.row_binding
    selected: dict[str, str] = {}
    for outcome in discovery_batch.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            row.context,
            outcome.next_ranks,
            outcome.failure,
        )
        prior = selected.get(state.state_id)
        if prior is None or outcome.outcome_id < prior:
            selected[state.state_id] = outcome.outcome_id
    result = tuple(sorted(selected.values()))
    if not result:
        _fail("discovery batch exposed no symbolic support")
    return result


def _bootstrap_stream(namespace: Any, row: Any, arm: Any) -> tuple[Any, Any]:
    from acfqp import v075_public_graph_semantics_v1 as graph

    root_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return (
        root_epoch,
        graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=arm.value,
        ),
    )


def _validation_stream(
    namespace: Any,
    row: Any,
    root_epoch: Any,
    evidence: tuple[Any, ...],
    arm: Any,
) -> Any:
    from acfqp import v075_public_graph_semantics_v1 as graph

    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=evidence,
        parent=root_epoch,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(root_epoch, epoch),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm.value,
    )


class _ChildProtocolV1:
    def __init__(self, launch: dict[str, Any]) -> None:
        self.launch = launch
        self.sequence = 0
        self.batches: list[Any] = []
        self.behavior = launch["_behavior"]
        self.attack_used = False

    def _send(self, document: dict[str, Any]) -> bytes:
        self.sequence += 1
        if document.get("sequence_number") != self.sequence:
            _fail("child protocol sequence was constructed incorrectly")
        outgoing = dict(document)
        if (
            not self.attack_used
            and self.behavior
            is V075ProductionIPCBehaviorV1.ATTACK_SEQUENCE_GAP
        ):
            outgoing["sequence_number"] += 1
            payload = dict(outgoing)
            id_field = (
                "intent_id"
                if outgoing["schema"].endswith("batch_intent.v1")
                else next(
                    key
                    for key in (
                        "support_intent_id",
                        "round_begin_id",
                    )
                    if key in outgoing
                )
            )
            payload.pop(id_field)
            role = {
                "intent_id": "batch_intent",
                "support_intent_id": "support_intent",
                "round_begin_id": "round_begin",
            }[id_field]
            outgoing[id_field] = _hash(role, payload)
            self.attack_used = True
        elif (
            not self.attack_used
            and self.behavior
            is V075ProductionIPCBehaviorV1.ATTACK_UNKNOWN_FIELD
        ):
            outgoing["unknown_field"] = True
            self.attack_used = True
        raw = _canonical_bytes(outgoing)
        _write_frame(sys.stdout.buffer, raw)
        return raw

    def request_batch(
        self,
        *,
        stream: Any,
        phase: str,
        round_index: int,
        intent_kind: str,
        scientific_intent_id: str,
        authorization_id: str | None,
        accepted_draw_start: int,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> Any:
        if (
            not self.attack_used
            and self.behavior
            is V075ProductionIPCBehaviorV1.ATTACK_TRANSPLANT_STREAM
        ):
            # A real, typed stream from another registered context is not
            # available without a different namespace graph.  Mutating one
            # identity field is sufficient to exercise strict reconstruction.
            document = _batch_intent_document(
                profile_id=self.launch["profile_id"],
                occurrence_id=self.launch["_identity"].occurrence_id,
                sequence_number=self.sequence + 1,
                phase=phase,
                round_index=round_index,
                intent_kind=intent_kind,
                scientific_intent_id=scientific_intent_id,
                authorization_id=authorization_id,
                stream=stream,
                accepted_draw_start=accepted_draw_start,
                accepted_draw_count=accepted_draw_count,
                accepted_draw_cap=accepted_draw_cap,
            )
            document["context_id"] = hashlib.sha256(
                b"v075-production-ipc-transplanted-context"
            ).hexdigest()
            payload = dict(document)
            payload.pop("intent_id")
            document["intent_id"] = _hash("batch_intent", payload)
            self.attack_used = True
        else:
            document = _batch_intent_document(
                profile_id=self.launch["profile_id"],
                occurrence_id=self.launch["_identity"].occurrence_id,
                sequence_number=self.sequence + 1,
                phase=phase,
                round_index=round_index,
                intent_kind=intent_kind,
                scientific_intent_id=scientific_intent_id,
                authorization_id=authorization_id,
                stream=stream,
                accepted_draw_start=accepted_draw_start,
                accepted_draw_count=accepted_draw_count,
                accepted_draw_cap=accepted_draw_cap,
            )
        raw = self._send(document)
        sent = _load_canonical(raw, field_name="child batch intent replay")
        response_raw = _read_frame_child(sys.stdin.buffer)
        response = _exact_mapping(
            _load_canonical(
                response_raw,
                field_name="parent batch response",
            ),
            {
                "schema",
                "schema_version",
                "profile_id",
                "occurrence_id",
                "sequence_number",
                "request_message_id",
                "request_id",
                "batch_id",
                "signed_public_batch",
                "private_replay_serialized",
                "private_material_serialized",
                "response_id",
            },
            field_name="parent batch response",
        )
        _strip_id_and_verify(
            response,
            role="batch_response",
            id_field="response_id",
            field_name="batch response",
        )
        if (
            response["schema"]
            != "acfqp.v075_production_occurrence_batch_response.v1"
            or response["schema_version"] != SCHEMA_VERSION
            or response["profile_id"] != self.launch["profile_id"]
            or response["occurrence_id"]
            != self.launch["_identity"].occurrence_id
            or response["sequence_number"] != self.sequence
            or response["request_message_id"] != sent["intent_id"]
            or response["private_replay_serialized"] is not False
            or response["private_material_serialized"] is not False
        ):
            _fail("parent batch response is stale, private, or reordered")
        batch = _load_signed_batch(
            response["signed_public_batch"],
            namespace=self.launch["_namespace"],
            context=self.launch["_context"],
            observer_binding=self.launch["_observer_binding"],
            session_public_id=(
                self.launch["open_lifecycle_binding"]["session_public_id"]
            ),
        )
        if (
            batch.batch_id != response["batch_id"]
            or batch.request.request_id != response["request_id"]
            or batch.request.stream_identity != stream
            or batch.request.accepted_draw_start != accepted_draw_start
            or batch.request.accepted_draw_count != accepted_draw_count
            or batch.request.accepted_draw_cap != accepted_draw_cap
        ):
            _fail("parent batch response differs from the authorized intent")
        self.batches.append(batch)
        return batch

    def freeze_support(
        self,
        *,
        phase: str,
        round_index: int,
        scientific_intent_id: str,
        authorization_id: str | None,
        discovery_batch: Any,
        root_epoch: Any,
    ) -> Any:
        selected = _support_outcome_ids(discovery_batch)
        document = _support_intent_document(
            profile_id=self.launch["profile_id"],
            occurrence_id=self.launch["_identity"].occurrence_id,
            sequence_number=self.sequence + 1,
            phase=phase,
            round_index=round_index,
            scientific_intent_id=scientific_intent_id,
            authorization_id=authorization_id,
            discovery_batch=discovery_batch,
            selected_outcome_ids=selected,
        )
        raw = self._send(document)
        sent = _load_canonical(raw, field_name="child support intent replay")
        response_raw = _read_frame_child(sys.stdin.buffer)
        response = _exact_mapping(
            _load_canonical(
                response_raw,
                field_name="parent support response",
            ),
            {
                "schema",
                "schema_version",
                "profile_id",
                "occurrence_id",
                "sequence_number",
                "support_intent_id",
                "evidence_ids",
                "evidence",
                "validation_stream_id",
                "validation_stream_identity",
                "private_material_serialized",
                "response_id",
            },
            field_name="parent support response",
        )
        _strip_id_and_verify(
            response,
            role="support_response",
            id_field="response_id",
            field_name="support response",
        )
        if (
            response["schema"]
            != "acfqp.v075_production_occurrence_support_response.v1"
            or response["schema_version"] != SCHEMA_VERSION
            or response["profile_id"] != self.launch["profile_id"]
            or response["occurrence_id"]
            != self.launch["_identity"].occurrence_id
            or response["sequence_number"] != self.sequence
            or response["support_intent_id"] != sent["support_intent_id"]
            or response["private_material_serialized"] is not False
            or type(response["evidence"]) is not list
        ):
            _fail("parent support response is stale, private, or reordered")
        row = discovery_batch.request.stream_identity.row_binding
        evidence = tuple(
            _load_support_evidence(
                item,
                namespace=self.launch["_namespace"],
                row=row,
                context=self.launch["_context"],
            )
            for item in response["evidence"]
        )
        if [item.evidence_id for item in evidence] != response["evidence_ids"]:
            _fail("support response evidence registry is reordered")
        expected = _validation_stream(
            self.launch["_namespace"],
            row,
            root_epoch,
            evidence,
            self.launch["_arm"],
        )
        stream = _load_stream(
            response["validation_stream_identity"],
            self.launch["_namespace"],
            self.launch["_context"],
        )
        if (
            stream != expected
            or stream.stream_id != response["validation_stream_id"]
        ):
            _fail("parent support response changed the validation stream")
        return stream

    def begin_round(
        self,
        *,
        round_index: int,
        backend_result: Any,
        planner_result: Any,
        frontier: Any,
        authorization: Any,
    ) -> None:
        document = _round_begin_document(
            profile_id=self.launch["profile_id"],
            occurrence_id=self.launch["_identity"].occurrence_id,
            sequence_number=self.sequence + 1,
            round_index=round_index,
            prior_backend_result_id=backend_result.result_id,
            prior_planner_result_id=planner_result.result_id,
            frontier=frontier,
            authorization=authorization,
        )
        raw = self._send(document)
        sent = _load_canonical(raw, field_name="child round-begin replay")
        response = _exact_mapping(
            _load_canonical(
                _read_frame_child(sys.stdin.buffer),
                field_name="parent round acknowledgement",
            ),
            {
                "schema",
                "schema_version",
                "profile_id",
                "occurrence_id",
                "sequence_number",
                "round_begin_id",
                "round_index",
                "parent_lifecycle_round_started",
                "ack_id",
            },
            field_name="parent round acknowledgement",
        )
        _strip_id_and_verify(
            response,
            role="round_ack",
            id_field="ack_id",
            field_name="round acknowledgement",
        )
        if (
            response["schema"]
            != "acfqp.v075_production_occurrence_round_ack.v1"
            or response["schema_version"] != SCHEMA_VERSION
            or response["profile_id"] != self.launch["profile_id"]
            or response["occurrence_id"]
            != self.launch["_identity"].occurrence_id
            or response["sequence_number"] != self.sequence
            or response["round_begin_id"] != sent["round_begin_id"]
            or response["round_index"] != round_index
            or response["parent_lifecycle_round_started"] is not True
        ):
            _fail("parent round acknowledgement is stale or reordered")


def _terminal_code(planner_result: Any, rounds: list[dict[str, Any]]) -> str | None:
    from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as bundle
    from acfqp import v075_learned_support_quotient_planners_v1 as planners

    if planner_result.ready_for_exact_total_lift:
        return "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT"
    if planner_result.status is planners.V075PlannerStatusV1.SEARCH_CAP_EXHAUSTED:
        return "PLANNER_SEARCH_CAP_EXHAUSTED"
    if rounds and rounds[-1]["execution"] is None:
        return (
            "NO_UNCERTAIN_PROOF_FRONTIER"
            if rounds[-1]["authorization"].status
            is bundle.V075BundleAuthorizationStatusV1
            .NO_UNCERTAIN_PROOF_FRONTIER
            else "INCREMENTAL_CAP_EXHAUSTED"
        )
    if len(rounds) == 2:
        return "ADAPTIVE_ROUND_LIMIT_REACHED"
    return None


def _child_scientific_run(launch: dict[str, Any]) -> dict[str, Any]:
    from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
    from acfqp import (
        v075_adaptive_acquisition_round_bundle_authority_v1 as bundle,
    )
    from acfqp import v075_batch_native_statistical_backend_v1 as backend

    protocol = _ChildProtocolV1(launch)
    namespace = launch["_namespace"]
    context = launch["_context"]
    arm = launch["_arm"]
    identity = launch["_identity"]
    source_transport = launch["_source_transport"]
    source_view = proposal.freeze_v075_source_proposal_view_v1(
        arm=arm,
        source_transport=source_transport,
    )
    schedule = proposal.freeze_v075_initial_root_acquisition_schedule_v1(
        context=context,
        arm=arm,
    )
    discoveries = tuple(
        item
        for item in schedule.intents
        if item.kind is proposal.V075InitialIntentKindV1.ROOT_DISCOVERY
    )
    validations = tuple(
        item
        for item in schedule.intents
        if item.kind is proposal.V075InitialIntentKindV1.ROOT_VALIDATION
    )
    discovery_by_intent: dict[str, tuple[Any, Any]] = {}
    validation_stream_by_intent: dict[str, Any] = {}
    for item in discoveries:
        root_epoch, stream = _bootstrap_stream(
            namespace,
            item.row_binding,
            arm,
        )
        observed = protocol.request_batch(
            stream=stream,
            phase="INITIAL_DISCOVERY",
            round_index=0,
            intent_kind=item.kind.value,
            scientific_intent_id=item.intent_id,
            authorization_id=None,
            accepted_draw_start=item.accepted_draw_start,
            accepted_draw_count=item.accepted_draw_count,
            accepted_draw_cap=item.accepted_draw_cap,
        )
        discovery_by_intent[item.intent_id] = (root_epoch, observed)
    for item in validations:
        dependency = discovery_by_intent.get(item.dependency_intent_id)
        if dependency is None:
            _fail("initial validation dependency is missing")
        root_epoch, discovery = dependency
        validation_stream_by_intent[item.intent_id] = (
            protocol.freeze_support(
                phase="INITIAL_SUPPORT_FREEZE",
                round_index=0,
                scientific_intent_id=item.intent_id,
                authorization_id=None,
                discovery_batch=discovery,
                root_epoch=root_epoch,
            )
        )
    for item in validations:
        protocol.request_batch(
            stream=validation_stream_by_intent[item.intent_id],
            phase="INITIAL_VALIDATION",
            round_index=0,
            intent_kind=item.kind.value,
            scientific_intent_id=item.intent_id,
            authorization_id=None,
            accepted_draw_start=item.accepted_draw_start,
            accepted_draw_count=item.accepted_draw_count,
            accepted_draw_cap=item.accepted_draw_cap,
        )

    def compile_plan() -> tuple[Any, Any]:
        request = backend.freeze_v075_batch_native_backend_request_v1(
            arm=arm,
            occurrence_ordinal=identity.occurrence_ordinal,
            batches=tuple(protocol.batches),
            source_prior_transport=source_transport,
            occurrence_identity=identity,
        )
        result = backend.compile_v075_batch_native_statistical_backend_v1(
            request
        )
        return result, backend.plan_v075_batch_native_route_v1(result)

    initial_backend, initial_planner = compile_plan()
    current_backend = initial_backend
    current_planner = initial_planner
    previous_execution = None
    rounds: list[dict[str, Any]] = []

    while _terminal_code(current_planner, rounds) is None:
        round_index = len(rounds) + 1
        frontier = bundle.freeze_v075_adaptive_round_bundle_frontier_v1(
            batch_result=current_backend,
            planner_result=current_planner,
            source_view=source_view,
            round_index=round_index,
            previous_execution=previous_execution,
        )
        authorization = bundle.authorize_v075_adaptive_round_bundle_v1(
            frontier
        )
        if (
            authorization.status
            is not bundle.V075BundleAuthorizationStatusV1.AUTHORIZED
        ):
            rounds.append(
                {
                    "round_index": round_index,
                    "frontier": frontier,
                    "authorization": authorization,
                    "execution": None,
                    "appended_batch_ids": (),
                    "resulting_backend": None,
                    "resulting_planner": None,
                }
            )
            break
        protocol.begin_round(
            round_index=round_index,
            backend_result=current_backend,
            planner_result=current_planner,
            frontier=frontier,
            authorization=authorization,
        )
        before = {item.batch_id for item in protocol.batches}
        discoveries_by_intent: dict[str, tuple[Any, Any]] = {}
        validation_streams: dict[str, Any] = {}
        for item in authorization.intents:
            if (
                item.kind
                is not bundle.V075BundleIntentKindV1
                .NEW_CHILD_ROW_DISCOVERY
            ):
                continue
            root_epoch, stream = _bootstrap_stream(
                namespace,
                item.row_binding,
                arm,
            )
            observed = protocol.request_batch(
                stream=stream,
                phase="ADAPTIVE_DISCOVERY",
                round_index=round_index,
                intent_kind=item.kind.value,
                scientific_intent_id=item.intent_id,
                authorization_id=authorization.authorization_id,
                accepted_draw_start=item.accepted_draw_start,
                accepted_draw_count=item.accepted_draw_count,
                accepted_draw_cap=item.accepted_draw_cap,
            )
            discoveries_by_intent[item.intent_id] = (root_epoch, observed)
        for item in authorization.intents:
            if (
                item.kind
                is not bundle.V075BundleIntentKindV1
                .NEW_CHILD_ROW_VALIDATION
            ):
                continue
            dependency = discoveries_by_intent.get(
                item.dependency_intent_id
            )
            if dependency is None:
                _fail("adaptive validation dependency is missing")
            root_epoch, discovery = dependency
            validation_streams[item.intent_id] = protocol.freeze_support(
                phase="ADAPTIVE_SUPPORT_FREEZE",
                round_index=round_index,
                scientific_intent_id=item.intent_id,
                authorization_id=authorization.authorization_id,
                discovery_batch=discovery,
                root_epoch=root_epoch,
            )
        existing_streams = {
            item.request.stream_identity.stream_id:
            item.request.stream_identity
            for item in current_backend.request.batches
        }
        for item in authorization.intents:
            if (
                item.kind
                is bundle.V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
            ):
                continue
            if (
                item.kind
                is bundle.V075BundleIntentKindV1
                .EXISTING_VALIDATION_PREFIX_EXTENSION
            ):
                stream = existing_streams.get(item.existing_stream_id)
            else:
                stream = validation_streams.get(item.intent_id)
            if stream is None:
                _fail("adaptive validation stream is missing")
            protocol.request_batch(
                stream=stream,
                phase="ADAPTIVE_VALIDATION",
                round_index=round_index,
                intent_kind=item.kind.value,
                scientific_intent_id=item.intent_id,
                authorization_id=authorization.authorization_id,
                accepted_draw_start=item.accepted_draw_start,
                accepted_draw_count=item.accepted_draw_count,
                accepted_draw_cap=item.accepted_draw_cap,
            )
        resulting_backend, resulting_planner = compile_plan()
        execution = bundle.verify_v075_adaptive_round_bundle_execution_v1(
            authorization=authorization,
            resulting_batch_result=resulting_backend,
        )
        appended = tuple(
            sorted(
                item.batch_id
                for item in protocol.batches
                if item.batch_id not in before
            )
        )
        if appended != execution.appended_batch_ids:
            _fail("child append registry differs from exact round replay")
        rounds.append(
            {
                "round_index": round_index,
                "frontier": frontier,
                "authorization": authorization,
                "execution": execution,
                "appended_batch_ids": appended,
                "resulting_backend": resulting_backend,
                "resulting_planner": resulting_planner,
            }
        )
        previous_execution = execution
        current_backend = resulting_backend
        current_planner = resulting_planner

    terminal = _terminal_code(current_planner, rounds)
    if terminal is None:
        _fail("isolated child exited without a registered terminal")
    payload = {
        "schema": "acfqp.v075_production_occurrence_child_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "profile_id": launch["profile_id"],
        "occurrence_id": identity.occurrence_id,
        "target_tape_namespace_id": identity.target_tape_namespace_id,
        "context_id": identity.context_id,
        "arm": arm.value,
        "route": "ADAPTIVE_QUOTIENT",
        "occurrence_ordinal": identity.occurrence_ordinal,
        "source_view_id": source_view.source_view_id,
        "initial_schedule_id": schedule.schedule_id,
        "initial_backend_result_id": initial_backend.result_id,
        "initial_planner_result_id": initial_planner.result_id,
        "rounds": [
            {
                "round_index": item["round_index"],
                "frontier_id": item["frontier"].frontier_id,
                "authorization_id": (
                    item["authorization"].authorization_id
                ),
                "authorization_status": (
                    item["authorization"].status.value
                ),
                "scientific_intent_ids": [
                    value.intent_id
                    for value in item["authorization"].intents
                ],
                "appended_batch_ids": list(item["appended_batch_ids"]),
                "execution_id": (
                    None
                    if item["execution"] is None
                    else item["execution"].execution_id
                ),
                "resulting_backend_result_id": (
                    None
                    if item["resulting_backend"] is None
                    else item["resulting_backend"].result_id
                ),
                "resulting_planner_result_id": (
                    None
                    if item["resulting_planner"] is None
                    else item["resulting_planner"].result_id
                ),
            }
            for item in rounds
        ],
        "batch_ids": sorted(item.batch_id for item in protocol.batches),
        "observation_order_batch_ids": [
            item.batch_id for item in protocol.batches
        ],
        "final_backend_result_id": current_backend.result_id,
        "final_planner_result_id": current_planner.result_id,
        "final_planner_status": current_planner.status.value,
        "ready_for_exact_total_lift": (
            current_planner.ready_for_exact_total_lift
        ),
        "terminal_code": terminal,
        "final_backend_result": current_backend.to_document(),
        "final_planner_result": current_planner.to_document(),
        "public_backend_computed_in_child": True,
        "public_planner_computed_in_child": True,
        "host_operational_full_planner_replay_required": False,
        "private_material_serialized": False,
        "scientific_plan_certificate": False,
        "target_execution_opened": False,
    }
    return _message_id(
        role="child_result",
        payload=payload,
        id_field="child_result_id",
    )


@dataclass(frozen=True, slots=True)
class V075ProductionIPCJournalEntryV1:
    sequence_number: int
    direction: str
    message_kind: str
    message_id: str
    byte_count: int
    bytes_sha256: str
    previous_entry_id: str
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.message_id, "journal message"),
            (self.bytes_sha256, "journal byte digest"),
            (self.previous_entry_id, "journal predecessor"),
        ):
            _cid(value, name)
        if (
            type(self.sequence_number) is not int
            or self.sequence_number <= 0
            or self.direction not in {"CHILD_TO_PARENT", "PARENT_TO_CHILD"}
            or self.message_kind
            not in {
                "BATCH_INTENT",
                "BATCH_RESPONSE",
                "SUPPORT_INTENT",
                "SUPPORT_RESPONSE",
                "ROUND_BEGIN",
                "ROUND_ACK",
                "FINAL_RESULT",
            }
            or type(self.byte_count) is not int
            or not 0 < self.byte_count <= MAX_FRAME_BYTES
        ):
            _fail("production IPC journal entry is malformed")
        object.__setattr__(
            self,
            "_entry_id",
            _hash("journal_entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_occurrence_ipc_journal_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "sequence_number": self.sequence_number,
            "direction": self.direction,
            "message_kind": self.message_kind,
            "message_id": self.message_id,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
            "previous_entry_id": self.previous_entry_id,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


def _append_journal(
    entries: list[V075ProductionIPCJournalEntryV1],
    *,
    direction: str,
    message_kind: str,
    message_id: str,
    raw: bytes,
) -> None:
    entries.append(
        V075ProductionIPCJournalEntryV1(
            len(entries) + 1,
            direction,
            message_kind,
            message_id,
            len(raw),
            hashlib.sha256(raw).hexdigest(),
            _INITIAL_JOURNAL_HASH if not entries else entries[-1].entry_id,
        )
    )


@dataclass(frozen=True, slots=True)
class V075ProductionIPCActualWorkV1:
    process_launches: int
    child_messages: int
    parent_messages: int
    batch_intents: int
    support_freeze_intents: int
    round_begin_intents: int
    accepted_draws: int
    outcome_aggregates: int
    child_bytes_read: int
    parent_bytes_written: int
    protocol_checks: int
    host_operational_planner_replays: int
    child_exit_code: int | None
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = (
            self.process_launches,
            self.child_messages,
            self.parent_messages,
            self.batch_intents,
            self.support_freeze_intents,
            self.round_begin_intents,
            self.accepted_draws,
            self.outcome_aggregates,
            self.child_bytes_read,
            self.parent_bytes_written,
            self.protocol_checks,
            self.host_operational_planner_replays,
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.process_launches != 1
            or self.host_operational_planner_replays != 0
            or type(self.child_exit_code) not in {int, type(None)}
        ):
            _fail("production IPC actual work is malformed")
        object.__setattr__(self, "_work_id", _hash("work", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_occurrence_ipc_work.v1",
            "schema_version": SCHEMA_VERSION,
            "process_launches": self.process_launches,
            "child_messages": self.child_messages,
            "parent_messages": self.parent_messages,
            "batch_intents": self.batch_intents,
            "support_freeze_intents": self.support_freeze_intents,
            "round_begin_intents": self.round_begin_intents,
            "accepted_draws": self.accepted_draws,
            "outcome_aggregates": self.outcome_aggregates,
            "child_bytes_read": self.child_bytes_read,
            "parent_bytes_written": self.parent_bytes_written,
            "protocol_checks": self.protocol_checks,
            "host_operational_planner_replays": (
                self.host_operational_planner_replays
            ),
            "child_exit_code": self.child_exit_code,
            "operational_lane": True,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrenceIPCResultV1:
    profile_id: str
    occurrence_id: str
    authority_scope: str
    route: str
    status: str
    terminal_code: str
    child_result: dict[str, Any] | None
    observed_batches: tuple[Any, ...] = field(repr=False)
    journal_entries: tuple[V075ProductionIPCJournalEntryV1, ...]
    actual_work: V075ProductionIPCActualWorkV1
    stderr_sha256: str
    stderr_byte_count: int
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import v075_batched_observer_authority_v1 as batched

        for value, name in (
            (self.profile_id, "IPC result profile"),
            (self.occurrence_id, "IPC result occurrence"),
            (self.stderr_sha256, "IPC result stderr digest"),
        ):
            _cid(value, name)
        if (
            self.authority_scope
            not in {"PRODUCTION_OPEN", "CONSTRUCTION_ONLY"}
            or self.route
            not in {"ADAPTIVE_QUOTIENT", "MATCHED_DIRECT_GROUND"}
            or self.status not in {"PASS", "FAILED"}
            or self.terminal_code
            not in {
                "CHILD_SCIENTIFIC_RESULT_READY",
                "PROTOCOL_FAILURE",
                "PROCESS_FAILURE",
                "TIMEOUT",
            }
            or type(self.observed_batches) is not tuple
            or any(
                type(item) is not batched.V075SignedBatchedObservationV1
                for item in self.observed_batches
            )
            or type(self.journal_entries) is not tuple
            or any(
                type(item) is not V075ProductionIPCJournalEntryV1
                for item in self.journal_entries
            )
            or tuple(item.sequence_number for item in self.journal_entries)
            != tuple(range(1, len(self.journal_entries) + 1))
            or tuple(item.previous_entry_id for item in self.journal_entries)
            != tuple(
                _INITIAL_JOURNAL_HASH
                if index == 0
                else self.journal_entries[index - 1].entry_id
                for index in range(len(self.journal_entries))
            )
            or type(self.actual_work) is not V075ProductionIPCActualWorkV1
            or type(self.stderr_byte_count) is not int
            or not 0 <= self.stderr_byte_count <= MAX_CHILD_STDERR_BYTES
        ):
            _fail("production occurrence IPC result is malformed")
        passed = self.status == "PASS"
        if passed != (
            self.terminal_code == "CHILD_SCIENTIFIC_RESULT_READY"
            and type(self.child_result) is dict
            and self.actual_work.child_exit_code == 0
        ):
            _fail("production IPC terminal and child result disagree")
        if passed:
            assert self.child_result is not None
            if (
                self.child_result.get("profile_id") != self.profile_id
                or self.child_result.get("occurrence_id")
                != self.occurrence_id
                or self.child_result.get("batch_ids")
                != sorted(item.batch_id for item in self.observed_batches)
            ):
                _fail("production IPC child result is identity-transplanted")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    @property
    def child_result_id(self) -> str | None:
        return (
            None
            if self.child_result is None
            else self.child_result["child_result_id"]
        )

    @property
    def journal_id(self) -> str:
        return _hash(
            "journal",
            {
                "schema": "acfqp.v075_production_occurrence_ipc_journal.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_id": self.profile_id,
                "occurrence_id": self.occurrence_id,
                "entry_ids": [item.entry_id for item in self.journal_entries],
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_occurrence_ipc_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "occurrence_id": self.occurrence_id,
            "authority_scope": self.authority_scope,
            "route": self.route,
            "status": self.status,
            "terminal_code": self.terminal_code,
            "child_result_id": self.child_result_id,
            "batch_ids": [item.batch_id for item in self.observed_batches],
            "journal_id": self.journal_id,
            "actual_work_id": self.actual_work.work_id,
            "stderr_sha256": self.stderr_sha256,
            "stderr_byte_count": self.stderr_byte_count,
            "one_fresh_process_per_occurrence": True,
            "parent_owned_private_observer": True,
            "canonical_json_frames_only": True,
            "host_operational_full_planner_replays": 0,
            "scientific_plan_certificate": False,
            "target_execution_opened": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child_result": self.child_result,
            "signed_public_batches": [
                item.to_document() for item in self.observed_batches
            ],
            "journal_entries": [
                item.to_document() for item in self.journal_entries
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
        else:  # pragma: no cover
            process.kill()
    except (ProcessLookupError, PermissionError):
        process.kill()


def _validate_child_batch_intent(
    *,
    raw: bytes,
    profile: V075ProductionOccurrenceIPCProfileV1,
    expected_sequence: int,
    next_start: dict[str, int],
    controller: Any,
    active_round: int,
    active_authorization_id: str | None,
    allowed_scientific_intent_ids: set[str],
    consumed_scientific_intent_ids: set[str],
    root_schedule_intents: dict[str, Any],
    child_state_ids: set[str],
    child_row_ids: set[str],
    incremental_draws: int,
) -> tuple[dict[str, Any], Any, int]:
    from acfqp import v075_public_graph_semantics_v1 as graph
    from acfqp import v075_registered_occurrence_worker_v1 as worker

    item = _exact_mapping(
        _load_canonical(raw, field_name="child batch intent"),
        {
            "schema",
            "schema_version",
            "profile_id",
            "occurrence_id",
            "sequence_number",
            "phase",
            "round_index",
            "intent_kind",
            "scientific_intent_id",
            "authorization_id",
            "target_tape_namespace_id",
            "context_id",
            "row_binding_id",
            "stream_id",
            "lane",
            "arm",
            "observer_epoch_index",
            "accepted_draw_start",
            "accepted_draw_count",
            "accepted_draw_end",
            "accepted_draw_cap",
            "stream_identity",
            "private_material_serialized",
            "intent_id",
        },
        field_name="child batch intent",
    )
    _strip_id_and_verify(
        item,
        role="batch_intent",
        id_field="intent_id",
        field_name="batch intent",
    )
    identity = profile.occurrence_identity
    stream = _load_stream(
        item["stream_identity"],
        profile.open_lifecycle_binding.namespace,
        profile.context,
    )
    for value, name in (
        (item["scientific_intent_id"], "scientific batch intent"),
        (item["stream_id"], "batch intent stream"),
        (item["row_binding_id"], "batch intent row"),
    ):
        _cid(value, name)
    if item["authorization_id"] is not None:
        _cid(item["authorization_id"], "batch intent authorization")
    if (
        item["schema"]
        != "acfqp.v075_production_occurrence_batch_intent.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_id"] != profile.profile_id
        or item["occurrence_id"] != identity.occurrence_id
        or item["sequence_number"] != expected_sequence
        or item["round_index"] != active_round
        or item["authorization_id"] != active_authorization_id
        or item["target_tape_namespace_id"]
        != identity.target_tape_namespace_id
        or item["context_id"] != identity.context_id
        or item["arm"] != identity.arm.value
        or item["row_binding_id"] != stream.row_binding_id
        or item["stream_id"] != stream.stream_id
        or item["lane"] != stream.lane.value
        or item["observer_epoch_index"] != stream.observer_epoch_index
        or item["accepted_draw_end"]
        != item["accepted_draw_start"]
        + item["accepted_draw_count"]
        - 1
        or item["private_material_serialized"] is not False
        or item["accepted_draw_start"] != next_start.get(stream.stream_id, 1)
        or item["scientific_intent_id"] in consumed_scientific_intent_ids
    ):
        _fail("child batch intent is stale, reordered, or transplanted")
    caps = profile.open_lifecycle_binding.route_cap_profile
    row = stream.row_binding
    if active_round == 0:
        expected = root_schedule_intents.get(item["scientific_intent_id"])
        if (
            expected is None
            or item["scientific_intent_id"]
            not in allowed_scientific_intent_ids
            or expected.row_binding != row
            or expected.kind.value != item["intent_kind"]
            or expected.observer_epoch_index != stream.observer_epoch_index
            or expected.accepted_draw_start != item["accepted_draw_start"]
            or expected.accepted_draw_count != item["accepted_draw_count"]
            or expected.accepted_draw_cap != item["accepted_draw_cap"]
        ):
            _fail("initial child batch intent differs from frozen schedule")
        next_incremental = incremental_draws
    else:
        if item["scientific_intent_id"] not in allowed_scientific_intent_ids:
            _fail("adaptive batch intent is outside its child authorization")
        if stream.lane is graph.V075ObservationLaneV1.DISCOVERY:
            if (
                row.remaining_horizon != 1
                or row.catalogue.state.state_id not in child_state_ids
                or item["accepted_draw_start"] != 1
                or item["accepted_draw_count"]
                != caps.new_child_discovery_draws_per_row
                or item["accepted_draw_cap"]
                != caps.new_child_discovery_draws_per_row
                or row.row_binding_id in child_row_ids
            ):
                _fail("adaptive discovery escaped observed complete child support")
            child_row_ids.add(row.row_binding_id)
        elif stream.lane is graph.V075ObservationLaneV1.VALIDATION:
            if row.remaining_horizon == 1:
                allowed_counts = {
                    caps.new_child_validation_draws_per_row,
                    caps.promotion_validation_draws_per_round,
                }
                expected_cap = (
                    caps.new_child_validation_draws_per_row
                    + caps.maximum_adaptive_rounds
                    * caps.promotion_validation_draws_per_round
                )
            else:
                allowed_counts = {caps.promotion_validation_draws_per_round}
                expected_cap = (
                    caps.initial_validation_draws_per_row
                    + caps.maximum_adaptive_rounds
                    * caps.promotion_validation_draws_per_round
                )
            if (
                item["accepted_draw_count"] not in allowed_counts
                or item["accepted_draw_cap"] != expected_cap
            ):
                _fail("adaptive validation intent is outside registered caps")
        else:  # pragma: no cover
            _fail("adaptive batch intent has an unknown lane")
        next_incremental = incremental_draws + item["accepted_draw_count"]
        if (
            next_incremental
            > caps.maximum_incremental_draws_per_adaptive_arm
            or len(child_row_ids) > caps.maximum_new_child_action_rows
        ):
            _fail("adaptive child intent exceeds occurrence caps")
    if stream.arm != identity.arm.value:
        _fail("batch intent stream changed arm")
    # The exact lifecycle rechecks support-freeze phase and stream provenance.
    if controller.open_binding != profile.open_lifecycle_binding:
        _fail("parent lifecycle changed after profile freeze")
    return item, stream, next_incremental


def _validate_child_result_operationally(
    *,
    raw: bytes,
    profile: V075ProductionOccurrenceIPCProfileV1,
    observed_batches: tuple[Any, ...],
    active_round: int,
) -> dict[str, Any]:
    item = _exact_mapping(
        _load_canonical(raw, field_name="child scientific result"),
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "profile_id",
            "occurrence_id",
            "target_tape_namespace_id",
            "context_id",
            "arm",
            "route",
            "occurrence_ordinal",
            "source_view_id",
            "initial_schedule_id",
            "initial_backend_result_id",
            "initial_planner_result_id",
            "rounds",
            "batch_ids",
            "observation_order_batch_ids",
            "final_backend_result_id",
            "final_planner_result_id",
            "final_planner_status",
            "ready_for_exact_total_lift",
            "terminal_code",
            "final_backend_result",
            "final_planner_result",
            "public_backend_computed_in_child",
            "public_planner_computed_in_child",
            "host_operational_full_planner_replay_required",
            "private_material_serialized",
            "scientific_plan_certificate",
            "target_execution_opened",
            "child_result_id",
        },
        field_name="child scientific result",
    )
    _strip_id_and_verify(
        item,
        role="child_result",
        id_field="child_result_id",
        field_name="child scientific result",
    )
    identity = profile.occurrence_identity
    id_fields = (
        "source_view_id",
        "initial_schedule_id",
        "initial_backend_result_id",
        "initial_planner_result_id",
        "final_backend_result_id",
        "final_planner_result_id",
    )
    for key in id_fields:
        _cid(item[key], f"child result {key}")
    if (
        item["schema"]
        != "acfqp.v075_production_occurrence_child_result.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["profile_id"] != profile.profile_id
        or item["occurrence_id"] != identity.occurrence_id
        or item["target_tape_namespace_id"]
        != identity.target_tape_namespace_id
        or item["context_id"] != identity.context_id
        or item["arm"] != identity.arm.value
        or item["route"] != "ADAPTIVE_QUOTIENT"
        or item["occurrence_ordinal"] != identity.occurrence_ordinal
        or item["batch_ids"]
        != sorted(batch.batch_id for batch in observed_batches)
        or item["observation_order_batch_ids"]
        != [batch.batch_id for batch in observed_batches]
        or type(item["rounds"]) is not list
        or len(item["rounds"]) != active_round
        or type(item["ready_for_exact_total_lift"]) is not bool
        or item["public_backend_computed_in_child"] is not True
        or item["public_planner_computed_in_child"] is not True
        or item["host_operational_full_planner_replay_required"] is not False
        or item["private_material_serialized"] is not False
        or item["scientific_plan_certificate"] is not False
        or item["target_execution_opened"] is not False
        or type(item["final_backend_result"]) is not dict
        or type(item["final_planner_result"]) is not dict
        or item["final_backend_result"].get("result_id")
        != item["final_backend_result_id"]
        or item["final_backend_result"].get("occurrence_id")
        != identity.occurrence_id
        or item["final_planner_result"].get("result_id")
        != item["final_planner_result_id"]
    ):
        _fail("child scientific result is malformed or identity-transplanted")
    return item


def execute_v075_production_adaptive_occurrence_ipc_v1(
    *,
    profile: V075ProductionOccurrenceIPCProfileV1,
    controller: Any,
) -> V075ProductionOccurrenceIPCResultV1:
    """Execute one adaptive occurrence in one fresh registered child.

    The parent performs capability/cap/protocol checks and observer execution
    only.  It never calls the statistical backend or planner.
    """

    from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
    from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
    from acfqp import v075_registered_occurrence_worker_v1 as worker

    if (
        type(profile) is not V075ProductionOccurrenceIPCProfileV1
        or type(controller)
        is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
        or controller.open_binding != profile.open_lifecycle_binding
        or controller.batches
        or controller.events
    ):
        _fail("production occurrence IPC requires its exact unused lifecycle")
    if (
        profile.occurrence_identity.arm
        is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ):
        _fail(
            "route-generic IPC profile is frozen, but the matched-direct "
            "child handler is not yet integrated"
        )
    launch = _launch_document(profile)
    launch_raw = _canonical_bytes(launch)
    entries: list[V075ProductionIPCJournalEntryV1] = []
    batches: list[Any] = []
    next_start: dict[str, int] = {}
    child_state_ids: set[str] = set()
    child_row_ids: set[str] = set()
    incremental_draws = 0
    protocol_checks = 1
    child_bytes = 0
    parent_bytes = len(launch_raw)
    batch_intents = 0
    support_intents = 0
    round_begins = 0
    active_round = 0
    active_authorization_id: str | None = None
    allowed_scientific_intent_ids: set[str] = set()
    consumed_scientific_intent_ids: set[str] = set()
    root_schedule = proposal.freeze_v075_initial_root_acquisition_schedule_v1(
        context=profile.context,
        arm=profile.occurrence_identity.arm,
    )
    root_schedule_intents = {
        item.intent_id: item for item in root_schedule.intents
    }
    allowed_scientific_intent_ids = set(root_schedule_intents)
    child_result: dict[str, Any] | None = None
    terminal_code = "PROTOCOL_FAILURE"
    process: subprocess.Popen[bytes] | None = None
    stderr = b""
    exit_code: int | None = None

    with tempfile.TemporaryDirectory(
        prefix="acfqp-v075-production-occurrence-"
    ) as sandbox:
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
                _fail("fresh occurrence child lacks isolated protocol pipes")
            _write_frame(process.stdin, launch_raw)
            deadline = time.monotonic() + profile.process_timeout_seconds
            for expected_sequence in range(1, MAX_PROTOCOL_MESSAGES + 1):
                raw = _read_frame_fd(process.stdout.fileno(), deadline)
                child_bytes += len(raw)
                document = _load_canonical(raw, field_name="child message")
                schema = (
                    document.get("schema")
                    if type(document) is dict
                    else None
                )
                if (
                    schema
                    == "acfqp.v075_production_occurrence_batch_intent.v1"
                ):
                    item, stream, incremental_draws = (
                        _validate_child_batch_intent(
                            raw=raw,
                            profile=profile,
                            expected_sequence=expected_sequence,
                            next_start=next_start,
                            controller=controller,
                            active_round=active_round,
                            active_authorization_id=(
                                active_authorization_id
                            ),
                            allowed_scientific_intent_ids=(
                                allowed_scientific_intent_ids
                            ),
                            consumed_scientific_intent_ids=(
                                consumed_scientific_intent_ids
                            ),
                            root_schedule_intents=root_schedule_intents,
                            child_state_ids=child_state_ids,
                            child_row_ids=child_row_ids,
                            incremental_draws=incremental_draws,
                        )
                    )
                    batch_intents += 1
                    if batch_intents > MAX_BATCH_INTENTS:
                        _fail("child exceeded the batch-intent cap")
                    _append_journal(
                        entries,
                        direction="CHILD_TO_PARENT",
                        message_kind="BATCH_INTENT",
                        message_id=item["intent_id"],
                        raw=raw,
                    )
                    observed = controller.execute_batch_v1(
                        stream_identity=stream,
                        accepted_draw_start=item["accepted_draw_start"],
                        accepted_draw_count=item["accepted_draw_count"],
                        accepted_draw_cap=item["accepted_draw_cap"],
                    )
                    batches.append(observed)
                    next_start[stream.stream_id] = (
                        item["accepted_draw_end"] + 1
                    )
                    consumed_scientific_intent_ids.add(
                        item["scientific_intent_id"]
                    )
                    if stream.row_binding.remaining_horizon == 2:
                        from acfqp import (
                            v075_public_graph_semantics_v1 as graph,
                        )

                        for outcome in observed.outcomes:
                            state = graph.V075SymbolicGraphStateV1(
                                profile.context,
                                outcome.next_ranks,
                                outcome.failure,
                            )
                            if not state.failure:
                                child_state_ids.add(state.state_id)
                    response = _response_document(
                        profile_id=profile.profile_id,
                        occurrence_id=(
                            profile.occurrence_identity.occurrence_id
                        ),
                        sequence_number=expected_sequence,
                        request_message_id=item["intent_id"],
                        signed_batch=observed,
                    )
                    response_raw = _canonical_bytes(response)
                    _append_journal(
                        entries,
                        direction="PARENT_TO_CHILD",
                        message_kind="BATCH_RESPONSE",
                        message_id=response["response_id"],
                        raw=response_raw,
                    )
                    _write_frame(process.stdin, response_raw)
                    parent_bytes += len(response_raw)
                    protocol_checks += 3
                    continue
                if (
                    schema
                    == "acfqp.v075_production_occurrence_support_intent.v1"
                ):
                    item = _exact_mapping(
                        document,
                        {
                            "schema",
                            "schema_version",
                            "profile_id",
                            "occurrence_id",
                            "sequence_number",
                            "phase",
                            "round_index",
                            "scientific_intent_id",
                            "authorization_id",
                            "discovery_request_id",
                            "discovery_batch_id",
                            "row_binding_id",
                            "selected_outcome_ids",
                            "private_material_serialized",
                            "support_intent_id",
                        },
                        field_name="child support intent",
                    )
                    _strip_id_and_verify(
                        item,
                        role="support_intent",
                        id_field="support_intent_id",
                        field_name="support intent",
                    )
                    discovery = next(
                        (
                            value
                            for value in batches
                            if value.batch_id
                            == item["discovery_batch_id"]
                        ),
                        None,
                    )
                    selected = (
                        tuple(item["selected_outcome_ids"])
                        if type(item["selected_outcome_ids"]) is list
                        else ()
                    )
                    if (
                        item["schema"]
                        != "acfqp.v075_production_occurrence_support_intent.v1"
                        or item["schema_version"] != SCHEMA_VERSION
                        or item["profile_id"] != profile.profile_id
                        or item["occurrence_id"]
                        != profile.occurrence_identity.occurrence_id
                        or item["sequence_number"] != expected_sequence
                        or item["round_index"] != active_round
                        or item["authorization_id"]
                        != active_authorization_id
                        or item["scientific_intent_id"]
                        not in allowed_scientific_intent_ids
                        or item["private_material_serialized"] is not False
                        or discovery is None
                        or discovery.request.request_id
                        != item["discovery_request_id"]
                        or discovery.request.stream_identity.row_binding_id
                        != item["row_binding_id"]
                        or selected != _support_outcome_ids(discovery)
                    ):
                        _fail("child support intent is stale or transplanted")
                    _append_journal(
                        entries,
                        direction="CHILD_TO_PARENT",
                        message_kind="SUPPORT_INTENT",
                        message_id=item["support_intent_id"],
                        raw=raw,
                    )
                    evidence = (
                        controller.freeze_aggregate_support_evidence_v1(
                            discovery_batch=discovery,
                            selected_outcome_ids=selected,
                        )
                    )
                    root_epoch, _stream = _bootstrap_stream(
                        profile.open_lifecycle_binding.namespace,
                        discovery.request.stream_identity.row_binding,
                        profile.occurrence_identity.arm,
                    )
                    validation_stream = _validation_stream(
                        profile.open_lifecycle_binding.namespace,
                        discovery.request.stream_identity.row_binding,
                        root_epoch,
                        evidence,
                        profile.occurrence_identity.arm,
                    )
                    controller.register_validation_support_epoch_v1(
                        stream_identity=validation_stream
                    )
                    response = _support_response_document(
                        profile_id=profile.profile_id,
                        occurrence_id=(
                            profile.occurrence_identity.occurrence_id
                        ),
                        sequence_number=expected_sequence,
                        support_intent_id=item["support_intent_id"],
                        evidence=evidence,
                        validation_stream=validation_stream,
                    )
                    response_raw = _canonical_bytes(response)
                    _append_journal(
                        entries,
                        direction="PARENT_TO_CHILD",
                        message_kind="SUPPORT_RESPONSE",
                        message_id=response["response_id"],
                        raw=response_raw,
                    )
                    _write_frame(process.stdin, response_raw)
                    parent_bytes += len(response_raw)
                    support_intents += 1
                    protocol_checks += 4
                    continue
                if (
                    schema
                    == "acfqp.v075_production_occurrence_round_begin.v1"
                ):
                    item = _exact_mapping(
                        document,
                        {
                            "schema",
                            "schema_version",
                            "profile_id",
                            "occurrence_id",
                            "sequence_number",
                            "round_index",
                            "prior_backend_result_id",
                            "prior_planner_result_id",
                            "frontier_id",
                            "authorization_id",
                            "authorization_status",
                            "scientific_intent_ids",
                            "frontier",
                            "authorization",
                            "private_material_serialized",
                            "round_begin_id",
                        },
                        field_name="child round begin",
                    )
                    _strip_id_and_verify(
                        item,
                        role="round_begin",
                        id_field="round_begin_id",
                        field_name="round begin",
                    )
                    ids = item["scientific_intent_ids"]
                    if (
                        item["schema"]
                        != "acfqp.v075_production_occurrence_round_begin.v1"
                        or item["schema_version"] != SCHEMA_VERSION
                        or item["profile_id"] != profile.profile_id
                        or item["occurrence_id"]
                        != profile.occurrence_identity.occurrence_id
                        or item["sequence_number"] != expected_sequence
                        or item["round_index"] != active_round + 1
                        or item["round_index"] not in (1, 2)
                        or item["authorization_status"] != "AUTHORIZED"
                        or type(ids) is not list
                        or not ids
                        or ids != list(dict.fromkeys(ids))
                        or any(
                            _cid(value, "authorized scientific intent")
                            != value
                            for value in ids
                        )
                        or item["authorization"].get("authorization_id")
                        != item["authorization_id"]
                        or item["authorization"].get("intent_ids") != ids
                        or item["frontier"].get("frontier_id")
                        != item["frontier_id"]
                        or item["private_material_serialized"] is not False
                    ):
                        _fail("child round begin is malformed or reordered")
                    for key in (
                        "prior_backend_result_id",
                        "prior_planner_result_id",
                        "frontier_id",
                        "authorization_id",
                    ):
                        _cid(item[key], f"round begin {key}")
                    controller.start_adaptive_round_v1(
                        item["round_index"]
                    )
                    active_round = item["round_index"]
                    active_authorization_id = item["authorization_id"]
                    allowed_scientific_intent_ids = set(ids)
                    consumed_scientific_intent_ids = set()
                    round_begins += 1
                    _append_journal(
                        entries,
                        direction="CHILD_TO_PARENT",
                        message_kind="ROUND_BEGIN",
                        message_id=item["round_begin_id"],
                        raw=raw,
                    )
                    ack = _round_ack_document(
                        profile_id=profile.profile_id,
                        occurrence_id=(
                            profile.occurrence_identity.occurrence_id
                        ),
                        sequence_number=expected_sequence,
                        round_begin_id=item["round_begin_id"],
                        round_index=active_round,
                    )
                    ack_raw = _canonical_bytes(ack)
                    _append_journal(
                        entries,
                        direction="PARENT_TO_CHILD",
                        message_kind="ROUND_ACK",
                        message_id=ack["ack_id"],
                        raw=ack_raw,
                    )
                    _write_frame(process.stdin, ack_raw)
                    parent_bytes += len(ack_raw)
                    protocol_checks += 4
                    continue
                if (
                    schema
                    == "acfqp.v075_production_occurrence_child_result.v1"
                ):
                    child_result = _validate_child_result_operationally(
                        raw=raw,
                        profile=profile,
                        observed_batches=tuple(batches),
                        active_round=active_round,
                    )
                    _append_journal(
                        entries,
                        direction="CHILD_TO_PARENT",
                        message_kind="FINAL_RESULT",
                        message_id=child_result["child_result_id"],
                        raw=raw,
                    )
                    protocol_checks += 3
                    terminal_code = "CHILD_SCIENTIFIC_RESULT_READY"
                    break
                _fail("child emitted an unknown protocol message")
            else:
                _fail("child exceeded the protocol-message cap")
            if child_result is None:
                _fail("child closed without one scientific result")
            process.stdin.close()
            remaining = max(0.001, deadline - time.monotonic())
            exit_code = process.wait(timeout=remaining)
            if exit_code != 0:
                terminal_code = "PROCESS_FAILURE"
                child_result = None
        except subprocess.TimeoutExpired:
            terminal_code = "TIMEOUT"
            child_result = None
            if process is not None:
                _terminate_process(process)
        except (
            V075ProductionOccurrenceIPCInvariantViolation,
            BrokenPipeError,
            OSError,
            subprocess.SubprocessError,
            TypeError,
            ValueError,
        ) as error:
            if isinstance(
                error,
                (BrokenPipeError, OSError, subprocess.SubprocessError),
            ):
                terminal_code = "PROCESS_FAILURE"
            elif terminal_code != "TIMEOUT":
                terminal_code = "PROTOCOL_FAILURE"
            child_result = None
            if process is not None:
                _terminate_process(process)
        finally:
            if process is not None:
                _terminate_process(process)
                try:
                    exit_code = process.wait(timeout=5)
                except subprocess.SubprocessError:
                    exit_code = process.poll()
                if process.stderr is not None:
                    stderr = process.stderr.read(MAX_CHILD_STDERR_BYTES + 1)
                    if len(stderr) > MAX_CHILD_STDERR_BYTES:
                        stderr = stderr[:MAX_CHILD_STDERR_BYTES]

    work = V075ProductionIPCActualWorkV1(
        1,
        sum(
            entry.direction == "CHILD_TO_PARENT"
            for entry in entries
        ),
        sum(
            entry.direction == "PARENT_TO_CHILD"
            for entry in entries
        ),
        batch_intents,
        support_intents,
        round_begins,
        sum(item.request.accepted_draw_count for item in batches),
        sum(len(item.outcomes) for item in batches),
        child_bytes,
        parent_bytes,
        protocol_checks,
        0,
        exit_code,
    )
    return V075ProductionOccurrenceIPCResultV1(
        profile.profile_id,
        profile.occurrence_identity.occurrence_id,
        profile.open_lifecycle_binding.authority_scope.value,
        "ADAPTIVE_QUOTIENT",
        (
            "PASS"
            if terminal_code == "CHILD_SCIENTIFIC_RESULT_READY"
            and exit_code == 0
            else "FAILED"
        ),
        terminal_code,
        child_result,
        tuple(batches),
        tuple(entries),
        work,
        hashlib.sha256(stderr).hexdigest(),
        len(stderr),
    )


@dataclass(frozen=True, slots=True)
class V075ProductionIPCStandaloneVerificationV1:
    result_id: str
    occurrence_id: str
    child_result_id: str
    final_backend_result_id: str
    final_planner_result_id: str
    replayed_batch_count: int
    evaluation_planner_replays: int = 1
    operational_work_charged: bool = False
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.result_id, "standalone verified IPC result"),
            (self.occurrence_id, "standalone verified occurrence"),
            (self.child_result_id, "standalone verified child result"),
            (self.final_backend_result_id, "standalone verified backend"),
            (self.final_planner_result_id, "standalone verified planner"),
        ):
            _cid(value, name)
        if (
            type(self.replayed_batch_count) is not int
            or self.replayed_batch_count <= 0
            or self.evaluation_planner_replays != 1
            or self.operational_work_charged is not False
        ):
            _fail("standalone IPC verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("standalone_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_occurrence_ipc_"
                "standalone_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "occurrence_id": self.occurrence_id,
            "child_result_id": self.child_result_id,
            "final_backend_result_id": self.final_backend_result_id,
            "final_planner_result_id": self.final_planner_result_id,
            "replayed_batch_count": self.replayed_batch_count,
            "evaluation_planner_replays": self.evaluation_planner_replays,
            "evaluation_lane": True,
            "operational_work_charged": self.operational_work_charged,
            "exact_public_semantic_replay": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_occurrence_ipc_result_standalone_v1(
    *,
    profile: V075ProductionOccurrenceIPCProfileV1,
    claimed: V075ProductionOccurrenceIPCResultV1,
) -> V075ProductionIPCStandaloneVerificationV1:
    """Evaluation-only exact backend/planner replay.

    This function is intentionally not called by the operational executor.
    """

    from acfqp import v075_batch_native_statistical_backend_v1 as backend

    if (
        type(profile) is not V075ProductionOccurrenceIPCProfileV1
        or type(claimed) is not V075ProductionOccurrenceIPCResultV1
        or claimed.profile_id != profile.profile_id
        or claimed.occurrence_id
        != profile.occurrence_identity.occurrence_id
        or claimed.status != "PASS"
        or claimed.child_result is None
    ):
        _fail("standalone verifier requires one matching passing IPC result")
    request = backend.freeze_v075_batch_native_backend_request_v1(
        arm=profile.occurrence_identity.arm,
        occurrence_ordinal=profile.occurrence_identity.occurrence_ordinal,
        batches=claimed.observed_batches,
        source_prior_transport=profile.source_prior_transport,
        occurrence_identity=profile.occurrence_identity,
    )
    replayed_backend = (
        backend.compile_v075_batch_native_statistical_backend_v1(request)
    )
    replayed_planner = backend.plan_v075_batch_native_route_v1(
        replayed_backend
    )
    child = claimed.child_result
    if (
        replayed_backend.result_id != child["final_backend_result_id"]
        or replayed_backend.to_document() != child["final_backend_result"]
        or replayed_planner.result_id != child["final_planner_result_id"]
        or replayed_planner.to_document() != child["final_planner_result"]
    ):
        _fail("isolated child backend/planner differs from standalone replay")
    return V075ProductionIPCStandaloneVerificationV1(
        claimed.result_id,
        claimed.occurrence_id,
        child["child_result_id"],
        replayed_backend.result_id,
        replayed_planner.result_id,
        len(claimed.observed_batches),
    )


def _child_main() -> int:
    try:
        # ``-I`` removes the repository from sys.path.  The registered module
        # digest fixes this source tree; only that fixed parent directory is
        # added, never caller input or PYTHONPATH.
        source_root = str(Path(__file__).resolve().parents[1])
        if source_root not in sys.path:
            sys.path.insert(0, source_root)
        launch = _load_launch(_read_frame_child(sys.stdin.buffer))
        result = _child_scientific_run(launch)
        if (
            launch["_behavior"]
            is V075ProductionIPCBehaviorV1.ATTACK_EXTRA_BATCH_INTENT
        ):
            # Emit an otherwise well-formed extra request after scientific
            # completion should have been determined.
            from acfqp import v075_public_graph_semantics_v1 as graph

            row = graph.observation_row_binding_v1(
                launch["_context"],
                graph.root_catalogue_v1(launch["_context"]),
                graph.root_catalogue_v1(launch["_context"]).actions[0],
            )
            _root, stream = _bootstrap_stream(
                launch["_namespace"],
                row,
                launch["_arm"],
            )
            extra = _batch_intent_document(
                profile_id=launch["profile_id"],
                occurrence_id=launch["_identity"].occurrence_id,
                sequence_number=MAX_PROTOCOL_MESSAGES + 1,
                phase="EXTRA",
                round_index=0,
                intent_kind="EXTRA",
                scientific_intent_id=hashlib.sha256(b"extra").hexdigest(),
                authorization_id=None,
                stream=stream,
                accepted_draw_start=1,
                accepted_draw_count=1,
                accepted_draw_cap=1,
            )
            _write_frame(sys.stdout.buffer, _canonical_bytes(extra))
            return 75
        _write_frame(sys.stdout.buffer, _canonical_bytes(result))
        return 0
    except BaseException as error:
        # Never echo values: exception types cannot contain a law, salt, key,
        # random word, or signed observation.
        sys.stderr.write(type(error).__name__ + "\n")
        return 74


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == _CHILD_ARG:
        raise SystemExit(_child_main())
    raise SystemExit(64)


__all__ = [
    "HOST_OPERATIONAL_FULL_PLANNER_REPLAY_ALLOWED",
    "MATCHED_DIRECT_HANDLER_READY",
    "PICKLE_TRANSPORT_ALLOWED",
    "PRIVATE_MATERIAL_TRANSPORT_ALLOWED",
    "PRODUCTION_OCCURRENCE_WORKER_COMPLETE",
    "PRODUCTION_TRANSPORT_READY",
    "TARGET_EXECUTION_OPENED",
    "V075ProductionIPCActualWorkV1",
    "V075ProductionIPCBehaviorV1",
    "V075ProductionIPCChildProgramRegistrationV1",
    "V075ProductionIPCJournalEntryV1",
    "V075ProductionIPCStandaloneVerificationV1",
    "V075ProductionOccurrenceIPCInvariantViolation",
    "V075ProductionOccurrenceIPCProfileV1",
    "V075ProductionOccurrenceIPCResultV1",
    "execute_v075_production_adaptive_occurrence_ipc_v1",
    "freeze_v075_production_occurrence_ipc_profile_v1",
    "registered_v075_production_occurrence_child_program_v1",
    "verify_v075_occurrence_ipc_result_standalone_v1",
]
