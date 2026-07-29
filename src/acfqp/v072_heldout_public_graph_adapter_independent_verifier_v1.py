"""Independent replay of the V0-072 held-out public graph adapter.

This verifier never calls a production adapter method.  It reads the exact
typed frozen fields, derives public legal actions from topology and ranks,
recomputes the observer public state/catalogue/row-binding IDs from their
canonical schemas, then independently recomputes every cold state/action,
cap, adapter, and verification identity.

No hidden-law, kernel, outcome, support, observation, or draw API is used.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_heldout_public_graph_adapter_v1 as adapter


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v072_heldout_public_graph_adapter_independent_replay_v1"
)
VERIFICATION_DOMAIN = (
    "acfqp:v072-heldout-public-graph-adapter-independent-verification:v1"
)

_OBSERVER_DOMAINS = {
    "state": "acfqp:v072-heldout-symbolic-graph-state:v3",
    "catalogue": "acfqp:v072-heldout-legal-action-catalogue:v3",
    "row_binding": "acfqp:v072-heldout-observation-row-binding:v3",
}
_COLD_DOMAINS = {
    "state": "acfqp:v072-cold-h2-public-state:v1",
    "action": "acfqp:v072-cold-h2-public-action:v1",
    "catalogue": "acfqp:v072-cold-h2-public-catalogue:v1",
}
_ADAPTER_DOMAINS = {
    "cap_key": (
        "acfqp:v072-heldout-public-context-total-row-cap-key:v1"
    ),
    "cap_binding": (
        "acfqp:v072-heldout-public-total-row-cap-binding:v1"
    ),
    "adapter": "acfqp:v072-heldout-public-graph-cold-adapter:v1",
}
_EXPECTED_CAPS = (
    ("heldout_graph_k7_confirmatory_v1", 96),
    ("heldout_graph_w7_confirmatory_v1", 48),
    ("heldout_graph_k7_minus_two_confirmatory_v1", 96),
)


class V072HeldoutPublicGraphAdapterIndependentVerificationFailure(
    ValueError
):
    """The public-only adapter differs from independent structural replay."""


def _fail(message: str) -> None:
    raise V072HeldoutPublicGraphAdapterIndependentVerificationFailure(
        message
    )


def _cid(value: Any, field_name: str) -> str:
    try:
        canonical = parse_content_id(value)
    except ValueError as error:
        raise V072HeldoutPublicGraphAdapterIndependentVerificationFailure(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error
    if canonical in prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS:
        _fail(f"{field_name} is a retired development identity")
    return canonical


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V072HeldoutPublicGraphAdapterIndependentVerificationFailure(
            str(error)
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + body
    ).hexdigest()


def _registered_context(
    claimed: Any,
) -> prereg.HeldoutPublicGraphContextV2:
    registered = prereg.registered_heldout_public_contexts_v2()
    caps = tuple(
        (
            item.context_key,
            item.maximum_physical_rows_per_confidence_epoch,
        )
        for item in registered
    )
    if (
        type(claimed) is not prereg.HeldoutPublicGraphContextV2
        or claimed not in registered
        or caps != _EXPECTED_CAPS
        or claimed.context_id
        in prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS
    ):
        _fail("verification requires one exact clean registered context")
    return claimed


def _legal_actions(
    context: prereg.HeldoutPublicGraphContextV2,
    ranks: tuple[int, ...],
    failure: bool,
) -> tuple[tuple[int, int, int], ...]:
    if (
        type(ranks) is not tuple
        or len(ranks) != context.topology.vertex_count
        or any(
            type(rank) is not int
            or not 0 <= rank <= context.rank_cap
            for rank in ranks
        )
        or type(failure) is not bool
    ):
        _fail("public state ranks/failure are malformed")
    result = (
        ()
        if failure
        else tuple(
            sorted(
                (first, second, survivor)
                for first, second in context.topology.edges
                if ranks[first] > 0
                and ranks[first] == ranks[second]
                for survivor in (first, second)
            )
        )
    )
    if failure != (not result):
        _fail("public failure flag disagrees with structural legal actions")
    return result


def _horizon(value: Any) -> int:
    if type(value) is not int or value not in (1, 2):
        _fail("remaining horizon is outside the registered H=2 query")
    return value


def _public_state_payload(
    ranks: tuple[int, ...],
    failure: bool,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_heldout_symbolic_graph_state.v2",
        "schema_version": "2.0.0",
        "ranks": list(ranks),
        "failure": failure,
    }


def _public_state_id(
    ranks: tuple[int, ...],
    failure: bool,
) -> str:
    return _hash(
        _OBSERVER_DOMAINS["state"],
        _public_state_payload(ranks, failure),
    )


def _public_catalogue_payload(
    context_id: str,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
    actions: tuple[tuple[int, int, int], ...],
) -> dict[str, Any]:
    state_payload = _public_state_payload(ranks, failure)
    state_id = _public_state_id(ranks, failure)
    return {
        "schema": "acfqp.v072_heldout_legal_action_catalogue.v2",
        "schema_version": "2.0.0",
        "context_id": context_id,
        "state": {**state_payload, "state_id": state_id},
        "remaining_horizon": remaining_horizon,
        "actions": [list(item) for item in actions],
        "complete_exact_legal_action_catalogue": True,
    }


def _public_catalogue_id(
    context_id: str,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
    actions: tuple[tuple[int, int, int], ...],
) -> str:
    return _hash(
        _OBSERVER_DOMAINS["catalogue"],
        _public_catalogue_payload(
            context_id,
            ranks,
            failure,
            remaining_horizon,
            actions,
        ),
    )


def _public_row_binding_id(
    context_id: str,
    public_catalogue_id: str,
    public_state_id: str,
    remaining_horizon: int,
    action: tuple[int, int, int],
) -> str:
    return _hash(
        _OBSERVER_DOMAINS["row_binding"],
        {
            "schema": "acfqp.v072_heldout_observation_row_binding.v2",
            "schema_version": "2.0.0",
            "context_id": context_id,
            "catalogue_id": public_catalogue_id,
            "state_id": public_state_id,
            "remaining_horizon": remaining_horizon,
            "action": list(action),
            "physical_row_binding": True,
        },
    )


def _cold_state_parts(
    context: prereg.HeldoutPublicGraphContextV2,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    actions = _legal_actions(context, ranks, failure)
    del actions
    horizon = _horizon(remaining_horizon)
    semantic_id = _public_state_id(ranks, failure)
    document = {
        "schema": "acfqp.v072_heldout_public_cold_state_binding.v1",
        "schema_version": "1.0.0",
        "context_id": context.context_id,
        "context_key": context.context_key,
        "topology_id": context.topology.topology_id,
        "public_state_id": semantic_id,
        "ranks": list(ranks),
        "failure": failure,
        "remaining_horizon": horizon,
        "semantic_state_id_reuses_public_state_id": True,
        "hidden_law_serialized": False,
        "outcome_serialized": False,
    }
    payload = {
        "schema": "acfqp.v072_cold_h2_public_state.v1",
        "schema_version": "1.0.0",
        "semantic_state_id": semantic_id,
        "document": document,
    }
    record_id = _hash(_COLD_DOMAINS["state"], payload)
    return (
        semantic_id,
        document,
        record_id,
        {**payload, "state_record_id": record_id},
    )


def _cold_action_parts(
    context: prereg.HeldoutPublicGraphContextV2,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
    action: tuple[int, int, int],
    public_catalogue_id: str,
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    public_state_id = _public_state_id(ranks, failure)
    semantic_id = _public_row_binding_id(
        context.context_id,
        public_catalogue_id,
        public_state_id,
        remaining_horizon,
        action,
    )
    document = {
        "schema": "acfqp.v072_heldout_public_cold_action_binding.v1",
        "schema_version": "1.0.0",
        "context_id": context.context_id,
        "context_key": context.context_key,
        "topology_id": context.topology.topology_id,
        "public_state_id": public_state_id,
        "public_catalogue_id": public_catalogue_id,
        "public_row_binding_id": semantic_id,
        "remaining_horizon": remaining_horizon,
        "action": list(action),
        "semantic_action_id_reuses_public_row_binding_id": True,
        "hidden_law_serialized": False,
        "outcome_serialized": False,
    }
    payload = {
        "schema": "acfqp.v072_cold_h2_public_action.v1",
        "schema_version": "1.0.0",
        "semantic_action_id": semantic_id,
        "document": document,
    }
    record_id = _hash(_COLD_DOMAINS["action"], payload)
    return (
        semantic_id,
        document,
        record_id,
        {**payload, "action_record_id": record_id},
    )


def _expected_action_parts(
    context: prereg.HeldoutPublicGraphContextV2,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
) -> tuple[
    str,
    tuple[
        tuple[str, dict[str, Any], str, dict[str, Any]],
        ...,
    ],
]:
    actions = _legal_actions(context, ranks, failure)
    public_catalogue_id = _public_catalogue_id(
        context.context_id,
        ranks,
        failure,
        remaining_horizon,
        actions,
    )
    parts = tuple(
        sorted(
            (
                _cold_action_parts(
                    context,
                    ranks,
                    failure,
                    remaining_horizon,
                    action,
                    public_catalogue_id,
                )
                for action in actions
            ),
            key=lambda item: item[2],
        )
    )
    return public_catalogue_id, parts


def _cap_parts(
    context: prereg.HeldoutPublicGraphContextV2,
) -> tuple[str, dict[str, Any], str]:
    key_payload = {
        "schema": (
            "acfqp.v072_heldout_public_context_total_row_cap_key.v1"
        ),
        "schema_version": "1.0.0",
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "context_id": context.context_id,
        "context_key": context.context_key,
        "cap_semantics": (
            "COMPLETE_COLD_H2_TOTAL_PHYSICAL_STATE_ACTION_ROWS"
        ),
    }
    key = _hash(_ADAPTER_DOMAINS["cap_key"], key_payload)
    binding_payload = {
        "schema": (
            "acfqp.v072_heldout_public_total_row_cap_binding.v1"
        ),
        "schema_version": "1.0.0",
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "authority_class": "CONFIRMATORY_REGISTERED_PUBLIC_ONLY",
        "context_id": context.context_id,
        "context_key": context.context_key,
        "context_specific_total_row_cap_key": key,
        "total_physical_row_cap": (
            context.maximum_physical_rows_per_confidence_epoch
        ),
        "preregistration_binding": {
            "kind": "NOT_FINALIZED_PUBLIC_ONLY",
            "final_preregistration_id": None,
        },
        "target_execution_allowed": False,
    }
    binding_id = _hash(
        _ADAPTER_DOMAINS["cap_binding"],
        binding_payload,
    )
    return key, binding_payload, binding_id


def _private_document(value: Any) -> dict[str, Any]:
    document = object.__getattribute__(value, "_document_object")
    if type(document) is not dict:
        _fail("cold public document has a substituted runtime type")
    return dict(document)


def _verify_cold_state(
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: Any,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
) -> tuple[str, str]:
    if type(claimed) is not cold.ColdPublicStateV1:
        _fail("claimed cold state has a substituted type")
    semantic_id, document, record_id, _ = _cold_state_parts(
        context,
        ranks,
        failure,
        remaining_horizon,
    )
    if (
        claimed.semantic_state_id != semantic_id
        or _private_document(claimed) != document
        or object.__getattribute__(claimed, "_state_record_id")
        != record_id
    ):
        _fail("cold state differs from independent public replay")
    return semantic_id, record_id


def _verify_cold_actions(
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: Any,
    ranks: tuple[int, ...],
    failure: bool,
    remaining_horizon: int,
) -> tuple[str, tuple[str, ...]]:
    if (
        type(claimed) is not tuple
        or any(type(item) is not cold.ColdPublicActionV1 for item in claimed)
    ):
        _fail("claimed cold actions have a substituted container/type")
    public_catalogue_id, expected = _expected_action_parts(
        context,
        ranks,
        failure,
        remaining_horizon,
    )
    if len(claimed) != len(expected):
        _fail("cold actions omit or add one public legal action")
    for actual, parts in zip(claimed, expected):
        semantic_id, document, record_id, _ = parts
        if (
            actual.semantic_action_id != semantic_id
            or _private_document(actual) != document
            or object.__getattribute__(actual, "_action_record_id")
            != record_id
        ):
            _fail("cold actions are reordered, stale, or caller-mapped")
    return public_catalogue_id, tuple(item[2] for item in expected)


def _verify_cap_binding(
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: Any,
) -> tuple[str, str]:
    if type(claimed) is not adapter.HeldoutPublicTotalRowCapBindingV1:
        _fail("total-row cap binding has a substituted type")
    if type(claimed.preregistration_binding) is not dict:
        _fail("total-row cap preregistration binding is not typed")
    key, payload, binding_id = _cap_parts(context)
    fields = {
        "confirmatory_family_generation": (
            claimed.confirmatory_family_generation
        ),
        "authority_class": claimed.authority_class,
        "context_id": claimed.context_id,
        "context_key": claimed.context_key,
        "context_specific_total_row_cap_key": (
            claimed.context_specific_total_row_cap_key
        ),
        "total_physical_row_cap": claimed.total_physical_row_cap,
        "preregistration_binding": dict(
            claimed.preregistration_binding
        ),
        "target_execution_allowed": claimed.target_execution_allowed,
    }
    if fields != {
        key_name: value
        for key_name, value in payload.items()
        if key_name not in {"schema", "schema_version"}
    }:
        _fail("total-row cap binding differs from public registry")
    return key, binding_id


def _adapter_id(
    *,
    context: prereg.HeldoutPublicGraphContextV2,
    public_root_state_id: str,
    public_root_catalogue_id: str,
    root_state_record_id: str,
    root_action_record_ids: tuple[str, ...],
    cap_key: str,
    cap_binding_id: str,
) -> str:
    payload = {
        "schema": "acfqp.v072_heldout_public_graph_adapter.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "1.36.0",
        "profile_key": "v072_heldout_public_graph_adapter_v1",
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "context_id": context.context_id,
        "context_key": context.context_key,
        "topology_id": context.topology.topology_id,
        "horizon": context.horizon,
        "public_root_state_id": public_root_state_id,
        "public_root_catalogue_id": public_root_catalogue_id,
        "root_state_record_id": root_state_record_id,
        "root_action_record_ids": list(root_action_record_ids),
        "total_row_cap_binding_id": cap_binding_id,
        "context_specific_total_row_cap_key": cap_key,
        "context_specific_total_row_cap": (
            context.maximum_physical_rows_per_confidence_epoch
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
    return _hash(_ADAPTER_DOMAINS["adapter"], payload)


@dataclass(frozen=True, slots=True)
class HeldoutPublicGraphAdapterIndependentVerificationV1:
    context_id: str
    adapter_id: str
    public_root_state_id: str
    public_root_catalogue_id: str
    root_state_record_id: str
    root_action_record_ids: tuple[str, ...]
    context_specific_total_row_cap_key: str
    total_row_cap_binding_id: str
    verification_profile: str = VERIFICATION_PROFILE
    production_adapter_methods_called: bool = False
    hidden_law_queries: int = 0
    kernel_calls: int = 0
    outcome_enumeration_calls: int = 0
    registered_observations_generated: int = 0
    target_execution_allowed: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "verification context"),
            (self.adapter_id, "verified adapter"),
            (self.public_root_state_id, "public root state"),
            (self.public_root_catalogue_id, "public root catalogue"),
            (self.root_state_record_id, "cold root state"),
            (
                self.context_specific_total_row_cap_key,
                "context total-row cap key",
            ),
            (
                self.total_row_cap_binding_id,
                "total-row cap binding",
            ),
        ):
            _cid(value, field_name)
        if (
            type(self.root_action_record_ids) is not tuple
            or not self.root_action_record_ids
            or self.root_action_record_ids
            != tuple(sorted(set(self.root_action_record_ids)))
            or any(
                _cid(item, "cold root action") != item
                for item in self.root_action_record_ids
            )
            or self.verification_profile != VERIFICATION_PROFILE
            or self.production_adapter_methods_called is not False
            or self.hidden_law_queries != 0
            or self.kernel_calls != 0
            or self.outcome_enumeration_calls != 0
            or self.registered_observations_generated != 0
            or self.target_execution_allowed is not False
        ):
            _fail("independent verification attestation is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_heldout_public_graph_adapter_"
                "independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verification_profile": self.verification_profile,
            "context_id": self.context_id,
            "adapter_id": self.adapter_id,
            "public_root_state_id": self.public_root_state_id,
            "public_root_catalogue_id": (
                self.public_root_catalogue_id
            ),
            "root_state_record_id": self.root_state_record_id,
            "root_action_record_ids": list(
                self.root_action_record_ids
            ),
            "context_specific_total_row_cap_key": (
                self.context_specific_total_row_cap_key
            ),
            "total_row_cap_binding_id": (
                self.total_row_cap_binding_id
            ),
            "production_adapter_methods_called": False,
            "hidden_law_queries": 0,
            "kernel_calls": 0,
            "outcome_enumeration_calls": 0,
            "registered_observations_generated": 0,
            "target_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return _hash(VERIFICATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def independently_verify_heldout_public_graph_adapter_v1(
    claimed: adapter.HeldoutPublicGraphColdClosureAdapterV1,
) -> HeldoutPublicGraphAdapterIndependentVerificationV1:
    """Recompute one adapter without invoking any adapter method."""

    if type(claimed) is not adapter.HeldoutPublicGraphColdClosureAdapterV1:
        _fail("claimed adapter has a foreign or duck-typed runtime type")
    context = _registered_context(
        object.__getattribute__(claimed, "context")
    )
    ranks = context.root_ranks
    failure = False
    actions = _legal_actions(context, ranks, failure)
    public_state_id = _public_state_id(ranks, failure)
    public_catalogue_id = _public_catalogue_id(
        context.context_id,
        ranks,
        failure,
        context.horizon,
        actions,
    )

    public_root_state = object.__getattribute__(
        claimed,
        "public_root_state",
    )
    if (
        type(public_root_state)
        is not observer.HeldoutSymbolicGraphStateV2
        or public_root_state.ranks != ranks
        or public_root_state.failure is not False
    ):
        _fail("stored public root state differs from registered ranks")

    public_root_catalogue = object.__getattribute__(
        claimed,
        "public_root_catalogue",
    )
    if (
        type(public_root_catalogue)
        is not observer.HeldoutLegalActionCatalogueV2
        or public_root_catalogue.context_id != context.context_id
        or public_root_catalogue.state != public_root_state
        or public_root_catalogue.remaining_horizon != context.horizon
        or public_root_catalogue.actions != actions
    ):
        _fail("stored public root catalogue is incomplete or reordered")

    _, root_state_record_id = _verify_cold_state(
        context,
        object.__getattribute__(claimed, "root_state"),
        ranks,
        failure,
        context.horizon,
    )
    replayed_catalogue_id, root_action_record_ids = (
        _verify_cold_actions(
            context,
            object.__getattribute__(claimed, "root_actions"),
            ranks,
            failure,
            context.horizon,
        )
    )
    if replayed_catalogue_id != public_catalogue_id:
        _fail("public root catalogue identity changed during replay")

    cap_key, cap_binding_id = _verify_cap_binding(
        context,
        object.__getattribute__(
            claimed,
            "total_row_cap_binding_v1",
        ),
    )
    expected_adapter_id = _adapter_id(
        context=context,
        public_root_state_id=public_state_id,
        public_root_catalogue_id=public_catalogue_id,
        root_state_record_id=root_state_record_id,
        root_action_record_ids=root_action_record_ids,
        cap_key=cap_key,
        cap_binding_id=cap_binding_id,
    )
    if (
        object.__getattribute__(claimed, "_adapter_id")
        != expected_adapter_id
    ):
        _fail("adapter ID differs from independent structural replay")

    return HeldoutPublicGraphAdapterIndependentVerificationV1(
        context.context_id,
        expected_adapter_id,
        public_state_id,
        public_catalogue_id,
        root_state_record_id,
        root_action_record_ids,
        cap_key,
        cap_binding_id,
    )


def independently_verify_cold_public_catalogue_v1(
    claimed_adapter: adapter.HeldoutPublicGraphColdClosureAdapterV1,
    claimed_catalogue: cold.ColdPublicCatalogueV1,
) -> str:
    """Verify any public H2/H1 catalogue without calling adapter methods."""

    independently_verify_heldout_public_graph_adapter_v1(
        claimed_adapter
    )
    context = _registered_context(
        object.__getattribute__(claimed_adapter, "context")
    )
    if (
        type(claimed_catalogue) is not cold.ColdPublicCatalogueV1
        or claimed_catalogue.context_id != context.context_id
    ):
        _fail("cold catalogue has a foreign context or runtime type")
    state = claimed_catalogue.state
    if type(state) is not cold.ColdPublicStateV1:
        _fail("cold catalogue state has a substituted type")
    document = _private_document(state)
    if (
        type(document.get("ranks")) is not list
        or type(document.get("failure")) is not bool
    ):
        _fail("cold catalogue state document is malformed")
    ranks = tuple(document["ranks"])
    failure = document["failure"]
    remaining_horizon = _horizon(
        claimed_catalogue.remaining_horizon
    )
    if document.get("remaining_horizon") != remaining_horizon:
        _fail("cold catalogue/state remaining horizon disagrees")
    _, state_record_id = _verify_cold_state(
        context,
        state,
        ranks,
        failure,
        remaining_horizon,
    )
    _, action_record_ids = _verify_cold_actions(
        context,
        claimed_catalogue.actions,
        ranks,
        failure,
        remaining_horizon,
    )
    payload = {
        "schema": "acfqp.v072_cold_h2_public_catalogue.v1",
        "schema_version": "1.0.0",
        "context_id": context.context_id,
        "state_record_id": state_record_id,
        "remaining_horizon": remaining_horizon,
        "action_record_ids": list(action_record_ids),
    }
    expected_id = _hash(_COLD_DOMAINS["catalogue"], payload)
    if claimed_catalogue.catalogue_id != expected_id:
        _fail("cold catalogue ID differs from independent replay")
    return expected_id


__all__ = [
    "HeldoutPublicGraphAdapterIndependentVerificationV1",
    "SCHEMA_VERSION",
    "VERIFICATION_PROFILE",
    "V072HeldoutPublicGraphAdapterIndependentVerificationFailure",
    "independently_verify_cold_public_catalogue_v1",
    "independently_verify_heldout_public_graph_adapter_v1",
]
