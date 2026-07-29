"""Law-free, nonexecuting graph semantics candidate for production V0-075.

Every identity in this module is reconstructed from a strict typed object
graph.  Caller-supplied context, state, action, horizon, support, and stream
IDs are never accepted as authority.

Support evidence is arm-free.  One shared evidence lineage authorizes all
five arms at a row/epoch.  The raw-word pairing key is fixed by the target
namespace, row, and observer epoch rather than by selectable support members;
changing support evidence therefore cannot reroll the CRN tape.

All signatures remain registry-relative until an independent verifier binds
the registry and exact public-key bytes to tracked final-preregistration and
remote-main Git objects.  Nothing in this module opens observer authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.h2_graph_transition_engine_v1 import (
    H2GraphStateV1,
    derive_splitmix64_seed_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_public_campaign_authority_v1 as public_authority


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_public_graph_semantics_v1"
TARGET_OBSERVER_OPEN_AUTHORITY = False
MAX_SUPPORT_MEMBERS_PER_ROW = 16
MAX_OBSERVER_EPOCH_INDEX = 3

SEED_DOMAINS = {
    "DISCOVERY": "acfqp:v075-heldout-discovery-stream-seed:v2",
    "VALIDATION": "acfqp:v075-heldout-validation-stream-seed:v2",
}

DOMAIN_TAGS = {
    "state": "acfqp:v075-heldout-symbolic-graph-state:v2",
    "catalogue": "acfqp:v075-heldout-legal-action-catalogue:v2",
    "row": "acfqp:v075-heldout-observation-row-binding:v2",
    "support_evidence": "acfqp:v075-heldout-support-evidence:v2",
    "pairing_support_set": (
        "acfqp:v075-heldout-arm-free-pairing-support-set:v2"
    ),
    "pairing_lineage": (
        "acfqp:v075-heldout-arm-free-support-lineage:v2"
    ),
    "support_epoch": "acfqp:v075-heldout-shared-support-epoch:v2",
    "support_chain": "acfqp:v075-heldout-shared-support-chain:v2",
    "raw_pairing_key": "acfqp:v075-arm-free-raw-word-pairing-key:v2",
    "five_arm_pairing": "acfqp:v075-five-arm-pairing-authority:v2",
    "stream_pair": "acfqp:v075-arm-isolated-stream-pair:v2",
    "pairing_group": "acfqp:v075-arm-free-raw-word-pairing-group:v2",
    "stream": "acfqp:v075-arm-isolated-transition-stream:v2",
    "five_arm_stream_set": "acfqp:v075-five-arm-stream-set:v2",
}

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or len(SEED_DOMAINS) != len(set(SEED_DOMAINS.values()))
    or any(
        not value.startswith("acfqp:v075-")
        for value in (*DOMAIN_TAGS.values(), *SEED_DOMAINS.values())
    )
):
    raise RuntimeError("V0-075 public/seed domains must be unique and v075-only")


class V075PublicGraphSemanticsInvariantViolation(ValueError):
    """A public state/action/support/pairing identity invariant failed."""


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PublicGraphSemanticsInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PublicGraphSemanticsInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _registered_context(
    value: Any,
) -> public_authority.V075PublicReplicateContextV1:
    try:
        return public_authority.registered_public_context_v1(value)
    except (
        public_authority.V075PublicCampaignAuthorityInvariantViolation
    ) as error:
        raise V075PublicGraphSemanticsInvariantViolation(
            str(error)
        ) from error


def _canonical_action(
    value: Any,
    *,
    field: str = "action",
) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
        or value[0] >= value[1]
        or value[2] not in value[:2]
    ):
        raise V075PublicGraphSemanticsInvariantViolation(
            f"{field} must be one ordered edge and endpoint survivor"
        )
    return value


def _arm(value: Any) -> str:
    if (
        type(value) is not str
        or value not in public_authority.ARM_ORDER
    ):
        raise V075PublicGraphSemanticsInvariantViolation(
            "arm is outside the preregistered five-arm order"
        )
    return value


@dataclass(frozen=True, slots=True)
class V075SymbolicGraphStateV1:
    context: public_authority.V075PublicReplicateContextV1
    ranks: tuple[int, ...]
    failure: bool = False

    def __post_init__(self) -> None:
        registered = _registered_context(self.context)
        if (
            type(self.ranks) is not tuple
            or len(self.ranks) != registered.topology.vertex_count
            or any(
                type(rank) is not int
                or rank < 0
                or rank > registered.rank_cap
                for rank in self.ranks
            )
            or type(self.failure) is not bool
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "symbolic state is outside its V0-075 context"
            )
        actions = legal_action_triples_v1(
            registered,
            self.ranks,
            False,
        )
        if self.failure != (not actions):
            raise V075PublicGraphSemanticsInvariantViolation(
                "state failure flag disagrees with public legal actions"
            )

    @property
    def context_id(self) -> str:
        return self.context.context_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_symbolic_graph_state.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "ranks": list(self.ranks),
            "failure": self.failure,
        }

    @property
    def state_id(self) -> str:
        return _hash("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "state_id": self.state_id,
        }

    def to_kernel_state(self) -> H2GraphStateV1:
        return H2GraphStateV1(self.ranks, self.failure)


def legal_action_triples_v1(
    context: public_authority.V075PublicReplicateContextV1,
    ranks: tuple[int, ...],
    failure: bool,
) -> tuple[tuple[int, int, int], ...]:
    registered = _registered_context(context)
    if (
        type(ranks) is not tuple
        or len(ranks) != registered.topology.vertex_count
        or any(
            type(rank) is not int
            or rank < 0
            or rank > registered.rank_cap
            for rank in ranks
        )
        or type(failure) is not bool
    ):
        raise V075PublicGraphSemanticsInvariantViolation(
            "legal-action query is outside the replicate context"
        )
    if failure:
        return ()
    return tuple(
        sorted(
            (first, second, survivor)
            for first, second in registered.topology.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )


@dataclass(frozen=True, slots=True)
class V075LegalActionCatalogueV1:
    context: public_authority.V075PublicReplicateContextV1
    state: V075SymbolicGraphStateV1
    remaining_horizon: int
    actions: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        registered = _registered_context(self.context)
        if type(self.state) is not V075SymbolicGraphStateV1:
            raise V075PublicGraphSemanticsInvariantViolation(
                "legal-action catalogue state is not typed"
            )
        expected = legal_action_triples_v1(
            registered,
            self.state.ranks,
            self.state.failure,
        )
        if (
            self.state.context != registered
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, registered.horizon)
            or type(self.actions) is not tuple
            or self.actions != expected
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "legal-action catalogue is incomplete or transplanted"
            )

    @property
    def context_id(self) -> str:
        return self.context.context_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_legal_action_catalogue.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_id": self.state.state_id,
            "remaining_horizon": self.remaining_horizon,
            "actions": [list(action) for action in self.actions],
            "complete_public_catalogue": True,
        }

    @property
    def catalogue_id(self) -> str:
        return _hash("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "state": self.state.to_document(),
            "catalogue_id": self.catalogue_id,
        }


def root_catalogue_v1(
    context: public_authority.V075PublicReplicateContextV1,
) -> V075LegalActionCatalogueV1:
    registered = _registered_context(context)
    state = V075SymbolicGraphStateV1(
        registered,
        registered.root_ranks,
        False,
    )
    return V075LegalActionCatalogueV1(
        registered,
        state,
        registered.horizon,
        legal_action_triples_v1(
            registered,
            state.ranks,
            state.failure,
        ),
    )


@dataclass(frozen=True, slots=True)
class V075ObservationRowBindingV1:
    context: public_authority.V075PublicReplicateContextV1
    catalogue: V075LegalActionCatalogueV1
    action: tuple[int, int, int]

    def __post_init__(self) -> None:
        registered = _registered_context(self.context)
        canonical_action = _canonical_action(self.action)
        if (
            type(self.catalogue) is not V075LegalActionCatalogueV1
            or self.catalogue.context != registered
            or canonical_action not in self.catalogue.actions
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "row binding is outside the complete typed catalogue"
            )

    @property
    def context_id(self) -> str:
        return self.context.context_id

    @property
    def catalogue_id(self) -> str:
        return self.catalogue.catalogue_id

    @property
    def state_id(self) -> str:
        return self.catalogue.state.state_id

    @property
    def remaining_horizon(self) -> int:
        return self.catalogue.remaining_horizon

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_observation_row_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "ids_reconstructed_from_typed_graph": True,
        }

    @property
    def row_binding_id(self) -> str:
        return _hash("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "catalogue": self.catalogue.to_document(),
            "row_binding_id": self.row_binding_id,
        }


def observation_row_binding_v1(
    context: public_authority.V075PublicReplicateContextV1,
    catalogue: V075LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> V075ObservationRowBindingV1:
    return V075ObservationRowBindingV1(
        _registered_context(context),
        catalogue,
        _canonical_action(action),
    )


@dataclass(frozen=True, slots=True)
class V075SupportEvidenceV1:
    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    row_binding: V075ObservationRowBindingV1
    observed_state: V075SymbolicGraphStateV1
    source_observer_epoch_index: int
    accepted_draw_index: int
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or type(self.row_binding) is not V075ObservationRowBindingV1
            or type(self.observed_state) is not V075SymbolicGraphStateV1
            or self.observed_state.context != self.row_binding.context
            or type(self.source_observer_epoch_index) is not int
            or self.source_observer_epoch_index
            not in range(MAX_OBSERVER_EPOCH_INDEX)
            or type(self.accepted_draw_index) is not int
            or self.accepted_draw_index <= 0
            or self.row_binding.context
            not in self.namespace.family.replicate_contexts
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "support evidence is not a row-bound shared observer fact"
            )
        message = support_evidence_signing_bytes_v1(
            namespace=self.namespace,
            row_binding=self.row_binding,
            observed_state=self.observed_state,
            source_observer_epoch_index=(
                self.source_observer_epoch_index
            ),
            accepted_draw_index=self.accepted_draw_index,
        )
        if not (
            public_authority
            .verify_rsa_pkcs1_v1_5_sha256_signature_v1(
                public_key=(
                    self.namespace.signer_registry.observer_evidence_key
                ),
                message=message,
                signature_hex=self.observer_signature_hex,
            )
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "support evidence observer signature is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_support_evidence.v2",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "context_id": self.row_binding.context_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "observed_state_id": self.observed_state.state_id,
            "observer_signer_key_id": (
                self.namespace.signer_registry.observer_evidence_key.key_id
            ),
            "source_observer_epoch_index": (
                self.source_observer_epoch_index
            ),
            "accepted_draw_index": self.accepted_draw_index,
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "signature_scope": "REGISTRY_RELATIVE_PROVENANCE_ONLY",
            "independent_final_authority_verified": False,
            "production_observation_authorized": False,
            "arm_serialized": False,
            "typed_evidence_graph_complete": True,
        }

    @property
    def evidence_id(self) -> str:
        return _hash("support_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "namespace": self.namespace.to_document(),
            "row_binding": self.row_binding.to_document(),
            "observed_state": self.observed_state.to_document(),
            "evidence_id": self.evidence_id,
        }


def support_evidence_signing_bytes_v1(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: V075ObservationRowBindingV1,
    observed_state: V075SymbolicGraphStateV1,
    source_observer_epoch_index: int,
    accepted_draw_index: int,
) -> bytes:
    if (
        type(namespace)
        is not public_authority.V075PublicTargetTapeNamespaceV1
        or type(row_binding) is not V075ObservationRowBindingV1
        or type(observed_state) is not V075SymbolicGraphStateV1
        or observed_state.context != row_binding.context
        or row_binding.context not in namespace.family.replicate_contexts
        or type(source_observer_epoch_index) is not int
        or source_observer_epoch_index
        not in range(MAX_OBSERVER_EPOCH_INDEX)
        or type(accepted_draw_index) is not int
        or accepted_draw_index <= 0
    ):
        raise V075PublicGraphSemanticsInvariantViolation(
            "support-evidence signing graph is invalid"
        )
    return (
        b"acfqp:v075-heldout-support-evidence-signature:v2"
        + b"\x00"
        + canonical_json_bytes(
            {
                "schema": (
                    "acfqp.v075_heldout_support_evidence_signature.v2"
                ),
                "schema_version": SCHEMA_VERSION,
                "target_tape_namespace_id": (
                    namespace.target_tape_namespace_id
                ),
                "signer_registry_id": (
                    namespace.signer_registry.registry_id
                ),
                "observer_signer_key_id": (
                    namespace.signer_registry.observer_evidence_key.key_id
                ),
                "context_id": row_binding.context_id,
                "row_binding_id": row_binding.row_binding_id,
                "observed_state_id": observed_state.state_id,
                "source_observer_epoch_index": (
                    source_observer_epoch_index
                ),
                "accepted_draw_index": accepted_draw_index,
                "arm_serialized": False,
            }
        )
    )


def bind_support_evidence_v1(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: V075ObservationRowBindingV1,
    observed_state: V075SymbolicGraphStateV1,
    source_observer_epoch_index: int,
    accepted_draw_index: int,
    observer_signature_hex: str,
) -> V075SupportEvidenceV1:
    """Verify a registry-relative observer claim without opening production."""

    return V075SupportEvidenceV1(
        namespace,
        row_binding,
        observed_state,
        source_observer_epoch_index,
        accepted_draw_index,
        observer_signature_hex,
    )


class V075ObservationLaneV1(str, Enum):
    DISCOVERY = "DISCOVERY"
    VALIDATION = "VALIDATION"


@dataclass(frozen=True, slots=True)
class V075SharedSupportEpochV1:
    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    row_binding: V075ObservationRowBindingV1
    epoch_index: int
    evidence: tuple[V075SupportEvidenceV1, ...]
    parent: "V075SharedSupportEpochV1 | None" = None

    def __post_init__(self) -> None:
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or type(self.row_binding) is not V075ObservationRowBindingV1
            or self.row_binding.context
            not in self.namespace.family.replicate_contexts
            or type(self.epoch_index) is not int
            or self.epoch_index
            not in range(MAX_OBSERVER_EPOCH_INDEX + 1)
            or type(self.evidence) is not tuple
            or len(self.evidence) > MAX_SUPPORT_MEMBERS_PER_ROW
            or any(
                type(item) is not V075SupportEvidenceV1
                for item in self.evidence
            )
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "shared support epoch graph is malformed"
            )
        evidence_ids = tuple(item.evidence_id for item in self.evidence)
        if (
            evidence_ids != tuple(sorted(set(evidence_ids)))
            or any(
                item.namespace != self.namespace
                or item.row_binding != self.row_binding
                or item.source_observer_epoch_index >= self.epoch_index
                for item in self.evidence
            )
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "support evidence is duplicated, reordered, or transplanted"
            )
        if self.epoch_index == 0:
            if self.evidence or self.parent is not None:
                raise V075PublicGraphSemanticsInvariantViolation(
                    "bootstrap support epoch must be empty and parentless"
                )
        elif (
            not self.evidence
            or type(self.parent) is not V075SharedSupportEpochV1
            or self.parent.namespace != self.namespace
            or self.parent.row_binding != self.row_binding
            or self.parent.epoch_index != self.epoch_index - 1
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "promoted support epoch requires immediate typed parent"
            )

    @property
    def context_id(self) -> str:
        return self.row_binding.context_id

    @property
    def row_binding_id(self) -> str:
        return self.row_binding.row_binding_id

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.evidence)

    @property
    def required_lane(self) -> V075ObservationLaneV1:
        return (
            V075ObservationLaneV1.DISCOVERY
            if self.epoch_index == 0
            else V075ObservationLaneV1.VALIDATION
        )

    @property
    def pairing_support_set_id(self) -> str:
        return _hash(
            "pairing_support_set",
            {
                "schema": (
                    "acfqp.v075_heldout_arm_free_pairing_support_set.v2"
                ),
                "schema_version": SCHEMA_VERSION,
                "target_tape_namespace_id": (
                    self.namespace.target_tape_namespace_id
                ),
                "context_id": self.context_id,
                "row_binding_id": self.row_binding_id,
                "evidence_ids": list(self.evidence_ids),
                "arm_serialized": False,
            },
        )

    @property
    def pairing_lineage_id(self) -> str:
        return _hash(
            "pairing_lineage",
            {
                "schema": (
                    "acfqp.v075_heldout_arm_free_support_lineage.v2"
                ),
                "schema_version": SCHEMA_VERSION,
                "target_tape_namespace_id": (
                    self.namespace.target_tape_namespace_id
                ),
                "context_id": self.context_id,
                "row_binding_id": self.row_binding_id,
                "epoch_index": self.epoch_index,
                "pairing_support_set_id": self.pairing_support_set_id,
                "parent_pairing_lineage_id": (
                    None
                    if self.parent is None
                    else self.parent.pairing_lineage_id
                ),
                "arm_serialized": False,
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_shared_support_epoch.v2",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "epoch_index": self.epoch_index,
            "required_lane": self.required_lane.value,
            "evidence_ids": list(self.evidence_ids),
            "pairing_support_set_id": self.pairing_support_set_id,
            "pairing_lineage_id": self.pairing_lineage_id,
            "parent_epoch_id": (
                None if self.parent is None else self.parent.epoch_id
            ),
            "shared_by_arms": list(public_authority.ARM_ORDER),
        }

    @property
    def epoch_id(self) -> str:
        return _hash("support_epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "namespace": self.namespace.to_document(),
            "row_binding": self.row_binding.to_document(),
            "evidence": [item.to_document() for item in self.evidence],
            "epoch_id": self.epoch_id,
        }


def derive_shared_support_epoch_v1(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: V075ObservationRowBindingV1,
    epoch_index: int,
    evidence: Iterable[V075SupportEvidenceV1],
    parent: V075SharedSupportEpochV1 | None = None,
) -> V075SharedSupportEpochV1:
    try:
        canonical_evidence = tuple(
            sorted(tuple(evidence), key=lambda item: item.evidence_id)
        )
    except (AttributeError, TypeError) as error:
        raise V075PublicGraphSemanticsInvariantViolation(
            "support evidence must be one concrete typed sequence"
        ) from error
    if epoch_index == 0 and parent is not None:
        raise V075PublicGraphSemanticsInvariantViolation(
            "bootstrap support epoch rejects a non-null parent"
        )
    return V075SharedSupportEpochV1(
        namespace,
        row_binding,
        epoch_index,
        canonical_evidence,
        parent,
    )


@dataclass(frozen=True, slots=True)
class V075SharedSupportChainV1:
    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    row_binding: V075ObservationRowBindingV1
    epochs: tuple[V075SharedSupportEpochV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or type(self.row_binding) is not V075ObservationRowBindingV1
            or type(self.epochs) is not tuple
            or not self.epochs
            or len(self.epochs) > MAX_OBSERVER_EPOCH_INDEX + 1
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "shared support chain is empty or malformed"
            )
        for index, epoch in enumerate(self.epochs):
            if (
                type(epoch) is not V075SharedSupportEpochV1
                or epoch.namespace != self.namespace
                or epoch.row_binding != self.row_binding
                or epoch.epoch_index != index
                or (
                    index == 0
                    and epoch.parent is not None
                )
                or (
                    index > 0
                    and epoch.parent != self.epochs[index - 1]
                )
            ):
                raise V075PublicGraphSemanticsInvariantViolation(
                    "support chain is reordered, gapped, or transplanted"
                )

    @property
    def leaf(self) -> V075SharedSupportEpochV1:
        return self.epochs[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_heldout_shared_support_chain.v2",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "context_id": self.row_binding.context_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "epoch_ids": [item.epoch_id for item in self.epochs],
            "leaf_epoch_id": self.leaf.epoch_id,
            "leaf_pairing_lineage_id": self.leaf.pairing_lineage_id,
            "arm_serialized": False,
        }

    @property
    def chain_id(self) -> str:
        return _hash("support_chain", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "namespace": self.namespace.to_document(),
            "row_binding": self.row_binding.to_document(),
            "epochs": [item.to_document() for item in self.epochs],
            "chain_id": self.chain_id,
        }


def freeze_shared_support_chain_v1(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: V075ObservationRowBindingV1,
    epochs: tuple[V075SharedSupportEpochV1, ...],
) -> V075SharedSupportChainV1:
    return V075SharedSupportChainV1(
        namespace,
        row_binding,
        epochs,
    )


@dataclass(frozen=True, slots=True)
class V075FiveArmPairingAuthorityV1:
    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    row_binding: V075ObservationRowBindingV1
    support_chain: V075SharedSupportChainV1
    arms: tuple[str, ...] = public_authority.ARM_ORDER

    def __post_init__(self) -> None:
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or type(self.row_binding) is not V075ObservationRowBindingV1
            or type(self.support_chain) is not V075SharedSupportChainV1
            or self.support_chain.namespace != self.namespace
            or self.support_chain.row_binding != self.row_binding
            or self.arms != public_authority.ARM_ORDER
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "five-arm pairing authority is stale or arm-drifted"
            )

    @property
    def observer_epoch_index(self) -> int:
        return self.support_chain.leaf.epoch_index

    @property
    def lane(self) -> V075ObservationLaneV1:
        return self.support_chain.leaf.required_lane

    @property
    def raw_word_pairing_key_id(self) -> str:
        return _hash(
            "raw_pairing_key",
            {
                "schema": (
                    "acfqp.v075_arm_free_raw_word_pairing_key.v2"
                ),
                "schema_version": SCHEMA_VERSION,
                "target_tape_namespace_id": (
                    self.namespace.target_tape_namespace_id
                ),
                "context_id": self.row_binding.context_id,
                "row_binding_id": self.row_binding.row_binding_id,
                "observer_epoch_index": self.observer_epoch_index,
                "lane": self.lane.value,
                "support_evidence_affects_seed": False,
                "arm_serialized": False,
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_five_arm_pairing_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "context_id": self.row_binding.context_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "support_chain_id": self.support_chain.chain_id,
            "pairing_lineage_id": (
                self.support_chain.leaf.pairing_lineage_id
            ),
            "observer_epoch_index": self.observer_epoch_index,
            "lane": self.lane.value,
            "raw_word_pairing_key_id": self.raw_word_pairing_key_id,
            "arms": list(self.arms),
            "one_shared_lineage_for_all_arms": True,
        }

    @property
    def pairing_authority_id(self) -> str:
        return _hash("five_arm_pairing", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "namespace": self.namespace.to_document(),
            "row_binding": self.row_binding.to_document(),
            "support_chain": self.support_chain.to_document(),
            "pairing_authority_id": self.pairing_authority_id,
        }


def freeze_five_arm_pairing_authority_v1(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    row_binding: V075ObservationRowBindingV1,
    support_chain: V075SharedSupportChainV1,
) -> V075FiveArmPairingAuthorityV1:
    return V075FiveArmPairingAuthorityV1(
        namespace,
        row_binding,
        support_chain,
    )


@dataclass(frozen=True, slots=True)
class V075TransitionStreamIdentityV1:
    pairing_authority: V075FiveArmPairingAuthorityV1
    arm: str

    def __post_init__(self) -> None:
        if (
            type(self.pairing_authority)
            is not V075FiveArmPairingAuthorityV1
            or _arm(self.arm) not in self.pairing_authority.arms
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "stream requires one typed shared pairing authority"
            )

    @property
    def namespace(self) -> public_authority.V075PublicTargetTapeNamespaceV1:
        return self.pairing_authority.namespace

    @property
    def row_binding(self) -> V075ObservationRowBindingV1:
        return self.pairing_authority.row_binding

    @property
    def target_tape_namespace_id(self) -> str:
        return self.namespace.target_tape_namespace_id

    @property
    def context_id(self) -> str:
        return self.row_binding.context_id

    @property
    def row_binding_id(self) -> str:
        return self.row_binding.row_binding_id

    @property
    def catalogue_id(self) -> str:
        return self.row_binding.catalogue_id

    @property
    def support_epoch_id(self) -> str:
        return self.pairing_authority.support_chain.leaf.epoch_id

    @property
    def support_chain_id(self) -> str:
        return self.pairing_authority.support_chain.chain_id

    @property
    def pairing_lineage_id(self) -> str:
        return (
            self.pairing_authority.support_chain.leaf.pairing_lineage_id
        )

    @property
    def observer_epoch_index(self) -> int:
        return self.pairing_authority.observer_epoch_index

    @property
    def lane(self) -> V075ObservationLaneV1:
        return self.pairing_authority.lane

    @property
    def action(self) -> tuple[int, int, int]:
        return self.row_binding.action

    def _pairing_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_arm_free_raw_word_pairing_group.v2",
            "schema_version": SCHEMA_VERSION,
            "raw_word_pairing_key_id": (
                self.pairing_authority.raw_word_pairing_key_id
            ),
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "observer_epoch_index": self.observer_epoch_index,
            "lane": self.lane.value,
            "arm_serialized": False,
            "worker_metadata_serialized": False,
            "support_evidence_affects_seed": False,
        }

    @property
    def pairing_group_id(self) -> str:
        return _hash("pairing_group", self._pairing_payload())

    def _pair_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_arm_isolated_stream_pair.v2",
            "schema_version": SCHEMA_VERSION,
            "pairing_authority_id": (
                self.pairing_authority.pairing_authority_id
            ),
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "catalogue_id": self.catalogue_id,
            "support_epoch_id": self.support_epoch_id,
            "support_chain_id": self.support_chain_id,
            "pairing_lineage_id": self.pairing_lineage_id,
            "observer_epoch_index": self.observer_epoch_index,
            "lane": self.lane.value,
            "arm": self.arm,
            "action": list(self.action),
            "pairing_group_id": self.pairing_group_id,
        }

    @property
    def pair_id(self) -> str:
        return _hash("stream_pair", self._pair_payload())

    @property
    def stream_id(self) -> str:
        return _hash(
            "stream",
            {
                "schema": "acfqp.v075_arm_isolated_transition_stream.v2",
                "schema_version": SCHEMA_VERSION,
                "pair_id": self.pair_id,
                "arm": self.arm,
                "lane": self.lane.value,
            },
        )

    @property
    def seed(self) -> int:
        return derive_splitmix64_seed_v1(
            seed_domain=SEED_DOMAINS[self.lane.value],
            pairing_group_id=self.pairing_group_id,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._pair_payload(),
            "pairing_authority": self.pairing_authority.to_document(),
            "pair_id": self.pair_id,
            "stream_id": self.stream_id,
            "seed_serialized": False,
            "target_observer_open_authority": False,
        }


def derive_transition_stream_identity_v1(
    *,
    pairing_authority: V075FiveArmPairingAuthorityV1,
    arm: str,
) -> V075TransitionStreamIdentityV1:
    return V075TransitionStreamIdentityV1(
        pairing_authority,
        _arm(arm),
    )


@dataclass(frozen=True, slots=True)
class V075FiveArmStreamSetV1:
    pairing_authority: V075FiveArmPairingAuthorityV1
    streams: tuple[V075TransitionStreamIdentityV1, ...]

    def __post_init__(self) -> None:
        expected = tuple(
            V075TransitionStreamIdentityV1(
                self.pairing_authority,
                arm,
            )
            for arm in public_authority.ARM_ORDER
        )
        if (
            type(self.pairing_authority)
            is not V075FiveArmPairingAuthorityV1
            or type(self.streams) is not tuple
            or self.streams != expected
            or len({stream.pairing_group_id for stream in self.streams})
            != 1
            or len({stream.seed for stream in self.streams}) != 1
        ):
            raise V075PublicGraphSemanticsInvariantViolation(
                "five-arm stream set drifted from one shared CRN lineage"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_five_arm_stream_set.v2",
            "schema_version": SCHEMA_VERSION,
            "pairing_authority_id": (
                self.pairing_authority.pairing_authority_id
            ),
            "arms": list(public_authority.ARM_ORDER),
            "stream_ids": [stream.stream_id for stream in self.streams],
            "pairing_group_id": self.streams[0].pairing_group_id,
            "one_shared_lineage_for_all_arms": True,
        }

    @property
    def stream_set_id(self) -> str:
        return _hash("five_arm_stream_set", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "pairing_authority": self.pairing_authority.to_document(),
            "streams": [stream.to_document() for stream in self.streams],
            "stream_set_id": self.stream_set_id,
        }


def freeze_five_arm_stream_set_v1(
    pairing_authority: V075FiveArmPairingAuthorityV1,
) -> V075FiveArmStreamSetV1:
    if type(pairing_authority) is not V075FiveArmPairingAuthorityV1:
        raise V075PublicGraphSemanticsInvariantViolation(
            "stream set requires one typed five-arm pairing authority"
        )
    return V075FiveArmStreamSetV1(
        pairing_authority,
        tuple(
            derive_transition_stream_identity_v1(
                pairing_authority=pairing_authority,
                arm=arm,
            )
            for arm in public_authority.ARM_ORDER
        ),
    )


def public_h2_kernel_without_hidden_law_v1(
    context: public_authority.V075PublicReplicateContextV1,
) -> None:
    """Fail closed: the public dependency graph has no production law."""

    _registered_context(context)
    raise V075PublicGraphSemanticsInvariantViolation(
        "production law and target observer authority are absent; public "
        "semantics cannot construct an H2 graph kernel"
    )


__all__ = [
    "DOMAIN_TAGS",
    "MAX_OBSERVER_EPOCH_INDEX",
    "MAX_SUPPORT_MEMBERS_PER_ROW",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SEED_DOMAINS",
    "TARGET_OBSERVER_OPEN_AUTHORITY",
    "V075FiveArmPairingAuthorityV1",
    "V075FiveArmStreamSetV1",
    "V075LegalActionCatalogueV1",
    "V075ObservationLaneV1",
    "V075ObservationRowBindingV1",
    "V075PublicGraphSemanticsInvariantViolation",
    "V075SharedSupportChainV1",
    "V075SharedSupportEpochV1",
    "V075SupportEvidenceV1",
    "V075SymbolicGraphStateV1",
    "V075TransitionStreamIdentityV1",
    "bind_support_evidence_v1",
    "derive_shared_support_epoch_v1",
    "derive_transition_stream_identity_v1",
    "freeze_five_arm_pairing_authority_v1",
    "freeze_five_arm_stream_set_v1",
    "freeze_shared_support_chain_v1",
    "legal_action_triples_v1",
    "observation_row_binding_v1",
    "public_h2_kernel_without_hidden_law_v1",
    "root_catalogue_v1",
    "support_evidence_signing_bytes_v1",
]
