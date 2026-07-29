"""Independent proof/candidate/order replay for registered V0-072 selector."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import public_novel_child_cardinality_authority_v2 as descriptors
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_archive
from acfqp import v072_cold_h2_model_builders_v1 as models
from acfqp import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)
from acfqp import v072_registered_target_selector_v1 as selector


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_registered_target_selector_independent_verifier_v1"

_DOMAINS = {
    "generic_candidate": (
        "acfqp:v072-generic-boundary-selector-candidate:v1"
    ),
    "generic_decision": (
        "acfqp:v072-generic-boundary-selector-decision:v1"
    ),
    "new_child": "acfqp:v072-registered-new-child-row-spec:v1",
    "candidate": "acfqp:v072-registered-boundary-candidate:v1",
    "inventory": "acfqp:v072-registered-candidate-inventory:v1",
    "causal": "acfqp:v072-registered-selector-causal-evidence:v1",
    "order": "acfqp:v072-registered-proposal-order:v1",
    "claim": "acfqp:v072-registered-selector-claim:v1",
    "attestation": (
        "acfqp:v072-registered-selector-independent-attestation:v1"
    ),
}


class V072RegisteredSelectorIndependentVerificationFailure(ValueError):
    """Independent selector reconstruction differs from the claim."""


class RegisteredSelectorIndependentGateLockedV1(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        observer_stream_opens: int = 0,
        observer_draw_calls: int = 0,
    ) -> None:
        super().__init__(message)
        self.observer_stream_opens = observer_stream_opens
        self.observer_draw_calls = observer_draw_calls


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            _DOMAINS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredSelectorIndependentVerificationFailure(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredSelectorIndependentVerificationFailure(
            f"{label} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "independent selector requires exact Fraction values"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any, label: str) -> Fraction:
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        raise V072RegisteredSelectorIndependentVerificationFailure(
            f"{label} is not a rational"
        )
    output = Fraction(value["numerator"], value["denominator"])
    if (
        output.numerator != value["numerator"]
        or output.denominator != value["denominator"]
    ):
        raise V072RegisteredSelectorIndependentVerificationFailure(
            f"{label} is not reduced"
        )
    return output


def _count_bin(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def replay_generic_boundary_selection_independently_v1(
    *,
    candidates: tuple[selector.GenericBoundaryCandidateV1, ...],
    arm: str,
    remaining_draw_cap: int,
    claimed: selector.GenericBoundarySelectionDecisionV1,
) -> selector.GenericBoundarySelectionDecisionV1:
    """Independently replay the registration-disjoint selection core."""

    if (
        type(candidates) is not tuple
        or any(
            type(item) is not selector.GenericBoundaryCandidateV1
            for item in candidates
        )
        or tuple(item.candidate_id for item in candidates)
        != tuple(sorted({item.candidate_id for item in candidates}))
        or arm not in prereg.ARM_ORDER[:-1]
        or type(remaining_draw_cap) is not int
        or remaining_draw_cap < 0
        or type(claimed)
        is not selector.GenericBoundarySelectionDecisionV1
    ):
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "generic selector replay input is malformed"
        )
    sound = tuple(
        item
        for item in candidates
        if item.sound_cover and item.causal_weight > 0
    )
    eligible = tuple(
        item
        for item in sound
        if item.cap_eligible and item.draw_upper <= remaining_draw_cap
    )

    def multiplier(
        item: selector.GenericBoundaryCandidateV1,
    ) -> Fraction:
        if (
            arm in ("SOURCE_CONSENSUS_PRIOR", "WRONG_CONSENSUS_PRIOR")
            and item.source_midrank is not None
        ):
            q = (
                item.source_midrank
                if arm == "SOURCE_CONSENSUS_PRIOR"
                else 1 - item.source_midrank
            )
            return Fraction(1, 2) + Fraction(3, 2) * q
        return Fraction(1)

    ordered = tuple(
        item.candidate_id
        for item in sorted(
            eligible,
            key=lambda item: (
                item.boundary_depth,
                -(item.causal_weight / item.draw_upper * multiplier(item)),
                -item.causal_weight,
                item.draw_upper,
                item.candidate_id,
            ),
        )
    )
    if not sound:
        outcome = selector.RegisteredSelectorOutcomeV1.NO_SOUND_COVER
        selected = None
    elif not eligible:
        outcome = selector.RegisteredSelectorOutcomeV1.CAP_EXHAUSTED
        selected = None
    else:
        outcome = selector.RegisteredSelectorOutcomeV1.SELECTED
        selected = ordered[0]
    replayed = selector.GenericBoundarySelectionDecisionV1(
        arm,
        remaining_draw_cap,
        tuple(item.candidate_id for item in candidates),
        ordered,
        outcome,
        selected,
    )
    if replayed._payload() != claimed._payload():
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "generic proposal order or typed closure differs"
        )
    return replayed


def _feature(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row: robust.IntervalSimplexRowV1,
) -> source_archive.PortableAcquisitionCoreFeatureV2:
    provenance = {
        item.row_id: item for item in audit.selected_row_provenance
    }.get(row.row_id)
    catalogue = {
        item.state_id: item for item in model.catalogues
    }.get(row.state_id)
    assignments = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if provenance is None or catalogue is None:
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "failed row lacks independently replayed provenance/catalogue"
        )
    action_key = assignments.get(
        (provenance.policy_scope_key, row.remaining_horizon)
    )
    sizes = {
        len(item.ground_action_ids)
        for item in model.concretizer_entries
        if item.state_id == row.state_id
        and item.abstract_action_key == action_key
    }
    if action_key is None or len(sizes) != 1:
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "failed row selected action/concretizer differs"
        )
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    categories = tuple(
        sorted(
            {
                destination_by_id[item.destination_id].category.value
                for item in row.masses
                if item.destination_id != row.other_destination_id
            }
        )
    )
    return source_archive.PortableAcquisitionCoreFeatureV2(
        "ROOT" if row.remaining_horizon == 2 else "CONTINUATION",
        provenance.category.value,
        _count_bin(len(catalogue.actions)),
        _count_bin(next(iter(sizes))),
        categories,
    )


def _source_q(
    chain: consumer.RegisteredCampaignAuthorityChainV1,
    arm: str,
) -> tuple[str | None, dict[str, Fraction]]:
    if arm not in (
        "SOURCE_CONSENSUS_PRIOR",
        "WRONG_CONSENSUS_PRIOR",
    ):
        return None, {}
    claim = chain.remote_main_anchor.claim
    recipe = source_recipe.load_source_reconstruction_recipe_v1(
        Path(chain.repository_root)
        / claim.source_reconstruction_recipe_repository_path
    )
    if recipe.recipe_id != claim.source_reconstruction_recipe_id:
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent source proposal recipe replay differs"
        )
    values = {}
    for item in recipe.to_document()["compact_derived_artifacts"][
        "source_archive"
    ]["consensus"]:
        if item["disposition"] == "APPLIED":
            values[_cid(item["feature_key"], "source feature")] = _fraction(
                item["mean_midrank"],
                "source mean midrank",
            )
    return recipe.recipe_id, values


def _descriptor_id(
    observation: observer.HeldoutObservedJointTransitionV2,
) -> str:
    return descriptors.RecordedTransitionDescriptorV2(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    ).descriptor_id


def _new_children(
    context: prereg.HeldoutPublicGraphContextV2,
    parent: accumulator.RegisteredTargetRowAcquisitionV1,
    existing_rows: set[str],
) -> tuple[dict[str, Any], ...]:
    states: dict[
        str, tuple[observer.HeldoutSymbolicGraphStateV2, set[str]]
    ] = {}
    novel = set(parent.validation_novel_descriptor_ids)
    for observation in parent.transcript.validation_observations:
        descriptor_id = _descriptor_id(observation)
        if (
            descriptor_id not in novel
            or observation.failure
            or observation.terminal
            or observation.remaining_horizon != 2
        ):
            continue
        state, evidence = states.setdefault(
            observation.next_state.state_id,
            (observation.next_state, set()),
        )
        del state
        evidence.add(descriptor_id)
    output: dict[str, dict[str, Any]] = {}
    for state, evidence in states.values():
        catalogue = observer.legal_action_catalogue_v2(context, state, 1)
        for action in catalogue.actions:
            row = observer.observation_row_binding_v2(
                context,
                catalogue,
                action,
            ).row_binding_id
            if row in existing_rows:
                continue
            payload = {
                "schema": "acfqp.v072_registered_new_child_row_spec.v1",
                "schema_version": SCHEMA_VERSION,
                "source_parent_row_binding_id": parent.row_binding_id,
                "source_descriptor_ids": list(sorted(evidence)),
                "catalogue_id": catalogue.catalogue_id,
                "action": list(action),
                "row_binding_id": row,
                "complete_public_catalogue": True,
                "caller_candidate": False,
            }
            output[row] = {
                "row": row,
                "catalogue": catalogue,
                "action": action,
                "source_ids": tuple(sorted(evidence)),
                "spec_id": _hash("new_child", payload),
                "payload": payload,
            }
    return tuple(output[key] for key in sorted(output))


def _preflight(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    failed_audit: Any,
    model_pair: Any,
    model_replay_attestation: Any,
    acquisitions: Any,
    round_index: Any,
    predecessor_frontier: Any,
    claimed: Any,
) -> None:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(occurrence_plan)
        is not consumer.RegisteredOccurrenceExecutionPlanV1
        or type(failed_audit) is not robust.RobustPlanAuditV1
        or type(model_pair) is not models.RegisteredColdH2ModelPairV1
        or type(model_replay_attestation)
        is not model_independent.RegisteredColdH2ModelIndependentReplayAttestationV1
        or type(acquisitions) is not tuple
        or not acquisitions
        or any(
            type(item)
            is not accumulator.RegisteredTargetRowAcquisitionV1
            for item in acquisitions
        )
        or round_index not in (1, 2)
        or type(claimed) is not selector.RegisteredSelectorClaimV1
    ):
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent selector requires exact typed inputs"
        )
    try:
        consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (ValueError, consumer.RegisteredCampaignAuthorityGateLockedV1) as error:
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent selector authority chain is stale"
        ) from error
    template = occurrence_plan.template
    if (
        occurrence_plan.chain_id != authority_chain.chain_id
        or template.route_kind
        is not consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        or template.context_id != model_pair.closure_bundle.context_id
        or template.arm not in prereg.ARM_ORDER[:-1]
        or model_pair.anchor_id != anchor.anchor_id
        or model_replay_attestation.model_pair_id
        != model_pair.model_pair_id
        or model_replay_attestation.remote_main_anchor_id
        != anchor.anchor_id
        or failed_audit.model_id
        != model_pair.quotient_planner_model.model_id
        or failed_audit.threshold_profile_id
        != model_pair.threshold_profile.threshold_profile_id
        or failed_audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or failed_audit.failed_frontier is None
    ):
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent selector proof/model/occurrence is rebound"
        )
    replayed_model = (
        model_independent
        .verify_registered_cold_h2_model_pair_independently_v1(
            anchor,
            authority_chain.remote_main_anchor_attestation,
            model_pair,
        )
    )
    if replayed_model.to_document() != model_replay_attestation.to_document():
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent registered model replay differs"
        )
    robust.verify_robust_plan_audit_v1(
        model_pair.quotient_planner_model,
        model_pair.threshold_profile,
        failed_audit,
    )
    acquisition_ids = tuple(item.acquisition_id for item in acquisitions)
    if (
        acquisition_ids != tuple(sorted(set(acquisition_ids)))
        or any(
            item.authority_chain_id != authority_chain.chain_id
            or item.anchor_id != anchor.anchor_id
            or item.context.context_id != template.context_id
            or item.arm != template.arm
            for item in acquisitions
        )
    ):
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent acquisition inventory is foreign"
        )
    if round_index == 1:
        if predecessor_frontier is not None:
            raise RegisteredSelectorIndependentGateLockedV1(
                "independent round one has a predecessor"
            )
    elif (
        type(predecessor_frontier)
        is not accumulator.RegisteredAcquisitionFrontierV1
        or predecessor_frontier.round_index != 1
        or predecessor_frontier.authority_chain_id
        != authority_chain.chain_id
        or not set(predecessor_frontier.supporting_acquisition_ids)
        < set(acquisition_ids)
    ):
        raise RegisteredSelectorIndependentGateLockedV1(
            "independent round two is not a fresh strict extension"
        )


def _expected(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    failed_audit: robust.RobustPlanAuditV1,
    model_pair: models.RegisteredColdH2ModelPairV1,
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ],
    round_index: int,
    predecessor_frontier: (
        accumulator.RegisteredAcquisitionFrontierV1 | None
    ),
) -> dict[str, Any]:
    model = model_pair.quotient_planner_model
    frontier = failed_audit.failed_frontier
    assert frontier is not None
    planner_to_source = {
        planner: source
        for source, _other, planner
        in model_pair.quotient_collapse_proof.row_mappings
    }
    projections = {
        item.interval_row.row_id: item for item in model_pair.row_projections
    }
    acquisitions_by_transcript = {
        item.transcript.transcript_id: item for item in acquisitions
    }
    existing_rows = {item.row_binding_id for item in acquisitions}
    recipe_id, q_by_feature = _source_q(
        authority_chain,
        occurrence_plan.template.arm,
    )
    previous_draws = (
        0
        if predecessor_frontier is None
        else predecessor_frontier.cumulative_draw_upper
    )
    previous_new = (
        set()
        if predecessor_frontier is None
        else set(predecessor_frontier.new_child_row_binding_ids)
    )
    remaining = (
        prereg.MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM
        - previous_draws
    )
    rows = {item.row_id: item for item in model.rows}
    expected_candidates = []
    for planner_row_id in frontier.other_positive_row_ids:
        source_row_id = planner_to_source.get(planner_row_id)
        projection = (
            None if source_row_id is None else projections.get(source_row_id)
        )
        row = rows.get(planner_row_id)
        if projection is None or row is None:
            raise V072RegisteredSelectorIndependentVerificationFailure(
                "frontier mapping omits a physical row"
            )
        parent = acquisitions_by_transcript.get(
            projection.validation_transcript_id
        )
        if parent is None:
            raise V072RegisteredSelectorIndependentVerificationFailure(
                "frontier physical row omits its acquisition"
            )
        children = _new_children(parent.context, parent, existing_rows)
        feature = _feature(model, failed_audit, row)
        weight = row.other_mass.upper
        sound = (
            frontier.other_only_counterfactual_changes
            and weight > 0
            and parent.round_index == round_index - 1
        )
        union_new = previous_new | {item["row"] for item in children}
        draw = (
            prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
            + (
                prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            )
            * len(children)
        )
        cap = (
            len(union_new)
            <= prereg.MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS
            and draw <= remaining
        )
        selected_rows = tuple(
            sorted((parent.row_binding_id, *(item["row"] for item in children)))
        )
        payload = {
            "schema": "acfqp.v072_registered_boundary_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "planner_row_id": planner_row_id,
            "source_row_id": source_row_id,
            "projection_id": projection.projection_id,
            "parent_acquisition_id": parent.acquisition_id,
            "promotion_row_binding_id": parent.row_binding_id,
            "new_child_spec_ids": [item["spec_id"] for item in children],
            "selected_row_binding_ids": list(selected_rows),
            "portable_feature_key": feature.feature_key,
            "boundary_depth": 2 - row.remaining_horizon,
            "causal_weight": _fdoc(weight),
            "sound_cover": sound,
            "cap_eligible": cap,
            "draw_upper": draw,
            "source_changes_legality": False,
            "source_quantity_serialized": False,
            "caller_candidate": False,
        }
        candidate_id = _hash("candidate", payload)
        generic_payload = {
            "schema": "acfqp.v072_generic_boundary_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "boundary_depth": 2 - row.remaining_horizon,
            "physical_row_binding_ids": list(selected_rows),
            "causal_weight": _fdoc(weight),
            "draw_upper": draw,
            "source_midrank": (
                None
                if q_by_feature.get(feature.feature_key) is None
                else _fdoc(q_by_feature[feature.feature_key])
            ),
            "sound_cover": sound,
            "cap_eligible": cap,
            "source_can_change_legality": False,
        }
        expected_candidates.append(
            {
                "candidate_id": candidate_id,
                "payload": payload,
                "generic_id": _hash(
                    "generic_candidate", generic_payload
                ),
                "planner_row_id": planner_row_id,
                "source_row_id": source_row_id,
                "projection_id": projection.projection_id,
                "parent_id": parent.acquisition_id,
                "promotion_row": parent.row_binding_id,
                "children": children,
                "feature_key": feature.feature_key,
                "q": q_by_feature.get(feature.feature_key),
                "depth": 2 - row.remaining_horizon,
                "weight": weight,
                "sound": sound,
                "cap": cap,
                "draw": draw,
                "selected_rows": selected_rows,
            }
        )
    expected_candidates.sort(key=lambda item: item["candidate_id"])
    sound = [
        item
        for item in expected_candidates
        if item["sound"] and item["weight"] > 0
    ]
    eligible = [
        item
        for item in sound
        if item["cap"] and item["draw"] <= remaining
    ]
    arm = occurrence_plan.template.arm

    def multiplier(item: dict[str, Any]) -> Fraction:
        if arm in (
            "SOURCE_CONSENSUS_PRIOR",
            "WRONG_CONSENSUS_PRIOR",
        ) and item["q"] is not None:
            q = item["q"] if arm == "SOURCE_CONSENSUS_PRIOR" else 1 - item["q"]
            return Fraction(1, 2) + Fraction(3, 2) * q
        return Fraction(1)

    ordered = tuple(
        item["candidate_id"]
        for item in sorted(
            eligible,
            key=lambda item: (
                item["depth"],
                -(item["weight"] / item["draw"] * multiplier(item)),
                -item["weight"],
                item["draw"],
                item["candidate_id"],
            ),
        )
    )
    if not sound:
        outcome = selector.RegisteredSelectorOutcomeV1.NO_SOUND_COVER
        selected = None
    elif not eligible:
        outcome = selector.RegisteredSelectorOutcomeV1.CAP_EXHAUSTED
        selected = None
    else:
        outcome = selector.RegisteredSelectorOutcomeV1.SELECTED
        selected = ordered[0]
    candidate_ids = tuple(item["candidate_id"] for item in expected_candidates)
    decision_payload = {
        "schema": "acfqp.v072_generic_boundary_selection_decision.v1",
        "schema_version": SCHEMA_VERSION,
        "arm": arm,
        "remaining_draw_cap": remaining,
        "candidate_ids": list(candidate_ids),
        "ordered_eligible_candidate_ids": list(ordered),
        "outcome": outcome.value,
        "selected_candidate_id": selected,
        "deterministic_tie_break": (
            "EARLIEST_BOUNDARY_THEN_SCORE_GAIN_DRAW_ID"
        ),
        "maximum_selected_candidates": 1,
        "source_changes_legality": False,
    }
    decision_id = _hash("generic_decision", decision_payload)
    acquisition_ids = tuple(item.acquisition_id for item in acquisitions)
    acquisition_rows = tuple(
        sorted({item.row_binding_id for item in acquisitions})
    )
    inventory_id = _hash(
        "inventory",
        {
            "schema": "acfqp.v072_registered_candidate_inventory.v1",
            "schema_version": SCHEMA_VERSION,
            "failed_frontier_id": frontier.frontier_id,
            "model_pair_id": model_pair.model_pair_id,
            "supporting_acquisition_ids": list(acquisition_ids),
            "candidate_ids": list(candidate_ids),
            "caller_candidates_accepted": False,
        },
    )
    causal_evidence_id = _hash(
        "causal",
        {
            "schema": (
                "acfqp.v072_registered_selector_causal_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": authority_chain.chain_id,
            "anchor_id": authority_chain.remote_main_anchor.anchor_id,
            "occurrence_id": occurrence_plan.occurrence_id,
            "context_id": occurrence_plan.template.context_id,
            "round_index": round_index,
            "predecessor_frontier_id": (
                None
                if predecessor_frontier is None
                else predecessor_frontier.frontier_id
            ),
            "failed_audit_id": failed_audit.audit_id,
            "failed_frontier_id": frontier.frontier_id,
            "model_pair_id": model_pair.model_pair_id,
            "candidate_inventory_id": inventory_id,
            "candidate_ids": list(candidate_ids),
            "source_prior_used": False,
        },
    )
    order_id = _hash(
        "order",
        {
            "schema": "acfqp.v072_registered_proposal_order.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_inventory_id": inventory_id,
            "arm": arm,
            "source_recipe_id": recipe_id,
            "decision_id": decision_id,
            "source_used_for_ordering_only": True,
        },
    )
    claim_payload = {
        "schema": "acfqp.v072_registered_selector_claim.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": selector.PROPOSED_CONTRACT_VERSION,
        "profile_key": selector.PROFILE_KEY,
        "authority_chain_id": authority_chain.chain_id,
        "anchor_id": authority_chain.remote_main_anchor.anchor_id,
        "occurrence_id": occurrence_plan.occurrence_id,
        "context_id": occurrence_plan.template.context_id,
        "arm": arm,
        "round_index": round_index,
        "predecessor_frontier_id": (
            None
            if predecessor_frontier is None
            else predecessor_frontier.frontier_id
        ),
        "failed_audit_id": failed_audit.audit_id,
        "failed_frontier_id": frontier.frontier_id,
        "model_pair_id": model_pair.model_pair_id,
        "model_replay_attestation_id": None,
        "supporting_acquisition_ids": list(acquisition_ids),
        "supporting_row_binding_ids": list(acquisition_rows),
        "candidate_inventory_id": inventory_id,
        "proposal_order_id": order_id,
        "source_recipe_id": recipe_id,
        "decision_id": decision_id,
        "outcome": outcome.value,
        "selected_candidate_id": selected,
        "cumulative_draw_upper_before_round": previous_draws,
        "source_used_in_confidence_or_certificate": False,
        "caller_candidate_or_status_accepted": False,
        "observer_stream_opens": 0,
        "observer_draw_calls": 0,
    }
    return {
        "candidates": expected_candidates,
        "candidate_ids": candidate_ids,
        "decision_payload": decision_payload,
        "decision_id": decision_id,
        "outcome": outcome,
        "selected": selected,
        "inventory_id": inventory_id,
        "causal_evidence_id": causal_evidence_id,
        "order_id": order_id,
        "recipe_id": recipe_id,
        "previous_draws": previous_draws,
        "remaining": remaining,
        "acquisition_ids": acquisition_ids,
        "acquisition_rows": acquisition_rows,
        "claim_payload": claim_payload,
    }


_ATTESTATION_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredSelectorIndependentAttestationV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_id: str
    context_id: str
    arm: str
    round_index: int
    predecessor_frontier_id: str | None
    failed_audit_id: str
    model_pair_id: str
    model_replay_attestation_id: str
    candidate_inventory_id: str
    proposal_order_id: str
    causal_evidence_id: str
    claim_id: str
    outcome: selector.RegisteredSelectorOutcomeV1
    selected_candidate_id: str | None
    supporting_acquisition_ids: tuple[str, ...]
    supporting_row_binding_ids: tuple[str, ...]
    promotion_row_binding_id: str | None
    new_child_row_binding_ids: tuple[str, ...]
    selected_row_binding_ids: tuple[str, ...]
    selected_draw_upper: int
    cumulative_draw_upper: int
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.occurrence_id,
            self.context_id,
            self.failed_audit_id,
            self.model_pair_id,
            self.model_replay_attestation_id,
            self.candidate_inventory_id,
            self.proposal_order_id,
            self.causal_evidence_id,
            self.claim_id,
            *self.supporting_acquisition_ids,
            *self.supporting_row_binding_ids,
            *self.new_child_row_binding_ids,
            *self.selected_row_binding_ids,
        ):
            _cid(value, "selector attestation identity")
        for value in (
            self.predecessor_frontier_id,
            self.selected_candidate_id,
            self.promotion_row_binding_id,
        ):
            if value is not None:
                _cid(value, "selector optional identity")
        selected = self.outcome is selector.RegisteredSelectorOutcomeV1.SELECTED
        if (
            self._minting_capability is not _ATTESTATION_MINTING_SENTINEL
            or self.arm not in prereg.ARM_ORDER[:-1]
            or self.round_index not in (1, 2)
            or type(self.outcome) is not selector.RegisteredSelectorOutcomeV1
            or self.supporting_acquisition_ids
            != tuple(sorted(set(self.supporting_acquisition_ids)))
            or not self.supporting_acquisition_ids
            or self.supporting_row_binding_ids
            != tuple(sorted(set(self.supporting_row_binding_ids)))
            or not self.supporting_row_binding_ids
            or self.new_child_row_binding_ids
            != tuple(sorted(set(self.new_child_row_binding_ids)))
            or self.selected_row_binding_ids
            != tuple(sorted(set(self.selected_row_binding_ids)))
            or type(self.selected_draw_upper) is not int
            or self.selected_draw_upper < 0
            or type(self.cumulative_draw_upper) is not int
            or self.cumulative_draw_upper < 0
            or selected
            != (
                self.selected_candidate_id is not None
                and self.promotion_row_binding_id is not None
                and bool(self.selected_row_binding_ids)
            )
            or (
                selected
                and self.selected_row_binding_ids
                != tuple(
                    sorted(
                        (
                            self.promotion_row_binding_id,
                            *self.new_child_row_binding_ids,
                        )
                    )
                )
            )
            or (
                selected
                and self.selected_draw_upper
                != (
                    prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
                    + (
                        prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                        + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
                    )
                    * len(self.new_child_row_binding_ids)
                )
            )
            or (
                not selected
                and (
                    self.selected_candidate_id is not None
                    or self.promotion_row_binding_id is not None
                    or self.new_child_row_binding_ids
                    or self.selected_row_binding_ids
                    or self.selected_draw_upper != 0
                )
            )
            or (
                self.round_index == 1
                and (
                    self.predecessor_frontier_id is not None
                    or self.cumulative_draw_upper
                    != self.selected_draw_upper
                )
            )
            or (
                self.round_index == 2
                and (
                    self.predecessor_frontier_id is None
                    or self.cumulative_draw_upper
                    <= self.selected_draw_upper
                )
            )
            or self.cumulative_draw_upper
            > prereg.MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM
        ):
            raise V072RegisteredSelectorIndependentVerificationFailure(
                "selector attestation is not privately replay-derived"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_selector_"
                "independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "round_index": self.round_index,
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "failed_audit_id": self.failed_audit_id,
            "model_pair_id": self.model_pair_id,
            "model_replay_attestation_id": (
                self.model_replay_attestation_id
            ),
            "candidate_inventory_id": self.candidate_inventory_id,
            "proposal_order_id": self.proposal_order_id,
            "causal_evidence_id": self.causal_evidence_id,
            "claim_id": self.claim_id,
            "outcome": self.outcome.value,
            "selected_candidate_id": self.selected_candidate_id,
            "supporting_acquisition_ids": list(
                self.supporting_acquisition_ids
            ),
            "supporting_row_binding_ids": list(
                self.supporting_row_binding_ids
            ),
            "promotion_row_binding_id": self.promotion_row_binding_id,
            "new_child_row_binding_ids": list(
                self.new_child_row_binding_ids
            ),
            "selected_row_binding_ids": list(
                self.selected_row_binding_ids
            ),
            "selected_draw_upper": self.selected_draw_upper,
            "cumulative_draw_upper": self.cumulative_draw_upper,
            "proof_dependency_replayed": True,
            "candidate_inventory_replayed": True,
            "proposal_order_replayed": True,
            "selection_replayed": True,
            "source_used_for_ordering_only": True,
            "source_used_in_confidence_or_certificate": False,
            "observer_stream_opens": 0,
            "observer_draw_calls": 0,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def verify_registered_selector_independently_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    failed_audit: robust.RobustPlanAuditV1,
    model_pair: models.RegisteredColdH2ModelPairV1,
    model_replay_attestation: (
        model_independent.RegisteredColdH2ModelIndependentReplayAttestationV1
    ),
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ],
    round_index: int,
    predecessor_frontier: (
        accumulator.RegisteredAcquisitionFrontierV1 | None
    ),
    claimed: selector.RegisteredSelectorClaimV1,
) -> RegisteredSelectorIndependentAttestationV1:
    """Reconstruct every proof/candidate/order identity without target access."""

    _preflight(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        failed_audit=failed_audit,
        model_pair=model_pair,
        model_replay_attestation=model_replay_attestation,
        acquisitions=acquisitions,
        round_index=round_index,
        predecessor_frontier=predecessor_frontier,
        claimed=claimed,
    )
    expected = _expected(
        authority_chain=authority_chain,
        occurrence_plan=occurrence_plan,
        failed_audit=failed_audit,
        model_pair=model_pair,
        acquisitions=acquisitions,
        round_index=round_index,
        predecessor_frontier=predecessor_frontier,
    )
    by_id = {item.candidate_id: item for item in claimed.candidates}
    if tuple(by_id) != expected["candidate_ids"]:
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "candidate inventory differs"
        )
    for item in expected["candidates"]:
        actual = by_id[item["candidate_id"]]
        if (
            actual.planner_row_id != item["planner_row_id"]
            or actual.source_row_id != item["source_row_id"]
            or actual.projection_id != item["projection_id"]
            or actual.parent_acquisition_id != item["parent_id"]
            or actual.promotion_row_binding_id != item["promotion_row"]
            or tuple(child.spec_id for child in actual.new_child_rows)
            != tuple(child["spec_id"] for child in item["children"])
            or tuple(
                child.row_binding_id for child in actual.new_child_rows
            )
            != tuple(child["row"] for child in item["children"])
            or actual.portable_feature_key != item["feature_key"]
            or actual.source_midrank != item["q"]
            or actual.boundary_depth != item["depth"]
            or actual.causal_weight != item["weight"]
            or actual.sound_cover != item["sound"]
            or actual.cap_eligible != item["cap"]
            or actual.draw_upper != item["draw"]
            or actual.selected_row_binding_ids != item["selected_rows"]
            or actual.candidate_id != item["candidate_id"]
        ):
            raise V072RegisteredSelectorIndependentVerificationFailure(
                "candidate proof/row/feature/cap replay differs"
            )
    decision = claimed.decision
    if (
        decision.decision_id != expected["decision_id"]
        or decision.outcome is not expected["outcome"]
        or decision.selected_candidate_id != expected["selected"]
        or decision.ordered_eligible_candidate_ids
        != tuple(expected["decision_payload"]["ordered_eligible_candidate_ids"])
        or claimed.candidate_inventory_id != expected["inventory_id"]
        or claimed.proposal_order_id != expected["order_id"]
        or claimed.source_recipe_id != expected["recipe_id"]
    ):
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "proposal ordering or selection differs"
        )
    expected["claim_payload"]["model_replay_attestation_id"] = (
        model_replay_attestation.attestation_id
    )
    expected_claim_id = _hash("claim", expected["claim_payload"])
    if (
        claimed.authority_chain_id != authority_chain.chain_id
        or claimed.anchor_id != anchor.anchor_id
        or claimed.occurrence_id != occurrence_plan.occurrence_id
        or claimed.failed_audit_id != failed_audit.audit_id
        or claimed.failed_frontier_id
        != failed_audit.failed_frontier.frontier_id
        or claimed.model_pair_id != model_pair.model_pair_id
        or claimed.model_replay_attestation_id
        != model_replay_attestation.attestation_id
        or claimed.supporting_acquisition_ids
        != expected["acquisition_ids"]
        or claimed.supporting_row_binding_ids
        != expected["acquisition_rows"]
        or claimed.cumulative_draw_upper_before_round
        != expected["previous_draws"]
        or claimed.claim_id != expected_claim_id
    ):
        raise V072RegisteredSelectorIndependentVerificationFailure(
            "selector claim content/dependency identity differs"
        )
    selected = claimed.selected_candidate
    if selected is None:
        promotion = None
        new_children: tuple[str, ...] = ()
        selected_rows: tuple[str, ...] = ()
        selected_draws = 0
        cumulative = expected["previous_draws"]
    else:
        promotion = selected.promotion_row_binding_id
        new_children = tuple(
            item.row_binding_id for item in selected.new_child_rows
        )
        selected_rows = selected.selected_row_binding_ids
        selected_draws = selected.draw_upper
        cumulative = expected["previous_draws"] + selected_draws
    return RegisteredSelectorIndependentAttestationV1(
        _ATTESTATION_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        occurrence_plan.occurrence_id,
        occurrence_plan.template.context_id,
        occurrence_plan.template.arm,
        round_index,
        (
            None
            if predecessor_frontier is None
            else predecessor_frontier.frontier_id
        ),
        failed_audit.audit_id,
        model_pair.model_pair_id,
        model_replay_attestation.attestation_id,
        expected["inventory_id"],
        expected["order_id"],
        expected["causal_evidence_id"],
        claimed.claim_id,
        expected["outcome"],
        expected["selected"],
        expected["acquisition_ids"],
        expected["acquisition_rows"],
        promotion,
        new_children,
        selected_rows,
        selected_draws,
        cumulative,
    )


__all__ = [
    "PROFILE_KEY",
    "RegisteredSelectorIndependentAttestationV1",
    "RegisteredSelectorIndependentGateLockedV1",
    "SCHEMA_VERSION",
    "V072RegisteredSelectorIndependentVerificationFailure",
    "replay_generic_boundary_selection_independently_v1",
    "verify_registered_selector_independently_v1",
]
