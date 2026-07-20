"""Cap-aware exact joint search over a sparse local-recovery capability.

The trusted side eliminates the selected abstract proof DAG before invoking
this stdlib-only worker.  The worker receives only:

* frontier input ports, each with the certified scalar value used while its
  cell remains abstract;
* abstract exit ports carrying a reward floor and failure ceiling; and
* sparse affine root forms.  Root reward is the minimum reward form and root
  failure is the maximum failure form.

For each candidate set of localized frontier cells the solver enumerates the
entire Cartesian product of deterministic ground actions.  It may Pareto-prune
only after a complete assignment has been reduced to a root
``(reward_floor, failure_ceiling)`` pair.  The exact frontier can be
exponential, so deterministic caps and work counters are part of the request
and result.  A cap is never confused with authorized-policy exhaustion.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import itertools
import json
import re
from typing import Any, Iterable, Mapping, Sequence


CAPABILITY_SCHEMA = "acfqp.sparse_robust_affine_capability.v1"
SLICE_SCHEMA = "acfqp.sparse_frontier_ground_slice.v1"
REQUEST_SCHEMA = "acfqp.general_local_recovery_request.v1"
RESULT_SCHEMA = "acfqp.general_local_solver_result.v1"

ALGORITHM_ID = "global_deterministic_assignment_root_pareto_v1"
SELECTION_RULE = (
    "minimum_localized_cell_cardinality_then_maximum_root_reward_floor_"
    "then_minimum_root_failure_ceiling_then_subset_and_policy_signature"
)
POLICY_CLASS = "deterministic_finite_horizon_markov"

CERTIFIED = "LOCAL_RECOVERY_CERTIFIED"
AUTHORIZED_EXHAUSTED = "LOCAL_RECOVERY_AUTHORIZED_EXHAUSTED"
SEARCH_CAP_EXHAUSTED = "LOCAL_RECOVERY_SEARCH_CAP_EXHAUSTED"

_OPAQUE_ID = re.compile(r"^[a-z][a-z0-9-]*(?::|-)[0-9a-f]{16,64}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _object_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def _logical_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _input_sha256(value: Any) -> str:
    return hashlib.sha256((_canonical_json(value) + "\n").encode("utf-8")).hexdigest()


def _require_fields(document: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = fields - set(document)
    if missing:
        raise ValueError(f"{label} is missing fields {sorted(missing)!r}")
    extra = set(document) - fields
    if extra:
        raise ValueError(f"{label} has forbidden extra fields {sorted(extra)!r}")


def _fraction(value: Any, *, field: str) -> Fraction:
    if not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}:
        raise ValueError(f"{field} must be a canonical exact rational object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if (
        isinstance(numerator, bool)
        or isinstance(denominator, bool)
        or not isinstance(numerator, int)
        or not isinstance(denominator, int)
        or denominator <= 0
    ):
        raise ValueError(f"{field} is not a canonical exact rational")
    result = Fraction(numerator, denominator)
    if result.numerator != numerator or result.denominator != denominator:
        raise ValueError(f"{field} exact rational is not reduced")
    return result


def _fraction_json(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _require_opaque_id(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise ValueError(f"{field} must be an opaque content ID")
    return value


def _require_port_id(value: Any, *, field: str) -> str:
    port_id = _require_opaque_id(value, field=field)
    if not port_id.startswith("proof-node-"):
        raise ValueError(f"{field} must identify an abstract proof-node cell")
    return port_id


def _product(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result *= value
    return result


def _rational_bits(value: Fraction) -> int:
    return max(abs(value.numerator).bit_length(), value.denominator.bit_length())


@dataclass(frozen=True, slots=True)
class SearchLimits:
    max_subset_evaluations: int
    max_policy_assignments: int
    max_root_frontier_points: int
    max_dominance_comparisons: int
    max_affine_term_evaluations: int
    max_rational_bits: int

    @classmethod
    def from_dict(cls, document: Any) -> "SearchLimits":
        if not isinstance(document, Mapping):
            raise ValueError("search limits must be an object")
        names = (
            "max_subset_evaluations",
            "max_policy_assignments",
            "max_root_frontier_points",
            "max_dominance_comparisons",
            "max_affine_term_evaluations",
            "max_rational_bits",
        )
        _require_fields(document, set(names), "search limits")
        return cls(
            *(
                _positive_int(document[name], field=f"search_limits.{name}")
                for name in names
            )
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_subset_evaluations": self.max_subset_evaluations,
            "max_policy_assignments": self.max_policy_assignments,
            "max_root_frontier_points": self.max_root_frontier_points,
            "max_dominance_comparisons": self.max_dominance_comparisons,
            "max_affine_term_evaluations": self.max_affine_term_evaluations,
            "max_rational_bits": self.max_rational_bits,
        }


@dataclass(frozen=True, slots=True)
class _InputPort:
    port_id: str
    default_reward_lower: Fraction
    default_failure_upper: Fraction


@dataclass(frozen=True, slots=True)
class _ExitPort:
    port_id: str
    reward_lower: Fraction
    failure_upper: Fraction


@dataclass(frozen=True, slots=True)
class _SparseForm:
    form_id: str
    constant: Fraction
    terms: tuple[tuple[str, Fraction], ...]


@dataclass(frozen=True, slots=True)
class _Action:
    action_id: str
    immediate_reward: Fraction
    immediate_failure: Fraction
    exits: tuple[tuple[str, Fraction], ...]


@dataclass(frozen=True, slots=True)
class _Member:
    state_id: str
    actions: tuple[_Action, ...]


@dataclass(frozen=True, slots=True)
class _Cell:
    node_id: str
    cell: str
    remaining: int
    input_port_id: str
    members: tuple[_Member, ...]


@dataclass(frozen=True, slots=True)
class _Capability:
    required_reward_floor: Fraction
    allowed_failure_ceiling: Fraction
    input_ports: Mapping[str, _InputPort]
    exit_ports: Mapping[str, _ExitPort]
    reward_forms: tuple[_SparseForm, ...]
    failure_forms: tuple[_SparseForm, ...]


@dataclass(frozen=True, slots=True)
class LocalPatchDecision:
    node_id: str
    cell: str
    remaining: int
    state_id: str
    input_port_id: str
    action_id: str
    reward_floor: Fraction
    failure_ceiling: Fraction

    def signature(self) -> tuple[int, str, str, str]:
        return (-self.remaining, self.node_id, self.state_id, self.action_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "cell": self.cell,
            "remaining": self.remaining,
            "state_id": self.state_id,
            "input_port_id": self.input_port_id,
            "action_id": self.action_id,
            "reward_floor": _fraction_json(self.reward_floor),
            "failure_ceiling": _fraction_json(self.failure_ceiling),
        }


@dataclass(frozen=True, slots=True)
class _RootPoint:
    reward_floor: Fraction
    failure_ceiling: Fraction
    decisions: tuple[LocalPatchDecision, ...]

    @property
    def policy_signature(self) -> tuple[tuple[int, str, str, str], ...]:
        return tuple(decision.signature() for decision in self.decisions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_reward_floor": _fraction_json(self.reward_floor),
            "root_failure_ceiling": _fraction_json(self.failure_ceiling),
            "policy_signature": [list(item) for item in self.policy_signature],
        }


@dataclass(slots=True)
class _Counters:
    subset_evaluations: int = 0
    policy_assignments: int = 0
    action_port_evaluations: int = 0
    affine_form_evaluations: int = 0
    affine_term_evaluations: int = 0
    dominance_comparisons: int = 0
    peak_root_frontier_points: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "subset_evaluations": self.subset_evaluations,
            "policy_assignments": self.policy_assignments,
            "action_port_evaluations": self.action_port_evaluations,
            "affine_form_evaluations": self.affine_form_evaluations,
            "affine_term_evaluations": self.affine_term_evaluations,
            "dominance_comparisons": self.dominance_comparisons,
            "peak_root_frontier_points": self.peak_root_frontier_points,
        }


@dataclass(frozen=True, slots=True)
class SubsetSearchRecord:
    localized_node_ids: tuple[str, ...]
    theoretical_policy_assignments: int
    evaluated_policy_assignments: int
    root_frontier: tuple[_RootPoint, ...]
    complete: bool
    cap_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "localized_node_ids": list(self.localized_node_ids),
            "theoretical_policy_assignments": self.theoretical_policy_assignments,
            "evaluated_policy_assignments": self.evaluated_policy_assignments,
            "root_frontier_size": len(self.root_frontier),
            "root_frontier": [point.to_dict() for point in self.root_frontier],
            "complete": self.complete,
            "cap_reason": self.cap_reason,
        }


@dataclass(frozen=True, slots=True)
class GeneralLocalSolverResult:
    request_id: str
    occurrence_id: str
    capability_id: str
    slice_id: str
    frontier_id: str
    status: str
    localized_node_ids: tuple[str, ...]
    decisions: tuple[LocalPatchDecision, ...]
    root_reward_lower: Fraction | None
    required_reward_floor: Fraction
    root_failure_upper: Fraction | None
    allowed_failure_ceiling: Fraction
    theoretical_total_policy_space: int
    subset_records: tuple[SubsetSearchRecord, ...]
    counters: Mapping[str, int]
    search_limits: SearchLimits
    cap_reason: str | None
    result_id: str

    @property
    def reward_margin(self) -> Fraction | None:
        if self.root_reward_lower is None:
            return None
        return self.root_reward_lower - self.required_reward_floor

    @property
    def certified_safe(self) -> bool:
        return (
            self.root_failure_upper is not None
            and self.root_failure_upper <= self.allowed_failure_ceiling
        )

    @property
    def certified_value(self) -> bool:
        return (
            self.reward_margin is not None and self.reward_margin >= 0
        )

    @property
    def certified(self) -> bool:
        return self.status == CERTIFIED and self.certified_safe and self.certified_value

    @property
    def search_complete(self) -> bool:
        return self.status in {CERTIFIED, AUTHORIZED_EXHAUSTED}

    @property
    def minimality_proven(self) -> bool:
        return self.search_complete

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RESULT_SCHEMA,
            "algorithm_id": ALGORITHM_ID,
            "selection_rule": SELECTION_RULE,
            "policy_class": POLICY_CLASS,
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "capability_id": self.capability_id,
            "slice_id": self.slice_id,
            "frontier_id": self.frontier_id,
            "status": self.status,
            "localized_node_ids": list(self.localized_node_ids),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "root_reward_lower": (
                _fraction_json(self.root_reward_lower)
                if self.root_reward_lower is not None
                else None
            ),
            "required_reward_floor": _fraction_json(self.required_reward_floor),
            "reward_margin": (
                _fraction_json(self.reward_margin)
                if self.reward_margin is not None
                else None
            ),
            "root_failure_upper": (
                _fraction_json(self.root_failure_upper)
                if self.root_failure_upper is not None
                else None
            ),
            "allowed_failure_ceiling": _fraction_json(
                self.allowed_failure_ceiling
            ),
            "theoretical_total_policy_space": self.theoretical_total_policy_space,
            "candidate_subset_count": len(self.subset_records),
            "subset_records": [record.to_dict() for record in self.subset_records],
            "counters": dict(self.counters),
            "search_limits": self.search_limits.to_dict(),
            "cap_reason": self.cap_reason,
            "search_complete": self.search_complete,
            "minimality_proven": self.minimality_proven,
            "certified_safe": self.certified_safe,
            "certified_value": self.certified_value,
            "certified": self.certified,
            "result_id": self.result_id,
        }


class _CapReached(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _parse_terms(raw: Any, *, field: str) -> tuple[tuple[str, Fraction], ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be a list")
    terms: dict[str, Fraction] = {}
    for index, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        _require_fields(row, {"port_id", "coefficient"}, f"{field}[{index}]")
        port_id = _require_port_id(
            row["port_id"], field=f"{field}[{index}].port_id"
        )
        if port_id in terms:
            raise ValueError("sparse form port IDs must be nonempty and unique")
        coefficient = _fraction(
            row["coefficient"], field=f"{field}[{index}].coefficient"
        )
        if coefficient <= 0:
            raise ValueError("serialized sparse affine coefficients must be positive")
        terms[port_id] = coefficient
    ordered = tuple(sorted(terms.items()))
    if [row["port_id"] for row in raw] != [port_id for port_id, _ in ordered]:
        raise ValueError("sparse affine terms must be ordered by port_id")
    return ordered


def _parse_forms(raw: Any, *, field: str) -> tuple[_SparseForm, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{field} must be a nonempty list")
    forms: list[_SparseForm] = []
    seen: set[str] = set()
    for index, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        _require_fields(row, {"form_id", "constant", "terms"}, f"{field}[{index}]")
        form_id = row["form_id"]
        _require_opaque_id(form_id, field=f"{field}[{index}].form_id")
        if form_id in seen:
            raise ValueError("sparse form IDs must be nonempty and unique")
        seen.add(form_id)
        constant = _fraction(row["constant"], field=f"{field}[{index}].constant")
        terms = _parse_terms(row["terms"], field=f"{field}[{index}].terms")
        form_payload = {"constant": row["constant"], "terms": row["terms"]}
        if form_id != _logical_id("sparse-form", form_payload):
            raise ValueError("form_id does not bind its sparse affine payload")
        forms.append(_SparseForm(form_id, constant, terms))
    ordered = tuple(sorted(forms, key=lambda form: form.form_id))
    if [row["form_id"] for row in raw] != [form.form_id for form in ordered]:
        raise ValueError(f"{field} must be ordered by form_id")
    return ordered


def _parse_capability(document: Mapping[str, Any]) -> _Capability:
    if document.get("schema") != CAPABILITY_SCHEMA:
        raise ValueError("unsupported sparse robust affine capability schema")
    fields = {
        "schema",
        "frontier_id",
        "reward_floor",
        "failure_ceiling",
        "input_ports",
        "exit_ports",
        "root_reward_forms",
        "root_failure_forms",
        "capability_id",
    }
    _require_fields(document, fields, "sparse robust affine capability")
    _require_opaque_id(document["frontier_id"], field="capability.frontier_id")
    required_reward = _fraction(
        document["reward_floor"], field="capability.reward_floor"
    )
    allowed_failure = _fraction(
        document["failure_ceiling"], field="capability.failure_ceiling"
    )
    if not 0 <= allowed_failure <= 1:
        raise ValueError("capability.failure_ceiling lies outside [0,1]")

    raw_inputs = document["input_ports"]
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError("input_ports must be a nonempty list")
    inputs: dict[str, _InputPort] = {}
    for index, row in enumerate(raw_inputs):
        if not isinstance(row, Mapping):
            raise ValueError("frontier input ports must be objects")
        _require_fields(
            row,
            {
                "port_id",
                "default_reward_lower",
                "default_failure_upper",
            },
            f"input_ports[{index}]",
        )
        port_id = _require_port_id(
            row["port_id"], field=f"input_ports[{index}].port_id"
        )
        if port_id in inputs:
            raise ValueError("frontier input port IDs must be nonempty and unique")
        failure = _fraction(
            row["default_failure_upper"],
            field="frontier input default_failure_upper",
        )
        if not 0 <= failure <= 1:
            raise ValueError("frontier input default failure lies outside [0,1]")
        inputs[port_id] = _InputPort(
            port_id,
            _fraction(
                row["default_reward_lower"],
                field="frontier input default_reward_lower",
            ),
            failure,
        )
    if [row["port_id"] for row in raw_inputs] != sorted(inputs):
        raise ValueError("input_ports must be uniquely sorted by port_id")

    raw_exits = document["exit_ports"]
    if not isinstance(raw_exits, list):
        raise ValueError("exit_ports must be a list")
    exits: dict[str, _ExitPort] = {}
    for index, row in enumerate(raw_exits):
        if not isinstance(row, Mapping):
            raise ValueError("abstract exit ports must be objects")
        _require_fields(
            row,
            {"port_id", "reward_lower", "failure_upper"},
            f"exit_ports[{index}]",
        )
        port_id = _require_port_id(
            row["port_id"], field=f"exit_ports[{index}].port_id"
        )
        if port_id in exits or port_id in inputs:
            raise ValueError("exit port IDs must be nonempty, unique, and disjoint")
        failure = _fraction(
            row["failure_upper"], field="abstract exit failure_upper"
        )
        if not 0 <= failure <= 1:
            raise ValueError("abstract exit failure lies outside [0,1]")
        exits[port_id] = _ExitPort(
            port_id,
            _fraction(row["reward_lower"], field="abstract exit reward_lower"),
            failure,
        )
    if [row["port_id"] for row in raw_exits] != sorted(exits):
        raise ValueError("exit_ports must be uniquely sorted by port_id")

    reward_forms = _parse_forms(document["root_reward_forms"], field="root_reward_forms")
    failure_forms = _parse_forms(
        document["root_failure_forms"], field="root_failure_forms"
    )
    known_inputs = set(inputs)
    for form in (*reward_forms, *failure_forms):
        unknown = {port_id for port_id, _ in form.terms} - known_inputs
        if unknown:
            raise ValueError(f"sparse root form references unknown inputs {sorted(unknown)!r}")
    payload = dict(document)
    capability_id = payload.pop("capability_id")
    if capability_id != _logical_id("sparse-robust-affine-capability", payload):
        raise ValueError("capability_id does not bind the sparse capability")
    _require_opaque_id(capability_id, field="capability.capability_id")
    return _Capability(
        required_reward,
        allowed_failure,
        inputs,
        exits,
        reward_forms,
        failure_forms,
    )


def _parse_exits(raw: Any, *, field: str) -> tuple[tuple[str, Fraction], ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be a list")
    exits: dict[str, Fraction] = {}
    for index, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        _require_fields(row, {"exit_port_id", "probability"}, f"{field}[{index}]")
        port_id = _require_port_id(
            row["exit_port_id"], field=f"{field}[{index}].exit_port_id"
        )
        if port_id in exits:
            raise ValueError("action exit port IDs must be nonempty and unique")
        probability = _fraction(
            row["probability"], field=f"{field}[{index}].probability"
        )
        if probability <= 0 or probability > 1:
            raise ValueError("action exit probability lies outside (0,1]")
        exits[port_id] = probability
    ordered = tuple(sorted(exits.items()))
    if [row["exit_port_id"] for row in raw] != [port_id for port_id, _ in ordered]:
        raise ValueError("action exits must be uniquely sorted by exit_port_id")
    return ordered


def _parse_slice(document: Mapping[str, Any]) -> dict[str, _Cell]:
    if document.get("schema") != SLICE_SCHEMA:
        raise ValueError("unsupported sparse frontier ground-slice schema")
    _require_fields(
        document,
        {"schema", "authorization_id", "frontier_id", "cells", "slice_id"},
        "sparse frontier ground slice",
    )
    _require_opaque_id(document["authorization_id"], field="slice.authorization_id")
    _require_opaque_id(document["frontier_id"], field="slice.frontier_id")
    raw_cells = document["cells"]
    if not isinstance(raw_cells, list) or not raw_cells:
        raise ValueError("ground slice cells must be a nonempty list")
    cells: dict[str, _Cell] = {}
    global_decisions: set[tuple[int, str]] = set()
    input_ports: set[str] = set()
    for cell_index, row in enumerate(raw_cells):
        if not isinstance(row, Mapping):
            raise ValueError("ground slice cell rows must be objects")
        _require_fields(
            row,
            {"node_id", "cell", "remaining", "input_port_id", "members"},
            f"slice.cells[{cell_index}]",
        )
        node_id = _require_port_id(
            row["node_id"], field=f"slice.cells[{cell_index}].node_id"
        )
        remaining = row["remaining"]
        if node_id in cells:
            raise ValueError("slice node IDs must be nonempty and unique")
        if not isinstance(row["cell"], str):
            raise ValueError("slice cell metadata must be a string")
        if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining <= 0:
            raise ValueError("slice remaining must be a positive integer")
        input_port_id = _require_port_id(
            row["input_port_id"],
            field=f"slice.cells[{cell_index}].input_port_id",
        )
        if input_port_id in input_ports:
            raise ValueError("slice cell input ports must be nonempty and unique")
        if input_port_id != node_id:
            raise ValueError("slice cell input_port_id must equal its proof-node ID")
        input_ports.add(input_port_id)
        raw_members = row["members"]
        if not isinstance(raw_members, list) or not raw_members:
            raise ValueError("localized cell must have active members")
        members: list[_Member] = []
        cell_states: set[str] = set()
        for member_index, member in enumerate(raw_members):
            if not isinstance(member, Mapping):
                raise ValueError("slice members must be objects")
            _require_fields(
                member,
                {"state_id", "actions"},
                f"slice.cells[{cell_index}].members[{member_index}]",
            )
            state_id = _require_opaque_id(
                member["state_id"],
                field=f"slice.cells[{cell_index}].members[{member_index}].state_id",
            )
            if state_id in cell_states:
                raise ValueError("state IDs must be nonempty and unique per cell")
            cell_states.add(state_id)
            if (remaining, state_id) in global_decisions:
                raise ValueError(
                    "a deterministic (state_id, remaining) decision occurs in multiple cells"
                )
            global_decisions.add((remaining, state_id))
            raw_actions = member["actions"]
            if not isinstance(raw_actions, list) or not raw_actions:
                raise ValueError("every localized member needs at least one action")
            actions: list[_Action] = []
            action_ids: set[str] = set()
            for action_index, action in enumerate(raw_actions):
                if not isinstance(action, Mapping):
                    raise ValueError("slice actions must be objects")
                _require_fields(
                    action,
                    {
                        "action_id",
                        "immediate_reward",
                        "failure_probability",
                        "termination_probability",
                        "exits",
                    },
                    f"slice action {action_index}",
                )
                action_id = _require_opaque_id(
                    action["action_id"], field=f"slice action {action_index}.action_id"
                )
                if action_id in action_ids:
                    raise ValueError("action IDs must be nonempty and unique per state")
                action_ids.add(action_id)
                failure = _fraction(
                    action["failure_probability"], field="slice action failure_probability"
                )
                termination = _fraction(
                    action["termination_probability"],
                    field="slice action termination_probability",
                )
                exits = _parse_exits(action["exits"], field="slice action exits")
                continuation = sum((probability for _, probability in exits), Fraction(0))
                if not 0 <= failure <= termination <= 1:
                    raise ValueError("slice action termination/failure mass is invalid")
                if termination + continuation != 1:
                    raise ValueError("slice action termination plus exit mass must equal one")
                actions.append(
                    _Action(
                        action_id,
                        _fraction(
                            action["immediate_reward"],
                            field="slice action immediate_reward",
                        ),
                        failure,
                        exits,
                    )
                )
            if [row["action_id"] for row in raw_actions] != sorted(action_ids):
                raise ValueError("slice actions must be uniquely sorted by action_id")
            members.append(
                _Member(
                    state_id,
                    tuple(sorted(actions, key=lambda item: item.action_id)),
                )
            )
        cells[node_id] = _Cell(
            node_id,
            row["cell"],
            remaining,
            input_port_id,
            tuple(sorted(members, key=lambda item: item.state_id)),
        )
        if [row["state_id"] for row in raw_members] != sorted(cell_states):
            raise ValueError("slice members must be uniquely sorted by state_id")
    if [row["node_id"] for row in raw_cells] != sorted(cells):
        raise ValueError("slice cells must be uniquely sorted by node_id")
    payload = dict(document)
    slice_id = payload.pop("slice_id")
    if slice_id != _object_id("sparse-frontier-ground-slice", payload):
        raise ValueError("slice_id does not bind the sparse ground slice")
    return cells


def _parse_request(
    document: Mapping[str, Any], capability: Mapping[str, Any], ground_slice: Mapping[str, Any]
) -> tuple[str, str, SearchLimits]:
    fields = {
        "schema",
        "request_id",
        "occurrence_id",
        "frontier_id",
        "capability_id",
        "slice_id",
        "capability_sha256",
        "slice_sha256",
        "algorithm_id",
        "selection_rule",
        "policy_class",
        "search_limits",
    }
    if not isinstance(document, Mapping):
        raise ValueError("general local request must be an object")
    _require_fields(document, fields, "general local request")
    if document.get("schema") != REQUEST_SCHEMA:
        raise ValueError("unsupported general local request schema")
    if document.get("algorithm_id") != ALGORITHM_ID:
        raise ValueError("general local request algorithm changed")
    if document.get("selection_rule") != SELECTION_RULE:
        raise ValueError("general local request selection rule changed")
    if document.get("policy_class") != POLICY_CLASS:
        raise ValueError("general local recovery forbids policy randomization")
    identifiers = {
        "frontier_id": capability.get("frontier_id"),
        "capability_id": capability.get("capability_id"),
        "slice_id": ground_slice.get("slice_id"),
    }
    if any(document.get(field) != value for field, value in identifiers.items()):
        raise ValueError("general local request cross-identifiers do not match")
    if capability.get("frontier_id") != ground_slice.get("frontier_id"):
        raise ValueError("capability and ground slice name different frontiers")
    if document.get("capability_sha256") != _input_sha256(capability):
        raise ValueError("general local request capability hash mismatch")
    if document.get("slice_sha256") != _input_sha256(ground_slice):
        raise ValueError("general local request slice hash mismatch")
    payload = dict(document)
    request_id = payload.pop("request_id")
    if request_id != _object_id("general-local-request", payload):
        raise ValueError("request_id does not bind the general local request")
    occurrence_id = document["occurrence_id"]
    _require_opaque_id(request_id, field="request.request_id")
    _require_opaque_id(occurrence_id, field="request.occurrence_id")
    return request_id, occurrence_id, SearchLimits.from_dict(document["search_limits"])


def _dominates(left: _RootPoint, right: _RootPoint) -> bool:
    return (
        left.reward_floor >= right.reward_floor
        and left.failure_ceiling <= right.failure_ceiling
        and (
            left.reward_floor > right.reward_floor
            or left.failure_ceiling < right.failure_ceiling
        )
    )


def _insert_root_point(
    frontier: list[_RootPoint],
    candidate: _RootPoint,
    counters: _Counters,
    limits: SearchLimits,
) -> None:
    duplicate: _RootPoint | None = None
    dominated = False
    remove: list[_RootPoint] = []
    for incumbent in frontier:
        if counters.dominance_comparisons >= limits.max_dominance_comparisons:
            raise _CapReached("max_dominance_comparisons")
        counters.dominance_comparisons += 1
        if (
            incumbent.reward_floor == candidate.reward_floor
            and incumbent.failure_ceiling == candidate.failure_ceiling
        ):
            duplicate = incumbent
            break
        if _dominates(incumbent, candidate):
            dominated = True
            break
        if _dominates(candidate, incumbent):
            remove.append(incumbent)
    if dominated:
        return
    if duplicate is not None:
        if duplicate.policy_signature <= candidate.policy_signature:
            return
        frontier.remove(duplicate)
    else:
        for point in remove:
            frontier.remove(point)
    frontier.append(candidate)
    frontier.sort(
        key=lambda point: (
            point.failure_ceiling,
            -point.reward_floor,
            point.policy_signature,
        )
    )
    counters.peak_root_frontier_points = max(
        counters.peak_root_frontier_points, len(frontier)
    )
    if len(frontier) > limits.max_root_frontier_points:
        raise _CapReached("max_root_frontier_points")


def _make_result(
    *,
    request_id: str,
    occurrence_id: str,
    capability_id: str,
    slice_id: str,
    frontier_id: str,
    status: str,
    required_reward_floor: Fraction,
    allowed_failure_ceiling: Fraction,
    theoretical_total: int,
    records: Sequence[SubsetSearchRecord],
    counters: _Counters,
    limits: SearchLimits,
    selected_subset: tuple[str, ...] = (),
    selected: _RootPoint | None = None,
    cap_reason: str | None = None,
) -> GeneralLocalSolverResult:
    provisional = GeneralLocalSolverResult(
        request_id=request_id,
        occurrence_id=occurrence_id,
        capability_id=capability_id,
        slice_id=slice_id,
        frontier_id=frontier_id,
        status=status,
        localized_node_ids=selected_subset,
        decisions=selected.decisions if selected else (),
        root_reward_lower=selected.reward_floor if selected else None,
        required_reward_floor=required_reward_floor,
        root_failure_upper=selected.failure_ceiling if selected else None,
        allowed_failure_ceiling=allowed_failure_ceiling,
        theoretical_total_policy_space=theoretical_total,
        subset_records=tuple(records),
        counters=counters.to_dict(),
        search_limits=limits,
        cap_reason=cap_reason,
        result_id="",
    )
    payload = provisional.to_dict()
    payload.pop("result_id")
    return replace(
        provisional,
        result_id=_logical_id("general-local-result", payload),
    )


def solve_general_local_recovery(
    capability_document: Mapping[str, Any],
    ground_slice: Mapping[str, Any],
    request: Mapping[str, Any],
) -> GeneralLocalSolverResult:
    """Jointly enumerate deterministic local overlays within explicit caps.

    A certified result exhausts every lower cell-cardinality and every subset
    at the selected cardinality.  An authorized-exhausted result is complete
    only for the supplied capability and fixed abstract policy outside the
    frontier.  A cap-exhausted result proves neither infeasibility nor
    cardinality minimality.
    """

    request_id, occurrence_id, limits = _parse_request(
        request, capability_document, ground_slice
    )
    capability = _parse_capability(capability_document)
    cells = _parse_slice(ground_slice)

    slice_ports = {cell.input_port_id for cell in cells.values()}
    if slice_ports != set(capability.input_ports):
        raise ValueError("slice cells do not exactly match capability input ports")
    for cell in cells.values():
        for member in cell.members:
            for action in member.actions:
                unknown = {port_id for port_id, _ in action.exits} - set(
                    capability.exit_ports
                )
                if unknown:
                    raise ValueError(
                        f"slice action references unknown exit ports {sorted(unknown)!r}"
                    )

    input_fractions: list[Fraction] = [
        capability.required_reward_floor,
        capability.allowed_failure_ceiling,
    ]
    for port in capability.input_ports.values():
        input_fractions.extend((port.default_reward_lower, port.default_failure_upper))
    for port in capability.exit_ports.values():
        input_fractions.extend((port.reward_lower, port.failure_upper))
    for form in (*capability.reward_forms, *capability.failure_forms):
        input_fractions.append(form.constant)
        input_fractions.extend(coefficient for _, coefficient in form.terms)
    for cell in cells.values():
        for member in cell.members:
            for action in member.actions:
                input_fractions.extend((action.immediate_reward, action.immediate_failure))
                input_fractions.extend(probability for _, probability in action.exits)

    frontier_ids = tuple(sorted(cells))
    cell_assignment_sizes = {
        node_id: _product(len(member.actions) for member in cells[node_id].members)
        for node_id in frontier_ids
    }
    theoretical_total = _product(
        1 + cell_assignment_sizes[node_id] for node_id in frontier_ids
    )
    counters = _Counters()
    records: list[SubsetSearchRecord] = []

    def cap_result(reason: str) -> GeneralLocalSolverResult:
        return _make_result(
            request_id=request_id,
            occurrence_id=occurrence_id,
            capability_id=capability_document["capability_id"],
            slice_id=ground_slice["slice_id"],
            frontier_id=capability_document["frontier_id"],
            status=SEARCH_CAP_EXHAUSTED,
            required_reward_floor=capability.required_reward_floor,
            allowed_failure_ceiling=capability.allowed_failure_ceiling,
            theoretical_total=theoretical_total,
            records=records,
            counters=counters,
            limits=limits,
            cap_reason=reason,
        )

    if any(_rational_bits(value) > limits.max_rational_bits for value in input_fractions):
        return cap_result("max_rational_bits")

    def charge_terms(count: int) -> None:
        if counters.affine_term_evaluations + count > limits.max_affine_term_evaluations:
            raise _CapReached("max_affine_term_evaluations")
        counters.affine_term_evaluations += count

    def check_bits(*values: Fraction) -> None:
        if any(_rational_bits(value) > limits.max_rational_bits for value in values):
            raise _CapReached("max_rational_bits")

    def action_value(action: _Action) -> tuple[Fraction, Fraction]:
        counters.action_port_evaluations += 1
        reward = action.immediate_reward
        failure = action.immediate_failure
        for exit_port_id, probability in action.exits:
            charge_terms(2)
            exit_port = capability.exit_ports[exit_port_id]
            reward += probability * exit_port.reward_lower
            failure += probability * exit_port.failure_upper
        check_bits(reward, failure)
        if not 0 <= failure <= 1:
            raise ValueError("action port failure ceiling lies outside [0,1]")
        return reward, failure

    def form_value(form: _SparseForm, values: Mapping[str, Fraction]) -> Fraction:
        counters.affine_form_evaluations += 1
        charge_terms(len(form.terms))
        result = form.constant + sum(
            (coefficient * values[port_id] for port_id, coefficient in form.terms),
            Fraction(0),
        )
        check_bits(result)
        return result

    def evaluate_assignment(
        assignment: Sequence[tuple[_Cell, _Member, _Action]],
    ) -> _RootPoint:
        reward_ports = {
            port_id: port.default_reward_lower
            for port_id, port in capability.input_ports.items()
        }
        failure_ports = {
            port_id: port.default_failure_upper
            for port_id, port in capability.input_ports.items()
        }
        decisions: list[LocalPatchDecision] = []
        cell_rewards: dict[str, list[Fraction]] = {}
        cell_failures: dict[str, list[Fraction]] = {}
        for cell, member, action in assignment:
            reward, failure = action_value(action)
            cell_rewards.setdefault(cell.node_id, []).append(reward)
            cell_failures.setdefault(cell.node_id, []).append(failure)
            decisions.append(
                LocalPatchDecision(
                    cell.node_id,
                    cell.cell,
                    cell.remaining,
                    member.state_id,
                    cell.input_port_id,
                    action.action_id,
                    reward,
                    failure,
                )
            )
        for node_id, rewards in cell_rewards.items():
            cell = cells[node_id]
            reward_ports[cell.input_port_id] = min(rewards)
            failure_ports[cell.input_port_id] = max(cell_failures[node_id])
        reward_floor = min(
            form_value(form, reward_ports) for form in capability.reward_forms
        )
        failure_ceiling = max(
            form_value(form, failure_ports) for form in capability.failure_forms
        )
        check_bits(reward_floor, failure_ceiling)
        if not 0 <= failure_ceiling <= 1:
            raise ValueError("root failure ceiling lies outside [0,1]")
        return _RootPoint(
            reward_floor,
            failure_ceiling,
            tuple(sorted(decisions, key=lambda decision: decision.signature())),
        )

    for cardinality in range(len(frontier_ids) + 1):
        feasible_at_cardinality: list[tuple[tuple[str, ...], _RootPoint]] = []
        for localized_tuple in itertools.combinations(frontier_ids, cardinality):
            if counters.subset_evaluations >= limits.max_subset_evaluations:
                return cap_result("max_subset_evaluations")
            counters.subset_evaluations += 1
            decision_members = tuple(
                (cells[node_id], member)
                for node_id in localized_tuple
                for member in cells[node_id].members
            )
            action_sets = tuple(member.actions for _, member in decision_members)
            theoretical = _product(len(actions) for actions in action_sets)
            evaluated_before = counters.policy_assignments
            root_frontier: list[_RootPoint] = []
            cap_reason: str | None = None
            try:
                for selected_actions in itertools.product(*action_sets):
                    if counters.policy_assignments >= limits.max_policy_assignments:
                        raise _CapReached("max_policy_assignments")
                    counters.policy_assignments += 1
                    assignment = tuple(
                        (cell, member, action)
                        for (cell, member), action in zip(
                            decision_members, selected_actions
                        )
                    )
                    point = evaluate_assignment(assignment)
                    _insert_root_point(root_frontier, point, counters, limits)
            except _CapReached as cap:
                cap_reason = cap.reason
            records.append(
                SubsetSearchRecord(
                    localized_tuple,
                    theoretical,
                    counters.policy_assignments - evaluated_before,
                    tuple(root_frontier),
                    cap_reason is None,
                    cap_reason,
                )
            )
            if cap_reason is not None:
                return cap_result(cap_reason)
            feasible = tuple(
                point
                for point in root_frontier
                if point.failure_ceiling <= capability.allowed_failure_ceiling
                and point.reward_floor >= capability.required_reward_floor
            )
            if feasible:
                selected = min(
                    feasible,
                    key=lambda point: (
                        -point.reward_floor,
                        point.failure_ceiling,
                        point.policy_signature,
                    ),
                )
                feasible_at_cardinality.append((localized_tuple, selected))
        if feasible_at_cardinality:
            selected_subset, selected_point = min(
                feasible_at_cardinality,
                key=lambda item: (
                    -item[1].reward_floor,
                    item[1].failure_ceiling,
                    item[0],
                    item[1].policy_signature,
                ),
            )
            return _make_result(
                request_id=request_id,
                occurrence_id=occurrence_id,
                capability_id=capability_document["capability_id"],
                slice_id=ground_slice["slice_id"],
                frontier_id=capability_document["frontier_id"],
                status=CERTIFIED,
                required_reward_floor=capability.required_reward_floor,
                allowed_failure_ceiling=capability.allowed_failure_ceiling,
                theoretical_total=theoretical_total,
                records=records,
                counters=counters,
                limits=limits,
                selected_subset=selected_subset,
                selected=selected_point,
            )

    return _make_result(
        request_id=request_id,
        occurrence_id=occurrence_id,
        capability_id=capability_document["capability_id"],
        slice_id=ground_slice["slice_id"],
        frontier_id=capability_document["frontier_id"],
        status=AUTHORIZED_EXHAUSTED,
        required_reward_floor=capability.required_reward_floor,
        allowed_failure_ceiling=capability.allowed_failure_ceiling,
        theoretical_total=theoretical_total,
        records=records,
        counters=counters,
        limits=limits,
    )


def validate_general_local_result(document: Mapping[str, Any]) -> None:
    """Validate result content binding and all serialized derived fields.

    This is intentionally useful outside the solver runtime: changing a
    status/flag/margin/counter and merely preserving the old result ID is
    rejected before a trusted verifier performs its independent semantic
    replay.
    """

    fields = {
        "schema",
        "algorithm_id",
        "selection_rule",
        "policy_class",
        "request_id",
        "occurrence_id",
        "capability_id",
        "slice_id",
        "frontier_id",
        "status",
        "localized_node_ids",
        "decisions",
        "root_reward_lower",
        "required_reward_floor",
        "reward_margin",
        "root_failure_upper",
        "allowed_failure_ceiling",
        "theoretical_total_policy_space",
        "candidate_subset_count",
        "subset_records",
        "counters",
        "search_limits",
        "cap_reason",
        "search_complete",
        "minimality_proven",
        "certified_safe",
        "certified_value",
        "certified",
        "result_id",
    }
    if not isinstance(document, Mapping):
        raise ValueError("general local result must be an object")
    _require_fields(document, fields, "general local result")
    if document.get("schema") != RESULT_SCHEMA:
        raise ValueError("unsupported general local result schema")
    if document.get("algorithm_id") != ALGORITHM_ID:
        raise ValueError("general local result algorithm changed")
    if document.get("selection_rule") != SELECTION_RULE:
        raise ValueError("general local result selection rule changed")
    if document.get("policy_class") != POLICY_CLASS:
        raise ValueError("general local result policy class changed")
    payload = dict(document)
    result_id = payload.pop("result_id")
    if result_id != _logical_id("general-local-result", payload):
        raise ValueError("result_id does not bind the complete result document")
    status = document["status"]
    if status not in {CERTIFIED, AUTHORIZED_EXHAUSTED, SEARCH_CAP_EXHAUSTED}:
        raise ValueError("general local result has an unknown status")
    records = document["subset_records"]
    if not isinstance(records, list):
        raise ValueError("subset_records must be a list")
    candidate_count = document["candidate_subset_count"]
    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count != len(records)
    ):
        raise ValueError("candidate_subset_count disagrees with subset_records")
    required = _fraction(
        document["required_reward_floor"], field="result.required_reward_floor"
    )
    allowed = _fraction(
        document["allowed_failure_ceiling"],
        field="result.allowed_failure_ceiling",
    )
    if not 0 <= allowed <= 1:
        raise ValueError("result allowed failure lies outside [0,1]")
    raw_reward = document["root_reward_lower"]
    raw_failure = document["root_failure_upper"]
    if (raw_reward is None) != (raw_failure is None):
        raise ValueError("root reward/failure must both be present or absent")
    reward = (
        _fraction(raw_reward, field="result.root_reward_lower")
        if raw_reward is not None
        else None
    )
    failure = (
        _fraction(raw_failure, field="result.root_failure_upper")
        if raw_failure is not None
        else None
    )
    if failure is not None and not 0 <= failure <= 1:
        raise ValueError("result root failure lies outside [0,1]")
    margin = reward - required if reward is not None else None
    expected_margin = _fraction_json(margin) if margin is not None else None
    if document["reward_margin"] != expected_margin:
        raise ValueError("serialized reward_margin is false")
    safe = failure is not None and failure <= allowed
    valuable = margin is not None and margin >= 0
    certified = status == CERTIFIED and safe and valuable
    expected_complete = status in {CERTIFIED, AUTHORIZED_EXHAUSTED}
    expected_flags = {
        "search_complete": expected_complete,
        "minimality_proven": expected_complete,
        "certified_safe": safe,
        "certified_value": valuable,
        "certified": certified,
    }
    for field, expected in expected_flags.items():
        if document[field] is not expected:
            raise ValueError(f"serialized {field} flag is false")
    if status == SEARCH_CAP_EXHAUSTED:
        if not isinstance(document["cap_reason"], str) or not document["cap_reason"]:
            raise ValueError("cap-exhausted result requires a cap_reason")
    elif document["cap_reason"] is not None:
        raise ValueError("complete result cannot carry a cap_reason")


__all__ = [
    "ALGORITHM_ID",
    "AUTHORIZED_EXHAUSTED",
    "CAPABILITY_SCHEMA",
    "CERTIFIED",
    "GeneralLocalSolverResult",
    "LocalPatchDecision",
    "POLICY_CLASS",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "SEARCH_CAP_EXHAUSTED",
    "SELECTION_RULE",
    "SLICE_SCHEMA",
    "SearchLimits",
    "SubsetSearchRecord",
    "solve_general_local_recovery",
    "validate_general_local_result",
]
