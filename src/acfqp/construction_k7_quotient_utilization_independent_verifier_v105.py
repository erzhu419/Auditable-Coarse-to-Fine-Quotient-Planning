"""Producer-free reconstruction of V105 quotient ordering and accounting."""

from __future__ import annotations

from collections import deque
import heapq
import hashlib
from itertools import product
from math import ceil
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v105 as domains
from acfqp import construction_k7_receipted_utilization_independent_verifier_v103 as v103
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "194cd7ccb5fa330dd4cad892f87c2618709a5320a4bdf49a3fd5f9a3fe4202ab"
CAMPAIGN_BYTE_COUNT = 3_348_042
CAMPAIGN_SHA256 = "fc21b35f88e83954aff0b9c79fc078188003c2911ad289beb4b7e5dcffc37772"
PREREGISTRATION_ID = "9310bb2f3b96c5b0540ef39c92989f628f6b3248bc1644baddfa5bb20a583cbe"
V104_CAMPAIGN_ID = "1f9787eee1cb853f695c3fcb494822f7168abdebb1363f357069f468ce67eb79"
V104_VERIFICATION_ID = "77cbc5f51f48eef1436c5c778048c0b32593dc7c99d428118e98f9af0c1c8af9"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_017_101),
    ("BALANCED_BATCH_REFINEMENT", 1_017_102),
    ("MAINTENANCE_CASCADE", 1_017_103),
    ("MAINTENANCE_CASCADE", 1_017_104),
)
EPISODES = (141, 142, 143)
VERIFICATION_ID = "588349230a4ccdce80f5e68bd66c7db54e4eb471d2c76925f70259f290723c4b"
EXPECTED_CANONICAL_BYTE_COUNT = 3_151
EXPECTED_CANONICAL_SHA256 = "2655f9a6d84ddd9bdfe5cdaeb9a4add22d0981cbe7ac5aad6b0a51cd514b3e9d"

_ACQUISITION_DOMAIN = b"acfqp:construction-k7-true-bit-symmetric-acquisition:v59\x00"
_LAYOUT_DOMAIN = b"acfqp:construction-k7-joint-factor-residual-layout:v54\x00"
_MODEL_DOMAIN = b"acfqp:generic-observation-quotient-graph:v105\x00"
_PLAN_DOMAIN = b"acfqp:generic-observation-quotient-plan:v105\x00"
_RECEIPT_DOMAIN = b"acfqp:generic-actual-quotient-execution-receipt:v105\x00"
_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-quotient-sequence:v105\x00"
_OOD_DOMAIN = b"acfqp:incompatible-schema-no-transfer-control:v99\x00"
_SOURCE_FACTOR_LIBRARY_ID = "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
_SIGNATURES = {
    "E00": "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
    "E01": "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
    "E07": "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
}
_EPISODE_EXTRAS = {
    "quotient_graph_before_episode",
    "actual_quotient_execution_receipts",
    "actual_quotient_execution_receipt_count",
    "quotient_proposal_admitted_execution_count",
    "chosen_action_matches_admitted_quotient_proposal_count",
    "new_certificate_labels_charged_this_episode",
    "paid_certificate_labels_cumulative",
    "persistent_exact_support_group_count_after_episode",
}


class ConstructionK7QuotientUtilizationIndependentVerifierV105Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QuotientUtilizationIndependentVerifierV105Error(message)


def _hash(domain: bytes, payload: Any) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _content(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V105 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _hash(domain, payload):
        _fail(f"V105 {key} changed")


def _row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        tuple(row["pre_vector"]),
        row["selected_action"]["action_key"],
        tuple(row["post_vector"]),
    )


def _row(document: Any) -> dict[str, Any]:
    keys = {
        "occurrence",
        "transition_index",
        "pre_vector",
        "legal_action_keys_before",
        "selected_action",
        "post_vector",
        "legal_action_keys_after",
        "terminal_acceptance_after",
        "outcome_tape_sha256",
    }
    if type(document) is not dict or set(document) != keys:
        _fail("V105 raw transition schema changed")
    selected = document["selected_action"]
    vectors = (document["pre_vector"], document["post_vector"])
    legal = (
        document["legal_action_keys_before"],
        document["legal_action_keys_after"],
    )
    if (
        type(document["occurrence"]) is not int
        or type(document["transition_index"]) is not int
        or type(selected) is not dict
        or set(selected) != {"action_key", "anonymous_fields"}
        or type(selected["action_key"]) is not int
        or type(selected["anonymous_fields"]) is not list
        or any(type(value) is not int for value in selected["anonymous_fields"])
        or any(type(vector) is not list or any(type(value) is not int for value in vector) for vector in vectors)
        or len(vectors[0]) != len(vectors[1])
        or any(type(values) is not list or any(type(key) is not int for key in values) for values in legal)
        or document["terminal_acceptance_after"] not in (None, True, False)
    ):
        _fail("V105 raw transition inventory changed")
    return document


def _deduplicate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {_row_key(_row(row)): row for row in rows}
    return [unique[key] for key in sorted(unique)]


def _group_count(rows: list[dict[str, Any]]) -> int:
    return len(
        {
            (tuple(row["pre_vector"]), row["selected_action"]["action_key"])
            for row in rows
        }
    )


def _catalogue(rows: list[dict[str, Any]]) -> dict[int, tuple[int, ...]]:
    result: dict[int, tuple[int, ...]] = {}
    for row in rows:
        selected = row["selected_action"]
        fields = tuple(selected["anonymous_fields"])
        old = result.setdefault(selected["action_key"], fields)
        if old != fields:
            _fail("V105 anonymous action descriptor changed for one key")
    if not result:
        _fail("V105 action catalogue is empty")
    return result


def _verify_candidate(candidate: Any, issuance_rows: list[dict[str, Any]], current_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if type(candidate) is not dict:
        _fail("V105 partial candidate type changed")
    payload = {key: value for key, value in candidate.items() if key != "candidate_id"}
    layout = candidate.get("layout")
    if type(layout) is not dict:
        _fail("V105 candidate layout changed")
    layout_payload = {
        key: value
        for key, value in layout.items()
        if key not in ("layout_id", "schema")
    }
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    state_width = candidate.get("state_width")
    action_width = candidate.get("action_field_width")
    assignments = candidate.get("compiled_factor_assignments")
    if (
        candidate.get("candidate_id") != _hash(_ACQUISITION_DOMAIN, payload)
        or layout.get("layout_id") != _hash(_LAYOUT_DOMAIN, layout_payload)
        or type(state_width) is not int
        or type(action_width) is not int
        or type(state_order) is not list
        or sorted(state_order) != list(range(state_width))
        or type(action_order) is not list
        or sorted(action_order) != list(range(action_width))
        or type(assignments) is not list
        or len(assignments) < 3
        or candidate.get("source_factor_library_id") != _SOURCE_FACTOR_LIBRARY_ID
        or candidate.get("target_slot_inventory_supplied_by_prior") is not False
        or candidate.get("target_bindings_derived_from_raw_observations") is not True
        or candidate.get("semantic_names_used") is not False
        or candidate.get("complete_world_model_claimed") is not False
        or candidate.get("planning_authority_present") is not False
    ):
        _fail("V105 candidate identity or boundary changed")
    targets = []
    for assignment in assignments:
        if type(assignment) is not dict:
            _fail("V105 factor assignment type changed")
        target = assignment.get("target_column")
        expression = assignment.get("expression")
        if type(target) is not int or target in targets or not 0 <= target < state_width or type(expression) is not list or not expression:
            _fail("V105 factor assignment inventory changed")
        targets.append(target)
        head = expression[0]
        if head == "E00":
            exact = (
                expression == ["E00", target]
                and assignment.get("result_type") == "INT"
                and assignment.get("state_dependencies") == [target]
                and assignment.get("action_dependencies") == []
            )
        elif head == "E01":
            field = expression[1] if len(expression) == 2 else None
            exact = (
                type(field) is int
                and 0 <= field < action_width
                and assignment.get("result_type") == "INT"
                and assignment.get("state_dependencies") == []
                and assignment.get("action_dependencies") == [field]
            )
        elif head == "E07":
            field = (
                expression[2][2][1]
                if len(expression) == 3
                and expression[1] == ["E00", target]
                and type(expression[2]) is list
                and len(expression[2]) == 3
                and expression[2][0] == "E05"
                and expression[2][1] == ["E00", target]
                and type(expression[2][2]) is list
                and len(expression[2][2]) == 2
                and expression[2][2][0] == "E01"
                else None
            )
            exact = (
                type(field) is int
                and 0 <= field < action_width
                and assignment.get("result_type") == "FINITE_INT_SUPPORT"
                and assignment.get("state_dependencies") == [target]
                and assignment.get("action_dependencies") == [field]
            )
        else:
            exact = False
        if not exact or assignment.get("signature_sha256") != _SIGNATURES.get(head):
            _fail("V105 factor assignment escaped the frozen grammar")
    if (
        targets != sorted(targets)
        or candidate.get("unknown_residual_target_columns")
        != sorted(set(range(state_width)) - set(targets))
        or candidate.get("raw_transition_count_at_issuance") != len(issuance_rows)
        or candidate.get("raw_transition_sha256")
        != hashlib.sha256(canonical_json_bytes(issuance_rows)).hexdigest()
    ):
        _fail("V105 candidate observation binding changed")
    for row in current_rows:
        _check_program_row(candidate, row)
    return candidate


def _aligned(candidate: Mapping[str, Any], row: Mapping[str, Any]) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    layout = candidate["layout"]
    pre = tuple(row["pre_vector"][index] for index in layout["state_canonical_to_raw"])
    post = tuple(row["post_vector"][index] for index in layout["state_canonical_to_raw"])
    fields = tuple(row["selected_action"]["anonymous_fields"][index] for index in layout["action_canonical_to_raw"])
    return pre, post, fields


def _supports(candidate: Mapping[str, Any], projected: tuple[int, ...], fields: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    assignments = candidate["compiled_factor_assignments"]
    by_target = dict(zip((row["target_column"] for row in assignments), projected, strict=True))
    values = []
    for assignment in assignments:
        expression = assignment["expression"]
        target = assignment["target_column"]
        if expression[0] == "E00":
            support = (by_target[target],)
        elif expression[0] == "E01":
            support = (fields[expression[1]],)
        elif expression[0] == "E07":
            base = by_target[target]
            field = expression[2][2][1]
            support = tuple(sorted({base, base + fields[field]}))
        else:
            _fail("V105 factor program escaped its grammar")
        values.append(support)
    return tuple(sorted(set(product(*values))))


def _check_program_row(candidate: Mapping[str, Any], row: Mapping[str, Any]) -> int:
    pre, post, fields = _aligned(candidate, row)
    targets = tuple(row["target_column"] for row in candidate["compiled_factor_assignments"])
    projected_pre = tuple(pre[target] for target in targets)
    projected_post = tuple(post[target] for target in targets)
    supports = _supports(candidate, projected_pre, fields)
    if projected_post not in supports:
        _fail("V105 observed edge escaped the compiled factor program")
    return len(supports)


def _verify_acquisition(document: Any, initial_rows: list[dict[str, Any]], family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V105 acquisition type changed")
    sorted_initial = sorted(initial_rows, key=lambda row: row["transition_index"])
    candidate = document.get("candidate")
    issuance_count = candidate.get("raw_transition_count_at_issuance") if type(candidate) is dict else None
    if type(issuance_count) is not int or not 0 < issuance_count <= len(sorted_initial):
        _fail("V105 candidate issuance prefix changed")
    _verify_candidate(candidate, sorted_initial[:issuance_count], sorted_initial)
    payload = {key: value for key, value in document.items() if key != "acquisition_id"}
    if (
        document.get("acquisition_id") != _hash(_ACQUISITION_DOMAIN, payload)
        or document.get("schema") != "acfqp.true_bit_partial_acquisition.v59"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("arm") != "ANONYMOUS_FACTOR_PRIOR_ON"
        or document.get("factor_prior_enabled") is not True
        or document.get("ground_support_labels") != _group_count(sorted_initial)
        or document.get("raw_transition_count") != len(sorted_initial)
        or document.get("raw_transition_sha256")
        != hashlib.sha256(canonical_json_bytes(sorted_initial)).hexdigest()
        or document.get("partial_prediction_scope_only") is not True
        or document.get("unknown_residual_outputs_claimed") is not False
        or document.get("complete_world_model_claimed") is not False
        or document.get("terminal_observation_required_for_planning_objective") is not True
        or document.get("reachable_frontier_exhaustion_input_consumed") is not False
        or document.get("heuristic_mdl_information_units_consumed") is not False
        or document.get("predictive_evidence_to_mdl_credit_consumed") is not False
        or document.get("symmetric_minimum_common_prefix_post_audit") is not True
    ):
        _fail("V105 acquisition identity or semantics changed")
    return candidate


def _expected_model(candidate: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _deduplicate(rows)
    targets = tuple(row["target_column"] for row in candidate["compiled_factor_assignments"])
    edges: set[tuple[tuple[int, ...], int, tuple[int, ...]]] = set()
    terminal: dict[tuple[int, ...], set[str]] = {}
    checks = 0
    for row in rows:
        pre, post, _fields = _aligned(candidate, row)
        projected_pre = tuple(pre[target] for target in targets)
        projected_post = tuple(post[target] for target in targets)
        checks += _check_program_row(candidate, row)
        edges.add((projected_pre, row["selected_action"]["action_key"], projected_post))
        terminal.setdefault(projected_post, set()).add(
            "ACTIVE"
            if row["legal_action_keys_after"]
            else "ACCEPT"
            if row["terminal_acceptance_after"] is True
            else "REJECT"
        )
    edge_rows = [
        {
            "projected_pre": list(pre),
            "action_key": key,
            "projected_post": list(post),
        }
        for pre, key, post in sorted(edges)
    ]
    terminal_rows = [
        {
            "projected_state": list(state),
            "observed_terminal_classes": sorted(classes),
        }
        for state, classes in sorted(terminal.items())
    ]
    payload = {
        "schema": "acfqp.generic_observation_quotient_graph.v105",
        "partial_candidate_id": candidate["candidate_id"],
        "layout_id": candidate["layout"]["layout_id"],
        "projected_state_target_columns": list(targets),
        "quotiented_residual_target_columns": candidate["unknown_residual_target_columns"],
        "projected_state_width": len(targets),
        "projected_edge_rows": edge_rows,
        "projected_edge_count": len(edge_rows),
        "projected_terminal_rows": terminal_rows,
        "projected_terminal_state_count": len(terminal_rows),
        "source_ground_support_label_count": _group_count(rows),
        "source_raw_transition_row_count": len(rows),
        "source_projected_edge_program_checks": checks,
        "source_projected_rows_sha256": hashlib.sha256(
            canonical_json_bytes({"edges": edge_rows, "terminal": terminal_rows})
        ).hexdigest(),
        "all_projected_edges_checked_by_compiled_factor_program": True,
        "residual_coordinates_deliberately_quotiented_not_imputed": True,
        "query_local_overlay_may_extend_graph_only_after_certificate_failure": True,
        "ground_transition_accessed_during_abstract_search": False,
        "quotient_graph_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_claimed": False,
    }
    return {**payload, "quotient_graph_id": _hash(_MODEL_DOMAIN, payload)}


def _terminal_rules(candidate: Mapping[str, Any], rows: list[dict[str, Any]], catalogue: Mapping[int, tuple[int, ...]]) -> list[dict[str, Any]]:
    accepting = []
    for row in rows:
        if row["terminal_acceptance_after"] is True:
            _pre, post, _fields = _aligned(candidate, row)
            accepting.append(post)
    if not accepting:
        _fail("V105 quotient graph has no accepting projection")
    aligned_actions = [
        tuple(fields[index] for index in candidate["layout"]["action_canonical_to_raw"])
        for _key, fields in sorted(catalogue.items())
    ]
    result = []
    for assignment in candidate["compiled_factor_assignments"]:
        target = assignment["target_column"]
        values = sorted({state[target] for state in accepting})
        expression = assignment["expression"]
        if expression[0] == "E00" and len(values) == 1:
            rule = {"kind": "EQUAL", "value": values[0]}
        elif expression[0] == "E07":
            field = expression[2][2][1]
            increments = [action[field] for action in aligned_actions]
            if all(value >= 0 for value in increments):
                rule = {"kind": "AT_LEAST", "value": min(values)}
            elif all(value <= 0 for value in increments):
                rule = {"kind": "AT_MOST", "value": max(values)}
            else:
                rule = {"kind": "OBSERVED_SET", "values": values}
        else:
            rule = {"kind": "UNCONSTRAINED"}
        result.append({"target_column": target, **rule})
    return result


def _terminal_match(state: tuple[int, ...], rules: list[dict[str, Any]]) -> bool:
    for value, rule in zip(state, rules, strict=True):
        kind = rule["kind"]
        if kind == "EQUAL" and value != rule["value"]:
            return False
        if kind == "AT_LEAST" and value < rule["value"]:
            return False
        if kind == "AT_MOST" and value > rule["value"]:
            return False
        if kind == "OBSERVED_SET" and value not in rule["values"]:
            return False
    return True


def _program_plan(
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
    initial: tuple[int, ...],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    actions = [
        (
            key,
            tuple(
                fields[index]
                for index in candidate["layout"]["action_canonical_to_raw"]
            ),
        )
        for key, fields in sorted(catalogue.items())
    ]
    action_values = {
        field: tuple(values[field] for _key, values in actions)
        for field in range(candidate["action_field_width"])
    }

    def lower_bound(state: tuple[int, ...]) -> int | None:
        bounds = []
        for offset, (assignment, rule) in enumerate(
            zip(candidate["compiled_factor_assignments"], rules, strict=True)
        ):
            current = state[offset]
            kind = rule["kind"]
            if kind == "UNCONSTRAINED":
                bounds.append(0)
                continue
            if kind == "EQUAL":
                if current != rule["value"]:
                    return None
                bounds.append(0)
                continue
            expression = assignment["expression"]
            if expression[0] != "E07":
                bounds.append(0)
                continue
            increments = action_values[expression[2][2][1]]
            if kind == "AT_LEAST":
                distance = max(0, rule["value"] - current)
                maximum = max(increments)
            elif kind == "AT_MOST":
                distance = max(0, current - rule["value"])
                maximum = max(-value for value in increments)
            else:
                distance = min(abs(current - value) for value in rule["values"])
                maximum = max(abs(value) for value in increments)
            bounds.append(
                0
                if distance == 0
                else ceil(distance / maximum)
                if maximum > 0
                else 13
            )
        return max(bounds, default=0)

    initial_bound = lower_bound(initial)
    if initial_bound is None or initial_bound > 12:
        _fail("V105 factor-program fallback is infeasible")
    frontier = [(initial_bound, 0, initial)]
    best_depth = {initial: 0}
    predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
        initial: None
    }
    terminal = None
    evaluations = 0
    while frontier:
        _priority, depth, state = heapq.heappop(frontier)
        if depth != best_depth[state]:
            continue
        if _terminal_match(state, rules):
            terminal = state
            break
        if depth == 12:
            continue
        for key, fields in actions:
            successors = _supports(candidate, state, fields)
            evaluations += len(successors)
            for successor in successors:
                if successor == state:
                    continue
                bound = lower_bound(successor)
                successor_depth = depth + 1
                if (
                    bound is None
                    or successor_depth + bound > 12
                    or successor_depth >= best_depth.get(successor, 13)
                ):
                    continue
                best_depth[successor] = successor_depth
                predecessor[successor] = (state, key)
                heapq.heappush(
                    frontier,
                    (successor_depth + bound, successor_depth, successor),
                )
    if terminal is None:
        _fail("V105 factor-program fallback found no continuation")
    reversed_actions = []
    cursor = terminal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        reversed_actions.append(key)
        cursor = parent
    plan = list(reversed(reversed_actions))
    return {
        "schema": "acfqp.generic_partial_factor_receding_plan.v15",
        "candidate_id": candidate["candidate_id"],
        "known_factor_target_columns": [
            row["target_column"] for row in candidate["compiled_factor_assignments"]
        ],
        "unknown_residual_target_columns": candidate["unknown_residual_target_columns"],
        "terminal_projection_rule": rules,
        "rejected_accepting_projection_count": 0,
        "selected_support_feasible_depth": len(plan),
        "action_keys": plan,
        "projected_planning_compute_events": evaluations,
        "stochastic_support_branch_receding_semantics": True,
        "robust_all_branches_completion_claimed": False,
        "finite_worst_case_completion_claimed": False,
        "ground_transition_accessed_during_abstract_search": False,
        "complete_world_model_claimed": False,
    }


def _expected_plan(model: Mapping[str, Any], candidate: Mapping[str, Any], rows: list[dict[str, Any]], catalogue: Mapping[int, tuple[int, ...]], raw_state: list[int], planning_source: str) -> dict[str, Any]:
    targets = tuple(row["target_column"] for row in candidate["compiled_factor_assignments"])
    canonical = tuple(raw_state[index] for index in candidate["layout"]["state_canonical_to_raw"])
    initial = tuple(canonical[target] for target in targets)
    adjacency: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = {}
    for edge in model["projected_edge_rows"]:
        adjacency.setdefault(tuple(edge["projected_pre"]), set()).add(
            (edge["action_key"], tuple(edge["projected_post"]))
        )
    rules = _terminal_rules(candidate, rows, catalogue)
    if planning_source == "OBSERVATION_QUOTIENT_GRAPH":
        queue = deque((initial,))
        predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {initial: None}
        goal = None
        evaluations = 0
        while queue:
            state = queue.popleft()
            if _terminal_match(state, rules):
                goal = state
                break
            for key, successor in sorted(adjacency.get(state, set())):
                evaluations += 1
                if successor not in predecessor:
                    predecessor[successor] = (state, key)
                    queue.append(successor)
        if goal is None:
            _fail("V105 recorded quotient graph plan is not reconstructable")
        reversed_actions = []
        cursor = goal
        while predecessor[cursor] is not None:
            parent, key = predecessor[cursor]
            reversed_actions.append(key)
            cursor = parent
        actions = list(reversed(reversed_actions))
        embedded = {
            "schema": "acfqp.generic_partial_factor_observation_graph_plan.v15",
            "candidate_id": candidate["candidate_id"],
            "known_factor_target_columns": list(targets),
            "unknown_residual_target_columns": candidate["unknown_residual_target_columns"],
            "abstract_state_count": len(adjacency),
            "abstract_edge_count": sum(len(edges) for edges in adjacency.values()),
            "compiled_factor_support_edge_checks": model["source_projected_edge_program_checks"],
            "terminal_projection_rule": rules,
            "action_keys": actions,
            "projected_planning_compute_events": evaluations,
            "compiled_factor_program_checked_each_abstract_edge": True,
            "ground_transition_accessed_during_abstract_search": False,
            "complete_world_model_claimed": False,
        }
    elif planning_source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        embedded = _program_plan(candidate, rows, catalogue, initial, rules)
        actions = embedded["action_keys"]
        evaluations = embedded["projected_planning_compute_events"]
    else:
        _fail("V105 quotient planning source changed")
    if not actions:
        _fail("V105 quotient plan action path is empty")
    payload = {
        "schema": "acfqp.generic_observation_quotient_plan.v105",
        "quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": candidate["candidate_id"],
        "planning_source": planning_source,
        "initial_action_key": actions[0],
        "projected_action_path": actions,
        "abstract_support_branch_evaluations": evaluations,
        "embedded_projected_plan": embedded,
        "residual_coordinates_read_during_search": False,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {**payload, "quotient_plan_id": _hash(_PLAN_DOMAIN, payload)}


def _receipt(document: Any, episode_index: int, expected_wrapper: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V105 actual quotient receipt type changed")
    base = v103._receipt(document.get("base_execution_receipt"))
    wrapper = document.get("quotient_plan_receipt")
    if wrapper != expected_wrapper:
        _fail("V105 plan/execution wrapper join changed")
    plan = None if wrapper is None else wrapper.get("abstract_plan")
    if wrapper is not None and (
        type(wrapper) is not dict
        or wrapper.get("raw_state") != base["raw_state"]
        or type(plan) is not dict
        or plan.get("agreement_shield_receipt") != base["shield_receipt"]
        or plan.get("legacy_two_channel_shield_carries_one_identical_quotient_proposal") is not True
    ):
        _fail("V105 plan/base receipt join changed")
    proposed = None if plan is None else plan["initial_action_key"]
    admitted = proposed in base["legal_action_keys"] if proposed is not None else False
    chosen = base["chosen_action_key"]
    match = admitted and chosen == proposed
    source = (
        "ACTUAL_QUOTIENT_MODEL_ORDER"
        if match
        else "EXACT_CERTIFICATE_FALLBACK_AFTER_QUOTIENT_ORDER"
        if admitted
        else "EXACT_CERTIFICATE_ONLY_NO_QUOTIENT_ORDER"
    )
    payload = {
        "schema": "acfqp.generic_actual_quotient_execution_receipt.v105",
        "episode_index": episode_index,
        "decision_index": base["decision_index"],
        "raw_state": base["raw_state"],
        "chosen_action_key": chosen,
        "legal_action_keys": base["legal_action_keys"],
        "base_execution_receipt": base,
        "base_execution_receipt_id": base["execution_receipt_id"],
        "quotient_plan_receipt": wrapper,
        "quotient_graph_id": None if plan is None else plan["quotient_graph_id"],
        "quotient_plan_id": None if plan is None else plan["quotient_plan_id"],
        "quotient_proposed_action_key": proposed,
        "quotient_proposal_admitted_to_real_action_order": admitted,
        "chosen_action_matches_admitted_quotient_proposal": match,
        "actual_action_ordering_source": source,
        "exact_certificate_may_override_fallible_quotient_order": True,
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    expected = {
        **payload,
        "actual_quotient_execution_receipt_id": _hash(_RECEIPT_DOMAIN, payload),
    }
    if document != expected:
        _fail("V105 actual quotient receipt semantics changed")
    return expected


def _episode(
    episode: Any,
    model: dict[str, Any],
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
    family: str,
    seed: int,
    episode_index: int,
    paid_before: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    if type(episode) is not dict:
        _fail("V105 quotient episode type changed")
    v103._content_id(
        episode,
        "episode_id",
        v103._LATER_EPISODE_DOMAIN,
        _EPISODE_EXTRAS,
    )
    if (
        episode.get("schema") != "acfqp.generic_receipted_preloaded_certificate_episode.v103"
        or episode.get("family") != family
        or episode.get("seed") != seed
        or episode.get("episode_index") != episode_index
        or episode.get("arm") != "OBSERVATION_DERIVED_QUOTIENT_GRAPH_ORDERING"
        or episode.get("target_candidate_id") != candidate["candidate_id"]
        or episode.get("preloaded_acquisition_ground_support_labels") != _group_count(rows)
        or episode.get("success") is not True
        or episode.get("abstract_model_used_only_for_action_ordering") is not True
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("target_episode_outcomes_used_to_refit_model_or_alignment") is not False
        or episode.get("same_exact_engine_implementation_for_transfer_and_strict_arms") is not True
        or episode.get("complete_world_model_synthesized") is not False
        or episode.get("quotient_graph_before_episode") != model
    ):
        _fail("V105 quotient episode boundary changed")
    wrappers = episode.get("abstract_plan_receipts")
    if type(wrappers) is not list:
        _fail("V105 quotient plan inventory changed")
    by_raw = {}
    verified_wrappers = []
    for wrapper in wrappers:
        if type(wrapper) is not dict or set(wrapper) != {"raw_state", "abstract_plan"}:
            _fail("V105 quotient plan wrapper changed")
        raw = wrapper["raw_state"]
        if type(raw) is not list or tuple(raw) in by_raw:
            _fail("V105 quotient plan state inventory changed")
        plan = wrapper["abstract_plan"]
        expected_plan = _expected_plan(
            model,
            candidate,
            rows,
            catalogue,
            raw,
            plan.get("planning_source") if type(plan) is dict else "",
        )
        core = {
            key: value
            for key, value in plan.items()
            if key
            not in (
                "agreement_shield_receipt",
                "legacy_two_channel_shield_carries_one_identical_quotient_proposal",
            )
        }
        if core != expected_plan:
            _fail("V105 quotient plan differs from independent graph replay")
        v103._shield(plan.get("agreement_shield_receipt"))
        by_raw[tuple(raw)] = wrapper
        verified_wrappers.append(wrapper)
    bases = episode.get("abstract_execution_receipts")
    actions = episode.get("action_keys")
    actual = episode.get("actual_quotient_execution_receipts")
    if (
        type(bases) is not list
        or type(actions) is not list
        or type(actual) is not list
        or episode.get("execution_steps") != len(actions)
        or len(bases) != len(actions)
        or len(actual) != len(actions)
        or episode.get("every_execution_action_has_content_addressed_receipt") is not True
    ):
        _fail("V105 episode execution inventory changed")
    expected_actual = []
    for decision, (base_document, actual_document, key) in enumerate(
        zip(bases, actual, actions, strict=True)
    ):
        base = v103._receipt(base_document)
        if base["decision_index"] != decision or base["chosen_action_key"] != key:
            _fail("V105 base receipt/action join changed")
        expected_actual.append(
            _receipt(actual_document, episode_index, by_raw.get(tuple(base["raw_state"])))
        )
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"]
        for row in expected_actual
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"]
        for row in expected_actual
    )
    if (
        episode.get("actual_quotient_execution_receipt_count") != len(expected_actual)
        or episode.get("quotient_proposal_admitted_execution_count") != admitted
        or episode.get("chosen_action_matches_admitted_quotient_proposal_count") != matches
        or episode.get("abstract_plan_success_count") != len(verified_wrappers)
        or type(episode.get("abstract_plan_attempt_count")) is not int
        or episode.get("abstract_plan_attempt_count") < len(verified_wrappers)
        or type(episode.get("abstract_plan_abstention_count")) is not int
        or episode.get("abstract_plan_abstention_count")
        < episode.get("abstract_plan_attempt_count") - len(verified_wrappers)
        or episode.get("abstract_planning_compute_events")
        != sum(
            wrapper["abstract_plan"]["abstract_support_branch_evaluations"]
            for wrapper in verified_wrappers
        )
    ):
        _fail("V105 quotient episode utilization changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if type(failures) is not list or type(distinctions) is not list or len(failures) != len(distinctions):
        _fail("V105 certificate/distinction inventory changed")
    for index, (failure, distinction) in enumerate(zip(failures, distinctions, strict=True)):
        if (
            type(failure) is not dict
            or type(distinction) is not dict
            or failure.get("failure_index") != index
            or distinction.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("ground_support_labels") != 1
        ):
            _fail("V105 certificate-first query discipline changed")
    incremental = sum(row["ground_support_labels"] for row in distinctions)
    raw_incremental = [
        _row(row)
        for distinction in distinctions
        for row in distinction.get("raw_transition_rows", [])
    ]
    if (
        episode.get("incremental_certificate_local_ground_support_labels") != incremental
        or episode.get("new_certificate_labels_charged_this_episode") != incremental
        or episode.get("total_target_ground_support_labels") != _group_count(rows) + incremental
        or episode.get("raw_incremental_transition_rows") != raw_incremental
        or episode.get("all_incremental_ground_queries_followed_failed_certificates") is not True
        or episode.get("paid_certificate_labels_cumulative") != paid_before + incremental
    ):
        _fail("V105 episode local-label accounting changed")
    updated = _deduplicate([*rows, *raw_incremental])
    if episode.get("persistent_exact_support_group_count_after_episode") != _group_count(updated):
        _fail("V105 persistent support count changed")
    return expected_actual, updated, incremental


def _sequence(document: Any, acquisition: Mapping[str, Any], family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V105 quotient sequence type changed")
    _content(document, "sequence_id", _SEQUENCE_DOMAIN)
    episodes = document.get("episodes")
    final_rows = document.get("persistent_exact_overlay_rows")
    models = document.get("quotient_models_before_each_episode")
    if (
        document.get("schema") != "acfqp.generic_persistent_quotient_sequence.v105"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id") != acquisition["candidate"]["candidate_id"]
        or type(episodes) is not list
        or len(episodes) != len(EPISODES)
        or type(models) is not list
        or len(models) != len(EPISODES)
        or type(final_rows) is not list
        or document.get("actual_engine_action_order_receipts_not_posthoc_policy_matches") is not True
        or document.get("query_local_exact_overlay_exclusively_discharges_safety") is not True
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("V105 quotient sequence boundary changed")
    final_rows = [_row(row) for row in final_rows]
    all_incremental = [
        _row(row)
        for episode in episodes
        for row in episode.get("raw_incremental_transition_rows", [])
    ]
    incremental_keys = {_row_key(row) for row in all_incremental}
    initial = [row for row in final_rows if _row_key(row) not in incremental_keys]
    if len(initial) + len(incremental_keys) != len(final_rows):
        _fail("V105 initial/overlay row partition changed")
    candidate = _verify_acquisition(acquisition, initial, family, seed)
    catalogue = _catalogue(final_rows)
    rows = _deduplicate(initial)
    all_actual = []
    all_failures = []
    all_distinctions = []
    paid = 0
    for expected_index, episode, model in zip(EPISODES, episodes, models, strict=True):
        expected_model = _expected_model(candidate, rows)
        if model != expected_model or episode.get("quotient_graph_before_episode") != expected_model:
            _fail("V105 quotient graph differs from observation replay")
        actual, rows, incremental = _episode(
            episode,
            expected_model,
            candidate,
            rows,
            catalogue,
            family,
            seed,
            expected_index,
            paid,
        )
        paid += incremental
        all_actual.extend(actual)
        all_failures.extend(episode["failed_certificates"])
        all_distinctions.extend(episode["local_distinctions"])
    if rows != final_rows:
        _fail("V105 final persistent overlay changed")
    steps = len(all_actual)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in all_actual
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in all_actual
    )
    if (
        document.get("all_actual_quotient_execution_receipts") != all_actual
        or document.get("actual_quotient_execution_receipt_count") != steps
        or document.get("execution_step_count") != steps
        or document.get("quotient_proposal_admitted_execution_count") != admitted
        or document.get("chosen_action_matches_admitted_quotient_proposal_count") != matches
        or document.get("quotient_proposal_admitted_strict_majority") != (2 * admitted > steps)
        or document.get("chosen_action_matches_admitted_quotient_proposal_strict_majority") != (2 * matches > steps)
        or document.get("initial_acquisition_ground_support_labels_paid_once") != acquisition["ground_support_labels"]
        or document.get("certificate_ground_support_labels_paid_once") != paid
        or document.get("lifetime_target_ground_support_labels") != acquisition["ground_support_labels"] + paid
        or document.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(final_rows)).hexdigest()
        or document.get("persistent_exact_support_group_count") != _group_count(final_rows)
        or document.get("all_failed_certificates") != all_failures
        or document.get("all_local_distinctions") != all_distinctions
        or document.get("every_new_ground_query_followed_a_failed_certificate") is not True
        or document.get("quotient_graph_updates_only_from_certificate_local_overlay") is not True
    ):
        _fail("V105 sequence aggregate reconstruction changed")
    return {
        "execution_steps": steps,
        "admitted": admitted,
        "matches": matches,
        "certificate_labels": paid,
        "initial_labels": acquisition["ground_support_labels"],
        "lifetime_labels": acquisition["ground_support_labels"] + paid,
        "planning_compute": sum(row["abstract_planning_compute_events"] for row in episodes),
        "later_zero_label_reuse": any(
            row["episode_index"] != EPISODES[0]
            and row["new_certificate_labels_charged_this_episode"] == 0
            and row["quotient_proposal_admitted_execution_count"] > 0
            for row in episodes
        ),
    }


def _direct(document: Any, family: str, seed: int, candidate_id: str) -> int:
    if (
        type(document) is not dict
        or document.get("schema") != "acfqp.generic_strict_cold_direct_sequence.v96"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("free_target_rows_received") is not False
        or document.get("abstract_planning_compute_events") != 0
    ):
        _fail("V105 direct sequence changed")
    episodes = document.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V105 direct episode inventory changed")
    labels = 0
    for expected_index, episode in zip(EPISODES, episodes, strict=True):
        v103._content_id(episode, "episode_id", v103._DIRECT_EPISODE_DOMAIN)
        failures = episode.get("failed_certificates")
        distinctions = episode.get("local_distinctions")
        if (
            episode.get("schema") != "acfqp.generic_preloaded_certificate_receding_episode.v74"
            or episode.get("family") != family
            or episode.get("seed") != seed
            or episode.get("episode_index") != expected_index
            or episode.get("arm") != "STRICT_COLD_DIRECT_GROUND"
            or episode.get("target_candidate_id") != candidate_id
            or episode.get("success") is not True
            or episode.get("preloaded_acquisition_ground_support_labels") != 0
            or episode.get("abstract_model_used_only_for_action_ordering") is not False
            or episode.get("abstract_plan_attempt_count") != 0
            or episode.get("abstract_plan_receipts") != []
            or episode.get("abstract_planning_compute_events") != 0
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
            or type(failures) is not list
            or type(distinctions) is not list
            or len(failures) != len(distinctions)
            or any(row.get("ground_query_performed_before_failure") is not False for row in failures)
            or any(row.get("query_after_failed_certificate") is not True for row in distinctions)
        ):
            _fail("V105 direct episode semantics changed")
        incremental = sum(row["ground_support_labels"] for row in distinctions)
        if (
            episode.get("incremental_certificate_local_ground_support_labels") != incremental
            or episode.get("total_target_ground_support_labels") != incremental
        ):
            _fail("V105 direct label accounting changed")
        labels += incremental
    if document.get("lifetime_target_ground_support_labels") != labels:
        _fail("V105 direct lifetime labels changed")
    return labels


def _utilization(sequence: Mapping[str, Any]) -> dict[str, Any]:
    receipts = sequence["all_actual_quotient_execution_receipts"]
    steps = len(receipts)
    admitted = sum(row["quotient_proposal_admitted_to_real_action_order"] for row in receipts)
    matches = sum(row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts)
    overrides = sum(
        row["actual_action_ordering_source"] == "EXACT_CERTIFICATE_FALLBACK_AFTER_QUOTIENT_ORDER"
        for row in receipts
    )
    return {
        "schema": "acfqp.actual_quotient_execution_utilization.v105",
        "execution_receipt_count": steps,
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "exact_certificate_override_after_quotient_order_count": overrides,
        "exact_certificate_only_no_quotient_order_count": steps - admitted,
        "quotient_proposal_admitted_fraction_numerator": admitted,
        "quotient_proposal_admitted_fraction_denominator": steps,
        "chosen_action_match_fraction_numerator": matches,
        "chosen_action_match_fraction_denominator": steps,
        "quotient_actually_orders_strict_majority_of_execution": 2 * admitted > steps,
        "chosen_action_matches_quotient_strict_majority": 2 * matches > steps,
        "every_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "ordering_is_engine_input_not_posthoc_policy_match": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V105 occurrence type changed")
    payload = {key: value for key, value in document.items() if key != "occurrence_id"}
    if (
        document.get("occurrence_id")
        != domains.extension_content_id_v105(
            domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_OCCURRENCE_V105_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.actual_quotient_utilization_occurrence.v105"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V105 occurrence identity changed")
    sequence_document = document.get("persistent_quotient_sequence")
    acquisition = document.get("partial_acquisition")
    sequence = _sequence(sequence_document, acquisition, family, seed)
    direct_labels = _direct(
        document.get("strict_cold_direct_sequence"),
        family,
        seed,
        acquisition["candidate"]["candidate_id"],
    )
    utilization = _utilization(sequence_document)
    accounting = {
        "initial_acquisition_labels": sequence["initial_labels"],
        "certificate_local_labels": sequence["certificate_labels"],
        "quotient_lifetime_target_labels": sequence["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction": direct_labels - sequence["lifetime_labels"],
        "execution_steps": sequence["execution_steps"],
        "abstract_planning_compute_events": sequence["planning_compute"],
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "every_action_independently_receipted": utilization["every_action_independently_receipted"],
        "quotient_model_actually_orders_strict_majority": utilization["quotient_actually_orders_strict_majority_of_execution"],
        "chosen_action_matches_quotient_strict_majority": utilization["chosen_action_matches_quotient_strict_majority"],
        "ordering_is_engine_input_not_posthoc_match": utilization["ordering_is_engine_input_not_posthoc_policy_match"],
        "certificate_failure_only_query_discipline_clean": sequence_document["every_new_ground_query_followed_a_failed_certificate"],
        "later_zero_label_quotient_reuse_observed": sequence["later_zero_label_reuse"],
        "quotient_lifetime_labels_strictly_below_cold_direct": sequence["lifetime_labels"] < direct_labels,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("actual_quotient_utilization") != utilization
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("observation_derived_quotient_primary_ordering_verified") != gate["passed"]
        or document.get("local_ground_distinctions_only_after_certificate_failure_verified") != gate["passed"]
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V105 occurrence Gate or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "execution_steps": sequence["execution_steps"],
        "quotient_proposal_admitted_execution_count": sequence["admitted"],
        "chosen_action_matches_admitted_quotient_proposal_count": sequence["matches"],
        "initial_acquisition_labels": sequence["initial_labels"],
        "certificate_local_labels": sequence["certificate_labels"],
        "quotient_lifetime_target_labels": sequence["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction": direct_labels - sequence["lifetime_labels"],
        "abstract_planning_compute_events": sequence["planning_compute"],
        "gate_passed": gate["passed"],
    }


def _ood(document: Any) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.incompatible_schema_no_transfer_control.v99",
        "source_required_interface": {
            "state_representation": "OPAQUE_FLAT_INTEGER_COLUMNS",
            "transition_representation": "PRE_ACTION_POST_VECTOR",
            "dependency_driver_space": "SUCCESSOR_COLUMNS",
        },
        "target_interface": {
            "state_representation": "NESTED_UNORDERED_TYPED_GRAPH",
            "transition_representation": "EVENT_LOG_WITHOUT_POST_VECTOR",
            "dependency_driver_space": None,
        },
        "exact_interface_match": False,
        "learned_structure_prior_delivered": False,
        "target_binding_search_started": False,
        "target_outcomes_accessed": False,
        "rejection_reason": "REQUIRED_FLAT_SUCCESSOR_COLUMN_INTERFACE_ABSENT",
        "strict_ood_no_transfer": True,
    }
    expected = {**payload, "control_id": _hash(_OOD_DOMAIN, payload)}
    if document != expected:
        _fail("V105 incompatible-schema no-transfer control changed")
    return expected


def verify_quotient_utilization_campaign_bytes_v105(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V105 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V105 campaign is noncanonical")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("campaign_id")
        != domains.extension_content_id_v105(
            domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_CAMPAIGN_V105_DOMAIN,
            payload,
        )
        or document.get("schema") != "acfqp.actual_quotient_utilization_campaign.v105"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v104_campaign_id") != V104_CAMPAIGN_ID
        or document.get("v104_verification_id") != V104_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V105 campaign inventory changed")
    replay = [
        _occurrence(row, family, seed)
        for row, (family, seed) in zip(rows, TARGETS, strict=True)
    ]
    totals = {
        key: sum(row[key] for row in replay)
        for key in (
            "initial_acquisition_labels",
            "certificate_local_labels",
            "quotient_lifetime_target_labels",
            "cold_direct_lifetime_target_labels",
            "target_label_reduction",
            "execution_steps",
            "abstract_planning_compute_events",
            "quotient_proposal_admitted_execution_count",
            "chosen_action_matches_admitted_quotient_proposal_count",
        )
    }
    expected_accounting = {
        "initial_acquisition_labels": totals["initial_acquisition_labels"],
        "certificate_local_labels": totals["certificate_local_labels"],
        "quotient_lifetime_target_labels": totals["quotient_lifetime_target_labels"],
        "cold_direct_lifetime_target_labels": totals["cold_direct_lifetime_target_labels"],
        "target_label_reduction": totals["target_label_reduction"],
        "execution_steps": totals["execution_steps"],
        "abstract_planning_compute_events": totals["abstract_planning_compute_events"],
        "quotient_proposal_admitted_execution_count": totals["quotient_proposal_admitted_execution_count"],
        "chosen_action_matches_admitted_quotient_proposal_count": totals["chosen_action_matches_admitted_quotient_proposal_count"],
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = _ood(document.get("incompatible_schema_no_transfer_control"))
    passed = (
        all(row["gate_passed"] for row in replay)
        and 2 * totals["quotient_proposal_admitted_execution_count"] > totals["execution_steps"]
        and 2 * totals["chosen_action_matches_admitted_quotient_proposal_count"] > totals["execution_steps"]
        and totals["quotient_lifetime_target_labels"] < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(row["gate_passed"] for row in replay),
        "every_occurrence_actual_quotient_ordering_strict_majority": all(
            2 * row["quotient_proposal_admitted_execution_count"] > row["execution_steps"] for row in replay
        ),
        "every_occurrence_chosen_action_match_strict_majority": all(
            2 * row["chosen_action_matches_admitted_quotient_proposal_count"] > row["execution_steps"] for row in replay
        ),
        "aggregate_quotient_labels_strictly_below_cold_direct": totals["quotient_lifetime_target_labels"] < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": passed,
    }
    if (
        document.get("accounting") != expected_accounting
        or document.get("registered_gate") != gate
        or document.get("registered_multistep_execution_primarily_ordered_by_observation_derived_quotient") != passed
        or document.get("ground_distinctions_acquired_only_after_certificate_failure_verified") != passed
        or document.get("actual_engine_ordering_not_posthoc_receipt_reclassification") is not True
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V105 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.actual_quotient_utilization_verification.v105",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V105_ACTUAL_QUOTIENT_ORDERING_VERIFIED",
        "producer_free_observation_graph_reconstruction": True,
        "producer_free_plan_and_per_action_receipt_replay": True,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": expected_accounting,
        "registered_gate_independently_verified": passed,
        "actual_engine_ordering_not_posthoc_receipt_reclassification": True,
        "ground_query_discipline_independently_verified": True,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_quotient_utilization_verification_v105(raw: bytes) -> bytes:
    payload = verify_quotient_utilization_campaign_bytes_v105(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v105(
            domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_VERIFICATION_V105_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V105 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_quotient_utilization_verification_v105",
    "verify_quotient_utilization_campaign_bytes_v105",
)
