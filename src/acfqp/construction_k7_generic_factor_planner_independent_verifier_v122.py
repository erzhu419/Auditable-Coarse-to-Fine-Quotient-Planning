"""Producer-free verifier for the registered V122 generic planner campaign."""

from __future__ import annotations

import hashlib
from itertools import product
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.construction_k7_generic_subprogram_independent_verifier_v121r1 import (
    freeze_generic_subprogram_verification_v121r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "a958bef4dfdc141f010e7ee7a93e27f84a9db36c5f630a3ebc656937733a6421"
CAMPAIGN_BYTE_COUNT = 4_139_139
CAMPAIGN_SHA256 = "1a71026284a5fe00a252bfa4a146315aaf4c229ea3dff5a954da8157a2042d0f"
PREREGISTRATION_ID = "37ad2738275cad9469c815c383f9951337697f619128581b6403424208fa5c88"
V121R1_CAMPAIGN_ID = "0369d6ea8811a6af926599a8667c589ab22b317a57e6d4f9e2b8ab23542ca00d"
V121R1_VERIFICATION_ID = "8568d810d9c61ad1b0dc96f4d84195ca7148e2208986202cd7800bf97fa4afc9"
ARTIFACT_FACTOR_LIBRARY_ID = "352084adc6c9dec68cb5b63976acb170aa4e02ed5004c89ebe8cd22d08e6b68a"
EXPECTED_SEEDS = (1_035_101, 1_035_102)
EXPECTED_EPISODES = (281, 282, 283)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64

_DOMAINS = {
    "campaign": "acfqp:construction-k7-generic-factor-planner-campaign:v122",
    "occurrence": "acfqp:construction-k7-generic-factor-planner-occurrence:v122",
    "sequence": "acfqp:construction-k7-generic-factor-planner-sequence:v122",
    "verification": "acfqp:construction-k7-generic-factor-planner-verification:v122",
    "acquisition": "acfqp:construction-k7-generic-artifact-subprogram-partial-acquisition:v121",
    "strict": "acfqp:construction-k7-generic-artifact-subprogram-strict-control:v121",
    "v119_sequence": "acfqp:construction-k7-source-unseen-residual-genesis-authorized-branch-sequence:v119",
    "v113_sequence": "acfqp:construction-k7-incremental-abstract-successor-sequence:v113",
    "v105_model": "acfqp:generic-observation-quotient-graph:v105",
    "v106_plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
}


class ConstructionK7GenericFactorPlannerIndependentVerifierV122Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericFactorPlannerIndependentVerifierV122Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V122 {key} changed")


class _Support(tuple):
    pass


def _evaluate(expression: Any, state: Mapping[int, int], action: tuple[int, ...]) -> Any:
    if type(expression) in {int, bool}:
        return expression
    _require(type(expression) is list and bool(expression), "V122 expression shape changed")
    opcode = expression[0]
    if opcode == "E00":
        _require(len(expression) == 2 and expression[1] in state, "V122 state atom changed")
        return state[expression[1]]
    if opcode == "E01":
        _require(
            len(expression) == 2 and type(expression[1]) is int and expression[1] in range(len(action)),
            "V122 action atom changed",
        )
        return action[expression[1]]
    values = [_evaluate(item, state, action) for item in expression[1:]]
    _require(not any(type(value) is _Support for value in values), "V122 nested support changed")
    if opcode == "E05" and len(values) == 2:
        return int(values[0]) + int(values[1])
    if opcode == "E06" and len(values) == 2:
        _require(int(values[1]) != 0, "V122 zero modulo changed")
        return int(values[0]) % int(values[1])
    if opcode == "E07" and len(values) == 2:
        return _Support(sorted({int(values[0]), int(values[1])}))
    if opcode == "E08" and len(values) == 2:
        return values[0] == values[1]
    if opcode == "E09" and len(values) == 2:
        return int(values[0]) > int(values[1])
    if opcode == "E10" and len(values) == 2:
        return bool(values[0]) and bool(values[1])
    if opcode == "E11" and len(values) == 1:
        return not bool(values[0])
    if opcode == "E12" and len(values) == 3:
        return int(values[1]) if bool(values[0]) else int(values[2])
    if opcode == "E13" and len(values) == 2:
        return int(values[0]) | int(values[1])
    _fail("V122 expression opcode or arity changed")


def _successors(
    assignments: Sequence[Mapping[str, Any]],
    projected_state: tuple[int, ...],
    action: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    targets = tuple(row["target_column"] for row in assignments)
    _require(len(targets) == len(set(targets)) == len(projected_state), "V122 target inventory changed")
    state = dict(zip(targets, projected_state, strict=True))
    supports = []
    for assignment in assignments:
        _require(
            set(assignment["state_dependencies"]).issubset(targets),
            "V122 expression escaped projected-state closure",
        )
        value = _evaluate(assignment["expression"], state, action)
        if type(value) is _Support:
            support = tuple(value)
        else:
            _require(type(value) is int, "V122 assignment output type changed")
            support = (value,)
        supports.append(support)
    return tuple(sorted(set(product(*supports))))


def _terminal_rules(
    assignments: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    terminal_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    accepting = [
        tuple(row["projected_state"])
        for row in terminal_rows
        if "ACCEPT" in row["observed_terminal_classes"]
    ]
    _require(bool(accepting) and bool(edges), "V122 terminal evidence changed")
    result = []
    for offset, assignment in enumerate(assignments):
        target = assignment["target_column"]
        values = tuple(sorted({state[offset] for state in accepting}))
        if target not in assignment["state_dependencies"]:
            rule = {"kind": "UNCONSTRAINED"}
        else:
            deltas = tuple(
                row["projected_post"][offset] - row["projected_pre"][offset]
                for row in edges
            )
            if all(delta == 0 for delta in deltas):
                rule = (
                    {"kind": "EQUAL", "value": values[0]}
                    if len(values) == 1
                    else {"kind": "UNCONSTRAINED"}
                )
            elif all(delta >= 0 for delta in deltas):
                rule = {"kind": "AT_LEAST", "value": min(values)}
            elif all(delta <= 0 for delta in deltas):
                rule = {"kind": "AT_MOST", "value": max(values)}
            else:
                rule = {"kind": "OBSERVED_SET", "values": list(values)}
        result.append({"target_column": target, **rule})
    return tuple(result)


def _terminal_match(state: tuple[int, ...], rules: Sequence[Mapping[str, Any]]) -> bool:
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


def _initial_projected(
    raw_state: Sequence[int], layout: Mapping[str, Any], assignments: Sequence[Mapping[str, Any]]
) -> tuple[int, ...]:
    canonical = tuple(raw_state[index] for index in layout["state_canonical_to_raw"])
    return tuple(canonical[row["target_column"]] for row in assignments)


def _verify_program_path(
    plan: Mapping[str, Any],
    raw_state: Sequence[int],
    layout: Mapping[str, Any],
    assignments: Sequence[Mapping[str, Any]],
    actions: Mapping[int, tuple[int, ...]],
    rules: tuple[Mapping[str, Any], ...],
) -> int:
    path = plan["projected_action_path"]
    _require(
        type(path) is list
        and bool(path)
        and path == plan["embedded_projected_plan"]["action_keys"]
        and path[0] in plan["exact_legal_action_keys_at_initial_state"],
        "V122 generic action path changed",
    )
    reachable = {_initial_projected(raw_state, layout, assignments)}
    checks = 0
    for key in path:
        _require(key in actions, "V122 plan action escaped canonical catalogue")
        next_states = set()
        for state in reachable:
            support = _successors(assignments, state, actions[key])
            checks += len(support)
            next_states.update(support)
        _require(bool(next_states), "V122 generic path has empty successor support")
        reachable = next_states
    _require(any(_terminal_match(state, rules) for state in reachable), "V122 generic path cannot reach terminal support")
    return checks


def _verify_graph_path(
    plan: Mapping[str, Any],
    raw_state: Sequence[int],
    layout: Mapping[str, Any],
    assignments: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any],
    rules: tuple[Mapping[str, Any], ...],
) -> int:
    path = plan["projected_action_path"]
    _require(path[0] in plan["exact_legal_action_keys_at_initial_state"], "V122 graph initial legality changed")
    reachable = {_initial_projected(raw_state, layout, assignments)}
    edges = {}
    for row in model["projected_edge_rows"]:
        edges.setdefault((tuple(row["projected_pre"]), row["action_key"]), set()).add(
            tuple(row["projected_post"])
        )
    checks = 0
    for key in path:
        next_states = set()
        for state in reachable:
            rows = edges.get((state, key), set())
            checks += len(rows)
            next_states.update(rows)
        _require(bool(next_states), "V122 observation-graph path changed")
        reachable = next_states
    _require(any(_terminal_match(state, rules) for state in reachable), "V122 graph path misses terminal")
    return checks


def _verify_occurrence(row: Mapping[str, Any]) -> dict[str, Any]:
    _require(row.get("schema") == "acfqp.generic_factor_planner_occurrence.v122", "V122 occurrence schema changed")
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    acquisition = row["partial_prior_acquisition"]
    strict = row["strict_no_prior_complete_model_control"]
    _verify_id(acquisition, "acquisition_id", _DOMAINS["acquisition"])
    _verify_id(strict, "strict_control_id", _DOMAINS["strict"])
    candidate = acquisition["candidate"]
    _verify_id(candidate, "candidate_id", _DOMAINS["acquisition"])
    _require(
        acquisition["raw_transition_sha256"] == strict["raw_transition_sha256"]
        and acquisition["ground_support_labels"] == strict["ground_support_labels"]
        and bool(candidate["unknown_residual_target_columns"]),
        "V122 acquisition/control join changed",
    )
    sequence = row["generic_factor_planner_sequence"]
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    v119 = sequence["generic_planner_base_sequence"]
    _verify_id(v119, "sequence_id", _DOMAINS["v119_sequence"])
    base = v119["genesis_authorized_base_sequence"]
    _verify_id(base, "sequence_id", _DOMAINS["v113_sequence"])
    _require(
        sequence["generic_planner_base_sequence_id"] == v119["sequence_id"]
        and v119["genesis_authorized_base_sequence_id"] == base["sequence_id"]
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and v119["partial_candidate_id"] == candidate["candidate_id"]
        and base["partial_candidate_id"] == candidate["candidate_id"],
        "V122 sequence/candidate join changed",
    )
    assignments = candidate["compiled_factor_assignments"]
    receipt = v119["program_branch_dependency_receipt"]
    _require(
        receipt["compiled_factor_assignments"] == assignments
        and receipt["partial_candidate_id"] == candidate["candidate_id"],
        "V122 program dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in receipt["canonical_action_catalogue"]
    }
    models = [*base["quotient_models_before_each_episode"], *base["quotient_models_after_each_episode"]]
    model_by_id = {}
    edge_checks = rule_checks = 0
    for model in models:
        _verify_id(model, "quotient_graph_id", _DOMAINS["v105_model"])
        model_by_id[model["quotient_graph_id"]] = model
    for model in model_by_id.values():
        rules = _terminal_rules(assignments, model["projected_edge_rows"], model["projected_terminal_rows"])
        rule_checks += len(rules)
        for edge in model["projected_edge_rows"]:
            support = _successors(
                assignments,
                tuple(edge["projected_pre"]),
                actions[edge["action_key"]],
            )
            edge_checks += len(support)
            _require(tuple(edge["projected_post"]) in support, "V122 model edge escaped generic program")
    direct = memoized = path_checks = 0
    all_plans = []
    for episode in base["episodes"]:
        _require(
            episode["success"] is True
            and episode["planner_raw_transition_argument_present"] is False
            and episode["all_incremental_ground_queries_followed_failed_certificates"] is True,
            "V122 episode/certificate discipline changed",
        )
        for plan_receipt in episode["abstract_plan_receipts"]:
            plan = plan_receipt["abstract_plan"]
            all_plans.append(plan)
            if plan["planning_source"] in {
                "OBSERVATION_QUOTIENT_GRAPH",
                "COMPILED_FACTOR_PROGRAM_FALLBACK",
            }:
                _verify_id(plan, "legality_conditioned_quotient_plan_id", _DOMAINS["v106_plan"])
                model = model_by_id[plan["quotient_graph_id"]]
                rules = _terminal_rules(
                    assignments, model["projected_edge_rows"], model["projected_terminal_rows"]
                )
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"]) == rules,
                    "V122 plan terminal rules changed",
                )
                if plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["generic_factor_program_execution_adapter_used"] is True
                        and plan["legacy_shape_specific_planner_execution_adapter_called"] is False
                        and plan["embedded_projected_plan"]["generic_planner_execution_adapter_verified"] is True
                        and plan["embedded_projected_plan"]["hand_written_expression_shape_case_count"] == 0,
                        "V122 direct generic planner claim changed",
                    )
                    path_checks += _verify_program_path(
                        plan,
                        plan_receipt["raw_state"],
                        candidate["layout"],
                        assignments,
                        actions,
                        rules,
                    )
                else:
                    path_checks += _verify_graph_path(
                        plan,
                        plan_receipt["raw_state"],
                        candidate["layout"],
                        assignments,
                        model,
                        rules,
                    )
            elif plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED":
                memoized += 1
                source = plan["source_compiled_factor_program_plan"]
                _require(
                    source["legacy_shape_specific_planner_execution_adapter_called"] is False
                    and source["generic_terminal_rules_equal_retained_matched_compiler"] is True,
                    "V122 memoized generic source changed",
                )
    execution = sequence["generic_execution_verification"]
    _require(
        execution
        == {
            "distinct_compiled_model_count": len(model_by_id),
            "generic_projected_edge_support_checks": edge_checks,
            "generic_terminal_rule_checks": rule_checks,
            "direct_generic_factor_program_plan_count": direct,
            "memoized_generic_planner_source_count": memoized,
            "every_compiled_model_edge_replayed_by_generic_interpreter": True,
            "every_direct_program_fallback_used_generic_adapter": True,
            "every_memoized_plan_descends_from_v122_generic_planner_source": True,
            "legacy_shape_specific_planner_execution_adapter_called": False,
        },
        "V122 generic execution summary changed",
    )
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": v119["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": v119["matched_uncached_abstract_planning_compute_events"],
        "planning_compute_events_avoided_against_uncached": v119["planning_compute_events_avoided_against_uncached"],
        "dependency_derivation_compute_events": v119["dependency_derivation_compute_events"],
        "same_epoch_genesis_authorized_cache_hits": v119["same_epoch_genesis_authorized_cache_hit_count"],
        "program_branch_cache_hits": v119["program_branch_cache_hit_count"],
        "generic_binding_candidate_evaluations": sum(
            item.get("exact_template_binding_count", 0)
            for item in candidate["binding_ambiguity_inventory"]
        ),
        "generic_projected_edge_support_checks": edge_checks,
        "generic_terminal_rule_checks": rule_checks,
        "direct_generic_factor_program_plans": direct,
        "memoized_generic_planner_sources": memoized,
        "sample_labels_execution_steps_binding_derivation_planning_dependency_and_generic_execution_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    _require(row["accounting"] == accounting, "V122 occurrence accounting changed")
    gate = row["registered_gate"]
    _require(
        gate["passed"] is True
        and all(value is True for key, value in gate.items() if key != "passed")
        and row["generic_planner_execution_adapter_verified"] is True
        and row["legacy_shape_specific_planner_execution_adapter_present"] is False
        and row["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V122 occurrence Gate or claim lock changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "seed": row["seed"],
        "episode_count": len(base["episodes"]),
        "generic_program_path_support_checks": path_checks,
        "accounting": accounting,
    }


def freeze_generic_factor_planner_verification_v122(
    campaign_raw: bytes,
    v121r1_campaign_raw: bytes,
    v121_failed_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    try:
        campaign = loads_canonical_json(campaign_raw)
    except Exception as exc:
        _fail(f"V122 campaign bytes are unreadable: {exc}")
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V122 frozen campaign identity or bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    _require(
        freeze_generic_subprogram_verification_v121r1(
            v121r1_campaign_raw, v121_failed_campaign_raw, dict(source_campaign_bytes)
        )
        == v121r1_verification_raw,
        "V122 predecessor producer-free verification changed",
    )
    predecessor_verification = loads_canonical_json(v121r1_verification_raw)
    _require(
        predecessor_verification["verification_id"] == V121R1_VERIFICATION_ID
        and campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v121r1_success_campaign_id"] == V121R1_CAMPAIGN_ID
        and campaign["v121r1_success_verification_id"] == V121R1_VERIFICATION_ID
        and campaign["artifact_factor_library_id"] == ARTIFACT_FACTOR_LIBRARY_ID,
        "V122 predecessor/content join changed",
    )
    rows = tuple(_verify_occurrence(row) for row in campaign["target_occurrences"])
    _require(
        tuple(row["seed"] for row in rows) == EXPECTED_SEEDS
        and all(row["episode_count"] == len(EXPECTED_EPISODES) for row in rows)
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V122 registered occurrence identity changed",
    )
    numeric_keys = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    expected_accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric_keys
    }
    expected_accounting.update(
        same_epoch_genesis_authorized_cache_hits_are_diagnostic_not_gate=True,
        sample_labels_execution_steps_binding_derivation_planning_dependency_and_generic_execution_checks_separate=True,
        sample_efficiency_improvement_claimed=False,
        scalar_cost_aggregation_performed=False,
    )
    _require(
        campaign["accounting"] == expected_accounting
        and campaign["registered_gate"]["passed"] is True
        and campaign["registered_gate"]["passed_target_occurrence_count"] == 2
        and campaign["generic_planner_execution_adapter_verified"] is True
        and campaign["legacy_shape_specific_planner_execution_adapter_present"] is False
        and campaign["sample_efficiency_improvement_claimed"] is False
        and campaign["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["global_exact_dynamics_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V122 campaign accounting, Gate, or claim lock changed",
    )
    payload = {
        "schema": "acfqp.generic_factor_planner_verification.v122",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v121r1_predecessor_verification_id": V121R1_VERIFICATION_ID,
        "artifact_factor_library_id": ARTIFACT_FACTOR_LIBRARY_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": expected_accounting,
        "producer_free_expression_successor_reconstruction": True,
        "producer_free_terminal_rule_reconstruction": True,
        "producer_free_program_and_graph_path_reachability_reconstruction": True,
        "producer_free_content_graph_reconstruction": True,
        "registered_gate_independently_verified": True,
        "legacy_shape_specific_model_builder_retained_as_matched_control": True,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "generic_planner_execution_adapter_verified": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": _content_id(_DOMAINS["verification"], payload),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V122 frozen independent verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_generic_factor_planner_verification_v122",
)
