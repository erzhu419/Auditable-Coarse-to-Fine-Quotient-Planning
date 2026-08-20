"""Producer-free reconstruction of the V71 factorial acquisition campaign.

This module deliberately does not import the V71 producer/core or the V36/V37
operator implementations.  It opens the independently frozen V70 template
library, derives both query schedules from retained pre-state/action fields,
and reconstructs every candidate, prediction, rejection, stop, and held-out
audit from the retained raw transitions.
"""

from __future__ import annotations

import hashlib
from itertools import combinations
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v71 as domains
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    GenericRelationalTerminalProgramIndependentReplayV32Error,
    reconstruct_relational_terminal_program_v32,
    verify_source_complete_relational_program_v32,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
CAMPAIGN_BYTE_COUNT = 3_531_014
CAMPAIGN_SHA256 = "4d8f6afa609e38aaad4f714abd550dcc9fbebe0dcadcc5611e92cc81e9f6e51d"
PREREGISTRATION_ID = "2a006b95d9976d53693977400369636148a688185f9fa5df80403cde272da765"
V70_CAMPAIGN_ID = "dafe32e5ec1eec433bef6e8044722aea7474399d8bc78a10c5edd70713175548"
V70_VERIFICATION_ID = "b55346fd542c47380f5581d065b3a50b1da786f8bb0f42f611dafa05fa897fd7"
TEMPLATE_LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
VERIFICATION_ID = "faf1e3d0569cacd98514c35874b0c59fb685436a326e899cb7dcc70ed94994fa"
EXPECTED_CANONICAL_BYTE_COUNT = 1_050
EXPECTED_CANONICAL_SHA256 = "e1e5aec123df8217fad4481419a7bba1d2b4033dc1a4cecf28712576bf9b04b2"
_SCHEDULE_DOMAIN = b"acfqp:generic-role-free-acquisition-query-schedule:v36\x00"
_ACQUISITION_DOMAIN = b"acfqp:generic-prequential-role-free-terminal-acquisition:v37\x00"
_TEMPLATE_LIBRARY_DOMAIN = b"acfqp:generic-role-free-relational-template-library:v33\x00"
_SOURCE_EPISODE_DOMAIN = b"acfqp:generic-source-complete-relational-world-model:v31\x00"


class ConstructionK7RoleFreePrequentialIndependentVerifierV71Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RoleFreePrequentialIndependentVerifierV71Error(message)


def _content(document: Mapping[str, Any], id_key: str, domain: str) -> None:
    if type(document) is not dict or type(document.get(id_key)) is not str:
        _fail(f"V71 {id_key} inventory changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if domains.extension_content_id_v71(domain, payload) != document[id_key]:
        _fail(f"V71 {id_key} content identity changed")


def _label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V71 target legal-action evidence changed")
    if legal:
        if terminal is not None:
            _fail("V71 active row carried terminal acceptance")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V71 terminal row omitted acceptance")


def _relation(opcode: str, left: int, right: int, state: tuple[int, ...]) -> bool:
    if opcode == "EQ":
        return state[left] == state[right]
    if opcode == "LT":
        return state[left] < state[right]
    if opcode == "LE":
        return state[left] <= state[right]
    if opcode == "GT":
        return state[left] > state[right]
    if opcode == "GE":
        return state[left] >= state[right]
    _fail("V71 relation opcode changed")


def _evaluate(node: Any, state: tuple[int, ...]) -> tuple[str, int]:
    while type(node) is dict and node.get("kind") == "RELATION":
        left, right = node.get("left_column"), node.get("right_column")
        if type(left) is not int or type(right) is not int:
            _fail("V71 relation columns changed")
        node = node["when_true"] if _relation(
            node.get("opcode"), left, right, state
        ) else node["when_false"]
    if type(node) is not dict or node.get("kind") != "LEAF":
        _fail("V71 relation leaf changed")
    label, token = node.get("terminal_class"), node.get("status_token")
    if label not in ("ACTIVE", "ACCEPT", "REJECT") or type(token) is not int:
        _fail("V71 relation leaf payload changed")
    return label, token


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    action = row.get("selected_action")
    pre = row.get("pre_vector")
    if (
        type(pre) is not list
        or type(action) is not dict
        or type(action.get("action_key")) is not int
        or type(action.get("anonymous_fields")) is not list
    ):
        _fail("V71 query projection changed")
    return {
        "pre_vector": pre,
        "action_key": action["action_key"],
        "anonymous_action_fields": action["anonymous_fields"],
    }


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    order = []
    for row in rows:
        projection = _projection(row)
        key = (tuple(projection["pre_vector"]), projection["action_key"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    return [grouped[key] for key in order]


def _schedule(
    evidence: Mapping[str, Any], *, structural_prior: bool, library_id: str | None
) -> dict[str, Any]:
    layout = evidence.get("layout")
    unknown = evidence.get("unknown_residual_target_columns")
    rows = evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
    ):
        _fail("V71 schedule source inventory changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V71 schedule layout changed")
    groups = _groups(rows)
    known = tuple(index for index in range(len(order)) if index not in unknown)
    if len(known) < 2:
        _fail("V71 schedule modeled-coordinate inventory changed")
    ranked = []
    source_projections = []
    for original_index, group in enumerate(groups):
        projection = _projection(group[0])
        source_projections.append(projection)
        identity_sha = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
        if structural_prior:
            canonical_pre = [projection["pre_vector"][raw] for raw in order]
            distance = min(
                abs(canonical_pre[left] - canonical_pre[right])
                for left, right in combinations(known, 2)
            )
            score = (distance, identity_sha)
            score_document = {
                "anonymous_modeled_coordinate_boundary_distance": distance,
                "content_hash_tiebreak": identity_sha,
            }
        else:
            score = (identity_sha,)
            score_document = {"content_hash_order": identity_sha}
        ranked.append((score, original_index, group, projection, score_document))
    ranked.sort(key=lambda row: (row[0], row[1]))
    payload = {
        "schema": "acfqp.generic_role_free_acquisition_query_schedule.v36",
        "arm": (
            "ROLE_FREE_HEURISTIC_OPERATOR_ON"
            if structural_prior
            else "STRICT_CONTENT_HASH_SCHEDULE"
        ),
        "role_free_template_library_id": library_id if structural_prior else None,
        "query_source_projection_sha256": hashlib.sha256(
            canonical_json_bytes(source_projections)
        ).hexdigest(),
        "query_count": len(groups),
        "raw_transition_row_count": len(rows),
        "outcome_blind_score_evaluation_count": (
            len(groups) * (len(known) * (len(known) - 1) // 2)
            if structural_prior
            else len(groups)
        ),
        "schedule": [
            {
                "scheduled_query_index": index,
                "original_query_index": row[1],
                "query_projection": row[3],
                "outcome_blind_score": row[4],
                "raw_transition_row_count": len(row[2]),
            }
            for index, row in enumerate(ranked)
        ],
        "scheduled_raw_transition_rows": [item for row in ranked for item in row[2]],
        "pre_state_fields_accessed": True,
        "anonymous_action_fields_accessed": True,
        "post_state_fields_accessed": False,
        "legality_after_accessed": False,
        "terminal_acceptance_label_accessed": False,
        "outcome_tape_accessed": False,
        "heuristic_operator_not_safety_authority": True,
    }
    return {
        **payload,
        "query_schedule_id": hashlib.sha256(
            _SCHEDULE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _template_classes(node: Mapping[str, Any]) -> set[str]:
    if node.get("kind") == "LEAF":
        return {node.get("terminal_class")}
    return _template_classes(node["when_true"]) | _template_classes(
        node["when_false"]
    )


def _observed_class_view(
    library: Mapping[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    observed = {_label(row) for row in rows}
    templates = [
        row
        for row in library.get("role_free_templates", [])
        if _template_classes(row["role_free_decision_tree"]) <= observed
    ]
    if not templates:
        raise GenericRoleFreeRelationalTemplateV33Error(
            "V35 prior has no template whose leaf inventory is observed"
        )
    payload = {
        key: value
        for key, value in library.items()
        if key not in ("template_library_id", "role_free_templates", "role_free_template_count")
    }
    payload["role_free_templates"] = templates
    payload["role_free_template_count"] = len(templates)
    return {
        **payload,
        "template_library_id": hashlib.sha256(
            _TEMPLATE_LIBRARY_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _signed_integer_bits(value: int) -> int:
    return 1 + 2 * math.ceil(math.log2(abs(value) + 1))


def _literal_bits(rows: list[dict[str, Any]]) -> int:
    return sum(
        2 + sum(_signed_integer_bits(value) for value in row["post_vector"])
        for row in rows
    )


def _program_bits(
    program: Mapping[str, Any],
    *,
    library: Mapping[str, Any] | None,
    instantiation: Mapping[str, Any] | None,
    width: int,
) -> int:
    column_bits = max(1, math.ceil(math.log2(max(2, width))))
    tokens = program.get("status_token_by_terminal_class")
    if type(tokens) is not dict:
        _fail("V71 status token map changed")
    token_bits = sum(_signed_integer_bits(value) for value in tokens.values())
    if library is None:
        frontier = program.get("decision_tree_candidate_frontier")
        if type(frontier) is not list or not frontier:
            _fail("V71 strict frontier changed")
        return 8 * frontier[0]["decision_tree_byte_count"] + token_bits
    if type(instantiation) is not dict:
        _fail("V71 prior instantiation changed")
    selected = instantiation.get("selected_instantiation")
    if type(selected) is not dict:
        _fail("V71 prior selected instantiation changed")
    count = library.get("role_free_template_count")
    binding = selected.get("target_role_binding")
    if type(count) is not int or type(binding) is not list:
        _fail("V71 prior code inventory changed")
    return (
        max(1, math.ceil(math.log2(max(2, count))))
        + len(binding) * column_bits
        + column_bits
        + token_bits
    )


def _consensus(program: Mapping[str, Any], states: tuple[tuple[int, ...], ...]) -> bool:
    frontier = program.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier:
        _fail("V71 candidate frontier changed")
    return all(
        len({_evaluate(row["decision_tree"], state) for row in frontier}) == 1
        for state in states
    )


def _candidate(
    layout: Mapping[str, Any],
    unknown: list[int],
    acquired: list[dict[str, Any]],
    *,
    library: Mapping[str, Any] | None,
    maximum: int,
    denominator: int,
) -> dict[str, Any]:
    evidence = {
        "layout": layout,
        "unknown_residual_target_columns": unknown,
        "raw_transition_rows": acquired,
    }
    try:
        instantiation = None
        if library is None:
            program = reconstruct_relational_terminal_program_v32(
                evidence, maximum_program_candidates=maximum
            )
            source = "FINITE_RELATION_GRAMMAR"
            compute = program["relation_feature_evaluation_count"]
        else:
            active_library = _observed_class_view(library, acquired)
            instantiation = instantiate_role_free_relational_template_v33(
                active_library,
                evidence,
                maximum_exact_instantiations=maximum,
            )
            program = instantiation.get("instantiated_terminal_program")
            if type(program) is not dict:
                raise GenericRoleFreeRelationalTemplateV33Error(
                    "V37 prior exposed no exact target instantiation"
                )
            source = "ROLE_FREE_TEMPLATE_LIBRARY"
            compute = instantiation["binding_evaluation_count"]
    except (
        GenericRelationalTerminalProgramIndependentReplayV32Error,
        GenericRoleFreeRelationalTemplateV33Error,
    ) as error:
        return {"candidate_present": False, "constructor_failure": str(error)}
    order = layout.get("state_canonical_to_raw")
    states = tuple(
        sorted(
            {
                tuple(row["post_vector"][index] for index in order)
                for row in acquired
            }
        )
    )
    consensus = _consensus(program, states)
    literal = _literal_bits(acquired)
    selected_bits = _program_bits(
        program,
        library=library,
        instantiation=instantiation,
        width=len(order),
    )
    required = math.ceil(math.log2(denominator))
    gain = literal - selected_bits
    return {
        "candidate_present": True,
        "candidate_source": source,
        "candidate_program": program,
        "candidate_program_id": program["terminal_program_id"],
        "candidate_count": program["decision_tree_candidate_count"],
        "candidate_constructor_compute": compute,
        "candidate_consensus_on_observed_successors": consensus,
        "literal_description_bits": literal,
        "selected_program_description_bits": selected_bits,
        "mdl_description_gain_bits": gain,
        "required_mdl_gain_bits": required,
        "training_calibrated": consensus and gain >= required,
    }


def _predict(
    program: Mapping[str, Any],
    group: list[dict[str, Any]],
    order: list[int],
) -> dict[str, Any]:
    target = program.get("status_target_column")
    tree = program.get("decision_tree")
    if type(target) is not int or type(tree) is not dict:
        _fail("V71 selected program changed")
    predictions = []
    exact = True
    for row in group:
        state = tuple(row["post_vector"][index] for index in order)
        predicted_class, predicted_token = _evaluate(tree, state)
        observed_class, observed_token = _label(row), state[target]
        row_exact = predicted_class == observed_class and predicted_token == observed_token
        exact = exact and row_exact
        predictions.append(
            {
                "predicted_terminal_class": predicted_class,
                "observed_terminal_class": observed_class,
                "predicted_status_token": predicted_token,
                "observed_status_token": observed_token,
                "exact": row_exact,
            }
        )
    return {"query_exact": exact, "raw_row_predictions": predictions}


def _acquisition(
    evidence: Mapping[str, Any],
    *,
    library: Mapping[str, Any] | None,
    maximum: int = 32,
    denominator: int = 64,
) -> dict[str, Any]:
    layout = evidence.get("layout")
    unknown = evidence.get("unknown_residual_target_columns")
    rows = evidence.get("raw_transition_rows")
    if type(layout) is not dict or type(unknown) is not list or type(rows) is not list:
        _fail("V71 acquisition evidence changed")
    order = layout.get("state_canonical_to_raw")
    groups = _groups(rows)
    required = math.ceil(math.log2(denominator))
    acquired: list[dict[str, Any]] = []
    attempts = []
    ledger = []
    active = None
    selected = None
    stop = None
    retired = 0
    for offset, group in enumerate(groups):
        count = offset + 1
        if active is not None:
            prediction = _predict(active["program"], group, order)
            ledger.append(
                {
                    "query_index": offset,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "candidate_training_query_count": active["training_query_count"],
                    "prediction": prediction,
                    "prediction_frozen_before_query_outcome": True,
                }
            )
            if prediction["query_exact"]:
                active["evidence_bits"] += 1
                active["confirmed_query_count"] += 1
            else:
                active = None
                retired += 1
        acquired.extend(group)
        if active is not None and active["evidence_bits"] >= required and count < len(groups):
            selected, stop = active["program"], count
            break
        if active is None and count < len(groups) - 1:
            constructed = _candidate(
                layout,
                unknown,
                acquired,
                library=library,
                maximum=maximum,
                denominator=denominator,
            )
            public = {key: value for key, value in constructed.items() if key != "candidate_program"}
            public["training_query_count"] = count
            attempts.append(public)
            if constructed.get("training_calibrated") is True:
                active = {
                    "program": constructed["candidate_program"],
                    "program_id": constructed["candidate_program_id"],
                    "training_query_count": count,
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }
    if selected is None or stop is None:
        status = "ABSTAINED_NO_PREQUENTIALLY_CALIBRATED_PROPOSAL"
        heldout, heldout_exact = [], False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        heldout_exact = all(_predict(selected, group, order)["query_exact"] for group in groups[stop:])
        status = (
            "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
            if heldout_exact
            else "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        )
    query_order = [
        {
            "pre_vector": group[0]["pre_vector"],
            "action_key": group[0]["selected_action"]["action_key"],
            "raw_transition_row_count": len(group),
        }
        for group in groups
    ]
    payload = {
        "schema": "acfqp.generic_prequential_role_free_terminal_acquisition.v37",
        "arm": "ROLE_FREE_FACTOR_PRIOR_ON" if library is not None else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
        "role_free_template_library_id": None if library is None else library.get("template_library_id"),
        "witness_blind_query_order": query_order,
        "witness_blind_query_order_sha256": hashlib.sha256(canonical_json_bytes(query_order)).hexdigest(),
        "full_query_stream_ground_support_labels": len(groups),
        "proposal_attempts": attempts,
        "prequential_prediction_ledger": ledger,
        "retired_failed_proposal_count": retired,
        "required_prequential_evidence_bits": required,
        "prequential_evidence_bits_per_exact_query": 1,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected,
        "selected_terminal_program_id": None if selected is None else selected["terminal_program_id"],
        "heldout_ground_query_count": len(groups) - (stop or len(groups)),
        "heldout_raw_transition_row_count": len(heldout),
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "same_prequential_state_machine_in_both_arms": True,
        "prediction_frozen_before_each_confirmation_outcome": True,
        "failed_proposal_retrained_only_after_failure_observed": True,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "confidence_denominator": denominator,
        "automatic_stop_rule": (
            "TRAINING_MDL_AND_OBSERVED_CONSENSUS_THEN_PREQUENTIAL_EXACT_"
            "EVIDENCE_BITS_GE_CEIL_LOG2_CONFIDENCE_DENOMINATOR"
        ),
        "prequential_bit_is_deterministic_calibration_unit_not_probability_bound": True,
        "statistical_coverage_claimed": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
        "future_unseen_dynamics_authority_present": False,
    }
    return {
        **payload,
        "prequential_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _ood(source: Mapping[str, Any], status_target: int) -> dict[str, Any]:
    import copy

    result = copy.deepcopy(source)
    layout = result["layout"]
    order = layout["state_canonical_to_raw"]
    raw_status = order[status_target]
    new_raw, new_canonical = len(order), len(order)
    order.append(new_raw)
    colors = layout.get("state_structural_colors")
    if type(colors) is list:
        colors.append("V71_OOD_DUPLICATE_STATUS_ROLE")
    result["unknown_residual_target_columns"].append(new_canonical)
    result["unknown_residual_target_columns"].sort()
    for row in result["raw_transition_rows"]:
        row["pre_vector"].append(row["pre_vector"][raw_status])
        row["post_vector"].append(row["post_vector"][raw_status])
    return result


def _consumed(row: Mapping[str, Any]) -> int:
    value = row.get("stopped_physical_ground_support_labels")
    if value is None:
        value = row.get("full_query_stream_ground_support_labels")
    if type(value) is not int:
        _fail("V71 acquisition label accounting changed")
    return value


def _constructor_compute(row: Mapping[str, Any]) -> int:
    return sum(
        attempt.get("candidate_constructor_compute", 0)
        for attempt in row.get("proposal_attempts", [])
    )


def verify_role_free_prequential_campaign_bytes_v71(raw: bytes) -> bytes:
    if type(raw) is not bytes:
        _fail("V71 campaign input must be exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V71 campaign bytes are not canonical")
    if (
        len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
        or document.get("campaign_id") != CAMPAIGN_ID
    ):
        _fail("V71 frozen campaign identity changed")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_CAMPAIGN_V71_DOMAIN,
    )
    if (
        document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v70_campaign_id") != V70_CAMPAIGN_ID
        or document.get("v70_verification_id") != V70_VERIFICATION_ID
        or document.get("template_library_artifact_id") != TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V71 predecessor identity changed")
    library_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    library_document = library_artifact.to_document()
    if library_artifact.library_artifact_id != TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V71 independently opened template library changed")
    library = library_document["compiled_template_library"]
    occurrences = document.get("occurrences")
    if type(occurrences) is not list or len(occurrences) != 6:
        _fail("V71 occurrence inventory changed")
    arm_names = (
        "JOINT_SCHEDULE_AND_PROGRAM_PRIOR",
        "SCHEDULE_PRIOR_ONLY",
        "PROGRAM_PRIOR_ONLY",
        "STRICT_NO_PRIOR",
    )
    ood_count = 0
    source_program_count = 0
    for occurrence in occurrences:
        _content(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_OCCURRENCE_V71_DOMAIN,
        )
        envelope = occurrence.get("target_source_complete_episode")
        source = occurrence.get("retained_target_source")
        if type(envelope) is not dict or type(source) is not dict:
            _fail("V71 retained source envelope changed")
        evidence = envelope.get("terminal_program_source_evidence")
        episode = envelope.get("predecessor_v30_episode")
        if (
            type(evidence) is not dict
            or type(episode) is not dict
            or source
            != {
                "layout": evidence.get("layout"),
                "unknown_residual_target_columns": evidence.get(
                    "unknown_residual_target_columns"
                ),
                "raw_transition_rows": evidence.get("raw_transition_rows"),
            }
        ):
            _fail("V71 retained target source join changed")
        episode_payload = {
            key: value
            for key, value in envelope.items()
            if key != "source_complete_episode_id"
        }
        if hashlib.sha256(
            _SOURCE_EPISODE_DOMAIN + canonical_json_bytes(episode_payload)
        ).hexdigest() != envelope.get("source_complete_episode_id"):
            _fail("V71 source-complete episode identity changed")
        verify_source_complete_relational_program_v32(
            source, episode["final_relational_terminal_program"]
        )
        source_program_count += 1
        prior_schedule = _schedule(
            source,
            structural_prior=True,
            library_id=library["template_library_id"],
        )
        strict_schedule = _schedule(
            source, structural_prior=False, library_id=None
        )
        if (
            prior_schedule != occurrence.get("prior_query_schedule")
            or strict_schedule != occurrence.get("strict_query_schedule")
        ):
            _fail("V71 outcome-blind schedule reconstruction changed")
        arms = occurrence.get("factorial_acquisition_arms")
        if type(arms) is not dict or set(arms) != set(arm_names):
            _fail("V71 factorial arm inventory changed")
        prior_ordered = {
            **source,
            "raw_transition_rows": prior_schedule["scheduled_raw_transition_rows"],
        }
        strict_ordered = {
            **source,
            "raw_transition_rows": strict_schedule["scheduled_raw_transition_rows"],
        }
        expected_arms = {
            "JOINT_SCHEDULE_AND_PROGRAM_PRIOR": _acquisition(
                prior_ordered, library=library
            ),
            "SCHEDULE_PRIOR_ONLY": _acquisition(prior_ordered, library=None),
            "PROGRAM_PRIOR_ONLY": _acquisition(strict_ordered, library=library),
            "STRICT_NO_PRIOR": _acquisition(strict_ordered, library=None),
        }
        if arms != expected_arms:
            _fail("V71 prequential acquisition reconstruction changed")
        expected_ood = _ood(
            source, episode["final_relational_terminal_program"]["status_target_column"]
        )
        if expected_ood != occurrence.get("retained_incompatible_schema_ood_source"):
            _fail("V71 retained OOD input changed")
        try:
            replay = instantiate_role_free_relational_template_v33(
                library, expected_ood, maximum_exact_instantiations=32
            )
        except GenericRoleFreeRelationalTemplateV33Error:
            pass
        else:
            if replay["exact_target_instantiation_count"] != 0:
                _fail("V71 OOD control received a transferred program")
        if occurrence.get("incompatible_schema_ood_control", {}).get("status") != "INCOMPATIBLE_SCHEMA_REJECTED":
            _fail("V71 OOD rejection receipt changed")
        ood_count += 1
        if (
            occurrence.get("same_target_query_pool_in_all_four_arms") is not True
            or occurrence.get("same_v37_stop_engine_in_all_four_arms") is not True
            or occurrence.get("retrospective_counterfactual_acquisition_only") is not True
            or occurrence.get("query_local_overlay_only_safety_authority") is not True
        ):
            _fail("V71 occurrence claim boundary changed")

    summaries = {}
    for name in arm_names:
        rows = [row["factorial_acquisition_arms"][name] for row in occurrences]
        summaries[name] = {
            "heldout_validated_occurrence_count": sum(
                row["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED" for row in rows
            ),
            "heldout_failed_noncertificate_occurrence_count": sum(
                row["status"] == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE" for row in rows
            ),
            "abstained_occurrence_count": sum(row["status"].startswith("ABSTAINED") for row in rows),
            "counterfactual_acquisition_consumed_labels": sum(_consumed(row) for row in rows),
            "post_stop_heldout_audit_labels": sum(row["heldout_ground_query_count"] for row in rows),
            "proposal_constructor_compute_events": sum(_constructor_compute(row) for row in rows),
            "retired_failed_proposal_count": sum(row["retired_failed_proposal_count"] for row in rows),
        }
    comparable = [
        row
        for row in occurrences
        if row["factorial_acquisition_arms"]["JOINT_SCHEDULE_AND_PROGRAM_PRIOR"]["status"]
        == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        and row["factorial_acquisition_arms"]["STRICT_NO_PRIOR"]["status"]
        == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    ]
    joint_labels = sum(
        _consumed(row["factorial_acquisition_arms"]["JOINT_SCHEDULE_AND_PROGRAM_PRIOR"])
        for row in comparable
    )
    strict_labels = sum(
        _consumed(row["factorial_acquisition_arms"]["STRICT_NO_PRIOR"])
        for row in comparable
    )
    sample = {
        "jointly_heldout_validated_occurrence_count": len(comparable),
        "joint_prior_consumed_labels_on_comparable_occurrences": joint_labels,
        "strict_consumed_labels_on_comparable_occurrences": strict_labels,
        "joint_prior_minus_strict_labels": joint_labels - strict_labels,
        "fresh_joint_prior_label_reduction_observed": bool(comparable) and joint_labels < strict_labels,
        "factorial_attribution_available": True,
        "online_actual_sample_reduction_claimed": False,
        "economics_claimed": False,
    }
    if document.get("sample_tax_comparison") != sample:
        _fail("V71 sample-tax ledger changed")
    accounting = document.get("accounting")
    episodes = [row["target_source_complete_episode"]["predecessor_v30_episode"] for row in occurrences]
    expected_accounting = {
        "offline_template_source_labels": library_document[
            "offline_template_source_ground_support_labels"
        ],
        "offline_residual_library_labels": 204,
        "underlying_target_common_partial_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "underlying_target_certificate_local_labels": sum(row["local_ground_support_labels"] for row in episodes),
        "underlying_target_execution_steps": sum(row["execution_steps"] for row in episodes),
        "underlying_target_partial_planning_compute_events": sum(row["partial_planning_compute_events"] for row in episodes),
        "underlying_target_relational_planning_compute_events": sum(row["relational_abstract_support_branch_evaluations"] for row in episodes),
        "prior_schedule_score_evaluations": sum(row["prior_query_schedule"]["outcome_blind_score_evaluation_count"] for row in occurrences),
        "strict_schedule_score_evaluations": sum(row["strict_query_schedule"]["outcome_blind_score_evaluation_count"] for row in occurrences),
        "factorial_arm_accounting": summaries,
        "all_axes_separate": True,
        "counterfactual_acquisition_labels_not_subtracted_from_actual_source_generation": True,
    }
    if accounting != expected_accounting:
        _fail("V71 separated accounting changed")
    gate = document.get("registered_prequential_gate")
    expected_gate = {
        "joint_prior_heldout_validated_occurrence_count": summaries[
            "JOINT_SCHEDULE_AND_PROGRAM_PRIOR"
        ]["heldout_validated_occurrence_count"],
        "strict_heldout_validated_occurrence_count": summaries["STRICT_NO_PRIOR"][
            "heldout_validated_occurrence_count"
        ],
        "incompatible_schema_ood_rejection_count": ood_count,
        "required_ood_rejection_count": len(occurrences),
        "all_schedules_outcome_blind": True,
        "sample_reduction_required": False,
        "passed": True,
    }
    if gate != expected_gate:
        _fail("V71 registered Gate changed")
    locks = {
        "same_target_query_pool_in_all_four_arms": True,
        "same_v37_stop_engine_in_all_four_arms": True,
        "heldout_rows_accessed_before_stop": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "producer_free_verification_present": False,
        "online_adaptive_acquisition_integrated": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V71 claim locks changed")
    payload = {
        "schema": "acfqp.role_free_prequential_verification.v71",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(occurrences),
        "source_complete_terminal_programs_reconstructed": source_program_count,
        "outcome_blind_query_schedules_reconstructed": 2 * len(occurrences),
        "prequential_arm_histories_reconstructed": len(arm_names) * len(occurrences),
        "incompatible_schema_ood_controls_reexecuted": ood_count,
        "joint_prior_heldout_validated_occurrence_count": summaries[
            "JOINT_SCHEDULE_AND_PROGRAM_PRIOR"
        ]["heldout_validated_occurrence_count"],
        "strict_heldout_validated_occurrence_count": summaries["STRICT_NO_PRIOR"][
            "heldout_validated_occurrence_count"
        ],
        "joint_prior_minus_strict_labels": sample["joint_prior_minus_strict_labels"],
        "fresh_joint_prior_label_reduction_observed": sample[
            "fresh_joint_prior_label_reduction_observed"
        ],
        "frozen_predecessor_template_library_opened": True,
        "all_accounting_axes_recomputed": True,
        "v71_producer_imported": False,
        "v71_campaign_core_imported": False,
        "v36_scheduler_imported": False,
        "v37_acquisition_imported": False,
        "online_actual_sample_reduction_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PRODUCER_FREE_FACTORIAL_PREQUENTIAL_EVIDENCE_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v71(
            domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_VERIFICATION_V71_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V71 verification changed")
    return result


__all__ = ("verify_role_free_prequential_campaign_bytes_v71",)
