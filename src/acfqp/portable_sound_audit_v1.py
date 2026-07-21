"""Sound, model-only policy certification for a serialized portable RAPM.

This module is intentionally on the far side of the ground-model boundary.  It
imports only the portable JSON model/query and portable policy types; no domain
kernel, ground state, concretizer callable, or ground planner is available.

The V1 proof uses the rectangular uncertainty semantics of the serialized
realization envelope:

* the unrestricted reward upper takes the maximum over semantic actions and
  over every realization row of that action;
* the supplied policy reward lower takes the minimum over its action's
  realization rows; and
* the supplied policy failure upper takes the maximum over those rows.

All three recurrences include the corresponding continuation bound.  Thus a
certificate remains sound when a quotient cell is not point valued.  The
portable model validator and an explicit coverage table jointly prove that
every active member of every cell has exactly one realization row for every
semantic action.  Missing policy decisions or incomplete realization coverage
fail closed before an audit artifact can be emitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Mapping

from acfqp.phase3e_ids import (
    ABSTRACT_PLAN_AUDIT_DOMAIN,
    PORTABLE_POLICY_BINDING_DOMAIN,
    PORTABLE_SOUND_BELLMAN_PROOF_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.portable import (
    PortableQuery,
    PortableRAPM,
    fraction_from_json,
    fraction_to_json,
)
from acfqp.portable_planner import PortablePolicy


SCHEMA_VERSION = "1.0.0"
SOUND_BELLMAN_FORMULA_ID = "portable_rectangular_realization_sound_bellman_v1"
SOUND_BELLMAN_PROOF_SCHEMA = "acfqp.portable_sound_bellman_proof.v1"
ABSTRACT_PLAN_AUDIT_SCHEMA = "acfqp.abstract_plan_audit.v1"

class PortableSoundAuditV1Error(ValueError):
    """The serialized evidence cannot establish the requested certificate."""


def _content_id(domain_tag: str, payload: Any) -> str:
    try:
        return content_id(domain_tag, payload)
    except ValueError as error:
        raise PortableSoundAuditV1Error(str(error)) from error


def _require_nonempty_string(value: Any, *, field: str) -> str:
    if type(value) is not str or not value:
        raise PortableSoundAuditV1Error(f"{field} must be a nonempty string")
    return value


def _require_bool(value: Any, *, field: str) -> bool:
    if type(value) is not bool:
        raise PortableSoundAuditV1Error(f"{field} must be a boolean")
    return value


def _require_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PortableSoundAuditV1Error(f"{field} must be a nonnegative integer")
    return value


def _fraction(value: Any, *, field: str) -> Fraction:
    try:
        return fraction_from_json(value, field=field)
    except ValueError as error:
        raise PortableSoundAuditV1Error(str(error)) from error


def _policy_id(policy: PortablePolicy) -> str:
    return _content_id(
        PORTABLE_POLICY_BINDING_DOMAIN,
        {
            "schema": "acfqp.portable_policy_binding.v1",
            "policy": policy.to_dict(),
        },
    )


@dataclass(frozen=True, order=True, slots=True)
class ActionRealizationCoverageRowV1:
    """Exact active-member coverage for one scoped semantic action."""

    cell_id: str
    action_id: str
    realization_state_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.cell_id, field="coverage.cell_id")
        _require_nonempty_string(self.action_id, field="coverage.action_id")
        if (
            not self.realization_state_ids
            or self.realization_state_ids
            != tuple(sorted(set(self.realization_state_ids)))
            or any(type(item) is not str or not item for item in self.realization_state_ids)
        ):
            raise PortableSoundAuditV1Error(
                "coverage realization_state_ids must be nonempty, unique, and sorted"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "action_id": self.action_id,
            "realization_state_ids": list(self.realization_state_ids),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ActionRealizationCoverageRowV1":
        require_exact_fields(
            document,
            {"cell_id", "action_id", "realization_state_ids"},
            context="action-realization coverage row",
        )
        raw_ids = document["realization_state_ids"]
        if not isinstance(raw_ids, list):
            raise PortableSoundAuditV1Error(
                "coverage realization_state_ids must be a list"
            )
        return cls(
            _require_nonempty_string(document["cell_id"], field="coverage.cell_id"),
            _require_nonempty_string(document["action_id"], field="coverage.action_id"),
            tuple(raw_ids),
        )


@dataclass(frozen=True, order=True, slots=True)
class UnrestrictedRewardUpperRowV1:
    remaining: int
    cell_id: str
    reward_upper: Fraction

    def __post_init__(self) -> None:
        if isinstance(self.remaining, bool) or not isinstance(self.remaining, int) or self.remaining <= 0:
            raise PortableSoundAuditV1Error("upper row remaining must be positive")
        _require_nonempty_string(self.cell_id, field="upper row cell_id")
        if not isinstance(self.reward_upper, Fraction) or self.reward_upper < 0:
            raise PortableSoundAuditV1Error("upper row reward must be a nonnegative Fraction")

    def to_dict(self) -> dict[str, Any]:
        return {
            "remaining": self.remaining,
            "cell_id": self.cell_id,
            "reward_upper": fraction_to_json(self.reward_upper),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "UnrestrictedRewardUpperRowV1":
        require_exact_fields(
            document,
            {"remaining", "cell_id", "reward_upper"},
            context="unrestricted reward-upper row",
        )
        return cls(
            document["remaining"],
            _require_nonempty_string(document["cell_id"], field="upper row cell_id"),
            _fraction(document["reward_upper"], field="upper row reward_upper"),
        )


@dataclass(frozen=True, order=True, slots=True)
class PolicySoundBoundRowV1:
    remaining: int
    cell_id: str
    action_id: str
    reward_lower: Fraction
    failure_upper: Fraction

    def __post_init__(self) -> None:
        if isinstance(self.remaining, bool) or not isinstance(self.remaining, int) or self.remaining <= 0:
            raise PortableSoundAuditV1Error("policy row remaining must be positive")
        _require_nonempty_string(self.cell_id, field="policy row cell_id")
        _require_nonempty_string(self.action_id, field="policy row action_id")
        if not isinstance(self.reward_lower, Fraction) or self.reward_lower < 0:
            raise PortableSoundAuditV1Error("policy reward lower must be nonnegative")
        if (
            not isinstance(self.failure_upper, Fraction)
            or self.failure_upper < 0
            or self.failure_upper > 1
        ):
            raise PortableSoundAuditV1Error("policy failure upper must lie in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "remaining": self.remaining,
            "cell_id": self.cell_id,
            "action_id": self.action_id,
            "reward_lower": fraction_to_json(self.reward_lower),
            "failure_upper": fraction_to_json(self.failure_upper),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "PolicySoundBoundRowV1":
        require_exact_fields(
            document,
            {"remaining", "cell_id", "action_id", "reward_lower", "failure_upper"},
            context="policy sound-bound row",
        )
        return cls(
            document["remaining"],
            _require_nonempty_string(document["cell_id"], field="policy row cell_id"),
            _require_nonempty_string(document["action_id"], field="policy row action_id"),
            _fraction(document["reward_lower"], field="policy row reward_lower"),
            _fraction(document["failure_upper"], field="policy row failure_upper"),
        )


@dataclass(frozen=True, slots=True)
class PortableSoundBellmanProofV1:
    model_id: str
    query_id: str
    policy_id: str
    coverage_rows: tuple[ActionRealizationCoverageRowV1, ...]
    unrestricted_rows: tuple[UnrestrictedRewardUpperRowV1, ...]
    policy_rows: tuple[PolicySoundBoundRowV1, ...]
    unrestricted_reward_upper: Fraction
    policy_reward_lower: Fraction
    policy_failure_upper: Fraction

    def __post_init__(self) -> None:
        _require_nonempty_string(self.model_id, field="proof.model_id")
        _require_nonempty_string(self.query_id, field="proof.query_id")
        parse_content_id(self.policy_id)
        if self.coverage_rows != tuple(sorted(set(self.coverage_rows))):
            raise PortableSoundAuditV1Error("coverage rows must be unique and sorted")
        if self.unrestricted_rows != tuple(sorted(set(self.unrestricted_rows))):
            raise PortableSoundAuditV1Error("unrestricted rows must be unique and sorted")
        if self.policy_rows != tuple(sorted(set(self.policy_rows))):
            raise PortableSoundAuditV1Error("policy rows must be unique and sorted")
        if self.unrestricted_reward_upper < 0 or self.policy_reward_lower < 0:
            raise PortableSoundAuditV1Error("root reward bounds must be nonnegative")
        if not 0 <= self.policy_failure_upper <= 1:
            raise PortableSoundAuditV1Error("root policy failure upper must lie in [0, 1]")
        if self.unrestricted_reward_upper < self.policy_reward_lower:
            raise PortableSoundAuditV1Error(
                "unrestricted reward upper is below policy reward lower"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOUND_BELLMAN_PROOF_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "formula_id": SOUND_BELLMAN_FORMULA_ID,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "policy_id": self.policy_id,
            "coverage_rows": [row.to_dict() for row in self.coverage_rows],
            "unrestricted_rows": [row.to_dict() for row in self.unrestricted_rows],
            "policy_rows": [row.to_dict() for row in self.policy_rows],
            "unrestricted_reward_upper": fraction_to_json(
                self.unrestricted_reward_upper
            ),
            "policy_reward_lower": fraction_to_json(self.policy_reward_lower),
            "policy_failure_upper": fraction_to_json(self.policy_failure_upper),
        }

    @property
    def proof_id(self) -> str:
        return _content_id(PORTABLE_SOUND_BELLMAN_PROOF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "PortableSoundBellmanProofV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "formula_id",
                "model_id",
                "query_id",
                "policy_id",
                "coverage_rows",
                "unrestricted_rows",
                "policy_rows",
                "unrestricted_reward_upper",
                "policy_reward_lower",
                "policy_failure_upper",
                "proof_id",
            },
            context="portable sound Bellman proof",
        )
        if (
            document["schema"] != SOUND_BELLMAN_PROOF_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
            or document["formula_id"] != SOUND_BELLMAN_FORMULA_ID
        ):
            raise PortableSoundAuditV1Error("unsupported sound Bellman proof")
        for field in ("coverage_rows", "unrestricted_rows", "policy_rows"):
            if not isinstance(document[field], list):
                raise PortableSoundAuditV1Error(f"proof {field} must be a list")
        proof = cls(
            _require_nonempty_string(document["model_id"], field="proof.model_id"),
            _require_nonempty_string(document["query_id"], field="proof.query_id"),
            parse_content_id(document["policy_id"]),
            tuple(
                ActionRealizationCoverageRowV1.from_dict(row)
                for row in document["coverage_rows"]
            ),
            tuple(
                UnrestrictedRewardUpperRowV1.from_dict(row)
                for row in document["unrestricted_rows"]
            ),
            tuple(
                PolicySoundBoundRowV1.from_dict(row)
                for row in document["policy_rows"]
            ),
            _fraction(
                document["unrestricted_reward_upper"],
                field="proof unrestricted_reward_upper",
            ),
            _fraction(
                document["policy_reward_lower"], field="proof policy_reward_lower"
            ),
            _fraction(
                document["policy_failure_upper"], field="proof policy_failure_upper"
            ),
        )
        if parse_content_id(document["proof_id"]) != proof.proof_id:
            raise PortableSoundAuditV1Error("sound Bellman proof content ID mismatch")
        return proof


@dataclass(frozen=True, slots=True)
class AbstractPlanAuditV1:
    model_id: str
    query_id: str
    policy_id: str
    proof_id: str
    unrestricted_reward_upper: Fraction
    policy_reward_lower: Fraction
    policy_failure_upper: Fraction
    regret_upper: Fraction
    regret_tolerance: Fraction
    risk_tolerance: Fraction
    reachable_cell_horizon_pairs: int
    action_realization_complete: bool
    outcome: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.model_id, field="audit.model_id")
        _require_nonempty_string(self.query_id, field="audit.query_id")
        parse_content_id(self.policy_id)
        parse_content_id(self.proof_id)
        for name, value in (
            ("unrestricted_reward_upper", self.unrestricted_reward_upper),
            ("policy_reward_lower", self.policy_reward_lower),
            ("regret_upper", self.regret_upper),
            ("regret_tolerance", self.regret_tolerance),
        ):
            if not isinstance(value, Fraction) or value < 0:
                raise PortableSoundAuditV1Error(f"audit {name} must be nonnegative")
        for name, value in (
            ("policy_failure_upper", self.policy_failure_upper),
            ("risk_tolerance", self.risk_tolerance),
        ):
            if not isinstance(value, Fraction) or not 0 <= value <= 1:
                raise PortableSoundAuditV1Error(f"audit {name} must lie in [0, 1]")
        _require_nonnegative_int(
            self.reachable_cell_horizon_pairs,
            field="audit.reachable_cell_horizon_pairs",
        )
        _require_bool(
            self.action_realization_complete,
            field="audit.action_realization_complete",
        )
        if self.outcome not in {"PASS", "FAIL"}:
            raise PortableSoundAuditV1Error("audit outcome must be PASS or FAIL")
        expected = (
            "PASS"
            if self.action_realization_complete
            and self.regret_upper <= self.regret_tolerance
            and self.policy_failure_upper <= self.risk_tolerance
            else "FAIL"
        )
        if self.outcome != expected:
            raise PortableSoundAuditV1Error("audit outcome is inconsistent with bounds")

    @property
    def certified(self) -> bool:
        return self.outcome == "PASS"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ABSTRACT_PLAN_AUDIT_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "policy_id": self.policy_id,
            "proof_id": self.proof_id,
            "unrestricted_reward_upper": fraction_to_json(
                self.unrestricted_reward_upper
            ),
            "policy_reward_lower": fraction_to_json(self.policy_reward_lower),
            "policy_failure_upper": fraction_to_json(self.policy_failure_upper),
            "regret_upper": fraction_to_json(self.regret_upper),
            "regret_tolerance": fraction_to_json(self.regret_tolerance),
            "risk_tolerance": fraction_to_json(self.risk_tolerance),
            "reachable_cell_horizon_pairs": self.reachable_cell_horizon_pairs,
            "action_realization_complete": self.action_realization_complete,
            "outcome": self.outcome,
        }

    @property
    def audit_id(self) -> str:
        return _content_id(ABSTRACT_PLAN_AUDIT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "AbstractPlanAuditV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "model_id",
                "query_id",
                "policy_id",
                "proof_id",
                "unrestricted_reward_upper",
                "policy_reward_lower",
                "policy_failure_upper",
                "regret_upper",
                "regret_tolerance",
                "risk_tolerance",
                "reachable_cell_horizon_pairs",
                "action_realization_complete",
                "outcome",
                "audit_id",
            },
            context="abstract plan audit",
        )
        if (
            document["schema"] != ABSTRACT_PLAN_AUDIT_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise PortableSoundAuditV1Error("unsupported abstract plan audit")
        audit = cls(
            _require_nonempty_string(document["model_id"], field="audit.model_id"),
            _require_nonempty_string(document["query_id"], field="audit.query_id"),
            parse_content_id(document["policy_id"]),
            parse_content_id(document["proof_id"]),
            _fraction(
                document["unrestricted_reward_upper"],
                field="audit unrestricted_reward_upper",
            ),
            _fraction(document["policy_reward_lower"], field="audit policy_reward_lower"),
            _fraction(document["policy_failure_upper"], field="audit policy_failure_upper"),
            _fraction(document["regret_upper"], field="audit regret_upper"),
            _fraction(document["regret_tolerance"], field="audit regret_tolerance"),
            _fraction(document["risk_tolerance"], field="audit risk_tolerance"),
            _require_nonnegative_int(
                document["reachable_cell_horizon_pairs"],
                field="audit.reachable_cell_horizon_pairs",
            ),
            _require_bool(
                document["action_realization_complete"],
                field="audit.action_realization_complete",
            ),
            _require_nonempty_string(document["outcome"], field="audit.outcome"),
        )
        if parse_content_id(document["audit_id"]) != audit.audit_id:
            raise PortableSoundAuditV1Error("abstract plan audit content ID mismatch")
        return audit


def _reward(realization: Mapping[str, Any], weights: Mapping[str, Fraction]) -> Fraction:
    features = {
        item["name"]: fraction_from_json(
            item["value"], field="realization reward feature"
        )
        for item in realization["reward_features"]
    }
    return sum(
        (weights.get(name, Fraction(0)) * value for name, value in features.items()),
        Fraction(0),
    )


def _build_proof(
    model: PortableRAPM,
    query: PortableQuery,
    policy: PortablePolicy,
    *,
    operation_counter: Callable[[str, int], None] | None = None,
) -> PortableSoundBellmanProofV1:
    model = PortableRAPM.from_dict(model.to_dict())
    query = PortableQuery.from_dict(query.to_dict(), model)
    document = model.to_dict()
    query_document = query.to_dict()

    state_kind = {
        row["state_id"]: row["planning_kind"] for row in document["state_catalog"]
    }
    members_by_cell = {
        row["cell_id"]: tuple(row["member_state_ids"])
        for row in document["partition"]
    }
    active_cells = {
        cell_id
        for cell_id, members in members_by_cell.items()
        if all(state_kind[state_id] == "active" for state_id in members)
    }
    actions_by_cell: dict[str, list[str]] = {}
    action_owner: dict[str, str] = {}
    for row in document["semantic_action_catalog"]:
        actions_by_cell.setdefault(row["cell_id"], []).append(row["action_id"])
        action_owner[row["action_id"]] = row["cell_id"]
    actions_by_cell = {
        cell_id: sorted(action_ids)
        for cell_id, action_ids in actions_by_cell.items()
    }
    envelope: dict[tuple[str, str], tuple[Mapping[str, Any], ...]] = {}
    coverage_rows: list[ActionRealizationCoverageRowV1] = []
    for row in document["envelope"]:
        key = (row["cell_id"], row["action_id"])
        realizations = tuple(row["realizations"])
        state_ids = tuple(realization["state_id"] for realization in realizations)
        expected = tuple(
            state_id
            for state_id in members_by_cell[row["cell_id"]]
            if state_kind[state_id] == "active"
        )
        if state_ids != expected:
            raise PortableSoundAuditV1Error(
                "semantic action realization rows do not exactly cover active cell members"
            )
        envelope[key] = realizations
        coverage_rows.append(
            ActionRealizationCoverageRowV1(row["cell_id"], row["action_id"], state_ids)
        )
        if operation_counter is not None:
            operation_counter("common.abstract_audit_obligations", 1)
    expected_keys = {
        (cell_id, action_id)
        for cell_id, action_ids in actions_by_cell.items()
        for action_id in action_ids
    }
    if set(envelope) != expected_keys or set(actions_by_cell) != active_cells:
        raise PortableSoundAuditV1Error(
            "action-realization coverage is incomplete for the active quotient"
        )

    weights = {
        row["name"]: fraction_from_json(
            row["value"], field="query normalized reward weight"
        )
        for row in query_document["normalized_reward_weights"]
    }
    upper: dict[tuple[int, str], Fraction] = {}
    unrestricted_rows: list[UnrestrictedRewardUpperRowV1] = []
    for remaining in range(1, query.horizon + 1):
        for cell_id in sorted(active_cells):
            candidates: list[Fraction] = []
            for action_id in actions_by_cell[cell_id]:
                for realization in envelope[(cell_id, action_id)]:
                    value = _reward(realization, weights)
                    if remaining > 1:
                        value += sum(
                            (
                                fraction_from_json(
                                    successor["probability"],
                                    field="realization successor probability",
                                )
                                * upper.get(
                                    (remaining - 1, successor["cell_id"]),
                                    Fraction(0),
                                )
                                for successor in realization["successor_probabilities"]
                            ),
                            Fraction(0),
                        )
                    candidates.append(value)
            if not candidates:
                raise PortableSoundAuditV1Error(
                    "active cell has no complete semantic action realization"
                )
            value = max(candidates)
            upper[(remaining, cell_id)] = value
            unrestricted_rows.append(
                UnrestrictedRewardUpperRowV1(remaining, cell_id, value)
            )
            if operation_counter is not None:
                operation_counter("common.abstract_bellman_backups", 1)
                operation_counter("common.abstract_audit_obligations", 1)

    decisions = policy.as_dict()
    for decision in policy.decisions:
        if decision.remaining > query.horizon:
            raise PortableSoundAuditV1Error("policy decision exceeds query horizon")
        if action_owner.get(decision.action_id) != decision.cell_id:
            raise PortableSoundAuditV1Error(
                "policy references an unknown or wrongly scoped semantic action"
            )

    reachable: dict[int, set[str]] = {remaining: set() for remaining in range(1, query.horizon + 1)}
    for row in query_document["initial_distribution"]:
        cell_id = row["cell_id"]
        if cell_id in active_cells:
            reachable[query.horizon].add(cell_id)
    for remaining in range(query.horizon, 0, -1):
        for cell_id in sorted(reachable[remaining]):
            action_id = decisions.get((remaining, cell_id))
            if action_id is None or (cell_id, action_id) not in envelope:
                raise PortableSoundAuditV1Error(
                    "portable policy is undefined or unavailable at a reachable cell"
                )
            if remaining > 1:
                for realization in envelope[(cell_id, action_id)]:
                    for successor in realization["successor_probabilities"]:
                        if (
                            fraction_from_json(
                                successor["probability"],
                                field="realization successor probability",
                            )
                            > 0
                            and successor["cell_id"] in active_cells
                        ):
                            reachable[remaining - 1].add(successor["cell_id"])

    lower: dict[tuple[int, str], Fraction] = {}
    failure: dict[tuple[int, str], Fraction] = {}
    policy_rows: list[PolicySoundBoundRowV1] = []
    for remaining in range(1, query.horizon + 1):
        for cell_id in sorted(reachable[remaining]):
            action_id = decisions[(remaining, cell_id)]
            reward_candidates: list[Fraction] = []
            failure_candidates: list[Fraction] = []
            for realization in envelope[(cell_id, action_id)]:
                reward_value = _reward(realization, weights)
                failure_value = fraction_from_json(
                    realization["failure_probability"],
                    field="realization failure probability",
                )
                if remaining > 1:
                    for successor in realization["successor_probabilities"]:
                        probability = fraction_from_json(
                            successor["probability"],
                            field="realization successor probability",
                        )
                        successor_id = successor["cell_id"]
                        if successor_id in active_cells and probability > 0:
                            try:
                                reward_value += probability * lower[
                                    (remaining - 1, successor_id)
                                ]
                                failure_value += probability * failure[
                                    (remaining - 1, successor_id)
                                ]
                            except KeyError as error:
                                raise PortableSoundAuditV1Error(
                                    "policy reachability proof is incomplete"
                                ) from error
                reward_candidates.append(reward_value)
                failure_candidates.append(failure_value)
            reward_lower = min(reward_candidates)
            failure_upper = max(failure_candidates)
            if failure_upper > 1:
                raise PortableSoundAuditV1Error(
                    "policy failure Bellman bound exceeds probability one"
                )
            lower[(remaining, cell_id)] = reward_lower
            failure[(remaining, cell_id)] = failure_upper
            policy_rows.append(
                PolicySoundBoundRowV1(
                    remaining,
                    cell_id,
                    action_id,
                    reward_lower,
                    failure_upper,
                )
            )
            if operation_counter is not None:
                operation_counter("common.abstract_bellman_backups", 1)
                operation_counter("common.abstract_audit_obligations", 1)

    root_upper = Fraction(0)
    root_lower = Fraction(0)
    root_failure = Fraction(0)
    for row in query_document["initial_distribution"]:
        probability = fraction_from_json(
            row["probability"], field="query initial probability"
        )
        cell_id = row["cell_id"]
        if cell_id in active_cells:
            root_upper += probability * upper[(query.horizon, cell_id)]
            root_lower += probability * lower[(query.horizon, cell_id)]
            root_failure += probability * failure[(query.horizon, cell_id)]

    return PortableSoundBellmanProofV1(
        model.model_id,
        query.query_id,
        _policy_id(policy),
        tuple(sorted(coverage_rows)),
        tuple(sorted(unrestricted_rows)),
        tuple(sorted(policy_rows)),
        root_upper,
        root_lower,
        root_failure,
    )


def build_portable_sound_audit_v1(
    model: PortableRAPM,
    query: PortableQuery,
    policy: PortablePolicy,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
    operation_counter: Callable[[str, int], None] | None = None,
) -> tuple[PortableSoundBellmanProofV1, AbstractPlanAuditV1]:
    """Build a replayable proof and strict abstract-plan audit artifact."""

    if query.model_id != model.model_id:
        raise PortableSoundAuditV1Error("portable query/model mismatch")
    if isinstance(regret_tolerance, bool) or not isinstance(
        regret_tolerance, (int, Fraction)
    ):
        raise PortableSoundAuditV1Error("regret_tolerance must be exact")
    tolerance = Fraction(regret_tolerance)
    if tolerance < 0:
        raise PortableSoundAuditV1Error("regret_tolerance must be nonnegative")
    proof = _build_proof(
        model, query, policy, operation_counter=operation_counter
    )
    query_document = PortableQuery.from_dict(query.to_dict(), model).to_dict()
    risk_tolerance = fraction_from_json(query_document["delta"], field="query.delta")
    regret = proof.unrestricted_reward_upper - proof.policy_reward_lower
    outcome = (
        "PASS"
        if regret <= tolerance and proof.policy_failure_upper <= risk_tolerance
        else "FAIL"
    )
    audit = AbstractPlanAuditV1(
        proof.model_id,
        proof.query_id,
        proof.policy_id,
        proof.proof_id,
        proof.unrestricted_reward_upper,
        proof.policy_reward_lower,
        proof.policy_failure_upper,
        regret,
        tolerance,
        risk_tolerance,
        len(proof.policy_rows),
        True,
        outcome,
    )
    if operation_counter is not None:
        # Coverage completeness, regret and risk are three distinct terminal
        # proof obligations, evaluated after the Bellman tables exist.
        operation_counter("common.abstract_audit_obligations", 3)
    return proof, audit


def verify_portable_sound_audit_v1(
    model: PortableRAPM,
    query: PortableQuery,
    policy: PortablePolicy,
    proof: PortableSoundBellmanProofV1 | Mapping[str, Any],
    audit: AbstractPlanAuditV1 | Mapping[str, Any],
    *,
    operation_counter: Callable[[str, int], None] | None = None,
) -> AbstractPlanAuditV1:
    """Replay every coverage/Bellman row and reject re-signed false evidence."""

    parsed_proof = PortableSoundBellmanProofV1.from_dict(
        proof.to_dict() if isinstance(proof, PortableSoundBellmanProofV1) else proof
    )
    parsed_audit = AbstractPlanAuditV1.from_dict(
        audit.to_dict() if isinstance(audit, AbstractPlanAuditV1) else audit
    )
    expected_proof, expected_audit = build_portable_sound_audit_v1(
        model,
        query,
        policy,
        regret_tolerance=parsed_audit.regret_tolerance,
        operation_counter=operation_counter,
    )
    if parsed_proof.to_dict() != expected_proof.to_dict():
        raise PortableSoundAuditV1Error(
            "sound Bellman proof is false, incomplete, or bound to another input"
        )
    if parsed_audit.to_dict() != expected_audit.to_dict():
        raise PortableSoundAuditV1Error(
            "abstract plan audit is false or inconsistent with its Bellman proof"
        )
    return parsed_audit


__all__ = [
    "ABSTRACT_PLAN_AUDIT_DOMAIN",
    "ABSTRACT_PLAN_AUDIT_SCHEMA",
    "PORTABLE_POLICY_BINDING_DOMAIN",
    "PORTABLE_SOUND_BELLMAN_PROOF_DOMAIN",
    "SCHEMA_VERSION",
    "SOUND_BELLMAN_FORMULA_ID",
    "SOUND_BELLMAN_PROOF_SCHEMA",
    "AbstractPlanAuditV1",
    "ActionRealizationCoverageRowV1",
    "PolicySoundBoundRowV1",
    "PortableSoundAuditV1Error",
    "PortableSoundBellmanProofV1",
    "UnrestrictedRewardUpperRowV1",
    "build_portable_sound_audit_v1",
    "verify_portable_sound_audit_v1",
]
