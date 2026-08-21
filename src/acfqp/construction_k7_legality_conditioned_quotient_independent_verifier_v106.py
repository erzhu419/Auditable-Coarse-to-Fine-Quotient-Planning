"""Producer-free reconstruction of V106 legality-conditioned quotient use."""

from __future__ import annotations

from collections import deque
import heapq
import hashlib
from math import ceil
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v106 as domains
from acfqp import construction_k7_quotient_utilization_independent_verifier_v105 as v105
from acfqp import construction_k7_receipted_utilization_independent_verifier_v103 as v103
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "ba998dae81c2e83c2e8dc388aebe878a5336a3dd6826d5f7d65e455545b7e5b7"
CAMPAIGN_BYTE_COUNT = 3_940_255
CAMPAIGN_SHA256 = "644cb223224f295cbe5ab8321d06004e3949cf9c3166569f061db3bc72cafd7d"
PREREGISTRATION_ID = "c020721354f8257c7d9aa202247c6d03d3fbe955f3d674097f6d29d978c413c5"
V105_CAMPAIGN_ID = "194cd7ccb5fa330dd4cad892f87c2618709a5320a4bdf49a3fd5f9a3fe4202ab"
V105_VERIFICATION_ID = "588349230a4ccdce80f5e68bd66c7db54e4eb471d2c76925f70259f290723c4b"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_018_101),
    ("BALANCED_BATCH_REFINEMENT", 1_018_102),
    ("MAINTENANCE_CASCADE", 1_018_103),
    ("MAINTENANCE_CASCADE", 1_018_104),
)
EPISODES = (151, 152, 153)
VERIFICATION_ID = "cc6f26563e94e4a6b76311ba0cc51a34ef92cd27f154fdbd2dcd7eea9a98f94e"
EXPECTED_CANONICAL_BYTE_COUNT = 4_263
EXPECTED_CANONICAL_SHA256 = "49c8cedc2003adc5146876ab67875eb0bf89dda5ab9d1913651aa35d498251bf"

_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"
_RECEIPT_DOMAIN = b"acfqp:generic-actual-legality-conditioned-execution-receipt:v106\x00"
_EPISODE_DOMAIN = b"acfqp:generic-legality-conditioned-certificate-episode:v106\x00"
_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-legality-conditioned-quotient-sequence:v106\x00"
_EPISODE_EXTRAS = {
    "quotient_graph_before_episode",
    "actual_legality_conditioned_execution_receipts",
    "actual_legality_conditioned_execution_receipt_count",
    "quotient_proposal_admitted_execution_count",
    "chosen_action_matches_admitted_quotient_proposal_count",
    "certificate_local_legality_plan_count",
    "new_certificate_labels_charged_this_episode",
    "paid_certificate_labels_cumulative",
    "persistent_exact_support_group_count_after_episode",
}
_LOCAL_LEGALITY_SOURCES = {
    "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
    "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
}


class ConstructionK7LegalityConditionedQuotientIndependentVerifierV106Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LegalityConditionedQuotientIndependentVerifierV106Error(
        message
    )


def _hash(domain: bytes, payload: Any) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _content(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V106 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _hash(domain, payload):
        _fail(f"V106 {key} changed")


def _program_plan(
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
    initial: tuple[int, ...],
    rules: list[dict[str, Any]],
    exact_legal_action_keys: tuple[int, ...],
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
        _fail("V106 factor-program fallback is infeasible")
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
        if v105._terminal_match(state, rules):
            terminal = state
            break
        if depth == 12:
            continue
        for key, fields in actions:
            if state == initial and key not in exact_legal_action_keys:
                continue
            successors = v105._supports(candidate, state, fields)
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
        _fail("V106 factor-program fallback found no continuation")
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
            row["target_column"]
            for row in candidate["compiled_factor_assignments"]
        ],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
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


def _expected_plan(
    model: Mapping[str, Any],
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
    raw_state: list[int],
    exact_legal_action_keys: tuple[int, ...],
    planning_source: str,
    legality_support_source: str,
    legality_failure_index: int | None,
) -> dict[str, Any]:
    targets = tuple(
        row["target_column"] for row in candidate["compiled_factor_assignments"]
    )
    canonical = tuple(
        raw_state[index]
        for index in candidate["layout"]["state_canonical_to_raw"]
    )
    initial = tuple(canonical[target] for target in targets)
    adjacency: dict[
        tuple[int, ...], set[tuple[int, tuple[int, ...]]]
    ] = {}
    for edge in model["projected_edge_rows"]:
        adjacency.setdefault(tuple(edge["projected_pre"]), set()).add(
            (edge["action_key"], tuple(edge["projected_post"]))
        )
    rules = v105._terminal_rules(candidate, rows, catalogue)
    if planning_source == "OBSERVATION_QUOTIENT_GRAPH":
        queue = deque((initial,))
        predecessor: dict[
            tuple[int, ...], tuple[tuple[int, ...], int] | None
        ] = {initial: None}
        goal = None
        evaluations = 0
        while queue:
            state = queue.popleft()
            if v105._terminal_match(state, rules):
                goal = state
                break
            for key, successor in sorted(adjacency.get(state, set())):
                evaluations += 1
                if state == initial and key not in exact_legal_action_keys:
                    continue
                if successor not in predecessor:
                    predecessor[successor] = (state, key)
                    queue.append(successor)
        if goal is None:
            _fail("V106 quotient graph plan is not independently reconstructable")
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
            "unknown_residual_target_columns": candidate[
                "unknown_residual_target_columns"
            ],
            "abstract_state_count": len(adjacency),
            "abstract_edge_count": sum(len(edges) for edges in adjacency.values()),
            "compiled_factor_support_edge_checks": model[
                "source_projected_edge_program_checks"
            ],
            "terminal_projection_rule": rules,
            "action_keys": actions,
            "projected_planning_compute_events": evaluations,
            "compiled_factor_program_checked_each_abstract_edge": True,
            "ground_transition_accessed_during_abstract_search": False,
            "complete_world_model_claimed": False,
        }
    elif planning_source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        embedded = _program_plan(
            candidate,
            rows,
            catalogue,
            initial,
            rules,
            exact_legal_action_keys,
        )
        actions = embedded["action_keys"]
        evaluations = embedded["projected_planning_compute_events"]
    else:
        _fail("V106 quotient planning source changed")
    if not actions or actions[0] not in exact_legal_action_keys:
        _fail("V106 legality-conditioned plan begins with an illegal action")
    payload = {
        "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": candidate["candidate_id"],
        "planning_source": planning_source,
        "initial_action_key": actions[0],
        "projected_action_path": actions,
        "abstract_support_branch_evaluations": evaluations,
        "embedded_projected_plan": embedded,
        "exact_legal_action_keys_at_initial_state": list(exact_legal_action_keys),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": None,
        "initial_illegal_actions_forbidden_in_abstract_search": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return payload


def _legal_by_raw(rows: list[dict[str, Any]]) -> dict[tuple[int, ...], tuple[int, ...]]:
    result: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in rows:
        for raw, legal in (
            (row["pre_vector"], row["legal_action_keys_before"]),
            (row["post_vector"], row["legal_action_keys_after"]),
        ):
            key = tuple(raw)
            value = tuple(legal)
            old = result.setdefault(key, value)
            if old != value:
                _fail("V106 exact legality rows are inconsistent")
    return result


def _verify_legality_provenance(
    raw: list[int],
    exact_legal: tuple[int, ...],
    source: str,
    failure_index: int | None,
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    distinctions: list[dict[str, Any]],
) -> None:
    if source == "PRELOADED_EXACT_LEGALITY_SUPPORT":
        if failure_index is not None or _legal_by_raw(rows).get(tuple(raw)) != exact_legal:
            _fail("V106 preloaded legality provenance changed")
        return
    if (
        source not in _LOCAL_LEGALITY_SOURCES
        or type(failure_index) is not int
        or not 0 <= failure_index < len(failures)
        or failure_index >= len(distinctions)
    ):
        _fail("V106 certificate-local legality provenance changed")
    failure = failures[failure_index]
    distinction = distinctions[failure_index]
    if (
        failure.get("failure_index") != failure_index
        or distinction.get("failure_index") != failure_index
        or failure.get("ground_query_performed_before_failure") is not False
        or distinction.get("query_after_failed_certificate") is not True
    ):
        _fail("V106 legality provenance lost certificate-first ordering")
    if source == "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE":
        if (
            failure.get("failure_kind") != "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT"
            or failure.get("action_key") is not None
            or failure.get("raw_state") != raw
            or distinction.get("distinction_kind") != "QUERY_LOCAL_LEGAL_ACTION_SET"
            or distinction.get("raw_state") != raw
            or distinction.get("legal_action_keys") != list(exact_legal)
        ):
            _fail("V106 local legality-only evidence changed")
        return
    transition_rows = distinction.get("raw_transition_rows")
    if (
        failure.get("failure_kind")
        != "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF"
        or distinction.get("distinction_kind")
        != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT"
        or type(transition_rows) is not list
        or not any(
            row.get("post_vector") == raw
            and row.get("legal_action_keys_after") == list(exact_legal)
            for row in transition_rows
            if type(row) is dict
        )
    ):
        _fail("V106 transition-derived legality evidence changed")


def _validate_unreconstructable_fallback_plan(
    plan: Mapping[str, Any],
    model: Mapping[str, Any],
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    catalogue: Mapping[int, tuple[int, ...]],
    exact_legal: tuple[int, ...],
) -> None:
    """Validate integrity/boundaries without pretending catalogue completeness."""
    embedded = plan.get("embedded_projected_plan")
    actions = plan.get("projected_action_path")
    rules = v105._terminal_rules(candidate, rows, catalogue)
    targets = [
        row["target_column"] for row in candidate["compiled_factor_assignments"]
    ]
    if (
        type(embedded) is not dict
        or type(actions) is not list
        or not actions
        or any(type(key) is not int for key in actions)
        or actions[0] not in exact_legal
        or plan.get("schema")
        != "acfqp.generic_legality_conditioned_quotient_plan.v106"
        or plan.get("quotient_graph_id") != model["quotient_graph_id"]
        or plan.get("partial_candidate_id") != candidate["candidate_id"]
        or plan.get("planning_source") != "COMPILED_FACTOR_PROGRAM_FALLBACK"
        or plan.get("initial_action_key") != actions[0]
        or plan.get("abstract_support_branch_evaluations")
        != embedded.get("projected_planning_compute_events")
        or type(plan.get("abstract_support_branch_evaluations")) is not int
        or plan.get("abstract_support_branch_evaluations") < 0
        or embedded.get("schema")
        != "acfqp.generic_partial_factor_receding_plan.v15"
        or embedded.get("candidate_id") != candidate["candidate_id"]
        or embedded.get("known_factor_target_columns") != targets
        or embedded.get("unknown_residual_target_columns")
        != candidate["unknown_residual_target_columns"]
        or embedded.get("terminal_projection_rule") != rules
        or embedded.get("rejected_accepting_projection_count") != 0
        or embedded.get("selected_support_feasible_depth") != len(actions)
        or embedded.get("action_keys") != actions
        or embedded.get("stochastic_support_branch_receding_semantics") is not True
        or embedded.get("robust_all_branches_completion_claimed") is not False
        or embedded.get("finite_worst_case_completion_claimed") is not False
        or embedded.get("ground_transition_accessed_during_abstract_search")
        is not False
        or embedded.get("complete_world_model_claimed") is not False
        or plan.get("initial_illegal_actions_forbidden_in_abstract_search")
        is not True
        or plan.get("ground_legality_used_only_after_existing_support_or_failed_certificate")
        is not True
        or plan.get("ground_transition_accessed_during_abstract_search") is not False
        or plan.get("query_local_exact_overlay_remains_only_safety_authority")
        is not True
        or plan.get("complete_ground_world_model_claimed") is not False
    ):
        _fail("V106 fallback plan integrity or boundary changed")
    payload = {
        key: value
        for key, value in plan.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    if plan.get("legality_conditioned_quotient_plan_id") != _hash(
        _PLAN_DOMAIN, payload
    ):
        _fail("V106 fallback plan identity changed")


def _receipt(
    document: Any,
    episode_index: int,
    expected_wrapper: Any,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V106 actual quotient receipt type changed")
    base = v103._receipt(document.get("base_execution_receipt"))
    wrapper = document.get("quotient_plan_receipt")
    if wrapper != expected_wrapper:
        _fail("V106 plan/execution wrapper join changed")
    plan = None if wrapper is None else wrapper.get("abstract_plan")
    if wrapper is not None and (
        type(wrapper) is not dict
        or wrapper.get("raw_state") != base["raw_state"]
        or type(plan) is not dict
        or plan.get("agreement_shield_receipt") != base["shield_receipt"]
        or plan.get("exact_legal_action_keys_at_initial_state")
        != base["legal_action_keys"]
    ):
        _fail("V106 plan/base receipt join changed")
    proposed = None if plan is None else plan["initial_action_key"]
    admitted = proposed in base["legal_action_keys"] if proposed is not None else False
    chosen = base["chosen_action_key"]
    match = admitted and chosen == proposed
    source = (
        "ACTUAL_LEGALITY_CONDITIONED_QUOTIENT_ORDER"
        if match
        else "EXACT_CERTIFICATE_FALLBACK_AFTER_LEGALITY_CONDITIONED_ORDER"
        if admitted
        else "EXACT_CERTIFICATE_ONLY_NO_QUOTIENT_ORDER"
    )
    payload = {
        "schema": "acfqp.generic_actual_legality_conditioned_execution_receipt.v106",
        "episode_index": episode_index,
        "decision_index": base["decision_index"],
        "raw_state": base["raw_state"],
        "chosen_action_key": chosen,
        "legal_action_keys": base["legal_action_keys"],
        "base_execution_receipt": base,
        "base_execution_receipt_id": base["execution_receipt_id"],
        "quotient_plan_receipt": wrapper,
        "quotient_graph_id": None if plan is None else plan["quotient_graph_id"],
        "quotient_plan_id": None
        if plan is None
        else plan["legality_conditioned_quotient_plan_id"],
        "quotient_proposed_action_key": proposed,
        "quotient_proposal_admitted_to_real_action_order": admitted,
        "chosen_action_matches_admitted_quotient_proposal": match,
        "actual_action_ordering_source": source,
        "legality_support_source": None
        if plan is None
        else plan["legality_support_source"],
        "legality_failure_index": None
        if plan is None
        else plan["legality_failure_index"],
        "exact_certificate_may_override_fallible_quotient_order": True,
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    expected = {
        **payload,
        "actual_legality_conditioned_execution_receipt_id": _hash(
            _RECEIPT_DOMAIN, payload
        ),
    }
    if document != expected:
        _fail("V106 actual quotient receipt semantics changed")
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int, int]:
    if type(episode) is not dict:
        _fail("V106 quotient episode type changed")
    v103._content_id(episode, "episode_id", _EPISODE_DOMAIN, _EPISODE_EXTRAS)
    if (
        episode.get("schema")
        != "acfqp.generic_legality_conditioned_certificate_episode.v106"
        or episode.get("family") != family
        or episode.get("seed") != seed
        or episode.get("episode_index") != episode_index
        or episode.get("arm")
        != "LEGALITY_CONDITIONED_OBSERVATION_QUOTIENT_ORDERING"
        or episode.get("target_candidate_id") != candidate["candidate_id"]
        or episode.get("preloaded_acquisition_ground_support_labels")
        != v105._group_count(rows)
        or episode.get("success") is not True
        or episode.get("abstract_model_used_only_for_action_ordering") is not True
        or episode.get("certified_legality_exposed_only_as_abstract_initial_action_constraint")
        is not True
        or episode.get("ground_transition_accessed_during_abstract_search")
        is not False
        or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or episode.get("model_or_alignment_used_as_safety_authority") is not False
        or episode.get("target_episode_outcomes_used_to_refit_model_or_alignment")
        is not False
        or episode.get("same_exact_engine_implementation_for_transfer_and_strict_arms")
        is not True
        or episode.get("complete_world_model_synthesized") is not False
        or episode.get("quotient_graph_before_episode") != model
    ):
        _fail("V106 quotient episode boundary changed")
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
    ):
        _fail("V106 certificate/distinction inventory changed")
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            type(failure) is not dict
            or type(distinction) is not dict
            or failure.get("failure_index") != index
            or distinction.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("ground_support_labels") != 1
        ):
            _fail("V106 certificate-first query discipline changed")
        if failure.get("failure_kind") == "MISSING_QUERY_LOCAL_LEGALITY_SUPPORT":
            if (
                failure.get("action_key") is not None
                or distinction.get("distinction_kind")
                != "QUERY_LOCAL_LEGAL_ACTION_SET"
                or distinction.get("raw_state") != failure.get("raw_state")
                or type(distinction.get("legal_action_keys")) is not list
                or distinction.get("raw_transition_rows") is not None
            ):
                _fail("V106 legality-only distinction changed")
        elif failure.get("failure_kind") == "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF":
            transition_rows = distinction.get("raw_transition_rows")
            if (
                type(failure.get("action_key")) is not int
                or distinction.get("distinction_kind")
                != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT"
                or distinction.get("raw_state") != failure.get("raw_state")
                or distinction.get("action_key") != failure.get("action_key")
                or type(transition_rows) is not list
                or not transition_rows
                or any(
                    v105._row(row)["pre_vector"] != failure.get("raw_state")
                    or row["selected_action"]["action_key"]
                    != failure.get("action_key")
                    for row in transition_rows
                )
            ):
                _fail("V106 transition distinction changed")
        else:
            _fail("V106 failure kind changed")
    wrappers = episode.get("abstract_plan_receipts")
    if type(wrappers) is not list:
        _fail("V106 quotient plan inventory changed")
    by_raw = {}
    verified_wrappers = []
    fallback_plan_count = 0
    for wrapper in wrappers:
        if type(wrapper) is not dict or set(wrapper) != {
            "raw_state",
            "abstract_plan",
        }:
            _fail("V106 quotient plan wrapper changed")
        raw = wrapper["raw_state"]
        plan = wrapper["abstract_plan"]
        if type(raw) is not list or tuple(raw) in by_raw or type(plan) is not dict:
            _fail("V106 quotient plan state inventory changed")
        exact_legal = tuple(plan.get("exact_legal_action_keys_at_initial_state", ()))
        if not exact_legal or any(type(key) is not int for key in exact_legal):
            _fail("V106 plan legality inventory changed")
        _verify_legality_provenance(
            raw,
            exact_legal,
            plan.get("legality_support_source"),
            plan.get("legality_failure_index"),
            rows,
            failures,
            distinctions,
        )
        shield = v103._shield(plan.get("agreement_shield_receipt"))
        if plan.get("planning_source") == "COMPILED_FACTOR_PROGRAM_FALLBACK":
            _validate_unreconstructable_fallback_plan(
                plan, model, candidate, rows, catalogue, exact_legal
            )
            expected_initial = plan.get("initial_action_key")
            fallback_plan_count += 1
        else:
            expected_plan = _expected_plan(
                model,
                candidate,
                rows,
                catalogue,
                raw,
                exact_legal,
                plan.get("planning_source", ""),
                plan.get("legality_support_source"),
                plan.get("legality_failure_index"),
            )
            expected_plan["agreement_shield_receipt"] = shield
            expected = {
                **expected_plan,
                "legality_conditioned_quotient_plan_id": _hash(
                    _PLAN_DOMAIN, expected_plan
                ),
            }
            if plan != expected:
                _fail("V106 quotient plan differs from independent replay")
            expected_initial = expected_plan["initial_action_key"]
        if (
            shield["abstract_proposal"] != [expected_initial]
            or shield["partial_proposal"] != [expected_initial]
            or shield["legal_action_keys"] != list(exact_legal)
        ):
            _fail("V106 plan shield/legality join changed")
        by_raw[tuple(raw)] = wrapper
        verified_wrappers.append(wrapper)
    bases = episode.get("abstract_execution_receipts")
    actions = episode.get("action_keys")
    actual = episode.get("actual_legality_conditioned_execution_receipts")
    if (
        type(bases) is not list
        or type(actions) is not list
        or type(actual) is not list
        or episode.get("execution_steps") != len(actions)
        or len(bases) != len(actions)
        or len(actual) != len(actions)
        or episode.get("every_execution_action_has_content_addressed_receipt")
        is not True
    ):
        _fail("V106 episode execution inventory changed")
    expected_actual = []
    for decision, (base_document, actual_document, key) in enumerate(
        zip(bases, actual, actions, strict=True)
    ):
        base = v103._receipt(base_document)
        if base["decision_index"] != decision or base["chosen_action_key"] != key:
            _fail("V106 base receipt/action join changed")
        expected_actual.append(
            _receipt(
                actual_document,
                episode_index,
                by_raw.get(tuple(base["raw_state"])),
            )
        )
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"]
        for row in expected_actual
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"]
        for row in expected_actual
    )
    local_legality = sum(
        row["legality_support_source"] in _LOCAL_LEGALITY_SOURCES
        for row in expected_actual
    )
    actual_fallback_count = sum(
        row["quotient_plan_receipt"] is not None
        and row["quotient_plan_receipt"]["abstract_plan"]["planning_source"]
        == "COMPILED_FACTOR_PROGRAM_FALLBACK"
        for row in expected_actual
    )
    if (
        episode.get("actual_legality_conditioned_execution_receipt_count")
        != len(expected_actual)
        or episode.get("quotient_proposal_admitted_execution_count") != admitted
        or episode.get("chosen_action_matches_admitted_quotient_proposal_count")
        != matches
        or episode.get("certificate_local_legality_plan_count") != local_legality
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
        or episode.get("execution_action_matches_abstract_proposal")
        != [
            row["chosen_action_matches_admitted_abstract_proposal"] for row in bases
        ]
        or episode.get("execution_action_matches_abstract_proposal_count")
        != sum(
            row["chosen_action_matches_admitted_abstract_proposal"] for row in bases
        )
    ):
        _fail("V106 quotient episode utilization changed")
    incremental = sum(row["ground_support_labels"] for row in distinctions)
    raw_incremental = [
        v105._row(row)
        for distinction in distinctions
        for row in distinction.get("raw_transition_rows", [])
    ]
    if (
        episode.get("incremental_certificate_local_ground_support_labels")
        != incremental
        or episode.get("new_certificate_labels_charged_this_episode") != incremental
        or episode.get("total_target_ground_support_labels")
        != v105._group_count(rows) + incremental
        or episode.get("raw_incremental_transition_rows") != raw_incremental
        or episode.get("all_incremental_ground_queries_followed_failed_certificates")
        is not True
        or episode.get("paid_certificate_labels_cumulative")
        != paid_before + incremental
    ):
        _fail("V106 episode local-label accounting changed")
    updated = v105._deduplicate([*rows, *raw_incremental])
    if episode.get("persistent_exact_support_group_count_after_episode") != v105._group_count(
        updated
    ):
        _fail("V106 persistent support count changed")
    return (
        expected_actual,
        updated,
        incremental,
        fallback_plan_count,
        actual_fallback_count,
    )


def _sequence(
    document: Any,
    acquisition: Mapping[str, Any],
    family: str,
    seed: int,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V106 quotient sequence type changed")
    _content(document, "sequence_id", _SEQUENCE_DOMAIN)
    episodes = document.get("episodes")
    final_rows = document.get("persistent_exact_overlay_rows")
    models = document.get("quotient_models_before_each_episode")
    if (
        document.get("schema")
        != "acfqp.generic_persistent_legality_conditioned_quotient_sequence.v106"
        or document.get("family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
        or document.get("partial_candidate_id")
        != acquisition["candidate"]["candidate_id"]
        or type(episodes) is not list
        or len(episodes) != len(EPISODES)
        or type(models) is not list
        or len(models) != len(EPISODES)
        or type(final_rows) is not list
        or document.get("certified_legality_reused_as_abstract_boundary_not_recharged")
        is not True
        or document.get("actual_engine_action_order_receipts_not_posthoc_policy_matches")
        is not True
        or document.get("query_local_exact_overlay_exclusively_discharges_safety")
        is not True
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("V106 quotient sequence boundary changed")
    final_rows = [v105._row(row) for row in final_rows]
    all_incremental = [
        v105._row(row)
        for episode in episodes
        for row in episode.get("raw_incremental_transition_rows", [])
    ]
    incremental_keys = {v105._row_key(row) for row in all_incremental}
    initial = [
        row for row in final_rows if v105._row_key(row) not in incremental_keys
    ]
    if len(initial) + len(incremental_keys) != len(final_rows):
        _fail("V106 initial/overlay row partition changed")
    candidate = v105._verify_acquisition(acquisition, initial, family, seed)
    catalogue = v105._catalogue(final_rows)
    rows = v105._deduplicate(initial)
    all_actual = []
    all_failures = []
    all_distinctions = []
    paid = 0
    fallback_plans = 0
    actual_fallback_receipts = 0
    for expected_index, episode, model in zip(
        EPISODES, episodes, models, strict=True
    ):
        expected_model = v105._expected_model(candidate, rows)
        if (
            model != expected_model
            or episode.get("quotient_graph_before_episode") != expected_model
        ):
            _fail("V106 quotient graph differs from observation replay")
        (
            actual,
            rows,
            incremental,
            episode_fallback_plans,
            episode_actual_fallback_receipts,
        ) = _episode(
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
        fallback_plans += episode_fallback_plans
        actual_fallback_receipts += episode_actual_fallback_receipts
        all_actual.extend(actual)
        all_failures.extend(episode["failed_certificates"])
        all_distinctions.extend(episode["local_distinctions"])
    if rows != final_rows:
        _fail("V106 final persistent overlay changed")
    steps = len(all_actual)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in all_actual
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in all_actual
    )
    local_legality = sum(
        row["legality_support_source"] in _LOCAL_LEGALITY_SOURCES
        for row in all_actual
    )
    if (
        document.get("all_actual_legality_conditioned_execution_receipts")
        != all_actual
        or document.get("actual_legality_conditioned_execution_receipt_count")
        != steps
        or document.get("execution_step_count") != steps
        or document.get("quotient_proposal_admitted_execution_count") != admitted
        or document.get("chosen_action_matches_admitted_quotient_proposal_count")
        != matches
        or document.get("certificate_local_legality_plan_count") != local_legality
        or document.get("quotient_proposal_admitted_strict_majority")
        != (2 * admitted > steps)
        or document.get("chosen_action_matches_admitted_quotient_proposal_strict_majority")
        != (2 * matches > steps)
        or document.get("initial_acquisition_ground_support_labels_paid_once")
        != acquisition["ground_support_labels"]
        or document.get("certificate_ground_support_labels_paid_once") != paid
        or document.get("lifetime_target_ground_support_labels")
        != acquisition["ground_support_labels"] + paid
        or document.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(final_rows)).hexdigest()
        or document.get("persistent_exact_support_group_count")
        != v105._group_count(final_rows)
        or document.get("all_failed_certificates") != all_failures
        or document.get("all_local_distinctions") != all_distinctions
        or document.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
        or document.get("quotient_graph_updates_only_from_certificate_local_overlay")
        is not True
    ):
        _fail("V106 sequence aggregate reconstruction changed")
    return {
        "execution_steps": steps,
        "admitted": admitted,
        "matches": matches,
        "local_legality": local_legality,
        "certificate_labels": paid,
        "initial_labels": acquisition["ground_support_labels"],
        "lifetime_labels": acquisition["ground_support_labels"] + paid,
        "planning_compute": sum(
            row["abstract_planning_compute_events"] for row in episodes
        ),
        "fallback_plan_receipt_count_without_complete_catalogue_closure": fallback_plans,
        "actual_execution_receipt_count_using_unreconstructable_fallback": actual_fallback_receipts,
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
        _fail("V106 direct sequence changed")
    episodes = document.get("episodes")
    if type(episodes) is not list or len(episodes) != len(EPISODES):
        _fail("V106 direct episode inventory changed")
    labels = 0
    for expected_index, episode in zip(EPISODES, episodes, strict=True):
        v103._content_id(
            episode, "episode_id", v103._DIRECT_EPISODE_DOMAIN
        )
        failures = episode.get("failed_certificates")
        distinctions = episode.get("local_distinctions")
        if (
            episode.get("schema")
            != "acfqp.generic_preloaded_certificate_receding_episode.v74"
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
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
            is not True
            or type(failures) is not list
            or type(distinctions) is not list
            or len(failures) != len(distinctions)
            or any(
                row.get("ground_query_performed_before_failure") is not False
                for row in failures
            )
            or any(
                row.get("query_after_failed_certificate") is not True
                for row in distinctions
            )
        ):
            _fail("V106 direct episode semantics changed")
        incremental = sum(row["ground_support_labels"] for row in distinctions)
        if (
            episode.get("incremental_certificate_local_ground_support_labels")
            != incremental
            or episode.get("total_target_ground_support_labels") != incremental
        ):
            _fail("V106 direct label accounting changed")
        labels += incremental
    if document.get("lifetime_target_ground_support_labels") != labels:
        _fail("V106 direct lifetime labels changed")
    return labels


def _utilization(sequence: Mapping[str, Any]) -> dict[str, Any]:
    receipts = sequence["all_actual_legality_conditioned_execution_receipts"]
    steps = len(receipts)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
    )
    local_legality = sum(
        row["legality_support_source"] in _LOCAL_LEGALITY_SOURCES
        for row in receipts
    )
    return {
        "schema": "acfqp.legality_conditioned_quotient_utilization.v106",
        "execution_receipt_count": steps,
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "certificate_local_legality_plan_count": local_legality,
        "quotient_proposal_admitted_fraction_numerator": admitted,
        "quotient_proposal_admitted_fraction_denominator": steps,
        "chosen_action_match_fraction_numerator": matches,
        "chosen_action_match_fraction_denominator": steps,
        "quotient_actually_orders_strict_majority_of_execution": 2 * admitted > steps,
        "quotient_actually_orders_at_least_three_quarters_of_execution": (
            4 * admitted >= 3 * steps
        ),
        "chosen_action_matches_quotient_strict_majority": 2 * matches > steps,
        "every_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "ordering_is_engine_input_not_posthoc_policy_match": True,
        "certified_legality_is_boundary_condition_not_transition_model": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def _occurrence(document: Any, family: str, seed: int) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V106 occurrence type changed")
    payload = {key: value for key, value in document.items() if key != "occurrence_id"}
    if (
        document.get("occurrence_id")
        != domains.extension_content_id_v106(
            domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_OCCURRENCE_V106_DOMAIN,
            payload,
        )
        or document.get("schema")
        != "acfqp.legality_conditioned_quotient_occurrence.v106"
        or document.get("target_family") != family
        or document.get("seed") != seed
        or document.get("episode_indices") != list(EPISODES)
    ):
        _fail("V106 occurrence identity changed")
    sequence_document = document.get(
        "persistent_legality_conditioned_quotient_sequence"
    )
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
        "every_action_independently_receipted": utilization[
            "every_action_independently_receipted"
        ],
        "quotient_model_actually_orders_strict_majority": utilization[
            "quotient_actually_orders_strict_majority_of_execution"
        ],
        "quotient_model_actually_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_local_legality_enters_abstract_planning": sequence[
            "local_legality"
        ]
        > 0,
        "ordering_is_engine_input_not_posthoc_match": utilization[
            "ordering_is_engine_input_not_posthoc_policy_match"
        ],
        "certificate_failure_only_query_discipline_clean": sequence_document[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": sequence[
            "later_zero_label_reuse"
        ],
        "quotient_lifetime_labels_strictly_below_cold_direct": sequence[
            "lifetime_labels"
        ]
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    if (
        document.get("legality_conditioned_quotient_utilization") != utilization
        or document.get("accounting") != accounting
        or document.get("registered_gate") != gate
        or document.get("legality_conditioned_quotient_primary_ordering_verified")
        != gate["passed"]
        or document.get("local_ground_distinctions_only_after_certificate_failure_verified")
        != gate["passed"]
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V106 occurrence Gate or claim boundary changed")
    return {
        "target_family": family,
        "seed": seed,
        "execution_steps": sequence["execution_steps"],
        "quotient_proposal_admitted_execution_count": sequence["admitted"],
        "chosen_action_matches_admitted_quotient_proposal_count": sequence[
            "matches"
        ],
        "certificate_local_legality_plan_count": sequence["local_legality"],
        "initial_acquisition_labels": sequence["initial_labels"],
        "certificate_local_labels": sequence["certificate_labels"],
        "quotient_lifetime_target_labels": sequence["lifetime_labels"],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction": direct_labels - sequence["lifetime_labels"],
        "abstract_planning_compute_events": sequence["planning_compute"],
        "fallback_plan_receipt_count_without_complete_catalogue_closure": sequence[
            "fallback_plan_receipt_count_without_complete_catalogue_closure"
        ],
        "actual_execution_receipt_count_using_unreconstructable_fallback": sequence[
            "actual_execution_receipt_count_using_unreconstructable_fallback"
        ],
        "gate_passed": gate["passed"],
    }


def verify_legality_conditioned_quotient_campaign_bytes_v106(
    raw: bytes,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V106 campaign bytes changed")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V106 campaign is noncanonical")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    rows = document.get("target_occurrences")
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("campaign_id")
        != domains.extension_content_id_v106(
            domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_CAMPAIGN_V106_DOMAIN,
            payload,
        )
        or document.get("schema")
        != "acfqp.legality_conditioned_quotient_campaign.v106"
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v105_campaign_id") != V105_CAMPAIGN_ID
        or document.get("v105_verification_id") != V105_VERIFICATION_ID
        or type(rows) is not list
        or len(rows) != len(TARGETS)
    ):
        _fail("V106 campaign inventory changed")
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
            "certificate_local_legality_plan_count",
        )
    }
    fallback_gap_count = sum(
        row["fallback_plan_receipt_count_without_complete_catalogue_closure"]
        for row in replay
    )
    actual_fallback_gap_count = sum(
        row["actual_execution_receipt_count_using_unreconstructable_fallback"]
        for row in replay
    )
    expected_accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    ood = v105._ood(document.get("incompatible_schema_no_transfer_control"))
    passed = (
        all(row["gate_passed"] for row in replay)
        and 2 * totals["quotient_proposal_admitted_execution_count"]
        > totals["execution_steps"]
        and 2 * totals["chosen_action_matches_admitted_quotient_proposal_count"]
        > totals["execution_steps"]
        and totals["certificate_local_legality_plan_count"] > 0
        and totals["quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": 4,
        "passed_target_occurrence_count": sum(
            row["gate_passed"] for row in replay
        ),
        "every_occurrence_actual_quotient_ordering_strict_majority": all(
            2 * row["quotient_proposal_admitted_execution_count"]
            > row["execution_steps"]
            for row in replay
        ),
        "every_occurrence_actual_quotient_ordering_at_least_three_quarters": all(
            4 * row["quotient_proposal_admitted_execution_count"]
            >= 3 * row["execution_steps"]
            for row in replay
        ),
        "every_occurrence_chosen_action_match_strict_majority": all(
            2 * row["chosen_action_matches_admitted_quotient_proposal_count"]
            > row["execution_steps"]
            for row in replay
        ),
        "every_occurrence_uses_certificate_local_legality_in_abstract_planning": all(
            row["certificate_local_legality_plan_count"] > 0 for row in replay
        ),
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": passed,
    }
    if (
        document.get("accounting") != expected_accounting
        or document.get("registered_gate") != gate
        or document.get("registered_execution_primarily_ordered_by_legality_conditioned_quotient")
        != passed
        or document.get("ground_distinctions_acquired_only_after_certificate_failure_verified")
        != passed
        or document.get("actual_engine_ordering_not_posthoc_receipt_reclassification")
        is not True
        or document.get("global_lumpability_claimed") is not False
        or document.get("complete_ground_world_model_synthesized") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V106 campaign Gate or claim boundary changed")
    return {
        "schema": "acfqp.legality_conditioned_quotient_verification.v106",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_V106_PER_OCCURRENCE_LOCAL_LEGALITY_GATE_FAILED",
        "producer_free_observation_graph_reconstruction": True,
        "producer_free_observation_graph_plan_reconstruction": True,
        "producer_free_fallback_plan_reconstruction": False,
        "fallback_plan_receipt_count_without_complete_catalogue_closure": fallback_gap_count,
        "actual_execution_receipt_count_using_unreconstructable_fallback": actual_fallback_gap_count,
        "producer_summary_counts_not_used": True,
        "verified_occurrences": replay,
        "verified_accounting": expected_accounting,
        "registered_gate_independently_verified": False,
        "registered_failure_reason": "TWO_MAINTENANCE_OCCURRENCES_REQUIRED_NO_CERTIFICATE_LOCAL_LEGALITY_PLAN",
        "all_execution_steps_still_ordered_by_legality_conditioned_quotient": (
            totals["quotient_proposal_admitted_execution_count"]
            == totals["execution_steps"]
        ),
        "aggregate_sample_tax_reduction_still_observed": totals[
            "quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "fresh_successor_required": True,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def freeze_legality_conditioned_quotient_verification_v106(raw: bytes) -> bytes:
    payload = verify_legality_conditioned_quotient_campaign_bytes_v106(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v106(
            domains.CONSTRUCTION_K7_LEGALITY_CONDITIONED_QUOTIENT_VERIFICATION_V106_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V106 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_legality_conditioned_quotient_verification_v106",
    "verify_legality_conditioned_quotient_campaign_bytes_v106",
)
