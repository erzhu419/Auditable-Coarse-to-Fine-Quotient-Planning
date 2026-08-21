"""Calibrate a target-local terminal overlay above a reusable residual model.

V92 showed that the anonymous residual successor program can remain compatible
while a source terminal tree fails on a fresh occurrence.  This additive
module therefore aligns and checks only the reusable partial/residual dynamics,
then learns a target-local terminal/status program prequentially from the
already registered common-partial prefix.  The overlay is frozen before the
target episode and remains proposal-only.
"""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    _minimal_terminal_frontier,
    _partial_support,
    _value,
    verify_joint_successor_version_space_model_v42,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    align_generic_occurrence_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
    synthesize_relational_terminal_program_v28,
)
from acfqp.generic_version_space_target_planner_v68 import (
    _AlignedTargetAdapterV68,
    _model_reference_inputs,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericTerminalOverlayVersionSpacePlannerV69Error(ValueError):
    pass


_ALIGNMENT_DOMAIN = b"acfqp:generic-residual-only-target-alignment:v69\x00"
_CANDIDATE_DOMAIN = b"acfqp:generic-terminal-overlay-target-candidate:v69\x00"
_OVERLAY_DOMAIN = b"acfqp:generic-prequential-terminal-overlay:v69\x00"
_PLAN_DOMAIN = b"acfqp:generic-terminal-overlay-version-space-plan:v69\x00"


def _fail(message: str) -> NoReturn:
    raise GenericTerminalOverlayVersionSpacePlannerV69Error(message)


def _identifier(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _groups(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[tuple[FlatRawTransitionV4, ...], ...]:
    grouped: dict[tuple[tuple[int, ...], int], list[FlatRawTransitionV4]] = {}
    order = []
    for row in rows:
        key = (row.pre, row.action.key)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        elif grouped[key][0].action != row.action:
            _fail("V69 one physical query carried multiple action descriptors")
        grouped[key].append(row)
    return tuple(tuple(grouped[key]) for key in order)


def _label(row: FlatRawTransitionV4) -> str:
    if row.legal_after:
        if row.terminal_acceptance_after is not None:
            _fail("V69 active row carried a terminal label")
        return "ACTIVE"
    if row.terminal_acceptance_after is True:
        return "ACCEPT"
    if row.terminal_acceptance_after is False:
        return "REJECT"
    _fail("V69 terminal row omitted its acceptance label")


def _evidence(
    candidate: PartialFactorCandidateV15,
    groups: tuple[tuple[FlatRawTransitionV4, ...], ...],
) -> dict[str, Any]:
    rows = [row.to_document() for group in groups for row in group]
    return {
        "layout": copy.deepcopy(candidate.public_document["layout"]),
        "unknown_residual_target_columns": list(
            candidate.public_document["unknown_residual_target_columns"]
        ),
        "raw_transition_rows": rows,
    }


def _frontier_exact(
    program: Mapping[str, Any], group: tuple[FlatRawTransitionV4, ...]
) -> bool:
    try:
        frontier = _minimal_terminal_frontier(program)
    except Exception as error:
        if error.__class__.__module__.startswith("acfqp.generic_"):
            return False
        raise
    status_target = program.get("status_target_column")
    if type(status_target) is not int:
        return False
    for row in group:
        expected = _label(row)
        for candidate in frontier:
            prediction = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": candidate["decision_tree"],
                },
                row.post,
            )
            if (
                prediction.get("terminal_class") != expected
                or prediction.get("status_token") != row.post[status_target]
            ):
                return False
    return True


def acquire_prequential_terminal_overlay_v69(
    candidate: PartialFactorCandidateV15,
    aligned_rows: tuple[FlatRawTransitionV4, ...],
    *,
    source_model_id: str,
    confidence_denominator: int,
    maximum_program_candidates: int,
) -> dict[str, Any]:
    """Issue, test, retire, and freeze a target terminal program online."""
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(aligned_rows) is not tuple
        or not aligned_rows
        or type(source_model_id) is not str
        or len(source_model_id) != 64
        or type(confidence_denominator) is not int
        or confidence_denominator <= 1
        or type(maximum_program_candidates) is not int
        or not 1 <= maximum_program_candidates <= 128
    ):
        _fail("V69 terminal-overlay acquisition inventory changed")
    groups = _groups(aligned_rows)
    program = None
    issuance_label = None
    stopped_label = None
    success_count = 0
    epoch = 0
    retired = []
    history = []
    for index, group in enumerate(groups):
        physical_label = index + 1
        if program is not None:
            exact = _frontier_exact(program, group)
            if exact:
                success_count += 1
                numerator = 2 ** (success_count + 1) - 1
                denominator = success_count + 1
                epoch_threshold = confidence_denominator * (epoch + 1) * (epoch + 2)
                stopped = numerator >= denominator * epoch_threshold
                history.append(
                    {
                        "physical_ground_support_label": physical_label,
                        "candidate_epoch": epoch,
                        "terminal_program_id": program["terminal_program_id"],
                        "exact_prequential_prediction": True,
                        "post_issuance_exact_prediction_success_count": success_count,
                        "universal_mixture_evalue_numerator": numerator,
                        "universal_mixture_evalue_denominator": denominator,
                        "evalue_threshold": epoch_threshold,
                        "stopped": stopped,
                    }
                )
                if stopped and stopped_label is None:
                    stopped_label = physical_label
                continue
            retired.append(
                {
                    "candidate_epoch": epoch,
                    "terminal_program_id": program["terminal_program_id"],
                    "failed_physical_ground_support_label": physical_label,
                    "reason": "PREQUENTIAL_TERMINAL_PREDICTION_FAILED",
                }
            )
            history.append(
                {
                    "physical_ground_support_label": physical_label,
                    "candidate_epoch": epoch,
                    "terminal_program_id": program["terminal_program_id"],
                    "exact_prequential_prediction": False,
                    "post_issuance_exact_prediction_success_count": success_count,
                    "stopped": False,
                }
            )
            epoch += 1
            program = None
            success_count = 0
            issuance_label = None
            stopped_label = None
        try:
            proposal = synthesize_relational_terminal_program_v28(
                _evidence(candidate, groups[:physical_label]),
                maximum_program_candidates=maximum_program_candidates,
            )
        except Exception as error:
            if not error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            history.append(
                {
                    "physical_ground_support_label": physical_label,
                    "candidate_epoch": epoch,
                    "terminal_program_id": None,
                    "candidate_issued": False,
                    "reason": str(error),
                    "stopped": False,
                }
            )
            continue
        program = proposal
        issuance_label = physical_label
        history.append(
            {
                "physical_ground_support_label": physical_label,
                "candidate_epoch": epoch,
                "terminal_program_id": program["terminal_program_id"],
                "candidate_issued": True,
                "post_issuance_exact_prediction_success_count": 0,
                "stopped": False,
            }
        )
    if program is None or issuance_label is None or stopped_label is None:
        _fail("V69 terminal overlay did not close before its common-prefix cap")
    continued_groups = groups[stopped_label:]
    frontier = _minimal_terminal_frontier(program)
    if program["status_target_column"] not in candidate.public_document[
        "unknown_residual_target_columns"
    ]:
        _fail("V69 target terminal overlay changed its anonymous status binding")
    payload = {
        "schema": "acfqp.generic_prequential_terminal_overlay.v69",
        "source_model_id": source_model_id,
        "target_candidate_id": candidate.public_document["candidate_id"],
        "target_common_partial_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in aligned_rows])
        ).hexdigest(),
        "physical_query_group_count": len(groups),
        "confidence_denominator": confidence_denominator,
        "maximum_program_candidates": maximum_program_candidates,
        "selected_terminal_program": copy.deepcopy(program),
        "selected_terminal_program_id": program["terminal_program_id"],
        "selected_mdl_minimal_terminal_frontier": frontier,
        "selected_mdl_minimal_terminal_candidate_count": len(frontier),
        "candidate_epoch": epoch,
        "candidate_issued_at_physical_ground_support_label": issuance_label,
        "candidate_confidence_crossing_ground_support_label": stopped_label,
        "joint_acquisition_stop_ground_support_labels": len(groups),
        "post_issuance_exact_prediction_success_count": success_count,
        "retired_terminal_candidate_count": len(retired),
        "retired_terminal_candidates": retired,
        "prequential_history": history,
        "post_confidence_ground_query_count_required_by_other_joint_obligations": len(
            continued_groups
        ),
        "post_confidence_raw_transition_row_count_required_by_other_joint_obligations": sum(
            map(len, continued_groups)
        ),
        "prequential_confidence_stop_reached": True,
        "post_confidence_rows_remained_exact": all(
            _frontier_exact(program, group) for group in continued_groups
        ),
        "fixed_confirmation_block_used": False,
        "heldout_prediction_claimed": False,
        "target_episode_outcomes_used": False,
        "source_residual_model_refit": False,
        "target_terminal_overlay_used_as_safety_authority": False,
        "global_exact_terminal_dynamics_claimed": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "terminal_overlay_id": _identifier(_OVERLAY_DOMAIN, payload),
    }


def _check_residual_prefix(
    model: Mapping[str, Any], rows: tuple[FlatRawTransitionV4, ...]
) -> dict[str, int]:
    partial_evaluations = 0
    residual_evaluations = 0
    source_terminal_mismatches = 0
    source_terminal = model["mdl_minimal_terminal_candidate_frontier"]
    status_target = model["status_target_column"]
    for row in rows:
        for assignment in model["known_partial_factor_assignments"]:
            partial_evaluations += 1
            if row.post[assignment["target_column"]] not in _partial_support(
                assignment, row.pre, row.action.fields
            ):
                _fail("V69 source partial factor missed the target prefix")
        for space in model["residual_version_spaces"]:
            target = space["target_column"]
            for expression in space["batch_exact_candidate_frontier"]:
                residual_evaluations += 1
                values = _value(
                    expression["normalized_expression"],
                    row.pre,
                    row.action.fields,
                    target,
                    expression.get("action_field_binding"),
                    expression.get("anonymous_integer_constant_binding"),
                )
                if row.post[target] not in values:
                    _fail("V69 retained residual expression missed the target prefix")
        expected = _label(row)
        for terminal in source_terminal:
            prediction = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": terminal["decision_tree"],
                },
                row.post,
            )
            if (
                prediction.get("terminal_class") != expected
                or prediction.get("status_token") != row.post[status_target]
            ):
                source_terminal_mismatches += 1
    return {
        "partial_replay_evaluations": partial_evaluations,
        "residual_replay_evaluations": residual_evaluations,
        "source_terminal_tree_mismatch_count": source_terminal_mismatches,
    }


def prepare_terminal_overlay_target_inputs_v69(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    *,
    layout_domain: str,
    layout_observed_rows: tuple[FlatRawTransitionV4, ...] | None = None,
    terminal_confidence_denominator: int,
    maximum_terminal_program_candidates: int,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    _AlignedTargetAdapterV68,
    PartialFactorCandidateV15,
    tuple[FlatRawTransitionV4, ...],
]:
    verified = verify_joint_successor_version_space_model_v42(model)
    if (
        type(target_candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or target_candidate.public_document.get("state_width")
        != verified["state_width"]
        or target_candidate.public_document.get("action_field_width")
        != verified["action_field_width"]
    ):
        _fail("V69 target alignment inventory changed")
    layout_rows = observed_rows if layout_observed_rows is None else layout_observed_rows
    if type(layout_rows) is not tuple or not layout_rows:
        _fail("V69 target layout prefix inventory changed")
    reference_rows, reference_catalogue, reference_layout = (
        _model_reference_inputs(verified)
    )
    matched_layout = match_generic_layout_meta_prior_v5(
        reference_rows,
        reference_catalogue,
        reference_layout,
        layout_rows,
        adapter.catalogue,
        layout_domain=layout_domain,
    )
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        observed_rows,
        adapter.catalogue,
        matched_layout,
        canonical_occurrence=0,
    )
    replay = _check_residual_prefix(verified, aligned_rows)
    width = verified["state_width"]
    action_width = verified["action_field_width"]
    identity_layout = DiscoveredLayoutV5(
        tuple(range(width)),
        tuple(range(action_width)),
        tuple(verified["source_layout"]["state_structural_colors"]),
        tuple(verified["source_layout"]["action_structural_colors"]),
        verified["source_layout"]["schema_signature"],
        0,
        replay["partial_replay_evaluations"]
        + replay["residual_replay_evaluations"],
        hashlib.sha256(
            b"acfqp:generic-terminal-overlay-identity-layout:v69\x00"
            + canonical_json_bytes(
                {
                    "source_model_id": verified[
                        "joint_successor_version_space_model_id"
                    ],
                    "target_partial_candidate_id": target_candidate.public_document[
                        "candidate_id"
                    ],
                    "state_order": list(range(width)),
                    "action_order": list(range(action_width)),
                }
            )
        ).hexdigest(),
        verified["source_layout"]["layout_id"],
        matched_layout.graph_edit_score,
        matched_layout.cross_occurrence_value_overlap,
    )
    candidate_payload = {
        "schema": "acfqp.generic_terminal_overlay_target_candidate.v69",
        "source_factor_library_id": target_candidate.public_document[
            "source_factor_library_id"
        ],
        "target_partial_candidate_id": target_candidate.public_document[
            "candidate_id"
        ],
        "source_model_id": verified["joint_successor_version_space_model_id"],
        "layout": identity_layout.to_document(),
        "state_width": width,
        "action_field_width": action_width,
        "compiled_factor_assignments": copy.deepcopy(
            verified["known_partial_factor_assignments"]
        ),
        "unknown_residual_target_columns": sorted(
            [
                *[
                    row["target_column"]
                    for row in verified["residual_version_spaces"]
                ],
                verified["status_target_column"],
            ]
        ),
        "transformed_observation_count": len(aligned_rows),
        "transformed_observation_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in aligned_rows])
        ).hexdigest(),
        "source_residual_model_refit": False,
        "source_terminal_program_reused_without_applicability_check": False,
        "planning_authority_present": False,
        "complete_world_model_claimed": False,
    }
    candidate_document = {
        **candidate_payload,
        "candidate_id": _identifier(_CANDIDATE_DOMAIN, candidate_payload),
    }
    candidate = PartialFactorCandidateV15(
        candidate_document,
        identity_layout,
        tuple(verified["known_partial_factor_assignments"]),
        aligned_rows,
    )
    overlay = acquire_prequential_terminal_overlay_v69(
        candidate,
        aligned_rows,
        source_model_id=verified["joint_successor_version_space_model_id"],
        confidence_denominator=terminal_confidence_denominator,
        maximum_program_candidates=maximum_terminal_program_candidates,
    )
    if overlay["selected_terminal_program"]["status_target_column"] != verified[
        "status_target_column"
    ]:
        _fail("V69 target terminal overlay changed the source status coordinate")
    alignment_payload = {
        "schema": "acfqp.generic_residual_only_target_alignment.v69",
        "source_model_id": verified["joint_successor_version_space_model_id"],
        "target_partial_candidate_id": target_candidate.public_document[
            "candidate_id"
        ],
        "projected_target_candidate_id": candidate_document["candidate_id"],
        "target_common_partial_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in layout_rows])
        ).hexdigest(),
        "target_common_partial_raw_transition_count": len(layout_rows),
        "target_joint_calibration_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in observed_rows])
        ).hexdigest(),
        "target_joint_calibration_raw_transition_count": len(observed_rows),
        "matched_target_layout": matched_layout.to_document(),
        "source_state_to_target_raw": list(
            matched_layout.state_canonical_to_raw
        ),
        "source_action_to_target_raw": list(
            matched_layout.action_canonical_to_raw
        ),
        "graph_edit_score": matched_layout.graph_edit_score,
        "cross_occurrence_value_overlap": (
            matched_layout.cross_occurrence_value_overlap
        ),
        **replay,
        "source_partial_and_residual_programs_exact_on_target_prefix": True,
        "source_terminal_tree_applicability_required": False,
        "source_terminal_mismatch_preserved_not_silently_ignored": True,
        "alignment_derived_only_from_target_common_partial_observations": True,
        "target_episode_outcomes_used": False,
        "alignment_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    alignment = {
        **alignment_payload,
        "alignment_id": _identifier(_ALIGNMENT_DOMAIN, alignment_payload),
    }
    projected = _AlignedTargetAdapterV68(
        adapter,
        adapter.family,
        adapter.seed,
        adapter.kernel,
        aligned_catalogue,
        tuple(matched_layout.state_canonical_to_raw),
    )
    return alignment, overlay, projected, candidate, aligned_rows


def plan_terminal_overlay_version_space_v69(
    model: Mapping[str, Any],
    terminal_overlay: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_state: tuple[int, ...],
    *,
    maximum_depth: int,
    maximum_robust_state_depth_evaluations: int,
    maximum_support_branch_evaluations: int,
    support_feasible_beam_width: int,
) -> dict[str, Any]:
    """Plan with source residuals and the target-local terminal frontier."""
    verified = verify_joint_successor_version_space_model_v42(model)
    if (
        type(terminal_overlay) is not dict
        or type(target_candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
        or type(initial_state) is not tuple
        or maximum_depth <= 0
        or maximum_robust_state_depth_evaluations <= 0
        or maximum_support_branch_evaluations <= 0
        or support_feasible_beam_width <= 0
    ):
        _fail("V69 planning inventory changed")
    overlay_payload = {
        key: value
        for key, value in terminal_overlay.items()
        if key != "terminal_overlay_id"
    }
    if (
        _identifier(_OVERLAY_DOMAIN, overlay_payload)
        != terminal_overlay.get("terminal_overlay_id")
        or terminal_overlay.get("source_model_id")
        != verified["joint_successor_version_space_model_id"]
        or terminal_overlay.get("prequential_confidence_stop_reached") is not True
        or terminal_overlay.get("fixed_confirmation_block_used") is not False
        or terminal_overlay.get("heldout_prediction_claimed") is not False
        or terminal_overlay.get("target_terminal_overlay_used_as_safety_authority")
        is not False
    ):
        _fail("V69 terminal overlay identity or authority changed")
    target = target_candidate.public_document
    if (
        target.get("compiled_factor_assignments")
        != verified["known_partial_factor_assignments"]
        or target.get("unknown_residual_target_columns")
        != sorted(
            [
                *[
                    row["target_column"]
                    for row in verified["residual_version_spaces"]
                ],
                verified["status_target_column"],
            ]
        )
        or target.get("layout", {}).get("state_canonical_to_raw")
        != list(range(verified["state_width"]))
        or target.get("layout", {}).get("action_canonical_to_raw")
        != list(range(verified["action_field_width"]))
    ):
        _fail("V69 projected target candidate changed")
    partial = {
        row["target_column"]: row
        for row in verified["known_partial_factor_assignments"]
    }
    residual = {
        row["target_column"]: row["batch_exact_candidate_frontier"]
        for row in verified["residual_version_spaces"]
    }
    status_target = verified["status_target_column"]
    terminal_program = terminal_overlay["selected_terminal_program"]
    terminal_frontier = terminal_overlay[
        "selected_mdl_minimal_terminal_frontier"
    ]
    if (
        terminal_program.get("status_target_column") != status_target
        or not terminal_frontier
    ):
        _fail("V69 target terminal frontier changed")

    def terminal_predictions(state: tuple[int, ...]) -> tuple[tuple[str, int], ...]:
        values = set()
        for row in terminal_frontier:
            result = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": row["decision_tree"],
                },
                state,
            )
            classification = result.get("terminal_class")
            token = result.get("status_token")
            if classification not in ("ACTIVE", "ACCEPT", "REJECT") or type(token) is not int:
                _fail("V69 target terminal prediction changed")
            values.add((classification, token))
        return tuple(sorted(values))

    branch_evaluations = 0
    maximum_branch_width = 0

    def successors(
        state: tuple[int, ...], action: FlatRawActionV4
    ) -> tuple[tuple[int, ...], ...]:
        nonlocal maximum_branch_width
        targets = sorted((*partial, *residual))
        supports = []
        for column in targets:
            if column in partial:
                values = _partial_support(partial[column], state, action.fields)
            else:
                found = set()
                for expression in residual[column]:
                    found.update(
                        _value(
                            expression["normalized_expression"],
                            state,
                            action.fields,
                            column,
                            expression.get("action_field_binding"),
                            expression.get("anonymous_integer_constant_binding"),
                        )
                    )
                values = tuple(sorted(found))
            if not values:
                _fail("V69 compiled successor support became empty")
            supports.append(values)
        width = math.prod(map(len, supports))
        if width > maximum_support_branch_evaluations:
            _fail("V69 one-step support crossed its compute cap")
        result = set()
        for values in product(*supports):
            projected = list(state)
            for column, value in zip(targets, values, strict=True):
                projected[column] = value
            for _classification, token in terminal_predictions(tuple(projected)):
                row = list(projected)
                row[status_target] = token
                result.add(tuple(row))
        maximum_branch_width = max(maximum_branch_width, len(result))
        return tuple(sorted(result))

    def consensus_class(state: tuple[int, ...]) -> str | None:
        classes = {row[0] for row in terminal_predictions(state)}
        return next(iter(classes)) if len(classes) == 1 else None

    robust_calls = 0
    robust_truncated = False
    visiting: set[tuple[tuple[int, ...], int]] = set()
    policy: dict[tuple[int, ...], int] = {}

    @lru_cache(maxsize=None)
    def robust(state: tuple[int, ...], depth: int) -> bool:
        nonlocal branch_evaluations, robust_calls, robust_truncated
        robust_calls += 1
        classification = consensus_class(state)
        if classification == "ACCEPT":
            return True
        if classification in (None, "REJECT"):
            return False
        if (
            depth == 0
            or (state, depth) in visiting
            or robust_calls > maximum_robust_state_depth_evaluations
            or branch_evaluations >= maximum_support_branch_evaluations
        ):
            robust_truncated = (
                robust_calls > maximum_robust_state_depth_evaluations
                or branch_evaluations >= maximum_support_branch_evaluations
            )
            return False
        visiting.add((state, depth))
        for action in catalogue:
            branch = successors(state, action)
            branch_evaluations += len(branch)
            if branch_evaluations > maximum_support_branch_evaluations:
                robust_truncated = True
                visiting.remove((state, depth))
                return False
            progressing = tuple(value for value in branch if value != state)
            if progressing and all(robust(value, depth - 1) for value in progressing):
                policy[state] = action.key
                visiting.remove((state, depth))
                return True
        visiting.remove((state, depth))
        return False

    closed = robust(initial_state, maximum_depth)
    support_path: list[int] = []
    if not closed:
        predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {
            initial_state: None
        }
        goal = None
        frontier_states = (initial_state,)
        accepting_rows = [
            row.post
            for row in target_candidate.issuance_rows
            if row.terminal_acceptance_after is True
        ]

        def distance(state: tuple[int, ...]) -> int:
            if not accepting_rows:
                return 0
            return min(
                sum(abs(left - right) for left, right in zip(state, prototype, strict=True))
                for prototype in accepting_rows
            )

        for _depth in range(maximum_depth):
            next_rows: dict[
                tuple[int, ...], tuple[tuple[int, ...], int]
            ] = {}
            for state in frontier_states:
                if consensus_class(state) != "ACTIVE":
                    continue
                for action in catalogue:
                    branch = successors(state, action)
                    branch_evaluations += len(branch)
                    if branch_evaluations > maximum_support_branch_evaluations:
                        _fail("V69 support-feasible search crossed its compute cap")
                    for successor in branch:
                        classification = consensus_class(successor)
                        if (
                            successor == state
                            or classification in (None, "REJECT")
                            or successor in predecessor
                        ):
                            continue
                        edge = (state, action.key)
                        prior = next_rows.get(successor)
                        if prior is None or edge < prior:
                            next_rows[successor] = edge
            ranked = sorted(next_rows, key=lambda row: (distance(row), row))
            frontier_states = tuple(ranked[:support_feasible_beam_width])
            for successor in frontier_states:
                predecessor[successor] = next_rows[successor]
                if consensus_class(successor) == "ACCEPT":
                    goal = successor
                    break
            if goal is not None or not frontier_states:
                break
        if goal is None:
            _fail("V69 target-overlay version space found no abstract continuation")
        cursor = goal
        reverse = []
        while predecessor[cursor] is not None:
            parent, key = predecessor[cursor]
            reverse.append(key)
            cursor = parent
        support_path = list(reversed(reverse))
    first = policy.get(initial_state) if closed else support_path[0] if support_path else None
    if type(first) is not int:
        _fail("V69 target-overlay plan omitted its initial action")
    payload = {
        "schema": "acfqp.generic_terminal_overlay_version_space_plan.v69",
        "source_model_id": verified["joint_successor_version_space_model_id"],
        "terminal_overlay_id": terminal_overlay["terminal_overlay_id"],
        "target_candidate_id": target["candidate_id"],
        "initial_state": list(initial_state),
        "initial_action_key": first,
        "support_feasible_action_keys": support_path,
        "maximum_depth": maximum_depth,
        "retained_residual_expression_count": sum(map(len, residual.values())),
        "retained_target_terminal_tree_count": len(terminal_frontier),
        "abstract_state_depth_cache_count": robust.cache_info().currsize,
        "abstract_support_branch_evaluations": branch_evaluations,
        "maximum_joint_successor_support_width": maximum_branch_width,
        "robust_all_version_space_branches_closed": closed,
        "robust_search_resource_cap_reached": robust_truncated,
        "support_feasible_receding_plan_found": True,
        "all_source_residual_version_spaces_jointly_propagated": True,
        "all_target_mdl_minimal_terminal_trees_jointly_propagated": True,
        "source_terminal_frontier_used": False,
        "target_episode_ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    return {**payload, "plan_id": _identifier(_PLAN_DOMAIN, payload)}


__all__ = (
    "GenericTerminalOverlayVersionSpacePlannerV69Error",
    "acquire_prequential_terminal_overlay_v69",
    "plan_terminal_overlay_version_space_v69",
    "prepare_terminal_overlay_target_inputs_v69",
)
