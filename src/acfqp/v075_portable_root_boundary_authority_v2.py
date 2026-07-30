"""Portable M2 authority for occurrence identity and root execution.

The only replay entry starts with the hardened M1B raw replay.  It then binds
the producer bytes for ``OCCURRENCE_IDENTITY`` to M0's exact typed occurrence
and reconstructs ``ROOT_EXECUTION`` as a strict same-implementation producer
view.  Root-execution semantics come from an exact relationship replay over
M0's preregistered schedule and M1B's signed head/intent/append/support/prefix
authorities; an in-process producer issuer token is never treated as evidence.

This remains a construction-only semantic cut.  It does not consume M1A's
private closure-verification claim, does not open a private observer channel,
does not authorize held-out access, and issues no plan or infeasibility
certificate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as identity
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_signed_batch_graph_authority_v2 as m1a
from acfqp import v075_portable_signed_control_graph_authority_v2 as m1b


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.72.0"
PROFILE_KEY = "v075_portable_root_boundary_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
PRIVATE_REPLAY_PERFORMED = False
M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED = False
INDEPENDENT_ROOT_EXECUTION_VERIFIER_PROVIDED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M2_ROOT_BOUNDARY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "M2_ROOT_BOUNDARY_PUBLICLY_REPLAYED_REMAINING_REGISTRY_OPEN"
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = ("OCCURRENCE_IDENTITY", "ROOT_EXECUTION")
_ROLE_SET = frozenset(ROLE_ORDER)
_ROLE_SCHEMA = MappingProxyType(
    {
        "OCCURRENCE_IDENTITY": "acfqp.v075_batch_native_occurrence.v1",
        "ROOT_EXECUTION": "acfqp.v075_observer_signed_root_execution.v2",
    }
)
_ROLE_ID_FIELD = MappingProxyType(
    {
        "OCCURRENCE_IDENTITY": "occurrence_id",
        "ROOT_EXECUTION": "execution_id",
    }
)

DOMAIN_TAGS = MappingProxyType(
    {
        "root_view": "acfqp:v075-portable-root-execution-view:v2",
        "typed_graph": "acfqp:v075-portable-root-boundary-typed-graph:v2",
        "dependency_dag": (
            "acfqp:v075-portable-root-boundary-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-root-boundary-record-attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-root-boundary-role-closure:v2"
        ),
        "aggregate": "acfqp:v075-portable-root-boundary-authority:v2",
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 M2 root-boundary content domains overlap")


class V075PortableRootBoundaryV2InvariantViolation(ValueError):
    """Raw bytes, producer identity, root relation, or dependency is invalid."""


class V075PortableRootBoundaryProductionV2NotReady(RuntimeError):
    """The M2 construction cut cannot authorize production execution."""


class V075PortableRootRoleClosureStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class V075PortableRootResolverKindV2(str, Enum):
    UPSTREAM_M1B_PUBLIC = "UPSTREAM_M1B_PUBLIC"
    M2_OCCURRENCE_IDENTITY = "M2_OCCURRENCE_IDENTITY"
    M2_ROOT_EXECUTION = "M2_ROOT_EXECUTION"
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableRootBoundaryV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableRootBoundaryV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortableRootBoundaryV2InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortableRootBoundaryV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


_ROOT_EXECUTION_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "schedule_id",
        "schedule_verification_id",
        "occurrence_id",
        "resulting_head_id",
        "open_prefix_verification_id",
        "discovery_intent_ids",
        "discovery_receipt_ids",
        "support_promotion_template_ids",
        "support_freeze_ids",
        "support_promotion_freeze_bindings",
        "validation_intent_ids",
        "validation_receipt_ids",
        "root_row_binding_ids",
        "all_preregistered_root_rows_executed_exactly_once",
        "all_support_promotion_templates_matched_exactly_once",
        "support_promotion_dependency_chain_exactly_replayed",
        "support_frozen_before_same_row_validation",
        "observer_signed_prefix_exactly_replayed",
        "official_execution_allowed",
        "execution_id",
    }
)
_ROOT_TRUE_FIELDS = (
    "all_preregistered_root_rows_executed_exactly_once",
    "all_support_promotion_templates_matched_exactly_once",
    "support_promotion_dependency_chain_exactly_replayed",
    "support_frozen_before_same_row_validation",
    "observer_signed_prefix_exactly_replayed",
)
_ROOT_ID_LIST_FIELDS = (
    "discovery_intent_ids",
    "discovery_receipt_ids",
    "support_promotion_template_ids",
    "support_freeze_ids",
    "validation_intent_ids",
    "validation_receipt_ids",
    "root_row_binding_ids",
)


def _parse_root_execution_document(
    raw: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = _strict_document(raw, label="M2 ROOT_EXECUTION")
    if (
        set(document) != _ROOT_EXECUTION_KEYS
        or document.get("schema")
        != "acfqp.v075_observer_signed_root_execution.v2"
        or document.get("schema_version") != runner.SCHEMA_VERSION
        or document.get("profile_key") != runner.PROFILE_KEY
        or any(document.get(name) is not True for name in _ROOT_TRUE_FIELDS)
        or document.get("official_execution_allowed") is not False
    ):
        _fail("M2 ROOT_EXECUTION metadata, shape, or locks changed")
    for field_name in (
        "schedule_id",
        "schedule_verification_id",
        "occurrence_id",
        "resulting_head_id",
        "open_prefix_verification_id",
        "execution_id",
    ):
        _cid(document.get(field_name), f"M2 ROOT_EXECUTION {field_name}")
    width: int | None = None
    normalized: dict[str, Any] = {}
    for field_name in _ROOT_ID_LIST_FIELDS:
        values = document.get(field_name)
        if (
            type(values) is not list
            or not values
            or len(set(values)) != len(values)
        ):
            _fail(f"M2 ROOT_EXECUTION {field_name} is malformed")
        for value in values:
            _cid(value, f"M2 ROOT_EXECUTION {field_name} member")
        if width is None:
            width = len(values)
        elif len(values) != width:
            _fail("M2 ROOT_EXECUTION row-aligned vectors differ in width")
        normalized[field_name] = tuple(values)
    raw_bindings = document.get("support_promotion_freeze_bindings")
    if (
        type(raw_bindings) is not list
        or len(raw_bindings) != width
        or any(
            type(item) is not dict
            or set(item)
            != {
                "support_promotion_template_id",
                "support_freeze_id",
            }
            for item in raw_bindings
        )
    ):
        _fail("M2 ROOT_EXECUTION promotion/freeze bindings are malformed")
    bindings = tuple(
        (
            _cid(
                item["support_promotion_template_id"],
                "M2 ROOT_EXECUTION promotion template",
            ),
            _cid(
                item["support_freeze_id"],
                "M2 ROOT_EXECUTION support freeze",
            ),
        )
        for item in raw_bindings
    )
    if bindings != tuple(
        zip(
            normalized["support_promotion_template_ids"],
            normalized["support_freeze_ids"],
            strict=True,
        )
    ):
        _fail("M2 ROOT_EXECUTION promotion/freeze pairing changed")
    payload = {key: value for key, value in document.items() if key != "execution_id"}
    try:
        expected_id = runner._hash("root_execution", payload)  # noqa: SLF001
    except Exception as error:
        raise V075PortableRootBoundaryV2InvariantViolation(
            "M2 ROOT_EXECUTION producer content-ID replay failed"
        ) from error
    if document["execution_id"] != expected_id:
        _fail("M2 ROOT_EXECUTION cached producer content ID is stale")
    normalized["support_promotion_freeze_bindings"] = bindings
    return document, normalized


@dataclass(frozen=True, slots=True)
class V075PortableRootExecutionProducerViewV2:
    """Strict producer-byte view; semantics are supplied by the M0/M1B replay."""

    canonical_bytes: bytes = field(repr=False)
    schedule_id: str = field(init=False)
    schedule_verification_id: str = field(init=False)
    occurrence_id: str = field(init=False)
    resulting_head_id: str = field(init=False)
    open_prefix_verification_id: str = field(init=False)
    discovery_intent_ids: tuple[str, ...] = field(init=False)
    discovery_receipt_ids: tuple[str, ...] = field(init=False)
    support_promotion_template_ids: tuple[str, ...] = field(init=False)
    support_freeze_ids: tuple[str, ...] = field(init=False)
    support_promotion_freeze_bindings: tuple[
        tuple[str, str], ...
    ] = field(init=False)
    validation_intent_ids: tuple[str, ...] = field(init=False)
    validation_receipt_ids: tuple[str, ...] = field(init=False)
    root_row_binding_ids: tuple[str, ...] = field(init=False)
    execution_id: str = field(init=False)
    _view_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        document, normalized = _parse_root_execution_document(
            self.canonical_bytes
        )
        for field_name in (
            "schedule_id",
            "schedule_verification_id",
            "occurrence_id",
            "resulting_head_id",
            "open_prefix_verification_id",
            "execution_id",
        ):
            object.__setattr__(self, field_name, document[field_name])
        for field_name in (
            *_ROOT_ID_LIST_FIELDS,
            "support_promotion_freeze_bindings",
        ):
            object.__setattr__(self, field_name, normalized[field_name])
        object.__setattr__(
            self,
            "_view_id",
            _hash("root_view", self._identity_payload()),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_root_execution_view.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "producer_execution_id": self.execution_id,
            "canonical_artifact_sha256": hashlib.sha256(
                self.canonical_bytes
            ).hexdigest(),
            "canonical_artifact_byte_count": len(self.canonical_bytes),
            "producer_content_id_recomputed": True,
            "same_implementation_reconstruction": True,
            "independent_verifier_provided": False,
            "issuer_token_consumed_as_authority": False,
        }

    def _assert_current(self) -> None:
        replayed = V075PortableRootExecutionProducerViewV2(
            self.canonical_bytes
        )
        fields = (
            "schedule_id",
            "schedule_verification_id",
            "occurrence_id",
            "resulting_head_id",
            "open_prefix_verification_id",
            *_ROOT_ID_LIST_FIELDS,
            "support_promotion_freeze_bindings",
            "execution_id",
        )
        if (
            any(getattr(self, name) != getattr(replayed, name) for name in fields)
            or self._view_id != replayed._view_id
        ):
            _fail("M2 ROOT_EXECUTION producer view is stale or mutated")

    @property
    def view_id(self) -> str:
        self._assert_current()
        return self._view_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return _strict_document(
            self.canonical_bytes,
            label="M2 ROOT_EXECUTION current bytes",
        )


@dataclass(frozen=True, slots=True)
class _RootRecordBindingV2:
    record_id: str
    record_index: int
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "M2 root-boundary record")
        _cid(self.semantic_artifact_id, "M2 root-boundary semantic artifact")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or self.artifact_schema != _ROLE_SCHEMA[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
            or type(self.canonical_artifact_bytes) is not bytes
            or not self.canonical_artifact_bytes
        ):
            _fail("M2 root-boundary record binding is malformed")
        for dependency_id in self.dependency_record_ids:
            _cid(dependency_id, "M2 root-boundary dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"M2 {self.role} record",
        )
        if (
            document.get("schema") != self.artifact_schema
            or _cid(
                document.get(_ROLE_ID_FIELD[self.role]),
                f"M2 {self.role} producer identity",
            )
            != self.semantic_artifact_id
        ):
            _fail(f"M2 {self.role} was role- or identity-transplanted")

    def commitment_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_sha256": hashlib.sha256(
                self.canonical_artifact_bytes
            ).hexdigest(),
            "canonical_artifact_byte_count": len(
                self.canonical_artifact_bytes
            ),
        }


def _binding_from_record(record: Any) -> _RootRecordBindingV2:
    try:
        return _RootRecordBindingV2(
            record.record_id,
            record.index,
            record.role,
            record.artifact_schema,
            record.semantic_artifact_id,
            tuple(record.dependency_record_ids),
            record.canonical_artifact_bytes,
        )
    except (AttributeError, TypeError, ValueError) as error:
        if type(error) is V075PortableRootBoundaryV2InvariantViolation:
            raise
        raise V075PortableRootBoundaryV2InvariantViolation(
            "M2 root-boundary record cannot be bound"
        ) from error


def _root_schedule_parts(schedule: Any) -> tuple[tuple[Any, ...], ...]:
    discoveries = tuple(
        item
        for item in schedule.intents
        if item.kind is acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY
    )
    promotions = tuple(
        item
        for item in schedule.intents
        if item.kind
        is acquisition.V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
    )
    validations = tuple(
        item
        for item in schedule.intents
        if item.kind is acquisition.V075InitialIntentKindV2.ROOT_VALIDATION
    )
    rows = tuple(item.row_binding for item in discoveries)
    if (
        not discoveries
        or len(discoveries) != len(promotions)
        or len(discoveries) != len(validations)
        or tuple(item.row_binding for item in promotions) != rows
        or tuple(item.row_binding for item in validations) != rows
        or tuple(item.dependency_intent_ids for item in promotions)
        != tuple((item.intent_id,) for item in discoveries)
        or tuple(item.dependency_intent_ids for item in validations)
        != tuple((item.intent_id,) for item in promotions)
    ):
        _fail("M2 M0 root discovery/promotion/validation schedule changed")
    return discoveries, promotions, validations


def _validate_occurrence_binding_against_m0(
    *,
    binding: _RootRecordBindingV2,
    occurrence: identity.V075BatchNativeOccurrenceIdentityV1,
) -> identity.V075BatchNativeOccurrenceIdentityV1:
    if binding.role != "OCCURRENCE_IDENTITY":
        _fail("M2 occurrence validation received a foreign role")
    replayed = identity.replay_v075_batch_native_occurrence_identity_v1(
        occurrence
    )
    if (
        binding.semantic_artifact_id != replayed.occurrence_id
        or binding.canonical_artifact_bytes
        != canonical_json_bytes(replayed.to_document())
    ):
        _fail("M2 occurrence record differs from exact M0 occurrence bytes")
    return replayed


def _validate_root_execution_relationship(
    *,
    replay: m1b.V075PortableSignedControlGraphReplayV2,
    occurrence: identity.V075BatchNativeOccurrenceIdentityV1,
    root: V075PortableRootExecutionProducerViewV2,
) -> None:
    """Replay every root-execution field against already-validated objects.

    The owning typed-graph transaction fully validates ``replay`` and ``root``
    exactly once before entering this relationship check.  Revalidating either
    here would recursively replay the complete M1B graph without adding an
    independent obligation.
    """
    m0_graph = (
        replay.typed_graph.m1a_result.typed_graph.m0_result.typed_graph
    )
    replayed_occurrence = identity.replay_v075_batch_native_occurrence_identity_v1(
        occurrence
    )
    discoveries, promotions, validations = _root_schedule_parts(
        m0_graph.schedule
    )
    expected_discovery_ids = tuple(item.intent_id for item in discoveries)
    expected_promotion_ids = tuple(item.intent_id for item in promotions)
    expected_validation_ids = tuple(item.intent_id for item in validations)
    expected_rows = tuple(
        item.row_binding.row_binding_id for item in discoveries
    )
    if (
        canonical_json_bytes(replayed_occurrence.to_document())
        != canonical_json_bytes(m0_graph.occurrence.to_document())
        or root.schedule_id != m0_graph.schedule.schedule_id
        or root.schedule_verification_id
        != m0_graph.verification.verification_id
        or root.occurrence_id != replayed_occurrence.occurrence_id
        or root.discovery_intent_ids != expected_discovery_ids
        or root.support_promotion_template_ids != expected_promotion_ids
        or root.validation_intent_ids != expected_validation_ids
        or root.root_row_binding_ids != expected_rows
    ):
        _fail("M2 ROOT_EXECUTION differs from exact M0 authorities")

    root_appends = tuple(
        item
        for item in replay.typed_graph.appends
        if item.intent.semantic_authority.role
        is (
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .INITIAL_SCHEDULE_ROW_INTENT
        )
    )
    expected_artifacts = (*expected_discovery_ids, *expected_validation_ids)
    if (
        len(root_appends) != len(expected_artifacts)
        or replay.typed_graph.appends[: len(root_appends)] != root_appends
        or tuple(
            item.intent.semantic_authority.semantic_artifact_id
            for item in root_appends
        )
        != expected_artifacts
    ):
        _fail("M2 signed ROOT appends are not the exact initial M0 prefix")
    width = len(discoveries)
    discovery_appends = root_appends[:width]
    validation_appends = root_appends[width:]
    if (
        root.discovery_receipt_ids
        != tuple(item.receipt.receipt_id for item in discovery_appends)
        or root.validation_receipt_ids
        != tuple(item.receipt.receipt_id for item in validation_appends)
        or root.resulting_head_id != root_appends[-1].resulting_head.head_id
    ):
        _fail("M2 ROOT_EXECUTION receipt/head mapping changed")

    support_by_discovery_receipt: dict[str, Any] = {}
    for support in replay.typed_graph.support_freezes:
        receipt_id = support.discovery_append_receipt_id
        if receipt_id in support_by_discovery_receipt:
            _fail("M2 signed support freezes duplicate a discovery receipt")
        support_by_discovery_receipt[receipt_id] = support
    supports = tuple(
        support_by_discovery_receipt.get(item.receipt.receipt_id)
        for item in discovery_appends
    )
    if (
        any(item is None for item in supports)
        or tuple(item.row_binding_id for item in supports) != expected_rows
        or root.support_freeze_ids
        != tuple(item.freeze_id for item in supports)
        or root.support_promotion_freeze_bindings
        != tuple(
            zip(
                expected_promotion_ids,
                root.support_freeze_ids,
                strict=True,
            )
        )
    ):
        _fail("M2 ROOT_EXECUTION support/promotion mapping changed")
    if any(
        append.intent.semantic_authority.support_freeze_id
        != support.freeze_id
        or append.intent.stream_identity.row_binding_id != row_id
        for append, support, row_id in zip(
            validation_appends,
            supports,
            expected_rows,
            strict=True,
        )
    ):
        _fail("M2 validation is not bound to its same-row support freeze")

    prefixes = tuple(
        item
        for item in replay.typed_graph.open_prefixes
        if item.verification_id == root.open_prefix_verification_id
    )
    expected_heads = replay.typed_graph.heads[: len(root_appends) + 1]
    if (
        len(prefixes) != 1
        or prefixes[0].heads != expected_heads
        or prefixes[0].appends != root_appends
        or prefixes[0].support_freezes != supports
        or prefixes[0].current_head_id != root.resulting_head_id
        or prefixes[0].head_ids
        != tuple(item.head_id for item in expected_heads)
        or prefixes[0].receipt_ids
        != (*root.discovery_receipt_ids, *root.validation_receipt_ids)
        or prefixes[0].support_freeze_ids != root.support_freeze_ids
    ):
        _fail("M2 ROOT_EXECUTION open signed prefix mapping changed")


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableRootBoundaryTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    m1b_result: m1b.V075PortableSignedControlGraphReplayV2 = field(
        repr=False
    )
    occurrence: identity.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    root_execution: V075PortableRootExecutionProducerViewV2 = field(
        repr=False
    )
    record_bindings: tuple[_RootRecordBindingV2, ...] = field(repr=False)
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("M2 root-boundary typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M2 typed graph bundle"),
            (self.public_context_closure_id, "M2 typed graph context"),
            (self.occurrence_id, "M2 typed graph occurrence"),
        ):
            _cid(value, label)
        if (
            type(self.m1b_result)
            is not m1b.V075PortableSignedControlGraphReplayV2
            or type(self.occurrence)
            is not identity.V075BatchNativeOccurrenceIdentityV1
            or type(self.root_execution)
            is not V075PortableRootExecutionProducerViewV2
            or type(self.record_bindings) is not tuple
            or len(self.record_bindings) != len(ROLE_ORDER)
            or tuple(item.role for item in self.record_bindings) != ROLE_ORDER
            or len({item.record_id for item in self.record_bindings})
            != len(self.record_bindings)
        ):
            _fail("M2 root-boundary typed graph is malformed")
        self.m1b_result._assert_current()  # noqa: SLF001
        self.root_execution._assert_current()
        for item in self.record_bindings:
            item._assert_current()
        by_role = {item.role: item for item in self.record_bindings}
        occurrence_binding = by_role["OCCURRENCE_IDENTITY"]
        root_binding = by_role["ROOT_EXECUTION"]
        replayed_occurrence = _validate_occurrence_binding_against_m0(
            binding=occurrence_binding,
            occurrence=self.occurrence,
        )
        if (
            self.m1b_result.bundle_id != self.bundle_id
            or self.m1b_result.public_context_closure_id
            != self.public_context_closure_id
            or self.m1b_result.occurrence_id != self.occurrence_id
            or replayed_occurrence.occurrence_id != self.occurrence_id
            or self.root_execution.occurrence_id != self.occurrence_id
            or root_binding.semantic_artifact_id
            != self.root_execution.execution_id
            or root_binding.canonical_artifact_bytes
            != self.root_execution.canonical_bytes
        ):
            _fail("M2 typed objects differ from exact portable records")
        _validate_root_execution_relationship(
            replay=self.m1b_result,
            occurrence=replayed_occurrence,
            root=self.root_execution,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_root_boundary_typed_graph.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            "m1b_result_id": self.m1b_result._result_id,  # noqa: SLF001
            "m1b_typed_graph_id": (
                self.m1b_result.typed_graph._graph_id  # noqa: SLF001
            ),
            "occurrence_producer_id": self.occurrence.occurrence_id,
            "root_execution_producer_id": self.root_execution.execution_id,
            "root_execution_view_id": self.root_execution._view_id,
            "ordered_record_commitments": [
                item.commitment_document() for item in self.record_bindings
            ],
            "root_relationship_replayed_against_m0_m1b": True,
            "root_signatures_consumed_through_hardened_m1b": True,
            "issuer_token_consumed_as_independent_authority": False,
            "same_implementation_root_view_used": True,
            "independent_root_execution_verifier_provided": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._identity_payload()):
            _fail("M2 root-boundary typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def __reduce__(self) -> NoReturn:
        raise TypeError("M2 root-boundary typed graph is in-memory-only")


@dataclass(frozen=True, slots=True)
class V075PortableRootDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    direct_dependency_record_ids: tuple[str, ...]
    resolver_kind: V075PortableRootResolverKindV2
    semantically_resolved: bool

    def _assert_current(self) -> None:
        _cid(self.record_id, "M2 dependency node")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or type(self.role) is not str
            or not self.role
            or type(self.direct_dependency_record_ids) is not tuple
            or tuple(sorted(set(self.direct_dependency_record_ids)))
            != self.direct_dependency_record_ids
            or type(self.resolver_kind)
            is not V075PortableRootResolverKindV2
            or type(self.semantically_resolved) is not bool
        ):
            _fail("M2 dependency node is malformed")
        for value in self.direct_dependency_record_ids:
            _cid(value, "M2 dependency edge")

    @property
    def local_semantic_authority_resolved(self) -> bool:
        return (
            self.resolver_kind
            is not V075PortableRootResolverKindV2
            .NO_REGISTERED_SEMANTIC_AUTHORITY
        )

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "direct_dependency_record_ids": list(
                self.direct_dependency_record_ids
            ),
            "resolver_kind": self.resolver_kind.value,
            "local_semantic_authority_resolved": (
                self.local_semantic_authority_resolved
            ),
            "semantically_resolved": self.semantically_resolved,
        }


def _expected_resolver_kind(
    *,
    record_id: str,
    role: str,
    upstream_public_record_ids: frozenset[str],
    private_verification_record_ids: frozenset[str],
) -> V075PortableRootResolverKindV2:
    if record_id in private_verification_record_ids:
        return V075PortableRootResolverKindV2.NO_REGISTERED_SEMANTIC_AUTHORITY
    if role == "OCCURRENCE_IDENTITY":
        return V075PortableRootResolverKindV2.M2_OCCURRENCE_IDENTITY
    if role == "ROOT_EXECUTION":
        return V075PortableRootResolverKindV2.M2_ROOT_EXECUTION
    if record_id in upstream_public_record_ids:
        return V075PortableRootResolverKindV2.UPSTREAM_M1B_PUBLIC
    return V075PortableRootResolverKindV2.NO_REGISTERED_SEMANTIC_AUTHORITY


def _iterative_root_dependency_nodes(
    *,
    records: tuple[Any, ...],
    upstream_public_record_ids: frozenset[str],
    private_verification_record_ids: frozenset[str],
) -> tuple[V075PortableRootDependencyNodeV2, ...]:
    """Resolve the complete direct-edge DAG in O(V+E), without recursion."""

    if type(records) is not tuple or not records:
        _fail("M2 dependency replay requires one nonempty record tuple")
    nodes: list[V075PortableRootDependencyNodeV2] = []
    resolved_by_id: dict[str, bool] = {}
    for expected_index, record in enumerate(records):
        try:
            record_id = record.record_id
            record_index = record.index
            role = record.role
            dependencies = tuple(record.dependency_record_ids)
        except (AttributeError, TypeError) as error:
            raise V075PortableRootBoundaryV2InvariantViolation(
                "M2 dependency record is malformed"
            ) from error
        if (
            record_index != expected_index
            or record_id in resolved_by_id
            or tuple(sorted(set(dependencies))) != dependencies
            or any(value not in resolved_by_id for value in dependencies)
        ):
            _fail("M2 dependency records are duplicated or non-topological")
        resolver_kind = _expected_resolver_kind(
            record_id=record_id,
            role=role,
            upstream_public_record_ids=upstream_public_record_ids,
            private_verification_record_ids=private_verification_record_ids,
        )
        local_resolved = (
            resolver_kind
            is not V075PortableRootResolverKindV2
            .NO_REGISTERED_SEMANTIC_AUTHORITY
        )
        semantically_resolved = local_resolved and all(
            resolved_by_id[value] for value in dependencies
        )
        node = V075PortableRootDependencyNodeV2(
            record_id,
            record_index,
            role,
            dependencies,
            resolver_kind,
            semantically_resolved,
        )
        node._assert_current()
        nodes.append(node)
        resolved_by_id[record_id] = semantically_resolved
    return tuple(nodes)


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableRootDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m1b_result_id: str
    typed_graph_id: str
    upstream_public_record_ids: tuple[str, ...]
    private_verification_record_ids: tuple[str, ...]
    nodes: tuple[V075PortableRootDependencyNodeV2, ...] = field(repr=False)
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("M2 dependency DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M2 DAG bundle"),
            (self.m1b_result_id, "M2 DAG M1B result"),
            (self.typed_graph_id, "M2 DAG typed graph"),
        ):
            _cid(value, label)
        for values, label in (
            (self.upstream_public_record_ids, "upstream"),
            (self.private_verification_record_ids, "private verification"),
        ):
            if (
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
            ):
                _fail(f"M2 DAG {label} identity set is malformed")
            for value in values:
                _cid(value, f"M2 DAG {label} record")
        if (
            set(self.upstream_public_record_ids)
            & set(self.private_verification_record_ids)
            or type(self.nodes) is not tuple
            or not self.nodes
            or tuple(item.record_index for item in self.nodes)
            != tuple(range(len(self.nodes)))
            or len({item.record_id for item in self.nodes})
            != len(self.nodes)
        ):
            _fail("M2 dependency DAG is malformed")
        upstream = frozenset(self.upstream_public_record_ids)
        private = frozenset(self.private_verification_record_ids)
        resolved: dict[str, bool] = {}
        for item in self.nodes:
            item._assert_current()
            if any(
                dependency_id not in resolved
                for dependency_id in item.direct_dependency_record_ids
            ):
                _fail("M2 dependency DAG is not topological")
            expected_kind = _expected_resolver_kind(
                record_id=item.record_id,
                role=item.role,
                upstream_public_record_ids=upstream,
                private_verification_record_ids=private,
            )
            expected_resolved = (
                expected_kind
                is not V075PortableRootResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
                and all(
                    resolved[value]
                    for value in item.direct_dependency_record_ids
                )
            )
            if (
                item.resolver_kind is not expected_kind
                or item.semantically_resolved is not expected_resolved
            ):
                _fail("M2 dependency resolver or status is stale")
            resolved[item.record_id] = item.semantically_resolved
        if any(resolved[value] for value in private):
            _fail("M2 dependency DAG consumed private verification")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_root_boundary_dependency_dag.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m1b_result_id": self.m1b_result_id,
            "m2_typed_graph_id": self.typed_graph_id,
            "upstream_public_record_ids": list(
                self.upstream_public_record_ids
            ),
            "private_verification_record_ids": list(
                self.private_verification_record_ids
            ),
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "edge_count": sum(
                len(item.direct_dependency_record_ids) for item in self.nodes
            ),
            "proof_shape": "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG",
            "transitive_closure_materialized": False,
            "recursive_dependency_walk_used": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("M2 dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(
        self,
    ) -> Mapping[str, V075PortableRootDependencyNodeV2]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableRootRecordAttestationV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    record_id: str
    record_index: int
    role: str
    semantic_artifact_id: str
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    direct_dependency_record_ids: tuple[str, ...]
    resolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_direct_dependency_roles: tuple[str, ...]
    resolver_kind: V075PortableRootResolverKindV2
    status: V075PortableRootRoleClosureStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("M2 root record attestation is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M2 attestation bundle"),
            (self.typed_graph_id, "M2 attestation typed graph"),
            (self.dependency_dag_id, "M2 attestation DAG"),
            (self.record_id, "M2 attestation record"),
            (self.semantic_artifact_id, "M2 attestation semantic artifact"),
            (self.canonical_artifact_sha256, "M2 attestation raw digest"),
        ):
            _cid(value, label)
        sequences = (
            self.direct_dependency_record_ids,
            self.resolved_direct_dependency_record_ids,
            self.unresolved_direct_dependency_record_ids,
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or set(self.resolved_direct_dependency_record_ids)
            | set(self.unresolved_direct_dependency_record_ids)
            != set(self.direct_dependency_record_ids)
            or set(self.resolved_direct_dependency_record_ids)
            & set(self.unresolved_direct_dependency_record_ids)
            or tuple(sorted(set(self.unresolved_direct_dependency_roles)))
            != self.unresolved_direct_dependency_roles
            or type(self.resolver_kind)
            is not V075PortableRootResolverKindV2
            or type(self.status)
            is not V075PortableRootRoleClosureStatusV2
            or self.status
            is V075PortableRootRoleClosureStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
        ):
            _fail("M2 root record attestation is malformed")
        expected_status = (
            V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
            if (
                self.resolver_kind
                is not V075PortableRootResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
                and not self.unresolved_direct_dependency_record_ids
            )
            else V075PortableRootRoleClosureStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        if self.status is not expected_status:
            _fail("M2 root record attestation overclaims semantics")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_root_boundary_record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_typed_graph_id": self.typed_graph_id,
            "m2_dependency_dag_id": self.dependency_dag_id,
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": self.canonical_artifact_sha256,
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "direct_dependency_record_ids": list(
                self.direct_dependency_record_ids
            ),
            "resolved_direct_dependency_record_ids": list(
                self.resolved_direct_dependency_record_ids
            ),
            "unresolved_direct_dependency_record_ids": list(
                self.unresolved_direct_dependency_record_ids
            ),
            "unresolved_direct_dependency_roles": list(
                self.unresolved_direct_dependency_roles
            ),
            "resolver_kind": self.resolver_kind.value,
            "status": self.status.value,
            "producer_canonical_bytes_reconstructed": True,
            "producer_content_id_recomputed": True,
            "root_relationship_replayed_against_m0_m1b": (
                self.role == "ROOT_EXECUTION"
            ),
            "same_implementation_root_view_used": (
                self.role == "ROOT_EXECUTION"
            ),
            "independent_root_execution_verifier_provided": False,
            "issuer_token_consumed_as_authority": False,
            "private_replay_performed": False,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload(),
        ):
            _fail("M2 root record attestation identity is stale")

    @property
    def attestation_id(self) -> str:
        self._assert_current()
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "attestation_id": self._attestation_id}


def _build_attestations(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dag: V075PortableRootDependencyDAGV2,
    bindings: tuple[_RootRecordBindingV2, ...],
) -> tuple[V075PortableRootRecordAttestationV2, ...]:
    dag._assert_current()
    nodes = {item.record_id: item for item in dag.nodes}
    roles_by_id = {item.record_id: item.role for item in dag.nodes}
    result = []
    for binding in bindings:
        node = nodes[binding.record_id]
        resolved = tuple(
            value
            for value in binding.dependency_record_ids
            if nodes[value].semantically_resolved
        )
        unresolved = tuple(
            value
            for value in binding.dependency_record_ids
            if not nodes[value].semantically_resolved
        )
        status = (
            V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
            if node.semantically_resolved
            else V075PortableRootRoleClosureStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortableRootRecordAttestationV2(
                _ATTESTATION_ISSUER,
                bundle_id,
                typed_graph_id,
                dag._dag_id,
                binding.record_id,
                binding.record_index,
                binding.role,
                binding.semantic_artifact_id,
                hashlib.sha256(
                    binding.canonical_artifact_bytes
                ).hexdigest(),
                len(binding.canonical_artifact_bytes),
                binding.dependency_record_ids,
                resolved,
                unresolved,
                tuple(
                    sorted({roles_by_id[value] for value in unresolved})
                ),
                node.resolver_kind,
                status,
            )
        )
    return tuple(result)


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableRootRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    role: str
    status: V075PortableRootRoleClosureStatusV2
    record_ids: tuple[str, ...]
    attestation_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_dependency_record_ids: tuple[str, ...]
    unresolved_dependency_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("M2 role closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M2 role closure bundle"),
            (self.typed_graph_id, "M2 role closure typed graph"),
            (self.dependency_dag_id, "M2 role closure DAG"),
        ):
            _cid(value, label)
        if (
            self.role not in _ROLE_SET
            or type(self.status)
            is not V075PortableRootRoleClosureStatusV2
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in (
                    self.record_ids,
                    self.attestation_ids,
                    self.unresolved_record_ids,
                    self.unresolved_dependency_record_ids,
                    self.unresolved_dependency_roles,
                )
            )
        ):
            _fail("M2 role closure is malformed")
        for value in (
            *self.record_ids,
            *self.attestation_ids,
            *self.unresolved_record_ids,
            *self.unresolved_dependency_record_ids,
        ):
            _cid(value, "M2 role closure member")
        present = bool(self.record_ids)
        if (
            (self.status is V075PortableRootRoleClosureStatusV2
             .NOT_PRESENT_IN_OCCURRENCE)
            != (not present)
            or (not present and any(
                (
                    self.attestation_ids,
                    self.unresolved_record_ids,
                    self.unresolved_dependency_record_ids,
                    self.unresolved_dependency_roles,
                )
            ))
            or (
                self.status
                is V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
                and (
                    self.unresolved_record_ids
                    or self.unresolved_dependency_record_ids
                    or self.unresolved_dependency_roles
                )
            )
            or (
                self.status
                is V075PortableRootRoleClosureStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                and not self.unresolved_record_ids
            )
        ):
            _fail("M2 role closure status differs from its evidence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_root_boundary_role_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_typed_graph_id": self.typed_graph_id,
            "m2_dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "status": self.status.value,
            "record_ids": list(self.record_ids),
            "attestation_ids": list(self.attestation_ids),
            "unresolved_record_ids": list(self.unresolved_record_ids),
            "unresolved_dependency_record_ids": list(
                self.unresolved_dependency_record_ids
            ),
            "unresolved_dependency_roles": list(
                self.unresolved_dependency_roles
            ),
            "present_in_occurrence": bool(self.record_ids),
            "absence_is_not_native_zero": not self.record_ids,
            "absence_is_not_completion": not self.record_ids,
            "public_semantic_closure_complete": (
                self.status
                is V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
            ),
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("M2 role closure identity is stale")

    @property
    def closure_id(self) -> str:
        self._assert_current()
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "closure_id": self._closure_id}


def _build_role_closures(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dependency_dag_id: str,
    records: tuple[Any, ...],
    attestations: tuple[V075PortableRootRecordAttestationV2, ...],
    _attestations_already_current: bool = False,
) -> tuple[V075PortableRootRoleClosureV2, ...]:
    if not _attestations_already_current:
        for item in attestations:
            item._assert_current()
    attestation_by_record = {
        item.record_id: item for item in attestations
    }
    result = []
    for role in ROLE_ORDER:
        role_records = tuple(
            sorted(
                (item for item in records if item.role == role),
                key=lambda item: item.record_id,
            )
        )
        role_attestations = tuple(
            attestation_by_record[item.record_id] for item in role_records
        )
        if not role_records:
            status = (
                V075PortableRootRoleClosureStatusV2
                .NOT_PRESENT_IN_OCCURRENCE
            )
        elif all(
            item.status is V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
            for item in role_attestations
        ):
            status = V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
        else:
            status = (
                V075PortableRootRoleClosureStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        unresolved = tuple(
            item
            for item in role_attestations
            if item.status
            is not V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
        )
        result.append(
            V075PortableRootRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                typed_graph_id,
                dependency_dag_id,
                role,
                status,
                tuple(item.record_id for item in role_records),
                tuple(item._attestation_id for item in role_attestations),
                tuple(item.record_id for item in unresolved),
                tuple(
                    sorted(
                        {
                            dependency_id
                            for item in unresolved
                            for dependency_id in (
                                item.unresolved_direct_dependency_record_ids
                            )
                        }
                    )
                ),
                tuple(
                    sorted(
                        {
                            dependency_role
                            for item in unresolved
                            for dependency_role in (
                                item.unresolved_direct_dependency_roles
                            )
                        }
                    )
                ),
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableRootBoundaryReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortableRootBoundaryTypedGraphV2 = field(repr=False)
    dependency_dag: V075PortableRootDependencyDAGV2 = field(repr=False)
    attestations: tuple[V075PortableRootRecordAttestationV2, ...]
    role_closures: tuple[V075PortableRootRoleClosureV2, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("M2 root-boundary replay result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M2 result bundle"),
            (self.occurrence_id, "M2 result occurrence"),
            (self.public_context_closure_id, "M2 result context"),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075PortableRootBoundaryTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortableRootDependencyDAGV2
            or type(self.attestations) is not tuple
            or tuple(item.role for item in self.attestations) != ROLE_ORDER
            or any(
                type(item) is not V075PortableRootRecordAttestationV2
                for item in self.attestations
            )
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item) is not V075PortableRootRoleClosureV2
                for item in self.role_closures
            )
        ):
            _fail("M2 root-boundary replay result is malformed")
        self.typed_graph._assert_current()
        self.dependency_dag._assert_current()
        typed_graph_id = self.typed_graph._graph_id
        dependency_dag_id = self.dependency_dag._dag_id
        m1b_result_id = self.typed_graph.m1b_result._result_id  # noqa: SLF001
        m1b_nodes = self.typed_graph.m1b_result.dependency_dag.nodes
        exact_upstream_public_record_ids = tuple(
            sorted(
                item.record_id
                for item in m1b_nodes
                if item.semantically_resolved
            )
        )
        exact_private_verification_record_ids = tuple(
            sorted(
                item.record_id
                for item in (
                    self.typed_graph.m1b_result.typed_graph.m1a_result
                    .typed_graph.record_bindings
                )
                if item.role == m1a.M1A_VERIFICATION_ROLE
            )
        )
        if (
            self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.m1b_result_id
            != m1b_result_id
            or self.dependency_dag.typed_graph_id
            != typed_graph_id
            or self.dependency_dag.upstream_public_record_ids
            != exact_upstream_public_record_ids
            or self.dependency_dag.private_verification_record_ids
            != exact_private_verification_record_ids
        ):
            _fail(
                "M2 result crossed authority identities or forged its "
                "M1B-derived authority registries"
            )
        if len(self.dependency_dag.nodes) != len(m1b_nodes):
            _fail("M2 dependency DAG differs from the complete M1B spine")
        for node, upstream_node in zip(
            self.dependency_dag.nodes,
            m1b_nodes,
            strict=True,
        ):
            if (
                node.record_id != upstream_node.record_id
                or node.record_index != upstream_node.record_index
                or node.role != upstream_node.role
                or node.direct_dependency_record_ids
                != upstream_node.direct_dependency_record_ids
            ):
                _fail(
                    "M2 dependency DAG record/index/role/direct-edge spine "
                    "differs from hardened M1B"
                )
        nodes = {
            item.record_id: item for item in self.dependency_dag.nodes
        }
        bindings = {
            item.record_id: item for item in self.typed_graph.record_bindings
        }
        attestations = {item.record_id: item for item in self.attestations}
        if set(bindings) != set(attestations):
            _fail("M2 attestations differ from exact root records")
        for record_id, binding in bindings.items():
            node = nodes[record_id]
            item = attestations[record_id]
            binding._assert_current()
            item._assert_current()
            resolved = tuple(
                value
                for value in binding.dependency_record_ids
                if nodes[value].semantically_resolved
            )
            unresolved = tuple(
                value
                for value in binding.dependency_record_ids
                if not nodes[value].semantically_resolved
            )
            expected_status = (
                V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
                if node.semantically_resolved
                else V075PortableRootRoleClosureStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
            if (
                item.bundle_id != self.bundle_id
                or item.typed_graph_id != typed_graph_id
                or item.dependency_dag_id != dependency_dag_id
                or item.record_index != binding.record_index
                or item.role != binding.role
                or item.semantic_artifact_id != binding.semantic_artifact_id
                or item.canonical_artifact_sha256
                != hashlib.sha256(
                    binding.canonical_artifact_bytes
                ).hexdigest()
                or item.canonical_artifact_byte_count
                != len(binding.canonical_artifact_bytes)
                or item.direct_dependency_record_ids
                != binding.dependency_record_ids
                or item.resolved_direct_dependency_record_ids != resolved
                or item.unresolved_direct_dependency_record_ids != unresolved
                or item.unresolved_direct_dependency_roles
                != tuple(
                    sorted(
                        {
                            nodes[value].role
                            for value in unresolved
                        }
                    )
                )
                or item.resolver_kind is not node.resolver_kind
                or item.status is not expected_status
            ):
                _fail("M2 attestation differs from binding/DAG replay")
        expected_closures = _build_role_closures(
            bundle_id=self.bundle_id,
            typed_graph_id=typed_graph_id,
            dependency_dag_id=dependency_dag_id,
            records=self.typed_graph.record_bindings,
            attestations=self.attestations,
            _attestations_already_current=True,
        )
        for item in self.role_closures:
            item._assert_current()
        if tuple(
            (item._payload(), item._closure_id)
            for item in self.role_closures
        ) != tuple(
            (item._payload(), item._closure_id)
            for item in expected_closures
        ):
            _fail("M2 role closure summary is stale or overclaims")
        private_ids = set(exact_private_verification_record_ids)
        if any(nodes[value].semantically_resolved for value in private_ids):
            _fail("M2 result consumed private closure verification")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_root_boundary_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "m1b_result_id": (
                self.typed_graph.m1b_result._result_id  # noqa: SLF001
            ),
            "m2_typed_graph_id": self.typed_graph._graph_id,
            "m2_dependency_dag_id": self.dependency_dag._dag_id,
            "role_order": list(ROLE_ORDER),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "record_attestation_ids": [
                item._attestation_id for item in self.attestations
            ],
            "role_closure_ids": [
                item._closure_id for item in self.role_closures
            ],
            "root_execution_public_semantic_closure_complete": (
                next(
                    item
                    for item in self.role_closures
                    if item.role == "ROOT_EXECUTION"
                ).status
                is V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
            ),
            "hardened_m1b_called_before_local_bundle_replay": True,
            "root_relationship_replayed_against_m0_m1b": True,
            "private_verifier_called": False,
            "private_input_channels_allowed": False,
            "private_replay_performed": False,
            "m1a_private_verification_claim_consumed": False,
            "issuer_token_consumed_as_independent_authority": False,
            "same_implementation_root_view_used": True,
            "independent_root_execution_verifier_provided": False,
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

    def _assert_current(self) -> None:
        self._validate()
        if self._result_id != _hash("aggregate", self._payload()):
            _fail("M2 root-boundary replay result identity is stale")

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "attestations": [
                item.to_document() for item in self.attestations
            ],
            "role_closures": [
                item.to_document() for item in self.role_closures
            ],
            "result_id": self._result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("M2 root-boundary replay result exceeds output cap")
        return raw


def replay_v075_portable_root_boundary_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortableRootBoundaryReplayV2:
    """Replay M2 from raw public authorities, starting with hardened M1B."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M2 accepts canonical raw byte authorities only")
    try:
        upstream = m1b.replay_v075_portable_signed_control_graph_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortableRootBoundaryV2InvariantViolation(
            "M2 hardened M1B authority failed raw replay"
        ) from error
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableRootBoundaryV2InvariantViolation(
            "M2 portable bundle failed raw replay after M1B"
        ) from error
    if (
        bundle.bundle_id != upstream.bundle_id
        or bundle.occurrence_id != upstream.occurrence_id
    ):
        _fail("M2 portable bundle and M1B identities differ")
    role_records = {
        role: tuple(item for item in bundle.records if item.role == role)
        for role in ROLE_ORDER
    }
    if any(len(role_records[role]) != 1 for role in ROLE_ORDER):
        _fail("M2 requires exactly one occurrence and root-execution record")
    occurrence_record = role_records["OCCURRENCE_IDENTITY"][0]
    root_record = role_records["ROOT_EXECUTION"][0]
    occurrence = (
        upstream.typed_graph.m1a_result.typed_graph.m0_result.typed_graph
        .occurrence
    )
    replayed_occurrence = (
        identity.replay_v075_batch_native_occurrence_identity_v1(occurrence)
    )
    if (
        occurrence_record.semantic_artifact_id
        != replayed_occurrence.occurrence_id
        or occurrence_record.canonical_artifact_bytes
        != canonical_json_bytes(replayed_occurrence.to_document())
    ):
        _fail("M2 occurrence record differs from exact M0 occurrence")
    root_view = V075PortableRootExecutionProducerViewV2(
        root_record.canonical_artifact_bytes
    )
    bindings = tuple(
        _binding_from_record(role_records[role][0]) for role in ROLE_ORDER
    )
    typed_graph = V075PortableRootBoundaryTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        upstream.public_context_closure_id,
        bundle.occurrence_id,
        upstream,
        replayed_occurrence,
        root_view,
        bindings,
    )
    upstream_public_ids = frozenset(
        item.record_id
        for item in upstream.dependency_dag.nodes
        if item.semantically_resolved
    )
    private_verification_ids = frozenset(
        item.record_id
        for item in upstream.typed_graph.m1a_result.typed_graph.record_bindings
        if item.role == m1a.M1A_VERIFICATION_ROLE
    )
    if (
        len(private_verification_ids) != 1
        or upstream_public_ids & private_verification_ids
    ):
        _fail("M2 upstream authority set consumed private verification")
    nodes = _iterative_root_dependency_nodes(
        records=bundle.records,
        upstream_public_record_ids=upstream_public_ids,
        private_verification_record_ids=private_verification_ids,
    )
    dag = V075PortableRootDependencyDAGV2(
        _DAG_ISSUER,
        bundle.bundle_id,
        upstream._result_id,  # noqa: SLF001
        typed_graph._graph_id,
        tuple(sorted(upstream_public_ids)),
        tuple(sorted(private_verification_ids)),
        nodes,
    )
    attestations = _build_attestations(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dag=dag,
        bindings=bindings,
    )
    role_closures = _build_role_closures(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dependency_dag_id=dag._dag_id,
        records=bindings,
        attestations=attestations,
    )
    return V075PortableRootBoundaryReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        upstream.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )


def open_v075_production_from_portable_root_boundary_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableRootBoundaryProductionV2NotReady(
        "M2 closes only occurrence/root-execution public semantics; source "
        "authority, code provenance, remaining registry roles, held-out "
        "execution, and independent verification remain incomplete"
    )


__all__ = [
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INDEPENDENT_ROOT_EXECUTION_VERIFIER_PROVIDED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED",
    "MAX_OUTPUT_BYTES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRIVATE_REPLAY_PERFORMED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075PortableRootBoundaryProductionV2NotReady",
    "V075PortableRootBoundaryReplayV2",
    "V075PortableRootBoundaryTypedGraphV2",
    "V075PortableRootBoundaryV2InvariantViolation",
    "V075PortableRootDependencyDAGV2",
    "V075PortableRootDependencyNodeV2",
    "V075PortableRootExecutionProducerViewV2",
    "V075PortableRootRecordAttestationV2",
    "V075PortableRootResolverKindV2",
    "V075PortableRootRoleClosureStatusV2",
    "V075PortableRootRoleClosureV2",
    "open_v075_production_from_portable_root_boundary_v2",
    "replay_v075_portable_root_boundary_v2",
]
