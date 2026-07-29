"""A bounded second, distinct-row partial-support transaction for K6.

V0-068 permits one causal row promotion.  The registered K6 transaction at
the 8,192-draw checkpoint remains uncertified after that promotion.  This
module adds one *new* transaction without weakening the first contract:

* transaction 2 is bound to the immutable transaction-1 consumer;
* causal counterfactuals are recomputed on the mixed transaction-1 model;
* the transaction-1 binding and physical evidence are excluded;
* exactly one different epoch-1 row may be promoted to epoch 2;
* the resulting closure contains exactly two distinct epoch-2 bindings; and
* no transaction 3 or global 16,384 checkpoint is reachable.

The operational path uses only the observation-driven V0-068 authorities.
An exact lift, when present, is a separately typed evaluation-only artifact
created only after the robust audit has certified.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
from multiprocessing import get_context
from typing import Any, Iterable, Mapping

import acfqp.observation_support_exact_evaluation_v1 as exact_evaluation
import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_promoted_h2_consumer_v1 as first_consumer
import acfqp.observation_support_relational_adapter_v1 as relational
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.33.0"
PROFILE_KEY = "k6_two_distinct_row_support_transactions_v0"

REGISTERED_CONTEXT_KEY = "opaque_graph_k6_v0"
REGISTERED_BASE_CHECKPOINT = 8_192
REGISTERED_PROMOTION_CHECKPOINT = 2_048
REGISTERED_NEW_CHILD_CHECKPOINT = 8_192
MAX_SUPPORT_TRANSACTIONS = 2
MAX_COUNTERFACTUAL_ROWS = 64
MAX_NEW_CHILD_CATALOGUES = 48
MAX_NEW_CHILD_ACTION_ROWS = 288
MAX_INCREMENTAL_OBSERVER_DRAWS = 2_379_776
MAX_PROCESS_WORKERS = h2_closure.MAX_PROCESS_WORKERS
GLOBAL_16K_CHECKPOINT_FORBIDDEN = True
STATISTICAL_CLAIM_SCOPE = observer.STATISTICAL_CLAIM_SCOPE


class ObservationSupportSecondTransactionInvariantViolation(ValueError):
    """A second-transaction identity, cap, lineage, or replay is invalid."""


class SecondTransactionOutcome(str, Enum):
    CERTIFIED_AT_8192 = "CERTIFIED_AT_8192"
    FAILED_NEW_FRONTIER = "FAILED_NEW_FRONTIER"
    NO_SOUND_DIFFERENT_ROW_COVER = "NO_SOUND_DIFFERENT_ROW_COVER"
    COUNTERFACTUAL_CAP_EXHAUSTED = "COUNTERFACTUAL_CAP_EXHAUSTED"
    MATERIALIZATION_CAP_EXHAUSTED = "MATERIALIZATION_CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"


DOMAIN_TAGS = {
    "caps": "acfqp:second-support-transaction-caps:v1",
    "context": "acfqp:second-support-transaction-context:v1",
    "authorization": (
        "acfqp:distinct-row-expansion-authorization:v2"
    ),
    "replacement": "acfqp:second-promoted-row-replacement:v1",
    "counters": "acfqp:second-support-transaction-counters:v1",
    "closure": "acfqp:second-promoted-h2-closure:v1",
    "run": "acfqp:second-support-transaction-run:v1",
    "probe": "acfqp:k6-two-distinct-row-probe:v1",
    "verification": (
        "acfqp:second-support-transaction-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("second-transaction domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportSecondTransactionInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportSecondTransactionInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _sorted_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    result = tuple(values)
    if result != tuple(sorted(set(result))):
        raise ObservationSupportSecondTransactionInvariantViolation(
            f"{field} must be a sorted distinct tuple"
        )
    for value in result:
        _cid(value, field)
    return result


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _workers(value: Any) -> int:
    if (
        type(value) is not int
        or isinstance(value, bool)
        or not 1 <= value <= MAX_PROCESS_WORKERS
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "max_workers is outside the registered finite range"
        )
    return value


def _registered_k6(
    context: observer.PublicGraphContextV1,
) -> observer.PublicGraphContextV1:
    expected = observer.public_context_by_key_v1(REGISTERED_CONTEXT_KEY)
    if (
        type(context) is not observer.PublicGraphContextV1
        or context != expected
        or context.horizon != 2
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "this profile is restricted to the registered K6 H=2 context"
        )
    return expected


@dataclass(frozen=True, slots=True)
class SecondSupportTransactionCapsV1:
    """Finite preregistered caps; values are part of every run identity."""

    max_support_transactions: int = MAX_SUPPORT_TRANSACTIONS
    max_counterfactual_rows: int = MAX_COUNTERFACTUAL_ROWS
    promoted_validation_checkpoint: int = REGISTERED_PROMOTION_CHECKPOINT
    new_child_validation_checkpoint: int = REGISTERED_NEW_CHILD_CHECKPOINT
    max_new_child_catalogues: int = MAX_NEW_CHILD_CATALOGUES
    max_new_child_action_rows: int = MAX_NEW_CHILD_ACTION_ROWS
    max_incremental_observer_draws: int = MAX_INCREMENTAL_OBSERVER_DRAWS
    max_global_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    global_16384_checkpoint_forbidden: bool = True

    def __post_init__(self) -> None:
        if (
            self.max_support_transactions != MAX_SUPPORT_TRANSACTIONS
            or self.max_counterfactual_rows != MAX_COUNTERFACTUAL_ROWS
            or self.promoted_validation_checkpoint
            != REGISTERED_PROMOTION_CHECKPOINT
            or self.new_child_validation_checkpoint
            != REGISTERED_NEW_CHILD_CHECKPOINT
            or self.max_new_child_catalogues
            != MAX_NEW_CHILD_CATALOGUES
            or self.max_new_child_action_rows != MAX_NEW_CHILD_ACTION_ROWS
            or self.max_incremental_observer_draws
            != MAX_INCREMENTAL_OBSERVER_DRAWS
            or self.max_global_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.global_16384_checkpoint_forbidden is not True
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second-transaction caps are not the registered finite profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_support_transaction_caps.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
        }

    @property
    def cap_profile_id(self) -> str:
        return _content_id("caps", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cap_profile_id": self.cap_profile_id}


def registered_second_transaction_caps_v1(
) -> SecondSupportTransactionCapsV1:
    return SecondSupportTransactionCapsV1()


@dataclass(frozen=True, slots=True)
class SecondSupportTransactionContextV1:
    """Immutable dependency chain for transaction 2."""

    context_id: str
    base_closure_id: str
    base_bridge_id: str
    base_audit_id: str
    threshold_profile_id: str
    transaction1_authorization_id: str
    transaction1_replacement_id: str
    transaction1_consumer_id: str
    transaction1_closure_id: str
    transaction1_bridge_id: str
    transaction1_model_id: str
    transaction1_audit_id: str
    transaction1_frontier_id: str
    transaction1_selected_binding_id: str
    transaction1_parent_partial_row_id: str
    transaction1_promoted_partial_row_id: str
    transaction1_parent_physical_evidence_id: str
    transaction1_promoted_physical_evidence_id: str
    transaction_history_ids: tuple[str, ...]
    cap_profile_id: str
    transaction_index: int = 2
    prior_transaction_count: int = 1
    base_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    global_16384_checkpoint_accesses: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "transaction context"),
            (self.base_closure_id, "base closure"),
            (self.base_bridge_id, "base bridge"),
            (self.base_audit_id, "base audit"),
            (self.threshold_profile_id, "transaction threshold"),
            (
                self.transaction1_authorization_id,
                "transaction-1 authorization",
            ),
            (self.transaction1_replacement_id, "transaction-1 replacement"),
            (self.transaction1_consumer_id, "transaction-1 consumer"),
            (self.transaction1_closure_id, "transaction-1 closure"),
            (self.transaction1_bridge_id, "transaction-1 bridge"),
            (self.transaction1_model_id, "transaction-1 model"),
            (self.transaction1_audit_id, "transaction-1 audit"),
            (self.transaction1_frontier_id, "transaction-1 frontier"),
            (
                self.transaction1_selected_binding_id,
                "transaction-1 selected binding",
            ),
            (
                self.transaction1_parent_partial_row_id,
                "transaction-1 parent row",
            ),
            (
                self.transaction1_promoted_partial_row_id,
                "transaction-1 promoted row",
            ),
            (
                self.transaction1_parent_physical_evidence_id,
                "transaction-1 parent physical evidence",
            ),
            (
                self.transaction1_promoted_physical_evidence_id,
                "transaction-1 physical evidence",
            ),
            (self.cap_profile_id, "transaction cap profile"),
        ):
            _cid(value, field)
        history = _sorted_ids(
            self.transaction_history_ids,
            "transaction history",
        )
        expected_history = tuple(
            sorted(
                (
                    self.transaction1_authorization_id,
                    self.transaction1_replacement_id,
                    self.transaction1_consumer_id,
                )
            )
        )
        if (
            history != expected_history
            or self.transaction_index != 2
            or self.prior_transaction_count != 1
            or self.base_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.global_16384_checkpoint_accesses != 0
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "transaction context history or checkpoint is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_support_transaction_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field: (
                    list(getattr(self, field))
                    if field == "transaction_history_ids"
                    else getattr(self, field)
                )
                for field in self.__dataclass_fields__
            },
            "no_transaction_1_candidate_reuse": True,
            "global_16384_checkpoint_forbidden": True,
        }

    @property
    def transaction_context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "transaction_context_id": self.transaction_context_id,
        }


@dataclass(frozen=True, slots=True)
class DistinctRowExpansionAuthorizationV2:
    """Permission to promote exactly one row different from transaction 1."""

    transaction_context_id: str
    parent_bridge_id: str
    parent_model_id: str
    parent_audit_id: str
    parent_frontier_id: str
    threshold_profile_id: str
    solver_kind: robust.RobustSolverKind
    parent_source_partial_row_ids: tuple[str, ...]
    excluded_binding_ids: tuple[str, ...]
    excluded_physical_evidence_ids: tuple[str, ...]
    candidate_evidence: tuple[
        expansion.RowOtherCounterfactualEvidenceV1, ...
    ]
    selected_evidence_id: str
    selected_planner_row_id: str
    selected_partial_row_id: str
    selected_binding_id: str
    selected_parent_physical_evidence_id: str
    selected_parent_support_epoch_id: str
    selected_parent_confidence_authority_id: str
    selected_remaining_horizon: int
    selected_novel_outcome_ids: tuple[str, ...]
    promoted_validation_checkpoint: int
    transaction_index: int = 2
    authorization_scope: str = (
        "ONE_DIFFERENT_ROW_ONE_SECOND_SUPPORT_TRANSACTION"
    )

    def __post_init__(self) -> None:
        for value, field in (
            (self.transaction_context_id, "authorization context"),
            (self.parent_bridge_id, "authorization parent bridge"),
            (self.parent_model_id, "authorization parent model"),
            (self.parent_audit_id, "authorization parent audit"),
            (self.parent_frontier_id, "authorization parent frontier"),
            (self.threshold_profile_id, "authorization threshold"),
            (self.selected_evidence_id, "selected evidence"),
            (self.selected_planner_row_id, "selected planner row"),
            (self.selected_partial_row_id, "selected partial row"),
            (self.selected_binding_id, "selected binding"),
            (
                self.selected_parent_physical_evidence_id,
                "selected physical evidence",
            ),
            (
                self.selected_parent_support_epoch_id,
                "selected support epoch",
            ),
            (
                self.selected_parent_confidence_authority_id,
                "selected confidence authority",
            ),
        ):
            _cid(value, field)
        source_ids = _sorted_ids(
            self.parent_source_partial_row_ids,
            "authorization source rows",
        )
        excluded_bindings = _sorted_ids(
            self.excluded_binding_ids,
            "excluded bindings",
        )
        excluded_evidence = _sorted_ids(
            self.excluded_physical_evidence_ids,
            "excluded evidence",
        )
        novel = _sorted_ids(
            self.selected_novel_outcome_ids,
            "selected novel outcomes",
        )
        evidence_ids = tuple(
            item.evidence_id for item in self.candidate_evidence
        )
        if (
            source_ids != self.parent_source_partial_row_ids
            or not excluded_bindings
            or not excluded_evidence
            or not novel
            or type(self.solver_kind) is not robust.RobustSolverKind
            or not self.candidate_evidence
            or any(
                type(item)
                is not expansion.RowOtherCounterfactualEvidenceV1
                for item in self.candidate_evidence
            )
            or evidence_ids != tuple(sorted(set(evidence_ids)))
            or self.selected_evidence_id not in set(evidence_ids)
            or not next(
                item
                for item in self.candidate_evidence
                if item.evidence_id == self.selected_evidence_id
            ).changes_failed_to_certified
            or self.selected_partial_row_id not in source_ids
            or self.selected_binding_id in excluded_bindings
            or self.selected_parent_physical_evidence_id in excluded_evidence
            or self.selected_remaining_horizon not in (1, 2)
            or self.promoted_validation_checkpoint
            != REGISTERED_PROMOTION_CHECKPOINT
            or self.transaction_index != 2
            or self.authorization_scope
            != "ONE_DIFFERENT_ROW_ONE_SECOND_SUPPORT_TRANSACTION"
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "distinct-row authorization is malformed or reuses evidence"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.distinct_row_expansion_authorization.v2",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_context_id": self.transaction_context_id,
            "parent_bridge_id": self.parent_bridge_id,
            "parent_model_id": self.parent_model_id,
            "parent_audit_id": self.parent_audit_id,
            "parent_frontier_id": self.parent_frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "solver_kind": self.solver_kind.value,
            "parent_source_partial_row_ids": list(
                self.parent_source_partial_row_ids
            ),
            "excluded_binding_ids": list(self.excluded_binding_ids),
            "excluded_physical_evidence_ids": list(
                self.excluded_physical_evidence_ids
            ),
            "candidate_evidence_ids": [
                item.evidence_id for item in self.candidate_evidence
            ],
            "selected_evidence_id": self.selected_evidence_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "selected_partial_row_id": self.selected_partial_row_id,
            "selected_binding_id": self.selected_binding_id,
            "selected_parent_physical_evidence_id": (
                self.selected_parent_physical_evidence_id
            ),
            "selected_parent_support_epoch_id": (
                self.selected_parent_support_epoch_id
            ),
            "selected_parent_confidence_authority_id": (
                self.selected_parent_confidence_authority_id
            ),
            "selected_remaining_horizon": self.selected_remaining_horizon,
            "selected_novel_outcome_ids": list(
                self.selected_novel_outcome_ids
            ),
            "promoted_validation_checkpoint": (
                self.promoted_validation_checkpoint
            ),
            "transaction_index": 2,
            "authorization_scope": self.authorization_scope,
            "counterfactuals_recomputed_on_parent_model": True,
            "transaction1_candidate_reuse_allowed": False,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidate_evidence": [
                item.to_document() for item in self.candidate_evidence
            ],
            "authorization_id": self.authorization_id,
        }


@dataclass(frozen=True, slots=True)
class SecondPromotedRowReplacementV1:
    authorization: DistinctRowExpansionAuthorizationV2
    parent_row: acquisition.GraphPartialSupportRowV1
    promoted_row: acquisition.GraphPartialSupportRowV1
    quarantined_parent_observation_ids: tuple[str, ...]
    fresh_validation_observation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.authorization)
            is not DistinctRowExpansionAuthorizationV2
            or type(self.parent_row)
            is not acquisition.GraphPartialSupportRowV1
            or type(self.promoted_row)
            is not acquisition.GraphPartialSupportRowV1
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second replacement inputs are untyped"
            )
        quarantined = _sorted_ids(
            self.quarantined_parent_observation_ids,
            "quarantined parent observations",
        )
        fresh = _sorted_ids(
            self.fresh_validation_observation_ids,
            "fresh validation observations",
        )
        parent = self.parent_row
        promoted = self.promoted_row
        expected_quarantined = tuple(
            sorted(
                {
                    *parent.initial_discovery_observation_ids,
                    *parent.prior_validation_observation_ids,
                    *parent.current_validation_observation_ids,
                }
            )
        )
        if (
            parent.partial_row_id
            != self.authorization.selected_partial_row_id
            or parent.binding.row_id
            != self.authorization.selected_binding_id
            or parent.physical_evidence_id
            != self.authorization.selected_parent_physical_evidence_id
            or parent.support_epoch_index != 1
            or promoted.parent_row != parent
            or promoted.binding != parent.binding
            or promoted.support_epoch_index != 2
            or quarantined != expected_quarantined
            or fresh
            != tuple(sorted(promoted.current_validation_observation_ids))
            or set(quarantined) & set(fresh)
            or len(fresh) != REGISTERED_PROMOTION_CHECKPOINT
            or not set(self.authorization.selected_novel_outcome_ids)
            .issubset(
                item.outcome_id for item in promoted.support_descriptors
            )
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second replacement reused samples or changed authorization"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_promoted_row_replacement.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization.authorization_id,
            "parent_partial_row_id": self.parent_row.partial_row_id,
            "promoted_partial_row_id": self.promoted_row.partial_row_id,
            "selected_binding_id": self.parent_row.binding.row_id,
            "quarantined_parent_observation_ids": list(
                self.quarantined_parent_observation_ids
            ),
            "fresh_validation_observation_ids": list(
                self.fresh_validation_observation_ids
            ),
            "transaction_index": 2,
        }

    @property
    def replacement_id(self) -> str:
        return _content_id("replacement", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization": self.authorization.to_document(),
            "parent_row_ref": {
                "partial_row_id": self.parent_row.partial_row_id,
                "physical_evidence_id": self.parent_row.physical_evidence_id,
            },
            "promoted_row_ref": {
                "partial_row_id": self.promoted_row.partial_row_id,
                "physical_evidence_id": (
                    self.promoted_row.physical_evidence_id
                ),
            },
            "replacement_id": self.replacement_id,
        }


@dataclass(frozen=True, slots=True)
class SecondSupportTransactionCountersV1:
    eligible_counterfactual_row_count: int
    causal_counterfactual_row_count: int
    promoted_validation_draws: int
    promoted_validation_random_word_calls: int
    promoted_validation_rejections: int
    new_child_catalogue_count: int
    new_child_action_row_count: int
    new_child_discovery_draws: int
    new_child_validation_draws: int
    new_child_observer_draws: int
    new_child_random_word_calls: int
    new_child_rejections: int
    incremental_observer_draws: int
    incremental_random_word_calls: int
    incremental_rejections: int
    cap_checks: int
    cap_rejections: int
    global_16384_checkpoint_accesses: int = 0
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0
    evaluation_exact_atom_calls: int = 0

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, field) for field in self.__dataclass_fields__
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.causal_counterfactual_row_count
            > self.eligible_counterfactual_row_count
            or self.promoted_validation_random_word_calls
            != self.promoted_validation_draws
            + self.promoted_validation_rejections
            or self.new_child_observer_draws
            != self.new_child_discovery_draws
            + self.new_child_validation_draws
            or self.incremental_observer_draws
            != self.promoted_validation_draws
            + self.new_child_observer_draws
            or self.incremental_random_word_calls
            != self.promoted_validation_random_word_calls
            + self.new_child_random_word_calls
            or self.incremental_rejections
            != self.promoted_validation_rejections
            + self.new_child_rejections
            or self.incremental_random_word_calls
            != self.incremental_observer_draws
            + self.incremental_rejections
            or self.cap_checks < 4
            or self.global_16384_checkpoint_accesses != 0
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
            or self.evaluation_exact_atom_calls != 0
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second-transaction counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_support_transaction_counters.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


def _sorted_rows(
    rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    result = tuple(sorted(rows, key=lambda item: item.binding.row_id))
    if (
        any(
            type(item) is not acquisition.GraphPartialSupportRowV1
            for item in result
        )
        or len({item.binding.row_id for item in result}) != len(result)
        or len({item.partial_row_id for item in result}) != len(result)
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "closure rows are not unique typed rows"
        )
    return result


def _sorted_catalogues(
    catalogues: Iterable[observer.LegalActionCatalogueV1],
) -> tuple[observer.LegalActionCatalogueV1, ...]:
    result = tuple(sorted(catalogues, key=lambda item: item.catalogue_id))
    if (
        any(
            type(item) is not observer.LegalActionCatalogueV1
            for item in result
        )
        or len({item.catalogue_id for item in result}) != len(result)
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "child catalogues are not unique typed catalogues"
        )
    return result


def _active_root_states(
    root_rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[observer.SymbolicGraphStateV1, ...]:
    by_id: dict[str, observer.SymbolicGraphStateV1] = {}
    for row in root_rows:
        for descriptor in row.support_descriptors:
            if descriptor.failure or descriptor.terminal:
                continue
            state = descriptor.next_state
            prior = by_id.setdefault(state.state_id, state)
            if prior != state:
                raise ObservationSupportSecondTransactionInvariantViolation(
                    "one successor ID has conflicting symbolic states"
                )
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class SecondPromotedH2ClosureV1:
    """Complete H2 closure after exactly two distinct row promotions."""

    transaction_context_id: str
    parent_consumer_id: str
    replacement: SecondPromotedRowReplacementV1
    context: observer.PublicGraphContextV1
    root_catalogue: observer.LegalActionCatalogueV1
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...]
    root_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    child_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    epoch2_binding_ids: tuple[str, ...]
    newly_admitted_child_catalogue_ids: tuple[str, ...]
    newly_acquired_child_partial_row_ids: tuple[str, ...]
    counters: SecondSupportTransactionCountersV1
    support_transaction_count: int = 2
    third_transaction_allowed: bool = False
    exact_iid_implementation_claimed: bool = False
    formal_exact_iid_plan_certificate: bool = False
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE

    def __post_init__(self) -> None:
        _cid(self.transaction_context_id, "closure transaction context")
        _cid(self.parent_consumer_id, "closure parent consumer")
        if (
            type(self.replacement)
            is not SecondPromotedRowReplacementV1
            or _registered_k6(self.context) != self.context
            or type(self.root_catalogue)
            is not observer.LegalActionCatalogueV1
            or type(self.counters)
            is not SecondSupportTransactionCountersV1
            or self.support_transaction_count != 2
            or self.third_transaction_allowed is not False
            or self.exact_iid_implementation_claimed is not False
            or self.formal_exact_iid_plan_certificate is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second promoted closure schema is invalid"
            )
        rows = (*self.root_rows, *self.child_rows)
        epoch2 = _sorted_ids(
            self.epoch2_binding_ids,
            "epoch-2 binding IDs",
        )
        new_catalogues = _sorted_ids(
            self.newly_admitted_child_catalogue_ids,
            "new child catalogue IDs",
        )
        new_rows = _sorted_ids(
            self.newly_acquired_child_partial_row_ids,
            "new child row IDs",
        )
        actual_epoch2 = tuple(
            sorted(
                row.binding.row_id
                for row in rows
                if row.support_epoch_index == 2
            )
        )
        if (
            _sorted_rows(self.root_rows) != self.root_rows
            or _sorted_rows(self.child_rows) != self.child_rows
            or _sorted_catalogues(self.child_catalogues)
            != self.child_catalogues
            or len(epoch2) != 2
            or actual_epoch2 != epoch2
            or self.replacement.parent_row.binding.row_id not in epoch2
            or len(rows) != len({row.binding.row_id for row in rows})
            or any(row.support_epoch_index not in (1, 2) for row in rows)
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "closure does not contain exactly two distinct epoch-2 rows"
            )
        expected_catalogues = _sorted_catalogues(
            observer.legal_action_catalogue_v1(self.context, state, 1)
            for state in _active_root_states(self.root_rows)
        )
        if tuple(
            item.to_document() for item in expected_catalogues
        ) != tuple(item.to_document() for item in self.child_catalogues):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second closure omits a reachable child catalogue"
            )
        expected_root_bindings = {
            (self.root_catalogue.catalogue_id, action)
            for action in self.root_catalogue.actions
        }
        expected_child_bindings = {
            (catalogue.catalogue_id, action)
            for catalogue in self.child_catalogues
            for action in catalogue.actions
        }
        actual_root_bindings = {
            (row.binding.catalogue_id, row.binding.action)
            for row in self.root_rows
        }
        actual_child_bindings = {
            (row.binding.catalogue_id, row.binding.action)
            for row in self.child_rows
        }
        if (
            actual_root_bindings != expected_root_bindings
            or actual_child_bindings != expected_child_bindings
            or len(new_catalogues)
            != self.counters.new_child_catalogue_count
            or len(new_rows) != self.counters.new_child_action_row_count
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second closure action coverage or counters are incomplete"
            )

    @property
    def all_rows(
        self,
    ) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
        return (*self.root_rows, *self.child_rows)

    @property
    def public_catalogues(
        self,
    ) -> tuple[observer.LegalActionCatalogueV1, ...]:
        return (self.root_catalogue, *self.child_catalogues)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_promoted_h2_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_context_id": self.transaction_context_id,
            "parent_consumer_id": self.parent_consumer_id,
            "replacement_id": self.replacement.replacement_id,
            "context_id": self.context.context_id,
            "root_catalogue_id": self.root_catalogue.catalogue_id,
            "child_catalogue_ids": [
                item.catalogue_id for item in self.child_catalogues
            ],
            "root_partial_row_ids": [
                item.partial_row_id for item in self.root_rows
            ],
            "child_partial_row_ids": [
                item.partial_row_id for item in self.child_rows
            ],
            "epoch2_binding_ids": list(self.epoch2_binding_ids),
            "newly_admitted_child_catalogue_ids": list(
                self.newly_admitted_child_catalogue_ids
            ),
            "newly_acquired_child_partial_row_ids": list(
                self.newly_acquired_child_partial_row_ids
            ),
            "counters_id": self.counters.counters_id,
            "support_transaction_count": 2,
            "third_transaction_allowed": False,
            "global_16384_checkpoint_accesses": 0,
            "exact_iid_implementation_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "statistical_claim_scope": self.statistical_claim_scope,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "replacement": self.replacement.to_document(),
            "counters": self.counters.to_document(),
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class SecondSupportTransactionRunV1:
    context: SecondSupportTransactionContextV1
    outcome: SecondTransactionOutcome
    candidate_evidence: tuple[
        expansion.RowOtherCounterfactualEvidenceV1, ...
    ]
    authorization: DistinctRowExpansionAuthorizationV2 | None
    replacement: SecondPromotedRowReplacementV1 | None
    closure: SecondPromotedH2ClosureV1 | None
    bridge: graph_model.ObservationSupportGraphModelBridgeV1 | None
    audit: robust.RobustPlanAuditV1 | None
    counters: SecondSupportTransactionCountersV1
    third_transaction_allowed: bool = False
    global_16384_checkpoint_accesses: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.context) is not SecondSupportTransactionContextV1
            or type(self.outcome) is not SecondTransactionOutcome
            or any(
                type(item)
                is not expansion.RowOtherCounterfactualEvidenceV1
                for item in self.candidate_evidence
            )
            or tuple(item.evidence_id for item in self.candidate_evidence)
            != tuple(
                sorted(
                    {
                        item.evidence_id for item in self.candidate_evidence
                    }
                )
            )
            or type(self.counters)
            is not SecondSupportTransactionCountersV1
            or self.third_transaction_allowed is not False
            or self.global_16384_checkpoint_accesses != 0
            or any(
                item.parent_model_id != self.context.transaction1_model_id
                or item.parent_audit_id
                != self.context.transaction1_audit_id
                or item.threshold_profile_id
                != self.context.threshold_profile_id
                or item.partial_row_id
                == self.context.transaction1_parent_partial_row_id
                or item.partial_row_id
                == self.context.transaction1_promoted_partial_row_id
                for item in self.candidate_evidence
            )
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second-transaction result schema is invalid"
            )
        materialized = self.outcome in (
            SecondTransactionOutcome.CERTIFIED_AT_8192,
            SecondTransactionOutcome.FAILED_NEW_FRONTIER,
        )
        if materialized:
            if (
                type(self.authorization)
                is not DistinctRowExpansionAuthorizationV2
                or type(self.replacement)
                is not SecondPromotedRowReplacementV1
                or type(self.closure) is not SecondPromotedH2ClosureV1
                or type(self.bridge)
                is not graph_model.ObservationSupportGraphModelBridgeV1
                or type(self.audit) is not robust.RobustPlanAuditV1
                or self.closure.transaction_context_id
                != self.context.transaction_context_id
                or self.bridge.source_partial_row_ids
                != tuple(
                    sorted(
                        row.partial_row_id for row in self.closure.all_rows
                    )
                )
                or self.audit.model_id != self.bridge.quotient_model.model_id
                or (
                    self.outcome
                    is SecondTransactionOutcome.CERTIFIED_AT_8192
                )
                is not self.audit.certified
                or (
                    self.outcome
                    is SecondTransactionOutcome.FAILED_NEW_FRONTIER
                )
                is not (
                    self.audit.status
                    is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
                )
            ):
                raise ObservationSupportSecondTransactionInvariantViolation(
                    "materialized second transaction has stale authorities"
                )
        elif any(
            item is not None
            for item in (
                self.authorization,
                self.replacement,
                self.closure,
                self.bridge,
                self.audit,
            )
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "nonmaterialized terminal outcome carries route artifacts"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_support_transaction_run.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_context_id": self.context.transaction_context_id,
            "outcome": self.outcome.value,
            "candidate_evidence_ids": [
                item.evidence_id for item in self.candidate_evidence
            ],
            "authorization_id": (
                None
                if self.authorization is None
                else self.authorization.authorization_id
            ),
            "replacement_id": (
                None
                if self.replacement is None
                else self.replacement.replacement_id
            ),
            "closure_id": (
                None if self.closure is None else self.closure.closure_id
            ),
            "bridge_id": (
                None if self.bridge is None else self.bridge.bridge_id
            ),
            "audit_id": (
                None if self.audit is None else self.audit.audit_id
            ),
            "counters_id": self.counters.counters_id,
            "third_transaction_allowed": False,
            "global_16384_checkpoint_accesses": 0,
            "formal_exact_iid_plan_certificate": False,
            "statistical_claim_scope": STATISTICAL_CLAIM_SCOPE,
        }

    @property
    def run_id(self) -> str:
        return _content_id("run", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "candidate_evidence": [
                item.to_document() for item in self.candidate_evidence
            ],
            "authorization": (
                None
                if self.authorization is None
                else self.authorization.to_document()
            ),
            "replacement": (
                None
                if self.replacement is None
                else self.replacement.to_document()
            ),
            "closure": (
                None if self.closure is None else self.closure.to_document()
            ),
            "bridge": (
                None if self.bridge is None else self.bridge.to_document()
            ),
            "audit": (
                None if self.audit is None else self.audit.to_document()
            ),
            "counters": self.counters.to_document(),
            "run_id": self.run_id,
        }


@dataclass(frozen=True, slots=True)
class K6TwoDistinctRowProbeV0:
    """Bounded K6@8192 probe and optional evaluation-only exact lift."""

    context_id: str
    base_closure_id: str
    first_consumer_id: str
    second_run: SecondSupportTransactionRunV1
    exact_lift: (
        exact_evaluation.ObservationSupportExactLiftEvaluationV1 | None
    )
    base_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    max_global_checkpoint: int = REGISTERED_BASE_CHECKPOINT
    global_16384_checkpoint_accesses: int = 0
    third_transaction_allowed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "probe context"),
            (self.base_closure_id, "probe base closure"),
            (self.first_consumer_id, "probe first consumer"),
        ):
            _cid(value, field)
        if (
            type(self.second_run) is not SecondSupportTransactionRunV1
            or self.second_run.context.context_id != self.context_id
            or self.second_run.context.base_closure_id
            != self.base_closure_id
            or self.second_run.context.transaction1_consumer_id
            != self.first_consumer_id
            or self.base_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.max_global_checkpoint != REGISTERED_BASE_CHECKPOINT
            or self.global_16384_checkpoint_accesses != 0
            or self.third_transaction_allowed is not False
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "bounded K6 probe identity or checkpoint changed"
            )
        if self.second_run.outcome is SecondTransactionOutcome.CERTIFIED_AT_8192:
            if (
                type(self.exact_lift)
                is not exact_evaluation.ObservationSupportExactLiftEvaluationV1
                or self.second_run.bridge is None
                or self.second_run.audit is None
                or self.exact_lift.bridge_id
                != self.second_run.bridge.bridge_id
                or self.exact_lift.audit_id
                != self.second_run.audit.audit_id
                or self.exact_lift.prerequisite_operational_freeze_id
                != self.second_run.run_id
            ):
                raise ObservationSupportSecondTransactionInvariantViolation(
                    "certified probe lacks its evaluation-only exact lift"
                )
        elif self.exact_lift is not None:
            raise ObservationSupportSecondTransactionInvariantViolation(
                "uncertified second transaction cannot invoke exact lift"
            )

    @property
    def exact_failure_probability(self) -> Fraction | None:
        return (
            None
            if self.exact_lift is None
            else self.exact_lift.exact_failure_probability
        )

    @property
    def exact_normalized_regret(self) -> Fraction | None:
        return (
            None
            if self.exact_lift is None
            else self.exact_lift.exact_normalized_regret
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k6_two_distinct_row_probe.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "base_closure_id": self.base_closure_id,
            "first_consumer_id": self.first_consumer_id,
            "second_run_id": self.second_run.run_id,
            "outcome": self.second_run.outcome.value,
            "exact_lift_evaluation_id": (
                None
                if self.exact_lift is None
                else self.exact_lift.evaluation_id
            ),
            "exact_failure_probability": (
                None
                if self.exact_failure_probability is None
                else _fdoc(self.exact_failure_probability)
            ),
            "exact_normalized_regret": (
                None
                if self.exact_normalized_regret is None
                else _fdoc(self.exact_normalized_regret)
            ),
            "base_checkpoint": REGISTERED_BASE_CHECKPOINT,
            "max_global_checkpoint": REGISTERED_BASE_CHECKPOINT,
            "global_16384_checkpoint_accesses": 0,
            "third_transaction_allowed": False,
            "exact_evaluation_lane_only": True,
        }

    @property
    def probe_id(self) -> str:
        return _content_id("probe", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "second_run": self.second_run.to_document(),
            "exact_lift": (
                None
                if self.exact_lift is None
                else self.exact_lift.to_document()
            ),
            "probe_id": self.probe_id,
        }


def _model_for_audit(
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
) -> robust.PartialSupportIntervalModelV1:
    return (
        bridge.direct_model
        if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else bridge.quotient_model
    )


@dataclass(frozen=True, slots=True)
class _CounterfactualTaskV1:
    model: robust.PartialSupportIntervalModelV1
    audit: robust.RobustPlanAuditV1
    threshold: robust.RobustThresholdProfileV1
    projection: graph_model.GraphRowModelProjectionV1


def _counterfactual_task_v1(
    task: _CounterfactualTaskV1,
) -> expansion.RowOtherCounterfactualEvidenceV1:
    return expansion._candidate_evidence(
        task.model,
        task.audit,
        task.threshold,
        task.projection,
    )


@dataclass(frozen=True, slots=True)
class _AcquireChildRowTaskV1:
    context: observer.PublicGraphContextV1
    catalogue: observer.LegalActionCatalogueV1
    action: tuple[int, int, int]


def _acquire_child_row_task_v1(
    task: _AcquireChildRowTaskV1,
) -> acquisition.GraphPartialSupportRowV1:
    return acquisition.acquire_graph_partial_support_row_v1(
        task.context,
        task.catalogue,
        task.action,
        REGISTERED_NEW_CHILD_CHECKPOINT,
    )


def _build_context(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    caps: SecondSupportTransactionCapsV1,
) -> SecondSupportTransactionContextV1:
    audit = transaction1.audit
    if (
        audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "transaction 2 requires the registered failed transaction-1 audit"
        )
    first_replacement = transaction1.promoted_closure.replacement
    return SecondSupportTransactionContextV1(
        context.context_id,
        base_closure.closure_id,
        base_bridge.bridge_id,
        base_audit.audit_id,
        threshold.threshold_profile_id,
        first_replacement.authorization.authorization_id,
        first_replacement.replacement_id,
        transaction1.consumer_id,
        transaction1.promoted_closure.closure_id,
        transaction1.bridge.bridge_id,
        audit.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        first_replacement.parent_row.binding.row_id,
        first_replacement.parent_row.partial_row_id,
        first_replacement.promoted_row.partial_row_id,
        first_replacement.parent_row.physical_evidence_id,
        first_replacement.promoted_row.physical_evidence_id,
        tuple(
            sorted(
                (
                    first_replacement.authorization.authorization_id,
                    first_replacement.replacement_id,
                    transaction1.consumer_id,
                )
            )
        ),
        caps.cap_profile_id,
    )


def _validate_first_transaction(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    max_workers: int,
) -> None:
    del max_workers  # Scheduling width is not part of semantic validation.
    if (
        base_closure.validation_checkpoint != REGISTERED_BASE_CHECKPOINT
        or base_closure.context != context
        or base_bridge.context_id != context.context_id
        or base_audit.audit_id
        != transaction1.promoted_closure.replacement.authorization.parent_audit_id
        or base_bridge.bridge_id != transaction1.parent_bridge_id
        or threshold.threshold_profile_id
        != transaction1.threshold_profile_id
        or transaction1.promoted_closure.parent_closure.closure_id
        != base_closure.closure_id
        or transaction1.audit.solver_kind
        is not robust.RobustSolverKind.QUOTIENT
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "transaction-1 chain is stale or not the registered K6 quotient"
        )
    graph_model.verify_observation_support_graph_models_v1(
        context=context,
        root_catalogue=base_closure.root_catalogue,
        catalogues=(base_closure.root_catalogue, *base_closure.child_catalogues),
        partial_rows=base_closure.all_rows,
        bridge=base_bridge,
    )
    robust.verify_robust_plan_audit_v1(
        base_bridge.quotient_model,
        threshold,
        base_audit,
    )
    graph_model.verify_observation_support_graph_models_v1(
        context=context,
        root_catalogue=transaction1.promoted_closure.root_catalogue,
        catalogues=transaction1.promoted_closure.public_catalogues,
        partial_rows=transaction1.promoted_closure.all_rows,
        bridge=transaction1.bridge,
        coordinate_profile=relational.base_coordinate_profile_v1(),
    )
    robust.verify_robust_plan_audit_v1(
        transaction1.bridge.quotient_model,
        threshold,
        transaction1.audit,
    )


def _eligible_counterfactuals(
    *,
    context: SecondSupportTransactionContextV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    threshold: robust.RobustThresholdProfileV1,
    max_workers: int,
) -> tuple[
    tuple[expansion.RowOtherCounterfactualEvidenceV1, ...],
    dict[str, acquisition.GraphPartialSupportRowV1],
    dict[str, graph_model.GraphRowModelProjectionV1],
]:
    bridge = transaction1.bridge
    audit = transaction1.audit
    assert audit.failed_frontier is not None
    rows = transaction1.promoted_closure.all_rows
    model = _model_for_audit(bridge, audit)
    robust.verify_robust_plan_audit_v1(model, threshold, audit)
    by_partial = {row.partial_row_id: row for row in rows}
    by_planner = {
        item.planner_row.row_id: item for item in bridge.row_projections
    }
    other_positive = tuple(audit.failed_frontier.other_positive_row_ids)
    tasks: list[_CounterfactualTaskV1] = []
    for planner_row_id in other_positive:
        projection = by_planner.get(planner_row_id)
        if projection is None:
            raise ObservationSupportSecondTransactionInvariantViolation(
                "failed frontier references an unknown planner row"
            )
        row = by_partial[projection.partial_row_id]
        if (
            row.binding.row_id
            == context.transaction1_selected_binding_id
            or row.physical_evidence_id
            == context.transaction1_parent_physical_evidence_id
            or row.physical_evidence_id
            == context.transaction1_promoted_physical_evidence_id
            or row.support_epoch_index != 1
            or not row.novel_descriptors
        ):
            continue
        tasks.append(_CounterfactualTaskV1(model, audit, threshold, projection))
    if len(tasks) > MAX_COUNTERFACTUAL_ROWS:
        return (), by_partial, by_planner
    if max_workers == 1 or len(tasks) <= 1:
        raw = tuple(_counterfactual_task_v1(task) for task in tasks)
    else:
        with ProcessPoolExecutor(
            max_workers=min(max_workers, len(tasks)),
            mp_context=get_context("spawn"),
        ) as executor:
            raw = tuple(executor.map(_counterfactual_task_v1, tasks))
    return (
        tuple(sorted(raw, key=lambda item: item.evidence_id)),
        by_partial,
        by_planner,
    )


def _authorize_second_row(
    *,
    context: SecondSupportTransactionContextV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    threshold: robust.RobustThresholdProfileV1,
    candidates: tuple[
        expansion.RowOtherCounterfactualEvidenceV1, ...
    ],
    by_partial: Mapping[str, acquisition.GraphPartialSupportRowV1],
) -> DistinctRowExpansionAuthorizationV2 | None:
    causal = tuple(
        item for item in candidates if item.changes_failed_to_certified
    )
    if not causal:
        return None
    selected = min(
        causal,
        key=lambda item: (-item.remaining_horizon, item.planner_row_id),
    )
    parent = by_partial[selected.partial_row_id]
    audit = transaction1.audit
    assert audit.failed_frontier is not None
    model = _model_for_audit(transaction1.bridge, audit)
    return DistinctRowExpansionAuthorizationV2(
        context.transaction_context_id,
        transaction1.bridge.bridge_id,
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        threshold.threshold_profile_id,
        audit.solver_kind,
        transaction1.bridge.source_partial_row_ids,
        (context.transaction1_selected_binding_id,),
        tuple(
            sorted(
                (
                    context.transaction1_parent_physical_evidence_id,
                    context.transaction1_promoted_physical_evidence_id,
                )
            )
        ),
        candidates,
        selected.evidence_id,
        selected.planner_row_id,
        selected.partial_row_id,
        parent.binding.row_id,
        parent.physical_evidence_id,
        parent.support_epoch.support_epoch_id,
        parent.confidence_authority.authority_id,
        parent.binding.remaining_horizon,
        tuple(
            sorted(item.outcome_id for item in parent.novel_descriptors)
        ),
        REGISTERED_PROMOTION_CHECKPOINT,
    )


def _promote_second_row(
    *,
    context: observer.PublicGraphContextV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    authorization: DistinctRowExpansionAuthorizationV2,
) -> SecondPromotedRowReplacementV1:
    rows = transaction1.promoted_closure.all_rows
    by_partial = {row.partial_row_id: row for row in rows}
    parent = by_partial[authorization.selected_partial_row_id]
    catalogue, action = expansion._catalogue_for_selected_row(
        context=context,
        bridge=transaction1.bridge,
        parent=parent,
        rows=rows,
    )
    promoted = acquisition.promote_graph_partial_support_row_v1(
        parent,
        context,
        catalogue,
        action,
        REGISTERED_PROMOTION_CHECKPOINT,
    )
    return SecondPromotedRowReplacementV1(
        authorization,
        parent,
        promoted,
        tuple(
            sorted(
                {
                    *parent.initial_discovery_observation_ids,
                    *parent.prior_validation_observation_ids,
                    *parent.current_validation_observation_ids,
                }
            )
        ),
        tuple(sorted(promoted.current_validation_observation_ids)),
    )


def _replace_row(
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    replacement: SecondPromotedRowReplacementV1,
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    matches = sum(
        row.partial_row_id == replacement.parent_row.partial_row_id
        for row in rows
    )
    if matches not in (0, 1):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "second replacement parent is duplicated"
        )
    return _sorted_rows(
        replacement.promoted_row
        if row.partial_row_id == replacement.parent_row.partial_row_id
        else row
        for row in rows
    )


def _make_counters(
    *,
    candidates: tuple[
        expansion.RowOtherCounterfactualEvidenceV1, ...
    ],
    replacement: SecondPromotedRowReplacementV1,
    new_rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    new_catalogue_count: int,
    cap_rejections: int = 0,
) -> SecondSupportTransactionCountersV1:
    promoted = replacement.promoted_row.counters
    promotion_draws = promoted.current_validation_draws
    promotion_words = promoted.current_validation_random_word_calls
    promotion_rejections = promoted.current_validation_rejections
    child_discovery = sum(row.counters.discovery_draws for row in new_rows)
    child_validation = sum(
        row.counters.current_validation_draws for row in new_rows
    )
    child_words = sum(
        row.counters.total_random_word_calls for row in new_rows
    )
    child_rejections = sum(
        row.counters.total_rejections for row in new_rows
    )
    child_observer = child_discovery + child_validation
    return SecondSupportTransactionCountersV1(
        len(candidates),
        sum(item.changes_failed_to_certified for item in candidates),
        promotion_draws,
        promotion_words,
        promotion_rejections,
        new_catalogue_count,
        len(new_rows),
        child_discovery,
        child_validation,
        child_observer,
        child_words,
        child_rejections,
        promotion_draws + child_observer,
        promotion_words + child_words,
        promotion_rejections + child_rejections,
        4,
        cap_rejections,
    )


def _empty_counters(
    *,
    eligible_count: int,
    causal_count: int,
    cap_rejections: int,
) -> SecondSupportTransactionCountersV1:
    return SecondSupportTransactionCountersV1(
        eligible_count,
        causal_count,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        4,
        cap_rejections,
    )


def run_second_support_transaction_v1(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    max_workers: int = 1,
) -> SecondSupportTransactionRunV1:
    """Run the only permitted distinct-row transaction 2."""

    registered = _registered_k6(context)
    workers = _workers(max_workers)
    caps = registered_second_transaction_caps_v1()
    _validate_first_transaction(
        context=registered,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        max_workers=workers,
    )
    transaction_context = _build_context(
        context=registered,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        caps=caps,
    )
    assert transaction1.audit.failed_frontier is not None
    eligible_ids = tuple(
        transaction1.audit.failed_frontier.other_positive_row_ids
    )
    if len(eligible_ids) > caps.max_counterfactual_rows:
        counters = _empty_counters(
            eligible_count=len(eligible_ids),
            causal_count=0,
            cap_rejections=1,
        )
        return SecondSupportTransactionRunV1(
            transaction_context,
            SecondTransactionOutcome.COUNTERFACTUAL_CAP_EXHAUSTED,
            (),
            None,
            None,
            None,
            None,
            None,
            counters,
        )
    candidates, by_partial, _ = _eligible_counterfactuals(
        context=transaction_context,
        transaction1=transaction1,
        threshold=threshold,
        max_workers=workers,
    )
    authorization = _authorize_second_row(
        context=transaction_context,
        transaction1=transaction1,
        threshold=threshold,
        candidates=candidates,
        by_partial=by_partial,
    )
    if authorization is None:
        counters = _empty_counters(
            eligible_count=len(candidates),
            causal_count=0,
            cap_rejections=0,
        )
        return SecondSupportTransactionRunV1(
            transaction_context,
            SecondTransactionOutcome.NO_SOUND_DIFFERENT_ROW_COVER,
            candidates,
            None,
            None,
            None,
            None,
            None,
            counters,
        )
    replacement = _promote_second_row(
        context=registered,
        transaction1=transaction1,
        authorization=authorization,
    )
    first_closure = transaction1.promoted_closure
    root_rows = _replace_row(first_closure.root_rows, replacement)
    child_rows = _replace_row(first_closure.child_rows, replacement)
    if (
        replacement.parent_row.partial_row_id
        not in {row.partial_row_id for row in first_closure.all_rows}
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "authorized second parent is absent from transaction-1 closure"
        )
    child_catalogues = _sorted_catalogues(
        observer.legal_action_catalogue_v1(registered, state, 1)
        for state in _active_root_states(root_rows)
    )
    prior_catalogue_ids = {
        item.catalogue_id for item in first_closure.child_catalogues
    }
    new_catalogues = tuple(
        item
        for item in child_catalogues
        if item.catalogue_id not in prior_catalogue_ids
    )
    tasks = tuple(
        _AcquireChildRowTaskV1(registered, catalogue, action)
        for catalogue in new_catalogues
        for action in catalogue.actions
    )
    predicted_draws = REGISTERED_PROMOTION_CHECKPOINT + len(tasks) * (
        acquisition.DISCOVERY_DRAW_COUNT
        + REGISTERED_NEW_CHILD_CHECKPOINT
    )
    if (
        len(new_catalogues) > caps.max_new_child_catalogues
        or len(tasks) > caps.max_new_child_action_rows
        or predicted_draws > caps.max_incremental_observer_draws
    ):
        counters = _empty_counters(
            eligible_count=len(candidates),
            causal_count=sum(
                item.changes_failed_to_certified for item in candidates
            ),
            cap_rejections=1,
        )
        return SecondSupportTransactionRunV1(
            transaction_context,
            SecondTransactionOutcome.MATERIALIZATION_CAP_EXHAUSTED,
            candidates,
            None,
            None,
            None,
            None,
            None,
            counters,
        )
    if workers == 1 or len(tasks) <= 1:
        new_rows = tuple(_acquire_child_row_task_v1(task) for task in tasks)
    else:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(tasks)),
            mp_context=get_context("spawn"),
        ) as executor:
            new_rows = tuple(executor.map(_acquire_child_row_task_v1, tasks))
    new_rows = _sorted_rows(new_rows) if new_rows else ()
    child_rows = _sorted_rows((*child_rows, *new_rows))
    profile = relational.base_coordinate_profile_v1()
    if transaction1.coordinate_profile_id != profile.profile_id:
        raise ObservationSupportSecondTransactionInvariantViolation(
            "second transaction cannot silently change coordinate profile"
        )
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=registered,
        root_catalogue=first_closure.root_catalogue,
        catalogues=(first_closure.root_catalogue, *child_catalogues),
        partial_rows=(*root_rows, *child_rows),
        coordinate_profile=profile,
    )
    graph_model.verify_observation_support_graph_models_v1(
        context=registered,
        root_catalogue=first_closure.root_catalogue,
        catalogues=(first_closure.root_catalogue, *child_catalogues),
        partial_rows=(*root_rows, *child_rows),
        bridge=bridge,
        coordinate_profile=profile,
    )
    audit = robust.solve_quotient_robust_h2_v1(
        bridge.quotient_model,
        threshold,
    )
    robust.verify_robust_plan_audit_v1(
        bridge.quotient_model,
        threshold,
        audit,
    )
    counters = _make_counters(
        candidates=candidates,
        replacement=replacement,
        new_rows=new_rows,
        new_catalogue_count=len(new_catalogues),
    )
    epoch2_bindings = tuple(
        sorted(
            row.binding.row_id
            for row in (*root_rows, *child_rows)
            if row.support_epoch_index == 2
        )
    )
    closure = SecondPromotedH2ClosureV1(
        transaction_context.transaction_context_id,
        transaction1.consumer_id,
        replacement,
        registered,
        first_closure.root_catalogue,
        child_catalogues,
        root_rows,
        child_rows,
        epoch2_bindings,
        tuple(sorted(item.catalogue_id for item in new_catalogues)),
        tuple(sorted(item.partial_row_id for item in new_rows)),
        counters,
    )
    outcome = (
        SecondTransactionOutcome.CERTIFIED_AT_8192
        if audit.certified
        else SecondTransactionOutcome.FAILED_NEW_FRONTIER
    )
    return SecondSupportTransactionRunV1(
        transaction_context,
        outcome,
        candidates,
        authorization,
        replacement,
        closure,
        bridge,
        audit,
        counters,
    )


def run_k6_two_distinct_row_probe_v0(
    *,
    max_workers: int = 1,
) -> K6TwoDistinctRowProbeV0:
    """Build only K6@8192, then run transactions 1 and 2."""

    workers = _workers(max_workers)
    context = observer.public_context_by_key_v1(REGISTERED_CONTEXT_KEY)
    closure = h2_closure.acquire_observation_support_h2_closure_v1(
        context,
        REGISTERED_BASE_CHECKPOINT,
        max_workers=workers,
    )
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=(closure.root_catalogue, *closure.child_catalogues),
        partial_rows=closure.all_rows,
    )
    graph_model.verify_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=(closure.root_catalogue, *closure.child_catalogues),
        partial_rows=closure.all_rows,
        bridge=bridge,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
    )
    base_audit = robust.solve_quotient_robust_h2_v1(
        bridge.quotient_model,
        threshold,
    )
    robust.verify_robust_plan_audit_v1(
        bridge.quotient_model,
        threshold,
        base_audit,
    )
    authorization1 = expansion.authorize_partial_support_expansion_v1(
        bridge=bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=closure.all_rows,
        checkpoint_draw_count=REGISTERED_PROMOTION_CHECKPOINT,
    )
    replacement1 = expansion.promote_authorized_partial_support_row_v1(
        bridge=bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=closure.all_rows,
        authorization=authorization1,
    )
    transaction1 = (
        first_consumer.consume_partial_support_promoted_row_replacement_v1(
            context=context,
            parent_closure=closure,
            parent_bridge=bridge,
            parent_audit=base_audit,
            threshold=threshold,
            replacement=replacement1,
            new_child_validation_checkpoint=(
                REGISTERED_NEW_CHILD_CHECKPOINT
            ),
            max_workers=workers,
        )
    )
    second = run_second_support_transaction_v1(
        context=context,
        base_closure=closure,
        base_bridge=bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        max_workers=workers,
    )
    return freeze_k6_two_distinct_row_probe_v0(
        context=context,
        base_closure=closure,
        transaction1=transaction1,
        second_run=second,
    )


def freeze_k6_two_distinct_row_probe_v0(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    second_run: SecondSupportTransactionRunV1,
) -> K6TwoDistinctRowProbeV0:
    """Freeze a completed operational run before optional exact evaluation."""

    registered = _registered_k6(context)
    if (
        type(base_closure)
        is not h2_closure.ObservationSupportH2ClosureV1
        or base_closure.context != registered
        or base_closure.validation_checkpoint != REGISTERED_BASE_CHECKPOINT
        or type(transaction1)
        is not first_consumer.ObservationSupportPromotedH2ConsumerV1
        or type(second_run) is not SecondSupportTransactionRunV1
        or second_run.context.context_id != registered.context_id
        or second_run.context.base_closure_id != base_closure.closure_id
        or second_run.context.transaction1_consumer_id
        != transaction1.consumer_id
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "probe freeze inputs are stale or leave the bounded K6 chain"
        )
    exact = None
    if second_run.outcome is SecondTransactionOutcome.CERTIFIED_AT_8192:
        assert second_run.bridge is not None and second_run.audit is not None
        # The operational run object is fully materialized before this
        # evaluation-only exact authority is called.
        _ = second_run.run_id
        exact = exact_evaluation.evaluate_observation_support_exact_lift_v1(
            registered,
            second_run.bridge,
            second_run.audit,
            prerequisite_operational_freeze_id=second_run.run_id,
        )
        exact_evaluation.verify_observation_support_exact_lift_v1(
            registered,
            second_run.bridge,
            second_run.audit,
            exact,
        )
    return K6TwoDistinctRowProbeV0(
        registered.context_id,
        base_closure.closure_id,
        transaction1.consumer_id,
        second_run,
        exact,
    )


@dataclass(frozen=True, slots=True)
class SecondSupportTransactionVerificationV1:
    claimed_run_id: str
    replayed_run_id: str
    outcome: SecondTransactionOutcome
    valid: bool = True
    exact_iid_implementation_claimed: bool = False
    independent_algorithm_implementation: bool = False

    def __post_init__(self) -> None:
        _cid(self.claimed_run_id, "claimed second run")
        _cid(self.replayed_run_id, "replayed second run")
        if (
            self.claimed_run_id != self.replayed_run_id
            or type(self.outcome) is not SecondTransactionOutcome
            or self.valid is not True
            or self.exact_iid_implementation_claimed is not False
            or self.independent_algorithm_implementation is not False
        ):
            raise ObservationSupportSecondTransactionInvariantViolation(
                "second-transaction verification failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.second_support_transaction_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_run_id": self.claimed_run_id,
            "replayed_run_id": self.replayed_run_id,
            "outcome": self.outcome.value,
            "valid": True,
            "exact_iid_implementation_claimed": False,
            "independent_algorithm_implementation": False,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_second_support_transaction_v1(
    *,
    context: observer.PublicGraphContextV1,
    base_closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    transaction1: first_consumer.ObservationSupportPromotedH2ConsumerV1,
    claimed: SecondSupportTransactionRunV1,
    max_workers: int = 1,
) -> SecondSupportTransactionVerificationV1:
    """Replay the complete first-consumer chain and transaction 2.

    The operational consumer performs content-bound structural and semantic
    checks without a second full transaction-1 execution.  This standalone
    verifier intentionally pays for the complete V0-068 promoted-consumer
    replay before it independently replays transaction 2.
    """

    first_consumer.verify_partial_support_promoted_h2_consumer_v1(
        context=context,
        parent_closure=base_closure,
        parent_bridge=base_bridge,
        parent_audit=base_audit,
        threshold=threshold,
        replacement=transaction1.promoted_closure.replacement,
        claimed=transaction1,
        max_workers=max_workers,
    )

    replay = run_second_support_transaction_v1(
        context=context,
        base_closure=base_closure,
        base_bridge=base_bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        max_workers=max_workers,
    )
    if (
        type(claimed) is not SecondSupportTransactionRunV1
        or replay.run_id != claimed.run_id
        or canonical_json_bytes(replay.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise ObservationSupportSecondTransactionInvariantViolation(
            "second-transaction replay differs from the claim"
        )
    return SecondSupportTransactionVerificationV1(
        claimed.run_id,
        replay.run_id,
        replay.outcome,
    )


__all__ = [
    "CONTRACT_VERSION",
    "GLOBAL_16K_CHECKPOINT_FORBIDDEN",
    "K6TwoDistinctRowProbeV0",
    "MAX_COUNTERFACTUAL_ROWS",
    "MAX_INCREMENTAL_OBSERVER_DRAWS",
    "MAX_NEW_CHILD_ACTION_ROWS",
    "MAX_NEW_CHILD_CATALOGUES",
    "MAX_SUPPORT_TRANSACTIONS",
    "ObservationSupportSecondTransactionInvariantViolation",
    "PROFILE_KEY",
    "REGISTERED_BASE_CHECKPOINT",
    "REGISTERED_NEW_CHILD_CHECKPOINT",
    "REGISTERED_PROMOTION_CHECKPOINT",
    "SecondPromotedH2ClosureV1",
    "SecondPromotedRowReplacementV1",
    "SecondSupportTransactionCapsV1",
    "SecondSupportTransactionContextV1",
    "SecondSupportTransactionCountersV1",
    "SecondSupportTransactionRunV1",
    "SecondSupportTransactionVerificationV1",
    "SecondTransactionOutcome",
    "DistinctRowExpansionAuthorizationV2",
    "registered_second_transaction_caps_v1",
    "freeze_k6_two_distinct_row_probe_v0",
    "run_k6_two_distinct_row_probe_v0",
    "run_second_support_transaction_v1",
    "verify_second_support_transaction_v1",
]
