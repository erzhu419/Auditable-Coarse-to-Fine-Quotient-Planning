"""Producer-free reconstruction of the frozen V123r1 campaign."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from itertools import product
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.construction_k7_generic_factor_planner_independent_verifier_v122 import (
    freeze_generic_factor_planner_verification_v122,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "b4267d948212555a86350f51b85f97dc6333a2f58e97836c9f8554fb775e8199"
CAMPAIGN_BYTE_COUNT = 5_620_455
CAMPAIGN_SHA256 = "487ae03a3702cf5f1f93d916e4e076f73eab43faa1fdf8bb10e6c94c27038a0b"
PREREGISTRATION_ID = "f588553d3113543de67d365c2fc743b7bb09ec5d70110deb906d480bb0f62991"
FAILED_V123_PREREGISTRATION_ID = "abf11379f9075d225b0a0233d3f8d7fea7d57e26c7c2eaf0b9b0a8a1686d505d"
FAILED_V123_RECORD_SHA256 = "84f32d6ed71ac0b4496d457662d5f750dacb9e77e37a51a17d6db6b6939b778e"
V122_CAMPAIGN_ID = "a958bef4dfdc141f010e7ee7a93e27f84a9db36c5f630a3ebc656937733a6421"
V122_VERIFICATION_ID = "3109127e80a90c8b77a34e387d31ff952abbdca76500bf33fc0c32b70285f3b1"
EXPECTED_SEEDS = (1_037_101, 1_037_102)
EXPECTED_EPISODES = (287, 288, 289)
VERIFICATION_ID = "def4bc52c8d3256d1627b62199d2868e5ff322726b89719631ed5ea1ed5a5d97"
EXPECTED_CANONICAL_BYTE_COUNT = 4_472
EXPECTED_CANONICAL_SHA256 = "2e6f8fb0413d96250bc1bad4490cc19823ca5c74aa3eca02765cc968ed6de7e4"


_DOMAINS = {
    "campaign": "acfqp:construction-k7-generic-quotient-compiler-campaign:v123r1",
    "occurrence": "acfqp:construction-k7-generic-quotient-compiler-occurrence:v123r1",
    "sequence": "acfqp:construction-k7-generic-quotient-compiler-sequence:v123",
    "verification": "acfqp:construction-k7-generic-quotient-compiler-verification:v123r1",
    "acquisition": "acfqp:construction-k7-generic-artifact-subprogram-partial-acquisition:v121",
    "strict": "acfqp:construction-k7-generic-artifact-subprogram-strict-control:v121",
    "v119_sequence": "acfqp:construction-k7-source-unseen-residual-genesis-authorized-branch-sequence:v119",
    "v113_sequence": "acfqp:construction-k7-incremental-abstract-successor-sequence:v113",
    "model": "acfqp:generic-observation-quotient-graph:v105",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
}


class ConstructionK7GenericQuotientCompilerIndependentVerifierV123r1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericQuotientCompilerIndependentVerifierV123r1Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V123r1 {key} changed")


class _Support(tuple):
    pass


def _evaluate(expression: Any, state: Mapping[int, int], action: tuple[int, ...]) -> Any:
    if type(expression) in {int, bool}:
        return expression
    _require(type(expression) is list and bool(expression), "V123r1 expression shape changed")
    opcode = expression[0]
    if opcode == "E00":
        _require(len(expression) == 2 and expression[1] in state, "V123r1 state atom changed")
        return state[expression[1]]
    if opcode == "E01":
        _require(
            len(expression) == 2
            and type(expression[1]) is int
            and expression[1] in range(len(action)),
            "V123r1 action atom changed",
        )
        return action[expression[1]]
    values = [_evaluate(item, state, action) for item in expression[1:]]
    _require(not any(type(value) is _Support for value in values), "V123r1 nested support changed")
    if opcode == "E05" and len(values) == 2:
        return int(values[0]) + int(values[1])
    if opcode == "E06" and len(values) == 2:
        _require(int(values[1]) != 0, "V123r1 zero modulo changed")
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
    _fail("V123r1 expression opcode or arity changed")


def _successors(
    assignments: Sequence[Mapping[str, Any]],
    projected_state: tuple[int, ...],
    action: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    targets = tuple(row["target_column"] for row in assignments)
    _require(len(targets) == len(set(targets)) == len(projected_state), "V123r1 target inventory changed")
    state = dict(zip(targets, projected_state, strict=True))
    supports = []
    for assignment in assignments:
        _require(
            set(assignment["state_dependencies"]).issubset(targets),
            "V123r1 expression escaped projected closure",
        )
        value = _evaluate(assignment["expression"], state, action)
        if type(value) is _Support:
            support = tuple(value)
        else:
            _require(type(value) is int, "V123r1 assignment type changed")
            support = (value,)
        supports.append(support)
    return tuple(sorted(set(product(*supports))))


def _affine_forms(expression: Any):
    if type(expression) is bool:
        return None
    if type(expression) is int:
        return frozenset(((expression, (), ()),))
    opcode = expression[0]
    if opcode == "E00":
        return frozenset(((0, ((expression[1], 1),), ()),))
    if opcode == "E01":
        return frozenset(((0, (), ((expression[1], 1),)),))
    if opcode == "E05":
        left, right = _affine_forms(expression[1]), _affine_forms(expression[2])
        if left is None or right is None:
            return None

        def add(left_rows, right_rows):
            result = dict(left_rows)
            for key, value in right_rows:
                result[key] = result.get(key, 0) + value
            return tuple(sorted((key, value) for key, value in result.items() if value))

        return frozenset(
            (lc + rc, add(ls, rs), add(la, ra))
            for lc, ls, la in left
            for rc, rs, ra in right
        )
    if opcode == "E07":
        left, right = _affine_forms(expression[1]), _affine_forms(expression[2])
        return None if left is None or right is None else left | right
    return None


def _terminal_rules(
    assignments: Sequence[Mapping[str, Any]],
    accepting: Mapping[int, set[int]],
    actions: Mapping[int, tuple[int, ...]],
) -> tuple[dict[str, Any], ...]:
    rules = []
    for assignment in assignments:
        target = assignment["target_column"]
        values = tuple(sorted(accepting.get(target, set())))
        _require(bool(values), "V123r1 accepting projection changed")
        forms = _affine_forms(assignment["expression"])
        deltas = None
        if forms is not None and all(state == ((target, 1),) for _c, state, _a in forms):
            deltas = tuple(
                sorted(
                    {
                        constant
                        + sum(coeff * action[field] for field, coeff in action_terms)
                        for constant, _state, action_terms in forms
                        for action in actions.values()
                    }
                )
            )
        if target not in assignment["state_dependencies"] or deltas is None:
            rule = {"kind": "UNCONSTRAINED"}
        elif all(delta == 0 for delta in deltas):
            rule = {"kind": "EQUAL", "value": values[0]} if len(values) == 1 else {"kind": "UNCONSTRAINED"}
        elif all(delta >= 0 for delta in deltas):
            rule = {"kind": "AT_LEAST", "value": min(values)}
        elif all(delta <= 0 for delta in deltas):
            rule = {"kind": "AT_MOST", "value": max(values)}
        else:
            rule = {"kind": "OBSERVED_SET", "values": list(values)}
        rules.append({"target_column": target, **rule})
    return tuple(rules)


def _raw_key(row: Mapping[str, Any]) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    return (
        tuple(row["pre_vector"]),
        row["selected_action"]["action_key"],
        tuple(row["post_vector"]),
    )


def _compile_model(
    rows: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    actions: Mapping[int, tuple[int, ...]],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    unique = {_raw_key(row): row for row in rows}
    raw_rows = [unique[key] for key in sorted(unique)]
    layout = candidate["layout"]
    state_order = layout["state_canonical_to_raw"]
    action_order = layout["action_canonical_to_raw"]
    assignments = candidate["compiled_factor_assignments"]
    targets = tuple(row["target_column"] for row in assignments)
    edges = set()
    terminal = defaultdict(set)
    contexts = set()
    accepting = defaultdict(set)
    checks = 0
    for row in raw_rows:
        selected = row["selected_action"]
        canonical_action = tuple(selected["anonymous_fields"][index] for index in action_order)
        key = selected["action_key"]
        _require(actions.get(key) == canonical_action, "V123r1 raw/catalogue action join changed")
        pre_full = tuple(row["pre_vector"][index] for index in state_order)
        post_full = tuple(row["post_vector"][index] for index in state_order)
        pre = tuple(pre_full[index] for index in targets)
        post = tuple(post_full[index] for index in targets)
        support = _successors(assignments, pre, canonical_action)
        checks += len(support)
        _require(post in support, "V123r1 raw edge escaped compiled program")
        edges.add((pre, key, post))
        terminal_class = (
            "ACTIVE"
            if row["legal_action_keys_after"]
            else "ACCEPT"
            if row["terminal_acceptance_after"] is True
            else "REJECT"
        )
        terminal[post].add(terminal_class)
        contexts.add((tuple(row["pre_vector"]), key))
        if row["terminal_acceptance_after"] is True:
            for target in targets:
                accepting[target].add(post_full[target])
    edge_rows = [
        {"projected_pre": list(pre), "action_key": key, "projected_post": list(post)}
        for pre, key, post in sorted(edges)
    ]
    terminal_rows = [
        {"projected_state": list(state), "observed_terminal_classes": sorted(classes)}
        for state, classes in sorted(terminal.items())
    ]
    payload = {
        "schema": "acfqp.generic_observation_quotient_graph.v105",
        "partial_candidate_id": candidate["candidate_id"],
        "layout_id": layout["layout_id"],
        "projected_state_target_columns": list(targets),
        "quotiented_residual_target_columns": candidate["unknown_residual_target_columns"],
        "projected_state_width": len(targets),
        "projected_edge_rows": edge_rows,
        "projected_edge_count": len(edge_rows),
        "projected_terminal_rows": terminal_rows,
        "projected_terminal_state_count": len(terminal_rows),
        "source_ground_support_label_count": len(contexts),
        "source_raw_transition_row_count": len(raw_rows),
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
    model = {**payload, "quotient_graph_id": _content_id(_DOMAINS["model"], payload)}
    return model, _terminal_rules(assignments, accepting, actions)


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


def _initial_projected(raw: Sequence[int], candidate: Mapping[str, Any]) -> tuple[int, ...]:
    canonical = tuple(raw[index] for index in candidate["layout"]["state_canonical_to_raw"])
    return tuple(canonical[row["target_column"]] for row in candidate["compiled_factor_assignments"])


def _verify_plan(
    plan: Mapping[str, Any],
    raw_state: Sequence[int],
    candidate: Mapping[str, Any],
    actions: Mapping[int, tuple[int, ...]],
    model: Mapping[str, Any],
    rules: tuple[Mapping[str, Any], ...],
) -> int:
    path = plan["projected_action_path"]
    _require(
        type(path) is list
        and bool(path)
        and path == plan["embedded_projected_plan"]["action_keys"]
        and path[0] in plan["exact_legal_action_keys_at_initial_state"],
        "V123r1 plan identity/initial legality changed",
    )
    reachable = {_initial_projected(raw_state, candidate)}
    checks = 0
    if plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        for key in path:
            next_states = set()
            for state in reachable:
                support = _successors(candidate["compiled_factor_assignments"], state, actions[key])
                checks += len(support)
                next_states.update(support)
            _require(bool(next_states), "V123r1 generic plan support changed")
            reachable = next_states
    else:
        edges = defaultdict(set)
        for edge in model["projected_edge_rows"]:
            edges[(tuple(edge["projected_pre"]), edge["action_key"])].add(tuple(edge["projected_post"]))
        for key in path:
            next_states = set()
            for state in reachable:
                rows = edges[(state, key)]
                checks += len(rows)
                next_states.update(rows)
            _require(bool(next_states), "V123r1 observation graph path changed")
            reachable = next_states
    _require(any(_terminal_match(state, rules) for state in reachable), "V123r1 plan misses terminal support")
    return checks


def _verify_occurrence(row: Mapping[str, Any]) -> dict[str, Any]:
    _require(row.get("schema") == "acfqp.generic_quotient_compiler_occurrence.v123r1", "V123r1 occurrence schema changed")
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    _require(
        row["frozen_failed_v123_preregistration_id"] == FAILED_V123_PREREGISTRATION_ID
        and row["frozen_failed_v123_record_sha256"] == FAILED_V123_RECORD_SHA256
        and row["same_failed_v123_identity_rerun"] is False,
        "V123r1 failed predecessor join changed",
    )
    acquisition = row["partial_prior_acquisition"]
    strict = row["strict_no_prior_complete_model_control"]
    _verify_id(acquisition, "acquisition_id", _DOMAINS["acquisition"])
    _verify_id(strict, "strict_control_id", _DOMAINS["strict"])
    candidate = acquisition["candidate"]
    _verify_id(candidate, "candidate_id", _DOMAINS["acquisition"])
    _require(
        acquisition["ground_support_labels"] == strict["ground_support_labels"]
        and acquisition["raw_transition_sha256"] == strict["raw_transition_sha256"]
        and bool(candidate["unknown_residual_target_columns"]),
        "V123r1 acquisition/control join changed",
    )
    sequence = row["generic_quotient_compiler_sequence"]
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    v119 = sequence["generic_compiler_base_sequence"]
    _verify_id(v119, "sequence_id", _DOMAINS["v119_sequence"])
    base = v119["genesis_authorized_base_sequence"]
    _verify_id(base, "sequence_id", _DOMAINS["v113_sequence"])
    _require(
        sequence["generic_compiler_base_sequence_id"] == v119["sequence_id"]
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and v119["partial_candidate_id"] == candidate["candidate_id"]
        and base["partial_candidate_id"] == candidate["candidate_id"],
        "V123r1 sequence/candidate join changed",
    )
    receipt = v119["program_branch_dependency_receipt"]
    _require(
        receipt["compiled_factor_assignments"] == candidate["compiled_factor_assignments"]
        and receipt["partial_candidate_id"] == candidate["candidate_id"],
        "V123r1 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in receipt["canonical_action_catalogue"]
    }
    persistent = base["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == base["persistent_exact_overlay_sha256"],
        "V123r1 persistent raw evidence changed",
    )
    new_keys = {
        _raw_key(raw)
        for episode in base["episodes"]
        for raw in episode["raw_incremental_transition_rows"]
    }
    current = {_raw_key(raw): raw for raw in persistent if _raw_key(raw) not in new_keys}
    rebuilt_models = []
    path_checks = direct = memoized = 0
    for index, episode in enumerate(base["episodes"]):
        before, rules_before = _compile_model(tuple(current.values()), candidate, actions)
        _require(before == base["quotient_models_before_each_episode"][index], "V123r1 before-model reconstruction changed")
        rebuilt_models.append(before)
        model_by_id = {before["quotient_graph_id"]: before}
        for plan_receipt in episode["abstract_plan_receipts"]:
            plan = plan_receipt["abstract_plan"]
            source = plan["planning_source"]
            if source in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}:
                _verify_id(plan, "legality_conditioned_quotient_plan_id", _DOMAINS["plan"])
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"]) == rules_before,
                    "V123r1 independently derived terminal rule changed",
                )
                path_checks += _verify_plan(plan, plan_receipt["raw_state"], candidate, actions, model_by_id[plan["quotient_graph_id"]], rules_before)
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["generic_factor_program_execution_adapter_used"] is True
                        and plan["legacy_shape_specific_planner_execution_adapter_called"] is False,
                        "V123r1 generic planner claim changed",
                    )
            elif source == "COMPILED_FACTOR_PROGRAM_MEMOIZED":
                memoized += 1
                _require(
                    plan["source_compiled_factor_program_plan"]["legacy_shape_specific_planner_execution_adapter_called"] is False,
                    "V123r1 memoized source changed",
                )
        for raw in episode["raw_incremental_transition_rows"]:
            current[_raw_key(raw)] = raw
        after, _rules_after = _compile_model(tuple(current.values()), candidate, actions)
        _require(after == base["quotient_models_after_each_episode"][index], "V123r1 after-model reconstruction changed")
        rebuilt_models.append(after)
        if index + 1 < len(base["episodes"]):
            _require(after == base["quotient_models_before_each_episode"][index + 1], "V123r1 epoch continuation changed")
        _require(
            episode["success"] is True
            and episode["all_incremental_ground_queries_followed_failed_certificates"] is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V123r1 episode/certificate discipline changed",
        )
    _require(
        len(current) == len(persistent)
        and sequence["direct_generic_factor_program_plan_count"] == direct,
        "V123r1 persistent inventory or direct-plan count changed",
    )
    comparison = sequence["generic_compiler_matched_control"]
    model_checks = sum(model["source_projected_edge_program_checks"] for model in rebuilt_models)
    _require(
        comparison
        == {
            "matched_model_comparison_count": len(rebuilt_models),
            "generic_model_program_support_checks": model_checks,
            "legacy_matched_control_program_support_checks": model_checks,
            "all_generic_models_equal_retained_v113_matched_control": True,
            "legacy_shape_specific_model_builder_used_as_planning_input": False,
            "legacy_matched_control_compute_charged_to_generic_arm": False,
        },
        "V123r1 compiler comparison changed",
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
        "generic_model_compiler_comparisons": len(rebuilt_models),
        "generic_model_program_support_checks": model_checks,
        "legacy_matched_control_program_support_checks": model_checks,
        "direct_generic_factor_program_plans": direct,
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "legacy_matched_control_compute_charged_to_generic_arm": False,
        "scalar_cost_aggregation_performed": False,
    }
    _require(row["accounting"] == accounting, "V123r1 occurrence accounting changed")
    _require(
        row["registered_gate"]["passed"] is True
        and all(value is True for key, value in row["registered_gate"].items() if key != "passed")
        and row["legacy_shape_specific_model_builder_used_as_planning_input"] is False
        and row["legacy_shape_specific_planner_execution_adapter_present"] is False
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V123r1 occurrence Gate or claim locks changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "seed": row["seed"],
        "episode_count": len(base["episodes"]),
        "independently_rebuilt_model_epoch_count": len(rebuilt_models),
        "independent_plan_path_support_checks": path_checks,
        "memoized_plan_count": memoized,
        "accounting": accounting,
    }


def freeze_generic_quotient_compiler_verification_v123r1(
    campaign_raw: bytes,
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
    failed_v123_raw: bytes,
    v121r1_campaign_raw: bytes,
    v121_failed_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    failed = loads_canonical_json(failed_v123_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V123r1 frozen campaign identity or bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    _require(
        hashlib.sha256(failed_v123_raw).hexdigest() == FAILED_V123_RECORD_SHA256
        and failed["preregistration_id"] == FAILED_V123_PREREGISTRATION_ID
        and failed["same_identity_rerun_forbidden"] is True,
        "V123r1 failure predecessor changed",
    )
    _require(
        freeze_generic_factor_planner_verification_v122(
            v122_campaign_raw,
            v121r1_campaign_raw,
            v121_failed_campaign_raw,
            v121r1_verification_raw,
            dict(source_campaign_bytes),
        )
        == v122_verification_raw,
        "V123r1 V122 producer-free predecessor changed",
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v122_success_campaign_id"] == V122_CAMPAIGN_ID
        and campaign["v122_success_verification_id"] == V122_VERIFICATION_ID
        and campaign["frozen_failed_v123_preregistration_id"] == FAILED_V123_PREREGISTRATION_ID
        and campaign["frozen_failed_v123_record_sha256"] == FAILED_V123_RECORD_SHA256
        and campaign["same_failed_v123_identity_rerun"] is False,
        "V123r1 predecessor/content joins changed",
    )
    rows = tuple(_verify_occurrence(row) for row in campaign["target_occurrences"])
    _require(
        tuple(row["seed"] for row in rows) == EXPECTED_SEEDS
        and all(row["episode_count"] == len(EXPECTED_EPISODES) for row in rows)
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V123r1 occurrence identities changed",
    )
    numeric_keys = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric_keys}
    accounting.update(
        sample_labels_execution_steps_derivation_planning_and_model_checks_separate=True,
        legacy_matched_control_compute_charged_to_generic_arm=False,
        sample_efficiency_improvement_claimed=False,
        scalar_cost_aggregation_performed=False,
    )
    _require(
        campaign["accounting"] == accounting
        and campaign["registered_gate"]["passed"] is True
        and campaign["registered_gate"]["passed_target_occurrence_count"] == 2
        and campaign["legacy_shape_specific_model_builder_used_as_planning_input"] is False
        and campaign["legacy_shape_specific_planner_execution_adapter_present"] is False
        and campaign["sample_efficiency_improvement_claimed"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["global_exact_dynamics_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V123r1 campaign accounting, Gate, or claim locks changed",
    )
    payload = {
        "schema": "acfqp.generic_quotient_compiler_verification.v123r1",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "failed_v123_preregistration_id": FAILED_V123_PREREGISTRATION_ID,
        "failed_v123_record_sha256": FAILED_V123_RECORD_SHA256,
        "v122_predecessor_verification_id": V122_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_raw_transition_model_epoch_reconstruction": True,
        "producer_free_recursive_expression_successor_reconstruction": True,
        "producer_free_terminal_rule_reconstruction": True,
        "producer_free_program_and_graph_path_reachability_reconstruction": True,
        "producer_free_content_graph_reconstruction": True,
        "registered_gate_independently_verified": True,
        "legacy_shape_specific_model_builder_used_as_planning_input": False,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "sample_efficiency_improvement_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {**payload, "verification_id": _content_id(_DOMAINS["verification"], payload)}
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V123r1 frozen independent verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_generic_quotient_compiler_verification_v123r1",
)
