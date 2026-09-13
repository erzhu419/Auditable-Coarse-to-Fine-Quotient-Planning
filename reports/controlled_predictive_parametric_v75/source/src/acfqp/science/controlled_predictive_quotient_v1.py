"""Development-only, finite-horizon controlled predictive quotients.

The representation fits action-conditional immediate rewards and recursive
successor-cell distributions. It does not fit optimal values, future policy
labels, or board features. The planner consumes only the compiled finite model;
the separately supplied ground model is used only by the policy audit.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class Outcome:
    probability: float
    next_state: int
    reward: float


@dataclass(frozen=True)
class FiniteModel:
    layers: dict[int, int]
    terminal: dict[int, str]
    rows: dict[tuple[int, str], tuple[Outcome, ...]]
    roots: tuple[int, ...]

    def __post_init__(self) -> None:
        """Check the finite kernel assumptions actually required by backward DP."""
        if self.layers.keys() != self.terminal.keys() or not self.roots:
            raise ValueError("states must have layers, statuses, and at least one root")
        if any(root not in self.layers for root in self.roots):
            raise ValueError("root missing from model")
        actions = defaultdict(set)
        for (state, action), outcomes in self.rows.items():
            if state not in self.layers or self.terminal[state] != "ACTIVE":
                raise ValueError("only active states have action rows")
            actions[state].add(action)
            if not outcomes or not math.isclose(
                math.fsum(o.probability for o in outcomes), 1.0, abs_tol=1e-9
            ):
                raise ValueError("action row probability mass must sum to one")
            for outcome in outcomes:
                if not math.isfinite(outcome.probability) or outcome.probability < 0:
                    raise ValueError("invalid outcome probability")
                if not math.isfinite(outcome.reward):
                    raise ValueError("invalid outcome reward")
                if self.layers.get(outcome.next_state) != self.layers[state] - 1:
                    raise ValueError("every outcome must decrease remaining horizon by one")
        for state, layer in self.layers.items():
            status = self.terminal[state]
            if layer < 0 or status not in {"ACTIVE", "WON", "LOST", "CUTOFF"}:
                raise ValueError("invalid layer or terminal status")
            if status == "ACTIVE" and (layer == 0 or not actions[state]):
                raise ValueError("active states require positive horizon and legal actions")
            if status == "CUTOFF" and layer != 0:
                raise ValueError("cutoff states must have zero remaining horizon")


@dataclass(frozen=True)
class Query:
    reward_weight: float = 1.0
    failure_penalty: float = 0.0
    goal_bonus: float = 0.0


@dataclass(frozen=True)
class Cell:
    layer: int
    terminal: str
    members: tuple[int, ...]


@dataclass(frozen=True)
class CompiledModel:
    cells: dict[int, Cell]
    rows: dict[tuple[int, str], tuple[Outcome, ...]]
    roots: tuple[int, ...]
    state_to_cell: dict[int, int]
    diameters: dict[int, dict[str, float]]


@dataclass(frozen=True)
class Plan:
    values: dict[int, float]
    policy: dict[int, str]
    counts: dict[str, int]


@dataclass(frozen=True)
class Audit:
    root_metrics: dict[int, dict[str, float]]
    aggregate: dict[str, float]
    counts: dict[str, int]


def _actions(model: FiniteModel | CompiledModel) -> dict[int, tuple[str, ...]]:
    actions: dict[int, list[str]] = defaultdict(list)
    for state, action in model.rows:
        actions[state].append(action)
    return {state: tuple(sorted(names)) for state, names in actions.items()}


def sample_model(model: FiniteModel, samples_per_row: int, seed: int) -> FiniteModel:
    """Sample every legal action once into a reusable empirical kernel."""
    if samples_per_row < 1:
        raise ValueError("samples_per_row must be positive")
    rng = random.Random(seed)
    rows = {}
    for key in sorted(model.rows):
        row = model.rows[key]
        counts: dict[tuple[int, float], int] = defaultdict(int)
        for outcome in rng.choices(row, weights=[o.probability for o in row], k=samples_per_row):
            counts[outcome.next_state, outcome.reward] += 1
        rows[key] = tuple(
            Outcome(count / samples_per_row, target, reward)
            for (target, reward), count in sorted(counts.items())
        )
    return FiniteModel(dict(model.layers), dict(model.terminal), rows, model.roots)


def action_outcome_shuffle(model: FiniteModel) -> FiniteModel:
    """Rotate complete outcome rows across each state's existing legal actions."""
    rows = {}
    for state, actions in _actions(model).items():
        for index, action in enumerate(actions):
            rows[state, action] = model.rows[state, actions[(index + 1) % len(actions)]]
    return FiniteModel(dict(model.layers), dict(model.terminal), rows, model.roots)


# Signature coordinates keep action names, expected rewards, and successor mass.
Signature = tuple[tuple[str, float, tuple[tuple[int, float], ...]], ...]


def _signature(model: FiniteModel, state: int, actions: tuple[str, ...], mapping: dict[int, int]) -> Signature:
    result = []
    for action in actions:
        row = model.rows[state, action]
        mass: dict[int, list[float]] = defaultdict(list)
        for outcome in row:
            if outcome.probability:
                mass[mapping[outcome.next_state]].append(outcome.probability)
        result.append((action, math.fsum(o.probability * o.reward for o in row), tuple(
            (cell, math.fsum(parts)) for cell, parts in sorted(mass.items())
        )))
    return tuple(result)


def _distance(left: Signature, right: Signature) -> tuple[float, float]:
    reward_distance = tv_distance = 0.0
    for (_, left_reward, left_mass), (_, right_reward, right_mass) in zip(left, right):
        reward_distance = max(reward_distance, abs(left_reward - right_reward))
        p, q = dict(left_mass), dict(right_mass)
        tv_distance = max(tv_distance, 0.5 * math.fsum(
            abs(p.get(cell, 0.0) - q.get(cell, 0.0)) for cell in p.keys() | q.keys()
        ))
    return reward_distance, tv_distance


def _compile_rows(model: FiniteModel, cells: dict[int, Cell], mapping: dict[int, int]) -> dict[tuple[int, str], tuple[Outcome, ...]]:
    actions = _actions(model)
    rows = {}
    for cell_id, cell in cells.items():
        for action in actions.get(cell.members[0], ()):
            mass: dict[int, list[float]] = defaultdict(list)
            reward_mass: dict[int, list[float]] = defaultdict(list)
            for state in cell.members:
                for outcome in model.rows[state, action]:
                    if outcome.probability:
                        target = mapping[outcome.next_state]
                        mass[target].append(outcome.probability)
                        reward_mass[target].append(outcome.probability * outcome.reward)
            rows[cell_id, action] = tuple(
                Outcome(math.fsum(parts) / len(cell.members), target,
                        math.fsum(reward_mass[target]) / math.fsum(parts))
                for target, parts in sorted(mass.items())
            )
    return rows


def build_quotient(model: FiniteModel, reward_tolerance: float = 0.0, tv_tolerance: float = 0.0) -> CompiledModel:
    """Build recursive action-conditional cells, with complete-link tolerances.

    Zero tolerances give the reference finite predictive quotient. Positive
    tolerances bound every pair in each fitted cell; they are empirical fitting
    tolerances, not statistical guarantees about the independent ground model.
    Intrinsic signature ordering makes the partition invariant to source IDs.
    """
    if not math.isfinite(reward_tolerance) or reward_tolerance < 0 or not 0 <= tv_tolerance <= 1:
        raise ValueError("invalid quotient tolerances")
    actions = _actions(model)
    mapping: dict[int, int] = {}
    cells: dict[int, Cell] = {}
    diameters: dict[int, dict[str, float]] = {}
    states_by_layer: dict[int, list[int]] = defaultdict(list)
    for state, layer in model.layers.items():
        states_by_layer[layer].append(state)
    for layer, states in sorted(states_by_layer.items()):
        groups: dict[tuple[str, tuple[str, ...]], list[int]] = defaultdict(list)
        for state in states:
            groups[model.terminal[state], actions.get(state, ())].append(state)
        for (status, legal), members in sorted(groups.items()):
            signatures = {state: _signature(model, state, legal, mapping) for state in members}
            clusters: list[list[int]] = []
            cluster_diameters: list[tuple[float, float]] = []
            exact_buckets: dict[Signature, list[int]] = {}
            if not legal or reward_tolerance == tv_tolerance == 0:
                for state in members:
                    exact_buckets.setdefault(signatures[state], []).append(state)
                clusters = [exact_buckets[key] for key in sorted(exact_buckets)]
                cluster_diameters = [(0.0, 0.0)] * len(clusters)
            else:
                for state in sorted(members, key=lambda candidate: signatures[candidate]):
                    for index, cluster in enumerate(clusters):
                        distances = [_distance(signatures[state], signatures[other]) for other in cluster]
                        reward_diameter = max([cluster_diameters[index][0]] + [d[0] for d in distances])
                        tv_diameter = max([cluster_diameters[index][1]] + [d[1] for d in distances])
                        if reward_diameter <= reward_tolerance and tv_diameter <= tv_tolerance:
                            cluster.append(state)
                            cluster_diameters[index] = reward_diameter, tv_diameter
                            break
                    else:
                        clusters.append([state])
                        cluster_diameters.append((0.0, 0.0))
            for cluster, (reward_diameter, tv_diameter) in zip(clusters, cluster_diameters):
                cell_id = len(cells)
                cells[cell_id] = Cell(layer, status, tuple(sorted(cluster)))
                diameters[cell_id] = {"reward": reward_diameter, "tv": tv_diameter}
                mapping.update((state, cell_id) for state in cluster)
    return CompiledModel(cells, _compile_rows(model, cells, mapping),
                         tuple(mapping[root] for root in model.roots), mapping, diameters)


def compile_full_state(model: FiniteModel) -> CompiledModel:
    """Compile the same data with singleton states, without representation fitting."""
    mapping = {state: index for index, state in enumerate(sorted(model.layers))}
    cells = {mapping[state]: Cell(model.layers[state], model.terminal[state], (state,)) for state in mapping}
    return CompiledModel(cells, _compile_rows(model, cells, mapping),
                         tuple(mapping[root] for root in model.roots), mapping,
                         {cell: {"reward": 0.0, "tv": 0.0} for cell in cells})


def _terminal_value(status: str, query: Query) -> float:
    return query.goal_bonus if status == "WON" else -query.failure_penalty if status == "LOST" else 0.0


def plan(model: CompiledModel, query: Query = Query()) -> Plan:
    """Optimize every compiled cell and charge actual DP work.

    The complete frozen policy covers cells an independent exact audit can reach
    even when finite empirical sampling missed the incoming transition.
    """
    actions = _actions(model)
    values: dict[int, float] = {}
    policy: dict[int, str] = {}
    counts = {"active_states": 0, "state_action_rows": 0, "outcomes": 0, "visited_cells": 0}

    def solve(cell: int) -> float:
        if cell in values:
            return values[cell]
        counts["visited_cells"] += 1
        status = model.cells[cell].terminal
        if status != "ACTIVE":
            values[cell] = _terminal_value(status, query)
            return values[cell]
        counts["active_states"] += 1
        best_value, best_action = -math.inf, ""
        for action in actions[cell]:
            row = model.rows[cell, action]
            counts["state_action_rows"] += 1
            counts["outcomes"] += len(row)
            value = math.fsum(o.probability * (query.reward_weight * o.reward + solve(o.next_state)) for o in row)
            if value > best_value:
                best_value, best_action = value, action
        values[cell], policy[cell] = best_value, best_action
        return best_value

    for cell in sorted(model.cells, key=lambda candidate: model.cells[candidate].layer):
        solve(cell)
    return Plan(values, policy, counts)


def _evaluate_policy(terminal: dict[int, str], rows: dict[tuple[int, str], tuple[Outcome, ...]],
                     roots: tuple[int, ...], policy: dict[int, str], query: Query) -> Audit:
    metrics: dict[int, dict[str, float]] = {}
    counts = {"active_states": 0, "state_action_rows": 0, "outcomes": 0, "visited_states": 0}

    def evaluate(state: int) -> dict[str, float]:
        if state in metrics:
            return metrics[state]
        counts["visited_states"] += 1
        status = terminal[state]
        if status != "ACTIVE":
            result = {"reward": 0.0, "failure": float(status == "LOST"), "success": float(status == "WON")}
        else:
            row = rows[state, policy[state]]
            counts["active_states"] += 1
            counts["state_action_rows"] += 1
            counts["outcomes"] += len(row)
            successors = [(o, evaluate(o.next_state)) for o in row if o.probability]
            result = {
                "reward": math.fsum(o.probability * (o.reward + m["reward"]) for o, m in successors),
                "failure": math.fsum(o.probability * m["failure"] for o, m in successors),
                "success": math.fsum(o.probability * m["success"] for o, m in successors),
            }
        result["value"] = query.reward_weight * result["reward"] - query.failure_penalty * result["failure"] + query.goal_bonus * result["success"]
        metrics[state] = result
        return result

    root_metrics = {root: evaluate(root) for root in roots}
    aggregate = {name: math.fsum(root_metrics[root][name] for root in roots) / len(roots)
                 for name in ("value", "reward", "failure", "success")}
    return Audit(root_metrics, aggregate, counts)


def evaluate_compiled_policy(compiled: CompiledModel, fitted_plan: Plan, query: Query = Query()) -> Audit:
    """Predict reward, failure, and success of the same frozen compiled policy.

    Root metrics use cell IDs. The separately reported counts charge this
    policy-evaluation traversal in addition to optimization work in ``Plan``.
    """
    return _evaluate_policy({cell: value.terminal for cell, value in compiled.cells.items()},
                            compiled.rows, compiled.roots, fitted_plan.policy, query)


def audit_policy(exact: FiniteModel, compiled: CompiledModel, fitted_plan: Plan, query: Query = Query()) -> Audit:
    """Lift one frozen cell policy into the independent exact finite kernel."""
    lifted = {state: fitted_plan.policy[compiled.state_to_cell[state]]
              for state, status in exact.terminal.items() if status == "ACTIVE"}
    return _evaluate_policy(exact.terminal, exact.rows, exact.roots, lifted, query)


def conflict_witness(model: FiniteModel, quotient: CompiledModel, left: int, right: int) -> dict[str, object] | None:
    """Return a concrete recursive action-coordinate conflict between two states."""
    actions = _actions(model)
    if (model.layers[left], model.terminal[left], actions.get(left, ())) != (
        model.layers[right], model.terminal[right], actions.get(right, ())
    ):
        return {"left": left, "right": right, "reason": "layer_status_or_legal_actions"}
    left_signature = _signature(model, left, actions.get(left, ()), quotient.state_to_cell)
    right_signature = _signature(model, right, actions.get(right, ()), quotient.state_to_cell)
    for a, b in zip(left_signature, right_signature):
        reward, tv = _distance((a,), (b,))
        if reward or tv:
            return {"left": left, "right": right, "action": a[0], "reward_difference": reward,
                    "total_variation": tv, "left_successor_cells": dict(a[2]), "right_successor_cells": dict(b[2])}
    return None
