"""Pure-stdlib solver for a redacted local-recovery transaction.

The module intentionally imports no ACFQP package code.  It can therefore be
copied next to three canonical JSON inputs and executed in a fresh interpreter.
Its only authority is the occurrence-bound request, finite abstract boundary
view, and authorized ground slice serialized by :mod:`acfqp.local_recovery`.

The solver enumerates frontier-cell subsets by cardinality.  For each proposed
localized cell it chooses, independently for every member state, a
deterministic Pareto action using the normative order: minimum exact failure,
maximum exact reward, then action ID.  A subset is accepted only when the
hybrid worst-case recursion proves both the root risk and value-regret bounds.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import itertools
import json
from typing import Any, Mapping, Sequence


BOUNDARY_SCHEMA = "acfqp.redacted_boundary_view.v1"
SLICE_SCHEMA = "acfqp.authorized_ground_slice.v1"
RESULT_SCHEMA = "acfqp.local_solver_result.v1"


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


def _input_sha256(value: Any) -> str:
    return hashlib.sha256((_canonical_json(value) + "\n").encode("utf-8")).hexdigest()


def _fraction(value: Any, *, field: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an exact rational")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Fraction(value[0], value[1])
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
        rational = Fraction(numerator, denominator)
        if rational.numerator != numerator or rational.denominator != denominator:
            raise ValueError(f"{field} is not reduced")
        return rational
    raise ValueError(f"{field} must be an exact rational")


def _fraction_json(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _require_fields(document: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = fields - set(document)
    if missing:
        raise ValueError(f"{label} is missing fields {sorted(missing)!r}")
    extra = set(document) - fields
    if extra:
        raise ValueError(f"{label} has forbidden extra fields {sorted(extra)!r}")


@dataclass(frozen=True, slots=True)
class LocalPatchDecision:
    node_id: str
    cell: str
    remaining: int
    state_id: str
    action_id: str
    expected_reward: Fraction
    failure_probability: Fraction

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "cell": self.cell,
            "remaining": self.remaining,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "expected_reward": _fraction_json(self.expected_reward),
            "failure_probability": _fraction_json(self.failure_probability),
        }


@dataclass(frozen=True, slots=True)
class LocalSolverResult:
    request_id: str
    occurrence_id: str
    boundary_view_id: str
    slice_id: str
    frontier_id: str
    localized_node_ids: tuple[str, ...]
    decisions: tuple[LocalPatchDecision, ...]
    root_reward_lower: Fraction
    unrestricted_reward_upper: Fraction
    regret_tolerance: Fraction
    root_failure_upper: Fraction
    delta: Fraction
    candidate_subset_count: int
    result_id: str

    @property
    def certified_safe(self) -> bool:
        return self.root_failure_upper <= self.delta

    @property
    def regret_upper(self) -> Fraction:
        return self.unrestricted_reward_upper - self.root_reward_lower

    @property
    def certified_value(self) -> bool:
        return 0 <= self.regret_upper <= self.regret_tolerance

    @property
    def certified(self) -> bool:
        return self.certified_safe and self.certified_value

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RESULT_SCHEMA,
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "boundary_view_id": self.boundary_view_id,
            "slice_id": self.slice_id,
            "frontier_id": self.frontier_id,
            "localized_node_ids": list(self.localized_node_ids),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "root_reward_lower": _fraction_json(self.root_reward_lower),
            "unrestricted_reward_upper": _fraction_json(
                self.unrestricted_reward_upper
            ),
            "regret_upper": _fraction_json(self.regret_upper),
            "regret_tolerance": _fraction_json(self.regret_tolerance),
            "root_failure_upper": _fraction_json(self.root_failure_upper),
            "delta": _fraction_json(self.delta),
            "candidate_subset_count": self.candidate_subset_count,
            "certified_safe": self.certified_safe,
            "certified_value": self.certified_value,
            "certified": self.certified,
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class _Branch:
    branch_id: str
    immediate_reward: Fraction
    immediate_failure: Fraction
    successors: tuple[tuple[str, Fraction], ...]
    action_id: str | None = None


@dataclass(frozen=True, slots=True)
class _Member:
    state_id: str
    actions: tuple[_Branch, ...]


@dataclass(frozen=True, slots=True)
class _SliceCell:
    node_id: str
    cell: str
    remaining: int
    members: tuple[_Member, ...]


def _parse_successors(
    raw: Any, *, field: str, include_cell: bool = False
) -> tuple[tuple[str, Fraction], ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be a list")
    mass: dict[str, Fraction] = {}
    for index, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        expected = {"node_id", "probability"}
        if include_cell:
            expected.add("cell")
        _require_fields(row, expected, f"{field}[{index}]")
        if include_cell and not isinstance(row["cell"], str):
            raise ValueError(f"{field}[{index}].cell must be a string")
        node_id = row["node_id"]
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(f"{field}[{index}].node_id must be nonempty")
        probability = _fraction(row["probability"], field=f"{field}[{index}].probability")
        if probability <= 0 or probability > 1:
            raise ValueError(f"{field}[{index}].probability lies outside (0,1]")
        mass[node_id] = mass.get(node_id, Fraction(0)) + probability
    if sum(mass.values(), Fraction(0)) > 1:
        raise ValueError(f"{field} continuation mass exceeds one")
    return tuple(sorted(mass.items()))


def _parse_boundary(document: Mapping[str, Any]) -> tuple[
    Fraction,
    Fraction,
    Fraction,
    tuple[tuple[str, Fraction], ...],
    dict[str, tuple[_Branch, ...]],
]:
    if document.get("schema") != BOUNDARY_SCHEMA:
        raise ValueError("unsupported redacted boundary schema")
    _require_fields(
        document,
        {
            "schema",
            "graph_id",
            "delta",
            "unrestricted_reward_upper",
            "regret_tolerance",
            "roots",
            "nodes",
            "boundary_view_id",
            "frontier_id",
        },
        "boundary view",
    )
    delta = _fraction(document["delta"], field="boundary.delta")
    if delta < 0 or delta > 1:
        raise ValueError("boundary.delta lies outside [0,1]")
    unrestricted_reward_upper = _fraction(
        document["unrestricted_reward_upper"],
        field="boundary.unrestricted_reward_upper",
    )
    regret_tolerance = _fraction(
        document["regret_tolerance"], field="boundary.regret_tolerance"
    )
    if regret_tolerance < 0:
        raise ValueError("boundary.regret_tolerance must be nonnegative")
    roots_raw = document["roots"]
    if not isinstance(roots_raw, list) or not roots_raw:
        raise ValueError("boundary.roots must be a nonempty list")
    root_mass: dict[str, Fraction] = {}
    for index, row in enumerate(roots_raw):
        if not isinstance(row, Mapping):
            raise ValueError("boundary root rows must be objects")
        _require_fields(row, {"node_id", "probability"}, f"boundary.roots[{index}]")
        node_id = row["node_id"]
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("boundary root node_id must be nonempty")
        probability = _fraction(row["probability"], field=f"boundary.roots[{index}].probability")
        if probability <= 0:
            raise ValueError("boundary root probabilities must be positive")
        root_mass[node_id] = root_mass.get(node_id, Fraction(0)) + probability
    if sum(root_mass.values(), Fraction(0)) != 1:
        raise ValueError("boundary root probabilities must sum to one")

    raw_nodes = document["nodes"]
    if not isinstance(raw_nodes, list):
        raise ValueError("boundary.nodes must be a list")
    nodes: dict[str, tuple[_Branch, ...]] = {}
    for node_index, row in enumerate(raw_nodes):
        if not isinstance(row, Mapping):
            raise ValueError("boundary node rows must be objects")
        _require_fields(
            row,
            {
                "node_id",
                "cell",
                "remaining",
                "selected_action",
                "abstract_realizations",
            },
            f"boundary.nodes[{node_index}]",
        )
        node_id = row["node_id"]
        if not isinstance(node_id, str) or not node_id or node_id in nodes:
            raise ValueError("boundary node IDs must be nonempty and unique")
        remaining = row["remaining"]
        if not isinstance(row["cell"], str) or not isinstance(
            row["selected_action"], str
        ):
            raise ValueError("boundary cell/action metadata must be strings")
        if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining <= 0:
            raise ValueError("boundary node remaining must be a positive integer")
        realizations = row["abstract_realizations"]
        if not isinstance(realizations, list) or not realizations:
            raise ValueError("every boundary node needs at least one realization")
        branches: list[_Branch] = []
        for branch_index, branch in enumerate(realizations):
            if not isinstance(branch, Mapping):
                raise ValueError("abstract realization must be an object")
            _require_fields(
                branch,
                {
                    "realization_id",
                    "immediate_reward",
                    "failure_probability",
                    "successors",
                },
                f"boundary.nodes[{node_index}].abstract_realizations[{branch_index}]",
            )
            realization_id = branch["realization_id"]
            if not isinstance(realization_id, str) or not realization_id:
                raise ValueError("realization IDs must be nonempty")
            failure = _fraction(
                branch["failure_probability"],
                field="abstract realization failure_probability",
            )
            if failure < 0 or failure > 1:
                raise ValueError("abstract realization failure lies outside [0,1]")
            successors = _parse_successors(
                branch["successors"], field="abstract realization successors"
            )
            if failure + sum((probability for _, probability in successors), Fraction(0)) > 1:
                raise ValueError("abstract branch failure plus continuation exceeds one")
            branches.append(
                _Branch(
                    branch_id=realization_id,
                    immediate_reward=_fraction(
                        branch["immediate_reward"],
                        field="abstract realization immediate_reward",
                    ),
                    immediate_failure=failure,
                    successors=successors,
                )
            )
        nodes[node_id] = tuple(sorted(branches, key=lambda item: item.branch_id))
    unknown_roots = set(root_mass) - set(nodes)
    if unknown_roots:
        raise ValueError(f"root nodes absent from boundary: {sorted(unknown_roots)!r}")
    boundary_payload = dict(document)
    boundary_id = boundary_payload.pop("boundary_view_id")
    if boundary_id != _object_id("redacted-boundary-view", boundary_payload):
        raise ValueError("boundary_view_id does not bind the boundary content")
    return (
        delta,
        unrestricted_reward_upper,
        regret_tolerance,
        tuple(sorted(root_mass.items())),
        nodes,
    )


def _parse_slice(document: Mapping[str, Any]) -> dict[str, _SliceCell]:
    if document.get("schema") != SLICE_SCHEMA:
        raise ValueError("unsupported authorized ground-slice schema")
    _require_fields(
        document,
        {
            "schema",
            "authorization_id",
            "cells",
            "slice_id",
            "frontier_id",
        },
        "ground slice",
    )
    cells_raw = document["cells"]
    if not isinstance(cells_raw, list) or not cells_raw:
        raise ValueError("ground slice cells must be a nonempty list")
    cells: dict[str, _SliceCell] = {}
    for cell_index, row in enumerate(cells_raw):
        if not isinstance(row, Mapping):
            raise ValueError("ground slice cell rows must be objects")
        _require_fields(
            row,
            {"node_id", "cell", "remaining", "members"},
            f"slice.cells[{cell_index}]",
        )
        node_id = row["node_id"]
        cell = row["cell"]
        remaining = row["remaining"]
        if not isinstance(node_id, str) or not node_id or node_id in cells:
            raise ValueError("slice node IDs must be nonempty and unique")
        if not isinstance(cell, str):
            raise ValueError("slice cell payload must be a string")
        if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining <= 0:
            raise ValueError("slice remaining must be a positive integer")
        members_raw = row["members"]
        if not isinstance(members_raw, list) or not members_raw:
            raise ValueError("localized cell must have active members")
        members: list[_Member] = []
        seen_states: set[str] = set()
        for member_index, member in enumerate(members_raw):
            if not isinstance(member, Mapping):
                raise ValueError("slice members must be objects")
            _require_fields(
                member,
                {"state_id", "actions"},
                f"slice.cells[{cell_index}].members[{member_index}]",
            )
            state_id = member["state_id"]
            if not isinstance(state_id, str) or not state_id or state_id in seen_states:
                raise ValueError("slice state IDs must be nonempty and unique per cell")
            seen_states.add(state_id)
            actions_raw = member["actions"]
            if not isinstance(actions_raw, list) or not actions_raw:
                raise ValueError("every localized member needs at least one action")
            actions: list[_Branch] = []
            seen_actions: set[str] = set()
            for action_index, action in enumerate(actions_raw):
                if not isinstance(action, Mapping):
                    raise ValueError("slice actions must be objects")
                _require_fields(
                    action,
                    {
                        "action_id",
                        "immediate_reward",
                        "failure_probability",
                        "termination_probability",
                        "successors",
                    },
                    "slice action",
                )
                action_id = action["action_id"]
                if not isinstance(action_id, str) or not action_id or action_id in seen_actions:
                    raise ValueError("slice action IDs must be nonempty and unique per state")
                seen_actions.add(action_id)
                failure = _fraction(
                    action["failure_probability"], field="slice action failure_probability"
                )
                if failure < 0 or failure > 1:
                    raise ValueError("slice action failure lies outside [0,1]")
                termination = _fraction(
                    action["termination_probability"],
                    field="slice action termination_probability",
                )
                if termination < 0 or termination > 1 or failure > termination:
                    raise ValueError("slice action termination/failure mass is invalid")
                successors = _parse_successors(
                    action["successors"],
                    field="slice action successors",
                )
                continuation = sum(
                    (probability for _, probability in successors), Fraction(0)
                )
                if termination + continuation != 1:
                    raise ValueError(
                        "slice action termination plus continuation must equal one"
                    )
                actions.append(
                    _Branch(
                        branch_id=action_id,
                        immediate_reward=_fraction(
                            action["immediate_reward"], field="slice action immediate_reward"
                        ),
                        immediate_failure=failure,
                        successors=successors,
                        action_id=action_id,
                    )
                )
            members.append(
                _Member(
                    state_id=state_id,
                    actions=tuple(sorted(actions, key=lambda item: item.action_id or "")),
                )
            )
        cells[node_id] = _SliceCell(
            node_id=node_id,
            cell=cell,
            remaining=remaining,
            members=tuple(sorted(members, key=lambda item: item.state_id)),
        )
    slice_payload = dict(document)
    slice_id = slice_payload.pop("slice_id")
    if slice_id != _object_id("authorized-ground-slice", slice_payload):
        raise ValueError("slice_id does not bind the ground-slice content")
    return cells


def _parse_request(
    document: Mapping[str, Any],
    boundary_view: Mapping[str, Any],
    ground_slice: Mapping[str, Any],
) -> tuple[str, str]:
    expected = {
        "schema",
        "request_id",
        "workload_id",
        "occurrence_id",
        "portable_model_id",
        "build_epoch_id",
        "ground_query_id",
        "portable_query_id",
        "portable_result_id",
        "pre_audit_id",
        "failed_proof_graph_id",
        "frontier_id",
        "authorization_id",
        "slice_id",
        "slice_sha256",
        "boundary_view_id",
        "boundary_sha256",
        "worker_inputs",
        "portable_rapm_mounted_to_worker",
        "ground_kernel_mounted_to_worker",
        "coverage_graph_mounted_to_worker",
        "j0_mounted_to_worker",
        "project_checkout_mounted_to_worker",
        "grammar_used",
        "selection_rule",
    }
    _require_fields(document, expected, "local request")
    if document.get("schema") != "acfqp.local_recovery_request.v1":
        raise ValueError("unsupported local request schema")
    request_payload = dict(document)
    request_id = request_payload.pop("request_id")
    if request_id != _object_id("local-request", request_payload):
        raise ValueError("request_id does not bind the request content")
    identifiers = {
        "frontier_id": boundary_view.get("frontier_id"),
        "boundary_view_id": boundary_view.get("boundary_view_id"),
        "slice_id": ground_slice.get("slice_id"),
        "authorization_id": ground_slice.get("authorization_id"),
    }
    if any(document.get(field) != value for field, value in identifiers.items()):
        raise ValueError("local request cross-identifiers do not match its capabilities")
    if document.get("failed_proof_graph_id") != boundary_view.get("graph_id"):
        raise ValueError("local request names a different failed-proof graph")
    if document.get("boundary_sha256") != _input_sha256(boundary_view):
        raise ValueError("local request boundary hash mismatch")
    if document.get("slice_sha256") != _input_sha256(ground_slice):
        raise ValueError("local request slice hash mismatch")
    if document.get("worker_inputs") != [
        "boundary.json",
        "request.json",
        "slice.json",
    ]:
        raise ValueError("local request worker input inventory changed")
    forbidden_mount_flags = (
        "portable_rapm_mounted_to_worker",
        "ground_kernel_mounted_to_worker",
        "coverage_graph_mounted_to_worker",
        "j0_mounted_to_worker",
        "project_checkout_mounted_to_worker",
        "grammar_used",
    )
    if any(document.get(field) is not False for field in forbidden_mount_flags):
        raise ValueError("local request declares forbidden worker authority")
    occurrence_id = document.get("occurrence_id")
    if not isinstance(request_id, str) or not isinstance(occurrence_id, str):
        raise ValueError("local request IDs must be strings")
    return request_id, occurrence_id


def _pareto_actions(
    actions: Sequence[tuple[_Branch, Fraction, Fraction]],
) -> tuple[tuple[_Branch, Fraction, Fraction], ...]:
    frontier: list[tuple[_Branch, Fraction, Fraction]] = []
    for candidate in actions:
        _, reward, failure = candidate
        dominated = any(
            other_reward >= reward
            and other_failure <= failure
            and (other_reward > reward or other_failure < failure)
            for _, other_reward, other_failure in actions
        )
        if not dominated:
            frontier.append(candidate)
    return tuple(
        sorted(
            frontier,
            key=lambda item: (
                item[2],
                -item[1],
                item[0].action_id or item[0].branch_id,
            ),
        )
    )


def solve_local_recovery(
    boundary_view: Mapping[str, Any],
    ground_slice: Mapping[str, Any],
    request: Mapping[str, Any],
) -> LocalSolverResult:
    """Return the first safe cardinality-minimal local frontier patch.

    Raises ``ValueError`` when the authorized frontier cannot certify safety;
    callers must route that condition to rebuild/fallback rather than silently
    widening the worker's authority.
    """

    if boundary_view.get("frontier_id") != ground_slice.get("frontier_id"):
        raise ValueError("boundary and ground slice name different frontiers")
    request_id, occurrence_id = _parse_request(
        request, boundary_view, ground_slice
    )
    (
        delta,
        unrestricted_reward_upper,
        regret_tolerance,
        roots,
        abstract_nodes,
    ) = _parse_boundary(boundary_view)
    slice_cells = _parse_slice(ground_slice)
    if not set(slice_cells).issubset(abstract_nodes):
        missing = set(slice_cells) - set(abstract_nodes)
        raise ValueError(f"frontier slice nodes absent from boundary: {sorted(missing)!r}")
    boundary_metadata = {
        row["node_id"]: (row["cell"], row["remaining"])
        for row in boundary_view["nodes"]
    }
    for node_id, cell in slice_cells.items():
        if boundary_metadata.get(node_id) != (cell.cell, cell.remaining):
            raise ValueError("slice cell metadata disagrees with abstract boundary")

    frontier_ids = tuple(sorted(slice_cells))
    considered = 0
    accepted: tuple[
        tuple[str, ...],
        Fraction,
        Fraction,
        tuple[LocalPatchDecision, ...],
    ] | None = None

    for cardinality in range(0, len(frontier_ids) + 1):
        for localized_tuple in itertools.combinations(frontier_ids, cardinality):
            considered += 1
            localized = frozenset(localized_tuple)
            memo: dict[str, tuple[Fraction, Fraction]] = {}
            active: set[str] = set()
            chosen: dict[tuple[str, str], tuple[_Branch, Fraction, Fraction]] = {}

            def evaluate(node_id: str) -> tuple[Fraction, Fraction]:
                cached = memo.get(node_id)
                if cached is not None:
                    return cached
                if node_id in active:
                    raise ValueError("boundary dependency graph contains a cycle")
                if node_id not in abstract_nodes:
                    raise ValueError(
                        f"successor {node_id!r} has no certified abstract boundary"
                    )
                active.add(node_id)

                def branch_value(branch: _Branch) -> tuple[Fraction, Fraction]:
                    reward = branch.immediate_reward
                    failure = branch.immediate_failure
                    for successor, probability in branch.successors:
                        successor_reward, successor_failure = evaluate(successor)
                        reward += probability * successor_reward
                        failure += probability * successor_failure
                    if failure < 0 or failure > 1:
                        raise ValueError("recursive failure bound lies outside [0,1]")
                    return reward, failure

                if node_id in localized:
                    member_rewards: list[Fraction] = []
                    member_failures: list[Fraction] = []
                    for member in slice_cells[node_id].members:
                        values = tuple(
                            (action, *branch_value(action)) for action in member.actions
                        )
                        pareto = _pareto_actions(values)
                        selected = min(
                            pareto,
                            key=lambda item: (
                                item[2],
                                -item[1],
                                item[0].action_id or item[0].branch_id,
                            ),
                        )
                        chosen[(node_id, member.state_id)] = selected
                        member_rewards.append(selected[1])
                        member_failures.append(selected[2])
                    result = min(member_rewards), max(member_failures)
                else:
                    values = tuple(
                        branch_value(branch) for branch in abstract_nodes[node_id]
                    )
                    result = (
                        min(reward for reward, _ in values),
                        max(failure for _, failure in values),
                    )
                active.remove(node_id)
                memo[node_id] = result
                return result

            root_reward = Fraction(0)
            root_failure = Fraction(0)
            for node_id, probability in roots:
                reward, failure = evaluate(node_id)
                root_reward += probability * reward
                root_failure += probability * failure
            regret_upper = unrestricted_reward_upper - root_reward
            if regret_upper < 0:
                raise ValueError(
                    "hybrid reward lower exceeds the supplied unrestricted upper bound"
                )
            if root_failure <= delta and regret_upper <= regret_tolerance:
                decisions = tuple(
                    LocalPatchDecision(
                        node_id=node_id,
                        cell=slice_cells[node_id].cell,
                        remaining=slice_cells[node_id].remaining,
                        state_id=state_id,
                        action_id=selection[0].action_id or selection[0].branch_id,
                        expected_reward=selection[1],
                        failure_probability=selection[2],
                    )
                    for (node_id, state_id), selection in sorted(chosen.items())
                    if node_id in localized
                )
                accepted = localized_tuple, root_reward, root_failure, decisions
                break
        if accepted is not None:
            break
    if accepted is None:
        raise ValueError(
            "authorized frontier cannot certify the requested value/risk bounds; "
            "authority expansion is forbidden"
        )

    localized_tuple, root_reward, root_failure, decisions = accepted
    payload = {
        "schema": RESULT_SCHEMA,
        "request_id": request_id,
        "occurrence_id": occurrence_id,
        "boundary_view_id": boundary_view["boundary_view_id"],
        "slice_id": ground_slice["slice_id"],
        "frontier_id": boundary_view["frontier_id"],
        "localized_node_ids": list(localized_tuple),
        "decisions": [decision.to_dict() for decision in decisions],
        "root_reward_lower": _fraction_json(root_reward),
        "unrestricted_reward_upper": _fraction_json(unrestricted_reward_upper),
        "regret_upper": _fraction_json(unrestricted_reward_upper - root_reward),
        "regret_tolerance": _fraction_json(regret_tolerance),
        "root_failure_upper": _fraction_json(root_failure),
        "delta": _fraction_json(delta),
        "candidate_subset_count": considered,
        "certified_safe": root_failure <= delta,
        "certified_value": (
            0 <= unrestricted_reward_upper - root_reward <= regret_tolerance
        ),
        "certified": (
            root_failure <= delta
            and 0 <= unrestricted_reward_upper - root_reward <= regret_tolerance
        ),
    }
    result_id = _logical_id("local-result", payload)
    return LocalSolverResult(
        request_id=request_id,
        occurrence_id=occurrence_id,
        boundary_view_id=boundary_view["boundary_view_id"],
        slice_id=ground_slice["slice_id"],
        frontier_id=boundary_view["frontier_id"],
        localized_node_ids=localized_tuple,
        decisions=decisions,
        root_reward_lower=root_reward,
        unrestricted_reward_upper=unrestricted_reward_upper,
        regret_tolerance=regret_tolerance,
        root_failure_upper=root_failure,
        delta=delta,
        candidate_subset_count=considered,
        result_id=result_id,
    )


__all__ = [
    "BOUNDARY_SCHEMA",
    "LocalPatchDecision",
    "LocalSolverResult",
    "RESULT_SCHEMA",
    "SLICE_SCHEMA",
    "solve_local_recovery",
]
