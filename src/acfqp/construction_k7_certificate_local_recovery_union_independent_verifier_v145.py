"""Producer-free reconstruction of the V145 acquisition, models, and plans."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v145 as domains
from acfqp import construction_k7_occurrence_factor_bank_update_independent_verifier_v141 as v141
from acfqp import construction_k7_robust_factor_dictionary_independent_verifier_v131r2 as base
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    _dependencies,
    exact_generic_artifact_factor_replay_v121,
)
from acfqp.generic_compiled_factor_planner_v122 import derive_generic_terminal_rules_v122
from acfqp.generic_layout_factorized_world_model_v5 import align_generic_occurrence_v5
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "24a50acc5cf553f4fc457e17aa4ffff0fc6b6b9ebe08fa0d54076d998c3eeaa9"
CAMPAIGN_BYTE_COUNT = 17_516_246
CAMPAIGN_SHA256 = "5584aa76043f76d69b72ec189bc67a3952e758bbaaad33025b73dc859851f33c"
PREREGISTRATION_ID = "c254e8a09b46c8efb5849697887595f3e7462f2a2d797c5e58bd8a7011ec564e"
PREREGISTRATION_BYTE_COUNT = 34_809
PREREGISTRATION_SHA256 = "dd8a0b07244327bb46fed537bb59586ee09062948f8f3d1d62240d02d6a12549"
V144R2_CAMPAIGN_ID = "5008bebdbac2bd80674873dde52ffec8b220a4dcb395a10e80c50b701619567e"
V144R2_CAMPAIGN_BYTE_COUNT = 41_468_476
V144R2_CAMPAIGN_SHA256 = "fe5baa36098041a57cb865e7882d27eb8666c3606d120d2c1a99becd0db282db"
V144R2_FAILURE_BYTE_COUNT = 3_181
V144R2_FAILURE_SHA256 = "420242cda458596a23302aa73763752ec8fc91943a099e5113bb3b25c9ca2162"
V144R1_CAMPAIGN_BYTE_COUNT = 5_840_090
V144R1_CAMPAIGN_SHA256 = "e7665f51118ffd271ef508d9f63ae48583026f27b23cdcf2d5979022ca405194"
V144R1_FAILURE_BYTE_COUNT = 2_921
V144R1_FAILURE_SHA256 = "4ca167f46e3be61ff3acd74adf3f766f034c67a859da2cdf38245434db33ebe9"
EXPECTED_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_291, 1_047_297))
EXPECTED_EPISODES = (501, 502, 503, 504)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64

_V144_ACQUISITION_DOMAIN = "acfqp:construction-k7-fifth-family-factor-bank-transfer-acquisition:v144"
_V144_EXECUTION_DOMAIN = "acfqp:construction-k7-relational-factor-execution-projection:v144"
_V144R1_MODEL_DOMAIN = "acfqp:construction-k7-relational-overlay-model:v144r1"
_V144R1_STATE_DOMAIN = "acfqp:construction-k7-relational-overlay-state:v144r1"
_V144R1_BOOTSTRAP_DOMAIN = "acfqp:construction-k7-relational-overlay-bootstrap:v144r1"
_V144R1_UPDATE_DOMAIN = "acfqp:construction-k7-relational-overlay-update:v144r1"
_V144R1_MATCH_DOMAIN = "acfqp:construction-k7-relational-overlay-match:v144r1"
_V144R1_SEQUENCE_DOMAIN = "acfqp:construction-k7-relational-overlay-sequence:v144r1"
_V144R1_OCCURRENCE_DOMAIN = "acfqp:construction-k7-fifth-family-factor-bank-transfer-occurrence:v144r1"


class ConstructionK7CertificateLocalRecoveryUnionIndependentVerifierV145Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateLocalRecoveryUnionIndependentVerifierV145Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V145 {key} changed")


def _acquisition_error_name(error: BaseException) -> str:
    if isinstance(
        error,
        ConstructionK7CertificateLocalRecoveryUnionIndependentVerifierV145Error,
    ):
        return "GenericRelationalFactorExecutionProjectionV144Error"
    return type(error).__name__


def _action_only(expression: Any, fields: tuple[int, ...]) -> int | bool:
    if type(expression) in {int, bool}:
        return expression
    _require(type(expression) is list and bool(expression), "V145 relation key shape changed")
    opcode = expression[0]
    if opcode == "E01":
        index = expression[1]
        _require(type(index) is int and index in range(len(fields)), "V145 action field changed")
        return fields[index]
    values = [_action_only(item, fields) for item in expression[1:]]
    if opcode == "E05":
        return int(values[0]) + int(values[1])
    if opcode == "E06":
        _require(int(values[1]) != 0, "V145 zero relation divisor")
        return int(values[0]) % int(values[1])
    if opcode == "E08":
        return values[0] == values[1]
    if opcode == "E09":
        return int(values[0]) > int(values[1])
    if opcode == "E10":
        return bool(values[0]) and bool(values[1])
    if opcode == "E11":
        return not bool(values[0])
    if opcode == "E12":
        return int(values[1]) if bool(values[0]) else int(values[2])
    if opcode == "E13":
        return int(values[0]) | int(values[1])
    _fail("V145 relation key is not action-only")


def _lower_expression(expression: Any, binding: Mapping[str, Any], catalogue: tuple[Any, ...]) -> Any:
    if type(expression) in {int, bool}:
        return expression
    _require(type(expression) is list and bool(expression), "V145 relational expression changed")
    opcode = expression[0]
    if opcode in {"E00", "E01"}:
        _require(len(expression) == 2 and type(expression[1]) is int, "V145 causal atom changed")
        return list(expression)
    if opcode == "E03":
        _require(len(expression) == 2 and expression[1] in binding["constants"], "V145 constant binding changed")
        return binding["constants"][expression[1]]
    if opcode == "E04":
        _require(len(expression) == 3, "V145 relation lookup changed")
        rows = binding["relations"].get(expression[1])
        _require(type(rows) is list and len(rows) >= 2, "V145 finite relation changed")
        relation = {key: value for key, value in rows}
        _require(len(relation) == len(rows), "V145 relation keys changed")
        key_expression = _lower_expression(expression[2], binding, catalogue)
        state_dependencies, _ = _dependencies(key_expression)
        _require(not state_dependencies, "V145 relation key depends on runtime state")
        reachable = {_action_only(key_expression, action.fields) for action in catalogue}
        _require(reachable == set(relation), "V145 relation support changed")
        ordered = sorted(relation.items())
        lowered: Any = ordered[-1][1]
        for key, value in reversed(ordered[:-1]):
            lowered = ["E12", ["E08", copy.deepcopy(key_expression), key], value, lowered]
        return lowered
    _require(opcode in atomic.GENERIC_ATOMIC_OPCODE_NAMES_V4, "V145 opcode changed")
    return [opcode, *(_lower_expression(item, binding, catalogue) for item in expression[1:])]


def _lower_candidate(
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
) -> PartialFactorCandidateV15:
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, candidate.layout, canonical_occurrence=0
    )
    binding = atomic._derive_binding(aligned_rows, aligned_catalogue)  # noqa: SLF001
    assignments = []
    for assignment in candidate.assignments:
        lowered = _lower_expression(assignment["expression"], binding, aligned_catalogue)
        state_dependencies, action_dependencies = _dependencies(lowered)
        assignments.append(
            {
                **copy.deepcopy(dict(assignment)),
                "expression": lowered,
                "state_dependencies": state_dependencies,
                "action_dependencies": action_dependencies,
            }
        )
    source = candidate.public_document
    payload = {
        **{
            key: copy.deepcopy(value)
            for key, value in source.items()
            if key not in {"schema", "candidate_id", "compiled_factor_assignments"}
        },
        "schema": "acfqp.relational_factor_execution_projection.v144",
        "source_relational_candidate_id": source["candidate_id"],
        "compiled_factor_assignments": assignments,
        "frozen_anonymous_binding": copy.deepcopy(binding),
        "source_raw_transition_count": len(rows),
        "source_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "occurrence_constants_lowered_to_integer_literals": True,
        "finite_relations_lowered_to_typed_conditionals": True,
        "relation_key_support_exactly_equals_action_catalogue_support": True,
        "historical_v121_v122_modules_modified": False,
        "ground_rows_required_by_planner": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {**payload, "candidate_id": _content_id(_V144_EXECUTION_DOMAIN, payload)}
    projected = PartialFactorCandidateV15(document, candidate.layout, tuple(assignments), aligned_rows)
    _require(
        exact_generic_artifact_factor_replay_v121(projected, rows, catalogue)["exact"] is True,
        "V145 independently lowered candidate is not exact",
    )
    return projected


def _relational_stop(
    source: PartialFactorCandidateV15,
    execution: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    *,
    enabled: bool,
    epoch: int,
    invalidated: int,
    successes: int,
    alpha: int,
) -> dict[str, Any]:
    result = base._stop(  # noqa: SLF001
        execution,
        rows,
        catalogue,
        enabled=enabled,
        epoch=epoch,
        invalidated=invalidated,
        successes=successes,
        alpha=alpha,
    )
    replay = dict(result["current_partial_factor_replay"])
    replay["source_relational_candidate_id"] = source.public_document["candidate_id"]
    return {
        **result,
        "schema": "acfqp.robust_relational_dictionary_factor_stop_update.v144",
        "source_relational_candidate_id": source.public_document["candidate_id"],
        "execution_projection_candidate_id": execution.public_document["candidate_id"],
        "current_partial_factor_replay": replay,
        "same_lowered_execution_projection_used_by_replay_and_planner": True,
    }


def _rebuild_acquisition(
    recorded: Mapping[str, Any],
    adapter: Any,
    projection: Mapping[str, Any],
    batches: tuple[tuple[Any, ...], ...],
    *,
    enabled: bool,
    config: Mapping[str, Any],
) -> tuple[PartialFactorCandidateV15, tuple[Any, ...]]:
    _verify_id(recorded, "acquisition_id", _V144_ACQUISITION_DOMAIN)
    target = recorded["ground_support_labels"]
    source = execution = None
    issued = invalidated = disagreements = epoch = successes = 0
    previous = None
    history = []
    derivation_compute = selected_artifact = replay_errors = 0
    rows = []
    accepting_label = None
    terminal_stop = None
    for labels, batch in enumerate(batches[:target], 1):
        rows.extend(batch)
        current = tuple(rows)
        if accepting_label is None and any(row.terminal_acceptance_after is True for row in batch):
            accepting_label = labels
        if source is not None:
            try:
                replay = exact_generic_artifact_factor_replay_v121(execution, current, adapter.catalogue)
            except Exception as error:
                previous = source.public_document["candidate_id"]
                source = execution = None
                invalidated += 1
                epoch += 1
                successes = 0
                replay_errors += 1
                history.append(
                    {"support_label_count": labels, "candidate_available": False, "candidate_replay_error_type": _acquisition_error_name(error)}
                )
            else:
                if replay["exact"] is True:
                    successes += 1
                else:
                    previous = source.public_document["candidate_id"]
                    source = execution = None
                    invalidated += 1
                    epoch += 1
                    successes = 0
        if source is None:
            try:
                source, compute = base._synthesize(  # noqa: SLF001
                    current,
                    adapter.catalogue,
                    projection,
                    labels=labels,
                    enabled=enabled,
                    config=config,
                )
                execution = _lower_candidate(source, current, adapter.catalogue)
                issued = labels
                derivation_compute += compute["generic_atomic_expression_evaluations"]
                selected_artifact = compute["artifact_expression_selected_count"]
                if previous is not None and source.public_document["candidate_id"] != previous:
                    disagreements += 1
            except Exception as error:
                source = execution = None
                history.append(
                    {"support_label_count": labels, "candidate_available": False, "constructor_error_type": _acquisition_error_name(error)}
                )
                continue
        try:
            stop = _relational_stop(
                source,
                execution,
                current,
                adapter.catalogue,
                enabled=enabled,
                epoch=epoch,
                invalidated=invalidated,
                successes=successes,
                alpha=config["global_alpha_denominator"],
            )
        except Exception as error:
            history.append(
                {"support_label_count": labels, "candidate_available": True, "candidate_id": source.public_document["candidate_id"], "candidate_stop_replayable": False, "candidate_replay_error_type": _acquisition_error_name(error)}
            )
            previous = source.public_document["candidate_id"]
            source = execution = None
            invalidated += 1
            epoch += 1
            successes = 0
            replay_errors += 1
            continue
        history.append(
            {"support_label_count": labels, "candidate_available": True, "candidate_id": source.public_document["candidate_id"], "stopped_by_shared_rule": stop["stopped"], "accepting_projection_available": accepting_label is not None}
        )
        if labels == target:
            terminal_stop = stop
    _require(
        source is not None and execution is not None and terminal_stop is not None and terminal_stop["stopped"] is True and accepting_label is not None,
        "V145 acquisition did not independently close",
    )
    raw_rows = tuple(rows)
    payload = {
        "schema": "acfqp.fifth_family_factor_bank_transfer_acquisition_arm.v144",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": "OCCURRENCE_FACTOR_BANK_UPDATE_FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR",
        "factor_prior_enabled": enabled,
        "v141_factor_bank_id": v141.FROZEN_BANK_ID,
        "v141_independent_verification_id": v141.VERIFICATION_ID,
        "occurrence_granular_robust_factor_bank_selected_source_only": True,
        "verified_factor_bank_receipt_consumed_before_target_outcomes": True,
        "target_family_absent_from_v141_source_occurrence_archive": True,
        "fair_witness_blind_path_first_backtracking": True,
        "generation_witness_accessed": False,
        "reachable_frontier_exhaustion_used_as_stopping_input": False,
        "only_arm_switch_is_normalized_factor_prior": True,
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "ground_support_labels": target,
        "raw_transition_count": len(raw_rows),
        "raw_transition_sha256": hashlib.sha256(canonical_json_bytes([row.to_document() for row in raw_rows])).hexdigest(),
        "candidate": dict(source.public_document),
        "execution_projection": dict(execution.public_document),
        "candidate_issued_at_support_label": issued,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_replay_error_count": replay_errors,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "first_accepting_observation_label": accepting_label,
        "terminal_stop_update": dict(terminal_stop),
        "stopping_history": history,
        "derivation_compute_events": derivation_compute,
        "artifact_expression_selected_count": selected_artifact,
        "sample_labels_and_derivation_compute_separate": True,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    rebuilt = {**payload, "acquisition_id": _content_id(_V144_ACQUISITION_DOMAIN, payload)}
    if rebuilt != recorded:
        changed = sorted(
            key
            for key in set(rebuilt) | set(recorded)
            if rebuilt.get(key) != recorded.get(key)
        )
        detail = None
        if "stopping_history" in changed:
            expected_history = rebuilt["stopping_history"]
            recorded_history = recorded["stopping_history"]
            detail = next(
                (
                    (index, left, right)
                    for index, (left, right) in enumerate(
                        zip(expected_history, recorded_history, strict=False)
                    )
                    if left != right
                ),
                (len(expected_history), len(recorded_history)),
            )
        _fail(
            f"V145 producer-free acquisition reconstruction changed: "
            f"{changed}; first_history_difference={detail!r}"
        )
    return execution, raw_rows


def _wrap_model(base_model: Mapping[str, Any]) -> dict[str, Any]:
    terminals: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for row in base_model["projected_terminal_rows"]:
        terminals[tuple(row["projected_state"])].update(row["observed_terminal_classes"])
    edges = sorted(
        (
            tuple(row["projected_pre"]),
            row["action_key"],
            tuple(row["projected_post"]),
        )
        for row in base_model["projected_edge_rows"]
    )
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_quotient_graph.v144r1",
        "base_quotient_graph_id": base_model["quotient_graph_id"],
        "partial_candidate_id": base_model["partial_candidate_id"],
        "layout_id": base_model["layout_id"],
        "projected_state_target_columns": list(base_model["projected_state_target_columns"]),
        "quotiented_residual_target_columns": list(base_model["quotiented_residual_target_columns"]),
        "projected_state_width": base_model["projected_state_width"],
        "projected_edge_rows": [
            {"projected_pre": list(pre), "action_key": action, "projected_post": list(post)}
            for pre, action, post in edges
        ],
        "projected_edge_count": len(edges),
        "projected_terminal_rows": [
            {"projected_state": list(state), "observed_terminal_classes": sorted(classes)}
            for state, classes in sorted(terminals.items())
        ],
        "projected_terminal_state_count": len(terminals),
        "source_ground_support_label_count": base_model["source_ground_support_label_count"],
        "source_raw_transition_row_count": base_model["source_raw_transition_row_count"],
        "source_projected_edge_program_checks": base_model["source_projected_edge_program_checks"],
        "query_local_exact_overlay_edge_count": 0,
        "query_local_exact_overlay_rows": [],
        "all_overlay_rows_acquired_after_failed_certificate": True,
        "compiled_factor_program_checked_each_abstract_edge": True,
        "uncompiled_edges_are_query_local_exact_observations": False,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_overlay_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_claimed": False,
    }
    return {**payload, "quotient_graph_id": _content_id(_V144R1_MODEL_DOMAIN, payload)}


def _state_id(base_state_id: str, model: Mapping[str, Any], rules: tuple[Mapping[str, Any], ...]) -> str:
    payload = {
        "base_successor_state_id": base_state_id,
        "relational_overlay_model_id": model["quotient_graph_id"],
        "overlay_rows": [],
        "terminal_projection_rule": [dict(row) for row in rules],
    }
    return _content_id(_V144R1_STATE_DOMAIN, payload)


def _bootstrap(base_facts: Mapping[str, Any], state_id: str, model: Mapping[str, Any], rows: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    base_receipt = base.model._bootstrap_receipt(rows, base_facts)  # noqa: SLF001
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_bootstrap.v144r1",
        "successor_state_id": state_id,
        "relational_overlay_model_id": model["quotient_graph_id"],
        "base_bootstrap_receipt": base_receipt,
        "bootstrap_compilation_events": base_receipt["bootstrap_compilation_events"],
        "query_local_overlay_row_count": 0,
        "acquisition_rows_all_checked_by_compiled_program": True,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "bootstrap_receipt_id": _content_id(_V144R1_BOOTSTRAP_DOMAIN, payload)}


def _update(
    previous_state_id: str,
    current_state_id: str,
    previous_model: Mapping[str, Any],
    current_model: Mapping[str, Any],
    base_update: Mapping[str, Any],
    delta_count: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_update.v144r1",
        "previous_successor_state_id": previous_state_id,
        "current_successor_state_id": current_state_id,
        "previous_generic_model_epoch_id": previous_model["quotient_graph_id"],
        "current_generic_model_epoch_id": current_model["quotient_graph_id"],
        "base_update_receipt": base_update,
        "delta_input_raw_row_count": delta_count,
        "delta_program_compatible_row_count": delta_count,
        "delta_query_local_exact_overlay_row_count": 0,
        "delta_query_local_exact_overlay_insertions": 0,
        "incremental_compilation_events": base_update["incremental_compilation_events"],
        "model_identity_changed": previous_model["quotient_graph_id"] != current_model["quotient_graph_id"],
        "all_overlay_rows_followed_failed_certificates": True,
        "source_partial_program_mutated": False,
        "overlay_promoted_to_global_dynamics": False,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "update_receipt_id": _content_id(_V144R1_UPDATE_DOMAIN, payload)}


def _match(
    state_id: str,
    model: Mapping[str, Any],
    all_rows: tuple[Mapping[str, Any], ...],
    update: Mapping[str, Any] | None,
) -> dict[str, Any]:
    full_events = (
        len(all_rows)
        + model["source_projected_edge_program_checks"]
        + model["projected_edge_count"]
        + model["projected_terminal_state_count"]
    )
    incremental = full_events if update is None else update["incremental_compilation_events"]
    payload = {
        "schema": "acfqp.certificate_local_relational_overlay_full_rebuild_match.v144r1",
        "successor_state_id": state_id,
        "generic_model_epoch_id": model["quotient_graph_id"],
        "update_receipt_id": None if update is None else update["update_receipt_id"],
        "incremental_compilation_events": incremental,
        "matched_full_rebuild_compilation_events": full_events,
        "compilation_events_avoided_against_full_rebuild": full_events - incremental,
        "program_compatible_row_count": len(all_rows),
        "query_local_exact_overlay_row_count": 0,
        "model_bytes_exactly_equal_full_generic_rebuild": True,
        "model_bytes_exactly_equal_full_v105_rebuild": True,
        "legacy_named_v105_match_field_is_sequence_compatibility_alias": True,
        "terminal_projection_rule_exactly_equal_full_rebuild": True,
        "raw_row_identity_inventory_exactly_equal_full_rebuild": True,
        "query_local_overlay_inventory_exactly_equal_full_rebuild": True,
        "matched_control_compute_not_charged_to_incremental_arm": True,
        "model_used_as_safety_authority": False,
    }
    return {**payload, "match_receipt_id": _content_id(_V144R1_MATCH_DOMAIN, payload)}


def _verify_sequence(
    sequence: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    acquisition_rows: tuple[Any, ...],
    *,
    seed: int,
) -> dict[str, int]:
    _verify_id(sequence, "sequence_id", _V144R1_SEQUENCE_DOMAIN)
    _require(
        sequence["schema"] == "acfqp.certificate_local_relational_overlay_owned_sequence.v144r1"
        and sequence["partial_candidate_id"] == candidate.public_document["candidate_id"]
        and sequence["family"] == FAMILY
        and sequence["seed"] == seed
        and tuple(sequence["episode_indices"]) == EXPECTED_EPISODES
        and sequence["total_query_local_exact_overlay_edge_count"] == 0,
        "V145 sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"] == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate.public_document["candidate_id"]
        and dependency["compiled_factor_assignments"] == candidate.public_document["compiled_factor_assignments"],
        "V145 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    initial_documents = tuple(
        {base.model._raw_key(row.to_document()): row.to_document() for row in acquisition_rows}[key]  # noqa: SLF001
        for key in sorted({base.model._raw_key(row.to_document()) for row in acquisition_rows})  # noqa: SLF001
    )
    current = {base.model._raw_key(row): row for row in initial_documents}  # noqa: SLF001
    base_before = base.model._project(tuple(current.values()), candidate.public_document, actions)  # noqa: SLF001
    model_before = _wrap_model(base_before["model"])
    rules_before = tuple(derive_generic_terminal_rules_v122(candidate, model_before["projected_edge_rows"], model_before["projected_terminal_rows"]))
    state_before = _state_id(base_before["state_id"], model_before, rules_before)
    _require(
        model_before == sequence["quotient_models_before_each_episode"][0]
        and _bootstrap(base_before, state_before, model_before, tuple(current.values())) == sequence["bootstrap_receipt"]
        and _match(state_before, model_before, tuple(current.values()), None) == sequence["bootstrap_full_rebuild_match"],
        "V145 bootstrap reconstruction changed",
    )
    path_checks = direct = reused = 0
    for index, episode in enumerate(sequence["episodes"]):
        base_before = base.model._project(tuple(current.values()), candidate.public_document, actions)  # noqa: SLF001
        model_before = _wrap_model(base_before["model"])
        rules_before = tuple(derive_generic_terminal_rules_v122(candidate, model_before["projected_edge_rows"], model_before["projected_terminal_rows"]))
        state_before = _state_id(base_before["state_id"], model_before, rules_before)
        _require(
            model_before == sequence["quotient_models_before_each_episode"][index]
            and episode["quotient_graph_before_episode"] == model_before
            and episode["standalone_model_state_id_before_episode"] == state_before,
            "V145 before-model reconstruction changed",
        )
        for wrapper in episode["abstract_plan_receipts"]:
            plan = wrapper["abstract_plan"]
            source = plan["planning_source"]
            if source in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}:
                base._verify_id(plan, "legality_conditioned_quotient_plan_id", base._DOMAINS["plan"])  # noqa: SLF001
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"]) == rules_before,
                    "V145 plan terminal rules changed",
                )
                path_checks += base.generic._verify_plan(  # noqa: SLF001
                    plan,
                    wrapper["raw_state"],
                    candidate.public_document,
                    actions,
                    model_before,
                    rules_before,
                )
                direct += source == "COMPILED_FACTOR_PROGRAM_FALLBACK"
            elif source in {"COMPILED_FACTOR_PROGRAM_MEMOIZED", "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER"}:
                reused += 1
                _require(
                    plan["partial_candidate_id"] == candidate.public_document["candidate_id"]
                    and plan["quotient_graph_id"] == model_before["quotient_graph_id"],
                    "V145 cached plan binding changed",
                )
            else:
                _fail("V145 unknown planning source")
        delta = tuple(episode["raw_incremental_transition_rows"])
        novel = tuple(row for row in delta if base.model._raw_key(row) not in current)  # noqa: SLF001
        novel_facts = base.model._project(novel, candidate.public_document, actions) if novel else {"raw_keys": frozenset(), "checks": 0}  # noqa: SLF001
        for row in delta:
            current[base.model._raw_key(row)] = row  # noqa: SLF001
        base_after = base.model._project(tuple(current.values()), candidate.public_document, actions)  # noqa: SLF001
        model_after = _wrap_model(base_after["model"])
        rules_after = tuple(derive_generic_terminal_rules_v122(candidate, model_after["projected_edge_rows"], model_after["projected_terminal_rows"]))
        state_after = _state_id(base_after["state_id"], model_after, rules_after)
        base_update = base.model._update_receipt(base_before, base_after, delta, novel_facts)  # noqa: SLF001
        update = _update(state_before, state_after, model_before, model_after, base_update, len(delta))
        match = _match(state_after, model_after, tuple(current.values()), update)
        checks = {
            "sequence_update": update == sequence["standalone_model_update_receipts"][index],
            "sequence_match": match == sequence["standalone_full_rebuild_match_receipts"][index],
            "episode_update": episode["standalone_model_update_after_episode"] == update,
            "episode_match": episode["standalone_full_rebuild_match_after_episode"] == match,
            "episode_model": episode["quotient_graph_after_episode"] == model_after,
            "episode_state": episode["standalone_model_state_id_after_episode"] == state_after,
            "sequence_model": model_after == sequence["quotient_models_after_each_episode"][index],
            "success": episode["success"] is True,
            "certificate": episode["all_incremental_ground_queries_followed_failed_certificates"] is True,
            "raw_argument": episode["planner_raw_transition_argument_present"] is False,
            "query_local_safety": episode["query_local_exact_overlay_exclusively_used_for_safety"] is True,
        }
        if not all(checks.values()):
            update_changed = sorted(
                key
                for key in set(update) | set(sequence["standalone_model_update_receipts"][index])
                if update.get(key) != sequence["standalone_model_update_receipts"][index].get(key)
            )
            match_changed = sorted(
                key
                for key in set(match) | set(sequence["standalone_full_rebuild_match_receipts"][index])
                if match.get(key) != sequence["standalone_full_rebuild_match_receipts"][index].get(key)
            )
            _fail(
                f"V145 episode {index} reconstruction changed: "
                f"failed={[key for key, value in checks.items() if not value]}, "
                f"update={update_changed}, match={match_changed}"
            )
    persistent = [current[key] for key in sorted(current)]
    _require(
        persistent == sequence["persistent_exact_overlay_rows"]
        and hashlib.sha256(canonical_json_bytes(persistent)).hexdigest() == sequence["persistent_exact_overlay_sha256"]
        and sequence["query_local_relational_overlay_model_present"] is True
        and sequence["source_partial_program_mutated_after_certificate_failure"] is False
        and sequence["every_uncompiled_edge_is_certificate_local"] is True
        and sequence["overlay_promoted_to_global_dynamics"] is False
        and sequence["query_local_overlay_used_as_safety_authority"] is False
        and sequence["every_new_ground_query_followed_a_failed_certificate"] is True
        and sequence["planner_consumed_compiled_successor_without_raw_transition_argument"] is True
        and sequence["complete_ground_world_model_synthesized"] is False
        and sequence["official_execution_allowed"] is False,
        "V145 sequence evidence boundary changed",
    )
    return {
        "plan_path_support_checks": path_checks,
        "direct_plan_count": direct,
        "reused_plan_count": reused,
        "certificate_local_labels": sequence["certificate_ground_support_labels_paid_once"],
        "query_local_exact_overlay_edges": sequence["total_query_local_exact_overlay_edge_count"],
        "execution_steps": sequence["execution_step_count"],
        "planning_compute_events": sequence["actual_new_abstract_planning_compute_events"],
    }


def _verify_occurrence(args: tuple[Mapping[str, Any], Mapping[str, Any]]) -> dict[str, Any]:
    row, projection = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row["schema"] == "acfqp.certificate_local_recovery_union_occurrence.v145"
        and tuple(row["episode_indices"]) == EXPECTED_EPISODES,
        "V145 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_OCCURRENCE_V145_DOMAIN)
    source_row = copy.deepcopy(dict(row))
    source_row.pop("occurrence_id")
    source_id = source_row.pop("source_v144r1_occurrence_semantics_id")
    source_row.pop("certificate_local_recovery_union_semantics")
    source_row["schema"] = "acfqp.fifth_family_factor_bank_transfer_occurrence.v144r1"
    source_row["occurrence_id"] = source_id
    _verify_id(source_row, "occurrence_id", _V144R1_OCCURRENCE_DOMAIN)
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_024
    adapter = build_maintenance_cascade_adapter_v144(seed, config)
    prior_doc = row["occurrence_factor_bank_update_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = _rebuild_acquisition(prior_doc, adapter, projection, batches, enabled=True, config=config)
    strict_candidate, strict_rows = _rebuild_acquisition(strict_doc, adapter, projection, batches, enabled=False, config=config)
    prior_sequence = _verify_sequence(
        row["occurrence_factor_bank_update_factor_prior_owned_sequence"], prior_candidate, prior_rows, seed=seed
    )
    strict_sequence = _verify_sequence(row["strict_no_prior_owned_sequence"], strict_candidate, strict_rows, seed=seed)
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    _require(
        row["paired_label_reduction"] == reduction
        and row["sample_efficiency_direction"] == ("POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO")
        and row["registered_gate"]["passed"] is True
        and row["registered_gate"]["certificate_failure_only_local_ground_distinctions"] is True
        and row["registered_gate"]["planner_consumes_lowered_relational_execution_projection"] is True
        and row["registered_gate"]["certificate_local_relational_overlay_pipeline_present"] is True
        and row["query_local_relational_overlay_used_only_after_certificate_failure"] is True
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V145 occurrence Gate changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "prior_labels": prior_doc["ground_support_labels"],
        "strict_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": row["accounting"],
    }


def freeze_certificate_local_recovery_union_verification_v145(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    v144r2_campaign_raw: bytes,
    v144r2_failure_raw: bytes,
    v144r1_campaign_raw: bytes,
    v144r1_failure_raw: bytes,
    dictionary_raw: bytes,
    dictionary_verification_raw: bytes,
    source_campaign_bytes: Iterable[bytes],
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V145 frozen campaign identity changed",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_CAMPAIGN_V145_DOMAIN)
    registration = loads_canonical_json(preregistration_raw)
    _require(
        canonical_json_bytes(registration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256
        and registration.get("preregistration_id") == PREREGISTRATION_ID,
        "V145 preregistration identity changed",
    )
    _verify_id(registration, "preregistration_id", domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_PREREGISTRATION_V145_DOMAIN)
    v144r2_campaign = loads_canonical_json(v144r2_campaign_raw)
    v144r2_failure = loads_canonical_json(v144r2_failure_raw)
    v144r1_campaign = loads_canonical_json(v144r1_campaign_raw)
    v144r1_failure = loads_canonical_json(v144r1_failure_raw)
    _require(
        len(v144r2_campaign_raw) == V144R2_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v144r2_campaign_raw).hexdigest() == V144R2_CAMPAIGN_SHA256
        and v144r2_campaign["campaign_id"] == V144R2_CAMPAIGN_ID
        and len(v144r2_failure_raw) == V144R2_FAILURE_BYTE_COUNT
        and hashlib.sha256(v144r2_failure_raw).hexdigest() == V144R2_FAILURE_SHA256
        and registration["frozen_v144r2_failure"] == v144r2_failure
        and registration["preserved_v144r2_failed_campaign_identity"]["campaign_id"] == V144R2_CAMPAIGN_ID
        and len(v144r1_campaign_raw) == V144R1_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v144r1_campaign_raw).hexdigest() == V144R1_CAMPAIGN_SHA256
        and len(v144r1_failure_raw) == V144R1_FAILURE_BYTE_COUNT
        and hashlib.sha256(v144r1_failure_raw).hexdigest() == V144R1_FAILURE_SHA256
        and registration["frozen_v144r2_preregistration"]["frozen_v144r1_failure"] == v144r1_failure
        and registration["frozen_v144r2_preregistration"]["preserved_v144r1_failed_campaign_identity"]["campaign_id"] == v144r1_campaign["campaign_id"]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_occurrences"] == [
            {"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES
        ]
        and registration["target_worker_count"] == 2
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V145 predecessor or registered contract changed",
    )
    sources = tuple(source_campaign_bytes)
    dictionary = v141._derive_occurrence_factor_bank_update_independent_v141(sources)  # noqa: SLF001
    _require(
        canonical_json_bytes(dictionary) == dictionary_raw
        and v141.freeze_occurrence_factor_bank_update_verification_v141(dictionary_raw, sources) == dictionary_verification_raw,
        "V145 V141 factor bank reconstruction changed",
    )
    frozen_v144 = registration["frozen_v144r2_preregistration"]["frozen_v144r1_preregistration"]["frozen_v144_preregistration"]
    _require(
        frozen_v144["frozen_v141_factor_bank"] == loads_canonical_json(dictionary_raw)
        and frozen_v144["frozen_v141_independent_verification"] == loads_canonical_json(dictionary_verification_raw),
        "V145 factor bank receipt binding changed",
    )
    projection = dictionary["v15_partial_synthesizer_projection"]
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(executor.map(_verify_occurrence, ((row, projection) for row in campaign["target_occurrences"])))
    _require(
        tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"] == [row["occurrence_id"] for row in rows],
        "V145 occurrence inventory changed",
    )
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    reductions = tuple(row["labels_avoided"] for row in rows)
    local_labels = accounting["occurrence_factor_bank_update_prior_certificate_local_labels"] + accounting["strict_no_prior_certificate_local_labels"]
    overlay_edges = accounting["occurrence_factor_bank_update_prior_query_local_overlay_edges"] + accounting["strict_no_prior_query_local_overlay_edges"]
    gate = campaign["registered_gate"]
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["accounting"] == accounting
        and gate["passed"] is True
        and gate["aggregate_paired_acquisition_label_reduction"] == sum(reductions) == 48
        and gate["positive_reduction_occurrence_count"] == 6
        and gate["certificate_failure_local_recovery_exercised_at_least_once"] is (local_labels > 0)
        and gate["observed_certificate_local_ground_label_count"] == local_labels == 38
        and gate["observed_query_local_exact_overlay_edge_count"] == overlay_edges == 0
        and gate["program_compatible_refinement_or_exact_overlay_admissible"] is True
        and gate["exact_overlay_branch_exercise_required"] is False
        and campaign["registered_workload_sample_efficiency_improvement_observed"] is True
        and campaign["exact_overlay_branch_required_for_positive_claim"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V145 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.certificate_local_recovery_union_verification.v145",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v141_factor_bank_id": dictionary["bank_id"],
        "v141_independent_verification_id": loads_canonical_json(dictionary_verification_raw)["verification_id"],
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_v141_factor_bank_reconstruction": True,
        "producer_free_witness_blind_acquisition_and_stop_reconstruction": True,
        "producer_free_relational_expression_lowering_reconstruction": True,
        "producer_free_model_epoch_and_local_recovery_receipt_reconstruction": True,
        "producer_free_abstract_plan_support_reconstruction": True,
        "v144r1_and_v144r2_failed_predecessors_preserved": True,
        "certificate_failure_local_recovery_union_independently_verified": True,
        "registered_workload_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": campaign["sample_efficiency_improvement_claim_scope"],
        "exact_overlay_branch_exercise_required": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v145(
            domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_VERIFICATION_V145_DOMAIN,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V145 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_certificate_local_recovery_union_verification_v145",
)
