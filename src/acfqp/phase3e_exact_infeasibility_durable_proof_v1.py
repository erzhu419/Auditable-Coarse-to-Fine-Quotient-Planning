"""Durable exact-infeasibility proof for the canonical G2048 fixture.

This additive, non-retroactive authority closes the portability gap left by
``phase3e_exact_cache_v1``.  A historical ``GroundFallbackResultV1`` binds an
exact frontier but its completeness statement is protected only by a live
process seal.  It is therefore *not* a durable proof source.  The canonical
Phase-0.5 G2048 regression additionally retains a complete state/action/
transition enumeration.  This module projects that evidence into a
self-contained proof and independently replays the finite H=1 deterministic
Markov policy problem from its bytes.

The independent verifier does not invoke the producer, the Phase-0.5 runner,
J0, ``solve_ground_pareto``, or the ground-fallback solver.  It implements the
narrow registered 2x2 G2048 transition law directly, verifies exhaustive
action closure for every initial state, enumerates every deterministic policy,
and recomputes the exact Pareto frontier with :class:`fractions.Fraction`.

No status string is proof.  ``CAP_EXHAUSTED`` is always a noncertificate, and
the legacy plan-frozen cache may only bind the owner-bound handle returned by
the independent verifier.  All official/economics/sample-efficiency gates
remain locked.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
from typing import Any, Mapping, Sequence

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
)
from acfqp.artifacts import sha256_file, verify_artifact_bundle
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    PHASE3E_EXACT_INFEASIBILITY_BLOCKER_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_CACHE_CONSUMPTION_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_DURABLE_PROOF_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_STATE_ACTION_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_STATE_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_PROFILE_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_V1_DOMAIN,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.34"
FIXTURE_KEY = "g2048_select_canonical_2x2_v0"

PROOF_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_DURABLE_PROOF_V1_DOMAIN
IDENTITY_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN
STRUCTURAL_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN
QUERY_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN
KERNEL_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN
BUILD_EPOCH_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN
THRESHOLD_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN
REWARD_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN
POLICY_CLASS_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN
SEARCH_PROFILE_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN
STATE_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_STATE_V1_DOMAIN
ACTION_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_STATE_ACTION_V1_DOMAIN
SOURCE_PROJECTION_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_PROFILE_V1_DOMAIN
VERIFICATION_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_V1_DOMAIN
CACHE_CONSUMPTION_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_CACHE_CONSUMPTION_V1_DOMAIN
BLOCKER_DOMAIN = PHASE3E_EXACT_INFEASIBILITY_BLOCKER_V1_DOMAIN

_DOMAINS = frozenset(
    {
        PROOF_DOMAIN,
        IDENTITY_DOMAIN,
        STRUCTURAL_DOMAIN,
        QUERY_DOMAIN,
        KERNEL_DOMAIN,
        BUILD_EPOCH_DOMAIN,
        THRESHOLD_DOMAIN,
        REWARD_DOMAIN,
        POLICY_CLASS_DOMAIN,
        SEARCH_PROFILE_DOMAIN,
        STATE_DOMAIN,
        ACTION_DOMAIN,
        SOURCE_PROJECTION_DOMAIN,
        VERIFICATION_PROFILE_DOMAIN,
        VERIFICATION_DOMAIN,
        CACHE_CONSUMPTION_DOMAIN,
        BLOCKER_DOMAIN,
    }
)
if not _DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("durable exact-infeasibility domains must be centrally registered")

_VERIFIER_AUTHORITY = object()


class DurableExactInfeasibilityV1Error(ValueError):
    """The durable proof, source evidence, or cache binding is invalid."""


class DurableProofVerificationOutcomeV1(str, Enum):
    IDENTICAL_MATCH = "IDENTICAL_MATCH"
    NO_MATCH = "NO_MATCH"
    INVALID = "INVALID"


def _id(domain: str, payload: Any) -> str:
    """Return one centrally registered, domain-separated exact identity."""

    if domain not in _DOMAINS:
        raise DurableExactInfeasibilityV1Error(
            f"unregistered durable-proof domain: {domain!r}"
        )
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DurableExactInfeasibilityV1Error(
            f"{name} must be a full lowercase SHA-256 content ID"
        ) from error


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    if type(document) is not dict:
        raise DurableExactInfeasibilityV1Error(f"{context} must be an object")
    present = set(document)
    if present != expected:
        missing = sorted(expected - present)
        extra = sorted(present - expected)
        raise DurableExactInfeasibilityV1Error(
            f"{context} fields mismatch; missing={missing}, extra={extra}"
        )


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DurableExactInfeasibilityV1Error(
            f"{name} must be an exact integer >= {minimum}"
        )
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        numerator = value["numerator"]
        denominator = value["denominator"]
        if type(numerator) is int and type(denominator) is int and denominator > 0:
            return Fraction(numerator, denominator)
    raise DurableExactInfeasibilityV1Error(f"{name} must be a reduced rational")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DurableExactInfeasibilityV1Error(
            f"cannot read exact source document {path}: {error}"
        ) from error
    if type(value) is not dict:
        raise DurableExactInfeasibilityV1Error(
            f"exact source document {path} must be an object"
        )
    return value


def _state_payload(board: Sequence[Any], status: Any) -> dict[str, Any]:
    if type(board) not in {list, tuple} or len(board) != 4:
        raise DurableExactInfeasibilityV1Error("G2048 state board must have four cells")
    cells = tuple(_integer(value, "board rank") for value in board)
    if any(value > 6 for value in cells):
        raise DurableExactInfeasibilityV1Error("G2048 rank exceeds the registered cap")
    if status not in {"active", "failure"}:
        raise DurableExactInfeasibilityV1Error("invalid G2048 state status")
    return {"board": list(cells), "status": status}


def _state_id(state: Mapping[str, Any]) -> str:
    return _id(STATE_DOMAIN, dict(state))


def _action_payload(value: Mapping[str, Any]) -> dict[str, int]:
    _fields(value, {"first", "second", "survivor"}, "G2048 action")
    first = _integer(value["first"], "action.first")
    second = _integer(value["second"], "action.second")
    survivor = _integer(value["survivor"], "action.survivor")
    if not (0 <= first < second < 4) or survivor not in (first, second):
        raise DurableExactInfeasibilityV1Error("invalid canonical G2048 action")
    return {"first": first, "second": second, "survivor": survivor}


def _action_key(action: Mapping[str, int]) -> tuple[int, int, int]:
    return action["first"], action["second"], action["survivor"]


def _action_id(state_id: str, action: Mapping[str, int]) -> str:
    return _id(
        ACTION_DOMAIN,
        {"state_id": state_id, "action": dict(action)},
    )


def _is_adjacent(first: int, second: int) -> bool:
    row_a, col_a = divmod(first, 2)
    row_b, col_b = divmod(second, 2)
    return abs(row_a - row_b) + abs(col_a - col_b) == 1


def _legal_actions(board: tuple[int, ...], status: str) -> tuple[dict[str, int], ...]:
    if status != "active":
        return ()
    result: list[dict[str, int]] = []
    for first, second in combinations(range(4), 2):
        if (
            _is_adjacent(first, second)
            and board[first] != 0
            and board[first] == board[second]
        ):
            result.extend(
                (
                    {"first": first, "second": second, "survivor": first},
                    {"first": first, "second": second, "survivor": second},
                )
            )
    return tuple(result)


def _semantic_outcomes(
    state: Mapping[str, Any], action: Mapping[str, int]
) -> tuple[dict[str, Any], ...]:
    """Independent implementation of the registered canonical 2x2 law."""

    board = tuple(state["board"])
    status = state["status"]
    action = _action_payload(action)
    if action not in _legal_actions(board, status):
        raise DurableExactInfeasibilityV1Error("transition uses an illegal action")
    rank = board[action["first"]]
    merged = list(board)
    merged[action["first"]] = 0
    merged[action["second"]] = 0
    merged[action["survivor"]] = min(rank + 1, 6)
    empty = tuple(index for index, value in enumerate(merged) if value == 0)
    reward = Fraction(2 ** (rank + 1), 2 ** 7)
    rows: list[dict[str, Any]] = []
    for cell in empty:
        for spawn_rank, rank_probability in (
            (1, Fraction(9, 10)),
            (2, Fraction(1, 10)),
        ):
            next_board = merged.copy()
            next_board[cell] = spawn_rank
            failed = not _legal_actions(tuple(next_board), "active")
            next_state = {
                "board": next_board,
                "status": "failure" if failed else "active",
            }
            rows.append(
                {
                    "probability": Fraction(1, len(empty)) * rank_probability,
                    "next_state": next_state,
                    "reward": reward,
                    "failure": failed,
                    "terminal": failed,
                }
            )
    rows.sort(
        key=lambda row: (
            _state_id(row["next_state"]),
            row["probability"],
            row["failure"],
        )
    )
    if sum((row["probability"] for row in rows), Fraction(0)) != 1:
        raise AssertionError("registered G2048 law did not normalize")
    return tuple(rows)


def _structural_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.phase3e_exact_infeasibility_structural.v1",
        "schema_version": SCHEMA_VERSION,
        "structural_key": FIXTURE_KEY,
        "board_geometry": "orthogonal_2x2",
        "rank_set": [1, 2, 3, 4, 5, 6],
        "empty_rank": 0,
        "ground_action": "one_adjacent_equal_pair_with_chosen_survivor",
        "merge_rank": "min(rank+1,6)",
        "merges_per_step": 1,
        "spawn_timing": "after_every_valid_merge",
        "spawn_count": 1,
        "spawn_rank_distribution": [
            {"rank": 1, "probability": Fraction(9, 10)},
            {"rank": 2, "probability": Fraction(1, 10)},
        ],
        "spawn_position": "uniform_over_empty_cells",
        "failure_rule": "post_spawn_no_legal_merge_enters_absorbing_failure",
        "failure_check_before_horizon_truncation": True,
        "invalid_actions_in_ground_set": False,
    }


def _policy_class_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.phase3e_exact_infeasibility_policy_class.v1",
        "schema_version": SCHEMA_VERSION,
        "policy_class": "deterministic_finite_horizon_markov",
        "randomized_ground_policy": False,
        "randomized_abstract_selector": False,
        "query_time_policy_mixture": False,
    }


STRUCTURAL_PAYLOAD = _structural_payload()
STRUCTURAL_ID = _id(STRUCTURAL_DOMAIN, STRUCTURAL_PAYLOAD)
POLICY_CLASS_PAYLOAD = _policy_class_payload()
POLICY_CLASS_ID = _id(POLICY_CLASS_DOMAIN, POLICY_CLASS_PAYLOAD)

VERIFICATION_PROFILE_PAYLOAD = {
    "schema": "acfqp.phase3e_exact_infeasibility_verification_profile.v1",
    "schema_version": SCHEMA_VERSION,
    "profile_key": "canonical_g2048_h1_independent_exhaustive_replay_v1",
    "producer_invocation_allowed": False,
    "ground_fallback_solver_invocation_allowed": False,
    "j0_invocation_allowed": False,
    "arithmetic": "exact_rational",
    "action_closure": "rederive_all_legal_actions_from_board",
    "policy_replay": "enumerate_all_deterministic_h1_markov_policies",
}
VERIFICATION_PROFILE_ID = _id(
    VERIFICATION_PROFILE_DOMAIN, VERIFICATION_PROFILE_PAYLOAD
)


@dataclass(frozen=True, slots=True)
class DurableExactInfeasibilityIdentityV1:
    structural_id: str
    query_id: str
    build_epoch_id: str
    kernel_id: str
    threshold_profile_id: str
    reward_profile_id: str
    policy_class_id: str
    complete_search_profile_id: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "structural_id",
            "query_id",
            "build_epoch_id",
            "kernel_id",
            "threshold_profile_id",
            "reward_profile_id",
            "policy_class_id",
            "complete_search_profile_id",
        ):
            _cid(getattr(self, name), name)
        if self.schema_version != SCHEMA_VERSION:
            raise DurableExactInfeasibilityV1Error("identity schema version mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_exact_infeasibility_identity.v1",
            "schema_version": self.schema_version,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "threshold_profile_id": self.threshold_profile_id,
            "reward_profile_id": self.reward_profile_id,
            "policy_class_id": self.policy_class_id,
            "complete_search_profile_id": self.complete_search_profile_id,
        }

    @property
    def exact_infeasibility_identity_id(self) -> str:
        return _id(IDENTITY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "exact_infeasibility_identity_id": self.exact_infeasibility_identity_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "DurableExactInfeasibilityIdentityV1":
        _fields(
            document,
            {
                "schema",
                "schema_version",
                "structural_id",
                "query_id",
                "BuildEpoch_id",
                "kernel_id",
                "threshold_profile_id",
                "reward_profile_id",
                "policy_class_id",
                "complete_search_profile_id",
                "exact_infeasibility_identity_id",
            },
            "durable exact-infeasibility identity",
        )
        if document["schema"] != "acfqp.phase3e_exact_infeasibility_identity.v1":
            raise DurableExactInfeasibilityV1Error("identity schema mismatch")
        result = cls(
            document["structural_id"],
            document["query_id"],
            document["BuildEpoch_id"],
            document["kernel_id"],
            document["threshold_profile_id"],
            document["reward_profile_id"],
            document["policy_class_id"],
            document["complete_search_profile_id"],
            document["schema_version"],
        )
        if (
            document["exact_infeasibility_identity_id"]
            != result.exact_infeasibility_identity_id
        ):
            raise DurableExactInfeasibilityV1Error("identity content ID mismatch")
        return result


def _source_projection(
    root: Path,
    run: Mapping[str, Any],
    structural: Mapping[str, Any],
    query: Mapping[str, Any],
    enumeration: Mapping[str, Any],
    frontier: Mapping[str, Any],
) -> dict[str, Any]:
    relative = (
        "run.json",
        "config/structural.json",
        "config/query.json",
        "ground/enumeration.json",
        "ground/j0_frontier.json",
        "manifest.json",
    )
    hashes = [
        {"path": name, "sha256": sha256_file(root / name)} for name in relative
    ]
    return {
        "schema": "acfqp.phase3e_exact_infeasibility_source_projection.v1",
        "schema_version": SCHEMA_VERSION,
        "source_profile": "phase05_complete_exact_ground_search_v1",
        "legacy_run_id": run["run_id"],
        "legacy_build_id": run["build_id"],
        "legacy_fixture_id": structural["fixture_id"],
        "legacy_query_id": query["query_id"],
        "legacy_exact_j0_proof_id": frontier["exact_j0_proof_id"],
        "legacy_transition_kernel_sha256": enumeration[
            "transition_kernel_sha256"
        ],
        "legacy_source_tree_sha256": run["source_tree_sha256"],
        "legacy_semantic_hash": run["semantic_hash"],
        "source_document_hashes": hashes,
        "bundle_integrity_verified": True,
        "search_complete": enumeration["complete"],
        "cap_exceeded": enumeration["cap_handling"]["cap_exceeded"],
        "evaluation_tier": enumeration["evaluation_tier"],
        "state_cap": enumeration["cap_handling"]["state_cap"],
        "state_count": enumeration["state_count"],
        "transition_count": len(enumeration["transitions"]),
        "composed_candidate_count": frontier["composed_candidate_count"],
        "source_claimed_feasible": frontier["feasible"],
        "source_known_exact_status": frontier["known_exact_j0_status"],
    }


def _query_projection(query: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    initial = query.get("initial_distribution")
    if type(initial) is not list:
        raise DurableExactInfeasibilityV1Error("source query lacks initial law")
    for index, row in enumerate(initial):
        if type(row) is not list or len(row) != 2 or type(row[1]) is not dict:
            raise DurableExactInfeasibilityV1Error(
                f"invalid initial-distribution row {index}"
            )
        probability = _fraction(row[0], f"initial mass {index}")
        state = _state_payload(row[1].get("board"), row[1].get("status"))
        records.append(
            {
                "probability": probability,
                "state_id": _state_id(state),
                "state": state,
            }
        )
    records.sort(key=lambda record: record["state_id"])
    if len(records) != 8 or len({row["state_id"] for row in records}) != 8:
        raise DurableExactInfeasibilityV1Error(
            "canonical query must have eight distinct initial states"
        )
    if sum((row["probability"] for row in records), Fraction(0)) != 1:
        raise DurableExactInfeasibilityV1Error("initial distribution is not normalized")
    return tuple(records)


def _translate_enumeration(
    enumeration: Mapping[str, Any],
    initial: tuple[dict[str, Any], ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_states = enumeration.get("states")
    source_transitions = enumeration.get("transitions")
    if type(source_states) is not list or type(source_transitions) is not list:
        raise DurableExactInfeasibilityV1Error("enumeration state/transition rows missing")
    legacy_to_state: dict[str, dict[str, Any]] = {}
    by_new_id: dict[str, dict[str, Any]] = {}
    for row in source_states:
        if type(row) is not dict or set(row) != {"id", "state", "terminal"}:
            raise DurableExactInfeasibilityV1Error("malformed source state row")
        if type(row["state"]) is not dict or type(row["terminal"]) is not bool:
            raise DurableExactInfeasibilityV1Error("malformed source state payload")
        state = _state_payload(row["state"].get("board"), row["state"].get("status"))
        if row["terminal"] != (state["status"] == "failure"):
            raise DurableExactInfeasibilityV1Error("source state terminal/status mismatch")
        state_id = _state_id(state)
        if row["id"] in legacy_to_state or state_id in by_new_id:
            raise DurableExactInfeasibilityV1Error("duplicate source state identity")
        legacy_to_state[row["id"]] = state
        by_new_id[state_id] = state
    initial_ids = {row["state_id"] for row in initial}
    if not initial_ids <= set(by_new_id):
        raise DurableExactInfeasibilityV1Error(
            "enumeration omits an initial-support state"
        )

    translated: list[dict[str, Any]] = []
    for source_row in source_transitions:
        if type(source_row) is not dict or set(source_row) != {
            "action",
            "depth",
            "outcomes",
            "state",
            "transition_id",
        }:
            raise DurableExactInfeasibilityV1Error("malformed source transition row")
        if source_row["depth"] != 0 or source_row["state"] not in legacy_to_state:
            raise DurableExactInfeasibilityV1Error(
                "canonical H1 witness contains a foreign transition layer"
            )
        state = legacy_to_state[source_row["state"]]
        state_id = _state_id(state)
        action = _action_payload(source_row["action"])
        outcomes: list[dict[str, Any]] = []
        if type(source_row["outcomes"]) is not list:
            raise DurableExactInfeasibilityV1Error("transition outcomes must be a list")
        for outcome in source_row["outcomes"]:
            if type(outcome) is not dict or set(outcome) != {
                "entered_failure",
                "next_state",
                "probability",
                "reward_features",
                "terminal",
            }:
                raise DurableExactInfeasibilityV1Error("malformed source outcome row")
            next_state = legacy_to_state.get(outcome["next_state"])
            if next_state is None:
                raise DurableExactInfeasibilityV1Error(
                    "transition references a state outside the complete catalogue"
                )
            features = outcome["reward_features"]
            if type(features) is not list or len(features) != 1 or features[0][0] != "merge":
                raise DurableExactInfeasibilityV1Error(
                    "canonical transition must carry one merge reward"
                )
            probability = _fraction(outcome["probability"], "outcome probability")
            reward = _fraction(features[0][1], "merge reward")
            failure = outcome["entered_failure"]
            terminal = outcome["terminal"]
            if type(failure) is not bool or type(terminal) is not bool:
                raise DurableExactInfeasibilityV1Error("outcome flags must be booleans")
            outcomes.append(
                {
                    "probability": probability,
                    "next_state_id": _state_id(next_state),
                    "reward": reward,
                    "failure": failure,
                    "terminal": terminal,
                }
            )
        outcomes.sort(
            key=lambda row: (
                row["next_state_id"],
                row["probability"],
                row["failure"],
            )
        )
        translated.append(
            {
                "remaining": 1,
                "state_id": state_id,
                "action_id": _action_id(state_id, action),
                "action": action,
                "outcomes": outcomes,
            }
        )
    translated.sort(key=lambda row: (row["state_id"], _action_key(row["action"])))
    catalogue = [
        {
            "state_id": state_id,
            "state": state,
            "terminal": state["status"] == "failure",
        }
        for state_id, state in sorted(by_new_id.items())
    ]
    return catalogue, translated


def _frontier_from_rows(
    initial: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
) -> tuple[tuple[Fraction, Fraction], ...]:
    actions_by_state: dict[str, list[tuple[Fraction, Fraction]]] = {}
    for row in transitions:
        reward = sum(
            (
                outcome["probability"] * outcome["reward"]
                for outcome in row["outcomes"]
            ),
            Fraction(0),
        )
        risk = sum(
            (
                outcome["probability"]
                for outcome in row["outcomes"]
                if outcome["failure"]
            ),
            Fraction(0),
        )
        actions_by_state.setdefault(row["state_id"], []).append((reward, risk))
    choices: list[tuple[tuple[Fraction, Fraction], ...]] = []
    masses: list[Fraction] = []
    for record in initial:
        rows = tuple(actions_by_state.get(record["state_id"], ()))
        if not rows:
            raise DurableExactInfeasibilityV1Error(
                "initial state has no exhaustively witnessed action"
            )
        choices.append(rows)
        masses.append(record["probability"])
    points: set[tuple[Fraction, Fraction]] = set()
    for assignment in product(*choices):
        points.add(
            (
                sum(
                    (mass * value[0] for mass, value in zip(masses, assignment)),
                    Fraction(0),
                ),
                sum(
                    (mass * value[1] for mass, value in zip(masses, assignment)),
                    Fraction(0),
                ),
            )
        )
    frontier = tuple(
        point
        for point in points
        if not any(
            other != point
            and other[0] >= point[0]
            and other[1] <= point[1]
            and (other[0] > point[0] or other[1] < point[1])
            for other in points
        )
    )
    return tuple(sorted(frontier, key=lambda point: (point[1], -point[0])))


def issue_phase3e_exact_infeasibility_durable_proof_v1(
    phase05_bundle_root: str | Path,
) -> bytes:
    """Project the canonical complete Phase-0.5 search into durable bytes.

    A raw ``GroundFallbackResultV1`` is intentionally not accepted: its
    complete-search statement has no serializable action/transition closure.
    """

    root = Path(phase05_bundle_root)
    failures = verify_artifact_bundle(root)
    if failures:
        raise DurableExactInfeasibilityV1Error(
            "source artifact bundle failed integrity replay: " + "; ".join(failures)
        )
    run = _read_json(root / "run.json")
    structural = _read_json(root / "config" / "structural.json")
    query = _read_json(root / "config" / "query.json")
    enumeration = _read_json(root / "ground" / "enumeration.json")
    frontier = _read_json(root / "ground" / "j0_frontier.json")

    if (
        run.get("structural_key") != FIXTURE_KEY
        or structural.get("structural_key") != FIXTURE_KEY
        or structural.get("benchmark_role")
        != "infeasibility_and_soundness_regression"
        or structural.get("board_size") != 2
        or structural.get("rank_cap") != 6
        or structural.get("spawn_distribution")
        != [[1, {"denominator": 10, "numerator": 9}], [2, {"denominator": 10, "numerator": 1}]]
    ):
        raise DurableExactInfeasibilityV1Error(
            "source is not the registered canonical infeasible G2048 fixture"
        )
    if (
        query.get("horizon") != 1
        or query.get("goal") != "default"
        or _fraction(query.get("delta"), "query.delta") != Fraction(1, 20)
        or query.get("reward_weights")
        != [["merge", {"denominator": 1, "numerator": 1}]]
        or _fraction(query.get("normalizer"), "query.normalizer") != 1
    ):
        raise DurableExactInfeasibilityV1Error("source query profile is not canonical")
    cap = enumeration.get("cap_handling")
    if (
        type(cap) is not dict
        or enumeration.get("complete") is not True
        or enumeration.get("evaluation_tier") != "EXACT_SOUND"
        or cap.get("cap_exceeded") is not False
        or cap.get("truncated_result_is_exact_sound") is not False
        or frontier.get("feasible") is not False
        or frontier.get("known_exact_j0_status") != "INFEASIBLE"
        or run.get("known_exact_j0_status") != "INFEASIBLE"
        or frontier.get("exact_j0_proof_id") != run.get("known_exact_j0_proof_id")
    ):
        raise DurableExactInfeasibilityV1Error(
            "source lacks complete exact non-cap-exhausted ground-search evidence"
        )

    initial = _query_projection(query)
    catalogue, transitions = _translate_enumeration(enumeration, initial)
    source_projection = _source_projection(
        root, run, structural, query, enumeration, frontier
    )
    source_projection_id = _id(SOURCE_PROJECTION_DOMAIN, source_projection)

    query_payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_query.v1",
        "schema_version": SCHEMA_VERSION,
        "horizon": 1,
        "goal": "default",
        "initial_distribution": list(initial),
    }
    threshold_payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_threshold.v1",
        "schema_version": SCHEMA_VERSION,
        "delta": Fraction(1, 20),
    }
    reward_payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_reward.v1",
        "schema_version": SCHEMA_VERSION,
        "reward_weights": [{"feature": "merge", "coefficient": Fraction(1)}],
        "normalizer": Fraction(1),
        "normalizer_proof_id": query["normalizer_proof_id"],
    }
    search_profile = {
        "schema": "acfqp.phase3e_exact_infeasibility_search_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "algorithm": "complete_h1_deterministic_markov_enumeration",
        "state_cap": cap["state_cap"],
        "state_count": enumeration["state_count"],
        "transition_count": len(transitions),
        "positive_outcome_count": sum(len(row["outcomes"]) for row in transitions),
        "policy_count": 2 ** len(initial),
        "cap_exhausted": False,
        "search_complete": True,
    }
    query_id = _id(QUERY_DOMAIN, query_payload)
    threshold_id = _id(THRESHOLD_DOMAIN, threshold_payload)
    reward_id = _id(REWARD_DOMAIN, reward_payload)
    search_profile_id = _id(SEARCH_PROFILE_DOMAIN, search_profile)
    kernel_payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_kernel.v1",
        "schema_version": SCHEMA_VERSION,
        "structural_id": STRUCTURAL_ID,
        "legacy_transition_kernel_sha256": enumeration[
            "transition_kernel_sha256"
        ],
        "state_catalogue": catalogue,
        "transition_rows": transitions,
    }
    kernel_id = _id(KERNEL_DOMAIN, kernel_payload)
    build_payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_build_epoch.v1",
        "schema_version": SCHEMA_VERSION,
        "kernel_id": kernel_id,
        "source_projection_id": source_projection_id,
        "legacy_build_id": run["build_id"],
        "legacy_source_tree_sha256": run["source_tree_sha256"],
        "manifest_sha256": sha256_file(root / "manifest.json"),
    }
    build_epoch_id = _id(BUILD_EPOCH_DOMAIN, build_payload)
    identity = DurableExactInfeasibilityIdentityV1(
        STRUCTURAL_ID,
        query_id,
        build_epoch_id,
        kernel_id,
        threshold_id,
        reward_id,
        POLICY_CLASS_ID,
        search_profile_id,
    )

    recomputed_frontier = _frontier_from_rows(initial, transitions)
    claimed_frontier = [
        {"expected_reward": reward, "failure_probability": risk}
        for reward, risk in recomputed_frontier
    ]
    source_points = frontier.get("frontier")
    if type(source_points) is not list:
        raise DurableExactInfeasibilityV1Error("source frontier is absent")
    source_reward_risk = tuple(
        sorted(
            (
                _fraction(row["expected_reward"], "source expected reward"),
                _fraction(row["failure_probability"], "source failure probability"),
            )
            for row in source_points
        )
    )
    if tuple(sorted(recomputed_frontier)) != source_reward_risk:
        raise DurableExactInfeasibilityV1Error(
            "source claimed frontier disagrees with its complete transition witness"
        )
    if any(risk <= Fraction(1, 20) for _, risk in recomputed_frontier):
        raise DurableExactInfeasibilityV1Error(
            "canonical source unexpectedly contains a feasible deterministic policy"
        )

    payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_durable_proof.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "proof_kind": "COMPLETE_FINITE_HORIZON_GROUND_INFEASIBILITY",
        "identity": identity.to_dict(),
        "structural_profile": STRUCTURAL_PAYLOAD,
        "query_profile": query_payload,
        "threshold_profile": threshold_payload,
        "reward_profile": reward_payload,
        "policy_class_profile": POLICY_CLASS_PAYLOAD,
        "complete_search_profile": search_profile,
        "source_projection": source_projection,
        "source_projection_id": source_projection_id,
        "kernel_profile": kernel_payload,
        "build_epoch": build_payload,
        "claimed_frontier": claimed_frontier,
        "claim": {
            "outcome": "INFEASIBLE_CERTIFIED",
            "search_complete": True,
            "cap_exhausted": False,
            "selected_policy": None,
            "minimum_failure_probability": min(
                risk for _, risk in recomputed_frontier
            ),
            "delta": Fraction(1, 20),
        },
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "workload_economics_gate": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "counter_completeness_gate": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "sample_efficiency_gate": "SAMPLE_EFFICIENCY_GATE_NOT_RUN",
    }
    proof_id = _id(PROOF_DOMAIN, payload)
    proof = {**payload, "durable_exact_infeasibility_proof_id": proof_id}
    proof_bytes = canonical_json_bytes(proof)
    verified = verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes
    )
    if verified.result.outcome is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH:
        raise DurableExactInfeasibilityV1Error(
            "producer output failed independent replay: " + verified.result.reason_code
        )
    return proof_bytes


def _parse_query_profile(document: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    _fields(
        document,
        {"schema", "schema_version", "horizon", "goal", "initial_distribution"},
        "query profile",
    )
    if (
        document["schema"] != "acfqp.phase3e_exact_infeasibility_query.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["horizon"] != 1
        or document["goal"] != "default"
        or type(document["initial_distribution"]) is not list
    ):
        raise DurableExactInfeasibilityV1Error("query profile mismatch")
    records: list[dict[str, Any]] = []
    for row in document["initial_distribution"]:
        _fields(row, {"probability", "state_id", "state"}, "initial row")
        state = _state_payload(row["state"].get("board"), row["state"].get("status"))
        probability = _fraction(row["probability"], "initial probability")
        if probability <= 0 or row["state_id"] != _state_id(state):
            raise DurableExactInfeasibilityV1Error("initial row identity/mass mismatch")
        records.append(
            {"probability": probability, "state_id": row["state_id"], "state": state}
        )
    if (
        len(records) != 8
        or records != sorted(records, key=lambda row: row["state_id"])
        or len({row["state_id"] for row in records}) != 8
        or sum((row["probability"] for row in records), Fraction(0)) != 1
    ):
        raise DurableExactInfeasibilityV1Error("initial law is not canonical")
    return tuple(records)


def _verify_structural_and_profiles(document: Mapping[str, Any]) -> None:
    if document["structural_profile"] != STRUCTURAL_PAYLOAD:
        raise DurableExactInfeasibilityV1Error("structural profile mismatch")
    if document["policy_class_profile"] != POLICY_CLASS_PAYLOAD:
        raise DurableExactInfeasibilityV1Error("policy class mismatch")
    threshold = document["threshold_profile"]
    _fields(threshold, {"schema", "schema_version", "delta"}, "threshold profile")
    if (
        threshold["schema"] != "acfqp.phase3e_exact_infeasibility_threshold.v1"
        or threshold["schema_version"] != SCHEMA_VERSION
        or _fraction(threshold["delta"], "delta") != Fraction(1, 20)
    ):
        raise DurableExactInfeasibilityV1Error("threshold profile mismatch")
    reward = document["reward_profile"]
    _fields(
        reward,
        {"schema", "schema_version", "reward_weights", "normalizer", "normalizer_proof_id"},
        "reward profile",
    )
    if (
        reward["schema"] != "acfqp.phase3e_exact_infeasibility_reward.v1"
        or reward["schema_version"] != SCHEMA_VERSION
        or reward["reward_weights"]
        != [{"feature": "merge", "coefficient": Fraction(1)}]
        or _fraction(reward["normalizer"], "normalizer") != 1
        or reward["normalizer_proof_id"]
        != "g2048.canonical.merge_le_1_per_step.total_le_h.v1"
    ):
        raise DurableExactInfeasibilityV1Error("reward profile mismatch")


def _verify_source_projection(source: Mapping[str, Any]) -> None:
    _fields(
        source,
        {
            "schema",
            "schema_version",
            "source_profile",
            "legacy_run_id",
            "legacy_build_id",
            "legacy_fixture_id",
            "legacy_query_id",
            "legacy_exact_j0_proof_id",
            "legacy_transition_kernel_sha256",
            "legacy_source_tree_sha256",
            "legacy_semantic_hash",
            "source_document_hashes",
            "bundle_integrity_verified",
            "search_complete",
            "cap_exceeded",
            "evaluation_tier",
            "state_cap",
            "state_count",
            "transition_count",
            "composed_candidate_count",
            "source_claimed_feasible",
            "source_known_exact_status",
        },
        "source projection",
    )
    if (
        source["schema"] != "acfqp.phase3e_exact_infeasibility_source_projection.v1"
        or source["schema_version"] != SCHEMA_VERSION
        or source["source_profile"] != "phase05_complete_exact_ground_search_v1"
        or source["bundle_integrity_verified"] is not True
        or source["search_complete"] is not True
        or source["cap_exceeded"] is not False
        or source["evaluation_tier"] != "EXACT_SOUND"
        or source["source_claimed_feasible"] is not False
        or source["source_known_exact_status"] != "INFEASIBLE"
        or source["state_count"] != 46
        or source["transition_count"] != 16
        or source["composed_candidate_count"] != 16
    ):
        raise DurableExactInfeasibilityV1Error(
            "source is incomplete, cap-exhausted, non-exact, or not canonical"
        )
    hashes = source["source_document_hashes"]
    if type(hashes) is not list or len(hashes) != 6:
        raise DurableExactInfeasibilityV1Error("source hash inventory is incomplete")
    expected_paths = sorted(
        (
            "run.json",
            "config/structural.json",
            "config/query.json",
            "ground/enumeration.json",
            "ground/j0_frontier.json",
            "manifest.json",
        )
    )
    paths: list[str] = []
    for row in hashes:
        _fields(row, {"path", "sha256"}, "source hash row")
        _cid(row["sha256"], "source document sha256")
        paths.append(row["path"])
    if sorted(paths) != expected_paths or len(set(paths)) != len(paths):
        raise DurableExactInfeasibilityV1Error("source hash roles are incomplete")


def _parse_kernel_and_verify_closure(
    kernel: Mapping[str, Any],
    initial: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _fields(
        kernel,
        {
            "schema",
            "schema_version",
            "structural_id",
            "legacy_transition_kernel_sha256",
            "state_catalogue",
            "transition_rows",
        },
        "kernel profile",
    )
    if (
        kernel["schema"] != "acfqp.phase3e_exact_infeasibility_kernel.v1"
        or kernel["schema_version"] != SCHEMA_VERSION
        or kernel["structural_id"] != STRUCTURAL_ID
        or type(kernel["state_catalogue"]) is not list
        or type(kernel["transition_rows"]) is not list
    ):
        raise DurableExactInfeasibilityV1Error("kernel profile mismatch")
    catalogue: list[dict[str, Any]] = []
    state_by_id: dict[str, dict[str, Any]] = {}
    for row in kernel["state_catalogue"]:
        _fields(row, {"state_id", "state", "terminal"}, "state catalogue row")
        state = _state_payload(row["state"].get("board"), row["state"].get("status"))
        state_id = _state_id(state)
        if (
            row["state_id"] != state_id
            or type(row["terminal"]) is not bool
            or row["terminal"] != (state["status"] == "failure")
            or state_id in state_by_id
        ):
            raise DurableExactInfeasibilityV1Error("state catalogue identity mismatch")
        state_by_id[state_id] = state
        catalogue.append({"state_id": state_id, "state": state, "terminal": row["terminal"]})
    if catalogue != sorted(catalogue, key=lambda row: row["state_id"]):
        raise DurableExactInfeasibilityV1Error("state catalogue is not canonical")

    transitions: list[dict[str, Any]] = []
    actions_by_state: dict[str, list[dict[str, int]]] = {}
    referenced_states = {row["state_id"] for row in initial}
    for row in kernel["transition_rows"]:
        _fields(
            row,
            {"remaining", "state_id", "action_id", "action", "outcomes"},
            "transition row",
        )
        if row["remaining"] != 1 or row["state_id"] not in state_by_id:
            raise DurableExactInfeasibilityV1Error("transition state/time mismatch")
        action = _action_payload(row["action"])
        if row["action_id"] != _action_id(row["state_id"], action):
            raise DurableExactInfeasibilityV1Error("transition action ID mismatch")
        state = state_by_id[row["state_id"]]
        expected = _semantic_outcomes(state, action)
        if type(row["outcomes"]) is not list:
            raise DurableExactInfeasibilityV1Error("outcomes must be a list")
        parsed_outcomes: list[dict[str, Any]] = []
        for outcome in row["outcomes"]:
            _fields(
                outcome,
                {"probability", "next_state_id", "reward", "failure", "terminal"},
                "transition outcome",
            )
            probability = _fraction(outcome["probability"], "outcome probability")
            reward = _fraction(outcome["reward"], "outcome reward")
            if (
                probability <= 0
                or outcome["next_state_id"] not in state_by_id
                or type(outcome["failure"]) is not bool
                or type(outcome["terminal"]) is not bool
            ):
                raise DurableExactInfeasibilityV1Error("invalid transition outcome")
            next_state = state_by_id[outcome["next_state_id"]]
            parsed_outcomes.append(
                {
                    "probability": probability,
                    "next_state_id": outcome["next_state_id"],
                    "reward": reward,
                    "failure": outcome["failure"],
                    "terminal": outcome["terminal"],
                }
            )
            referenced_states.add(outcome["next_state_id"])
            if (
                (next_state["status"] == "failure") != outcome["failure"]
                or outcome["terminal"] != outcome["failure"]
            ):
                raise DurableExactInfeasibilityV1Error("outcome status/flags mismatch")
        canonical = sorted(
            parsed_outcomes,
            key=lambda item: (
                item["next_state_id"], item["probability"], item["failure"]
            ),
        )
        if parsed_outcomes != canonical:
            raise DurableExactInfeasibilityV1Error("outcomes are not canonical")
        expected_projection = [
            {
                "probability": item["probability"],
                "next_state_id": _state_id(item["next_state"]),
                "reward": item["reward"],
                "failure": item["failure"],
                "terminal": item["terminal"],
            }
            for item in expected
        ]
        if parsed_outcomes != expected_projection:
            raise DurableExactInfeasibilityV1Error(
                "transition row disagrees with independent G2048 semantics"
            )
        actions_by_state.setdefault(row["state_id"], []).append(action)
        transitions.append(
            {
                "remaining": 1,
                "state_id": row["state_id"],
                "action_id": row["action_id"],
                "action": action,
                "outcomes": parsed_outcomes,
            }
        )
    if transitions != sorted(
        transitions, key=lambda row: (row["state_id"], _action_key(row["action"]))
    ):
        raise DurableExactInfeasibilityV1Error("transition rows are not canonical")
    if len({(row["state_id"], row["action_id"]) for row in transitions}) != len(transitions):
        raise DurableExactInfeasibilityV1Error("transition row duplicated")
    for initial_row in initial:
        state = initial_row["state"]
        expected_actions = list(_legal_actions(tuple(state["board"]), state["status"]))
        actual_actions = actions_by_state.get(initial_row["state_id"], [])
        if actual_actions != expected_actions:
            raise DurableExactInfeasibilityV1Error(
                "initial-state legal action closure is incomplete or duplicated"
            )
    if referenced_states != set(state_by_id):
        raise DurableExactInfeasibilityV1Error(
            "state catalogue contains unreachable or omits referenced H1 states"
        )
    if len(catalogue) != 46 or len(transitions) != 16:
        raise DurableExactInfeasibilityV1Error("canonical witness cardinality mismatch")
    return catalogue, transitions


def _verify_document(document: Mapping[str, Any]) -> tuple[
    DurableExactInfeasibilityIdentityV1, Fraction, str
]:
    expected_top = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "proof_kind",
        "identity",
        "structural_profile",
        "query_profile",
        "threshold_profile",
        "reward_profile",
        "policy_class_profile",
        "complete_search_profile",
        "source_projection",
        "source_projection_id",
        "kernel_profile",
        "build_epoch",
        "claimed_frontier",
        "claim",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "workload_economics_gate",
        "counter_completeness_gate",
        "sample_efficiency_gate",
        "durable_exact_infeasibility_proof_id",
    }
    _fields(document, expected_top, "durable exact-infeasibility proof")
    if (
        document["schema"] != "acfqp.phase3e_exact_infeasibility_durable_proof.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["proof_kind"]
        != "COMPLETE_FINITE_HORIZON_GROUND_INFEASIBILITY"
    ):
        raise DurableExactInfeasibilityV1Error("durable proof profile mismatch")
    if (
        document["official_execution_allowed"] is not False
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["workload_economics_gate"]
        != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
        or document["counter_completeness_gate"]
        != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        or document["sample_efficiency_gate"]
        != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    ):
        raise DurableExactInfeasibilityV1Error("durable proof attempts to unlock a gate")
    _verify_structural_and_profiles(document)
    initial = _parse_query_profile(document["query_profile"])
    source = document["source_projection"]
    _verify_source_projection(source)
    if document["source_projection_id"] != _id(SOURCE_PROJECTION_DOMAIN, source):
        raise DurableExactInfeasibilityV1Error("source projection ID mismatch")
    catalogue, transitions = _parse_kernel_and_verify_closure(
        document["kernel_profile"], initial
    )
    search = document["complete_search_profile"]
    _fields(
        search,
        {
            "schema",
            "schema_version",
            "algorithm",
            "state_cap",
            "state_count",
            "transition_count",
            "positive_outcome_count",
            "policy_count",
            "cap_exhausted",
            "search_complete",
        },
        "complete search profile",
    )
    if (
        search["schema"] != "acfqp.phase3e_exact_infeasibility_search_profile.v1"
        or search["schema_version"] != SCHEMA_VERSION
        or search["algorithm"] != "complete_h1_deterministic_markov_enumeration"
        or search["state_count"] != len(catalogue)
        or search["transition_count"] != len(transitions)
        or search["positive_outcome_count"]
        != sum(len(row["outcomes"]) for row in transitions)
        or search["policy_count"] != 256
        or search["cap_exhausted"] is not False
        or search["search_complete"] is not True
    ):
        raise DurableExactInfeasibilityV1Error(
            "search is incomplete, cap-exhausted, or cardinality-inconsistent"
        )
    frontier = _frontier_from_rows(initial, transitions)
    claimed = document["claimed_frontier"]
    if type(claimed) is not list:
        raise DurableExactInfeasibilityV1Error("claimed frontier must be a list")
    claimed_points: list[tuple[Fraction, Fraction]] = []
    for row in claimed:
        _fields(row, {"expected_reward", "failure_probability"}, "frontier row")
        claimed_points.append(
            (
                _fraction(row["expected_reward"], "expected reward"),
                _fraction(row["failure_probability"], "failure probability"),
            )
        )
    if tuple(claimed_points) != frontier:
        raise DurableExactInfeasibilityV1Error(
            "claimed frontier disagrees with exhaustive policy replay"
        )
    claim = document["claim"]
    _fields(
        claim,
        {
            "outcome",
            "search_complete",
            "cap_exhausted",
            "selected_policy",
            "minimum_failure_probability",
            "delta",
        },
        "infeasibility claim",
    )
    minimum_risk = min(risk for _, risk in frontier)
    delta = _fraction(claim["delta"], "claim delta")
    if (
        claim["outcome"] != "INFEASIBLE_CERTIFIED"
        or claim["search_complete"] is not True
        or claim["cap_exhausted"] is not False
        or claim["selected_policy"] is not None
        or _fraction(claim["minimum_failure_probability"], "minimum risk")
        != minimum_risk
        or delta != Fraction(1, 20)
        or minimum_risk <= delta
    ):
        raise DurableExactInfeasibilityV1Error(
            "claim is feasible, incomplete, cap-exhausted, or arithmetically false"
        )

    query_payload = document["query_profile"]
    threshold_payload = document["threshold_profile"]
    reward_payload = document["reward_profile"]
    kernel_payload = document["kernel_profile"]
    build_payload = document["build_epoch"]
    _fields(
        build_payload,
        {
            "schema",
            "schema_version",
            "kernel_id",
            "source_projection_id",
            "legacy_build_id",
            "legacy_source_tree_sha256",
            "manifest_sha256",
        },
        "build epoch",
    )
    kernel_id = _id(KERNEL_DOMAIN, kernel_payload)
    if (
        build_payload["schema"] != "acfqp.phase3e_exact_infeasibility_build_epoch.v1"
        or build_payload["schema_version"] != SCHEMA_VERSION
        or build_payload["kernel_id"] != kernel_id
        or build_payload["source_projection_id"] != document["source_projection_id"]
    ):
        raise DurableExactInfeasibilityV1Error("build epoch binding mismatch")
    _cid(build_payload["manifest_sha256"], "manifest_sha256")
    identity = DurableExactInfeasibilityIdentityV1.from_dict(document["identity"])
    expected_identity = DurableExactInfeasibilityIdentityV1(
        STRUCTURAL_ID,
        _id(QUERY_DOMAIN, query_payload),
        _id(BUILD_EPOCH_DOMAIN, build_payload),
        kernel_id,
        _id(THRESHOLD_DOMAIN, threshold_payload),
        _id(REWARD_DOMAIN, reward_payload),
        POLICY_CLASS_ID,
        _id(SEARCH_PROFILE_DOMAIN, search),
    )
    if identity != expected_identity:
        raise DurableExactInfeasibilityV1Error("proof identity chain mismatch")
    payload = dict(document)
    proof_id = payload.pop("durable_exact_infeasibility_proof_id")
    if proof_id != _id(PROOF_DOMAIN, payload):
        raise DurableExactInfeasibilityV1Error("durable proof content ID mismatch")
    return identity, minimum_risk, proof_id


@dataclass(frozen=True, slots=True)
class DurableProofVerificationResultV1:
    outcome: DurableProofVerificationOutcomeV1
    submitted_bytes_sha256: str
    durable_proof_id: str | None
    proof_identity_id: str | None
    current_identity_id: str | None
    proof_semantically_valid: bool
    minimum_failure_probability: Fraction | None
    reason_code: str
    verification_profile_id: str = VERIFICATION_PROFILE_ID
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", DurableProofVerificationOutcomeV1(self.outcome))
        _cid(self.submitted_bytes_sha256, "submitted_bytes_sha256")
        for name in (
            "durable_proof_id",
            "proof_identity_id",
            "current_identity_id",
        ):
            value = getattr(self, name)
            if value is not None:
                _cid(value, name)
        if self.minimum_failure_probability is not None:
            object.__setattr__(
                self,
                "minimum_failure_probability",
                _fraction(self.minimum_failure_probability, "minimum failure probability"),
            )
        if type(self.proof_semantically_valid) is not bool or not self.reason_code:
            raise DurableExactInfeasibilityV1Error("invalid verification result shape")
        if self.verification_profile_id != VERIFICATION_PROFILE_ID:
            raise DurableExactInfeasibilityV1Error("verification profile mismatch")
        if self.schema_version != SCHEMA_VERSION:
            raise DurableExactInfeasibilityV1Error("verification version mismatch")
        if self.outcome is DurableProofVerificationOutcomeV1.INVALID:
            if self.proof_semantically_valid or self.minimum_failure_probability is not None:
                raise DurableExactInfeasibilityV1Error("INVALID cannot carry proof authority")
        elif (
            not self.proof_semantically_valid
            or self.durable_proof_id is None
            or self.proof_identity_id is None
            or self.current_identity_id is None
            or self.minimum_failure_probability is None
        ):
            raise DurableExactInfeasibilityV1Error("valid replay lacks proof bindings")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_exact_infeasibility_verification.v1",
            "schema_version": self.schema_version,
            "outcome": self.outcome.value,
            "submitted_bytes_sha256": self.submitted_bytes_sha256,
            "durable_proof_id": self.durable_proof_id,
            "proof_identity_id": self.proof_identity_id,
            "current_identity_id": self.current_identity_id,
            "proof_semantically_valid": self.proof_semantically_valid,
            "minimum_failure_probability": self.minimum_failure_probability,
            "reason_code": self.reason_code,
            "verification_profile_id": self.verification_profile_id,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def verification_id(self) -> str:
        return _id(VERIFICATION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class VerifiedDurableExactInfeasibilityHandleV1:
    """Owner-bound result of independent proof replay; never deserializable."""

    result: DurableProofVerificationResultV1
    proof_bytes: bytes = field(repr=False)
    proof_identity: DurableExactInfeasibilityIdentityV1 | None = field(repr=False)
    current_identity: DurableExactInfeasibilityIdentityV1 | None = field(repr=False)
    _authority: object = field(repr=False, compare=False, default=None)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        repr=False, compare=False, default=None
    )

    def __post_init__(self) -> None:
        if self._authority is not _VERIFIER_AUTHORITY:
            raise DurableExactInfeasibilityV1Error(
                "verified durable proof handle was not minted by the independent verifier"
            )
        if type(self.proof_bytes) is not bytes:
            raise DurableExactInfeasibilityV1Error("verified proof bytes must be immutable")


def _invalid_handle(raw: bytes, reason: str) -> VerifiedDurableExactInfeasibilityHandleV1:
    result = DurableProofVerificationResultV1(
        DurableProofVerificationOutcomeV1.INVALID,
        _sha256_bytes(raw),
        None,
        None,
        None,
        False,
        None,
        reason,
    )
    handle = VerifiedDurableExactInfeasibilityHandleV1(
        result, raw, None, None, _VERIFIER_AUTHORITY
    )
    return bind_runtime_authority_v1(handle, issuer=_VERIFIER_AUTHORITY)


def verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
    proof_bytes: bytes,
    *,
    current_identity: DurableExactInfeasibilityIdentityV1 | Mapping[str, Any] | None = None,
) -> VerifiedDurableExactInfeasibilityHandleV1:
    """Independently replay durable proof bytes and compare exact identity.

    Malformed proof bytes or malformed current identities return ``INVALID``;
    an ordinary valid identity mismatch returns ``NO_MATCH``.
    """

    if type(proof_bytes) is not bytes:
        raw = repr(proof_bytes).encode("utf-8", errors="backslashreplace")
        return _invalid_handle(raw, "PROOF_BYTES_NOT_IMMUTABLE_BYTES")
    try:
        document = loads_canonical_json(proof_bytes)
        if type(document) is not dict:
            raise DurableExactInfeasibilityV1Error("proof root must be an object")
        proof_identity, minimum_risk, proof_id = _verify_document(document)
        if current_identity is None:
            current = proof_identity
        elif isinstance(current_identity, DurableExactInfeasibilityIdentityV1):
            current = DurableExactInfeasibilityIdentityV1.from_dict(
                current_identity.to_dict()
            )
        elif type(current_identity) is dict:
            current = DurableExactInfeasibilityIdentityV1.from_dict(current_identity)
        else:
            raise DurableExactInfeasibilityV1Error("current identity has wrong type")
    except (DurableExactInfeasibilityV1Error, TypeError, ValueError) as error:
        return _invalid_handle(
            proof_bytes,
            "INVALID_DURABLE_PROOF_OR_CURRENT_IDENTITY:" + str(error),
        )
    outcome = (
        DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
        if proof_identity == current
        else DurableProofVerificationOutcomeV1.NO_MATCH
    )
    result = DurableProofVerificationResultV1(
        outcome,
        _sha256_bytes(proof_bytes),
        proof_id,
        proof_identity.exact_infeasibility_identity_id,
        current.exact_infeasibility_identity_id,
        True,
        minimum_risk,
        "EXACT_IDENTITY_MATCH" if outcome is DurableProofVerificationOutcomeV1.IDENTICAL_MATCH else "EXACT_IDENTITY_MISMATCH",
    )
    handle = VerifiedDurableExactInfeasibilityHandleV1(
        result,
        proof_bytes,
        proof_identity,
        current,
        _VERIFIER_AUTHORITY,
    )
    return bind_runtime_authority_v1(handle, issuer=_VERIFIER_AUTHORITY)


@dataclass(frozen=True, slots=True)
class VerifiedDurableProofCacheConsumptionV1:
    """A plan binding that consumes, but cannot mint, a verified proof."""

    selected_plan_id: str
    durable_proof_id: str
    verification_id: str
    exact_infeasibility_identity_id: str
    outcome: str = "IDENTICAL_MATCH"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "selected_plan_id",
            "durable_proof_id",
            "verification_id",
            "exact_infeasibility_identity_id",
        ):
            _cid(getattr(self, name), name)
        if self.outcome != "IDENTICAL_MATCH" or self.schema_version != SCHEMA_VERSION:
            raise DurableExactInfeasibilityV1Error("cache consumption profile mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_exact_infeasibility_cache_consumption.v1",
            "schema_version": self.schema_version,
            "selected_plan_id": self.selected_plan_id,
            "durable_proof_id": self.durable_proof_id,
            "verification_id": self.verification_id,
            "exact_infeasibility_identity_id": self.exact_infeasibility_identity_id,
            "outcome": self.outcome,
            "mints_exact_infeasibility_proof": False,
        }

    @property
    def cache_consumption_id(self) -> str:
        return _id(CACHE_CONSUMPTION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "cache_consumption_id": self.cache_consumption_id}


def bind_verified_durable_exact_infeasibility_to_plan_v1(
    verified: VerifiedDurableExactInfeasibilityHandleV1,
    *,
    selected_plan_id: str,
) -> VerifiedDurableProofCacheConsumptionV1:
    """Bind a verified identical proof to a real plan without minting proof."""

    if not isinstance(verified, VerifiedDurableExactInfeasibilityHandleV1):
        raise DurableExactInfeasibilityV1Error(
            "plan-frozen cache requires the retained independent-verifier handle"
        )
    try:
        require_runtime_authority_v1(verified, issuer=_VERIFIER_AUTHORITY)
    except ValueError as error:
        raise DurableExactInfeasibilityV1Error(
            "plan-frozen cache requires the exact retained verifier handle"
        ) from error
    if (
        verified.result.outcome
        is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
        or not verified.result.proof_semantically_valid
        or verified.proof_identity is None
    ):
        raise DurableExactInfeasibilityV1Error(
            "only an independently verified IDENTICAL_MATCH may be cached"
        )
    return VerifiedDurableProofCacheConsumptionV1(
        _cid(selected_plan_id, "selected_plan_id"),
        verified.result.durable_proof_id,  # type: ignore[arg-type]
        verified.result.verification_id,
        verified.proof_identity.exact_infeasibility_identity_id,
    )


@dataclass(frozen=True, slots=True)
class DurableGroundFallbackPortabilityBlockerV1:
    """Typed explanation for why a legacy fallback result cannot mint proof."""

    source_result_id: str
    source_outcome: str
    blocker_code: str
    durable_proof_minted: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.source_result_id, "source_result_id")
        if self.blocker_code not in {
            "OPAQUE_SEARCH_COMPLETENESS_NOT_DURABLE",
            "CAP_EXHAUSTED_IS_NONCERTIFICATE",
            "FEASIBLE_RESULT_IS_NOT_INFEASIBILITY",
        }:
            raise DurableExactInfeasibilityV1Error("unknown portability blocker")
        if self.durable_proof_minted is not False or self.schema_version != SCHEMA_VERSION:
            raise DurableExactInfeasibilityV1Error("blocker cannot mint proof")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_exact_infeasibility_blocker.v1",
            "schema_version": self.schema_version,
            "source_result_id": self.source_result_id,
            "source_outcome": self.source_outcome,
            "blocker_code": self.blocker_code,
            "durable_proof_minted": False,
        }

    @property
    def blocker_id(self) -> str:
        return _id(BLOCKER_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "blocker_id": self.blocker_id}


def classify_legacy_ground_fallback_portability_v1(
    result: object,
) -> DurableGroundFallbackPortabilityBlockerV1:
    """Classify a strict legacy result without accepting its status as proof."""

    from acfqp.phase3e_fallback_v1 import (
        GroundFallbackOutcome,
        GroundFallbackResultV1,
    )

    if type(result) is not GroundFallbackResultV1:
        raise DurableExactInfeasibilityV1Error(
            "portability classification requires GroundFallbackResultV1"
        )
    try:
        parsed = GroundFallbackResultV1.from_dict(result.to_dict())
    except ValueError as error:
        raise DurableExactInfeasibilityV1Error(
            f"legacy ground fallback result does not replay: {error}"
        ) from error
    blocker = {
        GroundFallbackOutcome.INFEASIBLE_CERTIFIED: (
            "OPAQUE_SEARCH_COMPLETENESS_NOT_DURABLE"
        ),
        GroundFallbackOutcome.CAP_EXHAUSTED: "CAP_EXHAUSTED_IS_NONCERTIFICATE",
        GroundFallbackOutcome.FEASIBLE_CERTIFIED: (
            "FEASIBLE_RESULT_IS_NOT_INFEASIBILITY"
        ),
    }[parsed.outcome]
    return DurableGroundFallbackPortabilityBlockerV1(
        parsed.ground_fallback_result_id,
        parsed.outcome.value,
        blocker,
    )


__all__ = [
    "PROPOSED_CONTRACT_VERSION",
    "FIXTURE_KEY",
    "DurableExactInfeasibilityV1Error",
    "DurableProofVerificationOutcomeV1",
    "DurableExactInfeasibilityIdentityV1",
    "DurableProofVerificationResultV1",
    "VerifiedDurableExactInfeasibilityHandleV1",
    "VerifiedDurableProofCacheConsumptionV1",
    "DurableGroundFallbackPortabilityBlockerV1",
    "issue_phase3e_exact_infeasibility_durable_proof_v1",
    "verify_phase3e_exact_infeasibility_durable_proof_bytes_v1",
    "bind_verified_durable_exact_infeasibility_to_plan_v1",
    "classify_legacy_ground_fallback_portability_v1",
]
