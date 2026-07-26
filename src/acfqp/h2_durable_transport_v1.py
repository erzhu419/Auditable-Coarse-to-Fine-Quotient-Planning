"""Strict JSON transport reconstruction for the registered H=2 artifacts.

This module deliberately implements a narrow transport boundary.  It accepts
only the exact canonical ``to_document()`` representation of:

* :class:`QueryScopedPartialRAPMV3`;
* :class:`FrozenPartialAuditThresholdsV1`; and
* :class:`FrozenContingentAbstractPlanV1`.

Every record has a closed field set, every array must be a JSON-style list,
every primitive has its exact Python JSON type, and every rational document
must already be reduced with a positive denominator.  Rational leaves already
decoded by :func:`phase3e_ids.loads_canonical_json` are also accepted as exact
``Fraction`` objects.  Reconstruction always uses the public typed
constructors and finishes by requiring exact structural equality after
normalizing decoded fractions back to their canonical document form.  This is
a transport parser, not a new source of semantic authority.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd
from typing import Any, Callable, TypeVar

from acfqp.observation_partial_rapm_v1 import (
    AmbiguityPayloadV1,
    AmbiguityRowStatus,
    ConcretizerRowV1,
    DestinationIntervalV1,
    ExactIntervalV1,
    JointOutcomeAtomV1,
    JointOutcomeKind,
    JointSimplexConstraintV1,
    NamedIntervalV1,
    ObservationCoverageV1,
    PartialCellV1,
    PartialGroundRowV1,
    PartialSemanticActionV1,
    PartialSemanticRealizationV1,
    PlanningKind,
    QueryScopedPartialRAPMV3,
    RewardFeatureCapV1,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanAssignmentV1,
    ContingentPlanStageV1,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    RegisteredReturnBoundProofV1,
    RewardWeightV1,
)
from acfqp.phase3e_ids import parse_content_id


class H2DurableTransportRoundTripViolation(ValueError):
    """A transported document is not an exact canonical typed artifact."""


# Descriptive aliases let callers name either the boundary or its invariant
# while retaining one catchable exception type.
DurableTransportRoundTripViolation = H2DurableTransportRoundTripViolation
H2DurableTransportInvariantViolation = H2DurableTransportRoundTripViolation
DurableH2TransportInvariantViolation = H2DurableTransportRoundTripViolation


_T = TypeVar("_T")


def _fail(where: str, message: str) -> H2DurableTransportRoundTripViolation:
    return H2DurableTransportRoundTripViolation(f"{where}: {message}")


def _record(
    value: Any,
    fields: tuple[str, ...],
    where: str,
) -> dict[str, Any]:
    if type(value) is not dict:
        raise _fail(where, "must be an exact JSON object")
    actual = set(value)
    expected = set(fields)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing fields {missing!r}")
        if unknown:
            details.append(f"unknown fields {unknown!r}")
        raise _fail(where, "; ".join(details))
    if any(type(key) is not str for key in value):
        raise _fail(where, "object keys must be exact strings")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise _fail(where, "must be an exact JSON array")
    return value


def _text(value: Any, where: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value):
        qualifier = "nonempty " if nonempty else ""
        raise _fail(where, f"must be exact {qualifier}text")
    return value


def _boolean(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise _fail(where, "must be an exact boolean")
    return value


def _integer(value: Any, where: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise _fail(where, "must be an exact integer")
    if minimum is not None and value < minimum:
        raise _fail(where, f"must be >= {minimum}")
    return value


def _content_id(value: Any, where: str) -> str:
    text = _text(value, where)
    try:
        parsed = parse_content_id(text)
    except ValueError as error:
        raise _fail(where, "must be a full canonical content ID") from error
    if parsed != text:
        raise _fail(where, "content ID changed during canonical parsing")
    return parsed


def _literal(value: Any, expected: str, where: str) -> str:
    text = _text(value, where)
    if text != expected:
        raise _fail(where, f"must equal {expected!r}")
    return text


def _fraction(value: Any, where: str) -> Fraction:
    if type(value) is Fraction:
        return value
    row = _record(value, ("numerator", "denominator"), where)
    numerator = _integer(row["numerator"], f"{where}.numerator")
    denominator = _integer(
        row["denominator"], f"{where}.denominator", minimum=1
    )
    if gcd(abs(numerator), denominator) != 1:
        raise _fail(where, "must be a reduced rational document")
    exact = Fraction(numerator, denominator)
    if {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    } != row:
        raise _fail(where, "must use the canonical positive-denominator form")
    return exact


def _normalize_transport_document(value: Any, where: str) -> Any:
    """Restore loader-decoded fractions to canonical ``to_document`` leaves."""

    if type(value) is Fraction:
        return {
            "numerator": value.numerator,
            "denominator": value.denominator,
        }
    if type(value) is list:
        return [
            _normalize_transport_document(item, f"{where}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise _fail(where, "object keys must be exact strings")
        return {
            key: _normalize_transport_document(item, f"{where}.{key}")
            for key, item in value.items()
        }
    if value is None or type(value) in (str, bool, int):
        return value
    raise _fail(
        where,
        "contains a value outside the canonical JSON/Fraction transport language",
    )


def _enum(
    value: Any,
    enum_type: type[_T],
    where: str,
) -> _T:
    text = _text(value, where)
    try:
        member = enum_type(text)
    except ValueError as error:
        raise _fail(where, f"is not a registered {enum_type.__name__}") from error
    if type(member) is not enum_type:
        raise _fail(where, f"did not construct exact {enum_type.__name__}")
    return member


def _items(
    value: Any,
    parser: Callable[[Any, str], _T],
    where: str,
) -> tuple[_T, ...]:
    return tuple(
        parser(item, f"{where}[{index}]")
        for index, item in enumerate(_array(value, where))
    )


def _require_round_trip(
    result: Any,
    source: dict[str, Any],
    where: str,
) -> None:
    try:
        replay = result.to_document()
    except Exception as error:  # pragma: no cover - typed constructors own this
        raise _fail(where, "constructed object could not be serialized") from error
    normalized_source = _normalize_transport_document(source, where)
    if type(replay) is not dict or replay != normalized_source:
        raise _fail(where, "typed reconstruction does not exactly reproduce input")


def _parse_exact_interval(value: Any, where: str) -> ExactIntervalV1:
    row = _record(value, ("lower", "upper"), where)
    result = ExactIntervalV1(
        _fraction(row["lower"], f"{where}.lower"),
        _fraction(row["upper"], f"{where}.upper"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_named_interval(value: Any, where: str) -> NamedIntervalV1:
    row = _record(value, ("name", "interval"), where)
    result = NamedIntervalV1(
        _text(row["name"], f"{where}.name"),
        _parse_exact_interval(row["interval"], f"{where}.interval"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_destination_interval(
    value: Any,
    where: str,
) -> DestinationIntervalV1:
    row = _record(value, ("destination_id", "interval"), where)
    result = DestinationIntervalV1(
        _content_id(row["destination_id"], f"{where}.destination_id"),
        _parse_exact_interval(row["interval"], f"{where}.interval"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_joint_outcome_atom(
    value: Any,
    where: str,
) -> JointOutcomeAtomV1:
    row = _record(
        value,
        (
            "schema",
            "kind",
            "destination_id",
            "terminal",
            "failure",
            "atom_id",
        ),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.partial_rapm_joint_outcome_atom.v1",
        f"{where}.schema",
    )
    kind = _enum(row["kind"], JointOutcomeKind, f"{where}.kind")
    destination = row["destination_id"]
    if destination is not None:
        destination = _content_id(destination, f"{where}.destination_id")
    _boolean(row["terminal"], f"{where}.terminal")
    _boolean(row["failure"], f"{where}.failure")
    _content_id(row["atom_id"], f"{where}.atom_id")
    result = JointOutcomeAtomV1(kind, destination)
    _require_round_trip(result, row, where)
    return result


def _parse_joint_simplex_constraint(
    value: Any,
    where: str,
) -> JointSimplexConstraintV1:
    row = _record(
        value,
        (
            "schema",
            "atom_ids",
            "known_continuation_mass",
            "known_terminal_mass",
            "unknown_atom_mass_sum",
            "total_probability_mass",
            "partition_semantics",
            "failure_implies_terminal",
            "independent_marginal_box_forbidden",
            "constraint_id",
        ),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.partial_rapm_joint_simplex_constraint.v1",
        f"{where}.schema",
    )
    atom_ids = tuple(
        _content_id(item, f"{where}.atom_ids[{index}]")
        for index, item in enumerate(_array(row["atom_ids"], f"{where}.atom_ids"))
    )
    _content_id(row["constraint_id"], f"{where}.constraint_id")
    result = JointSimplexConstraintV1(
        atom_ids=atom_ids,
        known_continuation_mass=_fraction(
            row["known_continuation_mass"],
            f"{where}.known_continuation_mass",
        ),
        known_terminal_mass=_fraction(
            row["known_terminal_mass"], f"{where}.known_terminal_mass"
        ),
        unknown_atom_mass_sum=_fraction(
            row["unknown_atom_mass_sum"], f"{where}.unknown_atom_mass_sum"
        ),
        total_probability_mass=_fraction(
            row["total_probability_mass"], f"{where}.total_probability_mass"
        ),
        partition_semantics=_text(
            row["partition_semantics"], f"{where}.partition_semantics"
        ),
        failure_implies_terminal=_boolean(
            row["failure_implies_terminal"], f"{where}.failure_implies_terminal"
        ),
        independent_marginal_box_forbidden=_boolean(
            row["independent_marginal_box_forbidden"],
            f"{where}.independent_marginal_box_forbidden",
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_named_fraction_rows(
    value: Any,
    where: str,
) -> tuple[tuple[str, Fraction], ...]:
    parsed: list[tuple[str, Fraction]] = []
    for index, item in enumerate(_array(value, where)):
        item_where = f"{where}[{index}]"
        row = _record(item, ("name", "value"), item_where)
        parsed.append(
            (
                _text(row["name"], f"{item_where}.name"),
                _fraction(row["value"], f"{item_where}.value"),
            )
        )
    return tuple(parsed)


def _parse_destination_mass_rows(
    value: Any,
    where: str,
) -> tuple[tuple[str, Fraction], ...]:
    parsed: list[tuple[str, Fraction]] = []
    for index, item in enumerate(_array(value, where)):
        item_where = f"{where}[{index}]"
        row = _record(item, ("destination_id", "mass"), item_where)
        parsed.append(
            (
                _content_id(
                    row["destination_id"], f"{item_where}.destination_id"
                ),
                _fraction(row["mass"], f"{item_where}.mass"),
            )
        )
    return tuple(parsed)


def _parse_ambiguity(value: Any, where: str) -> AmbiguityPayloadV1:
    row = _record(
        value,
        (
            "known_reward_features",
            "known_successor_masses",
            "known_failure_mass",
            "known_terminal_mass",
            "unknown_mass",
            "unknown_successor_destination_ids",
            "external_boundary_id",
            "reward_intervals",
            "successor_intervals",
            "failure_interval",
            "terminal_interval",
            "joint_outcome_atoms",
            "joint_simplex_constraint",
            "unknown_failure_allowed",
            "unknown_terminal_allowed",
        ),
        where,
    )
    unknown_destinations = tuple(
        _content_id(
            item,
            f"{where}.unknown_successor_destination_ids[{index}]",
        )
        for index, item in enumerate(
            _array(
                row["unknown_successor_destination_ids"],
                f"{where}.unknown_successor_destination_ids",
            )
        )
    )
    result = AmbiguityPayloadV1(
        known_reward_features=_parse_named_fraction_rows(
            row["known_reward_features"], f"{where}.known_reward_features"
        ),
        known_successor_masses=_parse_destination_mass_rows(
            row["known_successor_masses"], f"{where}.known_successor_masses"
        ),
        known_failure_mass=_fraction(
            row["known_failure_mass"], f"{where}.known_failure_mass"
        ),
        known_terminal_mass=_fraction(
            row["known_terminal_mass"], f"{where}.known_terminal_mass"
        ),
        unknown_mass=_fraction(row["unknown_mass"], f"{where}.unknown_mass"),
        unknown_successor_destination_ids=unknown_destinations,
        external_boundary_id=_content_id(
            row["external_boundary_id"], f"{where}.external_boundary_id"
        ),
        reward_intervals=_items(
            row["reward_intervals"],
            _parse_named_interval,
            f"{where}.reward_intervals",
        ),
        successor_intervals=_items(
            row["successor_intervals"],
            _parse_destination_interval,
            f"{where}.successor_intervals",
        ),
        failure_interval=_parse_exact_interval(
            row["failure_interval"], f"{where}.failure_interval"
        ),
        terminal_interval=_parse_exact_interval(
            row["terminal_interval"], f"{where}.terminal_interval"
        ),
        joint_outcome_atoms=_items(
            row["joint_outcome_atoms"],
            _parse_joint_outcome_atom,
            f"{where}.joint_outcome_atoms",
        ),
        joint_simplex_constraint=_parse_joint_simplex_constraint(
            row["joint_simplex_constraint"],
            f"{where}.joint_simplex_constraint",
        ),
        unknown_failure_allowed=_boolean(
            row["unknown_failure_allowed"], f"{where}.unknown_failure_allowed"
        ),
        unknown_terminal_allowed=_boolean(
            row["unknown_terminal_allowed"], f"{where}.unknown_terminal_allowed"
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_coverage(value: Any, where: str) -> ObservationCoverageV1:
    row = _record(
        value,
        (
            "schema",
            "registered_state_ids",
            "registered_ground_row_ids",
            "observed_ground_row_ids",
            "missing_ground_row_ids",
            "external_boundary_id",
            "mode",
            "admissible_query_support_rule",
            "transition_closure_claimed",
            "outside_catalogue_requires_rebuild_or_fallback",
            "coverage_id",
        ),
        where,
    )
    _literal(row["schema"], "acfqp.observation_coverage.v1", f"{where}.schema")

    def ids(field: str) -> tuple[str, ...]:
        return tuple(
            _content_id(item, f"{where}.{field}[{index}]")
            for index, item in enumerate(
                _array(row[field], f"{where}.{field}")
            )
        )

    _content_id(row["coverage_id"], f"{where}.coverage_id")
    result = ObservationCoverageV1(
        registered_state_ids=ids("registered_state_ids"),
        registered_ground_row_ids=ids("registered_ground_row_ids"),
        observed_ground_row_ids=ids("observed_ground_row_ids"),
        missing_ground_row_ids=ids("missing_ground_row_ids"),
        external_boundary_id=_content_id(
            row["external_boundary_id"], f"{where}.external_boundary_id"
        ),
        mode=_text(row["mode"], f"{where}.mode"),
        admissible_query_support_rule=_text(
            row["admissible_query_support_rule"],
            f"{where}.admissible_query_support_rule",
        ),
        transition_closure_claimed=_boolean(
            row["transition_closure_claimed"],
            f"{where}.transition_closure_claimed",
        ),
        outside_catalogue_requires_rebuild_or_fallback=_boolean(
            row["outside_catalogue_requires_rebuild_or_fallback"],
            f"{where}.outside_catalogue_requires_rebuild_or_fallback",
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_cell(value: Any, where: str) -> PartialCellV1:
    row = _record(
        value,
        (
            "schema",
            "member_state_ids",
            "planning_kind",
            "coordinate_values",
            "cell_id",
        ),
        where,
    )
    _literal(row["schema"], "acfqp.partial_rapm_cell.v1", f"{where}.schema")
    member_ids = tuple(
        _content_id(item, f"{where}.member_state_ids[{index}]")
        for index, item in enumerate(
            _array(row["member_state_ids"], f"{where}.member_state_ids")
        )
    )
    coordinate_values = tuple(
        _integer(item, f"{where}.coordinate_values[{index}]")
        for index, item in enumerate(
            _array(row["coordinate_values"], f"{where}.coordinate_values")
        )
    )
    _content_id(row["cell_id"], f"{where}.cell_id")
    result = PartialCellV1(
        member_ids,
        _enum(row["planning_kind"], PlanningKind, f"{where}.planning_kind"),
        coordinate_values,
    )
    _require_round_trip(result, row, where)
    return result


def _parse_semantic_action(
    value: Any,
    where: str,
) -> PartialSemanticActionV1:
    row = _record(
        value,
        ("schema", "cell_id", "label_values", "semantic_action_id"),
        where,
    )
    _literal(
        row["schema"], "acfqp.partial_rapm_semantic_action.v1", f"{where}.schema"
    )
    labels = tuple(
        _boolean(item, f"{where}.label_values[{index}]")
        for index, item in enumerate(
            _array(row["label_values"], f"{where}.label_values")
        )
    )
    _content_id(row["semantic_action_id"], f"{where}.semantic_action_id")
    result = PartialSemanticActionV1(
        _content_id(row["cell_id"], f"{where}.cell_id"),
        labels,
    )
    _require_round_trip(result, row, where)
    return result


def _parse_concretizer_row(value: Any, where: str) -> ConcretizerRowV1:
    row = _record(
        value,
        ("state_id", "cell_id", "semantic_action_id", "support"),
        where,
    )
    support: list[tuple[str, Fraction]] = []
    for index, item in enumerate(_array(row["support"], f"{where}.support")):
        item_where = f"{where}.support[{index}]"
        support_row = _record(
            item, ("ground_action_id", "probability"), item_where
        )
        support.append(
            (
                _content_id(
                    support_row["ground_action_id"],
                    f"{item_where}.ground_action_id",
                ),
                _fraction(
                    support_row["probability"], f"{item_where}.probability"
                ),
            )
        )
    result = ConcretizerRowV1(
        _content_id(row["state_id"], f"{where}.state_id"),
        _content_id(row["cell_id"], f"{where}.cell_id"),
        _content_id(
            row["semantic_action_id"], f"{where}.semantic_action_id"
        ),
        tuple(support),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_ground_row(value: Any, where: str) -> PartialGroundRowV1:
    row = _record(
        value,
        (
            "ground_row_id",
            "state_id",
            "ground_action_id",
            "status",
            "observation_ids",
            "ambiguity",
        ),
        where,
    )
    observation_ids = tuple(
        _content_id(item, f"{where}.observation_ids[{index}]")
        for index, item in enumerate(
            _array(row["observation_ids"], f"{where}.observation_ids")
        )
    )
    result = PartialGroundRowV1(
        _content_id(row["ground_row_id"], f"{where}.ground_row_id"),
        _content_id(row["state_id"], f"{where}.state_id"),
        _content_id(row["ground_action_id"], f"{where}.ground_action_id"),
        _enum(row["status"], AmbiguityRowStatus, f"{where}.status"),
        observation_ids,
        _parse_ambiguity(row["ambiguity"], f"{where}.ambiguity"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_semantic_realization(
    value: Any,
    where: str,
) -> PartialSemanticRealizationV1:
    row = _record(
        value,
        (
            "state_id",
            "cell_id",
            "semantic_action_id",
            "support_ground_row_ids",
            "observed_ground_row_ids",
            "missing_ground_row_ids",
            "ambiguity",
        ),
        where,
    )

    def ids(field: str) -> tuple[str, ...]:
        return tuple(
            _content_id(item, f"{where}.{field}[{index}]")
            for index, item in enumerate(
                _array(row[field], f"{where}.{field}")
            )
        )

    result = PartialSemanticRealizationV1(
        _content_id(row["state_id"], f"{where}.state_id"),
        _content_id(row["cell_id"], f"{where}.cell_id"),
        _content_id(
            row["semantic_action_id"], f"{where}.semantic_action_id"
        ),
        ids("support_ground_row_ids"),
        ids("observed_ground_row_ids"),
        ids("missing_ground_row_ids"),
        _parse_ambiguity(row["ambiguity"], f"{where}.ambiguity"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_reward_feature_cap(
    value: Any,
    where: str,
) -> RewardFeatureCapV1:
    row = _record(value, ("name", "lower", "upper"), where)
    result = RewardFeatureCapV1(
        _text(row["name"], f"{where}.name"),
        _fraction(row["lower"], f"{where}.lower"),
        _fraction(row["upper"], f"{where}.upper"),
    )
    _require_round_trip(result, row, where)
    return result


_QUERY_SCOPED_PARTIAL_RAPM_V3_FIELDS = (
    "schema",
    "schema_version",
    "semantics_profile_id",
    "semantics_horizon_cap",
    "observation_log_id",
    "coordinate_proposal_id",
    "observation_authority_id",
    "acquisition_manifest_id",
    "acquisition_coverage_id",
    "evidence_ledger_id",
    "coverage",
    "external_boundary_id",
    "cells",
    "semantic_actions",
    "concretizer_rows",
    "ground_rows",
    "semantic_realizations",
    "reward_feature_caps",
    "base_model_id",
    "previous_model_id",
    "observed_synthesis_result_id",
    "source_thresholds_id",
    "source_plan_id",
    "source_failed_typed_audit_result_id",
    "evidence_request_id",
    "evidence_bundle_id",
    "boundary_expansion_id",
    "overlay_ledger_id",
    "overlay_version",
    "cumulative_exact_kernel_query_count",
    "registered_query_local_state_count",
    "evidence_kind",
    "query_neutral",
    "transition_closure_claimed",
    "exact_quotient_claimed",
    "plan_certificate_claimed",
    "infeasibility_claimed",
    "acquisition_query_neutral_attested",
    "preregistered_allowlisted_authority_required",
    "query_local_overlay_authority_required",
    "boundary_catalogue_authority_required",
    "base_model_mutated",
    "promotion_authorized",
    "model_id",
)


def _parse_query_scoped_partial_rapm_v3(
    document: Any,
) -> QueryScopedPartialRAPMV3:
    where = "QueryScopedPartialRAPMV3"
    row = _record(document, _QUERY_SCOPED_PARTIAL_RAPM_V3_FIELDS, where)
    _literal(
        row["schema"], "acfqp.query_scoped_partial_rapm.v3", f"{where}.schema"
    )
    _literal(row["schema_version"], "1.2.0", f"{where}.schema_version")
    for field in (
        "semantics_profile_id",
        "observation_log_id",
        "coordinate_proposal_id",
        "observation_authority_id",
        "acquisition_manifest_id",
        "acquisition_coverage_id",
        "evidence_ledger_id",
        "external_boundary_id",
        "base_model_id",
        "previous_model_id",
        "observed_synthesis_result_id",
        "source_thresholds_id",
        "source_plan_id",
        "source_failed_typed_audit_result_id",
        "evidence_request_id",
        "evidence_bundle_id",
        "boundary_expansion_id",
        "overlay_ledger_id",
        "model_id",
    ):
        _content_id(row[field], f"{where}.{field}")
    result = QueryScopedPartialRAPMV3(
        semantics_profile_id=row["semantics_profile_id"],
        semantics_horizon_cap=_integer(
            row["semantics_horizon_cap"],
            f"{where}.semantics_horizon_cap",
            minimum=1,
        ),
        observation_log_id=row["observation_log_id"],
        coordinate_proposal_id=row["coordinate_proposal_id"],
        observation_authority_id=row["observation_authority_id"],
        acquisition_manifest_id=row["acquisition_manifest_id"],
        acquisition_coverage_id=row["acquisition_coverage_id"],
        evidence_ledger_id=row["evidence_ledger_id"],
        coverage=_parse_coverage(row["coverage"], f"{where}.coverage"),
        external_boundary_id=row["external_boundary_id"],
        cells=_items(row["cells"], _parse_cell, f"{where}.cells"),
        semantic_actions=_items(
            row["semantic_actions"],
            _parse_semantic_action,
            f"{where}.semantic_actions",
        ),
        concretizer_rows=_items(
            row["concretizer_rows"],
            _parse_concretizer_row,
            f"{where}.concretizer_rows",
        ),
        ground_rows=_items(
            row["ground_rows"], _parse_ground_row, f"{where}.ground_rows"
        ),
        semantic_realizations=_items(
            row["semantic_realizations"],
            _parse_semantic_realization,
            f"{where}.semantic_realizations",
        ),
        reward_feature_caps=_items(
            row["reward_feature_caps"],
            _parse_reward_feature_cap,
            f"{where}.reward_feature_caps",
        ),
        base_model_id=row["base_model_id"],
        previous_model_id=row["previous_model_id"],
        observed_synthesis_result_id=row["observed_synthesis_result_id"],
        source_thresholds_id=row["source_thresholds_id"],
        source_plan_id=row["source_plan_id"],
        source_failed_typed_audit_result_id=(
            row["source_failed_typed_audit_result_id"]
        ),
        evidence_request_id=row["evidence_request_id"],
        evidence_bundle_id=row["evidence_bundle_id"],
        boundary_expansion_id=row["boundary_expansion_id"],
        overlay_ledger_id=row["overlay_ledger_id"],
        overlay_version=_integer(
            row["overlay_version"], f"{where}.overlay_version", minimum=1
        ),
        cumulative_exact_kernel_query_count=_integer(
            row["cumulative_exact_kernel_query_count"],
            f"{where}.cumulative_exact_kernel_query_count",
            minimum=1,
        ),
        registered_query_local_state_count=_integer(
            row["registered_query_local_state_count"],
            f"{where}.registered_query_local_state_count",
            minimum=1,
        ),
        evidence_kind=_text(row["evidence_kind"], f"{where}.evidence_kind"),
        query_neutral=_boolean(
            row["query_neutral"], f"{where}.query_neutral"
        ),
        transition_closure_claimed=_boolean(
            row["transition_closure_claimed"],
            f"{where}.transition_closure_claimed",
        ),
        exact_quotient_claimed=_boolean(
            row["exact_quotient_claimed"], f"{where}.exact_quotient_claimed"
        ),
        plan_certificate_claimed=_boolean(
            row["plan_certificate_claimed"],
            f"{where}.plan_certificate_claimed",
        ),
        infeasibility_claimed=_boolean(
            row["infeasibility_claimed"], f"{where}.infeasibility_claimed"
        ),
        acquisition_query_neutral_attested=_boolean(
            row["acquisition_query_neutral_attested"],
            f"{where}.acquisition_query_neutral_attested",
        ),
        preregistered_allowlisted_authority_required=_boolean(
            row["preregistered_allowlisted_authority_required"],
            f"{where}.preregistered_allowlisted_authority_required",
        ),
        query_local_overlay_authority_required=_boolean(
            row["query_local_overlay_authority_required"],
            f"{where}.query_local_overlay_authority_required",
        ),
        boundary_catalogue_authority_required=_boolean(
            row["boundary_catalogue_authority_required"],
            f"{where}.boundary_catalogue_authority_required",
        ),
        base_model_mutated=_boolean(
            row["base_model_mutated"], f"{where}.base_model_mutated"
        ),
        promotion_authorized=_boolean(
            row["promotion_authorized"], f"{where}.promotion_authorized"
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_initial_state_mass(value: Any, where: str) -> InitialStateMassV1:
    row = _record(value, ("state_id", "probability"), where)
    result = InitialStateMassV1(
        _content_id(row["state_id"], f"{where}.state_id"),
        _fraction(row["probability"], f"{where}.probability"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_reward_weight(value: Any, where: str) -> RewardWeightV1:
    row = _record(value, ("name", "weight"), where)
    result = RewardWeightV1(
        _text(row["name"], f"{where}.name"),
        _fraction(row["weight"], f"{where}.weight"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_return_bound_proof(
    value: Any,
    where: str,
) -> RegisteredReturnBoundProofV1:
    row = _record(
        value,
        (
            "schema",
            "schema_version",
            "structural_id",
            "environment_instance_id",
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "acquisition_manifest_id",
            "reward_weights",
            "item_count",
            "maximum_match_events",
            "terminal_clear_bonus_upper",
            "return_upper",
            "reward_basis_nonnegative",
            "formula_id",
            "authority_kind",
            "proof_id",
        ),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.registered_return_bound_proof.v1",
        f"{where}.schema",
    )
    _literal(row["schema_version"], "1.1.0", f"{where}.schema_version")
    for field in (
        "structural_id",
        "environment_instance_id",
        "observation_log_id",
        "semantics_profile_id",
        "observation_authority_id",
        "acquisition_manifest_id",
        "proof_id",
    ):
        _content_id(row[field], f"{where}.{field}")
    result = RegisteredReturnBoundProofV1(
        structural_id=row["structural_id"],
        environment_instance_id=row["environment_instance_id"],
        observation_log_id=row["observation_log_id"],
        semantics_profile_id=row["semantics_profile_id"],
        observation_authority_id=row["observation_authority_id"],
        acquisition_manifest_id=row["acquisition_manifest_id"],
        reward_weights=_items(
            row["reward_weights"],
            _parse_reward_weight,
            f"{where}.reward_weights",
        ),
        item_count=_integer(
            row["item_count"], f"{where}.item_count", minimum=1
        ),
        maximum_match_events=_integer(
            row["maximum_match_events"],
            f"{where}.maximum_match_events",
            minimum=0,
        ),
        terminal_clear_bonus_upper=_fraction(
            row["terminal_clear_bonus_upper"],
            f"{where}.terminal_clear_bonus_upper",
        ),
        return_upper=_fraction(row["return_upper"], f"{where}.return_upper"),
        reward_basis_nonnegative=_boolean(
            row["reward_basis_nonnegative"],
            f"{where}.reward_basis_nonnegative",
        ),
        formula_id=_text(row["formula_id"], f"{where}.formula_id"),
        authority_kind=_text(
            row["authority_kind"], f"{where}.authority_kind"
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_frozen_partial_audit_thresholds_v1(
    document: Any,
) -> FrozenPartialAuditThresholdsV1:
    where = "FrozenPartialAuditThresholdsV1"
    row = _record(
        document,
        (
            "schema",
            "schema_version",
            "partial_model_id",
            "horizon",
            "initial_state_distribution",
            "reward_weights",
            "normalized_regret_tolerance",
            "risk_tolerance",
            "return_bound_proof",
            "unrestricted_upper_formula_id",
            "goal_id",
            "thresholds_id",
        ),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.frozen_partial_audit_thresholds.v1",
        f"{where}.schema",
    )
    _literal(row["schema_version"], "1.1.0", f"{where}.schema_version")
    _content_id(row["partial_model_id"], f"{where}.partial_model_id")
    _content_id(row["thresholds_id"], f"{where}.thresholds_id")
    result = FrozenPartialAuditThresholdsV1(
        partial_model_id=row["partial_model_id"],
        horizon=_integer(row["horizon"], f"{where}.horizon", minimum=1),
        initial_state_distribution=_items(
            row["initial_state_distribution"],
            _parse_initial_state_mass,
            f"{where}.initial_state_distribution",
        ),
        reward_weights=_items(
            row["reward_weights"],
            _parse_reward_weight,
            f"{where}.reward_weights",
        ),
        normalized_regret_tolerance=_fraction(
            row["normalized_regret_tolerance"],
            f"{where}.normalized_regret_tolerance",
        ),
        risk_tolerance=_fraction(
            row["risk_tolerance"], f"{where}.risk_tolerance"
        ),
        return_bound_proof=_parse_return_bound_proof(
            row["return_bound_proof"], f"{where}.return_bound_proof"
        ),
        unrestricted_upper_formula_id=_text(
            row["unrestricted_upper_formula_id"],
            f"{where}.unrestricted_upper_formula_id",
        ),
        goal_id=_text(row["goal_id"], f"{where}.goal_id"),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_plan_assignment(
    value: Any,
    where: str,
) -> ContingentPlanAssignmentV1:
    row = _record(
        value,
        ("schema", "cell_id", "semantic_action_id", "assignment_id"),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.partial_contingent_plan_assignment.v1",
        f"{where}.schema",
    )
    _content_id(row["assignment_id"], f"{where}.assignment_id")
    result = ContingentPlanAssignmentV1(
        _content_id(row["cell_id"], f"{where}.cell_id"),
        _content_id(
            row["semantic_action_id"], f"{where}.semantic_action_id"
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_plan_stage(value: Any, where: str) -> ContingentPlanStageV1:
    row = _record(
        value,
        ("schema", "time_index", "assignments", "stage_id"),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.partial_contingent_plan_stage.v1",
        f"{where}.schema",
    )
    _content_id(row["stage_id"], f"{where}.stage_id")
    result = ContingentPlanStageV1(
        _integer(row["time_index"], f"{where}.time_index", minimum=0),
        _items(
            row["assignments"],
            _parse_plan_assignment,
            f"{where}.assignments",
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _parse_frozen_contingent_abstract_plan_v1(
    document: Any,
) -> FrozenContingentAbstractPlanV1:
    where = "FrozenContingentAbstractPlanV1"
    row = _record(
        document,
        (
            "schema",
            "schema_version",
            "partial_model_id",
            "horizon",
            "stages",
            "selector_kind",
            "policy_randomization_allowed",
            "plan_id",
        ),
        where,
    )
    _literal(
        row["schema"],
        "acfqp.frozen_partial_contingent_abstract_plan.v1",
        f"{where}.schema",
    )
    _literal(row["schema_version"], "1.1.0", f"{where}.schema_version")
    _content_id(row["partial_model_id"], f"{where}.partial_model_id")
    _content_id(row["plan_id"], f"{where}.plan_id")
    result = FrozenContingentAbstractPlanV1(
        partial_model_id=row["partial_model_id"],
        horizon=_integer(row["horizon"], f"{where}.horizon", minimum=1),
        stages=_items(row["stages"], _parse_plan_stage, f"{where}.stages"),
        selector_kind=_text(
            row["selector_kind"], f"{where}.selector_kind"
        ),
        policy_randomization_allowed=_boolean(
            row["policy_randomization_allowed"],
            f"{where}.policy_randomization_allowed",
        ),
    )
    _require_round_trip(result, row, where)
    return result


def _transport_call(parser: Callable[[Any], _T], document: Any) -> _T:
    try:
        return parser(document)
    except H2DurableTransportRoundTripViolation:
        raise
    except Exception as error:
        raise H2DurableTransportRoundTripViolation(
            f"typed constructor rejected transported document: {error}"
        ) from error


def parse_query_scoped_partial_rapm_v3(
    document: Any,
) -> QueryScopedPartialRAPMV3:
    """Reconstruct an exact V3 query-scoped partial RAPM document."""

    return _transport_call(_parse_query_scoped_partial_rapm_v3, document)


def parse_frozen_partial_audit_thresholds_v1(
    document: Any,
) -> FrozenPartialAuditThresholdsV1:
    """Reconstruct exact frozen partial-audit thresholds."""

    return _transport_call(_parse_frozen_partial_audit_thresholds_v1, document)


def parse_frozen_contingent_abstract_plan_v1(
    document: Any,
) -> FrozenContingentAbstractPlanV1:
    """Reconstruct an exact deterministic contingent abstract plan."""

    return _transport_call(_parse_frozen_contingent_abstract_plan_v1, document)


__all__ = [
    "DurableH2TransportInvariantViolation",
    "DurableTransportRoundTripViolation",
    "H2DurableTransportInvariantViolation",
    "H2DurableTransportRoundTripViolation",
    "parse_frozen_contingent_abstract_plan_v1",
    "parse_frozen_partial_audit_thresholds_v1",
    "parse_query_scoped_partial_rapm_v3",
]
