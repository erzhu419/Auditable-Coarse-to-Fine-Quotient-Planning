"""Public-only held-out graph adapter for the V0-072 cold H=2 closure.

The adapter consumes exactly one of the three clean registered public graph
contexts.  It maps public symbolic states and complete public legal-action
catalogues into ``ColdPublicStateV1`` and ``ColdPublicActionV1`` without
consulting a hidden law, transition kernel, target tape, support epoch, or
observation authority.

The semantic state ID reuses the observer's public symbolic-state ID.  The
semantic action ID reuses the observer's public physical row-binding ID,
which content-binds the context, public catalogue, public state, remaining
horizon, and action triple.  No caller-supplied ID or action mapping enters
either identity.

There is no final preregistration or target-execution anchor in this
revision.  Row, outcome, and observation adaptation entry points therefore
fail closed and cannot generate a draw or transition descriptor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_heldout_public_graph_adapter_v1"
CAP_SEMANTICS = "COMPLETE_COLD_H2_TOTAL_PHYSICAL_STATE_ACTION_ROWS"
CAP_AUTHORITY_CLASS = "CONFIRMATORY_REGISTERED_PUBLIC_ONLY"
PREREGISTRATION_BINDING_KIND = "NOT_FINALIZED_PUBLIC_ONLY"
TARGET_EXECUTION_ALLOWED = False

EXPECTED_CONTEXT_TOTAL_ROW_CAPS = (
    ("heldout_graph_k7_confirmatory_v1", 96),
    ("heldout_graph_w7_confirmatory_v1", 48),
    ("heldout_graph_k7_minus_two_confirmatory_v1", 96),
)

DOMAIN_TAGS = {
    "cap_key": (
        "acfqp:v072-heldout-public-context-total-row-cap-key:v1"
    ),
    "cap_binding": (
        "acfqp:v072-heldout-public-total-row-cap-binding:v1"
    ),
    "adapter": "acfqp:v072-heldout-public-graph-cold-adapter:v1",
}


class V072HeldoutPublicGraphAdapterInvariantViolation(ValueError):
    """A public context, state, action, cap, or lock invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        canonical = parse_content_id(value)
    except ValueError as error:
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error
    if canonical in prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS:
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            f"{field_name} is a retired development identity"
        )
    return canonical


def _registered_context(
    context: Any,
) -> prereg.HeldoutPublicGraphContextV2:
    registered = prereg.registered_heldout_public_contexts_v2()
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or type(context.topology) is not GraphTopologyV1
        or context not in registered
        or context.context_id
        in prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS
    ):
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "adapter requires one exact clean registered public context"
        )
    caps = tuple(
        (
            item.context_key,
            item.maximum_physical_rows_per_confidence_epoch,
        )
        for item in registered
    )
    if caps != EXPECTED_CONTEXT_TOTAL_ROW_CAPS:
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "registered public context total-row caps changed"
        )
    return context


def _remaining_horizon(value: Any) -> int:
    if type(value) is not int or value not in (1, prereg.HORIZON):
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "remaining horizon is outside the registered H=2 query"
        )
    return value


def _public_state(
    context: prereg.HeldoutPublicGraphContextV2,
    state: Any,
) -> observer.HeldoutSymbolicGraphStateV2:
    if (
        type(state) is not observer.HeldoutSymbolicGraphStateV2
        or type(state.ranks) is not tuple
        or len(state.ranks) != context.topology.vertex_count
        or any(
            type(rank) is not int
            or not 0 <= rank <= context.rank_cap
            for rank in state.ranks
        )
        or type(state.failure) is not bool
    ):
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "public state is not one exact registered symbolic-state type"
        )
    actions = _legal_action_triples(context, state.ranks, state.failure)
    if state.failure != (not actions):
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "public state failure flag disagrees with public legal actions"
        )
    _cid(state.state_id, "public symbolic state")
    return state


def _legal_action_triples(
    context: prereg.HeldoutPublicGraphContextV2,
    ranks: tuple[int, ...],
    failure: bool,
) -> tuple[tuple[int, int, int], ...]:
    if failure:
        return ()
    return tuple(
        sorted(
            (first, second, survivor)
            for first, second in context.topology.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )


def _observer_catalogue(
    context: prereg.HeldoutPublicGraphContextV2,
    state: observer.HeldoutSymbolicGraphStateV2,
    remaining_horizon: int,
) -> observer.HeldoutLegalActionCatalogueV2:
    canonical_state = _public_state(context, state)
    horizon = _remaining_horizon(remaining_horizon)
    catalogue = observer.HeldoutLegalActionCatalogueV2(
        context.context_id,
        canonical_state,
        horizon,
        _legal_action_triples(
            context,
            canonical_state.ranks,
            canonical_state.failure,
        ),
    )
    _cid(catalogue.catalogue_id, "public legal-action catalogue")
    return catalogue


def _cap_key_payload(
    context: prereg.HeldoutPublicGraphContextV2,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_heldout_public_context_total_row_cap_key.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "context_id": context.context_id,
        "context_key": context.context_key,
        "cap_semantics": CAP_SEMANTICS,
    }


def _context_specific_total_row_cap_key(
    context: prereg.HeldoutPublicGraphContextV2,
) -> str:
    return _content_id("cap_key", _cap_key_payload(context))


@dataclass(frozen=True, slots=True)
class HeldoutPublicTotalRowCapBindingV1:
    context_id: str
    context_key: str
    total_physical_row_cap: int
    context_specific_total_row_cap_key: str
    confirmatory_family_generation: str = (
        prereg.CONFIRMATORY_FAMILY_GENERATION
    )
    authority_class: str = CAP_AUTHORITY_CLASS
    preregistration_binding: Mapping[str, Any] = field(
        default_factory=lambda: {
            "kind": PREREGISTRATION_BINDING_KIND,
            "final_preregistration_id": None,
        }
    )
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        context = next(
            (
                item
                for item in prereg.registered_heldout_public_contexts_v2()
                if item.context_key == self.context_key
            ),
            None,
        )
        expected_preregistration_binding = {
            "kind": PREREGISTRATION_BINDING_KIND,
            "final_preregistration_id": None,
        }
        if (
            type(context) is not prereg.HeldoutPublicGraphContextV2
            or self.context_id != context.context_id
            or type(self.total_physical_row_cap) is not int
            or self.total_physical_row_cap
            != context.maximum_physical_rows_per_confidence_epoch
            or _cid(
                self.context_specific_total_row_cap_key,
                "context-specific total-row cap key",
            )
            != _context_specific_total_row_cap_key(context)
            or self.confirmatory_family_generation
            != prereg.CONFIRMATORY_FAMILY_GENERATION
            or self.authority_class != CAP_AUTHORITY_CLASS
            or type(self.preregistration_binding) is not dict
            or self.preregistration_binding
            != expected_preregistration_binding
            or self.target_execution_allowed is not False
        ):
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "held-out public total-row cap binding changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_heldout_public_total_row_cap_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "confirmatory_family_generation": (
                self.confirmatory_family_generation
            ),
            "authority_class": self.authority_class,
            "context_id": self.context_id,
            "context_key": self.context_key,
            "context_specific_total_row_cap_key": (
                self.context_specific_total_row_cap_key
            ),
            "total_physical_row_cap": self.total_physical_row_cap,
            "preregistration_binding": dict(
                self.preregistration_binding
            ),
            "target_execution_allowed": False,
        }

    @property
    def total_row_cap_binding_id(self) -> str:
        return _content_id("cap_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "total_row_cap_binding_id": self.total_row_cap_binding_id,
        }


def registered_heldout_public_total_row_cap_binding_v1(
    context: prereg.HeldoutPublicGraphContextV2,
) -> HeldoutPublicTotalRowCapBindingV1:
    registered = _registered_context(context)
    return HeldoutPublicTotalRowCapBindingV1(
        registered.context_id,
        registered.context_key,
        registered.maximum_physical_rows_per_confidence_epoch,
        _context_specific_total_row_cap_key(registered),
    )


def _cold_state_document(
    context: prereg.HeldoutPublicGraphContextV2,
    state: observer.HeldoutSymbolicGraphStateV2,
    remaining_horizon: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_heldout_public_cold_state_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "context_id": context.context_id,
        "context_key": context.context_key,
        "topology_id": context.topology.topology_id,
        "public_state_id": state.state_id,
        "ranks": list(state.ranks),
        "failure": state.failure,
        "remaining_horizon": remaining_horizon,
        "semantic_state_id_reuses_public_state_id": True,
        "hidden_law_serialized": False,
        "outcome_serialized": False,
    }


def _cold_state(
    context: prereg.HeldoutPublicGraphContextV2,
    state: observer.HeldoutSymbolicGraphStateV2,
    remaining_horizon: int,
) -> cold.ColdPublicStateV1:
    canonical_state = _public_state(context, state)
    horizon = _remaining_horizon(remaining_horizon)
    return cold.ColdPublicStateV1(
        canonical_state.state_id,
        _cold_state_document(
            context,
            canonical_state,
            horizon,
        ),
    )


def _cold_action_document(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: observer.HeldoutLegalActionCatalogueV2,
    row_binding: observer.HeldoutObservationRowBindingV2,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_heldout_public_cold_action_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "context_id": context.context_id,
        "context_key": context.context_key,
        "topology_id": context.topology.topology_id,
        "public_state_id": catalogue.state.state_id,
        "public_catalogue_id": catalogue.catalogue_id,
        "public_row_binding_id": row_binding.row_binding_id,
        "remaining_horizon": catalogue.remaining_horizon,
        "action": list(row_binding.action),
        "semantic_action_id_reuses_public_row_binding_id": True,
        "hidden_law_serialized": False,
        "outcome_serialized": False,
    }


def _cold_action(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: observer.HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
) -> cold.ColdPublicActionV1:
    if action not in catalogue.actions:
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "public action is outside the complete legal catalogue"
        )
    row_binding = observer.HeldoutObservationRowBindingV2(
        context.context_id,
        catalogue.catalogue_id,
        catalogue.state.state_id,
        catalogue.remaining_horizon,
        action,
    )
    _cid(row_binding.row_binding_id, "public row binding")
    return cold.ColdPublicActionV1(
        row_binding.row_binding_id,
        _cold_action_document(context, catalogue, row_binding),
    )


def _cold_actions(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: observer.HeldoutLegalActionCatalogueV2,
) -> tuple[cold.ColdPublicActionV1, ...]:
    actions = tuple(
        _cold_action(context, catalogue, action)
        for action in catalogue.actions
    )
    return tuple(
        sorted(actions, key=lambda item: item.action_record_id)
    )


def _adapter_payload(
    *,
    context: prereg.HeldoutPublicGraphContextV2,
    cap_binding: HeldoutPublicTotalRowCapBindingV1,
    public_root_state: observer.HeldoutSymbolicGraphStateV2,
    public_root_catalogue: observer.HeldoutLegalActionCatalogueV2,
    root_state: cold.ColdPublicStateV1,
    root_actions: tuple[cold.ColdPublicActionV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_heldout_public_graph_adapter.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "context_id": context.context_id,
        "context_key": context.context_key,
        "topology_id": context.topology.topology_id,
        "horizon": context.horizon,
        "public_root_state_id": public_root_state.state_id,
        "public_root_catalogue_id": public_root_catalogue.catalogue_id,
        "root_state_record_id": root_state.state_record_id,
        "root_action_record_ids": [
            item.action_record_id for item in root_actions
        ],
        "total_row_cap_binding_id": (
            cap_binding.total_row_cap_binding_id
        ),
        "context_specific_total_row_cap_key": (
            cap_binding.context_specific_total_row_cap_key
        ),
        "context_specific_total_row_cap": (
            cap_binding.total_physical_row_cap
        ),
        "public_only": True,
        "hidden_law_queries": 0,
        "kernel_calls": 0,
        "outcome_enumeration_calls": 0,
        "registered_observations_generated": 0,
        "final_preregistration_id": None,
        "target_execution_anchor_id": None,
        "target_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True, init=False)
class HeldoutPublicGraphColdClosureAdapterV1:
    """Exact registered public semantics implementing the cold protocol."""

    context: prereg.HeldoutPublicGraphContextV2
    total_row_cap_binding_v1: HeldoutPublicTotalRowCapBindingV1
    public_root_state: observer.HeldoutSymbolicGraphStateV2
    public_root_catalogue: observer.HeldoutLegalActionCatalogueV2
    root_state: cold.ColdPublicStateV1
    root_actions: tuple[cold.ColdPublicActionV1, ...]
    _adapter_id: str = field(repr=False)

    def __init__(
        self,
        context: prereg.HeldoutPublicGraphContextV2,
    ) -> None:
        registered = _registered_context(context)
        public_root_state = observer.HeldoutSymbolicGraphStateV2(
            registered.root_ranks,
            False,
        )
        public_root_catalogue = _observer_catalogue(
            registered,
            public_root_state,
            registered.horizon,
        )
        root_state = _cold_state(
            registered,
            public_root_state,
            registered.horizon,
        )
        root_actions = _cold_actions(
            registered,
            public_root_catalogue,
        )
        cap_binding = (
            registered_heldout_public_total_row_cap_binding_v1(
                registered
            )
        )
        payload = _adapter_payload(
            context=registered,
            cap_binding=cap_binding,
            public_root_state=public_root_state,
            public_root_catalogue=public_root_catalogue,
            root_state=root_state,
            root_actions=root_actions,
        )
        object.__setattr__(self, "context", registered)
        object.__setattr__(
            self,
            "total_row_cap_binding_v1",
            cap_binding,
        )
        object.__setattr__(
            self,
            "public_root_state",
            public_root_state,
        )
        object.__setattr__(
            self,
            "public_root_catalogue",
            public_root_catalogue,
        )
        object.__setattr__(self, "root_state", root_state)
        object.__setattr__(self, "root_actions", root_actions)
        object.__setattr__(
            self,
            "_adapter_id",
            _content_id("adapter", payload),
        )

    @property
    def context_id(self) -> str:
        return self.context.context_id

    @property
    def horizon(self) -> int:
        return self.context.horizon

    @property
    def context_specific_total_row_cap_key(self) -> str:
        return (
            self.total_row_cap_binding_v1
            .context_specific_total_row_cap_key
        )

    @property
    def context_specific_total_row_cap(self) -> int:
        return self.total_row_cap_binding_v1.total_physical_row_cap

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    def root_state_v1(self) -> cold.ColdPublicStateV1:
        return self.root_state

    def root_catalogue_v1(self) -> cold.ColdPublicCatalogueV1:
        return cold.ColdPublicCatalogueV1(
            self.context_id,
            self.root_state,
            self.horizon,
            self.root_actions,
        )

    def adapt_public_state_v1(
        self,
        state: observer.HeldoutSymbolicGraphStateV2,
        remaining_horizon: int,
    ) -> cold.ColdPublicStateV1:
        return _cold_state(
            self.context,
            state,
            remaining_horizon,
        )

    def canonical_state_v1(
        self,
        state: cold.ColdPublicStateV1,
    ) -> cold.ColdPublicStateV1:
        if type(state) is not cold.ColdPublicStateV1:
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "canonicalization requires one exact cold public state"
            )
        document = dict(state.document)
        expected_keys = {
            "schema",
            "schema_version",
            "context_id",
            "context_key",
            "topology_id",
            "public_state_id",
            "ranks",
            "failure",
            "remaining_horizon",
            "semantic_state_id_reuses_public_state_id",
            "hidden_law_serialized",
            "outcome_serialized",
        }
        if (
            set(document) != expected_keys
            or document["schema"]
            != "acfqp.v072_heldout_public_cold_state_binding.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or document["context_id"] != self.context_id
            or document["context_key"] != self.context.context_key
            or document["topology_id"]
            != self.context.topology.topology_id
            or type(document["ranks"]) is not list
            or len(document["ranks"])
            != self.context.topology.vertex_count
            or any(
                type(rank) is not int
                or not 0 <= rank <= self.context.rank_cap
                for rank in document["ranks"]
            )
            or type(document["failure"]) is not bool
            or document["semantic_state_id_reuses_public_state_id"]
            is not True
            or document["hidden_law_serialized"] is not False
            or document["outcome_serialized"] is not False
        ):
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "cold public state document is foreign or noncanonical"
            )
        public_state = observer.HeldoutSymbolicGraphStateV2(
            tuple(document["ranks"]),
            document["failure"],
        )
        expected = _cold_state(
            self.context,
            public_state,
            _remaining_horizon(document["remaining_horizon"]),
        )
        if (
            state.semantic_state_id != document["public_state_id"]
            or state.to_document() != expected.to_document()
        ):
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "cold public state identity is caller-supplied or stale"
            )
        return expected

    def legal_actions_v1(
        self,
        state: cold.ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[cold.ColdPublicActionV1, ...]:
        canonical = self.canonical_state_v1(state)
        horizon = _remaining_horizon(remaining_horizon)
        document = dict(canonical.document)
        if document["remaining_horizon"] != horizon:
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "cold state and legal-action horizon disagree"
            )
        public_state = observer.HeldoutSymbolicGraphStateV2(
            tuple(document["ranks"]),
            document["failure"],
        )
        catalogue = _observer_catalogue(
            self.context,
            public_state,
            horizon,
        )
        return _cold_actions(self.context, catalogue)

    def adapt_public_legal_action_catalogue_v1(
        self,
        catalogue: observer.HeldoutLegalActionCatalogueV2,
    ) -> cold.ColdPublicCatalogueV1:
        if (
            type(catalogue)
            is not observer.HeldoutLegalActionCatalogueV2
            or catalogue.context_id != self.context_id
        ):
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "catalogue is not an exact public catalogue for this context"
            )
        expected = _observer_catalogue(
            self.context,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        if catalogue.to_document() != expected.to_document():
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "public catalogue omits, adds, or reorders a legal action"
            )
        state = _cold_state(
            self.context,
            expected.state,
            expected.remaining_horizon,
        )
        actions = _cold_actions(self.context, expected)
        if not actions:
            raise V072HeldoutPublicGraphAdapterInvariantViolation(
                "failure/terminal public catalogue has no cold row"
            )
        return cold.ColdPublicCatalogueV1(
            self.context_id,
            state,
            expected.remaining_horizon,
            actions,
        )

    def _locked_target_evidence_boundary(self) -> NoReturn:
        raise V072HeldoutPublicGraphAdapterInvariantViolation(
            "row/outcome/observation adaptation is locked until a future "
            "final preregistration and verified target-execution anchor"
        )

    def adapt_row_evidence_v1(self, *args: Any, **kwargs: Any) -> NoReturn:
        del args, kwargs
        self._locked_target_evidence_boundary()

    def adapt_outcome_descriptor_v1(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> NoReturn:
        del args, kwargs
        self._locked_target_evidence_boundary()

    def adapt_registered_observation_v1(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> NoReturn:
        del args, kwargs
        self._locked_target_evidence_boundary()

    def _payload(self) -> dict[str, Any]:
        return _adapter_payload(
            context=self.context,
            cap_binding=self.total_row_cap_binding_v1,
            public_root_state=self.public_root_state,
            public_root_catalogue=self.public_root_catalogue,
            root_state=self.root_state,
            root_actions=self.root_actions,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "total_row_cap_binding": (
                self.total_row_cap_binding_v1.to_document()
            ),
            "public_root_state": self.public_root_state.to_document(),
            "public_root_catalogue": (
                self.public_root_catalogue.to_document()
            ),
            "root_state": self.root_state.to_document(),
            "root_actions": [
                item.to_document() for item in self.root_actions
            ],
            "adapter_id": self.adapter_id,
        }


def registered_heldout_public_graph_adapter_v1(
    context: prereg.HeldoutPublicGraphContextV2,
) -> HeldoutPublicGraphColdClosureAdapterV1:
    return HeldoutPublicGraphColdClosureAdapterV1(context)


__all__ = [
    "CAP_AUTHORITY_CLASS",
    "CAP_SEMANTICS",
    "DOMAIN_TAGS",
    "EXPECTED_CONTEXT_TOTAL_ROW_CAPS",
    "HeldoutPublicGraphColdClosureAdapterV1",
    "HeldoutPublicTotalRowCapBindingV1",
    "PROFILE_KEY",
    "PREREGISTRATION_BINDING_KIND",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_ALLOWED",
    "V072HeldoutPublicGraphAdapterInvariantViolation",
    "registered_heldout_public_graph_adapter_v1",
    "registered_heldout_public_total_row_cap_binding_v1",
]
