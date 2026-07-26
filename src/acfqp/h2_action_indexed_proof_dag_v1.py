"""Action-indexed H2 proof DAG for the registered V0-054B semantic switch.

This module is deliberately model-only.  It contains no ground-domain or
kernel import and accepts no transition callback.  The registered five-row
model is small enough to make every lower proof dependency explicit:

* five ground-row leaves;
* the two semantic-action mixtures;
* the unrestricted H2 recurrence;
* the two fixed-plan value, regret, risk and coverage branches; and
* one deterministic selection node.

Lower proof keys bind exact content slices, query facets and ordered parent
entries, but never a whole model, epoch or query identity.  Three role-bound
roots are freshly materialized per epoch and are never inserted into the lower
cache.  Consequently the one-row ``M`` delta rebuilds exactly the reverse-edge
closure of that leaf while retaining the eight unaffected lower entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_h2_action_indexed_semantic_switch_v0"

FORMULA_IDS = {
    "ROW": "ACTION_INDEXED_EXACT_OR_VACUOUS_GROUND_ROW_V1",
    "Q": "ACTION_INDEXED_UNIFORM_SEMANTIC_ACTION_MIXTURE_V1",
    "U1": "ACTION_INDEXED_H2_UNRESTRICTED_STAGE_ONE_MAX_V1",
    "U0": "ACTION_INDEXED_H2_UNRESTRICTED_STAGE_ZERO_RECURRENCE_V1",
    "PLAN": "ACTION_INDEXED_H2_FIXED_PLAN_RECURRENCE_V1",
    "REGRET": "ACTION_INDEXED_NORMALIZED_REGRET_V1",
    "RISK": "ACTION_INDEXED_FAILURE_UPPER_GATE_V1",
    "COVERAGE": "ACTION_INDEXED_SELECTED_ROW_COVERAGE_GATE_V1",
    "SELECTION": "ACTION_INDEXED_CERTIFICATE_FIRST_SEMANTIC_SELECTION_V1",
    "ROOT": "ACTION_INDEXED_FULL_ROLE_BOUND_ROOT_V1",
}

DOMAIN_TAGS = {
    "row": "acfqp:action-indexed-ground-row:v1",
    "model": "acfqp:action-indexed-h2-model:v1",
    "query": "acfqp:action-indexed-h2-query:v1",
    "slice": "acfqp:action-indexed-model-slice:v1",
    "result": "acfqp:action-indexed-proof-result:v1",
    "node_key": "acfqp:action-indexed-proof-node-key:v1",
    "node": "acfqp:action-indexed-proof-node:v1",
    "resolution": "acfqp:action-indexed-proof-resolution:v1",
    "runtime": "acfqp:action-indexed-proof-runtime-snapshot:v1",
    "work": "acfqp:action-indexed-proof-work:v1",
    "audit": "acfqp:action-indexed-candidate-audit:v1",
    "root": "acfqp:action-indexed-proof-root:v1",
    "proposal": "acfqp:action-indexed-plan-proposal:v1",
    "execution": "acfqp:action-indexed-epoch-execution:v1",
    "restore": "acfqp:action-indexed-first-runtime-restore:v1",
    "final_restore": "acfqp:action-indexed-final-runtime-restore:v1",
    "restored_roots": "acfqp:action-indexed-restored-root-replay:v1",
    "delta": "acfqp:action-indexed-model-delta:v1",
    "edge": "acfqp:action-indexed-invalidation-edge:v1",
    "pre_invalidation": "acfqp:action-indexed-preexecution-invalidation:v1",
    "invalidation": "acfqp:action-indexed-invalidation-manifest:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-054B content domains must be unique")


class ActionIndexedProofInvariantViolation(ValueError):
    """The registered model, proof graph, cache, or invalidation is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ActionIndexedProofInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ActionIndexedProofInvariantViolation(
            f"{name} must be a full content ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ActionIndexedProofInvariantViolation(
            f"{name} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ActionIndexedProofInvariantViolation(f"{name} must be exact")
    return Fraction(value)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _ftext(value: Fraction) -> str:
    exact = Fraction(value)
    return f"{exact.numerator}/{exact.denominator}"


def _require_exact_tuple(
    values: Any,
    exact_type: type,
    name: str,
    *,
    nonempty: bool = True,
) -> tuple[Any, ...]:
    if type(values) is not tuple or any(type(item) is not exact_type for item in values):
        raise ActionIndexedProofInvariantViolation(
            f"{name} must be an exact tuple of {exact_type.__name__}"
        )
    if nonempty and not values:
        raise ActionIndexedProofInvariantViolation(f"{name} cannot be empty")
    return values


class GroundRowStatus(str, Enum):
    OBSERVED = "OBSERVED"
    MISSING_VACUOUS = "MISSING_VACUOUS"


class GroundRowName(str, Enum):
    S = "S"
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    M = "M"


class CandidateAction(str, Enum):
    N = "N"
    M = "M"


class ModelEpoch(str, Enum):
    FIRST_4_OBSERVED_1_MISSING = "FIRST_4_OBSERVED_1_MISSING"
    FINAL_5_OBSERVED_0_MISSING = "FINAL_5_OBSERVED_0_MISSING"


class ProofNodeKind(str, Enum):
    GROUND_ROW = "GROUND_ROW"
    SEMANTIC_ACTION_Q = "SEMANTIC_ACTION_Q"
    UNRESTRICTED_VALUE = "UNRESTRICTED_VALUE"
    FIXED_PLAN = "FIXED_PLAN"
    REGRET_GATE = "REGRET_GATE"
    RISK_GATE = "RISK_GATE"
    COVERAGE_GATE = "COVERAGE_GATE"
    SELECTION = "SELECTION"


class ProofAddress(str, Enum):
    ROW_S = "ROW_S"
    ROW_N1 = "ROW_N1"
    ROW_N2 = "ROW_N2"
    ROW_N3 = "ROW_N3"
    ROW_M = "ROW_M"
    Q_N = "Q_N"
    Q_M = "Q_M"
    U1 = "U1"
    U0 = "U0"
    PLAN_N = "PLAN_N"
    PLAN_M = "PLAN_M"
    REGRET_N = "REGRET_N"
    REGRET_M = "REGRET_M"
    RISK_N = "RISK_N"
    RISK_M = "RISK_M"
    COVERAGE_N = "COVERAGE_N"
    COVERAGE_M = "COVERAGE_M"
    SELECTION = "SELECTION"


ADDRESS_ORDER = tuple(ProofAddress)
ADDRESS_INDEX = {address: index for index, address in enumerate(ADDRESS_ORDER)}

ROW_ADDRESS_BY_NAME = {
    GroundRowName.S: ProofAddress.ROW_S,
    GroundRowName.N1: ProofAddress.ROW_N1,
    GroundRowName.N2: ProofAddress.ROW_N2,
    GroundRowName.N3: ProofAddress.ROW_N3,
    GroundRowName.M: ProofAddress.ROW_M,
}
ROW_NAME_BY_ADDRESS = {value: key for key, value in ROW_ADDRESS_BY_NAME.items()}

KIND_BY_ADDRESS = {
    **{
        address: ProofNodeKind.GROUND_ROW
        for address in (
            ProofAddress.ROW_S,
            ProofAddress.ROW_N1,
            ProofAddress.ROW_N2,
            ProofAddress.ROW_N3,
            ProofAddress.ROW_M,
        )
    },
    ProofAddress.Q_N: ProofNodeKind.SEMANTIC_ACTION_Q,
    ProofAddress.Q_M: ProofNodeKind.SEMANTIC_ACTION_Q,
    ProofAddress.U1: ProofNodeKind.UNRESTRICTED_VALUE,
    ProofAddress.U0: ProofNodeKind.UNRESTRICTED_VALUE,
    ProofAddress.PLAN_N: ProofNodeKind.FIXED_PLAN,
    ProofAddress.PLAN_M: ProofNodeKind.FIXED_PLAN,
    ProofAddress.REGRET_N: ProofNodeKind.REGRET_GATE,
    ProofAddress.REGRET_M: ProofNodeKind.REGRET_GATE,
    ProofAddress.RISK_N: ProofNodeKind.RISK_GATE,
    ProofAddress.RISK_M: ProofNodeKind.RISK_GATE,
    ProofAddress.COVERAGE_N: ProofNodeKind.COVERAGE_GATE,
    ProofAddress.COVERAGE_M: ProofNodeKind.COVERAGE_GATE,
    ProofAddress.SELECTION: ProofNodeKind.SELECTION,
}

EXPECTED_PARENT_ADDRESSES = {
    ProofAddress.ROW_S: (),
    ProofAddress.ROW_N1: (),
    ProofAddress.ROW_N2: (),
    ProofAddress.ROW_N3: (),
    ProofAddress.ROW_M: (),
    ProofAddress.Q_N: (
        ProofAddress.ROW_N1,
        ProofAddress.ROW_N2,
        ProofAddress.ROW_N3,
    ),
    ProofAddress.Q_M: (ProofAddress.ROW_M,),
    ProofAddress.U1: (ProofAddress.Q_N, ProofAddress.Q_M),
    ProofAddress.U0: (ProofAddress.ROW_S, ProofAddress.U1),
    ProofAddress.PLAN_N: (ProofAddress.ROW_S, ProofAddress.Q_N),
    ProofAddress.PLAN_M: (ProofAddress.ROW_S, ProofAddress.Q_M),
    ProofAddress.REGRET_N: (ProofAddress.U0, ProofAddress.PLAN_N),
    ProofAddress.REGRET_M: (ProofAddress.U0, ProofAddress.PLAN_M),
    ProofAddress.RISK_N: (ProofAddress.PLAN_N,),
    ProofAddress.RISK_M: (ProofAddress.PLAN_M,),
    ProofAddress.COVERAGE_N: (ProofAddress.ROW_S, ProofAddress.Q_N),
    ProofAddress.COVERAGE_M: (ProofAddress.ROW_S, ProofAddress.Q_M),
    ProofAddress.SELECTION: (
        ProofAddress.PLAN_N,
        ProofAddress.REGRET_N,
        ProofAddress.RISK_N,
        ProofAddress.COVERAGE_N,
        ProofAddress.PLAN_M,
        ProofAddress.REGRET_M,
        ProofAddress.RISK_M,
        ProofAddress.COVERAGE_M,
    ),
}

EXPECTED_UNAFFECTED_ADDRESSES = (
    ProofAddress.ROW_S,
    ProofAddress.ROW_N1,
    ProofAddress.ROW_N2,
    ProofAddress.ROW_N3,
    ProofAddress.Q_N,
    ProofAddress.PLAN_N,
    ProofAddress.RISK_N,
    ProofAddress.COVERAGE_N,
)
EXPECTED_AFFECTED_ADDRESSES = tuple(
    address
    for address in ADDRESS_ORDER
    if address not in set(EXPECTED_UNAFFECTED_ADDRESSES)
)


def _ordered_addresses(values: Iterable[ProofAddress]) -> tuple[ProofAddress, ...]:
    return tuple(sorted(set(values), key=ADDRESS_INDEX.__getitem__))


@dataclass(frozen=True, slots=True)
class ActionIndexedGroundRowV1:
    name: GroundRowName
    state_key: str
    action_label: str
    concretizer_weight: Fraction
    status: GroundRowStatus
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction

    def __post_init__(self) -> None:
        if type(self.name) is not GroundRowName or type(self.status) is not GroundRowStatus:
            raise ActionIndexedProofInvariantViolation("ground row enum type changed")
        if type(self.state_key) is not str or self.state_key not in ("x0", "x1"):
            raise ActionIndexedProofInvariantViolation("ground row state is outside x0/x1")
        if type(self.action_label) is not str or self.action_label not in ("A0", "A1"):
            raise ActionIndexedProofInvariantViolation("ground row action is outside A0/A1")
        for field in (
            "concretizer_weight",
            "reward_lower",
            "reward_upper",
            "failure_lower",
            "failure_upper",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if (
            not 0 < self.concretizer_weight <= 1
            or not 0 <= self.reward_lower <= self.reward_upper <= 3
            or not 0 <= self.failure_lower <= self.failure_upper <= 1
        ):
            raise ActionIndexedProofInvariantViolation("ground row interval is invalid")
        expected_shape = {
            GroundRowName.S: ("x0", "A0", Fraction(1)),
            GroundRowName.N1: ("x1", "A0", Fraction(1, 3)),
            GroundRowName.N2: ("x1", "A0", Fraction(1, 3)),
            GroundRowName.N3: ("x1", "A0", Fraction(1, 3)),
            GroundRowName.M: ("x1", "A1", Fraction(1)),
        }[self.name]
        if (self.state_key, self.action_label, self.concretizer_weight) != expected_shape:
            raise ActionIndexedProofInvariantViolation("registered ground row shape changed")
        if self.name is GroundRowName.M:
            allowed = (
                (
                    GroundRowStatus.MISSING_VACUOUS,
                    Fraction(0),
                    Fraction(3),
                    Fraction(0),
                    Fraction(1),
                ),
                (
                    GroundRowStatus.OBSERVED,
                    Fraction(1),
                    Fraction(1),
                    Fraction(0),
                    Fraction(0),
                ),
            )
            actual = (
                self.status,
                self.reward_lower,
                self.reward_upper,
                self.failure_lower,
                self.failure_upper,
            )
            if actual not in allowed:
                raise ActionIndexedProofInvariantViolation("M row semantics changed")
        elif (
            self.status is not GroundRowStatus.OBSERVED
            or self.reward_lower != 0
            or self.reward_upper != 0
            or self.failure_lower != 0
            or self.failure_upper != 0
        ):
            raise ActionIndexedProofInvariantViolation("S/N row semantics changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "name": self.name.value,
            "state_key": self.state_key,
            "action_label": self.action_label,
            "concretizer_weight": _fdoc(self.concretizer_weight),
            "status": self.status.value,
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_lower": _fdoc(self.failure_lower),
            "failure_upper": _fdoc(self.failure_upper),
        }

    @property
    def row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedH2ModelV1:
    epoch: ModelEpoch
    rows: tuple[ActionIndexedGroundRowV1, ...]
    state_keys: tuple[str, str] = ("x0", "x1")
    action_semantics: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("N", ("N1", "N2", "N3")),
        ("M", ("M",)),
    )

    def __post_init__(self) -> None:
        if type(self.epoch) is not ModelEpoch:
            raise ActionIndexedProofInvariantViolation("model epoch type changed")
        _require_exact_tuple(self.rows, ActionIndexedGroundRowV1, "model rows")
        if tuple(item.name for item in self.rows) != tuple(GroundRowName):
            raise ActionIndexedProofInvariantViolation(
                "model must contain S,N1,N2,N3,M in canonical order"
            )
        if self.state_keys != ("x0", "x1") or self.action_semantics != (
            ("N", ("N1", "N2", "N3")),
            ("M", ("M",)),
        ):
            raise ActionIndexedProofInvariantViolation("registered model structure changed")
        observed = sum(item.status is GroundRowStatus.OBSERVED for item in self.rows)
        missing = len(self.rows) - observed
        m = self.rows[-1]
        if self.epoch is ModelEpoch.FIRST_4_OBSERVED_1_MISSING:
            if (
                (observed, missing) != (4, 1)
                or m.status is not GroundRowStatus.MISSING_VACUOUS
            ):
                raise ActionIndexedProofInvariantViolation("first model is not 4/1")
        elif (
            (observed, missing) != (5, 0)
            or m.status is not GroundRowStatus.OBSERVED
        ):
            raise ActionIndexedProofInvariantViolation("final model is not 5/0")

    @property
    def observed_row_count(self) -> int:
        return sum(item.status is GroundRowStatus.OBSERVED for item in self.rows)

    @property
    def missing_row_count(self) -> int:
        return len(self.rows) - self.observed_row_count

    def row(self, name: GroundRowName) -> ActionIndexedGroundRowV1:
        if type(name) is not GroundRowName:
            raise ActionIndexedProofInvariantViolation("row lookup requires exact enum")
        return self.rows[tuple(GroundRowName).index(name)]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_h2_model.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "rows": [item.to_document() for item in self.rows],
            "state_keys": list(self.state_keys),
            "action_semantics": [
                {"action": action, "row_names": list(names)}
                for action, names in self.action_semantics
            ],
            "observed_row_count": self.observed_row_count,
            "missing_row_count": self.missing_row_count,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedH2QueryV1:
    horizon: int = 2
    initial_state_key: str = "x0"
    return_upper: Fraction = Fraction(4)
    normalized_regret_tolerance: Fraction = Fraction(0)
    risk_tolerance: Fraction = Fraction(0)
    reward_basis: tuple[tuple[str, Fraction], ...] = (
        ("match", Fraction(1)),
        ("terminal_clear", Fraction(1)),
    )
    policy_class: str = "DETERMINISTIC_FINITE_HORIZON_MARKOV"

    def __post_init__(self) -> None:
        _integer(self.horizon, "query horizon", 1)
        for field in (
            "return_upper",
            "normalized_regret_tolerance",
            "risk_tolerance",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if type(self.reward_basis) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) not in (int, Fraction)
            for item in self.reward_basis
        ):
            raise ActionIndexedProofInvariantViolation("query reward basis is not exact")
        normalized_basis = tuple((name, Fraction(value)) for name, value in self.reward_basis)
        object.__setattr__(self, "reward_basis", normalized_basis)
        if (
            self.horizon != 2
            or self.initial_state_key != "x0"
            or self.return_upper != 4
            or self.normalized_regret_tolerance != 0
            or self.risk_tolerance != 0
            or self.reward_basis
            != (("match", Fraction(1)), ("terminal_clear", Fraction(1)))
            or self.policy_class != "DETERMINISTIC_FINITE_HORIZON_MARKOV"
        ):
            raise ActionIndexedProofInvariantViolation("registered H2 query changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_h2_query.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "horizon": self.horizon,
            "initial_state_key": self.initial_state_key,
            "return_upper": _fdoc(self.return_upper),
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "reward_basis": [
                {"name": name, "weight": _fdoc(weight)}
                for name, weight in self.reward_basis
            ],
            "policy_class": self.policy_class,
        }

    @property
    def query_id(self) -> str:
        return _content_id("query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


class ResultFieldKind(str, Enum):
    FRACTION = "FRACTION"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"


@dataclass(frozen=True, slots=True)
class ActionIndexedResultFieldV1:
    name: str
    kind: ResultFieldKind
    fraction_value: Fraction | None = None
    boolean_value: bool | None = None
    text_value: str | None = None

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name or type(self.kind) is not ResultFieldKind:
            raise ActionIndexedProofInvariantViolation("result field name/kind invalid")
        supplied = sum(
            value is not None
            for value in (self.fraction_value, self.boolean_value, self.text_value)
        )
        if supplied != 1:
            raise ActionIndexedProofInvariantViolation(
                "result field must contain exactly one typed value"
            )
        if self.kind is ResultFieldKind.FRACTION:
            object.__setattr__(
                self,
                "fraction_value",
                _fraction(self.fraction_value, f"result field {self.name}"),
            )
            if self.boolean_value is not None or self.text_value is not None:
                raise ActionIndexedProofInvariantViolation("fraction field type mismatch")
        elif self.kind is ResultFieldKind.BOOLEAN:
            if type(self.boolean_value) is not bool or (
                self.fraction_value is not None or self.text_value is not None
            ):
                raise ActionIndexedProofInvariantViolation("boolean field type mismatch")
        elif type(self.text_value) is not str or not self.text_value or (
            self.fraction_value is not None or self.boolean_value is not None
        ):
            raise ActionIndexedProofInvariantViolation("text field type mismatch")

    def to_document(self) -> dict[str, Any]:
        value: Any
        if self.kind is ResultFieldKind.FRACTION:
            value = _fdoc(self.fraction_value)  # type: ignore[arg-type]
        elif self.kind is ResultFieldKind.BOOLEAN:
            value = self.boolean_value
        else:
            value = self.text_value
        return {"name": self.name, "kind": self.kind.value, "value": value}


def _ff(name: str, value: Fraction) -> ActionIndexedResultFieldV1:
    return ActionIndexedResultFieldV1(
        name, ResultFieldKind.FRACTION, fraction_value=Fraction(value)
    )


def _bf(name: str, value: bool) -> ActionIndexedResultFieldV1:
    return ActionIndexedResultFieldV1(
        name, ResultFieldKind.BOOLEAN, boolean_value=value
    )


def _tf(name: str, value: str) -> ActionIndexedResultFieldV1:
    return ActionIndexedResultFieldV1(
        name, ResultFieldKind.TEXT, text_value=value
    )


_INTERVAL_FIELD_NAMES = (
    "all_rows_observed",
    "failure_lower",
    "failure_upper",
    "reward_lower",
    "reward_upper",
)


@dataclass(frozen=True, slots=True)
class ActionIndexedProofNodeV1:
    address: ProofAddress
    kind: ProofNodeKind
    input_slice_id: str
    ordered_parent_node_ids: tuple[str, ...]
    identity_terms: tuple[tuple[str, str], ...]
    result_fields: tuple[ActionIndexedResultFieldV1, ...]

    def __post_init__(self) -> None:
        if type(self.address) is not ProofAddress or type(self.kind) is not ProofNodeKind:
            raise ActionIndexedProofInvariantViolation("proof node enum type changed")
        if KIND_BY_ADDRESS[self.address] is not self.kind:
            raise ActionIndexedProofInvariantViolation("proof node address/kind mismatch")
        _cid(self.input_slice_id, "proof node input slice")
        if type(self.ordered_parent_node_ids) is not tuple:
            raise ActionIndexedProofInvariantViolation("proof parents must be ordered")
        for value in self.ordered_parent_node_ids:
            _cid(value, "proof parent node")
        if len(self.ordered_parent_node_ids) != len(
            EXPECTED_PARENT_ADDRESSES[self.address]
        ):
            raise ActionIndexedProofInvariantViolation("proof parent arity changed")
        if (
            type(self.identity_terms) is not tuple
            or self.identity_terms != tuple(sorted(self.identity_terms))
            or len({name for name, _ in self.identity_terms})
            != len(self.identity_terms)
            or any(
                type(name) is not str
                or not name
                or type(value) is not str
                or not value
                for name, value in self.identity_terms
            )
        ):
            raise ActionIndexedProofInvariantViolation(
                "proof identity terms are not canonical"
            )
        forbidden = {"model_id", "epoch", "epoch_id", "query_id", "request_id", "role"}
        if forbidden & {name for name, _ in self.identity_terms}:
            raise ActionIndexedProofInvariantViolation(
                "lower proof node leaked whole model/epoch/query identity"
            )
        _require_exact_tuple(
            self.result_fields, ActionIndexedResultFieldV1, "proof result fields"
        )
        names = tuple(item.name for item in self.result_fields)
        if names != tuple(sorted(set(names))):
            raise ActionIndexedProofInvariantViolation(
                "proof result fields must be unique and sorted"
            )
        expected_names = {
            ProofNodeKind.GROUND_ROW: _INTERVAL_FIELD_NAMES,
            ProofNodeKind.SEMANTIC_ACTION_Q: _INTERVAL_FIELD_NAMES,
            ProofNodeKind.FIXED_PLAN: _INTERVAL_FIELD_NAMES,
            ProofNodeKind.UNRESTRICTED_VALUE: ("reward_upper",),
            ProofNodeKind.REGRET_GATE: ("normalized_regret", "passes"),
            ProofNodeKind.RISK_GATE: ("failure_upper", "passes"),
            ProofNodeKind.COVERAGE_GATE: ("passes",),
            ProofNodeKind.SELECTION: (
                "schedule_code",
                "selected_action",
                "selection_mode",
            ),
        }[self.kind]
        if names != expected_names:
            raise ActionIndexedProofInvariantViolation(
                "proof result field allowlist changed"
            )
        fields = {item.name: item for item in self.result_fields}
        if self.kind in (
            ProofNodeKind.GROUND_ROW,
            ProofNodeKind.SEMANTIC_ACTION_Q,
            ProofNodeKind.FIXED_PLAN,
        ):
            lower = fields["reward_lower"].fraction_value
            upper = fields["reward_upper"].fraction_value
            f_lower = fields["failure_lower"].fraction_value
            f_upper = fields["failure_upper"].fraction_value
            if (
                lower is None
                or upper is None
                or f_lower is None
                or f_upper is None
                or not 0 <= lower <= upper <= 4
                or not 0 <= f_lower <= f_upper <= 1
            ):
                raise ActionIndexedProofInvariantViolation("node interval invalid")

    def _key_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_proof_node_key.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "address": self.address.value,
            "kind": self.kind.value,
            "input_slice_id": self.input_slice_id,
            "ordered_parent_node_ids": list(self.ordered_parent_node_ids),
            "identity_terms": [
                {"name": name, "value": value}
                for name, value in self.identity_terms
            ],
        }

    @property
    def node_key_id(self) -> str:
        return _content_id("node_key", self._key_payload())

    def _result_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_proof_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "address": self.address.value,
            "result_fields": [item.to_document() for item in self.result_fields],
        }

    @property
    def result_digest(self) -> str:
        return _content_id("result", self._result_payload())

    def _payload(self) -> dict[str, Any]:
        return {
            **self._key_payload(),
            "schema": "acfqp.action_indexed_proof_node.v1",
            "node_key_id": self.node_key_id,
            "result_digest": self.result_digest,
            "result_fields": [item.to_document() for item in self.result_fields],
        }

    @property
    def node_id(self) -> str:
        return _content_id("node", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "node_id": self.node_id}

    def fraction(self, name: str) -> Fraction:
        for item in self.result_fields:
            if item.name == name and item.kind is ResultFieldKind.FRACTION:
                assert item.fraction_value is not None
                return item.fraction_value
        raise ActionIndexedProofInvariantViolation(
            f"{self.address.value} has no fraction field {name}"
        )

    def boolean(self, name: str) -> bool:
        for item in self.result_fields:
            if item.name == name and item.kind is ResultFieldKind.BOOLEAN:
                assert item.boolean_value is not None
                return item.boolean_value
        raise ActionIndexedProofInvariantViolation(
            f"{self.address.value} has no boolean field {name}"
        )

    def text(self, name: str) -> str:
        for item in self.result_fields:
            if item.name == name and item.kind is ResultFieldKind.TEXT:
                assert item.text_value is not None
                return item.text_value
        raise ActionIndexedProofInvariantViolation(
            f"{self.address.value} has no text field {name}"
        )


def _parse_fraction_document(value: Any, name: str) -> Fraction:
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        raise ActionIndexedProofInvariantViolation(
            f"{name} is not a reduced rational document"
        )
    result = Fraction(value["numerator"], value["denominator"])
    if _fdoc(result) != value:
        raise ActionIndexedProofInvariantViolation(
            f"{name} rational document is not reduced"
        )
    return result


def parse_action_indexed_proof_node_document_v1(
    document: Mapping[str, Any],
) -> ActionIndexedProofNodeV1:
    """Reconstruct one canonical lower node from durable JSON bytes."""

    expected_keys = {
        "schema",
        "schema_version",
        "profile_key",
        "address",
        "kind",
        "input_slice_id",
        "ordered_parent_node_ids",
        "identity_terms",
        "node_key_id",
        "result_digest",
        "result_fields",
        "node_id",
    }
    if type(document) is not dict or set(document) != expected_keys:
        raise ActionIndexedProofInvariantViolation(
            "durable proof-node document shape changed"
        )
    if (
        document["schema"] != "acfqp.action_indexed_proof_node.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["profile_key"] != PROFILE_KEY
        or type(document["ordered_parent_node_ids"]) is not list
        or type(document["identity_terms"]) is not list
        or type(document["result_fields"]) is not list
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable proof-node schema changed"
        )
    identity_terms: list[tuple[str, str]] = []
    for item in document["identity_terms"]:
        if type(item) is not dict or set(item) != {"name", "value"}:
            raise ActionIndexedProofInvariantViolation(
                "durable proof-node identity term changed"
            )
        identity_terms.append((item["name"], item["value"]))
    result_fields: list[ActionIndexedResultFieldV1] = []
    for item in document["result_fields"]:
        if type(item) is not dict or set(item) != {"name", "kind", "value"}:
            raise ActionIndexedProofInvariantViolation(
                "durable proof-node result field changed"
            )
        try:
            kind = ResultFieldKind(item["kind"])
        except (TypeError, ValueError) as error:
            raise ActionIndexedProofInvariantViolation(
                "durable proof-node result kind changed"
            ) from error
        if kind is ResultFieldKind.FRACTION:
            result_fields.append(
                ActionIndexedResultFieldV1(
                    item["name"],
                    kind,
                    fraction_value=_parse_fraction_document(
                        item["value"],
                        f"durable {item['name']}",
                    ),
                )
            )
        elif kind is ResultFieldKind.BOOLEAN:
            result_fields.append(
                ActionIndexedResultFieldV1(
                    item["name"],
                    kind,
                    boolean_value=item["value"],
                )
            )
        else:
            result_fields.append(
                ActionIndexedResultFieldV1(
                    item["name"],
                    kind,
                    text_value=item["value"],
                )
            )
    try:
        node = ActionIndexedProofNodeV1(
            ProofAddress(document["address"]),
            ProofNodeKind(document["kind"]),
            document["input_slice_id"],
            tuple(document["ordered_parent_node_ids"]),
            tuple(identity_terms),
            tuple(result_fields),
        )
    except (TypeError, ValueError) as error:
        raise ActionIndexedProofInvariantViolation(
            "durable proof-node document cannot be reconstructed"
        ) from error
    if node.to_document() != document:
        raise ActionIndexedProofInvariantViolation(
            "durable proof-node document is not canonical"
        )
    return node


class ProofResolutionOutcome(str, Enum):
    COMPUTED = "COMPUTED"
    REUSED = "REUSED"


@dataclass(frozen=True, slots=True)
class ActionIndexedProofResolutionV1:
    sequence_number: int
    epoch: ModelEpoch
    model_id: str
    query_id: str
    address: ProofAddress
    node_key_id: str
    node_id: str
    outcome: ProofResolutionOutcome

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "resolution sequence", 1)
        if (
            type(self.epoch) is not ModelEpoch
            or type(self.address) is not ProofAddress
            or type(self.outcome) is not ProofResolutionOutcome
        ):
            raise ActionIndexedProofInvariantViolation("resolution enum type changed")
        for value in (self.model_id, self.query_id, self.node_key_id, self.node_id):
            _cid(value, "resolution identity")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_proof_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "address": self.address.value,
            "node_key_id": self.node_key_id,
            "node_id": self.node_id,
            "outcome": self.outcome.value,
        }

    @property
    def resolution_id(self) -> str:
        return _content_id("resolution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedProofWorkV1:
    lower_computed: int
    lower_reused: int
    fresh_root_computed: int

    def __post_init__(self) -> None:
        for field in ("lower_computed", "lower_reused", "fresh_root_computed"):
            _integer(getattr(self, field), f"work {field}")
        if (
            self.lower_computed + self.lower_reused != 18
            or self.fresh_root_computed != 3
        ):
            raise ActionIndexedProofInvariantViolation("registered work does not reconcile")

    @property
    def total_computed(self) -> int:
        return self.lower_computed + self.fresh_root_computed

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_proof_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lower_computed": self.lower_computed,
            "lower_reused": self.lower_reused,
            "fresh_root_computed": self.fresh_root_computed,
            "total_computed": self.total_computed,
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


class ActionIndexedProofRuntimeV1:
    """Owner of reusable lower values; roots are intentionally never cached."""

    __slots__ = (
        "_cache",
        "_model_ids",
        "_execution_ids",
        "_pending_invalidation",
    )

    def __init__(self) -> None:
        self._cache: dict[str, ActionIndexedProofNodeV1] = {}
        self._model_ids: list[str] = []
        self._execution_ids: list[str] = []
        self._pending_invalidation: ActionIndexedPreExecutionInvalidationV1 | None = None

    def _validate_next(self, model: ActionIndexedH2ModelV1) -> None:
        if type(model) is not ActionIndexedH2ModelV1:
            raise ActionIndexedProofInvariantViolation("runtime model type changed")
        if not self._model_ids:
            if model.epoch is not ModelEpoch.FIRST_4_OBSERVED_1_MISSING:
                raise ActionIndexedProofInvariantViolation(
                    "runtime must start from the registered first epoch"
                )
            return
        if (
            len(self._model_ids) != 1
            or model.epoch is not ModelEpoch.FINAL_5_OBSERVED_0_MISSING
            or self._pending_invalidation is None
            or self._pending_invalidation.final_model_id != model.model_id
            or self._pending_invalidation.first_execution_id
            != self._execution_ids[0]
        ):
            raise ActionIndexedProofInvariantViolation(
                "final epoch requires the exact pre-execution invalidation authority"
            )

    def _authorize_final_invalidation(
        self,
        plan: ActionIndexedPreExecutionInvalidationV1,
    ) -> None:
        if type(plan) is not ActionIndexedPreExecutionInvalidationV1:
            raise ActionIndexedProofInvariantViolation(
                "runtime rejects copied pre-execution invalidation"
            )
        plan.__post_init__()
        if (
            self._pending_invalidation is not None
            or len(self._model_ids) != 1
            or len(self._execution_ids) != 1
            or plan.first_model_id != self._model_ids[0]
            or plan.first_execution_id != self._execution_ids[0]
            or self.cache_size != 18
        ):
            raise ActionIndexedProofInvariantViolation(
                "pre-execution invalidation does not own the live first epoch"
            )
        nodes_by_address = {
            node.address: node for node in self._cache.values()
        }
        nodes_by_id = {node.node_id: node for node in self._cache.values()}
        if (
            set(nodes_by_address) != set(ADDRESS_ORDER)
            or len(nodes_by_address) != 18
            or len(nodes_by_id) != 18
        ):
            raise ActionIndexedProofInvariantViolation(
                "live first-epoch cache is incomplete or aliased"
            )
        expected_edges = []
        for child in nodes_by_address.values():
            for parent_id in child.ordered_parent_node_ids:
                parent = nodes_by_id.get(parent_id)
                if parent is None:
                    raise ActionIndexedProofInvariantViolation(
                        "live first-epoch cache has a missing parent"
                    )
                if (
                    parent.address in plan.affected_addresses
                    and child.address in plan.affected_addresses
                ):
                    expected_edges.append(
                        ActionIndexedInvalidationEdgeV1(
                            parent.address,
                            child.address,
                            parent.node_id,
                            child.node_id,
                        )
                    )
        canonical_edges = tuple(
            sorted(expected_edges, key=lambda item: item.edge_id)
        )
        if tuple(
            item.to_document() for item in plan.closure_edges
        ) != tuple(item.to_document() for item in canonical_edges):
            raise ActionIndexedProofInvariantViolation(
                "pre-execution invalidation omits or forges live closure edges"
            )
        self._pending_invalidation = plan

    def _resolve(
        self, candidate: ActionIndexedProofNodeV1
    ) -> tuple[ActionIndexedProofNodeV1, ProofResolutionOutcome]:
        if type(candidate) is not ActionIndexedProofNodeV1:
            raise ActionIndexedProofInvariantViolation("runtime rejects duck nodes")
        cached = self._cache.get(candidate.node_key_id)
        if cached is not None:
            cached.__post_init__()
            if (
                cached.address is not candidate.address
                or cached.kind is not candidate.kind
                or cached.to_document() != candidate.to_document()
            ):
                raise ActionIndexedProofInvariantViolation(
                    "cache hit differs from exact recomputation"
                )
            return cached, ProofResolutionOutcome.REUSED
        self._cache[candidate.node_key_id] = candidate
        return candidate, ProofResolutionOutcome.COMPUTED

    def _commit_execution(
        self, model_id: str, execution_id: str
    ) -> None:
        _cid(model_id, "runtime committed model")
        _cid(execution_id, "runtime committed execution")
        self._model_ids.append(model_id)
        self._execution_ids.append(execution_id)
        if len(self._model_ids) == 2:
            self._pending_invalidation = None

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    @property
    def snapshot_id(self) -> str:
        payload = {
            "schema": "acfqp.action_indexed_proof_runtime_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "cached_node_ids": sorted(item.node_id for item in self._cache.values()),
            "model_ids": list(self._model_ids),
            "execution_ids": list(self._execution_ids),
            "pending_preexecution_invalidation_id": (
                self._pending_invalidation.plan_id
                if self._pending_invalidation is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "NO_AUTHORIZED_FINAL_EPOCH",
                }
            ),
        }
        return _content_id("runtime", payload)


@dataclass(frozen=True, slots=True)
class ActionIndexedCandidateAuditV1:
    epoch: ModelEpoch
    model_id: str
    query_id: str
    action: CandidateAction
    schedule_code: str
    unrestricted_reward_upper: Fraction
    policy_reward_lower: Fraction
    policy_reward_upper: Fraction
    policy_failure_upper: Fraction
    normalized_regret: Fraction
    regret_passed: bool
    risk_passed: bool
    coverage_passed: bool
    certified: bool
    ordered_lower_node_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.epoch) is not ModelEpoch
            or type(self.action) is not CandidateAction
        ):
            raise ActionIndexedProofInvariantViolation("candidate audit enum changed")
        for value in (self.model_id, self.query_id, *self.ordered_lower_node_ids):
            _cid(value, "candidate audit identity")
        expected_code = "A0A0" if self.action is CandidateAction.N else "A0A1"
        if self.schedule_code != expected_code:
            raise ActionIndexedProofInvariantViolation("candidate schedule code changed")
        for field in (
            "unrestricted_reward_upper",
            "policy_reward_lower",
            "policy_reward_upper",
            "policy_failure_upper",
            "normalized_regret",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if (
            not 0 <= self.policy_reward_lower <= self.policy_reward_upper <= 4
            or not 0 <= self.policy_failure_upper <= 1
            or not 0 <= self.normalized_regret <= 1
            or any(
                type(value) is not bool
                for value in (
                    self.regret_passed,
                    self.risk_passed,
                    self.coverage_passed,
                    self.certified,
                )
            )
            or self.certified
            != (self.regret_passed and self.risk_passed and self.coverage_passed)
            or len(self.ordered_lower_node_ids) != 18
            or len(set(self.ordered_lower_node_ids)) != 18
        ):
            raise ActionIndexedProofInvariantViolation("candidate audit values invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_candidate_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "action": self.action.value,
            "schedule_code": self.schedule_code,
            "unrestricted_reward_upper": _fdoc(self.unrestricted_reward_upper),
            "policy_reward_lower": _fdoc(self.policy_reward_lower),
            "policy_reward_upper": _fdoc(self.policy_reward_upper),
            "policy_failure_upper": _fdoc(self.policy_failure_upper),
            "normalized_regret": _fdoc(self.normalized_regret),
            "regret_passed": self.regret_passed,
            "risk_passed": self.risk_passed,
            "coverage_passed": self.coverage_passed,
            "certified": self.certified,
            "ordered_lower_node_ids": list(self.ordered_lower_node_ids),
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


class ProofRootRole(str, Enum):
    CANDIDATE_AUDIT = "CANDIDATE_AUDIT"
    INDEPENDENT_SELECTED_ROOT = "INDEPENDENT_SELECTED_ROOT"


@dataclass(frozen=True, slots=True)
class ActionIndexedProofRootV1:
    epoch: ModelEpoch
    model_id: str
    query_id: str
    role: ProofRootRole
    action: CandidateAction
    candidate_audit_id: str
    ordered_lower_node_ids: tuple[str, ...]
    proposal_id: str | None
    certified: bool
    cacheable: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.epoch) is not ModelEpoch
            or type(self.role) is not ProofRootRole
            or type(self.action) is not CandidateAction
        ):
            raise ActionIndexedProofInvariantViolation("proof root enum changed")
        for value in (
            self.model_id,
            self.query_id,
            self.candidate_audit_id,
            *self.ordered_lower_node_ids,
        ):
            _cid(value, "proof root identity")
        if self.proposal_id is not None:
            _cid(self.proposal_id, "proof root proposal")
        selected = self.role is ProofRootRole.INDEPENDENT_SELECTED_ROOT
        if (
            selected != (self.proposal_id is not None)
            or len(self.ordered_lower_node_ids) != 18
            or len(set(self.ordered_lower_node_ids)) != 18
            or type(self.certified) is not bool
            or self.cacheable is not False
        ):
            raise ActionIndexedProofInvariantViolation(
                "proof root binding/cache policy changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_proof_root.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "formula_id": FORMULA_IDS["ROOT"],
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "role": self.role.value,
            "action": self.action.value,
            "candidate_audit_id": self.candidate_audit_id,
            "ordered_lower_node_ids": list(self.ordered_lower_node_ids),
            "proposal_id": (
                self.proposal_id
                if self.proposal_id is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "CANDIDATE_ROOT_PRECEDES_PROPOSAL",
                }
            ),
            "certified": self.certified,
            "cacheable": self.cacheable,
        }

    @property
    def root_id(self) -> str:
        return _content_id("root", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "root_id": self.root_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedPlanProposalV1:
    epoch: ModelEpoch
    model_id: str
    query_id: str
    selection_node_id: str
    candidate_audit_ids: tuple[str, str]
    candidate_root_ids: tuple[str, str]
    selected_action: CandidateAction
    selected_schedule_code: str
    selection_mode: str
    semantic_tie_break: str = "REACHABLE_NUMERIC_GATE_THEN_A0_PREFIX_V1"

    def __post_init__(self) -> None:
        if (
            type(self.epoch) is not ModelEpoch
            or type(self.selected_action) is not CandidateAction
        ):
            raise ActionIndexedProofInvariantViolation("proposal enum changed")
        for value in (
            self.model_id,
            self.query_id,
            self.selection_node_id,
            *self.candidate_audit_ids,
            *self.candidate_root_ids,
        ):
            _cid(value, "proposal identity")
        if (
            type(self.candidate_audit_ids) is not tuple
            or len(self.candidate_audit_ids) != 2
            or len(set(self.candidate_audit_ids)) != 2
            or type(self.candidate_root_ids) is not tuple
            or len(self.candidate_root_ids) != 2
            or len(set(self.candidate_root_ids)) != 2
            or self.selected_schedule_code
            != ("A0A0" if self.selected_action is CandidateAction.N else "A0A1")
            or self.selection_mode
            not in (
                "RISK_COVERAGE_FEASIBLE_REWARD_MAX",
                "CERTIFIED_REWARD_MAX",
            )
            or self.semantic_tie_break != "REACHABLE_NUMERIC_GATE_THEN_A0_PREFIX_V1"
        ):
            raise ActionIndexedProofInvariantViolation("proposal selection changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_plan_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "selection_node_id": self.selection_node_id,
            "candidate_audit_ids": list(self.candidate_audit_ids),
            "candidate_root_ids": list(self.candidate_root_ids),
            "selected_action": self.selected_action.value,
            "selected_schedule_code": self.selected_schedule_code,
            "selection_mode": self.selection_mode,
            "semantic_tie_break": self.semantic_tie_break,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedEpochSemanticReplayV1:
    """Pure model/query replay of every semantic artifact in one epoch.

    This is deliberately not a content-addressed artifact.  It is a trusted,
    deterministic reconstruction used to validate a submitted execution graph;
    no submitted lower-node result, audit, root, or proposal is an input.
    """

    nodes: tuple[ActionIndexedProofNodeV1, ...]
    candidate_audits: tuple[ActionIndexedCandidateAuditV1, ...]
    candidate_roots: tuple[ActionIndexedProofRootV1, ...]
    proposal: ActionIndexedPlanProposalV1
    selected_root: ActionIndexedProofRootV1

    def __post_init__(self) -> None:
        _require_exact_tuple(
            self.nodes, ActionIndexedProofNodeV1, "semantic replay nodes"
        )
        _require_exact_tuple(
            self.candidate_audits,
            ActionIndexedCandidateAuditV1,
            "semantic replay candidate audits",
        )
        _require_exact_tuple(
            self.candidate_roots,
            ActionIndexedProofRootV1,
            "semantic replay candidate roots",
        )
        if (
            tuple(item.address for item in self.nodes) != ADDRESS_ORDER
            or tuple(item.action for item in self.candidate_audits)
            != (CandidateAction.N, CandidateAction.M)
            or tuple(item.action for item in self.candidate_roots)
            != (CandidateAction.N, CandidateAction.M)
            or type(self.proposal) is not ActionIndexedPlanProposalV1
            or type(self.selected_root) is not ActionIndexedProofRootV1
        ):
            raise ActionIndexedProofInvariantViolation(
                "semantic replay graph shape changed"
            )


@dataclass(frozen=True, slots=True)
class ActionIndexedEpochExecutionV1:
    epoch: ModelEpoch
    model_id: str
    query_id: str
    pre_runtime_snapshot_id: str
    post_runtime_snapshot_id: str
    resolutions: tuple[ActionIndexedProofResolutionV1, ...]
    nodes: tuple[ActionIndexedProofNodeV1, ...]
    candidate_audits: tuple[ActionIndexedCandidateAuditV1, ...]
    candidate_roots: tuple[ActionIndexedProofRootV1, ...]
    proposal: ActionIndexedPlanProposalV1
    selected_root: ActionIndexedProofRootV1
    work: ActionIndexedProofWorkV1
    preexecution_invalidation_id: str | None
    semantic_model: ActionIndexedH2ModelV1 = field(repr=False, compare=False)
    semantic_query: ActionIndexedH2QueryV1 = field(repr=False, compare=False)
    ground_transition_calls: int = 0
    kernel_imported: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.epoch) is not ModelEpoch
            or type(self.semantic_model) is not ActionIndexedH2ModelV1
            or type(self.semantic_query) is not ActionIndexedH2QueryV1
        ):
            raise ActionIndexedProofInvariantViolation("execution epoch type changed")
        self.semantic_model.__post_init__()
        self.semantic_query.__post_init__()
        if (
            self.epoch is not self.semantic_model.epoch
            or self.model_id != self.semantic_model.model_id
            or self.query_id != self.semantic_query.query_id
        ):
            raise ActionIndexedProofInvariantViolation(
                "execution model/query replay binding changed"
            )
        for value in (
            self.model_id,
            self.query_id,
            self.pre_runtime_snapshot_id,
            self.post_runtime_snapshot_id,
        ):
            _cid(value, "execution identity")
        if self.preexecution_invalidation_id is not None:
            _cid(
                self.preexecution_invalidation_id,
                "execution preexecution_invalidation_id",
            )
        _require_exact_tuple(
            self.resolutions, ActionIndexedProofResolutionV1, "execution resolutions"
        )
        _require_exact_tuple(self.nodes, ActionIndexedProofNodeV1, "execution nodes")
        _require_exact_tuple(
            self.candidate_audits,
            ActionIndexedCandidateAuditV1,
            "execution candidate audits",
        )
        _require_exact_tuple(
            self.candidate_roots,
            ActionIndexedProofRootV1,
            "execution candidate roots",
        )
        if (
            type(self.proposal) is not ActionIndexedPlanProposalV1
            or type(self.selected_root) is not ActionIndexedProofRootV1
            or type(self.work) is not ActionIndexedProofWorkV1
        ):
            raise ActionIndexedProofInvariantViolation("execution nested type changed")
        ordered_node_ids = tuple(item.node_id for item in self.nodes)
        selected_index = (
            0 if self.proposal.selected_action is CandidateAction.N else 1
        )
        selected_audit = self.candidate_audits[selected_index]
        selection_node = self.nodes[ADDRESS_INDEX[ProofAddress.SELECTION]]
        if (
            tuple(item.sequence_number for item in self.resolutions)
            != tuple(range(1, 19))
            or tuple(item.address for item in self.resolutions) != ADDRESS_ORDER
            or tuple(item.address for item in self.nodes) != ADDRESS_ORDER
            or any(
                item.epoch is not self.epoch
                or item.model_id != self.model_id
                or item.query_id != self.query_id
                or item.node_id != node.node_id
                or item.node_key_id != node.node_key_id
                for item, node in zip(self.resolutions, self.nodes)
            )
            or tuple(item.action for item in self.candidate_audits)
            != (CandidateAction.N, CandidateAction.M)
            or tuple(item.action for item in self.candidate_roots)
            != (CandidateAction.N, CandidateAction.M)
            or any(item.role is not ProofRootRole.CANDIDATE_AUDIT for item in self.candidate_roots)
            or any(
                audit.ordered_lower_node_ids != ordered_node_ids
                for audit in self.candidate_audits
            )
            or any(
                root.candidate_audit_id != audit.audit_id
                or root.ordered_lower_node_ids != ordered_node_ids
                or root.certified is not audit.certified
                for root, audit in zip(
                    self.candidate_roots, self.candidate_audits
                )
            )
            or self.proposal.epoch is not self.epoch
            or self.proposal.model_id != self.model_id
            or self.proposal.query_id != self.query_id
            or self.proposal.selection_node_id != selection_node.node_id
            or self.proposal.candidate_audit_ids
            != tuple(item.audit_id for item in self.candidate_audits)
            or self.proposal.candidate_root_ids
            != tuple(item.root_id for item in self.candidate_roots)
            or self.proposal.selected_action.value
            != selection_node.text("selected_action")
            or self.proposal.selected_schedule_code
            != selection_node.text("schedule_code")
            or self.proposal.selection_mode
            != selection_node.text("selection_mode")
            or self.selected_root.role is not ProofRootRole.INDEPENDENT_SELECTED_ROOT
            or self.selected_root.action is not self.proposal.selected_action
            or self.selected_root.proposal_id != self.proposal.proposal_id
            or self.selected_root.candidate_audit_id != selected_audit.audit_id
            or self.selected_root.ordered_lower_node_ids != ordered_node_ids
            or self.selected_root.certified is not selected_audit.certified
            or (
                self.epoch is ModelEpoch.FIRST_4_OBSERVED_1_MISSING
                and self.preexecution_invalidation_id is not None
            )
            or (
                self.epoch is ModelEpoch.FINAL_5_OBSERVED_0_MISSING
                and self.preexecution_invalidation_id is None
            )
            or self.ground_transition_calls != 0
            or self.kernel_imported is not False
        ):
            raise ActionIndexedProofInvariantViolation("execution graph/binding changed")
        node_by_id = {item.node_id: item for item in self.nodes}
        for address, node in zip(ADDRESS_ORDER, self.nodes):
            parents = tuple(
                node_by_id[parent_id].address for parent_id in node.ordered_parent_node_ids
            )
            if parents != EXPECTED_PARENT_ADDRESSES[address]:
                raise ActionIndexedProofInvariantViolation(
                    "execution parent address topology changed"
                )
        computed = sum(
            item.outcome is ProofResolutionOutcome.COMPUTED
            for item in self.resolutions
        )
        reused = len(self.resolutions) - computed
        expected_work = (
            (18, 0)
            if self.epoch is ModelEpoch.FIRST_4_OBSERVED_1_MISSING
            else (10, 8)
        )
        if (
            (computed, reused) != expected_work
            or (self.work.lower_computed, self.work.lower_reused) != expected_work
        ):
            raise ActionIndexedProofInvariantViolation("epoch cache work changed")
        replay = replay_action_indexed_epoch_semantics_v1(
            self.semantic_model,
            self.semantic_query,
        )
        if (
            tuple(item.to_document() for item in self.nodes)
            != tuple(item.to_document() for item in replay.nodes)
            or tuple(item.to_document() for item in self.candidate_audits)
            != tuple(
                item.to_document() for item in replay.candidate_audits
            )
            or tuple(item.to_document() for item in self.candidate_roots)
            != tuple(
                item.to_document() for item in replay.candidate_roots
            )
            or self.proposal.to_document() != replay.proposal.to_document()
            or self.selected_root.to_document()
            != replay.selected_root.to_document()
        ):
            raise ActionIndexedProofInvariantViolation(
                "execution semantic replay differs from exact model/query"
            )
        n, m = self.candidate_audits
        if self.epoch is ModelEpoch.FIRST_4_OBSERVED_1_MISSING:
            expected = (
                (
                    n.unrestricted_reward_upper,
                    n.policy_reward_lower,
                    n.policy_failure_upper,
                    n.normalized_regret,
                    n.coverage_passed,
                    n.certified,
                ),
                (
                    m.unrestricted_reward_upper,
                    m.policy_reward_lower,
                    m.policy_failure_upper,
                    m.normalized_regret,
                    m.coverage_passed,
                    m.certified,
                ),
                self.proposal.selected_action,
                self.proposal.selection_mode,
            )
            if expected != (
                (Fraction(3), Fraction(0), Fraction(0), Fraction(3, 4), True, False),
                (Fraction(3), Fraction(0), Fraction(1), Fraction(3, 4), False, False),
                CandidateAction.N,
                "RISK_COVERAGE_FEASIBLE_REWARD_MAX",
            ):
                raise ActionIndexedProofInvariantViolation("first epoch golden changed")
        else:
            expected = (
                (
                    n.unrestricted_reward_upper,
                    n.policy_reward_lower,
                    n.policy_failure_upper,
                    n.normalized_regret,
                    n.coverage_passed,
                    n.certified,
                ),
                (
                    m.unrestricted_reward_upper,
                    m.policy_reward_lower,
                    m.policy_failure_upper,
                    m.normalized_regret,
                    m.coverage_passed,
                    m.certified,
                ),
                self.proposal.selected_action,
                self.proposal.selection_mode,
            )
            if expected != (
                (Fraction(1), Fraction(0), Fraction(0), Fraction(1, 4), True, False),
                (Fraction(1), Fraction(1), Fraction(0), Fraction(0), True, True),
                CandidateAction.M,
                "CERTIFIED_REWARD_MAX",
            ):
                raise ActionIndexedProofInvariantViolation("final epoch golden changed")

    def node(self, address: ProofAddress) -> ActionIndexedProofNodeV1:
        if type(address) is not ProofAddress:
            raise ActionIndexedProofInvariantViolation("node lookup requires exact enum")
        return self.nodes[ADDRESS_INDEX[address]]

    def audit(self, action: CandidateAction) -> ActionIndexedCandidateAuditV1:
        if type(action) is not CandidateAction:
            raise ActionIndexedProofInvariantViolation("audit lookup requires exact enum")
        return self.candidate_audits[0 if action is CandidateAction.N else 1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_epoch_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "pre_runtime_snapshot_id": self.pre_runtime_snapshot_id,
            "post_runtime_snapshot_id": self.post_runtime_snapshot_id,
            "resolutions": [item.to_document() for item in self.resolutions],
            "nodes": [item.to_document() for item in self.nodes],
            "candidate_audits": [
                item.to_document() for item in self.candidate_audits
            ],
            "candidate_roots": [
                item.to_document() for item in self.candidate_roots
            ],
            "proposal": self.proposal.to_document(),
            "selected_root": self.selected_root.to_document(),
            "work": self.work.to_document(),
            "preexecution_invalidation_id": (
                self.preexecution_invalidation_id
                if self.preexecution_invalidation_id is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "FIRST_EPOCH_PRECEDES_MODEL_DELTA",
                }
            ),
            "ground_transition_calls": self.ground_transition_calls,
            "kernel_imported": self.kernel_imported,
        }

    @property
    def execution_id(self) -> str:
        return _content_id("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedFirstRuntimeRestoreV1:
    """Receipt for loading a verified first-epoch lower graph into a runtime.

    The receipt does not prove that the nodes came from durable storage.  A
    storage profile must bind it to its own verified lease.  It proves only
    that this model-only module accepted the exact registered first
    model/query/execution semantics and loaded lower nodes but no roots.
    """

    model_id: str
    query_id: str
    execution_id: str
    ordered_lower_node_ids: tuple[str, ...]
    pre_runtime_snapshot_id: str
    post_runtime_snapshot_id: str
    lower_entries_loaded: int = 18
    roots_loaded: int = 0
    semantic_replay_required: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.model_id,
            self.query_id,
            self.execution_id,
            self.pre_runtime_snapshot_id,
            self.post_runtime_snapshot_id,
            *self.ordered_lower_node_ids,
        ):
            _cid(value, "first-runtime restore identity")
        if (
            type(self.ordered_lower_node_ids) is not tuple
            or len(self.ordered_lower_node_ids) != 18
            or len(set(self.ordered_lower_node_ids)) != 18
            or self.lower_entries_loaded != 18
            or self.roots_loaded != 0
            or self.semantic_replay_required is not True
            or self.pre_runtime_snapshot_id == self.post_runtime_snapshot_id
        ):
            raise ActionIndexedProofInvariantViolation(
                "first-runtime restore receipt changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_first_runtime_restore.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "execution_id": self.execution_id,
            "ordered_lower_node_ids": list(self.ordered_lower_node_ids),
            "pre_runtime_snapshot_id": self.pre_runtime_snapshot_id,
            "post_runtime_snapshot_id": self.post_runtime_snapshot_id,
            "lower_entries_loaded": self.lower_entries_loaded,
            "roots_loaded": self.roots_loaded,
            "semantic_replay_required": self.semantic_replay_required,
        }

    @property
    def restore_id(self) -> str:
        return _content_id("restore", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "restore_id": self.restore_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedFinalRuntimeRestoreV1:
    """Receipt for loading the active final lower graph from a 28-node union."""

    model_id: str
    query_id: str
    execution_id: str
    full_ordered_node_ids: tuple[str, ...]
    active_ordered_node_ids: tuple[str, ...]
    pre_runtime_snapshot_id: str
    post_runtime_snapshot_id: str
    full_entries_validated: int = 28
    active_entries_loaded: int = 18
    roots_loaded: int = 0
    semantic_replay_required: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.model_id,
            self.query_id,
            self.execution_id,
            self.pre_runtime_snapshot_id,
            self.post_runtime_snapshot_id,
            *self.full_ordered_node_ids,
            *self.active_ordered_node_ids,
        ):
            _cid(value, "final-runtime restore identity")
        if (
            type(self.full_ordered_node_ids) is not tuple
            or len(self.full_ordered_node_ids) != 28
            or len(set(self.full_ordered_node_ids)) != 28
            or self.full_ordered_node_ids
            != tuple(sorted(self.full_ordered_node_ids))
            or type(self.active_ordered_node_ids) is not tuple
            or len(self.active_ordered_node_ids) != 18
            or len(set(self.active_ordered_node_ids)) != 18
            or not set(self.active_ordered_node_ids).issubset(
                self.full_ordered_node_ids
            )
            or self.full_entries_validated != 28
            or self.active_entries_loaded != 18
            or self.roots_loaded != 0
            or self.semantic_replay_required is not True
            or self.pre_runtime_snapshot_id == self.post_runtime_snapshot_id
        ):
            raise ActionIndexedProofInvariantViolation(
                "final-runtime restore receipt changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_final_runtime_restore.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "execution_id": self.execution_id,
            "full_ordered_node_ids": list(self.full_ordered_node_ids),
            "active_ordered_node_ids": list(
                self.active_ordered_node_ids
            ),
            "pre_runtime_snapshot_id": self.pre_runtime_snapshot_id,
            "post_runtime_snapshot_id": self.post_runtime_snapshot_id,
            "full_entries_validated": self.full_entries_validated,
            "active_entries_loaded": self.active_entries_loaded,
            "roots_loaded": self.roots_loaded,
            "semantic_replay_required": self.semantic_replay_required,
        }

    @property
    def restore_id(self) -> str:
        return _content_id("final_restore", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "restore_id": self.restore_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedRestoredRootReplayV1:
    """Three fresh roots derived from 18 operationally loaded lower nodes."""

    epoch: ModelEpoch
    model_id: str
    query_id: str
    source_execution_id: str
    restore_binding_id: str
    runtime_snapshot_id: str
    ordered_lower_node_ids: tuple[str, ...]
    candidate_audits: tuple[ActionIndexedCandidateAuditV1, ...]
    candidate_roots: tuple[ActionIndexedProofRootV1, ...]
    proposal: ActionIndexedPlanProposalV1
    selected_root: ActionIndexedProofRootV1
    lower_computed: int = 0
    lower_reused: int = 18
    roots_loaded: int = 0
    fresh_root_computed: int = 3
    ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        if type(self.epoch) is not ModelEpoch:
            raise ActionIndexedProofInvariantViolation(
                "restored-root epoch changed"
            )
        for value in (
            self.model_id,
            self.query_id,
            self.source_execution_id,
            self.restore_binding_id,
            self.runtime_snapshot_id,
            *self.ordered_lower_node_ids,
        ):
            _cid(value, "restored-root identity")
        _require_exact_tuple(
            self.candidate_audits,
            ActionIndexedCandidateAuditV1,
            "restored-root audits",
        )
        _require_exact_tuple(
            self.candidate_roots,
            ActionIndexedProofRootV1,
            "restored-root candidate roots",
        )
        if (
            len(self.ordered_lower_node_ids) != 18
            or len(set(self.ordered_lower_node_ids)) != 18
            or tuple(item.action for item in self.candidate_audits)
            != (CandidateAction.N, CandidateAction.M)
            or tuple(item.action for item in self.candidate_roots)
            != (CandidateAction.N, CandidateAction.M)
            or type(self.proposal) is not ActionIndexedPlanProposalV1
            or type(self.selected_root) is not ActionIndexedProofRootV1
            or self.proposal.model_id != self.model_id
            or self.proposal.query_id != self.query_id
            or self.proposal.epoch is not self.epoch
            or self.proposal.candidate_audit_ids
            != tuple(item.audit_id for item in self.candidate_audits)
            or self.proposal.candidate_root_ids
            != tuple(item.root_id for item in self.candidate_roots)
            or self.selected_root.proposal_id != self.proposal.proposal_id
            or self.selected_root.action is not self.proposal.selected_action
            or self.selected_root.ordered_lower_node_ids
            != self.ordered_lower_node_ids
            or self.lower_computed != 0
            or self.lower_reused != 18
            or self.roots_loaded != 0
            or self.fresh_root_computed != 3
            or self.ground_transition_calls != 0
        ):
            raise ActionIndexedProofInvariantViolation(
                "restored-root replay changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_restored_root_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch": self.epoch.value,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "source_execution_id": self.source_execution_id,
            "restore_binding_id": self.restore_binding_id,
            "runtime_snapshot_id": self.runtime_snapshot_id,
            "ordered_lower_node_ids": list(self.ordered_lower_node_ids),
            "candidate_audits": [
                item.to_document() for item in self.candidate_audits
            ],
            "candidate_roots": [
                item.to_document() for item in self.candidate_roots
            ],
            "proposal": self.proposal.to_document(),
            "selected_root": self.selected_root.to_document(),
            "lower_computed": self.lower_computed,
            "lower_reused": self.lower_reused,
            "roots_loaded": self.roots_loaded,
            "fresh_root_computed": self.fresh_root_computed,
            "ground_transition_calls": self.ground_transition_calls,
        }

    @property
    def replay_id(self) -> str:
        return _content_id("restored_roots", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def _slice_id(address: ProofAddress, document: Mapping[str, Any]) -> str:
    return _content_id(
        "slice",
        {
            "schema": "acfqp.action_indexed_model_slice.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "address": address.value,
            "document": dict(document),
        },
    )


def _formula_key(address: ProofAddress) -> str:
    kind = KIND_BY_ADDRESS[address]
    if kind is ProofNodeKind.GROUND_ROW:
        return "ROW"
    if kind is ProofNodeKind.SEMANTIC_ACTION_Q:
        return "Q"
    if address is ProofAddress.U1:
        return "U1"
    if address is ProofAddress.U0:
        return "U0"
    if kind is ProofNodeKind.FIXED_PLAN:
        return "PLAN"
    if kind is ProofNodeKind.REGRET_GATE:
        return "REGRET"
    if kind is ProofNodeKind.RISK_GATE:
        return "RISK"
    if kind is ProofNodeKind.COVERAGE_GATE:
        return "COVERAGE"
    return "SELECTION"


def _identity_terms(
    address: ProofAddress, query: ActionIndexedH2QueryV1
) -> tuple[tuple[str, str], ...]:
    terms: dict[str, str] = {"formula_id": FORMULA_IDS[_formula_key(address)]}
    if address in (ProofAddress.U1, ProofAddress.U0):
        terms["return_upper"] = _ftext(query.return_upper)
    elif KIND_BY_ADDRESS[address] is ProofNodeKind.REGRET_GATE:
        terms["normalized_regret_tolerance"] = _ftext(
            query.normalized_regret_tolerance
        )
        terms["return_upper"] = _ftext(query.return_upper)
    elif KIND_BY_ADDRESS[address] is ProofNodeKind.RISK_GATE:
        terms["risk_tolerance"] = _ftext(query.risk_tolerance)
    elif address is ProofAddress.SELECTION:
        terms["candidate_order"] = "N,M"
        terms["schedule_mapping"] = "N:A0A0,M:A0A1"
        terms["tie_break"] = "REACHABLE_NUMERIC_GATE_THEN_A0_PREFIX_V1"
    return tuple(sorted(terms.items()))


def _interval_fields(
    reward_lower: Fraction,
    reward_upper: Fraction,
    failure_lower: Fraction,
    failure_upper: Fraction,
    all_rows_observed: bool,
) -> tuple[ActionIndexedResultFieldV1, ...]:
    return (
        _bf("all_rows_observed", all_rows_observed),
        _ff("failure_lower", failure_lower),
        _ff("failure_upper", failure_upper),
        _ff("reward_lower", reward_lower),
        _ff("reward_upper", reward_upper),
    )


def _candidate_action_for_address(address: ProofAddress) -> CandidateAction:
    if address.value.endswith("_N"):
        return CandidateAction.N
    if address.value.endswith("_M"):
        return CandidateAction.M
    raise ActionIndexedProofInvariantViolation(
        f"{address.value} is not action-indexed"
    )


def _node_candidate(
    address: ProofAddress,
    parent_nodes: tuple[ActionIndexedProofNodeV1, ...],
    input_document: Mapping[str, Any],
    query: ActionIndexedH2QueryV1,
    result_fields: tuple[ActionIndexedResultFieldV1, ...],
) -> ActionIndexedProofNodeV1:
    if tuple(item.address for item in parent_nodes) != EXPECTED_PARENT_ADDRESSES[address]:
        raise ActionIndexedProofInvariantViolation(
            f"{address.value} received wrong logical parents"
        )
    return ActionIndexedProofNodeV1(
        address,
        KIND_BY_ADDRESS[address],
        _slice_id(address, input_document),
        tuple(item.node_id for item in parent_nodes),
        _identity_terms(address, query),
        result_fields,
    )


def _selection(
    nodes: Mapping[ProofAddress, ActionIndexedProofNodeV1],
) -> tuple[CandidateAction, str, str]:
    rows = []
    for action in CandidateAction:
        suffix = action.value
        plan = nodes[ProofAddress[f"PLAN_{suffix}"]]
        regret = nodes[ProofAddress[f"REGRET_{suffix}"]]
        risk = nodes[ProofAddress[f"RISK_{suffix}"]]
        coverage = nodes[ProofAddress[f"COVERAGE_{suffix}"]]
        certified = (
            regret.boolean("passes")
            and risk.boolean("passes")
            and coverage.boolean("passes")
        )
        feasible = risk.boolean("passes") and coverage.boolean("passes")
        rows.append(
            (
                action,
                certified,
                feasible,
                plan.fraction("reward_lower"),
                plan.fraction("failure_upper"),
            )
        )
    if any(item[1] for item in rows):
        eligible = [item for item in rows if item[1]]
        mode = "CERTIFIED_REWARD_MAX"
    elif any(item[2] for item in rows):
        eligible = [item for item in rows if item[2]]
        mode = "RISK_COVERAGE_FEASIBLE_REWARD_MAX"
    else:
        eligible = rows
        mode = "MIN_FAILURE_FALLBACK"
    selected = min(
        eligible,
        key=lambda item: (
            -item[3],
            item[4],
            0 if item[0] is CandidateAction.N else 1,
        ),
    )[0]
    if mode == "MIN_FAILURE_FALLBACK":
        raise ActionIndexedProofInvariantViolation(
            "registered fixture unexpectedly requires unsafe fallback"
        )
    return selected, ("A0A0" if selected is CandidateAction.N else "A0A1"), mode


def _build_candidate_audit(
    epoch: ModelEpoch,
    model_id: str,
    query_id: str,
    action: CandidateAction,
    nodes: Mapping[ProofAddress, ActionIndexedProofNodeV1],
) -> ActionIndexedCandidateAuditV1:
    suffix = action.value
    u0 = nodes[ProofAddress.U0]
    plan = nodes[ProofAddress[f"PLAN_{suffix}"]]
    regret = nodes[ProofAddress[f"REGRET_{suffix}"]]
    risk = nodes[ProofAddress[f"RISK_{suffix}"]]
    coverage = nodes[ProofAddress[f"COVERAGE_{suffix}"]]
    ordered = tuple(nodes[address].node_id for address in ADDRESS_ORDER)
    return ActionIndexedCandidateAuditV1(
        epoch,
        model_id,
        query_id,
        action,
        "A0A0" if action is CandidateAction.N else "A0A1",
        u0.fraction("reward_upper"),
        plan.fraction("reward_lower"),
        plan.fraction("reward_upper"),
        plan.fraction("failure_upper"),
        regret.fraction("normalized_regret"),
        regret.boolean("passes"),
        risk.boolean("passes"),
        coverage.boolean("passes"),
        (
            regret.boolean("passes")
            and risk.boolean("passes")
            and coverage.boolean("passes")
        ),
        ordered,
    )


def replay_action_indexed_epoch_semantics_v1(
    model: ActionIndexedH2ModelV1,
    query: ActionIndexedH2QueryV1,
) -> ActionIndexedEpochSemanticReplayV1:
    """Rebuild the complete semantic proof graph from only ``model``/``query``.

    Runtime cache contents, submitted proof nodes, submitted audits and
    submitted roots are intentionally unavailable to this replay.  Exact
    document equality against its result therefore rejects a graph whose
    internally consistent content IDs merely re-sign contradictory semantics.
    """

    if (
        type(model) is not ActionIndexedH2ModelV1
        or type(query) is not ActionIndexedH2QueryV1
    ):
        raise ActionIndexedProofInvariantViolation(
            "semantic replay requires exact model/query types"
        )
    model.__post_init__()
    query.__post_init__()
    nodes: dict[ProofAddress, ActionIndexedProofNodeV1] = {}

    def build(
        address: ProofAddress,
        input_document: Mapping[str, Any],
        result_fields: tuple[ActionIndexedResultFieldV1, ...],
    ) -> ActionIndexedProofNodeV1:
        parents = tuple(nodes[item] for item in EXPECTED_PARENT_ADDRESSES[address])
        node = _node_candidate(
            address,
            parents,
            input_document,
            query,
            result_fields,
        )
        nodes[address] = node
        return node

    for row in model.rows:
        build(
            ROW_ADDRESS_BY_NAME[row.name],
            {"ground_row": row.to_document()},
            _interval_fields(
                row.reward_lower,
                row.reward_upper,
                row.failure_lower,
                row.failure_upper,
                row.status is GroundRowStatus.OBSERVED,
            ),
        )

    for action, row_names, address in (
        (
            CandidateAction.N,
            (GroundRowName.N1, GroundRowName.N2, GroundRowName.N3),
            ProofAddress.Q_N,
        ),
        (CandidateAction.M, (GroundRowName.M,), ProofAddress.Q_M),
    ):
        parents = tuple(nodes[ROW_ADDRESS_BY_NAME[name]] for name in row_names)
        rows = tuple(model.row(name) for name in row_names)
        build(
            address,
            {
                "action": action.value,
                "mixture": [
                    {
                        "row_name": row.name.value,
                        "weight": _fdoc(row.concretizer_weight),
                    }
                    for row in rows
                ],
            },
            _interval_fields(
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("reward_lower")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("reward_upper")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("failure_lower")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("failure_upper")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                all(parent.boolean("all_rows_observed") for parent in parents),
            ),
        )

    build(
        ProofAddress.U1,
        {"action_order": ["N", "M"], "remaining_horizon": 1},
        (
            _ff(
                "reward_upper",
                max(
                    nodes[ProofAddress.Q_N].fraction("reward_upper"),
                    nodes[ProofAddress.Q_M].fraction("reward_upper"),
                ),
            ),
        ),
    )
    build(
        ProofAddress.U0,
        {
            "stage_zero_row": GroundRowName.S.value,
            "remaining_horizon": 2,
        },
        (
            _ff(
                "reward_upper",
                min(
                    query.return_upper,
                    nodes[ProofAddress.ROW_S].fraction("reward_upper")
                    + nodes[ProofAddress.U1].fraction("reward_upper"),
                ),
            ),
        ),
    )

    for action, plan_address, q_address in (
        (CandidateAction.N, ProofAddress.PLAN_N, ProofAddress.Q_N),
        (CandidateAction.M, ProofAddress.PLAN_M, ProofAddress.Q_M),
    ):
        s = nodes[ProofAddress.ROW_S]
        q = nodes[q_address]
        build(
            plan_address,
            {
                "action": action.value,
                "schedule_code": (
                    "A0A0" if action is CandidateAction.N else "A0A1"
                ),
                "stage_zero_row": GroundRowName.S.value,
            },
            _interval_fields(
                s.fraction("reward_lower") + q.fraction("reward_lower"),
                min(
                    query.return_upper,
                    s.fraction("reward_upper") + q.fraction("reward_upper"),
                ),
                min(
                    Fraction(1),
                    s.fraction("failure_lower") + q.fraction("failure_lower"),
                ),
                min(
                    Fraction(1),
                    s.fraction("failure_upper") + q.fraction("failure_upper"),
                ),
                s.boolean("all_rows_observed")
                and q.boolean("all_rows_observed"),
            ),
        )

    for action in CandidateAction:
        suffix = action.value
        plan = nodes[ProofAddress[f"PLAN_{suffix}"]]
        regret = max(
            Fraction(0),
            (
                nodes[ProofAddress.U0].fraction("reward_upper")
                - plan.fraction("reward_lower")
            )
            / query.return_upper,
        )
        build(
            ProofAddress[f"REGRET_{suffix}"],
            {"action": action.value},
            (
                _ff("normalized_regret", regret),
                _bf("passes", regret <= query.normalized_regret_tolerance),
            ),
        )

    for action in CandidateAction:
        suffix = action.value
        failure = nodes[ProofAddress[f"PLAN_{suffix}"]].fraction(
            "failure_upper"
        )
        build(
            ProofAddress[f"RISK_{suffix}"],
            {"action": action.value},
            (
                _ff("failure_upper", failure),
                _bf("passes", failure <= query.risk_tolerance),
            ),
        )

    for action in CandidateAction:
        suffix = action.value
        plan = nodes[ProofAddress[f"PLAN_{suffix}"]]
        build(
            ProofAddress[f"COVERAGE_{suffix}"],
            {
                "action": action.value,
                "required_rows": (
                    ["S", "N1", "N2", "N3"]
                    if action is CandidateAction.N
                    else ["S", "M"]
                ),
            },
            (_bf("passes", plan.boolean("all_rows_observed")),),
        )

    selected_action, selected_code, selection_mode = _selection(nodes)
    build(
        ProofAddress.SELECTION,
        {
            "candidate_order": ["N", "M"],
            "schedule_mapping": {"N": "A0A0", "M": "A0A1"},
        },
        (
            _tf("schedule_code", selected_code),
            _tf("selected_action", selected_action.value),
            _tf("selection_mode", selection_mode),
        ),
    )

    nodes_tuple = tuple(nodes[address] for address in ADDRESS_ORDER)
    audits = tuple(
        _build_candidate_audit(
            model.epoch,
            model.model_id,
            query.query_id,
            action,
            nodes,
        )
        for action in CandidateAction
    )
    lower_ids = tuple(item.node_id for item in nodes_tuple)
    candidate_roots = tuple(
        ActionIndexedProofRootV1(
            model.epoch,
            model.model_id,
            query.query_id,
            ProofRootRole.CANDIDATE_AUDIT,
            audit.action,
            audit.audit_id,
            lower_ids,
            None,
            audit.certified,
        )
        for audit in audits
    )
    proposal = ActionIndexedPlanProposalV1(
        model.epoch,
        model.model_id,
        query.query_id,
        nodes[ProofAddress.SELECTION].node_id,
        tuple(item.audit_id for item in audits),  # type: ignore[arg-type]
        tuple(item.root_id for item in candidate_roots),  # type: ignore[arg-type]
        selected_action,
        selected_code,
        selection_mode,
    )
    selected_audit = audits[0 if selected_action is CandidateAction.N else 1]
    selected_root = ActionIndexedProofRootV1(
        model.epoch,
        model.model_id,
        query.query_id,
        ProofRootRole.INDEPENDENT_SELECTED_ROOT,
        selected_action,
        selected_audit.audit_id,
        lower_ids,
        proposal.proposal_id,
        selected_audit.certified,
    )
    return ActionIndexedEpochSemanticReplayV1(
        nodes_tuple,
        audits,
        candidate_roots,
        proposal,
        selected_root,
    )


def execute_action_indexed_epoch_v1(
    model: ActionIndexedH2ModelV1,
    query: ActionIndexedH2QueryV1,
    runtime: ActionIndexedProofRuntimeV1,
) -> ActionIndexedEpochExecutionV1:
    """Execute one registered epoch against a reusable lower-proof runtime."""

    if (
        type(model) is not ActionIndexedH2ModelV1
        or type(query) is not ActionIndexedH2QueryV1
        or type(runtime) is not ActionIndexedProofRuntimeV1
    ):
        raise ActionIndexedProofInvariantViolation(
            "epoch execution requires exact model/query/runtime types"
        )
    model.__post_init__()
    query.__post_init__()
    runtime._validate_next(model)
    pre_snapshot = runtime.snapshot_id
    nodes: dict[ProofAddress, ActionIndexedProofNodeV1] = {}
    resolutions: list[ActionIndexedProofResolutionV1] = []

    def resolve(
        address: ProofAddress,
        input_document: Mapping[str, Any],
        result_fields: tuple[ActionIndexedResultFieldV1, ...],
    ) -> ActionIndexedProofNodeV1:
        parents = tuple(nodes[item] for item in EXPECTED_PARENT_ADDRESSES[address])
        candidate = _node_candidate(
            address, parents, input_document, query, result_fields
        )
        node, outcome = runtime._resolve(candidate)
        nodes[address] = node
        resolutions.append(
            ActionIndexedProofResolutionV1(
                len(resolutions) + 1,
                model.epoch,
                model.model_id,
                query.query_id,
                address,
                node.node_key_id,
                node.node_id,
                outcome,
            )
        )
        return node

    for row in model.rows:
        resolve(
            ROW_ADDRESS_BY_NAME[row.name],
            {"ground_row": row.to_document()},
            _interval_fields(
                row.reward_lower,
                row.reward_upper,
                row.failure_lower,
                row.failure_upper,
                row.status is GroundRowStatus.OBSERVED,
            ),
        )

    for action, row_names, address in (
        (
            CandidateAction.N,
            (GroundRowName.N1, GroundRowName.N2, GroundRowName.N3),
            ProofAddress.Q_N,
        ),
        (CandidateAction.M, (GroundRowName.M,), ProofAddress.Q_M),
    ):
        parents = tuple(nodes[ROW_ADDRESS_BY_NAME[name]] for name in row_names)
        rows = tuple(model.row(name) for name in row_names)
        resolve(
            address,
            {
                "action": action.value,
                "mixture": [
                    {
                        "row_name": row.name.value,
                        "weight": _fdoc(row.concretizer_weight),
                    }
                    for row in rows
                ],
            },
            _interval_fields(
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("reward_lower")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("reward_upper")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("failure_lower")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                sum(
                    (
                        row.concretizer_weight
                        * parent.fraction("failure_upper")
                        for row, parent in zip(rows, parents)
                    ),
                    Fraction(0),
                ),
                all(parent.boolean("all_rows_observed") for parent in parents),
            ),
        )

    resolve(
        ProofAddress.U1,
        {"action_order": ["N", "M"], "remaining_horizon": 1},
        (
            _ff(
                "reward_upper",
                max(
                    nodes[ProofAddress.Q_N].fraction("reward_upper"),
                    nodes[ProofAddress.Q_M].fraction("reward_upper"),
                ),
            ),
        ),
    )
    resolve(
        ProofAddress.U0,
        {
            "stage_zero_row": GroundRowName.S.value,
            "remaining_horizon": 2,
        },
        (
            _ff(
                "reward_upper",
                min(
                    query.return_upper,
                    nodes[ProofAddress.ROW_S].fraction("reward_upper")
                    + nodes[ProofAddress.U1].fraction("reward_upper"),
                ),
            ),
        ),
    )

    for action, plan_address, q_address in (
        (CandidateAction.N, ProofAddress.PLAN_N, ProofAddress.Q_N),
        (CandidateAction.M, ProofAddress.PLAN_M, ProofAddress.Q_M),
    ):
        s = nodes[ProofAddress.ROW_S]
        q = nodes[q_address]
        resolve(
            plan_address,
            {
                "action": action.value,
                "schedule_code": (
                    "A0A0" if action is CandidateAction.N else "A0A1"
                ),
                "stage_zero_row": GroundRowName.S.value,
            },
            _interval_fields(
                s.fraction("reward_lower") + q.fraction("reward_lower"),
                min(
                    query.return_upper,
                    s.fraction("reward_upper") + q.fraction("reward_upper"),
                ),
                min(
                    Fraction(1),
                    s.fraction("failure_lower") + q.fraction("failure_lower"),
                ),
                min(
                    Fraction(1),
                    s.fraction("failure_upper") + q.fraction("failure_upper"),
                ),
                s.boolean("all_rows_observed") and q.boolean("all_rows_observed"),
            ),
        )

    for action in CandidateAction:
        suffix = action.value
        plan = nodes[ProofAddress[f"PLAN_{suffix}"]]
        regret = max(
            Fraction(0),
            (
                nodes[ProofAddress.U0].fraction("reward_upper")
                - plan.fraction("reward_lower")
            )
            / query.return_upper,
        )
        resolve(
            ProofAddress[f"REGRET_{suffix}"],
            {"action": action.value},
            (
                _ff("normalized_regret", regret),
                _bf("passes", regret <= query.normalized_regret_tolerance),
            ),
        )

    for action in CandidateAction:
        suffix = action.value
        failure = nodes[ProofAddress[f"PLAN_{suffix}"]].fraction("failure_upper")
        resolve(
            ProofAddress[f"RISK_{suffix}"],
            {"action": action.value},
            (
                _ff("failure_upper", failure),
                _bf("passes", failure <= query.risk_tolerance),
            ),
        )

    for action in CandidateAction:
        suffix = action.value
        plan = nodes[ProofAddress[f"PLAN_{suffix}"]]
        resolve(
            ProofAddress[f"COVERAGE_{suffix}"],
            {
                "action": action.value,
                "required_rows": (
                    ["S", "N1", "N2", "N3"]
                    if action is CandidateAction.N
                    else ["S", "M"]
                ),
            },
            (_bf("passes", plan.boolean("all_rows_observed")),),
        )

    selected_action, selected_code, selection_mode = _selection(nodes)
    resolve(
        ProofAddress.SELECTION,
        {
            "candidate_order": ["N", "M"],
            "schedule_mapping": {"N": "A0A0", "M": "A0A1"},
        },
        (
            _tf("schedule_code", selected_code),
            _tf("selected_action", selected_action.value),
            _tf("selection_mode", selection_mode),
        ),
    )

    nodes_tuple = tuple(nodes[address] for address in ADDRESS_ORDER)
    resolutions_tuple = tuple(resolutions)
    audits = tuple(
        _build_candidate_audit(
            model.epoch, model.model_id, query.query_id, action, nodes
        )
        for action in CandidateAction
    )
    lower_ids = tuple(item.node_id for item in nodes_tuple)
    candidate_roots = tuple(
        ActionIndexedProofRootV1(
            model.epoch,
            model.model_id,
            query.query_id,
            ProofRootRole.CANDIDATE_AUDIT,
            audit.action,
            audit.audit_id,
            lower_ids,
            None,
            audit.certified,
        )
        for audit in audits
    )
    proposal = ActionIndexedPlanProposalV1(
        model.epoch,
        model.model_id,
        query.query_id,
        nodes[ProofAddress.SELECTION].node_id,
        tuple(item.audit_id for item in audits),  # type: ignore[arg-type]
        tuple(item.root_id for item in candidate_roots),  # type: ignore[arg-type]
        selected_action,
        selected_code,
        selection_mode,
    )
    selected_audit = audits[0 if selected_action is CandidateAction.N else 1]
    selected_root = ActionIndexedProofRootV1(
        model.epoch,
        model.model_id,
        query.query_id,
        ProofRootRole.INDEPENDENT_SELECTED_ROOT,
        selected_action,
        selected_audit.audit_id,
        lower_ids,
        proposal.proposal_id,
        selected_audit.certified,
    )
    lower_computed = sum(
        item.outcome is ProofResolutionOutcome.COMPUTED
        for item in resolutions_tuple
    )
    work = ActionIndexedProofWorkV1(
        lower_computed, 18 - lower_computed, 3
    )
    pending = runtime._pending_invalidation
    preexecution_invalidation_id: str | None = None
    if model.epoch is ModelEpoch.FINAL_5_OBSERVED_0_MISSING:
        if pending is None:
            raise ActionIndexedProofInvariantViolation(
                "final execution lost its pre-execution invalidation authority"
            )
        outcomes = {item.address: item.outcome for item in resolutions_tuple}
        recomputed = _ordered_addresses(
            address
            for address in ADDRESS_ORDER
            if outcomes[address] is ProofResolutionOutcome.COMPUTED
        )
        reused = _ordered_addresses(
            address
            for address in ADDRESS_ORDER
            if outcomes[address] is ProofResolutionOutcome.REUSED
        )
        if (
            recomputed != pending.affected_addresses
            or reused != pending.unaffected_addresses
        ):
            raise ActionIndexedProofInvariantViolation(
                "final proof work violates the pre-authorized invalidation cone"
            )
        preexecution_invalidation_id = pending.plan_id

    # The post snapshot must bind the execution, but the execution itself also
    # contains that snapshot.  Freeze a pre-commit cache snapshot here; after
    # construction the runtime records the execution ID separately.
    post_snapshot = runtime.snapshot_id
    execution = ActionIndexedEpochExecutionV1(
        model.epoch,
        model.model_id,
        query.query_id,
        pre_snapshot,
        post_snapshot,
        resolutions_tuple,
        nodes_tuple,
        audits,
        candidate_roots,
        proposal,
        selected_root,
        work,
        preexecution_invalidation_id,
        model,
        query,
    )
    runtime._commit_execution(model.model_id, execution.execution_id)
    return execution


def restore_verified_action_indexed_first_runtime_v1(
    model: ActionIndexedH2ModelV1,
    query: ActionIndexedH2QueryV1,
    execution: ActionIndexedEpochExecutionV1,
) -> tuple[ActionIndexedProofRuntimeV1, ActionIndexedFirstRuntimeRestoreV1]:
    """Load the exact verified first lower graph without persisting roots.

    Semantic validation is deliberately repeated before loading.  The returned
    runtime records the canonical first execution history so a separately
    verified durable lease can continue with the normal pre-invalidation and
    final-epoch APIs.  Callers must account semantic replay and storage I/O
    separately from the 18 loaded lower entries; this helper makes no work-
    saving claim.
    """

    if (
        type(model) is not ActionIndexedH2ModelV1
        or type(query) is not ActionIndexedH2QueryV1
        or type(execution) is not ActionIndexedEpochExecutionV1
    ):
        raise ActionIndexedProofInvariantViolation(
            "first-runtime restore requires exact model/query/execution types"
        )
    model.__post_init__()
    query.__post_init__()
    execution.__post_init__()
    if (
        model.epoch is not ModelEpoch.FIRST_4_OBSERVED_1_MISSING
        or execution.epoch is not model.epoch
        or execution.model_id != model.model_id
        or execution.query_id != query.query_id
        or execution.semantic_model.to_document() != model.to_document()
        or execution.semantic_query.to_document() != query.to_document()
        or execution.work.lower_computed != 18
        or execution.work.lower_reused != 0
    ):
        raise ActionIndexedProofInvariantViolation(
            "first-runtime restore source is not the exact first execution"
        )
    validation_runtime = ActionIndexedProofRuntimeV1()
    canonical_execution = execute_action_indexed_epoch_v1(
        model,
        query,
        validation_runtime,
    )
    if execution.to_document() != canonical_execution.to_document():
        raise ActionIndexedProofInvariantViolation(
            "first-runtime restore execution differs from fresh semantic replay"
        )
    return restore_verified_action_indexed_first_lower_graph_v1(
        model,
        query,
        execution.nodes,
        execution.execution_id,
    )


def restore_verified_action_indexed_first_lower_graph_v1(
    model: ActionIndexedH2ModelV1,
    query: ActionIndexedH2QueryV1,
    durable_nodes: tuple[ActionIndexedProofNodeV1, ...],
    source_execution_id: str,
) -> tuple[ActionIndexedProofRuntimeV1, ActionIndexedFirstRuntimeRestoreV1]:
    """Load canonical first lower-node objects supplied by durable storage."""

    if (
        type(model) is not ActionIndexedH2ModelV1
        or type(query) is not ActionIndexedH2QueryV1
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable first restore requires exact model/query types"
        )
    _require_exact_tuple(
        durable_nodes,
        ActionIndexedProofNodeV1,
        "durable first lower nodes",
    )
    source_execution_id = _cid(
        source_execution_id,
        "durable first source execution",
    )
    if (
        model.epoch is not ModelEpoch.FIRST_4_OBSERVED_1_MISSING
        or tuple(item.address for item in durable_nodes) != ADDRESS_ORDER
        or len({item.node_key_id for item in durable_nodes}) != 18
        or len({item.node_id for item in durable_nodes}) != 18
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable first lower graph shape changed"
        )
    validation_runtime = ActionIndexedProofRuntimeV1()
    canonical_execution = execute_action_indexed_epoch_v1(
        model,
        query,
        validation_runtime,
    )
    if (
        source_execution_id != canonical_execution.execution_id
        or tuple(item.to_document() for item in durable_nodes)
        != tuple(
            item.to_document()
            for item in canonical_execution.nodes
        )
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable first lower graph differs from semantic replay"
        )
    runtime = ActionIndexedProofRuntimeV1()
    pre_snapshot = runtime.snapshot_id
    runtime._cache = {
        node.node_key_id: node
        for node in durable_nodes
    }
    if (
        len(runtime._cache) != 18
        or any(
            runtime._cache[node.node_key_id] is not node
            for node in durable_nodes
        )
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable first lower objects were not loaded exactly"
        )
    runtime._commit_execution(model.model_id, source_execution_id)
    post_snapshot = runtime.snapshot_id
    receipt = ActionIndexedFirstRuntimeRestoreV1(
        model.model_id,
        query.query_id,
        source_execution_id,
        tuple(item.node_id for item in durable_nodes),
        pre_snapshot,
        post_snapshot,
    )
    if runtime.cache_size != 18:
        raise ActionIndexedProofInvariantViolation(
            "durable first restore cache cardinality changed"
        )
    return runtime, receipt


def restore_verified_action_indexed_final_lower_graph_v1(
    model: ActionIndexedH2ModelV1,
    query: ActionIndexedH2QueryV1,
    durable_full_nodes: tuple[ActionIndexedProofNodeV1, ...],
    active_final_bindings: tuple[tuple[str, str, str], ...],
    source_execution_id: str,
) -> tuple[ActionIndexedProofRuntimeV1, ActionIndexedFinalRuntimeRestoreV1]:
    """Validate a 28-node union and operationally load its 18 active nodes."""

    if (
        type(model) is not ActionIndexedH2ModelV1
        or type(query) is not ActionIndexedH2QueryV1
        or type(active_final_bindings) is not tuple
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable final restore requires exact typed inputs"
        )
    _require_exact_tuple(
        durable_full_nodes,
        ActionIndexedProofNodeV1,
        "durable final full lower nodes",
    )
    source_execution_id = _cid(
        source_execution_id,
        "durable final source execution",
    )
    if (
        model.epoch is not ModelEpoch.FINAL_5_OBSERVED_0_MISSING
        or len(durable_full_nodes) != 28
        or tuple(item.node_id for item in durable_full_nodes)
        != tuple(sorted(item.node_id for item in durable_full_nodes))
        or len({item.node_id for item in durable_full_nodes}) != 28
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable final union shape changed"
        )
    first_replay = replay_action_indexed_epoch_semantics_v1(
        registered_first_action_indexed_h2_model_v1(),
        query,
    )
    final_replay = replay_action_indexed_epoch_semantics_v1(model, query)
    expected_union = {
        node.node_id: node
        for node in (*first_replay.nodes, *final_replay.nodes)
    }
    supplied_union = {
        node.node_id: node for node in durable_full_nodes
    }
    if (
        len(expected_union) != 28
        or set(supplied_union) != set(expected_union)
        or any(
            supplied_union[node_id].to_document()
            != expected.to_document()
            for node_id, expected in expected_union.items()
        )
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable final union differs from semantic replay"
        )
    if (
        len(active_final_bindings) != 18
        or tuple(item[0] for item in active_final_bindings)
        != tuple(address.value for address in ADDRESS_ORDER)
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable final active bindings changed"
        )
    active_nodes: list[ActionIndexedProofNodeV1] = []
    for binding, expected in zip(
        active_final_bindings,
        final_replay.nodes,
    ):
        if (
            type(binding) is not tuple
            or len(binding) != 3
            or binding
            != (
                expected.address.value,
                expected.node_key_id,
                expected.node_id,
            )
        ):
            raise ActionIndexedProofInvariantViolation(
                "durable final active binding differs from semantic replay"
            )
        active_nodes.append(supplied_union[expected.node_id])
    canonical_final = run_registered_action_indexed_h2_switch_v1()[1]
    if source_execution_id != canonical_final.execution_id:
        raise ActionIndexedProofInvariantViolation(
            "durable final source execution changed"
        )
    runtime = ActionIndexedProofRuntimeV1()
    pre_snapshot = runtime.snapshot_id
    runtime._cache = {
        node.node_key_id: node for node in active_nodes
    }
    if (
        len(runtime._cache) != 18
        or any(
            runtime._cache[node.node_key_id] is not node
            for node in active_nodes
        )
    ):
        raise ActionIndexedProofInvariantViolation(
            "durable final active objects were not loaded exactly"
        )
    runtime._commit_execution(model.model_id, source_execution_id)
    post_snapshot = runtime.snapshot_id
    receipt = ActionIndexedFinalRuntimeRestoreV1(
        model.model_id,
        query.query_id,
        source_execution_id,
        tuple(item.node_id for item in durable_full_nodes),
        tuple(item.node_id for item in active_nodes),
        pre_snapshot,
        post_snapshot,
    )
    return runtime, receipt


def rebuild_action_indexed_roots_from_restored_runtime_v1(
    model: ActionIndexedH2ModelV1,
    query: ActionIndexedH2QueryV1,
    runtime: ActionIndexedProofRuntimeV1,
    restore: ActionIndexedFirstRuntimeRestoreV1
    | ActionIndexedFinalRuntimeRestoreV1,
) -> ActionIndexedRestoredRootReplayV1:
    """Build the three non-cacheable roots from the loaded lower objects."""

    if (
        type(model) is not ActionIndexedH2ModelV1
        or type(query) is not ActionIndexedH2QueryV1
        or type(runtime) is not ActionIndexedProofRuntimeV1
        or type(restore)
        not in (
            ActionIndexedFirstRuntimeRestoreV1,
            ActionIndexedFinalRuntimeRestoreV1,
        )
    ):
        raise ActionIndexedProofInvariantViolation(
            "restored-root replay requires exact typed inputs"
        )
    restore.__post_init__()
    if (
        restore.model_id != model.model_id
        or restore.query_id != query.query_id
        or restore.post_runtime_snapshot_id != runtime.snapshot_id
        or runtime.cache_size != 18
    ):
        raise ActionIndexedProofInvariantViolation(
            "restored-root replay lost its runtime binding"
        )
    nodes_by_address = {
        node.address: node for node in runtime._cache.values()
    }
    if set(nodes_by_address) != set(ADDRESS_ORDER):
        raise ActionIndexedProofInvariantViolation(
            "restored-root replay has an incomplete lower graph"
        )
    nodes = tuple(nodes_by_address[address] for address in ADDRESS_ORDER)
    expected_active_ids = (
        restore.ordered_lower_node_ids
        if type(restore) is ActionIndexedFirstRuntimeRestoreV1
        else restore.active_ordered_node_ids
    )
    if tuple(item.node_id for item in nodes) != expected_active_ids:
        raise ActionIndexedProofInvariantViolation(
            "restored-root lower-node order changed"
        )
    node_by_id = {item.node_id: item for item in nodes}
    for address, node in zip(ADDRESS_ORDER, nodes):
        try:
            parents = tuple(
                node_by_id[parent].address
                for parent in node.ordered_parent_node_ids
            )
        except KeyError as error:
            raise ActionIndexedProofInvariantViolation(
                "restored-root graph has a missing parent"
            ) from error
        if parents != EXPECTED_PARENT_ADDRESSES[address]:
            raise ActionIndexedProofInvariantViolation(
                "restored-root parent topology changed"
            )
    mapping = {
        node.address: node for node in nodes
    }
    audits = tuple(
        _build_candidate_audit(
            model.epoch,
            model.model_id,
            query.query_id,
            action,
            mapping,
        )
        for action in CandidateAction
    )
    lower_ids = tuple(item.node_id for item in nodes)
    candidate_roots = tuple(
        ActionIndexedProofRootV1(
            model.epoch,
            model.model_id,
            query.query_id,
            ProofRootRole.CANDIDATE_AUDIT,
            audit.action,
            audit.audit_id,
            lower_ids,
            None,
            audit.certified,
        )
        for audit in audits
    )
    selected_action = CandidateAction(
        mapping[ProofAddress.SELECTION].text("selected_action")
    )
    selected_code = mapping[ProofAddress.SELECTION].text("schedule_code")
    selection_mode = mapping[ProofAddress.SELECTION].text("selection_mode")
    proposal = ActionIndexedPlanProposalV1(
        model.epoch,
        model.model_id,
        query.query_id,
        mapping[ProofAddress.SELECTION].node_id,
        tuple(item.audit_id for item in audits),  # type: ignore[arg-type]
        tuple(item.root_id for item in candidate_roots),  # type: ignore[arg-type]
        selected_action,
        selected_code,
        selection_mode,
    )
    selected_audit = audits[
        0 if selected_action is CandidateAction.N else 1
    ]
    selected_root = ActionIndexedProofRootV1(
        model.epoch,
        model.model_id,
        query.query_id,
        ProofRootRole.INDEPENDENT_SELECTED_ROOT,
        selected_action,
        selected_audit.audit_id,
        lower_ids,
        proposal.proposal_id,
        selected_audit.certified,
    )
    replay = replay_action_indexed_epoch_semantics_v1(model, query)
    if (
        tuple(item.to_document() for item in nodes)
        != tuple(item.to_document() for item in replay.nodes)
        or tuple(item.to_document() for item in audits)
        != tuple(
            item.to_document() for item in replay.candidate_audits
        )
        or tuple(item.to_document() for item in candidate_roots)
        != tuple(
            item.to_document() for item in replay.candidate_roots
        )
        or proposal.to_document() != replay.proposal.to_document()
        or selected_root.to_document()
        != replay.selected_root.to_document()
        or runtime.snapshot_id != restore.post_runtime_snapshot_id
    ):
        raise ActionIndexedProofInvariantViolation(
            "restored-root result differs from semantic replay"
        )
    return ActionIndexedRestoredRootReplayV1(
        model.epoch,
        model.model_id,
        query.query_id,
        restore.execution_id,
        restore.restore_id,
        runtime.snapshot_id,
        lower_ids,
        audits,
        candidate_roots,
        proposal,
        selected_root,
    )


@dataclass(frozen=True, slots=True)
class ActionIndexedModelDeltaV1:
    first_model_id: str
    final_model_id: str
    changed_row_names: tuple[GroundRowName, ...]
    changed_first_row_ids: tuple[str, ...]
    changed_final_row_ids: tuple[str, ...]
    unchanged_row_names: tuple[GroundRowName, ...]
    unchanged_row_ids: tuple[str, ...]
    first_observed_count: int
    first_missing_count: int
    final_observed_count: int
    final_missing_count: int

    def __post_init__(self) -> None:
        for value in (
            self.first_model_id,
            self.final_model_id,
            *self.changed_first_row_ids,
            *self.changed_final_row_ids,
            *self.unchanged_row_ids,
        ):
            _cid(value, "model delta identity")
        if (
            type(self.changed_row_names) is not tuple
            or any(type(item) is not GroundRowName for item in self.changed_row_names)
            or type(self.unchanged_row_names) is not tuple
            or any(type(item) is not GroundRowName for item in self.unchanged_row_names)
            or self.changed_row_names != (GroundRowName.M,)
            or self.unchanged_row_names
            != (
                GroundRowName.S,
                GroundRowName.N1,
                GroundRowName.N2,
                GroundRowName.N3,
            )
            or len(self.changed_first_row_ids) != 1
            or len(self.changed_final_row_ids) != 1
            or self.changed_first_row_ids == self.changed_final_row_ids
            or len(self.unchanged_row_ids) != 4
            or (
                self.first_observed_count,
                self.first_missing_count,
                self.final_observed_count,
                self.final_missing_count,
            )
            != (4, 1, 5, 0)
        ):
            raise ActionIndexedProofInvariantViolation("registered one-row delta changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_model_delta.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "first_model_id": self.first_model_id,
            "final_model_id": self.final_model_id,
            "changed_row_names": [item.value for item in self.changed_row_names],
            "changed_first_row_ids": list(self.changed_first_row_ids),
            "changed_final_row_ids": list(self.changed_final_row_ids),
            "unchanged_row_names": [item.value for item in self.unchanged_row_names],
            "unchanged_row_ids": list(self.unchanged_row_ids),
            "first_observed_count": self.first_observed_count,
            "first_missing_count": self.first_missing_count,
            "final_observed_count": self.final_observed_count,
            "final_missing_count": self.final_missing_count,
        }

    @property
    def delta_id(self) -> str:
        return _content_id("delta", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "delta_id": self.delta_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedInvalidationEdgeV1:
    parent_address: ProofAddress
    child_address: ProofAddress
    first_parent_node_id: str
    first_child_node_id: str

    def __post_init__(self) -> None:
        if (
            type(self.parent_address) is not ProofAddress
            or type(self.child_address) is not ProofAddress
        ):
            raise ActionIndexedProofInvariantViolation("invalidation edge enum changed")
        for value in (self.first_parent_node_id, self.first_child_node_id):
            _cid(value, "invalidation edge node")
        if self.parent_address not in EXPECTED_PARENT_ADDRESSES[self.child_address]:
            raise ActionIndexedProofInvariantViolation("edge is absent from proof topology")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_invalidation_edge.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "parent_address": self.parent_address.value,
            "child_address": self.child_address.value,
            "first_parent_node_id": self.first_parent_node_id,
            "first_child_node_id": self.first_child_node_id,
        }

    @property
    def edge_id(self) -> str:
        return _content_id("edge", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "edge_id": self.edge_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedPreExecutionInvalidationV1:
    delta_id: str
    first_model_id: str
    final_model_id: str
    first_execution_id: str
    direct_changed_addresses: tuple[ProofAddress, ...]
    affected_addresses: tuple[ProofAddress, ...]
    unaffected_addresses: tuple[ProofAddress, ...]
    closure_edges: tuple[ActionIndexedInvalidationEdgeV1, ...]
    reverse_edge_closure_derived: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.delta_id,
            self.first_model_id,
            self.final_model_id,
            self.first_execution_id,
        ):
            _cid(value, "pre-execution invalidation identity")
        for name in (
            "direct_changed_addresses",
            "affected_addresses",
            "unaffected_addresses",
        ):
            values = getattr(self, name)
            if (
                type(values) is not tuple
                or any(type(item) is not ProofAddress for item in values)
                or values != _ordered_addresses(values)
            ):
                raise ActionIndexedProofInvariantViolation(
                    f"{name} is not canonical"
                )
        _require_exact_tuple(
            self.closure_edges,
            ActionIndexedInvalidationEdgeV1,
            "pre-execution closure edges",
        )
        if tuple(item.edge_id for item in self.closure_edges) != tuple(
            sorted({item.edge_id for item in self.closure_edges})
        ):
            raise ActionIndexedProofInvariantViolation(
                "pre-execution closure edges are not canonical"
            )
        if (
            self.direct_changed_addresses != (ProofAddress.ROW_M,)
            or self.affected_addresses != EXPECTED_AFFECTED_ADDRESSES
            or self.unaffected_addresses != EXPECTED_UNAFFECTED_ADDRESSES
            or len(self.closure_edges) != 14
            or set(self.affected_addresses) & set(self.unaffected_addresses)
            or set((*self.affected_addresses, *self.unaffected_addresses))
            != set(ADDRESS_ORDER)
            or self.reverse_edge_closure_derived is not True
        ):
            raise ActionIndexedProofInvariantViolation(
                "registered pre-execution invalidation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_preexecution_invalidation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "delta_id": self.delta_id,
            "first_model_id": self.first_model_id,
            "final_model_id": self.final_model_id,
            "first_execution_id": self.first_execution_id,
            "direct_changed_addresses": [
                item.value for item in self.direct_changed_addresses
            ],
            "affected_addresses": [item.value for item in self.affected_addresses],
            "unaffected_addresses": [
                item.value for item in self.unaffected_addresses
            ],
            "closure_edges": [item.to_document() for item in self.closure_edges],
            "reverse_edge_closure_derived": self.reverse_edge_closure_derived,
        }

    @property
    def plan_id(self) -> str:
        return _content_id("pre_invalidation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "plan_id": self.plan_id}


@dataclass(frozen=True, slots=True)
class ActionIndexedInvalidationManifestV1:
    delta_id: str
    preexecution_invalidation_id: str
    first_execution_id: str
    final_execution_id: str
    direct_changed_addresses: tuple[ProofAddress, ...]
    affected_addresses: tuple[ProofAddress, ...]
    unaffected_addresses: tuple[ProofAddress, ...]
    recomputed_addresses: tuple[ProofAddress, ...]
    reused_addresses: tuple[ProofAddress, ...]
    closure_edges: tuple[ActionIndexedInvalidationEdgeV1, ...]
    reverse_edge_closure_derived: bool = True
    output_equality_cannot_bypass_parent_change: bool = True
    whole_model_identity_absent_from_lower_keys: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.delta_id,
            self.preexecution_invalidation_id,
            self.first_execution_id,
            self.final_execution_id,
        ):
            _cid(value, "invalidation manifest identity")
        for name in (
            "direct_changed_addresses",
            "affected_addresses",
            "unaffected_addresses",
            "recomputed_addresses",
            "reused_addresses",
        ):
            values = getattr(self, name)
            if (
                type(values) is not tuple
                or any(type(item) is not ProofAddress for item in values)
                or values != _ordered_addresses(values)
            ):
                raise ActionIndexedProofInvariantViolation(
                    f"{name} is not canonical"
                )
        _require_exact_tuple(
            self.closure_edges,
            ActionIndexedInvalidationEdgeV1,
            "closure edges",
            nonempty=True,
        )
        if tuple(item.edge_id for item in self.closure_edges) != tuple(
            sorted({item.edge_id for item in self.closure_edges})
        ):
            raise ActionIndexedProofInvariantViolation(
                "closure edges must be unique and content-ID sorted"
            )
        if (
            self.direct_changed_addresses != (ProofAddress.ROW_M,)
            or len(self.affected_addresses) != 10
            or self.unaffected_addresses != EXPECTED_UNAFFECTED_ADDRESSES
            or self.recomputed_addresses != self.affected_addresses
            or self.reused_addresses != self.unaffected_addresses
            or set(self.affected_addresses) & set(self.unaffected_addresses)
            or set((*self.affected_addresses, *self.unaffected_addresses))
            != set(ADDRESS_ORDER)
            or self.reverse_edge_closure_derived is not True
            or self.output_equality_cannot_bypass_parent_change is not True
            or self.whole_model_identity_absent_from_lower_keys is not True
        ):
            raise ActionIndexedProofInvariantViolation(
                "registered invalidation partition changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.action_indexed_invalidation_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "delta_id": self.delta_id,
            "preexecution_invalidation_id": self.preexecution_invalidation_id,
            "first_execution_id": self.first_execution_id,
            "final_execution_id": self.final_execution_id,
            "direct_changed_addresses": [
                item.value for item in self.direct_changed_addresses
            ],
            "affected_addresses": [item.value for item in self.affected_addresses],
            "unaffected_addresses": [
                item.value for item in self.unaffected_addresses
            ],
            "recomputed_addresses": [
                item.value for item in self.recomputed_addresses
            ],
            "reused_addresses": [item.value for item in self.reused_addresses],
            "closure_edges": [item.to_document() for item in self.closure_edges],
            "reverse_edge_closure_derived": self.reverse_edge_closure_derived,
            "output_equality_cannot_bypass_parent_change": (
                self.output_equality_cannot_bypass_parent_change
            ),
            "whole_model_identity_absent_from_lower_keys": (
                self.whole_model_identity_absent_from_lower_keys
            ),
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("invalidation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


def _derive_registered_model_delta(
    first_model: ActionIndexedH2ModelV1,
    final_model: ActionIndexedH2ModelV1,
) -> ActionIndexedModelDeltaV1:
    if (
        type(first_model) is not ActionIndexedH2ModelV1
        or type(final_model) is not ActionIndexedH2ModelV1
    ):
        raise ActionIndexedProofInvariantViolation(
            "model delta derivation requires exact registered models"
        )
    first_model.__post_init__()
    final_model.__post_init__()
    if (
        first_model.epoch is not ModelEpoch.FIRST_4_OBSERVED_1_MISSING
        or final_model.epoch is not ModelEpoch.FINAL_5_OBSERVED_0_MISSING
    ):
        raise ActionIndexedProofInvariantViolation("model delta epoch binding changed")
    changed = tuple(
        name
        for name in GroundRowName
        if first_model.row(name).to_document()
        != final_model.row(name).to_document()
    )
    unchanged = tuple(name for name in GroundRowName if name not in set(changed))
    return ActionIndexedModelDeltaV1(
        first_model.model_id,
        final_model.model_id,
        changed,
        tuple(first_model.row(name).row_id for name in changed),
        tuple(final_model.row(name).row_id for name in changed),
        unchanged,
        tuple(first_model.row(name).row_id for name in unchanged),
        first_model.observed_row_count,
        first_model.missing_row_count,
        final_model.observed_row_count,
        final_model.missing_row_count,
    )


def _derive_reverse_closure(
    first_execution: ActionIndexedEpochExecutionV1,
    delta: ActionIndexedModelDeltaV1,
) -> tuple[
    tuple[ProofAddress, ...],
    tuple[ProofAddress, ...],
    tuple[ProofAddress, ...],
    tuple[ActionIndexedInvalidationEdgeV1, ...],
]:
    if (
        type(first_execution) is not ActionIndexedEpochExecutionV1
        or type(delta) is not ActionIndexedModelDeltaV1
    ):
        raise ActionIndexedProofInvariantViolation(
            "reverse closure requires exact execution and delta"
        )
    first_execution.__post_init__()
    delta.__post_init__()
    if (
        first_execution.epoch is not ModelEpoch.FIRST_4_OBSERVED_1_MISSING
        or first_execution.model_id != delta.first_model_id
    ):
        raise ActionIndexedProofInvariantViolation(
            "reverse closure first-epoch binding changed"
        )
    first_node_by_id = {item.node_id: item for item in first_execution.nodes}
    reverse: dict[ProofAddress, set[ProofAddress]] = {
        address: set() for address in ADDRESS_ORDER
    }
    all_edges: list[ActionIndexedInvalidationEdgeV1] = []
    for child in first_execution.nodes:
        for parent_id in child.ordered_parent_node_ids:
            parent = first_node_by_id.get(parent_id)
            if parent is None:
                raise ActionIndexedProofInvariantViolation(
                    "first execution parent is absent from its node catalogue"
                )
            reverse[parent.address].add(child.address)
            all_edges.append(
                ActionIndexedInvalidationEdgeV1(
                    parent.address,
                    child.address,
                    parent.node_id,
                    child.node_id,
                )
            )
    direct = _ordered_addresses(
        ROW_ADDRESS_BY_NAME[name] for name in delta.changed_row_names
    )
    closure = set(direct)
    queue = list(direct)
    while queue:
        parent = queue.pop(0)
        for child in sorted(reverse[parent], key=ADDRESS_INDEX.__getitem__):
            if child not in closure:
                closure.add(child)
                queue.append(child)
    affected = _ordered_addresses(closure)
    unaffected = _ordered_addresses(set(ADDRESS_ORDER) - closure)
    closure_edges = tuple(
        sorted(
            (
                edge
                for edge in all_edges
                if edge.parent_address in closure
                and edge.child_address in closure
            ),
            key=lambda item: item.edge_id,
        )
    )
    return direct, affected, unaffected, closure_edges


def derive_action_indexed_preexecution_invalidation_v1(
    first_model: ActionIndexedH2ModelV1,
    final_model: ActionIndexedH2ModelV1,
    first_execution: ActionIndexedEpochExecutionV1,
) -> tuple[
    ActionIndexedModelDeltaV1,
    ActionIndexedPreExecutionInvalidationV1,
]:
    """Freeze the exact delta and reverse closure before final replanning."""

    if type(first_execution) is not ActionIndexedEpochExecutionV1:
        raise ActionIndexedProofInvariantViolation(
            "pre-execution invalidation requires the exact first execution"
        )
    delta = _derive_registered_model_delta(first_model, final_model)
    first_execution.__post_init__()
    if first_execution.model_id != first_model.model_id:
        raise ActionIndexedProofInvariantViolation(
            "pre-execution invalidation model/execution binding changed"
        )
    direct, affected, unaffected, closure_edges = _derive_reverse_closure(
        first_execution,
        delta,
    )
    plan = ActionIndexedPreExecutionInvalidationV1(
        delta.delta_id,
        first_model.model_id,
        final_model.model_id,
        first_execution.execution_id,
        direct,
        affected,
        unaffected,
        closure_edges,
    )
    return delta, plan


def authorize_action_indexed_final_epoch_v1(
    runtime: ActionIndexedProofRuntimeV1,
    plan: ActionIndexedPreExecutionInvalidationV1,
) -> None:
    """Bind a derived pre-execution invalidation to the live proof runtime."""

    if type(runtime) is not ActionIndexedProofRuntimeV1:
        raise ActionIndexedProofInvariantViolation(
            "final-epoch authorization requires the exact runtime"
        )
    runtime._authorize_final_invalidation(plan)


def derive_action_indexed_delta_and_invalidation_v1(
    first_model: ActionIndexedH2ModelV1,
    final_model: ActionIndexedH2ModelV1,
    first_execution: ActionIndexedEpochExecutionV1,
    final_execution: ActionIndexedEpochExecutionV1,
) -> tuple[ActionIndexedModelDeltaV1, ActionIndexedInvalidationManifestV1]:
    """Verify final work against the already frozen reverse-closure authority."""

    if type(final_execution) is not ActionIndexedEpochExecutionV1:
        raise ActionIndexedProofInvariantViolation(
            "post-execution invalidation requires the exact final execution"
        )
    delta, pre = derive_action_indexed_preexecution_invalidation_v1(
        first_model,
        final_model,
        first_execution,
    )
    final_execution.__post_init__()
    if (
        final_execution.model_id != final_model.model_id
        or first_execution.query_id != final_execution.query_id
        or final_execution.preexecution_invalidation_id != pre.plan_id
    ):
        raise ActionIndexedProofInvariantViolation(
            "final execution lacks the frozen pre-execution invalidation"
        )
    direct = pre.direct_changed_addresses
    affected = pre.affected_addresses
    unaffected = pre.unaffected_addresses
    closure_edges = pre.closure_edges
    outcomes = {item.address: item.outcome for item in final_execution.resolutions}
    recomputed = _ordered_addresses(
        address
        for address in ADDRESS_ORDER
        if outcomes[address] is ProofResolutionOutcome.COMPUTED
    )
    reused = _ordered_addresses(
        address
        for address in ADDRESS_ORDER
        if outcomes[address] is ProofResolutionOutcome.REUSED
    )
    first_nodes = {item.address: item for item in first_execution.nodes}
    final_nodes = {item.address: item for item in final_execution.nodes}
    if any(
        first_nodes[address].node_id != final_nodes[address].node_id
        for address in reused
    ) or any(
        first_nodes[address].node_id == final_nodes[address].node_id
        for address in recomputed
    ):
        raise ActionIndexedProofInvariantViolation(
            "reuse/recompute identity does not match node entries"
        )
    manifest = ActionIndexedInvalidationManifestV1(
        delta.delta_id,
        pre.plan_id,
        first_execution.execution_id,
        final_execution.execution_id,
        direct,
        affected,
        unaffected,
        recomputed,
        reused,
        closure_edges,
    )
    return delta, manifest


def registered_first_action_indexed_h2_model_v1() -> ActionIndexedH2ModelV1:
    """Return the exact 4-observed/1-missing registered first model."""

    return ActionIndexedH2ModelV1(
        ModelEpoch.FIRST_4_OBSERVED_1_MISSING,
        (
            ActionIndexedGroundRowV1(
                GroundRowName.S,
                "x0",
                "A0",
                Fraction(1),
                GroundRowStatus.OBSERVED,
                Fraction(0),
                Fraction(0),
                Fraction(0),
                Fraction(0),
            ),
            *(
                ActionIndexedGroundRowV1(
                    name,
                    "x1",
                    "A0",
                    Fraction(1, 3),
                    GroundRowStatus.OBSERVED,
                    Fraction(0),
                    Fraction(0),
                    Fraction(0),
                    Fraction(0),
                )
                for name in (GroundRowName.N1, GroundRowName.N2, GroundRowName.N3)
            ),
            ActionIndexedGroundRowV1(
                GroundRowName.M,
                "x1",
                "A1",
                Fraction(1),
                GroundRowStatus.MISSING_VACUOUS,
                Fraction(0),
                Fraction(3),
                Fraction(0),
                Fraction(1),
            ),
        ),
    )


def registered_final_action_indexed_h2_model_v1() -> ActionIndexedH2ModelV1:
    """Return the exact 5-observed registered one-row successor model."""

    first = registered_first_action_indexed_h2_model_v1()
    return ActionIndexedH2ModelV1(
        ModelEpoch.FINAL_5_OBSERVED_0_MISSING,
        (
            *first.rows[:-1],
            ActionIndexedGroundRowV1(
                GroundRowName.M,
                "x1",
                "A1",
                Fraction(1),
                GroundRowStatus.OBSERVED,
                Fraction(1),
                Fraction(1),
                Fraction(0),
                Fraction(0),
            ),
        ),
    )


def registered_action_indexed_h2_query_v1() -> ActionIndexedH2QueryV1:
    """Return the exact H2/zero-risk/zero-regret/Rmax=4 query."""

    return ActionIndexedH2QueryV1()


def run_registered_action_indexed_h2_switch_v1() -> tuple[
    ActionIndexedEpochExecutionV1,
    ActionIndexedEpochExecutionV1,
    ActionIndexedModelDeltaV1,
    ActionIndexedInvalidationManifestV1,
]:
    """Convenience model-only replay of both epochs and exact invalidation."""

    first_model = registered_first_action_indexed_h2_model_v1()
    final_model = registered_final_action_indexed_h2_model_v1()
    query = registered_action_indexed_h2_query_v1()
    runtime = ActionIndexedProofRuntimeV1()
    first = execute_action_indexed_epoch_v1(first_model, query, runtime)
    _, pre = derive_action_indexed_preexecution_invalidation_v1(
        first_model, final_model, first
    )
    authorize_action_indexed_final_epoch_v1(runtime, pre)
    final = execute_action_indexed_epoch_v1(final_model, query, runtime)
    delta, manifest = derive_action_indexed_delta_and_invalidation_v1(
        first_model, final_model, first, final
    )
    return first, final, delta, manifest


__all__ = [
    "ADDRESS_ORDER",
    "ActionIndexedCandidateAuditV1",
    "ActionIndexedEpochExecutionV1",
    "ActionIndexedEpochSemanticReplayV1",
    "ActionIndexedFinalRuntimeRestoreV1",
    "ActionIndexedFirstRuntimeRestoreV1",
    "ActionIndexedGroundRowV1",
    "ActionIndexedH2ModelV1",
    "ActionIndexedH2QueryV1",
    "ActionIndexedInvalidationEdgeV1",
    "ActionIndexedInvalidationManifestV1",
    "ActionIndexedModelDeltaV1",
    "ActionIndexedPlanProposalV1",
    "ActionIndexedPreExecutionInvalidationV1",
    "ActionIndexedProofInvariantViolation",
    "ActionIndexedProofNodeV1",
    "ActionIndexedProofResolutionV1",
    "ActionIndexedProofRootV1",
    "ActionIndexedProofRuntimeV1",
    "ActionIndexedProofWorkV1",
    "ActionIndexedRestoredRootReplayV1",
    "CandidateAction",
    "GroundRowName",
    "GroundRowStatus",
    "ModelEpoch",
    "PROFILE_KEY",
    "ProofAddress",
    "ProofNodeKind",
    "ProofResolutionOutcome",
    "ProofRootRole",
    "SCHEMA_VERSION",
    "authorize_action_indexed_final_epoch_v1",
    "derive_action_indexed_delta_and_invalidation_v1",
    "derive_action_indexed_preexecution_invalidation_v1",
    "execute_action_indexed_epoch_v1",
    "parse_action_indexed_proof_node_document_v1",
    "rebuild_action_indexed_roots_from_restored_runtime_v1",
    "replay_action_indexed_epoch_semantics_v1",
    "registered_action_indexed_h2_query_v1",
    "registered_final_action_indexed_h2_model_v1",
    "registered_first_action_indexed_h2_model_v1",
    "restore_verified_action_indexed_first_runtime_v1",
    "restore_verified_action_indexed_first_lower_graph_v1",
    "restore_verified_action_indexed_final_lower_graph_v1",
    "run_registered_action_indexed_h2_switch_v1",
]
