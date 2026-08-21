"""Coordinate-align and certificate-check a reusable V42 version space.

The source model proposes a receding action from every retained successor and
terminal program.  It never discharges an unseen target obligation.  Missing
legality or transition support first produces a failed certificate, after
which one exact query-local distinction is added to an occurrence-local
overlay and the exact policy is recomputed.

Only the target common-partial prefix is available while the anonymous
source/target coordinate projection is selected.  Target episode outcomes are
not used to refit the source model or the projection.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    _partial_support,
    _value,
    plan_joint_successor_version_space_v42,
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
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericVersionSpaceTargetPlannerV68Error(ValueError):
    pass


_ALIGNMENT_DOMAIN = b"acfqp:generic-version-space-target-alignment:v68\x00"
_CANDIDATE_DOMAIN = b"acfqp:generic-version-space-target-candidate:v68\x00"
_EPISODE_DOMAIN = b"acfqp:generic-version-space-target-episode:v68\x00"
_ABLATION_DOMAIN = b"acfqp:generic-version-space-target-ablation:v68\x00"


def _fail(message: str) -> NoReturn:
    raise GenericVersionSpaceTargetPlannerV68Error(message)


def _identifier(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _layout(document: Any) -> DiscoveredLayoutV5:
    if type(document) is not dict:
        _fail("V68 source layout changed")
    try:
        result = DiscoveredLayoutV5(
            tuple(document["state_canonical_to_raw"]),
            tuple(document["action_canonical_to_raw"]),
            tuple(document["state_structural_colors"]),
            tuple(document["action_structural_colors"]),
            document["schema_signature"],
            document["refinement_rounds"],
            document["relation_evaluations"],
            document["layout_id"],
            document["reference_layout_id"],
            document["graph_edit_score"],
            document["cross_occurrence_value_overlap"],
        )
    except (KeyError, TypeError) as error:
        _fail(f"V68 source layout rejected: {error}")
    if result.to_document() != document:
        _fail("V68 source layout reconstruction diverged")
    return result


def _model_reference_inputs(
    model: Mapping[str, Any],
) -> tuple[
    tuple[FlatRawTransitionV4, ...],
    tuple[FlatRawActionV4, ...],
    DiscoveredLayoutV5,
]:
    verified = verify_joint_successor_version_space_model_v42(model)
    by_key: dict[int, FlatRawActionV4] = {}
    for document in verified["acquired_raw_transition_rows"]:
        selected = document.get("selected_action") if type(document) is dict else None
        key = selected.get("action_key") if type(selected) is dict else None
        fields = selected.get("anonymous_fields") if type(selected) is dict else None
        if type(key) is not int or type(fields) is not list:
            _fail("V68 source selected-action inventory changed")
        action = FlatRawActionV4(key, tuple(fields))
        previous = by_key.setdefault(key, action)
        if previous != action:
            _fail("V68 one source action key carried multiple descriptors")
    catalogue = tuple(by_key[key] for key in sorted(by_key))
    rows = []
    for index, document in enumerate(verified["acquired_raw_transition_rows"]):
        selected = document["selected_action"]
        try:
            row = FlatRawTransitionV4(
                0,
                index,
                tuple(document["pre_vector"]),
                tuple(document["legal_action_keys_before"]),
                by_key[selected["action_key"]],
                tuple(document["post_vector"]),
                tuple(document["legal_action_keys_after"]),
                document["terminal_acceptance_after"],
                document.get("outcome_tape_sha256"),
            )
        except (KeyError, TypeError, ValueError) as error:
            _fail(f"V68 source transition rejected: {error}")
        rows.append(row)
    return tuple(rows), catalogue, _layout(verified["source_layout"])


def _terminal_label(row: FlatRawTransitionV4) -> str:
    if row.legal_after:
        if row.terminal_acceptance_after is not None:
            _fail("V68 active target prefix row carried a terminal label")
        return "ACTIVE"
    if row.terminal_acceptance_after is True:
        return "ACCEPT"
    if row.terminal_acceptance_after is False:
        return "REJECT"
    _fail("V68 terminal target prefix row omitted its label")


def _model_replays_target_prefix(
    model: Mapping[str, Any], rows: tuple[FlatRawTransitionV4, ...]
) -> int:
    evaluations = 0
    assignments = model["known_partial_factor_assignments"]
    spaces = model["residual_version_spaces"]
    status_target = model["status_target_column"]
    terminal = model["mdl_minimal_terminal_candidate_frontier"]
    for row in rows:
        for assignment in assignments:
            evaluations += 1
            if row.post[assignment["target_column"]] not in _partial_support(
                assignment, row.pre, row.action.fields
            ):
                _fail("V68 source partial factor did not replay the target prefix")
        for space in spaces:
            target = space["target_column"]
            for expression in space["batch_exact_candidate_frontier"]:
                evaluations += 1
                values = _value(
                    expression["normalized_expression"],
                    row.pre,
                    row.action.fields,
                    target,
                    expression.get("action_field_binding"),
                    expression.get("anonymous_integer_constant_binding"),
                )
                if row.post[target] not in values:
                    _fail("V68 retained residual expression missed the target prefix")
        label = _terminal_label(row)
        for candidate in terminal:
            evaluations += 1
            prediction = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": candidate["decision_tree"],
                },
                row.post,
            )
            if (
                prediction.get("terminal_class") != label
                or prediction.get("status_token") != row.post[status_target]
            ):
                _fail("V68 retained terminal tree missed the target prefix")
    return evaluations


@dataclass(frozen=True, slots=True)
class _AlignedTargetAdapterV68:
    original: Any
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    state_canonical_to_raw: tuple[int, ...]

    def initial(self) -> Any:
        return self.original.initial()

    def actions(self, state: Any) -> tuple[Any, ...]:
        return self.original.actions(state)

    def action_key(self, action: Any) -> int:
        return self.original.action_key(action)

    def action(self, key: int) -> Any:
        return self.original.action(key)

    def active(self, state: Any) -> bool:
        return self.original.active(state)

    def success(self, state: Any) -> bool:
        return self.original.success(state)

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return self.original.select_outcome(
            state, key, episode_index, decision_index
        )

    def encode(self, state: Any) -> tuple[int, ...]:
        raw = self.original.encode(state)
        return tuple(raw[index] for index in self.state_canonical_to_raw)


def align_version_space_target_inputs_v68(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    *,
    layout_domain: str,
) -> tuple[
    dict[str, Any],
    _AlignedTargetAdapterV68,
    PartialFactorCandidateV15,
    tuple[FlatRawTransitionV4, ...],
]:
    """Derive an anonymous source-to-target projection from the common prefix."""
    verified = verify_joint_successor_version_space_model_v42(model)
    if (
        type(target_candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or type(layout_domain) is not str
        or not layout_domain
    ):
        _fail("V68 target alignment inventory changed")
    target_document = target_candidate.public_document
    if (
        target_document.get("state_width") != verified["state_width"]
        or target_document.get("action_field_width")
        != verified["action_field_width"]
        or target_document.get("planning_authority_present") is not False
        or target_document.get("complete_world_model_claimed") is not False
    ):
        _fail("V68 target common-partial schema is incompatible")
    reference_rows, reference_catalogue, reference_layout = (
        _model_reference_inputs(verified)
    )
    matched_layout = match_generic_layout_meta_prior_v5(
        reference_rows,
        reference_catalogue,
        reference_layout,
        observed_rows,
        adapter.catalogue,
        layout_domain=layout_domain,
    )
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        observed_rows,
        adapter.catalogue,
        matched_layout,
        canonical_occurrence=0,
    )
    replay_evaluations = _model_replays_target_prefix(verified, aligned_rows)
    alignment_payload = {
        "schema": "acfqp.generic_version_space_target_alignment.v68",
        "source_model_id": verified["joint_successor_version_space_model_id"],
        "target_partial_candidate_id": target_document["candidate_id"],
        "target_common_partial_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in observed_rows])
        ).hexdigest(),
        "target_common_partial_raw_transition_count": len(observed_rows),
        "source_reference_transition_count": len(reference_rows),
        "source_reference_selected_action_count": len(reference_catalogue),
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
        "target_prefix_model_replay_evaluations": replay_evaluations,
        "every_retained_partial_residual_and_terminal_program_replayed": True,
        "alignment_derived_only_from_target_common_partial_observations": True,
        "target_episode_outcomes_used": False,
        "source_model_refit": False,
        "semantic_names_used": False,
        "alignment_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    alignment = {
        **alignment_payload,
        "alignment_id": _identifier(_ALIGNMENT_DOMAIN, alignment_payload),
    }
    width = verified["state_width"]
    action_width = verified["action_field_width"]
    identity_layout = DiscoveredLayoutV5(
        tuple(range(width)),
        tuple(range(action_width)),
        tuple(verified["source_layout"]["state_structural_colors"]),
        tuple(verified["source_layout"]["action_structural_colors"]),
        verified["source_layout"]["schema_signature"],
        0,
        replay_evaluations,
        hashlib.sha256(
            b"acfqp:generic-version-space-target-identity-layout:v68\x00"
            + canonical_json_bytes(
                {
                    "alignment_id": alignment["alignment_id"],
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
        "schema": "acfqp.generic_version_space_target_candidate.v68",
        "source_factor_library_id": target_document["source_factor_library_id"],
        "target_partial_candidate_id": target_document["candidate_id"],
        "alignment_id": alignment["alignment_id"],
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
        "source_model_refit": False,
        "semantic_names_used": False,
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
    projected = _AlignedTargetAdapterV68(
        adapter,
        adapter.family,
        adapter.seed,
        adapter.kernel,
        aligned_catalogue,
        tuple(matched_layout.state_canonical_to_raw),
    )
    return alignment, projected, candidate, aligned_rows


def run_version_space_certificate_episode_v68(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    reusable_model: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_target_ground_support_labels: int,
    maximum_robust_state_depth_evaluations: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    """Use the model only to order an exact query-local proof."""
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or type(episode_index) is not int
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
        or maximum_target_ground_support_labels <= 0
        or maximum_robust_state_depth_evaluations <= 0
        or maximum_abstract_support_branch_evaluations <= 0
        or abstract_support_feasible_beam_width <= 0
    ):
        _fail("V68 episode inventory changed")
    model = (
        None
        if reusable_model is None
        else verify_joint_successor_version_space_model_v42(reusable_model)
    )
    legal_by_raw: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in observed_rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after
    transition_cache: dict[tuple[Any, int], tuple[Any, ...]] = {}
    exact_policy: dict[Any, int] = {}
    visiting: set[Any] = set()
    failed_certificates: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    local_rows: list[FlatRawTransitionV4] = []
    local_labels = 0
    abstract_attempts = 0
    abstract_successes = 0
    abstract_abstentions = 0
    abstract_compute = 0
    abstract_robust_closures = 0
    abstract_resource_truncations = 0
    abstract_proposal_by_raw: dict[tuple[int, ...], int] = {}
    abstract_plan_receipts: list[dict[str, Any]] = []
    plan_cache: dict[tuple[int, ...], dict[str, Any] | None] = {}

    def failure(kind: str, state: Any, key: int | None) -> int:
        index = len(failed_certificates)
        failed_certificates.append(
            {
                "failure_index": index,
                "failure_kind": kind,
                "raw_state": list(adapter.encode(state)),
                "action_key": key,
                "ground_query_performed_before_failure": False,
            }
        )
        return index

    def model_preferred(raw: tuple[int, ...], legal: tuple[int, ...]) -> list[int]:
        nonlocal abstract_attempts, abstract_successes, abstract_abstentions
        nonlocal abstract_compute, abstract_robust_closures
        nonlocal abstract_resource_truncations
        if model is None:
            return []
        if raw in plan_cache:
            plan = plan_cache[raw]
            if plan is None:
                return []
        else:
            abstract_attempts += 1
            try:
                plan = plan_joint_successor_version_space_v42(
                    model,
                    candidate,
                    adapter.catalogue,
                    raw,
                    maximum_depth=maximum_abstract_depth,
                    maximum_robust_state_depth_evaluations=(
                        maximum_robust_state_depth_evaluations
                    ),
                    maximum_support_branch_evaluations=(
                        maximum_abstract_support_branch_evaluations
                    ),
                    support_feasible_beam_width=(
                        abstract_support_feasible_beam_width
                    ),
                )
            except GenericJointSuccessorVersionSpacePlannerV42Error:
                plan_cache[raw] = None
                abstract_abstentions += 1
                return []
            plan_cache[raw] = plan
            abstract_plan_receipts.append(
                {"raw_state": list(raw), "abstract_plan": copy.deepcopy(plan)}
            )
            abstract_successes += 1
            abstract_compute += plan["abstract_support_branch_evaluations"]
            abstract_robust_closures += (
                plan["robust_all_version_space_branches_closed"] is True
            )
            abstract_resource_truncations += (
                plan["robust_search_resource_cap_reached"] is True
            )
        key = plan["initial_action_key"]
        if key not in legal:
            abstract_abstentions += 1
            return []
        abstract_proposal_by_raw[raw] = key
        return [key]

    def ordered_actions(state: Any) -> tuple[int, ...]:
        nonlocal local_labels
        raw = adapter.encode(state)
        legal = legal_by_raw.get(raw)
        if legal is None:
            if local_labels >= maximum_target_ground_support_labels:
                _fail("V68 label cap reached before legality query")
            index = failure("MISSING_QUERY_LOCAL_LEGALITY_SUPPORT", state, None)
            legal = tuple(
                sorted(adapter.action_key(action) for action in adapter.actions(state))
            )
            legal_by_raw[raw] = legal
            local_labels += 1
            distinctions.append(
                {
                    "failure_index": index,
                    "distinction_kind": "QUERY_LOCAL_LEGAL_ACTION_SET",
                    "raw_state": list(raw),
                    "legal_action_keys": list(legal),
                    "ground_support_labels": 1,
                    "query_after_failed_certificate": True,
                }
            )
        ordered = []
        for key in (*model_preferred(raw, legal), *legal):
            if key in legal and key not in ordered:
                ordered.append(key)
        return tuple(ordered)

    def query(state: Any, key: int) -> tuple[Any, ...]:
        nonlocal local_labels
        pair = (state, key)
        if pair in transition_cache:
            return transition_cache[pair]
        if local_labels >= maximum_target_ground_support_labels:
            _fail("V68 label cap reached before transition query")
        raw = adapter.encode(state)
        index = failure(
            "UNSEEN_TRANSITION_SUPPORT_PREVENTS_EXACT_BRANCH_PROOF",
            state,
            key,
        )
        outcomes = tuple(adapter.kernel.step(state, adapter.action(key)))
        if not outcomes:
            _fail("V68 target ground kernel returned empty support")
        successors = tuple(outcome.next_state for outcome in outcomes)
        batch = []
        for successor in successors:
            raw_successor = adapter.encode(successor)
            legal_after = tuple(
                sorted(
                    adapter.action_key(action)
                    for action in adapter.actions(successor)
                )
            )
            legal_by_raw[raw_successor] = legal_after
            batch.append(
                FlatRawTransitionV4(
                    0,
                    len(observed_rows) + len(local_rows) + len(batch),
                    raw,
                    legal_by_raw[raw],
                    adapter.catalogue[key],
                    raw_successor,
                    legal_after,
                    None if legal_after else adapter.success(successor),
                )
            )
        local_rows.extend(batch)
        local_labels += 1
        transition_cache[pair] = successors
        distinctions.append(
            {
                "failure_index": index,
                "distinction_kind": "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT",
                "raw_state": list(raw),
                "action_key": key,
                "raw_transition_rows": [row.to_document() for row in batch],
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
            }
        )
        return successors

    def solve(state: Any) -> bool:
        if adapter.success(state):
            return True
        if not adapter.active(state) or state in visiting:
            return False
        visiting.add(state)
        for key in ordered_actions(state):
            if all(solve(successor) for successor in query(state, key)):
                exact_policy[state] = key
                visiting.remove(state)
                return True
        visiting.remove(state)
        return False

    state = adapter.initial()
    if not solve(state):
        _fail("V68 exact query-local proof found no policy")
    action_keys = []
    outcome_tapes = []
    execution_abstract_matches = []
    for decision in range(maximum_execution_steps):
        if not adapter.active(state):
            break
        if state not in exact_policy and not solve(state):
            _fail("V68 receding exact query-local proof did not close")
        raw = adapter.encode(state)
        key = exact_policy[state]
        execution_abstract_matches.append(
            model is not None and abstract_proposal_by_raw.get(raw) == key
        )
        outcome, tape = adapter.select_outcome(
            state, key, episode_index, decision
        )
        state = outcome.next_state
        action_keys.append(key)
        outcome_tapes.append(tape)
    if adapter.active(state) or not adapter.success(state):
        _fail("V68 execution crossed its cap or terminated outside success")
    if (
        local_labels
        != sum(row["ground_support_labels"] for row in distinctions)
        or len(failed_certificates) != len(distinctions)
        or any(
            row["query_after_failed_certificate"] is not True
            for row in distinctions
        )
    ):
        _fail("V68 certificate-local accounting changed")
    payload = {
        "schema": "acfqp.generic_version_space_target_episode.v68",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "arm": (
            "JOINT_VERSION_SPACE_WORLD_MODEL"
            if model is not None
            else "STRICT_DIRECT_GROUND"
        ),
        "source_model_id": (
            None if model is None else model["joint_successor_version_space_model_id"]
        ),
        "target_candidate_id": candidate.public_document["candidate_id"],
        "action_keys": action_keys,
        "outcome_tape_sha256": outcome_tapes,
        "execution_steps": len(action_keys),
        "target_certificate_local_ground_support_labels": local_labels,
        "queried_state_action_count": len(transition_cache),
        "abstract_plan_attempt_count": abstract_attempts,
        "abstract_plan_success_count": abstract_successes,
        "abstract_plan_abstention_count": abstract_abstentions,
        "abstract_planning_compute_events": abstract_compute,
        "abstract_robust_closure_count": abstract_robust_closures,
        "abstract_robust_resource_truncation_count": (
            abstract_resource_truncations
        ),
        "abstract_plan_receipts": abstract_plan_receipts,
        "execution_action_matches_abstract_proposal": execution_abstract_matches,
        "execution_action_matches_abstract_proposal_count": sum(
            execution_abstract_matches
        ),
        "failed_certificates": failed_certificates,
        "local_distinctions": distinctions,
        "raw_local_transition_rows": [row.to_document() for row in local_rows],
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "model_used_only_for_action_ordering": model is not None,
        "model_or_alignment_used_as_safety_authority": False,
        "target_outcomes_used_to_refit_model_or_alignment": False,
        "complete_world_model_synthesized": False,
        "success": True,
    }
    return {
        **payload,
        "episode_id": _identifier(_EPISODE_DOMAIN, payload),
    }


def run_matched_version_space_target_ablation_v68(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    *,
    layout_domain: str,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_target_ground_support_labels: int,
    maximum_robust_state_depth_evaluations: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    alignment, projected, candidate, rows = align_version_space_target_inputs_v68(
        adapter,
        target_candidate,
        observed_rows,
        model,
        layout_domain=layout_domain,
    )
    arguments = {
        "episode_index": episode_index,
        "maximum_abstract_depth": maximum_abstract_depth,
        "maximum_execution_steps": maximum_execution_steps,
        "maximum_target_ground_support_labels": (
            maximum_target_ground_support_labels
        ),
        "maximum_robust_state_depth_evaluations": (
            maximum_robust_state_depth_evaluations
        ),
        "maximum_abstract_support_branch_evaluations": (
            maximum_abstract_support_branch_evaluations
        ),
        "abstract_support_feasible_beam_width": (
            abstract_support_feasible_beam_width
        ),
    }
    derived = run_version_space_certificate_episode_v68(
        projected,
        candidate,
        rows,
        reusable_model=model,
        **arguments,
    )
    strict = run_version_space_certificate_episode_v68(
        projected,
        candidate,
        rows,
        reusable_model=None,
        **arguments,
    )
    derived_labels = derived["target_certificate_local_ground_support_labels"]
    strict_labels = strict["target_certificate_local_ground_support_labels"]
    payload = {
        "schema": "acfqp.generic_version_space_target_ablation.v68",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_partial_candidate_id": target_candidate.public_document[
            "candidate_id"
        ],
        "projected_target_candidate_id": candidate.public_document[
            "candidate_id"
        ],
        "alignment": alignment,
        "alignment_id": alignment["alignment_id"],
        "arms": {
            "JOINT_VERSION_SPACE_WORLD_MODEL": derived,
            "STRICT_DIRECT_GROUND": strict,
        },
        "derived_target_certificate_local_ground_support_labels": derived_labels,
        "strict_target_certificate_local_ground_support_labels": strict_labels,
        "strict_minus_derived_target_labels": strict_labels - derived_labels,
        "actual_target_sample_reduction_observed": derived_labels < strict_labels,
        "same_target_prefix_adapter_kernel_seed_episode_and_exact_engine": True,
        "only_world_model_availability_differs_between_episode_arms": True,
        "alignment_frozen_before_target_episode": True,
        "target_episode_outcomes_used_to_select_alignment": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "model_or_alignment_used_as_safety_authority": False,
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "ablation_id": _identifier(_ABLATION_DOMAIN, payload),
    }


__all__ = (
    "GenericVersionSpaceTargetPlannerV68Error",
    "align_version_space_target_inputs_v68",
    "run_matched_version_space_target_ablation_v68",
    "run_version_space_certificate_episode_v68",
)
