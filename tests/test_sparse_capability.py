from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import itertools
import json

import pytest

from acfqp.general_local_solver import (
    ALGORITHM_ID,
    CERTIFIED,
    POLICY_CLASS,
    REQUEST_SCHEMA,
    SELECTION_RULE,
    solve_general_local_recovery,
)
from acfqp.local_recovery import (
    LocalRecoveryAuthorization,
    build_failed_proof_graph,
    build_redacted_boundary_view,
    materialize_authorized_slice,
    redact_authorized_slice_for_worker,
)
from acfqp.phase3c import (
    _select_recovery_proposal,
    construct_phase3c_world,
)
from acfqp.planning import FiniteHorizonPolicy, audit_abstract_policy
from acfqp.portable_planner import solve_portable_pareto
from acfqp.sparse_capability import (
    CAPABILITY_SCHEMA,
    SPARSE_SLICE_SCHEMA,
    capability_exit_bounds,
    compile_sparse_capability,
    compile_sparse_recovery_inputs,
    evaluate_sparse_capability,
    parse_sparse_capability,
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _logical_id(prefix: str, value: object) -> str:
    return f"{prefix}:{hashlib.sha256(_canonical_json(value).encode()).hexdigest()}"


def _object_id(prefix: str, value: object) -> str:
    return f"{prefix}-{hashlib.sha256(_canonical_json(value).encode()).hexdigest()[:16]}"


def _sha(value: object) -> str:
    return hashlib.sha256((_canonical_json(value) + "\n").encode()).hexdigest()


def _fraction(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _q(numerator: int, denominator: int = 1) -> dict[str, int]:
    value = Fraction(numerator, denominator)
    return {"numerator": value.numerator, "denominator": value.denominator}


@pytest.fixture(scope="module")
def sparse_case() -> dict:
    world = construct_phase3c_world()
    query = world.queries[1].query
    result = solve_portable_pareto(
        world.portable.model,
        world.portable.query_from_spec(query),
    )
    proposal, _ = _select_recovery_proposal(result)
    policy = FiniteHorizonPolicy.from_mapping(
        world.portable.decode_policy(proposal.policy)
    )
    audit = audit_abstract_policy(
        world.kernel,
        query,
        world.models.envelope,
        policy,
    )
    graph = build_failed_proof_graph(
        world.kernel,
        query,
        world.models.envelope,
        policy,
        audit,
    )
    frontier = graph.frontier()
    authorization = LocalRecoveryAuthorization.for_frontier(
        world.kernel,
        world.models.envelope,
        frontier,
        graph,
    )
    materialized = materialize_authorized_slice(
        world.kernel,
        query,
        world.models.envelope,
        frontier,
        authorization,
        graph=graph,
    )
    ground_slice = redact_authorized_slice_for_worker(materialized)
    boundary = build_redacted_boundary_view(
        query,
        world.models.envelope,
        policy,
        graph,
        unrestricted_reward_upper=audit.unrestricted_reward_upper,
        regret_tolerance=audit.regret_tolerance,
    )

    # The slack-aware causal cone retains only the eight-member common cell.
    causal_cell = next(
        cell for cell in ground_slice["cells"] if len(cell["members"]) == 8
    )
    causal_port = causal_cell["node_id"]
    member_actions = []
    for member in causal_cell["members"]:
        member_actions.append(
            tuple(
                (
                    _fraction(action["immediate_reward"]),
                    _fraction(action["failure_probability"]),
                )
                for action in member["actions"]
            )
        )
    admissible_pairs = {
        (
            min(item[0] for item in assignment),
            max(item[1] for item in assignment),
        )
        for assignment in itertools.product(*member_actions)
    }
    compilation = compile_sparse_capability(
        boundary,
        frontier_input_port_ids=(causal_port,),
        admissible_input_pairs={causal_port: admissible_pairs},
    )
    return {
        "world": world,
        "query": query,
        "audit": audit,
        "graph": graph,
        "frontier": frontier,
        "ground_slice": ground_slice,
        "boundary": boundary,
        "causal_port": causal_port,
        "admissible_pairs": admissible_pairs,
        "compilation": compilation,
    }


def _causal_v1_slice(case: dict) -> tuple[dict, str]:
    causal_port = case["causal_port"]
    target_frontier_id = _object_id(
        "failed-proof-frontier",
        {
            "graph_id": case["boundary"]["graph_id"],
            "node_ids": (causal_port,),
        },
    )
    source = case["ground_slice"]
    payload = {
        "schema": source["schema"],
        "frontier_id": target_frontier_id,
        "authorization_id": _object_id(
            "local-recovery-authorization",
            {"target_frontier_id": target_frontier_id},
        ),
        "cells": [
            copy.deepcopy(
                next(cell for cell in source["cells"] if cell["node_id"] == causal_port)
            )
        ],
    }
    payload["slice_id"] = _object_id("authorized-ground-slice", payload)
    return payload, target_frontier_id


def _synthetic_exit_documents() -> tuple[dict, dict, str, str, str]:
    input_port = "proof-node-1111111111111111"
    exit_port = "proof-node-2222222222222222"
    graph_id = "failed-proof-graph-3333333333333333"
    source_frontier_id = "failed-proof-frontier-4444444444444444"
    target_frontier_id = _object_id(
        "failed-proof-frontier",
        {"graph_id": graph_id, "node_ids": (input_port,)},
    )
    boundary = {
        "schema": "acfqp.redacted_boundary_view.v1",
        "graph_id": graph_id,
        "frontier_id": source_frontier_id,
        "delta": _q(1, 2),
        "unrestricted_reward_upper": _q(1),
        "regret_tolerance": _q(1),
        "roots": [{"node_id": input_port, "probability": _q(1)}],
        "nodes": [
            {
                "node_id": input_port,
                "cell": "synthetic-h2",
                "remaining": 2,
                "selected_action": "selected-h2",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-5555555555555555",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [
                            {"node_id": exit_port, "probability": _q(1)}
                        ],
                    }
                ],
            },
            {
                "node_id": exit_port,
                "cell": "synthetic-h1-exit",
                "remaining": 1,
                "selected_action": "selected-h1",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-6666666666666666",
                        "immediate_reward": _q(1, 2),
                        "failure_probability": _q(1, 4),
                        "successors": [],
                    }
                ],
            },
        ],
    }
    boundary["boundary_view_id"] = _object_id("redacted-boundary-view", boundary)
    v1_slice = {
        "schema": "acfqp.authorized_ground_slice.v1",
        "frontier_id": target_frontier_id,
        "authorization_id": "local-recovery-authorization-7777777777777777",
        "cells": [
            {
                "node_id": input_port,
                "cell": "synthetic-h2",
                "remaining": 2,
                "members": [
                    {
                        "state_id": "state-8888888888888888",
                        "actions": [
                            {
                                "action_id": "action-9999999999999999",
                                "immediate_reward": _q(1, 10),
                                "failure_probability": _q(0),
                                "termination_probability": _q(1, 2),
                                "successors": [
                                    {"node_id": exit_port, "probability": _q(1, 2)}
                                ],
                            },
                            {
                                "action_id": "action-aaaaaaaaaaaaaaaa",
                                "immediate_reward": _q(1, 5),
                                "failure_probability": _q(2, 5),
                                "termination_probability": _q(1),
                                "successors": [],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    v1_slice["slice_id"] = _object_id("authorized-ground-slice", v1_slice)
    return boundary, v1_slice, target_frontier_id, input_port, exit_port


def _conditional_two_port_boundary() -> tuple[dict, str, str]:
    """Return a root envelope ``min(left, right)`` with zero defaults.

    Each port is irrelevant while the other port remains at its default zero,
    but both are necessary over the complete admissible two-port domain.
    """

    left = "proof-node-1111111111111111"
    right = "proof-node-2222222222222222"
    root = "proof-node-3333333333333333"
    boundary = {
        "schema": "acfqp.redacted_boundary_view.v1",
        "graph_id": "failed-proof-graph-4444444444444444",
        "frontier_id": "failed-proof-frontier-5555555555555555",
        "delta": _q(1),
        "unrestricted_reward_upper": _q(0),
        "regret_tolerance": _q(0),
        "roots": [{"node_id": root, "probability": _q(1)}],
        "nodes": [
            {
                "node_id": root,
                "cell": "conditional-root",
                "remaining": 2,
                "selected_action": "selected-root",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-1111111111111111",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [{"node_id": left, "probability": _q(1)}],
                    },
                    {
                        "realization_id": "redacted-realization-2222222222222222",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [{"node_id": right, "probability": _q(1)}],
                    },
                ],
            },
            {
                "node_id": left,
                "cell": "conditional-left",
                "remaining": 1,
                "selected_action": "selected-left",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-3333333333333333",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [],
                    }
                ],
            },
            {
                "node_id": right,
                "cell": "conditional-right",
                "remaining": 1,
                "selected_action": "selected-right",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-4444444444444444",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [],
                    }
                ],
            },
        ],
    }
    boundary["boundary_view_id"] = _object_id("redacted-boundary-view", boundary)
    return boundary, left, right


def test_safe_chain_compiles_to_one_cell_port_and_two_sparse_root_forms(
    sparse_case: dict,
) -> None:
    capability = sparse_case["compilation"].capability
    evidence = sparse_case["compilation"].evidence
    port = sparse_case["causal_port"]

    assert capability.to_dict()["schema"] == CAPABILITY_SCHEMA
    assert capability.input_port_ids == (port,)
    assert capability.exit_ports == ()
    assert len(capability.root_reward_forms) == 1
    assert len(capability.root_failure_forms) == 1
    assert capability.reward_floor == Fraction(-1, 320)
    assert capability.failure_ceiling == Fraction(1, 20)

    input_port = capability.input_ports[0]
    assert input_port == (port, Fraction(1, 32), Fraction(101, 200))
    reward_form = capability.root_reward_forms[0]
    failure_form = capability.root_failure_forms[0]
    # The authorized slice has one fixed reward at this horizon, so the
    # reward channel is constant-folded.  The rare cell remains trusted-side
    # and contributes 199/20000 to the risk constant.
    assert reward_form.constant == Fraction(3, 64)
    assert reward_form.terms == ()
    assert failure_form.constant == Fraction(199, 20000)
    assert failure_form.terms == ((port, Fraction(99, 100)),)

    assert evidence["source_node_count"] == 4
    assert evidence["source_abstract_realization_row_count"] == 20
    assert evidence["retained_input_port_ids"] == [port]
    assert evidence["retained_reward_form_count"] == 1
    assert evidence["retained_failure_form_count"] == 1
    assert len(evidence["form_necessity_witnesses"]) == 2
    assert len(evidence["input_port_necessity_witnesses"]) == 1
    assert evidence["exit_port_necessity_witnesses"] == []
    assert evidence["redaction"]["observed_forbidden_worker_keys"] == []

    # The worker capability is materially smaller than the v1 selected-policy
    # realization graph.  Exact bytes are implementation metadata; semantic
    # counts and field allowlists are the normative surface.
    boundary_bytes = len(_canonical_json(sparse_case["boundary"]).encode())
    capability_bytes = len(_canonical_json(capability.to_dict()).encode())
    assert boundary_bytes == 6548
    assert capability_bytes < 1500
    assert capability_bytes * 4 < boundary_bytes


def test_sparse_capability_reproduces_pre_and_post_value_risk_bounds(
    sparse_case: dict,
) -> None:
    capability = sparse_case["compilation"].capability
    port = sparse_case["causal_port"]

    before = evaluate_sparse_capability(capability)
    assert before.root_reward_lower == Fraction(3, 64)
    assert before.root_failure_upper == Fraction(5099, 10000)
    assert before.certified_value
    assert not before.certified_safe
    assert not before.certified

    after = evaluate_sparse_capability(
        capability,
        {port: (Fraction(1, 32), Fraction(1, 100))},
    )
    assert after.root_reward_lower == Fraction(3, 64)
    assert after.root_failure_upper == Fraction(397, 20000)
    assert after.certified_value
    assert after.certified_safe
    assert after.certified


def test_compilation_evidence_is_extensionally_sufficient_and_minimal(
    sparse_case: dict,
) -> None:
    evidence = sparse_case["compilation"].evidence
    assert all(
        row["source_value"] == row["capability_value"]
        for row in evidence["reward_equivalence_cases"]
    )
    assert all(
        row["source_value"] == row["capability_value"]
        for row in evidence["failure_equivalence_cases"]
    )
    assert all(
        row["deletion_changes_output"]
        for row in evidence["form_necessity_witnesses"]
    )
    witness = evidence["input_port_necessity_witnesses"][0]
    assert witness["left_root"] != witness["right_root"]

    payload = dict(evidence)
    evidence_id = payload.pop("evidence_id")
    assert evidence_id == _logical_id("sparse-capability-evidence", payload)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda doc: doc.__setitem__("graph_id", "forbidden"), "field set mismatch"),
        (
            lambda doc: doc["input_ports"][0].__setitem__(
                "state_id", "state:0000000000000000"
            ),
            "field set mismatch",
        ),
        (
            lambda doc: doc["root_reward_forms"][0].__setitem__(
                "abstract_realizations", []
            ),
            "field set mismatch",
        ),
        (
            lambda doc: doc["root_failure_forms"][0]["terms"][0].__setitem__(
                "coefficient", {"numerator": 0, "denominator": 1}
            ),
            "positive coefficients",
        ),
    ),
)
def test_worker_parser_rejects_extra_fields_and_redaction_attacks(
    sparse_case: dict,
    mutation,
    message: str,
) -> None:
    document = copy.deepcopy(sparse_case["compilation"].capability.to_dict())
    mutation(document)
    with pytest.raises(ValueError, match=message):
        parse_sparse_capability(document)


def test_worker_parser_rejects_state_level_port_and_unknown_assignment(
    sparse_case: dict,
) -> None:
    document = copy.deepcopy(sparse_case["compilation"].capability.to_dict())
    document["input_ports"][0]["port_id"] = "state:0123456789abcdef"
    payload = dict(document)
    payload.pop("capability_id")
    document["capability_id"] = _logical_id(
        "sparse-robust-affine-capability", payload
    )
    with pytest.raises(ValueError, match="abstract proof-node cell"):
        parse_sparse_capability(document)

    with pytest.raises(ValueError, match="unknown ports"):
        evaluate_sparse_capability(
            sparse_case["compilation"].capability,
            {"proof-node-0000000000000000": (Fraction(0), Fraction(0))},
        )


def test_content_resigning_cannot_replace_trusted_recompilation(
    sparse_case: dict,
) -> None:
    """A coordinated forger can rehash bytes but not change authority truth."""

    authoritative = sparse_case["compilation"].capability.to_dict()
    forged = copy.deepcopy(authoritative)
    form = forged["root_failure_forms"][0]
    form["terms"][0]["coefficient"] = {"numerator": 1, "denominator": 2}
    form_payload = {"constant": form["constant"], "terms": form["terms"]}
    form["form_id"] = _logical_id("sparse-form", form_payload)
    forged_payload = dict(forged)
    forged_payload.pop("capability_id")
    forged["capability_id"] = _logical_id(
        "sparse-robust-affine-capability", forged_payload
    )

    # Integrity/content-address validation alone succeeds.
    parsed_forgery = parse_sparse_capability(forged)
    assert parsed_forgery.to_dict() == forged
    # Independent trusted compilation is the semantic authority.
    assert forged != authoritative
    assert evaluate_sparse_capability(parsed_forgery).root_failure_upper != Fraction(
        5099, 10000
    )


def test_trusted_recovery_input_compiler_builds_one_cell_worker_handoff(
    sparse_case: dict,
) -> None:
    v1_slice, target_frontier_id = _causal_v1_slice(sparse_case)
    result = compile_sparse_recovery_inputs(
        sparse_case["boundary"],
        v1_slice,
        target_frontier_id=target_frontier_id,
    )
    capability = result.compilation.capability
    evidence = result.compilation.evidence
    sparse_slice = result.sparse_slice

    assert capability.frontier_id == target_frontier_id
    assert capability.frontier_id != sparse_case["boundary"]["frontier_id"]
    assert evidence["source_frontier_id"] == sparse_case["boundary"]["frontier_id"]
    assert evidence["target_frontier_id"] == target_frontier_id
    assert sparse_slice["schema"] == SPARSE_SLICE_SCHEMA
    assert sparse_slice["frontier_id"] == target_frontier_id
    assert [cell["input_port_id"] for cell in sparse_slice["cells"]] == [
        sparse_case["causal_port"]
    ]
    assert all(
        action["exits"] == []
        for cell in sparse_slice["cells"]
        for member in cell["members"]
        for action in member["actions"]
    )
    construction = evidence["recovery_input_compilation"]
    assert construction["status"] == "COMPLETE"
    assert construction["enumeration_complete"]
    assert construction["counts"]["slice_cells"] == 1
    assert construction["counts"]["cell_policy_assignments"] == 256
    assert construction["counts"]["distinct_scalar_exit_ports"] == 0
    assert evidence["enumeration"]["status"] == "COMPLETE"

    payload = dict(evidence)
    evidence_id = payload.pop("evidence_id")
    assert evidence_id == _logical_id("sparse-capability-evidence", payload)


def test_compiled_safe_chain_handoff_runs_in_joint_solver(sparse_case: dict) -> None:
    v1_slice, target_frontier_id = _causal_v1_slice(sparse_case)
    inputs = compile_sparse_recovery_inputs(
        sparse_case["boundary"],
        v1_slice,
        target_frontier_id=target_frontier_id,
    )
    capability = inputs.compilation.capability.to_dict()
    sparse_slice = inputs.sparse_slice
    request_payload = {
        "schema": REQUEST_SCHEMA,
        "occurrence_id": "occurrence-0123456789abcdef",
        "frontier_id": target_frontier_id,
        "capability_id": capability["capability_id"],
        "slice_id": sparse_slice["slice_id"],
        "capability_sha256": _sha(capability),
        "slice_sha256": _sha(sparse_slice),
        "algorithm_id": ALGORITHM_ID,
        "selection_rule": SELECTION_RULE,
        "policy_class": POLICY_CLASS,
        "search_limits": {
            "max_subset_evaluations": 10,
            "max_policy_assignments": 1_000,
            "max_root_frontier_points": 1_000,
            "max_dominance_comparisons": 100_000,
            "max_affine_term_evaluations": 100_000,
            "max_rational_bits": 1_024,
        },
    }
    request = {
        **request_payload,
        "request_id": _object_id("general-local-request", request_payload),
    }
    result = solve_general_local_recovery(capability, sparse_slice, request)
    assert result.status == CERTIFIED
    assert result.localized_node_ids == (sparse_case["causal_port"],)
    assert result.root_reward_lower == Fraction(3, 64)
    assert result.root_failure_upper == Fraction(397, 20000)
    assert result.search_complete
    assert result.minimality_proven


def test_recovery_input_compiler_rejects_frontier_mismatch_and_assignment_cap(
    sparse_case: dict,
) -> None:
    v1_slice, target_frontier_id = _causal_v1_slice(sparse_case)
    with pytest.raises(ValueError, match="slice and target_frontier_id mismatch"):
        compile_sparse_recovery_inputs(
            sparse_case["boundary"],
            v1_slice,
            target_frontier_id=sparse_case["boundary"]["frontier_id"],
        )
    with pytest.raises(ValueError, match="cell-policy assignment cap exceeded"):
        compile_sparse_recovery_inputs(
            sparse_case["boundary"],
            v1_slice,
            target_frontier_id=target_frontier_id,
            max_cell_policy_assignments=255,
        )


def test_horizon_two_successor_becomes_a_scalar_exit_port() -> None:
    boundary, v1_slice, target_frontier_id, input_port, exit_port = (
        _synthetic_exit_documents()
    )
    result = compile_sparse_recovery_inputs(
        boundary,
        v1_slice,
        target_frontier_id=target_frontier_id,
    )
    capability = result.compilation.capability
    assert capability.input_port_ids == (input_port,)
    assert capability_exit_bounds(capability) == {
        exit_port: (Fraction(1, 2), Fraction(1, 4))
    }
    assert capability.input_ports[0] == (
        input_port,
        Fraction(1, 2),
        Fraction(1, 4),
    )
    actions = result.sparse_slice["cells"][0]["members"][0]["actions"]
    assert actions[0]["exits"] == [
        {"exit_port_id": exit_port, "probability": _q(1, 2)}
    ]
    assert actions[1]["exits"] == []
    assert all("successors" not in action for action in actions)
    construction = result.compilation.evidence["recovery_input_compilation"]
    assert construction["counts"]["cell_policy_assignments"] == 2
    assert construction["counts"]["distinct_scalar_exit_ports"] == 1
    assert result.compilation.evidence["exit_port_necessity_witnesses"][0][
        "port_id"
    ] == exit_port


def test_input_port_necessity_search_uses_conditional_multi_port_contexts() -> None:
    boundary, left, right = _conditional_two_port_boundary()
    compilation = compile_sparse_capability(
        boundary,
        frontier_input_port_ids=(left, right),
        admissible_input_pairs={
            left: ((Fraction(0), Fraction(0)), (Fraction(1), Fraction(0))),
            right: ((Fraction(0), Fraction(0)), (Fraction(2), Fraction(0))),
        },
    )

    capability = compilation.capability
    assert capability.input_port_ids == (left, right)
    assert evaluate_sparse_capability(
        capability,
        {left: (Fraction(0), Fraction(0)), right: (Fraction(2), Fraction(0))},
    ).root_reward_lower == 0
    assert evaluate_sparse_capability(
        capability,
        {left: (Fraction(1), Fraction(0)), right: (Fraction(2), Fraction(0))},
    ).root_reward_lower == 1

    witnesses = {
        row["port_id"]: row
        for row in compilation.evidence["input_port_necessity_witnesses"]
    }
    assert witnesses[left]["fixed_context_pairs"] == [
        {
            "port_id": right,
            "reward_lower": _q(2),
            "failure_upper": _q(0),
        }
    ]
    assert witnesses[right]["fixed_context_pairs"] == [
        {
            "port_id": left,
            "reward_lower": _q(1),
            "failure_upper": _q(0),
        }
    ]
    assert compilation.evidence["enumeration"]["counts"][
        "input_port_context_evaluations"
    ] == 4


def test_form_cover_subset_search_has_an_explicit_cap() -> None:
    input_port = "proof-node-bbbbbbbbbbbbbbbb"
    root = "proof-node-cccccccccccccccc"
    boundary = {
        "schema": "acfqp.redacted_boundary_view.v1",
        "graph_id": "failed-proof-graph-dddddddddddddddd",
        "frontier_id": "failed-proof-frontier-eeeeeeeeeeeeeeee",
        "delta": _q(1),
        "unrestricted_reward_upper": _q(1),
        "regret_tolerance": _q(1),
        "roots": [{"node_id": root, "probability": _q(1)}],
        "nodes": [
            {
                "node_id": root,
                "cell": "root",
                "remaining": 2,
                "selected_action": "root-action",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-1111111111111111",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [
                            {"node_id": input_port, "probability": _q(1)}
                        ],
                    },
                    {
                        "realization_id": "redacted-realization-2222222222222222",
                        "immediate_reward": _q(1, 2),
                        "failure_probability": _q(1, 2),
                        "successors": [],
                    },
                ],
            },
            {
                "node_id": input_port,
                "cell": "input",
                "remaining": 1,
                "selected_action": "input-action",
                "abstract_realizations": [
                    {
                        "realization_id": "redacted-realization-3333333333333333",
                        "immediate_reward": _q(0),
                        "failure_probability": _q(0),
                        "successors": [],
                    }
                ],
            },
        ],
    }
    boundary["boundary_view_id"] = _object_id("redacted-boundary-view", boundary)
    with pytest.raises(ValueError, match="form-subset evaluation cap exceeded"):
        compile_sparse_capability(
            boundary,
            frontier_input_port_ids=(input_port,),
            admissible_input_pairs={
                input_port: ((Fraction(0), Fraction(0)), (Fraction(1), Fraction(1)))
            },
            max_form_subset_evaluations=1,
        )


def test_abstract_exit_ports_are_scalar_only_and_require_usage_witness(
    sparse_case: dict,
) -> None:
    boundary = sparse_case["boundary"]
    causal_port = sparse_case["causal_port"]
    other_port = next(
        node["node_id"]
        for node in boundary["nodes"]
        if node["remaining"] == 1 and node["node_id"] != causal_port
    )
    with pytest.raises(ValueError, match="usage witness"):
        compile_sparse_capability(
            boundary,
            frontier_input_port_ids=(causal_port,),
            admissible_input_pairs={
                causal_port: sparse_case["admissible_pairs"]
            },
            abstract_exit_port_ids=(other_port,),
        )

    compilation = compile_sparse_capability(
        boundary,
        frontier_input_port_ids=(causal_port,),
        admissible_input_pairs={causal_port: sparse_case["admissible_pairs"]},
        abstract_exit_port_ids=(other_port,),
        exit_usage_witnesses={other_port: ("slice-branch:0123456789abcdef",)},
    )
    assert capability_exit_bounds(compilation.capability) == {
        other_port: (Fraction(1, 32), Fraction(199, 200))
    }
    exit_row = compilation.capability.to_dict()["exit_ports"][0]
    assert set(exit_row) == {"port_id", "reward_lower", "failure_upper"}
    assert compilation.evidence["exit_port_necessity_witnesses"] == [
        {
            "port_id": other_port,
            "authorized_slice_branch_ids": ["slice-branch:0123456789abcdef"],
        }
    ]
