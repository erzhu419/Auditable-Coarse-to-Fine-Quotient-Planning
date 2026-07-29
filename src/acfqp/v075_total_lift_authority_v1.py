"""Law-free V0-075 partial-support total-lift authority.

The operational side of this module consumes only public graph objects,
observer-signed observation capabilities, and typed model/policy bindings.  It
has no transition-law constructor and no target observer access.

Exact transition atoms are accepted only by the disjoint
``V075IndependentExactReplayBoundaryV1`` surface.  Its production mint
requires the independently issued reveal-attested
``V075ObserverOpenAuthorizationV1`` and the exact private environment emitted
by the registered generator, replays the signed private observer journal
against the committed environment, reconstructs the full H=2 closure in
memory, and binds that closure to the selected model, policy, concretizer and
operational envelope.  A domain-separated construction mint exercises the
same path without opening a target.

The exact lift is total.  For every selected root realization:

* exact environment failures remain environment failures;
* an exact positive child inside the frozen row-specific modeled support must
  have its bound child decision, whose complete fixed concretizer is
  integrated; and
* every exact positive child outside that support enters one global absorbing
  policy-abort failure with continuation reward zero.

Protocol failures and statistical envelope misses are different typed
outcomes.  All metric arithmetic is exact :class:`fractions.Fraction`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.h2_graph_transition_engine_v1 import (
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphTransitionAtomV1,
    H2GraphTransitionInvariantViolation,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_private_observer_boundary_v1 as observer_boundary
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_partial_support_total_lift_authority_v1"
POLICY_ABORT_RULE = (
    "EXACT_POSITIVE_CHILD_OUTSIDE_FROZEN_MODELED_SUPPORT_IS_"
    "ABSORBING_POLICY_ABORT_FAILURE"
)
POLICY_ABORT_BEHAVIOR = "ABSORBING_POLICY_ABORT_FAILURE"
INDEPENDENT_EXACT_REPLAY_LANE = "STANDALONE_EVALUATION_ONLY"
PRODUCTION_EXACT_REPLAY_MINT_IMPLEMENTED = True
PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED = False

DOMAIN_TAGS = {
    "occurrence": "acfqp:v075-total-lift-law-free-occurrence:v1",
    "observed_row": "acfqp:v075-total-lift-observed-row-binding:v1",
    "semantic_action": "acfqp:v075-total-lift-semantic-action:v1",
    "concretizer": "acfqp:v075-total-lift-fixed-concretizer:v1",
    "root_support": "acfqp:v075-total-lift-selected-root-support:v1",
    "model": "acfqp:v075-total-lift-partial-model-binding:v1",
    "policy": "acfqp:v075-total-lift-selected-policy-binding:v1",
    "envelope": "acfqp:v075-total-lift-operational-envelope:v1",
    "exact_atom": "acfqp:v075-total-lift-exact-replay-atom:v1",
    "exact_row": "acfqp:v075-total-lift-exact-replay-row:v1",
    "construction_replay": (
        "acfqp:v075-total-lift-construction-exact-replay:v1"
    ),
    "replay_request_cas": (
        "acfqp:v075-total-lift-exact-replay-request-cas:v1"
    ),
    "replay_mint_verification": (
        "acfqp:v075-total-lift-exact-replay-mint-verification:v1"
    ),
    "verified_replay_mint": (
        "acfqp:v075-total-lift-verified-exact-replay-mint:v1"
    ),
    "exact_replay_boundary": (
        "acfqp:v075-total-lift-independent-exact-replay-boundary:v1"
    ),
    "branch_partition": (
        "acfqp:v075-total-lift-exact-branch-partition-witness:v1"
    ),
    "policy_abort_branch": (
        "acfqp:v075-total-lift-policy-abort-branch-witness:v1"
    ),
    "candidate": "acfqp:v075-total-lift-closure-candidate:v1",
    "protocol_failure": "acfqp:v075-total-lift-protocol-failure:v1",
    "envelope_miss": "acfqp:v075-total-lift-statistical-envelope-miss:v1",
    "endpoint": "acfqp:v075-total-lift-exact-endpoint:v1",
}

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(
        not value.startswith("acfqp:v075-")
        for value in DOMAIN_TAGS.values()
    )
):
    raise RuntimeError("V0-075 total-lift domains must be unique")


class V075TotalLiftProtocolCodeV1(str, Enum):
    INPUT_TYPE_MISMATCH = "INPUT_TYPE_MISMATCH"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    INCOMPLETE_FIXED_CONCRETIZER = "INCOMPLETE_FIXED_CONCRETIZER"
    SELECTED_ROOT_SUPPORT_INCOMPLETE = (
        "SELECTED_ROOT_SUPPORT_INCOMPLETE"
    )
    MODELED_SUPPORT_NOT_EXACT_POSITIVE = (
        "MODELED_SUPPORT_NOT_EXACT_POSITIVE"
    )
    MODELED_CHILD_DECISION_MISSING = "MODELED_CHILD_DECISION_MISSING"
    EXACT_REPLAY_INCOMPLETE = "EXACT_REPLAY_INCOMPLETE"
    EXACT_BRANCH_PARTITION_INVALID = "EXACT_BRANCH_PARTITION_INVALID"
    CANDIDATE_RECOMPUTATION_MISMATCH = (
        "CANDIDATE_RECOMPUTATION_MISMATCH"
    )


class V075TotalLiftProtocolViolation(ValueError):
    """A typed total-lift protocol invariant failed."""

    def __init__(
        self,
        code: V075TotalLiftProtocolCodeV1,
        message: str,
    ) -> None:
        if type(code) is not V075TotalLiftProtocolCodeV1:
            raise TypeError("total-lift protocol code must be typed")
        super().__init__(message)
        self.code = code


class V075ExactReplayMintFailureClassV1(str, Enum):
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


class V075ExactReplayMintFailureCodeV1(str, Enum):
    PRODUCTION_AUTHORITY_TYPE_MISMATCH = (
        "PRODUCTION_AUTHORITY_TYPE_MISMATCH"
    )
    CONSTRUCTION_AUTHORITY_TYPE_MISMATCH = (
        "CONSTRUCTION_AUTHORITY_TYPE_MISMATCH"
    )
    NAMESPACE_ENVELOPE_TRANSPLANT = "NAMESPACE_ENVELOPE_TRANSPLANT"
    PRIVATE_REVEAL_MISMATCH = "PRIVATE_REVEAL_MISMATCH"
    OBSERVER_CLOSURE_INVALID = "OBSERVER_CLOSURE_INVALID"
    CAPABILITY_LINEAGE_INVALID = "CAPABILITY_LINEAGE_INVALID"
    REPLAY_REQUEST_CAS_TRANSPLANT = "REPLAY_REQUEST_CAS_TRANSPLANT"
    EXACT_RECONSTRUCTION_INVALID = "EXACT_RECONSTRUCTION_INVALID"
    MODEL_POLICY_BINDING_INVALID = "MODEL_POLICY_BINDING_INVALID"


class V075ExactReplayMintViolation(ValueError):
    """A typed production/construction exact-replay mint failure."""

    def __init__(
        self,
        failure_class: V075ExactReplayMintFailureClassV1,
        code: V075ExactReplayMintFailureCodeV1,
        message: str,
    ) -> None:
        if (
            type(failure_class)
            is not V075ExactReplayMintFailureClassV1
            or type(code) is not V075ExactReplayMintFailureCodeV1
        ):
            raise TypeError("exact-replay mint failure must be strictly typed")
        super().__init__(message)
        self.failure_class = failure_class
        self.code = code


def _mint_fail(
    failure_class: V075ExactReplayMintFailureClassV1,
    code: V075ExactReplayMintFailureCodeV1,
    message: str,
) -> None:
    raise V075ExactReplayMintViolation(failure_class, code, message)


def _fail(
    code: V075TotalLiftProtocolCodeV1,
    message: str,
) -> None:
    raise V075TotalLiftProtocolViolation(code, message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            str(error),
        )
    raise AssertionError("unreachable")


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            f"{field_name} must be one lowercase SHA-256 content ID",
        )
        raise AssertionError("unreachable") from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            f"{field_name} must be canonical nonempty text",
        )
    return value


def _fraction(value: Any, field_name: str) -> Fraction:
    if type(value) is not Fraction:
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            f"{field_name} must use exact Fraction arithmetic",
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    canonical = _fraction(value, "serialized exact value")
    return {
        "numerator": canonical.numerator,
        "denominator": canonical.denominator,
    }


def _action(
    value: Any,
    field_name: str,
) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
        or value[0] >= value[1]
        or value[2] not in value[:2]
    ):
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            f"{field_name} must be one canonical graph action",
        )
    return value


def _registered_context(
    value: Any,
) -> public_authority.V075PublicReplicateContextV1:
    try:
        return public_authority.registered_public_context_v1(value)
    except (
        public_authority.V075PublicCampaignAuthorityInvariantViolation
    ) as error:
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            str(error),
        )
    raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class V075LawFreePlannerOccurrenceV1:
    namespace: public_authority.V075PublicTargetTapeNamespaceV1
    context: public_authority.V075PublicReplicateContextV1
    arm: str
    occurrence_ordinal: int
    _occurrence_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        context = _registered_context(self.context)
        if (
            type(self.namespace)
            is not public_authority.V075PublicTargetTapeNamespaceV1
            or context not in self.namespace.family.replicate_contexts
            or type(self.arm) is not str
            or self.arm not in public_authority.ARM_ORDER
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal < 0
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "law-free planner occurrence is malformed or transplanted",
            )
        object.__setattr__(
            self,
            "_occurrence_id",
            _hash("occurrence", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_law_free_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "context_id": self.context.context_id,
            "arm": self.arm,
            "occurrence_ordinal": self.occurrence_ordinal,
            "planner_transition_law_access": False,
            "planner_exact_atom_access": False,
        }

    @property
    def occurrence_id(self) -> str:
        return self._occurrence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_id": self.occurrence_id,
        }


@dataclass(frozen=True, slots=True)
class V075ObservedRowBindingV1:
    occurrence: V075LawFreePlannerOccurrenceV1
    row_binding: public_graph.V075ObservationRowBindingV1
    capabilities: tuple[
        observer_boundary.V075ObservationCapabilityV1,
        ...,
    ]
    _capability_ids: tuple[str, ...] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _observed_row_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not V075LawFreePlannerOccurrenceV1
            or type(self.row_binding)
            is not public_graph.V075ObservationRowBindingV1
            or self.row_binding.context != self.occurrence.context
            or type(self.capabilities) is not tuple
            or not self.capabilities
            or any(
                type(item)
                is not observer_boundary.V075ObservationCapabilityV1
                for item in self.capabilities
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "observed row requires typed signed capabilities",
            )
        capability_ids = tuple(
            item.capability_id for item in self.capabilities
        )
        if capability_ids != tuple(sorted(set(capability_ids))):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "observed row capabilities are duplicated or noncanonical",
            )
        for capability in self.capabilities:
            record = capability.record
            stream = record.stream_identity
            if (
                stream.namespace != self.occurrence.namespace
                or stream.row_binding != self.row_binding
                or stream.arm != self.occurrence.arm
            ):
                _fail(
                    V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                    "signed observation capability was transplanted",
                )
        object.__setattr__(self, "_capability_ids", capability_ids)
        object.__setattr__(
            self,
            "_observed_row_id",
            _hash("observed_row", self._payload()),
        )

    @property
    def action(self) -> tuple[int, int, int]:
        return self.row_binding.action

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_observed_row_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "catalogue_id": self.row_binding.catalogue_id,
            "action": list(self.action),
            "observation_capability_ids": [
                item for item in self._capability_ids
            ],
            "signed_observations_only": True,
            "exact_atoms_in_planner_binding": False,
        }

    @property
    def observed_row_id(self) -> str:
        return self._observed_row_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observed_row_id": self.observed_row_id,
        }


@dataclass(frozen=True, slots=True)
class V075ObservedSemanticActionV1:
    occurrence: V075LawFreePlannerOccurrenceV1
    catalogue: public_graph.V075LegalActionCatalogueV1
    semantic_key: str
    action_rows: tuple[V075ObservedRowBindingV1, ...]
    _semantic_action_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not V075LawFreePlannerOccurrenceV1
            or type(self.catalogue)
            is not public_graph.V075LegalActionCatalogueV1
            or self.catalogue.context != self.occurrence.context
            or type(self.action_rows) is not tuple
            or not self.action_rows
            or any(
                type(item) is not V075ObservedRowBindingV1
                or item.occurrence != self.occurrence
                or item.row_binding.catalogue != self.catalogue
                for item in self.action_rows
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "semantic action rows are untyped or transplanted",
            )
        _token(self.semantic_key, "semantic action key")
        actions = tuple(item.action for item in self.action_rows)
        if actions != tuple(sorted(set(actions))):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "semantic action ground support is duplicated or noncanonical",
            )
        object.__setattr__(
            self,
            "_semantic_action_id",
            _hash("semantic_action", self._payload()),
        )

    @property
    def ground_actions(self) -> tuple[tuple[int, int, int], ...]:
        return tuple(item.action for item in self.action_rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_semantic_action.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "remaining_horizon": self.catalogue.remaining_horizon,
            "semantic_key": self.semantic_key,
            "observed_row_ids": [
                item.observed_row_id for item in self.action_rows
            ],
            "ground_actions": [
                list(action) for action in self.ground_actions
            ],
        }

    @property
    def semantic_action_id(self) -> str:
        return self._semantic_action_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "semantic_action_id": self.semantic_action_id,
        }


@dataclass(frozen=True, slots=True)
class V075FixedConcretizerDecisionV1:
    semantic_action: V075ObservedSemanticActionV1
    ground_actions: tuple[tuple[int, int, int], ...]
    uniform_weights: tuple[Fraction, ...]
    _decision_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.semantic_action)
            is not V075ObservedSemanticActionV1
            or type(self.ground_actions) is not tuple
            or type(self.uniform_weights) is not tuple
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.INCOMPLETE_FIXED_CONCRETIZER,
                "fixed concretizer is not strictly typed",
            )
        expected_actions = self.semantic_action.ground_actions
        expected_weight = Fraction(1, len(expected_actions))
        if (
            self.ground_actions != expected_actions
            or self.ground_actions
            != tuple(sorted(set(self.ground_actions)))
            or len(self.uniform_weights) != len(self.ground_actions)
            or any(
                type(weight) is not Fraction
                or weight != expected_weight
                for weight in self.uniform_weights
            )
            or sum(self.uniform_weights, Fraction(0)) != 1
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.INCOMPLETE_FIXED_CONCRETIZER,
                "fixed concretizer must integrate the complete distinct "
                "semantic-action support uniformly",
            )
        object.__setattr__(
            self,
            "_decision_id",
            _hash("concretizer", self._payload()),
        )

    @property
    def catalogue(self) -> public_graph.V075LegalActionCatalogueV1:
        return self.semantic_action.catalogue

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_fixed_concretizer.v1",
            "schema_version": SCHEMA_VERSION,
            "semantic_action_id": self.semantic_action.semantic_action_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "ground_actions": [
                list(action) for action in self.ground_actions
            ],
            "uniform_weights": [
                _fdoc(weight) for weight in self.uniform_weights
            ],
            "distinct_action_uniformity_verified": True,
            "policy_randomization": False,
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class V075SelectedRootSupportV1:
    root_row: V075ObservedRowBindingV1
    modeled_children: tuple[
        public_graph.V075LegalActionCatalogueV1,
        ...,
    ]
    _support_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.root_row) is not V075ObservedRowBindingV1
            or self.root_row.row_binding.remaining_horizon
            != public_authority.HORIZON
            or type(self.modeled_children) is not tuple
            or any(
                type(item)
                is not public_graph.V075LegalActionCatalogueV1
                or item.context != self.root_row.occurrence.context
                or item.remaining_horizon != 1
                or item.state.failure
                for item in self.modeled_children
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "selected root support is malformed",
            )
        state_ids = tuple(
            item.state.state_id for item in self.modeled_children
        )
        if state_ids != tuple(sorted(set(state_ids))):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "modeled child support is duplicated or noncanonical",
            )
        object.__setattr__(
            self,
            "_support_id",
            _hash("root_support", self._payload()),
        )

    @property
    def root_action(self) -> tuple[int, int, int]:
        return self.root_row.action

    @property
    def modeled_child_state_ids(self) -> tuple[str, ...]:
        return tuple(
            item.state.state_id for item in self.modeled_children
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_selected_root_support.v1",
            "schema_version": SCHEMA_VERSION,
            "observed_root_row_id": self.root_row.observed_row_id,
            "root_action": list(self.root_action),
            "modeled_child_catalogue_ids": [
                item.catalogue_id for item in self.modeled_children
            ],
            "modeled_child_state_ids": list(
                self.modeled_child_state_ids
            ),
            "row_specific_support": True,
        }

    @property
    def support_id(self) -> str:
        return self._support_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_id": self.support_id}


@dataclass(frozen=True, slots=True)
class V075LawFreePartialModelBindingV1:
    occurrence: V075LawFreePlannerOccurrenceV1
    root_catalogue: public_graph.V075LegalActionCatalogueV1
    semantic_actions: tuple[V075ObservedSemanticActionV1, ...]
    selected_root_supports: tuple[V075SelectedRootSupportV1, ...]
    global_child_catalogues: tuple[
        public_graph.V075LegalActionCatalogueV1,
        ...,
    ]
    _model_id: str = field(init=False, repr=False, compare=False)
    _global_other_destination_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        expected_root = public_graph.root_catalogue_v1(
            self.occurrence.context
        )
        if (
            type(self.occurrence) is not V075LawFreePlannerOccurrenceV1
            or type(self.root_catalogue)
            is not public_graph.V075LegalActionCatalogueV1
            or self.root_catalogue != expected_root
            or type(self.semantic_actions) is not tuple
            or not self.semantic_actions
            or any(
                type(item) is not V075ObservedSemanticActionV1
                or item.occurrence != self.occurrence
                for item in self.semantic_actions
            )
            or type(self.selected_root_supports) is not tuple
            or not self.selected_root_supports
            or any(
                type(item) is not V075SelectedRootSupportV1
                or item.root_row.occurrence != self.occurrence
                or item.root_row.row_binding.catalogue
                != self.root_catalogue
                for item in self.selected_root_supports
            )
            or type(self.global_child_catalogues) is not tuple
            or any(
                type(item)
                is not public_graph.V075LegalActionCatalogueV1
                or item.context != self.occurrence.context
                or item.remaining_horizon != 1
                or item.state.failure
                for item in self.global_child_catalogues
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "law-free partial model graph is malformed",
            )
        semantic_ids = tuple(
            item.semantic_action_id for item in self.semantic_actions
        )
        support_actions = tuple(
            item.root_action for item in self.selected_root_supports
        )
        child_state_ids = tuple(
            item.state.state_id for item in self.global_child_catalogues
        )
        if (
            semantic_ids != tuple(sorted(set(semantic_ids)))
            or support_actions != tuple(sorted(set(support_actions)))
            or child_state_ids != tuple(sorted(set(child_state_ids)))
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "partial model registries are duplicated or noncanonical",
            )
        global_ids = set(child_state_ids)
        if any(
            not set(item.modeled_child_state_ids) <= global_ids
            for item in self.selected_root_supports
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "row-specific support is outside the global modeled registry",
            )
        row_ids = {
            row.observed_row_id
            for semantic in self.semantic_actions
            for row in semantic.action_rows
        }
        if any(
            support.root_row.observed_row_id not in row_ids
            for support in self.selected_root_supports
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "selected root support lacks its observed semantic row",
            )
        if any(
            semantic.catalogue.remaining_horizon == 1
            and semantic.catalogue.state.state_id not in global_ids
            for semantic in self.semantic_actions
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "child semantic action is outside the global model registry",
            )
        model_id = _hash("model", self._payload())
        object.__setattr__(self, "_model_id", model_id)
        object.__setattr__(
            self,
            "_global_other_destination_id",
            _hash(
                "model",
                {
                    "schema": (
                        "acfqp.v075_total_lift_global_other_destination.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "model_id": model_id,
                    "behavior": POLICY_ABORT_BEHAVIOR,
                    "absorbing": True,
                },
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_partial_model_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "root_catalogue_id": self.root_catalogue.catalogue_id,
            "semantic_action_ids": [
                item.semantic_action_id for item in self.semantic_actions
            ],
            "selected_root_support_ids": [
                item.support_id for item in self.selected_root_supports
            ],
            "global_child_catalogue_ids": [
                item.catalogue_id
                for item in self.global_child_catalogues
            ],
            "global_other_behavior": POLICY_ABORT_BEHAVIOR,
            "policy_abort_continuation_reward": _fdoc(Fraction(0)),
            "law_free_observation_capabilities_only": True,
            "exact_atoms_in_model": False,
        }

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def global_other_destination_id(self) -> str:
        return self._global_other_destination_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "global_other_destination_id": (
                self.global_other_destination_id
            ),
            "model_id": self.model_id,
        }


class V075RouteKindV1(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


@dataclass(frozen=True, slots=True)
class V075SelectedPolicyBindingV1:
    model: V075LawFreePartialModelBindingV1
    route_kind: V075RouteKindV1
    root_decision: V075FixedConcretizerDecisionV1
    child_decisions: tuple[V075FixedConcretizerDecisionV1, ...]
    _policy_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.model) is not V075LawFreePartialModelBindingV1
            or type(self.route_kind) is not V075RouteKindV1
            or type(self.root_decision)
            is not V075FixedConcretizerDecisionV1
            or self.root_decision.catalogue != self.model.root_catalogue
            or type(self.child_decisions) is not tuple
            or any(
                type(item) is not V075FixedConcretizerDecisionV1
                or item.catalogue.remaining_horizon != 1
                for item in self.child_decisions
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "selected policy binding is malformed",
            )
        registered_semantics = set(self.model.semantic_actions)
        if (
            self.root_decision.semantic_action not in registered_semantics
            or any(
                item.semantic_action not in registered_semantics
                for item in self.child_decisions
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "selected decision is outside the frozen model",
            )
        state_ids = tuple(
            item.catalogue.state.state_id
            for item in self.child_decisions
        )
        if state_ids != tuple(sorted(set(state_ids))):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "child decisions are duplicated or noncanonical",
            )
        object.__setattr__(
            self,
            "_policy_id",
            _hash("policy", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_selected_policy_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model.model_id,
            "route_kind": self.route_kind.value,
            "root_decision_id": self.root_decision.decision_id,
            "child_decision_ids": [
                item.decision_id for item in self.child_decisions
            ],
            "deterministic_semantic_selector": True,
            "fixed_stochastic_concretizer": True,
            "policy_randomization": False,
        }

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "policy_id": self.policy_id}


@dataclass(frozen=True, slots=True)
class V075OperationalEnvelopeV1:
    policy: V075SelectedPolicyBindingV1
    selected_reward_lower: Fraction
    unrestricted_reward_upper: Fraction
    selected_failure_upper: Fraction
    normalized_regret_upper: Fraction
    _envelope_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.policy) is not V075SelectedPolicyBindingV1:
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "operational envelope lacks its typed policy",
            )
        lower = _fraction(
            self.selected_reward_lower,
            "selected reward lower",
        )
        upper = _fraction(
            self.unrestricted_reward_upper,
            "unrestricted reward upper",
        )
        failure = _fraction(
            self.selected_failure_upper,
            "selected failure upper",
        )
        regret = _fraction(
            self.normalized_regret_upper,
            "normalized regret upper",
        )
        if (
            lower < 0
            or upper < lower
            or not 0 <= failure <= 1
            or regret < 0
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                "operational envelope bounds are malformed",
            )
        object.__setattr__(
            self,
            "_envelope_id",
            _hash("envelope", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        occurrence = self.policy.model.occurrence
        return {
            "schema": "acfqp.v075_total_lift_operational_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": occurrence.occurrence_id,
            "model_id": self.policy.model.model_id,
            "policy_id": self.policy.policy_id,
            "context_id": occurrence.context.context_id,
            "selected_reward_lower": _fdoc(
                self.selected_reward_lower
            ),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "selected_failure_upper": _fdoc(
                self.selected_failure_upper
            ),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "caller_validity_flag_accepted": False,
            "exact_atom_access": False,
        }

    @property
    def envelope_id(self) -> str:
        return self._envelope_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class V075ExactReplayAtomV1:
    row_binding: public_graph.V075ObservationRowBindingV1
    atom: H2GraphTransitionAtomV1
    _next_state: public_graph.V075SymbolicGraphStateV1 = field(
        init=False,
        repr=False,
        compare=False,
    )
    _atom_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.row_binding)
            is not public_graph.V075ObservationRowBindingV1
            or type(self.atom) is not H2GraphTransitionAtomV1
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay atom is not behind the typed row boundary",
            )
        try:
            successor = public_graph.V075SymbolicGraphStateV1(
                self.row_binding.context,
                self.atom.next_state.ranks,
                self.atom.next_state.failure,
            )
        except (
            public_graph.V075PublicGraphSemanticsInvariantViolation
        ) as error:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                str(error),
            )
        object.__setattr__(self, "_next_state", successor)
        if (
            self.atom.spawn_cell
            not in range(self.row_binding.context.topology.vertex_count)
            or self.atom.spawn_rank > self.row_binding.context.rank_cap
            or self.atom.terminal
            != (
                self.atom.failure
                or self.row_binding.remaining_horizon == 1
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay atom violates H=2 terminal semantics",
            )
        object.__setattr__(
            self,
            "_atom_id",
            _hash("exact_atom", self._payload()),
        )

    @property
    def next_state(self) -> public_graph.V075SymbolicGraphStateV1:
        return self._next_state

    @property
    def next_state_id(self) -> str:
        return self.next_state.state_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_exact_replay_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding.row_binding_id,
            "next_state_id": self.next_state_id,
            "next_ranks": list(self.atom.next_state.ranks),
            "probability": _fdoc(self.atom.probability),
            "realized_row_reward": _fdoc(
                self.atom.realized_row_reward
            ),
            "failure": self.atom.failure,
            "terminal": self.atom.terminal,
            "spawn_cell": self.atom.spawn_cell,
            "spawn_rank": self.atom.spawn_rank,
            "execution_lane": INDEPENDENT_EXACT_REPLAY_LANE,
        }

    @property
    def atom_id(self) -> str:
        return self._atom_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class V075ExactReplayRowV1:
    row_binding: public_graph.V075ObservationRowBindingV1
    atoms: tuple[V075ExactReplayAtomV1, ...]
    _row_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.row_binding)
            is not public_graph.V075ObservationRowBindingV1
            or type(self.atoms) is not tuple
            or not self.atoms
            or any(
                type(item) is not V075ExactReplayAtomV1
                or item.row_binding != self.row_binding
                for item in self.atoms
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay row is malformed",
            )
        atom_ids = tuple(item.atom_id for item in self.atoms)
        if (
            atom_ids != tuple(sorted(set(atom_ids)))
            or sum(
                (item.atom.probability for item in self.atoms),
                Fraction(0),
            )
            != 1
            or len(
                {
                    item.atom.realized_row_reward
                    for item in self.atoms
                }
            )
            != 1
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay row is duplicated, nonnormalized, or "
                "reward-inconsistent",
            )
        object.__setattr__(
            self,
            "_row_id",
            _hash("exact_row", self._payload()),
        )

    @property
    def reward(self) -> Fraction:
        return self.atoms[0].atom.realized_row_reward

    @property
    def failure_probability(self) -> Fraction:
        return sum(
            (
                item.atom.probability
                for item in self.atoms
                if item.atom.failure
            ),
            Fraction(0),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_exact_replay_row.v1",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding.row_binding_id,
            "catalogue_id": self.row_binding.catalogue_id,
            "state_id": self.row_binding.state_id,
            "remaining_horizon": self.row_binding.remaining_horizon,
            "action": list(self.row_binding.action),
            "atom_ids": [item.atom_id for item in self.atoms],
            "reward": _fdoc(self.reward),
            "failure_probability": _fdoc(
                self.failure_probability
            ),
            "execution_lane": INDEPENDENT_EXACT_REPLAY_LANE,
        }

    @property
    def row_id(self) -> str:
        return self._row_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


class V075ExactReplayScopeV1(str, Enum):
    CONSTRUCTION_ONLY = "CONSTRUCTION_ONLY"
    INDEPENDENT_CLOSURE_REPLAY = "INDEPENDENT_CLOSURE_REPLAY"


_EXACT_REPLAY_BOUNDARY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075IndependentExactReplayBoundaryV1:
    occurrence: V075LawFreePlannerOccurrenceV1
    rows: tuple[V075ExactReplayRowV1, ...]
    scope: V075ExactReplayScopeV1
    replay_verification_id: str
    bound_model_id: str | None
    bound_policy_id: str | None
    bound_envelope_id: str | None
    replay_request_cas_id: str | None
    _issuer: object = field(repr=False, compare=False)
    _boundary_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _EXACT_REPLAY_BOUNDARY_ISSUER:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay boundary requires its independent issuer",
            )
        _cid(
            self.replay_verification_id,
            "exact replay verification",
        )
        if (
            type(self.occurrence) is not V075LawFreePlannerOccurrenceV1
            or type(self.rows) is not tuple
            or not self.rows
            or any(
                type(item) is not V075ExactReplayRowV1
                or item.row_binding.context != self.occurrence.context
                for item in self.rows
            )
            or type(self.scope) is not V075ExactReplayScopeV1
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay boundary is malformed or transplanted",
            )
        binding_ids = (
            self.bound_model_id,
            self.bound_policy_id,
            self.bound_envelope_id,
            self.replay_request_cas_id,
        )
        if any(value is None for value in binding_ids):
            if (
                any(value is not None for value in binding_ids)
                or self.scope
                is V075ExactReplayScopeV1.INDEPENDENT_CLOSURE_REPLAY
            ):
                _fail(
                    V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                    "exact replay boundary has a partial or missing "
                    "production model/policy/envelope/CAS binding",
                )
        else:
            for value, label in zip(
                binding_ids,
                (
                    "bound replay model",
                    "bound replay policy",
                    "bound replay envelope",
                    "bound replay request CAS",
                ),
                strict=True,
            ):
                _cid(value, label)
        row_ids = tuple(item.row_id for item in self.rows)
        if row_ids != tuple(sorted(set(row_ids))):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay rows are duplicated or noncanonical",
            )
        _verify_complete_exact_replay_inventory(self)
        object.__setattr__(
            self,
            "_boundary_id",
            _hash("exact_replay_boundary", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_total_lift_independent_exact_replay_"
                "boundary.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "scope": self.scope.value,
            "replay_verification_id": self.replay_verification_id,
            "bound_model_id": self.bound_model_id,
            "bound_policy_id": self.bound_policy_id,
            "bound_envelope_id": self.bound_envelope_id,
            "replay_request_cas_id": self.replay_request_cas_id,
            "exact_row_ids": [item.row_id for item in self.rows],
            "execution_lane": INDEPENDENT_EXACT_REPLAY_LANE,
            "planner_access_allowed": False,
        }

    @property
    def boundary_id(self) -> str:
        return self._boundary_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


def _row_key(
    row_binding: public_graph.V075ObservationRowBindingV1,
) -> tuple[str, int, tuple[int, int, int]]:
    return (
        row_binding.state_id,
        row_binding.remaining_horizon,
        row_binding.action,
    )


def _child_catalogue(
    state: public_graph.V075SymbolicGraphStateV1,
) -> public_graph.V075LegalActionCatalogueV1:
    actions = public_graph.legal_action_triples_v1(
        state.context,
        state.ranks,
        state.failure,
    )
    return public_graph.V075LegalActionCatalogueV1(
        state.context,
        state,
        1,
        actions,
    )


def _verify_complete_exact_replay_inventory(
    boundary: V075IndependentExactReplayBoundaryV1,
) -> None:
    rows_by_key: dict[
        tuple[str, int, tuple[int, int, int]],
        V075ExactReplayRowV1,
    ] = {}
    for row in boundary.rows:
        key = _row_key(row.row_binding)
        if key in rows_by_key:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay contains duplicate state/action rows",
            )
        rows_by_key[key] = row
    root = public_graph.root_catalogue_v1(boundary.occurrence.context)
    expected_keys = {
        (root.state.state_id, root.remaining_horizon, action)
        for action in root.actions
    }
    active_children: dict[
        str,
        public_graph.V075SymbolicGraphStateV1,
    ] = {}
    for key in tuple(sorted(expected_keys)):
        row = rows_by_key.get(key)
        if row is None or row.row_binding.catalogue != root:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "exact replay omits a complete root catalogue row",
            )
        for exact_atom in row.atoms:
            atom = exact_atom.atom
            if atom.failure:
                continue
            if atom.terminal:
                _fail(
                    V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                    "H=2 root replay contains terminal nonfailure mass",
                )
            state = exact_atom.next_state
            previous = active_children.setdefault(state.state_id, state)
            if previous != state:
                _fail(
                    V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                    "one exact state identity names different states",
                )
    for state in active_children.values():
        catalogue = _child_catalogue(state)
        for action in catalogue.actions:
            key = (state.state_id, 1, action)
            expected_keys.add(key)
            row = rows_by_key.get(key)
            if row is None or row.row_binding.catalogue != catalogue:
                _fail(
                    V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                    "exact replay omits a reachable child action row",
                )
    if set(rows_by_key) != expected_keys:
        _fail(
            V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
            "exact replay contains rows outside the complete H=2 closure",
        )


def mint_construction_exact_replay_boundary_v1(
    *,
    occurrence: V075LawFreePlannerOccurrenceV1,
    rows: Iterable[V075ExactReplayRowV1],
    construction_fixture_registration_id: str,
) -> V075IndependentExactReplayBoundaryV1:
    """Mint an exact replay boundary for synthetic construction tests only."""

    if type(occurrence) is not V075LawFreePlannerOccurrenceV1:
        _fail(
            V075TotalLiftProtocolCodeV1.INPUT_TYPE_MISMATCH,
            "construction replay requires one typed occurrence",
        )
    registration = _cid(
        construction_fixture_registration_id,
        "construction replay registration",
    )
    try:
        canonical_rows = tuple(
            sorted(tuple(rows), key=lambda item: item.row_id)
        )
    except (AttributeError, TypeError) as error:
        _fail(
            V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
            "construction replay rows must be concrete typed rows",
        )
        raise AssertionError("unreachable") from error
    verification_id = _hash(
        "construction_replay",
        {
            "schema": (
                "acfqp.v075_total_lift_construction_exact_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": occurrence.occurrence_id,
            "construction_fixture_registration_id": registration,
            "exact_row_ids": [item.row_id for item in canonical_rows],
            "production_claim_allowed": False,
        },
    )
    return V075IndependentExactReplayBoundaryV1(
        occurrence,
        canonical_rows,
        V075ExactReplayScopeV1.CONSTRUCTION_ONLY,
        verification_id,
        None,
        None,
        None,
        None,
        _EXACT_REPLAY_BOUNDARY_ISSUER,
    )


_REPLAY_MINT_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ExactReplayMintVerificationV1:
    """Public, law-free attestation for one exact replay reconstruction."""

    _issuer: object = field(repr=False, compare=False)
    scope: V075ExactReplayScopeV1
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    observer_open_binding_id: str
    observer_closure_id: str
    observer_closure_verification_id: str
    replay_request_cas_id: str
    model_id: str
    policy_id: str
    envelope_id: str
    observation_capability_ids: tuple[str, ...]
    exact_row_ids: tuple[str, ...]
    exact_atom_count: int
    _verification_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _REPLAY_MINT_VERIFICATION_ISSUER
            or type(self.scope) is not V075ExactReplayScopeV1
            or type(self.observation_capability_ids) is not tuple
            or type(self.exact_row_ids) is not tuple
            or type(self.exact_atom_count) is not int
            or self.exact_atom_count <= 0
        ):
            _mint_fail(
                V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
                V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
                "exact replay mint verification is not issuer-typed",
            )
        for value, label in (
            (self.occurrence_id, "mint occurrence"),
            (
                self.target_tape_namespace_id,
                "mint target-tape namespace",
            ),
            (self.context_id, "mint context"),
            (self.observer_open_binding_id, "mint observer binding"),
            (self.observer_closure_id, "mint observer closure"),
            (
                self.observer_closure_verification_id,
                "mint observer closure verification",
            ),
            (self.replay_request_cas_id, "mint request CAS"),
            (self.model_id, "mint model"),
            (self.policy_id, "mint policy"),
            (self.envelope_id, "mint envelope"),
        ):
            _cid(value, label)
        for values, label in (
            (
                self.observation_capability_ids,
                "mint observation capabilities",
            ),
            (self.exact_row_ids, "mint exact rows"),
        ):
            if values != tuple(sorted(set(values))) or not values:
                _mint_fail(
                    V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                    (
                        V075ExactReplayMintFailureCodeV1
                        .CAPABILITY_LINEAGE_INVALID
                        if label == "mint observation capabilities"
                        else (
                            V075ExactReplayMintFailureCodeV1
                            .EXACT_RECONSTRUCTION_INVALID
                        )
                    ),
                    f"{label} are empty, duplicated, or noncanonical",
                )
            for value in values:
                _cid(value, label)
        object.__setattr__(
            self,
            "_verification_id",
            _hash("replay_mint_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_total_lift_exact_replay_mint_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "scope": self.scope.value,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "observer_closure_id": self.observer_closure_id,
            "observer_closure_verification_id": (
                self.observer_closure_verification_id
            ),
            "replay_request_cas_id": self.replay_request_cas_id,
            "model_id": self.model_id,
            "policy_id": self.policy_id,
            "envelope_id": self.envelope_id,
            "observation_capability_ids": list(
                self.observation_capability_ids
            ),
            "exact_row_ids": list(self.exact_row_ids),
            "exact_atom_count": self.exact_atom_count,
            "full_h2_exact_closure_reconstructed": True,
            "observer_journal_exact_replay_verified": True,
            "capability_lineage_verified": True,
            "model_policy_envelope_binding_verified": True,
            "private_environment_serialized": False,
            "private_salt_serialized": False,
            "transition_law_serialized": False,
            "random_tape_serialized": False,
            "exact_atom_payload_serialized": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


@dataclass(frozen=True, slots=True)
class V075VerifiedExactReplayMintV1:
    verification: V075ExactReplayMintVerificationV1
    boundary: V075IndependentExactReplayBoundaryV1
    _mint_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.verification)
            is not V075ExactReplayMintVerificationV1
            or type(self.boundary)
            is not V075IndependentExactReplayBoundaryV1
            or self.boundary.scope != self.verification.scope
            or self.boundary.occurrence.occurrence_id
            != self.verification.occurrence_id
            or self.boundary.replay_verification_id
            != self.verification.verification_id
            or self.boundary.bound_model_id
            != self.verification.model_id
            or self.boundary.bound_policy_id
            != self.verification.policy_id
            or self.boundary.bound_envelope_id
            != self.verification.envelope_id
            or self.boundary.replay_request_cas_id
            != self.verification.replay_request_cas_id
            or tuple(item.row_id for item in self.boundary.rows)
            != self.verification.exact_row_ids
            or sum(len(item.atoms) for item in self.boundary.rows)
            != self.verification.exact_atom_count
        ):
            _mint_fail(
                V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                V075ExactReplayMintFailureCodeV1.REPLAY_REQUEST_CAS_TRANSPLANT,
                "verified exact replay mint was transplanted",
            )
        object.__setattr__(
            self,
            "_mint_id",
            _hash(
                "verified_replay_mint",
                {
                    "schema": (
                        "acfqp.v075_total_lift_verified_exact_replay_mint.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "verification_id": self.verification.verification_id,
                    "exact_replay_boundary_id": self.boundary.boundary_id,
                },
            ),
        )

    @property
    def mint_id(self) -> str:
        return self._mint_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_total_lift_verified_exact_replay_mint.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verification": self.verification.to_document(),
            "exact_replay_boundary": self.boundary.to_document(),
            "mint_id": self.mint_id,
            "private_material_serialized": False,
        }


def _canonical_private_environment_for_mint(
    *,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[
    tuple[tuple[tuple[int, Fraction], ...], ...],
    dict[str, H2GraphKernelV1],
]:
    if (
        type(namespace)
        is not public_authority.V075PublicTargetTapeNamespaceV1
        or type(private_salt) is not bytes
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            V075ExactReplayMintFailureCodeV1.NAMESPACE_ENVELOPE_TRANSPLANT,
            "exact replay mint namespace or private salt is untyped",
        )
    try:
        environment = tuple(tuple(row) for row in private_environment)
    except TypeError as error:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
            "private environment must be one concrete exact sequence",
        )
        raise AssertionError("unreachable") from error
    if len(environment) != len(namespace.family.replicate_contexts):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
            "private environment does not cover the registered family",
        )
    try:
        kernels = {
            context.context_id: H2GraphKernelV1(
                context.topology,
                context.rank_cap,
                context.horizon,
                law,
            )
            for context, law in zip(
                namespace.family.replicate_contexts,
                environment,
                strict=True,
            )
        }
        reveal = public_authority.verify_opaque_environment_reveal_v1(
            commitment=namespace.environment_commitment,
            secret_salt=private_salt,
            secret_laws=environment,
        )
    except (
        H2GraphTransitionInvariantViolation,
        public_authority.V075PublicCampaignAuthorityInvariantViolation,
    ) as error:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.PRIVATE_REVEAL_MISMATCH,
            str(error),
        )
    if not reveal.matched:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.PRIVATE_REVEAL_MISMATCH,
            "private environment reveal does not match the opaque commitment",
        )
    return environment, kernels


def _reconstruct_full_h2_exact_rows(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    kernel: H2GraphKernelV1,
) -> tuple[V075ExactReplayRowV1, ...]:
    if (
        _registered_context(context) != context
        or type(kernel) is not H2GraphKernelV1
        or kernel.topology != context.topology
        or kernel.rank_cap != context.rank_cap
        or kernel.horizon != context.horizon
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
            "private kernel was transplanted across public contexts",
        )
    rows: list[V075ExactReplayRowV1] = []
    active_states: dict[
        str,
        public_graph.V075SymbolicGraphStateV1,
    ] = {}

    def add_row(
        catalogue: public_graph.V075LegalActionCatalogueV1,
        action: tuple[int, int, int],
    ) -> None:
        binding = public_graph.observation_row_binding_v1(
            context,
            catalogue,
            action,
        )
        try:
            atoms = tuple(
                V075ExactReplayAtomV1(binding, atom)
                for atom in kernel.exact_atoms(
                    catalogue.state.to_kernel_state(),
                    H2GraphActionV1(*action),
                    remaining_horizon=catalogue.remaining_horizon,
                )
            )
        except (
            H2GraphTransitionInvariantViolation,
            V075TotalLiftProtocolViolation,
        ) as error:
            _mint_fail(
                V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
                str(error),
            )
        try:
            row = V075ExactReplayRowV1(
                binding,
                tuple(sorted(atoms, key=lambda item: item.atom_id)),
            )
        except V075TotalLiftProtocolViolation as error:
            _mint_fail(
                V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
                str(error),
            )
        rows.append(row)
        if catalogue.remaining_horizon == context.horizon:
            for exact_atom in row.atoms:
                if exact_atom.atom.failure:
                    continue
                prior = active_states.setdefault(
                    exact_atom.next_state_id,
                    exact_atom.next_state,
                )
                if prior != exact_atom.next_state:
                    _mint_fail(
                        V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                        (
                            V075ExactReplayMintFailureCodeV1
                            .EXACT_RECONSTRUCTION_INVALID
                        ),
                        "one reconstructed state ID names different states",
                    )

    root = public_graph.root_catalogue_v1(context)
    for action in root.actions:
        add_row(root, action)
    for state_id in sorted(active_states):
        catalogue = _child_catalogue(active_states[state_id])
        for action in catalogue.actions:
            add_row(catalogue, action)
    return tuple(sorted(rows, key=lambda item: item.row_id))


def _model_observation_lineage(
    model: V075LawFreePartialModelBindingV1,
) -> tuple[
    tuple[V075ObservedRowBindingV1, ...],
    tuple[observer_boundary.V075ObservationCapabilityV1, ...],
]:
    observed_rows = tuple(
        row
        for semantic in model.semantic_actions
        for row in semantic.action_rows
    )
    observed_row_ids = tuple(item.observed_row_id for item in observed_rows)
    if len(set(observed_row_ids)) != len(observed_row_ids):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.CAPABILITY_LINEAGE_INVALID,
            "model observed-row registry is duplicated or noncanonical",
        )
    capabilities = tuple(
        capability
        for row in observed_rows
        for capability in row.capabilities
    )
    capability_ids = tuple(item.capability_id for item in capabilities)
    if len(set(capability_ids)) != len(capability_ids):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.CAPABILITY_LINEAGE_INVALID,
            "model capability registry is duplicated or noncanonical",
        )
    return (
        tuple(
            sorted(
                observed_rows,
                key=lambda item: item.observed_row_id,
            )
        ),
        tuple(
            sorted(
                capabilities,
                key=lambda item: item.capability_id,
            )
        ),
    )


def _verify_observer_capability_lineage(
    *,
    envelope: V075OperationalEnvelopeV1,
    closure: observer_boundary.V075ObserverJournalClosureV1,
    rows: tuple[V075ExactReplayRowV1, ...],
) -> tuple[str, ...]:
    model = envelope.policy.model
    observed_rows, capabilities = _model_observation_lineage(model)
    closure_records: dict[
        str,
        observer_boundary.V075SignedObservationRecordV1,
    ] = {}
    for entry in closure.entries:
        record = entry.record
        if record.record_id in closure_records:
            _mint_fail(
                V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                V075ExactReplayMintFailureCodeV1.CAPABILITY_LINEAGE_INVALID,
                "observer journal repeats one signed observation record",
            )
        closure_records[record.record_id] = record
    for capability in capabilities:
        record = closure_records.get(capability.record.record_id)
        if record is None or record != capability.record:
            _mint_fail(
                V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
                V075ExactReplayMintFailureCodeV1.CAPABILITY_LINEAGE_INVALID,
                "modeled row lacks its exact signed observer-journal record",
            )
    exact_keys = {_row_key(item.row_binding) for item in rows}
    if any(
        _row_key(item.row_binding) not in exact_keys
        for item in observed_rows
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.CAPABILITY_LINEAGE_INVALID,
            "observed model row is outside the reconstructed H=2 closure",
        )
    return tuple(sorted(item.capability_id for item in capabilities))


def _verify_and_mint_exact_replay_from_closure(
    *,
    scope: V075ExactReplayScopeV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    envelope: V075OperationalEnvelopeV1,
    closure: observer_boundary.V075ObserverJournalClosureV1,
    closure_verification: observer_boundary.V075ObserverClosureVerificationV1,
    kernels: Mapping[str, H2GraphKernelV1],
) -> V075VerifiedExactReplayMintV1:
    if (
        type(scope) is not V075ExactReplayScopeV1
        or type(namespace)
        is not public_authority.V075PublicTargetTapeNamespaceV1
        or type(envelope) is not V075OperationalEnvelopeV1
        or type(closure)
        is not observer_boundary.V075ObserverJournalClosureV1
        or type(closure_verification)
        is not observer_boundary.V075ObserverClosureVerificationV1
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            V075ExactReplayMintFailureCodeV1.NAMESPACE_ENVELOPE_TRANSPLANT,
            "exact replay mint inputs are not strictly typed",
        )
    occurrence = envelope.policy.model.occurrence
    if (
        occurrence.namespace != namespace
        or occurrence.context
        not in namespace.family.replicate_contexts
        or closure.authority_binding.namespace != namespace
        or closure_verification.closure_id != closure.closure_id
        or closure_verification.observer_open_binding_id
        != closure.authority_binding.binding_id
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.NAMESPACE_ENVELOPE_TRANSPLANT,
            "namespace, envelope, occurrence, or observer closure was "
            "transplanted",
        )
    kernel = kernels.get(occurrence.context.context_id)
    if type(kernel) is not H2GraphKernelV1:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.EXACT_RECONSTRUCTION_INVALID,
            "private environment lacks the occurrence context",
        )
    rows = _reconstruct_full_h2_exact_rows(
        context=occurrence.context,
        kernel=kernel,
    )
    capability_ids = _verify_observer_capability_lineage(
        envelope=envelope,
        closure=closure,
        rows=rows,
    )
    replay_request_cas_id = _hash(
        "replay_request_cas",
        {
            "schema": (
                "acfqp.v075_total_lift_exact_replay_request_cas.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "scope": scope.value,
            "occurrence_id": occurrence.occurrence_id,
            "target_tape_namespace_id": (
                namespace.target_tape_namespace_id
            ),
            "context_id": occurrence.context.context_id,
            "observer_open_binding_id": (
                closure.authority_binding.binding_id
            ),
            "observer_closure_id": closure.closure_id,
            "observer_closure_verification_id": (
                closure_verification.verification_id
            ),
            "model_id": envelope.policy.model.model_id,
            "policy_id": envelope.policy.policy_id,
            "envelope_id": envelope.envelope_id,
            "observation_capability_ids": list(capability_ids),
            "exact_row_ids": [item.row_id for item in rows],
        },
    )
    verification = V075ExactReplayMintVerificationV1(
        _REPLAY_MINT_VERIFICATION_ISSUER,
        scope,
        occurrence.occurrence_id,
        namespace.target_tape_namespace_id,
        occurrence.context.context_id,
        closure.authority_binding.binding_id,
        closure.closure_id,
        closure_verification.verification_id,
        replay_request_cas_id,
        envelope.policy.model.model_id,
        envelope.policy.policy_id,
        envelope.envelope_id,
        capability_ids,
        tuple(item.row_id for item in rows),
        sum(len(item.atoms) for item in rows),
    )
    try:
        boundary = V075IndependentExactReplayBoundaryV1(
            occurrence,
            rows,
            scope,
            verification.verification_id,
            envelope.policy.model.model_id,
            envelope.policy.policy_id,
            envelope.envelope_id,
            replay_request_cas_id,
            _EXACT_REPLAY_BOUNDARY_ISSUER,
        )
        _derive_total_lift_candidate(
            envelope=envelope,
            exact_replay=boundary,
        )
    except V075TotalLiftProtocolViolation as error:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            V075ExactReplayMintFailureCodeV1.MODEL_POLICY_BINDING_INVALID,
            f"{error.code.value}: {error}",
        )
    return V075VerifiedExactReplayMintV1(verification, boundary)


def verify_and_mint_production_exact_replay_boundary_v1(
    *,
    authority: Any,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    envelope: V075OperationalEnvelopeV1,
    observer_journal_closure: observer_boundary.V075ObserverJournalClosureV1,
    private_salt: bytes,
    private_environment: Any,
) -> V075VerifiedExactReplayMintV1:
    """Strict production mint from an independently anchored private replay."""

    from acfqp import v075_preopen_target_authorization_v1 as preopen
    from acfqp import (
        v075_private_environment_generation_profile_v1 as private_generation,
    )

    if (
        type(authority) is not preopen.V075ObserverOpenAuthorizationV1
        or type(private_environment)
        is not private_generation.V075PrivateGeneratedEnvironmentV1
        or private_environment.family != namespace.family
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            (
                V075ExactReplayMintFailureCodeV1
                .PRODUCTION_AUTHORITY_TYPE_MISMATCH
            ),
            "production exact replay requires the independently issued "
            "production-open authority and exact generated private "
            "environment",
        )
    environment_input = private_environment.secret_laws_for_commitment()
    environment, kernels = _canonical_private_environment_for_mint(
        namespace=namespace,
        private_salt=private_salt,
        private_environment=environment_input,
    )
    try:
        closure_verification = (
            observer_boundary.verify_private_observer_journal_closure_v1(
                closure=observer_journal_closure,
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=environment,
            )
        )
    except (
        observer_boundary.V075PrivateObserverBoundaryInvariantViolation
    ) as error:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.OBSERVER_CLOSURE_INVALID,
            str(error),
        )
    return _verify_and_mint_exact_replay_from_closure(
        scope=V075ExactReplayScopeV1.INDEPENDENT_CLOSURE_REPLAY,
        namespace=namespace,
        envelope=envelope,
        closure=observer_journal_closure,
        closure_verification=closure_verification,
        kernels=kernels,
    )


def verify_and_mint_construction_exact_replay_from_journal_v1(
    *,
    authority: observer_boundary.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    namespace: public_authority.V075PublicTargetTapeNamespaceV1,
    envelope: V075OperationalEnvelopeV1,
    observer_journal_closure: observer_boundary.V075ObserverJournalClosureV1,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075VerifiedExactReplayMintV1:
    """Test-only parity path with a domain-disjoint construction authority."""

    if (
        type(authority)
        is not (
            observer_boundary
            .V075ConstructionOnlyObserverOpenAuthorityFixtureV1
        )
    ):
        _mint_fail(
            V075ExactReplayMintFailureClassV1.PROTOCOL_FAILURE,
            (
                V075ExactReplayMintFailureCodeV1
                .CONSTRUCTION_AUTHORITY_TYPE_MISMATCH
            ),
            "construction replay mint requires its exact fixture authority",
        )
    environment, kernels = _canonical_private_environment_for_mint(
        namespace=namespace,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    try:
        closure_verification = (
            observer_boundary
            .verify_construction_private_observer_journal_closure_v1(
                closure=observer_journal_closure,
                authority=authority,
                private_salt=private_salt,
                private_environment=environment,
            )
        )
    except (
        observer_boundary.V075PrivateObserverBoundaryInvariantViolation
    ) as error:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.OBSERVER_CLOSURE_INVALID,
            str(error),
        )
    if authority.namespace != namespace:
        _mint_fail(
            V075ExactReplayMintFailureClassV1.INTEGRITY_FAILURE,
            V075ExactReplayMintFailureCodeV1.NAMESPACE_ENVELOPE_TRANSPLANT,
            "construction replay authority was transplanted",
        )
    return _verify_and_mint_exact_replay_from_closure(
        scope=V075ExactReplayScopeV1.CONSTRUCTION_ONLY,
        namespace=namespace,
        envelope=envelope,
        closure=observer_journal_closure,
        closure_verification=closure_verification,
        kernels=kernels,
    )


@dataclass(frozen=True, slots=True)
class V075ExactBranchPartitionWitnessV1:
    occurrence_id: str
    root_ground_action: tuple[int, int, int]
    root_realization_weight: Fraction
    exact_root_row_id: str
    exact_atom_probability_items: tuple[tuple[str, Fraction], ...]
    environment_failure_atom_ids: tuple[str, ...]
    modeled_recurse_atom_ids: tuple[str, ...]
    policy_abort_atom_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "branch-partition occurrence")
        _action(self.root_ground_action, "branch-partition root action")
        weight = _fraction(
            self.root_realization_weight,
            "root realization weight",
        )
        _cid(self.exact_root_row_id, "branch-partition exact row")
        if (
            not 0 < weight <= 1
            or type(self.exact_atom_probability_items) is not tuple
            or not self.exact_atom_probability_items
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[1]) is not Fraction
                or not 0 < item[1] <= 1
                for item in self.exact_atom_probability_items
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "exact branch atom inventory is malformed",
            )
        exact_ids = tuple(
            item[0] for item in self.exact_atom_probability_items
        )
        for atom_id in exact_ids:
            _cid(atom_id, "branch-partition exact atom")
        if (
            exact_ids != tuple(sorted(set(exact_ids)))
            or sum(
                (
                    probability
                    for _atom_id, probability
                    in self.exact_atom_probability_items
                ),
                Fraction(0),
            )
            != 1
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "exact branch atom inventory is duplicated or nonnormalized",
            )
        partitions = (
            self.environment_failure_atom_ids,
            self.modeled_recurse_atom_ids,
            self.policy_abort_atom_ids,
        )
        if any(
            type(items) is not tuple
            or items != tuple(sorted(set(items)))
            for items in partitions
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "exact branch class is duplicated or noncanonical",
            )
        sets = tuple(set(items) for items in partitions)
        if (
            any(
                sets[left] & sets[right]
                for left in range(3)
                for right in range(left + 1, 3)
            )
            or set().union(*sets) != set(exact_ids)
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "exact branch classes are not a disjoint exhaustive union",
            )

    @property
    def exact_atom_ids(self) -> tuple[str, ...]:
        return tuple(
            atom_id
            for atom_id, _probability
            in self.exact_atom_probability_items
        )

    def probability_of(
        self,
        atom_ids: tuple[str, ...],
    ) -> Fraction:
        probabilities = dict(self.exact_atom_probability_items)
        return sum(
            (probabilities[atom_id] for atom_id in atom_ids),
            Fraction(0),
        )

    @property
    def environment_failure_probability(self) -> Fraction:
        return self.probability_of(self.environment_failure_atom_ids)

    @property
    def modeled_recurse_probability(self) -> Fraction:
        return self.probability_of(self.modeled_recurse_atom_ids)

    @property
    def policy_abort_probability(self) -> Fraction:
        return self.probability_of(self.policy_abort_atom_ids)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_total_lift_exact_branch_partition_witness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "root_ground_action": list(self.root_ground_action),
            "root_realization_weight": _fdoc(
                self.root_realization_weight
            ),
            "exact_root_row_id": self.exact_root_row_id,
            "exact_atom_probability_items": [
                {
                    "exact_atom_id": atom_id,
                    "probability": _fdoc(probability),
                }
                for atom_id, probability
                in self.exact_atom_probability_items
            ],
            "environment_failure_atom_ids": list(
                self.environment_failure_atom_ids
            ),
            "modeled_recurse_atom_ids": list(
                self.modeled_recurse_atom_ids
            ),
            "policy_abort_atom_ids": list(
                self.policy_abort_atom_ids
            ),
            "environment_failure_probability": _fdoc(
                self.environment_failure_probability
            ),
            "modeled_recurse_probability": _fdoc(
                self.modeled_recurse_probability
            ),
            "policy_abort_probability": _fdoc(
                self.policy_abort_probability
            ),
            "disjoint_exhaustive_partition": True,
        }

    @property
    def witness_id(self) -> str:
        return _hash("branch_partition", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


@dataclass(frozen=True, slots=True)
class V075PolicyAbortBranchWitnessV1:
    occurrence_id: str
    root_ground_action: tuple[int, int, int]
    root_realization_weight: Fraction
    exact_child_state_id: str
    exact_atom_ids: tuple[str, ...]
    conditional_branch_probability: Fraction
    branch_partition_witness_id: str
    global_other_destination_id: str

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "policy-abort occurrence")
        _action(self.root_ground_action, "policy-abort root action")
        weight = _fraction(
            self.root_realization_weight,
            "policy-abort root weight",
        )
        _cid(self.exact_child_state_id, "policy-abort exact child")
        _cid(
            self.branch_partition_witness_id,
            "policy-abort partition",
        )
        _cid(
            self.global_other_destination_id,
            "policy-abort global OTHER",
        )
        probability = _fraction(
            self.conditional_branch_probability,
            "policy-abort conditional probability",
        )
        if (
            not 0 < weight <= 1
            or not 0 < probability <= 1
            or type(self.exact_atom_ids) is not tuple
            or not self.exact_atom_ids
            or self.exact_atom_ids
            != tuple(sorted(set(self.exact_atom_ids)))
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "policy-abort branch witness is malformed",
            )
        for atom_id in self.exact_atom_ids:
            _cid(atom_id, "policy-abort exact atom")

    @property
    def marginal_failure_probability(self) -> Fraction:
        return (
            self.root_realization_weight
            * self.conditional_branch_probability
        )

    @property
    def continuation_reward(self) -> Fraction:
        return Fraction(0)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_total_lift_policy_abort_branch_witness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "root_ground_action": list(self.root_ground_action),
            "root_realization_weight": _fdoc(
                self.root_realization_weight
            ),
            "exact_child_state_id": self.exact_child_state_id,
            "exact_atom_ids": list(self.exact_atom_ids),
            "conditional_branch_probability": _fdoc(
                self.conditional_branch_probability
            ),
            "marginal_failure_probability": _fdoc(
                self.marginal_failure_probability
            ),
            "branch_partition_witness_id": (
                self.branch_partition_witness_id
            ),
            "global_other_destination_id": (
                self.global_other_destination_id
            ),
            "behavior": POLICY_ABORT_BEHAVIOR,
            "failure": _fdoc(Fraction(1)),
            "continuation_reward": _fdoc(Fraction(0)),
        }

    @property
    def witness_id(self) -> str:
        return _hash("policy_abort_branch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


@dataclass(frozen=True, slots=True)
class V075TotalLiftClosureCandidateV1:
    occurrence_id: str
    model_id: str
    policy_id: str
    envelope_id: str
    exact_replay_boundary_id: str
    selected_expected_reward: Fraction
    environment_failure_probability: Fraction
    policy_abort_failure_probability: Fraction
    selected_failure_probability: Fraction
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    exact_regret: Fraction | None
    exact_normalized_regret: Fraction | None
    branch_partitions: tuple[
        V075ExactBranchPartitionWitnessV1,
        ...,
    ]
    policy_abort_branches: tuple[
        V075PolicyAbortBranchWitnessV1,
        ...,
    ]

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "candidate occurrence"),
            (self.model_id, "candidate model"),
            (self.policy_id, "candidate policy"),
            (self.envelope_id, "candidate envelope"),
            (self.exact_replay_boundary_id, "candidate exact replay"),
        ):
            _cid(value, label)
        selected_reward = _fraction(
            self.selected_expected_reward,
            "candidate selected reward",
        )
        environment_failure = _fraction(
            self.environment_failure_probability,
            "candidate environment failure",
        )
        abort_failure = _fraction(
            self.policy_abort_failure_probability,
            "candidate policy-abort failure",
        )
        total_failure = _fraction(
            self.selected_failure_probability,
            "candidate selected failure",
        )
        if (
            selected_reward < 0
            or not 0 <= environment_failure <= 1
            or not 0 <= abort_failure <= 1
            or total_failure != environment_failure + abort_failure
            or not 0 <= total_failure <= 1
            or type(self.branch_partitions) is not tuple
            or any(
                type(item)
                is not V075ExactBranchPartitionWitnessV1
                for item in self.branch_partitions
            )
            or type(self.policy_abort_branches) is not tuple
            or any(
                type(item) is not V075PolicyAbortBranchWitnessV1
                for item in self.policy_abort_branches
            )
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.CANDIDATE_RECOMPUTATION_MISMATCH,
                "total-lift closure candidate is malformed",
            )
        optional = (
            self.optimal_expected_reward,
            self.optimal_failure_probability,
            self.exact_regret,
            self.exact_normalized_regret,
        )
        if all(value is None for value in optional):
            return
        if (
            any(type(value) is not Fraction for value in optional)
            or self.optimal_expected_reward is None
            or self.optimal_expected_reward < 0
            or self.optimal_failure_probability is None
            or not 0 <= self.optimal_failure_probability <= 1
            or self.exact_regret
            != self.optimal_expected_reward - selected_reward
            or self.exact_normalized_regret
            != self.exact_regret / public_authority.REWARD_CEILING
        ):
            _fail(
                V075TotalLiftProtocolCodeV1.CANDIDATE_RECOMPUTATION_MISMATCH,
                "candidate optimum or exact regret is stale",
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_closure_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "model_id": self.model_id,
            "policy_id": self.policy_id,
            "envelope_id": self.envelope_id,
            "exact_replay_boundary_id": (
                self.exact_replay_boundary_id
            ),
            "selected_expected_reward": _fdoc(
                self.selected_expected_reward
            ),
            "environment_failure_probability": _fdoc(
                self.environment_failure_probability
            ),
            "policy_abort_failure_probability": _fdoc(
                self.policy_abort_failure_probability
            ),
            "selected_failure_probability": _fdoc(
                self.selected_failure_probability
            ),
            "optimal_expected_reward": (
                None
                if self.optimal_expected_reward is None
                else _fdoc(self.optimal_expected_reward)
            ),
            "optimal_failure_probability": (
                None
                if self.optimal_failure_probability is None
                else _fdoc(self.optimal_failure_probability)
            ),
            "exact_regret": (
                None
                if self.exact_regret is None
                else _fdoc(self.exact_regret)
            ),
            "exact_normalized_regret": (
                None
                if self.exact_normalized_regret is None
                else _fdoc(self.exact_normalized_regret)
            ),
            "branch_partition_witness_ids": [
                item.witness_id for item in self.branch_partitions
            ],
            "policy_abort_branch_witness_ids": [
                item.witness_id
                for item in self.policy_abort_branches
            ],
            "missing_reachable_child_semantics": POLICY_ABORT_RULE,
        }

    @property
    def candidate_id(self) -> str:
        return _hash("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "branch_partitions": [
                item.to_document() for item in self.branch_partitions
            ],
            "policy_abort_branches": [
                item.to_document()
                for item in self.policy_abort_branches
            ],
            "candidate_id": self.candidate_id,
        }


class V075TotalLiftEndpointStatusV1(str, Enum):
    EXACT_POSITIVE_ENDPOINT = "EXACT_POSITIVE_ENDPOINT"
    EXACT_POLICY_RISK_FAILURE = "EXACT_POLICY_RISK_FAILURE"
    EXACT_POLICY_REGRET_FAILURE = "EXACT_POLICY_REGRET_FAILURE"
    EXACT_GROUND_QUERY_INFEASIBLE = "EXACT_GROUND_QUERY_INFEASIBLE"


@dataclass(frozen=True, slots=True)
class V075TotalLiftProtocolFailureV1:
    code: V075TotalLiftProtocolCodeV1
    diagnostic_digest: str

    def __post_init__(self) -> None:
        if type(self.code) is not V075TotalLiftProtocolCodeV1:
            raise TypeError("protocol failure code is not typed")
        _cid(self.diagnostic_digest, "protocol diagnostic digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_protocol_failure.v1",
            "schema_version": SCHEMA_VERSION,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            "protocol_code": self.code.value,
            "diagnostic_digest": self.diagnostic_digest,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def failure_id(self) -> str:
        return _hash("protocol_failure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "failure_id": self.failure_id}


@dataclass(frozen=True, slots=True)
class V075TotalLiftStatisticalEnvelopeMissV1:
    candidate: V075TotalLiftClosureCandidateV1
    miss_axes: tuple[str, ...]

    def __post_init__(self) -> None:
        allowed = (
            "NORMALIZED_REGRET_UPPER",
            "SELECTED_FAILURE_UPPER",
            "SELECTED_REWARD_LOWER",
            "UNRESTRICTED_REWARD_UPPER",
        )
        if (
            type(self.candidate) is not V075TotalLiftClosureCandidateV1
            or type(self.miss_axes) is not tuple
            or not self.miss_axes
            or self.miss_axes != tuple(sorted(set(self.miss_axes)))
            or any(item not in allowed for item in self.miss_axes)
        ):
            raise TypeError("statistical envelope miss is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_total_lift_statistical_envelope_miss.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate.candidate_id,
            "miss_axes": list(self.miss_axes),
            "classification": "STATISTICAL_ENVELOPE_MISS",
            "protocol_failure": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def miss_id(self) -> str:
        return _hash("envelope_miss", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "miss_id": self.miss_id}


@dataclass(frozen=True, slots=True)
class V075TotalLiftEndpointV1:
    candidate: V075TotalLiftClosureCandidateV1
    status: V075TotalLiftEndpointStatusV1

    def __post_init__(self) -> None:
        if (
            type(self.candidate) is not V075TotalLiftClosureCandidateV1
            or type(self.status) is not V075TotalLiftEndpointStatusV1
        ):
            raise TypeError("total-lift endpoint is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_total_lift_exact_endpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate.candidate_id,
            "status": self.status.value,
            "operational_envelope_containment": True,
            "protocol_failure": False,
            "exact_fraction_arithmetic": True,
        }

    @property
    def endpoint_id(self) -> str:
        return _hash("endpoint", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "endpoint_id": self.endpoint_id}


V075TotalLiftVerificationOutcomeV1 = (
    V075TotalLiftEndpointV1
    | V075TotalLiftStatisticalEnvelopeMissV1
    | V075TotalLiftProtocolFailureV1
)


def _protocol_failure(
    violation: V075TotalLiftProtocolViolation,
) -> V075TotalLiftProtocolFailureV1:
    digest = hashlib.sha256(
        b"acfqp:v075-total-lift-protocol-diagnostic:v1"
        + b"\x00"
        + violation.code.value.encode("utf-8")
        + b"\x00"
        + str(violation).encode("utf-8")
    ).hexdigest()
    return V075TotalLiftProtocolFailureV1(
        violation.code,
        digest,
    )


def _boundary_rows(
    boundary: V075IndependentExactReplayBoundaryV1,
) -> dict[
    tuple[str, int, tuple[int, int, int]],
    V075ExactReplayRowV1,
]:
    return {
        _row_key(item.row_binding): item
        for item in boundary.rows
    }


def _row_for(
    rows: Mapping[
        tuple[str, int, tuple[int, int, int]],
        V075ExactReplayRowV1,
    ],
    catalogue: public_graph.V075LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> V075ExactReplayRowV1:
    row = rows.get(
        (
            catalogue.state.state_id,
            catalogue.remaining_horizon,
            action,
        )
    )
    if row is None or row.row_binding.catalogue != catalogue:
        _fail(
            V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
            "exact replay row lookup failed",
        )
    return row


def _active_probability_by_state(
    row: V075ExactReplayRowV1,
) -> dict[str, tuple[public_graph.V075SymbolicGraphStateV1, Fraction]]:
    result: dict[
        str,
        tuple[public_graph.V075SymbolicGraphStateV1, Fraction],
    ] = {}
    for exact_atom in row.atoms:
        atom = exact_atom.atom
        if atom.failure:
            continue
        if atom.terminal:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_REPLAY_INCOMPLETE,
                "selected H=2 root row has terminal success mass",
            )
        state = exact_atom.next_state
        previous = result.get(state.state_id)
        result[state.state_id] = (
            state,
            atom.probability
            + (Fraction(0) if previous is None else previous[1]),
        )
    return result


def _pareto(
    points: Iterable[tuple[Fraction, Fraction]],
) -> tuple[tuple[Fraction, Fraction], ...]:
    unique = tuple(sorted(set(points), key=lambda item: (item[1], -item[0])))
    retained = tuple(
        point
        for point in unique
        if not any(
            (
                other[0] >= point[0]
                and other[1] <= point[1]
                and other != point
            )
            for other in unique
        )
    )
    return tuple(sorted(retained, key=lambda item: (item[1], -item[0])))


def _exact_ground_optimum(
    *,
    occurrence: V075LawFreePlannerOccurrenceV1,
    rows: Mapping[
        tuple[str, int, tuple[int, int, int]],
        V075ExactReplayRowV1,
    ],
) -> tuple[Fraction, Fraction] | None:
    root_catalogue = public_graph.root_catalogue_v1(occurrence.context)
    candidates: list[tuple[Fraction, Fraction]] = []
    for root_action in root_catalogue.actions:
        root_row = _row_for(rows, root_catalogue, root_action)
        frontier = (
            (
                root_row.reward,
                root_row.failure_probability,
            ),
        )
        active = _active_probability_by_state(root_row)
        for state_id in sorted(active):
            state, branch_probability = active[state_id]
            catalogue = _child_catalogue(state)
            options = tuple(
                (
                    branch_probability
                    * _row_for(rows, catalogue, action).reward,
                    branch_probability
                    * _row_for(
                        rows,
                        catalogue,
                        action,
                    ).failure_probability,
                )
                for action in catalogue.actions
            )
            frontier = _pareto(
                (
                    reward + option_reward,
                    failure + option_failure,
                )
                for reward, failure in frontier
                for option_reward, option_failure in options
            )
        candidates.extend(frontier)
    feasible = tuple(
        point
        for point in candidates
        if point[1] <= public_authority.RISK_TOLERANCE
    )
    if not feasible:
        return None
    return max(feasible, key=lambda item: (item[0], -item[1]))


def _derive_total_lift_candidate(
    *,
    envelope: V075OperationalEnvelopeV1,
    exact_replay: V075IndependentExactReplayBoundaryV1,
) -> V075TotalLiftClosureCandidateV1:
    if (
        type(envelope) is not V075OperationalEnvelopeV1
        or type(exact_replay)
        is not V075IndependentExactReplayBoundaryV1
    ):
        _fail(
            V075TotalLiftProtocolCodeV1.INPUT_TYPE_MISMATCH,
            "total lift requires exact operational and replay authority types",
        )
    policy = envelope.policy
    model = policy.model
    occurrence = model.occurrence
    if exact_replay.occurrence != occurrence:
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            "exact replay occurrence was transplanted",
        )
    if exact_replay.bound_envelope_id is not None and (
        exact_replay.bound_model_id != model.model_id
        or exact_replay.bound_policy_id != policy.policy_id
        or exact_replay.bound_envelope_id != envelope.envelope_id
    ):
        _fail(
            V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
            "verified exact replay boundary was transplanted across its "
            "model, policy, or operational envelope",
        )
    rows = _boundary_rows(exact_replay)
    support_by_action = {
        item.root_action: item
        for item in model.selected_root_supports
    }
    selected_actions = policy.root_decision.ground_actions
    if not set(selected_actions) <= set(support_by_action):
        _fail(
            V075TotalLiftProtocolCodeV1.SELECTED_ROOT_SUPPORT_INCOMPLETE,
            "selected root concretizer lacks one row-specific support",
        )
    child_decision_by_state = {
        item.catalogue.state.state_id: item
        for item in policy.child_decisions
    }
    root_catalogue = model.root_catalogue
    selected_reward = Fraction(0)
    environment_failure = Fraction(0)
    policy_abort_failure = Fraction(0)
    partitions: list[V075ExactBranchPartitionWitnessV1] = []
    abort_branches: list[V075PolicyAbortBranchWitnessV1] = []
    for root_action, root_weight in zip(
        policy.root_decision.ground_actions,
        policy.root_decision.uniform_weights,
        strict=True,
    ):
        root_row = _row_for(rows, root_catalogue, root_action)
        support = support_by_action[root_action]
        modeled_catalogue_by_state = {
            item.state.state_id: item
            for item in support.modeled_children
        }
        active = _active_probability_by_state(root_row)
        if not set(modeled_catalogue_by_state) <= set(active):
            _fail(
                V075TotalLiftProtocolCodeV1.MODELED_SUPPORT_NOT_EXACT_POSITIVE,
                "modeled selected child is absent from exact positive mass",
            )
        missing_decisions = (
            set(modeled_catalogue_by_state)
            - set(child_decision_by_state)
        )
        if missing_decisions:
            _fail(
                V075TotalLiftProtocolCodeV1.MODELED_CHILD_DECISION_MISSING,
                "modeled selected child lacks its bound policy decision",
            )
        selected_reward += root_weight * root_row.reward
        environment_ids: list[str] = []
        modeled_ids: list[str] = []
        abort_ids: list[str] = []
        abort_ids_by_state: dict[str, list[str]] = {}
        for exact_atom in root_row.atoms:
            if exact_atom.atom.failure:
                environment_ids.append(exact_atom.atom_id)
                environment_failure += (
                    root_weight * exact_atom.atom.probability
                )
            elif exact_atom.next_state_id in modeled_catalogue_by_state:
                modeled_ids.append(exact_atom.atom_id)
            else:
                abort_ids.append(exact_atom.atom_id)
                abort_ids_by_state.setdefault(
                    exact_atom.next_state_id,
                    [],
                ).append(exact_atom.atom_id)
                policy_abort_failure += (
                    root_weight * exact_atom.atom.probability
                )
        partition = V075ExactBranchPartitionWitnessV1(
            occurrence.occurrence_id,
            root_action,
            root_weight,
            root_row.row_id,
            tuple(
                (
                    item.atom_id,
                    item.atom.probability,
                )
                for item in root_row.atoms
            ),
            tuple(sorted(environment_ids)),
            tuple(sorted(modeled_ids)),
            tuple(sorted(abort_ids)),
        )
        partitions.append(partition)
        probability_by_atom = dict(
            partition.exact_atom_probability_items
        )
        for state_id in sorted(abort_ids_by_state):
            atom_ids = tuple(sorted(abort_ids_by_state[state_id]))
            abort_branches.append(
                V075PolicyAbortBranchWitnessV1(
                    occurrence.occurrence_id,
                    root_action,
                    root_weight,
                    state_id,
                    atom_ids,
                    sum(
                        (
                            probability_by_atom[atom_id]
                            for atom_id in atom_ids
                        ),
                        Fraction(0),
                    ),
                    partition.witness_id,
                    model.global_other_destination_id,
                )
            )
        for state_id in sorted(modeled_catalogue_by_state):
            catalogue = modeled_catalogue_by_state[state_id]
            exact_state, branch_probability = active[state_id]
            if catalogue != _child_catalogue(exact_state):
                _fail(
                    V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                    "modeled child catalogue is stale",
                )
            decision = child_decision_by_state[state_id]
            if decision.catalogue != catalogue:
                _fail(
                    V075TotalLiftProtocolCodeV1.BINDING_MISMATCH,
                    "modeled child decision was transplanted",
                )
            for child_action, action_weight in zip(
                decision.ground_actions,
                decision.uniform_weights,
                strict=True,
            ):
                child_row = _row_for(
                    rows,
                    catalogue,
                    child_action,
                )
                mass = root_weight * branch_probability * action_weight
                selected_reward += mass * child_row.reward
                environment_failure += (
                    mass * child_row.failure_probability
                )
    partitions_tuple = tuple(
        sorted(
            partitions,
            key=lambda item: item.root_ground_action,
        )
    )
    abort_tuple = tuple(
        sorted(
            abort_branches,
            key=lambda item: (
                item.root_ground_action,
                item.exact_child_state_id,
            ),
        )
    )
    if (
        sum(
            (
                item.marginal_failure_probability
                for item in abort_tuple
            ),
            Fraction(0),
        )
        != policy_abort_failure
        or {
            atom_id
            for item in abort_tuple
            for atom_id in item.exact_atom_ids
        }
        != {
            atom_id
            for item in partitions_tuple
            for atom_id in item.policy_abort_atom_ids
        }
    ):
        _fail(
            V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
            "policy-abort witnesses do not cover the exact abort partition",
        )
    selected_failure = environment_failure + policy_abort_failure
    optimum = _exact_ground_optimum(
        occurrence=occurrence,
        rows=rows,
    )
    if optimum is None:
        optimal_reward = None
        optimal_failure = None
        regret = None
        normalized_regret = None
    else:
        optimal_reward, optimal_failure = optimum
        regret = optimal_reward - selected_reward
        normalized_regret = regret / public_authority.REWARD_CEILING
    return V075TotalLiftClosureCandidateV1(
        occurrence.occurrence_id,
        model.model_id,
        policy.policy_id,
        envelope.envelope_id,
        exact_replay.boundary_id,
        selected_reward,
        environment_failure,
        policy_abort_failure,
        selected_failure,
        optimal_reward,
        optimal_failure,
        regret,
        normalized_regret,
        partitions_tuple,
        abort_tuple,
    )


def _classify_verified_candidate(
    *,
    envelope: V075OperationalEnvelopeV1,
    candidate: V075TotalLiftClosureCandidateV1,
) -> (
    V075TotalLiftEndpointV1
    | V075TotalLiftStatisticalEnvelopeMissV1
):
    misses: list[str] = []
    if (
        candidate.selected_expected_reward
        < envelope.selected_reward_lower
    ):
        misses.append("SELECTED_REWARD_LOWER")
    if (
        candidate.selected_expected_reward
        > envelope.unrestricted_reward_upper
    ):
        misses.append("UNRESTRICTED_REWARD_UPPER")
    if (
        candidate.selected_failure_probability
        > envelope.selected_failure_upper
    ):
        misses.append("SELECTED_FAILURE_UPPER")
    if (
        candidate.exact_normalized_regret is not None
        and candidate.exact_normalized_regret
        > envelope.normalized_regret_upper
    ):
        misses.append("NORMALIZED_REGRET_UPPER")
    if misses:
        return V075TotalLiftStatisticalEnvelopeMissV1(
            candidate,
            tuple(sorted(misses)),
        )
    if candidate.optimal_expected_reward is None:
        status = (
            V075TotalLiftEndpointStatusV1.EXACT_GROUND_QUERY_INFEASIBLE
        )
    elif (
        candidate.selected_failure_probability
        > public_authority.RISK_TOLERANCE
    ):
        status = V075TotalLiftEndpointStatusV1.EXACT_POLICY_RISK_FAILURE
    elif (
        candidate.exact_normalized_regret is None
        or candidate.exact_normalized_regret
        > public_authority.NORMALIZED_REGRET_TOLERANCE
    ):
        status = V075TotalLiftEndpointStatusV1.EXACT_POLICY_REGRET_FAILURE
    else:
        status = V075TotalLiftEndpointStatusV1.EXACT_POSITIVE_ENDPOINT
    return V075TotalLiftEndpointV1(candidate, status)


def evaluate_total_lift_v1(
    *,
    envelope: V075OperationalEnvelopeV1,
    exact_replay: V075IndependentExactReplayBoundaryV1,
) -> V075TotalLiftVerificationOutcomeV1:
    """Recompute and classify one total lifted policy exactly."""

    try:
        candidate = _derive_total_lift_candidate(
            envelope=envelope,
            exact_replay=exact_replay,
        )
    except V075TotalLiftProtocolViolation as violation:
        return _protocol_failure(violation)
    return _classify_verified_candidate(
        envelope=envelope,
        candidate=candidate,
    )


def verify_total_lift_candidate_v1(
    *,
    envelope: V075OperationalEnvelopeV1,
    exact_replay: V075IndependentExactReplayBoundaryV1,
    candidate: V075TotalLiftClosureCandidateV1,
) -> V075TotalLiftVerificationOutcomeV1:
    """Independently recompute a serialized candidate before classification."""

    if (
        type(envelope) is not V075OperationalEnvelopeV1
        or type(exact_replay)
        is not V075IndependentExactReplayBoundaryV1
        or type(candidate) is not V075TotalLiftClosureCandidateV1
    ):
        return _protocol_failure(
            V075TotalLiftProtocolViolation(
                V075TotalLiftProtocolCodeV1.INPUT_TYPE_MISMATCH,
                "candidate verifier rejects duck-typed inputs",
            )
        )
    try:
        expected = _derive_total_lift_candidate(
            envelope=envelope,
            exact_replay=exact_replay,
        )
        if candidate.branch_partitions != expected.branch_partitions:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "candidate branch witnesses are omitted, duplicated, or stale",
            )
        if candidate.policy_abort_branches != expected.policy_abort_branches:
            _fail(
                V075TotalLiftProtocolCodeV1.EXACT_BRANCH_PARTITION_INVALID,
                "candidate policy-abort witnesses are incomplete or stale",
            )
        if candidate != expected:
            _fail(
                V075TotalLiftProtocolCodeV1.CANDIDATE_RECOMPUTATION_MISMATCH,
                "candidate metrics or authority bindings do not replay",
            )
    except V075TotalLiftProtocolViolation as violation:
        return _protocol_failure(violation)
    return _classify_verified_candidate(
        envelope=envelope,
        candidate=expected,
    )


__all__ = [
    "DOMAIN_TAGS",
    "INDEPENDENT_EXACT_REPLAY_LANE",
    "POLICY_ABORT_BEHAVIOR",
    "POLICY_ABORT_RULE",
    "PRODUCTION_EXACT_REPLAY_MINT_IMPLEMENTED",
    "PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075ExactBranchPartitionWitnessV1",
    "V075ExactReplayMintFailureClassV1",
    "V075ExactReplayMintFailureCodeV1",
    "V075ExactReplayMintVerificationV1",
    "V075ExactReplayMintViolation",
    "V075ExactReplayAtomV1",
    "V075ExactReplayRowV1",
    "V075ExactReplayScopeV1",
    "V075FixedConcretizerDecisionV1",
    "V075IndependentExactReplayBoundaryV1",
    "V075LawFreePartialModelBindingV1",
    "V075LawFreePlannerOccurrenceV1",
    "V075ObservedRowBindingV1",
    "V075ObservedSemanticActionV1",
    "V075OperationalEnvelopeV1",
    "V075PolicyAbortBranchWitnessV1",
    "V075RouteKindV1",
    "V075SelectedPolicyBindingV1",
    "V075SelectedRootSupportV1",
    "V075TotalLiftClosureCandidateV1",
    "V075TotalLiftEndpointStatusV1",
    "V075TotalLiftEndpointV1",
    "V075TotalLiftProtocolCodeV1",
    "V075TotalLiftProtocolFailureV1",
    "V075TotalLiftProtocolViolation",
    "V075TotalLiftStatisticalEnvelopeMissV1",
    "V075TotalLiftVerificationOutcomeV1",
    "V075VerifiedExactReplayMintV1",
    "evaluate_total_lift_v1",
    "mint_construction_exact_replay_boundary_v1",
    "verify_and_mint_construction_exact_replay_from_journal_v1",
    "verify_and_mint_production_exact_replay_boundary_v1",
    "verify_total_lift_candidate_v1",
]
