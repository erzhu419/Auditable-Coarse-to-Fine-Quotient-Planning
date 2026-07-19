#!/usr/bin/env python3
"""Verify Phase 0.5 artifacts and independently recompute semantic hashes."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.artifacts import (  # noqa: E402
    PHASE05_DOCUMENT_CONTRACTS,
    PHASE05_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    verify_artifact_bundle,
)
from acfqp.build_coverage import BuildCoverage  # noqa: E402
from acfqp.core import QuerySpec  # noqa: E402
from acfqp.domains.g2048 import G2048State, G2048Status  # noqa: E402
from acfqp.domains.matching_buffer import LMBState, LMBStatus  # noqa: E402
from acfqp.phase05 import _fixture, _source_tree_hash, run_fixture  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def exact(value: dict | int) -> Fraction:
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(value["numerator"], value["denominator"])


def _state_from_document(domain: str, value: dict) -> object:
    """Reconstruct a query state using the authoritative fixture state type."""

    if not isinstance(value, dict):
        raise ValueError("serialized query state must be an object")
    if domain == "g2048":
        return G2048State(
            tuple(int(rank) for rank in value["board"]),
            G2048Status(value["status"]),
        )
    if domain == "lmb":
        return LMBState(
            int(value["removed_mask"]),
            tuple(int(count) for count in value["buffer"]),
            LMBStatus(value["status"]),
        )
    raise ValueError(f"unknown authoritative Phase 0.5 fixture: {domain!r}")


def _query_from_document(domain: str, value: dict) -> QuerySpec:
    """Rebuild the immutable query contract from its serialized config."""

    initial = tuple(
        (exact(probability), _state_from_document(domain, state))
        for probability, state in value["initial_distribution"]
    )
    reward_weights = tuple(
        (str(name), exact(weight)) for name, weight in value["reward_weights"]
    )
    return QuerySpec(
        initial_distribution=initial,
        horizon=int(value["horizon"]),
        reward_weights=reward_weights,
        goal=str(value["goal"]),
        delta=exact(value["delta"]),
        normalizer=exact(value["normalizer_value"]),
        normalizer_proof_id=str(value["normalizer_proof_id"]),
    )


def _verify_policy(policy: dict | None, failures: list[str], location: str) -> None:
    if policy is None:
        return
    nodes = policy.get("decisions", [])
    node_ids = [node.get("node_id") for node in nodes]
    if len(node_ids) != len(set(node_ids)) or any(node_id is None for node_id in node_ids):
        failures.append(f"{location}: policy node IDs are missing or duplicated")
    if policy.get("selector_class") != "deterministic_finite_horizon_markov":
        failures.append(f"{location}: policy selector class is not deterministic Markov")
    decision_keys = [
        (node.get("remaining"), node.get("state_or_cell")) for node in nodes
    ]
    if len(decision_keys) != len(set(decision_keys)):
        failures.append(
            f"{location}: duplicate state/cell-horizon key permits history dependence"
        )
    for node in nodes:
        for child in node.get("child_node_ids", []):
            if child not in node_ids:
                failures.append(f"{location}: unresolved policy child {child!r}")
    expected_policy_id = object_id(
        {"level": policy.get("level"), "signature": policy.get("signature")},
        "policy",
    )
    if policy.get("policy_id") != expected_policy_id:
        failures.append(f"{location}: policy ID does not match its canonical signature")


def _verify_frontier(
    frontier: dict,
    *,
    query_id: str,
    failures: list[str],
    location: str,
) -> None:
    if frontier.get("query_id") != query_id:
        failures.append(f"{location}: query ID mismatch")
    points = frontier.get("frontier", [])
    selected = [point for point in points if point.get("selected")]
    if bool(frontier.get("feasible")) != (len(selected) == 1):
        failures.append(f"{location}: feasible/selected frontier accounting mismatch")
    selection = frontier.get("selection", {})
    if frontier.get("feasible"):
        if selection.get("status") != "SELECTED":
            failures.append(f"{location}: feasible frontier lacks SELECTED status")
        elif selection.get("selected_policy_id") != selected[0].get("policy", {}).get(
            "policy_id"
        ):
            failures.append(f"{location}: selected policy reference is unresolved")
    elif selection.get("status") != "INFEASIBLE_QUERY" or selection.get(
        "selected_policy_id"
    ) is not None:
        failures.append(f"{location}: infeasible frontier has inconsistent selection")
    for index, point in enumerate(points):
        _verify_policy(point.get("policy"), failures, f"{location}.frontier[{index}]")


def _verify_audit(
    audit: dict,
    *,
    query_id: str,
    delta: Fraction,
    envelope: dict,
    envelope_path: str,
    kernel_sha256: str,
    failures: list[str],
    location: str,
) -> None:
    if audit.get("query_id") != query_id:
        failures.append(f"{location}: query ID mismatch")
    if audit.get("U_all") != audit.get("unrestricted_reward_upper"):
        failures.append(f"{location}: U_all alias mismatch")
    if audit.get("L_pi") != audit.get("lifted_reward_lower"):
        failures.append(f"{location}: L_pi alias mismatch")
    if audit.get("U_F") != audit.get("lifted_failure_upper"):
        failures.append(f"{location}: U_F alias mismatch")
    policy = audit.get("policy")
    _verify_policy(policy, failures, f"{location}.policy")
    if not policy or audit.get("policy_id") != policy.get("policy_id"):
        failures.append(f"{location}: unresolved audit policy ID")

    entries = envelope.get("entries", [])
    entry_ids: set[str] = set()
    for index, entry in enumerate(entries):
        payload = dict(entry)
        entry_id = payload.pop("entry_id", None)
        if entry_id != object_id(payload, "envelope-entry"):
            failures.append(f"{envelope_path}.entries[{index}]: invalid entry ID")
        if entry_id in entry_ids:
            failures.append(f"{envelope_path}: duplicate entry ID")
        entry_ids.add(entry_id)

    dependencies = audit.get("proof_dependencies", [])
    dependency_ids = [dependency.get("dependency_id") for dependency in dependencies]
    dependency_set = set(dependency_ids)
    if len(dependency_ids) != len(dependency_set) or None in dependency_set:
        failures.append(f"{location}: proof dependency IDs are missing or duplicated")
    if audit.get("proof_dependency_count") != len(dependencies):
        failures.append(f"{location}: proof dependency count mismatch")
    for dependency in dependencies:
        for child in dependency.get("child_dependency_ids", []):
            if child not in dependency_set:
                failures.append(f"{location}: unresolved child proof dependency {child!r}")
        query_ref = dependency.get("query_ref", {})
        if query_ref.get("artifact") != "config/query.json" or query_ref.get(
            "query_id"
        ) != query_id:
            failures.append(f"{location}: invalid proof query reference")
        if dependency.get("kind") == "cell_policy_bound":
            envelope_ref = dependency.get("envelope_ref", {})
            if envelope_ref.get("artifact") != envelope_path or envelope_ref.get(
                "entry_id"
            ) not in entry_ids:
                failures.append(f"{location}: unresolved envelope proof reference")
            kernel_ref = dependency.get("kernel_ref", {})
            if kernel_ref.get("artifact") != "ground/enumeration.json" or kernel_ref.get(
                "transition_kernel_sha256"
            ) != kernel_sha256:
                failures.append(f"{location}: invalid exact-kernel proof reference")
    for dependency_id in audit.get("certificate_dependency_ids", []):
        if dependency_id not in dependency_set:
            failures.append(f"{location}: unresolved certificate dependency")
    bound_ids = {bound.get("bound_id") for bound in audit.get("reachable_bounds", [])}
    if not bound_ids <= dependency_set:
        failures.append(f"{location}: reachable bound lacks a proof dependency")

    pointwise = audit.get("pointwise", [])
    pointwise_pass = bool(pointwise) and all(point.get("certified") for point in pointwise)
    combined = bool(audit.get("aggregate_certified") and pointwise_pass)
    if audit.get("pointwise_all_certified") != pointwise_pass:
        failures.append(f"{location}: pointwise certification aggregate mismatch")
    if audit.get("certified") != combined:
        failures.append(f"{location}: combined certification flag mismatch")
    if audit.get("risk_tolerance") is not None and exact(audit["risk_tolerance"]) != delta:
        failures.append(f"{location}: audit risk tolerance differs from query delta")
    regrets = [exact(point["regret_upper"]) for point in pointwise]
    risks = [exact(point["lifted_failure_upper"]) for point in pointwise]
    if regrets and exact(audit["maximum_pointwise_regret_upper"]) != max(regrets):
        failures.append(f"{location}: maximum pointwise regret is inconsistent")
    if risks and exact(audit["maximum_pointwise_failure_upper"]) != max(risks):
        failures.append(f"{location}: maximum pointwise failure is inconsistent")
    for index, point in enumerate(pointwise):
        expected = (
            exact(point["regret_upper"]) <= Fraction(1, 20)
            and exact(point["lifted_failure_upper"]) <= delta
        )
        if point.get("certified") != expected:
            failures.append(f"{location}.pointwise[{index}]: certification inequality mismatch")


def verify_domain(bundle: Path, *, recompute: bool) -> dict:
    failures = verify_artifact_bundle(bundle)
    manifest = load(bundle / "manifest.json")
    records = {record["path"]: record for record in manifest.get("files", [])}
    declared = set(records)
    for path in PHASE05_REQUIRED_PATHS:
        if path not in declared:
            failures.append(f"required path absent from manifest: {path}")
        elif records[path].get("required") is not True:
            failures.append(f"required path is not marked required: {path}")
        else:
            expected_role, expected_schema = PHASE05_DOCUMENT_CONTRACTS[path]
            if records[path].get("role") != expected_role:
                failures.append(f"manifest role mismatch: {path}")
            if records[path].get("schema") != expected_schema:
                failures.append(f"manifest schema mismatch: {path}")

    run = load(bundle / "run.json")
    structural = load(bundle / "config" / "structural.json")
    query = load(bundle / "config" / "query.json")
    enumeration = load(bundle / "ground" / "enumeration.json")
    j0 = load(bundle / "ground" / "j0_frontier.json")
    partition_before = load(bundle / "rapm" / "partition_before.json")
    envelope_before = load(bundle / "rapm" / "envelope_before.json")
    witness = load(bundle / "refinement" / "witness.json")
    candidates = load(bundle / "refinement" / "candidates.json")
    pre = load(bundle / "audit" / "pre_refinement.json")
    split = load(bundle / "refinement" / "accepted_split.json")
    partition_after = load(bundle / "rapm" / "partition_after.json")
    envelope_after = load(bundle / "rapm" / "envelope_after.json")
    policy_graph = load(bundle / "result" / "policy_graph.json")
    result = load(bundle / "result" / "certificate_or_fallback.json")
    metrics = load(bundle / "metrics.json")

    if run.get("contract_version") != "0.4.0":
        failures.append("run contract version is not the frozen Phase 0.5 contract")
    if run.get("source_tree_sha256") != _source_tree_hash():
        failures.append("run source-tree hash is stale for the current workspace")
    for field in ("spec_hashes", "reference_manifest_hashes"):
        records_for_parent = run.get(field)
        if not isinstance(records_for_parent, dict) or not records_for_parent:
            failures.append(f"run {field} is missing or malformed")
            continue
        for relative, recorded_hash in records_for_parent.items():
            parent = ROOT / relative
            if not parent.is_file():
                failures.append(f"run {field} parent is missing: {relative}")
            elif sha256_file(parent) != recorded_hash:
                failures.append(f"run {field} parent hash is stale: {relative}")
    expected_spec_parents = {
        "DECISION_LEDGER.md",
        *(path.relative_to(ROOT).as_posix() for path in (ROOT / "specs").glob("*.md")),
    }
    if set(run.get("spec_hashes", {})) != expected_spec_parents:
        failures.append("run spec-hash parent inventory is incomplete")
    expected_reference_parents = {
        "reference/download_manifest.json",
        "reference/repo_clone_manifest.json",
    }
    if set(run.get("reference_manifest_hashes", {})) != expected_reference_parents:
        failures.append("run reference-manifest parent inventory is incomplete")

    query_payload = dict(query)
    query_id = query_payload.pop("query_id", None)
    if query_id != object_id(query_payload, "query") or run.get("query_id") != query_id:
        failures.append("run/query canonical ID mismatch")
    if query.get("normalizer") != query.get("normalizer_value"):
        failures.append("query normalizer/value aliases disagree")
    if not isinstance(query.get("normalizer_proof_id"), str) or not query.get(
        "normalizer_proof_id"
    ):
        failures.append("query normalizer proof ID is missing")
    structural_payload = dict(structural)
    fixture_id = structural_payload.pop("fixture_id", None)
    if fixture_id != object_id(structural_payload, "fixture") or run.get(
        "fixture_id"
    ) != fixture_id:
        failures.append("run/structural fixture ID mismatch")
    if run.get("structural_key") != structural.get("structural_key"):
        failures.append("run structural key does not match structural config")
    if run.get("benchmark_role") != structural.get("benchmark_role"):
        failures.append("run benchmark role does not match structural config")
    if "initial_law" in structural:
        failures.append("query-owned initial_law must not appear in structural config")
    if run.get("execution_profile") != "phase05_vertical_slice":
        failures.append("Phase 0.5 bundle has the wrong execution profile")
    canonical_override = (
        run.get("structural_key") == "g2048_select_canonical_2x2_v0"
    )
    if bool(run.get("phase05_test_override")) != canonical_override:
        failures.append("known-infeasible Phase 0.5 override has invalid scope")
    if canonical_override and run.get("claim_eligibility") != "infeasibility_only":
        failures.append("canonical G2048 fixture has invalid claim eligibility")
    seed_ledger = structural.get("seed_ledger")
    tape_ledger = structural.get("tape_ledger")
    if not isinstance(seed_ledger, dict):
        failures.append("structural seed ledger is missing or malformed")
        seed_ledger = {}
    if not isinstance(tape_ledger, dict):
        failures.append("structural tape ledger is missing or malformed")
        tape_ledger = {}
    if structural.get("seed_ledger_id") != object_id(seed_ledger, "seed-ledger"):
        failures.append("structural seed-ledger ID mismatch")
    if structural.get("tape_ledger_id") != object_id(tape_ledger, "tape-ledger"):
        failures.append("structural tape-ledger ID mismatch")
    run_seed = run.get("seed_ledger", {})
    run_tapes = run.get("random_tapes", {})
    if run_seed.get("seed_ledger_id") != structural.get("seed_ledger_id"):
        failures.append("run seed-ledger reference does not resolve")
    expected_seed_ids = {
        purpose: object_id(record, f"seed-{purpose}")
        for purpose, record in seed_ledger.items()
    }
    if run_seed.get("seed_ids") != expected_seed_ids:
        failures.append("run seed IDs do not match the serialized ledger")
    if run_tapes.get("tape_ledger_id") != structural.get("tape_ledger_id"):
        failures.append("run tape-ledger reference does not resolve")
    expected_tape_ids = [record["tape_id"] for record in tape_ledger.values()]
    if run_tapes.get("tape_ids") != expected_tape_ids:
        failures.append("run tape IDs do not match the serialized ledger")

    if enumeration.get("status") != "EXACT" or not enumeration.get("complete"):
        failures.append("finite-horizon enumeration is not complete/exact")
    if enumeration.get("evaluation_tier") != "EXACT_SOUND":
        failures.append("exact Phase 0.5 enumeration has the wrong evidence tier")
    states = enumeration.get("states", [])
    state_ids = [state.get("id") for state in states]
    state_set = set(state_ids)
    if len(state_ids) != len(state_set) or None in state_set:
        failures.append("enumeration state IDs are missing or duplicated")
    for state in states:
        if state.get("id") != object_id(state.get("state"), "state"):
            failures.append(f"invalid canonical state ID: {state.get('id')!r}")
    transitions = enumeration.get("transitions", [])
    transition_ids: set[str] = set()
    derived_failure_set: set[str] = set()
    for index, transition in enumerate(transitions):
        payload = dict(transition)
        transition_id = payload.pop("transition_id", None)
        if transition_id != object_id(payload, "transition"):
            failures.append(f"enumeration transition {index} has an invalid ID")
        if transition_id in transition_ids:
            failures.append("enumeration transition IDs are duplicated")
        transition_ids.add(transition_id)
        if transition.get("state") not in state_set:
            failures.append("enumeration transition references an unknown source state")
        for outcome in transition.get("outcomes", []):
            if outcome.get("next_state") not in state_set:
                failures.append("enumeration transition references an unknown successor")
            if outcome.get("entered_failure"):
                derived_failure_set.add(outcome.get("next_state"))
    expected_kernel_hash = canonical_sha256(
        {"horizon": enumeration.get("horizon"), "transitions": transitions}
    )
    kernel_hash = enumeration.get("transition_kernel_sha256")
    if kernel_hash != expected_kernel_hash:
        failures.append("enumeration transition-kernel hash mismatch")
    coverage = run.get("build_coverage", {})
    authoritative_query = None
    recomputed_coverage = None
    try:
        authoritative_fixture = _fixture(str(run.get("domain")))
        authoritative_query = _query_from_document(str(run.get("domain")), query)
        recomputed_coverage = BuildCoverage.from_query(
            authoritative_fixture.kernel,
            authoritative_query,
        )
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        failures.append(f"cannot recompute authoritative build coverage: {error}")
    expected_coverage = (
        recomputed_coverage.descriptor()
        if recomputed_coverage is not None
        else {
            "mode": "query_support_transition_closure",
            "initial_support_sha256": canonical_sha256(
                query.get("initial_distribution")
            ),
            "covered_state_count": metrics.get(
                "rapm_transition_closure_states"
            ),
            "reuse_outside_coverage_forbidden": True,
        }
    )
    if coverage != expected_coverage:
        failures.append("run build-coverage restriction is inconsistent")
    serialized_coverage_ids = enumeration.get("covered_state_ids")
    if not isinstance(serialized_coverage_ids, list):
        failures.append("enumeration covered_state_ids are missing or malformed")
        serialized_coverage_ids = []
    if serialized_coverage_ids != sorted(serialized_coverage_ids) or len(
        serialized_coverage_ids
    ) != len(set(serialized_coverage_ids)):
        failures.append("enumeration covered_state_ids are not canonical and unique")
    if enumeration.get("covered_state_count") != len(serialized_coverage_ids):
        failures.append("enumeration covered-state count is not parseable from IDs")
    if metrics.get("rapm_transition_closure_states") != len(
        serialized_coverage_ids
    ):
        failures.append("metrics coverage count disagrees with serialized state IDs")
    if recomputed_coverage is not None:
        if serialized_coverage_ids != list(recomputed_coverage.covered_state_ids):
            failures.append(
                "serialized build coverage differs from authoritative transition closure"
            )
        if enumeration.get(
            "covered_state_count"
        ) != recomputed_coverage.covered_state_count:
            failures.append(
                "serialized build coverage count differs from authoritative closure"
            )
    expected_build_id = object_id(
        {
            "structural_id": fixture_id,
            "coverage": expected_coverage,
            "source": run.get("source_tree_sha256"),
        },
        "build",
    )
    if run.get("build_id") != expected_build_id:
        failures.append("run build ID does not bind structural/source/coverage identity")
    failure_set = set(enumeration.get("failure_set", []))
    success_set = set(enumeration.get("success_set", []))
    derived_success_set = {
        state["id"] for state in states if state.get("terminal")
    } - derived_failure_set
    if failure_set != derived_failure_set or success_set != derived_success_set:
        failures.append("enumeration failure/success set mismatch")
    if failure_set & success_set or not enumeration.get("failure_success_sets_disjoint"):
        failures.append("enumeration failure and success sets are not disjoint")

    _verify_frontier(
        j0,
        query_id=query_id,
        failures=failures,
        location="ground/j0_frontier.json",
    )
    expected_j0_status = "FEASIBLE" if j0.get("feasible") else "INFEASIBLE"
    proof_identity = {
        "structural_id": fixture_id,
        "build_id": run.get("build_id"),
        "kernel_hash": kernel_hash,
        "query_hash": query_id,
    }
    expected_j0_proof_id = object_id(
        {
            "identity": proof_identity,
            "status": expected_j0_status,
            "frontier": j0.get("frontier"),
        },
        "j0-proof",
    )
    if j0.get("known_exact_j0_status") != expected_j0_status:
        failures.append("J0 exact status disagrees with its frontier")
    if j0.get("proof_identity") != proof_identity:
        failures.append("J0 proof does not bind structural/build/kernel/query identity")
    if j0.get("exact_j0_proof_id") != expected_j0_proof_id:
        failures.append("J0 proof ID is inconsistent")
    if (
        run.get("known_exact_j0_status") != expected_j0_status
        or run.get("known_exact_j0_proof_id") != expected_j0_proof_id
        or run.get("known_exact_j0_structural_id") != fixture_id
        or run.get("known_exact_j0_build_id") != run.get("build_id")
        or run.get("known_exact_j0_kernel_hash") != kernel_hash
        or run.get("known_exact_j0_query_hash") != query_id
    ):
        failures.append("run known-J0 provenance is incomplete or mismatched")
    j0_accounting = j0.get("oracle_accounting", {})
    if (
        j0_accounting.get("ordinal") != 1
        or j0_accounting.get("composed_candidate_count")
        != j0.get("composed_candidate_count")
        or not j0_accounting.get("same_query")
    ):
        failures.append("J0 oracle accounting is incomplete or inconsistent")

    if pre.get("certified") is not False:
        failures.append("coarse proposal was not explicitly uncertified")
    delta = exact(query["delta"])
    _verify_audit(
        pre,
        query_id=query_id,
        delta=delta,
        envelope=envelope_before,
        envelope_path="rapm/envelope_before.json",
        kernel_sha256=kernel_hash,
        failures=failures,
        location="audit/pre_refinement.json",
    )
    post = result.get("abstract_audit", {})
    _verify_audit(
        post,
        query_id=query_id,
        delta=delta,
        envelope=envelope_after,
        envelope_path="rapm/envelope_after.json",
        kernel_sha256=kernel_hash,
        failures=failures,
        location="result/certificate_or_fallback.json.abstract_audit",
    )

    witness_payload = dict(witness)
    witness_id = witness_payload.pop("witness_id", None)
    if witness_id != object_id(witness_payload, "witness"):
        failures.append("witness ID does not match its canonical payload")
    if witness.get("left_state") not in {
        member for cell in partition_before.get("cells", []) for member in cell.get("members", [])
    } or witness.get("right_state") not in {
        member for cell in partition_before.get("cells", []) for member in cell.get("members", [])
    }:
        failures.append("witness state reference is absent from the pre-split partition")

    candidate_records = candidates.get("candidates", [])
    ranks = [candidate.get("deterministic_rank") for candidate in candidate_records]
    if ranks != list(range(1, len(candidate_records) + 1)):
        failures.append("candidate deterministic ranks are not contiguous")
    accepted = [candidate for candidate in candidate_records if candidate.get("status") == "ACCEPTED"]
    if len(accepted) != 1:
        failures.append("Phase 0.5 candidates must contain exactly one accepted candidate")
    for candidate in candidate_records:
        if candidate.get("witness_id") != witness_id:
            failures.append("candidate witness reference is unresolved")
        rejected = candidate.get("status") != "ACCEPTED"
        if rejected != bool(candidate.get("rejection_reasons")):
            failures.append("candidate rejection status/reasons mismatch")
    if split.get("status") != "SPLIT_ACCEPTED":
        failures.append("mandatory split was not accepted")
    elif accepted:
        if split.get("accepted_candidate_id") != accepted[0].get("candidate_id"):
            failures.append("accepted split candidate reference is unresolved")
        if split.get("accepted_rank") != accepted[0].get("deterministic_rank"):
            failures.append("accepted split rank mismatch")
        if split.get("witness_id") != witness_id or not split.get("witness_separated"):
            failures.append("accepted split does not resolve a separating witness")
    if split.get("partition_before_signature_sha256") != canonical_sha256(
        partition_before.get("signature")
    ) or split.get("partition_after_signature_sha256") != canonical_sha256(
        partition_after.get("signature")
    ):
        failures.append("accepted split partition signature hash mismatch")
    after_cells = {
        cell.get("cell_id"): sorted(cell.get("members", []))
        for cell in partition_after.get("cells", [])
    }
    predicate_id = split.get("predicate", {}).get("predicate_id")
    for child in split.get("children", []):
        members = sorted(child.get("member_state_ids", []))
        if after_cells.get(child.get("cell_id")) != members:
            failures.append("split child membership does not match partition_after")
        if child.get("member_signature_sha256") != canonical_sha256(members):
            failures.append("split child member signature hash mismatch")
        path = child.get("path_predicates", [])
        if not path or path[-1] != predicate_id:
            failures.append("split child path does not end in the accepted predicate")
        if child.get("path_signature_sha256") != canonical_sha256(path):
            failures.append("split child path signature hash mismatch")
    if metrics.get("accepted_splits") != 1:
        failures.append("Phase 0.5 must record exactly one accepted split")
    if metrics.get("quotient_leaves_after") != metrics.get("quotient_leaves_before") + 1:
        failures.append("accepted split did not increase leaves by exactly one")

    status = run.get("status")
    if status != result.get("status"):
        failures.append("run/result status mismatch")
    if result.get("benchmark_role") != run.get("benchmark_role") or result.get(
        "claim_eligibility"
    ) != run.get("claim_eligibility"):
        failures.append("result claim context disagrees with run metadata")
    if run.get("claim_eligibility") == "infeasibility_only" and status == "CERTIFIED":
        failures.append("infeasibility-only fixture cannot support a positive certificate")
    if result.get("normalizer_value") != query.get("normalizer_value") or result.get(
        "normalizer_proof_id"
    ) != query.get("normalizer_proof_id"):
        failures.append("result normalizer provenance disagrees with query")
    normalized_regret = result.get("normalized_regret_upper")
    raw_regret = result.get("raw_regret_upper")
    if normalized_regret is not None:
        if raw_regret is None or exact(raw_regret) != exact(normalized_regret) * exact(
            query["normalizer_value"]
        ):
            failures.append("raw/normalized regret accounting is inconsistent")
    if result.get("query_id") != query_id or policy_graph.get("query_id") != query_id:
        failures.append("terminal artifact query reference mismatch")
    _verify_policy(
        policy_graph.get("abstract_proposal_after_split"),
        failures,
        "result/policy_graph.json.abstract_proposal_after_split",
    )
    _verify_policy(
        policy_graph.get("returned_policy"),
        failures,
        "result/policy_graph.json.returned_policy",
    )
    audit = post
    if status == "CERTIFIED":
        if not audit.get("certified"):
            failures.append("CERTIFIED result lacks aggregate+pointwise certification")
        if not audit.get("pointwise_all_certified"):
            failures.append("CERTIFIED result fails an initial-support point")
        if exact(audit["regret_upper"]) > Fraction(1, 20):
            failures.append("certified regret exceeds tolerance")
        if exact(audit["lifted_failure_upper"]) > delta:
            failures.append("certified failure bound exceeds delta")
    elif status in {"GROUND_FALLBACK", "INFEASIBLE_QUERY"}:
        location = result.get("fallback_location") or {}
        if not location.get("charged") or not location.get("same_query"):
            failures.append("fallback is not charged against the identical query")
        if result.get("fallback") is None:
            failures.append("fallback frontier is missing")
        else:
            fallback = result["fallback"]
            _verify_frontier(
                fallback,
                query_id=query_id,
                failures=failures,
                location="result/certificate_or_fallback.json.fallback",
            )
            fallback_accounting = fallback.get("oracle_accounting", {})
            if (
                fallback_accounting.get("invocation_id")
                != location.get("oracle_invocation_id")
                or fallback_accounting.get("ordinal") != 2
                or not fallback_accounting.get("same_query")
                or fallback_accounting.get("composed_candidate_count")
                != location.get("candidate_work")
            ):
                failures.append("fallback oracle accounting is inconsistent")
        if status == "GROUND_FALLBACK" and not result.get("ground_query_feasible"):
            failures.append("GROUND_FALLBACK has no feasible constrained ground policy")
        if status == "INFEASIBLE_QUERY" and result.get("ground_query_feasible"):
            failures.append("INFEASIBLE_QUERY contradicts the ground frontier")
    else:
        failures.append(f"unexpected terminal status: {status!r}")

    oracle_accounting = metrics.get("oracle_accounting", {})
    invocations = oracle_accounting.get("invocations", [])
    if metrics.get("exact_oracle_invocations") != len(invocations) or oracle_accounting.get(
        "recorded_invocation_total"
    ) != len(invocations):
        failures.append("end-to-end oracle invocation accounting mismatch")
    if len({item.get("invocation_id") for item in invocations}) != len(invocations):
        failures.append("oracle invocation IDs are duplicated")
    candidate_total = sum(item.get("composed_candidate_count", 0) for item in invocations)
    if oracle_accounting.get("component_candidate_work_total") != candidate_total:
        failures.append("oracle candidate-work total does not reconcile")
    gate = metrics.get("gate", {})
    if gate.get("included_in_gate"):
        if metrics.get("evidence") != "exact_sound":
            failures.append("Gate includes non-exact evidence")
        if enumeration.get("status") != "EXACT" or enumeration.get(
            "evaluation_tier"
        ) != "EXACT_SOUND":
            failures.append("Gate includes a capped/stress-only enumeration")
        if not all(gate.get("checks", {}).values()):
            failures.append("Gate includes a run with a failed eligibility check")
        for metric in metrics.get("metric_records", []):
            if metric.get("included_in_gate") and metric.get("evidence_label") != "exact_sound":
                failures.append("Gate includes a nominal/diagnostic metric")
    elif gate.get("exclusion_reason") is None:
        failures.append("Gate-excluded result lacks an exclusion reason")

    recomputed_hash = None
    if recompute and not failures:
        with tempfile.TemporaryDirectory(prefix="acfqp-phase05-verify-") as temporary:
            recomputed = run_fixture(
                run["domain"],
                Path(temporary) / run["domain"],
                query_override=authoritative_query,
            )
            recomputed_hash = recomputed["semantic_hash"]
            if recomputed_hash != run.get("semantic_hash"):
                failures.append("independent semantic-hash recomputation differs")

    return {
        "domain": run.get("domain"),
        "status": status,
        "semantic_hash": run.get("semantic_hash"),
        "recomputed_semantic_hash": recomputed_hash,
        "failures": failures,
        "verified": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle_root",
        type=Path,
        nargs="?",
        default=ROOT / "artifacts" / "phase05",
    )
    parser.add_argument(
        "--no-recompute",
        action="store_true",
        help="verify hashes/Gate logic without executing the kernels again",
    )
    args = parser.parse_args(argv)
    reports = [
        verify_domain(args.bundle_root / domain, recompute=not args.no_recompute)
        for domain in ("g2048", "lmb")
    ]
    result = {"verified": all(report["verified"] for report in reports), "runs": reports}
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
