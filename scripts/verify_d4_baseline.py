#!/usr/bin/env python3
"""Independently verify and recompute the exact safe-chain D4 bundle."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.artifacts import (  # noqa: E402
    D4_BASELINE_DOCUMENT_CONTRACTS,
    D4_BASELINE_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    verify_artifact_bundle,
)
from acfqp.d4_baseline import (  # noqa: E402
    ABSTRACTION_SOURCE,
    CERTIFIED,
    EXECUTION_PROFILE,
    GROUP_PROFILE_VERSION,
    INVARIANT_VIOLATION,
    SEMANTIC_DOCUMENT_PATHS,
    _profile_document,
    _source_tree_hash,
    run_exact_d4_baseline,
)
from acfqp.domains import (  # noqa: E402
    D4_ELEMENTS,
    SAFE_CHAIN_STRUCTURAL_KEY,
    G2048Action,
    G2048State,
    canonicalize_state,
    inverse_d4,
    safe_chain_fixture,
    transform_action,
    transform_state,
)
from acfqp.domains.g2048 import G2048Status  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def exact(value: dict | int) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("boolean is not an exact rational")
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(value["numerator"], value["denominator"])


def _verify_reference_manifest_hashes(
    run: dict,
    failures: list[str],
    *,
    root: Path = ROOT,
) -> None:
    """Validate the optional local provenance-manifest pair."""

    relative_paths = (
        "reference/download_manifest.json",
        "reference/repo_clone_manifest.json",
    )
    paths = {relative: root / relative for relative in relative_paths}
    present = {relative: path.is_file() for relative, path in paths.items()}
    recorded = run.get("reference_manifest_hashes")
    if not isinstance(recorded, dict):
        failures.append("run reference_manifest_hashes is missing or malformed")
        return

    if all(present.values()):
        expected = {
            relative: sha256_file(path) for relative, path in paths.items()
        }
        if recorded != expected:
            failures.append(
                "run reference-manifest hashes do not exactly match the complete local pair"
            )
        return

    if not any(present.values()):
        if recorded:
            failures.append(
                "run reference-manifest hashes must be empty when the local pair is absent"
            )
        return

    missing = sorted(relative for relative, exists in present.items() if not exists)
    failures.append(
        "local reference-manifest pair is incomplete; missing: " + ", ".join(missing)
    )


def _state(value: dict) -> G2048State:
    return G2048State(tuple(value["board"]), G2048Status(value["status"]))


def _action(value: dict) -> G2048Action:
    return G2048Action(value["first"], value["second"], value["survivor"])


def _coalesced_outcome_measure(
    kernel: Any,
    state: G2048State,
    action: G2048Action,
    *,
    transform: Any | None = None,
) -> dict[tuple[G2048State, tuple, bool, bool], Fraction]:
    """Recompute one exact kernel measure without using quotient evidence."""

    measure: dict[tuple[G2048State, tuple, bool, bool], Fraction] = {}
    for outcome in kernel.step(state, action):
        next_state = (
            transform_state(outcome.next_state, transform)
            if transform is not None
            else outcome.next_state
        )
        key = (
            next_state,
            tuple(sorted(outcome.reward_features)),
            bool(outcome.failure),
            bool(outcome.terminal),
        )
        measure[key] = measure.get(key, Fraction(0)) + outcome.probability
    return measure


def _logical_documents(bundle: Path) -> dict[str, dict]:
    return {path: load(bundle / path) for path in SEMANTIC_DOCUMENT_PATHS}


def _verify_manifest_contract(bundle: Path, failures: list[str]) -> set[str]:
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        return set()
    manifest = load(manifest_path)
    records = {
        record.get("path"): record
        for record in manifest.get("files", [])
        if isinstance(record, dict)
    }
    paths = set(records)
    required = set(D4_BASELINE_REQUIRED_PATHS)
    for path in sorted(required - paths):
        failures.append(f"required D4 path absent from manifest: {path}")
    for path in sorted(paths):
        record = records[path]
        contract = D4_BASELINE_DOCUMENT_CONTRACTS.get(path)
        if contract is None:
            failures.append(f"unexpected exact-D4 artifact path: {path}")
            continue
        expected_role, expected_schema = contract
        if record.get("required") is not True:
            failures.append(f"D4 path is not marked required: {path}")
        if record.get("role") != expected_role:
            failures.append(f"manifest role mismatch: {path}")
        if record.get("schema") != expected_schema:
            failures.append(f"manifest schema mismatch: {path}")
    forbidden_markers = ("refinement/", "witness", "candidate", "split", "fallback")
    for path in paths:
        if any(marker in path.lower() for marker in forbidden_markers):
            failures.append(f"exact-D4 bundle contains forbidden refinement/fallback file: {path}")
    return paths


def _verify_policy(policy: dict | None, failures: list[str], location: str) -> None:
    if policy is None:
        failures.append(f"{location}: certified baseline lacks a policy")
        return
    if policy.get("selector_class") != "deterministic_finite_horizon_markov":
        failures.append(f"{location}: selector is not deterministic finite-horizon Markov")
    decisions = policy.get("decisions", [])
    keys = [
        (decision.get("remaining"), decision.get("state_or_cell"))
        for decision in decisions
    ]
    if len(keys) != len(set(keys)):
        failures.append(f"{location}: duplicate state/cell-horizon decision")
    node_ids = [decision.get("node_id") for decision in decisions]
    if None in node_ids or len(node_ids) != len(set(node_ids)):
        failures.append(f"{location}: policy node IDs are missing or duplicated")
    payload = dict(policy)
    policy_id = payload.pop("policy_id", None)
    if policy_id != object_id(payload, "policy"):
        failures.append(f"{location}: policy ID is not content addressed")


def verify_exact_d4_bundle(bundle: Path, *, recompute: bool = True) -> dict:
    failures = verify_artifact_bundle(bundle)
    declared_paths = _verify_manifest_contract(bundle, failures)
    required = set(D4_BASELINE_REQUIRED_PATHS)
    if not required <= declared_paths:
        return {
            "verified": False,
            "failures": failures,
            "status": INVARIANT_VIOLATION,
            "recorded_status": None,
            "included_in_positive_claim": False,
            "semantic_hash": None,
            "recomputed_semantic_hash": None,
        }

    run = load(bundle / "run.json")
    structural = load(bundle / "config/structural.json")
    query = load(bundle / "config/query.json")
    enumeration = load(bundle / "ground/enumeration.json")
    j0 = load(bundle / "ground/j0_frontier.json")
    graph = load(bundle / "ground/state_time_graph.json")
    profile = load(bundle / "symmetry/profile.json")
    automorphisms = load(bundle / "symmetry/automorphism_checks.json")
    state_orbits = load(bundle / "symmetry/state_orbits.json")
    canonicalizers = load(bundle / "symmetry/canonicalizers.json")
    action_orbits = load(bundle / "symmetry/action_orbits.json")
    concretizers = load(bundle / "symmetry/concretizers.json")
    nominal = load(bundle / "rapm/nominal_exact.json")
    envelope = load(bundle / "rapm/envelope_exact.json")
    representative = load(bundle / "audit/representative_independence.json")
    values = load(bundle / "audit/value_policy_preservation.json")
    policy_graph = load(bundle / "result/policy_graph.json")
    certificate = load(bundle / "result/exact_d4_certificate.json")
    metrics = load(bundle / "metrics.json")
    events = [
        json.loads(line)
        for line in (bundle / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]

    if run.get("execution_profile") != EXECUTION_PROFILE:
        failures.append("run has the wrong exact-D4 execution profile")
    if run.get("contract_version") != "0.4.0":
        failures.append("run has the wrong normative contract version")
    if run.get("status") != CERTIFIED or certificate.get("status") != CERTIFIED:
        failures.append("run/certificate status is not CERTIFIED")
    if run.get("structural_key") != SAFE_CHAIN_STRUCTURAL_KEY:
        failures.append("run has the wrong safe-chain structural key")
    if run.get("abstraction_source") != ABSTRACTION_SOURCE:
        failures.append("run incorrectly claims a discovered abstraction")
    if run.get("phase05_test_override") is not False:
        failures.append("exact-D4 baseline cannot use the Phase 0.5 override")
    if run.get("refinement_enabled") is not False or run.get("fallback_enabled") is not False:
        failures.append("exact-D4 run enables refinement or fallback")
    if run.get("source_tree_sha256") != _source_tree_hash():
        failures.append("run source-tree hash is stale for the current workspace")
    expected_spec_parents = {
        "DECISION_LEDGER.md",
        *(path.relative_to(ROOT).as_posix() for path in (ROOT / "specs").glob("*.md")),
    }
    if set(run.get("spec_hashes", {})) != expected_spec_parents:
        failures.append("run spec-hash inventory is incomplete")
    for relative, recorded in run.get("spec_hashes", {}).items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != recorded:
            failures.append(f"run spec parent hash is stale: {relative}")
    _verify_reference_manifest_hashes(run, failures)

    structural_payload = dict(structural)
    structural_id = structural_payload.pop("structural_id", None)
    fixture_id = structural_payload.pop("fixture_id", None)
    if structural_id != fixture_id or structural_id != object_id(
        structural_payload, "structural"
    ):
        failures.append("structural ID is not content addressed")
    if run.get("structural_id") != structural_id or run.get("fixture_id") != structural_id:
        failures.append("run structural identity does not resolve")
    if structural.get("group_profile_hash") != profile.get("group_profile_hash"):
        failures.append("structural group profile hash does not resolve")
    expected_build_id = object_id(
        {
            "structural_id": structural_id,
            "group_profile_hash": profile.get("group_profile_hash"),
            "implementation": "acfqp.exact_d4_quotient.v1",
            "source_tree_sha256": run.get("source_tree_sha256"),
        },
        "build",
    )
    if run.get("build_id") != expected_build_id:
        failures.append("run build ID is not content addressed")

    expected_profile = _profile_document(2)
    if profile != expected_profile:
        failures.append("registered D4 profile/order/table differs from authoritative code")
    if profile.get("profile_version") != GROUP_PROFILE_VERSION:
        failures.append("D4 group profile version mismatch")
    expected_elements = [element.value for element in D4_ELEMENTS]
    if run.get("ordered_group_element_ids") != expected_elements:
        failures.append("run group-element order differs from the registered tie order")

    query_payload = dict(query)
    query_id = query_payload.pop("query_id", None)
    if query_id != object_id(query_payload, "query") or run.get("query_id") != query_id:
        failures.append("query ID is not content addressed or run-bound")
    if query.get("horizon") != 2 or exact(query.get("delta")) != Fraction(1, 20):
        failures.append("safe-chain query H/delta differs from the frozen query")
    if exact(query.get("normalizer_value")) != Fraction(2) or query.get(
        "normalizer"
    ) != query.get("normalizer_value"):
        failures.append("safe-chain query normalizer is invalid")
    initial = query.get("initial_distribution_registration", [])
    if len(initial) != 8 or any(exact(item["probability"]) != Fraction(1, 8) for item in initial):
        failures.append("safe-chain rho0 is not uniform on eight states")
    kernel, expected_query = safe_chain_fixture()
    expected_initial = {
        object_id(state, "state") for _, state in expected_query.initial_distribution
    }
    if {item.get("state_id") for item in initial} != expected_initial:
        failures.append("safe-chain rho0 is not the frozen D4 base-board orbit")

    if enumeration.get("status") != "EXACT" or enumeration.get("complete") is not True:
        failures.append("ground enumeration is not complete and exact")
    states = enumeration.get("states", [])
    state_ids = [record.get("id") for record in states]
    if None in state_ids or len(state_ids) != len(set(state_ids)):
        failures.append("ground enumeration state IDs are missing or duplicated")
    for record in states:
        if record.get("id") != object_id(record.get("state"), "state"):
            failures.append("ground enumeration has a noncanonical state ID")
    graph_payload = dict(graph)
    graph_hash = graph_payload.pop("complete_state_time_graph_hash", None)
    if graph_hash != canonical_sha256(graph_payload):
        failures.append("complete state-time graph hash is inconsistent")
    if run.get("complete_state_time_graph_hash") != graph_hash:
        failures.append("run state-time graph hash does not resolve")
    graph_nodes = graph.get("nodes", [])
    graph_node_ids = [node.get("state_time_id") for node in graph_nodes]
    if None in graph_node_ids or len(graph_node_ids) != len(set(graph_node_ids)):
        failures.append("state-time graph node IDs are missing or duplicated")
    if graph.get("ground_state_time_count") != len(graph_nodes):
        failures.append("state-time graph node count is inconsistent")
    for node in graph_nodes:
        state = _state(node["state"])
        expected_terminal = node.get("remaining_horizon") == 0 or kernel.is_terminal(
            state
        )
        if node.get("terminal") is not expected_terminal:
            failures.append("state-time node terminal flag ignores h=0 semantics")
    transition_ids = [item.get("transition_id") for item in graph.get("transitions", [])]
    if None in transition_ids or len(transition_ids) != len(set(transition_ids)):
        failures.append("state-time transition IDs are missing or duplicated")
    if graph.get("ground_state_action_pair_count") != len(transition_ids):
        failures.append("state-time ground action-pair count is inconsistent")
    for transition in graph.get("transitions", []):
        for outcome in transition.get("outcomes", []):
            if outcome.get("next_state_time_id") not in set(graph_node_ids):
                failures.append("state-time transition target is unresolved")

    orbit_records = state_orbits.get("orbits", [])
    orbit_record_by_id = {
        orbit.get("state_orbit_id"): orbit for orbit in orbit_records
    }
    orbit_ids = [orbit.get("state_orbit_id") for orbit in orbit_records]
    if orbit_ids != state_orbits.get("state_orbit_ids") or orbit_ids != run.get(
        "state_orbit_ids"
    ):
        failures.append("state-orbit inventory/order does not resolve")
    member_ids = [
        member
        for orbit in orbit_records
        for member in orbit.get("member_state_time_ids", [])
    ]
    if len(member_ids) != len(set(member_ids)) or set(member_ids) != set(graph_node_ids):
        failures.append("state-orbit partition is incomplete or overlapping")
    node_by_id = {node["state_time_id"]: node for node in graph_nodes}
    raw_state_by_id = {
        node["state_id"]: _state(node["state"])
        for node in graph_nodes
        if "state" in node
    }
    for orbit in orbit_records:
        remaining = orbit.get("remaining_horizon")
        if any(
            node_by_id[member].get("remaining_horizon") != remaining
            for member in orbit.get("member_state_time_ids", [])
            if member in node_by_id
        ):
            failures.append("state orbit merges different remaining horizons")
        if orbit.get("failure") and (
            orbit.get("kind") != "absorbing_failure" or not orbit.get("terminal")
        ):
            failures.append("failure orbit is not an absorbing terminal F_h cell")
        if not orbit.get("failure") and orbit.get("kind") == "absorbing_failure":
            failures.append("nonfailure orbit is labelled as F_h")
        if remaining == 0 and not orbit.get("terminal"):
            failures.append("h=0 state orbit is not terminal")
        if not orbit.get("failure"):
            canonical_value = orbit.get("canonical_state")
            if canonical_value is None:
                failures.append("ordinary state orbit lacks a canonical representative")
                continue
            canonical = _state(canonical_value)
            expected_members = {
                transform_state(canonical, element) for element in D4_ELEMENTS
            }
            stored_members = {
                raw_state_by_id[state_id]
                for state_id in orbit.get("member_state_ids", [])
                if state_id in raw_state_by_id
            }
            if stored_members != expected_members:
                failures.append("ordinary state-orbit members are not exactly {g x_c}")
            expected_stabilizer = [
                element.value
                for element in D4_ELEMENTS
                if transform_state(canonical, element) == canonical
            ]
            if orbit.get("stabilizer_element_ids") != expected_stabilizer:
                failures.append("state-orbit stabilizer differs from {g: g x_c=x_c}")

    canonicalizer_records = canonicalizers.get("records", [])
    if canonicalizers.get("tie_order") != expected_elements:
        failures.append("canonicalizer tie order differs from the registered D4 order")
    if len(canonicalizer_records) != len(graph_nodes):
        failures.append("canonicalizer inventory does not cover every state-time node")
    for record in canonicalizer_records:
        state = raw_state_by_id.get(record.get("state_id"))
        if state is None:
            failures.append("canonicalizer references an unknown ground state")
            continue
        canonical, chosen = canonicalize_state(state)
        transforms = [
            element.value
            for element in D4_ELEMENTS
            if transform_state(state, element) == canonical
        ]
        if record.get("canonical_state_id") != object_id(canonical, "state"):
            failures.append("canonicalizer chose the wrong orbit representative")
        if record.get("canonicalizing_transform_ids") != transforms:
            failures.append("canonicalizer transform set is incomplete")
        if record.get("chosen_transform_id") != chosen.value:
            failures.append("canonicalizer tie choice is nondeterministic or stale")
    if not all(
        check.get("passed") for check in canonicalizers.get("choice_independence_checks", [])
    ):
        failures.append("canonicalizer-choice independence has a failed check")

    action_records = action_orbits.get("action_orbits", [])
    action_orbit_ids = [record.get("action_orbit_id") for record in action_records]
    if action_orbit_ids != action_orbits.get("action_orbit_ids") or action_orbit_ids != run.get(
        "action_orbit_ids"
    ):
        failures.append("semantic action-orbit inventory/order does not resolve")
    action_record_by_id = {
        record.get("action_orbit_id"): record for record in action_records
    }
    for record in action_records:
        parent_orbit = orbit_record_by_id.get(record.get("state_orbit_id"))
        if parent_orbit is None:
            failures.append("semantic action orbit references an unknown state orbit")
            continue
        if parent_orbit.get("terminal") or parent_orbit.get("failure"):
            failures.append("terminal/failure state orbit exposes a semantic action")
        if record.get("representative_state_id") != parent_orbit.get(
            "canonical_state_id"
        ):
            failures.append("semantic action representative differs from its state orbit")
        if record.get("stabilizer_element_ids") != parent_orbit.get(
            "stabilizer_element_ids"
        ):
            failures.append("semantic action cites the wrong state stabilizer")
        action_ids = record.get("deduplicated_canonical_action_ids", [])
        if len(action_ids) != len(set(action_ids)) or not record.get("deduplicated"):
            failures.append("semantic action orbit retains a duplicate stabilizer image")
        actions = record.get("canonical_actions", [])
        if action_ids != [object_id(action, "action") for action in actions]:
            failures.append("semantic action IDs do not address their canonical actions")
        if record.get("canonical_action_id") not in action_ids:
            failures.append("semantic action canonical representative is unresolved")
            continue
        if record.get("canonical_action_id") != action_ids[0]:
            failures.append("semantic action canonical representative violates tie order")
        canonical_index = action_ids.index(record["canonical_action_id"])
        canonical_action = _action(actions[canonical_index])
        stabilizer_ids = record.get("stabilizer_element_ids", [])
        try:
            stabilizer = [
                next(element for element in D4_ELEMENTS if element.value == identifier)
                for identifier in stabilizer_ids
            ]
        except StopIteration:
            failures.append("semantic action orbit cites an unknown stabilizer element")
            continue
        expected_actions = sorted(
            {transform_action(canonical_action, element) for element in stabilizer},
            key=repr,
        )
        if actions != [
            {"first": action.first, "second": action.second, "survivor": action.survivor}
            for action in expected_actions
        ]:
            failures.append("semantic action members are not the deduplicated H_x orbit")

    for orbit in orbit_records:
        records = [
            record
            for record in action_records
            if record.get("state_orbit_id") == orbit.get("state_orbit_id")
        ]
        if orbit.get("terminal") or orbit.get("failure"):
            if records:
                failures.append("terminal/failure orbit has a nonempty abstract action set")
            continue
        canonical_value = orbit.get("canonical_state")
        if canonical_value is None:
            failures.append("active orbit lacks a canonical state for action coverage")
            continue
        legal_actions = set(kernel.actions(_state(canonical_value)))
        partitioned_actions = [
            _action(action)
            for record in records
            for action in record.get("canonical_actions", [])
        ]
        if (
            set(partitioned_actions) != legal_actions
            or len(partitioned_actions) != len(set(partitioned_actions))
        ):
            failures.append("semantic action orbits do not partition A(x_c) exactly")

    graph_state_by_time = {
        node["state_time_id"]: _state(node["state"]) for node in graph_nodes
    }
    concretizer_records = concretizers.get("records", [])
    concretizer_keys = [
        (record.get("state_time_id"), record.get("semantic_action_id"))
        for record in concretizer_records
    ]
    expected_concretizer_keys = {
        (member, record.get("action_orbit_id"))
        for record in action_records
        for member in orbit_record_by_id.get(
            record.get("state_orbit_id"), {}
        ).get("member_state_time_ids", [])
    }
    if (
        len(concretizer_keys) != len(set(concretizer_keys))
        or set(concretizer_keys) != expected_concretizer_keys
    ):
        failures.append("concretizer inventory does not cover each (x,h,abstract-action) once")
    for record in concretizer_records:
        support_ids = record.get("distinct_inverse_ground_action_ids", [])
        support = record.get("distinct_inverse_ground_actions", [])
        distribution = record.get("action_distribution", [])
        if len(support_ids) != len(set(support_ids)) or len(support_ids) != len(support):
            failures.append("concretizer support is not a distinct action set")
            continue
        if support_ids != [object_id(action, "action") for action in support]:
            failures.append("concretizer support IDs do not address their actions")
        if [item.get("ground_action_id") for item in distribution] != support_ids:
            failures.append("concretizer distribution support differs from K_x")
        expected_probability = Fraction(1, len(support_ids)) if support_ids else None
        if expected_probability is None or any(
            exact(item["probability"]) != expected_probability for item in distribution
        ):
            failures.append("concretizer is not uniform after distinct-action deduplication")
        if expected_probability is not None and exact(
            record.get("exact_uniform_probability")
        ) != expected_probability:
            failures.append("concretizer uniform-probability summary is inconsistent")
        if exact(record.get("mass")) != 1:
            failures.append("concretizer probability mass differs from one")
        state = graph_state_by_time.get(record.get("state_time_id"))
        if state is None:
            failures.append("concretizer state-time support is unresolved")
        else:
            legal = set(kernel.actions(state))
            if not {_action(action) for action in support} <= legal or not record.get(
                "support_legal"
            ):
                failures.append("concretizer contains an illegal ground action")
            semantic = action_record_by_id.get(record.get("semantic_action_id"))
            if semantic is None:
                failures.append("concretizer semantic action is unresolved")
            else:
                representative_state = raw_state_by_id.get(
                    semantic.get("representative_state_id")
                )
                canonical_ids = semantic.get(
                    "deduplicated_canonical_action_ids", []
                )
                canonical_actions = semantic.get("canonical_actions", [])
                canonical_id = semantic.get("canonical_action_id")
                if representative_state is None or canonical_id not in canonical_ids:
                    failures.append("concretizer canonical action/representative is unresolved")
                else:
                    canonical_action = _action(
                        canonical_actions[canonical_ids.index(canonical_id)]
                    )
                    transporters = [
                        element
                        for element in D4_ELEMENTS
                        if transform_state(state, element) == representative_state
                    ]
                    expected_transporter_ids = [
                        element.value for element in transporters
                    ]
                    if record.get("transporter_to_representative_ids") != expected_transporter_ids:
                        failures.append("concretizer transporter set differs from {t:t x=x_c}")
                    expected_support = sorted(
                        {
                            transform_action(canonical_action, inverse_d4(element))
                            for element in transporters
                        },
                        key=repr,
                    )
                    expected_support_ids = [
                        object_id(action, "action") for action in expected_support
                    ]
                    if support_ids != expected_support_ids:
                        failures.append("concretizer K_x is not the deduplicated inverse-action set")
        payload = dict(record)
        concretizer_id = payload.pop("concretizer_id", None)
        if concretizer_id != object_id(payload, "concretizer"):
            failures.append("concretizer ID is not content addressed")

    if not automorphisms.get("exhaustive_over_complete_state_time_graph"):
        failures.append("automorphism evidence is not exhaustive")
    state_checks = automorphisms.get("state_checks", [])
    transition_checks = automorphisms.get("transition_checks", [])
    if automorphisms.get("state_check_count") != len(state_checks) or automorphisms.get(
        "state_action_group_check_count"
    ) != len(transition_checks):
        failures.append("automorphism check counts are inconsistent")
    if not automorphisms.get("all_passed") or not all(
        check.get("passed") for check in (*state_checks, *transition_checks)
    ):
        failures.append("a D4 automorphism check failed")
    expected_state_checks = len(graph_nodes) * len(D4_ELEMENTS)
    expected_transition_checks = len(graph.get("transitions", [])) * len(D4_ELEMENTS)
    if len(state_checks) != expected_state_checks or len(transition_checks) != expected_transition_checks:
        failures.append("automorphism checks do not cover every graph node/action/group element")
    graph_state_time = {
        (node["remaining_horizon"], _state(node["state"])): node
        for node in graph_nodes
    }
    direct_state_checks = 0
    direct_transition_checks = 0
    direct_automorphism_exact = True
    for node in graph_nodes:
        remaining = node["remaining_horizon"]
        state = _state(node["state"])
        source_actions = set(kernel.actions(state))
        for element in D4_ELEMENTS:
            direct_state_checks += 1
            transformed_state = transform_state(state, element)
            transformed_node = graph_state_time.get((remaining, transformed_state))
            if transformed_node is None:
                direct_automorphism_exact = False
                continue
            transformed_actions = {
                transform_action(action, element) for action in source_actions
            }
            if transformed_actions != set(kernel.actions(transformed_state)):
                direct_automorphism_exact = False
            if transformed_node.get("terminal") is not node.get("terminal"):
                direct_automorphism_exact = False
            if transformed_node.get("failure") is not node.get("failure"):
                direct_automorphism_exact = False
            if remaining <= 0 or node.get("terminal"):
                continue
            for action in source_actions:
                direct_transition_checks += 1
                transformed_action = transform_action(action, element)
                if _coalesced_outcome_measure(
                    kernel, state, action, transform=element
                ) != _coalesced_outcome_measure(
                    kernel, transformed_state, transformed_action
                ):
                    direct_automorphism_exact = False
    if (
        not direct_automorphism_exact
        or direct_state_checks != expected_state_checks
        or direct_transition_checks != expected_transition_checks
    ):
        failures.append("registered kernel fails independent exact D4 automorphism recomputation")

    nominal_entries = nominal.get("entries", [])
    envelope_entries = envelope.get("entries", [])
    nominal_ids = {entry.get("entry_id") for entry in nominal_entries}
    if nominal.get("model_kind") != "exact_point_quotient" or not nominal.get(
        "nominal_equals_exact"
    ):
        failures.append("nominal quotient is not labelled as the exact point model")
    if envelope.get("model_kind") != "singleton_sound_envelope" or not envelope.get(
        "uncertainty_sets_are_singletons"
    ):
        failures.append("D4 envelope is not a singleton exact model")
    for field in (
        "maximum_reward_width",
        "maximum_failure_width",
        "maximum_transition_width",
    ):
        if exact(envelope.get(field)) != 0:
            failures.append(f"D4 envelope records nonzero {field}")
    for entry in envelope_entries:
        if entry.get("entry_id") not in nominal_ids:
            failures.append("envelope entry does not resolve to an exact nominal entry")
        if (
            entry.get("reward_lower") != entry.get("reward_upper")
            or entry.get("failure_lower") != entry.get("failure_upper")
            or entry.get("termination_lower") != entry.get("termination_upper")
            or entry.get("transition_uncertainty") != "singleton"
            or not entry.get("interval_width_zero")
        ):
            failures.append("D4 exact envelope fails to collapse to point values")
        for field in (
            "failure_width",
            "termination_width",
            "successor_total_variation_width",
        ):
            if exact(entry.get(field)) != 0:
                failures.append("D4 exact envelope contains a nonzero interval width")
        if any(exact(item[1]) != 0 for item in entry.get("reward_feature_widths", [])):
            failures.append("D4 exact envelope contains a nonzero reward width")
    if not representative.get("representative_independent") or not representative.get(
        "all_checks_passed"
    ) or not all(check.get("representative_independent") for check in representative.get("checks", [])):
        failures.append("representative-induced quotient tuples are not identical")

    value_checks = values.get("per_state_time_value_equalities", [])
    if len(value_checks) != len(graph_nodes):
        failures.append("value-preservation audit does not cover every state-time node")
    if not values.get("all_state_time_values_exact") or not all(
        check.get("exact_match")
        and check.get("frontier_exact")
        and check.get("unconstrained_value_exact")
        and check.get("constrained_result_exact")
        for check in value_checks
    ):
        failures.append("per-state-time exact value/frontier preservation failed")
    root_equality = values.get("constrained_value_risk_equality", {})
    if not root_equality.get("exact"):
        failures.append("root ground/abstract/lifted value-risk equality failed")
    expected_value = Fraction(3, 64)
    expected_failure = Fraction(99, 5000)
    if any(
        exact(root_equality[field]) != expected
        for field, expected in (
            ("ground_value", expected_value),
            ("abstract_value", expected_value),
            ("lifted_value", expected_value),
            ("ground_failure_probability", expected_failure),
            ("abstract_failure_probability", expected_failure),
            ("lifted_failure_probability", expected_failure),
        )
    ):
        failures.append("root exact value or frozen 99/5000 risk regression differs")
    if exact(values.get("action_restriction_gap")) != 0 or not values.get(
        "zero_restriction_gap"
    ):
        failures.append("D4 quotient has a nonzero action-restriction gap")
    compression = values.get("compression", {})
    if not (
        compression.get("ground_state_time_count", 0)
        > compression.get("quotient_state_time_count", 0)
        and compression.get("ground_legal_action_count", 0)
        > compression.get("semantic_action_orbit_count", 0)
        and values.get("strict_state_compression")
        and values.get("strict_action_compression")
    ):
        failures.append("exact-D4 certificate does not strictly compress state and action graphs")

    _verify_policy(
        policy_graph.get("abstract_selector"), failures, "result/policy_graph.json"
    )
    lifted_decisions = policy_graph.get("lifted_decisions", [])
    lifted_keys = [
        (record.get("remaining"), record.get("state_time_id"))
        for record in lifted_decisions
    ]
    if len(lifted_keys) != len(set(lifted_keys)):
        failures.append("lifted policy has duplicate state-time decisions")

    if exact(certificate.get("expected_failure_probability")) != expected_failure or exact(
        certificate.get("expected_survival_probability")
    ) != Fraction(4901, 5000):
        failures.append("certificate does not carry the frozen safe-chain probability")
    if exact(certificate.get("action_restriction_gap")) != 0:
        failures.append("certificate action-restriction gap is nonzero")
    for field in (
        "included_in_positive_claim",
        "all_state_time_values_exact",
        "zero_envelope_width",
        "automorphism_exact",
        "representative_independent",
        "canonicalizer_choice_independent",
        "distinct_uniform_concretizer",
        "strict_state_compression",
        "strict_action_compression",
    ):
        if certificate.get(field) is not True:
            failures.append(f"certificate required invariant is false: {field}")
    if any(certificate.get(field) != 0 for field in ("refinement_event_count", "split_count", "fallback_count")):
        failures.append("certificate records a forbidden refinement/split/fallback operation")
    certificate_payload = dict(certificate)
    certificate_id = certificate_payload.pop("certificate_id", None)
    if certificate_id != object_id(certificate_payload, "exact-d4-certificate"):
        failures.append("exact-D4 certificate ID is not content addressed")
    for dependency in certificate.get("proof_dependencies", []):
        artifact = dependency.get("artifact")
        if artifact not in declared_paths:
            failures.append(f"certificate dependency is unresolved: {artifact}")
        elif dependency.get("logical_sha256") != canonical_sha256(load(bundle / artifact)):
            failures.append(f"certificate dependency hash is stale: {artifact}")

    selected = [point for point in j0.get("frontier", []) if point.get("selected")]
    if not j0.get("feasible") or len(selected) != 1:
        failures.append("ground J0 does not select exactly one feasible policy")
    elif exact(selected[0]["failure_probability"]) != expected_failure:
        failures.append("ground J0 selected risk differs from 99/5000")
    proof_identity = {
        "structural_id": structural_id,
        "build_id": run.get("build_id"),
        "kernel_hash": enumeration.get("transition_kernel_sha256"),
        "query_hash": query_id,
    }
    expected_proof_id = object_id(
        {"identity": proof_identity, "status": "FEASIBLE", "frontier": j0.get("frontier")},
        "j0-proof",
    )
    if j0.get("proof_identity") != proof_identity or j0.get(
        "exact_j0_proof_id"
    ) != expected_proof_id:
        failures.append("J0 proof identity/ID is inconsistent")
    if any(
        run.get(field) != expected
        for field, expected in (
            ("known_exact_j0_status", "FEASIBLE"),
            ("known_exact_j0_proof_id", expected_proof_id),
            ("known_exact_j0_structural_id", structural_id),
            ("known_exact_j0_build_id", run.get("build_id")),
            ("known_exact_j0_kernel_hash", enumeration.get("transition_kernel_sha256")),
            ("known_exact_j0_query_hash", query_id),
        )
    ):
        failures.append("run known-J0 identity binding is incomplete")

    forbidden_events = ("split", "witness", "counterexample", "fallback", "refinement")
    if any(
        any(marker in str(event.get("event", "")).lower() for marker in forbidden_events)
        for event in events
    ):
        failures.append("event log contains a forbidden CEGAR/fallback event")
    if any(metrics.get(field) != 0 for field in ("refinement_events", "accepted_splits", "fallback_invocations")):
        failures.append("metrics contain nonzero refinement/split/fallback counts")
    if metrics.get("status") != CERTIFIED or metrics.get("evidence") != "exact_sound" or not metrics.get(
        "included_in_gate"
    ):
        failures.append("metrics do not label the exact certified evidence correctly")
    if exact(metrics.get("raw_regret")) != 0 or exact(metrics.get("normalized_regret")) != 0:
        failures.append("exact quotient records nonzero regret")

    stored_documents = _logical_documents(bundle)
    stored_semantic_hash = canonical_sha256(
        {path: stored_documents[path] for path in sorted(stored_documents)}
    )
    if run.get("semantic_hash") != stored_semantic_hash or metrics.get(
        "semantic_hash"
    ) != stored_semantic_hash:
        failures.append("run/metrics semantic hash does not match deterministic documents")

    recomputed_hash = None
    if recompute and not failures:
        with tempfile.TemporaryDirectory(prefix="acfqp-exact-d4-verify-") as temporary:
            fresh_root = Path(temporary) / "exact_d4"
            fresh = run_exact_d4_baseline(fresh_root)
            recomputed_hash = fresh["semantic_hash"]
            fresh_documents = _logical_documents(fresh_root)
            for path in SEMANTIC_DOCUMENT_PATHS:
                if canonical_sha256(stored_documents[path]) != canonical_sha256(
                    fresh_documents[path]
                ):
                    failures.append(f"independent recomputation differs: {path}")
            if recomputed_hash != stored_semantic_hash:
                failures.append("independent exact-D4 semantic hash differs")

    return {
        "verified": not failures,
        "status": INVARIANT_VIOLATION if failures else run.get("status"),
        "recorded_status": run.get("status"),
        "included_in_positive_claim": not failures
        and certificate.get("included_in_positive_claim") is True,
        "semantic_hash": stored_semantic_hash,
        "recomputed_semantic_hash": recomputed_hash,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        type=Path,
        nargs="?",
        default=ROOT / "artifacts" / "exact_d4",
    )
    parser.add_argument(
        "--no-recompute",
        action="store_true",
        help="verify the stored exact evidence without rerunning the kernel",
    )
    arguments = parser.parse_args(argv)
    report = verify_exact_d4_bundle(
        arguments.bundle.resolve(), recompute=not arguments.no_recompute
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
