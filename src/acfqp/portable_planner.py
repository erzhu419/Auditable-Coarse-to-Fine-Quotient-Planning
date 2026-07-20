"""Fresh-process exact planning over a :mod:`acfqp.portable` RAPM.

This module is deliberately on the consumption side of the model boundary. It
does not import a domain kernel, the ground planner, or refinement machinery.
All probabilities and values are exact :class:`fractions.Fraction` objects.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from acfqp.portable import (
    PortableQuery,
    PortableRAPM,
    canonical_json,
    fraction_from_json,
    fraction_to_json,
    load_model,
    load_query,
    logical_id,
)


RESULT_SCHEMA = "acfqp.portable_plan_result.v1"
REWARD_UPPER_PROOF_SCHEMA = "acfqp.portable_reward_upper_proof.v1"
REWARD_UPPER_FORMULA_ID = "portable_reward_bellman_upper_v1"


@dataclass(frozen=True, order=True, slots=True)
class PortablePolicyDecision:
    remaining: int
    cell_id: str
    action_id: str

    def __post_init__(self) -> None:
        if self.remaining <= 0:
            raise ValueError("portable policy decisions require a positive horizon")
        if not self.cell_id or not self.action_id:
            raise ValueError("portable policy cell/action IDs must be nonempty")


@dataclass(frozen=True, slots=True)
class PortablePolicy:
    decisions: tuple[PortablePolicyDecision, ...]

    def __post_init__(self) -> None:
        seen: set[tuple[int, str]] = set()
        previous: tuple[int, str, str] | None = None
        for decision in self.decisions:
            key = (decision.remaining, decision.cell_id)
            if key in seen:
                raise ValueError(f"duplicate portable policy decision for {key!r}")
            seen.add(key)
            ordering_key = (-decision.remaining, decision.cell_id, decision.action_id)
            if previous is not None and ordering_key < previous:
                raise ValueError("portable policy decisions must be canonically sorted")
            previous = ordering_key

    @classmethod
    def from_mapping(
        cls, mapping: Mapping[tuple[int, str], str] | Iterable[tuple[tuple[int, str], str]]
    ) -> "PortablePolicy":
        items = mapping.items() if isinstance(mapping, Mapping) else mapping
        decisions = tuple(
            sorted(
                (
                    PortablePolicyDecision(remaining, cell_id, action_id)
                    for (remaining, cell_id), action_id in items
                ),
                key=lambda decision: (
                    -decision.remaining,
                    decision.cell_id,
                    decision.action_id,
                ),
            )
        )
        return cls(decisions)

    def as_dict(self) -> dict[tuple[int, str], str]:
        return {
            (decision.remaining, decision.cell_id): decision.action_id
            for decision in self.decisions
        }

    def signature(self) -> tuple[tuple[int, str, str], ...]:
        return tuple(
            (decision.remaining, decision.cell_id, decision.action_id)
            for decision in self.decisions
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [
                {
                    "remaining": decision.remaining,
                    "cell_id": decision.cell_id,
                    "action_id": decision.action_id,
                }
                for decision in self.decisions
            ]
        }

    @classmethod
    def from_dict(cls, document: Any) -> "PortablePolicy":
        if not isinstance(document, dict) or set(document) != {"decisions"}:
            raise ValueError("portable policy has an invalid field set")
        raw = document["decisions"]
        if not isinstance(raw, list):
            raise ValueError("portable policy decisions must be a list")
        decisions: list[PortablePolicyDecision] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict) or set(item) != {
                "remaining",
                "cell_id",
                "action_id",
            }:
                raise ValueError(f"portable policy decision {index} has invalid fields")
            remaining = item["remaining"]
            if isinstance(remaining, bool) or not isinstance(remaining, int):
                raise ValueError("portable policy remaining horizon must be an integer")
            if not isinstance(item["cell_id"], str) or not isinstance(item["action_id"], str):
                raise ValueError("portable policy IDs must be strings")
            decisions.append(
                PortablePolicyDecision(remaining, item["cell_id"], item["action_id"])
            )
        return cls(tuple(decisions))


EMPTY_POLICY = PortablePolicy(())


@dataclass(frozen=True, slots=True)
class PortableParetoPoint:
    expected_reward: Fraction
    failure_probability: Fraction
    policy: PortablePolicy

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_reward": fraction_to_json(self.expected_reward),
            "failure_probability": fraction_to_json(self.failure_probability),
            "policy": self.policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, document: Any) -> "PortableParetoPoint":
        if not isinstance(document, dict) or set(document) != {
            "expected_reward",
            "failure_probability",
            "policy",
        }:
            raise ValueError("portable Pareto point has an invalid field set")
        failure = fraction_from_json(
            document["failure_probability"], field="result.failure_probability"
        )
        if failure < 0 or failure > 1:
            raise ValueError("portable Pareto failure probability lies outside [0, 1]")
        return cls(
            fraction_from_json(document["expected_reward"], field="result.expected_reward"),
            failure,
            PortablePolicy.from_dict(document["policy"]),
        )


@dataclass(frozen=True, slots=True)
class PortableExactEnvelopeAudit:
    """Exact full-plan check using the serialized realization envelope only."""

    expected_reward: Fraction
    failure_probability: Fraction
    unrestricted_reward_upper: Fraction
    regret_upper: Fraction
    regret_tolerance: Fraction
    risk_tolerance: Fraction
    reachable_cell_horizon_pairs: int
    certified: bool


@dataclass(frozen=True, order=True, slots=True)
class PortableRewardUpperRow:
    """One independently replayable reward-only Bellman upper entry."""

    remaining: int
    cell_id: str
    reward_upper: Fraction

    def __post_init__(self) -> None:
        if self.remaining <= 0:
            raise ValueError("reward-upper rows require a positive horizon")
        if not self.cell_id:
            raise ValueError("reward-upper rows require a cell ID")
        if self.reward_upper < 0:
            raise ValueError("reward-upper rows must be nonnegative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "remaining": self.remaining,
            "cell_id": self.cell_id,
            "reward_upper": fraction_to_json(self.reward_upper),
        }

    @classmethod
    def from_dict(cls, document: Any) -> "PortableRewardUpperRow":
        if not isinstance(document, dict) or set(document) != {
            "remaining",
            "cell_id",
            "reward_upper",
        }:
            raise ValueError("portable reward-upper row has an invalid field set")
        remaining = document["remaining"]
        cell_id = document["cell_id"]
        if isinstance(remaining, bool) or not isinstance(remaining, int):
            raise ValueError("reward-upper row remaining must be an integer")
        if not isinstance(cell_id, str):
            raise ValueError("reward-upper row cell_id must be a string")
        return cls(
            remaining,
            cell_id,
            fraction_from_json(
                document["reward_upper"], field="reward-upper row value"
            ),
        )


@dataclass(frozen=True, slots=True)
class PortableRewardUpperProof:
    """Content-addressed reward-only Bellman proof independent of a frontier.

    The proof is deliberately generated without a :class:`PortablePlanResult`.
    A consumer replays the scalar Bellman equations against the frozen RAPM and
    query, which proves a sound unrestricted reward upper without reconstructing
    the value--risk policy frontier.
    """

    model_id: str
    query_id: str
    rows: tuple[PortableRewardUpperRow, ...]
    root_upper: Fraction

    def __post_init__(self) -> None:
        if not self.model_id or not self.query_id:
            raise ValueError("reward-upper proof IDs must be nonempty")
        if self.rows != tuple(sorted(set(self.rows))):
            raise ValueError("reward-upper proof rows must be unique and sorted")
        if self.root_upper < 0:
            raise ValueError("reward-upper proof root must be nonnegative")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REWARD_UPPER_PROOF_SCHEMA,
            "formula_id": REWARD_UPPER_FORMULA_ID,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "rows": [row.to_dict() for row in self.rows],
            "root_upper": fraction_to_json(self.root_upper),
        }

    @property
    def proof_id(self) -> str:
        return logical_id("portable-reward-upper-proof", self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}

    @classmethod
    def from_dict(
        cls,
        document: Any,
        *,
        model: PortableRAPM | None = None,
        query: PortableQuery | None = None,
    ) -> "PortableRewardUpperProof":
        if not isinstance(document, dict) or set(document) != {
            "schema",
            "formula_id",
            "model_id",
            "query_id",
            "rows",
            "root_upper",
            "proof_id",
        }:
            raise ValueError("portable reward-upper proof has an invalid field set")
        if (
            document["schema"] != REWARD_UPPER_PROOF_SCHEMA
            or document["formula_id"] != REWARD_UPPER_FORMULA_ID
        ):
            raise ValueError("unsupported portable reward-upper proof")
        for field in ("model_id", "query_id", "proof_id"):
            if not isinstance(document[field], str) or not document[field]:
                raise ValueError(
                    f"portable reward-upper proof {field} must be a nonempty string"
                )
        if not isinstance(document["rows"], list):
            raise ValueError("portable reward-upper proof rows must be a list")
        proof = cls(
            document["model_id"],
            document["query_id"],
            tuple(PortableRewardUpperRow.from_dict(row) for row in document["rows"]),
            fraction_from_json(
                document["root_upper"], field="reward-upper proof root"
            ),
        )
        if document["proof_id"] != proof.proof_id:
            raise ValueError("portable reward-upper proof content ID mismatch")
        if model is not None and proof.model_id != model.model_id:
            raise ValueError("portable reward-upper proof/model mismatch")
        if query is not None and proof.query_id != query.query_id:
            raise ValueError("portable reward-upper proof/query mismatch")
        return proof


def _reward_upper_bellman(
    model: PortableRAPM,
    query: PortableQuery,
) -> tuple[tuple[PortableRewardUpperRow, ...], Fraction]:
    """Compute the scalar Bellman table used to generate or replay a proof."""

    if query.model_id != model.model_id:
        raise ValueError("portable query/model mismatch")
    model = PortableRAPM.from_dict(model.to_dict())
    query = PortableQuery.from_dict(query.to_dict(), model)
    model_document = model.to_dict()
    query_document = query.to_dict()
    weights = {
        record["name"]: fraction_from_json(
            record["value"], field="query normalized reward weight"
        )
        for record in query_document["normalized_reward_weights"]
    }
    entries_by_cell: dict[str, list[dict[str, Any]]] = {}
    for entry in model_document["nominal"]:
        entries_by_cell.setdefault(entry["cell_id"], []).append(entry["model"])
    values: dict[tuple[int, str], Fraction] = {}
    rows: list[PortableRewardUpperRow] = []
    for remaining in range(1, query.horizon + 1):
        for cell_id in sorted(entries_by_cell):
            candidates: list[Fraction] = []
            for transition in entries_by_cell[cell_id]:
                features = {
                    record["name"]: fraction_from_json(
                        record["value"], field="nominal reward feature"
                    )
                    for record in transition["reward_features"]
                }
                value = sum(
                    (
                        weights.get(name, Fraction(0)) * feature
                        for name, feature in features.items()
                    ),
                    Fraction(0),
                )
                if remaining > 1:
                    for successor in transition["successor_probabilities"]:
                        probability = fraction_from_json(
                            successor["probability"],
                            field="nominal successor probability",
                        )
                        value += probability * values.get(
                            (remaining - 1, successor["cell_id"]), Fraction(0)
                        )
                candidates.append(value)
            upper = max(candidates, default=Fraction(0))
            values[(remaining, cell_id)] = upper
            rows.append(PortableRewardUpperRow(remaining, cell_id, upper))
    root_upper = sum(
        (
            fraction_from_json(
                record["probability"], field="query initial probability"
            )
            * values.get((query.horizon, record["cell_id"]), Fraction(0))
            for record in query_document["initial_distribution"]
        ),
        Fraction(0),
    )
    return tuple(rows), root_upper


def build_portable_reward_upper_proof(
    model: PortableRAPM,
    query: PortableQuery,
) -> PortableRewardUpperProof:
    """Freeze a result-independent reward upper before planner output exists."""

    rows, root_upper = _reward_upper_bellman(model, query)
    return PortableRewardUpperProof(model.model_id, query.query_id, rows, root_upper)


def verify_portable_reward_upper_proof(
    model: PortableRAPM,
    query: PortableQuery,
    proof: PortableRewardUpperProof | Mapping[str, Any],
) -> PortableRewardUpperProof:
    """Replay the scalar proof without enumerating a value--risk frontier."""

    parsed = PortableRewardUpperProof.from_dict(
        proof.to_dict() if isinstance(proof, PortableRewardUpperProof) else dict(proof),
        model=model,
        query=query,
    )
    expected_rows, expected_root = _reward_upper_bellman(model, query)
    if parsed.rows != expected_rows or parsed.root_upper != expected_root:
        raise ValueError("portable reward-upper Bellman proof is false or incomplete")
    return parsed


def _pareto_prune(points: list[PortableParetoPoint]) -> tuple[PortableParetoPoint, ...]:
    unique: dict[tuple[Fraction, Fraction], PortableParetoPoint] = {}
    for point in points:
        key = (point.expected_reward, point.failure_probability)
        incumbent = unique.get(key)
        if incumbent is None or point.policy.signature() < incumbent.policy.signature():
            unique[key] = point
    candidates = list(unique.values())
    frontier: list[PortableParetoPoint] = []
    for point in candidates:
        dominated = any(
            other is not point
            and other.expected_reward >= point.expected_reward
            and other.failure_probability <= point.failure_probability
            and (
                other.expected_reward > point.expected_reward
                or other.failure_probability < point.failure_probability
            )
            for other in candidates
        )
        if not dominated:
            frontier.append(point)
    frontier.sort(
        key=lambda point: (
            point.failure_probability,
            -point.expected_reward,
            point.policy.signature(),
        )
    )
    return tuple(frontier)


def _select_constrained(
    frontier: tuple[PortableParetoPoint, ...], delta: Fraction
) -> PortableParetoPoint | None:
    feasible = [point for point in frontier if point.failure_probability <= delta]
    if not feasible:
        return None
    return min(
        feasible,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


@dataclass(frozen=True, slots=True)
class PortablePlanResult:
    model_id: str
    query_id: str
    frontier: tuple[PortableParetoPoint, ...]
    selected: PortableParetoPoint | None
    composed_candidate_count: int

    @property
    def feasible(self) -> bool:
        return self.selected is not None

    @property
    def result_id(self) -> str:
        return logical_id("plan-result", self._payload())

    def _payload(self) -> dict[str, Any]:
        selected_index = None
        if self.selected is not None:
            try:
                selected_index = self.frontier.index(self.selected)
            except ValueError as error:
                raise ValueError("selected Pareto point is absent from frontier") from error
        return {
            "schema": RESULT_SCHEMA,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "frontier": [point.to_dict() for point in self.frontier],
            "selected_index": selected_index,
            "composed_candidate_count": self.composed_candidate_count,
        }

    def to_dict(self) -> dict[str, Any]:
        document = self._payload()
        document["result_id"] = logical_id("plan-result", document)
        return document

    @classmethod
    def from_dict(
        cls,
        document: Any,
        *,
        model: PortableRAPM | None = None,
        query: PortableQuery | None = None,
    ) -> "PortablePlanResult":
        if not isinstance(document, dict):
            raise ValueError("portable plan result must be an object")
        clean = json.loads(canonical_json(document))
        expected_keys = {
            "schema",
            "model_id",
            "query_id",
            "frontier",
            "selected_index",
            "composed_candidate_count",
            "result_id",
        }
        if set(clean) != expected_keys or clean["schema"] != RESULT_SCHEMA:
            raise ValueError("portable plan result has invalid fields/schema")
        claimed_id = clean.pop("result_id")
        if claimed_id != logical_id("plan-result", clean):
            raise ValueError("portable plan result result_id mismatch")
        if not isinstance(clean["model_id"], str) or not isinstance(clean["query_id"], str):
            raise ValueError("portable plan result IDs must be strings")
        if model is not None and clean["model_id"] != model.model_id:
            raise ValueError("portable plan result/model mismatch")
        if query is not None:
            if clean["query_id"] != query.query_id:
                raise ValueError("portable plan result/query mismatch")
            if clean["model_id"] != query.model_id:
                raise ValueError("portable plan result uses query from another model")
        raw_frontier = clean["frontier"]
        if not isinstance(raw_frontier, list) or not raw_frontier:
            raise ValueError("portable plan frontier must be a nonempty list")
        frontier = tuple(PortableParetoPoint.from_dict(point) for point in raw_frontier)
        if frontier != _pareto_prune(list(frontier)):
            raise ValueError("portable plan frontier is not canonical/nondominated")
        selected_index = clean["selected_index"]
        if selected_index is not None and (
            isinstance(selected_index, bool)
            or not isinstance(selected_index, int)
            or selected_index < 0
            or selected_index >= len(frontier)
        ):
            raise ValueError("portable plan selected_index is invalid")
        count = clean["composed_candidate_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("portable plan candidate count must be nonnegative")
        selected = None if selected_index is None else frontier[selected_index]
        if query is not None:
            delta = fraction_from_json(query.to_dict()["delta"], field="query.delta")
            if selected != _select_constrained(frontier, delta):
                raise ValueError("portable plan selected point is inconsistent with query delta")
            _validate_policy_references(frontier, model, query)
        return cls(
            clean["model_id"],
            clean["query_id"],
            frontier,
            selected,
            count,
        )


def _validate_policy_references(
    frontier: tuple[PortableParetoPoint, ...],
    model: PortableRAPM | None,
    query: PortableQuery,
) -> None:
    if model is None:
        return
    document = model.to_dict()
    action_cells = {
        record["action_id"]: record["cell_id"]
        for record in document["semantic_action_catalog"]
    }
    for point in frontier:
        for decision in point.policy.decisions:
            if decision.remaining > query.horizon:
                raise ValueError("portable policy decision exceeds query horizon")
            if action_cells.get(decision.action_id) != decision.cell_id:
                raise ValueError("portable policy references an unknown or wrongly scoped action")


def solve_portable_pareto(
    model: PortableRAPM, query: PortableQuery
) -> PortablePlanResult:
    """Solve a finite-horizon deterministic-policy chance-constrained query."""

    if query.model_id != model.model_id:
        raise ValueError("portable query/model mismatch")
    # Re-validation catches an object constructed through an unexpected route
    # and gives a single binding check before planning.
    query = PortableQuery.from_dict(query.to_dict(), model)
    model_document = model.to_dict()
    query_document = query.to_dict()

    actions_by_cell: dict[str, tuple[str, ...]] = {}
    transitions: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in model_document["nominal"]:
        cell_id = entry["cell_id"]
        action_id = entry["action_id"]
        actions_by_cell.setdefault(cell_id, ())
        actions_by_cell[cell_id] = actions_by_cell[cell_id] + (action_id,)
        transitions[(cell_id, action_id)] = entry["model"]
    actions_by_cell = {
        cell_id: tuple(sorted(action_ids))
        for cell_id, action_ids in actions_by_cell.items()
    }
    weights = {
        record["name"]: fraction_from_json(
            record["value"], field=f"query weight {record['name']}"
        )
        for record in query_document["normalized_reward_weights"]
    }
    horizon = query.horizon
    Distribution = tuple[tuple[str, Fraction], ...]
    memo: dict[tuple[int, Distribution], tuple[PortableParetoPoint, ...]] = {}
    candidate_count = 0
    zero = PortableParetoPoint(Fraction(0), Fraction(0), EMPTY_POLICY)

    def canonical_distribution(masses: dict[str, Fraction]) -> Distribution:
        return tuple(sorted((cell, mass) for cell, mass in masses.items() if mass > 0))

    def frontier_for(
        distribution: Distribution, remaining: int
    ) -> tuple[PortableParetoPoint, ...]:
        nonlocal candidate_count
        key = (remaining, distribution)
        if key in memo:
            return memo[key]
        if remaining <= 0 or not distribution:
            memo[key] = (zero,)
            return memo[key]

        cell_mass = dict(distribution)
        decision_cells: list[str] = []
        action_sets: list[tuple[str, ...]] = []
        for cell_id, mass in distribution:
            if mass <= 0:
                continue
            actions = actions_by_cell.get(cell_id, ())
            if actions:
                decision_cells.append(cell_id)
                action_sets.append(actions)
        if not decision_cells:
            memo[key] = (zero,)
            return memo[key]

        candidates: list[PortableParetoPoint] = []
        for chosen_actions in product(*action_sets):
            immediate_reward = Fraction(0)
            immediate_failure = Fraction(0)
            successor_mass: dict[str, Fraction] = {}
            current_decisions: list[tuple[tuple[int, str], str]] = []
            for cell_id, action_id in zip(decision_cells, chosen_actions):
                mass = cell_mass[cell_id]
                transition = transitions[(cell_id, action_id)]
                current_decisions.append(((remaining, cell_id), action_id))
                reward_features = {
                    record["name"]: fraction_from_json(
                        record["value"], field="nominal reward feature"
                    )
                    for record in transition["reward_features"]
                }
                immediate_reward += mass * sum(
                    (
                        weights.get(name, Fraction(0)) * value
                        for name, value in reward_features.items()
                    ),
                    Fraction(0),
                )
                immediate_failure += mass * fraction_from_json(
                    transition["failure_probability"],
                    field="nominal failure probability",
                )
                for successor in transition["successor_probabilities"]:
                    successor_id = successor["cell_id"]
                    probability = fraction_from_json(
                        successor["probability"], field="nominal successor probability"
                    )
                    successor_mass[successor_id] = (
                        successor_mass.get(successor_id, Fraction(0))
                        + mass * probability
                    )

            continuation_frontier = frontier_for(
                canonical_distribution(successor_mass), remaining - 1
            )
            for continuation in continuation_frontier:
                candidate_count += 1
                mapping = continuation.policy.as_dict()
                conflict = False
                for decision_key, action_id in current_decisions:
                    incumbent = mapping.get(decision_key)
                    if incumbent is not None and incumbent != action_id:
                        conflict = True
                        break
                    mapping[decision_key] = action_id
                if conflict:
                    continue
                candidates.append(
                    PortableParetoPoint(
                        immediate_reward + continuation.expected_reward,
                        immediate_failure + continuation.failure_probability,
                        PortablePolicy.from_mapping(mapping),
                    )
                )
        memo[key] = _pareto_prune(candidates)
        return memo[key]

    initial_mass = {
        record["cell_id"]: fraction_from_json(
            record["probability"], field="query initial probability"
        )
        for record in query_document["initial_distribution"]
    }
    frontier = frontier_for(canonical_distribution(initial_mass), horizon)
    delta = fraction_from_json(query_document["delta"], field="query.delta")
    selected = _select_constrained(frontier, delta)
    result = PortablePlanResult(
        model.model_id,
        query.query_id,
        frontier,
        selected,
        candidate_count,
    )
    # Exercise all result invariants before returning a user-visible object.
    return PortablePlanResult.from_dict(
        result.to_dict(), model=model, query=query
    )


def audit_exact_portable_policy(
    model: PortableRAPM,
    query: PortableQuery,
    policy: PortablePolicy,
    *,
    regret_tolerance: Fraction = Fraction(1, 20),
) -> PortableExactEnvelopeAudit:
    """Audit an exact-behavioural policy without a simulator or nominal entries.

    Phase 3B deliberately uses a point-valued behavioural quotient.  This
    routine first proves that every state realization for each serialized
    cell/action has the same reward, stopping, failure, and successor payload;
    it then evaluates the policy from those envelope values.  The unrestricted
    reward upper bound is the maximum-reward point on the complete portable
    deterministic-policy frontier.
    """

    if query.model_id != model.model_id:
        raise ValueError("portable query/model mismatch")
    model = PortableRAPM.from_dict(model.to_dict())
    query = PortableQuery.from_dict(query.to_dict(), model)
    frontier = solve_portable_pareto(model, query).frontier
    unrestricted_reward_upper = max(
        (point.expected_reward for point in frontier), default=Fraction(0)
    )
    return audit_exact_portable_policy_with_frozen_upper(
        model,
        query,
        policy,
        unrestricted_reward_upper=unrestricted_reward_upper,
        regret_tolerance=regret_tolerance,
    )


def audit_exact_portable_policy_with_frozen_upper(
    model: PortableRAPM,
    query: PortableQuery,
    policy: PortablePolicy,
    *,
    unrestricted_reward_upper: Fraction | int,
    regret_tolerance: Fraction = Fraction(1, 20),
) -> PortableExactEnvelopeAudit:
    """Audit one policy against an already frozen sound reward upper bound.

    Unlike :func:`audit_exact_portable_policy`, this operational verifier does
    not solve the portable planning problem or reconstruct its frontier.  The
    caller must supply the content-bound upper produced before this validation
    step.  The routine only round-trips the serialized model/query, proves that
    the realization envelope is point-valued, and evaluates the supplied
    policy exactly against that envelope.
    """

    if query.model_id != model.model_id:
        raise ValueError("portable query/model mismatch")
    if isinstance(unrestricted_reward_upper, bool) or not isinstance(
        unrestricted_reward_upper, (int, Fraction)
    ):
        raise ValueError(
            "unrestricted_reward_upper must be an exact int or Fraction"
        )
    root_upper = Fraction(unrestricted_reward_upper)
    if root_upper < 0:
        raise ValueError("unrestricted_reward_upper must be nonnegative")
    if isinstance(regret_tolerance, bool) or not isinstance(
        regret_tolerance, (int, Fraction)
    ):
        raise ValueError("regret_tolerance must be an exact int or Fraction")
    regret_tolerance = Fraction(regret_tolerance)
    if regret_tolerance < 0:
        raise ValueError("regret_tolerance must be nonnegative")
    model = PortableRAPM.from_dict(model.to_dict())
    query = PortableQuery.from_dict(query.to_dict(), model)
    document = model.to_dict()
    query_document = query.to_dict()
    transitions: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in document["envelope"]:
        payloads = []
        for realization in entry["realizations"]:
            payloads.append(
                {
                    key: value
                    for key, value in realization.items()
                    if key != "state_id"
                }
            )
        if not payloads or any(payload != payloads[0] for payload in payloads[1:]):
            raise ValueError(
                "exact portable audit requires a point-valued realization envelope"
            )
        transitions[(entry["cell_id"], entry["action_id"])] = payloads[0]

    active_cells = {
        entry["cell_id"] for entry in document["nominal"]
    }
    weights = {
        record["name"]: fraction_from_json(
            record["value"], field="query normalized reward weight"
        )
        for record in query_document["normalized_reward_weights"]
    }
    decisions = policy.as_dict()
    visited: set[tuple[int, str]] = set()

    def evaluate(
        distribution: tuple[tuple[str, Fraction], ...], remaining: int
    ) -> tuple[Fraction, Fraction]:
        if remaining <= 0 or not distribution:
            return Fraction(0), Fraction(0)
        immediate_reward = Fraction(0)
        immediate_failure = Fraction(0)
        successor_mass: dict[str, Fraction] = {}
        for cell_id, mass in distribution:
            if cell_id not in active_cells:
                continue
            key = (remaining, cell_id)
            visited.add(key)
            try:
                action_id = decisions[key]
                transition = transitions[(cell_id, action_id)]
            except KeyError as error:
                raise ValueError(
                    "portable policy is undefined or unavailable at a reachable cell"
                ) from error
            feature_values = {
                feature["name"]: fraction_from_json(
                    feature["value"], field="envelope reward feature"
                )
                for feature in transition["reward_features"]
            }
            immediate_reward += mass * sum(
                (
                    weights.get(name, Fraction(0)) * value
                    for name, value in feature_values.items()
                ),
                Fraction(0),
            )
            immediate_failure += mass * fraction_from_json(
                transition["failure_probability"],
                field="envelope failure probability",
            )
            for successor in transition["successor_probabilities"]:
                successor_id = successor["cell_id"]
                probability = fraction_from_json(
                    successor["probability"],
                    field="envelope successor probability",
                )
                successor_mass[successor_id] = (
                    successor_mass.get(successor_id, Fraction(0))
                    + mass * probability
                )
        continuation_reward, continuation_failure = evaluate(
            tuple(
                sorted(
                    (cell, mass)
                    for cell, mass in successor_mass.items()
                    if mass > 0
                )
            ),
            remaining - 1,
        )
        return (
            immediate_reward + continuation_reward,
            immediate_failure + continuation_failure,
        )

    initial = tuple(
        (
            record["cell_id"],
            fraction_from_json(
                record["probability"], field="query initial probability"
            ),
        )
        for record in query_document["initial_distribution"]
    )
    expected_reward, failure_probability = evaluate(initial, query.horizon)
    if root_upper < expected_reward:
        raise ValueError(
            "unrestricted_reward_upper is below the audited policy reward"
        )
    regret_upper = root_upper - expected_reward
    risk_tolerance = fraction_from_json(query_document["delta"], field="query.delta")
    return PortableExactEnvelopeAudit(
        expected_reward,
        failure_probability,
        root_upper,
        regret_upper,
        regret_tolerance,
        risk_tolerance,
        len(visited),
        failure_probability <= risk_tolerance and regret_upper <= regret_tolerance,
    )


def dump_result(result: PortablePlanResult, path: str | Path) -> None:
    Path(path).write_text(canonical_json(result.to_dict()) + "\n", encoding="utf-8")


def load_result(
    path: str | Path,
    *,
    model: PortableRAPM | None = None,
    query: PortableQuery | None = None,
) -> PortablePlanResult:
    return PortablePlanResult.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8")),
        model=model,
        query=query,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Solve an exact query using only a portable ACFQP RAPM"
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--query", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    model = load_model(args.model)
    query = load_query(args.query, model)
    result = solve_portable_pareto(model, query)
    dump_result(result, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(main())


__all__ = [
    "REWARD_UPPER_FORMULA_ID",
    "REWARD_UPPER_PROOF_SCHEMA",
    "RESULT_SCHEMA",
    "PortableParetoPoint",
    "PortableExactEnvelopeAudit",
    "PortablePlanResult",
    "PortablePolicy",
    "PortablePolicyDecision",
    "PortableRewardUpperProof",
    "PortableRewardUpperRow",
    "build_portable_reward_upper_proof",
    "dump_result",
    "audit_exact_portable_policy",
    "audit_exact_portable_policy_with_frozen_upper",
    "load_result",
    "main",
    "solve_portable_pareto",
    "verify_portable_reward_upper_proof",
]
