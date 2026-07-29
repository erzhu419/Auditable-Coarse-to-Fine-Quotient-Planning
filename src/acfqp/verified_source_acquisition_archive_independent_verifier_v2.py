"""Independent verifier for the V0-072 source-acquisition archive.

This verifier deliberately does not rebuild an archive through the production
archive implementation.  It consumes the immutable V0-068 campaign and its
existing full same-implementation verification, then independently derives
the seven registered checkpoint transitions, every local score, the
nonrectangular consensus, and the complete V0-072 content-identity tree.

The boundary is intentionally narrow and explicit: the V0-068 verification
being consumed is not an independent implementation.  Consequently this
module independently verifies the *archive transform*, but it must keep
``independent_source_campaign_verifier_claimed`` false.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from typing import Any, Mapping, Sequence

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import observation_support_campaign_v1 as campaign_v1
from . import observation_support_graph_acquisition_v1 as graph_acquisition
from . import partial_support_robust_planner_v1 as robust
from . import verified_source_acquisition_archive_v2 as archive_v2


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "verified_source_acquisition_archive_independent_verifier_v2"
SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY = (
    "CONSUMES_V0068_SAME_IMPLEMENTATION_FULL_REPLAY;"
    "DOES_NOT_INDEPENDENTLY_REPLAY_V0068"
)


class IndependentSourceArchiveVerificationViolation(ValueError):
    """Raised when source evidence and the claimed V0-072 archive diverge."""


def _fail(message: str) -> None:
    raise IndependentSourceArchiveVerificationViolation(message)


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentSourceArchiveVerificationViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("independent source verification requires exact Fractions")
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _archive_content_id(role: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        f"acfqp:verified-source-acquisition-archive:{role}:v2".encode(
            "utf-8"
        )
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _verification_content_id(
    role: str,
    payload: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        (
            "acfqp:verified-source-acquisition-archive-independent-verifier:"
            f"{role}:v2"
        ).encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _ordered_digest(domain: str, values: Sequence[str]) -> str:
    if type(values) is not tuple:
        _fail("raw observation sequence is not an immutable tuple")
    for value in values:
        _cid(value, "raw observation")
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(list(values))
    ).hexdigest()


def _sorted_distinct_ids(
    values: Any,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(values) is not tuple:
        _fail(f"{field} is not an immutable tuple")
    for value in values:
        _cid(value, field)
    if values != tuple(sorted(set(values))):
        _fail(f"{field} is not sorted and distinct")
    if not values and not allow_empty:
        _fail(f"{field} is empty")
    return values


def _id_tuple(values: Any, field: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        _fail(f"{field} is not an immutable tuple")
    for value in values:
        _cid(value, field)
    return values


def _count_bin(value: int) -> str:
    if type(value) is not int or value < 0:
        _fail("portable count input is invalid")
    return ("0", "1", "2", "3_PLUS")[min(value, 3)]


@dataclass(frozen=True, slots=True)
class _StateValue:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction


@dataclass(frozen=True, slots=True)
class _Metrics:
    reward_lower: Fraction
    failure_upper: Fraction
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    certificate_slack: Fraction


@dataclass(frozen=True, slots=True)
class _ExpectedTrial:
    claimed: archive_v2.VerifiedSourceLocalTrialV2
    trial_id: str
    feature_key: str
    source_context_id: str
    gain_per_draw: Fraction


def _box_simplex_optimum(
    masses: tuple[robust.IntervalDestinationMassV1, ...],
    coefficient_by_destination: Mapping[str, Fraction],
    *,
    largest_first: bool,
) -> Fraction:
    """Solve one exact interval-simplex linear program.

    The implementation starts from the lower-bound vertex and performs an
    explicit residual-capacity allocation ordered by the objective
    coefficient.  It neither calls nor shares state with either archive
    scoring or the production robust planner.
    """

    if (
        type(masses) is not tuple
        or not masses
        or {item.destination_id for item in masses}
        != set(coefficient_by_destination)
    ):
        _fail("interval-simplex objective has a changed destination domain")
    allocation: dict[str, Fraction] = {}
    residual = Fraction(1)
    capacities: list[tuple[Fraction, str, Fraction]] = []
    for mass in masses:
        if (
            type(mass) is not robust.IntervalDestinationMassV1
            or type(mass.lower) is not Fraction
            or type(mass.upper) is not Fraction
            or not 0 <= mass.lower <= mass.upper <= 1
        ):
            _fail("interval-simplex mass is malformed")
        coefficient = coefficient_by_destination[mass.destination_id]
        if type(coefficient) is not Fraction:
            _fail("interval-simplex coefficient is not exact")
        allocation[mass.destination_id] = mass.lower
        residual -= mass.lower
        capacities.append(
            (
                coefficient,
                mass.destination_id,
                mass.upper - mass.lower,
            )
        )
    if residual < 0 or residual > sum(
        (item[2] for item in capacities),
        Fraction(0),
    ):
        _fail("interval-simplex row is infeasible")
    capacities.sort(
        key=lambda item: (
            -item[0] if largest_first else item[0],
            item[1],
        )
    )
    for _, destination_id, capacity in capacities:
        amount = min(residual, capacity)
        allocation[destination_id] += amount
        residual -= amount
        if residual == 0:
            break
    if residual != 0:
        _fail("interval-simplex allocation did not close")
    return sum(
        (
            allocation[destination_id]
            * coefficient_by_destination[destination_id]
            for destination_id in allocation
        ),
        Fraction(0),
    )


def _evaluate_ground_row(
    row: robust.IntervalSimplexRowV1,
    *,
    destination_by_id: Mapping[str, robust.RegisteredDestinationV1],
    continuation_by_state: Mapping[str, _StateValue],
    threshold: robust.RobustThresholdProfileV1,
) -> _StateValue:
    risk: dict[str, Fraction] = {}
    reward_low: dict[str, Fraction] = {}
    reward_high: dict[str, Fraction] = {}
    for mass in row.masses:
        destination = destination_by_id.get(mass.destination_id)
        if destination is None:
            _fail("planner row references an unregistered destination")
        has_continuation = (
            row.remaining_horizon == 2
            and destination.category
            is robust.DestinationCategory.ACTIVE_STATE
        )
        if has_continuation:
            if destination.state_id is None:
                _fail("active destination omits its state identity")
            child = continuation_by_state.get(destination.state_id)
            if child is None:
                _fail("fixed-policy recurrence omits a reachable child")
            risk[mass.destination_id] = child.failure_upper
            reward_low[mass.destination_id] = child.reward_lower
            reward_high[mass.destination_id] = child.reward_upper
        else:
            aborts = destination.category in (
                robust.DestinationCategory.FAILURE,
                robust.DestinationCategory.OTHER,
            )
            risk[mass.destination_id] = (
                Fraction(1) if aborts else Fraction(0)
            )
            reward_low[mass.destination_id] = Fraction(0)
            reward_high[mass.destination_id] = (
                threshold.reward_ceiling
                if (
                    destination.category
                    is robust.DestinationCategory.OTHER
                    and row.remaining_horizon == 2
                )
                else Fraction(0)
            )
    lower = row.reward_lower + _box_simplex_optimum(
        row.masses,
        reward_low,
        largest_first=False,
    )
    upper = min(
        threshold.reward_ceiling,
        row.reward_upper
        + _box_simplex_optimum(
            row.masses,
            reward_high,
            largest_first=True,
        ),
    )
    failure = _box_simplex_optimum(
        row.masses,
        risk,
        largest_first=True,
    )
    if lower > upper or failure > 1:
        _fail("fixed-policy recurrence produced an invalid bound")
    return _StateValue(lower, upper, failure)


def _fixed_concretizer_value(
    *,
    model: robust.PartialSupportIntervalModelV1,
    state_id: str,
    remaining_horizon: int,
    semantic_action: str,
    continuation_by_state: Mapping[str, _StateValue],
    catalogue_by_state: Mapping[str, robust.StateActionCatalogueV1],
    destination_by_id: Mapping[str, robust.RegisteredDestinationV1],
    row_by_key: Mapping[
        tuple[str, int, str],
        robust.IntervalSimplexRowV1,
    ],
    threshold: robust.RobustThresholdProfileV1,
) -> _StateValue:
    cell = catalogue_by_state[state_id].state_coordinate_key
    entries = [
        item
        for item in model.concretizer_entries
        if (
            item.state_coordinate_key == cell
            and item.state_id == state_id
            and item.abstract_action_key == semantic_action
        )
    ]
    if len(entries) != 1:
        _fail("selected semantic action lacks one fixed concretizer")
    values: list[_StateValue] = []
    for ground_action_id in entries[0].ground_action_ids:
        row = row_by_key.get(
            (state_id, remaining_horizon, ground_action_id)
        )
        if row is None:
            _fail("selected concretizer action lacks its planner row")
        values.append(
            _evaluate_ground_row(
                row,
                destination_by_id=destination_by_id,
                continuation_by_state=continuation_by_state,
                threshold=threshold,
            )
        )
    divisor = len(values)
    return _StateValue(
        sum((item.reward_lower for item in values), Fraction(0))
        / divisor,
        sum((item.reward_upper for item in values), Fraction(0))
        / divisor,
        sum((item.failure_upper for item in values), Fraction(0))
        / divisor,
    )


def _independent_fixed_policy_metrics(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    replacement: robust.IntervalSimplexRowV1 | None = None,
) -> _Metrics:
    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or model.context_id != threshold.context_id
    ):
        _fail("fixed-policy recurrence inputs are stale or non-quotient")
    if any(
        assignment.scope is not robust.PolicyScope.QUOTIENT_CELL
        for assignment in audit.assignments
    ):
        _fail("source policy is not a deterministic quotient policy")
    assignments = {
        (assignment.scope_key, assignment.remaining_horizon):
        assignment.selected_action_key
        for assignment in audit.assignments
    }
    if len(assignments) != len(audit.assignments):
        _fail("source policy duplicates one state-time assignment")
    catalogue_by_state = {
        catalogue.state_id: catalogue for catalogue in model.catalogues
    }
    destination_by_id = {
        destination.destination_id: destination
        for destination in model.destinations
    }
    row_by_key = {row.row_key: row for row in model.rows}
    if replacement is not None:
        if (
            type(replacement) is not robust.IntervalSimplexRowV1
            or replacement.row_key not in row_by_key
        ):
            _fail("roll-forward row does not replace one registered row")
        row_by_key[replacement.row_key] = replacement

    root_catalogue = catalogue_by_state.get(model.root_state_id)
    if root_catalogue is None:
        _fail("model root catalogue is absent")
    reachable_children: set[str] = set()
    for action in root_catalogue.actions:
        root_row = row_by_key.get(
            (model.root_state_id, 2, action.action_id)
        )
        if root_row is None:
            _fail("root ground action lacks its horizon-two row")
        for mass in root_row.masses:
            destination = destination_by_id[mass.destination_id]
            if (
                mass.upper > 0
                and destination.category
                is robust.DestinationCategory.ACTIVE_STATE
            ):
                if destination.state_id is None:
                    _fail("active root destination omits a child state")
                reachable_children.add(destination.state_id)

    policy_domain: set[tuple[str, int]] = set()
    selected_child_values: dict[str, _StateValue] = {}
    unrestricted_child_values: dict[str, _StateValue] = {}
    for child_state in sorted(reachable_children):
        child_catalogue = catalogue_by_state.get(child_state)
        if child_catalogue is None:
            _fail("reachable child lacks its public action catalogue")
        policy_key = (child_catalogue.state_coordinate_key, 1)
        policy_domain.add(policy_key)
        semantic_action = assignments.get(policy_key)
        if semantic_action is None:
            _fail("fixed policy omits a reachable child quotient cell")
        selected_child_values[child_state] = _fixed_concretizer_value(
            model=model,
            state_id=child_state,
            remaining_horizon=1,
            semantic_action=semantic_action,
            continuation_by_state={},
            catalogue_by_state=catalogue_by_state,
            destination_by_id=destination_by_id,
            row_by_key=row_by_key,
            threshold=threshold,
        )
        ground_candidates = [
            _evaluate_ground_row(
                row_by_key[(child_state, 1, action.action_id)],
                destination_by_id=destination_by_id,
                continuation_by_state={},
                threshold=threshold,
            )
            for action in child_catalogue.actions
        ]
        unrestricted_child_values[child_state] = max(
            ground_candidates,
            key=lambda item: item.reward_upper,
        )

    root_policy_key = (root_catalogue.state_coordinate_key, 2)
    policy_domain.add(root_policy_key)
    root_semantic_action = assignments.get(root_policy_key)
    if root_semantic_action is None or set(assignments) != policy_domain:
        _fail("fixed policy domain is not the complete reachable H=2 domain")
    selected_root = _fixed_concretizer_value(
        model=model,
        state_id=model.root_state_id,
        remaining_horizon=2,
        semantic_action=root_semantic_action,
        continuation_by_state=selected_child_values,
        catalogue_by_state=catalogue_by_state,
        destination_by_id=destination_by_id,
        row_by_key=row_by_key,
        threshold=threshold,
    )
    unrestricted_root_upper = max(
        _evaluate_ground_row(
            row_by_key[(model.root_state_id, 2, action.action_id)],
            destination_by_id=destination_by_id,
            continuation_by_state=unrestricted_child_values,
            threshold=threshold,
        ).reward_upper
        for action in root_catalogue.actions
    )
    regret = max(
        Fraction(0),
        unrestricted_root_upper - selected_root.reward_lower,
    ) / threshold.reward_ceiling
    slack = min(
        threshold.risk_tolerance - selected_root.failure_upper,
        threshold.normalized_regret_tolerance - regret,
    )
    return _Metrics(
        selected_root.reward_lower,
        selected_root.failure_upper,
        unrestricted_root_upper,
        regret,
        slack,
    )


def _assert_metrics_equal(
    claimed: archive_v2.IndependentFixedPolicyMetricsV2,
    expected: _Metrics,
    field: str,
) -> None:
    if (
        type(claimed) is not archive_v2.IndependentFixedPolicyMetricsV2
        or claimed.reward_lower != expected.reward_lower
        or claimed.failure_upper != expected.failure_upper
        or claimed.unrestricted_reward_upper
        != expected.unrestricted_reward_upper
        or claimed.normalized_regret_upper
        != expected.normalized_regret_upper
        or claimed.certificate_slack != expected.certificate_slack
    ):
        _fail(f"{field} differs from the independent exact recurrence")


def _metrics_document(metrics: Any) -> dict[str, Any]:
    return {
        "reward_lower": _fraction_document(metrics.reward_lower),
        "failure_upper": _fraction_document(metrics.failure_upper),
        "unrestricted_reward_upper": _fraction_document(
            metrics.unrestricted_reward_upper
        ),
        "normalized_regret_upper": _fraction_document(
            metrics.normalized_regret_upper
        ),
        "certificate_slack": _fraction_document(
            metrics.certificate_slack
        ),
    }


def _assert_audit_arithmetic(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> _Metrics:
    metrics = _independent_fixed_policy_metrics(
        model=model,
        audit=audit,
        threshold=threshold,
    )
    if (
        audit.root_reward_lower != metrics.reward_lower
        or audit.root_failure_upper != metrics.failure_upper
        or audit.unrestricted_reward_upper
        != metrics.unrestricted_reward_upper
        or audit.normalized_regret_upper
        != metrics.normalized_regret_upper
    ):
        _fail("source audit fails the independent exact recurrence")
    return metrics


def _assert_structural_continuity(
    before: robust.PartialSupportIntervalModelV1,
    after: robust.PartialSupportIntervalModelV1,
) -> None:
    before_rows = {row.row_key: row for row in before.rows}
    after_rows = {row.row_key: row for row in after.rows}
    if (
        before.context_id != after.context_id
        or before.root_state_id != after.root_state_id
        or before.catalogues != after.catalogues
        or before.destinations != after.destinations
        or before.concretizer_entries != after.concretizer_entries
        or set(before_rows) != set(after_rows)
    ):
        _fail("adjacent source models changed structural semantics")
    for key in before_rows:
        if tuple(
            mass.destination_id for mass in before_rows[key].masses
        ) != tuple(
            mass.destination_id for mass in after_rows[key].masses
        ):
            _fail("adjacent source row changed its destination registry")


def _physical_row(
    execution: campaign_v1.CheckpointExecutionV1,
    planner_row: robust.IntervalSimplexRowV1,
) -> graph_acquisition.GraphPartialSupportRowV1:
    matching_projections = [
        projection
        for projection in execution.bridge.row_projections
        if projection.planner_row.row_id == planner_row.row_id
    ]
    if len(matching_projections) != 1:
        _fail("planner row lacks exactly one physical-row projection")
    projection = matching_projections[0]
    if projection.planner_row != planner_row:
        _fail("row projection carries a coherently re-signed planner row")
    matching_rows = [
        row
        for row in execution.closure.all_rows
        if row.partial_row_id == projection.partial_row_id
    ]
    if (
        len(matching_rows) != 1
        or type(matching_rows[0])
        is not graph_acquisition.GraphPartialSupportRowV1
    ):
        _fail("physical source row is absent or duplicated")
    physical = matching_rows[0]
    if (
        physical.confidence_authority.authority_id
        != projection.confidence_authority_id
        or physical.support_epoch.support_epoch_id
        != projection.support_epoch_id
    ):
        _fail("physical source row is stale relative to its projection")
    return physical


def _raw_prefix_expected(
    before: graph_acquisition.GraphPartialSupportRowV1,
    after: graph_acquisition.GraphPartialSupportRowV1,
    *,
    before_checkpoint: int,
    after_checkpoint: int,
    replayed_row_ids: set[str],
    replayed_role_row_ids: set[str],
) -> dict[str, Any]:
    before_validation = before.current_validation_observation_ids
    after_validation = after.current_validation_observation_ids
    discovery = before.initial_discovery_observation_ids
    prior_validation = before.prior_validation_observation_ids
    for values, field in (
        (discovery, "source discovery observations"),
        (prior_validation, "source prior-validation observations"),
        (before_validation, "source before-validation observations"),
        (after_validation, "source after-validation observations"),
    ):
        _id_tuple(values, field)
    if (
        before.binding != after.binding
        or before.support_epoch.support_epoch_id
        != after.support_epoch.support_epoch_id
        or before.initial_discovery_observation_ids
        != after.initial_discovery_observation_ids
        or before.prior_validation_observation_ids
        != after.prior_validation_observation_ids
        or before.support_epoch_index != 1
        or after.support_epoch_index != 1
        or len(discovery)
        != graph_acquisition.DISCOVERY_DRAW_COUNT
        or len(set(discovery)) != len(discovery)
        or len(before_validation) != before_checkpoint
        or len(after_validation) != after_checkpoint
        or len(set(before_validation)) != len(before_validation)
        or len(set(after_validation)) != len(after_validation)
        or len(set(prior_validation)) != len(prior_validation)
        or after_validation[:before_checkpoint] != before_validation
        or set(discovery) & set(before_validation)
        or set(discovery) & set(after_validation)
        or set(prior_validation)
        & (set(discovery) | set(after_validation))
    ):
        _fail("adjacent physical rows are not one exact epoch-1 raw prefix")
    for row in (before, after):
        counters = row.counters
        if (
            counters.support_epoch_index != 1
            or counters.initial_discovery_draws != len(
                row.initial_discovery_observation_ids
            )
            or counters.prior_validation_draws != len(
                row.prior_validation_observation_ids
            )
            or counters.current_validation_draws != len(
                row.current_validation_observation_ids
            )
            or counters.total_observer_draws
            != (
                counters.initial_discovery_draws
                + counters.prior_validation_draws
                + counters.current_validation_draws
            )
            or counters.discovery_random_word_calls
            != counters.initial_discovery_draws
            + counters.discovery_rejections
            or counters.prior_validation_random_word_calls
            != counters.prior_validation_draws
            + counters.prior_validation_rejections
            or counters.current_validation_random_word_calls
            != counters.current_validation_draws
            + counters.current_validation_rejections
            or counters.total_random_word_calls
            != (
                counters.discovery_random_word_calls
                + counters.prior_validation_random_word_calls
                + counters.current_validation_random_word_calls
            )
            or counters.total_rejections
            != (
                counters.discovery_rejections
                + counters.prior_validation_rejections
                + counters.current_validation_rejections
            )
        ):
            _fail("raw-prefix native counters do not reconcile")
    required_rows = {before.partial_row_id, after.partial_row_id}
    if (
        not required_rows.issubset(replayed_row_ids)
        or not required_rows.issubset(replayed_role_row_ids)
    ):
        _fail("raw-prefix rows lack consumed V0-068 replay authority")
    suffix = after_validation[before_checkpoint:]
    random_word_delta = (
        after.counters.current_validation_random_word_calls
        - before.counters.current_validation_random_word_calls
    )
    rejection_delta = (
        after.counters.current_validation_rejections
        - before.counters.current_validation_rejections
    )
    if (
        random_word_delta < 0
        or rejection_delta < 0
        or random_word_delta != len(suffix) + rejection_delta
    ):
        _fail("raw-prefix suffix counters do not reconcile")
    return {
        "binding_id": before.binding.row_id,
        "support_epoch_id": before.support_epoch.support_epoch_id,
        "before_partial_row_id": before.partial_row_id,
        "after_partial_row_id": after.partial_row_id,
        "before_physical_evidence_id": before.physical_evidence_id,
        "after_physical_evidence_id": after.physical_evidence_id,
        "discovery_ids_digest": _ordered_digest(
            "acfqp:v072-source-discovery-prefix:v1",
            discovery,
        ),
        "before_validation_ids_digest": _ordered_digest(
            "acfqp:v072-source-validation-before:v1",
            before_validation,
        ),
        "after_validation_ids_digest": _ordered_digest(
            "acfqp:v072-source-validation-after:v1",
            after_validation,
        ),
        "suffix_ids_digest": _ordered_digest(
            "acfqp:v072-source-validation-suffix:v1",
            suffix,
        ),
        "before_validation_draws": len(before_validation),
        "after_validation_draws": len(after_validation),
        "incremental_accepted_draws": len(suffix),
        "incremental_random_word_calls": random_word_delta,
        "incremental_rejections": rejection_delta,
    }


def _raw_prefix_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "acfqp.raw_prefix_extension_proof.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        **dict(fields),
        "exact_ordered_prefix": True,
        "same_support_epoch": True,
        "semantically_replayed_by_source_campaign_verification": True,
    }


def _assert_raw_prefix(
    claimed: archive_v2.RawPrefixExtensionProofV2,
    expected_fields: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    if type(claimed) is not archive_v2.RawPrefixExtensionProofV2:
        _fail("local snapshot lacks its typed raw-prefix proof")
    for field, expected in expected_fields.items():
        if getattr(claimed, field) != expected:
            _fail(f"raw-prefix {field} differs from source chronology")
    if (
        claimed.exact_ordered_prefix is not True
        or claimed.same_support_epoch is not True
        or claimed.semantically_replayed_by_source_campaign_verification
        is not True
    ):
        _fail("raw-prefix proof overstates or changes its authority")
    payload = _raw_prefix_payload(expected_fields)
    return _archive_content_id("raw-prefix-extension", payload), payload


def _portable_feature_expected(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row: robust.IntervalSimplexRowV1,
) -> dict[str, Any]:
    matching_provenance = [
        item
        for item in audit.selected_row_provenance
        if item.row_id == row.row_id
    ]
    if len(matching_provenance) != 1:
        _fail("failed-frontier row lacks one selected-policy provenance")
    provenance = matching_provenance[0]
    if (
        provenance.ground_state_id != row.state_id
        or provenance.ground_action_id != row.action_id
        or provenance.remaining_horizon != row.remaining_horizon
    ):
        _fail("selected-row provenance is stale relative to its planner row")
    assignment_by_key = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if len(assignment_by_key) != len(audit.assignments):
        _fail("portable feature sees duplicate policy assignments")
    selected_semantic_action = assignment_by_key.get(
        (provenance.policy_scope_key, row.remaining_horizon)
    )
    if selected_semantic_action is None:
        _fail("frontier row is not bound to a frozen semantic action")
    supports = [
        entry.ground_action_ids
        for entry in model.concretizer_entries
        if (
            entry.state_id == row.state_id
            and entry.abstract_action_key == selected_semantic_action
        )
    ]
    if (
        len(supports) != 1
        or row.action_id not in supports[0]
    ):
        _fail("frontier row is outside the selected concretizer support")
    catalogue_by_state = {
        item.state_id: item for item in model.catalogues
    }
    catalogue = catalogue_by_state.get(row.state_id)
    if catalogue is None:
        _fail("frontier row lacks its public action catalogue")
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    categories = tuple(
        sorted(
            {
                destination_by_id[mass.destination_id].category.value
                for mass in row.masses
                if mass.destination_id != row.other_destination_id
            }
        )
    )
    if not categories:
        _fail("portable feature has no non-OTHER destination category")
    return {
        "stage_role": (
            "ROOT" if row.remaining_horizon == 2 else "CONTINUATION"
        ),
        "selected_row_category": provenance.category.value,
        "catalogue_action_count_bin": _count_bin(
            len(catalogue.actions)
        ),
        "concretizer_support_count_bin": _count_bin(len(supports[0])),
        "destination_category_presence": categories,
    }


def _feature_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "acfqp.portable_acquisition_core_feature.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "feature_schema_id": archive_v2.FEATURE_SCHEMA_ID,
        "stage_role": fields["stage_role"],
        "selected_row_category": fields["selected_row_category"],
        "catalogue_action_count_bin": (
            fields["catalogue_action_count_bin"]
        ),
        "concretizer_support_count_bin": (
            fields["concretizer_support_count_bin"]
        ),
        "destination_category_presence": list(
            fields["destination_category_presence"]
        ),
        "ids_stripped": True,
        "exact_probabilities_absent": True,
        "exact_counts_absent": True,
        "vertex_labels_absent": True,
        "context_identity_absent": True,
        "observed_support_count_absent": True,
    }


def _assert_feature(
    claimed: archive_v2.PortableAcquisitionCoreFeatureV2,
    expected_fields: Mapping[str, Any],
    *,
    forbidden_identities: set[str],
) -> tuple[str, dict[str, Any]]:
    if type(claimed) is not archive_v2.PortableAcquisitionCoreFeatureV2:
        _fail("trial portable feature has a noncanonical type")
    for field, expected in expected_fields.items():
        if getattr(claimed, field) != expected:
            _fail(f"portable feature {field} differs from source semantics")
    if (
        claimed.feature_schema_id != archive_v2.FEATURE_SCHEMA_ID
        or claimed.ids_stripped is not True
        or claimed.exact_probabilities_absent is not True
    ):
        _fail("portable feature leaks identity/probability authority")
    payload = _feature_payload(expected_fields)
    encoded = canonical_json_bytes(payload)
    if any(identity.encode("utf-8") in encoded for identity in forbidden_identities):
        _fail("portable feature contains a source-local identity")
    for forbidden_token in (
        b'"lower"',
        b'"upper"',
        b'"probability"',
        b'"observed_support_count_bin"',
        b'"context_id"',
        b'"row_id"',
    ):
        if forbidden_token in encoded:
            _fail("portable feature contains a forbidden local field")
    return _archive_content_id("portable-feature", payload), payload


def _mass_fields(
    model: robust.PartialSupportIntervalModelV1,
    row: robust.IntervalSimplexRowV1,
) -> tuple[tuple[str, robust.DestinationCategory, Fraction, Fraction], ...]:
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    return tuple(
        (
            mass.destination_id,
            destination_by_id[mass.destination_id].category,
            mass.lower,
            mass.upper,
        )
        for mass in row.masses
    )


def _mass_document(
    values: tuple[str, robust.DestinationCategory, Fraction, Fraction],
) -> dict[str, Any]:
    return {
        "destination_id": values[0],
        "category": values[1].value,
        "lower": _fraction_document(values[2]),
        "upper": _fraction_document(values[3]),
    }


def _assert_masses(
    claimed: Any,
    expected: tuple[
        tuple[str, robust.DestinationCategory, Fraction, Fraction],
        ...,
    ],
    field: str,
) -> None:
    if (
        type(claimed) is not tuple
        or len(claimed) != len(expected)
        or any(
            type(item) is not archive_v2.IdentityBoundMassIntervalV2
            for item in claimed
        )
    ):
        _fail(f"{field} mass registry is malformed")
    observed = tuple(
        (item.destination_id, item.category, item.lower, item.upper)
        for item in claimed
    )
    if observed != expected:
        _fail(f"{field} mass registry differs from the source model")


def _snapshot_payload(
    *,
    source_context_id: str,
    before_execution_id: str,
    after_execution_id: str,
    before_model_id: str,
    after_model_id: str,
    before_audit_id: str,
    after_audit_id: str,
    threshold_profile_id: str,
    before_checkpoint: int,
    after_checkpoint: int,
    before_row: robust.IntervalSimplexRowV1,
    after_row: robust.IntervalSimplexRowV1,
    before_masses: tuple[
        tuple[str, robust.DestinationCategory, Fraction, Fraction],
        ...,
    ],
    after_masses: tuple[
        tuple[str, robust.DestinationCategory, Fraction, Fraction],
        ...,
    ],
    raw_prefix_proof_id: str,
    feature_key: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.identity_bound_local_snapshot.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "source_context_id": source_context_id,
        "before_execution_id": before_execution_id,
        "after_execution_id": after_execution_id,
        "before_model_id": before_model_id,
        "after_model_id": after_model_id,
        "before_audit_id": before_audit_id,
        "after_audit_id": after_audit_id,
        "threshold_profile_id": threshold_profile_id,
        "before_checkpoint": before_checkpoint,
        "after_checkpoint": after_checkpoint,
        "before_row_id": before_row.row_id,
        "after_row_id": after_row.row_id,
        "state_id": before_row.state_id,
        "action_id": before_row.action_id,
        "remaining_horizon": before_row.remaining_horizon,
        "before_reward_lower": _fraction_document(
            before_row.reward_lower
        ),
        "before_reward_upper": _fraction_document(
            before_row.reward_upper
        ),
        "after_reward_lower": _fraction_document(
            after_row.reward_lower
        ),
        "after_reward_upper": _fraction_document(after_row.reward_upper),
        "before_mass_intervals": [
            _mass_document(item) for item in before_masses
        ],
        "after_mass_intervals": [
            _mass_document(item) for item in after_masses
        ],
        "raw_prefix_extension_proof_id": raw_prefix_proof_id,
        "incremental_draws": after_checkpoint - before_checkpoint,
        "portable_feature_key": feature_key,
        "portable_fields_repeated": False,
    }


def _assert_snapshot(
    claimed: archive_v2.IdentityBoundLocalSnapshotV2,
    *,
    source_context_id: str,
    before_execution_id: str,
    after_execution_id: str,
    before_model: robust.PartialSupportIntervalModelV1,
    after_model: robust.PartialSupportIntervalModelV1,
    before_audit: robust.RobustPlanAuditV1,
    after_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    before_checkpoint: int,
    after_checkpoint: int,
    before_row: robust.IntervalSimplexRowV1,
    after_row: robust.IntervalSimplexRowV1,
    expected_prefix_fields: Mapping[str, Any],
    feature_key: str,
) -> tuple[str, dict[str, Any]]:
    if type(claimed) is not archive_v2.IdentityBoundLocalSnapshotV2:
        _fail("trial lacks its typed identity-bound snapshot")
    prefix_id, _ = _assert_raw_prefix(
        claimed.raw_prefix_extension,
        expected_prefix_fields,
    )
    before_masses = _mass_fields(before_model, before_row)
    after_masses = _mass_fields(after_model, after_row)
    _assert_masses(
        claimed.before_mass_intervals,
        before_masses,
        "before snapshot",
    )
    _assert_masses(
        claimed.after_mass_intervals,
        after_masses,
        "after snapshot",
    )
    expected_scalars = {
        "source_context_id": source_context_id,
        "before_execution_id": before_execution_id,
        "after_execution_id": after_execution_id,
        "before_model_id": before_model.model_id,
        "after_model_id": after_model.model_id,
        "before_audit_id": before_audit.audit_id,
        "after_audit_id": after_audit.audit_id,
        "threshold_profile_id": threshold.threshold_profile_id,
        "before_checkpoint": before_checkpoint,
        "after_checkpoint": after_checkpoint,
        "before_row_id": before_row.row_id,
        "after_row_id": after_row.row_id,
        "state_id": before_row.state_id,
        "action_id": before_row.action_id,
        "remaining_horizon": before_row.remaining_horizon,
        "before_reward_lower": before_row.reward_lower,
        "before_reward_upper": before_row.reward_upper,
        "after_reward_lower": after_row.reward_lower,
        "after_reward_upper": after_row.reward_upper,
        "incremental_draws": after_checkpoint - before_checkpoint,
        "portable_feature_key": feature_key,
    }
    for field, expected in expected_scalars.items():
        if getattr(claimed, field) != expected:
            _fail(f"identity-bound snapshot {field} is stale or forged")
    payload = _snapshot_payload(
        source_context_id=source_context_id,
        before_execution_id=before_execution_id,
        after_execution_id=after_execution_id,
        before_model_id=before_model.model_id,
        after_model_id=after_model.model_id,
        before_audit_id=before_audit.audit_id,
        after_audit_id=after_audit.audit_id,
        threshold_profile_id=threshold.threshold_profile_id,
        before_checkpoint=before_checkpoint,
        after_checkpoint=after_checkpoint,
        before_row=before_row,
        after_row=after_row,
        before_masses=before_masses,
        after_masses=after_masses,
        raw_prefix_proof_id=prefix_id,
        feature_key=feature_key,
    )
    return _archive_content_id("local-snapshot", payload), payload


def _trial_payload(
    *,
    source_context_id: str,
    feature_key: str,
    snapshot_id: str,
    before_metrics: _Metrics,
    roll_forward_metrics: _Metrics,
    slack_gain: Fraction,
    gain_per_draw: Fraction,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.verified_source_local_trial.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "source_context_id": source_context_id,
        "portable_feature_key": feature_key,
        "local_snapshot_id": snapshot_id,
        "before_metrics": _metrics_document(before_metrics),
        "roll_forward_metrics": _metrics_document(
            roll_forward_metrics
        ),
        "slack_gain": _fraction_document(slack_gain),
        "gain_per_draw": _fraction_document(gain_per_draw),
        "independent_fraction_recurrence": True,
        "production_scoring_helper_used": False,
        "caller_supplied_score": False,
        "proposal_only": True,
    }


def _assert_trial(
    claimed: archive_v2.VerifiedSourceLocalTrialV2,
    *,
    source_context_id: str,
    before_execution_id: str,
    after_execution_id: str,
    before_model: robust.PartialSupportIntervalModelV1,
    after_model: robust.PartialSupportIntervalModelV1,
    before_audit: robust.RobustPlanAuditV1,
    after_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    before_checkpoint: int,
    after_checkpoint: int,
    before_row: robust.IntervalSimplexRowV1,
    after_row: robust.IntervalSimplexRowV1,
    expected_prefix_fields: Mapping[str, Any],
    before_metrics: _Metrics,
    roll_forward_metrics: _Metrics,
) -> tuple[_ExpectedTrial, dict[str, Any]]:
    if type(claimed) is not archive_v2.VerifiedSourceLocalTrialV2:
        _fail("archive trial has a noncanonical type")
    feature_fields = _portable_feature_expected(
        model=before_model,
        audit=before_audit,
        row=before_row,
    )
    feature_key, feature_payload = _assert_feature(
        claimed.portable_feature,
        feature_fields,
        forbidden_identities={
            source_context_id,
            before_row.row_id,
            after_row.row_id,
            before_execution_id,
            after_execution_id,
            before_model.model_id,
            after_model.model_id,
            before_audit.audit_id,
            after_audit.audit_id,
        },
    )
    snapshot_id, snapshot_payload = _assert_snapshot(
        claimed.local_snapshot,
        source_context_id=source_context_id,
        before_execution_id=before_execution_id,
        after_execution_id=after_execution_id,
        before_model=before_model,
        after_model=after_model,
        before_audit=before_audit,
        after_audit=after_audit,
        threshold=threshold,
        before_checkpoint=before_checkpoint,
        after_checkpoint=after_checkpoint,
        before_row=before_row,
        after_row=after_row,
        expected_prefix_fields=expected_prefix_fields,
        feature_key=feature_key,
    )
    _assert_metrics_equal(
        claimed.before_metrics,
        before_metrics,
        "before trial metrics",
    )
    _assert_metrics_equal(
        claimed.roll_forward_metrics,
        roll_forward_metrics,
        "roll-forward trial metrics",
    )
    gain = max(
        Fraction(0),
        roll_forward_metrics.certificate_slack
        - before_metrics.certificate_slack,
    )
    draw_count = after_checkpoint - before_checkpoint
    gain_per_draw = gain / draw_count
    if (
        claimed.source_context_id != source_context_id
        or claimed.slack_gain != gain
        or claimed.gain_per_draw != gain_per_draw
        or claimed.independent_fraction_recurrence is not True
        or claimed.proposal_only is not True
    ):
        _fail("trial gain/identity differs from independent derivation")
    payload = _trial_payload(
        source_context_id=source_context_id,
        feature_key=feature_key,
        snapshot_id=snapshot_id,
        before_metrics=before_metrics,
        roll_forward_metrics=roll_forward_metrics,
        slack_gain=gain,
        gain_per_draw=gain_per_draw,
    )
    trial_id = _archive_content_id("source-trial", payload)
    document = {
        **payload,
        "portable_feature": {
            **feature_payload,
            "feature_key": feature_key,
        },
        "local_snapshot": {
            **snapshot_payload,
            "snapshot_id": snapshot_id,
        },
        "trial_id": trial_id,
    }
    return (
        _ExpectedTrial(
            claimed,
            trial_id,
            feature_key,
            source_context_id,
            gain_per_draw,
        ),
        document,
    )


def _pair_payload(
    *,
    source_context_id: str,
    source_context_key: str,
    before_checkpoint: int,
    after_checkpoint: int,
    before_execution_id: str,
    after_execution_id: str,
    before_model_id: str,
    after_model_id: str,
    before_audit_id: str,
    after_audit_id: str,
    trial_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.verified_adjacent_checkpoint_pair.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "source_context_id": source_context_id,
        "source_context_key": source_context_key,
        "before_checkpoint": before_checkpoint,
        "after_checkpoint": after_checkpoint,
        "before_execution_id": before_execution_id,
        "after_execution_id": after_execution_id,
        "before_model_id": before_model_id,
        "after_model_id": after_model_id,
        "before_audit_id": before_audit_id,
        "after_audit_id": after_audit_id,
        "trial_ids": list(trial_ids),
    }


def _assert_pair(
    claimed: archive_v2.VerifiedAdjacentCheckpointPairV2,
    *,
    source_context_id: str,
    source_context_key: str,
    before_checkpoint: int,
    after_checkpoint: int,
    before_execution_id: str,
    after_execution_id: str,
    before_model_id: str,
    after_model_id: str,
    before_audit_id: str,
    after_audit_id: str,
    trial_ids: tuple[str, ...],
) -> tuple[str, dict[str, Any]]:
    if type(claimed) is not archive_v2.VerifiedAdjacentCheckpointPairV2:
        _fail("archive pair has a noncanonical type")
    expected = {
        "source_context_id": source_context_id,
        "source_context_key": source_context_key,
        "before_checkpoint": before_checkpoint,
        "after_checkpoint": after_checkpoint,
        "before_execution_id": before_execution_id,
        "after_execution_id": after_execution_id,
        "before_model_id": before_model_id,
        "after_model_id": after_model_id,
        "before_audit_id": before_audit_id,
        "after_audit_id": after_audit_id,
        "trial_ids": trial_ids,
    }
    for field, value in expected.items():
        if getattr(claimed, field) != value:
            _fail(f"checkpoint pair {field} differs from source chronology")
    payload = _pair_payload(**expected)
    return _archive_content_id("checkpoint-pair", payload), payload


def _aggregate_payload(
    *,
    source_context_id: str,
    feature_key: str,
    trial_ids: tuple[str, ...],
    mean_gain_per_draw: Fraction,
    normalized_midrank: Fraction,
    context_ranking_degenerate: bool,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.source_context_feature_aggregate.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "source_context_id": source_context_id,
        "feature_key": feature_key,
        "trial_ids": list(trial_ids),
        "mean_gain_per_draw": _fraction_document(mean_gain_per_draw),
        "normalized_midrank": _fraction_document(normalized_midrank),
        "context_ranking_degenerate": context_ranking_degenerate,
    }


def _consensus_payload(
    *,
    feature_key: str,
    source_context_ids: tuple[str, ...],
    aggregate_ids: tuple[str, ...],
    mean_gain_per_draw: Fraction,
    mean_midrank: Fraction,
    worst_midrank: Fraction,
    disagreement: Fraction,
    any_context_ranking_degenerate: bool,
    disposition: archive_v2.FeatureConsensusDispositionV2,
    multiplier: Fraction,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.nonrectangular_feature_consensus.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "feature_key": feature_key,
        "source_context_ids": list(source_context_ids),
        "aggregate_ids": list(aggregate_ids),
        "mean_gain_per_draw": _fraction_document(mean_gain_per_draw),
        "mean_midrank": _fraction_document(mean_midrank),
        "worst_midrank": _fraction_document(worst_midrank),
        "disagreement": _fraction_document(disagreement),
        "any_context_ranking_degenerate": (
            any_context_ranking_degenerate
        ),
        "disagreement_threshold": _fraction_document(
            archive_v2.MAX_MIDRANK_DISAGREEMENT
        ),
        "disposition": disposition.value,
        "multiplier": _fraction_document(multiplier),
        "missing_feature_behavior": "NEUTRAL_MULTIPLIER",
    }


def _derive_and_assert_consensus(
    expected_trials: tuple[_ExpectedTrial, ...],
    claimed_aggregates: tuple[
        archive_v2.SourceContextFeatureAggregateV2,
        ...,
    ],
    claimed_consensus: tuple[
        archive_v2.NonrectangularFeatureConsensusV2,
        ...,
    ],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    grouped: dict[tuple[str, str], list[_ExpectedTrial]] = {}
    for trial in expected_trials:
        grouped.setdefault(
            (trial.source_context_id, trial.feature_key),
            [],
        ).append(trial)
    mean_by_key = {
        key: sum(
            (trial.gain_per_draw for trial in values),
            Fraction(0),
        )
        / len(values)
        for key, values in grouped.items()
    }
    by_context: dict[str, list[tuple[str, Fraction]]] = {}
    for (context_id, feature_key), mean in mean_by_key.items():
        by_context.setdefault(context_id, []).append((feature_key, mean))
    degenerate_by_context = {
        context_id: (
            len(entries) < 2
            or len({mean for _, mean in entries}) < 2
        )
        for context_id, entries in by_context.items()
    }
    rank_by_key: dict[tuple[str, str], Fraction] = {}
    for context_id, entries in by_context.items():
        ordered = sorted(entries, key=lambda item: (item[1], item[0]))
        scale = len(ordered) - 1
        cursor = 0
        while cursor < len(ordered):
            end = cursor + 1
            while (
                end < len(ordered)
                and ordered[end][1] == ordered[cursor][1]
            ):
                end += 1
            rank = (
                Fraction(1, 2)
                if scale == 0
                else Fraction(cursor + end - 1, 2 * scale)
            )
            for feature_key, _ in ordered[cursor:end]:
                rank_by_key[(context_id, feature_key)] = rank
            cursor = end

    expected_aggregates: list[
        tuple[str, dict[str, Any], tuple[str, str]]
    ] = []
    for key in sorted(grouped):
        context_id, feature_key = key
        trial_ids = tuple(
            sorted(trial.trial_id for trial in grouped[key])
        )
        payload = _aggregate_payload(
            source_context_id=context_id,
            feature_key=feature_key,
            trial_ids=trial_ids,
            mean_gain_per_draw=mean_by_key[key],
            normalized_midrank=rank_by_key[key],
            context_ranking_degenerate=degenerate_by_context[context_id],
        )
        aggregate_id = _archive_content_id(
            "context-feature-aggregate",
            payload,
        )
        expected_aggregates.append((aggregate_id, payload, key))
    expected_aggregates.sort(key=lambda item: item[0])
    claimed_aggregate_by_id: dict[
        str,
        archive_v2.SourceContextFeatureAggregateV2,
    ] = {}
    for item in claimed_aggregates:
        if type(item) is not archive_v2.SourceContextFeatureAggregateV2:
            _fail("archive aggregate has a noncanonical type")
        payload = _aggregate_payload(
            source_context_id=item.source_context_id,
            feature_key=item.feature_key,
            trial_ids=item.trial_ids,
            mean_gain_per_draw=item.mean_gain_per_draw,
            normalized_midrank=item.normalized_midrank,
            context_ranking_degenerate=item.context_ranking_degenerate,
        )
        item_id = _archive_content_id(
            "context-feature-aggregate",
            payload,
        )
        if item_id in claimed_aggregate_by_id:
            _fail("archive repeats a context-feature aggregate")
        claimed_aggregate_by_id[item_id] = item
    if set(claimed_aggregate_by_id) != {
        item[0] for item in expected_aggregates
    }:
        _fail("context ranks/midranks differ from independent derivation")
    for aggregate_id, payload, _ in expected_aggregates:
        item = claimed_aggregate_by_id[aggregate_id]
        expected_values = {
            "source_context_id": payload["source_context_id"],
            "feature_key": payload["feature_key"],
            "trial_ids": tuple(payload["trial_ids"]),
            "mean_gain_per_draw": mean_by_key[
                (payload["source_context_id"], payload["feature_key"])
            ],
            "normalized_midrank": rank_by_key[
                (payload["source_context_id"], payload["feature_key"])
            ],
            "context_ranking_degenerate": degenerate_by_context[
                payload["source_context_id"]
            ],
        }
        if any(
            getattr(item, field) != value
            for field, value in expected_values.items()
        ):
            _fail("context aggregate is a coherently re-signed forgery")

    aggregate_by_feature: dict[
        str,
        list[tuple[str, dict[str, Any], tuple[str, str]]],
    ] = {}
    for item in expected_aggregates:
        aggregate_by_feature.setdefault(item[2][1], []).append(item)
    expected_consensus: list[tuple[str, dict[str, Any]]] = []
    for feature_key, values in aggregate_by_feature.items():
        ordered = sorted(
            values,
            key=lambda item: item[2][0],
        )
        context_ids = tuple(item[2][0] for item in ordered)
        aggregate_ids = tuple(sorted(item[0] for item in ordered))
        means = [
            mean_by_key[(item[2][0], feature_key)]
            for item in ordered
        ]
        ranks = [
            rank_by_key[(item[2][0], feature_key)]
            for item in ordered
        ]
        mean_gain = sum(means, Fraction(0)) / len(means)
        mean_rank = sum(ranks, Fraction(0)) / len(ranks)
        worst_rank = min(ranks)
        disagreement = mean_rank - worst_rank
        any_degenerate = any(
            degenerate_by_context[context_id]
            for context_id in context_ids
        )
        if len(context_ids) < archive_v2.MIN_SOURCE_CONTEXTS_PER_FEATURE:
            disposition = (
                archive_v2.FeatureConsensusDispositionV2
                .INSUFFICIENT_CONTEXTS
            )
        elif any_degenerate:
            disposition = (
                archive_v2.FeatureConsensusDispositionV2
                .DEGENERATE_CONTEXT_RANKING
            )
        elif mean_gain <= 0:
            disposition = (
                archive_v2.FeatureConsensusDispositionV2
                .NONPOSITIVE_SOURCE_GAIN
            )
        elif disagreement > archive_v2.MAX_MIDRANK_DISAGREEMENT:
            disposition = (
                archive_v2.FeatureConsensusDispositionV2.HIGH_DISAGREEMENT
            )
        else:
            disposition = archive_v2.FeatureConsensusDispositionV2.APPLIED
        multiplier = (
            archive_v2.MIN_PRIOR_MULTIPLIER
            + (
                archive_v2.MAX_PRIOR_MULTIPLIER
                - archive_v2.MIN_PRIOR_MULTIPLIER
            )
            * mean_rank
            if disposition
            is archive_v2.FeatureConsensusDispositionV2.APPLIED
            else archive_v2.NEUTRAL_PRIOR_MULTIPLIER
        )
        payload = _consensus_payload(
            feature_key=feature_key,
            source_context_ids=context_ids,
            aggregate_ids=aggregate_ids,
            mean_gain_per_draw=mean_gain,
            mean_midrank=mean_rank,
            worst_midrank=worst_rank,
            disagreement=disagreement,
            any_context_ranking_degenerate=any_degenerate,
            disposition=disposition,
            multiplier=multiplier,
        )
        expected_consensus.append(
            (
                _archive_content_id("feature-consensus", payload),
                payload,
            )
        )
    expected_consensus.sort(key=lambda item: item[0])
    claimed_consensus_by_id: dict[
        str,
        archive_v2.NonrectangularFeatureConsensusV2,
    ] = {}
    for item in claimed_consensus:
        if type(item) is not archive_v2.NonrectangularFeatureConsensusV2:
            _fail("archive consensus has a noncanonical type")
        payload = _consensus_payload(
            feature_key=item.feature_key,
            source_context_ids=item.source_context_ids,
            aggregate_ids=item.aggregate_ids,
            mean_gain_per_draw=item.mean_gain_per_draw,
            mean_midrank=item.mean_midrank,
            worst_midrank=item.worst_midrank,
            disagreement=item.disagreement,
            any_context_ranking_degenerate=(
                item.any_context_ranking_degenerate
            ),
            disposition=item.disposition,
            multiplier=item.multiplier,
        )
        item_id = _archive_content_id("feature-consensus", payload)
        if item_id in claimed_consensus_by_id:
            _fail("archive repeats a feature consensus")
        claimed_consensus_by_id[item_id] = item
    if set(claimed_consensus_by_id) != {
        item[0] for item in expected_consensus
    }:
        _fail("nonrectangular consensus differs from independent derivation")
    return (
        tuple(item[0] for item in expected_aggregates),
        tuple(item[0] for item in expected_consensus),
        tuple(
            {**item[1], "aggregate_id": item[0]}
            for item in expected_aggregates
        ),
        tuple(
            {**item[1], "consensus_id": item[0]}
            for item in expected_consensus
        ),
    )


def _source_family_payload(
    campaign_id: str,
    context_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v0068_source_family.v2",
        "campaign_id": campaign_id,
        "registered_context_ids": list(context_ids),
    }


def _source_training_split_payload(
    source_family_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v0068_source_training_split.v2",
        "source_family_id": source_family_id,
        "context_checkpoint_pairs": [
            {
                "context_key": context_key,
                "pairs": [list(pair) for pair in pairs],
            }
            for context_key, pairs in (
                archive_v2.REGISTERED_ADJACENT_PAIRS.items()
            )
        ],
    }


def _archive_payload(
    *,
    source_campaign_id: str,
    source_campaign_verification_id: str,
    source_family_id: str,
    source_training_split_id: str,
    pair_ids: tuple[str, ...],
    trial_ids: tuple[str, ...],
    aggregate_ids: tuple[str, ...],
    consensus_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.verified_source_acquisition_archive.v2",
        "schema_version": archive_v2.SCHEMA_VERSION,
        "proposed_contract_version": (
            archive_v2.PROPOSED_CONTRACT_VERSION
        ),
        "profile_key": archive_v2.PROFILE_KEY,
        "source_campaign_id": source_campaign_id,
        "source_campaign_verification_id": (
            source_campaign_verification_id
        ),
        "source_family_id": source_family_id,
        "source_training_split_id": source_training_split_id,
        "feature_schema_id": archive_v2.FEATURE_SCHEMA_ID,
        "adjacent_pair_ids": list(pair_ids),
        "trial_ids": list(trial_ids),
        "context_feature_aggregate_ids": list(aggregate_ids),
        "consensus_ids": list(consensus_ids),
        "source_campaign_same_implementation_verified": True,
        "independent_fraction_recurrence_verified": True,
        "independent_source_campaign_verifier_claimed": False,
        "source_frozen": True,
        "proposal_only": True,
        "may_certify": False,
        "caller_supplied_gain_or_score": False,
        "raw_prefix_extensions_semantically_replayed": True,
        "nonrectangular_consensus": True,
        "observed_support_count_in_portable_feature": False,
        "promoted_mixed_epoch_source_excluded": True,
        "target_identity_fields_absent": True,
        "missing_or_abstained_multiplier": _fraction_document(
            archive_v2.NEUTRAL_PRIOR_MULTIPLIER
        ),
    }


def _consume_source_campaign_verification(
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        campaign_v1.ObservationSupportCampaignVerificationV1
    ),
) -> tuple[str, str, set[str], set[str]]:
    if (
        type(source_campaign)
        is not campaign_v1.ObservationSupportCampaignV1
        or type(source_verification)
        is not campaign_v1.ObservationSupportCampaignVerificationV1
    ):
        _fail("independent archive verifier requires concrete V0-068 inputs")
    campaign_id = source_campaign.campaign_id
    verification_id = source_verification.verification_id
    _cid(campaign_id, "source campaign")
    _cid(verification_id, "source campaign verification")
    replayed_rows = set(
        _sorted_distinct_ids(
            source_verification.replayed_row_ids,
            "source replayed rows",
        )
    )
    verification_ids = _id_tuple(
        source_verification.replayed_row_verification_ids,
        "source row replay verifications",
    )
    if (
        len(replayed_rows) != len(verification_ids)
        or source_verification.campaign_id != campaign_id
        or source_verification.replayed_campaign_id != campaign_id
        or source_verification.valid is not True
        or source_verification.same_implementation_full_replay is not True
        or source_verification.independent_implementation_claimed
        is not False
        or source_verification.exact_iid_implementation_claimed
        is not False
        or source_verification.formal_exact_iid_plan_certificate
        is not False
        or source_verification.role_manifest.campaign_id != campaign_id
    ):
        _fail("consumed V0-068 verification is stale or overstated")
    _cid(
        source_verification.family_verification_id,
        "source family verification",
    )
    role_rows = {
        binding.artifact_id
        for binding in source_verification.role_manifest.bindings
        if binding.artifact_role == "RAW_PARTIAL_SUPPORT_ROW_REPLAY"
    }
    for row_id in role_rows:
        _cid(row_id, "source replay role row")
    if role_rows != replayed_rows:
        _fail("V0-068 replay roles do not cover exactly the replayed rows")
    return campaign_id, verification_id, replayed_rows, role_rows


@dataclass(frozen=True, slots=True)
class IndependentSourceAcquisitionArchiveVerificationV2:
    archive_id: str
    independently_recomputed_archive_id: str
    archive_document_digest: str
    source_campaign_id: str
    source_campaign_verification_id: str
    registered_adjacent_pair_count: int
    trial_count: int
    feature_count: int
    independent_archive_transform_verified: bool = True
    source_campaign_same_implementation_verification_consumed: bool = True
    independent_source_campaign_verifier_claimed: bool = False
    source_campaign_verification_boundary: str = (
        SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY
    )
    valid: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.archive_id, "independently verified archive"),
            (
                self.independently_recomputed_archive_id,
                "independently recomputed archive",
            ),
            (self.archive_document_digest, "archive document digest"),
            (self.source_campaign_id, "independent source campaign"),
            (
                self.source_campaign_verification_id,
                "consumed source campaign verification",
            ),
        ):
            _cid(value, field)
        if (
            self.archive_id != self.independently_recomputed_archive_id
            or self.registered_adjacent_pair_count != 7
            or type(self.trial_count) is not int
            or self.trial_count <= 0
            or type(self.feature_count) is not int
            or self.feature_count <= 0
            or self.independent_archive_transform_verified is not True
            or (
                self.source_campaign_same_implementation_verification_consumed
                is not True
            )
            or self.independent_source_campaign_verifier_claimed is not False
            or self.source_campaign_verification_boundary
            != SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY
            or self.valid is not True
        ):
            _fail("independent archive verification overstates its boundary")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.independent_source_acquisition_archive_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "archive_id": self.archive_id,
            "independently_recomputed_archive_id": (
                self.independently_recomputed_archive_id
            ),
            "archive_document_digest": self.archive_document_digest,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "registered_adjacent_pair_count": (
                self.registered_adjacent_pair_count
            ),
            "trial_count": self.trial_count,
            "feature_count": self.feature_count,
            "independent_archive_transform_verified": True,
            (
                "source_campaign_same_implementation_verification_consumed"
            ): True,
            "independent_source_campaign_verifier_claimed": False,
            "source_campaign_verification_boundary": (
                SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY
            ),
            "production_archive_builder_or_verifier_called": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return _verification_content_id(
            "verification",
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_source_acquisition_archive_independently_v2(
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        campaign_v1.ObservationSupportCampaignVerificationV1
    ),
    claimed: archive_v2.VerifiedSourceAcquisitionArchiveV2,
) -> IndependentSourceAcquisitionArchiveVerificationV2:
    """Independently replay the V0-068 -> V0-072 archive transform."""

    if type(claimed) is not archive_v2.VerifiedSourceAcquisitionArchiveV2:
        _fail("claimed source archive is not the concrete V2 artifact")
    (
        source_campaign_id,
        source_verification_id,
        replayed_row_ids,
        replayed_role_row_ids,
    ) = _consume_source_campaign_verification(
        source_campaign,
        source_verification,
    )
    if (
        claimed.source_campaign_id != source_campaign_id
        or claimed.source_campaign_verification_id
        != source_verification_id
        or claimed.source_campaign_same_implementation_verified is not True
        or claimed.independent_fraction_recurrence_verified is not True
        or claimed.independent_source_campaign_verifier_claimed is not False
        or claimed.source_frozen is not True
        or claimed.proposal_only is not True
        or claimed.may_certify is not False
    ):
        _fail("claimed archive source boundary is stale or overstated")
    if (
        type(claimed.adjacent_pairs) is not tuple
        or type(claimed.trials) is not tuple
        or type(claimed.context_feature_aggregates) is not tuple
        or type(claimed.consensus) is not tuple
    ):
        _fail("claimed archive registries are not immutable tuples")

    result_by_key: dict[str, campaign_v1.ContextCampaignResultV1] = {}
    if type(source_campaign.context_results) is not tuple:
        _fail("source campaign context results are not immutable")
    for result in source_campaign.context_results:
        if type(result) is not campaign_v1.ContextCampaignResultV1:
            _fail("source campaign contains a noncanonical context result")
        key = result.context.context_key
        if key in result_by_key:
            _fail("source campaign duplicates one registered context")
        result_by_key[key] = result
    if tuple(result_by_key) != campaign_v1.REGISTERED_CONTEXT_ORDER:
        _fail("source campaign context chronology changed")

    claimed_pair_by_semantics: dict[
        tuple[str, int, int],
        archive_v2.VerifiedAdjacentCheckpointPairV2,
    ] = {}
    for pair in claimed.adjacent_pairs:
        if type(pair) is not archive_v2.VerifiedAdjacentCheckpointPairV2:
            _fail("claimed archive contains a noncanonical pair")
        key = (
            pair.source_context_key,
            pair.before_checkpoint,
            pair.after_checkpoint,
        )
        if key in claimed_pair_by_semantics:
            _fail("claimed archive duplicates one registered pair")
        claimed_pair_by_semantics[key] = pair
    expected_pair_keys = {
        (context_key, before, after)
        for context_key, pairs in (
            archive_v2.REGISTERED_ADJACENT_PAIRS.items()
        )
        for before, after in pairs
    }
    if set(claimed_pair_by_semantics) != expected_pair_keys:
        _fail("claimed archive has a missing or extra checkpoint pair")

    claimed_trial_by_semantics: dict[
        tuple[str, int, int, str],
        archive_v2.VerifiedSourceLocalTrialV2,
    ] = {}
    for trial in claimed.trials:
        if type(trial) is not archive_v2.VerifiedSourceLocalTrialV2:
            _fail("claimed archive contains a noncanonical trial")
        snapshot = trial.local_snapshot
        key = (
            trial.source_context_id,
            snapshot.before_checkpoint,
            snapshot.after_checkpoint,
            snapshot.before_row_id,
        )
        if key in claimed_trial_by_semantics:
            _fail("claimed archive duplicates one semantic source trial")
        claimed_trial_by_semantics[key] = trial

    derived_trials: list[_ExpectedTrial] = []
    derived_trial_documents: dict[str, dict[str, Any]] = {}
    derived_pair_records: list[
        tuple[str, dict[str, Any], archive_v2.VerifiedAdjacentCheckpointPairV2]
    ] = []
    seen_trial_semantics: set[tuple[str, int, int, str]] = set()
    for context_key in campaign_v1.REGISTERED_CONTEXT_ORDER:
        result = result_by_key[context_key]
        source_context_id = result.context.context_id
        _cid(source_context_id, "source context")
        if (
            type(result.executions) is not tuple
            or any(
                type(item) is not campaign_v1.CheckpointExecutionV1
                for item in result.executions
            )
        ):
            _fail("source checkpoint executions are not canonical")
        execution_by_checkpoint = {
            execution.checkpoint: execution
            for execution in result.executions
        }
        if len(execution_by_checkpoint) != len(result.executions):
            _fail("source result duplicates one checkpoint execution")
        for before_checkpoint, after_checkpoint in (
            archive_v2.REGISTERED_ADJACENT_PAIRS[context_key]
        ):
            before = execution_by_checkpoint.get(before_checkpoint)
            after = execution_by_checkpoint.get(after_checkpoint)
            if before is None or after is None:
                _fail("source campaign omits a registered checkpoint")
            if (
                before.quotient_considered is not True
                or after.quotient_considered is not True
                or type(before.quotient_base_audit)
                is not robust.RobustPlanAuditV1
                or type(after.quotient_base_audit)
                is not robust.RobustPlanAuditV1
                or before.quotient_base_audit.certified
                or before.quotient_base_audit.failed_frontier is None
                or not before.quotient_base_audit.failed_frontier
                .other_positive_row_ids
                or before.threshold != after.threshold
            ):
                _fail(
                    "registered pair lacks its failed-to-next quotient chronology"
                )
            before_model = before.bridge.quotient_model
            after_model = after.bridge.quotient_model
            before_audit = before.quotient_base_audit
            after_audit = after.quotient_base_audit
            threshold = before.threshold
            if (
                type(before_model)
                is not robust.PartialSupportIntervalModelV1
                or type(after_model)
                is not robust.PartialSupportIntervalModelV1
                or before_model.context_id != source_context_id
                or after_model.context_id != source_context_id
                or threshold.context_id != source_context_id
            ):
                _fail("registered pair has a stale context/model binding")
            _assert_structural_continuity(before_model, after_model)
            before_metrics = _assert_audit_arithmetic(
                before_model,
                before_audit,
                threshold,
            )
            _assert_audit_arithmetic(
                after_model,
                after_audit,
                threshold,
            )
            before_execution_id = before.execution_id
            after_execution_id = after.execution_id
            before_row_by_id = {
                row.row_id: row for row in before_model.rows
            }
            after_row_by_key = {
                row.row_key: row for row in after_model.rows
            }
            pair_trial_ids: list[str] = []
            for before_row_id in (
                before_audit.failed_frontier.other_positive_row_ids
            ):
                before_row = before_row_by_id.get(before_row_id)
                if before_row is None:
                    _fail("failed frontier references an absent planner row")
                after_row = after_row_by_key.get(before_row.row_key)
                if after_row is None:
                    _fail("next checkpoint omits the frontier row key")
                before_physical = _physical_row(before, before_row)
                after_physical = _physical_row(after, after_row)
                prefix_fields = _raw_prefix_expected(
                    before_physical,
                    after_physical,
                    before_checkpoint=before_checkpoint,
                    after_checkpoint=after_checkpoint,
                    replayed_row_ids=replayed_row_ids,
                    replayed_role_row_ids=replayed_role_row_ids,
                )
                trial_key = (
                    source_context_id,
                    before_checkpoint,
                    after_checkpoint,
                    before_row.row_id,
                )
                claimed_trial = claimed_trial_by_semantics.get(trial_key)
                if claimed_trial is None:
                    _fail("archive omits one source failed-frontier trial")
                seen_trial_semantics.add(trial_key)
                roll_forward_metrics = _independent_fixed_policy_metrics(
                    model=before_model,
                    audit=before_audit,
                    threshold=threshold,
                    replacement=after_row,
                )
                expected_trial, trial_document = _assert_trial(
                    claimed_trial,
                    source_context_id=source_context_id,
                    before_execution_id=before_execution_id,
                    after_execution_id=after_execution_id,
                    before_model=before_model,
                    after_model=after_model,
                    before_audit=before_audit,
                    after_audit=after_audit,
                    threshold=threshold,
                    before_checkpoint=before_checkpoint,
                    after_checkpoint=after_checkpoint,
                    before_row=before_row,
                    after_row=after_row,
                    expected_prefix_fields=prefix_fields,
                    before_metrics=before_metrics,
                    roll_forward_metrics=roll_forward_metrics,
                )
                derived_trials.append(expected_trial)
                derived_trial_documents[expected_trial.trial_id] = (
                    trial_document
                )
                pair_trial_ids.append(expected_trial.trial_id)
            pair_trial_id_tuple = tuple(sorted(pair_trial_ids))
            pair_key = (
                context_key,
                before_checkpoint,
                after_checkpoint,
            )
            claimed_pair = claimed_pair_by_semantics[pair_key]
            pair_id, pair_payload = _assert_pair(
                claimed_pair,
                source_context_id=source_context_id,
                source_context_key=context_key,
                before_checkpoint=before_checkpoint,
                after_checkpoint=after_checkpoint,
                before_execution_id=before_execution_id,
                after_execution_id=after_execution_id,
                before_model_id=before_model.model_id,
                after_model_id=after_model.model_id,
                before_audit_id=before_audit.audit_id,
                after_audit_id=after_audit.audit_id,
                trial_ids=pair_trial_id_tuple,
            )
            derived_pair_records.append(
                (pair_id, pair_payload, claimed_pair)
            )
    if set(claimed_trial_by_semantics) != seen_trial_semantics:
        _fail("archive has an extra source trial outside registered frontiers")

    derived_trials_tuple = tuple(
        sorted(derived_trials, key=lambda item: item.trial_id)
    )
    derived_trial_ids = tuple(
        item.trial_id for item in derived_trials_tuple
    )
    trial_id_by_semantics = {
        (
            item.source_context_id,
            item.claimed.local_snapshot.before_checkpoint,
            item.claimed.local_snapshot.after_checkpoint,
            item.claimed.local_snapshot.before_row_id,
        ): item.trial_id
        for item in derived_trials_tuple
    }
    claimed_trial_order = tuple(
        trial_id_by_semantics.get(
            (
                item.source_context_id,
                item.local_snapshot.before_checkpoint,
                item.local_snapshot.after_checkpoint,
                item.local_snapshot.before_row_id,
            ),
            "",
        )
        for item in claimed.trials
    )
    if claimed_trial_order != derived_trial_ids:
        _fail("archive trial registry is not independent-content-ID sorted")

    derived_pair_records.sort(key=lambda item: item[0])
    pair_ids = tuple(item[0] for item in derived_pair_records)
    claimed_pair_order = tuple(
        _archive_content_id(
            "checkpoint-pair",
            _pair_payload(
                source_context_id=item.source_context_id,
                source_context_key=item.source_context_key,
                before_checkpoint=item.before_checkpoint,
                after_checkpoint=item.after_checkpoint,
                before_execution_id=item.before_execution_id,
                after_execution_id=item.after_execution_id,
                before_model_id=item.before_model_id,
                after_model_id=item.after_model_id,
                before_audit_id=item.before_audit_id,
                after_audit_id=item.after_audit_id,
                trial_ids=item.trial_ids,
            ),
        )
        for item in claimed.adjacent_pairs
    )
    if claimed_pair_order != pair_ids:
        _fail("archive pair registry is not independent-content-ID sorted")

    (
        aggregate_ids,
        consensus_ids,
        aggregate_documents,
        consensus_documents,
    ) = _derive_and_assert_consensus(
        derived_trials_tuple,
        claimed.context_feature_aggregates,
        claimed.consensus,
    )
    claimed_aggregate_order = tuple(
        _archive_content_id(
            "context-feature-aggregate",
            _aggregate_payload(
                source_context_id=item.source_context_id,
                feature_key=item.feature_key,
                trial_ids=item.trial_ids,
                mean_gain_per_draw=item.mean_gain_per_draw,
                normalized_midrank=item.normalized_midrank,
                context_ranking_degenerate=(
                    item.context_ranking_degenerate
                ),
            ),
        )
        for item in claimed.context_feature_aggregates
    )
    claimed_consensus_order = tuple(
        _archive_content_id(
            "feature-consensus",
            _consensus_payload(
                feature_key=item.feature_key,
                source_context_ids=item.source_context_ids,
                aggregate_ids=item.aggregate_ids,
                mean_gain_per_draw=item.mean_gain_per_draw,
                mean_midrank=item.mean_midrank,
                worst_midrank=item.worst_midrank,
                disagreement=item.disagreement,
                any_context_ranking_degenerate=(
                    item.any_context_ranking_degenerate
                ),
                disposition=item.disposition,
                multiplier=item.multiplier,
            ),
        )
        for item in claimed.consensus
    )
    if (
        claimed_aggregate_order != aggregate_ids
        or claimed_consensus_order != consensus_ids
    ):
        _fail("archive consensus registries are not content-ID sorted")

    context_ids = tuple(
        result_by_key[key].context.context_id
        for key in campaign_v1.REGISTERED_CONTEXT_ORDER
    )
    family_payload = _source_family_payload(
        source_campaign_id,
        context_ids,
    )
    source_family_id = _archive_content_id(
        "source-family",
        family_payload,
    )
    split_payload = _source_training_split_payload(source_family_id)
    source_training_split_id = _archive_content_id(
        "source-training-split",
        split_payload,
    )
    if (
        claimed.source_family_id != source_family_id
        or claimed.source_training_split_id != source_training_split_id
    ):
        _fail("source family/training split identity was coherently re-signed")
    payload = _archive_payload(
        source_campaign_id=source_campaign_id,
        source_campaign_verification_id=source_verification_id,
        source_family_id=source_family_id,
        source_training_split_id=source_training_split_id,
        pair_ids=pair_ids,
        trial_ids=derived_trial_ids,
        aggregate_ids=aggregate_ids,
        consensus_ids=consensus_ids,
    )
    archive_id = _archive_content_id("archive", payload)
    pair_documents = tuple(
        {**item[1], "pair_id": item[0]}
        for item in derived_pair_records
    )
    trial_documents = tuple(
        derived_trial_documents[trial_id]
        for trial_id in derived_trial_ids
    )
    archive_document = {
        **payload,
        "adjacent_pairs": list(pair_documents),
        "trials": list(trial_documents),
        "context_feature_aggregates": list(aggregate_documents),
        "consensus": list(consensus_documents),
        "archive_id": archive_id,
    }
    archive_document_digest = hashlib.sha256(
        b"acfqp:v072-independent-archive-document:v2\x00"
        + canonical_json_bytes(archive_document)
    ).hexdigest()
    return IndependentSourceAcquisitionArchiveVerificationV2(
        archive_id,
        archive_id,
        archive_document_digest,
        source_campaign_id,
        source_verification_id,
        len(pair_ids),
        len(derived_trial_ids),
        len(consensus_ids),
    )


__all__ = [
    "IndependentSourceAcquisitionArchiveVerificationV2",
    "IndependentSourceArchiveVerificationViolation",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY",
    "verify_source_acquisition_archive_independently_v2",
]
