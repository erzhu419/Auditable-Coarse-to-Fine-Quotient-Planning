"""Executable exact-:math:`D_4` positive-control artifact bundle.

This profile is deliberately separate from the Phase 0.5 CEGAR slice.  The
quotient is supplied by the registered square automorphism group, must be
exact at construction time, and emits no witness, split, or fallback record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from acfqp.artifacts import (
    D4_BASELINE_DOCUMENT_CONTRACTS,
    D4_BASELINE_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
)
from acfqp.domains import (
    D4_ELEMENTS,
    SAFE_CHAIN_STRUCTURAL_KEY,
    canonicalize_state,
    compose_d4,
    inverse_d4,
    safe_chain_fixture,
    transform_action,
    transform_cell,
    transform_state,
)
from acfqp.domains.g2048 import G2048Status
from acfqp.enumeration import EnumerationStatus, enumerate_reachable
from acfqp.planning import solve_ground_pareto
from acfqp.symmetry import (
    EXACT_D4_QUOTIENT_INVARIANT_VIOLATION,
    ExactD4QuotientInvariantViolation,
    FiniteGroupAction,
    build_state_time_d4_quotient,
    solve_exact_d4_quotient,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_CAP = 50_000
EXECUTION_PROFILE = "exact_d4_quotient_baseline"
CERTIFIED = "CERTIFIED"
INVARIANT_VIOLATION = EXACT_D4_QUOTIENT_INVARIANT_VIOLATION
GROUP_PROFILE_VERSION = "d4-square-2x2.v1"
ABSTRACTION_SOURCE = "known_group_exact_homomorphism"
SEMANTIC_DOCUMENT_PATHS = tuple(
    path
    for path in D4_BASELINE_REQUIRED_PATHS
    if path not in {"run.json", "metrics.json", "events.jsonl"}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_tree_hash() -> str:
    paths: list[Path] = []
    for root_name in ("src", "scripts", "specs", "tests"):
        root = PROJECT_ROOT / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
            )
    for filename in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = PROJECT_ROOT / filename
        if path.is_file():
            paths.append(path)
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    paths = [
        PROJECT_ROOT / "DECISION_LEDGER.md",
        *sorted((PROJECT_ROOT / "specs").glob("*.md")),
    ]
    return {
        path.relative_to(PROJECT_ROOT).as_posix(): sha256_file(path) for path in paths
    }


def _reference_manifest_hashes() -> dict[str, str]:
    records: dict[str, str] = {}
    for filename in ("download_manifest.json", "repo_clone_manifest.json"):
        path = PROJECT_ROOT / "reference" / filename
        if path.is_file():
            records[f"reference/{filename}"] = sha256_file(path)
    return records


def safe_chain_d4_group(kernel: Any) -> FiniteGroupAction:
    """Return the quotient adapter over the single authoritative D4 registry."""

    return FiniteGroupAction(
        elements=D4_ELEMENTS,
        transform_state=lambda element, state: transform_state(
            state, element, kernel.size
        ),
        transform_action=lambda element, action: transform_action(
            action, element, kernel.size
        ),
        inverse=inverse_d4,
        state_key=lambda state: repr((state.board, state.status.value)),
        action_key=repr,
    )


def _state_id(state: Any) -> str:
    return object_id(state, "state")


def _action_id(action: Any) -> str:
    return object_id(action, "action")


def _state_time_id(state: Any, remaining: int) -> str:
    return object_id(
        {"remaining_horizon": remaining, "state_id": _state_id(state)},
        "state-time",
    )


def _cell_id(cell: Any) -> str:
    return object_id(
        {
            "remaining_horizon": cell.remaining,
            "kind": cell.kind.value,
            "representative_key": cell.representative_key,
        },
        "state-orbit",
    )


def _action_orbit_id(cell: Any, label: Any) -> str:
    return object_id(
        {
            "state_orbit_id": _cell_id(cell),
            "representative_state_key": label.representative_state_key,
            "deduplicated_action_keys": label.action_keys,
        },
        "action-orbit",
    )


def _profile_payload(size: int) -> dict[str, Any]:
    element_ids = [element.value for element in D4_ELEMENTS]
    return {
        "profile_version": GROUP_PROFILE_VERSION,
        "abstraction_source": ABSTRACTION_SOURCE,
        "board_size": size,
        "coordinate_convention": {
            "storage": "row_major_empty_is_0",
            "rotation": "clockwise_(i,j)->(j,n-1-i)",
            "reflection": "vertical_(i,j)->(i,n-1-j)_before_rotation",
            "composition": "(g*h)x=g(hx)",
        },
        "ordered_group_element_ids": element_ids,
        "cell_permutations": {
            element.value: [
                transform_cell(cell, size, element) for cell in range(size * size)
            ]
            for element in D4_ELEMENTS
        },
        "inverse_element_ids": {
            element.value: inverse_d4(element).value for element in D4_ELEMENTS
        },
        "composition_table": {
            left.value: {
                right.value: compose_d4(left, right).value
                for right in D4_ELEMENTS
            }
            for left in D4_ELEMENTS
        },
    }


def _profile_document(size: int) -> dict[str, Any]:
    payload = _profile_payload(size)
    return {
        **payload,
        "group_profile_id": object_id(payload, "group-profile"),
        "group_profile_hash": canonical_sha256(payload),
        "known_not_discovered": True,
    }


def _policy_document(policy: Any, *, level: str, cell_ids: dict[Any, str] | None = None) -> dict[str, Any] | None:
    if policy is None:
        return None
    decisions = []
    for decision in policy.decisions:
        if level == "ground":
            state_or_cell = _state_id(decision.state)
            action = _action_id(decision.action)
        else:
            if cell_ids is None:
                raise AssertionError("abstract policy serialization requires cell IDs")
            state_or_cell = cell_ids[decision.state]
            action = _action_orbit_id(decision.state, decision.action)
        record = {
            "remaining": decision.remaining,
            "state_or_cell": state_or_cell,
            "action_id": action,
        }
        record["node_id"] = object_id(record, "policy-node")
        decisions.append(record)
    signature = [
        (record["remaining"], record["state_or_cell"], record["action_id"])
        for record in decisions
    ]
    payload = {
        "level": level,
        "selector_class": "deterministic_finite_horizon_markov",
        "signature": signature,
        "decisions": decisions,
    }
    return {**payload, "policy_id": object_id(payload, "policy")}


def _frontier_document(result: Any, query_id: str) -> dict[str, Any]:
    selected_signature = (
        result.selected.policy.signature() if result.selected is not None else None
    )
    frontier = []
    for point in result.frontier:
        policy = _policy_document(point.policy, level="ground")
        selected = point.policy.signature() == selected_signature
        payload = {
            "query_id": query_id,
            "expected_reward": point.expected_reward,
            "failure_probability": point.failure_probability,
            "selected": selected,
            "policy_id": policy["policy_id"],
        }
        frontier.append(
            {
                **payload,
                "frontier_point_id": object_id(payload, "frontier-point"),
                "policy": policy,
            }
        )
    selected_ids = [
        point["policy"]["policy_id"] for point in frontier if point["selected"]
    ]
    return {
        "query_id": query_id,
        "feasible": result.selected is not None,
        "composed_candidate_count": result.composed_candidate_count,
        "selection": {
            "status": "SELECTED" if result.selected is not None else "INFEASIBLE_QUERY",
            "selected_policy_id": selected_ids[0] if selected_ids else None,
        },
        "frontier": frontier,
    }


def _enumeration_document(result: Any, kernel: Any) -> dict[str, Any]:
    states = {_state_id(state): state for state in result.states}
    transitions = []
    failure_states: set[str] = set()
    for transition in result.transitions:
        record = {
            "depth": transition.depth,
            "state_id": _state_id(transition.state),
            "action_id": _action_id(transition.action),
            "action": transition.action,
            "outcomes": [
                {
                    "probability": outcome.probability,
                    "next_state_id": _state_id(outcome.next_state),
                    "reward_features": outcome.reward_features,
                    "entered_failure": outcome.failure,
                    "terminal": outcome.terminal,
                }
                for outcome in transition.outcomes
            ],
        }
        record["transition_id"] = object_id(record, "transition")
        transitions.append(record)
        failure_states.update(
            _state_id(outcome.next_state)
            for outcome in transition.outcomes
            if outcome.failure
        )
    terminal = {identifier for identifier, state in states.items() if kernel.is_terminal(state)}
    kernel_payload = {"horizon": result.horizon, "transitions": transitions}
    return {
        "status": result.status,
        "evaluation_tier": result.evaluation_tier,
        "complete": result.complete,
        "horizon": result.horizon,
        "state_count": result.state_count,
        "state_count_lower_bound": result.state_count_lower_bound,
        "state_count_by_depth": [len(layer) for layer in result.layers],
        "cap_handling": {
            "state_cap": STATE_CAP,
            "cap_exceeded": result.status is EnumerationStatus.STATE_CAP_EXCEEDED,
            "truncated_result_is_exact_sound": False,
        },
        "layers": [[_state_id(state) for state in layer] for layer in result.layers],
        "states": [
            {
                "id": identifier,
                "state": state,
                "terminal": kernel.is_terminal(state),
            }
            for identifier, state in sorted(states.items())
        ],
        "failure_set": sorted(failure_states),
        "success_set": sorted(terminal - failure_states),
        "failure_success_sets_disjoint": not bool(
            failure_states & (terminal - failure_states)
        ),
        "transitions": transitions,
        "transition_kernel_sha256": canonical_sha256(kernel_payload),
    }


def _state_time_graph_document(report: Any, kernel: Any, query_id: str) -> dict[str, Any]:
    quotient = report.quotient
    assignments = {
        (assignment.remaining, assignment.state): assignment
        for assignment in quotient.assignments
    }
    nodes = []
    for assignment in quotient.assignments:
        nodes.append(
            {
                "state_time_id": _state_time_id(assignment.state, assignment.remaining),
                "remaining_horizon": assignment.remaining,
                "state_id": _state_id(assignment.state),
                "state": assignment.state,
                "terminal": assignment.remaining == 0
                or kernel.is_terminal(assignment.state),
                "failure": assignment.state.status is G2048Status.FAILURE,
                "state_orbit_id": _cell_id(assignment.cell_id),
            }
        )
    transitions = []
    for assignment in quotient.assignments:
        if assignment.remaining <= 0 or kernel.is_terminal(assignment.state):
            continue
        for action in kernel.actions(assignment.state):
            outcomes = []
            for outcome in kernel.step(assignment.state, action):
                target_key = (assignment.remaining - 1, outcome.next_state)
                if target_key not in assignments:
                    raise AssertionError("state-time quotient is not kernel closed")
                outcomes.append(
                    {
                        "probability": outcome.probability,
                        "next_state_time_id": _state_time_id(
                            outcome.next_state, assignment.remaining - 1
                        ),
                        "reward_features": outcome.reward_features,
                        "entered_failure": outcome.failure,
                        "terminal": outcome.terminal,
                    }
                )
            record = {
                "remaining_horizon": assignment.remaining,
                "state_time_id": _state_time_id(
                    assignment.state, assignment.remaining
                ),
                "action_id": _action_id(action),
                "action": action,
                "outcomes": outcomes,
            }
            record["transition_id"] = object_id(record, "state-time-transition")
            transitions.append(record)
    payload = {
        "query_id": query_id,
        "complete": True,
        "horizon": quotient.horizon,
        "ground_state_time_count": len(nodes),
        "ground_state_action_pair_count": len(transitions),
        "nodes": nodes,
        "transitions": transitions,
    }
    return {
        **payload,
        "complete_state_time_graph_hash": canonical_sha256(payload),
    }


def _state_orbit_documents(report: Any, query_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    quotient = report.quotient
    canonicalizer_records = []
    canonicalizer_ids: dict[tuple[int, Any], str] = {}
    for assignment in quotient.assignments:
        canonical, chosen = canonicalize_state(assignment.state)
        all_transforms = [
            element.value
            for element in D4_ELEMENTS
            if transform_state(assignment.state, element) == canonical
        ]
        record = {
            "state_time_id": _state_time_id(assignment.state, assignment.remaining),
            "state_id": _state_id(assignment.state),
            "remaining_horizon": assignment.remaining,
            "state_orbit_id": _cell_id(assignment.cell_id),
            "canonical_state_id": _state_id(canonical),
            "canonicalizing_transform_ids": all_transforms,
            "chosen_transform_id": chosen.value,
            "tie_rule": "first_in_registered_D4_order",
            "failure_cell_pooling_exception": assignment.cell_id.kind.value
            == "absorbing_failure",
        }
        record["canonicalizer_record_id"] = object_id(record, "canonicalizer")
        canonicalizer_records.append(record)
        canonicalizer_ids[(assignment.remaining, assignment.state)] = record[
            "canonicalizer_record_id"
        ]

    orbit_records = []
    for orbit in quotient.state_time_orbits:
        record = {
            "state_orbit_id": _cell_id(orbit.cell_id),
            "remaining_horizon": orbit.cell_id.remaining,
            "kind": orbit.cell_id.kind.value,
            "canonical_state_id": (
                _state_id(orbit.representative)
                if orbit.representative is not None
                else None
            ),
            "canonical_state": orbit.representative,
            "member_state_time_ids": [
                _state_time_id(state, orbit.cell_id.remaining) for state in orbit.members
            ],
            "member_state_ids": [_state_id(state) for state in orbit.members],
            "canonicalizer_record_ids": [
                canonicalizer_ids[(orbit.cell_id.remaining, state)]
                for state in orbit.members
            ],
            "stabilizer_element_ids": [element.value for element in orbit.stabilizer],
            "terminal": orbit.terminal,
            "failure": orbit.failure,
        }
        orbit_records.append(record)
    state_orbits = {
        "query_id": query_id,
        "partition_complete": True,
        "state_orbit_count": len(orbit_records),
        "state_orbit_ids": [record["state_orbit_id"] for record in orbit_records],
        "orbits": orbit_records,
    }
    canonicalizers = {
        "query_id": query_id,
        "canonicalizer": "lexicographic_board_then_status",
        "tie_order": [element.value for element in D4_ELEMENTS],
        "record_count": len(canonicalizer_records),
        "records": canonicalizer_records,
        "choice_independence_checks": [
            {
                "state_orbit_id": _cell_id(check.cell_id),
                "semantic_action_id": _action_orbit_id(check.cell_id, check.label),
                "alternative_representative_state_id": _state_id(
                    check.alternative_representative
                ),
                "transporter_choices_checked": check.transporter_choices_checked,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in quotient.canonicalizer_choice_checks
        ],
    }
    return state_orbits, canonicalizers


def _action_documents(
    report: Any, kernel: Any, query_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    quotient = report.quotient
    action_records = []
    for orbit in quotient.action_orbits:
        action_records.append(
            {
                "action_orbit_id": _action_orbit_id(orbit.cell_id, orbit.label),
                "state_orbit_id": _cell_id(orbit.cell_id),
                "remaining_horizon": orbit.cell_id.remaining,
                "representative_state_id": _state_id(orbit.representative_state),
                "stabilizer_element_ids": [element.value for element in orbit.stabilizer],
                "deduplicated_canonical_action_ids": [
                    _action_id(action) for action in orbit.representative_actions
                ],
                "canonical_action_id": _action_id(orbit.canonical_action),
                "canonical_actions": orbit.representative_actions,
                "deduplicated": len(orbit.representative_actions)
                == len(set(orbit.representative_actions)),
            }
        )
    concretizer_records = []
    for record in quotient.concretizations:
        support = [action for _, action in record.action_distribution]
        probabilities = [probability for probability, _ in record.action_distribution]
        payload = {
            "state_time_id": _state_time_id(record.state, record.cell_id.remaining),
            "state_id": _state_id(record.state),
            "remaining_horizon": record.cell_id.remaining,
            "state_orbit_id": _cell_id(record.cell_id),
            "semantic_action_id": _action_orbit_id(record.cell_id, record.label),
            "transporter_to_representative_ids": [
                element.value for element in record.transporters_to_representative
            ],
            "distinct_inverse_ground_action_ids": [
                _action_id(action) for action in support
            ],
            "distinct_inverse_ground_actions": support,
            "action_distribution": [
                {"probability": probability, "ground_action_id": _action_id(action)}
                for probability, action in record.action_distribution
            ],
            "exact_uniform_probability": Fraction(1, len(support)),
            "mass": sum(probabilities, Fraction(0)),
            "support_legal": set(support) <= set(kernel.actions(record.state)),
            "deduplicated": len(support) == len(set(support)),
        }
        concretizer_records.append(
            {**payload, "concretizer_id": object_id(payload, "concretizer")}
        )
    return (
        {
            "query_id": query_id,
            "semantic_action_definition": "stabilizer_orbit_at_canonical_state",
            "action_orbit_count": len(action_records),
            "action_orbit_ids": [
                record["action_orbit_id"] for record in action_records
            ],
            "action_orbits": action_records,
        },
        {
            "query_id": query_id,
            "construction": "uniform_over_distinct_inverse_ground_actions",
            "group_element_multiplicity_is_not_probability_weight": True,
            "record_count": len(concretizer_records),
            "records": concretizer_records,
        },
    )


def _automorphism_document(report: Any, query_id: str) -> dict[str, Any]:
    quotient = report.quotient
    state_checks = [
        {
            "remaining_horizon": check.remaining,
            "state_id": _state_id(check.state),
            "element_id": check.element.value,
            "transformed_state_id": _state_id(check.transformed_state),
            "terminal_semantics_preserved": check.terminal_semantics_preserved,
            "failure_semantics_preserved": check.failure_semantics_preserved,
            "legal_action_set_preserved": check.legal_action_set_preserved,
            "passed": check.passed,
            "detail": check.detail,
        }
        for check in quotient.state_automorphism_checks
    ]
    transition_checks = [
        {
            "remaining_horizon": check.remaining,
            "state_id": _state_id(check.state),
            "action_id": _action_id(check.action),
            "element_id": check.element.value,
            "transformed_state_id": _state_id(check.transformed_state),
            "transformed_action_id": _action_id(check.transformed_action),
            "legal_action_image_equal": check.passed,
            "reward_features_equal": check.passed,
            "one_time_failure_cost_equal": check.passed,
            "terminal_semantics_equal": check.passed,
            "coalesced_exact_kernel_equal": check.passed,
            "passed": check.passed,
            "detail": check.detail,
        }
        for check in quotient.automorphism_checks
    ]
    return {
        "query_id": query_id,
        "exhaustive_over_complete_state_time_graph": True,
        "state_check_count": len(state_checks),
        "state_action_group_check_count": len(transition_checks),
        "all_passed": all(
            check["passed"] for check in (*state_checks, *transition_checks)
        ),
        "state_checks": state_checks,
        "transition_checks": transition_checks,
    }


def _model_documents(report: Any, query_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    quotient = report.quotient
    transition_map = {
        (transition.cell_id, transition.label): transition
        for transition in quotient.transitions
    }
    nominal_entries = []
    envelope_entries = []
    audit_entries = []
    for action_orbit in quotient.action_orbits:
        key = (action_orbit.cell_id, action_orbit.label)
        transition = transition_map[key]
        entry_payload = {
            "state_orbit_id": _cell_id(transition.cell_id),
            "semantic_action_id": _action_orbit_id(transition.cell_id, transition.label),
            "reward_features": transition.reward_features,
            "failure_probability": transition.failure_probability,
            "termination_probability": transition.termination_probability,
            "successor_probabilities": [
                {
                    "state_orbit_id": _cell_id(successor),
                    "probability": probability,
                }
                for successor, probability in transition.successor_probabilities
            ],
        }
        entry_id = object_id(entry_payload, "exact-quotient-entry")
        nominal_entries.append({**entry_payload, "entry_id": entry_id})
        width = next(
            width
            for width in quotient.envelope_widths
            if (width.cell_id, width.label) == key
        )
        envelope_entries.append(
            {
                "entry_id": entry_id,
                "state_orbit_id": entry_payload["state_orbit_id"],
                "semantic_action_id": entry_payload["semantic_action_id"],
                "reward_lower": transition.reward_features,
                "reward_upper": transition.reward_features,
                "failure_lower": transition.failure_probability,
                "failure_upper": transition.failure_probability,
                "termination_lower": transition.termination_probability,
                "termination_upper": transition.termination_probability,
                "transition_uncertainty": "singleton",
                "singleton_successor_distribution": entry_payload[
                    "successor_probabilities"
                ],
                "reward_feature_widths": width.reward_feature_widths,
                "failure_width": width.failure_width,
                "termination_width": width.termination_width,
                "successor_total_variation_width": width.successor_total_variation_width,
                "interval_width_zero": width.zero,
            }
        )
        realizations = [
            realization
            for realization in quotient.realizations
            if (realization.cell_id, realization.label) == key
        ]
        audit_entries.append(
            {
                "entry_id": entry_id,
                "state_orbit_id": entry_payload["state_orbit_id"],
                "semantic_action_id": entry_payload["semantic_action_id"],
                "representative_independent": all(
                    (
                        realization.reward_features,
                        realization.failure_probability,
                        realization.termination_probability,
                        realization.successor_probabilities,
                    )
                    == (
                        transition.reward_features,
                        transition.failure_probability,
                        transition.termination_probability,
                        transition.successor_probabilities,
                    )
                    for realization in realizations
                ),
                "representative_induced_tuples": [
                    {
                        "state_id": _state_id(realization.state),
                        "reward_features": realization.reward_features,
                        "failure_probability": realization.failure_probability,
                        "termination_probability": realization.termination_probability,
                        "successor_probabilities": [
                            {
                                "state_orbit_id": _cell_id(successor),
                                "probability": probability,
                            }
                            for successor, probability in realization.successor_probabilities
                        ],
                    }
                    for realization in realizations
                ],
            }
        )
    nominal = {
        "query_id": query_id,
        "model_kind": "exact_point_quotient",
        "nominal_equals_exact": True,
        "entry_count": len(nominal_entries),
        "entries": nominal_entries,
    }
    envelope = {
        "query_id": query_id,
        "model_kind": "singleton_sound_envelope",
        "uncertainty_sets_are_singletons": True,
        "maximum_reward_width": Fraction(0),
        "maximum_failure_width": Fraction(0),
        "maximum_transition_width": Fraction(0),
        "entries": envelope_entries,
    }
    audit = {
        "query_id": query_id,
        "representative_independent": report.validation.representative_independent,
        "check_count": len(audit_entries),
        "all_checks_passed": all(
            entry["representative_independent"] for entry in audit_entries
        ),
        "checks": audit_entries,
    }
    return nominal, envelope, audit


def _value_policy_document(report: Any, query_id: str, cell_ids: dict[Any, str]) -> dict[str, Any]:
    abstract_policy = _policy_document(
        report.abstract_selected_policy, level="abstract", cell_ids=cell_ids
    )
    checks = [
        {
            "state_time_id": _state_time_id(check.state, check.cell_id.remaining),
            "state_orbit_id": _cell_id(check.cell_id),
            "abstract_feasible": check.abstract_feasible,
            "ground_feasible": check.ground_feasible,
            "abstract_value": check.abstract_value,
            "abstract_risk": check.abstract_risk,
            "lifted_value": check.lifted_value,
            "lifted_risk": check.lifted_risk,
            "ground_value": check.ground_value,
            "ground_risk": check.ground_risk,
            "abstract_frontier_signature": check.abstract_frontier_signature,
            "ground_frontier_signature": check.ground_frontier_signature,
            "frontier_exact": check.frontier_exact,
            "abstract_unconstrained_value": check.abstract_unconstrained_value,
            "lifted_unconstrained_value": check.lifted_unconstrained_value,
            "ground_unconstrained_value": check.ground_unconstrained_value,
            "unconstrained_value_exact": check.unconstrained_value_exact,
            "constrained_result_exact": check.constrained_result_exact,
            "exact_match": check.exact_match,
        }
        for check in report.state_time_value_checks
    ]
    return {
        "query_id": query_id,
        "selector_class": "deterministic_finite_horizon_markov",
        "concretizer_class": "fixed_uniform_over_distinct_inverse_actions",
        "abstract_policy": abstract_policy,
        "per_state_time_value_equalities": checks,
        "all_state_time_values_exact": report.all_state_time_values_exact,
        "constrained_value_risk_equality": {
            "ground_value": report.ground_value,
            "ground_failure_probability": report.ground_risk,
            "abstract_value": report.abstract_value,
            "abstract_failure_probability": report.abstract_risk,
            "lifted_value": report.lifted_value,
            "lifted_failure_probability": report.lifted_risk,
            "exact": (report.ground_value, report.ground_risk)
            == (report.abstract_value, report.abstract_risk)
            == (report.lifted_value, report.lifted_risk),
        },
        "action_restriction_gap": report.delta_action,
        "zero_restriction_gap": report.delta_action == 0,
        "compression": report.compression,
        "strict_state_compression": report.compression.ground_state_time_count
        > report.compression.quotient_state_time_count,
        "strict_action_compression": report.compression.ground_legal_action_count
        > report.compression.semantic_action_orbit_count,
    }


def _policy_graph_document(report: Any, query_id: str, cell_ids: dict[Any, str]) -> dict[str, Any]:
    abstract_policy = _policy_document(
        report.abstract_selected_policy, level="abstract", cell_ids=cell_ids
    )
    lifted = []
    if report.lifted_ground_policy is not None:
        for decision in report.lifted_ground_policy.decisions:
            record = {
                "remaining": decision.cell_id.remaining,
                "state_time_id": _state_time_id(
                    decision.state, decision.cell_id.remaining
                ),
                "state_orbit_id": _cell_id(decision.cell_id),
                "semantic_action_id": _action_orbit_id(
                    decision.cell_id, decision.label
                ),
                "action_distribution": [
                    {
                        "probability": probability,
                        "ground_action_id": _action_id(action),
                    }
                    for probability, action in decision.action_distribution
                ],
            }
            record["lifted_decision_id"] = object_id(record, "lifted-decision")
            lifted.append(record)
    return {
        "query_id": query_id,
        "abstract_selector": abstract_policy,
        "lifted_policy_class": "deterministic_semantic_selector_plus_fixed_concretizer",
        "lifted_decisions": lifted,
    }


def run_exact_d4_baseline(output_dir: Path) -> dict[str, Any]:
    """Construct, solve, certify, and write the frozen safe-chain baseline."""

    started = _utc_now()
    kernel, query = safe_chain_fixture()
    group = safe_chain_d4_group(kernel)
    enumeration = enumerate_reachable(
        kernel,
        initial_distribution=query.initial_distribution,
        horizon=query.horizon,
        state_cap=STATE_CAP,
    )
    if enumeration.status is not EnumerationStatus.EXACT or not enumeration.complete:
        raise RuntimeError("safe-chain D4 baseline exceeded exact enumeration cap")
    ground = solve_ground_pareto(kernel, query)
    try:
        quotient = build_state_time_d4_quotient(
            kernel,
            query,
            group,
            is_failure=lambda state: state.status is G2048Status.FAILURE,
        )
        report = solve_exact_d4_quotient(
            kernel, query, quotient, ground_result=ground
        )
    except ExactD4QuotientInvariantViolation:
        raise
    except (AssertionError, ValueError) as error:
        raise ExactD4QuotientInvariantViolation((str(error),)) from error
    if not report.validation.exact:
        raise ExactD4QuotientInvariantViolation(report.validation.failures)
    frozen_value = Fraction(3, 64)
    frozen_failure = Fraction(99, 5000)
    if not (
        report.validation.exact
        and report.validation.automorphism_exact
        and report.validation.zero_width_exact_model
        and report.validation.representative_independent
        and report.validation.canonicalizer_choice_independent
        and report.validation.distinct_uniform_concretizer
        and report.all_state_time_values_exact
        and report.delta_action == 0
        and report.compression.ground_state_time_count
        > report.compression.quotient_state_time_count
        and report.compression.ground_legal_action_count
        > report.compression.semantic_action_orbit_count
        and report.ground_value == report.abstract_value == report.lifted_value == frozen_value
        and report.ground_risk == report.abstract_risk == report.lifted_risk == frozen_failure
    ):
        raise ExactD4QuotientInvariantViolation(
            ("safe-chain exact-D4 acceptance gate failed",)
        )

    source_hash = _source_tree_hash()
    profile = _profile_document(kernel.size)
    structural_basis = {
        "structural_key": SAFE_CHAIN_STRUCTURAL_KEY,
        "benchmark_role": "nontrivial_safe_planning_and_quotient_certificate",
        "display_name": kernel.display_name,
        "domain": "G2048-Select",
        "kernel": kernel.structural_key(),
        "group_profile_id": profile["group_profile_id"],
        "group_profile_hash": profile["group_profile_hash"],
        "group_profile_version": GROUP_PROFILE_VERSION,
        "abstraction_source": ABSTRACTION_SOURCE,
        "selector_class": "deterministic_finite_horizon_markov",
        "concretizer": "fixed_uniform_over_distinct_inverse_actions",
        "seed_ledger": {},
        "tape_ledger": {
            "exact_enumeration": {
                "tape_id": "tape-none-exact-rational-enumeration",
                "reason": "all stochastic laws are enumerated exactly",
            }
        },
    }
    structural_id = object_id(structural_basis, "structural")
    structural = {
        **structural_basis,
        "structural_id": structural_id,
        "fixture_id": structural_id,
    }
    build_payload = {
        "structural_id": structural_id,
        "group_profile_hash": profile["group_profile_hash"],
        "implementation": "acfqp.exact_d4_quotient.v1",
        "source_tree_sha256": source_hash,
    }
    build_id = object_id(build_payload, "build")
    query_payload = {
        "structural_id": structural_id,
        "query_name": "safe_chain_d4_uniform_h2",
        "initial_distribution_registration": [
            {
                "probability": probability,
                "state_id": _state_id(state),
                "state": state,
            }
            for probability, state in query.initial_distribution
        ],
        "horizon": query.horizon,
        "delta": query.delta,
        "reward_weights": query.reward_weights,
        "goal": query.goal,
        "normalizer": query.normalizer,
        "normalizer_value": query.normalizer_value,
        "normalizer_proof_id": query.normalizer_proof_id,
        "normalizer_proof": "each normalized merge reward is at most one; total is at most H",
    }
    query_id = object_id(query_payload, "query")
    query_document = {**query_payload, "query_id": query_id}

    enumeration_document = _enumeration_document(enumeration, kernel)
    kernel_hash = enumeration_document["transition_kernel_sha256"]
    graph_document = _state_time_graph_document(report, kernel, query_id)
    state_orbits, canonicalizers = _state_orbit_documents(report, query_id)
    action_orbits, concretizers = _action_documents(report, kernel, query_id)
    automorphisms = _automorphism_document(report, query_id)
    nominal, envelope, representative_audit = _model_documents(report, query_id)
    cell_ids = {
        orbit.cell_id: _cell_id(orbit.cell_id) for orbit in report.quotient.state_time_orbits
    }
    value_audit = _value_policy_document(report, query_id, cell_ids)
    policy_graph = _policy_graph_document(report, query_id, cell_ids)
    j0_document = _frontier_document(ground, query_id)
    proof_identity = {
        "structural_id": structural_id,
        "build_id": build_id,
        "kernel_hash": kernel_hash,
        "query_hash": query_id,
    }
    j0_proof_id = object_id(
        {
            "identity": proof_identity,
            "status": "FEASIBLE",
            "frontier": j0_document["frontier"],
        },
        "j0-proof",
    )
    j0_document.update(
        {
            "known_exact_j0_status": "FEASIBLE",
            "exact_j0_proof_id": j0_proof_id,
            "proof_identity": proof_identity,
            "oracle_accounting": {
                "ordinal": 1,
                "same_query": True,
                "composed_candidate_count": ground.composed_candidate_count,
            },
        }
    )

    certificate_payload = {
        "query_id": query_id,
        "status": CERTIFIED,
        "evidence": "exact_sound",
        "included_in_positive_claim": True,
        "claim_eligibility": "known_group_exact_quotient_eligible_after_certification",
        "supported_claim": "exact known-D4 state-action quotient preserves finite-horizon constrained planning",
        "unsupported_claims": [
            "automatic_symmetry_discovery",
            "predicate_grammar_discovery",
            "CEGAR_refinement_effectiveness",
            "learned_meta_controller_effectiveness",
        ],
        "abstraction_source": ABSTRACTION_SOURCE,
        "group_profile_id": profile["group_profile_id"],
        "group_profile_hash": profile["group_profile_hash"],
        "complete_state_time_graph_hash": graph_document[
            "complete_state_time_graph_hash"
        ],
        "ground_value": report.ground_value,
        "abstract_value": report.abstract_value,
        "lifted_value": report.lifted_value,
        "ground_failure_probability": report.ground_risk,
        "abstract_failure_probability": report.abstract_risk,
        "lifted_failure_probability": report.lifted_risk,
        "expected_failure_probability": frozen_failure,
        "expected_survival_probability": Fraction(4901, 5000),
        "risk_tolerance": query.delta,
        "action_restriction_gap": report.delta_action,
        "all_state_time_values_exact": report.all_state_time_values_exact,
        "zero_envelope_width": report.validation.zero_width_exact_model,
        "automorphism_exact": report.validation.automorphism_exact,
        "representative_independent": report.validation.representative_independent,
        "canonicalizer_choice_independent": report.validation.canonicalizer_choice_independent,
        "distinct_uniform_concretizer": report.validation.distinct_uniform_concretizer,
        "compression": report.compression,
        "strict_state_compression": report.compression.ground_state_time_count
        > report.compression.quotient_state_time_count,
        "strict_action_compression": report.compression.ground_legal_action_count
        > report.compression.semantic_action_orbit_count,
        "refinement_event_count": 0,
        "split_count": 0,
        "fallback_count": 0,
        "proof_dependencies": [
            {
                "artifact": path,
                "logical_sha256": canonical_sha256(document),
            }
            for path, document in (
                ("ground/state_time_graph.json", graph_document),
                ("symmetry/profile.json", profile),
                ("symmetry/automorphism_checks.json", automorphisms),
                ("symmetry/state_orbits.json", state_orbits),
                ("symmetry/canonicalizers.json", canonicalizers),
                ("symmetry/action_orbits.json", action_orbits),
                ("symmetry/concretizers.json", concretizers),
                ("rapm/nominal_exact.json", nominal),
                ("rapm/envelope_exact.json", envelope),
                ("audit/representative_independence.json", representative_audit),
                ("audit/value_policy_preservation.json", value_audit),
                ("ground/j0_frontier.json", j0_document),
            )
        ],
    }
    certificate = {
        **certificate_payload,
        "certificate_id": object_id(certificate_payload, "exact-d4-certificate"),
    }
    deterministic_documents: dict[str, Any] = {
        "config/structural.json": structural,
        "config/query.json": query_document,
        "ground/enumeration.json": enumeration_document,
        "ground/j0_frontier.json": j0_document,
        "ground/state_time_graph.json": graph_document,
        "symmetry/profile.json": profile,
        "symmetry/automorphism_checks.json": automorphisms,
        "symmetry/state_orbits.json": state_orbits,
        "symmetry/canonicalizers.json": canonicalizers,
        "symmetry/action_orbits.json": action_orbits,
        "symmetry/concretizers.json": concretizers,
        "rapm/nominal_exact.json": nominal,
        "rapm/envelope_exact.json": envelope,
        "audit/representative_independence.json": representative_audit,
        "audit/value_policy_preservation.json": value_audit,
        "result/policy_graph.json": policy_graph,
        "result/exact_d4_certificate.json": certificate,
    }
    semantic_hash = canonical_sha256(
        {
            path: deterministic_documents[path]
            for path in sorted(deterministic_documents)
        }
    )
    metrics = {
        "query_id": query_id,
        "status": CERTIFIED,
        "evidence": "exact_sound",
        "included_in_gate": True,
        "semantic_hash": semantic_hash,
        "normalizer_value": query.normalizer_value,
        "normalizer_proof_id": query.normalizer_proof_id,
        "raw_regret": Fraction(0),
        "normalized_regret": Fraction(0),
        "ground_state_time_count": report.compression.ground_state_time_count,
        "abstract_state_time_count": report.compression.quotient_state_time_count,
        "ground_state_action_pair_count": report.compression.ground_legal_action_count,
        "abstract_state_action_pair_count": report.compression.semantic_action_orbit_count,
        "state_compression_ratio": report.compression.state_compression_ratio,
        "action_compression_ratio": report.compression.action_compression_ratio,
        "maximum_reward_width": Fraction(0),
        "maximum_failure_width": Fraction(0),
        "maximum_transition_width": Fraction(0),
        "automorphism_check_count": report.validation.automorphism_check_count,
        "state_time_value_check_count": len(report.state_time_value_checks),
        "refinement_events": 0,
        "accepted_splits": 0,
        "fallback_invocations": 0,
        "ground_oracle_candidate_work": report.ground_composed_candidate_count,
        "abstract_oracle_candidate_work": report.abstract_composed_candidate_count,
    }
    run_id = object_id(
        {
            "structural_id": structural_id,
            "build_id": build_id,
            "query_id": query_id,
            "execution_profile": EXECUTION_PROFILE,
            "semantic_hash": semantic_hash,
        },
        "run",
    )
    run_document = {
        "schema_version": "exact_d4.v1",
        "contract_version": "0.4.0",
        "run_id": run_id,
        "fixture_id": structural_id,
        "structural_id": structural_id,
        "build_id": build_id,
        "query_id": query_id,
        "structural_key": SAFE_CHAIN_STRUCTURAL_KEY,
        "benchmark_role": "nontrivial_safe_planning_and_quotient_certificate",
        "execution_profile": EXECUTION_PROFILE,
        "domain": "g2048_safe_chain",
        "status": CERTIFIED,
        "evidence": "exact_sound",
        "semantic_hash": semantic_hash,
        "claim_eligibility": "known_group_exact_quotient_eligible_after_certification",
        "included_in_positive_claim": True,
        "abstraction_source": ABSTRACTION_SOURCE,
        "group_profile_id": profile["group_profile_id"],
        "group_profile_hash": profile["group_profile_hash"],
        "ordered_group_element_ids": [element.value for element in D4_ELEMENTS],
        "complete_state_time_graph_hash": graph_document[
            "complete_state_time_graph_hash"
        ],
        "state_orbit_ids": state_orbits["state_orbit_ids"],
        "action_orbit_ids": action_orbits["action_orbit_ids"],
        "known_exact_j0_status": "FEASIBLE",
        "known_exact_j0_proof_id": j0_proof_id,
        "known_exact_j0_structural_id": structural_id,
        "known_exact_j0_build_id": build_id,
        "known_exact_j0_kernel_hash": kernel_hash,
        "known_exact_j0_query_hash": query_id,
        "phase05_test_override": False,
        "refinement_enabled": False,
        "fallback_enabled": False,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "command": "PYTHONPATH=src python3 -m acfqp.d4_baseline --output artifacts/exact_d4",
        "vcs": "none",
        "source_tree_sha256": source_hash,
        "dirty_state_digest": source_hash,
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor() or "unreported",
        "worker_count": 1,
        "dependency_lock": {
            "runtime_dependencies": "stdlib_only",
            "pyproject_sha256": sha256_file(PROJECT_ROOT / "pyproject.toml"),
        },
        "seed_ledger": {"seed_ids": [], "deterministic": True},
        "random_tapes": {
            "tape_ids": ["tape-none-exact-rational-enumeration"]
        },
        "determinism_environment": {
            "PYTHONHASHSEED": os.environ.get(
                "PYTHONHASHSEED", "unset; canonical ordering enforced"
            )
        },
        "spec_hashes": _spec_hashes(),
        "reference_manifest_hashes": _reference_manifest_hashes(),
    }
    documents = {
        "run.json": run_document,
        **deterministic_documents,
        "metrics.json": metrics,
        "events.jsonl": [
            {"sequence": 1, "event": "complete_state_time_graph_enumerated"},
            {"sequence": 2, "event": "D4_automorphism_checks_passed"},
            {"sequence": 3, "event": "exact_D4_quotient_constructed"},
            {"sequence": 4, "event": "exact_quotient_solved_and_lifted"},
            {"sequence": 5, "event": CERTIFIED},
        ],
    }
    manifest = write_artifact_bundle(
        output_dir,
        documents,
        roles={
            path: contract[0]
            for path, contract in D4_BASELINE_DOCUMENT_CONTRACTS.items()
        },
        schemas={
            path: contract[1]
            for path, contract in D4_BASELINE_DOCUMENT_CONTRACTS.items()
        },
        required_paths=D4_BASELINE_REQUIRED_PATHS,
    )
    failures = verify_artifact_bundle(output_dir)
    if failures:
        raise AssertionError(f"artifact integrity failure: {failures}")
    return {
        "run_id": run_id,
        "status": CERTIFIED,
        "semantic_hash": semantic_hash,
        "ground_state_time_count": report.compression.ground_state_time_count,
        "abstract_state_time_count": report.compression.quotient_state_time_count,
        "ground_state_action_pair_count": report.compression.ground_legal_action_count,
        "abstract_state_action_pair_count": report.compression.semantic_action_orbit_count,
        "failure_probability": frozen_failure,
        "manifest_sha256": sha256_file(output_dir / "manifest.json"),
        "bundle_sha256": manifest["bundle_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "exact_d4",
        help="output directory (default: artifacts/exact_d4)",
    )
    arguments = parser.parse_args(argv)
    try:
        summary = run_exact_d4_baseline(arguments.output.resolve())
    except ExactD4QuotientInvariantViolation as error:
        print(
            json.dumps(
                {
                    "status": error.status,
                    "included_in_positive_claim": False,
                    "failures": error.failures,
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(to_jsonable(summary), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
