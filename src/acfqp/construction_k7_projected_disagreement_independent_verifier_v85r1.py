"""Producer-free reconstruction of the frozen V85r1 source evidence."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v85 as domains_v85
from acfqp import construction_k7_domain_registry_extension_v85r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "da749b6ad8996aba86896476fd7293540cca77cd1b4db7145b9bf4fe2759ec70"
CAMPAIGN_BYTE_COUNT = 6_400_725
CAMPAIGN_SHA256 = "9371c385cdbfa795752c79e57e3a557f278707df5341b52f81cfdc291e440541"
PREREGISTRATION_ID = "f93a236934e32cb03bc8e6303410dd4e420525de70d48b9a4075d1e917c12b86"
TEMPLATE_LIBRARY_ARTIFACT_ID = "9e55eb31f49aedce8c611fd37d66f87f42643f385bf9d6f6e98e0856b1ef7520"
V85_PRE_OUTCOME_FAILURE_ID = "82f3212d9e755c769795d1a908bbb1aac33b18de8f6cbe5a407256cac3e60acb"
SOURCE_SEEDS = (879_101, 879_102, 879_103, 879_104, 879_105, 879_106)
VERIFICATION_ID = "391038636f3b1744112f1a4a08b9d4acb5d32f8d19c27af603e69431cd40ad0f"
EXPECTED_CANONICAL_BYTE_COUNT = 1_763
EXPECTED_CANONICAL_SHA256 = "bdfcbbe3de71c4a804ec0eb2221dd378c64b2301cae8b800149d927db9242813"

_PARTITION_DOMAIN = b"acfqp:generic-structural-source-partition:v50\x00"
_ACQUISITION_DOMAIN = b"acfqp:generic-projected-disagreement-acquisition:v56\x00"
_BUNDLE_DOMAIN = b"acfqp:projected-disagreement-contextual-acquisition:v56\x00"
_MODEL_DOMAIN = b"acfqp:generic-projected-disagreement-successor-model:v56\x00"

_TOP_KEYS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "accounting",
    "acquisition_diagnostics",
    "all_preregistered_source_seeds_executed_without_selection",
    "all_terminal_and_residual_candidates_validated_before_compilation",
    "arbitrary_domain_transfer_claimed",
    "campaign_id",
    "candidate_disagreement_scheduling_uses_only_abstract_successors",
    "complete_world_model_synthesized",
    "fresh_v85r1_member_outcomes_only",
    "global_exact_dynamics_claimed",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "predecessor_producer_dereference_used",
    "preregistration_id",
    "producer_free_verification_present",
    "registered_gate",
    "residual_uncertainty_retained_for_robust_planning",
    "retained_model_diagnostics",
    "schema",
    "self_contained_template_library_id",
    "source_members",
    "structural_group_results",
    "structural_source_partition",
    "target_execution_performed",
    "v84_failed_campaign_id",
    "v84_failed_predecessor_preserved",
    "v85_member_content_domain_reused_without_v85_outcome_reuse",
    "v85_pre_outcome_failure_id",
}


class ConstructionK7ProjectedDisagreementIndependentVerifierV85R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedDisagreementIndependentVerifierV85R1Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _permutation(value: Any, width: int, label: str) -> list[int]:
    if (
        type(value) is not list
        or value != list(value)
        or sorted(value) != list(range(width))
        or any(type(row) is not int for row in value)
    ):
        _fail(f"V85r1 {label} changed")
    return value


def _terminal_class(row: Mapping[str, Any]) -> str:
    if row.get("terminal_acceptance_after") is True:
        return "ACCEPT"
    legal = row.get("legal_action_keys_after")
    if type(legal) is not list:
        _fail("V85r1 terminal label evidence changed")
    return "ACTIVE" if legal else "REJECT"


def _eval_tree(tree: Mapping[str, Any], state: tuple[int, ...]) -> tuple[str, int]:
    if type(tree) is not dict:
        _fail("V85r1 terminal tree changed")
    kind = tree.get("kind")
    if kind == "LEAF":
        terminal_class = tree.get("terminal_class")
        token = tree.get("status_token")
        if terminal_class not in ("ACCEPT", "ACTIVE", "REJECT") or type(token) is not int:
            _fail("V85r1 terminal leaf changed")
        return terminal_class, token
    if kind != "RELATION":
        _fail("V85r1 terminal node changed")
    left = tree.get("left_column")
    right = tree.get("right_column")
    opcode = tree.get("opcode")
    if (
        type(left) is not int
        or type(right) is not int
        or not 0 <= left < len(state)
        or not 0 <= right < len(state)
    ):
        _fail("V85r1 terminal relation coordinates changed")
    predicates = {
        "EQ": state[left] == state[right],
        "NE": state[left] != state[right],
        "LT": state[left] < state[right],
        "LE": state[left] <= state[right],
        "GT": state[left] > state[right],
        "GE": state[left] >= state[right],
    }
    if opcode not in predicates:
        _fail("V85r1 terminal relation opcode changed")
    branch = tree.get("when_true" if predicates[opcode] else "when_false")
    return _eval_tree(branch, state)


def _partial_support(
    assignment: Mapping[str, Any], state: tuple[int, ...], action: tuple[int, ...]
) -> tuple[int, ...]:
    expression = assignment.get("expression") if type(assignment) is dict else None
    if type(expression) is not list or not expression:
        _fail("V85r1 partial expression changed")
    if expression[0] == "E00" and len(expression) == 2:
        return (state[expression[1]],)
    if expression[0] == "E01" and len(expression) == 2:
        return (action[expression[1]],)
    if expression[0] == "E07" and len(expression) == 3:
        target = expression[1][1]
        field = expression[2][2][1]
        return tuple(sorted({state[target], state[target] + action[field]}))
    _fail("V85r1 partial expression escaped the retained grammar")


def _residual_support(
    expression: Any,
    state: tuple[int, ...],
    action: tuple[int, ...],
    target: int,
    field: int | None,
    constant: int | None,
    context: int,
    supports: Mapping[int, tuple[tuple[int, ...], ...]],
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (state[target],)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if expression == ["R05"] and field is not None:
        support = supports[context][field]
        if action[field] not in support:
            _fail("V85r1 contextual ordinal value escaped support")
        return (support.index(action[field]) + 1,)
    if type(expression) is list and len(expression) == 3 and expression[0] in ("R03", "R04"):
        left = _residual_support(
            expression[1], state, action, target, field, constant, context, supports
        )
        right = _residual_support(
            expression[2], state, action, target, field, constant, context, supports
        )
        if len(left) != 1 or len(right) != 1:
            _fail("V85r1 residual operands changed")
        if expression[0] == "R03":
            return (left[0] + right[0],)
        return tuple(sorted({left[0], right[0]}))
    _fail("V85r1 residual expression escaped R00--R05")


def _aligned_row(
    row: Mapping[str, Any], state_order: list[int], action_order: list[int]
) -> tuple[int, tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    selected = row.get("selected_action") if type(row) is dict else None
    pre = row.get("pre_vector") if type(row) is dict else None
    post = row.get("post_vector") if type(row) is dict else None
    fields = selected.get("anonymous_fields") if type(selected) is dict else None
    context = row.get("canonical_source_pool_member_index")
    if (
        type(pre) is not list
        or type(post) is not list
        or type(fields) is not list
        or type(context) is not int
        or len(pre) != len(post) != 0
        or any(type(value) is not int for value in (*pre, *post, *fields))
    ):
        _fail("V85r1 raw transition row changed")
    return (
        context,
        tuple(pre[index] for index in state_order),
        tuple(post[index] for index in state_order),
        tuple(fields[index] for index in action_order),
    )


def _verify_model(
    model: Mapping[str, Any],
    acquisition_bundle: Mapping[str, Any],
    structural_group: Mapping[str, Any],
) -> str:
    if type(model) is not dict:
        _fail("V85r1 compiled model changed")
    payload = {
        key: value
        for key, value in model.items()
        if key != "projected_disagreement_successor_model_id"
    }
    model_id = model.get("projected_disagreement_successor_model_id")
    acquisition = acquisition_bundle["projected_disagreement_acquisition"]
    rows = model.get("acquired_raw_transition_rows")
    layout = model.get("source_layout")
    width = model.get("state_width")
    action_width = model.get("action_field_width")
    if (
        _generic_id(_MODEL_DOMAIN, payload) != model_id
        or model.get("schema") != "acfqp.generic_projected_disagreement_successor_model.v56"
        or model.get("source_projected_disagreement_acquisition_id")
        != acquisition_bundle.get("projected_disagreement_contextual_acquisition_id")
        or model.get("source_contextual_ordinal_acquisition_id")
        != acquisition.get("projected_disagreement_acquisition_id")
        or type(rows) is not list
        or rows != acquisition.get("executed_raw_transition_rows")
        or model.get("acquired_raw_transition_row_count") != len(rows)
        or model.get("acquired_raw_transition_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or model.get("acquisition_prefix_ground_support_labels")
        != acquisition.get("stopped_physical_ground_support_labels")
        or type(layout) is not dict
        or type(width) is not int
        or type(action_width) is not int
        or model.get("projected_candidate_disagreement_schedule_used") is not True
        or model.get("contextual_ordinal_action_support_operator_present") is not True
        or model.get("every_terminal_and_residual_frontier_candidate_prequentially_checked") is not True
        or model.get("every_terminal_and_residual_frontier_candidate_heldout_checked") is not True
        or model.get("complete_world_model_claimed") is not False
        or model.get("abstract_plan_safety_authority_present") is not False
    ):
        _fail("V85r1 model identity or claim boundary changed")
    state_order = _permutation(layout.get("state_canonical_to_raw"), width, "state layout")
    action_order = _permutation(
        layout.get("action_canonical_to_raw"), action_width, "action layout"
    )
    context_rows = model.get("source_contextual_action_field_supports")
    member_ids = structural_group.get("source_member_ids")
    if type(context_rows) is not list or type(member_ids) is not list:
        _fail("V85r1 contextual support inventory changed")
    supports: dict[int, tuple[tuple[int, ...], ...]] = {}
    for expected, context_row in enumerate(context_rows):
        raw_supports = context_row.get("action_field_supports")
        if (
            context_row.get("context_index") != expected
            or context_row.get("source_member_id") != member_ids[expected]
            or type(raw_supports) is not list
            or len(raw_supports) != action_width
        ):
            _fail("V85r1 contextual action support changed")
        frozen = tuple(tuple(row) for row in raw_supports)
        if any(list(row) != sorted(set(row)) or not row for row in frozen):
            _fail("V85r1 contextual support set changed")
        supports[expected] = frozen
    evidence = structural_group.get("source_evidence")
    full_rows = evidence.get("raw_transition_rows") if type(evidence) is dict else None
    if type(full_rows) is not list or not full_rows:
        _fail("V85r1 full heldout source evidence changed")
    aligned = [
        (_aligned_row(row, state_order, action_order), row) for row in full_rows
    ]
    assignments = model.get("known_partial_factor_assignments")
    spaces = model.get("residual_version_spaces")
    status_target = model.get("status_target_column")
    frontier = model.get("mdl_minimal_terminal_candidate_frontier")
    if (
        type(assignments) is not list
        or type(spaces) is not list
        or type(status_target) is not int
        or type(frontier) is not list
        or not frontier
        or model.get("mdl_minimal_terminal_candidate_count") != len(frontier)
    ):
        _fail("V85r1 compiled component inventory changed")
    modeled = {
        *(row.get("target_column") for row in assignments),
        *(row.get("target_column") for row in spaces),
        status_target,
    }
    if modeled != set(range(width)):
        _fail("V85r1 compiled coordinate coverage changed")
    for (context, pre, post, action), raw_row in aligned:
        if context not in supports:
            _fail("V85r1 row context escaped compiled supports")
        for assignment in assignments:
            target = assignment["target_column"]
            if post[target] not in _partial_support(assignment, pre, action):
                _fail("V85r1 partial factor failed full-source replay")
        actual_class = _terminal_class(raw_row)
        for terminal in frontier:
            prediction = _eval_tree(terminal.get("decision_tree"), post)
            if prediction != (actual_class, post[status_target]):
                _fail("V85r1 terminal frontier failed full-source replay")
    grouped: dict[tuple[Any, ...], list[tuple[int, ...]]] = {}
    for aligned_row, _raw in aligned:
        context, pre, post, action = aligned_row
        grouped.setdefault((context, pre, action), []).append(post)
    for space in spaces:
        target = space.get("target_column")
        candidates = space.get("batch_exact_candidate_frontier")
        if (
            type(target) is not int
            or type(candidates) is not list
            or not candidates
            or space.get("batch_exact_candidate_count") != len(candidates)
        ):
            _fail("V85r1 residual version space changed")
        for (context, pre, action), posts in grouped.items():
            observed = tuple(sorted({post[target] for post in posts}))
            for candidate in candidates:
                predicted = _residual_support(
                    candidate.get("normalized_expression"),
                    pre,
                    action,
                    target,
                    candidate.get("action_field_binding"),
                    candidate.get("anonymous_integer_constant_binding"),
                    context,
                    supports,
                )
                if predicted != observed:
                    _fail("V85r1 residual frontier failed full-source batch replay")
    acquired_aligned = [
        (_aligned_row(row, state_order, action_order), row) for row in rows
    ]
    accepting = sorted(
        {
            aligned_row[2]
            for aligned_row, raw_row in acquired_aligned
            if raw_row.get("terminal_acceptance_after") is True
        }
    )
    if model.get("canonical_accepting_state_prototypes") != [list(row) for row in accepting]:
        _fail("V85r1 accepting-state prototypes changed")
    return model_id


def _verify_acquisition(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    acquisition = bundle.get("projected_disagreement_acquisition") if type(bundle) is dict else None
    if type(acquisition) is not dict:
        _fail("V85r1 acquisition bundle changed")
    acquisition_payload = {
        key: value
        for key, value in acquisition.items()
        if key != "projected_disagreement_acquisition_id"
    }
    bundle_payload = {
        key: value
        for key, value in bundle.items()
        if key != "projected_disagreement_contextual_acquisition_id"
    }
    ledger = acquisition.get("adaptive_query_selection_ledger")
    if (
        _generic_id(_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("projected_disagreement_acquisition_id")
        or _generic_id(_BUNDLE_DOMAIN, bundle_payload)
        != bundle.get("projected_disagreement_contextual_acquisition_id")
        or type(ledger) is not list
        or acquisition.get("executed_query_count") != len(ledger)
        or len({row.get("base_context_stratified_query_index") for row in ledger})
        != len(ledger)
        or any(row.get("query_index") != index for index, row in enumerate(ledger))
        or any(row.get("selection_frozen_before_query_outcome") is not True for row in ledger)
        or any(row.get("unacquired_post_state_or_label_accessed") is not False for row in ledger)
        or acquisition.get("query_selection_projection_compute_events")
        != sum(row.get("all_candidate_projection_compute_events", -1) for row in ledger)
        or acquisition.get("candidate_disagreement_scheduling_uses_only_abstract_successor_support") is not True
        or acquisition.get("unacquired_post_state_or_label_accessed_by_query_selection") is not False
        or acquisition.get("retrospective_acquisition_only") is not True
        or acquisition.get("online_execution_integrated") is not False
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or acquisition.get("empirical_version_space_promoted_to_global_dynamics") is not False
    ):
        _fail("V85r1 acquisition identity, ledger, or claim boundary changed")
    if acquisition.get("status") == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        if (
            acquisition.get("stopped_physical_ground_support_labels") != len(ledger)
            or acquisition.get("terminal_heldout_exact_prediction") is not True
            or acquisition.get("residual_heldout_exact_prediction") is not True
            or acquisition.get("heldout_exact_prediction") is not True
        ):
            _fail("V85r1 issued proposal heldout evidence changed")
    elif acquisition.get("status") != "ABSTAINED_NO_PROJECTED_DISAGREEMENT_PROPOSAL":
        _fail("V85r1 acquisition status changed")
    return acquisition


def verify_projected_disagreement_campaign_bytes_v85r1(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V85r1 campaign bytes changed")
    document = loads_canonical_json(raw)
    if (
        type(document) is not dict
        or set(document) != _TOP_KEYS
        or canonical_json_bytes(document) != raw
    ):
        _fail("V85r1 campaign canonical schema changed")
    campaign_payload = {
        key: value for key, value in document.items() if key != "campaign_id"
    }
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or domains.extension_content_id_v85r1(
            domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_CAMPAIGN_V85R1_DOMAIN,
            campaign_payload,
        )
        != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("self_contained_template_library_id")
        != TEMPLATE_LIBRARY_ARTIFACT_ID
        or document.get("v85_pre_outcome_failure_id") != V85_PRE_OUTCOME_FAILURE_ID
        or document.get("predecessor_producer_dereference_used") is not False
        or document.get("fresh_v85r1_member_outcomes_only") is not True
        or document.get("target_execution_performed") is not False
        or document.get("producer_free_verification_present") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("global_exact_dynamics_claimed") is not False
        or document.get("arbitrary_domain_transfer_claimed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("official_N_break_even") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V85r1 campaign identity or claim boundary changed")
    members = document.get("source_members")
    if type(members) is not list or len(members) != 6:
        _fail("V85r1 source member inventory changed")
    member_by_id = {}
    for member in members:
        payload = {key: value for key, value in member.items() if key != "member_id"}
        member_id = member.get("member_id")
        episode = member.get("source_complete_episode", {}).get("predecessor_v30_episode")
        if (
            domains_v85.extension_content_id_v85(
                domains_v85.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_MEMBER_V85_DOMAIN,
                payload,
            )
            != member_id
            or type(episode) is not dict
            or episode.get("success") is not True
            or episode.get("all_ground_queries_followed_failed_certificates") is not True
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety") is not True
            or member.get("target_outcome_accessed") is not False
        ):
            _fail("V85r1 source member identity or certificate discipline changed")
        member_by_id[member_id] = member
    if tuple(sorted(member["source_seed"] for member in members)) != SOURCE_SEEDS:
        _fail("V85r1 registered source seeds changed")
    partition = document.get("structural_source_partition")
    partition_payload = {
        key: value
        for key, value in partition.items()
        if key != "structural_source_partition_id"
    } if type(partition) is dict else {}
    groups = partition.get("structural_groups") if type(partition) is dict else None
    if (
        _generic_id(_PARTITION_DOMAIN, partition_payload)
        != partition.get("structural_source_partition_id")
        or type(groups) is not list
        or partition.get("source_member_count") != 6
        or partition.get("every_source_member_retained_exactly_once") is not True
        or sorted(member_id for group in groups for member_id in group["source_member_ids"])
        != sorted(member_by_id)
    ):
        _fail("V85r1 structural partition changed")
    for group in groups:
        descriptor = group.get("compatibility_descriptor")
        if (
            type(descriptor) is not dict
            or hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest()
            != group.get("structural_signature_id")
            or group.get("source_member_count") != len(group.get("source_member_ids", []))
        ):
            _fail("V85r1 structural compatibility group changed")
    results = document.get("structural_group_results")
    if type(results) is not list or len(results) != len(groups):
        _fail("V85r1 structural result inventory changed")
    models = []
    compiled_members = 0
    acquisitions = []
    for result, group in zip(results, groups, strict=True):
        if (
            result.get("structural_signature_id") != group.get("structural_signature_id")
            or result.get("source_member_ids") != group.get("source_member_ids")
            or result.get("source_member_count") != group.get("source_member_count")
        ):
            _fail("V85r1 group/result join changed")
        acquisition = _verify_acquisition(result.get("projected_disagreement_acquisition"))
        acquisitions.append(acquisition)
        model = result.get("projected_disagreement_successor_model")
        if model is not None:
            models.append(_verify_model(model, result["projected_disagreement_acquisition"], group))
            compiled_members += group["source_member_count"]
            if result.get("status") != "GROUP_PROJECTED_DISAGREEMENT_MODEL_COMPILED_NO_TARGET_EXECUTION":
                _fail("V85r1 compiled group status changed")
        elif result.get("status") != "GROUP_ACQUISITION_ABSTAINED_NONCERTIFICATE":
            _fail("V85r1 abstaining group status changed")
    source_episodes = [
        member["source_complete_episode"]["predecessor_v30_episode"]
        for member in members
    ]
    accounting = document.get("accounting")
    expected_accounting = {
        "offline_template_source_labels": 515,
        "offline_residual_library_labels": 204,
        "source_common_partial_labels": sum(
            member["common_partial_acquisition"]["ground_support_labels"]
            for member in members
        ),
        "source_certificate_local_labels": sum(
            episode["local_ground_support_labels"] for episode in source_episodes
        ),
        "group_acquisition_query_groups_consumed": sum(
            acquisition["stopped_physical_ground_support_labels"]
            if type(acquisition["stopped_physical_ground_support_labels"]) is int
            else acquisition["full_query_stream_ground_support_labels"]
            for acquisition in acquisitions
        ),
        "source_execution_steps": sum(
            episode["execution_steps"] for episode in source_episodes
        ),
        "source_partial_planning_compute_events": sum(
            episode["partial_planning_compute_events"] for episode in source_episodes
        ),
        "source_relational_planning_compute_events": sum(
            episode["relational_abstract_support_branch_evaluations"]
            for episode in source_episodes
        ),
        "terminal_candidate_derivation_compute_events": sum(
            acquisition["terminal_candidate_derivation_compute_events"]
            for acquisition in acquisitions
        ),
        "contextual_version_space_readiness_compute_events": sum(
            acquisition["compiler_readiness_compute_events"]
            for acquisition in acquisitions
        ),
        "query_selection_projection_compute_events": sum(
            acquisition["query_selection_projection_compute_events"]
            for acquisition in acquisitions
        ),
        "joint_version_space_selection_compute_events": sum(
            result["projected_disagreement_successor_model"]["version_space_selection_compute_events"]
            for result in results
            if result["projected_disagreement_successor_model"] is not None
        ),
        "target_labels": 0,
        "target_execution_steps": 0,
        "target_planning_compute": 0,
    }
    if (
        type(accounting) is not dict
        or any(accounting.get(key) != value for key, value in expected_accounting.items())
        or accounting.get("group_acquisition_query_groups_are_not_physical_label_count") is not True
        or accounting.get("all_axes_separate") is not True
    ):
        _fail("V85r1 accounting axes changed")
    gate = document.get("registered_gate")
    if (
        type(gate) is not dict
        or gate.get("actual_source_member_count") != 6
        or gate.get("actual_compiled_model_count") != len(models)
        or gate.get("actual_compiled_source_member_count") != compiled_members
        or len(models) < gate.get("minimum_compiled_model_count", 99)
        or compiled_members < gate.get("minimum_compiled_source_member_count", 99)
        or gate.get("source_certificate_discipline_clean") is not True
        or gate.get("every_source_member_retained_exactly_once") is not True
        or gate.get("every_compilation_eligible_group_compiled") is not True
        or gate.get("every_compiled_model_uses_contextual_ordinal_operator") is not True
        or gate.get("every_compiled_model_uses_projected_disagreement_schedule") is not True
        or gate.get("every_compiled_model_retains_all_batch_exact_residuals") is not True
        or gate.get("fresh_target_outcome_count") != 0
        or gate.get("passed") is not True
    ):
        _fail("V85r1 registered Gate changed")
    payload = {
        "schema": "acfqp.projected_disagreement_independent_verification.v85r1",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "self_contained_template_library_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        "source_member_ids": sorted(member_by_id),
        "source_member_count": 6,
        "structural_group_count": len(groups),
        "compiled_model_ids": models,
        "compiled_model_count": len(models),
        "compiled_source_member_count": compiled_members,
        "full_source_transition_rows_replayed": sum(
            len(group["source_evidence"]["raw_transition_rows"]) for group in groups
        ),
        "partial_residual_and_terminal_components_replayed_on_full_sources": True,
        "adaptive_query_ledgers_recomputed": True,
        "separate_accounting_axes_recomputed": True,
        "registered_source_gate_verified": True,
        "fresh_target_outcome_count": 0,
        "sample_tax_reduction_verified": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v85r1(
            domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_VERIFICATION_V85R1_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V85r1 verification changed")
    return result


__all__ = ("verify_projected_disagreement_campaign_bytes_v85r1",)
