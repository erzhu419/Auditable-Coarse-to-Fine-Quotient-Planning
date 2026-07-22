"""Kernel-blind construction of a query-neutral partial RAPM from observations.

This module is the first observation-driven dynamics slice.  It deliberately
does not import a ground domain, an exact kernel, build coverage, a query, or a
planner.  Its only transition authority is an immutable observation log under
one frozen deterministic/stationary semantics profile.

An observed ground state--action row is therefore a point singleton.  A legal
but unobserved row remains the vacuous ``known mass + unknown simplex mass``
set, including an explicit out-of-catalog continuation boundary.  The model is
sound only relative to the trusted observation/action-catalogue contract.  It
is not a plan certificate, an exact quotient certificate, or an infeasibility
certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.1.0"
TYPED_COORDINATE_SCHEMA_VERSION = "1.2.0"
PROFILE_KEY = "lmb_deterministic_observation_partial_rapm_v0"

DOMAIN_TAGS = {
    "evidence_ledger": "acfqp:observation-evidence-ledger:v1",
    "semantics_profile": "acfqp:deterministic-observation-semantics:v1",
    "state": "acfqp:canonical-observed-state:v1",
    "ground_action": "acfqp:canonical-observed-ground-action:v1",
    "action_catalogue": "acfqp:trusted-complete-action-catalogue:v1",
    "coordinate_expression": "acfqp:frozen-coordinate-expression:v1",
    "coordinate_ancestry": "acfqp:coordinate-ancestry-reference:v1",
    "coordinate_proposal": "acfqp:frozen-coordinate-proposal:v1",
    "typed_state_coordinate_values": "acfqp:frozen-typed-state-coordinate-values:v2",
    "typed_action_coordinate_values": "acfqp:frozen-typed-action-coordinate-values:v2",
    "typed_coordinate_value_table": "acfqp:frozen-typed-coordinate-value-table:v2",
    "typed_coordinate_proposal": "acfqp:frozen-typed-coordinate-proposal:v2",
    "typed_action_coordinate_atom": "acfqp:frozen-typed-action-coordinate-atom:v2",
    "ground_row": "acfqp:observed-ground-row:v1",
    "acquisition_coverage": "acfqp:preregistered-observation-acquisition-coverage:v1",
    "acquisition_manifest": "acfqp:preregistered-observation-acquisition-manifest:v1",
    "observation": "acfqp:deterministic-transition-observation:v1",
    "log_manifest": "acfqp:observation-log-manifest:v1",
    "authority_event_binding": "acfqp:observation-authority-event-binding:v1",
    "observation_authority": "acfqp:preregistered-observation-authority:v1",
    "external_boundary": "acfqp:partial-rapm-external-boundary:v1",
    "joint_outcome_atom": "acfqp:partial-rapm-joint-outcome-atom:v1",
    "joint_simplex_constraint": "acfqp:partial-rapm-joint-simplex-constraint:v1",
    "coverage": "acfqp:observation-coverage:v1",
    "cell": "acfqp:partial-rapm-cell:v1",
    "semantic_action": "acfqp:partial-rapm-semantic-action:v1",
    "model": "acfqp:portable-partial-rapm:v1",
    "query_scoped_model": "acfqp:query-scoped-partial-rapm:v2",
    "query_scoped_multistep_model": "acfqp:query-scoped-partial-rapm:v3",
    "result": "acfqp:observation-partial-rapm-build-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("observation-partial RAPM domain tags must be unique")


class ObservationPartialRAPMInvariantViolation(ValueError):
    """A typed observation, ambiguity row, or authority binding is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, ValueError) as error:
        raise ObservationPartialRAPMInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _ground_row_id(state_id: str, ground_action_id: str) -> str:
    """Return the canonical state--action row identity used by every layer."""

    return _content_id(
        "ground_row",
        {
            "schema": "acfqp.observed_ground_row_key.v1",
            "state_id": state_id,
            "ground_action_id": ground_action_id,
        },
    )


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be nonempty text"
        )
    return value


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if type(value) not in (int, Fraction):
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be exact"
        )
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _require_stable_documents(items: tuple[Any, ...], field: str) -> None:
    """Reject nested values whose canonical representation changes on replay."""

    try:
        first = tuple(canonical_json_bytes(item.to_document()) for item in items)
        second = tuple(canonical_json_bytes(item.to_document()) for item in items)
    except (AttributeError, TypeError, ValueError) as error:
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} failed canonical stability"
        ) from error
    if first != second:
        raise ObservationPartialRAPMInvariantViolation(f"{field} is not canonically stable")


def _sorted_unique_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be an exact tuple"
        )
    if any(type(item) is not str for item in values):
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} rejects nested duck IDs before hashing"
        )
    for item in values:
        _cid(item, field)
    if values != tuple(sorted(set(values))):
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be unique and sorted"
        )
    return values


class EvidenceClass(str, Enum):
    ENVIRONMENT_INTERACTION = "ENVIRONMENT_INTERACTION"
    GENERATIVE_ORACLE_SAMPLE = "GENERATIVE_ORACLE_SAMPLE"
    EXACT_KERNEL_QUERY = "EXACT_KERNEL_QUERY"
    OFFLINE_LOGGED_OBSERVATION = "OFFLINE_LOGGED_OBSERVATION"
    SYNTHETIC_MODEL_ROLLOUT = "SYNTHETIC_MODEL_ROLLOUT"


class EvidenceLane(str, Enum):
    OFFLINE_SOURCE = "offline_source"
    ONLINE_TARGET = "online_target"
    OPERATIONAL_QUERY = "operational_query"
    STANDALONE_EVALUATION = "standalone_evaluation"


class PlanningKind(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


class CoordinateContext(str, Enum):
    STATE = "STATE"
    STATE_ACTION = "STATE_ACTION"


class CoordinateOperation(str, Enum):
    LEGAL_ACTION_COUNT = "legal_action_count"
    COMPLETES_MATCH = "completes_match"


class SuccessorKind(str, Enum):
    REGISTERED_STATE = "REGISTERED_STATE"
    EXTERNAL_STATE = "EXTERNAL_STATE"


class JointOutcomeKind(str, Enum):
    CONTINUATION = "CONTINUATION"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


class AmbiguityRowStatus(str, Enum):
    OBSERVED_SINGLETON = "OBSERVED_SINGLETON"
    MISSING_VACUOUS = "MISSING_VACUOUS"


class TypedActionAtomKind(str, Enum):
    INTEGER_LEQ = "INTEGER_LEQ"
    BOOLEAN_IDENTITY = "BOOLEAN_IDENTITY"
    UNIVERSAL_TRUE = "UNIVERSAL_TRUE"


@dataclass(frozen=True, order=True, slots=True)
class EvidenceCounterV1:
    lane: EvidenceLane
    evidence_class: EvidenceClass
    count: int

    def __post_init__(self) -> None:
        if type(self.lane) is not EvidenceLane or type(self.evidence_class) is not EvidenceClass:
            raise ObservationPartialRAPMInvariantViolation(
                "evidence counters require exact lane/class enums"
            )
        _integer(self.count, "evidence counter")

    def to_document(self) -> dict[str, Any]:
        return {
            "lane": self.lane.value,
            "evidence_class": self.evidence_class.value,
            "count": self.count,
        }


@dataclass(frozen=True, slots=True)
class EvidenceLedgerV1:
    counters: tuple[EvidenceCounterV1, ...]

    def __post_init__(self) -> None:
        if type(self.counters) is not tuple or any(
            type(item) is not EvidenceCounterV1 for item in self.counters
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "evidence ledger rejects duck counters before canonical access"
            )
        _require_stable_documents(self.counters, "evidence counters")
        expected_keys = tuple(
            sorted(
                product(tuple(EvidenceLane), tuple(EvidenceClass)),
                key=lambda item: (item[0].value, item[1].value),
            )
        )
        actual_keys = tuple((item.lane, item.evidence_class) for item in self.counters)
        if actual_keys != expected_keys:
            raise ObservationPartialRAPMInvariantViolation(
                "evidence ledger must contain every lane/class exactly once, including native zeros"
            )

    @classmethod
    def complete(
        cls,
        counts: Mapping[tuple[EvidenceLane, EvidenceClass], int] | None = None,
    ) -> "EvidenceLedgerV1":
        supplied = dict(counts or {})
        unknown = set(supplied) - set(product(tuple(EvidenceLane), tuple(EvidenceClass)))
        if unknown:
            raise ObservationPartialRAPMInvariantViolation(
                "evidence ledger contains an unknown lane/class key"
            )
        return cls(
            tuple(
                EvidenceCounterV1(lane, evidence_class, supplied.get((lane, evidence_class), 0))
                for lane, evidence_class in sorted(
                    product(tuple(EvidenceLane), tuple(EvidenceClass)),
                    key=lambda item: (item[0].value, item[1].value),
                )
            )
        )

    def count(self, lane: EvidenceLane, evidence_class: EvidenceClass) -> int:
        for row in self.counters:
            if row.lane is lane and row.evidence_class is evidence_class:
                return row.count
        raise AssertionError("complete evidence ledger lost a row")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_evidence_ledger.v1",
            "schema_version": SCHEMA_VERSION,
            "counters": [item.to_document() for item in self.counters],
        }

    @property
    def ledger_id(self) -> str:
        return _content_id("evidence_ledger", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "ledger_id": self.ledger_id}


@dataclass(frozen=True, order=True, slots=True)
class RewardFeatureCapV1:
    name: str
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        _text(self.name, "reward feature name")
        object.__setattr__(self, "lower", _fraction(self.lower, "reward lower cap"))
        object.__setattr__(self, "upper", _fraction(self.upper, "reward upper cap"))
        if self.lower > self.upper:
            raise ObservationPartialRAPMInvariantViolation(
                "reward feature lower cap exceeds upper cap"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lower": _fraction_document(self.lower),
            "upper": _fraction_document(self.upper),
        }


@dataclass(frozen=True, slots=True)
class DeterministicObservationProfileV1:
    structural_id: str
    trusted_observer_id: str
    reward_feature_caps: tuple[RewardFeatureCapV1, ...]
    horizon_cap: int
    profile_key: str = PROFILE_KEY
    dynamics_assumption: str = "DETERMINISTIC_STATIONARY"
    action_catalogue_semantics: str = "trusted_complete_legal_action_catalogue_v1"
    unknown_successor_scope: str = "registered_active_cells_plus_external_boundary"
    concretizer_rule: str = "uniform_over_distinct_ground_actions_v1"
    evidence_kind: str = "DETERMINISTIC_LOG_CONDITIONAL_SOUND_V1"
    query_neutral: bool = True
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.structural_id, "structural_id")
        _cid(self.trusted_observer_id, "trusted_observer_id")
        if (
            self.profile_key != PROFILE_KEY
            or self.dynamics_assumption != "DETERMINISTIC_STATIONARY"
            or self.action_catalogue_semantics != "trusted_complete_legal_action_catalogue_v1"
            or self.unknown_successor_scope
            != "registered_active_cells_plus_external_boundary"
            or self.concretizer_rule != "uniform_over_distinct_ground_actions_v1"
            or self.evidence_kind != "DETERMINISTIC_LOG_CONDITIONAL_SOUND_V1"
            or self.query_neutral is not True
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "deterministic observation profile was relaxed"
            )
        _integer(self.horizon_cap, "horizon_cap", 1)
        if type(self.reward_feature_caps) is not tuple or any(
            type(item) is not RewardFeatureCapV1 for item in self.reward_feature_caps
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "observation profile rejects duck reward caps before canonical access"
            )
        if not self.reward_feature_caps:
            raise ObservationPartialRAPMInvariantViolation(
                "reward feature caps must be nonempty"
            )
        _require_stable_documents(self.reward_feature_caps, "reward feature caps")
        cap_names = tuple(item.name for item in self.reward_feature_caps)
        if self.reward_feature_caps != tuple(sorted(set(self.reward_feature_caps))):
            raise ObservationPartialRAPMInvariantViolation(
                "reward feature caps must be nonempty, unique, and sorted"
            )
        if len(cap_names) != len(set(cap_names)):
            raise ObservationPartialRAPMInvariantViolation(
                "reward feature cap names must be unique"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.deterministic_observation_profile.v1",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "structural_id": self.structural_id,
            "trusted_observer_id": self.trusted_observer_id,
            "reward_feature_caps": [item.to_document() for item in self.reward_feature_caps],
            "horizon_cap": self.horizon_cap,
            "dynamics_assumption": self.dynamics_assumption,
            "action_catalogue_semantics": self.action_catalogue_semantics,
            "unknown_successor_scope": self.unknown_successor_scope,
            "concretizer_rule": self.concretizer_rule,
            "evidence_kind": self.evidence_kind,
            "query_neutral": self.query_neutral,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("semantics_profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class CanonicalStateObservationV1:
    state_key: str
    removed_mask: int
    buffer_counts: tuple[int, ...]
    status: str
    planning_kind: PlanningKind

    def __post_init__(self) -> None:
        _text(self.state_key, "state_key")
        _integer(self.removed_mask, "removed_mask")
        if (
            not self.buffer_counts
            or type(self.buffer_counts) is not tuple
            or any(type(value) is not int or value < 0 for value in self.buffer_counts)
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "buffer_counts must be a nonempty tuple of nonnegative integers"
            )
        _text(self.status, "state status")
        if type(self.planning_kind) is not PlanningKind:
            raise ObservationPartialRAPMInvariantViolation(
                "planning_kind requires the exact enum"
            )
        expected = {
            "active": PlanningKind.ACTIVE,
            "success": PlanningKind.SUCCESS,
            "failure": PlanningKind.FAILURE,
        }.get(self.status)
        if expected is None or expected is not self.planning_kind:
            raise ObservationPartialRAPMInvariantViolation(
                "state status/planning kind mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.canonical_observed_state.v1",
            "state_key": self.state_key,
            "removed_mask": self.removed_mask,
            "buffer_counts": list(self.buffer_counts),
            "status": self.status,
            "planning_kind": self.planning_kind.value,
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_id": self.state_id}


@dataclass(frozen=True, slots=True)
class CanonicalGroundActionV1:
    state_id: str
    action_key: str
    selected_type: int

    def __post_init__(self) -> None:
        _cid(self.state_id, "action state_id")
        _text(self.action_key, "action_key")
        _integer(self.selected_type, "selected_type")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.canonical_observed_ground_action.v1",
            "state_id": self.state_id,
            "action_key": self.action_key,
            "selected_type": self.selected_type,
        }

    @property
    def action_id(self) -> str:
        return _content_id("ground_action", self._payload())

    @property
    def ground_row_id(self) -> str:
        return _ground_row_id(self.state_id, self.action_id)

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "ground_action_id": self.action_id,
            "ground_row_id": self.ground_row_id,
        }


@dataclass(frozen=True, slots=True)
class TrustedCompleteActionCatalogueV1:
    state_id: str
    actions: tuple[CanonicalGroundActionV1, ...]
    trusted_observer_id: str
    complete: bool = True
    semantics_id: str = "trusted_complete_legal_action_catalogue_v1"

    def __post_init__(self) -> None:
        _cid(self.state_id, "catalogue state_id")
        _cid(self.trusted_observer_id, "catalogue trusted_observer_id")
        if self.complete is not True or self.semantics_id != (
            "trusted_complete_legal_action_catalogue_v1"
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "action catalogue must carry the frozen complete-catalogue authority"
            )
        if type(self.actions) is not tuple or any(
            type(action) is not CanonicalGroundActionV1 for action in self.actions
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "action catalogue rejects duck actions"
            )
        if any(action.state_id != self.state_id for action in self.actions):
            raise ObservationPartialRAPMInvariantViolation(
                "catalogue action belongs to another state"
            )
        action_ids = tuple(action.action_id for action in self.actions)
        if action_ids != tuple(sorted(set(action_ids))):
            raise ObservationPartialRAPMInvariantViolation(
                "catalogue actions must be unique and sorted by content ID"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.trusted_complete_action_catalogue.v1",
            "state_id": self.state_id,
            "ground_action_ids": [action.action_id for action in self.actions],
            "trusted_observer_id": self.trusted_observer_id,
            "complete": self.complete,
            "semantics_id": self.semantics_id,
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("action_catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


@dataclass(frozen=True, order=True, slots=True)
class FrozenCoordinateExpressionV1:
    context: CoordinateContext
    operation: CoordinateOperation

    def __post_init__(self) -> None:
        if type(self.context) is not CoordinateContext or type(self.operation) is not CoordinateOperation:
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate expression requires exact context/operation enums"
            )
        expected = {
            CoordinateOperation.LEGAL_ACTION_COUNT: CoordinateContext.STATE,
            CoordinateOperation.COMPLETES_MATCH: CoordinateContext.STATE_ACTION,
        }[self.operation]
        if self.context is not expected:
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate expression context/operation mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_coordinate_expression.v1",
            "context": self.context.value,
            "operation": self.operation.value,
        }

    @property
    def expression_id(self) -> str:
        return _content_id("coordinate_expression", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "expression_id": self.expression_id}


_FORBIDDEN_ANCESTRY_TOKENS = (
    "EXACT_TARGET",
    "TARGET_EXACT",
    "HOMOMORPHISM_CERTIFICATE",
    "TARGET_QUERY",
    "Q_VALUE",
    "POLICY",
    "J0",
)


@dataclass(frozen=True, order=True, slots=True)
class CoordinateAncestryRefV1:
    role: str
    artifact_id: str

    def __post_init__(self) -> None:
        role = _text(self.role, "coordinate ancestry role").upper()
        _cid(self.artifact_id, "coordinate ancestry artifact_id")
        if any(token in role for token in _FORBIDDEN_ANCESTRY_TOKENS):
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate ancestry imports a forbidden exact-target/query authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.coordinate_ancestry_reference.v1",
            "role": self.role,
            "artifact_id": self.artifact_id,
        }

    @property
    def ancestry_ref_id(self) -> str:
        return _content_id("coordinate_ancestry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "ancestry_ref_id": self.ancestry_ref_id}


@dataclass(frozen=True, slots=True)
class FrozenCoordinateProposalV1:
    state_expressions: tuple[FrozenCoordinateExpressionV1, ...]
    action_expressions: tuple[FrozenCoordinateExpressionV1, ...]
    ancestry: tuple[CoordinateAncestryRefV1, ...] = ()
    origin: str = "manual_preregistered_generated_ast_v1"
    query_neutral: bool = True
    target_exact_audit_used: bool = False

    def __post_init__(self) -> None:
        # Exact nested-type validation must precede sorting, hashing, property
        # access, or serialization.  Otherwise a hashable duck can run a
        # kernel/query getter before being rejected.
        if type(self.state_expressions) is not tuple or any(
            type(item) is not FrozenCoordinateExpressionV1
            for item in self.state_expressions
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate proposal rejects duck state expressions before canonical access"
            )
        if type(self.action_expressions) is not tuple or any(
            type(item) is not FrozenCoordinateExpressionV1
            for item in self.action_expressions
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate proposal rejects duck action expressions before canonical access"
            )
        _require_stable_documents(self.state_expressions, "state coordinate expressions")
        _require_stable_documents(self.action_expressions, "action coordinate expressions")
        if (
            self.state_expressions
            != tuple(sorted(set(self.state_expressions), key=lambda item: item.expression_id))
            or self.action_expressions
            != tuple(sorted(set(self.action_expressions), key=lambda item: item.expression_id))
            or not self.state_expressions
            or not self.action_expressions
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate expressions must be nonempty, unique, and content-ID sorted"
            )
        if any(item.context is not CoordinateContext.STATE for item in self.state_expressions):
            raise ObservationPartialRAPMInvariantViolation(
                "state coordinate proposal contains a state-action expression"
            )
        if any(item.context is not CoordinateContext.STATE_ACTION for item in self.action_expressions):
            raise ObservationPartialRAPMInvariantViolation(
                "action coordinate proposal contains a state-only expression"
            )
        if type(self.ancestry) is not tuple or any(
            type(item) is not CoordinateAncestryRefV1 for item in self.ancestry
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate proposal rejects duck ancestry"
            )
        # A role-name blacklist is not a trust boundary: a target exact
        # certificate can be benignly renamed.  V0-042 needs no upstream
        # authority, so production proposals remain ancestry-free until a
        # later contract adds a strict source-only schema/domain allowlist.
        if self.ancestry:
            raise ObservationPartialRAPMInvariantViolation(
                "V0-042 production coordinate proposal must be ancestry-free"
            )
        if (
            self.origin != "manual_preregistered_generated_ast_v1"
            or self.query_neutral is not True
            or self.target_exact_audit_used is not False
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "coordinate proposal imports target/query selection authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_coordinate_proposal.v1",
            "state_expression_ids": [item.expression_id for item in self.state_expressions],
            "action_expression_ids": [item.expression_id for item in self.action_expressions],
            "ancestry_ref_ids": [item.ancestry_ref_id for item in self.ancestry],
            "origin": self.origin,
            "query_neutral": self.query_neutral,
            "target_exact_audit_used": self.target_exact_audit_used,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("coordinate_proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


def _typed_coordinate_values(values: Any, field: str) -> tuple[int | bool, ...]:
    if type(values) is not tuple or any(type(value) not in (int, bool) for value in values):
        raise ObservationPartialRAPMInvariantViolation(
            f"{field} must be an exact tuple of integer/boolean scalars"
        )
    return values


def _typed_coordinate_value_document(value: int | bool) -> dict[str, Any]:
    if type(value) is bool:
        return {"kind": "BOOLEAN", "value": value}
    if type(value) is int:
        return {"kind": "INTEGER", "value": value}
    raise ObservationPartialRAPMInvariantViolation("typed coordinate scalar substitution")


@dataclass(frozen=True, slots=True)
class FrozenStateCoordinateValuesV2:
    state_id: str
    values: tuple[int | bool, ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "typed state-coordinate state_id")
        _typed_coordinate_values(self.values, "typed state-coordinate values")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_typed_state_coordinate_values.v2",
            "schema_version": TYPED_COORDINATE_SCHEMA_VERSION,
            "state_id": self.state_id,
            "values": [_typed_coordinate_value_document(value) for value in self.values],
        }

    @property
    def value_row_id(self) -> str:
        return _content_id("typed_state_coordinate_values", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "value_row_id": self.value_row_id}


@dataclass(frozen=True, slots=True)
class FrozenActionCoordinateValuesV2:
    ground_row_id: str
    state_id: str
    ground_action_id: str
    values: tuple[int | bool, ...]

    def __post_init__(self) -> None:
        _cid(self.ground_row_id, "typed action-coordinate ground_row_id")
        _cid(self.state_id, "typed action-coordinate state_id")
        _cid(self.ground_action_id, "typed action-coordinate ground_action_id")
        if self.ground_row_id != _ground_row_id(self.state_id, self.ground_action_id):
            raise ObservationPartialRAPMInvariantViolation(
                "typed action-coordinate ground-row identity mismatch"
            )
        _typed_coordinate_values(self.values, "typed action-coordinate values")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_typed_action_coordinate_values.v2",
            "schema_version": TYPED_COORDINATE_SCHEMA_VERSION,
            "ground_row_id": self.ground_row_id,
            "state_id": self.state_id,
            "ground_action_id": self.ground_action_id,
            "values": [_typed_coordinate_value_document(value) for value in self.values],
        }

    @property
    def value_row_id(self) -> str:
        return _content_id("typed_action_coordinate_values", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "value_row_id": self.value_row_id}


@dataclass(frozen=True, slots=True)
class FrozenTypedCoordinateValueTableV2:
    observation_log_id: str
    semantics_profile_id: str
    observation_authority_id: str
    structural_binding_id: str
    dsl_registry_id: str
    state_expression_ids: tuple[str, ...]
    action_expression_ids: tuple[str, ...]
    state_rows: tuple[FrozenStateCoordinateValuesV2, ...]
    action_rows: tuple[FrozenActionCoordinateValuesV2, ...]
    source_kind: str = "complete_preregistered_observation_source_graph_v1"
    callable_evaluator_present: bool = False
    schema_version: str = TYPED_COORDINATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "structural_binding_id",
            "dsl_registry_id",
        ):
            _cid(getattr(self, field), field)
        _sorted_unique_ids(self.state_expression_ids, "typed state expression IDs")
        _sorted_unique_ids(self.action_expression_ids, "typed action expression IDs")
        if type(self.state_rows) is not tuple or any(
            type(item) is not FrozenStateCoordinateValuesV2 for item in self.state_rows
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed value table rejects duck state rows before canonical access"
            )
        if type(self.action_rows) is not tuple or any(
            type(item) is not FrozenActionCoordinateValuesV2 for item in self.action_rows
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed value table rejects duck action rows before canonical access"
            )
        _require_stable_documents(self.state_rows, "typed state-coordinate rows")
        _require_stable_documents(self.action_rows, "typed action-coordinate rows")
        if tuple(item.state_id for item in self.state_rows) != tuple(
            sorted({item.state_id for item in self.state_rows})
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed state-coordinate rows must be unique and state-ID sorted"
            )
        if tuple(item.ground_row_id for item in self.action_rows) != tuple(
            sorted({item.ground_row_id for item in self.action_rows})
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed action-coordinate rows must be unique and ground-row-ID sorted"
            )
        if any(len(item.values) != len(self.state_expression_ids) for item in self.state_rows):
            raise ObservationPartialRAPMInvariantViolation(
                "typed state-coordinate row width mismatch"
            )
        if any(len(item.values) != len(self.action_expression_ids) for item in self.action_rows):
            raise ObservationPartialRAPMInvariantViolation(
                "typed action-coordinate row width mismatch"
            )
        if (
            self.source_kind != "complete_preregistered_observation_source_graph_v1"
            or self.callable_evaluator_present is not False
            or self.schema_version != TYPED_COORDINATE_SCHEMA_VERSION
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed coordinate value-table trust boundary was relaxed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_typed_coordinate_value_table.v2",
            "schema_version": self.schema_version,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "observation_authority_id": self.observation_authority_id,
            "structural_binding_id": self.structural_binding_id,
            "dsl_registry_id": self.dsl_registry_id,
            "state_expression_ids": list(self.state_expression_ids),
            "action_expression_ids": list(self.action_expression_ids),
            "state_rows": [item.to_document() for item in self.state_rows],
            "action_rows": [item.to_document() for item in self.action_rows],
            "source_kind": self.source_kind,
            "callable_evaluator_present": self.callable_evaluator_present,
        }

    @property
    def value_table_id(self) -> str:
        return _content_id("typed_coordinate_value_table", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "value_table_id": self.value_table_id}


@dataclass(frozen=True, slots=True)
class FrozenTypedActionCoordinateAtomV2:
    kind: TypedActionAtomKind
    source_expression_id: str | None
    threshold: Fraction | None

    def __post_init__(self) -> None:
        if type(self.kind) is not TypedActionAtomKind:
            raise ObservationPartialRAPMInvariantViolation(
                "typed action atom requires the exact kind enum"
            )
        if self.kind is TypedActionAtomKind.UNIVERSAL_TRUE:
            if self.source_expression_id is not None or self.threshold is not None:
                raise ObservationPartialRAPMInvariantViolation(
                    "universal action atom cannot carry a source or threshold"
                )
        elif self.kind is TypedActionAtomKind.BOOLEAN_IDENTITY:
            _cid(self.source_expression_id, "boolean action atom source expression")
            if self.threshold is not None:
                raise ObservationPartialRAPMInvariantViolation(
                    "boolean identity action atom cannot carry a threshold"
                )
        else:
            _cid(self.source_expression_id, "integer action atom source expression")
            if type(self.threshold) not in (int, Fraction):
                raise ObservationPartialRAPMInvariantViolation(
                    "integer action atom threshold must be exact"
                )
            object.__setattr__(self, "threshold", Fraction(self.threshold))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_typed_action_coordinate_atom.v2",
            "schema_version": TYPED_COORDINATE_SCHEMA_VERSION,
            "kind": self.kind.value,
            "source_expression_id": self.source_expression_id,
            "operator": (
                "<=" if self.kind is TypedActionAtomKind.INTEGER_LEQ
                else "IDENTITY" if self.kind is TypedActionAtomKind.BOOLEAN_IDENTITY
                else "UNIVERSAL_TRUE"
            ),
            "threshold": (
                _fraction_document(self.threshold) if self.threshold is not None else None
            ),
        }

    @property
    def atom_id(self) -> str:
        return _content_id("typed_action_coordinate_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class FrozenTypedCoordinateProposalV2:
    state_expression_ids: tuple[str, ...]
    action_expression_ids: tuple[str, ...]
    action_atoms: tuple[FrozenTypedActionCoordinateAtomV2, ...]
    dsl_registry_id: str
    structural_binding_id: str
    value_table_id: str
    synthesis_spec_id: str
    selected_candidate_id: str
    candidate_trace_id: str
    observation_log_id: str
    semantics_profile_id: str
    observation_authority_id: str
    acquisition_manifest_id: str
    origin: str = "observation_only_fixed_typed_dsl_synthesis_v1"
    query_neutral: bool = True
    target_exact_audit_used: bool = False
    callable_adapter_present: bool = False
    schema_version: str = TYPED_COORDINATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _sorted_unique_ids(self.state_expression_ids, "typed proposal state expression IDs")
        _sorted_unique_ids(self.action_expression_ids, "typed proposal action expression IDs")
        if type(self.action_atoms) is not tuple or any(
            type(item) is not FrozenTypedActionCoordinateAtomV2
            for item in self.action_atoms
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed proposal rejects duck action atoms before canonical access"
            )
        _require_stable_documents(self.action_atoms, "typed proposal action atoms")
        if not self.action_atoms or self.action_atoms != tuple(
            sorted({item.atom_id: item for item in self.action_atoms}.values(), key=lambda item: item.atom_id)
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed proposal action atoms must be nonempty, unique, and atom-ID sorted"
            )
        universal = tuple(
            item for item in self.action_atoms
            if item.kind is TypedActionAtomKind.UNIVERSAL_TRUE
        )
        if (not self.action_expression_ids and len(universal) != 1) or (
            self.action_expression_ids and universal
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "universal action atom is reserved for the empty action-program subset"
            )
        for field in (
            "dsl_registry_id",
            "structural_binding_id",
            "value_table_id",
            "synthesis_spec_id",
            "selected_candidate_id",
            "candidate_trace_id",
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "acquisition_manifest_id",
        ):
            _cid(getattr(self, field), field)
        if (
            self.origin != "observation_only_fixed_typed_dsl_synthesis_v1"
            or self.query_neutral is not True
            or self.target_exact_audit_used is not False
            or self.callable_adapter_present is not False
            or self.schema_version != TYPED_COORDINATE_SCHEMA_VERSION
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed coordinate proposal imports a query/target/callable authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_typed_coordinate_proposal.v2",
            "schema_version": self.schema_version,
            "state_expression_ids": list(self.state_expression_ids),
            "action_expression_ids": list(self.action_expression_ids),
            "action_atoms": [item.to_document() for item in self.action_atoms],
            "dsl_registry_id": self.dsl_registry_id,
            "structural_binding_id": self.structural_binding_id,
            "value_table_id": self.value_table_id,
            "synthesis_spec_id": self.synthesis_spec_id,
            "selected_candidate_id": self.selected_candidate_id,
            "candidate_trace_id": self.candidate_trace_id,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "observation_authority_id": self.observation_authority_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "origin": self.origin,
            "query_neutral": self.query_neutral,
            "target_exact_audit_used": self.target_exact_audit_used,
            "callable_adapter_present": self.callable_adapter_present,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("typed_coordinate_proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class ObservedSuccessorRefV1:
    kind: SuccessorKind
    reference: str

    def __post_init__(self) -> None:
        if type(self.kind) is not SuccessorKind:
            raise ObservationPartialRAPMInvariantViolation(
                "successor kind requires the exact enum"
            )
        _cid(self.reference, "successor reference")

    def to_document(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "reference": self.reference}


@dataclass(frozen=True, slots=True)
class DeterministicTransitionObservationV1:
    sequence_number: int
    state_id: str
    ground_action_id: str
    successor: ObservedSuccessorRefV1
    reward_features: tuple[tuple[str, Fraction], ...]
    failure: bool
    terminal: bool
    event_receipt_id: str
    evidence_class: EvidenceClass
    evidence_lane: EvidenceLane
    trusted_observer_id: str

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "observation sequence_number", 1)
        _cid(self.state_id, "observation state_id")
        _cid(self.ground_action_id, "observation ground_action_id")
        if type(self.successor) is not ObservedSuccessorRefV1:
            raise ObservationPartialRAPMInvariantViolation(
                "observation successor rejects duck values"
            )
        if type(self.reward_features) is not tuple:
            raise ObservationPartialRAPMInvariantViolation(
                "reward features must be a tuple"
            )
        if any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.reward_features
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "reward features reject nested duck pairs before canonical access"
            )
        normalized: list[tuple[str, Fraction]] = []
        for name, value in self.reward_features:
            normalized.append((_text(name, "reward feature name"), _fraction(value, "reward feature")))
        normalized_tuple = tuple(normalized)
        if normalized_tuple != tuple(sorted(set(normalized_tuple))):
            raise ObservationPartialRAPMInvariantViolation(
                "reward features must be unique and sorted"
            )
        object.__setattr__(self, "reward_features", normalized_tuple)
        if type(self.failure) is not bool or type(self.terminal) is not bool:
            raise ObservationPartialRAPMInvariantViolation(
                "failure/terminal markers must be booleans"
            )
        if self.failure and not self.terminal:
            raise ObservationPartialRAPMInvariantViolation(
                "a failure observation must terminate"
            )
        _cid(self.event_receipt_id, "observation event_receipt_id")
        if type(self.evidence_class) is not EvidenceClass or type(self.evidence_lane) is not EvidenceLane:
            raise ObservationPartialRAPMInvariantViolation(
                "observation evidence class/lane require exact enums"
            )
        if self.evidence_class is EvidenceClass.SYNTHETIC_MODEL_ROLLOUT:
            raise ObservationPartialRAPMInvariantViolation(
                "synthetic model rollout cannot become an observed dynamics row"
            )
        if self.evidence_class is EvidenceClass.EXACT_KERNEL_QUERY:
            raise ObservationPartialRAPMInvariantViolation(
                "construction-time exact-kernel evidence is forbidden in V0-042"
            )
        if (
            self.evidence_class is not EvidenceClass.OFFLINE_LOGGED_OBSERVATION
            or self.evidence_lane is not EvidenceLane.OFFLINE_SOURCE
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "V0-042 production accepts only preregistered offline-source logged observations"
            )
        _cid(self.trusted_observer_id, "observation trusted_observer_id")

    @property
    def ground_row_id(self) -> str:
        return _ground_row_id(self.state_id, self.ground_action_id)

    def outcome_payload(self) -> dict[str, Any]:
        return {
            "successor": self.successor.to_document(),
            "reward_features": [
                {"name": name, "value": _fraction_document(value)}
                for name, value in self.reward_features
            ],
            "failure": self.failure,
            "terminal": self.terminal,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.deterministic_transition_observation.v1",
            "sequence_number": self.sequence_number,
            "state_id": self.state_id,
            "ground_action_id": self.ground_action_id,
            "ground_row_id": self.ground_row_id,
            **self.outcome_payload(),
            "event_receipt_id": self.event_receipt_id,
            "evidence_class": self.evidence_class.value,
            "evidence_lane": self.evidence_lane.value,
            "trusted_observer_id": self.trusted_observer_id,
        }

    @property
    def observation_id(self) -> str:
        return _content_id("observation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observation_id": self.observation_id}


@dataclass(frozen=True, slots=True)
class PreregisteredAcquisitionManifestV1:
    structural_id: str
    environment_instance_id: str
    semantics_profile_id: str
    trusted_observer_id: str
    acquisition_protocol_id: str
    registered_state_ids: tuple[str, ...]
    registered_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    event_receipt_ids: tuple[str, ...]
    acquisition_query_inputs_used: int = 0
    authority_registry_freeze_sequence: int = 1
    query_registration_open_sequence: int = 2
    allowlist_registered_before_query: bool = True
    selection_rule: str = "preregistered_fixed_structural_state_action_rows_v1"
    evidence_class: EvidenceClass = EvidenceClass.OFFLINE_LOGGED_OBSERVATION
    evidence_lane: EvidenceLane = EvidenceLane.OFFLINE_SOURCE
    prequery_frozen: bool = True
    complete_for_declared_receipts: bool = True

    def __post_init__(self) -> None:
        for field in (
            "structural_id",
            "environment_instance_id",
            "semantics_profile_id",
            "trusted_observer_id",
            "acquisition_protocol_id",
        ):
            _cid(getattr(self, field), f"acquisition {field}")
        states = _sorted_unique_ids(self.registered_state_ids, "acquisition state IDs")
        rows = _sorted_unique_ids(
            self.registered_ground_row_ids, "acquisition registered row IDs"
        )
        observed = _sorted_unique_ids(
            self.observed_ground_row_ids, "acquisition observed row IDs"
        )
        receipts = _sorted_unique_ids(
            self.event_receipt_ids, "acquisition event receipt IDs"
        )
        if not states or not rows or not observed or not set(observed) <= set(rows):
            raise ObservationPartialRAPMInvariantViolation(
                "acquisition coverage/observed rows are incomplete or inconsistent"
            )
        if len(observed) != len(receipts):
            raise ObservationPartialRAPMInvariantViolation(
                "acquisition observed rows and event receipts must be one-to-one"
            )
        _integer(self.authority_registry_freeze_sequence, "authority registry freeze sequence", 1)
        _integer(self.query_registration_open_sequence, "query registration open sequence", 1)
        if (
            self.acquisition_query_inputs_used != 0
            or self.authority_registry_freeze_sequence
            >= self.query_registration_open_sequence
            or self.allowlist_registered_before_query is not True
            or self.selection_rule
            != "preregistered_fixed_structural_state_action_rows_v1"
            or type(self.evidence_class) is not EvidenceClass
            or self.evidence_class is not EvidenceClass.OFFLINE_LOGGED_OBSERVATION
            or type(self.evidence_lane) is not EvidenceLane
            or self.evidence_lane is not EvidenceLane.OFFLINE_SOURCE
            or self.prequery_frozen is not True
            or self.complete_for_declared_receipts is not True
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "acquisition manifest is not the frozen pre-query offline profile"
            )

    @property
    def coverage_id(self) -> str:
        return _content_id(
            "acquisition_coverage",
            {
                "schema": "acfqp.preregistered_observation_acquisition_coverage.v1",
                "registered_state_ids": list(self.registered_state_ids),
                "registered_ground_row_ids": list(self.registered_ground_row_ids),
                "observed_ground_row_ids": list(self.observed_ground_row_ids),
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.preregistered_observation_acquisition_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "semantics_profile_id": self.semantics_profile_id,
            "trusted_observer_id": self.trusted_observer_id,
            "acquisition_protocol_id": self.acquisition_protocol_id,
            "coverage_id": self.coverage_id,
            "registered_state_ids": list(self.registered_state_ids),
            "registered_ground_row_ids": list(self.registered_ground_row_ids),
            "observed_ground_row_ids": list(self.observed_ground_row_ids),
            "event_receipt_ids": list(self.event_receipt_ids),
            "acquisition_query_inputs_used": self.acquisition_query_inputs_used,
            "authority_registry_freeze_sequence": self.authority_registry_freeze_sequence,
            "query_registration_open_sequence": self.query_registration_open_sequence,
            "allowlist_registered_before_query": self.allowlist_registered_before_query,
            "selection_rule": self.selection_rule,
            "evidence_class": self.evidence_class.value,
            "evidence_lane": self.evidence_lane.value,
            "prequery_frozen": self.prequery_frozen,
            "complete_for_declared_receipts": self.complete_for_declared_receipts,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("acquisition_manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


@dataclass(frozen=True, order=True, slots=True)
class ObservationAuthorityEventBindingV1:
    event_receipt_id: str
    observation_id: str
    ground_row_id: str
    evidence_class: EvidenceClass
    evidence_lane: EvidenceLane

    def __post_init__(self) -> None:
        if type(self.evidence_class) is not EvidenceClass or type(self.evidence_lane) is not EvidenceLane:
            raise ObservationPartialRAPMInvariantViolation(
                "authority event binding requires exact evidence enums"
            )
        for field in ("event_receipt_id", "observation_id", "ground_row_id"):
            _cid(getattr(self, field), f"authority event {field}")
        if (
            self.evidence_class is not EvidenceClass.OFFLINE_LOGGED_OBSERVATION
            or self.evidence_lane is not EvidenceLane.OFFLINE_SOURCE
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "authority event binding is outside the V0-042 evidence matrix cell"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_authority_event_binding.v1",
            "event_receipt_id": self.event_receipt_id,
            "observation_id": self.observation_id,
            "ground_row_id": self.ground_row_id,
            "evidence_class": self.evidence_class.value,
            "evidence_lane": self.evidence_lane.value,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("authority_event_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class PreregisteredObservationAuthorityV1:
    acquisition_manifest: PreregisteredAcquisitionManifestV1
    structural_id: str
    environment_instance_id: str
    semantics_profile_id: str
    trusted_observer_id: str
    observation_log_id: str
    evidence_ledger_id: str
    state_ids: tuple[str, ...]
    action_catalogue_ids: tuple[str, ...]
    event_bindings: tuple[ObservationAuthorityEventBindingV1, ...]
    trust_root_key: str = "acfqp_v0_042_preregistered_offline_observer_root_v1"
    action_catalogues_complete_asserted: bool = True
    deterministic_stationary_asserted: bool = True
    observation_source_authenticity_asserted: bool = True
    in_memory_exact_graph_required: bool = True
    transport_authority_claimed: bool = False

    def __post_init__(self) -> None:
        # The exact nested graph is checked before any ID/property access.
        if type(self.acquisition_manifest) is not PreregisteredAcquisitionManifestV1:
            raise ObservationPartialRAPMInvariantViolation(
                "observation authority rejects duck acquisition manifests before canonical access"
            )
        _require_stable_documents((self.acquisition_manifest,), "authority acquisition manifest")
        if type(self.event_bindings) is not tuple or any(
            type(item) is not ObservationAuthorityEventBindingV1
            for item in self.event_bindings
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "observation authority rejects duck event bindings before canonical access"
            )
        _require_stable_documents(self.event_bindings, "authority event bindings")
        for field in (
            "structural_id",
            "environment_instance_id",
            "semantics_profile_id",
            "trusted_observer_id",
            "observation_log_id",
            "evidence_ledger_id",
        ):
            _cid(getattr(self, field), f"authority {field}")
        states = _sorted_unique_ids(self.state_ids, "authority state IDs")
        catalogues = _sorted_unique_ids(
            self.action_catalogue_ids, "authority action catalogue IDs"
        )
        binding_ids = tuple(item.binding_id for item in self.event_bindings)
        if binding_ids != tuple(sorted(set(binding_ids))):
            raise ObservationPartialRAPMInvariantViolation(
                "authority event bindings must be unique and content-ID sorted"
            )
        if tuple(sorted(item.event_receipt_id for item in self.event_bindings)) != (
            self.acquisition_manifest.event_receipt_ids
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "authority event receipts differ from the acquisition manifest"
            )
        if tuple(sorted(item.ground_row_id for item in self.event_bindings)) != (
            self.acquisition_manifest.observed_ground_row_ids
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "authority observed rows differ from the acquisition manifest"
            )
        if (
            self.structural_id != self.acquisition_manifest.structural_id
            or self.environment_instance_id
            != self.acquisition_manifest.environment_instance_id
            or self.semantics_profile_id
            != self.acquisition_manifest.semantics_profile_id
            or self.trusted_observer_id
            != self.acquisition_manifest.trusted_observer_id
            or states != self.acquisition_manifest.registered_state_ids
            or len(catalogues) != len(states)
            or self.trust_root_key
            != "acfqp_v0_042_preregistered_offline_observer_root_v1"
            or self.action_catalogues_complete_asserted is not True
            or self.deterministic_stationary_asserted is not True
            or self.observation_source_authenticity_asserted is not True
            or self.in_memory_exact_graph_required is not True
            or self.transport_authority_claimed is not False
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "observation authority is not the frozen preregistered trust-root profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.preregistered_observation_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "trust_root_key": self.trust_root_key,
            "acquisition_manifest_id": self.acquisition_manifest.manifest_id,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "semantics_profile_id": self.semantics_profile_id,
            "trusted_observer_id": self.trusted_observer_id,
            "observation_log_id": self.observation_log_id,
            "evidence_ledger_id": self.evidence_ledger_id,
            "state_ids": list(self.state_ids),
            "action_catalogue_ids": list(self.action_catalogue_ids),
            "event_bindings": [item.to_document() for item in self.event_bindings],
            "action_catalogues_complete_asserted": self.action_catalogues_complete_asserted,
            "deterministic_stationary_asserted": self.deterministic_stationary_asserted,
            "observation_source_authenticity_asserted": self.observation_source_authenticity_asserted,
            "in_memory_exact_graph_required": self.in_memory_exact_graph_required,
            "transport_authority_claimed": self.transport_authority_claimed,
        }

    @property
    def authority_id(self) -> str:
        return _content_id("observation_authority", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authority_id": self.authority_id}


# This is an external trust-root registry, not a claim that hashes prove source
# truth.  New acquisition fixtures require a contract/registry revision.
PREREGISTERED_OBSERVATION_AUTHORITY_IDS = frozenset(
    {"5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825"}
)


@dataclass(frozen=True, slots=True)
class ObservationLogManifestV1:
    structural_id: str
    environment_instance_id: str
    semantics_profile_id: str
    acquisition_manifest_id: str
    states: tuple[CanonicalStateObservationV1, ...]
    action_catalogues: tuple[TrustedCompleteActionCatalogueV1, ...]
    observations: tuple[DeterministicTransitionObservationV1, ...]
    evidence_ledger: EvidenceLedgerV1

    def __post_init__(self) -> None:
        _cid(self.structural_id, "log structural_id")
        _cid(self.environment_instance_id, "environment_instance_id")
        _cid(self.semantics_profile_id, "semantics_profile_id")
        _cid(self.acquisition_manifest_id, "log acquisition_manifest_id")
        if type(self.evidence_ledger) is not EvidenceLedgerV1:
            raise ObservationPartialRAPMInvariantViolation(
                "log rejects duck evidence ledgers"
            )
        if (
            not self.states
            or type(self.states) is not tuple
            or any(type(item) is not CanonicalStateObservationV1 for item in self.states)
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "log requires exact state observation tuples"
            )
        state_ids = tuple(item.state_id for item in self.states)
        if state_ids != tuple(sorted(set(state_ids))):
            raise ObservationPartialRAPMInvariantViolation(
                "log states must be unique and content-ID sorted"
            )
        if type(self.action_catalogues) is not tuple or any(
            type(item) is not TrustedCompleteActionCatalogueV1
            for item in self.action_catalogues
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "log rejects duck action catalogues"
            )
        catalogue_state_ids = tuple(item.state_id for item in self.action_catalogues)
        if catalogue_state_ids != state_ids:
            raise ObservationPartialRAPMInvariantViolation(
                "log needs exactly one sorted complete action catalogue per state"
            )
        state_by_id = {item.state_id: item for item in self.states}
        action_by_id: dict[str, CanonicalGroundActionV1] = {}
        for catalogue in self.action_catalogues:
            state = state_by_id[catalogue.state_id]
            if state.planning_kind is PlanningKind.ACTIVE and not catalogue.actions:
                raise ObservationPartialRAPMInvariantViolation(
                    "active state has an empty complete action catalogue"
                )
            if state.planning_kind is not PlanningKind.ACTIVE and catalogue.actions:
                raise ObservationPartialRAPMInvariantViolation(
                    "terminal state action catalogue must be empty"
                )
            for action in catalogue.actions:
                if action.selected_type >= len(state.buffer_counts):
                    raise ObservationPartialRAPMInvariantViolation(
                        "action selected_type lies outside the observed buffer vector"
                    )
                if action.action_id in action_by_id:
                    raise ObservationPartialRAPMInvariantViolation(
                        "ground action IDs must be globally unique"
                    )
                action_by_id[action.action_id] = action
        if type(self.observations) is not tuple or any(
            type(item) is not DeterministicTransitionObservationV1
            for item in self.observations
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "log rejects duck transition observations"
            )
        sequences = tuple(item.sequence_number for item in self.observations)
        if sequences != tuple(range(1, len(self.observations) + 1)):
            raise ObservationPartialRAPMInvariantViolation(
                "observation sequence numbers must be contiguous and ordered"
            )
        receipt_ids = tuple(item.event_receipt_id for item in self.observations)
        observation_ids = tuple(item.observation_id for item in self.observations)
        if len(set(receipt_ids)) != len(receipt_ids):
            raise ObservationPartialRAPMInvariantViolation(
                "observation event receipts must be globally unique"
            )
        if len(set(observation_ids)) != len(observation_ids):
            raise ObservationPartialRAPMInvariantViolation(
                "observation IDs must be globally unique"
            )
        cap_by_name: dict[str, RewardFeatureCapV1] | None = None
        row_outcomes: dict[str, dict[str, Any]] = {}
        observed_counts: dict[tuple[EvidenceLane, EvidenceClass], int] = {}
        for observation in self.observations:
            if observation.state_id not in state_by_id:
                raise ObservationPartialRAPMInvariantViolation(
                    "observation references an unregistered source state"
                )
            action = action_by_id.get(observation.ground_action_id)
            if action is None or action.state_id != observation.state_id:
                raise ObservationPartialRAPMInvariantViolation(
                    "observation action is absent from its trusted complete catalogue"
                )
            if observation.successor.kind is SuccessorKind.REGISTERED_STATE:
                successor = state_by_id.get(observation.successor.reference)
                if successor is None:
                    raise ObservationPartialRAPMInvariantViolation(
                        "registered successor is absent from the state catalogue"
                    )
                successor_terminal = successor.planning_kind is not PlanningKind.ACTIVE
                if successor_terminal != observation.terminal:
                    raise ObservationPartialRAPMInvariantViolation(
                        "registered successor planning kind disagrees with terminal marker"
                    )
                if (
                    successor.planning_kind is PlanningKind.FAILURE
                ) != observation.failure:
                    raise ObservationPartialRAPMInvariantViolation(
                        "registered successor planning kind disagrees with failure marker"
                    )
            else:
                if observation.successor.reference in state_by_id:
                    raise ObservationPartialRAPMInvariantViolation(
                        "external successor reference aliases a registered state"
                    )
                if observation.failure or observation.terminal:
                    raise ObservationPartialRAPMInvariantViolation(
                        "V0 external successor is active, nonterminal and nonfailure"
                    )
            outcome = observation.outcome_payload()
            incumbent = row_outcomes.get(observation.ground_row_id)
            if incumbent is not None:
                if incumbent != outcome:
                    raise ObservationPartialRAPMInvariantViolation(
                        "deterministic duplicate observations conflict"
                    )
                raise ObservationPartialRAPMInvariantViolation(
                    "deterministic observation replay of one ground row is forbidden"
                )
            row_outcomes[observation.ground_row_id] = outcome
            key = (observation.evidence_lane, observation.evidence_class)
            observed_counts[key] = observed_counts.get(key, 0) + 1
        for lane, evidence_class in product(tuple(EvidenceLane), tuple(EvidenceClass)):
            if self.evidence_ledger.count(lane, evidence_class) != observed_counts.get(
                (lane, evidence_class), 0
            ):
                raise ObservationPartialRAPMInvariantViolation(
                    "evidence ledger does not exactly reconcile transition observations"
                )

    def validate_against_profile(
        self, profile: DeterministicObservationProfileV1
    ) -> None:
        if type(profile) is not DeterministicObservationProfileV1:
            raise ObservationPartialRAPMInvariantViolation(
                "log validation rejects duck semantics profiles"
            )
        if (
            self.structural_id != profile.structural_id
            or self.semantics_profile_id != profile.profile_id
            or any(
                item.trusted_observer_id != profile.trusted_observer_id
                for item in self.action_catalogues
            )
            or any(
                item.trusted_observer_id != profile.trusted_observer_id
                for item in self.observations
            )
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "log/profile structural or trusted-observer binding mismatch"
            )
        caps = {item.name: item for item in profile.reward_feature_caps}
        for observation in self.observations:
            values = dict(observation.reward_features)
            if set(values) - set(caps):
                raise ObservationPartialRAPMInvariantViolation(
                    "observation uses an unregistered reward feature"
                )
            for name, cap in caps.items():
                value = values.get(name, Fraction(0))
                if not cap.lower <= value <= cap.upper:
                    raise ObservationPartialRAPMInvariantViolation(
                        "observation reward lies outside the structural cap"
                    )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_log_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "semantics_profile_id": self.semantics_profile_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "states": [item.to_document() for item in self.states],
            "action_catalogues": [item.to_document() for item in self.action_catalogues],
            "observations": [item.to_document() for item in self.observations],
            "evidence_ledger": self.evidence_ledger.to_document(),
        }

    @property
    def log_id(self) -> str:
        return _content_id("log_manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


def _validate_preregistered_observation_authority_v1(
    log: ObservationLogManifestV1,
    profile: DeterministicObservationProfileV1,
    authority: PreregisteredObservationAuthorityV1,
) -> None:
    _validate_preregistered_observation_source_runtime_types_v1(
        log, profile, authority
    )
    if type(authority) is not PreregisteredObservationAuthorityV1:
        raise ObservationPartialRAPMInvariantViolation(
            "builder rejects duck observation authorities"
        )
    if authority.authority_id not in PREREGISTERED_OBSERVATION_AUTHORITY_IDS:
        raise ObservationPartialRAPMInvariantViolation(
            "observation authority is absent from the frozen preregistered allowlist"
        )
    acquisition = authority.acquisition_manifest
    state_ids = tuple(item.state_id for item in log.states)
    catalogue_ids = tuple(sorted(item.catalogue_id for item in log.action_catalogues))
    registered_rows = tuple(
        sorted(
            action.ground_row_id
            for catalogue in log.action_catalogues
            for action in catalogue.actions
        )
    )
    observed_rows = tuple(sorted(item.ground_row_id for item in log.observations))
    receipt_ids = tuple(sorted(item.event_receipt_id for item in log.observations))
    event_bindings = tuple(
        sorted(
            (
                ObservationAuthorityEventBindingV1(
                    item.event_receipt_id,
                    item.observation_id,
                    item.ground_row_id,
                    item.evidence_class,
                    item.evidence_lane,
                )
                for item in log.observations
            ),
            key=lambda item: item.binding_id,
        )
    )
    if (
        authority.structural_id != log.structural_id
        or authority.environment_instance_id != log.environment_instance_id
        or authority.semantics_profile_id != log.semantics_profile_id
        or authority.trusted_observer_id != profile.trusted_observer_id
        or authority.observation_log_id != log.log_id
        or authority.evidence_ledger_id != log.evidence_ledger.ledger_id
        or authority.state_ids != state_ids
        or authority.action_catalogue_ids != catalogue_ids
        or authority.event_bindings != event_bindings
        or acquisition.manifest_id != log.acquisition_manifest_id
        or acquisition.structural_id != log.structural_id
        or acquisition.environment_instance_id != log.environment_instance_id
        or acquisition.semantics_profile_id != log.semantics_profile_id
        or acquisition.trusted_observer_id != profile.trusted_observer_id
        or acquisition.registered_state_ids != state_ids
        or acquisition.registered_ground_row_ids != registered_rows
        or acquisition.observed_ground_row_ids != observed_rows
        or acquisition.event_receipt_ids != receipt_ids
        or acquisition.acquisition_query_inputs_used != 0
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "observation log differs from its preregistered authority binding"
        )
    log.validate_against_profile(profile)


def _validate_preregistered_observation_source_runtime_types_v1(
    log: ObservationLogManifestV1,
    profile: DeterministicObservationProfileV1,
    authority: PreregisteredObservationAuthorityV1,
) -> None:
    """Reject nested substitutions before any content-ID/property replay.

    The source graph is retained in memory, so a frozen dataclass can still be
    corrupted with low-level mutation after its constructor has run.  This pass
    deliberately checks the complete nested runtime shape before the authority
    validator reads ``authority_id``, ``log_id`` or any other derived property.
    """

    if type(log) is not ObservationLogManifestV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects duck observation logs"
        )
    if type(profile) is not DeterministicObservationProfileV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects duck semantics profiles"
        )
    if type(authority) is not PreregisteredObservationAuthorityV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects duck observation authorities"
        )

    def require_fields(
        instance: Any,
        specification: tuple[tuple[str, tuple[type, ...]], ...],
        scope: str,
    ) -> None:
        for field, allowed in specification:
            value = object.__getattribute__(instance, field)
            if type(value) not in allowed:
                raise ObservationPartialRAPMInvariantViolation(
                    f"source replay rejects malformed {scope}.{field} before canonical access"
                )

    require_fields(
        profile,
        (
            ("structural_id", (str,)),
            ("trusted_observer_id", (str,)),
            ("reward_feature_caps", (tuple,)),
            ("horizon_cap", (int,)),
            ("profile_key", (str,)),
            ("dynamics_assumption", (str,)),
            ("action_catalogue_semantics", (str,)),
            ("unknown_successor_scope", (str,)),
            ("concretizer_rule", (str,)),
            ("evidence_kind", (str,)),
            ("query_neutral", (bool,)),
            ("schema_version", (str,)),
        ),
        "semantics profile",
    )

    if type(profile.reward_feature_caps) is not tuple or any(
        type(item) is not RewardFeatureCapV1 for item in profile.reward_feature_caps
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested reward-cap substitutions before canonical access"
        )
    for cap in profile.reward_feature_caps:
        require_fields(
            cap,
            (("name", (str,)), ("lower", (Fraction,)), ("upper", (Fraction,))),
            "reward cap",
        )

    require_fields(
        log,
        (
            ("structural_id", (str,)),
            ("environment_instance_id", (str,)),
            ("semantics_profile_id", (str,)),
            ("acquisition_manifest_id", (str,)),
            ("states", (tuple,)),
            ("action_catalogues", (tuple,)),
            ("observations", (tuple,)),
            ("evidence_ledger", (EvidenceLedgerV1,)),
        ),
        "observation log",
    )

    if type(log.evidence_ledger) is not EvidenceLedgerV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested evidence-ledger substitutions before canonical access"
        )
    if type(log.evidence_ledger.counters) is not tuple or any(
        type(item) is not EvidenceCounterV1
        for item in log.evidence_ledger.counters
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested evidence-counter substitutions before canonical access"
        )
    for counter in log.evidence_ledger.counters:
        require_fields(
            counter,
            (
                ("lane", (EvidenceLane,)),
                ("evidence_class", (EvidenceClass,)),
                ("count", (int,)),
            ),
            "evidence counter",
        )
    if type(log.states) is not tuple or any(
        type(item) is not CanonicalStateObservationV1 for item in log.states
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested state substitutions before canonical access"
        )
    if any(
        type(item.buffer_counts) is not tuple
        or any(type(value) is not int for value in item.buffer_counts)
        or type(item.planning_kind) is not PlanningKind
        for item in log.states
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects malformed nested state values before canonical access"
        )
    for state in log.states:
        require_fields(
            state,
            (
                ("state_key", (str,)),
                ("removed_mask", (int,)),
                ("buffer_counts", (tuple,)),
                ("status", (str,)),
                ("planning_kind", (PlanningKind,)),
            ),
            "state",
        )
    if type(log.action_catalogues) is not tuple or any(
        type(item) is not TrustedCompleteActionCatalogueV1
        for item in log.action_catalogues
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested action-catalogue substitutions before canonical access"
        )
    if any(
        type(item.actions) is not tuple
        or any(type(action) is not CanonicalGroundActionV1 for action in item.actions)
        for item in log.action_catalogues
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested ground-action substitutions before canonical access"
        )
    for catalogue in log.action_catalogues:
        require_fields(
            catalogue,
            (
                ("state_id", (str,)),
                ("actions", (tuple,)),
                ("trusted_observer_id", (str,)),
                ("complete", (bool,)),
                ("semantics_id", (str,)),
            ),
            "action catalogue",
        )
        for action in catalogue.actions:
            require_fields(
                action,
                (
                    ("state_id", (str,)),
                    ("action_key", (str,)),
                    ("selected_type", (int,)),
                ),
                "ground action",
            )
    if type(log.observations) is not tuple or any(
        type(item) is not DeterministicTransitionObservationV1
        for item in log.observations
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested transition substitutions before canonical access"
        )
    for observation in log.observations:
        if type(observation.successor) is not ObservedSuccessorRefV1:
            raise ObservationPartialRAPMInvariantViolation(
                "source replay rejects nested successor substitutions before canonical access"
            )
        if type(observation.reward_features) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in observation.reward_features
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "source replay rejects nested reward substitutions before canonical access"
            )
        if (
            type(observation.successor.kind) is not SuccessorKind
            or type(observation.evidence_class) is not EvidenceClass
            or type(observation.evidence_lane) is not EvidenceLane
            or type(observation.failure) is not bool
            or type(observation.terminal) is not bool
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "source replay rejects malformed transition markers before canonical access"
            )
        require_fields(
            observation.successor,
            (("kind", (SuccessorKind,)), ("reference", (str,))),
            "successor",
        )
        require_fields(
            observation,
            (
                ("sequence_number", (int,)),
                ("state_id", (str,)),
                ("ground_action_id", (str,)),
                ("successor", (ObservedSuccessorRefV1,)),
                ("reward_features", (tuple,)),
                ("failure", (bool,)),
                ("terminal", (bool,)),
                ("event_receipt_id", (str,)),
                ("evidence_class", (EvidenceClass,)),
                ("evidence_lane", (EvidenceLane,)),
                ("trusted_observer_id", (str,)),
            ),
            "transition observation",
        )

    if type(authority.acquisition_manifest) is not PreregisteredAcquisitionManifestV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested acquisition substitutions before canonical access"
        )
    acquisition = authority.acquisition_manifest
    require_fields(
        acquisition,
        (
            ("structural_id", (str,)),
            ("environment_instance_id", (str,)),
            ("semantics_profile_id", (str,)),
            ("trusted_observer_id", (str,)),
            ("acquisition_protocol_id", (str,)),
            ("registered_state_ids", (tuple,)),
            ("registered_ground_row_ids", (tuple,)),
            ("observed_ground_row_ids", (tuple,)),
            ("event_receipt_ids", (tuple,)),
            ("acquisition_query_inputs_used", (int,)),
            ("authority_registry_freeze_sequence", (int,)),
            ("query_registration_open_sequence", (int,)),
            ("allowlist_registered_before_query", (bool,)),
            ("selection_rule", (str,)),
            ("evidence_class", (EvidenceClass,)),
            ("evidence_lane", (EvidenceLane,)),
            ("prequery_frozen", (bool,)),
            ("complete_for_declared_receipts", (bool,)),
        ),
        "acquisition manifest",
    )
    require_fields(
        authority,
        (
            ("acquisition_manifest", (PreregisteredAcquisitionManifestV1,)),
            ("structural_id", (str,)),
            ("environment_instance_id", (str,)),
            ("semantics_profile_id", (str,)),
            ("trusted_observer_id", (str,)),
            ("observation_log_id", (str,)),
            ("evidence_ledger_id", (str,)),
            ("state_ids", (tuple,)),
            ("action_catalogue_ids", (tuple,)),
            ("event_bindings", (tuple,)),
            ("trust_root_key", (str,)),
            ("action_catalogues_complete_asserted", (bool,)),
            ("deterministic_stationary_asserted", (bool,)),
            ("observation_source_authenticity_asserted", (bool,)),
            ("in_memory_exact_graph_required", (bool,)),
            ("transport_authority_claimed", (bool,)),
        ),
        "observation authority",
    )
    for value, field in (
        (acquisition.registered_state_ids, "acquisition state IDs"),
        (acquisition.registered_ground_row_ids, "acquisition ground-row IDs"),
        (acquisition.observed_ground_row_ids, "acquisition observed-row IDs"),
        (acquisition.event_receipt_ids, "acquisition receipt IDs"),
        (authority.state_ids, "authority state IDs"),
        (authority.action_catalogue_ids, "authority catalogue IDs"),
    ):
        if type(value) is not tuple or any(type(item) is not str for item in value):
            raise ObservationPartialRAPMInvariantViolation(
                f"source replay rejects nested {field} before canonical access"
            )
    if type(authority.event_bindings) is not tuple or any(
        type(item) is not ObservationAuthorityEventBindingV1
        for item in authority.event_bindings
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects nested authority-event substitutions before canonical access"
        )
    if any(
        type(item.evidence_class) is not EvidenceClass
        or type(item.evidence_lane) is not EvidenceLane
        for item in authority.event_bindings
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects malformed authority-event markers before canonical access"
        )
    for binding in authority.event_bindings:
        require_fields(
            binding,
            (
                ("event_receipt_id", (str,)),
                ("observation_id", (str,)),
                ("ground_row_id", (str,)),
                ("evidence_class", (EvidenceClass,)),
                ("evidence_lane", (EvidenceLane,)),
            ),
            "authority event binding",
        )


@dataclass(frozen=True, order=True, slots=True)
class ExactIntervalV1:
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "lower", _fraction(self.lower, "interval lower"))
        object.__setattr__(self, "upper", _fraction(self.upper, "interval upper"))
        if self.lower > self.upper:
            raise ObservationPartialRAPMInvariantViolation(
                "interval lower exceeds upper"
            )

    @property
    def is_point(self) -> bool:
        return self.lower == self.upper

    def to_document(self) -> dict[str, Any]:
        return {
            "lower": _fraction_document(self.lower),
            "upper": _fraction_document(self.upper),
        }


@dataclass(frozen=True, order=True, slots=True)
class NamedIntervalV1:
    name: str
    interval: ExactIntervalV1

    def __post_init__(self) -> None:
        _text(self.name, "interval name")
        if type(self.interval) is not ExactIntervalV1:
            raise ObservationPartialRAPMInvariantViolation(
                "named interval rejects duck intervals"
            )

    def to_document(self) -> dict[str, Any]:
        return {"name": self.name, "interval": self.interval.to_document()}


@dataclass(frozen=True, order=True, slots=True)
class DestinationIntervalV1:
    destination_id: str
    interval: ExactIntervalV1

    def __post_init__(self) -> None:
        _cid(self.destination_id, "destination_id")
        if type(self.interval) is not ExactIntervalV1:
            raise ObservationPartialRAPMInvariantViolation(
                "destination interval rejects duck intervals"
            )
        if self.interval.lower < 0 or self.interval.upper > 1:
            raise ObservationPartialRAPMInvariantViolation(
                "destination probability interval lies outside [0,1]"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "destination_id": self.destination_id,
            "interval": self.interval.to_document(),
        }


@dataclass(frozen=True, order=True, slots=True)
class JointOutcomeAtomV1:
    kind: JointOutcomeKind
    destination_id: str | None

    def __post_init__(self) -> None:
        if type(self.kind) is not JointOutcomeKind:
            raise ObservationPartialRAPMInvariantViolation(
                "joint outcome atom requires the exact kind enum"
            )
        if self.kind is JointOutcomeKind.CONTINUATION:
            if type(self.destination_id) is not str:
                raise ObservationPartialRAPMInvariantViolation(
                    "continuation atom requires an exact destination ID"
                )
            _cid(self.destination_id, "joint continuation destination")
        elif self.destination_id is not None:
            raise ObservationPartialRAPMInvariantViolation(
                "terminal joint atoms cannot carry a continuation destination"
            )

    @property
    def terminal(self) -> bool:
        return self.kind is not JointOutcomeKind.CONTINUATION

    @property
    def failure(self) -> bool:
        return self.kind is JointOutcomeKind.TERMINAL_FAILURE

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_rapm_joint_outcome_atom.v1",
            "kind": self.kind.value,
            "destination_id": self.destination_id,
            "terminal": self.terminal,
            "failure": self.failure,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("joint_outcome_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class JointSimplexConstraintV1:
    atom_ids: tuple[str, ...]
    known_continuation_mass: Fraction
    known_terminal_mass: Fraction
    unknown_atom_mass_sum: Fraction
    total_probability_mass: Fraction = Fraction(1)
    partition_semantics: str = "continuation_plus_terminal_equals_one_v1"
    failure_implies_terminal: bool = True
    independent_marginal_box_forbidden: bool = True

    def __post_init__(self) -> None:
        atoms = _sorted_unique_ids(self.atom_ids, "joint simplex atom IDs")
        if not atoms:
            raise ObservationPartialRAPMInvariantViolation(
                "joint simplex requires at least one atom"
            )
        for field in (
            "known_continuation_mass",
            "known_terminal_mass",
            "unknown_atom_mass_sum",
            "total_probability_mass",
        ):
            value = _fraction(getattr(self, field), field)
            object.__setattr__(self, field, value)
            if not 0 <= value <= 1:
                raise ObservationPartialRAPMInvariantViolation(
                    f"{field} lies outside [0,1]"
                )
        if (
            self.known_continuation_mass
            + self.known_terminal_mass
            + self.unknown_atom_mass_sum
            != self.total_probability_mass
            or self.total_probability_mass != 1
            or self.partition_semantics
            != "continuation_plus_terminal_equals_one_v1"
            or self.failure_implies_terminal is not True
            or self.independent_marginal_box_forbidden is not True
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "joint simplex coupling constraints were relaxed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_rapm_joint_simplex_constraint.v1",
            "atom_ids": list(self.atom_ids),
            "known_continuation_mass": _fraction_document(self.known_continuation_mass),
            "known_terminal_mass": _fraction_document(self.known_terminal_mass),
            "unknown_atom_mass_sum": _fraction_document(self.unknown_atom_mass_sum),
            "total_probability_mass": _fraction_document(self.total_probability_mass),
            "partition_semantics": self.partition_semantics,
            "failure_implies_terminal": self.failure_implies_terminal,
            "independent_marginal_box_forbidden": self.independent_marginal_box_forbidden,
        }

    @property
    def constraint_id(self) -> str:
        return _content_id("joint_simplex_constraint", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "constraint_id": self.constraint_id}


@dataclass(frozen=True, slots=True)
class AmbiguityPayloadV1:
    known_reward_features: tuple[tuple[str, Fraction], ...]
    known_successor_masses: tuple[tuple[str, Fraction], ...]
    known_failure_mass: Fraction
    known_terminal_mass: Fraction
    unknown_mass: Fraction
    unknown_successor_destination_ids: tuple[str, ...]
    external_boundary_id: str
    reward_intervals: tuple[NamedIntervalV1, ...]
    successor_intervals: tuple[DestinationIntervalV1, ...]
    failure_interval: ExactIntervalV1
    terminal_interval: ExactIntervalV1
    joint_outcome_atoms: tuple[JointOutcomeAtomV1, ...]
    joint_simplex_constraint: JointSimplexConstraintV1
    unknown_failure_allowed: bool = True
    unknown_terminal_allowed: bool = True

    def __post_init__(self) -> None:
        if type(self.known_reward_features) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.known_reward_features
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "known reward features reject nested duck pairs before canonical access"
            )
        if type(self.known_successor_masses) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.known_successor_masses
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "known successor masses reject nested duck pairs before canonical access"
            )
        if type(self.reward_intervals) is not tuple or any(
            type(item) is not NamedIntervalV1 for item in self.reward_intervals
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "ambiguity payload rejects duck reward intervals before canonical access"
            )
        if type(self.successor_intervals) is not tuple or any(
            type(item) is not DestinationIntervalV1 for item in self.successor_intervals
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "ambiguity payload rejects duck successor intervals before canonical access"
            )
        if type(self.failure_interval) is not ExactIntervalV1 or type(self.terminal_interval) is not ExactIntervalV1:
            raise ObservationPartialRAPMInvariantViolation(
                "failure/terminal intervals reject duck values"
            )
        if type(self.joint_outcome_atoms) is not tuple or any(
            type(item) is not JointOutcomeAtomV1 for item in self.joint_outcome_atoms
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "ambiguity payload rejects duck joint atoms before canonical access"
            )
        if type(self.joint_simplex_constraint) is not JointSimplexConstraintV1:
            raise ObservationPartialRAPMInvariantViolation(
                "ambiguity payload rejects duck joint constraints before canonical access"
            )
        _require_stable_documents(self.joint_outcome_atoms, "joint outcome atoms")
        rewards = tuple((name, _fraction(value, "known reward")) for name, value in self.known_reward_features)
        reward_names = tuple(name for name, _ in rewards)
        if rewards != tuple(sorted(set(rewards))):
            raise ObservationPartialRAPMInvariantViolation(
                "known reward features must be unique and sorted"
            )
        if len(reward_names) != len(set(reward_names)):
            raise ObservationPartialRAPMInvariantViolation(
                "known reward feature names must be unique"
            )
        object.__setattr__(self, "known_reward_features", rewards)
        successors = tuple(
            (destination, _fraction(value, "known successor mass"))
            for destination, value in self.known_successor_masses
        )
        successor_names = tuple(destination for destination, _ in successors)
        if successors != tuple(sorted(set(successors))):
            raise ObservationPartialRAPMInvariantViolation(
                "known successor masses must be unique and sorted"
            )
        if len(successor_names) != len(set(successor_names)):
            raise ObservationPartialRAPMInvariantViolation(
                "known successor destination names must be unique"
            )
        if any(value <= 0 or value > 1 for _, value in successors):
            raise ObservationPartialRAPMInvariantViolation(
                "known successor masses must lie in (0,1]"
            )
        for destination, _ in successors:
            _cid(destination, "known successor destination")
        object.__setattr__(self, "known_successor_masses", successors)
        for field in ("known_failure_mass", "known_terminal_mass", "unknown_mass"):
            value = _fraction(getattr(self, field), field)
            object.__setattr__(self, field, value)
            if not 0 <= value <= 1:
                raise ObservationPartialRAPMInvariantViolation(
                    f"{field} lies outside [0,1]"
                )
        if self.known_failure_mass > self.known_terminal_mass:
            raise ObservationPartialRAPMInvariantViolation(
                "known failure mass exceeds known terminal mass"
            )
        if sum((value for _, value in successors), self.known_terminal_mass) + self.unknown_mass != 1:
            raise ObservationPartialRAPMInvariantViolation(
                "known continuation + known termination + unknown simplex mass must equal one"
            )
        _cid(self.external_boundary_id, "external_boundary_id")
        destinations = _sorted_unique_ids(
            self.unknown_successor_destination_ids,
            "unknown successor destinations",
        )
        if self.external_boundary_id not in destinations:
            raise ObservationPartialRAPMInvariantViolation(
                "unknown successor simplex omits the external boundary"
            )
        if not set(destination for destination, _ in successors) <= set(destinations):
            raise ObservationPartialRAPMInvariantViolation(
                "known successor lies outside the registered active-plus-boundary scope"
            )
        reward_interval_names = tuple(item.name for item in self.reward_intervals)
        successor_interval_names = tuple(
            item.destination_id for item in self.successor_intervals
        )
        if (
            self.reward_intervals != tuple(sorted(set(self.reward_intervals)))
            or self.successor_intervals != tuple(sorted(set(self.successor_intervals)))
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "ambiguity intervals must be unique and sorted"
            )
        if len(reward_interval_names) != len(set(reward_interval_names)):
            raise ObservationPartialRAPMInvariantViolation(
                "reward interval names must be unique"
            )
        if len(successor_interval_names) != len(set(successor_interval_names)):
            raise ObservationPartialRAPMInvariantViolation(
                "successor interval destination names must be unique"
            )
        if tuple(item.destination_id for item in self.successor_intervals) != destinations:
            raise ObservationPartialRAPMInvariantViolation(
                "successor intervals must exactly cover the unknown destination scope"
            )
        if (
            self.failure_interval.lower != self.known_failure_mass
            or self.failure_interval.upper != self.known_failure_mass + self.unknown_mass
            or self.terminal_interval.lower != self.known_terminal_mass
            or self.terminal_interval.upper != self.known_terminal_mass + self.unknown_mass
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "failure/terminal intervals do not match known + unknown mass"
            )
        known_successors = dict(successors)
        for row in self.successor_intervals:
            lower = known_successors.get(row.destination_id, Fraction(0))
            if row.interval != ExactIntervalV1(lower, lower + self.unknown_mass):
                raise ObservationPartialRAPMInvariantViolation(
                    "successor interval does not match the simplex projection"
                )
        atom_ids = tuple(item.atom_id for item in self.joint_outcome_atoms)
        if atom_ids != tuple(sorted(set(atom_ids))):
            raise ObservationPartialRAPMInvariantViolation(
                "joint outcome atoms must be unique and content-ID sorted"
            )
        continuation_destinations = tuple(
            sorted(
                item.destination_id
                for item in self.joint_outcome_atoms
                if item.kind is JointOutcomeKind.CONTINUATION
            )
        )
        terminal_kinds = tuple(
            sorted(
                item.kind.value
                for item in self.joint_outcome_atoms
                if item.kind is not JointOutcomeKind.CONTINUATION
            )
        )
        if (
            continuation_destinations != destinations
            or terminal_kinds
            != (JointOutcomeKind.TERMINAL_FAILURE.value, JointOutcomeKind.TERMINAL_SUCCESS.value)
            or self.joint_simplex_constraint.atom_ids != atom_ids
            or self.joint_simplex_constraint.known_continuation_mass
            != sum((value for _, value in successors), Fraction(0))
            or self.joint_simplex_constraint.known_terminal_mass != self.known_terminal_mass
            or self.joint_simplex_constraint.unknown_atom_mass_sum != self.unknown_mass
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "joint outcome atoms/constraint do not encode this ambiguity simplex"
            )
        if self.unknown_failure_allowed is not True or self.unknown_terminal_allowed is not True:
            raise ObservationPartialRAPMInvariantViolation(
                "unknown simplex must retain failure and terminal atoms"
            )

    @property
    def is_singleton(self) -> bool:
        return self.unknown_mass == 0 and all(
            item.interval.is_point
            for item in (*self.reward_intervals, *self.successor_intervals)
        ) and self.failure_interval.is_point and self.terminal_interval.is_point

    def to_document(self) -> dict[str, Any]:
        return {
            "known_reward_features": [
                {"name": name, "value": _fraction_document(value)}
                for name, value in self.known_reward_features
            ],
            "known_successor_masses": [
                {"destination_id": destination, "mass": _fraction_document(value)}
                for destination, value in self.known_successor_masses
            ],
            "known_failure_mass": _fraction_document(self.known_failure_mass),
            "known_terminal_mass": _fraction_document(self.known_terminal_mass),
            "unknown_mass": _fraction_document(self.unknown_mass),
            "unknown_successor_destination_ids": list(self.unknown_successor_destination_ids),
            "external_boundary_id": self.external_boundary_id,
            "reward_intervals": [item.to_document() for item in self.reward_intervals],
            "successor_intervals": [item.to_document() for item in self.successor_intervals],
            "failure_interval": self.failure_interval.to_document(),
            "terminal_interval": self.terminal_interval.to_document(),
            "joint_outcome_atoms": [item.to_document() for item in self.joint_outcome_atoms],
            "joint_simplex_constraint": self.joint_simplex_constraint.to_document(),
            "unknown_failure_allowed": self.unknown_failure_allowed,
            "unknown_terminal_allowed": self.unknown_terminal_allowed,
        }


@dataclass(frozen=True, slots=True)
class PartialGroundRowV1:
    ground_row_id: str
    state_id: str
    ground_action_id: str
    status: AmbiguityRowStatus
    observation_ids: tuple[str, ...]
    ambiguity: AmbiguityPayloadV1

    def __post_init__(self) -> None:
        _cid(self.ground_row_id, "ground_row_id")
        _cid(self.state_id, "ground row state_id")
        _cid(self.ground_action_id, "ground_action_id")
        if self.ground_row_id != _ground_row_id(self.state_id, self.ground_action_id):
            raise ObservationPartialRAPMInvariantViolation(
                "ground row ID is not the canonical state-action identity"
            )
        if type(self.status) is not AmbiguityRowStatus or type(self.ambiguity) is not AmbiguityPayloadV1:
            raise ObservationPartialRAPMInvariantViolation(
                "ground row rejects duck status/ambiguity"
            )
        _sorted_unique_ids(self.observation_ids, "ground row observation IDs")
        if self.status is AmbiguityRowStatus.OBSERVED_SINGLETON:
            if not self.observation_ids or not self.ambiguity.is_singleton:
                raise ObservationPartialRAPMInvariantViolation(
                    "observed ground row must be a point singleton with evidence"
                )
        elif self.observation_ids or self.ambiguity.unknown_mass != 1:
            raise ObservationPartialRAPMInvariantViolation(
                "missing ground row must retain unit unknown simplex mass"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "ground_row_id": self.ground_row_id,
            "state_id": self.state_id,
            "ground_action_id": self.ground_action_id,
            "status": self.status.value,
            "observation_ids": list(self.observation_ids),
            "ambiguity": self.ambiguity.to_document(),
        }


@dataclass(frozen=True, slots=True)
class ObservationCoverageV1:
    registered_state_ids: tuple[str, ...]
    registered_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    external_boundary_id: str
    mode: str = "observation_state_catalogue_partial_rows_v1"
    admissible_query_support_rule: str = "positive_support_subset_of_registered_state_catalogue"
    transition_closure_claimed: bool = False
    outside_catalogue_requires_rebuild_or_fallback: bool = True

    def __post_init__(self) -> None:
        states = _sorted_unique_ids(self.registered_state_ids, "coverage state IDs")
        rows = _sorted_unique_ids(self.registered_ground_row_ids, "coverage ground row IDs")
        observed = _sorted_unique_ids(self.observed_ground_row_ids, "coverage observed row IDs")
        missing = _sorted_unique_ids(self.missing_ground_row_ids, "coverage missing row IDs")
        _cid(self.external_boundary_id, "coverage external boundary")
        if set(observed) & set(missing) or tuple(sorted((*observed, *missing))) != rows:
            raise ObservationPartialRAPMInvariantViolation(
                "observed and missing rows must partition registered ground rows"
            )
        if (
            self.mode != "observation_state_catalogue_partial_rows_v1"
            or self.admissible_query_support_rule
            != "positive_support_subset_of_registered_state_catalogue"
            or self.transition_closure_claimed is not False
            or self.outside_catalogue_requires_rebuild_or_fallback is not True
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "observation coverage overclaims transition closure or reuse"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_coverage.v1",
            "registered_state_ids": list(self.registered_state_ids),
            "registered_ground_row_ids": list(self.registered_ground_row_ids),
            "observed_ground_row_ids": list(self.observed_ground_row_ids),
            "missing_ground_row_ids": list(self.missing_ground_row_ids),
            "external_boundary_id": self.external_boundary_id,
            "mode": self.mode,
            "admissible_query_support_rule": self.admissible_query_support_rule,
            "transition_closure_claimed": self.transition_closure_claimed,
            "outside_catalogue_requires_rebuild_or_fallback": self.outside_catalogue_requires_rebuild_or_fallback,
        }

    @property
    def coverage_id(self) -> str:
        return _content_id("coverage", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "coverage_id": self.coverage_id}

    def validate_registered_support(self, state_ids: Iterable[str]) -> None:
        requested = tuple(state_ids)
        if not requested:
            raise ObservationPartialRAPMInvariantViolation(
                "query support cannot be empty"
            )
        unknown = sorted(set(requested) - set(self.registered_state_ids))
        if unknown:
            raise ObservationPartialRAPMInvariantViolation(
                "query support lies outside observation coverage; rebuild or fallback required"
            )


@dataclass(frozen=True, slots=True)
class PartialCellV1:
    member_state_ids: tuple[str, ...]
    planning_kind: PlanningKind
    coordinate_values: tuple[int, ...]

    def __post_init__(self) -> None:
        if not _sorted_unique_ids(self.member_state_ids, "cell member IDs"):
            raise ObservationPartialRAPMInvariantViolation("partial cell cannot be empty")
        if type(self.planning_kind) is not PlanningKind:
            raise ObservationPartialRAPMInvariantViolation(
                "partial cell planning kind requires exact enum"
            )
        if type(self.coordinate_values) is not tuple or any(
            type(value) is not int for value in self.coordinate_values
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "cell coordinate values must be exact integers"
            )
        if self.planning_kind is not PlanningKind.ACTIVE and self.coordinate_values:
            raise ObservationPartialRAPMInvariantViolation(
                "terminal cells cannot carry active coordinates"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_rapm_cell.v1",
            "member_state_ids": list(self.member_state_ids),
            "planning_kind": self.planning_kind.value,
            "coordinate_values": list(self.coordinate_values),
        }

    @property
    def cell_id(self) -> str:
        return _content_id("cell", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cell_id": self.cell_id}


@dataclass(frozen=True, slots=True)
class PartialSemanticActionV1:
    cell_id: str
    label_values: tuple[bool, ...]

    def __post_init__(self) -> None:
        _cid(self.cell_id, "semantic action cell_id")
        if not self.label_values or type(self.label_values) is not tuple or any(
            type(value) is not bool for value in self.label_values
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "semantic action label values must be a nonempty boolean tuple"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_rapm_semantic_action.v1",
            "cell_id": self.cell_id,
            "label_values": list(self.label_values),
        }

    @property
    def semantic_action_id(self) -> str:
        return _content_id("semantic_action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantic_action_id": self.semantic_action_id}


@dataclass(frozen=True, slots=True)
class ConcretizerRowV1:
    state_id: str
    cell_id: str
    semantic_action_id: str
    support: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "concretizer state_id")
        _cid(self.cell_id, "concretizer cell_id")
        _cid(self.semantic_action_id, "concretizer semantic_action_id")
        if type(self.support) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.support
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "concretizer support rejects nested duck pairs before canonical access"
            )
        normalized = tuple(
            (action_id, _fraction(probability, "concretizer probability"))
            for action_id, probability in self.support
        )
        if not normalized or normalized != tuple(sorted(set(normalized))):
            raise ObservationPartialRAPMInvariantViolation(
                "concretizer support must be nonempty, unique, and sorted"
            )
        uniform_weight = Fraction(1, len(normalized))
        if any(probability <= 0 for _, probability in normalized) or sum(
            (probability for _, probability in normalized), Fraction(0)
        ) != 1:
            raise ObservationPartialRAPMInvariantViolation(
                "concretizer support must have positive unit mass"
            )
        if any(probability != uniform_weight for _, probability in normalized):
            raise ObservationPartialRAPMInvariantViolation(
                "V0-042 concretizer must be uniform over distinct ground actions"
            )
        for action_id, _ in normalized:
            _cid(action_id, "concretizer ground action ID")
        object.__setattr__(self, "support", normalized)

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
            "support": [
                {"ground_action_id": action_id, "probability": _fraction_document(probability)}
                for action_id, probability in self.support
            ],
        }


@dataclass(frozen=True, slots=True)
class PartialSemanticRealizationV1:
    state_id: str
    cell_id: str
    semantic_action_id: str
    support_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    ambiguity: AmbiguityPayloadV1

    def __post_init__(self) -> None:
        _cid(self.state_id, "realization state_id")
        _cid(self.cell_id, "realization cell_id")
        _cid(self.semantic_action_id, "realization semantic_action_id")
        support = _sorted_unique_ids(self.support_ground_row_ids, "realization support rows")
        observed = _sorted_unique_ids(self.observed_ground_row_ids, "realization observed rows")
        missing = _sorted_unique_ids(self.missing_ground_row_ids, "realization missing rows")
        if not support or set(observed) & set(missing) or tuple(sorted((*observed, *missing))) != support:
            raise ObservationPartialRAPMInvariantViolation(
                "realization observed/missing rows must partition its support"
            )
        if type(self.ambiguity) is not AmbiguityPayloadV1:
            raise ObservationPartialRAPMInvariantViolation(
                "semantic realization rejects duck ambiguity"
            )
        if self.ambiguity.unknown_mass != Fraction(len(missing), len(support)):
            raise ObservationPartialRAPMInvariantViolation(
                "semantic realization unknown mass differs from missing concretizer support"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "cell_id": self.cell_id,
            "semantic_action_id": self.semantic_action_id,
            "support_ground_row_ids": list(self.support_ground_row_ids),
            "observed_ground_row_ids": list(self.observed_ground_row_ids),
            "missing_ground_row_ids": list(self.missing_ground_row_ids),
            "ambiguity": self.ambiguity.to_document(),
        }


@dataclass(frozen=True, slots=True)
class PortablePartialRAPMV1:
    semantics_profile_id: str
    semantics_horizon_cap: int
    observation_log_id: str
    coordinate_proposal_id: str
    observation_authority_id: str
    acquisition_manifest_id: str
    acquisition_coverage_id: str
    evidence_ledger_id: str
    coverage: ObservationCoverageV1
    external_boundary_id: str
    cells: tuple[PartialCellV1, ...]
    semantic_actions: tuple[PartialSemanticActionV1, ...]
    concretizer_rows: tuple[ConcretizerRowV1, ...]
    ground_rows: tuple[PartialGroundRowV1, ...]
    semantic_realizations: tuple[PartialSemanticRealizationV1, ...]
    reward_feature_caps: tuple[RewardFeatureCapV1, ...]
    evidence_kind: str = "DETERMINISTIC_LOG_CONDITIONAL_SOUND_V1"
    query_neutral: bool = True
    transition_closure_claimed: bool = False
    exact_quotient_claimed: bool = False
    plan_certificate_claimed: bool = False
    infeasibility_claimed: bool = False
    acquisition_query_neutral_attested: bool = True
    preregistered_allowlisted_authority_required: bool = True

    def __post_init__(self) -> None:
        for field in (
            "semantics_profile_id",
            "observation_log_id",
            "coordinate_proposal_id",
            "observation_authority_id",
            "acquisition_manifest_id",
            "acquisition_coverage_id",
            "evidence_ledger_id",
            "external_boundary_id",
        ):
            _cid(getattr(self, field), field)
        _integer(self.semantics_horizon_cap, "semantics_horizon_cap", 1)
        if type(self.coverage) is not ObservationCoverageV1:
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM rejects duck coverage"
            )
        if self.coverage.external_boundary_id != self.external_boundary_id:
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM external-boundary binding mismatch"
            )
        if (
            self.evidence_kind != "DETERMINISTIC_LOG_CONDITIONAL_SOUND_V1"
            or self.query_neutral is not True
            or self.transition_closure_claimed is not False
            or self.exact_quotient_claimed is not False
            or self.plan_certificate_claimed is not False
            or self.infeasibility_claimed is not False
            or self.acquisition_query_neutral_attested is not True
            or self.preregistered_allowlisted_authority_required is not True
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM overclaims its log-conditional scope"
            )
        typed_sets = (
            (self.cells, PartialCellV1, "cells", lambda item: item.cell_id),
            (
                self.semantic_actions,
                PartialSemanticActionV1,
                "semantic actions",
                lambda item: item.semantic_action_id,
            ),
            (
                self.concretizer_rows,
                ConcretizerRowV1,
                "concretizer rows",
                lambda item: (item.state_id, item.semantic_action_id),
            ),
            (
                self.ground_rows,
                PartialGroundRowV1,
                "ground rows",
                lambda item: item.ground_row_id,
            ),
            (
                self.semantic_realizations,
                PartialSemanticRealizationV1,
                "semantic realizations",
                lambda item: (item.state_id, item.semantic_action_id),
            ),
        )
        for rows, exact_type, label, key in typed_sets:
            if type(rows) is not tuple or any(type(item) is not exact_type for item in rows):
                raise ObservationPartialRAPMInvariantViolation(
                    f"partial RAPM rejects duck {label}"
                )
            keys = tuple(key(item) for item in rows)
            if keys != tuple(sorted(set(keys))):
                raise ObservationPartialRAPMInvariantViolation(
                    f"partial RAPM {label} must be unique and sorted"
                )
        member_ids = tuple(sorted(state_id for cell in self.cells for state_id in cell.member_state_ids))
        if member_ids != self.coverage.registered_state_ids:
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM cells do not exactly partition registered states"
            )
        row_ids = tuple(row.ground_row_id for row in self.ground_rows)
        if row_ids != self.coverage.registered_ground_row_ids:
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM ground rows differ from observation coverage"
            )
        observed = tuple(
            row.ground_row_id
            for row in self.ground_rows
            if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
        )
        missing = tuple(
            row.ground_row_id
            for row in self.ground_rows
            if row.status is AmbiguityRowStatus.MISSING_VACUOUS
        )
        if observed != self.coverage.observed_ground_row_ids or missing != self.coverage.missing_ground_row_ids:
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM row status differs from coverage"
            )
        if type(self.reward_feature_caps) is not tuple or any(
            type(item) is not RewardFeatureCapV1 for item in self.reward_feature_caps
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM rejects duck reward caps before canonical access"
            )
        _require_stable_documents(self.reward_feature_caps, "partial RAPM reward caps")
        cap_names = tuple(item.name for item in self.reward_feature_caps)
        if self.reward_feature_caps != tuple(sorted(set(self.reward_feature_caps))):
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM reward caps must be unique and sorted"
            )
        if len(cap_names) != len(set(cap_names)):
            raise ObservationPartialRAPMInvariantViolation(
                "partial RAPM reward feature cap names must be unique"
            )
        active_cell_ids = tuple(
            sorted(cell.cell_id for cell in self.cells if cell.planning_kind is PlanningKind.ACTIVE)
        )
        expected_destinations = tuple(sorted((*active_cell_ids, self.external_boundary_id)))
        for row in (*self.ground_rows, *self.semantic_realizations):
            if row.ambiguity.unknown_successor_destination_ids != expected_destinations:
                raise ObservationPartialRAPMInvariantViolation(
                    "ambiguity row destination scope differs from the active model plus boundary"
                )

        # A portable model is a consumer-facing authority boundary.  Recompute
        # every derived realization from its cells, concretizer and ground rows;
        # a new self-signed model ID must not be able to turn missing evidence
        # into a singleton while retaining an allowlisted source authority ID.
        cell_by_id = {cell.cell_id: cell for cell in self.cells}
        cell_by_state = {
            state_id: cell
            for cell in self.cells
            for state_id in cell.member_state_ids
        }
        semantic_action_by_id = {
            action.semantic_action_id: action for action in self.semantic_actions
        }
        actions_by_cell: dict[str, set[str]] = {}
        for action in self.semantic_actions:
            cell = cell_by_id.get(action.cell_id)
            if cell is None or cell.planning_kind is not PlanningKind.ACTIVE:
                raise ObservationPartialRAPMInvariantViolation(
                    "semantic action references a missing or non-active cell"
                )
            actions_by_cell.setdefault(action.cell_id, set()).add(
                action.semantic_action_id
            )
        if set(actions_by_cell) != set(active_cell_ids):
            raise ObservationPartialRAPMInvariantViolation(
                "every active cell must expose at least one semantic action"
            )

        cap_by_name = {cap.name: cap for cap in self.reward_feature_caps}
        ground_by_state_action: dict[tuple[str, str], PartialGroundRowV1] = {}
        ground_by_id: dict[str, PartialGroundRowV1] = {}
        for row in self.ground_rows:
            cell = cell_by_state.get(row.state_id)
            if cell is None or cell.planning_kind is not PlanningKind.ACTIVE:
                raise ObservationPartialRAPMInvariantViolation(
                    "ground row source is absent from the active state partition"
                )
            expected_row_id = _ground_row_id(row.state_id, row.ground_action_id)
            if row.ground_row_id != expected_row_id:
                raise ObservationPartialRAPMInvariantViolation(
                    "ground row ID is not bound to its state and action"
                )
            key = (row.state_id, row.ground_action_id)
            if key in ground_by_state_action:
                raise ObservationPartialRAPMInvariantViolation(
                    "partial RAPM repeats one state-action ground row"
                )
            ground_by_state_action[key] = row
            ground_by_id[row.ground_row_id] = row

            known_reward = dict(row.ambiguity.known_reward_features)
            if set(known_reward) - set(cap_by_name):
                raise ObservationPartialRAPMInvariantViolation(
                    "ground-row ambiguity uses an unregistered reward feature"
                )
            if any(
                not cap_by_name[name].lower <= value <= cap_by_name[name].upper
                for name, value in known_reward.items()
            ):
                raise ObservationPartialRAPMInvariantViolation(
                    "ground-row ambiguity reward lies outside the profile cap"
                )
            if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON:
                if len(row.observation_ids) != 1:
                    raise ObservationPartialRAPMInvariantViolation(
                        "deterministic observed ground row needs exactly one event"
                    )
                unknown_mass = Fraction(0)
            else:
                if (
                    row.ambiguity.known_reward_features
                    or row.ambiguity.known_successor_masses
                    or row.ambiguity.known_failure_mass
                    or row.ambiguity.known_terminal_mass
                ):
                    raise ObservationPartialRAPMInvariantViolation(
                        "missing ground row must be the canonical vacuous simplex"
                    )
                unknown_mass = Fraction(1)
            expected_ambiguity = _ambiguity_payload(
                known_reward=known_reward,
                known_successor=dict(row.ambiguity.known_successor_masses),
                known_failure=row.ambiguity.known_failure_mass,
                known_terminal=row.ambiguity.known_terminal_mass,
                unknown_mass=unknown_mass,
                destinations=expected_destinations,
                external_boundary_id=self.external_boundary_id,
                caps=self.reward_feature_caps,
            )
            if row.ambiguity.to_document() != expected_ambiguity.to_document():
                raise ObservationPartialRAPMInvariantViolation(
                    "ground-row ambiguity is not the canonical profile projection"
                )

        expected_pairs = {
            (state_id, action.semantic_action_id)
            for action in self.semantic_actions
            for state_id in cell_by_id[action.cell_id].member_state_ids
        }
        concretizer_by_pair = {
            (row.state_id, row.semantic_action_id): row
            for row in self.concretizer_rows
        }
        realization_by_pair = {
            (row.state_id, row.semantic_action_id): row
            for row in self.semantic_realizations
        }
        if set(concretizer_by_pair) != expected_pairs or set(realization_by_pair) != expected_pairs:
            raise ObservationPartialRAPMInvariantViolation(
                "concretizer/realization coverage differs from the state-action quotient"
            )

        for pair in sorted(expected_pairs):
            state_id, semantic_action_id = pair
            concretizer = concretizer_by_pair[pair]
            realization = realization_by_pair[pair]
            action = semantic_action_by_id[semantic_action_id]
            expected_cell = cell_by_state[state_id]
            if (
                action.cell_id != expected_cell.cell_id
                or concretizer.cell_id != expected_cell.cell_id
                or realization.cell_id != expected_cell.cell_id
            ):
                raise ObservationPartialRAPMInvariantViolation(
                    "semantic action, concretizer and realization cell bindings disagree"
                )

            support_rows: list[tuple[PartialGroundRowV1, Fraction]] = []
            for ground_action_id, probability in concretizer.support:
                ground_row = ground_by_state_action.get((state_id, ground_action_id))
                if ground_row is None:
                    raise ObservationPartialRAPMInvariantViolation(
                        "concretizer support lacks a matching state-action ground row"
                    )
                support_rows.append((ground_row, probability))
            expected_support = tuple(sorted(row.ground_row_id for row, _ in support_rows))
            expected_observed = tuple(
                sorted(
                    row.ground_row_id
                    for row, _ in support_rows
                    if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
                )
            )
            expected_missing = tuple(
                sorted(
                    row.ground_row_id
                    for row, _ in support_rows
                    if row.status is AmbiguityRowStatus.MISSING_VACUOUS
                )
            )
            if (
                realization.support_ground_row_ids != expected_support
                or realization.observed_ground_row_ids != expected_observed
                or realization.missing_ground_row_ids != expected_missing
            ):
                raise ObservationPartialRAPMInvariantViolation(
                    "semantic realization evidence partition differs from its concretizer support"
                )

            known_reward: dict[str, Fraction] = {}
            known_successor: dict[str, Fraction] = {}
            known_failure = Fraction(0)
            known_terminal = Fraction(0)
            unknown_mass = Fraction(0)
            for ground_row, probability in support_rows:
                if ground_row.status is AmbiguityRowStatus.MISSING_VACUOUS:
                    unknown_mass += probability
                    continue
                for name, value in ground_row.ambiguity.known_reward_features:
                    known_reward[name] = known_reward.get(name, Fraction(0)) + probability * value
                for destination, mass in ground_row.ambiguity.known_successor_masses:
                    known_successor[destination] = known_successor.get(destination, Fraction(0)) + probability * mass
                known_failure += probability * ground_row.ambiguity.known_failure_mass
                known_terminal += probability * ground_row.ambiguity.known_terminal_mass
            expected_realization_ambiguity = _ambiguity_payload(
                known_reward=known_reward,
                known_successor=known_successor,
                known_failure=known_failure,
                known_terminal=known_terminal,
                unknown_mass=unknown_mass,
                destinations=expected_destinations,
                external_boundary_id=self.external_boundary_id,
                caps=self.reward_feature_caps,
            )
            if realization.ambiguity.to_document() != expected_realization_ambiguity.to_document():
                raise ObservationPartialRAPMInvariantViolation(
                    "semantic realization ambiguity differs from the exact concretizer mixture"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_partial_rapm.v1",
            "schema_version": SCHEMA_VERSION,
            "semantics_profile_id": self.semantics_profile_id,
            "semantics_horizon_cap": self.semantics_horizon_cap,
            "observation_log_id": self.observation_log_id,
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "observation_authority_id": self.observation_authority_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "acquisition_coverage_id": self.acquisition_coverage_id,
            "evidence_ledger_id": self.evidence_ledger_id,
            "coverage": self.coverage.to_document(),
            "external_boundary_id": self.external_boundary_id,
            "cells": [item.to_document() for item in self.cells],
            "semantic_actions": [item.to_document() for item in self.semantic_actions],
            "concretizer_rows": [item.to_document() for item in self.concretizer_rows],
            "ground_rows": [item.to_document() for item in self.ground_rows],
            "semantic_realizations": [item.to_document() for item in self.semantic_realizations],
            "reward_feature_caps": [item.to_document() for item in self.reward_feature_caps],
            "evidence_kind": self.evidence_kind,
            "query_neutral": self.query_neutral,
            "transition_closure_claimed": self.transition_closure_claimed,
            "exact_quotient_claimed": self.exact_quotient_claimed,
            "plan_certificate_claimed": self.plan_certificate_claimed,
            "infeasibility_claimed": self.infeasibility_claimed,
            "acquisition_query_neutral_attested": self.acquisition_query_neutral_attested,
            "preregistered_allowlisted_authority_required": self.preregistered_allowlisted_authority_required,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}

    def validate_registered_support(self, state_ids: Iterable[str]) -> None:
        self.coverage.validate_registered_support(state_ids)


@dataclass(frozen=True, slots=True)
class QueryScopedPartialRAPMV2:
    """Immutable query-owned refinement of one verified V0-045 base model.

    The structural rows are validated with the same exact closure checks as
    ``PortablePartialRAPMV1``, but the provenance and claim flags are distinct:
    this model is never query neutral and can only be consumed together with
    the complete evidence-overlay authority chain bound below.
    """

    semantics_profile_id: str
    semantics_horizon_cap: int
    observation_log_id: str
    coordinate_proposal_id: str
    observation_authority_id: str
    acquisition_manifest_id: str
    acquisition_coverage_id: str
    evidence_ledger_id: str
    coverage: ObservationCoverageV1
    external_boundary_id: str
    cells: tuple[PartialCellV1, ...]
    semantic_actions: tuple[PartialSemanticActionV1, ...]
    concretizer_rows: tuple[ConcretizerRowV1, ...]
    ground_rows: tuple[PartialGroundRowV1, ...]
    semantic_realizations: tuple[PartialSemanticRealizationV1, ...]
    reward_feature_caps: tuple[RewardFeatureCapV1, ...]
    base_model_id: str
    observed_synthesis_result_id: str
    source_thresholds_id: str
    source_plan_id: str
    failed_typed_audit_result_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    overlay_context_id: str
    overlay_version: int = 1
    evidence_kind: str = "DETERMINISTIC_QUERY_LOCAL_EXACT_OVERLAY_V1"
    query_neutral: bool = False
    transition_closure_claimed: bool = False
    exact_quotient_claimed: bool = False
    plan_certificate_claimed: bool = False
    infeasibility_claimed: bool = False
    acquisition_query_neutral_attested: bool = False
    preregistered_allowlisted_authority_required: bool = True
    query_local_overlay_authority_required: bool = True
    base_model_mutated: bool = False
    promotion_authorized: bool = False

    def __post_init__(self) -> None:
        for field in (
            "base_model_id",
            "observed_synthesis_result_id",
            "source_thresholds_id",
            "source_plan_id",
            "failed_typed_audit_result_id",
            "evidence_request_id",
            "evidence_bundle_id",
            "overlay_context_id",
        ):
            _cid(getattr(self, field), f"query-scoped model {field}")
        _integer(self.overlay_version, "query-scoped overlay version", 1)
        if (
            self.overlay_version != 1
            or self.evidence_kind != "DETERMINISTIC_QUERY_LOCAL_EXACT_OVERLAY_V1"
            or self.query_neutral is not False
            or self.transition_closure_claimed is not False
            or self.exact_quotient_claimed is not False
            or self.plan_certificate_claimed is not False
            or self.infeasibility_claimed is not False
            or self.acquisition_query_neutral_attested is not False
            or self.preregistered_allowlisted_authority_required is not True
            or self.query_local_overlay_authority_required is not True
            or self.base_model_mutated is not False
            or self.promotion_authorized is not False
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "query-scoped partial RAPM crossed its local-overlay claim boundary"
            )

        # Reuse the exact structural closure checker without serializing or
        # retaining a misleading V1 artifact.  The temporary object is only a
        # validator for cells, rows, concretizers, realizations and ambiguity.
        PortablePartialRAPMV1(
            self.semantics_profile_id,
            self.semantics_horizon_cap,
            self.observation_log_id,
            self.coordinate_proposal_id,
            self.observation_authority_id,
            self.acquisition_manifest_id,
            self.acquisition_coverage_id,
            self.evidence_ledger_id,
            self.coverage,
            self.external_boundary_id,
            self.cells,
            self.semantic_actions,
            self.concretizer_rows,
            self.ground_rows,
            self.semantic_realizations,
            self.reward_feature_caps,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_scoped_partial_rapm.v2",
            "schema_version": TYPED_COORDINATE_SCHEMA_VERSION,
            "semantics_profile_id": self.semantics_profile_id,
            "semantics_horizon_cap": self.semantics_horizon_cap,
            "observation_log_id": self.observation_log_id,
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "observation_authority_id": self.observation_authority_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "acquisition_coverage_id": self.acquisition_coverage_id,
            "evidence_ledger_id": self.evidence_ledger_id,
            "coverage": self.coverage.to_document(),
            "external_boundary_id": self.external_boundary_id,
            "cells": [item.to_document() for item in self.cells],
            "semantic_actions": [item.to_document() for item in self.semantic_actions],
            "concretizer_rows": [item.to_document() for item in self.concretizer_rows],
            "ground_rows": [item.to_document() for item in self.ground_rows],
            "semantic_realizations": [
                item.to_document() for item in self.semantic_realizations
            ],
            "reward_feature_caps": [
                item.to_document() for item in self.reward_feature_caps
            ],
            "base_model_id": self.base_model_id,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_id": self.source_plan_id,
            "failed_typed_audit_result_id": self.failed_typed_audit_result_id,
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "overlay_context_id": self.overlay_context_id,
            "overlay_version": self.overlay_version,
            "evidence_kind": self.evidence_kind,
            "query_neutral": self.query_neutral,
            "transition_closure_claimed": self.transition_closure_claimed,
            "exact_quotient_claimed": self.exact_quotient_claimed,
            "plan_certificate_claimed": self.plan_certificate_claimed,
            "infeasibility_claimed": self.infeasibility_claimed,
            "acquisition_query_neutral_attested": (
                self.acquisition_query_neutral_attested
            ),
            "preregistered_allowlisted_authority_required": (
                self.preregistered_allowlisted_authority_required
            ),
            "query_local_overlay_authority_required": (
                self.query_local_overlay_authority_required
            ),
            "base_model_mutated": self.base_model_mutated,
            "promotion_authorized": self.promotion_authorized,
        }

    @property
    def model_id(self) -> str:
        return _content_id("query_scoped_model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}

    def validate_registered_support(self, state_ids: Iterable[str]) -> None:
        self.coverage.validate_registered_support(state_ids)


@dataclass(frozen=True, slots=True)
class QueryScopedPartialRAPMV3:
    """Immutable multi-step query overlay with locally registered boundary states.

    V3 preserves the V1 structural checker but carries a versioned provenance
    chain for query-local state/action-catalogue expansion.  It is deliberately
    neither query neutral nor promotable; only a verifier holding the complete
    multi-step evolution chain may consume it.
    """

    semantics_profile_id: str
    semantics_horizon_cap: int
    observation_log_id: str
    coordinate_proposal_id: str
    observation_authority_id: str
    acquisition_manifest_id: str
    acquisition_coverage_id: str
    evidence_ledger_id: str
    coverage: ObservationCoverageV1
    external_boundary_id: str
    cells: tuple[PartialCellV1, ...]
    semantic_actions: tuple[PartialSemanticActionV1, ...]
    concretizer_rows: tuple[ConcretizerRowV1, ...]
    ground_rows: tuple[PartialGroundRowV1, ...]
    semantic_realizations: tuple[PartialSemanticRealizationV1, ...]
    reward_feature_caps: tuple[RewardFeatureCapV1, ...]
    base_model_id: str
    previous_model_id: str
    observed_synthesis_result_id: str
    source_thresholds_id: str
    source_plan_id: str
    source_failed_typed_audit_result_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    boundary_expansion_id: str
    overlay_ledger_id: str
    overlay_version: int
    cumulative_exact_kernel_query_count: int
    registered_query_local_state_count: int
    evidence_kind: str = "DETERMINISTIC_QUERY_LOCAL_MULTISTEP_EXACT_OVERLAY_V1"
    query_neutral: bool = False
    transition_closure_claimed: bool = False
    exact_quotient_claimed: bool = False
    plan_certificate_claimed: bool = False
    infeasibility_claimed: bool = False
    acquisition_query_neutral_attested: bool = False
    preregistered_allowlisted_authority_required: bool = True
    query_local_overlay_authority_required: bool = True
    boundary_catalogue_authority_required: bool = True
    base_model_mutated: bool = False
    promotion_authorized: bool = False

    def __post_init__(self) -> None:
        for field in (
            "base_model_id",
            "previous_model_id",
            "observed_synthesis_result_id",
            "source_thresholds_id",
            "source_plan_id",
            "source_failed_typed_audit_result_id",
            "evidence_request_id",
            "evidence_bundle_id",
            "boundary_expansion_id",
            "overlay_ledger_id",
        ):
            _cid(getattr(self, field), f"multi-step query model {field}")
        _integer(self.overlay_version, "multi-step overlay version", 1)
        _integer(
            self.cumulative_exact_kernel_query_count,
            "multi-step cumulative exact-kernel count",
            1,
        )
        _integer(
            self.registered_query_local_state_count,
            "multi-step registered query-local state count",
            1,
        )
        if self.overlay_version not in (1, 2):
            raise ObservationPartialRAPMInvariantViolation(
                "V3 multi-step overlay version lies outside the frozen two-round profile"
            )
        if (self.overlay_version == 1) != (self.previous_model_id == self.base_model_id):
            raise ObservationPartialRAPMInvariantViolation(
                "multi-step previous-model binding disagrees with overlay version"
            )
        if (
            self.evidence_kind
            != "DETERMINISTIC_QUERY_LOCAL_MULTISTEP_EXACT_OVERLAY_V1"
            or self.query_neutral is not False
            or self.transition_closure_claimed is not False
            or self.exact_quotient_claimed is not False
            or self.plan_certificate_claimed is not False
            or self.infeasibility_claimed is not False
            or self.acquisition_query_neutral_attested is not False
            or self.preregistered_allowlisted_authority_required is not True
            or self.query_local_overlay_authority_required is not True
            or self.boundary_catalogue_authority_required is not True
            or self.base_model_mutated is not False
            or self.promotion_authorized is not False
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "multi-step query model crossed its local-overlay claim boundary"
            )

        PortablePartialRAPMV1(
            self.semantics_profile_id,
            self.semantics_horizon_cap,
            self.observation_log_id,
            self.coordinate_proposal_id,
            self.observation_authority_id,
            self.acquisition_manifest_id,
            self.acquisition_coverage_id,
            self.evidence_ledger_id,
            self.coverage,
            self.external_boundary_id,
            self.cells,
            self.semantic_actions,
            self.concretizer_rows,
            self.ground_rows,
            self.semantic_realizations,
            self.reward_feature_caps,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.query_scoped_partial_rapm.v3",
            "schema_version": TYPED_COORDINATE_SCHEMA_VERSION,
            "semantics_profile_id": self.semantics_profile_id,
            "semantics_horizon_cap": self.semantics_horizon_cap,
            "observation_log_id": self.observation_log_id,
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "observation_authority_id": self.observation_authority_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "acquisition_coverage_id": self.acquisition_coverage_id,
            "evidence_ledger_id": self.evidence_ledger_id,
            "coverage": self.coverage.to_document(),
            "external_boundary_id": self.external_boundary_id,
            "cells": [item.to_document() for item in self.cells],
            "semantic_actions": [item.to_document() for item in self.semantic_actions],
            "concretizer_rows": [item.to_document() for item in self.concretizer_rows],
            "ground_rows": [item.to_document() for item in self.ground_rows],
            "semantic_realizations": [
                item.to_document() for item in self.semantic_realizations
            ],
            "reward_feature_caps": [
                item.to_document() for item in self.reward_feature_caps
            ],
            "base_model_id": self.base_model_id,
            "previous_model_id": self.previous_model_id,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "source_thresholds_id": self.source_thresholds_id,
            "source_plan_id": self.source_plan_id,
            "source_failed_typed_audit_result_id": (
                self.source_failed_typed_audit_result_id
            ),
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "boundary_expansion_id": self.boundary_expansion_id,
            "overlay_ledger_id": self.overlay_ledger_id,
            "overlay_version": self.overlay_version,
            "cumulative_exact_kernel_query_count": (
                self.cumulative_exact_kernel_query_count
            ),
            "registered_query_local_state_count": (
                self.registered_query_local_state_count
            ),
            "evidence_kind": self.evidence_kind,
            "query_neutral": self.query_neutral,
            "transition_closure_claimed": self.transition_closure_claimed,
            "exact_quotient_claimed": self.exact_quotient_claimed,
            "plan_certificate_claimed": self.plan_certificate_claimed,
            "infeasibility_claimed": self.infeasibility_claimed,
            "acquisition_query_neutral_attested": (
                self.acquisition_query_neutral_attested
            ),
            "preregistered_allowlisted_authority_required": (
                self.preregistered_allowlisted_authority_required
            ),
            "query_local_overlay_authority_required": (
                self.query_local_overlay_authority_required
            ),
            "boundary_catalogue_authority_required": (
                self.boundary_catalogue_authority_required
            ),
            "base_model_mutated": self.base_model_mutated,
            "promotion_authorized": self.promotion_authorized,
        }

    @property
    def model_id(self) -> str:
        return _content_id("query_scoped_multistep_model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}

    def validate_registered_support(self, state_ids: Iterable[str]) -> None:
        self.coverage.validate_registered_support(state_ids)


@dataclass(frozen=True, slots=True)
class ObservationPartialRAPMBuildV1:
    semantics_profile_id: str
    semantics_horizon_cap: int
    observation_log_id: str
    coordinate_proposal_id: str
    observation_authority_id: str
    acquisition_manifest_id: str
    model: PortablePartialRAPMV1
    observed_ground_row_count: int
    missing_ground_row_count: int
    exact_kernel_queries_during_construction: int = 0
    generative_oracle_samples_during_construction: int = 0
    synthetic_model_rollouts_used_as_evidence: int = 0
    construction_query_inputs_used: int = 0
    acquisition_query_inputs_used: int = 0
    claim_kind: str = "LOG_CONDITIONAL_QUERY_NEUTRAL_PARTIAL_RAPM"

    def __post_init__(self) -> None:
        for field in (
            "semantics_profile_id",
            "observation_log_id",
            "coordinate_proposal_id",
            "observation_authority_id",
            "acquisition_manifest_id",
        ):
            _cid(getattr(self, field), field)
        _integer(self.semantics_horizon_cap, "semantics_horizon_cap", 1)
        if type(self.model) is not PortablePartialRAPMV1:
            raise ObservationPartialRAPMInvariantViolation(
                "build result rejects duck models"
            )
        if (
            self.model.semantics_profile_id != self.semantics_profile_id
            or self.model.semantics_horizon_cap != self.semantics_horizon_cap
            or self.model.observation_log_id != self.observation_log_id
            or self.model.coordinate_proposal_id != self.coordinate_proposal_id
            or self.model.observation_authority_id != self.observation_authority_id
            or self.model.acquisition_manifest_id != self.acquisition_manifest_id
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "build result/model identity mismatch"
            )
        _integer(self.observed_ground_row_count, "observed row count")
        _integer(self.missing_ground_row_count, "missing row count")
        if (
            self.observed_ground_row_count != len(self.model.coverage.observed_ground_row_ids)
            or self.missing_ground_row_count != len(self.model.coverage.missing_ground_row_ids)
            or self.exact_kernel_queries_during_construction != 0
            or self.generative_oracle_samples_during_construction != 0
            or self.synthetic_model_rollouts_used_as_evidence != 0
            or self.construction_query_inputs_used != 0
            or self.acquisition_query_inputs_used != 0
            or self.claim_kind != "LOG_CONDITIONAL_QUERY_NEUTRAL_PARTIAL_RAPM"
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "build result overclaims evidence, query neutrality, or row counts"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_partial_rapm_build_result.v1",
            "schema_version": SCHEMA_VERSION,
            "semantics_profile_id": self.semantics_profile_id,
            "semantics_horizon_cap": self.semantics_horizon_cap,
            "observation_log_id": self.observation_log_id,
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "observation_authority_id": self.observation_authority_id,
            "acquisition_manifest_id": self.acquisition_manifest_id,
            "model_id": self.model.model_id,
            "observed_ground_row_count": self.observed_ground_row_count,
            "missing_ground_row_count": self.missing_ground_row_count,
            "exact_kernel_queries_during_construction": self.exact_kernel_queries_during_construction,
            "generative_oracle_samples_during_construction": self.generative_oracle_samples_during_construction,
            "synthetic_model_rollouts_used_as_evidence": self.synthetic_model_rollouts_used_as_evidence,
            "construction_query_inputs_used": self.construction_query_inputs_used,
            "acquisition_query_inputs_used": self.acquisition_query_inputs_used,
            "claim_kind": self.claim_kind,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _external_boundary_id(log: ObservationLogManifestV1) -> str:
    return _content_id(
        "external_boundary",
        {
            "schema": "acfqp.partial_rapm_external_boundary.v1",
            "structural_id": log.structural_id,
            "environment_instance_id": log.environment_instance_id,
            "observation_log_id": log.log_id,
            "semantics": "unregistered_active_successor_with_vacuous_continuation_v1",
        },
    )


def _state_coordinate_values(
    catalogue: TrustedCompleteActionCatalogueV1,
    proposal: FrozenCoordinateProposalV1,
) -> tuple[int, ...]:
    values: list[int] = []
    for expression in proposal.state_expressions:
        if expression.operation is CoordinateOperation.LEGAL_ACTION_COUNT:
            values.append(len(catalogue.actions))
        else:  # pragma: no cover - enum/profile closes this branch
            raise ObservationPartialRAPMInvariantViolation(
                "unsupported state coordinate operation"
            )
    return tuple(values)


def _action_label_values(
    state: CanonicalStateObservationV1,
    action: CanonicalGroundActionV1,
    proposal: FrozenCoordinateProposalV1,
) -> tuple[bool, ...]:
    values: list[bool] = []
    for expression in proposal.action_expressions:
        if expression.operation is CoordinateOperation.COMPLETES_MATCH:
            values.append(state.buffer_counts[action.selected_type] == 2)
        else:  # pragma: no cover - enum/profile closes this branch
            raise ObservationPartialRAPMInvariantViolation(
                "unsupported action coordinate operation"
            )
    return tuple(values)


def _reward_intervals(
    known: Mapping[str, Fraction],
    unknown_mass: Fraction,
    caps: tuple[RewardFeatureCapV1, ...],
) -> tuple[NamedIntervalV1, ...]:
    return tuple(
        NamedIntervalV1(
            cap.name,
            ExactIntervalV1(
                known.get(cap.name, Fraction(0)) + unknown_mass * cap.lower,
                known.get(cap.name, Fraction(0)) + unknown_mass * cap.upper,
            ),
        )
        for cap in caps
    )


def _ambiguity_payload(
    *,
    known_reward: Mapping[str, Fraction],
    known_successor: Mapping[str, Fraction],
    known_failure: Fraction,
    known_terminal: Fraction,
    unknown_mass: Fraction,
    destinations: tuple[str, ...],
    external_boundary_id: str,
    caps: tuple[RewardFeatureCapV1, ...],
) -> AmbiguityPayloadV1:
    successor_intervals = tuple(
        DestinationIntervalV1(
            destination,
            ExactIntervalV1(
                known_successor.get(destination, Fraction(0)),
                known_successor.get(destination, Fraction(0)) + unknown_mass,
            ),
        )
        for destination in destinations
    )
    joint_atoms = tuple(
        sorted(
            (
                *(JointOutcomeAtomV1(JointOutcomeKind.CONTINUATION, destination) for destination in destinations),
                JointOutcomeAtomV1(JointOutcomeKind.TERMINAL_SUCCESS, None),
                JointOutcomeAtomV1(JointOutcomeKind.TERMINAL_FAILURE, None),
            ),
            key=lambda item: item.atom_id,
        )
    )
    joint_constraint = JointSimplexConstraintV1(
        tuple(item.atom_id for item in joint_atoms),
        sum(known_successor.values(), Fraction(0)),
        known_terminal,
        unknown_mass,
    )
    return AmbiguityPayloadV1(
        known_reward_features=tuple(sorted(known_reward.items())),
        known_successor_masses=tuple(
            sorted((destination, mass) for destination, mass in known_successor.items() if mass > 0)
        ),
        known_failure_mass=known_failure,
        known_terminal_mass=known_terminal,
        unknown_mass=unknown_mass,
        unknown_successor_destination_ids=destinations,
        external_boundary_id=external_boundary_id,
        reward_intervals=_reward_intervals(known_reward, unknown_mass, caps),
        successor_intervals=successor_intervals,
        failure_interval=ExactIntervalV1(known_failure, known_failure + unknown_mass),
        terminal_interval=ExactIntervalV1(known_terminal, known_terminal + unknown_mass),
        joint_outcome_atoms=joint_atoms,
        joint_simplex_constraint=joint_constraint,
    )


def _expected_typed_action_atoms_v2(
    proposal: FrozenTypedCoordinateProposalV2,
    value_table: FrozenTypedCoordinateValueTableV2,
) -> tuple[FrozenTypedActionCoordinateAtomV2, ...]:
    if not proposal.action_expression_ids:
        return (
            FrozenTypedActionCoordinateAtomV2(
                TypedActionAtomKind.UNIVERSAL_TRUE, None, None
            ),
        )
    atoms: list[FrozenTypedActionCoordinateAtomV2] = []
    for expression_id in proposal.action_expression_ids:
        index = value_table.action_expression_ids.index(expression_id)
        values = tuple(row.values[index] for row in value_table.action_rows)
        runtime_types = {type(value) for value in values}
        if runtime_types == {bool}:
            atoms.append(
                FrozenTypedActionCoordinateAtomV2(
                    TypedActionAtomKind.BOOLEAN_IDENTITY, expression_id, None
                )
            )
        elif runtime_types == {int}:
            distinct = tuple(sorted(set(values)))
            atoms.extend(
                FrozenTypedActionCoordinateAtomV2(
                    TypedActionAtomKind.INTEGER_LEQ,
                    expression_id,
                    Fraction(left + right, 2),
                )
                for left, right in zip(distinct, distinct[1:])
            )
        else:
            raise ObservationPartialRAPMInvariantViolation(
                "typed action-coordinate column changes or violates its scalar type"
            )
    if not atoms:
        raise ObservationPartialRAPMInvariantViolation(
            "a nonempty action-program subset compiled to no separating boolean atom"
        )
    return tuple(sorted(atoms, key=lambda item: item.atom_id))


def _validate_typed_coordinate_runtime_types_v2(
    proposal: FrozenTypedCoordinateProposalV2,
    value_table: FrozenTypedCoordinateValueTableV2,
) -> None:
    """Validate the complete V2 object shape before reading a derived ID."""

    if type(proposal) is not FrozenTypedCoordinateProposalV2:
        raise ObservationPartialRAPMInvariantViolation(
            "typed source replay rejects a coordinate-proposal substitution"
        )
    if type(value_table) is not FrozenTypedCoordinateValueTableV2:
        raise ObservationPartialRAPMInvariantViolation(
            "typed source replay rejects a coordinate-value-table substitution"
        )

    def require_fields(
        instance: Any,
        specification: tuple[tuple[str, tuple[type, ...]], ...],
        scope: str,
    ) -> None:
        for field, allowed in specification:
            value = object.__getattribute__(instance, field)
            if type(value) not in allowed:
                raise ObservationPartialRAPMInvariantViolation(
                    f"typed source replay rejects malformed {scope}.{field} before canonical access"
                )

    require_fields(
        proposal,
        (
            ("state_expression_ids", (tuple,)),
            ("action_expression_ids", (tuple,)),
            ("action_atoms", (tuple,)),
            ("dsl_registry_id", (str,)),
            ("structural_binding_id", (str,)),
            ("value_table_id", (str,)),
            ("synthesis_spec_id", (str,)),
            ("selected_candidate_id", (str,)),
            ("candidate_trace_id", (str,)),
            ("observation_log_id", (str,)),
            ("semantics_profile_id", (str,)),
            ("observation_authority_id", (str,)),
            ("acquisition_manifest_id", (str,)),
            ("origin", (str,)),
            ("query_neutral", (bool,)),
            ("target_exact_audit_used", (bool,)),
            ("callable_adapter_present", (bool,)),
            ("schema_version", (str,)),
        ),
        "coordinate proposal",
    )
    for values, scope in (
        (proposal.state_expression_ids, "proposal state-expression IDs"),
        (proposal.action_expression_ids, "proposal action-expression IDs"),
    ):
        if any(type(item) is not str for item in values):
            raise ObservationPartialRAPMInvariantViolation(
                f"typed source replay rejects malformed {scope} before canonical access"
            )
    if any(
        type(item) is not FrozenTypedActionCoordinateAtomV2
        for item in proposal.action_atoms
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "typed source replay rejects nested action-atom substitutions before canonical access"
        )
    for atom in proposal.action_atoms:
        require_fields(
            atom,
            (
                ("kind", (TypedActionAtomKind,)),
                ("source_expression_id", (str, type(None))),
                ("threshold", (Fraction, type(None))),
            ),
            "action atom",
        )

    require_fields(
        value_table,
        (
            ("observation_log_id", (str,)),
            ("semantics_profile_id", (str,)),
            ("observation_authority_id", (str,)),
            ("structural_binding_id", (str,)),
            ("dsl_registry_id", (str,)),
            ("state_expression_ids", (tuple,)),
            ("action_expression_ids", (tuple,)),
            ("state_rows", (tuple,)),
            ("action_rows", (tuple,)),
            ("source_kind", (str,)),
            ("callable_evaluator_present", (bool,)),
            ("schema_version", (str,)),
        ),
        "coordinate value table",
    )
    for values, scope in (
        (value_table.state_expression_ids, "table state-expression IDs"),
        (value_table.action_expression_ids, "table action-expression IDs"),
    ):
        if any(type(item) is not str for item in values):
            raise ObservationPartialRAPMInvariantViolation(
                f"typed source replay rejects malformed {scope} before canonical access"
            )
    if any(type(item) is not FrozenStateCoordinateValuesV2 for item in value_table.state_rows):
        raise ObservationPartialRAPMInvariantViolation(
            "typed source replay rejects nested state-value rows before canonical access"
        )
    if any(type(item) is not FrozenActionCoordinateValuesV2 for item in value_table.action_rows):
        raise ObservationPartialRAPMInvariantViolation(
            "typed source replay rejects nested action-value rows before canonical access"
        )
    for row in value_table.state_rows:
        require_fields(
            row,
            (("state_id", (str,)), ("values", (tuple,))),
            "state-value row",
        )
        if any(type(value) not in (int, bool) for value in row.values):
            raise ObservationPartialRAPMInvariantViolation(
                "typed source replay rejects malformed state values before canonical access"
            )
    for row in value_table.action_rows:
        require_fields(
            row,
            (
                ("ground_row_id", (str,)),
                ("state_id", (str,)),
                ("ground_action_id", (str,)),
                ("values", (tuple,)),
            ),
            "action-value row",
        )
        if any(type(value) not in (int, bool) for value in row.values):
            raise ObservationPartialRAPMInvariantViolation(
                "typed source replay rejects malformed action values before canonical access"
            )


def _validate_typed_coordinate_source_v2(
    log: ObservationLogManifestV1,
    proposal: FrozenTypedCoordinateProposalV2,
    value_table: FrozenTypedCoordinateValueTableV2,
    semantics: DeterministicObservationProfileV1,
    authority: PreregisteredObservationAuthorityV1,
) -> None:
    _validate_typed_coordinate_runtime_types_v2(proposal, value_table)
    if (
        proposal.observation_log_id != log.log_id
        or proposal.semantics_profile_id != semantics.profile_id
        or proposal.observation_authority_id != authority.authority_id
        or proposal.acquisition_manifest_id != authority.acquisition_manifest.manifest_id
        or proposal.value_table_id != value_table.value_table_id
        or proposal.dsl_registry_id != value_table.dsl_registry_id
        or proposal.structural_binding_id != value_table.structural_binding_id
        or value_table.observation_log_id != log.log_id
        or value_table.semantics_profile_id != semantics.profile_id
        or value_table.observation_authority_id != authority.authority_id
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "typed proposal/value table differs from the allowlisted source graph"
        )
    if not set(proposal.state_expression_ids) <= set(value_table.state_expression_ids):
        raise ObservationPartialRAPMInvariantViolation(
            "typed proposal uses an unregistered state expression"
        )
    if not set(proposal.action_expression_ids) <= set(value_table.action_expression_ids):
        raise ObservationPartialRAPMInvariantViolation(
            "typed proposal uses an unregistered action expression"
        )
    expected_state_ids = tuple(item.state_id for item in log.states)
    if tuple(item.state_id for item in value_table.state_rows) != expected_state_ids:
        raise ObservationPartialRAPMInvariantViolation(
            "typed value table does not cover every registered state exactly once"
        )
    expected_actions = {
        action.ground_row_id: action
        for catalogue in log.action_catalogues
        for action in catalogue.actions
    }
    if tuple(item.ground_row_id for item in value_table.action_rows) != tuple(
        sorted(expected_actions)
    ):
        raise ObservationPartialRAPMInvariantViolation(
            "typed value table does not cover every registered ground row exactly once"
        )
    for row in value_table.action_rows:
        expected = expected_actions[row.ground_row_id]
        if row.state_id != expected.state_id or row.ground_action_id != expected.action_id:
            raise ObservationPartialRAPMInvariantViolation(
                "typed action-coordinate row differs from the complete action catalogue"
            )
    for column in range(len(value_table.state_expression_ids)):
        types = {type(row.values[column]) for row in value_table.state_rows}
        if len(types) != 1:
            raise ObservationPartialRAPMInvariantViolation(
                "typed state-coordinate column changes runtime scalar type"
            )
    for column in range(len(value_table.action_expression_ids)):
        types = {type(row.values[column]) for row in value_table.action_rows}
        if len(types) != 1:
            raise ObservationPartialRAPMInvariantViolation(
                "typed action-coordinate column changes runtime scalar type"
            )
    if proposal.action_atoms != _expected_typed_action_atoms_v2(proposal, value_table):
        raise ObservationPartialRAPMInvariantViolation(
            "typed proposal action atoms differ from exact midpoint/identity compilation"
        )



def _derive_partial_model_v1(
    log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1 | FrozenTypedCoordinateProposalV2,
    semantics: DeterministicObservationProfileV1,
    authority: PreregisteredObservationAuthorityV1,
    coordinate_value_table: FrozenTypedCoordinateValueTableV2 | None = None,
) -> PortablePartialRAPMV1:
    _validate_preregistered_observation_authority_v1(log, semantics, authority)
    typed_coordinate_path = type(coordinate_proposal) is FrozenTypedCoordinateProposalV2
    state_by_id = {item.state_id: item for item in log.states}
    catalogue_by_state = {item.state_id: item for item in log.action_catalogues}
    action_by_id = {
        action.action_id: action
        for catalogue in log.action_catalogues
        for action in catalogue.actions
    }
    if type(coordinate_proposal) is FrozenCoordinateProposalV1:
        if coordinate_value_table is not None:
            raise ObservationPartialRAPMInvariantViolation(
                "manual V1 proposal cannot consume a typed value table"
            )
        proposal_id = coordinate_proposal.proposal_id
        state_coordinates_by_id = {
            state.state_id: _state_coordinate_values(
                catalogue_by_state[state.state_id], coordinate_proposal
            )
            for state in log.states
        }
        action_labels_by_row = {
            action.ground_row_id: _action_label_values(
                state_by_id[action.state_id], action, coordinate_proposal
            )
            for action in action_by_id.values()
        }
    elif type(coordinate_proposal) is FrozenTypedCoordinateProposalV2 and type(
        coordinate_value_table
    ) is FrozenTypedCoordinateValueTableV2:
        _validate_typed_coordinate_source_v2(
            log, coordinate_proposal, coordinate_value_table, semantics, authority
        )
        proposal_id = coordinate_proposal.proposal_id
        state_indexes = tuple(
            coordinate_value_table.state_expression_ids.index(expression_id)
            for expression_id in coordinate_proposal.state_expression_ids
        )
        state_coordinates_by_id = {
            row.state_id: tuple(row.values[index] for index in state_indexes)
            for row in coordinate_value_table.state_rows
        }
        if any(type(value) is not int for values in state_coordinates_by_id.values() for value in values):
            raise ObservationPartialRAPMInvariantViolation(
                "selected state-coordinate programs must return exact integers"
            )
        action_labels_by_row: dict[str, tuple[bool, ...]] = {}
        for row in coordinate_value_table.action_rows:
            labels: list[bool] = []
            for atom in coordinate_proposal.action_atoms:
                if atom.kind is TypedActionAtomKind.UNIVERSAL_TRUE:
                    labels.append(True)
                    continue
                index = coordinate_value_table.action_expression_ids.index(
                    atom.source_expression_id
                )
                value = row.values[index]
                if atom.kind is TypedActionAtomKind.BOOLEAN_IDENTITY:
                    if type(value) is not bool:
                        raise ObservationPartialRAPMInvariantViolation(
                            "boolean identity action atom received a nonboolean value"
                        )
                    labels.append(value)
                else:
                    if type(value) is not int:
                        raise ObservationPartialRAPMInvariantViolation(
                            "integer threshold action atom received a noninteger value"
                        )
                    labels.append(Fraction(value) <= atom.threshold)
            action_labels_by_row[row.ground_row_id] = tuple(labels)
    else:
        raise ObservationPartialRAPMInvariantViolation(
            "coordinate proposal/value-table schema pairing is invalid"
        )

    grouped: dict[tuple[PlanningKind, tuple[int, ...]], list[str]] = {}
    for state in log.states:
        coordinates = (
            state_coordinates_by_id[state.state_id]
            if state.planning_kind is PlanningKind.ACTIVE
            else ()
        )
        grouped.setdefault((state.planning_kind, coordinates), []).append(state.state_id)
    cells = tuple(
        sorted(
            (
                PartialCellV1(tuple(sorted(member_ids)), planning_kind, coordinates)
                for (planning_kind, coordinates), member_ids in grouped.items()
            ),
            key=lambda item: item.cell_id,
        )
    )
    cell_by_state = {
        state_id: cell
        for cell in cells
        for state_id in cell.member_state_ids
    }
    external_boundary_id = _external_boundary_id(log)
    active_cell_ids = tuple(
        sorted(cell.cell_id for cell in cells if cell.planning_kind is PlanningKind.ACTIVE)
    )
    destinations = tuple(sorted((*active_cell_ids, external_boundary_id)))

    observations_by_row: dict[str, list[DeterministicTransitionObservationV1]] = {}
    for observation in log.observations:
        observations_by_row.setdefault(observation.ground_row_id, []).append(observation)

    ground_rows: list[PartialGroundRowV1] = []
    ground_row_by_id: dict[str, PartialGroundRowV1] = {}
    for action in sorted(action_by_id.values(), key=lambda item: item.ground_row_id):
        observations = observations_by_row.get(action.ground_row_id, [])
        if observations:
            observation = observations[0]
            known_reward = dict(observation.reward_features)
            known_successor: dict[str, Fraction] = {}
            if not observation.terminal:
                destination = (
                    cell_by_state[observation.successor.reference].cell_id
                    if observation.successor.kind is SuccessorKind.REGISTERED_STATE
                    else external_boundary_id
                )
                known_successor[destination] = Fraction(1)
            ambiguity = _ambiguity_payload(
                known_reward=known_reward,
                known_successor=known_successor,
                known_failure=Fraction(int(observation.failure)),
                known_terminal=Fraction(int(observation.terminal)),
                unknown_mass=Fraction(0),
                destinations=destinations,
                external_boundary_id=external_boundary_id,
                caps=semantics.reward_feature_caps,
            )
            row = PartialGroundRowV1(
                action.ground_row_id,
                action.state_id,
                action.action_id,
                AmbiguityRowStatus.OBSERVED_SINGLETON,
                tuple(sorted(item.observation_id for item in observations)),
                ambiguity,
            )
        else:
            ambiguity = _ambiguity_payload(
                known_reward={},
                known_successor={},
                known_failure=Fraction(0),
                known_terminal=Fraction(0),
                unknown_mass=Fraction(1),
                destinations=destinations,
                external_boundary_id=external_boundary_id,
                caps=semantics.reward_feature_caps,
            )
            row = PartialGroundRowV1(
                action.ground_row_id,
                action.state_id,
                action.action_id,
                AmbiguityRowStatus.MISSING_VACUOUS,
                (),
                ambiguity,
            )
        ground_rows.append(row)
        ground_row_by_id[row.ground_row_id] = row
    ground_rows_tuple = tuple(ground_rows)

    semantic_actions: list[PartialSemanticActionV1] = []
    concretizer_rows: list[ConcretizerRowV1] = []
    semantic_realizations: list[PartialSemanticRealizationV1] = []
    for cell in cells:
        if cell.planning_kind is not PlanningKind.ACTIVE:
            continue
        labels_by_state: dict[str, dict[tuple[bool, ...], list[CanonicalGroundActionV1]]] = {}
        common_labels: set[tuple[bool, ...]] | None = None
        for state_id in cell.member_state_ids:
            grouped_actions: dict[tuple[bool, ...], list[CanonicalGroundActionV1]] = {}
            for action in catalogue_by_state[state_id].actions:
                label = action_labels_by_row[action.ground_row_id]
                grouped_actions.setdefault(label, []).append(action)
            labels_by_state[state_id] = grouped_actions
            labels = set(grouped_actions)
            common_labels = labels if common_labels is None else common_labels & labels
        if typed_coordinate_path and any(
            set(labels_by_state[state_id]) != common_labels
            for state_id in cell.member_state_ids
        ):
            raise ObservationPartialRAPMInvariantViolation(
                "typed active-cell members must expose exactly the same semantic label set"
            )
        if not common_labels:
            raise ObservationPartialRAPMInvariantViolation(
                "active abstract cell has no common semantic action"
            )
        for label in sorted(common_labels):
            semantic_action = PartialSemanticActionV1(cell.cell_id, label)
            semantic_actions.append(semantic_action)
            for state_id in cell.member_state_ids:
                support_actions = tuple(
                    sorted(labels_by_state[state_id][label], key=lambda item: item.action_id)
                )
                weight = Fraction(1, len(support_actions))
                concretizer_rows.append(
                    ConcretizerRowV1(
                        state_id,
                        cell.cell_id,
                        semantic_action.semantic_action_id,
                        tuple((action.action_id, weight) for action in support_actions),
                    )
                )
                support_rows = tuple(
                    ground_row_by_id[action.ground_row_id] for action in support_actions
                )
                observed_ids = tuple(
                    sorted(
                        row.ground_row_id
                        for row in support_rows
                        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
                    )
                )
                missing_ids = tuple(
                    sorted(
                        row.ground_row_id
                        for row in support_rows
                        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
                    )
                )
                known_reward: dict[str, Fraction] = {}
                known_successor: dict[str, Fraction] = {}
                known_failure = Fraction(0)
                known_terminal = Fraction(0)
                for row in support_rows:
                    if row.status is not AmbiguityRowStatus.OBSERVED_SINGLETON:
                        continue
                    for name, value in row.ambiguity.known_reward_features:
                        known_reward[name] = known_reward.get(name, Fraction(0)) + weight * value
                    for destination, mass in row.ambiguity.known_successor_masses:
                        known_successor[destination] = known_successor.get(destination, Fraction(0)) + weight * mass
                    known_failure += weight * row.ambiguity.known_failure_mass
                    known_terminal += weight * row.ambiguity.known_terminal_mass
                unknown_mass = Fraction(len(missing_ids), len(support_rows))
                semantic_realizations.append(
                    PartialSemanticRealizationV1(
                        state_id,
                        cell.cell_id,
                        semantic_action.semantic_action_id,
                        tuple(sorted(row.ground_row_id for row in support_rows)),
                        observed_ids,
                        missing_ids,
                        _ambiguity_payload(
                            known_reward=known_reward,
                            known_successor=known_successor,
                            known_failure=known_failure,
                            known_terminal=known_terminal,
                            unknown_mass=unknown_mass,
                            destinations=destinations,
                            external_boundary_id=external_boundary_id,
                            caps=semantics.reward_feature_caps,
                        ),
                    )
                )

    semantic_actions_tuple = tuple(
        sorted(semantic_actions, key=lambda item: item.semantic_action_id)
    )
    concretizer_tuple = tuple(
        sorted(concretizer_rows, key=lambda item: (item.state_id, item.semantic_action_id))
    )
    realizations_tuple = tuple(
        sorted(semantic_realizations, key=lambda item: (item.state_id, item.semantic_action_id))
    )
    observed_row_ids = tuple(
        row.ground_row_id
        for row in ground_rows_tuple
        if row.status is AmbiguityRowStatus.OBSERVED_SINGLETON
    )
    missing_row_ids = tuple(
        row.ground_row_id
        for row in ground_rows_tuple
        if row.status is AmbiguityRowStatus.MISSING_VACUOUS
    )
    coverage = ObservationCoverageV1(
        tuple(item.state_id for item in log.states),
        tuple(row.ground_row_id for row in ground_rows_tuple),
        observed_row_ids,
        missing_row_ids,
        external_boundary_id,
    )
    return PortablePartialRAPMV1(
        semantics.profile_id,
        semantics.horizon_cap,
        log.log_id,
        proposal_id,
        authority.authority_id,
        authority.acquisition_manifest.manifest_id,
        authority.acquisition_manifest.coverage_id,
        log.evidence_ledger.ledger_id,
        coverage,
        external_boundary_id,
        cells,
        semantic_actions_tuple,
        concretizer_tuple,
        ground_rows_tuple,
        realizations_tuple,
        semantics.reward_feature_caps,
    )


def validate_preregistered_observation_source_graph_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> None:
    """Replay the complete hardened V0-042 source graph without building a model."""
    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects duck observation logs"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects duck semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservationPartialRAPMInvariantViolation(
            "source replay rejects duck observation authorities"
        )
    _validate_preregistered_observation_authority_v1(
        observation_log, semantics_profile, observation_authority
    )


def build_observation_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ObservationPartialRAPMBuildV1:
    """Build a query-neutral partial RAPM without a ground transition API."""

    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservationPartialRAPMInvariantViolation(
            "constructor rejects duck observation logs"
        )
    if type(coordinate_proposal) is not FrozenCoordinateProposalV1:
        raise ObservationPartialRAPMInvariantViolation(
            "constructor rejects duck coordinate proposals"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservationPartialRAPMInvariantViolation(
            "constructor rejects duck semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservationPartialRAPMInvariantViolation(
            "constructor rejects duck observation authorities"
        )
    model = _derive_partial_model_v1(
        observation_log, coordinate_proposal, semantics_profile, observation_authority
    )
    return ObservationPartialRAPMBuildV1(
        semantics_profile.profile_id,
        semantics_profile.horizon_cap,
        observation_log.log_id,
        coordinate_proposal.proposal_id,
        observation_authority.authority_id,
        observation_authority.acquisition_manifest.manifest_id,
        model,
        len(model.coverage.observed_ground_row_ids),
        len(model.coverage.missing_ground_row_ids),
    )


def verify_observation_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    claimed_result: ObservationPartialRAPMBuildV1,
) -> tuple[str, ...]:
    """Reconstruct the model from the allowlisted authority graph and compare bytes.

    The verifier receives neither a kernel nor a query.  It does not trust any
    claimed coverage, known mass, interval, or content ID in ``claimed_result``;
    the supplied log/profile/AST graph is accepted only through the frozen external
    observation-authority allowlist.
    """

    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservationPartialRAPMInvariantViolation(
            "verifier rejects duck observation logs"
        )
    if type(coordinate_proposal) is not FrozenCoordinateProposalV1:
        raise ObservationPartialRAPMInvariantViolation(
            "verifier rejects duck coordinate proposals"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservationPartialRAPMInvariantViolation(
            "verifier rejects duck semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservationPartialRAPMInvariantViolation(
            "verifier rejects duck observation authorities"
        )
    if type(claimed_result) is not ObservationPartialRAPMBuildV1:
        raise ObservationPartialRAPMInvariantViolation(
            "verifier rejects duck build results"
        )
    expected_model = _derive_partial_model_v1(
        observation_log, coordinate_proposal, semantics_profile, observation_authority
    )
    expected = ObservationPartialRAPMBuildV1(
        semantics_profile.profile_id,
        semantics_profile.horizon_cap,
        observation_log.log_id,
        coordinate_proposal.proposal_id,
        observation_authority.authority_id,
        observation_authority.acquisition_manifest.manifest_id,
        expected_model,
        len(expected_model.coverage.observed_ground_row_ids),
        len(expected_model.coverage.missing_ground_row_ids),
    )
    failures: list[str] = []
    if claimed_result.observation_log_id != observation_log.log_id:
        failures.append("OBSERVATION_LOG_ID_MISMATCH")
    if claimed_result.observation_authority_id != observation_authority.authority_id:
        failures.append("OBSERVATION_AUTHORITY_ID_MISMATCH")
    if claimed_result.acquisition_manifest_id != observation_authority.acquisition_manifest.manifest_id:
        failures.append("ACQUISITION_MANIFEST_ID_MISMATCH")
    if claimed_result.model.to_document() != expected.model.to_document():
        failures.append("MODEL_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected.to_document():
        failures.append("RESULT_RECONSTRUCTION_MISMATCH")
    return tuple(failures)


def build_observation_partial_rapm_from_typed_values_v2(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenTypedCoordinateProposalV2,
    coordinate_value_table: FrozenTypedCoordinateValueTableV2,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ObservationPartialRAPMBuildV1:
    """Internal pure derivation for an already-authorized typed value table.

    This helper does not establish how the proposal or table was obtained and
    therefore is not a coordinate-synthesis authority.  Production consumers
    must accept and replay the complete V0-045 synthesis result instead.
    """
    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservationPartialRAPMInvariantViolation("typed constructor rejects duck observation logs")
    if type(coordinate_proposal) is not FrozenTypedCoordinateProposalV2:
        raise ObservationPartialRAPMInvariantViolation("typed constructor rejects duck coordinate proposals")
    if type(coordinate_value_table) is not FrozenTypedCoordinateValueTableV2:
        raise ObservationPartialRAPMInvariantViolation("typed constructor rejects duck coordinate value tables")
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservationPartialRAPMInvariantViolation("typed constructor rejects duck semantics profiles")
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservationPartialRAPMInvariantViolation("typed constructor rejects duck observation authorities")
    model = _derive_partial_model_v1(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        coordinate_value_table,
    )
    return ObservationPartialRAPMBuildV1(
        semantics_profile.profile_id,
        semantics_profile.horizon_cap,
        observation_log.log_id,
        coordinate_proposal.proposal_id,
        observation_authority.authority_id,
        observation_authority.acquisition_manifest.manifest_id,
        model,
        len(model.coverage.observed_ground_row_ids),
        len(model.coverage.missing_ground_row_ids),
    )


def verify_observation_partial_rapm_from_typed_values_v2(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenTypedCoordinateProposalV2,
    coordinate_value_table: FrozenTypedCoordinateValueTableV2,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    claimed_result: ObservationPartialRAPMBuildV1,
) -> tuple[str, ...]:
    """Check the internal typed-table derivation, not synthesis provenance.

    Passing this check alone never authorizes a typed coordinate proposal or a
    downstream planning certificate; that requires full V0-045 replay.
    """
    if type(claimed_result) is not ObservationPartialRAPMBuildV1:
        raise ObservationPartialRAPMInvariantViolation("typed verifier rejects duck build results")
    expected = build_observation_partial_rapm_from_typed_values_v2(
        observation_log,
        coordinate_proposal,
        coordinate_value_table,
        semantics_profile,
        observation_authority,
    )
    failures: list[str] = []
    if claimed_result.observation_log_id != observation_log.log_id:
        failures.append("OBSERVATION_LOG_ID_MISMATCH")
    if claimed_result.coordinate_proposal_id != coordinate_proposal.proposal_id:
        failures.append("COORDINATE_PROPOSAL_ID_MISMATCH")
    if claimed_result.observation_authority_id != observation_authority.authority_id:
        failures.append("OBSERVATION_AUTHORITY_ID_MISMATCH")
    if claimed_result.acquisition_manifest_id != observation_authority.acquisition_manifest.manifest_id:
        failures.append("ACQUISITION_MANIFEST_ID_MISMATCH")
    if claimed_result.model.to_document() != expected.model.to_document():
        failures.append("MODEL_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected.to_document():
        failures.append("RESULT_RECONSTRUCTION_MISMATCH")
    return tuple(failures)

__all__ = [
    "AmbiguityPayloadV1",
    "AmbiguityRowStatus",
    "CanonicalGroundActionV1",
    "CanonicalStateObservationV1",
    "ConcretizerRowV1",
    "CoordinateAncestryRefV1",
    "CoordinateContext",
    "CoordinateOperation",
    "DeterministicObservationProfileV1",
    "DeterministicTransitionObservationV1",
    "DestinationIntervalV1",
    "EvidenceClass",
    "EvidenceCounterV1",
    "EvidenceLane",
    "EvidenceLedgerV1",
    "ExactIntervalV1",
    "FrozenActionCoordinateValuesV2",
    "FrozenTypedActionCoordinateAtomV2",
    "FrozenCoordinateExpressionV1",
    "FrozenCoordinateProposalV1",
    "FrozenStateCoordinateValuesV2",
    "FrozenTypedCoordinateProposalV2",
    "FrozenTypedCoordinateValueTableV2",
    "JointOutcomeAtomV1",
    "JointOutcomeKind",
    "JointSimplexConstraintV1",
    "NamedIntervalV1",
    "ObservationAuthorityEventBindingV1",
    "ObservationCoverageV1",
    "ObservationLogManifestV1",
    "ObservationPartialRAPMBuildV1",
    "ObservationPartialRAPMInvariantViolation",
    "ObservedSuccessorRefV1",
    "PartialCellV1",
    "PartialGroundRowV1",
    "PartialSemanticActionV1",
    "PartialSemanticRealizationV1",
    "PlanningKind",
    "PortablePartialRAPMV1",
    "QueryScopedPartialRAPMV2",
    "QueryScopedPartialRAPMV3",
    "PREREGISTERED_OBSERVATION_AUTHORITY_IDS",
    "PreregisteredAcquisitionManifestV1",
    "PreregisteredObservationAuthorityV1",
    "RewardFeatureCapV1",
    "SuccessorKind",
    "TYPED_COORDINATE_SCHEMA_VERSION",
    "TrustedCompleteActionCatalogueV1",
    "TypedActionAtomKind",
    "build_observation_partial_rapm_v1",
    "validate_preregistered_observation_source_graph_v1",
    "verify_observation_partial_rapm_v1",
]
