"""Arithmetic replay of Phase-3E marginal route-upper candidates.

``RouteUpperBoundEnvelopeV1`` is intentionally a transport envelope: its
constructor proves only that the envelope is well typed.  This module supplies
the missing generation proof.  In the official profile, an envelope is
admissible only when it is recomputed from all of the following frozen inputs:

* the official counter registry and shared-resource comparison profile;
* the route-specific, content-addressed affine formula;
* pre-execution cardinality *claims*;
* the finite V0 cap profile; and
* the exact route context, decision point, transaction, and causal evidence.

Every operational counter leaf has exactly one formula term.  Cardinality
inputs are explicit even when their value is zero, so a missing forbidden
route family can never be silently interpreted as native zero.  The proof in
this module establishes formula arithmetic and identity binding only.  It does
**not** establish that a cardinality claim is true of its source artifacts or
that hard caps were operationally enforced.  Consequently it cannot, by
itself, authorize a route decision.  The Contract-1.0 semantic registry keeps
``CARDINALITY_EVIDENCE`` fail closed until its authoritative parent-source
extractors exist.  Its ``ROUTE_UPPER`` handler additionally requires the
authority-bearing cardinality result before replaying this formula, so the
dependency cannot be bypassed with a self-hash.  No scalar cost or break-even
claim is introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from acfqp.accounting_v1 import (
    LaneEnum,
    ReducerEnum,
    SHARED_AXES,
    ComparisonProfileV1,
    CounterRegistryV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.phase3e_ids import (
    ROUTE_UPPER_DERIVATION_PROOF_DOMAIN,
    ROUTE_UPPER_FORMULA_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import (
    LOCAL_WORK_CAP_BINDINGS,
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteUpperBoundEnvelopeV1,
    TIGHT_PREEXECUTION_UPPER,
    TransactionV1,
    TypedNotApplicable,
)


SCHEMA_VERSION = "1.0.0"
FORMULA_KEY = "phase3e_tight_marginal_route_upper_formula_v1"
FORMULA_REPLAY_ONLY = "FORMULA_AND_BINDING_REPLAY_ONLY"


class RouteUpperFormulaV1Error(ValueError):
    """A formula, derivation input, or replay proof is invalid."""


class LocalCapImpossible(RouteUpperFormulaV1Error):
    """A pre-execution structural cardinality exceeds the local hard cap."""

    outcome = CausalOutcome.LOCAL_CAP_IMPOSSIBLE

    def __init__(self, count_name: str, value: int, cap_name: str, hard_cap: int):
        self.count_name = count_name
        self.value = value
        self.cap_name = cap_name
        self.hard_cap = hard_cap
        super().__init__(
            "LOCAL_CAP_IMPOSSIBLE: "
            f"{count_name}={value} exceeds {cap_name}={hard_cap}"
        )


class CapMode(str, Enum):
    NONE = "NONE"
    MIN_HARD_CAP = "MIN_HARD_CAP"


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise RouteUpperFormulaV1Error(str(error)) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RouteUpperFormulaV1Error(f"{field} must be a full content ID") from error


def _token(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise RouteUpperFormulaV1Error(f"{field} must be a nonempty string")
    return value


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise RouteUpperFormulaV1Error(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _route(value: Any) -> RouteKind:
    try:
        return RouteKind(value)
    except (TypeError, ValueError) as error:
        raise RouteUpperFormulaV1Error(f"invalid route kind: {value!r}") from error


def _cap_mode(value: Any) -> CapMode:
    try:
        return CapMode(value)
    except (TypeError, ValueError) as error:
        raise RouteUpperFormulaV1Error(f"invalid cap mode: {value!r}") from error


@dataclass(frozen=True, slots=True)
class AffineLeafUpperTermV1:
    """One exact nonnegative affine expression for one operational leaf."""

    target_leaf: str
    source_count: str
    coefficient: int
    addend: int
    cap_mode: CapMode
    cap_name: str | None

    def __post_init__(self) -> None:
        _token(self.target_leaf, "target_leaf")
        _token(self.source_count, "source_count")
        _nonnegative(self.coefficient, "coefficient")
        _nonnegative(self.addend, "addend")
        object.__setattr__(self, "cap_mode", _cap_mode(self.cap_mode))
        if self.cap_mode is CapMode.NONE:
            if self.cap_name is not None:
                raise RouteUpperFormulaV1Error(
                    "uncapped formula term cannot name a hard cap"
                )
        else:
            _token(self.cap_name, "cap_name")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_leaf": self.target_leaf,
            "source_count": self.source_count,
            "coefficient": self.coefficient,
            "addend": self.addend,
            "cap_mode": self.cap_mode.value,
            "cap_name": self.cap_name,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "AffineLeafUpperTermV1":
        expected = {
            "target_leaf",
            "source_count",
            "coefficient",
            "addend",
            "cap_mode",
            "cap_name",
        }
        _fields(document, expected, "affine leaf-upper term")
        return cls(
            document["target_leaf"],
            document["source_count"],
            document["coefficient"],
            document["addend"],
            document["cap_mode"],
            document["cap_name"],
        )


@dataclass(frozen=True, slots=True)
class StructuralCapGuardV1:
    """A non-work structural cardinality that must fit before local execution."""

    source_count: str
    cap_name: str

    def __post_init__(self) -> None:
        _token(self.source_count, "structural source_count")
        _token(self.cap_name, "structural cap_name")

    def to_dict(self) -> dict[str, str]:
        return {"source_count": self.source_count, "cap_name": self.cap_name}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "StructuralCapGuardV1":
        _fields(document, {"source_count", "cap_name"}, "structural cap guard")
        return cls(document["source_count"], document["cap_name"])


# These cardinalities are compiler/solver capacity facts rather than native
# FQ11 work leaves.  Successor-row work is already upper-bounded through
# ``local.compiler_input_records``; the other structural facts need explicit
# guards so they cannot disappear from the pre-execution proof.
OFFICIAL_STRUCTURAL_GUARDS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            ("structural.cell_policy_assignments", "max_cell_policy_assignments"),
            ("structural.form_subset_evaluations", "max_form_subset_evaluations"),
            ("structural.rational_bits", "max_rational_bits"),
            ("structural.slice_actions", "max_slice_actions"),
            ("structural.slice_cells", "max_slice_cells"),
            ("structural.slice_members", "max_slice_members"),
        )
    )
)


@dataclass(frozen=True, slots=True)
class RouteUpperFormulaV1:
    counter_registry_id: str
    comparison_profile_id: str
    route_cap_profile_id: str
    route_kind: RouteKind
    terms: tuple[AffineLeafUpperTermV1, ...]
    structural_guards: tuple[StructuralCapGuardV1, ...]
    formula_key: str = FORMULA_KEY
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.counter_registry_id, "counter_registry_id")
        _cid(self.comparison_profile_id, "comparison_profile_id")
        _cid(self.route_cap_profile_id, "route_cap_profile_id")
        object.__setattr__(self, "route_kind", _route(self.route_kind))
        if self.formula_key != FORMULA_KEY or self.schema_version != SCHEMA_VERSION:
            raise RouteUpperFormulaV1Error("formula key/version mismatch")
        if not self.terms or tuple(
            sorted(self.terms, key=lambda term: term.target_leaf)
        ) != self.terms:
            raise RouteUpperFormulaV1Error(
                "formula terms must be nonempty and target-leaf sorted"
            )
        if len({term.target_leaf for term in self.terms}) != len(self.terms):
            raise RouteUpperFormulaV1Error(
                "each operational leaf may have only one formula term"
            )
        if len({term.source_count for term in self.terms}) != len(self.terms):
            raise RouteUpperFormulaV1Error(
                "official affine terms require distinct source counts"
            )
        if tuple(
            sorted(self.structural_guards, key=lambda guard: guard.source_count)
        ) != self.structural_guards:
            raise RouteUpperFormulaV1Error(
                "structural guards must be source-count sorted"
            )
        guard_counts = [guard.source_count for guard in self.structural_guards]
        if len(set(guard_counts)) != len(guard_counts):
            raise RouteUpperFormulaV1Error("structural guard repeats a source count")
        if set(guard_counts).intersection(term.source_count for term in self.terms):
            raise RouteUpperFormulaV1Error(
                "structural and work-leaf source counts must be disjoint"
            )

    @property
    def required_count_names(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                [term.source_count for term in self.terms]
                + [guard.source_count for guard in self.structural_guards]
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_upper_formula.v1",
            "schema_version": self.schema_version,
            "formula_key": self.formula_key,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "route_cap_profile_id": self.route_cap_profile_id,
            "route_kind": self.route_kind.value,
            "terms": [term.to_dict() for term in self.terms],
            "structural_guards": [
                guard.to_dict() for guard in self.structural_guards
            ],
        }

    @property
    def formula_id(self) -> str:
        return content_id(ROUTE_UPPER_FORMULA_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "formula_id": self.formula_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteUpperFormulaV1":
        expected = {
            "schema",
            "schema_version",
            "formula_key",
            "counter_registry_id",
            "comparison_profile_id",
            "route_cap_profile_id",
            "route_kind",
            "terms",
            "structural_guards",
            "formula_id",
        }
        _fields(document, expected, "route-upper formula")
        if (
            document["schema"] != "acfqp.route_upper_formula.v1"
            or type(document["terms"]) is not list
            or type(document["structural_guards"]) is not list
        ):
            raise RouteUpperFormulaV1Error("route-upper formula schema mismatch")
        result = cls(
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["route_cap_profile_id"],
            document["route_kind"],
            tuple(AffineLeafUpperTermV1.from_dict(row) for row in document["terms"]),
            tuple(
                StructuralCapGuardV1.from_dict(row)
                for row in document["structural_guards"]
            ),
            document["formula_key"],
            document["schema_version"],
        )
        if document["formula_id"] != result.formula_id:
            raise RouteUpperFormulaV1Error("formula content ID mismatch")
        return result

    def validate_official(
        self,
        registry: CounterRegistryV1,
        profile: ComparisonProfileV1,
        cap_profile: Any,
    ) -> None:
        expected = official_route_upper_formula_v1(
            self.route_kind, registry=registry, profile=profile, cap_profile=cap_profile
        )
        if self != expected or self.formula_id != expected.formula_id:
            raise RouteUpperFormulaV1Error(
                "formula differs from the official route/cardinality/cap formula"
            )


def official_route_upper_formula_v1(
    route_kind: RouteKind | str,
    *,
    registry: CounterRegistryV1 | None = None,
    profile: ComparisonProfileV1 | None = None,
    cap_profile: Any | None = None,
) -> RouteUpperFormulaV1:
    """Return the one official affine formula for a marginal route kind."""

    route = _route(route_kind)
    registry = registry or official_counter_registry_v1()
    registry.validate_official_catalogue()
    profile = profile or official_comparison_profile_v1(registry)
    profile.validate(registry)
    if cap_profile is None:
        if route is RouteKind.LOCAL_ATTEMPT:
            cap_profile = RouteCapProfileV1()
        else:
            raise RouteUpperFormulaV1Error(
                "direct-fallback formula requires an explicit finite "
                "GroundFallbackCapProfileV1"
            )
    cap_profile_id = _validated_route_cap_profile_id(route, cap_profile)
    local_bindings = dict(LOCAL_WORK_CAP_BINDINGS)
    if route is RouteKind.DIRECT_FALLBACK:
        from acfqp.phase3e_fallback_v1 import (
            GROUND_FALLBACK_WORK_CAP_BINDINGS,
        )

        fallback_bindings = dict(GROUND_FALLBACK_WORK_CAP_BINDINGS)
    else:
        fallback_bindings = {}
    work_cap_bindings = (
        local_bindings if route is RouteKind.LOCAL_ATTEMPT else fallback_bindings
    )
    terms = tuple(
        AffineLeafUpperTermV1(
            target_leaf=leaf.path,
            source_count=leaf.path,
            coefficient=1,
            addend=0,
            cap_mode=(
                CapMode.MIN_HARD_CAP
                if leaf.path in work_cap_bindings
                else CapMode.NONE
            ),
            cap_name=work_cap_bindings.get(leaf.path),
        )
        for leaf in registry.operational_leaves
    )
    guards = (
        tuple(StructuralCapGuardV1(*row) for row in OFFICIAL_STRUCTURAL_GUARDS)
        if route is RouteKind.LOCAL_ATTEMPT
        else ()
    )
    return RouteUpperFormulaV1(
        registry.registry_id,
        profile.comparison_profile_id,
        cap_profile_id,
        route,
        terms,
        guards,
    )


def _fallback_na(field: str) -> TypedNotApplicable:
    return TypedNotApplicable(
        f"{field} does not apply to the direct-fallback marginal upper"
    )


def _ref_payload(value: str | TypedNotApplicable) -> Any:
    return value.to_dict() if isinstance(value, TypedNotApplicable) else value


def _parse_ref(value: Any, field: str) -> str | TypedNotApplicable:
    if isinstance(value, Mapping):
        return TypedNotApplicable.from_dict(value)
    return _cid(value, field)


@dataclass(frozen=True, slots=True)
class RouteUpperDerivationProofV1:
    route_decision_context_id: str
    decision_point_id: str
    transaction_id: str | TypedNotApplicable
    causal_evidence_id: str | TypedNotApplicable
    route_cap_profile_id: str
    cardinality_evidence_id: str
    counter_registry_id: str
    comparison_profile_id: str
    formula_id: str
    route_kind: RouteKind
    leaf_upper_bounds: tuple[tuple[str, int], ...]
    comparison_upper_bounds: tuple[tuple[str, int], ...]
    route_upper_bound_envelope_id: str
    proof_scope: str = FORMULA_REPLAY_ONLY
    authorizes_route_selection: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "decision_point_id",
            "route_cap_profile_id",
            "cardinality_evidence_id",
            "counter_registry_id",
            "comparison_profile_id",
            "formula_id",
            "route_upper_bound_envelope_id",
        ):
            _cid(getattr(self, field), field)
        for field in ("transaction_id", "causal_evidence_id"):
            value = getattr(self, field)
            if isinstance(value, TypedNotApplicable):
                continue
            _cid(value, field)
        object.__setattr__(self, "route_kind", _route(self.route_kind))
        if (
            self.schema_version != SCHEMA_VERSION
            or self.proof_scope != FORMULA_REPLAY_ONLY
            or self.authorizes_route_selection is not False
        ):
            raise RouteUpperFormulaV1Error("derivation-proof schema version mismatch")
        if (
            not self.leaf_upper_bounds
            or tuple(sorted(self.leaf_upper_bounds)) != self.leaf_upper_bounds
            or len(dict(self.leaf_upper_bounds)) != len(self.leaf_upper_bounds)
        ):
            raise RouteUpperFormulaV1Error(
                "leaf upper bounds must be nonempty, unique, and sorted"
            )
        for name, value in self.leaf_upper_bounds:
            _token(name, "leaf upper name")
            _nonnegative(value, name)
        if tuple(axis for axis, _ in self.comparison_upper_bounds) != SHARED_AXES:
            raise RouteUpperFormulaV1Error(
                "derivation proof must contain the exact eight shared axes"
            )
        for axis, value in self.comparison_upper_bounds:
            _nonnegative(value, axis)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_upper_derivation_proof.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": _ref_payload(self.transaction_id),
            "causal_evidence_id": _ref_payload(self.causal_evidence_id),
            "route_cap_profile_id": self.route_cap_profile_id,
            "cardinality_evidence_id": self.cardinality_evidence_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "formula_id": self.formula_id,
            "route_kind": self.route_kind.value,
            "leaf_upper_bounds": [
                {"path": path, "value": value}
                for path, value in self.leaf_upper_bounds
            ],
            "comparison_upper_bounds": [
                {"axis": axis, "value": value}
                for axis, value in self.comparison_upper_bounds
            ],
            "route_upper_bound_envelope_id": self.route_upper_bound_envelope_id,
            "proof_scope": self.proof_scope,
            "authorizes_route_selection": False,
        }

    @property
    def derivation_proof_id(self) -> str:
        return content_id(ROUTE_UPPER_DERIVATION_PROOF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "derivation_proof_id": self.derivation_proof_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "RouteUpperDerivationProofV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "transaction_id",
            "causal_evidence_id",
            "route_cap_profile_id",
            "cardinality_evidence_id",
            "counter_registry_id",
            "comparison_profile_id",
            "formula_id",
            "route_kind",
            "leaf_upper_bounds",
            "comparison_upper_bounds",
            "route_upper_bound_envelope_id",
            "proof_scope",
            "authorizes_route_selection",
            "derivation_proof_id",
        }
        _fields(document, expected, "route-upper derivation proof")
        if (
            document["schema"] != "acfqp.route_upper_derivation_proof.v1"
            or type(document["leaf_upper_bounds"]) is not list
            or type(document["comparison_upper_bounds"]) is not list
        ):
            raise RouteUpperFormulaV1Error("derivation-proof schema mismatch")
        leaves: list[tuple[str, int]] = []
        for row in document["leaf_upper_bounds"]:
            _fields(row, {"path", "value"}, "leaf upper row")
            leaves.append((row["path"], row["value"]))
        axes: list[tuple[str, int]] = []
        for row in document["comparison_upper_bounds"]:
            _fields(row, {"axis", "value"}, "comparison upper row")
            axes.append((row["axis"], row["value"]))
        result = cls(
            document["RouteDecisionContext_id"],
            document["decision_point_id"],
            _parse_ref(document["transaction_id"], "transaction_id"),
            _parse_ref(document["causal_evidence_id"], "causal_evidence_id"),
            document["route_cap_profile_id"],
            document["cardinality_evidence_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["formula_id"],
            document["route_kind"],
            tuple(leaves),
            tuple(axes),
            document["route_upper_bound_envelope_id"],
            document["proof_scope"],
            document["authorizes_route_selection"],
            document["schema_version"],
        )
        if document["derivation_proof_id"] != result.derivation_proof_id:
            raise RouteUpperFormulaV1Error("derivation-proof content ID mismatch")
        return result


def _validated_route_cap_profile_id(route: RouteKind, cap_profile: Any) -> str:
    """Validate and return the route-specific finite cap identity.

    Local transaction caps are the frozen V0 ``RouteCapProfileV1``.  Direct
    ground fallback has an independent, query-attempt finite cap profile; it
    must not be rebound to the local cap merely to satisfy the generic route
    envelope schema.
    """

    if route is RouteKind.LOCAL_ATTEMPT:
        if not isinstance(cap_profile, RouteCapProfileV1):
            raise RouteUpperFormulaV1Error(
                "local upper requires RouteCapProfileV1"
            )
        RouteCapProfileV1.from_dict(cap_profile.to_dict())
        return cap_profile.route_cap_profile_id
    from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1

    if not isinstance(cap_profile, GroundFallbackCapProfileV1):
        raise RouteUpperFormulaV1Error(
            "direct-fallback upper requires GroundFallbackCapProfileV1"
        )
    GroundFallbackCapProfileV1.from_dict(cap_profile.to_dict())
    return cap_profile.ground_fallback_cap_profile_id


def _validate_chain(
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cardinality: CardinalityEvidenceV1,
    cap_profile: Any,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    formula: RouteUpperFormulaV1,
    transaction: TransactionV1 | None,
    causal: CausalEvidenceV1 | None,
) -> None:
    registry.validate_official_catalogue()
    profile.validate(registry)
    cap_profile_id = _validated_route_cap_profile_id(
        formula.route_kind, cap_profile
    )
    formula.validate_official(registry, profile, cap_profile)
    if context.counter_registry_id != registry.registry_id:
        raise RouteUpperFormulaV1Error("route context/counter registry mismatch")
    if context.comparison_profile_id != profile.comparison_profile_id:
        raise RouteUpperFormulaV1Error("route context/comparison profile mismatch")
    if formula.counter_registry_id != registry.registry_id:
        raise RouteUpperFormulaV1Error("formula/counter registry mismatch")
    if formula.comparison_profile_id != profile.comparison_profile_id:
        raise RouteUpperFormulaV1Error("formula/comparison profile mismatch")
    if formula.route_cap_profile_id != cap_profile_id:
        raise RouteUpperFormulaV1Error("formula/cap profile mismatch")
    if decision_point.route_decision_context_id != context.route_decision_context_id:
        raise RouteUpperFormulaV1Error("decision point uses a stale route context")
    if cardinality.route_decision_context_id != context.route_decision_context_id:
        raise RouteUpperFormulaV1Error("cardinality uses a stale route context")
    if cardinality.route_kind is not formula.route_kind:
        raise RouteUpperFormulaV1Error("formula/cardinality route mismatch")
    if cardinality.route_cap_profile_id != cap_profile_id:
        raise RouteUpperFormulaV1Error("cardinality/cap profile mismatch")

    if formula.route_kind is RouteKind.LOCAL_ATTEMPT:
        if transaction is None or causal is None:
            raise RouteUpperFormulaV1Error(
                "local derivation requires current transaction and causal evidence"
            )
        if causal.local_allowed is not True or causal.outcome is not CausalOutcome.FOUND:
            raise RouteUpperFormulaV1Error(
                "only FOUND causal evidence can derive a local upper"
            )
        if causal.cap_id != cap_profile_id:
            raise RouteUpperFormulaV1Error("causal evidence/cap profile mismatch")
        if transaction.logical_occurrence_id != context.logical_occurrence_id:
            raise RouteUpperFormulaV1Error("transaction occurrence mismatch")
        if transaction.route_attempt_id != context.route_attempt_id:
            raise RouteUpperFormulaV1Error("transaction route-attempt mismatch")
        if transaction.decision_point_id != decision_point.decision_point_id:
            raise RouteUpperFormulaV1Error("transaction decision-point mismatch")
        if transaction.route_cap_profile_id != cap_profile_id:
            raise RouteUpperFormulaV1Error("transaction/cap profile mismatch")
        if decision_point.transaction_index != transaction.transaction_index:
            raise RouteUpperFormulaV1Error("decision-point transaction index mismatch")
        if decision_point.frontier_snapshot_id != transaction.frontier_snapshot_id:
            raise RouteUpperFormulaV1Error("decision-point transaction frontier mismatch")
        if decision_point.causal_evidence_id != causal.causal_evidence_id:
            raise RouteUpperFormulaV1Error("decision-point causal evidence mismatch")
        if causal.frontier_snapshot_id != transaction.frontier_snapshot_id:
            raise RouteUpperFormulaV1Error("causal/transaction frontier mismatch")
        if cardinality.frontier_snapshot_id != transaction.frontier_snapshot_id:
            raise RouteUpperFormulaV1Error("cardinality/transaction frontier mismatch")
    elif transaction is not None or causal is not None:
        raise RouteUpperFormulaV1Error(
            "direct-fallback derivation cannot consume local transaction/causal inputs"
        )


def _derive_leaf_uppers(
    formula: RouteUpperFormulaV1,
    cardinality: CardinalityEvidenceV1,
    cap_profile: Any,
) -> tuple[tuple[str, int], ...]:
    counts = dict(cardinality.counts)
    expected = set(formula.required_count_names)
    actual = set(counts)
    if actual != expected:
        raise RouteUpperFormulaV1Error(
            "cardinality/formula input mismatch; "
            f"missing={sorted(expected - actual)!r}, extra={sorted(actual - expected)!r}"
        )
    if formula.route_kind is RouteKind.LOCAL_ATTEMPT:
        caps = dict(cap_profile.limits)
    else:
        from acfqp.phase3e_fallback_v1 import (
            GROUND_FALLBACK_WORK_CAP_BINDINGS,
        )

        caps = {
            cap_name: getattr(cap_profile, cap_name)
            for _, cap_name in GROUND_FALLBACK_WORK_CAP_BINDINGS
        }
        # One composed candidate is one Bellman backup, so both independent
        # hard caps bound the same native leaf.
        caps["max_bellman_backups"] = min(
            cap_profile.max_bellman_backups,
            cap_profile.max_composed_candidates,
        )
    for guard in formula.structural_guards:
        if guard.cap_name not in caps:
            raise RouteUpperFormulaV1Error("structural guard names an unknown cap")
        value = counts[guard.source_count]
        hard_cap = caps[guard.cap_name]
        if value > hard_cap:
            raise LocalCapImpossible(
                guard.source_count, value, guard.cap_name, hard_cap
            )

    values: dict[str, int] = {}
    for term in formula.terms:
        raw = counts[term.source_count] * term.coefficient + term.addend
        if term.cap_mode is CapMode.MIN_HARD_CAP:
            assert term.cap_name is not None
            try:
                raw = min(raw, caps[term.cap_name])
            except KeyError as error:
                raise RouteUpperFormulaV1Error(
                    "formula term names an unknown hard cap"
                ) from error
        values[term.target_leaf] = raw

    # The already-spent common-prefix vector is never part of these counts.
    # ``common.*`` values that do appear here are post-freeze operational
    # verification suffix work (result/cap/projection/terminal checks).  That
    # suffix must be estimated per route and later aggregated with execution;
    # forbidding the paths outright would make complete operational accounting
    # impossible.  Rebuild work remains outside every marginal route upper.
    rebuild_only = {
        path for path in values if path.startswith("rebuild.")
    }
    forbidden_family = (
        {path for path in values if path.startswith("fallback.")}
        if formula.route_kind is RouteKind.LOCAL_ATTEMPT
        else {path for path in values if path.startswith("local.")}
    )
    forbidden = rebuild_only | forbidden_family
    nonzero = sorted(path for path in forbidden if values[path] != 0)
    if nonzero:
        raise RouteUpperFormulaV1Error(
            "marginal route cardinality contains forbidden nonzero leaves: "
            f"{nonzero!r}"
        )
    return tuple(sorted(values.items()))


def _project_leaf_uppers(
    leaf_values: tuple[tuple[str, int], ...],
    profile: ComparisonProfileV1,
) -> tuple[tuple[str, int], ...]:
    source = dict(leaf_values)
    axes = {axis.name: 0 for axis in profile.axes}
    for term in profile.terms:
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    result = tuple(sorted(axes.items()))
    if tuple(axis for axis, _ in result) != SHARED_AXES:
        raise RouteUpperFormulaV1Error(
            "official projection did not produce the exact eight shared axes"
        )
    return result


def derive_route_upper_v1(
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cardinality: CardinalityEvidenceV1,
    cap_profile: Any,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    formula: RouteUpperFormulaV1,
    transaction: TransactionV1 | None = None,
    causal: CausalEvidenceV1 | None = None,
) -> tuple[RouteUpperBoundEnvelopeV1, RouteUpperDerivationProofV1]:
    """Derive one formula-consistent marginal upper candidate.

    The returned proof deliberately has ``authorizes_route_selection=False``.
    Source-cardinality truth is a separate semantic obligation.
    """

    _validate_chain(
        context=context,
        decision_point=decision_point,
        cardinality=cardinality,
        cap_profile=cap_profile,
        registry=registry,
        profile=profile,
        formula=formula,
        transaction=transaction,
        causal=causal,
    )
    leaf_values = _derive_leaf_uppers(formula, cardinality, cap_profile)
    comparison_values = _project_leaf_uppers(leaf_values, profile)
    local = formula.route_kind is RouteKind.LOCAL_ATTEMPT
    transaction_ref: str | TypedNotApplicable = (
        transaction.transaction_id if local and transaction else _fallback_na("transaction")
    )
    transaction_index: int | TypedNotApplicable = (
        transaction.transaction_index
        if local and transaction
        else _fallback_na("transaction index")
    )
    frontier_ref: str | TypedNotApplicable = (
        transaction.frontier_snapshot_id
        if local and transaction
        else _fallback_na("frontier snapshot")
    )
    causal_ref: str | TypedNotApplicable = (
        causal.causal_evidence_id if local and causal else _fallback_na("causal evidence")
    )
    envelope = RouteUpperBoundEnvelopeV1(
        context.preregistration_id,
        context.protocol_id,
        context.comparison_profile_id,
        context.counter_registry_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        transaction_ref,
        transaction_index,
        frontier_ref,
        causal_ref,
        _validated_route_cap_profile_id(formula.route_kind, cap_profile),
        cardinality.cardinality_evidence_id,
        formula.formula_id,
        formula.route_kind,
        TIGHT_PREEXECUTION_UPPER,
        comparison_values,
    )
    envelope.validate_bindings(
        context,
        decision_point,
        cardinality,
        transaction=transaction,
        causal=causal,
    )
    proof = RouteUpperDerivationProofV1(
        context.route_decision_context_id,
        decision_point.decision_point_id,
        transaction_ref,
        causal_ref,
        _validated_route_cap_profile_id(formula.route_kind, cap_profile),
        cardinality.cardinality_evidence_id,
        registry.registry_id,
        profile.comparison_profile_id,
        formula.formula_id,
        formula.route_kind,
        leaf_values,
        comparison_values,
        envelope.route_upper_bound_envelope_id,
    )
    return envelope, proof


def verify_route_upper_derivation_v1(
    envelope: RouteUpperBoundEnvelopeV1,
    proof: RouteUpperDerivationProofV1,
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    cardinality: CardinalityEvidenceV1,
    cap_profile: Any,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    formula: RouteUpperFormulaV1,
    transaction: TransactionV1 | None = None,
    causal: CausalEvidenceV1 | None = None,
) -> None:
    """Reject hand-filled, stale, or incompletely projected upper candidates.

    This is an arithmetic replay, not a cardinality-source or cap-enforcement
    authority.  Successful return therefore must not be interpreted as route
    authorization.
    """

    recomputed_envelope, recomputed_proof = derive_route_upper_v1(
        context=context,
        decision_point=decision_point,
        cardinality=cardinality,
        cap_profile=cap_profile,
        registry=registry,
        profile=profile,
        formula=formula,
        transaction=transaction,
        causal=causal,
    )
    if (
        envelope != recomputed_envelope
        or envelope.route_upper_bound_envelope_id
        != recomputed_envelope.route_upper_bound_envelope_id
    ):
        raise RouteUpperFormulaV1Error(
            "route upper does not recompute from the frozen formula inputs"
        )
    if (
        proof != recomputed_proof
        or proof.derivation_proof_id != recomputed_proof.derivation_proof_id
    ):
        raise RouteUpperFormulaV1Error(
            "route-upper derivation proof does not replay exactly"
        )


__all__ = [
    "AffineLeafUpperTermV1",
    "CapMode",
    "FORMULA_KEY",
    "FORMULA_REPLAY_ONLY",
    "LocalCapImpossible",
    "OFFICIAL_STRUCTURAL_GUARDS",
    "RouteUpperDerivationProofV1",
    "RouteUpperFormulaV1",
    "RouteUpperFormulaV1Error",
    "StructuralCapGuardV1",
    "derive_route_upper_v1",
    "official_route_upper_formula_v1",
    "verify_route_upper_derivation_v1",
]
