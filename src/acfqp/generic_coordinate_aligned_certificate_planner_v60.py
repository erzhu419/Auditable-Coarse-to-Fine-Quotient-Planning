"""Run the V59 certificate engine through a learned coordinate projection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_applicability_certificate_planner_v59 import (
    run_matched_applicability_ablation_v59,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_coordinate_alignment_v60 import (
    aligned_source_views_v60,
    compile_coordinate_alignment_v60,
)
from acfqp.generic_layout_factorized_world_model_v5 import DiscoveredLayoutV5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


_PROJECTED_CANDIDATE_DOMAIN = b"acfqp:generic-coordinate-aligned-candidate:v60\x00"
_ABLATION_DOMAIN = b"acfqp:generic-coordinate-aligned-ablation:v60\x00"


class GenericCoordinateAlignedCertificatePlannerV60Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCoordinateAlignedCertificatePlannerV60Error(message)


@dataclass(frozen=True, slots=True)
class _CoordinateAlignedAdapterV60:
    original: Any
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    target_state_canonical_to_raw: tuple[int, ...]
    source_state_to_target_canonical: tuple[int, ...]

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
        return self.original.select_outcome(state, key, episode_index, decision_index)

    def encode(self, state: Any) -> tuple[int, ...]:
        raw = self.original.encode(state)
        target_canonical = tuple(
            raw[index] for index in self.target_state_canonical_to_raw
        )
        return tuple(
            target_canonical[index]
            for index in self.source_state_to_target_canonical
        )


def _projection(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    alignment: Mapping[str, Any],
) -> tuple[
    _CoordinateAlignedAdapterV60,
    PartialFactorCandidateV15,
    tuple[FlatRawTransitionV4, ...],
]:
    transformed_rows, transformed_catalogue = aligned_source_views_v60(
        alignment, target_candidate, observed_rows, adapter.catalogue
    )
    source_layout = model["source_layout"]
    state_width = model["state_width"]
    action_width = model["action_field_width"]
    identity_layout = DiscoveredLayoutV5(
        tuple(range(state_width)),
        tuple(range(action_width)),
        tuple(source_layout["state_structural_colors"]),
        tuple(source_layout["action_structural_colors"]),
        source_layout["schema_signature"],
        source_layout["refinement_rounds"],
        source_layout["relation_evaluations"],
        hashlib.sha256(
            b"acfqp:generic-coordinate-aligned-layout:v60\x00"
            + canonical_json_bytes(
                {
                    "coordinate_alignment_id": alignment["coordinate_alignment_id"],
                    "state_order": list(range(state_width)),
                    "action_order": list(range(action_width)),
                }
            )
        ).hexdigest(),
    )
    target_document = target_candidate.public_document
    candidate_payload = {
        "schema": "acfqp.generic_coordinate_aligned_partial_candidate.v60",
        "source_factor_library_id": target_document["source_factor_library_id"],
        "target_partial_candidate_id": target_document["candidate_id"],
        "coordinate_alignment_id": alignment["coordinate_alignment_id"],
        "layout": identity_layout.to_document(),
        "state_width": state_width,
        "action_field_width": action_width,
        "compiled_factor_assignments": model["known_partial_factor_assignments"],
        "unknown_residual_target_columns": model[
            "unknown_residual_target_columns"
        ],
        "transformed_observation_count": len(transformed_rows),
        "transformed_observation_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in transformed_rows])
        ).hexdigest(),
        "source_model_refit": False,
        "semantic_names_used": False,
        "planning_authority_present": False,
        "complete_world_model_claimed": False,
    }
    candidate_document = {
        **candidate_payload,
        "candidate_id": hashlib.sha256(
            _PROJECTED_CANDIDATE_DOMAIN + canonical_json_bytes(candidate_payload)
        ).hexdigest(),
    }
    candidate = PartialFactorCandidateV15(
        candidate_document,
        identity_layout,
        tuple(model["known_partial_factor_assignments"]),
        transformed_rows,
    )
    target_layout = target_document["layout"]
    projected_adapter = _CoordinateAlignedAdapterV60(
        adapter,
        adapter.family,
        adapter.seed,
        adapter.kernel,
        transformed_catalogue,
        tuple(target_layout["state_canonical_to_raw"]),
        tuple(alignment["source_state_to_target_canonical"]),
    )
    if projected_adapter.encode(adapter.initial()) != transformed_rows[0].pre:
        _fail("V60 projected adapter and observation coordinate systems diverged")
    return projected_adapter, candidate, transformed_rows


def run_coordinate_aligned_applicability_ablation_v60(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    *,
    model_source_episode_index: int,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_target_ground_support_labels: int = 100_000,
    maximum_abstract_support_branch_evaluations: int = 1_000_000,
    abstract_support_feasible_beam_width: int = 64,
) -> dict[str, Any]:
    alignment = compile_coordinate_alignment_v60(
        model,
        applicability_program,
        target_candidate,
        observed_rows,
        adapter.catalogue,
    )
    projected_adapter, projected_candidate, projected_rows = _projection(
        adapter, target_candidate, observed_rows, model, alignment
    )
    ablation = run_matched_applicability_ablation_v59(
        projected_adapter,
        projected_candidate,
        projected_rows,
        model,
        applicability_program,
        model_source_episode_index=model_source_episode_index,
        episode_index=episode_index,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_target_ground_support_labels=maximum_target_ground_support_labels,
        maximum_abstract_support_branch_evaluations=(
            maximum_abstract_support_branch_evaluations
        ),
        abstract_support_feasible_beam_width=abstract_support_feasible_beam_width,
    )
    payload = {
        "schema": "acfqp.generic_coordinate_aligned_applicability_ablation.v60",
        "family": adapter.family,
        "seed": adapter.seed,
        "target_partial_candidate_id": target_candidate.public_document[
            "candidate_id"
        ],
        "projected_partial_candidate_id": projected_candidate.public_document[
            "candidate_id"
        ],
        "coordinate_alignment": alignment,
        "coordinate_alignment_id": alignment["coordinate_alignment_id"],
        "underlying_matched_ablation": ablation,
        "arms": ablation["arms"],
        "derived_target_certificate_local_ground_support_labels": ablation[
            "derived_target_certificate_local_ground_support_labels"
        ],
        "strict_target_certificate_local_ground_support_labels": ablation[
            "strict_target_certificate_local_ground_support_labels"
        ],
        "derived_minus_strict_target_labels": ablation[
            "derived_minus_strict_target_labels"
        ],
        "actual_target_sample_reduction_observed": ablation[
            "actual_target_sample_reduction_observed"
        ],
        "alignment_frozen_before_target_episode": True,
        "target_episode_outcomes_used_to_select_alignment": False,
        "same_exact_query_local_certificate_engine": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "coordinate_alignment_or_model_used_as_safety_authority": False,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "ablation_id": hashlib.sha256(
            _ABLATION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_coordinate_aligned_applicability_ablation_v60",)
