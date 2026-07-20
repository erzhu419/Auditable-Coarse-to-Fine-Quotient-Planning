"""Minimal sparse value/risk handoff capabilities for isolated local solvers.

The trusted compiler in this module consumes the complete selected-policy
``redacted_boundary_view.v1`` and eliminates that recursive graph into two
root functions.  The worker receives only a small capability:

* frontier input ports, with the certified abstract pair used when a port is
  not localized;
* optional scalar abstract-exit ports used by local slice successors;
* a lower-reward envelope represented as a minimum of sparse affine forms;
* an upper-failure envelope represented as a maximum of sparse affine forms;
* the two query acceptance thresholds.

Ground identities, selected actions, realization rows, graph/root metadata,
and minimality witnesses remain in trusted compilation evidence.  The worker
parser deliberately uses an exact field allowlist so those records cannot be
smuggled back into its authority surface.

Minimality is relative to the caller-declared *finite admissible input domain*.
The domain contains the default abstract pair plus every robust cell pair that
the independently authorized local slice can produce.  Singleton coordinates
are constant-folded, duplicate forms are removed, and a canonical minimum-cardinality
set of forms is selected over that finite domain.  The evidence supplies an
exact equivalence table and a necessity witness for every retained form and
input/exit port.  This is a verifiable minimum in the frozen sparse-affine
representation class; it is not an information-theoretic minimum encoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import itertools
import json
import re
from typing import Any, Iterable, Mapping, Sequence


CAPABILITY_SCHEMA = "acfqp.sparse_robust_affine_capability.v1"
EVIDENCE_SCHEMA = "acfqp.sparse_capability_compilation_evidence.v1"
SOURCE_SCHEMA = "acfqp.redacted_boundary_view.v1"
SPARSE_SLICE_SCHEMA = "acfqp.sparse_frontier_ground_slice.v1"
V1_SLICE_SCHEMA = "acfqp.authorized_ground_slice.v1"

_OPAQUE_ID = re.compile(r"^[a-z][a-z0-9-]*(?::|-)[0-9a-f]{16,64}$")
_FORBIDDEN_WORKER_KEYS = {
    "abstract_realizations",
    "action_id",
    "cell",
    "graph_id",
    "model_id",
    "node_id",
    "realization_id",
    "remaining",
    "roots",
    "selected_action",
    "state_id",
    "successors",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _logical_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _object_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def _fraction(value: Any, *, field: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an exact rational")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Mapping) and set(value) == {"numerator", "denominator"}:
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
            raise ValueError(f"{field} is not reduced")
        return result
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Fraction(value[0], value[1])
    raise ValueError(f"{field} must be an exact rational")


def _fraction_json(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _require_fields(value: Mapping[str, Any], fields: set[str], label: str) -> None:
    if set(value) != fields:
        missing = sorted(fields - set(value))
        extra = sorted(set(value) - fields)
        raise ValueError(
            f"{label} field set mismatch; missing={missing!r}, extra={extra!r}"
        )


def _require_opaque_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise ValueError(f"{field} must be an opaque content ID")
    return value


def _require_port_id(value: Any, field: str) -> str:
    """Require a cell-level proof-node handle, never a ground-state handle."""

    port_id = _require_opaque_id(value, field)
    if not port_id.startswith("proof-node-"):
        raise ValueError(f"{field} must identify an abstract proof-node cell")
    return port_id


def _positive_cap(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class SparseAffineForm:
    constant: Fraction
    terms: tuple[tuple[str, Fraction], ...]
    form_id: str

    @classmethod
    def create(
        cls,
        constant: Fraction,
        terms: Mapping[str, Fraction] | Iterable[tuple[str, Fraction]],
    ) -> "SparseAffineForm":
        source = dict(terms)
        ordered = tuple(
            (port_id, coefficient)
            for port_id, coefficient in sorted(source.items())
            if coefficient != 0
        )
        if any(coefficient < 0 for _, coefficient in ordered):
            raise ValueError("sparse capability coefficients must be nonnegative")
        payload = {
            "constant": _fraction_json(Fraction(constant)),
            "terms": [
                {
                    "port_id": port_id,
                    "coefficient": _fraction_json(coefficient),
                }
                for port_id, coefficient in ordered
            ],
        }
        return cls(
            Fraction(constant),
            ordered,
            _logical_id("sparse-form", payload),
        )

    def evaluate(self, values: Mapping[str, Fraction]) -> Fraction:
        return self.constant + sum(
            (coefficient * values[port_id] for port_id, coefficient in self.terms),
            Fraction(0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_id": self.form_id,
            "constant": _fraction_json(self.constant),
            "terms": [
                {
                    "port_id": port_id,
                    "coefficient": _fraction_json(coefficient),
                }
                for port_id, coefficient in self.terms
            ],
        }


@dataclass(frozen=True, slots=True)
class SparseRobustAffineCapability:
    frontier_id: str
    reward_floor: Fraction
    failure_ceiling: Fraction
    input_ports: tuple[tuple[str, Fraction, Fraction], ...]
    exit_ports: tuple[tuple[str, Fraction, Fraction], ...]
    root_reward_forms: tuple[SparseAffineForm, ...]
    root_failure_forms: tuple[SparseAffineForm, ...]
    capability_id: str

    @property
    def input_port_ids(self) -> tuple[str, ...]:
        return tuple(item[0] for item in self.input_ports)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CAPABILITY_SCHEMA,
            "frontier_id": self.frontier_id,
            "reward_floor": _fraction_json(self.reward_floor),
            "failure_ceiling": _fraction_json(self.failure_ceiling),
            "input_ports": [
                {
                    "port_id": port_id,
                    "default_reward_lower": _fraction_json(reward),
                    "default_failure_upper": _fraction_json(failure),
                }
                for port_id, reward, failure in self.input_ports
            ],
            "exit_ports": [
                {
                    "port_id": port_id,
                    "reward_lower": _fraction_json(reward),
                    "failure_upper": _fraction_json(failure),
                }
                for port_id, reward, failure in self.exit_ports
            ],
            "root_reward_forms": [form.to_dict() for form in self.root_reward_forms],
            "root_failure_forms": [form.to_dict() for form in self.root_failure_forms],
            "capability_id": self.capability_id,
        }


@dataclass(frozen=True, slots=True)
class CapabilityEvaluation:
    root_reward_lower: Fraction
    root_failure_upper: Fraction
    reward_floor: Fraction
    failure_ceiling: Fraction

    @property
    def certified_value(self) -> bool:
        return self.root_reward_lower >= self.reward_floor

    @property
    def certified_safe(self) -> bool:
        return self.root_failure_upper <= self.failure_ceiling

    @property
    def certified(self) -> bool:
        return self.certified_value and self.certified_safe


@dataclass(frozen=True, slots=True)
class CapabilityCompilation:
    capability: SparseRobustAffineCapability
    evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SparseRecoveryInputs:
    """Trusted compilation result mounted into one isolated worker request."""

    sparse_slice: dict[str, Any]
    compilation: CapabilityCompilation


def _parse_form(
    value: Any,
    *,
    input_port_ids: set[str],
    field: str,
) -> SparseAffineForm:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    _require_fields(value, {"form_id", "constant", "terms"}, field)
    raw_terms = value["terms"]
    if not isinstance(raw_terms, list):
        raise ValueError(f"{field}.terms must be a list")
    terms: list[tuple[str, Fraction]] = []
    for index, raw in enumerate(raw_terms):
        if not isinstance(raw, Mapping):
            raise ValueError(f"{field}.terms[{index}] must be an object")
        _require_fields(raw, {"port_id", "coefficient"}, f"{field}.terms[{index}]")
        port_id = _require_port_id(raw["port_id"], f"{field}.terms[{index}].port_id")
        if port_id not in input_port_ids:
            raise ValueError(f"{field} references an unknown/non-input port")
        coefficient = _fraction(
            raw["coefficient"], field=f"{field}.terms[{index}].coefficient"
        )
        if coefficient <= 0:
            raise ValueError("sparse form terms must have positive coefficients")
        terms.append((port_id, coefficient))
    if terms != sorted(terms) or len({port_id for port_id, _ in terms}) != len(terms):
        raise ValueError(f"{field}.terms must be uniquely sorted by port_id")
    form = SparseAffineForm.create(
        _fraction(value["constant"], field=f"{field}.constant"), terms
    )
    if value["form_id"] != form.form_id:
        raise ValueError(f"{field}.form_id does not bind its sparse form")
    return form


def parse_sparse_capability(document: Mapping[str, Any]) -> SparseRobustAffineCapability:
    """Strict worker-side parser for the minimal capability schema."""

    if not isinstance(document, Mapping):
        raise ValueError("sparse capability must be an object")
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
    _require_fields(document, fields, "sparse capability")
    if document["schema"] != CAPABILITY_SCHEMA:
        raise ValueError("unsupported sparse capability schema")
    frontier_id = _require_opaque_id(document["frontier_id"], "frontier_id")
    reward_floor = _fraction(document["reward_floor"], field="reward_floor")
    failure_ceiling = _fraction(document["failure_ceiling"], field="failure_ceiling")
    if failure_ceiling < 0 or failure_ceiling > 1:
        raise ValueError("failure_ceiling lies outside [0,1]")

    raw_inputs = document["input_ports"]
    raw_exits = document["exit_ports"]
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError("input_ports must be a nonempty list")
    if not isinstance(raw_exits, list):
        raise ValueError("exit_ports must be a list")
    inputs: list[tuple[str, Fraction, Fraction]] = []
    for index, raw in enumerate(raw_inputs):
        if not isinstance(raw, Mapping):
            raise ValueError("input port rows must be objects")
        _require_fields(
            raw,
            {"port_id", "default_reward_lower", "default_failure_upper"},
            f"input_ports[{index}]",
        )
        port_id = _require_port_id(raw["port_id"], f"input_ports[{index}].port_id")
        failure = _fraction(
            raw["default_failure_upper"],
            field=f"input_ports[{index}].default_failure_upper",
        )
        if failure < 0 or failure > 1:
            raise ValueError("default_failure_upper lies outside [0,1]")
        inputs.append(
            (
                port_id,
                _fraction(
                    raw["default_reward_lower"],
                    field=f"input_ports[{index}].default_reward_lower",
                ),
                failure,
            )
        )
    if inputs != sorted(inputs) or len({item[0] for item in inputs}) != len(inputs):
        raise ValueError("input_ports must be uniquely sorted by port_id")

    exits: list[tuple[str, Fraction, Fraction]] = []
    for index, raw in enumerate(raw_exits):
        if not isinstance(raw, Mapping):
            raise ValueError("exit port rows must be objects")
        _require_fields(
            raw,
            {"port_id", "reward_lower", "failure_upper"},
            f"exit_ports[{index}]",
        )
        port_id = _require_port_id(raw["port_id"], f"exit_ports[{index}].port_id")
        failure = _fraction(
            raw["failure_upper"], field=f"exit_ports[{index}].failure_upper"
        )
        if failure < 0 or failure > 1:
            raise ValueError("exit failure_upper lies outside [0,1]")
        exits.append(
            (
                port_id,
                _fraction(raw["reward_lower"], field=f"exit_ports[{index}].reward_lower"),
                failure,
            )
        )
    if exits != sorted(exits) or len({item[0] for item in exits}) != len(exits):
        raise ValueError("exit_ports must be uniquely sorted by port_id")
    if {item[0] for item in inputs} & {item[0] for item in exits}:
        raise ValueError("input and exit ports must be disjoint")

    input_ids = {item[0] for item in inputs}
    raw_reward_forms = document["root_reward_forms"]
    raw_failure_forms = document["root_failure_forms"]
    if not isinstance(raw_reward_forms, list) or not raw_reward_forms:
        raise ValueError("root_reward_forms must be nonempty")
    if not isinstance(raw_failure_forms, list) or not raw_failure_forms:
        raise ValueError("root_failure_forms must be nonempty")
    reward_forms = tuple(
        _parse_form(raw, input_port_ids=input_ids, field=f"root_reward_forms[{index}]")
        for index, raw in enumerate(raw_reward_forms)
    )
    failure_forms = tuple(
        _parse_form(raw, input_port_ids=input_ids, field=f"root_failure_forms[{index}]")
        for index, raw in enumerate(raw_failure_forms)
    )
    for name, forms in (("reward", reward_forms), ("failure", failure_forms)):
        ids = [form.form_id for form in forms]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError(f"root_{name}_forms must be uniquely sorted by form_id")

    payload = dict(document)
    capability_id = payload.pop("capability_id")
    expected_id = _logical_id("sparse-robust-affine-capability", payload)
    if capability_id != expected_id:
        raise ValueError("capability_id does not bind the capability")
    _require_opaque_id(capability_id, "capability_id")
    return SparseRobustAffineCapability(
        frontier_id,
        reward_floor,
        failure_ceiling,
        tuple(inputs),
        tuple(exits),
        reward_forms,
        failure_forms,
        capability_id,
    )


def evaluate_sparse_capability(
    capability: SparseRobustAffineCapability | Mapping[str, Any],
    localized_values: Mapping[str, tuple[Any, Any]] | None = None,
) -> CapabilityEvaluation:
    """Evaluate a complete global frontier assignment.

    ``localized_values`` overrides the default abstract pair for localized
    input ports.  Omitted ports remain abstract.  Reward and risk envelopes
    are evaluated independently, preserving the sound rectangular audit
    semantics required by a joint value-risk solver.
    """

    parsed = (
        capability
        if isinstance(capability, SparseRobustAffineCapability)
        else parse_sparse_capability(capability)
    )
    localized_values = {} if localized_values is None else localized_values
    unknown = set(localized_values) - set(parsed.input_port_ids)
    if unknown:
        raise ValueError(f"localized assignment contains unknown ports: {sorted(unknown)!r}")
    rewards = {port_id: reward for port_id, reward, _ in parsed.input_ports}
    failures = {port_id: failure for port_id, _, failure in parsed.input_ports}
    for port_id, raw_pair in localized_values.items():
        if not isinstance(raw_pair, (tuple, list)) or len(raw_pair) != 2:
            raise ValueError("localized port values must be exact (reward,risk) pairs")
        reward = _fraction(raw_pair[0], field=f"localized_values[{port_id}].reward")
        failure = _fraction(raw_pair[1], field=f"localized_values[{port_id}].failure")
        if failure < 0 or failure > 1:
            raise ValueError("localized failure lies outside [0,1]")
        rewards[port_id] = reward
        failures[port_id] = failure
    root_reward = min(form.evaluate(rewards) for form in parsed.root_reward_forms)
    root_failure = max(form.evaluate(failures) for form in parsed.root_failure_forms)
    if root_failure < 0 or root_failure > 1:
        raise ValueError("capability root failure lies outside [0,1]")
    return CapabilityEvaluation(
        root_reward,
        root_failure,
        parsed.reward_floor,
        parsed.failure_ceiling,
    )


# A symbolic channel is a lower/upper envelope of affine forms.  The same
# representation works for both channels; callers supply min versus max.
_Forms = tuple[SparseAffineForm, ...]


def _deduplicate(forms: Iterable[SparseAffineForm]) -> _Forms:
    by_payload: dict[tuple[Fraction, tuple[tuple[str, Fraction], ...]], SparseAffineForm] = {}
    for form in forms:
        by_payload[(form.constant, form.terms)] = form
    return tuple(sorted(by_payload.values(), key=lambda item: item.form_id))


def _scale(form: SparseAffineForm, scalar: Fraction) -> SparseAffineForm:
    return SparseAffineForm.create(
        scalar * form.constant,
        {port_id: scalar * coefficient for port_id, coefficient in form.terms},
    )


def _add(forms: Sequence[SparseAffineForm]) -> SparseAffineForm:
    constant = sum((form.constant for form in forms), Fraction(0))
    terms: dict[str, Fraction] = {}
    for form in forms:
        for port_id, coefficient in form.terms:
            terms[port_id] = terms.get(port_id, Fraction(0)) + coefficient
    return SparseAffineForm.create(constant, terms)


def _sum_envelopes(
    weighted: Sequence[tuple[Fraction, _Forms]],
    *,
    max_expanded_forms: int,
) -> _Forms:
    if not weighted:
        return (SparseAffineForm.create(Fraction(0), {}),)
    count = 1
    for _, forms in weighted:
        count *= len(forms)
        if count > max_expanded_forms:
            raise ValueError("sparse capability symbolic expansion cap exceeded")
    expanded = (
        _add(tuple(_scale(form, probability) for (probability, _), form in zip(weighted, combo)))
        for combo in itertools.product(*(forms for _, forms in weighted))
    )
    return _deduplicate(expanded)


def _source_nodes(boundary: Mapping[str, Any]) -> tuple[
    dict[str, list[dict[str, Any]]], tuple[tuple[str, Fraction], ...]
]:
    if boundary.get("schema") != SOURCE_SCHEMA:
        raise ValueError("trusted compiler requires redacted_boundary_view.v1")
    required = {
        "schema",
        "graph_id",
        "frontier_id",
        "delta",
        "unrestricted_reward_upper",
        "regret_tolerance",
        "roots",
        "nodes",
        "boundary_view_id",
    }
    _require_fields(boundary, required, "source boundary")
    payload = dict(boundary)
    source_id = payload.pop("boundary_view_id")
    # Existing v1 uses the project's truncated object ID.  Recompute it here
    # without importing trusted project code.
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    if source_id != f"redacted-boundary-view-{digest[:16]}":
        raise ValueError("source boundary_view_id does not bind its content")
    nodes: dict[str, list[dict[str, Any]]] = {}
    for index, raw in enumerate(boundary["nodes"]):
        if not isinstance(raw, Mapping):
            raise ValueError("source boundary nodes must be objects")
        _require_fields(
            raw,
            {"node_id", "cell", "remaining", "selected_action", "abstract_realizations"},
            f"source.nodes[{index}]",
        )
        node_id = _require_opaque_id(raw["node_id"], f"source.nodes[{index}].node_id")
        if node_id in nodes or not isinstance(raw["abstract_realizations"], list):
            raise ValueError("source boundary node IDs must be unique")
        rows: list[dict[str, Any]] = []
        for row_index, row in enumerate(raw["abstract_realizations"]):
            if not isinstance(row, Mapping):
                raise ValueError("source realization rows must be objects")
            _require_fields(
                row,
                {"realization_id", "immediate_reward", "failure_probability", "successors"},
                f"source.nodes[{index}].rows[{row_index}]",
            )
            successors: list[tuple[str, Fraction]] = []
            for successor in row["successors"]:
                if not isinstance(successor, Mapping):
                    raise ValueError("source successor rows must be objects")
                _require_fields(successor, {"node_id", "probability"}, "source successor")
                successors.append(
                    (
                        _require_opaque_id(successor["node_id"], "source successor node_id"),
                        _fraction(successor["probability"], field="source successor probability"),
                    )
                )
            rows.append(
                {
                    "reward": _fraction(row["immediate_reward"], field="source reward"),
                    "failure": _fraction(
                        row["failure_probability"], field="source failure"
                    ),
                    "successors": tuple(successors),
                }
            )
        if not rows:
            raise ValueError("source boundary nodes require realization rows")
        nodes[node_id] = rows
    roots: list[tuple[str, Fraction]] = []
    for raw in boundary["roots"]:
        if not isinstance(raw, Mapping):
            raise ValueError("source roots must be objects")
        _require_fields(raw, {"node_id", "probability"}, "source root")
        node_id = _require_opaque_id(raw["node_id"], "source root node_id")
        if node_id not in nodes:
            raise ValueError("source root is absent from the boundary graph")
        roots.append((node_id, _fraction(raw["probability"], field="root probability")))
    if sum((probability for _, probability in roots), Fraction(0)) != 1:
        raise ValueError("source root probabilities must sum to one")
    return nodes, tuple(roots)


def _symbolic_root_forms(
    nodes: Mapping[str, list[dict[str, Any]]],
    roots: Sequence[tuple[str, Fraction]],
    symbolic_ports: set[str],
    *,
    channel: str,
    max_expanded_forms: int,
) -> _Forms:
    memo: dict[str, _Forms] = {}
    active: set[str] = set()

    def visit(node_id: str) -> _Forms:
        if node_id in symbolic_ports:
            return (SparseAffineForm.create(Fraction(0), {node_id: Fraction(1)}),)
        if node_id in memo:
            return memo[node_id]
        if node_id in active:
            raise ValueError("source boundary dependency graph contains a cycle")
        try:
            rows = nodes[node_id]
        except KeyError as error:
            raise ValueError(f"source boundary omits successor {node_id!r}") from error
        active.add(node_id)
        row_forms: list[SparseAffineForm] = []
        for row in rows:
            weighted = [
                (probability, visit(successor))
                for successor, probability in row["successors"]
            ]
            continuation = _sum_envelopes(
                weighted, max_expanded_forms=max_expanded_forms
            )
            immediate = row["reward"] if channel == "reward" else row["failure"]
            row_forms.extend(
                _add((SparseAffineForm.create(immediate, {}), form))
                for form in continuation
            )
        active.remove(node_id)
        memo[node_id] = _deduplicate(row_forms)
        return memo[node_id]

    return _sum_envelopes(
        [(probability, visit(node_id)) for node_id, probability in roots],
        max_expanded_forms=max_expanded_forms,
    )


def _point_bound(
    nodes: Mapping[str, list[dict[str, Any]]],
    node_id: str,
    *,
    channel: str,
    max_expanded_forms: int = 100_000,
) -> Fraction:
    forms = _symbolic_root_forms(
        nodes,
        ((node_id, Fraction(1)),),
        set(),
        channel=channel,
        max_expanded_forms=max_expanded_forms,
    )
    values = [form.constant for form in forms]
    return min(values) if channel == "reward" else max(values)


def _substitute_singletons(
    forms: _Forms, domains: Mapping[str, tuple[Fraction, ...]]
) -> _Forms:
    result: list[SparseAffineForm] = []
    for form in forms:
        constant = form.constant
        terms: dict[str, Fraction] = {}
        for port_id, coefficient in form.terms:
            values = domains[port_id]
            if len(values) == 1:
                constant += coefficient * values[0]
            else:
                terms[port_id] = coefficient
        result.append(SparseAffineForm.create(constant, terms))
    return _deduplicate(result)


def _domain_assignments(
    forms: _Forms,
    domains: Mapping[str, tuple[Fraction, ...]],
    *,
    max_assignments: int,
) -> tuple[dict[str, Fraction], ...]:
    ports = sorted({port_id for form in forms for port_id, _ in form.terms})
    count = 1
    for port_id in ports:
        count *= len(domains[port_id])
        if count > max_assignments:
            raise ValueError("capability admissible-domain assignment cap exceeded")
    return tuple(
        dict(zip(ports, values))
        for values in itertools.product(*(domains[port_id] for port_id in ports))
    ) or ({},)


def _minimum_form_cover(
    forms: _Forms,
    domains: Mapping[str, tuple[Fraction, ...]],
    *,
    operator: str,
    max_assignments: int,
    max_form_assignment_evaluations: int,
    max_subset_evaluations: int,
) -> tuple[_Forms, tuple[dict[str, Fraction], ...], int]:
    forms = _deduplicate(forms)
    assignments = _domain_assignments(forms, domains, max_assignments=max_assignments)
    form_assignment_evaluations = len(forms) * len(assignments)
    if form_assignment_evaluations > max_form_assignment_evaluations:
        raise ValueError(
            "sparse capability form-assignment evaluation cap exceeded"
        )
    extrema = []
    covers: list[set[int]] = [set() for _ in forms]
    for assignment_index, assignment in enumerate(assignments):
        values = [form.evaluate(assignment) for form in forms]
        target = min(values) if operator == "min" else max(values)
        extrema.append(target)
        for form_index, value in enumerate(values):
            if value == target:
                covers[form_index].add(assignment_index)
    universe = set(range(len(assignments)))
    chosen: tuple[int, ...] | None = None
    subset_evaluations = 0
    for cardinality in range(1, len(forms) + 1):
        for subset in itertools.combinations(range(len(forms)), cardinality):
            if subset_evaluations >= max_subset_evaluations:
                raise ValueError(
                    "sparse capability form-subset evaluation cap exceeded"
                )
            subset_evaluations += 1
            if set().union(*(covers[index] for index in subset)) == universe:
                chosen = subset
                break
        if chosen is not None:
            break
    if chosen is None:  # pragma: no cover - nonempty forms always cover their extrema
        raise AssertionError("failed to cover an affine envelope")
    selected = tuple(forms[index] for index in chosen)
    return (
        tuple(sorted(selected, key=lambda item: item.form_id)),
        assignments,
        subset_evaluations,
    )


def _assignment_json(assignment: Mapping[str, Fraction]) -> list[dict[str, Any]]:
    return [
        {"port_id": port_id, "value": _fraction_json(value)}
        for port_id, value in sorted(assignment.items())
    ]


def compile_sparse_capability(
    boundary_view: Mapping[str, Any],
    *,
    frontier_input_port_ids: Iterable[str],
    admissible_input_pairs: Mapping[str, Iterable[tuple[Any, Any]]],
    target_frontier_id: str | None = None,
    abstract_exit_port_ids: Iterable[str] = (),
    exit_usage_witnesses: Mapping[str, Sequence[str]] | None = None,
    max_admissible_pair_rows: int = 100_000,
    max_expanded_forms: int = 100_000,
    max_domain_assignments: int = 100_000,
    max_form_assignment_evaluations: int = 1_000_000,
    max_form_subset_evaluations: int = 100_000,
) -> CapabilityCompilation:
    """Compile a full selected-policy boundary into a minimal worker capability.

    ``admissible_input_pairs`` is trusted-side evidence derived from the
    authorized slice's complete deterministic robust cell frontier.  The
    compiler always adds the certified abstract default pair.  Ports absent
    from ``frontier_input_port_ids`` remain abstract and are folded into the
    root transfer; this is how a slack/causal analysis can shrink the original
    DirectBad frontier before granting worker authority.
    """

    max_admissible_pair_rows = _positive_cap(
        max_admissible_pair_rows, "max_admissible_pair_rows"
    )
    max_expanded_forms = _positive_cap(max_expanded_forms, "max_expanded_forms")
    max_domain_assignments = _positive_cap(
        max_domain_assignments, "max_domain_assignments"
    )
    max_form_subset_evaluations = _positive_cap(
        max_form_subset_evaluations, "max_form_subset_evaluations"
    )
    max_form_assignment_evaluations = _positive_cap(
        max_form_assignment_evaluations, "max_form_assignment_evaluations"
    )
    exit_usage_witnesses = (
        {} if exit_usage_witnesses is None else exit_usage_witnesses
    )
    nodes, roots = _source_nodes(boundary_view)
    source_frontier_id = _require_opaque_id(
        boundary_view["frontier_id"], "source frontier_id"
    )
    selected_frontier_id = (
        source_frontier_id
        if target_frontier_id is None
        else _require_opaque_id(target_frontier_id, "target_frontier_id")
    )
    declared_ports = tuple(sorted(set(frontier_input_port_ids)))
    if not declared_ports:
        raise ValueError("at least one causal frontier input port is required")
    for port_id in declared_ports:
        _require_port_id(port_id, "frontier input port")
        if port_id not in nodes:
            raise ValueError("frontier input port is absent from the source boundary")
    if set(admissible_input_pairs) != set(declared_ports):
        raise ValueError("admissible_input_pairs must exactly cover declared input ports")

    default_pairs = {
        port_id: (
            _point_bound(
                nodes,
                port_id,
                channel="reward",
                max_expanded_forms=max_expanded_forms,
            ),
            _point_bound(
                nodes,
                port_id,
                channel="failure",
                max_expanded_forms=max_expanded_forms,
            ),
        )
        for port_id in declared_ports
    }
    pair_domains: dict[str, tuple[tuple[Fraction, Fraction], ...]] = {}
    admissible_pair_rows = 0
    for port_id in declared_ports:
        pairs = {default_pairs[port_id]}
        for index, raw_pair in enumerate(admissible_input_pairs[port_id]):
            admissible_pair_rows += 1
            if admissible_pair_rows > max_admissible_pair_rows:
                raise ValueError("sparse capability admissible-pair row cap exceeded")
            if not isinstance(raw_pair, (tuple, list)) or len(raw_pair) != 2:
                raise ValueError("admissible input values must be (reward,risk) pairs")
            pair = (
                _fraction(raw_pair[0], field=f"admissible[{port_id}][{index}].reward"),
                _fraction(raw_pair[1], field=f"admissible[{port_id}][{index}].failure"),
            )
            if pair[1] < 0 or pair[1] > 1:
                raise ValueError("admissible failure lies outside [0,1]")
            pairs.add(pair)
        pair_domains[port_id] = tuple(sorted(pairs))

    reward_domains = {
        port_id: tuple(sorted({pair[0] for pair in pairs}))
        for port_id, pairs in pair_domains.items()
    }
    failure_domains = {
        port_id: tuple(sorted({pair[1] for pair in pairs}))
        for port_id, pairs in pair_domains.items()
    }
    source_reward_forms = _symbolic_root_forms(
        nodes,
        roots,
        set(declared_ports),
        channel="reward",
        max_expanded_forms=max_expanded_forms,
    )
    source_failure_forms = _symbolic_root_forms(
        nodes,
        roots,
        set(declared_ports),
        channel="failure",
        max_expanded_forms=max_expanded_forms,
    )
    folded_reward = _substitute_singletons(source_reward_forms, reward_domains)
    folded_failure = _substitute_singletons(source_failure_forms, failure_domains)
    reward_forms, reward_assignments, reward_subset_evaluations = _minimum_form_cover(
        folded_reward,
        reward_domains,
        operator="min",
        max_assignments=max_domain_assignments,
        max_form_assignment_evaluations=max_form_assignment_evaluations,
        max_subset_evaluations=max_form_subset_evaluations,
    )
    failure_forms, failure_assignments, failure_subset_evaluations = _minimum_form_cover(
        folded_failure,
        failure_domains,
        operator="max",
        max_assignments=max_domain_assignments,
        max_form_assignment_evaluations=max_form_assignment_evaluations,
        max_subset_evaluations=max_form_subset_evaluations,
    )

    used_ports = {
        port_id
        for form in (*reward_forms, *failure_forms)
        for port_id, _ in form.terms
    }
    input_ports = tuple(
        (port_id, *default_pairs[port_id])
        for port_id in declared_ports
        if port_id in used_ports
    )
    if not input_ports:
        raise ValueError("all declared input ports constant-folded; worker recovery is unnecessary")

    exit_ids = tuple(sorted(set(abstract_exit_port_ids)))
    exits: list[tuple[str, Fraction, Fraction]] = []
    exit_witness_records: list[dict[str, Any]] = []
    for port_id in exit_ids:
        _require_port_id(port_id, "abstract exit port")
        if port_id in used_ports or port_id not in nodes:
            raise ValueError("abstract exit ports must be disjoint source boundary nodes")
        witnesses = tuple(sorted(set(exit_usage_witnesses.get(port_id, ()))))
        if not witnesses:
            raise ValueError("every abstract exit port requires a trusted usage witness")
        exits.append(
            (
                port_id,
                _point_bound(
                    nodes,
                    port_id,
                    channel="reward",
                    max_expanded_forms=max_expanded_forms,
                ),
                _point_bound(
                    nodes,
                    port_id,
                    channel="failure",
                    max_expanded_forms=max_expanded_forms,
                ),
            )
        )
        exit_witness_records.append(
            {"port_id": port_id, "authorized_slice_branch_ids": list(witnesses)}
        )
    if set(exit_usage_witnesses) - set(exit_ids):
        raise ValueError("exit usage witnesses name undeclared exit ports")

    reward_floor = _fraction(
        boundary_view["unrestricted_reward_upper"], field="unrestricted reward upper"
    ) - _fraction(boundary_view["regret_tolerance"], field="regret tolerance")
    failure_ceiling = _fraction(boundary_view["delta"], field="delta")
    payload = {
        "schema": CAPABILITY_SCHEMA,
        "frontier_id": selected_frontier_id,
        "reward_floor": _fraction_json(reward_floor),
        "failure_ceiling": _fraction_json(failure_ceiling),
        "input_ports": [
            {
                "port_id": port_id,
                "default_reward_lower": _fraction_json(reward),
                "default_failure_upper": _fraction_json(failure),
            }
            for port_id, reward, failure in input_ports
        ],
        "exit_ports": [
            {
                "port_id": port_id,
                "reward_lower": _fraction_json(reward),
                "failure_upper": _fraction_json(failure),
            }
            for port_id, reward, failure in exits
        ],
        "root_reward_forms": [form.to_dict() for form in reward_forms],
        "root_failure_forms": [form.to_dict() for form in failure_forms],
    }
    payload["capability_id"] = _logical_id(
        "sparse-robust-affine-capability", payload
    )
    capability = parse_sparse_capability(payload)

    def equivalence_cases(
        source_forms: _Forms,
        compiled_forms: _Forms,
        assignments: Sequence[Mapping[str, Fraction]],
        *,
        operator: str,
        domains: Mapping[str, tuple[Fraction, ...]],
    ) -> list[dict[str, Any]]:
        records = []
        for assignment in assignments:
            # Reinsert singleton coordinates for the un-folded source forms.
            full_assignment = dict(assignment)
            for port_id, values in domains.items():
                if len(values) == 1:
                    full_assignment[port_id] = values[0]
            source_values = [form.evaluate(full_assignment) for form in source_forms]
            compiled_values = [form.evaluate(assignment) for form in compiled_forms]
            source_value = (
                min(source_values) if operator == "min" else max(source_values)
            )
            compiled_value = (
                min(compiled_values) if operator == "min" else max(compiled_values)
            )
            if source_value != compiled_value:
                raise ValueError("compiled sparse capability is not extensionally sufficient")
            records.append(
                {
                    "assignment": _assignment_json(full_assignment),
                    "source_value": _fraction_json(source_value),
                    "capability_value": _fraction_json(compiled_value),
                }
            )
        return records

    reward_equivalence_evaluations = (
        len(source_reward_forms) + len(reward_forms)
    ) * len(reward_assignments)
    failure_equivalence_evaluations = (
        len(source_failure_forms) + len(failure_forms)
    ) * len(failure_assignments)
    if max(
        reward_equivalence_evaluations,
        failure_equivalence_evaluations,
    ) > max_form_assignment_evaluations:
        raise ValueError("sparse capability equivalence evaluation cap exceeded")
    reward_cases = equivalence_cases(
        source_reward_forms,
        reward_forms,
        reward_assignments,
        operator="min",
        domains=reward_domains,
    )
    failure_cases = equivalence_cases(
        source_failure_forms,
        failure_forms,
        failure_assignments,
        operator="max",
        domains=failure_domains,
    )

    form_witnesses: list[dict[str, Any]] = []
    form_witness_evaluations = 0
    for channel, forms, assignments, operator in (
        ("reward", reward_forms, reward_assignments, "min"),
        ("failure", failure_forms, failure_assignments, "max"),
    ):
        for form in forms:
            witness: dict[str, Fraction] | None = None
            for assignment in assignments:
                form_witness_evaluations += len(forms) + max(len(forms) - 1, 0) + 1
                if form_witness_evaluations > max_form_assignment_evaluations:
                    raise ValueError(
                        "sparse capability form-witness evaluation cap exceeded"
                    )
                values = [candidate.evaluate(assignment) for candidate in forms]
                target = min(values) if operator == "min" else max(values)
                without = [
                    candidate.evaluate(assignment)
                    for candidate in forms
                    if candidate.form_id != form.form_id
                ]
                if not without:
                    witness = dict(assignment)
                    break
                alternative = min(without) if operator == "min" else max(without)
                if form.evaluate(assignment) == target and alternative != target:
                    witness = dict(assignment)
                    break
            if witness is None:
                raise ValueError("retained affine form lacks a necessity witness")
            form_witnesses.append(
                {
                    "channel": channel,
                    "form_id": form.form_id,
                    "assignment": _assignment_json(witness),
                    "deletion_changes_output": True,
                }
            )

    port_witnesses: list[dict[str, Any]] = []
    port_pair_evaluations = 0
    port_context_evaluations = 0
    for port_id, _, _ in input_ports:
        witness = None
        pairs = pair_domains[port_id]
        other_ids = tuple(
            other_id
            for other_id, _, _ in input_ports
            if other_id != port_id
        )
        context_count = 1
        for other_id in other_ids:
            context_count *= len(pair_domains[other_id])
            if context_count > max_domain_assignments:
                raise ValueError(
                    "sparse capability input-port context assignment cap exceeded"
                )
        contexts = itertools.product(*(pair_domains[other_id] for other_id in other_ids))
        for context_values in contexts:
            port_context_evaluations += 1
            context = dict(zip(other_ids, context_values))
            for left, right in itertools.combinations(pairs, 2):
                port_pair_evaluations += 1
                if port_pair_evaluations > max_form_assignment_evaluations:
                    raise ValueError(
                        "sparse capability input-port pair evaluation cap exceeded"
                    )
                left_eval = evaluate_sparse_capability(
                    capability, {**context, port_id: left}
                )
                right_eval = evaluate_sparse_capability(
                    capability, {**context, port_id: right}
                )
                if (
                    left_eval.root_reward_lower != right_eval.root_reward_lower
                    or left_eval.root_failure_upper != right_eval.root_failure_upper
                ):
                    witness = (context, left, right, left_eval, right_eval)
                    break
            if witness is not None:
                break
        if witness is None:
            raise ValueError("retained input port lacks a necessity witness")
        context, left, right, left_eval, right_eval = witness
        port_witnesses.append(
            {
                "port_id": port_id,
                "fixed_context_pairs": [
                    {
                        "port_id": other_id,
                        "reward_lower": _fraction_json(pair[0]),
                        "failure_upper": _fraction_json(pair[1]),
                    }
                    for other_id, pair in sorted(context.items())
                ],
                "left_pair": {
                    "reward_lower": _fraction_json(left[0]),
                    "failure_upper": _fraction_json(left[1]),
                },
                "right_pair": {
                    "reward_lower": _fraction_json(right[0]),
                    "failure_upper": _fraction_json(right[1]),
                },
                "left_root": {
                    "reward_lower": _fraction_json(left_eval.root_reward_lower),
                    "failure_upper": _fraction_json(left_eval.root_failure_upper),
                },
                "right_root": {
                    "reward_lower": _fraction_json(right_eval.root_reward_lower),
                    "failure_upper": _fraction_json(right_eval.root_failure_upper),
                },
            }
        )

    worker_keys: set[str] = set()

    def collect_keys(value: Any) -> None:
        if isinstance(value, Mapping):
            worker_keys.update(str(key) for key in value)
            for child in value.values():
                collect_keys(child)
        elif isinstance(value, list):
            for child in value:
                collect_keys(child)

    collect_keys(capability.to_dict())
    forbidden_hits = sorted(worker_keys & _FORBIDDEN_WORKER_KEYS)
    if forbidden_hits:
        raise ValueError(f"worker capability leaked forbidden fields: {forbidden_hits!r}")

    evidence_payload = {
        "schema": EVIDENCE_SCHEMA,
        "source_boundary_view_id": boundary_view["boundary_view_id"],
        "source_graph_id": boundary_view["graph_id"],
        "source_frontier_id": source_frontier_id,
        "target_frontier_id": selected_frontier_id,
        "frontier_id": selected_frontier_id,
        "capability_id": capability.capability_id,
        "representation_class": "finite-domain-canonical-sparse-minmax-affine-v1",
        "source_node_count": len(nodes),
        "source_abstract_realization_row_count": sum(len(rows) for rows in nodes.values()),
        "declared_input_port_ids": list(declared_ports),
        "retained_input_port_ids": list(capability.input_port_ids),
        "dropped_constant_input_port_ids": sorted(set(declared_ports) - used_ports),
        "admissible_input_pairs": [
            {
                "port_id": port_id,
                "pairs": [
                    {
                        "reward_lower": _fraction_json(reward),
                        "failure_upper": _fraction_json(failure),
                    }
                    for reward, failure in pair_domains[port_id]
                ],
            }
            for port_id in declared_ports
        ],
        "source_reward_form_count": len(source_reward_forms),
        "source_failure_form_count": len(source_failure_forms),
        "retained_reward_form_count": len(reward_forms),
        "retained_failure_form_count": len(failure_forms),
        "enumeration": {
            "status": "COMPLETE",
            "limits": {
                "max_expanded_forms": max_expanded_forms,
                "max_domain_assignments": max_domain_assignments,
                "max_admissible_pair_rows": max_admissible_pair_rows,
                "max_form_assignment_evaluations": max_form_assignment_evaluations,
                "max_form_subset_evaluations": max_form_subset_evaluations,
            },
            "counts": {
                "reward_domain_assignments": len(reward_assignments),
                "failure_domain_assignments": len(failure_assignments),
                "admissible_pair_rows": admissible_pair_rows,
                "reward_form_assignment_evaluations": (
                    len(folded_reward) * len(reward_assignments)
                ),
                "failure_form_assignment_evaluations": (
                    len(folded_failure) * len(failure_assignments)
                ),
                "reward_equivalence_form_evaluations": (
                    reward_equivalence_evaluations
                ),
                "failure_equivalence_form_evaluations": (
                    failure_equivalence_evaluations
                ),
                "form_witness_evaluations": form_witness_evaluations,
                "input_port_context_evaluations": port_context_evaluations,
                "input_port_pair_evaluations": port_pair_evaluations,
                "reward_form_subset_evaluations": reward_subset_evaluations,
                "failure_form_subset_evaluations": failure_subset_evaluations,
            },
        },
        "reward_equivalence_cases": reward_cases,
        "failure_equivalence_cases": failure_cases,
        "form_necessity_witnesses": form_witnesses,
        "input_port_necessity_witnesses": port_witnesses,
        "exit_port_necessity_witnesses": exit_witness_records,
        "redaction": {
            "forbidden_worker_keys": sorted(_FORBIDDEN_WORKER_KEYS),
            "observed_forbidden_worker_keys": forbidden_hits,
            "source_rows_mounted_to_worker": False,
        },
    }
    evidence_payload["evidence_id"] = _logical_id(
        "sparse-capability-evidence", evidence_payload
    )
    return CapabilityCompilation(capability, evidence_payload)


def _parse_v1_authorized_slice(
    document: Mapping[str, Any],
    *,
    target_frontier_id: str,
    max_slice_cells: int,
    max_slice_members: int,
    max_slice_actions: int,
    max_slice_successor_rows: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Strictly validate the trusted redacted v1 slice before translation."""

    if not isinstance(document, Mapping):
        raise ValueError("redacted v1 authorized slice must be an object")
    _require_fields(
        document,
        {"schema", "frontier_id", "authorization_id", "cells", "slice_id"},
        "redacted v1 authorized slice",
    )
    if document["schema"] != V1_SLICE_SCHEMA:
        raise ValueError("trusted recovery-input compiler requires authorized_ground_slice.v1")
    source_slice_frontier = _require_opaque_id(
        document["frontier_id"], "authorized slice frontier_id"
    )
    if source_slice_frontier != target_frontier_id:
        raise ValueError("authorized slice and target_frontier_id mismatch")
    _require_opaque_id(document["authorization_id"], "authorization_id")
    payload = dict(document)
    slice_id = payload.pop("slice_id")
    if slice_id != _object_id("authorized-ground-slice", payload):
        raise ValueError("authorized v1 slice_id does not bind its content")

    raw_cells = document["cells"]
    if not isinstance(raw_cells, list) or not raw_cells:
        raise ValueError("authorized v1 slice cells must be a nonempty list")
    if len(raw_cells) > max_slice_cells:
        raise ValueError("sparse recovery slice-cell cap exceeded")
    cells: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    member_count = 0
    action_count = 0
    successor_count = 0
    state_times: set[tuple[int, str]] = set()
    for cell_index, raw_cell in enumerate(raw_cells):
        if not isinstance(raw_cell, Mapping):
            raise ValueError("authorized v1 slice cell rows must be objects")
        _require_fields(
            raw_cell,
            {"node_id", "cell", "remaining", "members"},
            f"authorized slice cells[{cell_index}]",
        )
        node_id = _require_port_id(
            raw_cell["node_id"], f"authorized slice cells[{cell_index}].node_id"
        )
        if node_id in node_ids:
            raise ValueError("authorized v1 slice cell node IDs must be unique")
        node_ids.add(node_id)
        remaining = raw_cell["remaining"]
        if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining <= 0:
            raise ValueError("authorized v1 slice remaining must be a positive integer")
        if not isinstance(raw_cell["cell"], str):
            raise ValueError("authorized v1 slice cell metadata must be a string")
        raw_members = raw_cell["members"]
        if not isinstance(raw_members, list) or not raw_members:
            raise ValueError("authorized v1 slice cells require active members")
        member_count += len(raw_members)
        if member_count > max_slice_members:
            raise ValueError("sparse recovery slice-member cap exceeded")
        members: list[dict[str, Any]] = []
        member_ids: set[str] = set()
        for member_index, raw_member in enumerate(raw_members):
            if not isinstance(raw_member, Mapping):
                raise ValueError("authorized v1 slice members must be objects")
            _require_fields(
                raw_member,
                {"state_id", "actions"},
                f"authorized slice member[{member_index}]",
            )
            state_id = _require_opaque_id(
                raw_member["state_id"], "authorized slice state_id"
            )
            if state_id in member_ids or (remaining, state_id) in state_times:
                raise ValueError("authorized v1 slice state-time decisions must be unique")
            member_ids.add(state_id)
            state_times.add((remaining, state_id))
            raw_actions = raw_member["actions"]
            if not isinstance(raw_actions, list) or not raw_actions:
                raise ValueError("authorized v1 slice members require actions")
            action_count += len(raw_actions)
            if action_count > max_slice_actions:
                raise ValueError("sparse recovery slice-action cap exceeded")
            actions: list[dict[str, Any]] = []
            action_ids: set[str] = set()
            for action_index, raw_action in enumerate(raw_actions):
                if not isinstance(raw_action, Mapping):
                    raise ValueError("authorized v1 slice actions must be objects")
                _require_fields(
                    raw_action,
                    {
                        "action_id",
                        "immediate_reward",
                        "failure_probability",
                        "termination_probability",
                        "successors",
                    },
                    f"authorized slice action[{action_index}]",
                )
                action_id = _require_opaque_id(
                    raw_action["action_id"], "authorized slice action_id"
                )
                if action_id in action_ids:
                    raise ValueError("authorized v1 action IDs must be unique per state")
                action_ids.add(action_id)
                immediate_reward = _fraction(
                    raw_action["immediate_reward"], field="slice immediate_reward"
                )
                immediate_failure = _fraction(
                    raw_action["failure_probability"], field="slice failure_probability"
                )
                termination = _fraction(
                    raw_action["termination_probability"],
                    field="slice termination_probability",
                )
                if not 0 <= immediate_failure <= termination <= 1:
                    raise ValueError("authorized v1 action failure/termination mass is invalid")
                raw_successors = raw_action["successors"]
                if not isinstance(raw_successors, list):
                    raise ValueError("authorized v1 action successors must be a list")
                successor_count += len(raw_successors)
                if successor_count > max_slice_successor_rows:
                    raise ValueError("sparse recovery slice-successor cap exceeded")
                successors: list[tuple[str, Fraction]] = []
                successor_ids: set[str] = set()
                for raw_successor in raw_successors:
                    if not isinstance(raw_successor, Mapping):
                        raise ValueError("authorized v1 successor rows must be objects")
                    _require_fields(
                        raw_successor,
                        {"node_id", "probability"},
                        "authorized v1 successor",
                    )
                    successor_id = _require_port_id(
                        raw_successor["node_id"], "authorized v1 successor node_id"
                    )
                    if successor_id in successor_ids:
                        raise ValueError("authorized v1 action successor IDs must be unique")
                    successor_ids.add(successor_id)
                    probability = _fraction(
                        raw_successor["probability"],
                        field="authorized v1 successor probability",
                    )
                    if probability <= 0 or probability > 1:
                        raise ValueError("authorized v1 successor probability lies outside (0,1]")
                    successors.append((successor_id, probability))
                if termination + sum(
                    (probability for _, probability in successors), Fraction(0)
                ) != 1:
                    raise ValueError(
                        "authorized v1 termination plus successor mass must equal one"
                    )
                actions.append(
                    {
                        "action_id": action_id,
                        "immediate_reward": immediate_reward,
                        "failure_probability": immediate_failure,
                        "termination_probability": termination,
                        "successors": tuple(sorted(successors)),
                    }
                )
            members.append(
                {
                    "state_id": state_id,
                    "actions": tuple(
                        sorted(actions, key=lambda item: item["action_id"])
                    ),
                }
            )
        cells.append(
            {
                "node_id": node_id,
                "cell": raw_cell["cell"],
                "remaining": remaining,
                "members": tuple(
                    sorted(members, key=lambda item: item["state_id"])
                ),
            }
        )
    cells.sort(key=lambda item: (-item["remaining"], item["node_id"]))
    return cells, {
        "slice_cells": len(cells),
        "slice_members": member_count,
        "slice_actions": action_count,
        "slice_successor_rows": successor_count,
    }


def compile_sparse_recovery_inputs(
    boundary_view: Mapping[str, Any],
    redacted_v1_slice: Mapping[str, Any],
    *,
    target_frontier_id: str,
    max_slice_cells: int = 1_000,
    max_slice_members: int = 100_000,
    max_slice_actions: int = 1_000_000,
    max_slice_successor_rows: int = 1_000_000,
    max_cell_policy_assignments: int = 100_000,
    max_expanded_forms: int = 100_000,
    max_domain_assignments: int = 100_000,
    max_form_assignment_evaluations: int = 1_000_000,
    max_form_subset_evaluations: int = 100_000,
) -> SparseRecoveryInputs:
    """Build the complete minimal worker handoff from trusted v1 artifacts.

    Every local successor is replaced by an abstract scalar exit port.  For
    each authorized cell the compiler completely enumerates deterministic
    choices (one action per active member) and derives the exact robust
    ``(min reward, max failure)`` domain consumed by capability minimization.
    No incomplete enumeration is returned: every cap hit raises explicitly.
    """

    target_frontier_id = _require_opaque_id(
        target_frontier_id, "target_frontier_id"
    )
    limits = {
        "max_slice_cells": _positive_cap(max_slice_cells, "max_slice_cells"),
        "max_slice_members": _positive_cap(max_slice_members, "max_slice_members"),
        "max_slice_actions": _positive_cap(max_slice_actions, "max_slice_actions"),
        "max_slice_successor_rows": _positive_cap(
            max_slice_successor_rows, "max_slice_successor_rows"
        ),
        "max_cell_policy_assignments": _positive_cap(
            max_cell_policy_assignments, "max_cell_policy_assignments"
        ),
        "max_expanded_forms": _positive_cap(
            max_expanded_forms, "max_expanded_forms"
        ),
        "max_domain_assignments": _positive_cap(
            max_domain_assignments, "max_domain_assignments"
        ),
        "max_form_assignment_evaluations": _positive_cap(
            max_form_assignment_evaluations,
            "max_form_assignment_evaluations",
        ),
        "max_form_subset_evaluations": _positive_cap(
            max_form_subset_evaluations, "max_form_subset_evaluations"
        ),
    }
    nodes, _ = _source_nodes(boundary_view)
    cells, counts = _parse_v1_authorized_slice(
        redacted_v1_slice,
        target_frontier_id=target_frontier_id,
        max_slice_cells=limits["max_slice_cells"],
        max_slice_members=limits["max_slice_members"],
        max_slice_actions=limits["max_slice_actions"],
        max_slice_successor_rows=limits["max_slice_successor_rows"],
    )
    expected_target = _object_id(
        "failed-proof-frontier",
        {
            "graph_id": boundary_view["graph_id"],
            "node_ids": tuple(
                cell["node_id"]
                for cell in sorted(
                    cells,
                    key=lambda item: (
                        -item["remaining"],
                        item["cell"],
                        item["node_id"],
                    ),
                )
            ),
        },
    )
    if target_frontier_id != expected_target:
        raise ValueError("target_frontier_id does not bind the authorized cell set")
    cell_ids = {cell["node_id"] for cell in cells}
    absent_cells = cell_ids - set(nodes)
    if absent_cells:
        raise ValueError(
            f"authorized slice cells are absent from source boundary: {sorted(absent_cells)!r}"
        )

    exit_ids = {
        successor_id
        for cell in cells
        for member in cell["members"]
        for action in member["actions"]
        for successor_id, _ in action["successors"]
    }
    internal = exit_ids & cell_ids
    if internal:
        raise ValueError(
            "sparse v1 translation does not permit local-cell successor dependencies; "
            f"found {sorted(internal)!r}"
        )
    missing_exits = exit_ids - set(nodes)
    if missing_exits:
        raise ValueError(
            f"authorized slice successors lack abstract boundary values: {sorted(missing_exits)!r}"
        )
    exit_bounds = {
        port_id: (
            _point_bound(
                nodes,
                port_id,
                channel="reward",
                max_expanded_forms=limits["max_expanded_forms"],
            ),
            _point_bound(
                nodes,
                port_id,
                channel="failure",
                max_expanded_forms=limits["max_expanded_forms"],
            ),
        )
        for port_id in sorted(exit_ids)
    }

    admissible: dict[str, set[tuple[Fraction, Fraction]]] = {}
    assignment_records: list[dict[str, Any]] = []
    total_assignments = 0
    for cell in cells:
        action_sets = tuple(member["actions"] for member in cell["members"])
        assignment_count = 1
        for actions in action_sets:
            assignment_count *= len(actions)
            if total_assignments + assignment_count > limits["max_cell_policy_assignments"]:
                raise ValueError("sparse recovery cell-policy assignment cap exceeded")
        total_assignments += assignment_count
        pairs: set[tuple[Fraction, Fraction]] = set()
        for assignment in itertools.product(*action_sets):
            member_values: list[tuple[Fraction, Fraction]] = []
            for action in assignment:
                reward = action["immediate_reward"]
                failure = action["failure_probability"]
                for exit_port_id, probability in action["successors"]:
                    exit_reward, exit_failure = exit_bounds[exit_port_id]
                    reward += probability * exit_reward
                    failure += probability * exit_failure
                if failure < 0 or failure > 1:
                    raise ValueError("scalarized local action failure lies outside [0,1]")
                member_values.append((reward, failure))
            pairs.add(
                (
                    min(value[0] for value in member_values),
                    max(value[1] for value in member_values),
                )
            )
        admissible[cell["node_id"]] = pairs
        assignment_records.append(
            {
                "port_id": cell["node_id"],
                "deterministic_assignment_count": assignment_count,
                "distinct_robust_pair_count": len(pairs),
            }
        )

    usage_records: dict[str, list[tuple[str, str]]] = {
        port_id: [] for port_id in exit_ids
    }
    for cell in cells:
        for member in cell["members"]:
            for action in member["actions"]:
                for exit_port_id, _ in action["successors"]:
                    usage_records[exit_port_id].append(
                        (
                            cell["node_id"],
                            _logical_id(
                                "slice-branch",
                                {
                                    "cell_node_id": cell["node_id"],
                                    "state_id": member["state_id"],
                                    "action_id": action["action_id"],
                                    "exit_port_id": exit_port_id,
                                },
                            ),
                        )
                    )
    usage = {
        port_id: tuple(sorted(witness for _, witness in records))
        for port_id, records in sorted(usage_records.items())
    }

    compile_args = {
        "target_frontier_id": target_frontier_id,
        "max_admissible_pair_rows": limits["max_cell_policy_assignments"],
        "max_expanded_forms": limits["max_expanded_forms"],
        "max_domain_assignments": limits["max_domain_assignments"],
        "max_form_assignment_evaluations": limits[
            "max_form_assignment_evaluations"
        ],
        "max_form_subset_evaluations": limits["max_form_subset_evaluations"],
    }
    compilation = compile_sparse_capability(
        boundary_view,
        frontier_input_port_ids=tuple(sorted(cell_ids)),
        admissible_input_pairs=admissible,
        abstract_exit_port_ids=tuple(sorted(exit_ids)),
        exit_usage_witnesses=usage,
        **compile_args,
    )
    retained_ids = set(compilation.capability.input_port_ids)
    retained_cells = [cell for cell in cells if cell["node_id"] in retained_ids]
    retained_exit_ids = {
        successor_id
        for cell in retained_cells
        for member in cell["members"]
        for action in member["actions"]
        for successor_id, _ in action["successors"]
    }
    compiler_passes = 1
    if retained_exit_ids != exit_ids:
        compiler_passes = 2
        compilation = compile_sparse_capability(
            boundary_view,
            frontier_input_port_ids=tuple(sorted(cell_ids)),
            admissible_input_pairs=admissible,
            abstract_exit_port_ids=tuple(sorted(retained_exit_ids)),
            exit_usage_witnesses={
                port_id: tuple(
                    sorted(
                        witness
                        for cell_id, witness in usage_records[port_id]
                        if cell_id in retained_ids
                    )
                )
                for port_id in sorted(retained_exit_ids)
            },
            **compile_args,
        )
        retained_ids = set(compilation.capability.input_port_ids)
        retained_cells = [cell for cell in cells if cell["node_id"] in retained_ids]

    sparse_cells: list[dict[str, Any]] = []
    for cell in sorted(retained_cells, key=lambda item: item["node_id"]):
        sparse_cells.append(
            {
                "node_id": cell["node_id"],
                "cell": cell["cell"],
                "remaining": cell["remaining"],
                "input_port_id": cell["node_id"],
                "members": [
                    {
                        "state_id": member["state_id"],
                        "actions": [
                            {
                                "action_id": action["action_id"],
                                "immediate_reward": _fraction_json(
                                    action["immediate_reward"]
                                ),
                                "failure_probability": _fraction_json(
                                    action["failure_probability"]
                                ),
                                "termination_probability": _fraction_json(
                                    action["termination_probability"]
                                ),
                                "exits": [
                                    {
                                        "exit_port_id": successor_id,
                                        "probability": _fraction_json(probability),
                                    }
                                    for successor_id, probability in action["successors"]
                                ],
                            }
                            for action in member["actions"]
                        ],
                    }
                    for member in cell["members"]
                ],
            }
        )
    sparse_payload = {
        "schema": SPARSE_SLICE_SCHEMA,
        "authorization_id": redacted_v1_slice["authorization_id"],
        "frontier_id": target_frontier_id,
        "cells": sparse_cells,
    }
    sparse_payload["slice_id"] = _object_id(
        "sparse-frontier-ground-slice", sparse_payload
    )

    evidence = dict(compilation.evidence)
    evidence.pop("evidence_id")
    evidence["recovery_input_compilation"] = {
        "status": "COMPLETE",
        "source_authorized_slice_id": redacted_v1_slice["slice_id"],
        "sparse_slice_id": sparse_payload["slice_id"],
        "target_frontier_id": target_frontier_id,
        "limits": limits,
        "counts": {
            **counts,
            "cell_policy_assignments": total_assignments,
            "distinct_scalar_exit_ports": len(retained_exit_ids),
            "retained_slice_cells": len(retained_cells),
            "capability_compiler_passes": compiler_passes,
        },
        "cell_assignment_counts": assignment_records,
        "successor_translation": "abstract_node_to_scalar_exit_port",
        "enumeration_complete": True,
    }
    evidence["evidence_id"] = _logical_id("sparse-capability-evidence", evidence)
    final_compilation = CapabilityCompilation(compilation.capability, evidence)
    return SparseRecoveryInputs(sparse_payload, final_compilation)


def capability_exit_bounds(
    capability: SparseRobustAffineCapability | Mapping[str, Any],
) -> dict[str, tuple[Fraction, Fraction]]:
    """Return the scalar handoff map consumed by local-slice successor exits."""

    parsed = (
        capability
        if isinstance(capability, SparseRobustAffineCapability)
        else parse_sparse_capability(capability)
    )
    return {
        port_id: (reward, failure)
        for port_id, reward, failure in parsed.exit_ports
    }


__all__ = [
    "CAPABILITY_SCHEMA",
    "EVIDENCE_SCHEMA",
    "SPARSE_SLICE_SCHEMA",
    "CapabilityCompilation",
    "CapabilityEvaluation",
    "SparseAffineForm",
    "SparseRecoveryInputs",
    "SparseRobustAffineCapability",
    "capability_exit_bounds",
    "compile_sparse_capability",
    "compile_sparse_recovery_inputs",
    "evaluate_sparse_capability",
    "parse_sparse_capability",
]
