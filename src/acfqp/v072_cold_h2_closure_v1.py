"""Generic cold H=2 closure authority for V0-072.

The authority consumes already-frozen row evidence.  It has no transition
sampler, hidden-law interface, kernel, planner, or audit dependency.  Public
graph semantics supply only canonical states and complete legal-action
catalogues.

The root catalogue is closed first.  Only active nonterminal successor states
present in the *discovery-frozen* root support are expanded at H=1.
Validation-novel descriptors remain local row evidence and never create a
child catalogue or row obligation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import copy
import hashlib
from typing import Any, Mapping, Protocol, runtime_checkable

from .phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from . import partial_support_confidence_v2 as confidence_v2
from . import transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_cold_h2_closure_v1"
HORIZON = 2
DISCOVERY_DRAWS_PER_ROW = 64
VALIDATION_DRAWS_PER_ROW = 2_048
NEW_CHILD_VALIDATION_DRAWS_PER_ROW = 8_192
DIRECT_ONLY_CONSUMER_ROUTES = ("DIRECT",)
ADAPTIVE_CONSUMER_ROUTES = ("DIRECT", "QUOTIENT")
DISCOVERY_EXPANSION_RULE = (
    "ROOT_DISCOVERY_FROZEN_ACTIVE_NONTERMINAL_SUCCESSORS_ONLY"
)
VALIDATION_NOVEL_RULE = (
    "VALIDATION_NOVEL_DESCRIPTORS_NEVER_EXPAND_COLD_CLOSURE"
)
SHARED_CHARGE_RULE = (
    "ONE_NATIVE_PHYSICAL_CLOSURE_CHARGE_PER_ARM_CONSUMER_PROFILE"
)


class V072ColdH2ClosureInvariantViolation(ValueError):
    """A cold closure identity, inventory, cap, or work claim is invalid."""


DOMAIN_TAGS = {
    "state": "acfqp:v072-cold-h2-public-state:v1",
    "action": "acfqp:v072-cold-h2-public-action:v1",
    "catalogue": "acfqp:v072-cold-h2-public-catalogue:v1",
    "descriptor": "acfqp:v072-cold-h2-outcome-descriptor:v1",
    "row_work": "acfqp:v072-cold-h2-row-work:v1",
    "row": "acfqp:v072-cold-h2-row-evidence:v1",
    "cap_evidence": "acfqp:v072-cold-h2-context-total-row-cap-evidence:v1",
    "cap_registry": "acfqp:v072-cold-h2-confirmatory-cap-registry:v1",
    "consumer_profile": "acfqp:v072-cold-h2-consumer-profile:v1",
    "counters": "acfqp:v072-cold-h2-native-counters:v1",
    "charge": "acfqp:v072-cold-h2-shared-logical-charge:v1",
    "bundle": "acfqp:v072-cold-h2-closure-bundle:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-072 cold H2 content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V072ColdH2ClosureInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ColdH2ClosureInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _canonical_object(
    value: Mapping[str, Any],
    field_name: str,
) -> tuple[bytes, dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise V072ColdH2ClosureInvariantViolation(
            f"{field_name} must be one mapping"
        )
    try:
        encoded = canonical_json_bytes(dict(value))
        decoded = loads_canonical_json(encoded)
    except (TypeError, ValueError) as error:
        raise V072ColdH2ClosureInvariantViolation(
            f"{field_name} is not canonical: {error}"
        ) from error
    if type(decoded) is not dict:
        raise V072ColdH2ClosureInvariantViolation(
            f"{field_name} must decode to one object"
        )
    return encoded, decoded


@dataclass(frozen=True, slots=True, init=False)
class ColdPublicStateV1:
    """Opaque canonical public state; no hidden dynamics are serialized."""

    semantic_state_id: str
    _document_bytes: bytes = field(repr=False)
    _document_object: dict[str, Any] = field(repr=False, compare=False)
    _state_record_id: str = field(init=False, repr=False)

    def __init__(
        self,
        semantic_state_id: str,
        document: Mapping[str, Any],
    ) -> None:
        _cid(semantic_state_id, "public semantic state")
        encoded, decoded = _canonical_object(document, "public state")
        object.__setattr__(self, "semantic_state_id", semantic_state_id)
        object.__setattr__(self, "_document_bytes", encoded)
        object.__setattr__(self, "_document_object", decoded)
        object.__setattr__(
            self,
            "_state_record_id",
            _content_id("state", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_public_state.v1",
            "schema_version": SCHEMA_VERSION,
            "semantic_state_id": self.semantic_state_id,
            "document": self._document_object,
        }

    @property
    def document(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._document_object)

    @property
    def state_record_id(self) -> str:
        return self._state_record_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_record_id": self.state_record_id}


@dataclass(frozen=True, slots=True, init=False)
class ColdPublicActionV1:
    semantic_action_id: str
    _document_bytes: bytes = field(repr=False)
    _document_object: dict[str, Any] = field(repr=False, compare=False)
    _action_record_id: str = field(init=False, repr=False)

    def __init__(
        self,
        semantic_action_id: str,
        document: Mapping[str, Any],
    ) -> None:
        _cid(semantic_action_id, "public semantic action")
        encoded, decoded = _canonical_object(document, "public action")
        object.__setattr__(self, "semantic_action_id", semantic_action_id)
        object.__setattr__(self, "_document_bytes", encoded)
        object.__setattr__(self, "_document_object", decoded)
        object.__setattr__(
            self,
            "_action_record_id",
            _content_id("action", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_public_action.v1",
            "schema_version": SCHEMA_VERSION,
            "semantic_action_id": self.semantic_action_id,
            "document": self._document_object,
        }

    @property
    def document(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._document_object)

    @property
    def action_record_id(self) -> str:
        return self._action_record_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "action_record_id": self.action_record_id}


@runtime_checkable
class ColdH2PublicGraphProtocolV1(Protocol):
    """Public-only semantics used by construction and independent replay."""

    @property
    def context_id(self) -> str: ...

    @property
    def horizon(self) -> int: ...

    def root_state_v1(self) -> ColdPublicStateV1: ...

    def canonical_state_v1(
        self,
        state: ColdPublicStateV1,
    ) -> ColdPublicStateV1: ...

    def legal_actions_v1(
        self,
        state: ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[ColdPublicActionV1, ...]: ...


@runtime_checkable
class ColdH2RowEvidenceProtocolV1(Protocol):
    """Adapter boundary for an already-verified row-evidence authority."""

    @property
    def context_id(self) -> str: ...

    @property
    def state(self) -> ColdPublicStateV1: ...

    @property
    def remaining_horizon(self) -> int: ...

    @property
    def action(self) -> ColdPublicActionV1: ...

    @property
    def discovery_support(
        self,
    ) -> tuple["ColdOutcomeDescriptorV1", ...]: ...

    @property
    def validation_novel(
        self,
    ) -> tuple["ColdOutcomeDescriptorV1", ...]: ...

    @property
    def support_epoch_id(self) -> str: ...

    @property
    def confidence_snapshot_id(self) -> str: ...

    @property
    def row_replay_verification_id(self) -> str: ...

    @property
    def physical_evidence_id(self) -> str: ...

    @property
    def native_work(self) -> "ColdRowNativeWorkV1": ...

    @property
    def discovery_frozen(self) -> bool: ...

    @property
    def validation_novel_separate(self) -> bool: ...

    @property
    def route_independent_physical_evidence(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ColdPublicCatalogueV1:
    context_id: str
    state: ColdPublicStateV1
    remaining_horizon: int
    actions: tuple[ColdPublicActionV1, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "catalogue context")
        if (
            type(self.state) is not ColdPublicStateV1
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.actions) is not tuple
            or not self.actions
            or any(
                type(item) is not ColdPublicActionV1
                for item in self.actions
            )
            or tuple(item.action_record_id for item in self.actions)
            != tuple(
                sorted({item.action_record_id for item in self.actions})
            )
            or len(
                {item.semantic_action_id for item in self.actions}
            )
            != len(self.actions)
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "public legal-action catalogue is not canonical and complete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_public_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_record_id": self.state.state_record_id,
            "remaining_horizon": self.remaining_horizon,
            "action_record_ids": [
                item.action_record_id for item in self.actions
            ],
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "state": self.state.to_document(),
            "actions": [item.to_document() for item in self.actions],
            "catalogue_id": self.catalogue_id,
        }


@dataclass(frozen=True, slots=True, init=False)
class ColdOutcomeDescriptorV1:
    """Discovery or validation semantic outcome descriptor."""

    semantic_descriptor_id: str
    failure: bool
    terminal: bool
    successor_state: ColdPublicStateV1 | None
    _document_bytes: bytes = field(repr=False)
    _document_object: dict[str, Any] = field(repr=False, compare=False)
    _descriptor_record_id: str = field(init=False, repr=False)

    def __init__(
        self,
        semantic_descriptor_id: str,
        *,
        failure: bool,
        terminal: bool,
        successor_state: ColdPublicStateV1 | None,
        document: Mapping[str, Any],
    ) -> None:
        _cid(semantic_descriptor_id, "semantic outcome descriptor")
        if (
            type(failure) is not bool
            or type(terminal) is not bool
            or (failure and not terminal)
            or (
                not failure
                and not terminal
                and type(successor_state) is not ColdPublicStateV1
            )
            or (
                (failure or terminal)
                and successor_state is not None
            )
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "outcome descriptor state/terminal semantics are malformed"
            )
        encoded, decoded = _canonical_object(
            document,
            "outcome descriptor",
        )
        object.__setattr__(
            self,
            "semantic_descriptor_id",
            semantic_descriptor_id,
        )
        object.__setattr__(self, "failure", failure)
        object.__setattr__(self, "terminal", terminal)
        object.__setattr__(self, "successor_state", successor_state)
        object.__setattr__(self, "_document_bytes", encoded)
        object.__setattr__(self, "_document_object", decoded)
        object.__setattr__(
            self,
            "_descriptor_record_id",
            _content_id("descriptor", self._payload()),
        )

    @property
    def active_nonterminal(self) -> bool:
        return not self.failure and not self.terminal

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_outcome_descriptor.v1",
            "schema_version": SCHEMA_VERSION,
            "semantic_descriptor_id": self.semantic_descriptor_id,
            "failure": self.failure,
            "terminal": self.terminal,
            "successor_state_record_id": (
                None
                if self.successor_state is None
                else self.successor_state.state_record_id
            ),
            "document": self._document_object,
        }

    @property
    def document(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._document_object)

    @property
    def descriptor_record_id(self) -> str:
        return self._descriptor_record_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "successor_state": (
                None
                if self.successor_state is None
                else self.successor_state.to_document()
            ),
            "descriptor_record_id": self.descriptor_record_id,
        }


class ColdRowAcquisitionPurposeV1(str, Enum):
    COLD_INITIAL = "COLD_INITIAL"
    INCREMENTAL_PROMOTION = "INCREMENTAL_PROMOTION"
    INCREMENTAL_NEW_CHILD = "INCREMENTAL_NEW_CHILD"
    MATCHED_DIRECT_CHECKPOINT = "MATCHED_DIRECT_CHECKPOINT"


@dataclass(frozen=True, slots=True)
class ColdRowNativeWorkV1:
    acquisition_purpose: ColdRowAcquisitionPurposeV1 = (
        ColdRowAcquisitionPurposeV1.COLD_INITIAL
    )
    discovery_draws: int = DISCOVERY_DRAWS_PER_ROW
    validation_draws: int = VALIDATION_DRAWS_PER_ROW
    discovery_random_word_calls: int = DISCOVERY_DRAWS_PER_ROW
    validation_random_word_calls: int = VALIDATION_DRAWS_PER_ROW
    discovery_rejections: int = 0
    validation_rejections: int = 0
    planner_calls: int = 0
    audit_calls: int = 0
    kernel_calls: int = 0
    hidden_law_queries: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.acquisition_purpose)
            is not ColdRowAcquisitionPurposeV1
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.discovery_draws,
                    self.validation_draws,
                    self.discovery_random_word_calls,
                    self.validation_random_word_calls,
                    self.discovery_rejections,
                    self.validation_rejections,
                    self.planner_calls,
                    self.audit_calls,
                    self.kernel_calls,
                    self.hidden_law_queries,
                )
            )
            or (
                self.acquisition_purpose
                is ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
                and (
                    self.discovery_draws != DISCOVERY_DRAWS_PER_ROW
                    or self.validation_draws
                    not in prereg.DIRECT_VALIDATION_CHECKPOINTS
                )
            )
            or (
                self.acquisition_purpose
                is not ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
                and (
                    self.discovery_draws,
                    self.validation_draws,
                )
                != {
                    ColdRowAcquisitionPurposeV1.COLD_INITIAL: (
                        DISCOVERY_DRAWS_PER_ROW,
                        VALIDATION_DRAWS_PER_ROW,
                    ),
                    ColdRowAcquisitionPurposeV1.INCREMENTAL_PROMOTION: (
                        0,
                        VALIDATION_DRAWS_PER_ROW,
                    ),
                    ColdRowAcquisitionPurposeV1.INCREMENTAL_NEW_CHILD: (
                        DISCOVERY_DRAWS_PER_ROW,
                        NEW_CHILD_VALIDATION_DRAWS_PER_ROW,
                    ),
                }[self.acquisition_purpose]
            )
            or self.discovery_random_word_calls
            != self.discovery_draws + self.discovery_rejections
            or self.validation_random_word_calls
            != self.validation_draws + self.validation_rejections
            or any(
                value != 0
                for value in (
                    self.planner_calls,
                    self.audit_calls,
                    self.kernel_calls,
                    self.hidden_law_queries,
                )
            )
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold row native work differs from its frozen purpose"
            )

    @property
    def total_draws(self) -> int:
        return self.discovery_draws + self.validation_draws

    @property
    def total_random_word_calls(self) -> int:
        return (
            self.discovery_random_word_calls
            + self.validation_random_word_calls
        )

    @property
    def total_rejections(self) -> int:
        return self.discovery_rejections + self.validation_rejections

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_row_native_work.v1",
            "schema_version": SCHEMA_VERSION,
            "acquisition_purpose": self.acquisition_purpose.value,
            "discovery_draws": self.discovery_draws,
            "validation_draws": self.validation_draws,
            "total_draws": self.total_draws,
            "discovery_random_word_calls": (
                self.discovery_random_word_calls
            ),
            "validation_random_word_calls": (
                self.validation_random_word_calls
            ),
            "total_random_word_calls": self.total_random_word_calls,
            "discovery_rejections": self.discovery_rejections,
            "validation_rejections": self.validation_rejections,
            "total_rejections": self.total_rejections,
            "planner_calls": 0,
            "audit_calls": 0,
            "kernel_calls": 0,
            "hidden_law_queries": 0,
        }

    @property
    def work_id(self) -> str:
        return _content_id("row_work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class ColdRowEvidenceV1:
    """Verified semantic row summary consumed by the closure authority."""

    context_id: str
    state: ColdPublicStateV1
    remaining_horizon: int
    action: ColdPublicActionV1
    discovery_support: tuple[ColdOutcomeDescriptorV1, ...]
    validation_novel: tuple[ColdOutcomeDescriptorV1, ...]
    support_epoch_id: str
    confidence_snapshot_id: str
    row_replay_verification_id: str
    physical_evidence_id: str
    native_work: ColdRowNativeWorkV1
    discovery_frozen: bool = True
    validation_novel_separate: bool = True
    route_independent_physical_evidence: bool = True

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "row context"),
            (self.support_epoch_id, "row support epoch"),
            (self.confidence_snapshot_id, "row confidence snapshot"),
            (
                self.row_replay_verification_id,
                "row replay verification",
            ),
            (self.physical_evidence_id, "row physical evidence"),
        ):
            _cid(value, field_name)
        if (
            type(self.state) is not ColdPublicStateV1
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.action) is not ColdPublicActionV1
            or type(self.discovery_support) is not tuple
            or not self.discovery_support
            or type(self.validation_novel) is not tuple
            or any(
                type(item) is not ColdOutcomeDescriptorV1
                for item in (
                    *self.discovery_support,
                    *self.validation_novel,
                )
            )
            or tuple(
                item.descriptor_record_id
                for item in self.discovery_support
            )
            != tuple(
                sorted(
                    {
                        item.descriptor_record_id
                        for item in self.discovery_support
                    }
                )
            )
            or tuple(
                item.descriptor_record_id
                for item in self.validation_novel
            )
            != tuple(
                sorted(
                    {
                        item.descriptor_record_id
                        for item in self.validation_novel
                    }
                )
            )
            or {
                item.semantic_descriptor_id
                for item in self.discovery_support
            }
            & {
                item.semantic_descriptor_id
                for item in self.validation_novel
            }
            or type(self.native_work) is not ColdRowNativeWorkV1
            or self.discovery_frozen is not True
            or self.validation_novel_separate is not True
            or self.route_independent_physical_evidence is not True
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold row evidence is not split, canonical, and immutable"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_row_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_record_id": self.state.state_record_id,
            "remaining_horizon": self.remaining_horizon,
            "action_record_id": self.action.action_record_id,
            "discovery_support_descriptor_ids": [
                item.descriptor_record_id
                for item in self.discovery_support
            ],
            "validation_novel_descriptor_ids": [
                item.descriptor_record_id
                for item in self.validation_novel
            ],
            "support_epoch_id": self.support_epoch_id,
            "confidence_snapshot_id": self.confidence_snapshot_id,
            "row_replay_verification_id": (
                self.row_replay_verification_id
            ),
            "physical_evidence_id": self.physical_evidence_id,
            "native_work_id": self.native_work.work_id,
            "discovery_frozen": True,
            "validation_novel_separate": True,
            "route_independent_physical_evidence": True,
        }

    @property
    def row_evidence_id(self) -> str:
        return _content_id("row", self._payload())

    @property
    def semantic_key(self) -> tuple[str, int, str]:
        return (
            self.state.semantic_state_id,
            self.remaining_horizon,
            self.action.semantic_action_id,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "state": self.state.to_document(),
            "action": self.action.to_document(),
            "discovery_support": [
                item.to_document() for item in self.discovery_support
            ],
            "validation_novel": [
                item.to_document() for item in self.validation_novel
            ],
            "native_work": self.native_work.to_document(),
            "row_evidence_id": self.row_evidence_id,
        }


def bind_cold_row_evidence_protocol_v1(
    value: ColdH2RowEvidenceProtocolV1,
) -> ColdRowEvidenceV1:
    """Snapshot a generic verified row protocol into the closure domain."""

    if not isinstance(value, ColdH2RowEvidenceProtocolV1):
        raise V072ColdH2ClosureInvariantViolation(
            "row adapter does not implement the cold evidence protocol"
        )
    if type(value) is ColdRowEvidenceV1:
        return value
    return ColdRowEvidenceV1(
        value.context_id,
        value.state,
        value.remaining_horizon,
        value.action,
        value.discovery_support,
        value.validation_novel,
        value.support_epoch_id,
        value.confidence_snapshot_id,
        value.row_replay_verification_id,
        value.physical_evidence_id,
        value.native_work,
        value.discovery_frozen,
        value.validation_novel_separate,
        value.route_independent_physical_evidence,
    )


class ColdH2CapEvidenceClassV1(str, Enum):
    CONFIRMATORY_REGISTERED = "CONFIRMATORY_REGISTERED"
    DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY = (
        "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY"
    )


def _registered_contexts_by_id(
) -> dict[str, prereg.HeldoutPublicGraphContextV2]:
    return {
        item.context_id: item
        for item in prereg.registered_heldout_public_contexts_v2()
    }


PUBLIC_TOTAL_ROW_CAP_KEY_DOMAIN = (
    "acfqp:v072-heldout-public-context-total-row-cap-key:v1"
)
PUBLIC_TOTAL_ROW_CAP_BINDING_DOMAIN = (
    "acfqp:v072-heldout-public-total-row-cap-binding:v1"
)


def _external_public_content_id(
    domain_tag: str,
    payload: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        domain_tag.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _public_total_row_cap_key(
    context_id: str,
    context_key: str,
) -> str:
    return _external_public_content_id(
        PUBLIC_TOTAL_ROW_CAP_KEY_DOMAIN,
        {
            "schema": (
                "acfqp.v072_heldout_public_context_total_row_cap_key.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "confirmatory_family_generation": (
                prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "context_id": context_id,
            "context_key": context_key,
            "cap_semantics": (
                "COMPLETE_COLD_H2_TOTAL_PHYSICAL_STATE_ACTION_ROWS"
            ),
        },
    )


def _public_total_row_cap_binding_id(
    context_id: str,
    context_key: str,
    total_physical_row_cap: int,
) -> str:
    key = _public_total_row_cap_key(context_id, context_key)
    return _external_public_content_id(
        PUBLIC_TOTAL_ROW_CAP_BINDING_DOMAIN,
        {
            "schema": (
                "acfqp.v072_heldout_public_total_row_cap_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "context_key": context_key,
            "total_physical_row_cap": total_physical_row_cap,
            "confirmatory_family_generation": (
                prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "authority_class": "CONFIRMATORY_REGISTERED_PUBLIC_ONLY",
            "context_specific_total_row_cap_key": key,
            "preregistration_binding": {
                "kind": "NOT_FINALIZED_PUBLIC_ONLY",
                "final_preregistration_id": None,
            },
            "target_execution_allowed": False,
        },
    )


@runtime_checkable
class ColdH2TotalRowCapBindingProtocolV1(Protocol):
    """Public adapter boundary; contains no hidden law or kernel handle."""

    @property
    def context_id(self) -> str: ...

    @property
    def context_key(self) -> str: ...

    @property
    def total_physical_row_cap(self) -> int: ...

    @property
    def confirmatory_family_generation(self) -> str: ...

    @property
    def authority_class(self) -> str: ...

    @property
    def context_specific_total_row_cap_key(self) -> str: ...

    @property
    def total_row_cap_binding_id(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ColdH2ContextTotalRowCapEvidenceV1:
    """One context-bound *total* root-plus-child physical-row cap."""

    context_id: str
    context_key: str
    total_physical_row_cap: int
    evidence_class: ColdH2CapEvidenceClassV1
    confirmatory_family_generation: str | None
    source_total_row_cap_binding_id: str | None
    context_specific_total_row_cap_key: str | None
    development_scope_id: str | None

    def __post_init__(self) -> None:
        _cid(self.context_id, "cap-evidence context")
        if (
            type(self.context_key) is not str
            or not self.context_key
            or type(self.total_physical_row_cap) is not int
            or self.total_physical_row_cap <= 0
            or type(self.evidence_class) is not ColdH2CapEvidenceClassV1
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold H2 total-row cap evidence is malformed"
            )
        registered_by_id = _registered_contexts_by_id()
        registered_by_key = {
            item.context_key: item for item in registered_by_id.values()
        }
        if (
            self.evidence_class
            is ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
        ):
            expected = registered_by_id.get(self.context_id)
            if (
                expected is None
                or expected.context_key != self.context_key
                or expected.maximum_physical_rows_per_confidence_epoch
                != self.total_physical_row_cap
                or self.confirmatory_family_generation
                != prereg.CONFIRMATORY_FAMILY_GENERATION
                or self.source_total_row_cap_binding_id is None
                or _cid(
                    self.source_total_row_cap_binding_id,
                    "public total-row cap binding",
                )
                != self.source_total_row_cap_binding_id
                or self.context_specific_total_row_cap_key is None
                or _cid(
                    self.context_specific_total_row_cap_key,
                    "context-specific total-row cap key",
                )
                != self.context_specific_total_row_cap_key
                or self.context_specific_total_row_cap_key
                != _public_total_row_cap_key(
                    self.context_id,
                    self.context_key,
                )
                or self.source_total_row_cap_binding_id
                != _public_total_row_cap_binding_id(
                    self.context_id,
                    self.context_key,
                    self.total_physical_row_cap,
                )
                or self.development_scope_id is not None
            ):
                raise V072ColdH2ClosureInvariantViolation(
                    "confirmatory total-row cap is not the exact registered "
                    "context/key/cap binding"
                )
        else:
            if (
                self.context_id in registered_by_id
                or self.context_key in registered_by_key
                or self.confirmatory_family_generation is not None
                or self.source_total_row_cap_binding_id is not None
                or self.context_specific_total_row_cap_key is not None
                or self.development_scope_id is None
                or _cid(
                    self.development_scope_id,
                    "synthetic cap development scope",
                )
                != self.development_scope_id
            ):
                raise V072ColdH2ClosureInvariantViolation(
                    "synthetic cap evidence cannot impersonate a registered "
                    "confirmatory context"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_h2_context_total_row_cap_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "context_key": self.context_key,
            "total_physical_row_cap": self.total_physical_row_cap,
            "evidence_class": self.evidence_class.value,
            "confirmatory_family_generation": (
                self.confirmatory_family_generation
            ),
            "source_total_row_cap_binding_id": (
                self.source_total_row_cap_binding_id
            ),
            "context_specific_total_row_cap_key": (
                self.context_specific_total_row_cap_key
            ),
            "development_scope_id": self.development_scope_id,
            "preregistration_binding": {
                "kind": "NOT_FINALIZED",
                "reason": (
                    "PUBLIC_ONLY_CAP_AUTHORITY_PRECEDES_FINAL_ANCHORED_"
                    "CONFIRMATORY_PREREGISTRATION"
                ),
            },
            "cap_semantics": (
                "TOTAL_ROOT_PLUS_DISCOVERY_CHILD_ACTION_ROWS_PER_CONTEXT"
            ),
            "root_subcap_claimed": False,
            "child_state_subcap_claimed": False,
            "child_row_subcap_claimed": False,
        }

    @property
    def cap_evidence_id(self) -> str:
        return _content_id("cap_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cap_evidence_id": self.cap_evidence_id}


def bind_cold_h2_total_row_cap_protocol_v1(
    value: ColdH2TotalRowCapBindingProtocolV1,
) -> ColdH2ContextTotalRowCapEvidenceV1:
    if not isinstance(value, ColdH2TotalRowCapBindingProtocolV1):
        raise V072ColdH2ClosureInvariantViolation(
            "public total-row cap adapter does not implement the protocol"
        )
    if value.authority_class != "CONFIRMATORY_REGISTERED_PUBLIC_ONLY":
        raise V072ColdH2ClosureInvariantViolation(
            "public cap adapter is not a confirmatory registered authority"
        )
    evidence = ColdH2ContextTotalRowCapEvidenceV1(
        value.context_id,
        value.context_key,
        value.total_physical_row_cap,
        ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED,
        value.confirmatory_family_generation,
        value.total_row_cap_binding_id,
        value.context_specific_total_row_cap_key,
        None,
    )
    return evidence


@dataclass(frozen=True, slots=True)
class ColdH2ConfirmatoryCapRegistryV1:
    """Exact 96/48/96 context registry and confidence-cap reconciliation."""

    confirmatory_family_generation: str
    context_cap_evidence: tuple[ColdH2ContextTotalRowCapEvidenceV1, ...]
    total_physical_row_cap_sum: int
    maximum_confidence_epochs_per_physical_row: int
    maximum_promotions_per_physical_row: int
    maximum_promotion_authorities_per_context: int
    row_epoch_authority_cap_rule: str
    maximum_row_epoch_authorities_per_arm: int
    confidence_authority_row_epoch_cap_per_arm: int
    maximum_initial_accepted_draw_cap_per_arm: int

    def __post_init__(self) -> None:
        contexts = prereg.registered_heldout_public_contexts_v2()
        expected_evidence = tuple(
            ColdH2ContextTotalRowCapEvidenceV1(
                item.context_id,
                item.context_key,
                item.maximum_physical_rows_per_confidence_epoch,
                ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED,
                prereg.CONFIRMATORY_FAMILY_GENERATION,
                _public_total_row_cap_binding_id(
                    item.context_id,
                    item.context_key,
                    item.maximum_physical_rows_per_confidence_epoch,
                ),
                _public_total_row_cap_key(
                    item.context_id,
                    item.context_key,
                ),
                None,
            )
            for item in contexts
        )
        expected_sum = sum(
            item.maximum_physical_rows_per_confidence_epoch
            for item in contexts
        )
        expected_row_epochs = 2 * expected_sum
        if (
            self.confirmatory_family_generation
            != prereg.CONFIRMATORY_FAMILY_GENERATION
            or self.context_cap_evidence != expected_evidence
            or tuple(
                item.total_physical_row_cap
                for item in self.context_cap_evidence
            )
            != (96, 48, 96)
            or self.total_physical_row_cap_sum != expected_sum
            or self.maximum_confidence_epochs_per_physical_row
            != prereg.MAX_EPOCHS
            or self.maximum_promotions_per_physical_row
            != prereg.MAX_PROMOTIONS_PER_PHYSICAL_ROW
            or self.maximum_promotion_authorities_per_context
            != prereg.MAX_PROMOTION_AUTHORITIES_PER_CONTEXT
            or self.row_epoch_authority_cap_rule
            != prereg.ROW_EPOCH_AUTHORITY_CAP_RULE
            or self.maximum_row_epoch_authorities_per_arm
            != expected_row_epochs
            or self.maximum_row_epoch_authorities_per_arm
            != prereg.MAX_ROW_EPOCH_AUTHORITIES_PER_ARM
            or self.confidence_authority_row_epoch_cap_per_arm
            != confidence_v2.MAX_ARM_ROW_EPOCH_AUTHORITIES
            or self.confidence_authority_row_epoch_cap_per_arm
            != self.maximum_row_epoch_authorities_per_arm
            or self.maximum_initial_accepted_draw_cap_per_arm
            != expected_sum
            * (DISCOVERY_DRAWS_PER_ROW + VALIDATION_DRAWS_PER_ROW)
            or self.maximum_initial_accepted_draw_cap_per_arm
            != prereg.MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "confirmatory total-row cap registry or confidence bound "
                "changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_confirmatory_cap_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "confirmatory_family_generation": (
                self.confirmatory_family_generation
            ),
            "preregistration_binding": {
                "kind": "NOT_FINALIZED",
                "reason": (
                    "PUBLIC_ONLY_CAP_REGISTRY_PRECEDES_FINAL_ANCHORED_"
                    "CONFIRMATORY_PREREGISTRATION"
                ),
            },
            "context_cap_evidence_ids": [
                item.cap_evidence_id for item in self.context_cap_evidence
            ],
            "context_total_physical_row_caps": [
                {
                    "context_id": item.context_id,
                    "context_key": item.context_key,
                    "total_physical_row_cap": item.total_physical_row_cap,
                }
                for item in self.context_cap_evidence
            ],
            "total_physical_row_cap_sum": (
                self.total_physical_row_cap_sum
            ),
            "maximum_confidence_epochs_per_physical_row": (
                self.maximum_confidence_epochs_per_physical_row
            ),
            "maximum_promotions_per_physical_row": (
                self.maximum_promotions_per_physical_row
            ),
            "maximum_promotion_authorities_per_context": (
                self.maximum_promotion_authorities_per_context
            ),
            "row_epoch_authority_cap_rule": (
                self.row_epoch_authority_cap_rule
            ),
            "maximum_row_epoch_authorities_per_arm": (
                self.maximum_row_epoch_authorities_per_arm
            ),
            "confidence_authority_row_epoch_cap_per_arm": (
                self.confidence_authority_row_epoch_cap_per_arm
            ),
            "maximum_initial_accepted_draw_cap_per_arm": (
                self.maximum_initial_accepted_draw_cap_per_arm
            ),
        }

    @property
    def cap_registry_id(self) -> str:
        return _content_id("cap_registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context_cap_evidence": [
                item.to_document() for item in self.context_cap_evidence
            ],
            "cap_registry_id": self.cap_registry_id,
        }

    def evidence_for_context(
        self,
        context_id: str,
    ) -> ColdH2ContextTotalRowCapEvidenceV1:
        _cid(context_id, "registered cap lookup context")
        matches = tuple(
            item
            for item in self.context_cap_evidence
            if item.context_id == context_id
        )
        if len(matches) != 1:
            raise V072ColdH2ClosureInvariantViolation(
                "context is absent from the confirmatory total-row registry"
            )
        return matches[0]


def registered_confirmatory_cold_h2_cap_registry_v1(
) -> ColdH2ConfirmatoryCapRegistryV1:
    evidence = tuple(
        ColdH2ContextTotalRowCapEvidenceV1(
            item.context_id,
            item.context_key,
            item.maximum_physical_rows_per_confidence_epoch,
            ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED,
            prereg.CONFIRMATORY_FAMILY_GENERATION,
            _public_total_row_cap_binding_id(
                item.context_id,
                item.context_key,
                item.maximum_physical_rows_per_confidence_epoch,
            ),
            _public_total_row_cap_key(
                item.context_id,
                item.context_key,
            ),
            None,
        )
        for item in prereg.registered_heldout_public_contexts_v2()
    )
    total_cap = sum(item.total_physical_row_cap for item in evidence)
    return ColdH2ConfirmatoryCapRegistryV1(
        prereg.CONFIRMATORY_FAMILY_GENERATION,
        evidence,
        total_cap,
        prereg.MAX_EPOCHS,
        prereg.MAX_PROMOTIONS_PER_PHYSICAL_ROW,
        prereg.MAX_PROMOTION_AUTHORITIES_PER_CONTEXT,
        prereg.ROW_EPOCH_AUTHORITY_CAP_RULE,
        2 * total_cap,
        confidence_v2.MAX_ARM_ROW_EPOCH_AUTHORITIES,
        total_cap
        * (DISCOVERY_DRAWS_PER_ROW + VALIDATION_DRAWS_PER_ROW),
    )


def development_synthetic_cold_h2_cap_evidence_v1(
    *,
    context_id: str,
    context_key: str,
    total_physical_row_cap: int,
    development_scope_id: str,
) -> ColdH2ContextTotalRowCapEvidenceV1:
    return ColdH2ContextTotalRowCapEvidenceV1(
        context_id,
        context_key,
        total_physical_row_cap,
        ColdH2CapEvidenceClassV1.DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY,
        None,
        None,
        None,
        development_scope_id,
    )


def verify_total_physical_row_cap_v1(
    cap_evidence: ColdH2ContextTotalRowCapEvidenceV1,
    total_action_row_count: int,
) -> None:
    if (
        type(cap_evidence) is not ColdH2ContextTotalRowCapEvidenceV1
        or type(total_action_row_count) is not int
        or total_action_row_count < 0
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "total-row cap check requires exact typed evidence and count"
        )
    if total_action_row_count > cap_evidence.total_physical_row_cap:
        raise V072ColdH2ClosureInvariantViolation(
            "complete root-plus-discovery-child row inventory exceeds "
            f"context total cap {cap_evidence.total_physical_row_cap}"
        )


@dataclass(frozen=True, slots=True)
class ColdH2ClosureNativeCountersV1:
    cap_evidence_id: str
    context_total_physical_row_cap: int
    root_catalogue_count: int
    child_catalogue_count: int
    root_action_row_count: int
    child_action_row_count: int
    total_action_row_count: int
    cold_initial_row_count: int
    incremental_promotion_row_count: int
    incremental_new_child_row_count: int
    matched_direct_checkpoint_row_count: int
    discovery_active_descriptor_count: int
    discovery_child_state_count: int
    discovery_support_descriptor_count: int
    validation_novel_descriptor_count: int
    discovery_draws: int
    validation_draws: int
    total_draws: int
    discovery_random_word_calls: int
    validation_random_word_calls: int
    total_random_word_calls: int
    discovery_rejections: int
    validation_rejections: int
    total_rejections: int
    public_root_state_queries: int
    public_canonical_state_queries: int
    public_legal_catalogue_queries: int
    row_evidence_reads: int
    validation_novel_child_expansions: int = 0
    planner_calls: int = 0
    audit_calls: int = 0
    kernel_calls: int = 0
    hidden_law_queries: int = 0
    cap_checked_after_complete_derivation: int = 1
    native_physical_charge_count: int = 1

    def __post_init__(self) -> None:
        _cid(self.cap_evidence_id, "counter cap evidence")
        values = tuple(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "cap_evidence_id"
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.context_total_physical_row_cap <= 0
            or self.total_action_row_count
            > self.context_total_physical_row_cap
            or self.root_catalogue_count != 1
            or self.total_action_row_count
            != self.root_action_row_count + self.child_action_row_count
            or self.total_action_row_count
            != (
                self.cold_initial_row_count
                + self.incremental_promotion_row_count
                + self.incremental_new_child_row_count
                + self.matched_direct_checkpoint_row_count
            )
            or self.discovery_child_state_count
            != self.child_catalogue_count
            or (
                self.matched_direct_checkpoint_row_count == 0
                and (
                    self.discovery_draws
                    != DISCOVERY_DRAWS_PER_ROW * (
                        self.cold_initial_row_count
                        + self.incremental_new_child_row_count
                    )
                    or self.validation_draws
                    != (
                        VALIDATION_DRAWS_PER_ROW * (
                            self.cold_initial_row_count
                            + self.incremental_promotion_row_count
                        )
                        + NEW_CHILD_VALIDATION_DRAWS_PER_ROW
                        * self.incremental_new_child_row_count
                    )
                )
            )
            or (
                self.matched_direct_checkpoint_row_count > 0
                and (
                    self.matched_direct_checkpoint_row_count
                    != self.total_action_row_count
                    or any(
                        value != 0
                        for value in (
                            self.cold_initial_row_count,
                            self.incremental_promotion_row_count,
                            self.incremental_new_child_row_count,
                        )
                    )
                    or self.discovery_draws
                    != DISCOVERY_DRAWS_PER_ROW
                    * self.matched_direct_checkpoint_row_count
                    or self.validation_draws
                    not in {
                        checkpoint
                        * self.matched_direct_checkpoint_row_count
                        for checkpoint
                        in prereg.DIRECT_VALIDATION_CHECKPOINTS
                    }
                )
            )
            or self.total_draws
            != self.discovery_draws + self.validation_draws
            or self.discovery_random_word_calls
            != self.discovery_draws + self.discovery_rejections
            or self.validation_random_word_calls
            != self.validation_draws + self.validation_rejections
            or self.total_random_word_calls
            != (
                self.discovery_random_word_calls
                + self.validation_random_word_calls
            )
            or self.total_rejections
            != self.discovery_rejections + self.validation_rejections
            or self.public_root_state_queries != 1
            or self.public_canonical_state_queries
            != 1 + self.discovery_active_descriptor_count
            or self.public_legal_catalogue_queries
            != 1 + self.discovery_child_state_count
            or self.row_evidence_reads != self.total_action_row_count
            or self.validation_novel_child_expansions != 0
            or any(
                value != 0
                for value in (
                    self.planner_calls,
                    self.audit_calls,
                    self.kernel_calls,
                    self.hidden_law_queries,
                )
            )
            or self.cap_checked_after_complete_derivation != 1
            or self.native_physical_charge_count != 1
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold H2 closure native counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_closure_native_counters.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


class ColdH2ClosureConsumerRouteV1(str, Enum):
    DIRECT = "DIRECT"
    QUOTIENT = "QUOTIENT"


def _consumer_routes_for_arm(arm: str) -> tuple[str, ...]:
    if arm not in prereg.ARM_ORDER:
        raise V072ColdH2ClosureInvariantViolation(
            "cold H2 consumer arm is not preregistered"
        )
    if arm == "MATCHED_DIRECT_GROUND":
        return DIRECT_ONLY_CONSUMER_ROUTES
    return ADAPTIVE_CONSUMER_ROUTES


@dataclass(frozen=True, slots=True)
class ColdH2ConsumerProfileV1:
    arm: str
    consumer_routes: tuple[str, ...]
    native_physical_charge_count: int = 1

    def __post_init__(self) -> None:
        expected_routes = _consumer_routes_for_arm(self.arm)
        if (
            self.consumer_routes != expected_routes
            or self.native_physical_charge_count != 1
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold H2 arm/consumer route profile was transplanted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_consumer_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "arm": self.arm,
            "consumer_routes": list(self.consumer_routes),
            "ground_model_built": True,
            "quotient_model_built": (
                self.consumer_routes == ADAPTIVE_CONSUMER_ROUTES
            ),
            "native_physical_charge_count": 1,
        }

    @property
    def consumer_profile_id(self) -> str:
        return _content_id("consumer_profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "consumer_profile_id": self.consumer_profile_id,
        }


def cold_h2_consumer_profile_for_arm_v1(
    arm: str,
) -> ColdH2ConsumerProfileV1:
    return ColdH2ConsumerProfileV1(
        arm,
        _consumer_routes_for_arm(arm),
    )


@dataclass(frozen=True, slots=True)
class ColdH2SharedLogicalChargeV1:
    logical_occurrence_id: str
    physical_bundle_id: str
    physical_evidence_ids: tuple[str, ...]
    counters_id: str
    cap_evidence_id: str
    arm: str
    consumer_profile_id: str
    consumer_routes: tuple[str, ...]
    native_physical_charge_count: int = 1

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.logical_occurrence_id, "logical occurrence"),
            (self.physical_bundle_id, "physical closure bundle"),
            (self.counters_id, "charged closure counters"),
            (self.cap_evidence_id, "charged context total-row cap"),
            (self.consumer_profile_id, "charged arm consumer profile"),
        ):
            _cid(value, field_name)
        expected_profile = cold_h2_consumer_profile_for_arm_v1(self.arm)
        if (
            type(self.physical_evidence_ids) is not tuple
            or self.physical_evidence_ids
            != tuple(sorted(set(self.physical_evidence_ids)))
            or not self.physical_evidence_ids
            or any(
                _cid(item, "charged physical evidence") != item
                for item in self.physical_evidence_ids
            )
            or self.consumer_routes != expected_profile.consumer_routes
            or self.consumer_profile_id
            != expected_profile.consumer_profile_id
            or self.native_physical_charge_count != 1
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold H2 closure arm/route charge is stale or duplicated"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_shared_logical_charge.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "physical_bundle_id": self.physical_bundle_id,
            "physical_evidence_ids": list(self.physical_evidence_ids),
            "counters_id": self.counters_id,
            "cap_evidence_id": self.cap_evidence_id,
            "arm": self.arm,
            "consumer_profile_id": self.consumer_profile_id,
            "consumer_routes": list(self.consumer_routes),
            "native_physical_charge_count": 1,
            "shared_charge_rule": SHARED_CHARGE_RULE,
        }

    @property
    def charge_id(self) -> str:
        return _content_id("charge", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "charge_id": self.charge_id}


def _sorted_actions(
    actions: Any,
) -> tuple[ColdPublicActionV1, ...]:
    if (
        type(actions) is not tuple
        or not actions
        or any(type(item) is not ColdPublicActionV1 for item in actions)
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "public semantics returned a malformed legal-action inventory"
        )
    result = tuple(sorted(actions, key=lambda item: item.action_record_id))
    if (
        len({item.action_record_id for item in result}) != len(result)
        or len({item.semantic_action_id for item in result}) != len(result)
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "public legal-action inventory is duplicated"
        )
    return result


def _catalogue_from_public_semantics(
    public_graph: ColdH2PublicGraphProtocolV1,
    state: ColdPublicStateV1,
    remaining_horizon: int,
) -> ColdPublicCatalogueV1:
    actions = _sorted_actions(
        public_graph.legal_actions_v1(state, remaining_horizon)
    )
    return ColdPublicCatalogueV1(
        public_graph.context_id,
        state,
        remaining_horizon,
        actions,
    )


def _canonical_public_state(
    public_graph: ColdH2PublicGraphProtocolV1,
    state: ColdPublicStateV1,
) -> ColdPublicStateV1:
    if type(state) is not ColdPublicStateV1:
        raise V072ColdH2ClosureInvariantViolation(
            "public graph returned a noncanonical state type"
        )
    canonical = public_graph.canonical_state_v1(state)
    if (
        type(canonical) is not ColdPublicStateV1
        or canonical != state
        or canonical.state_record_id != state.state_record_id
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "public state is not its deterministic canonical form"
        )
    return state


def _discovery_child_states(
    public_graph: ColdH2PublicGraphProtocolV1,
    root_rows: tuple[ColdRowEvidenceV1, ...],
) -> tuple[
    tuple[ColdPublicStateV1, ...],
    int,
]:
    by_semantic_id: dict[str, ColdPublicStateV1] = {}
    active_descriptor_count = 0
    for row in root_rows:
        for descriptor in row.discovery_support:
            if not descriptor.active_nonterminal:
                continue
            active_descriptor_count += 1
            assert descriptor.successor_state is not None
            state = _canonical_public_state(
                public_graph,
                descriptor.successor_state,
            )
            previous = by_semantic_id.setdefault(
                state.semantic_state_id,
                state,
            )
            if previous != state:
                raise V072ColdH2ClosureInvariantViolation(
                    "one public child identity has conflicting state documents"
                )
    states = tuple(
        sorted(
            by_semantic_id.values(),
            key=lambda item: item.state_record_id,
        )
    )
    return states, active_descriptor_count


def _aggregate_native_counters(
    *,
    root_rows: tuple[ColdRowEvidenceV1, ...],
    child_catalogues: tuple[ColdPublicCatalogueV1, ...],
    child_rows: tuple[ColdRowEvidenceV1, ...],
    active_descriptor_count: int,
    cap_evidence: ColdH2ContextTotalRowCapEvidenceV1,
) -> ColdH2ClosureNativeCountersV1:
    rows = (*root_rows, *child_rows)
    return ColdH2ClosureNativeCountersV1(
        cap_evidence_id=cap_evidence.cap_evidence_id,
        context_total_physical_row_cap=(
            cap_evidence.total_physical_row_cap
        ),
        root_catalogue_count=1,
        child_catalogue_count=len(child_catalogues),
        root_action_row_count=len(root_rows),
        child_action_row_count=len(child_rows),
        total_action_row_count=len(rows),
        cold_initial_row_count=sum(
            row.native_work.acquisition_purpose
            is ColdRowAcquisitionPurposeV1.COLD_INITIAL
            for row in rows
        ),
        incremental_promotion_row_count=sum(
            row.native_work.acquisition_purpose
            is ColdRowAcquisitionPurposeV1.INCREMENTAL_PROMOTION
            for row in rows
        ),
        incremental_new_child_row_count=sum(
            row.native_work.acquisition_purpose
            is ColdRowAcquisitionPurposeV1.INCREMENTAL_NEW_CHILD
            for row in rows
        ),
        matched_direct_checkpoint_row_count=sum(
            row.native_work.acquisition_purpose
            is ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
            for row in rows
        ),
        discovery_active_descriptor_count=active_descriptor_count,
        discovery_child_state_count=len(child_catalogues),
        discovery_support_descriptor_count=sum(
            len(row.discovery_support) for row in rows
        ),
        validation_novel_descriptor_count=sum(
            len(row.validation_novel) for row in rows
        ),
        discovery_draws=sum(
            row.native_work.discovery_draws for row in rows
        ),
        validation_draws=sum(
            row.native_work.validation_draws for row in rows
        ),
        total_draws=sum(row.native_work.total_draws for row in rows),
        discovery_random_word_calls=sum(
            row.native_work.discovery_random_word_calls for row in rows
        ),
        validation_random_word_calls=sum(
            row.native_work.validation_random_word_calls for row in rows
        ),
        total_random_word_calls=sum(
            row.native_work.total_random_word_calls for row in rows
        ),
        discovery_rejections=sum(
            row.native_work.discovery_rejections for row in rows
        ),
        validation_rejections=sum(
            row.native_work.validation_rejections for row in rows
        ),
        total_rejections=sum(
            row.native_work.total_rejections for row in rows
        ),
        public_root_state_queries=1,
        public_canonical_state_queries=1 + active_descriptor_count,
        public_legal_catalogue_queries=1 + len(child_catalogues),
        row_evidence_reads=len(rows),
    )


def _bundle_core_payload(
    *,
    context_id: str,
    arm: str,
    consumer_profile_id: str,
    root_state: ColdPublicStateV1,
    root_catalogue: ColdPublicCatalogueV1,
    child_states: tuple[ColdPublicStateV1, ...],
    child_catalogues: tuple[ColdPublicCatalogueV1, ...],
    root_rows: tuple[ColdRowEvidenceV1, ...],
    child_rows: tuple[ColdRowEvidenceV1, ...],
    cap_evidence_id: str,
    cap_evidence_class: str,
    confirmatory_cap_registry_id: str | None,
    counters_id: str,
) -> dict[str, Any]:
    physical_evidence_ids = tuple(
        sorted(
            row.physical_evidence_id
            for row in (*root_rows, *child_rows)
        )
    )
    return {
        "schema": "acfqp.v072_cold_h2_closure_bundle.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "context_id": context_id,
        "arm": arm,
        "consumer_profile_id": consumer_profile_id,
        "horizon": HORIZON,
        "root_state_record_id": root_state.state_record_id,
        "root_catalogue_id": root_catalogue.catalogue_id,
        "child_state_record_ids": [
            item.state_record_id for item in child_states
        ],
        "child_catalogue_ids": [
            item.catalogue_id for item in child_catalogues
        ],
        "root_row_evidence_ids": [
            item.row_evidence_id for item in root_rows
        ],
        "child_row_evidence_ids": [
            item.row_evidence_id for item in child_rows
        ],
        "physical_evidence_ids": list(physical_evidence_ids),
        "cap_evidence_id": cap_evidence_id,
        "cap_evidence_class": cap_evidence_class,
        "confirmatory_cap_registry_id": confirmatory_cap_registry_id,
        "counters_id": counters_id,
        "discovery_expansion_rule": DISCOVERY_EXPANSION_RULE,
        "validation_novel_rule": VALIDATION_NOVEL_RULE,
        "validation_novel_child_expansion_allowed": False,
        "observation_only": True,
        "planner_calls": 0,
        "audit_calls": 0,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "route_independent_physical_evidence": True,
    }


@dataclass(frozen=True, slots=True)
class V072ColdH2ClosureBundleV1:
    context_id: str
    arm: str
    consumer_profile: ColdH2ConsumerProfileV1
    root_state: ColdPublicStateV1
    root_catalogue: ColdPublicCatalogueV1
    child_states: tuple[ColdPublicStateV1, ...]
    child_catalogues: tuple[ColdPublicCatalogueV1, ...]
    root_rows: tuple[ColdRowEvidenceV1, ...]
    child_rows: tuple[ColdRowEvidenceV1, ...]
    cap_evidence: ColdH2ContextTotalRowCapEvidenceV1
    confirmatory_cap_registry_id: str | None
    counters: ColdH2ClosureNativeCountersV1
    shared_charge: ColdH2SharedLogicalChargeV1
    observation_only: bool = True
    validation_novel_child_expansion_allowed: bool = False
    route_independent_physical_evidence: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "closure context")
        if (
            type(self.root_state) is not ColdPublicStateV1
            or type(self.arm) is not str
            or type(self.consumer_profile) is not ColdH2ConsumerProfileV1
            or self.consumer_profile.arm != self.arm
            or type(self.root_catalogue) is not ColdPublicCatalogueV1
            or self.root_catalogue.context_id != self.context_id
            or self.root_catalogue.state != self.root_state
            or self.root_catalogue.remaining_horizon != HORIZON
            or type(self.child_states) is not tuple
            or type(self.child_catalogues) is not tuple
            or type(self.root_rows) is not tuple
            or type(self.child_rows) is not tuple
            or type(self.cap_evidence)
            is not ColdH2ContextTotalRowCapEvidenceV1
            or self.cap_evidence.context_id != self.context_id
            or type(self.counters) is not ColdH2ClosureNativeCountersV1
            or type(self.shared_charge) is not ColdH2SharedLogicalChargeV1
            or self.observation_only is not True
            or self.validation_novel_child_expansion_allowed is not False
            or self.route_independent_physical_evidence is not True
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold H2 closure has a malformed concrete schema"
            )
        registry = registered_confirmatory_cold_h2_cap_registry_v1()
        if (
            self.cap_evidence.evidence_class
            is ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
        ):
            if (
                self.confirmatory_cap_registry_id
                != registry.cap_registry_id
                or registry.evidence_for_context(self.context_id)
                != self.cap_evidence
            ):
                raise V072ColdH2ClosureInvariantViolation(
                    "confirmatory closure cap evidence is not registry-bound"
                )
        elif self.confirmatory_cap_registry_id is not None:
            raise V072ColdH2ClosureInvariantViolation(
                "synthetic closure cannot claim the confirmatory cap registry"
            )
        if (
            tuple(item.state_record_id for item in self.child_states)
            != tuple(
                sorted(
                    {item.state_record_id for item in self.child_states}
                )
            )
            or tuple(item.catalogue_id for item in self.child_catalogues)
            != tuple(
                sorted(
                    {
                        item.catalogue_id
                        for item in self.child_catalogues
                    }
                )
            )
            or tuple(item.row_evidence_id for item in self.root_rows)
            != tuple(
                sorted({item.row_evidence_id for item in self.root_rows})
            )
            or tuple(item.row_evidence_id for item in self.child_rows)
            != tuple(
                sorted({item.row_evidence_id for item in self.child_rows})
            )
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold H2 closure registries are not content-ID canonical"
            )
        state_by_semantic_id: dict[str, ColdPublicStateV1] = {}
        for row in self.root_rows:
            for descriptor in row.discovery_support:
                if descriptor.active_nonterminal:
                    assert descriptor.successor_state is not None
                    prior = state_by_semantic_id.setdefault(
                        descriptor.successor_state.semantic_state_id,
                        descriptor.successor_state,
                    )
                    if prior != descriptor.successor_state:
                        raise V072ColdH2ClosureInvariantViolation(
                            "discovery support has conflicting child states"
                        )
        expected_states = tuple(
            sorted(
                state_by_semantic_id.values(),
                key=lambda item: item.state_record_id,
            )
        )
        if expected_states != self.child_states:
            raise V072ColdH2ClosureInvariantViolation(
                "child states differ from root discovery-frozen support"
            )
        child_state_by_semantic_id = {
            item.semantic_state_id: item for item in self.child_states
        }
        if (
            {
                item.state.semantic_state_id
                for item in self.child_catalogues
            }
            != {
                item.semantic_state_id for item in self.child_states
            }
            or any(
                item.state
                != child_state_by_semantic_id[
                    item.state.semantic_state_id
                ]
                for item in self.child_catalogues
            )
            or any(
                item.context_id != self.context_id
                or item.remaining_horizon != 1
                for item in self.child_catalogues
            )
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "child catalogue registry is stale or incomplete"
            )
        expected_root_keys = {
            (
                self.root_state.semantic_state_id,
                HORIZON,
                action.semantic_action_id,
            )
            for action in self.root_catalogue.actions
        }
        expected_child_keys = {
            (
                catalogue.state.semantic_state_id,
                1,
                action.semantic_action_id,
            )
            for catalogue in self.child_catalogues
            for action in catalogue.actions
        }
        root_action_by_semantic_id = {
            item.semantic_action_id: item
            for item in self.root_catalogue.actions
        }
        child_binding_by_key = {
            (
                catalogue.state.semantic_state_id,
                action.semantic_action_id,
            ): (catalogue.state, action)
            for catalogue in self.child_catalogues
            for action in catalogue.actions
        }
        if (
            {row.semantic_key for row in self.root_rows}
            != expected_root_keys
            or len(self.root_rows) != len(expected_root_keys)
            or any(
                row.state != self.root_state
                or row.action
                != root_action_by_semantic_id[
                    row.action.semantic_action_id
                ]
                for row in self.root_rows
            )
            or {row.semantic_key for row in self.child_rows}
            != expected_child_keys
            or len(self.child_rows) != len(expected_child_keys)
            or any(
                (row.state, row.action)
                != child_binding_by_key[
                    (
                        row.state.semantic_state_id,
                        row.action.semantic_action_id,
                    )
                ]
                for row in self.child_rows
            )
            or any(
                row.context_id != self.context_id
                for row in (*self.root_rows, *self.child_rows)
            )
            or len(
                {
                    row.physical_evidence_id
                    for row in (*self.root_rows, *self.child_rows)
                }
            )
            != len(self.root_rows) + len(self.child_rows)
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "cold closure omits, duplicates, or transplants a row"
            )
        verify_total_physical_row_cap_v1(
            self.cap_evidence,
            len(self.root_rows) + len(self.child_rows),
        )
        active_count = sum(
            descriptor.active_nonterminal
            for row in self.root_rows
            for descriptor in row.discovery_support
        )
        expected_counters = _aggregate_native_counters(
            root_rows=self.root_rows,
            child_catalogues=self.child_catalogues,
            child_rows=self.child_rows,
            active_descriptor_count=active_count,
            cap_evidence=self.cap_evidence,
        )
        matched_direct_rows = tuple(
            row
            for row in (*self.root_rows, *self.child_rows)
            if row.native_work.acquisition_purpose
            is ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
        )
        if matched_direct_rows and (
            self.arm != "MATCHED_DIRECT_GROUND"
            or len(matched_direct_rows)
            != len(self.root_rows) + len(self.child_rows)
            or len(
                {
                    row.native_work.validation_draws
                    for row in matched_direct_rows
                }
            )
            != 1
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "matched-direct closure rows are not one synchronized "
                "complete checkpoint"
            )
        if self.counters != expected_counters:
            raise V072ColdH2ClosureInvariantViolation(
                "closure counters differ from native row work"
            )
        physical_evidence_ids = tuple(
            sorted(
                row.physical_evidence_id
                for row in (*self.root_rows, *self.child_rows)
            )
        )
        if (
            self.shared_charge.physical_bundle_id
            != self.physical_bundle_id
            or self.shared_charge.physical_evidence_ids
            != physical_evidence_ids
            or self.shared_charge.counters_id != self.counters.counters_id
            or self.shared_charge.cap_evidence_id
            != self.cap_evidence.cap_evidence_id
            or self.shared_charge.arm != self.arm
            or self.shared_charge.consumer_profile_id
            != self.consumer_profile.consumer_profile_id
            or self.shared_charge.consumer_routes
            != self.consumer_profile.consumer_routes
            or self.shared_charge.native_physical_charge_count != 1
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "closure shared logical charge is stale or duplicated"
            )

    def _core_payload(self) -> dict[str, Any]:
        return _bundle_core_payload(
            context_id=self.context_id,
            arm=self.arm,
            consumer_profile_id=self.consumer_profile.consumer_profile_id,
            root_state=self.root_state,
            root_catalogue=self.root_catalogue,
            child_states=self.child_states,
            child_catalogues=self.child_catalogues,
            root_rows=self.root_rows,
            child_rows=self.child_rows,
            cap_evidence_id=self.cap_evidence.cap_evidence_id,
            cap_evidence_class=self.cap_evidence.evidence_class.value,
            confirmatory_cap_registry_id=(
                self.confirmatory_cap_registry_id
            ),
            counters_id=self.counters.counters_id,
        )

    @property
    def physical_bundle_id(self) -> str:
        return _content_id("bundle", self._core_payload())

    @property
    def closure_id(self) -> str:
        return self.physical_bundle_id

    @property
    def all_rows(self) -> tuple[ColdRowEvidenceV1, ...]:
        return (*self.root_rows, *self.child_rows)

    def to_document(self) -> dict[str, Any]:
        return {
            **self._core_payload(),
            "consumer_profile": self.consumer_profile.to_document(),
            "root_state": self.root_state.to_document(),
            "root_catalogue": self.root_catalogue.to_document(),
            "child_states": [
                item.to_document() for item in self.child_states
            ],
            "child_catalogues": [
                item.to_document() for item in self.child_catalogues
            ],
            "root_rows": [item.to_document() for item in self.root_rows],
            "child_rows": [item.to_document() for item in self.child_rows],
            "cap_evidence": self.cap_evidence.to_document(),
            "counters": self.counters.to_document(),
            "shared_charge": self.shared_charge.to_document(),
            "shared_charge_id": self.shared_charge.charge_id,
            "closure_id": self.closure_id,
        }


def freeze_v072_cold_h2_closure_v1(
    *,
    public_graph: ColdH2PublicGraphProtocolV1,
    row_evidence: tuple[ColdH2RowEvidenceProtocolV1, ...],
    logical_occurrence_id: str,
    arm: str,
    cap_evidence: ColdH2ContextTotalRowCapEvidenceV1,
) -> V072ColdH2ClosureBundleV1:
    """Freeze one complete observation-only cold H=2 closure."""

    _cid(logical_occurrence_id, "cold closure logical occurrence")
    if (
        not isinstance(public_graph, ColdH2PublicGraphProtocolV1)
        or public_graph.horizon != HORIZON
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "cold closure requires the generic public H=2 graph protocol"
        )
    context_id = _cid(public_graph.context_id, "public graph context")
    consumer_profile = cold_h2_consumer_profile_for_arm_v1(arm)
    if (
        type(cap_evidence) is not ColdH2ContextTotalRowCapEvidenceV1
        or cap_evidence.context_id != context_id
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "cold closure cap evidence was transplanted across contexts"
        )
    cap_registry = registered_confirmatory_cold_h2_cap_registry_v1()
    confirmatory_cap_registry_id = None
    if (
        cap_evidence.evidence_class
        is ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
    ):
        if (
            cap_registry.evidence_for_context(context_id)
            != cap_evidence
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "confirmatory closure cap is not the registered context cap"
            )
        confirmatory_cap_registry_id = cap_registry.cap_registry_id
    if (
        type(row_evidence) is not tuple
        or not row_evidence
        or any(
            not isinstance(item, ColdH2RowEvidenceProtocolV1)
            for item in row_evidence
        )
    ):
        raise V072ColdH2ClosureInvariantViolation(
            "cold closure row evidence must be one immutable typed inventory"
        )
    frozen_rows = tuple(
        bind_cold_row_evidence_protocol_v1(item)
        for item in row_evidence
    )
    row_by_key: dict[tuple[str, int, str], ColdRowEvidenceV1] = {}
    for row in frozen_rows:
        if row.context_id != context_id:
            raise V072ColdH2ClosureInvariantViolation(
                "cold row was transplanted across public contexts"
            )
        previous = row_by_key.setdefault(row.semantic_key, row)
        if previous is not row:
            raise V072ColdH2ClosureInvariantViolation(
                "cold row inventory duplicates one semantic state-action"
            )

    root_state = _canonical_public_state(
        public_graph,
        public_graph.root_state_v1(),
    )
    root_catalogue = _catalogue_from_public_semantics(
        public_graph,
        root_state,
        HORIZON,
    )
    root_rows: list[ColdRowEvidenceV1] = []
    for action in root_catalogue.actions:
        key = (
            root_state.semantic_state_id,
            HORIZON,
            action.semantic_action_id,
        )
        row = row_by_key.get(key)
        if (
            row is None
            or row.state != root_state
            or row.action != action
        ):
            raise V072ColdH2ClosureInvariantViolation(
                "complete root legal catalogue lacks one exact row"
            )
        root_rows.append(row)
    root_row_tuple = tuple(
        sorted(root_rows, key=lambda item: item.row_evidence_id)
    )
    child_states, active_descriptor_count = _discovery_child_states(
        public_graph,
        root_row_tuple,
    )
    child_catalogues = tuple(
        sorted(
            (
                _catalogue_from_public_semantics(
                    public_graph,
                    state,
                    1,
                )
                for state in child_states
            ),
            key=lambda item: item.catalogue_id,
        )
    )
    child_rows: list[ColdRowEvidenceV1] = []
    for catalogue in child_catalogues:
        for action in catalogue.actions:
            key = (
                catalogue.state.semantic_state_id,
                1,
                action.semantic_action_id,
            )
            row = row_by_key.get(key)
            if (
                row is None
                or row.state != catalogue.state
                or row.action != action
            ):
                raise V072ColdH2ClosureInvariantViolation(
                    "discovery-known child lacks one complete public H1 row"
                )
            child_rows.append(row)
    child_row_tuple = tuple(
        sorted(child_rows, key=lambda item: item.row_evidence_id)
    )
    expected_keys = {
        row.semantic_key for row in (*root_row_tuple, *child_row_tuple)
    }
    if set(row_by_key) != expected_keys:
        raise V072ColdH2ClosureInvariantViolation(
            "row inventory contains an extra/non-discovery child row"
        )
    verify_total_physical_row_cap_v1(
        cap_evidence,
        len(root_row_tuple) + len(child_row_tuple),
    )
    counters = _aggregate_native_counters(
        root_rows=root_row_tuple,
        child_catalogues=child_catalogues,
        child_rows=child_row_tuple,
        active_descriptor_count=active_descriptor_count,
        cap_evidence=cap_evidence,
    )
    core_payload = _bundle_core_payload(
        context_id=context_id,
        arm=arm,
        consumer_profile_id=consumer_profile.consumer_profile_id,
        root_state=root_state,
        root_catalogue=root_catalogue,
        child_states=child_states,
        child_catalogues=child_catalogues,
        root_rows=root_row_tuple,
        child_rows=child_row_tuple,
        cap_evidence_id=cap_evidence.cap_evidence_id,
        cap_evidence_class=cap_evidence.evidence_class.value,
        confirmatory_cap_registry_id=confirmatory_cap_registry_id,
        counters_id=counters.counters_id,
    )
    physical_bundle_id = _content_id("bundle", core_payload)
    charge = ColdH2SharedLogicalChargeV1(
        logical_occurrence_id,
        physical_bundle_id,
        tuple(
            sorted(
                row.physical_evidence_id
                for row in (*root_row_tuple, *child_row_tuple)
            )
        ),
        counters.counters_id,
        cap_evidence.cap_evidence_id,
        arm,
        consumer_profile.consumer_profile_id,
        consumer_profile.consumer_routes,
    )
    return V072ColdH2ClosureBundleV1(
        context_id,
        arm,
        consumer_profile,
        root_state,
        root_catalogue,
        child_states,
        child_catalogues,
        root_row_tuple,
        child_row_tuple,
        cap_evidence,
        confirmatory_cap_registry_id,
        counters,
        charge,
    )


__all__ = [
    "ADAPTIVE_CONSUMER_ROUTES",
    "DIRECT_ONLY_CONSUMER_ROUTES",
    "DISCOVERY_DRAWS_PER_ROW",
    "DISCOVERY_EXPANSION_RULE",
    "ColdH2CapEvidenceClassV1",
    "ColdH2ClosureConsumerRouteV1",
    "ColdH2ClosureNativeCountersV1",
    "ColdH2ConfirmatoryCapRegistryV1",
    "ColdH2ConsumerProfileV1",
    "ColdH2ContextTotalRowCapEvidenceV1",
    "ColdH2PublicGraphProtocolV1",
    "ColdH2RowEvidenceProtocolV1",
    "ColdH2SharedLogicalChargeV1",
    "ColdH2TotalRowCapBindingProtocolV1",
    "ColdOutcomeDescriptorV1",
    "ColdPublicActionV1",
    "ColdPublicCatalogueV1",
    "ColdPublicStateV1",
    "ColdRowEvidenceV1",
    "ColdRowAcquisitionPurposeV1",
    "ColdRowNativeWorkV1",
    "HORIZON",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SHARED_CHARGE_RULE",
    "V072ColdH2ClosureBundleV1",
    "V072ColdH2ClosureInvariantViolation",
    "VALIDATION_DRAWS_PER_ROW",
    "NEW_CHILD_VALIDATION_DRAWS_PER_ROW",
    "VALIDATION_NOVEL_RULE",
    "bind_cold_row_evidence_protocol_v1",
    "bind_cold_h2_total_row_cap_protocol_v1",
    "cold_h2_consumer_profile_for_arm_v1",
    "development_synthetic_cold_h2_cap_evidence_v1",
    "freeze_v072_cold_h2_closure_v1",
    "registered_confirmatory_cold_h2_cap_registry_v1",
    "verify_total_physical_row_cap_v1",
]
