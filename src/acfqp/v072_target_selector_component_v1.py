"""Production selector plus a separately implemented semantic verifier.

The operational half calls the frozen V0-072 target selector exactly once.
The semantic half independently replays the standard-model selected policy,
every one-row zero-``OTHER`` counterfactual, arm multiplier, stable ranking,
native-zero access log, and authorization identity.  It does not call the
production selector's preparation, counterfactual, score, or schedule
helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import verified_source_acquisition_archive_v2 as source_v2


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_target_selector_component_v1"
VERIFICATION_PROFILE = (
    "v072_target_selector_independent_semantic_replay_v1"
)

DOMAIN_TAGS = {
    "counterfactual_replay": (
        "acfqp:v072-target-selector-counterfactual-semantic-replay:v1"
    ),
    "verification": (
        "acfqp:v072-target-selector-semantic-verification:v1"
    ),
    "component": "acfqp:v072-target-selector-component:v1",
    "optimistic_destination": (
        "acfqp:v072-row-bound-optimistic-success-destination:v2"
    ),
    "optimistic_resolution": (
        "acfqp:v072-mass-preserving-optimistic-resolution:v2"
    ),
}


class V072TargetSelectorComponentInvariantViolation(ValueError):
    """The selector claim differs from independent semantic replay."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072TargetSelectorComponentInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072TargetSelectorComponentInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072TargetSelectorComponentInvariantViolation(
            "selector semantic replay requires exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


@dataclass(frozen=True, slots=True)
class _FixedPolicyReplayV1:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    certificate_slack: Fraction
    selected_row_bounds: tuple[robust.RobustSelectedRowBoundV1, ...]
    selected_row_provenance: tuple[
        robust.SelectedRowProvenanceV1, ...
    ]


def _fixed_policy_replay(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> _FixedPolicyReplayV1:
    assignments = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if len(assignments) != len(audit.assignments):
        raise V072TargetSelectorComponentInvariantViolation(
            "selected policy duplicates a decision scope"
        )
    catalogue_by_state, destination_by_id, row_by_key = (
        robust._registries(model)
    )
    child_states = robust._reachable_child_states(model)
    child_values: dict[str, robust._StateActionEvaluation] = {}
    row_evaluations: list[robust._RowEvaluation] = []
    expected_assignment_keys: set[tuple[str, int]] = set()

    if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        if any(
            item.scope is not robust.PolicyScope.GROUND_STATE
            for item in audit.assignments
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "ground policy contains a non-ground assignment"
            )
        for state_id in child_states:
            key = (state_id, 1)
            expected_assignment_keys.add(key)
            action_id = assignments.get(key)
            if action_id is None:
                raise V072TargetSelectorComponentInvariantViolation(
                    "ground policy omits a reachable continuation state"
                )
            try:
                evaluated = robust._evaluate_ground_row(
                    row_by_key[(state_id, 1, action_id)],
                    destination_by_id=destination_by_id,
                    child_values={},
                    threshold=threshold,
                    category=(
                        robust.SelectedRowCategory.CONTINUATION_SELECTED
                    ),
                    policy_scope_key=state_id,
                )
            except (
                KeyError,
                robust.PartialSupportRobustPlannerInvariantViolation,
            ) as error:
                raise V072TargetSelectorComponentInvariantViolation(
                    "ground continuation assignment is not replayable"
                ) from error
            child_values[state_id] = robust._StateActionEvaluation(
                evaluated.bound.reward_lower,
                evaluated.bound.reward_upper,
                evaluated.bound.failure_upper,
                (evaluated,),
            )
            row_evaluations.append(evaluated)
        root_scope = model.root_state_id
        root_action = assignments.get((root_scope, 2))
        expected_assignment_keys.add((root_scope, 2))
        if root_action is None:
            raise V072TargetSelectorComponentInvariantViolation(
                "ground policy omits its root assignment"
            )
        try:
            root = robust._evaluate_ground_row(
                row_by_key[(model.root_state_id, 2, root_action)],
                destination_by_id=destination_by_id,
                child_values=child_values,
                threshold=threshold,
                category=robust.SelectedRowCategory.ROOT_SELECTED,
                policy_scope_key=root_scope,
            )
        except (
            KeyError,
            robust.PartialSupportRobustPlannerInvariantViolation,
        ) as error:
            raise V072TargetSelectorComponentInvariantViolation(
                "ground root assignment is not replayable"
            ) from error
        root_value = robust._StateActionEvaluation(
            root.bound.reward_lower,
            root.bound.reward_upper,
            root.bound.failure_upper,
            (root,),
        )
        row_evaluations.append(root)
    elif audit.solver_kind is robust.RobustSolverKind.QUOTIENT:
        if any(
            item.scope is not robust.PolicyScope.QUOTIENT_CELL
            for item in audit.assignments
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "quotient policy contains a non-cell assignment"
            )
        for state_id in child_states:
            cell = catalogue_by_state[state_id].state_coordinate_key
            key = (cell, 1)
            expected_assignment_keys.add(key)
            semantic_action = assignments.get(key)
            if semantic_action is None:
                raise V072TargetSelectorComponentInvariantViolation(
                    "quotient policy omits a reachable continuation cell"
                )
            try:
                evaluated = robust._evaluate_concretized_state_action(
                    model,
                    threshold,
                    state_id=state_id,
                    remaining_horizon=1,
                    abstract_action_key=semantic_action,
                    child_values={},
                    category=(
                        robust.SelectedRowCategory
                        .CONTINUATION_CONCRETIZER_COMPONENT
                    ),
                )
            except robust.PartialSupportRobustPlannerInvariantViolation as error:
                raise V072TargetSelectorComponentInvariantViolation(
                    "quotient continuation assignment is not replayable"
                ) from error
            child_values[state_id] = evaluated
            row_evaluations.extend(evaluated.rows)
        root_cell = catalogue_by_state[
            model.root_state_id
        ].state_coordinate_key
        root_key = (root_cell, 2)
        expected_assignment_keys.add(root_key)
        root_action = assignments.get(root_key)
        if root_action is None:
            raise V072TargetSelectorComponentInvariantViolation(
                "quotient policy omits its root cell"
            )
        try:
            root_value = robust._evaluate_concretized_state_action(
                model,
                threshold,
                state_id=model.root_state_id,
                remaining_horizon=2,
                abstract_action_key=root_action,
                child_values=child_values,
                category=(
                    robust.SelectedRowCategory
                    .ROOT_CONCRETIZER_COMPONENT
                ),
            )
        except robust.PartialSupportRobustPlannerInvariantViolation as error:
            raise V072TargetSelectorComponentInvariantViolation(
                "quotient root assignment is not replayable"
            ) from error
        row_evaluations.extend(root_value.rows)
    else:  # pragma: no cover - exact enum guarded by audit type
        raise V072TargetSelectorComponentInvariantViolation(
            "selector audit uses an unknown solver kind"
        )

    if set(assignments) != expected_assignment_keys:
        raise V072TargetSelectorComponentInvariantViolation(
            "selected policy domain changed under semantic replay"
        )
    try:
        unrestricted = robust._unrestricted_ground_reward_upper_h2(
            model,
            threshold,
        )
    except robust.PartialSupportRobustPlannerInvariantViolation as error:
        raise V072TargetSelectorComponentInvariantViolation(
            "unrestricted ground comparator is not replayable"
        ) from error
    regret = max(
        Fraction(0),
        unrestricted - root_value.reward_lower,
    ) / threshold.reward_ceiling
    slack = min(
        threshold.risk_tolerance - root_value.failure_upper,
        threshold.normalized_regret_tolerance - regret,
    )
    bounds = tuple(
        sorted(
            (item.bound for item in row_evaluations),
            key=lambda item: item.row_bound_id,
        )
    )
    provenance = tuple(
        sorted(
            (item.provenance for item in row_evaluations),
            key=lambda item: item.provenance_id,
        )
    )
    if (
        len({item.row_bound_id for item in bounds}) != len(bounds)
        or len({item.provenance_id for item in provenance})
        != len(provenance)
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "fixed-policy replay duplicated selected physical rows"
        )
    return _FixedPolicyReplayV1(
        root_value.reward_lower,
        root_value.reward_upper,
        root_value.failure_upper,
        unrestricted,
        regret,
        slack,
        bounds,
        provenance,
    )


def _verify_original_audit(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> _FixedPolicyReplayV1:
    replay = _fixed_policy_replay(model, audit, threshold)
    if (
        replay.reward_lower != audit.root_reward_lower
        or replay.failure_upper != audit.root_failure_upper
        or replay.unrestricted_reward_upper
        != audit.unrestricted_reward_upper
        or replay.normalized_regret_upper
        != audit.normalized_regret_upper
        or replay.selected_row_bounds != audit.selected_row_bounds
        or replay.selected_row_provenance
        != audit.selected_row_provenance
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "failed audit differs from independent fixed-policy replay"
        )
    return replay


def _count_bin(value: int) -> str:
    if type(value) is not int or value < 0:
        raise V072TargetSelectorComponentInvariantViolation(
            "portable feature count is invalid"
        )
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def _independent_portable_feature(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row: robust.IntervalSimplexRowV1,
) -> source_v2.PortableAcquisitionCoreFeatureV2:
    provenance = {
        item.row_id: item for item in audit.selected_row_provenance
    }.get(row.row_id)
    if provenance is None:
        raise V072TargetSelectorComponentInvariantViolation(
            "candidate row lacks selected-policy provenance"
        )
    assignments = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    selected_action = assignments.get(
        (provenance.policy_scope_key, row.remaining_horizon)
    )
    if selected_action is None:
        raise V072TargetSelectorComponentInvariantViolation(
            "candidate row is not in the selected action support"
        )
    catalogue = {
        item.state_id: item for item in model.catalogues
    }.get(row.state_id)
    if catalogue is None:
        raise V072TargetSelectorComponentInvariantViolation(
            "candidate row state lacks a public action catalogue"
        )
    if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        concretizer_support = 1
    else:
        sizes = {
            len(item.ground_action_ids)
            for item in model.concretizer_entries
            if (
                item.state_id == row.state_id
                and item.abstract_action_key == selected_action
            )
        }
        if len(sizes) != 1:
            raise V072TargetSelectorComponentInvariantViolation(
                "candidate semantic action lacks one support cardinality"
            )
        concretizer_support = next(iter(sizes))
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    try:
        categories = tuple(
            sorted(
                {
                    destination_by_id[mass.destination_id].category.value
                    for mass in row.masses
                    if mass.destination_id != row.other_destination_id
                }
            )
        )
    except KeyError as error:
        raise V072TargetSelectorComponentInvariantViolation(
            "candidate row references an unknown destination"
        ) from error
    return source_v2.PortableAcquisitionCoreFeatureV2(
        "ROOT" if row.remaining_horizon == 2 else "CONTINUATION",
        provenance.category.value,
        _count_bin(len(catalogue.actions)),
        _count_bin(concretizer_support),
        categories,
    )


def _verify_and_rebuild_registry(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: selector.TargetCandidateRegistryV2,
    previous_selection: selector.PreparedTargetSelectionV2 | None,
    previous_development_authorization: (
        selector.TargetRowAuthorizationV2 | None
    ) = None,
    previous_materializer_attestation_id: str | None = None,
) -> selector.TargetCandidateRegistryV2:
    if (
        audit.failed_frontier is None
        or registry.model_id != model.model_id
        or registry.audit_id != audit.audit_id
        or registry.frontier_id != audit.failed_frontier.frontier_id
        or registry.threshold_profile_id
        != threshold.threshold_profile_id
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "candidate registry is stale for the current failed proof"
        )
    if registry.round_index == 1:
        if (
            previous_selection is not None
            or previous_development_authorization is not None
            or previous_materializer_attestation_id is not None
            or registry.previous_registry_id is not None
            or registry.previous_authorization_id is not None
            or registry.cumulative_new_child_actions_before_round != 0
            or registry.cumulative_draw_upper_before_round != 0
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "round one contains a transplanted predecessor"
            )
    else:
        standard_predecessor = (
            type(previous_selection)
            is selector.PreparedTargetSelectionV2
            and previous_development_authorization is None
            and previous_materializer_attestation_id is None
        )
        development_predecessor = (
            previous_selection is None
            and type(previous_development_authorization)
            is selector.TargetRowAuthorizationV2
            and previous_materializer_attestation_id is not None
        )
        if standard_predecessor:
            assert previous_selection is not None
            previous_registry_id = (
                previous_selection.registry.registry_id
            )
            previous_authorization = previous_selection.authorization
            previous_model_id = previous_selection.registry.model_id
            previous_audit_id = previous_selection.registry.audit_id
            previous_frontier_id = (
                previous_selection.registry.frontier_id
            )
            previous_support_epoch_id = (
                previous_selection.registry.support_epoch_id
            )
        elif development_predecessor:
            assert previous_development_authorization is not None
            _cid(
                previous_materializer_attestation_id,
                "development predecessor materializer attestation",
            )
            previous_registry_id = (
                previous_development_authorization.registry_id
            )
            previous_authorization = (
                previous_development_authorization
            )
            previous_model_id = previous_authorization.model_id
            previous_audit_id = previous_authorization.audit_id
            previous_frontier_id = previous_authorization.frontier_id
            previous_support_epoch_id = (
                previous_authorization.support_epoch_id
            )
        else:
            raise V072TargetSelectorComponentInvariantViolation(
                "round two requires exactly one typed predecessor mode"
            )
        if (
            previous_authorization.round_index != 1
            or registry.previous_registry_id != previous_registry_id
            or registry.previous_authorization_id
            != previous_authorization.authorization_id
            or registry.cumulative_new_child_actions_before_round
            != (
                previous_authorization
                .cumulative_new_child_actions_after_selection
            )
            or registry.cumulative_draw_upper_before_round
            != (
                previous_authorization
                .cumulative_draw_upper_after_selection
            )
            or model.model_id == previous_model_id
            or audit.audit_id == previous_audit_id
            or audit.failed_frontier.frontier_id
            == previous_frontier_id
            or registry.support_epoch_id == previous_support_epoch_id
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "round two predecessor or rebuilt identity chain is stale"
            )
    row_by_id = {item.row_id: item for item in model.rows}
    catalogue_by_state = {
        item.state_id: item for item in model.catalogues
    }
    currently_reachable = set(robust._reachable_child_states(model))
    candidate_by_row = {
        item.planner_row_id: item for item in registry.candidates
    }
    if set(candidate_by_row) != set(
        audit.failed_frontier.selected_row_ids
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "registry candidates do not cover exactly the failed frontier"
        )
    rebuilt_candidates: list[selector.TargetAcquisitionCandidateV2] = []
    for planner_row_id in audit.failed_frontier.selected_row_ids:
        candidate = candidate_by_row[planner_row_id]
        row = row_by_id.get(planner_row_id)
        metadata = candidate.row_metadata
        if (
            row is None
            or (
                metadata.state_id,
                metadata.remaining_horizon,
                metadata.action_id,
            )
            != row.row_key
            or candidate.model_id != model.model_id
            or candidate.audit_id != audit.audit_id
            or candidate.frontier_id
            != audit.failed_frontier.frontier_id
            or candidate.threshold_profile_id
            != threshold.threshold_profile_id
            or candidate.support_epoch_id != registry.support_epoch_id
            or any(
                (
                    catalogue_by_state.get(item.state_id) is not None
                    and catalogue_by_state.get(item.state_id) != item
                )
                or item.state_id in currently_reachable
                for item in metadata.newly_reachable_child_catalogues
            )
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "registry contains a transplanted row or public catalogue"
            )
        expected_feature = _independent_portable_feature(
            model=model,
            audit=audit,
            row=row,
        )
        rebuilt = selector.TargetAcquisitionCandidateV2(
            model.model_id,
            audit.audit_id,
            audit.failed_frontier.frontier_id,
            threshold.threshold_profile_id,
            registry.support_epoch_id,
            metadata,
            expected_feature,
        )
        if rebuilt != candidate:
            raise V072TargetSelectorComponentInvariantViolation(
                "candidate feature or identity differs from public replay"
            )
        rebuilt_candidates.append(rebuilt)
    ordered_candidates = tuple(
        sorted(rebuilt_candidates, key=lambda item: item.candidate_id)
    )
    metadata = selector.PublicFrontierActionCatalogueMetadataV2(
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        registry.support_epoch_id,
        tuple(
            sorted(
                (item.row_metadata for item in ordered_candidates),
                key=lambda item: item.metadata_id,
            )
        ),
    )
    if metadata.public_metadata_id != registry.public_metadata_id:
        raise V072TargetSelectorComponentInvariantViolation(
            "registry public-metadata identity was transplanted"
        )
    rebuilt = selector.TargetCandidateRegistryV2(
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        threshold.threshold_profile_id,
        registry.support_epoch_id,
        metadata.public_metadata_id,
        registry.round_index,
        registry.previous_registry_id,
        registry.previous_authorization_id,
        registry.cumulative_new_child_actions_before_round,
        registry.cumulative_draw_upper_before_round,
        ordered_candidates,
    )
    if rebuilt != registry:
        raise V072TargetSelectorComponentInvariantViolation(
            "candidate registry differs from independent reconstruction"
        )
    return rebuilt


def _one_row_zero_other_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> robust.PartialSupportIntervalModelV1:
    target = {item.row_id: item for item in model.rows}.get(
        planner_row_id
    )
    if target is None:
        raise V072TargetSelectorComponentInvariantViolation(
            "zero-OTHER candidate row is absent from the model"
        )
    replacement = replace(
        target,
        masses=tuple(
            (
                robust.IntervalDestinationMassV1(
                    mass.destination_id,
                    Fraction(0),
                    Fraction(0),
                )
                if mass.destination_id == target.other_destination_id
                else mass
            )
            for mass in target.masses
        ),
    )
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=tuple(
            replacement if item.row_id == planner_row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )


def _mass_preserving_optimistic_resolution_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> tuple[robust.PartialSupportIntervalModelV1, str, str]:
    """Independently replay the proposal-only mass-preserving resolution."""

    target = {item.row_id: item for item in model.rows}.get(
        planner_row_id
    )
    if target is None:
        raise V072TargetSelectorComponentInvariantViolation(
            "optimistic-resolution candidate row is absent"
        )
    other = target.other_mass
    zero_lower_sum = sum(
        (
            item.lower
            for item in target.masses
            if item.destination_id != target.other_destination_id
        ),
        Fraction(0),
    )
    zero_upper_sum = sum(
        (
            item.upper
            for item in target.masses
            if item.destination_id != target.other_destination_id
        ),
        Fraction(0),
    )
    if zero_lower_sum > 1 or zero_upper_sum >= 1:
        raise V072TargetSelectorComponentInvariantViolation(
            "optimistic replay requires the typed zero-OTHER "
            "upper-sum-deficit case"
        )
    destination_id = _content_id(
        "optimistic_destination",
        {
            "schema": (
                "acfqp.v072_row_bound_optimistic_success_destination.v2"
            ),
            "schema_version": selector.SCHEMA_VERSION,
            "model_id": model.model_id,
            "planner_row_id": target.row_id,
            "original_other_destination_id": (
                target.other_destination_id
            ),
            "preserved_lower": _fdoc(other.lower),
            "preserved_upper": _fdoc(other.upper),
            "zero_other_lower_sum": _fdoc(zero_lower_sum),
            "zero_other_upper_sum": _fdoc(zero_upper_sum),
            "zero_other_simplex_disposition": "UPPER_SUM_DEFICIT",
            "category": (
                robust.DestinationCategory.SUCCESS_TERMINAL.value
            ),
            "proposal_only": True,
            "certificate_authority": False,
        },
    )
    destination = robust.RegisteredDestinationV1(
        destination_id,
        robust.DestinationCategory.SUCCESS_TERMINAL,
    )
    replacement = replace(
        target,
        masses=tuple(
            sorted(
                (
                    *(
                        (
                            robust.IntervalDestinationMassV1(
                                mass.destination_id,
                                Fraction(0),
                                Fraction(0),
                            )
                            if mass.destination_id
                            == target.other_destination_id
                            else mass
                        )
                        for mass in target.masses
                    ),
                    robust.IntervalDestinationMassV1(
                        destination_id,
                        other.lower,
                        other.upper,
                    ),
                ),
                key=lambda item: item.destination_id,
            )
        ),
    )
    resolved = robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=tuple(
            sorted(
                (*model.destinations, destination),
                key=lambda item: item.destination_id,
            )
        ),
        rows=tuple(
            replacement if item.row_id == planner_row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )
    resolution_id = _content_id(
        "optimistic_resolution",
        {
            "schema": (
                "acfqp.v072_mass_preserving_optimistic_resolution.v2"
            ),
            "schema_version": selector.SCHEMA_VERSION,
            "source_model_id": model.model_id,
            "planner_row_id": target.row_id,
            "source_other_destination_id": (
                target.other_destination_id
            ),
            "source_other_lower": _fdoc(other.lower),
            "source_other_upper": _fdoc(other.upper),
            "zero_other_lower_sum": _fdoc(zero_lower_sum),
            "zero_other_upper_sum": _fdoc(zero_upper_sum),
            "zero_other_simplex_disposition": "UPPER_SUM_DEFICIT",
            "resolution_destination_id": destination_id,
            "resolution_model_id": resolved.model_id,
            "unique_new_destination_count": 1,
            "other_interval_preserved_exactly": True,
            "all_other_rows_and_masses_unchanged": True,
            "proposal_only": True,
            "certificate_authority": False,
        },
    )
    return resolved, destination_id, resolution_id


@dataclass(frozen=True, slots=True)
class V072TargetSelectorCounterfactualSemanticReplayV1:
    counterfactual_id: str
    candidate_id: str
    planner_row_id: str
    zero_other_model_id: str | None
    status: selector.CounterfactualEvaluationStatusV2
    current_slack: Fraction
    counterfactual_slack: Fraction | None
    gain: Fraction
    base: Fraction
    exact_draw_upper: int
    resolution_model_id: str | None = None
    resolution_destination_id: str | None = None
    optimistic_resolution_id: str | None = None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.counterfactual_id, "replayed counterfactual"),
            (self.candidate_id, "replayed candidate"),
            (self.planner_row_id, "replayed planner row"),
        ):
            _cid(value, field_name)
        if self.zero_other_model_id is not None:
            _cid(self.zero_other_model_id, "replayed zero-OTHER model")
        for value, field_name in (
            (self.resolution_model_id, "replayed resolution model"),
            (
                self.resolution_destination_id,
                "replayed resolution destination",
            ),
            (
                self.optimistic_resolution_id,
                "replayed optimistic resolution",
            ),
        ):
            if value is not None:
                _cid(value, field_name)
        if (
            type(self.status)
            is not selector.CounterfactualEvaluationStatusV2
            or type(self.current_slack) is not Fraction
            or (
                self.counterfactual_slack is not None
                and type(self.counterfactual_slack) is not Fraction
            )
            or type(self.gain) is not Fraction
            or type(self.base) is not Fraction
            or type(self.exact_draw_upper) is not int
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "counterfactual semantic replay is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_target_selector_counterfactual_semantic_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "counterfactual_id": self.counterfactual_id,
            "candidate_id": self.candidate_id,
            "planner_row_id": self.planner_row_id,
            "zero_other_model_id": self.zero_other_model_id,
            "resolution_model_id": self.resolution_model_id,
            "resolution_destination_id": self.resolution_destination_id,
            "optimistic_resolution_id": self.optimistic_resolution_id,
            "status": self.status.value,
            "current_slack": _fdoc(self.current_slack),
            "counterfactual_slack": (
                None
                if self.counterfactual_slack is None
                else _fdoc(self.counterfactual_slack)
            ),
            "gain": _fdoc(self.gain),
            "base": _fdoc(self.base),
            "exact_draw_upper": self.exact_draw_upper,
        }

    @property
    def replay_id(self) -> str:
        return _content_id("counterfactual_replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def _replay_counterfactuals(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: selector.TargetCandidateRegistryV2,
    current_slack: Fraction,
) -> tuple[
    tuple[selector.OneRowCounterfactualGainV2, ...],
    tuple[V072TargetSelectorCounterfactualSemanticReplayV1, ...],
]:
    counterfactuals: list[selector.OneRowCounterfactualGainV2] = []
    replay_records: list[
        V072TargetSelectorCounterfactualSemanticReplayV1
    ] = []
    for candidate in registry.candidates:
        common = (
            registry.registry_id,
            candidate.candidate_id,
            model.model_id,
            audit.audit_id,
            registry.frontier_id,
            threshold.threshold_profile_id,
            registry.support_epoch_id,
            candidate.planner_row_id,
            candidate.exact_draw_upper,
        )
        resolution_destination_id = None
        optimistic_resolution_id = None
        status = selector.CounterfactualEvaluationStatusV2.EVALUATED
        candidate_row = {
            item.row_id: item for item in model.rows
        }.get(candidate.planner_row_id)
        if candidate_row is None:
            raise V072TargetSelectorComponentInvariantViolation(
                "counterfactual candidate row is absent"
            )
        zero_lower_sum = sum(
            (
                item.lower
                for item in candidate_row.masses
                if item.destination_id
                != candidate_row.other_destination_id
            ),
            Fraction(0),
        )
        zero_upper_sum = sum(
            (
                item.upper
                for item in candidate_row.masses
                if item.destination_id
                != candidate_row.other_destination_id
            ),
            Fraction(0),
        )
        if zero_lower_sum > 1:
            counterfactual = selector.OneRowCounterfactualGainV2(
                *common,
                selector.CounterfactualEvaluationStatusV2
                .INFEASIBLE_SIMPLEX,
                None,
                current_slack,
                None,
                Fraction(0),
                Fraction(0),
            )
            counterfactuals.append(counterfactual)
            replay_records.append(
                V072TargetSelectorCounterfactualSemanticReplayV1(
                    counterfactual.counterfactual_id,
                    candidate.candidate_id,
                    candidate.planner_row_id,
                    counterfactual.zero_other_model_id,
                    counterfactual.status,
                    counterfactual.current_slack,
                    counterfactual.counterfactual_slack,
                    counterfactual.gain,
                    counterfactual.base,
                    counterfactual.exact_draw_upper,
                )
            )
            continue
        if zero_upper_sum < 1:
            try:
                zero_model, resolution_destination_id, (
                    optimistic_resolution_id
                ) = _mass_preserving_optimistic_resolution_model(
                    model,
                    candidate.planner_row_id,
                )
                status = (
                    selector.CounterfactualEvaluationStatusV2
                    .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
                )
            except robust.PartialSupportRobustPlannerInvariantViolation as error:
                raise V072TargetSelectorComponentInvariantViolation(
                    "typed optimistic-resolution replay construction failed"
                ) from error
        else:
            try:
                zero_model = _one_row_zero_other_model(
                    model,
                    candidate.planner_row_id,
                )
            except robust.PartialSupportRobustPlannerInvariantViolation as error:
                raise V072TargetSelectorComponentInvariantViolation(
                    "admissible zero-OTHER replay construction failed"
                ) from error
        try:
            zero_replay = _fixed_policy_replay(
                zero_model,
                audit,
                threshold,
            )
        except robust.PartialSupportRobustPlannerInvariantViolation as error:
            raise V072TargetSelectorComponentInvariantViolation(
                "counterfactual fixed-policy semantic replay failed"
            ) from error
        else:
            counterfactual_slack = zero_replay.certificate_slack
            gain = max(
                Fraction(0),
                counterfactual_slack - current_slack,
            )
            counterfactual = selector.OneRowCounterfactualGainV2(
                *common,
                status,
                (
                    zero_model.model_id
                    if status
                    is selector.CounterfactualEvaluationStatusV2.EVALUATED
                    else None
                ),
                current_slack,
                counterfactual_slack,
                gain,
                gain / candidate.exact_draw_upper,
                resolution_model_id=(
                    zero_model.model_id
                    if status
                    is selector.CounterfactualEvaluationStatusV2
                    .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
                    else None
                ),
                resolution_destination_id=resolution_destination_id,
                optimistic_resolution_id=optimistic_resolution_id,
            )
        counterfactuals.append(counterfactual)
        replay_records.append(
            V072TargetSelectorCounterfactualSemanticReplayV1(
                counterfactual.counterfactual_id,
                candidate.candidate_id,
                candidate.planner_row_id,
                counterfactual.zero_other_model_id,
                counterfactual.status,
                counterfactual.current_slack,
                counterfactual.counterfactual_slack,
                counterfactual.gain,
                counterfactual.base,
                counterfactual.exact_draw_upper,
                counterfactual.resolution_model_id,
                counterfactual.resolution_destination_id,
                counterfactual.optimistic_resolution_id,
            )
        )
    return (
        tuple(
            sorted(
                counterfactuals,
                key=lambda item: item.counterfactual_id,
            )
        ),
        tuple(
            sorted(replay_records, key=lambda item: item.replay_id)
        ),
    )


def _resolve_prior(
    *,
    arm: selector.TargetSelectionArmV2,
    source_prior: selector.VerifiedSourcePriorBindingV2 | None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None,
) -> selector.PriorResolutionKindV2:
    if arm in (
        selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
    ):
        if (
            type(source_prior)
            is not selector.VerifiedSourcePriorBindingV2
            or ood_abstention is not None
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "source arm lacks exactly one verified source binding"
            )
        return selector.PriorResolutionKindV2.SOURCE_ARCHIVE_APPLIED
    if arm is selector.TargetSelectionArmV2.NO_PRIOR:
        if source_prior is not None or ood_abstention is not None:
            raise V072TargetSelectorComponentInvariantViolation(
                "no-prior arm received a prior artifact"
            )
        return selector.PriorResolutionKindV2.NO_PRIOR
    if (
        arm is not selector.TargetSelectionArmV2.OOD_ABSTENTION
        or source_prior is not None
        or type(ood_abstention)
        is not selector.OodPriorTypedAbstentionV2
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "OOD arm lacks its exact typed abstention"
        )
    return selector.PriorResolutionKindV2.OOD_TYPED_ABSTENTION


def _replay_scores(
    *,
    registry: selector.TargetCandidateRegistryV2,
    counterfactuals: tuple[
        selector.OneRowCounterfactualGainV2, ...
    ],
    arm: selector.TargetSelectionArmV2,
    source_prior: selector.VerifiedSourcePriorBindingV2 | None,
) -> tuple[selector.TargetArmRankingScoreV2, ...]:
    candidate_by_id = {
        item.candidate_id: item for item in registry.candidates
    }
    consensus_by_feature = (
        {}
        if source_prior is None
        else {
            item.feature_key: item for item in source_prior.consensus
        }
    )
    scores: list[selector.TargetArmRankingScoreV2] = []
    for counterfactual in counterfactuals:
        candidate = candidate_by_id.get(counterfactual.candidate_id)
        if candidate is None:
            raise V072TargetSelectorComponentInvariantViolation(
                "counterfactual references an unknown candidate"
            )
        consensus = consensus_by_feature.get(
            candidate.feature.feature_key
        )
        if arm is selector.TargetSelectionArmV2.NO_PRIOR:
            binding_id = None
            consensus_id = None
            disposition = "NO_PRIOR"
            q = None
            multiplier = Fraction(1)
        elif arm is selector.TargetSelectionArmV2.OOD_ABSTENTION:
            binding_id = None
            consensus_id = None
            disposition = "SCHEMA_MISMATCH"
            q = None
            multiplier = Fraction(1)
        else:
            assert source_prior is not None
            binding_id = source_prior.source_prior_binding_id
            if (
                consensus is None
                or consensus.disposition
                is not source_v2.FeatureConsensusDispositionV2.APPLIED
            ):
                consensus_id = None
                q = None
                disposition = (
                    "UNSEEN"
                    if consensus is None
                    else consensus.disposition.value
                )
                if disposition not in selector.TARGET_FEATURE_DISPOSITIONS:
                    raise V072TargetSelectorComponentInvariantViolation(
                        "source consensus disposition is unregistered"
                    )
                multiplier = Fraction(1)
            else:
                consensus_id = consensus.consensus_id
                disposition = "APPLIED"
                q = consensus.mean_midrank
                multiplier = (
                    Fraction(1, 2) + Fraction(3, 2) * q
                    if arm
                    is selector.TargetSelectionArmV2
                    .SOURCE_CONSENSUS_PRIOR
                    else Fraction(1, 2)
                    + Fraction(3, 2) * (1 - q)
                )
        scores.append(
            selector.TargetArmRankingScoreV2(
                counterfactual.counterfactual_id,
                candidate.candidate_id,
                candidate.feature.feature_key,
                arm,
                binding_id,
                consensus_id,
                disposition,
                q,
                counterfactual.base,
                multiplier,
                counterfactual.base * multiplier,
                counterfactual.gain,
                counterfactual.exact_draw_upper,
                counterfactual.eligible,
            )
        )
    return tuple(sorted(scores, key=lambda item: item.score_id))


def _schedule_key(
    item: selector.TargetSelectionScheduleEntryV2,
) -> tuple[Fraction, Fraction, int, str]:
    return (
        -item.score,
        -item.gain,
        item.exact_draw_upper,
        item.candidate_id,
    )


def _replay_schedule(
    *,
    registry: selector.TargetCandidateRegistryV2,
    scores: tuple[selector.TargetArmRankingScoreV2, ...],
) -> selector.TargetSelectionScheduleCoreV2:
    candidate_by_id = {
        item.candidate_id: item for item in registry.candidates
    }
    entries: list[selector.TargetSelectionScheduleEntryV2] = []
    for score in scores:
        candidate = candidate_by_id.get(score.candidate_id)
        if candidate is None:
            raise V072TargetSelectorComponentInvariantViolation(
                "score references an unknown candidate"
            )
        cap_eligible = (
            registry.cumulative_new_child_actions_before_round
            + candidate.n_new_child_actions
            <= selector.MAX_NEW_CHILD_ACTIONS_TOTAL
            and registry.cumulative_draw_upper_before_round
            + candidate.exact_draw_upper
            <= selector.MAX_TWO_ROUND_DRAW_UPPER
        )
        entries.append(
            selector.TargetSelectionScheduleEntryV2(
                score.counterfactual_id,
                score.candidate_id,
                score.score,
                score.gain,
                score.exact_draw_upper,
                score.gain_eligible,
                cap_eligible,
            )
        )
    ordered = tuple(sorted(entries, key=_schedule_key))
    eligible = tuple(
        item
        for item in ordered
        if item.gain_eligible and item.cap_eligible
    )
    if not eligible:
        raise V072TargetSelectorComponentInvariantViolation(
            "independent schedule has no positive-gain cap-eligible row"
        )
    return selector.TargetSelectionScheduleCoreV2(
        registry.registry_id,
        registry.round_index,
        ordered,
        eligible[0].candidate_id,
    )


@dataclass(frozen=True, slots=True)
class V072TargetSelectorSemanticVerificationV1:
    prepared_selection_id: str
    model_id: str
    audit_id: str
    threshold_profile_id: str
    registry_id: str
    round_index: int
    previous_prepared_selection_id: str | None
    arm: selector.TargetSelectionArmV2
    prior_resolution: selector.PriorResolutionKindV2
    counterfactual_replays: tuple[
        V072TargetSelectorCounterfactualSemanticReplayV1, ...
    ]
    score_ids: tuple[str, ...]
    schedule_core_id: str
    access_log_id: str
    authorization_id: str
    selected_candidate_id: str
    selected_planner_row_id: str
    previous_development_authorization_id: str | None = None
    previous_materializer_attestation_id: str | None = None
    semantic_replay_valid: bool = True
    production_prepare_or_private_derivation_called: bool = False
    caller_score_or_gain_trusted: bool = False
    native_zero_access_verified: bool = True

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.prepared_selection_id, "verified prepared selection"),
            (self.model_id, "verified model"),
            (self.audit_id, "verified audit"),
            (self.threshold_profile_id, "verified threshold"),
            (self.registry_id, "verified registry"),
            (self.schedule_core_id, "verified schedule"),
            (self.access_log_id, "verified access log"),
            (self.authorization_id, "verified authorization"),
            (self.selected_candidate_id, "verified candidate"),
            (self.selected_planner_row_id, "verified planner row"),
        ):
            _cid(value, field_name)
        if self.previous_prepared_selection_id is not None:
            _cid(
                self.previous_prepared_selection_id,
                "verified previous prepared selection",
            )
        if self.previous_development_authorization_id is not None:
            _cid(
                self.previous_development_authorization_id,
                "verified previous development authorization",
            )
        if self.previous_materializer_attestation_id is not None:
            _cid(
                self.previous_materializer_attestation_id,
                "verified previous materializer attestation",
            )
        predecessor_count = sum(
            (
                self.previous_prepared_selection_id is not None,
                self.previous_development_authorization_id is not None
                and self.previous_materializer_attestation_id is not None,
            )
        )
        if (
            self.round_index not in (1, 2)
            or (
                self.round_index == 1
                and (
                    predecessor_count != 0
                    or self.previous_development_authorization_id
                    is not None
                    or self.previous_materializer_attestation_id
                    is not None
                )
            )
            or (
                self.round_index == 2
                and predecessor_count != 1
            )
            or
            type(self.arm) is not selector.TargetSelectionArmV2
            or type(self.prior_resolution)
            is not selector.PriorResolutionKindV2
            or type(self.counterfactual_replays) is not tuple
            or not self.counterfactual_replays
            or any(
                type(item)
                is not V072TargetSelectorCounterfactualSemanticReplayV1
                for item in self.counterfactual_replays
            )
            or tuple(
                item.replay_id for item in self.counterfactual_replays
            )
            != tuple(
                sorted(
                    {
                        item.replay_id
                        for item in self.counterfactual_replays
                    }
                )
            )
            or type(self.score_ids) is not tuple
            or not self.score_ids
            or tuple(_cid(item, "verified score") for item in self.score_ids)
            != tuple(sorted(set(self.score_ids)))
            or self.semantic_replay_valid is not True
            or self.production_prepare_or_private_derivation_called is not False
            or self.caller_score_or_gain_trusted is not False
            or self.native_zero_access_verified is not True
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "selector semantic verification is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_target_selector_semantic_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile": VERIFICATION_PROFILE,
            "prepared_selection_id": self.prepared_selection_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "registry_id": self.registry_id,
            "round_index": self.round_index,
            "previous_prepared_selection_id": (
                self.previous_prepared_selection_id
            ),
            "previous_development_authorization_id": (
                self.previous_development_authorization_id
            ),
            "previous_materializer_attestation_id": (
                self.previous_materializer_attestation_id
            ),
            "predecessor_kind": (
                "PREPARED_SELECTION"
                if self.previous_prepared_selection_id is not None
                else (
                    "DEVELOPMENT_AUTHORIZATION_WITH_INDEPENDENT_"
                    "MATERIALIZER_ATTESTATION"
                    if self.previous_development_authorization_id
                    is not None
                    else "NONE_ROUND_ONE"
                )
            ),
            "arm": self.arm.value,
            "prior_resolution": self.prior_resolution.value,
            "counterfactual_replay_ids": [
                item.replay_id for item in self.counterfactual_replays
            ],
            "score_ids": list(self.score_ids),
            "schedule_core_id": self.schedule_core_id,
            "access_log_id": self.access_log_id,
            "authorization_id": self.authorization_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "semantic_replay_valid": True,
            "production_prepare_or_private_derivation_called": False,
            "caller_score_or_gain_trusted": False,
            "native_zero_access_verified": True,
            "target_observer_calls": 0,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counterfactual_replays": [
                item.to_document()
                for item in self.counterfactual_replays
            ],
            "verification_id": self.verification_id,
        }


def verify_target_selection_semantically_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: selector.TargetCandidateRegistryV2,
    arm: selector.TargetSelectionArmV2,
    claimed: selector.PreparedTargetSelectionV2,
    previous_selection: selector.PreparedTargetSelectionV2 | None = None,
    previous_development_authorization: (
        selector.TargetRowAuthorizationV2 | None
    ) = None,
    previous_materializer_attestation_id: str | None = None,
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
) -> V072TargetSelectorSemanticVerificationV1:
    """Independently replay one frozen selector result.

    ``claimed`` is evidence to be checked; no contained score or gain is used
    as an input to the replay.
    """

    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(registry) is not selector.TargetCandidateRegistryV2
        or type(arm) is not selector.TargetSelectionArmV2
        or type(claimed) is not selector.PreparedTargetSelectionV2
        or model.context_id != threshold.context_id
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "semantic verifier requires one exact failed standard-model chain"
        )
    prior_resolution = _resolve_prior(
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    rebuilt_registry = _verify_and_rebuild_registry(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        previous_selection=previous_selection,
        previous_development_authorization=(
            previous_development_authorization
        ),
        previous_materializer_attestation_id=(
            previous_materializer_attestation_id
        ),
    )
    original = _verify_original_audit(model, audit, threshold)
    expected_counterfactuals, replay_records = _replay_counterfactuals(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=rebuilt_registry,
        current_slack=original.certificate_slack,
    )
    expected_scores = _replay_scores(
        registry=rebuilt_registry,
        counterfactuals=expected_counterfactuals,
        arm=arm,
        source_prior=source_prior,
    )
    expected_schedule = _replay_schedule(
        registry=rebuilt_registry,
        scores=expected_scores,
    )
    native_zeros = tuple(
        selector.NativeZeroPreauthorizationCounterV2(path)
        for path in selector.REQUIRED_NATIVE_ZERO_PATHS
    )
    expected_access = selector.TargetPreauthorizationAccessLogV2(
        rebuilt_registry.registry_id,
        model.model_id,
        audit.audit_id,
        rebuilt_registry.frontier_id,
        threshold.threshold_profile_id,
        rebuilt_registry.support_epoch_id,
        rebuilt_registry.round_index,
        len(rebuilt_registry.candidates),
        len(expected_counterfactuals),
        (
            len(rebuilt_registry.candidates)
            if arm
            in (
                selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
                selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
            )
            else 0
        ),
        native_zeros,
    )
    selected = {
        item.candidate_id: item
        for item in rebuilt_registry.candidates
    }[expected_schedule.selected_candidate_id]
    expected_authorization = selector.TargetRowAuthorizationV2(
        rebuilt_registry.registry_id,
        model.model_id,
        audit.audit_id,
        rebuilt_registry.frontier_id,
        threshold.threshold_profile_id,
        rebuilt_registry.support_epoch_id,
        (
            None
            if source_prior is None
            else source_prior.source_prior_binding_id
        ),
        (
            None
            if ood_abstention is None
            else ood_abstention.abstention_id
        ),
        arm,
        rebuilt_registry.round_index,
        expected_schedule.schedule_core_id,
        expected_access.access_log_id,
        selected.candidate_id,
        selected.planner_row_id,
        selected.exact_draw_upper,
        rebuilt_registry.cumulative_new_child_actions_before_round
        + selected.n_new_child_actions,
        rebuilt_registry.cumulative_draw_upper_before_round
        + selected.exact_draw_upper,
        2 * rebuilt_registry.round_index - 1,
        2 * rebuilt_registry.round_index,
    )
    expected = selector.PreparedTargetSelectionV2(
        rebuilt_registry,
        expected_counterfactuals,
        expected_scores,
        expected_schedule,
        expected_access,
        expected_authorization,
        source_prior,
        ood_abstention,
    )
    if (
        claimed != expected
        or claimed.registry != registry
        or claimed.source_prior_binding != source_prior
        or claimed.ood_abstention != ood_abstention
        or claimed.prepared_selection_id != expected.prepared_selection_id
    ):
        raise V072TargetSelectorComponentInvariantViolation(
            "claimed gains, scores, ordering, access, or authorization differ "
            "from independent semantic replay"
        )
    return V072TargetSelectorSemanticVerificationV1(
        expected.prepared_selection_id,
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        registry.registry_id,
        registry.round_index,
        (
            None
            if previous_selection is None
            else previous_selection.prepared_selection_id
        ),
        arm,
        prior_resolution,
        replay_records,
        tuple(item.score_id for item in expected_scores),
        expected_schedule.schedule_core_id,
        expected_access.access_log_id,
        expected_authorization.authorization_id,
        selected.candidate_id,
        selected.planner_row_id,
        previous_development_authorization_id=(
            None
            if previous_development_authorization is None
            else previous_development_authorization.authorization_id
        ),
        previous_materializer_attestation_id=(
            previous_materializer_attestation_id
        ),
    )


@dataclass(frozen=True, slots=True)
class V072TargetSelectorComponentV1:
    prepared_selection: selector.PreparedTargetSelectionV2
    semantic_verification: V072TargetSelectorSemanticVerificationV1
    _component_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.prepared_selection)
            is not selector.PreparedTargetSelectionV2
            or type(self.semantic_verification)
            is not V072TargetSelectorSemanticVerificationV1
            or self.semantic_verification.prepared_selection_id
            != self.prepared_selection.prepared_selection_id
            or self.semantic_verification.registry_id
            != self.prepared_selection.registry.registry_id
            or self.semantic_verification.authorization_id
            != self.prepared_selection.authorization.authorization_id
            or self.semantic_verification.selected_candidate_id
            != self.prepared_selection.authorization.selected_candidate_id
            or self.semantic_verification.selected_planner_row_id
            != self.prepared_selection.authorization.selected_planner_row_id
        ):
            raise V072TargetSelectorComponentInvariantViolation(
                "selector component lacks its matching semantic verification"
            )
        object.__setattr__(
            self,
            "_component_id",
            _content_id("component", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_target_selector_component.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "prepared_selection_id": (
                self.prepared_selection.prepared_selection_id
            ),
            "semantic_verification_id": (
                self.semantic_verification.verification_id
            ),
            "registry_id": self.prepared_selection.registry.registry_id,
            "authorization_id": (
                self.prepared_selection.authorization.authorization_id
            ),
            "selected_candidate_id": (
                self.prepared_selection.authorization.selected_candidate_id
            ),
            "selected_planner_row_id": (
                self.prepared_selection.authorization.selected_planner_row_id
            ),
            "semantic_replay_valid": True,
            "proposal_only": True,
            "certificate_authority": False,
            "target_access_performed": False,
        }

    @property
    def component_id(self) -> str:
        return self._component_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "prepared_selection": self.prepared_selection.to_document(),
            "semantic_verification": (
                self.semantic_verification.to_document()
            ),
            "component_id": self.component_id,
        }


def prepare_and_verify_v072_target_selection_component_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: selector.TargetCandidateRegistryV2,
    arm: selector.TargetSelectionArmV2,
    previous_selection: selector.PreparedTargetSelectionV2 | None = None,
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
) -> V072TargetSelectorComponentV1:
    """Run production preparation once, then independently replay it."""

    prepared = selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    verification = verify_target_selection_semantically_v1(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=arm,
        claimed=prepared,
        previous_selection=previous_selection,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    return V072TargetSelectorComponentV1(prepared, verification)


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "VERIFICATION_PROFILE",
    "V072TargetSelectorComponentInvariantViolation",
    "V072TargetSelectorComponentV1",
    "V072TargetSelectorCounterfactualSemanticReplayV1",
    "V072TargetSelectorSemanticVerificationV1",
    "prepare_and_verify_v072_target_selection_component_v1",
    "verify_target_selection_semantically_v1",
]
