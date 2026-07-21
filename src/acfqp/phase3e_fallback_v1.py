"""Strictly capped exact ground fallback for the Phase-3E consumer.

The public production entry point in this module is deliberately authority
gated.  It will not touch the ground kernel until the selected fallback route,
its upper, and its cardinality evidence have authority-bearing semantic replay
results.  The current partial FQ7 registry may therefore reject execution with
``NOT_IMPLEMENTED``; that is the intended fail-closed behaviour, not a reason
to silently run J0.

``run_ground_fallback_search_v1`` is the separately named raw search primitive
used by evaluation tests.  It is exact over deterministic, finite-horizon
Markov policies, but its result explicitly carries no semantic authority.
The authority-gated production executor adds a non-serializable in-process
runtime seal only after all pre-execution and actual-bound checks pass.  The
``GROUND_FALLBACK`` verifier checks that seal without rerunning the solver, as
required by FQ10.  This V0 seal is not an isolated-worker/public-bundle proof.

The hard-cap profile is independent of the frozen *local* transaction cap
profile in :mod:`acfqp.routing_v1`.  In particular, this module never wraps an
uncapped J0 call and never aliases fallback limits to ``RouteCapProfileV1``.
Every kernel transition is preceded by a conservative reservation of
``max_positive_outcomes_per_step`` rows, so the actual outcome-row counter can
never overshoot its cap after an unexpectedly large ``kernel.step`` result.
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from itertools import product
from typing import Any, Hashable, Mapping, Sequence

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.accounting_v1 import (
    CounterRegistryV1,
    RouteKindEnum,
    WorkVectorV1,
    explicit_records_v1,
    official_counter_registry_v1,
)
from acfqp.phase3e_ids import (
    GROUND_FALLBACK_CAP_PROFILE_DOMAIN,
    GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN,
    GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN,
    GROUND_FALLBACK_EXTRACTION_PROFILE_DOMAIN,
    GROUND_FALLBACK_ISOLATION_PROFILE_DOMAIN,
    GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
    GROUND_FALLBACK_RESULT_DOMAIN,
    SEALED_GROUND_FALLBACK_ROUTE_CAP_PROFILE_DOMAIN,
    canonical_json,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_sealed_executor_v1 import (
    RuntimeFactoryCardinalityV1,
)
from acfqp.planning.common import (
    as_fraction,
    deterministic_order,
    is_stopped,
    iter_outcomes,
    outcome_reward,
    query_horizon,
    query_initial_distribution,
    reward_weights,
    validate_query,
)
from acfqp.planning.ground import ParetoPoint, pareto_prune, select_constrained
from acfqp.planning.policy import FiniteHorizonPolicy


SCHEMA_VERSION = "1.0.0"
CAP_PROFILE_KEY = "phase3e_ground_fallback_caps_v1"
SEALED_ROUTE_CAP_PROFILE_KEY = (
    "phase3e_sealed_ground_fallback_route_caps_v1"
)
_LEGACY_CAP_SCHEMA = "acfqp.ground_fallback_cap_profile.v1"
_SEALED_ROUTE_CAP_SCHEMA = (
    "acfqp.sealed_ground_fallback_route_cap_profile.v1"
)
RECORDER_ID = "phase3e_ground_fallback_executor_v1"
TRUSTED_EXECUTOR_PROFILE_KEY = (
    "phase3e_inprocess_trusted_ground_fallback_executor_v1"
)
TRUSTED_EXECUTOR_SCOPE = "IN_PROCESS_TRUSTED_EXECUTOR_VERTICAL_SLICE"
ISOLATED_TRUSTED_EXECUTOR_PROFILE_KEY = (
    "phase3e_safe_chain_isolated_ground_fallback_executor_v1"
)
ISOLATED_TRUSTED_EXECUTOR_SCOPE = (
    "BUBBLEWRAP_SAFE_CHAIN_GROUND_FALLBACK_VERTICAL_SLICE"
)
SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_KEY = (
    "safe_chain_frozen_phase3c_fallback_cardinality_v1"
)

# This is a capacity profile, not an observed execution.  The isolated
# supervisor rejects a source tree, frozen Phase-3C bundle, request, or output
# that exceeds the corresponding component cap.  Actual WorkVector byte
# leaves are computed from the exact files mounted/read/written by that run.
# The caps are grounded in the current fixture payload (roughly 4.8 MiB of
# Python source and 0.45 MiB of frozen artifacts), with a finite allowance for
# the canonical request and result rather than arbitrary padding.
FALLBACK_RUNTIME_SOURCE_BYTES_CAP = 6 * 1024 * 1024
FALLBACK_FROZEN_BUNDLE_BYTES_CAP = 512 * 1024
FALLBACK_REQUEST_BYTES_CAP = 64 * 1024
FALLBACK_OUTPUT_BYTES_CAP = 1024 * 1024
FALLBACK_WORKING_BYTES_CAP = 256 * 1024 * 1024
FALLBACK_STAGED_BYTES_UPPER = (
    FALLBACK_RUNTIME_SOURCE_BYTES_CAP
    + FALLBACK_FROZEN_BUNDLE_BYTES_CAP
    + FALLBACK_REQUEST_BYTES_CAP
)
FALLBACK_READ_BYTES_UPPER = (
    FALLBACK_STAGED_BYTES_UPPER + FALLBACK_OUTPUT_BYTES_CAP
)
FALLBACK_MOUNTED_BYTES_UPPER = (
    FALLBACK_STAGED_BYTES_UPPER + FALLBACK_OUTPUT_BYTES_CAP
)

_FALLBACK_ISOLATION_PROFILE_PAYLOAD = {
    "schema": "acfqp.ground_fallback_isolation_profile.v1",
    "schema_version": SCHEMA_VERSION,
    "profile_key": ISOLATED_TRUSTED_EXECUTOR_PROFILE_KEY,
    "isolation_backend": "bubblewrap_mount_and_network_namespace",
    "runtime_source_bytes_cap": FALLBACK_RUNTIME_SOURCE_BYTES_CAP,
    "frozen_bundle_bytes_cap": FALLBACK_FROZEN_BUNDLE_BYTES_CAP,
    "request_bytes_cap": FALLBACK_REQUEST_BYTES_CAP,
    "output_bytes_cap": FALLBACK_OUTPUT_BYTES_CAP,
    "working_bytes_cap": FALLBACK_WORKING_BYTES_CAP,
    "process_launches_upper": 1,
    "read_bytes_upper": FALLBACK_READ_BYTES_UPPER,
    "staged_bytes_upper": FALLBACK_STAGED_BYTES_UPPER,
    "mounted_bytes_upper": FALLBACK_MOUNTED_BYTES_UPPER,
    "resource_accounting": (
        "actual mounted payload bytes plus actual worker output bytes; "
        "read traffic uses the allowed upper-bound semantics"
    ),
}

FALLBACK_ISOLATION_PROFILE_ID = content_id(
    GROUND_FALLBACK_ISOLATION_PROFILE_DOMAIN,
    _FALLBACK_ISOLATION_PROFILE_PAYLOAD,
)

# The exact native-work leaves controlled by the independent ground-fallback
# hard-cap profile.  Route-upper replay imports this registry at call time, so
# cardinality derivation, formula clipping, and post-run compliance cannot
# silently drift to different cap names.
GROUND_FALLBACK_WORK_CAP_BINDINGS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            ("fallback.actions_evaluated", "max_actions_evaluated"),
            ("fallback.bellman_backups", "max_bellman_backups"),
            ("fallback.ground_steps", "max_ground_steps"),
            ("fallback.outcome_rows", "max_outcome_rows"),
            ("fallback.states_expanded", "max_states_expanded"),
            ("control.cap_checks", "max_cap_checks"),
        )
    )
)


_SAFE_CHAIN_EXTRACTION_PROFILE_PAYLOAD = {
    "schema": "acfqp.fallback_cardinality_extraction_profile.v1",
    "profile_key": SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_KEY,
    "parent_schema": "FrozenPhase3CWorld",
    "query_profile": "g2048_select_safe_chain_2x2_v0:H2",
    "solver_semantics_id": "phase3e_ground_fallback_executor_v1",
    "inputs": [
        "verified Phase3C manifest/model/BuildEpoch byte identities",
        "verified full_same_query_all_action_graph metadata",
        "complete bound ground-action catalogue",
    ],
    "formula": {
        "states_expanded": "decision_state_time_pairs",
        "actions_evaluated": "state_action_pairs",
        "ground_steps": "state_action_pairs",
        "outcome_rows": "positive_probability_outcomes",
        # This exact theorem is deliberately fixture/profile specific.  It is
        # not inferred from a previous fallback execution and must not be
        # reused for another query, horizon, solver, or parent bundle.
        "composed_candidates": 5696,
        "bellman_backups": "composed_candidates",
        "verification_suffix_protocol_checks": 5,
        "cap_checks": (
            "states_expanded + actions_evaluated + ground_steps + "
            "composed_candidates"
        ),
    },
    "isolation_profile_id": FALLBACK_ISOLATION_PROFILE_ID,
    "forbidden_preselection_operations": [
        "kernel.step",
        "transition materialization",
        "ground outcome enumeration",
    ],
}


SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_ID = content_id(
    GROUND_FALLBACK_EXTRACTION_PROFILE_DOMAIN,
    _SAFE_CHAIN_EXTRACTION_PROFILE_PAYLOAD,
)


class GroundFallbackV1Error(ValueError):
    """A fallback cap, identity binding, or result is invalid."""


class GroundFallbackProtocolError(GroundFallbackV1Error):
    """The kernel violated a preregistered execution assumption."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        # Populated by the outer executor before re-raising.  This preserves
        # all native work preceding a protocol failure without turning that
        # failure into one of the three ground-solver certificate outcomes.
        self.partial_work_vector: WorkVectorV1 | None = None


class GroundFallbackRouteUpperNotIntegratedError(GroundFallbackV1Error):
    """A supplied route-upper formula does not bind the fallback cap type."""


class GroundFallbackOutcome(str, Enum):
    FEASIBLE_CERTIFIED = "FEASIBLE_CERTIFIED"
    INFEASIBLE_CERTIFIED = "INFEASIBLE_CERTIFIED"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"


_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY = object()


def _positive(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise GroundFallbackV1Error(f"{field_name} must be a positive exact integer")
    return value


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise GroundFallbackV1Error(
            f"{field_name} must be a nonnegative exact integer"
        )
    return value


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise GroundFallbackV1Error(
            f"{field_name} must be a full Phase-3E content ID"
        ) from error


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise GroundFallbackV1Error(str(error)) from error


def _outcome(value: Any) -> GroundFallbackOutcome:
    try:
        return GroundFallbackOutcome(value)
    except (TypeError, ValueError) as error:
        raise GroundFallbackV1Error(f"invalid ground fallback outcome: {value!r}") from error


@dataclass(frozen=True, slots=True)
class GroundFallbackCapProfileV1:
    """Finite hard caps for one direct-ground fallback attempt.

    ``max_composed_candidates`` is a structural search cap.  Every candidate
    composition is also charged as one registered
    ``fallback.bellman_backups`` event; occupancy-frontier setup itself is not
    charged a second time.  This prevents an exponential candidate family from
    disappearing into a diagnostic-only result field.
    """

    max_states_expanded: int
    max_actions_evaluated: int
    max_ground_steps: int
    max_outcome_rows: int
    max_bellman_backups: int
    max_composed_candidates: int
    max_cap_checks: int
    max_positive_outcomes_per_step: int
    reserved_route_cap_checks: int = field(default=0, kw_only=True)
    profile_key: str = CAP_PROFILE_KEY
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "max_states_expanded",
            "max_actions_evaluated",
            "max_ground_steps",
            "max_outcome_rows",
            "max_bellman_backups",
            "max_composed_candidates",
            "max_cap_checks",
            "max_positive_outcomes_per_step",
        ):
            _positive(getattr(self, field_name), field_name)
        if (
            type(self.reserved_route_cap_checks) is not int
            or self.reserved_route_cap_checks < 0
            or self.reserved_route_cap_checks > self.max_cap_checks
        ):
            raise GroundFallbackV1Error(
                "reserved_route_cap_checks must fit within max_cap_checks"
            )
        expected_profile_key = (
            CAP_PROFILE_KEY
            if self.reserved_route_cap_checks == 0
            else SEALED_ROUTE_CAP_PROFILE_KEY
        )
        if (
            self.profile_key != expected_profile_key
            or self.schema_version != SCHEMA_VERSION
        ):
            raise GroundFallbackV1Error(
                "ground fallback cap profile key/version mismatch"
            )
        if self.max_ground_steps > self.max_actions_evaluated:
            raise GroundFallbackV1Error(
                "ground-step cap cannot exceed the action-evaluation cap"
            )
        if self.max_outcome_rows < self.max_positive_outcomes_per_step:
            raise GroundFallbackV1Error(
                "outcome-row cap must admit at least one preregistered transition"
            )

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": (
                _LEGACY_CAP_SCHEMA
                if self.reserved_route_cap_checks == 0
                else _SEALED_ROUTE_CAP_SCHEMA
            ),
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "max_states_expanded": self.max_states_expanded,
            "max_actions_evaluated": self.max_actions_evaluated,
            "max_ground_steps": self.max_ground_steps,
            "max_outcome_rows": self.max_outcome_rows,
            "max_bellman_backups": self.max_bellman_backups,
            "max_composed_candidates": self.max_composed_candidates,
            "max_cap_checks": self.max_cap_checks,
            "max_positive_outcomes_per_step": (
                self.max_positive_outcomes_per_step
            ),
        }
        if self.reserved_route_cap_checks:
            payload.update(
                {
                    "reserved_route_cap_checks": (
                        self.reserved_route_cap_checks
                    ),
                    "max_solver_cap_checks": self.max_solver_cap_checks,
                }
            )
        return payload

    @property
    def max_solver_cap_checks(self) -> int:
        """Return the fallback-worker share of the route-wide check cap.

        A sealed route charges runtime-factory checks in the same native leaf.
        Reserving them here prevents the worker from consuming a route-wide
        allowance that its own WorkVector does not include.
        """

        return self.max_cap_checks - self.reserved_route_cap_checks

    @property
    def ground_fallback_cap_profile_id(self) -> str:
        domain = (
            GROUND_FALLBACK_CAP_PROFILE_DOMAIN
            if self.reserved_route_cap_checks == 0
            else SEALED_GROUND_FALLBACK_ROUTE_CAP_PROFILE_DOMAIN
        )
        return content_id(domain, self._payload())

    @property
    def route_cap_profile_id(self) -> str:
        """Compatibility name used by generic route envelopes."""

        return self.ground_fallback_cap_profile_id

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "ground_fallback_cap_profile_id": self.ground_fallback_cap_profile_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "GroundFallbackCapProfileV1":
        legacy_expected = {
            "schema",
            "schema_version",
            "profile_key",
            "max_states_expanded",
            "max_actions_evaluated",
            "max_ground_steps",
            "max_outcome_rows",
            "max_bellman_backups",
            "max_composed_candidates",
            "max_cap_checks",
            "max_positive_outcomes_per_step",
            "ground_fallback_cap_profile_id",
        }
        schema = document.get("schema")
        if schema == _LEGACY_CAP_SCHEMA:
            expected = legacy_expected
            reserve = 0
        elif schema == _SEALED_ROUTE_CAP_SCHEMA:
            expected = legacy_expected | {
                "reserved_route_cap_checks",
                "max_solver_cap_checks",
            }
            reserve = document.get("reserved_route_cap_checks")
        else:
            raise GroundFallbackV1Error("ground fallback cap schema mismatch")
        _fields(document, expected, "ground fallback cap profile")
        result = cls(
            document["max_states_expanded"],
            document["max_actions_evaluated"],
            document["max_ground_steps"],
            document["max_outcome_rows"],
            document["max_bellman_backups"],
            document["max_composed_candidates"],
            document["max_cap_checks"],
            document["max_positive_outcomes_per_step"],
            document["profile_key"],
            document["schema_version"],
            reserved_route_cap_checks=reserve,
        )
        if (
            schema == _SEALED_ROUTE_CAP_SCHEMA
            and document["max_solver_cap_checks"]
            != result.max_solver_cap_checks
        ):
            raise GroundFallbackV1Error(
                "sealed fallback cap solver reservation is inconsistent"
            )
        if (
            document["ground_fallback_cap_profile_id"]
            != result.ground_fallback_cap_profile_id
        ):
            raise GroundFallbackV1Error("ground fallback cap content ID mismatch")
        return result


_BOUND_NAMES = (
    "common.protocol_checks",
    "fallback.actions_evaluated",
    "fallback.bellman_backups",
    "fallback.composed_candidates",
    "fallback.ground_steps",
    "fallback.outcome_rows",
    "fallback.states_expanded",
    "control.cap_checks",
)


_SAFE_CHAIN_PARENT_ROLES = (
    "bound_ground_action_catalogue",
    "build_epoch",
    "locality_metadata",
    "manifest",
    "portable_rapm",
)
_SAFE_CHAIN_GRAPH_COUNT_NAMES = (
    "decision_state_time_pairs",
    "positive_probability_outcomes",
    "state_action_pairs",
)


def _fallback_parent_id(role: str, payload: Any) -> str:
    return content_id(
        GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
        {
            "schema": "acfqp.safe_chain_fallback_parent_binding.v1",
            "role": role,
            "payload": payload,
        },
    )


@dataclass(frozen=True, slots=True)
class SafeChainFallbackCardinalitySourceV1:
    """Frozen parent projection for the safe-chain direct-fallback profile.

    This remains a transport object.  Semantic authority comes only from
    reloading and independently validating ``FrozenPhase3CWorld.source_bundle``
    and recomputing this complete object with the registered extractor.
    """

    route_decision_context_id: str
    decision_point_id: str
    ground_fallback_cap_profile_id: str
    structural_id: str
    query_id: str
    build_epoch_id: str
    parent_artifact_ids: tuple[tuple[str, str], ...]
    ground_action_member_ids: tuple[str, ...]
    graph_counts: tuple[tuple[str, int], ...]
    frozen_at_protocol_step: int
    extraction_profile_id: str = SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_ID
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "route_decision_context_id",
            "decision_point_id",
            "ground_fallback_cap_profile_id",
            "structural_id",
            "query_id",
            "build_epoch_id",
            "extraction_profile_id",
        ):
            _cid(getattr(self, field_name), field_name)
        if self.extraction_profile_id != SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_ID:
            raise GroundFallbackV1Error(
                "unregistered safe-chain cardinality extraction profile"
            )
        if tuple(role for role, _ in self.parent_artifact_ids) != (
            _SAFE_CHAIN_PARENT_ROLES
        ):
            raise GroundFallbackV1Error(
                "safe-chain fallback source lacks the exact parent roles"
            )
        for role, artifact_id in self.parent_artifact_ids:
            if not role:
                raise GroundFallbackV1Error("parent role must be nonempty")
            _cid(artifact_id, f"{role} parent artifact ID")
        if (
            not self.ground_action_member_ids
            or tuple(sorted(self.ground_action_member_ids))
            != self.ground_action_member_ids
            or len(set(self.ground_action_member_ids))
            != len(self.ground_action_member_ids)
        ):
            raise GroundFallbackV1Error(
                "ground-action members must be nonempty, unique, and sorted"
            )
        for member_id in self.ground_action_member_ids:
            _cid(member_id, "ground_action_member_id")
        if tuple(name for name, _ in self.graph_counts) != (
            _SAFE_CHAIN_GRAPH_COUNT_NAMES
        ):
            raise GroundFallbackV1Error(
                "safe-chain graph counts use the wrong registered fields"
            )
        for name, value in self.graph_counts:
            _nonnegative(value, name)
        if (
            type(self.frozen_at_protocol_step) is not int
            or self.frozen_at_protocol_step < 0
        ):
            raise GroundFallbackV1Error(
                "frozen_at_protocol_step must be a nonnegative exact integer"
            )
        if self.measured_before_execution is not True:
            raise GroundFallbackV1Error(
                "safe-chain cardinality source must predate execution"
            )
        if self.depends_on_actual_route_work is not False:
            raise GroundFallbackV1Error(
                "safe-chain cardinality source cannot consume actual route work"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise GroundFallbackV1Error(
                "safe-chain cardinality source schema version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.safe_chain_fallback_cardinality_source.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "ground_fallback_cap_profile_id": (
                self.ground_fallback_cap_profile_id
            ),
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "parent_artifact_ids": [
                {"role": role, "artifact_id": artifact_id}
                for role, artifact_id in self.parent_artifact_ids
            ],
            "ground_action_member_ids": list(self.ground_action_member_ids),
            "graph_counts": [
                {"name": name, "value": value}
                for name, value in self.graph_counts
            ],
            "frozen_at_protocol_step": self.frozen_at_protocol_step,
            "extraction_profile_id": self.extraction_profile_id,
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
        }

    @property
    def source_artifact_id(self) -> str:
        return content_id(
            GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "source_artifact_id": self.source_artifact_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SafeChainFallbackCardinalitySourceV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "ground_fallback_cap_profile_id",
            "structural_id",
            "query_id",
            "BuildEpoch_id",
            "parent_artifact_ids",
            "ground_action_member_ids",
            "graph_counts",
            "frozen_at_protocol_step",
            "extraction_profile_id",
            "measured_before_execution",
            "depends_on_actual_route_work",
            "source_artifact_id",
        }
        _fields(document, expected, "safe-chain fallback cardinality source")
        if (
            document["schema"]
            != "acfqp.safe_chain_fallback_cardinality_source.v1"
            or type(document["parent_artifact_ids"]) is not list
            or type(document["ground_action_member_ids"]) is not list
            or type(document["graph_counts"]) is not list
        ):
            raise GroundFallbackV1Error(
                "safe-chain fallback cardinality source schema mismatch"
            )
        parents: list[tuple[str, str]] = []
        for row in document["parent_artifact_ids"]:
            _fields(row, {"role", "artifact_id"}, "fallback parent row")
            parents.append((row["role"], row["artifact_id"]))
        counts: list[tuple[str, int]] = []
        for row in document["graph_counts"]:
            _fields(row, {"name", "value"}, "fallback graph-count row")
            counts.append((row["name"], row["value"]))
        result = cls(
            document["RouteDecisionContext_id"],
            document["decision_point_id"],
            document["ground_fallback_cap_profile_id"],
            document["structural_id"],
            document["query_id"],
            document["BuildEpoch_id"],
            tuple(parents),
            tuple(document["ground_action_member_ids"]),
            tuple(counts),
            document["frozen_at_protocol_step"],
            document["extraction_profile_id"],
            document["measured_before_execution"],
            document["depends_on_actual_route_work"],
            document["schema_version"],
        )
        if document["source_artifact_id"] != result.source_artifact_id:
            raise GroundFallbackV1Error(
                "safe-chain fallback source content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class GroundFallbackCardinalityBoundV1:
    """Pre-execution fallback cardinalities derived from frozen sources.

    ``bounds`` retain the exact complete-search cardinalities derived from the
    frozen source, even when a finite execution cap is smaller.  The official
    route formula applies ``min(exact cardinality, hard cap)`` to controlled
    native leaves.  Keeping these layers separate prevents a wide hard cap
    from masquerading as a tight estimate and permits a deliberately small
    selected fallback to close as ``CAP_EXHAUSTED``.

    This object proves only shape, execution-assumption compatibility, and
    identity binding.  It is a source artifact for ``CardinalityEvidenceV1``
    and is deliberately *not* semantic authority for the truth of the supplied
    bounds.
    """

    route_decision_context_id: str
    decision_point_id: str
    ground_fallback_cap_profile_id: str
    bounds: tuple[tuple[str, int], ...]
    source_artifact_ids: tuple[str, ...]
    runtime_factory_cardinality: RuntimeFactoryCardinalityV1 | None = field(
        default=None, kw_only=True
    )
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False
    authorizes_route_selection: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.route_decision_context_id, "route_decision_context_id")
        _cid(self.decision_point_id, "decision_point_id")
        _cid(
            self.ground_fallback_cap_profile_id,
            "ground_fallback_cap_profile_id",
        )
        if tuple(name for name, _ in self.bounds) != _BOUND_NAMES:
            raise GroundFallbackV1Error(
                "fallback cardinality bounds must contain the exact canonical names"
            )
        for name, value in self.bounds:
            _nonnegative(value, name)
        if (
            not self.source_artifact_ids
            or tuple(sorted(self.source_artifact_ids)) != self.source_artifact_ids
            or len(set(self.source_artifact_ids)) != len(self.source_artifact_ids)
        ):
            raise GroundFallbackV1Error(
                "fallback cardinality source IDs must be nonempty, unique, and sorted"
            )
        for source_id in self.source_artifact_ids:
            _cid(source_id, "source_artifact_id")
        if self.runtime_factory_cardinality is not None:
            parsed_runtime = RuntimeFactoryCardinalityV1.from_dict(
                self.runtime_factory_cardinality.to_dict()
            )
            if (
                parsed_runtime.runtime_factory_cardinality_id
                not in self.source_artifact_ids
            ):
                raise GroundFallbackV1Error(
                    "fallback bound does not bind its runtime cardinality source"
                )
        if self.measured_before_execution is not True:
            raise GroundFallbackV1Error(
                "fallback cardinalities must be frozen before execution"
            )
        if self.depends_on_actual_route_work is not False:
            raise GroundFallbackV1Error(
                "fallback cardinalities cannot depend on actual route work"
            )
        if self.authorizes_route_selection is not False:
            raise GroundFallbackV1Error(
                "a raw cardinality-bound source cannot authorize route selection"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise GroundFallbackV1Error("fallback cardinality schema version mismatch")

    def validate_against_cap(self, cap: GroundFallbackCapProfileV1) -> None:
        GroundFallbackCapProfileV1.from_dict(cap.to_dict())
        if self.ground_fallback_cap_profile_id != cap.ground_fallback_cap_profile_id:
            raise GroundFallbackV1Error("fallback cardinality/cap identity mismatch")
        expected_reserve = (
            0
            if self.runtime_factory_cardinality is None
            else dict(
                self.runtime_factory_cardinality.upper_values()
            )["control.cap_checks"]
        )
        if cap.reserved_route_cap_checks != expected_reserve:
            raise GroundFallbackV1Error(
                "fallback cap does not reserve the exact runtime-factory checks"
            )
        values = dict(self.bounds)
        if values["fallback.ground_steps"] > values["fallback.actions_evaluated"]:
            raise GroundFallbackV1Error(
                "ground-step upper cannot exceed action-evaluation upper"
            )
        if (
            values["fallback.bellman_backups"]
            < values["fallback.composed_candidates"]
        ):
            raise GroundFallbackV1Error(
                "every composed candidate needs a registered Bellman-backup upper"
            )
        if values["fallback.outcome_rows"] > (
            values["fallback.ground_steps"]
            * cap.max_positive_outcomes_per_step
        ):
            raise GroundFallbackV1Error(
                "outcome-row upper exceeds the preregistered per-step bound"
            )

    def operational_upper_values(
        self,
        cap: GroundFallbackCapProfileV1,
        registry: CounterRegistryV1 | None = None,
    ) -> tuple[tuple[str, int], ...]:
        """Return the exact FQ4 formula-plus-hard-cap marginal leaf upper."""

        self.validate_against_cap(cap)
        values = dict(self.operational_count_values(registry))
        for path, cap_name in GROUND_FALLBACK_WORK_CAP_BINDINGS:
            values[path] = min(values[path], getattr(cap, cap_name))
        # A composed candidate is charged as one Bellman backup.  Therefore
        # either cap can stop this native leaf; using only
        # ``max_bellman_backups`` would cease to be an upper for deliberately
        # asymmetric cap profiles.
        values["fallback.bellman_backups"] = min(
            values["fallback.bellman_backups"],
            cap.max_composed_candidates,
        )
        values["control.cap_rejections"] = self.cap_rejection_upper(cap)
        return tuple(sorted(values.items()))

    def cap_rejection_upper(self, cap: GroundFallbackCapProfileV1) -> int:
        """Return the exact 0/1 rejection upper implied before execution."""

        self.validate_against_cap(cap)
        source = dict(self.bounds)
        return int(
            any(
                (
                    path == "fallback.bellman_backups"
                    and source[path]
                    > min(cap.max_bellman_backups, cap.max_composed_candidates)
                )
                or (
                    path != "fallback.bellman_backups"
                    and source[path]
                    > (
                        cap.max_solver_cap_checks
                        if path == "control.cap_checks"
                        else getattr(cap, cap_name)
                    )
                )
                for path, cap_name in GROUND_FALLBACK_WORK_CAP_BINDINGS
            )
        )

    def operational_count_values(
        self, registry: CounterRegistryV1 | None = None
    ) -> tuple[tuple[str, int], ...]:
        """Project into the exact native count names consumed by route formulas.

        All non-fallback execution leaves are explicit native zero.  The
        registered five ``common.protocol_checks`` are the post-freeze
        verification suffix, not the already-spent common prefix.  The single
        possible cap rejection is included because a selected fallback may
        legitimately terminate as ``CAP_EXHAUSTED``.
        """

        trusted = registry or official_counter_registry_v1()
        trusted.validate_official_catalogue()
        values = {leaf.path: 0 for leaf in trusted.operational_leaves}
        source = dict(self.bounds)
        for path in (
            "common.protocol_checks",
            "fallback.states_expanded",
            "fallback.actions_evaluated",
            "fallback.ground_steps",
            "fallback.outcome_rows",
            "fallback.bellman_backups",
            "control.cap_checks",
        ):
            values[path] = source[path]
        # The official direct-fallback comparison is the isolated profile.
        # These are finite, preregistered capacity uppers; the isolated
        # supervisor later records exact payload/output sizes and peak RSS.
        # Keeping process launch nonzero removes the artificial structural
        # advantage of the historical in-process seam.
        values.update(
            {
                "process.launches": 1,
                "io.read_bytes": FALLBACK_READ_BYTES_UPPER,
                "io.staged_bytes": FALLBACK_STAGED_BYTES_UPPER,
                "io.output_bytes": FALLBACK_OUTPUT_BYTES_CAP,
                "io.mounted_bytes_peak": FALLBACK_MOUNTED_BYTES_UPPER,
                "memory.working_bytes_peak": FALLBACK_WORKING_BYTES_CAP,
            }
        )
        if self.runtime_factory_cardinality is not None:
            runtime = dict(self.runtime_factory_cardinality.upper_values())
            values["common.integrity_checks"] += 1
            for path in (
                "common.hash_invocations",
                "common.integrity_checks",
                "common.protocol_checks",
                "control.cap_checks",
                "io.read_bytes",
                "io.staged_bytes",
                "io.output_bytes",
            ):
                values[path] += runtime[path]
            # Both mounts coexist.  Working-set capacity uses MAX.
            values["io.mounted_bytes_peak"] += runtime[
                "io.mounted_bytes_peak"
            ]
            values["memory.working_bytes_peak"] += runtime[
                "memory.working_bytes_peak"
            ]
        # This uncapped structural view cannot predict whether a caller's
        # finite cap will reject work.  ``operational_upper_values`` replaces
        # this placeholder with the exact cap-relative 0/1 upper.
        values["control.cap_rejections"] = 0
        return tuple(sorted(values.items()))

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.ground_fallback_cardinality_bound.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "ground_fallback_cap_profile_id": self.ground_fallback_cap_profile_id,
            "bounds": [{"name": name, "value": value} for name, value in self.bounds],
            "source_artifact_ids": list(self.source_artifact_ids),
            "measured_before_execution": self.measured_before_execution,
            "depends_on_actual_route_work": self.depends_on_actual_route_work,
            "authorizes_route_selection": self.authorizes_route_selection,
        }
        if self.runtime_factory_cardinality is not None:
            payload["runtime_factory_cardinality"] = (
                self.runtime_factory_cardinality.to_dict()
            )
        return payload

    @property
    def ground_fallback_cardinality_bound_id(self) -> str:
        return content_id(GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "ground_fallback_cardinality_bound_id": (
                self.ground_fallback_cardinality_bound_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "GroundFallbackCardinalityBoundV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "ground_fallback_cap_profile_id",
            "bounds",
            "source_artifact_ids",
            "measured_before_execution",
            "depends_on_actual_route_work",
            "authorizes_route_selection",
            "ground_fallback_cardinality_bound_id",
        }
        if "runtime_factory_cardinality" in document:
            expected.add("runtime_factory_cardinality")
        _fields(document, expected, "ground fallback cardinality bound")
        if (
            document["schema"] != "acfqp.ground_fallback_cardinality_bound.v1"
            or type(document["bounds"]) is not list
            or type(document["source_artifact_ids"]) is not list
        ):
            raise GroundFallbackV1Error("ground fallback cardinality schema mismatch")
        bounds: list[tuple[str, int]] = []
        for row in document["bounds"]:
            _fields(row, {"name", "value"}, "fallback cardinality bound row")
            bounds.append((row["name"], row["value"]))
        result = cls(
            document["RouteDecisionContext_id"],
            document["decision_point_id"],
            document["ground_fallback_cap_profile_id"],
            tuple(bounds),
            tuple(document["source_artifact_ids"]),
            document["measured_before_execution"],
            document["depends_on_actual_route_work"],
            document["authorizes_route_selection"],
            document["schema_version"],
            runtime_factory_cardinality=(
                RuntimeFactoryCardinalityV1.from_dict(
                    document["runtime_factory_cardinality"]
                )
                if "runtime_factory_cardinality" in document
                else None
            ),
        )
        if (
            document["ground_fallback_cardinality_bound_id"]
            != result.ground_fallback_cardinality_bound_id
        ):
            raise GroundFallbackV1Error(
                "ground fallback cardinality content ID mismatch"
            )
        return result


def _require_frozen_safe_chain_world(world: Any) -> Any:
    from acfqp.frozen_phase3c import FrozenPhase3CWorld

    if not isinstance(world, FrozenPhase3CWorld):
        raise GroundFallbackV1Error(
            "safe-chain fallback authority requires FrozenPhase3CWorld"
        )
    counters = world.binding_counters
    if (
        counters.get("kernel_step_calls") != 0
        or counters.get("transition_closure_calls") != 0
    ):
        raise GroundFallbackV1Error(
            "frozen parent binding used ground transitions before route decision"
        )
    return world


def _safe_chain_action_member_ids(world: Any) -> tuple[str, ...]:
    from acfqp.artifacts import object_id

    members = tuple(
        sorted(
            _fallback_parent_id(
                "ground_state_action_member",
                {
                    "state_source_id": object_id(state, "state"),
                    "action_source_id": object_id(action, "ground-action"),
                },
            )
            for state, action in world.bound_ground_action_records
        )
    )
    if len(set(members)) != len(members):
        raise GroundFallbackV1Error(
            "frozen ground-action catalogue contains duplicate members"
        )
    return members


def safe_chain_fallback_context_identity_v1(world: Any) -> dict[str, str]:
    """Return the Phase-3E context identities derived from a frozen parent."""

    from acfqp.artifacts import object_id

    frozen = _require_frozen_safe_chain_world(world)
    action_members = _safe_chain_action_member_ids(frozen)
    structural_id = _fallback_parent_id(
        "structural",
        {"legacy_structural_id": frozen.structural_id},
    )
    query_id = _fallback_parent_id(
        "query",
        {
            "legacy_query_id": object_id(frozen.queries[1].query, "query"),
            "query_key": frozen.queries[1].query_key,
        },
    )
    build_epoch_id = _fallback_parent_id(
        "build_epoch",
        {
            "legacy_build_epoch_id": frozen.build_epoch["build_epoch_id"],
            "serialized_sha256": frozen.build_epoch_source_sha256,
        },
    )
    return {
        "structural_id": structural_id,
        "query_id": query_id,
        "build_epoch_id": build_epoch_id,
        "bound_ground_action_catalogue_id": _fallback_parent_id(
            "bound_ground_action_catalogue", list(action_members)
        ),
        "locality_metadata_id": _fallback_parent_id(
            "locality_metadata", frozen.source_locality_document
        ),
        "manifest_id": _fallback_parent_id(
            "manifest",
            {
                "manifest_sha256": frozen.source_manifest_sha256,
                "run_id": frozen.source_run_document["run_id"],
            },
        ),
        "portable_rapm_id": _fallback_parent_id(
            "portable_rapm",
            {
                "model_id": frozen.portable.model.model_id,
                "serialized_sha256": frozen.portable_rapm_source_sha256,
            },
        ),
    }


def derive_safe_chain_fallback_cardinality_source_v1(
    *,
    world: Any,
    context: Any,
    decision_point: Any,
    cap_profile: GroundFallbackCapProfileV1,
    frozen_at_protocol_step: int,
) -> SafeChainFallbackCardinalitySourceV1:
    """Project a verified frozen Phase-3C parent without ground transitions."""

    from acfqp.routing_v1 import DecisionPointV1, RouteDecisionContextV1

    frozen = _require_frozen_safe_chain_world(world)
    if not isinstance(context, RouteDecisionContextV1):
        raise GroundFallbackV1Error("context must be RouteDecisionContextV1")
    if not isinstance(decision_point, DecisionPointV1):
        raise GroundFallbackV1Error("decision_point must be DecisionPointV1")
    GroundFallbackCapProfileV1.from_dict(cap_profile.to_dict())
    if (
        decision_point.route_decision_context_id
        != context.route_decision_context_id
    ):
        raise GroundFallbackV1Error("decision point uses another route context")
    identities = safe_chain_fallback_context_identity_v1(frozen)
    for field in ("structural_id", "query_id", "build_epoch_id"):
        if getattr(context, field) != identities[field]:
            raise GroundFallbackV1Error(
                f"fallback context/{field} does not bind the frozen parent"
            )
    graph = frozen.source_locality_document.get(
        "full_same_query_all_action_graph"
    )
    if graph != {
        "decision_state_time_pairs": 20,
        "state_action_pairs": 48,
        "positive_probability_outcomes": 192,
    }:
        raise GroundFallbackV1Error(
            "frozen parent does not satisfy the registered safe-chain graph profile"
        )
    action_members = _safe_chain_action_member_ids(frozen)
    if len(action_members) != 144:
        raise GroundFallbackV1Error(
            "frozen parent ground-action catalogue is not complete for safe-chain"
        )
    parents = (
        (
            "bound_ground_action_catalogue",
            identities["bound_ground_action_catalogue_id"],
        ),
        ("build_epoch", identities["build_epoch_id"]),
        ("locality_metadata", identities["locality_metadata_id"]),
        ("manifest", identities["manifest_id"]),
        ("portable_rapm", identities["portable_rapm_id"]),
    )
    counts = tuple((name, int(graph[name])) for name in _SAFE_CHAIN_GRAPH_COUNT_NAMES)
    return SafeChainFallbackCardinalitySourceV1(
        context.route_decision_context_id,
        decision_point.decision_point_id,
        cap_profile.ground_fallback_cap_profile_id,
        context.structural_id,
        context.query_id,
        context.build_epoch_id,
        parents,
        action_members,
        counts,
        frozen_at_protocol_step,
    )


def derive_safe_chain_fallback_cardinality_bound_v1(
    *,
    source: SafeChainFallbackCardinalitySourceV1,
    cap_profile: GroundFallbackCapProfileV1,
    runtime_factory_cardinality: RuntimeFactoryCardinalityV1 | None = None,
) -> GroundFallbackCardinalityBoundV1:
    """Apply the registered fixture-specific integer upper formula."""

    parsed_source = SafeChainFallbackCardinalitySourceV1.from_dict(
        source.to_dict()
    )
    GroundFallbackCapProfileV1.from_dict(cap_profile.to_dict())
    if (
        parsed_source.ground_fallback_cap_profile_id
        != cap_profile.ground_fallback_cap_profile_id
    ):
        raise GroundFallbackV1Error("fallback source/cap identity mismatch")
    graph = dict(parsed_source.graph_counts)
    if graph != {
        "decision_state_time_pairs": 20,
        "positive_probability_outcomes": 192,
        "state_action_pairs": 48,
    }:
        raise GroundFallbackV1Error(
            "safe-chain graph counts do not satisfy the registered extractor"
        )
    states = graph["decision_state_time_pairs"]
    actions = graph["state_action_pairs"]
    outcomes = graph["positive_probability_outcomes"]
    composed = 5_696
    bounds = (
        ("common.protocol_checks", 5),
        ("fallback.actions_evaluated", actions),
        ("fallback.bellman_backups", composed),
        ("fallback.composed_candidates", composed),
        ("fallback.ground_steps", actions),
        ("fallback.outcome_rows", outcomes),
        ("fallback.states_expanded", states),
        ("control.cap_checks", states + actions + actions + composed),
    )
    parsed_runtime = (
        RuntimeFactoryCardinalityV1.from_dict(
            runtime_factory_cardinality.to_dict()
        )
        if runtime_factory_cardinality is not None
        else None
    )
    result = GroundFallbackCardinalityBoundV1(
        parsed_source.route_decision_context_id,
        parsed_source.decision_point_id,
        parsed_source.ground_fallback_cap_profile_id,
        bounds,
        tuple(
            sorted(
                (parsed_source.source_artifact_id,)
                + (
                    (parsed_runtime.runtime_factory_cardinality_id,)
                    if parsed_runtime is not None
                    else ()
                )
            )
        ),
        runtime_factory_cardinality=parsed_runtime,
    )
    result.validate_against_cap(cap_profile)
    return result


def build_ground_fallback_cardinality_evidence_v1(
    *,
    context: Any,
    decision_point: Any,
    cap_profile: GroundFallbackCapProfileV1,
    bound: GroundFallbackCardinalityBoundV1,
) -> Any:
    """Adapt a fallback bound into the generic ``CardinalityEvidenceV1`` shape.

    The adapter is intentionally limited to cardinality transport.  Call
    :func:`require_fallback_formula_binding_v1` at the formula boundary so a
    local cap profile or another fallback cap cannot be substituted for this
    exact source-bound profile.
    """

    from acfqp.routing_v1 import (
        CardinalityEvidenceV1,
        DecisionPointV1,
        RouteDecisionContextV1,
        RouteKind,
        TypedNotApplicable,
    )

    if not isinstance(context, RouteDecisionContextV1):
        raise GroundFallbackV1Error("context must be RouteDecisionContextV1")
    if not isinstance(decision_point, DecisionPointV1):
        raise GroundFallbackV1Error("decision_point must be DecisionPointV1")
    if decision_point.route_decision_context_id != context.route_decision_context_id:
        raise GroundFallbackV1Error("decision point uses another route context")
    bound.validate_against_cap(cap_profile)
    if (
        bound.route_decision_context_id != context.route_decision_context_id
        or bound.decision_point_id != decision_point.decision_point_id
    ):
        raise GroundFallbackV1Error("fallback cardinality bound is stale")
    sources = tuple(
        sorted(
            set(bound.source_artifact_ids)
            | {bound.ground_fallback_cardinality_bound_id}
        )
    )
    counts = dict(bound.operational_count_values())
    counts["control.cap_rejections"] = bound.cap_rejection_upper(cap_profile)
    return CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.DIRECT_FALLBACK,
        cap_profile.route_cap_profile_id,
        TypedNotApplicable("direct fallback cardinality is attempt-scoped"),
        tuple(sorted(counts.items())),
        sources,
    )


def require_fallback_formula_binding_v1(
    formula: Any,
    cap_profile: GroundFallbackCapProfileV1,
) -> None:
    """Fail closed unless a route formula supports the fallback-specific cap.

    This seam makes route-specific cap binding observable to an integrated
    runner and its tests; it must not substitute the local-only cap ID merely
    to make an envelope type-check.
    """

    from acfqp.routing_v1 import RouteKind

    if (
        getattr(formula, "route_kind", None) is not RouteKind.DIRECT_FALLBACK
        or getattr(formula, "route_cap_profile_id", None)
        != cap_profile.route_cap_profile_id
    ):
        raise GroundFallbackRouteUpperNotIntegratedError(
            "direct-fallback route formula does not bind the independent "
            "GroundFallbackCapProfileV1; the local-only cap adapter is forbidden"
        )


PolicySignature = tuple[tuple[int, str, str], ...]


def _ground_identity_payload(value: Any) -> Any:
    """Return a typed canonical payload, rejecting repr-only identities."""

    if isinstance(value, Enum):
        return {
            "kind": "enum",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _ground_identity_payload(value.value),
        }
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            "kind": "dataclass",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": [
                {
                    "name": descriptor.name,
                    "value": _ground_identity_payload(
                        getattr(value, descriptor.name)
                    ),
                }
                for descriptor in dataclasses.fields(value)
            ],
        }
    if isinstance(value, Fraction):
        return value
    if value is None or type(value) in {str, int, bool, float}:
        return value
    if type(value) in {tuple, list}:
        return {
            "kind": "tuple" if type(value) is tuple else "list",
            "items": [_ground_identity_payload(item) for item in value],
        }
    if type(value) in {set, frozenset}:
        rows = [_ground_identity_payload(item) for item in value]
        return {
            "kind": "frozenset" if type(value) is frozenset else "set",
            "items": sorted(rows, key=canonical_json),
        }
    if isinstance(value, Mapping):
        rows = [
            {
                "key": _ground_identity_payload(key),
                "value": _ground_identity_payload(item),
            }
            for key, item in value.items()
        ]
        return {"kind": "mapping", "items": sorted(rows, key=canonical_json)}
    raise GroundFallbackProtocolError(
        "ground state/action lacks a typed canonical identity encoding: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def _ground_object_id(value: Any, role: str) -> str:
    return content_id(
        GROUND_FALLBACK_RESULT_DOMAIN,
        {"identity_role": role, "payload": _ground_identity_payload(value)},
    )


def _policy_content_signature(
    policy: FiniteHorizonPolicy[Any, Any],
) -> PolicySignature:
    rows = tuple(
        (
            decision.remaining,
            _ground_object_id(decision.state, "ground_state"),
            _ground_object_id(decision.action, "ground_action"),
        )
        for decision in policy.decisions
    )
    return tuple(sorted(rows, key=lambda item: (-item[0], item[1], item[2])))


def reconstruct_safe_chain_policy_from_signature_v1(
    world: Any,
    signature: PolicySignature,
) -> FiniteHorizonPolicy[Any, Any]:
    """Bind worker policy IDs to frozen catalogue objects without transitions."""

    frozen = _require_frozen_safe_chain_world(world)
    parsed = _parse_policy_rows(_policy_rows(signature), "policy signature")
    by_pair: dict[tuple[str, str], tuple[Any, Any]] = {}
    for state, action in frozen.bound_ground_action_records:
        key = (
            _ground_object_id(state, "ground_state"),
            _ground_object_id(action, "ground_action"),
        )
        incumbent = by_pair.get(key)
        if incumbent is not None and incumbent != (state, action):
            raise GroundFallbackV1Error(
                "frozen ground catalogue has a policy-identity collision"
            )
        by_pair[key] = (state, action)
    decisions: list[tuple[tuple[int, Any], Any]] = []
    for remaining, state_id, action_id in parsed:
        try:
            state, action = by_pair[(state_id, action_id)]
        except KeyError as error:
            raise GroundFallbackV1Error(
                "isolated policy refers outside the frozen ground-action catalogue"
            ) from error
        decisions.append(((remaining, state), action))
    policy = FiniteHorizonPolicy.from_mapping(decisions)
    if _policy_content_signature(policy) != parsed:
        raise GroundFallbackV1Error(
            "reconstructed isolated policy does not preserve its exact signature"
        )
    return policy


def _policy_rows(signature: PolicySignature) -> list[dict[str, Any]]:
    return [
        {"remaining": remaining, "state": state, "action": action}
        for remaining, state, action in signature
    ]


def _parse_policy_rows(value: Any, context: str) -> PolicySignature:
    if type(value) is not list:
        raise GroundFallbackV1Error(f"{context} must be a list")
    result: list[tuple[int, str, str]] = []
    for row in value:
        _fields(row, {"remaining", "state", "action"}, context)
        remaining = _positive(row["remaining"], f"{context}.remaining")
        state_id = _cid(row["state"], f"{context}.state")
        action_id = _cid(row["action"], f"{context}.action")
        result.append((remaining, state_id, action_id))
    signature = tuple(result)
    if signature != tuple(
        sorted(signature, key=lambda item: (-item[0], item[1], item[2]))
    ):
        raise GroundFallbackV1Error(f"{context} is not canonically ordered")
    if len({(row[0], row[1]) for row in signature}) != len(signature):
        raise GroundFallbackV1Error(f"{context} repeats a state-time decision")
    return signature


@dataclass(frozen=True, slots=True)
class GroundFallbackFrontierPointV1:
    expected_reward: Fraction
    failure_probability: Fraction
    policy_signature: PolicySignature

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_reward", as_fraction(self.expected_reward))
        object.__setattr__(
            self, "failure_probability", as_fraction(self.failure_probability)
        )
        if self.failure_probability < 0 or self.failure_probability > 1:
            raise GroundFallbackV1Error("frontier failure probability lies outside [0,1]")
        _parse_policy_rows(_policy_rows(self.policy_signature), "policy signature")

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_reward": self.expected_reward,
            "failure_probability": self.failure_probability,
            "policy_signature": _policy_rows(self.policy_signature),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "GroundFallbackFrontierPointV1":
        _fields(
            document,
            {"expected_reward", "failure_probability", "policy_signature"},
            "ground fallback frontier point",
        )
        return cls(
            as_fraction(document["expected_reward"]),
            as_fraction(document["failure_probability"]),
            _parse_policy_rows(document["policy_signature"], "policy signature"),
        )


@dataclass(frozen=True, slots=True)
class GroundFallbackResultV1:
    """Serializable operational result; never semantic authority by itself."""

    route_decision_context_id: str
    decision_point_id: str
    route_decision_id: str
    selected_upper_id: str
    route_attempt_id: str
    query_id: str
    ground_fallback_cap_profile_id: str
    work_vector_id: str
    outcome: GroundFallbackOutcome
    search_complete: bool
    frontier: tuple[GroundFallbackFrontierPointV1, ...]
    selected_policy_signature: PolicySignature
    selected_expected_reward: Fraction | None
    selected_failure_probability: Fraction | None
    cap_exhausted_name: str | None
    composed_candidate_count: int
    semantic_authority: bool = False
    authorizes_terminal_classification: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "route_decision_context_id",
            "decision_point_id",
            "route_decision_id",
            "selected_upper_id",
            "route_attempt_id",
            "query_id",
            "ground_fallback_cap_profile_id",
            "work_vector_id",
        ):
            _cid(getattr(self, field_name), field_name)
        object.__setattr__(self, "outcome", _outcome(self.outcome))
        if type(self.search_complete) is not bool:
            raise GroundFallbackV1Error("search_complete must be an exact boolean")
        _nonnegative(self.composed_candidate_count, "composed_candidate_count")
        if self.semantic_authority is not False or self.authorizes_terminal_classification is not False:
            raise GroundFallbackV1Error(
                "raw fallback results cannot self-assert semantic or terminal authority"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise GroundFallbackV1Error("ground fallback result version mismatch")
        if tuple(
            sorted(
                self.frontier,
                key=lambda point: (
                    point.failure_probability,
                    -point.expected_reward,
                    point.policy_signature,
                ),
            )
        ) != self.frontier:
            raise GroundFallbackV1Error("ground fallback frontier is not canonical")
        _parse_policy_rows(
            _policy_rows(self.selected_policy_signature),
            "selected policy signature",
        )
        if self.outcome is GroundFallbackOutcome.CAP_EXHAUSTED:
            if self.search_complete or self.cap_exhausted_name is None:
                raise GroundFallbackV1Error(
                    "CAP_EXHAUSTED must be incomplete and name the exhausted cap"
                )
            if (
                self.frontier
                or self.selected_policy_signature
                or self.selected_expected_reward is not None
                or self.selected_failure_probability is not None
            ):
                raise GroundFallbackV1Error(
                    "partial cap-exhausted search cannot expose a certificate candidate"
                )
        elif not self.search_complete or self.cap_exhausted_name is not None:
            raise GroundFallbackV1Error(
                "a fallback certificate outcome requires exhaustive completion"
            )
        elif self.outcome is GroundFallbackOutcome.FEASIBLE_CERTIFIED:
            if (
                self.selected_expected_reward is None
                or self.selected_failure_probability is None
            ):
                raise GroundFallbackV1Error("feasible fallback lacks selected exact values")
            object.__setattr__(
                self,
                "selected_expected_reward",
                as_fraction(self.selected_expected_reward),
            )
            object.__setattr__(
                self,
                "selected_failure_probability",
                as_fraction(self.selected_failure_probability),
            )
            if not any(
                point.policy_signature == self.selected_policy_signature
                and point.expected_reward == self.selected_expected_reward
                and point.failure_probability == self.selected_failure_probability
                for point in self.frontier
            ):
                raise GroundFallbackV1Error(
                    "selected feasible point is absent from the exact frontier"
                )
        else:
            if (
                self.selected_policy_signature
                or self.selected_expected_reward is not None
                or self.selected_failure_probability is not None
            ):
                raise GroundFallbackV1Error(
                    "infeasibility certificate cannot expose a selected policy"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.ground_fallback_result.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_decision_id": self.route_decision_id,
            "selected_upper_id": self.selected_upper_id,
            "route_attempt_id": self.route_attempt_id,
            "query_id": self.query_id,
            "ground_fallback_cap_profile_id": self.ground_fallback_cap_profile_id,
            "work_vector_id": self.work_vector_id,
            "outcome": self.outcome.value,
            "search_complete": self.search_complete,
            "frontier": [point.to_dict() for point in self.frontier],
            "selected_policy_signature": _policy_rows(
                self.selected_policy_signature
            ),
            "selected_expected_reward": self.selected_expected_reward,
            "selected_failure_probability": self.selected_failure_probability,
            "cap_exhausted_name": self.cap_exhausted_name,
            "composed_candidate_count": self.composed_candidate_count,
            "semantic_authority": self.semantic_authority,
            "authorizes_terminal_classification": (
                self.authorizes_terminal_classification
            ),
        }

    @property
    def ground_fallback_result_id(self) -> str:
        return content_id(GROUND_FALLBACK_RESULT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "ground_fallback_result_id": self.ground_fallback_result_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "GroundFallbackResultV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "decision_point_id",
            "route_decision_id",
            "selected_upper_id",
            "route_attempt_id",
            "query_id",
            "ground_fallback_cap_profile_id",
            "work_vector_id",
            "outcome",
            "search_complete",
            "frontier",
            "selected_policy_signature",
            "selected_expected_reward",
            "selected_failure_probability",
            "cap_exhausted_name",
            "composed_candidate_count",
            "semantic_authority",
            "authorizes_terminal_classification",
            "ground_fallback_result_id",
        }
        _fields(document, expected, "ground fallback result")
        if (
            document["schema"] != "acfqp.ground_fallback_result.v1"
            or type(document["frontier"]) is not list
        ):
            raise GroundFallbackV1Error("ground fallback result schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"],
            document["decision_point_id"],
            document["route_decision_id"],
            document["selected_upper_id"],
            document["route_attempt_id"],
            document["query_id"],
            document["ground_fallback_cap_profile_id"],
            document["work_vector_id"],
            document["outcome"],
            document["search_complete"],
            tuple(
                GroundFallbackFrontierPointV1.from_dict(row)
                for row in document["frontier"]
            ),
            _parse_policy_rows(
                document["selected_policy_signature"],
                "selected policy signature",
            ),
            (
                None
                if document["selected_expected_reward"] is None
                else as_fraction(document["selected_expected_reward"])
            ),
            (
                None
                if document["selected_failure_probability"] is None
                else as_fraction(document["selected_failure_probability"])
            ),
            document["cap_exhausted_name"],
            document["composed_candidate_count"],
            document["semantic_authority"],
            document["authorizes_terminal_classification"],
            document["schema_version"],
        )
        if document["ground_fallback_result_id"] != result.ground_fallback_result_id:
            raise GroundFallbackV1Error("ground fallback result content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class GroundFallbackTrustedExecutionProvenanceV1:
    """Opaque provenance minted at a registered trusted executor boundary.

    This is deliberately not a serializable artifact and has no ``to_dict`` or
    ``from_dict`` method.  The historical in-process seam and the safe-chain
    bubblewrap worker are distinct profiles.  The latter additionally binds
    strict request, worker-output, and runtime-attestation identities.  Neither
    profile is a public-bundle proof or an official-execution claim.
    """

    execution_binding_digest: str
    constraint_delta: Fraction
    executor_profile_key: str = TRUSTED_EXECUTOR_PROFILE_KEY
    execution_scope: str = TRUSTED_EXECUTOR_SCOPE
    isolated_worker_attested: bool = False
    isolated_request_id: str | None = None
    isolated_output_id: str | None = None
    isolated_attestation_id: str | None = None
    public_bundle_proof: bool = False
    official_execution_allowed: bool = False
    _authority: object = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.execution_binding_digest, "execution_binding_digest")
        object.__setattr__(self, "constraint_delta", as_fraction(self.constraint_delta))
        if self.constraint_delta < 0 or self.constraint_delta > 1:
            raise GroundFallbackV1Error("trusted execution delta lies outside [0,1]")
        inprocess = (
            self.executor_profile_key == TRUSTED_EXECUTOR_PROFILE_KEY
            and self.execution_scope == TRUSTED_EXECUTOR_SCOPE
            and self.isolated_worker_attested is False
            and self.isolated_request_id is None
            and self.isolated_output_id is None
            and self.isolated_attestation_id is None
        )
        isolated = (
            self.executor_profile_key == ISOLATED_TRUSTED_EXECUTOR_PROFILE_KEY
            and self.execution_scope == ISOLATED_TRUSTED_EXECUTOR_SCOPE
            and self.isolated_worker_attested is True
            and all(
                isinstance(value, str)
                for value in (
                    self.isolated_request_id,
                    self.isolated_output_id,
                    self.isolated_attestation_id,
                )
            )
        )
        if isolated:
            _cid(self.isolated_request_id, "isolated_request_id")
            _cid(self.isolated_output_id, "isolated_output_id")
            _cid(self.isolated_attestation_id, "isolated_attestation_id")
        if (
            not (inprocess or isolated)
            or self.public_bundle_proof is not False
            or self.official_execution_allowed is not False
        ):
            raise GroundFallbackV1Error(
                "trusted fallback provenance overclaims its V0 execution scope"
            )
        if self._authority is not _TRUSTED_EXECUTOR_RUNTIME_AUTHORITY:
            raise GroundFallbackV1Error(
                "fallback provenance was not minted by the trusted executor"
            )


@dataclass(frozen=True, slots=True)
class GroundFallbackExecutionV1:
    """In-memory result retaining a policy and optional opaque provenance.

    The raw search primitive returns ``trusted_provenance=None``.  Only the
    authority-gated production executor seals the completed tuple.  Keeping
    the two states in one type lets the runner preserve existing native-work
    ownership without allowing a serialized ``GroundFallbackResultV1`` to
    masquerade as trusted execution provenance.
    """

    result: GroundFallbackResultV1
    work_vector: WorkVectorV1
    selected_policy: FiniteHorizonPolicy[Any, Any] | None = field(
        compare=False, repr=False
    )
    trusted_provenance: GroundFallbackTrustedExecutionProvenanceV1 | None = field(
        default=None, compare=False, repr=False
    )
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        if self.result.work_vector_id != self.work_vector.work_vector_id:
            raise GroundFallbackV1Error("fallback result/work-vector identity mismatch")
        if self.work_vector.route_kind is not RouteKindEnum.DIRECT_FALLBACK:
            raise GroundFallbackV1Error("fallback execution carries a non-fallback vector")
        if self.work_vector.subject_id != self.result.route_attempt_id:
            raise GroundFallbackV1Error("fallback WorkVector subject is not the route attempt")
        if self.result.outcome is GroundFallbackOutcome.FEASIBLE_CERTIFIED:
            if self.selected_policy is None:
                raise GroundFallbackV1Error("feasible fallback lost its policy object")
            if _policy_content_signature(self.selected_policy) != (
                self.result.selected_policy_signature
            ):
                raise GroundFallbackV1Error("selected policy/signature mismatch")
        elif self.selected_policy is not None:
            raise GroundFallbackV1Error(
                "non-feasible fallback outcome cannot carry an executable policy"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise GroundFallbackV1Error(
                    "trusted fallback execution is a copied or modified authority"
                ) from error


def require_trusted_ground_fallback_execution_authority_v1(
    execution: object,
) -> GroundFallbackExecutionV1:
    """Require the exact selected-route executor result instance."""

    if type(execution) is not GroundFallbackExecutionV1:
        raise GroundFallbackV1Error(
            "ground fallback semantic verification requires an in-memory execution"
        )
    try:
        require_runtime_authority_v1(
            execution,
            issuer=_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY,
        )
    except ValueError as error:
        raise GroundFallbackV1Error(
            "fallback execution lacks trusted runtime provenance from the "
            "retained trusted-executor instance"
        ) from error
    return execution


def _trusted_execution_binding_payload_v1(
    execution: GroundFallbackExecutionV1,
    constraint_delta: Fraction,
    *,
    executor_profile_key: str = TRUSTED_EXECUTOR_PROFILE_KEY,
    execution_scope: str = TRUSTED_EXECUTOR_SCOPE,
    isolated_worker_attested: bool = False,
    isolated_request_id: str | None = None,
    isolated_output_id: str | None = None,
    isolated_attestation_id: str | None = None,
) -> dict[str, Any]:
    """Return the exact runtime tuple covered by the opaque executor seal."""

    return {
        "schema": "acfqp.trusted_ground_fallback_execution_binding.v1",
        "executor_profile_key": executor_profile_key,
        "execution_scope": execution_scope,
        "ground_fallback_result_id": execution.result.ground_fallback_result_id,
        "work_vector_id": execution.work_vector.work_vector_id,
        "ground_fallback_cap_profile_id": (
            execution.result.ground_fallback_cap_profile_id
        ),
        "RouteDecisionContext_id": execution.result.route_decision_context_id,
        "decision_point_id": execution.result.decision_point_id,
        "route_decision_id": execution.result.route_decision_id,
        "selected_upper_id": execution.result.selected_upper_id,
        "route_attempt_id": execution.result.route_attempt_id,
        "query_id": execution.result.query_id,
        "outcome": execution.result.outcome.value,
        "selected_policy_signature": _policy_rows(
            execution.result.selected_policy_signature
        ),
        "constraint_delta": as_fraction(constraint_delta),
        "isolated_worker_attested": isolated_worker_attested,
        "isolated_request_id": isolated_request_id,
        "isolated_output_id": isolated_output_id,
        "isolated_attestation_id": isolated_attestation_id,
        "public_bundle_proof": False,
        "official_execution_allowed": False,
    }


def _trusted_execution_binding_digest_v1(
    execution: GroundFallbackExecutionV1,
    constraint_delta: Fraction,
    **profile_fields: Any,
) -> str:
    payload = (
        b"acfqp:trusted-ground-fallback-execution-binding:v1"
        + b"\x00"
        + canonical_json(
            _trusted_execution_binding_payload_v1(
                execution, constraint_delta, **profile_fields
            )
        ).encode("utf-8")
    )
    return hashlib.sha256(payload).hexdigest()


def _seal_trusted_ground_fallback_execution_v1(
    execution: GroundFallbackExecutionV1,
    *,
    constraint_delta: Fraction,
) -> GroundFallbackExecutionV1:
    """Seal a result after trusted selected-route execution.

    This private helper is intentionally called only after the production
    authorization chain and actual-vs-preexecution-bound checks have passed.
    Tests may use it to model that narrow boundary for microscopic negative
    fixtures; callers outside this trusted module must not treat it as a public
    authorization API.
    """

    if execution.trusted_provenance is not None:
        raise GroundFallbackV1Error("fallback execution is already sealed")
    delta = as_fraction(constraint_delta)
    provenance = GroundFallbackTrustedExecutionProvenanceV1(
        _trusted_execution_binding_digest_v1(execution, delta),
        delta,
        _authority=_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY,
    )
    sealed = GroundFallbackExecutionV1(
        execution.result,
        execution.work_vector,
        execution.selected_policy,
        provenance,
    )
    return bind_runtime_authority_v1(
        sealed,
        issuer=_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY,
    )


def _seal_isolated_ground_fallback_execution_v1(
    execution: GroundFallbackExecutionV1,
    *,
    constraint_delta: Fraction,
    isolated_request_id: str,
    isolated_output_id: str,
    isolated_attestation_id: str,
) -> GroundFallbackExecutionV1:
    """Seal a strictly validated bubblewrap result without host solver replay."""

    if execution.trusted_provenance is not None:
        raise GroundFallbackV1Error("fallback execution is already sealed")
    delta = as_fraction(constraint_delta)
    profile_fields = {
        "executor_profile_key": ISOLATED_TRUSTED_EXECUTOR_PROFILE_KEY,
        "execution_scope": ISOLATED_TRUSTED_EXECUTOR_SCOPE,
        "isolated_worker_attested": True,
        "isolated_request_id": _cid(isolated_request_id, "isolated_request_id"),
        "isolated_output_id": _cid(isolated_output_id, "isolated_output_id"),
        "isolated_attestation_id": _cid(
            isolated_attestation_id, "isolated_attestation_id"
        ),
    }
    provenance = GroundFallbackTrustedExecutionProvenanceV1(
        _trusted_execution_binding_digest_v1(
            execution, delta, **profile_fields
        ),
        delta,
        _authority=_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY,
        **profile_fields,
    )
    sealed = GroundFallbackExecutionV1(
        execution.result,
        execution.work_vector,
        execution.selected_policy,
        provenance,
    )
    return bind_runtime_authority_v1(
        sealed,
        issuer=_TRUSTED_EXECUTOR_RUNTIME_AUTHORITY,
    )


def verify_trusted_ground_fallback_execution_provenance_v1(
    execution: GroundFallbackExecutionV1,
) -> Fraction:
    """Verify and return the query delta bound by an opaque runtime seal.

    The check performs no ground search and therefore respects FQ10.  Exact
    frontier completeness remains a statement made by the trusted in-process
    executor, not an independently portable proof.
    """

    execution = require_trusted_ground_fallback_execution_authority_v1(
        execution
    )
    provenance = execution.trusted_provenance
    if (
        not isinstance(provenance, GroundFallbackTrustedExecutionProvenanceV1)
        or provenance._authority is not _TRUSTED_EXECUTOR_RUNTIME_AUTHORITY
    ):
        raise GroundFallbackV1Error(
            "ground fallback execution lacks trusted runtime provenance"
        )
    expected = _trusted_execution_binding_digest_v1(
        execution,
        provenance.constraint_delta,
        executor_profile_key=provenance.executor_profile_key,
        execution_scope=provenance.execution_scope,
        isolated_worker_attested=provenance.isolated_worker_attested,
        isolated_request_id=provenance.isolated_request_id,
        isolated_output_id=provenance.isolated_output_id,
        isolated_attestation_id=provenance.isolated_attestation_id,
    )
    if provenance.execution_binding_digest != expected:
        raise GroundFallbackV1Error(
            "trusted fallback provenance does not bind this result/work/policy/context"
        )
    return provenance.constraint_delta


class _CapExhausted(RuntimeError):
    def __init__(self, cap_name: str) -> None:
        super().__init__(cap_name)
        self.cap_name = cap_name


class _FallbackLedger:
    def __init__(self, cap: GroundFallbackCapProfileV1) -> None:
        self.cap = cap
        self.states_expanded = 0
        self.actions_evaluated = 0
        self.ground_steps = 0
        self.outcome_rows = 0
        self.bellman_backups = 0
        self.composed_candidates = 0
        self.cap_checks = 0
        self.cap_rejections = 0

    def _guard(self, *checks: tuple[str, int, int]) -> None:
        if self.cap_checks >= self.cap.max_solver_cap_checks:
            self.cap_rejections = 1
            raise _CapExhausted("max_cap_checks")
        self.cap_checks += 1
        for cap_name, proposed, maximum in checks:
            if proposed > maximum:
                self.cap_rejections = 1
                raise _CapExhausted(cap_name)

    def expand_state(self) -> None:
        self._guard(
            (
                "max_states_expanded",
                self.states_expanded + 1,
                self.cap.max_states_expanded,
            )
        )
        self.states_expanded += 1

    def evaluate_action(self) -> None:
        self._guard(
            (
                "max_actions_evaluated",
                self.actions_evaluated + 1,
                self.cap.max_actions_evaluated,
            )
        )
        self.actions_evaluated += 1

    def reserve_transition(self) -> None:
        self._guard(
            (
                "max_ground_steps",
                self.ground_steps + 1,
                self.cap.max_ground_steps,
            ),
            (
                "max_outcome_rows",
                self.outcome_rows + self.cap.max_positive_outcomes_per_step,
                self.cap.max_outcome_rows,
            ),
        )
        self.ground_steps += 1

    def record_outcomes(self, count: int) -> None:
        if count <= 0:
            raise GroundFallbackProtocolError(
                "ground fallback kernel returned no positive-probability outcome"
            )
        # kernel.step has already produced these rows, so a violated
        # preregistered bound must still charge the actual work before the
        # attempt closes as a protocol failure.
        self.outcome_rows += count
        if count > self.cap.max_positive_outcomes_per_step:
            raise GroundFallbackProtocolError(
                "kernel outcome count exceeded max_positive_outcomes_per_step"
            )
        # The full per-step allowance was reserved before the kernel call, so
        # this actual increment cannot cross max_outcome_rows.
        if self.outcome_rows > self.cap.max_outcome_rows:  # defensive invariant
            raise AssertionError("pre-reserved outcome cap was violated")

    def compose_candidate(self) -> None:
        self._guard(
            (
                "max_composed_candidates",
                self.composed_candidates + 1,
                self.cap.max_composed_candidates,
            ),
            (
                "max_bellman_backups",
                self.bellman_backups + 1,
                self.cap.max_bellman_backups,
            ),
        )
        self.composed_candidates += 1
        self.bellman_backups += 1


def _work_vector(
    ledger: _FallbackLedger,
    *,
    route_attempt_id: str,
    outcome: GroundFallbackOutcome,
    registry: CounterRegistryV1,
    recorder_id: str,
) -> WorkVectorV1:
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "fallback.states_expanded": ledger.states_expanded,
            "fallback.actions_evaluated": ledger.actions_evaluated,
            "fallback.ground_steps": ledger.ground_steps,
            "fallback.outcome_rows": ledger.outcome_rows,
            "fallback.bellman_backups": ledger.bellman_backups,
            "control.cap_checks": ledger.cap_checks,
            "control.cap_rejections": ledger.cap_rejections,
            "route.attempts": 1,
            "route.successes": (
                0 if outcome is GroundFallbackOutcome.CAP_EXHAUSTED else 1
            ),
            "route.failures": (
                1 if outcome is GroundFallbackOutcome.CAP_EXHAUSTED else 0
            ),
            "solver.attempts": 1,
            "solver.successes": (
                0 if outcome is GroundFallbackOutcome.CAP_EXHAUSTED else 1
            ),
            "solver.failures": (
                1 if outcome is GroundFallbackOutcome.CAP_EXHAUSTED else 0
            ),
        }
    )
    records = explicit_records_v1(
        registry,
        values,
        recorder_id=recorder_id,
    )
    return registry.materialize(
        subject_id=route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        records=records,
    )


def run_ground_fallback_search_v1(
    kernel: Any,
    query: Any,
    *,
    route_decision_context_id: str,
    decision_point_id: str,
    route_decision_id: str,
    selected_upper_id: str,
    route_attempt_id: str,
    query_id: str,
    cap_profile: GroundFallbackCapProfileV1,
    registry: CounterRegistryV1 | None = None,
    recorder_id: str = RECORDER_ID,
) -> GroundFallbackExecutionV1:
    """Run exhaustive deterministic-Markov ground search under finite caps.

    The function never emits semantic authority.  Exhaustive completion with
    no chance-constrained policy is the *only* path to
    ``INFEASIBLE_CERTIFIED``.  Any cap denial discards the partial frontier and
    returns ``CAP_EXHAUSTED``.
    """

    for field_name, value in (
        ("route_decision_context_id", route_decision_context_id),
        ("decision_point_id", decision_point_id),
        ("route_decision_id", route_decision_id),
        ("selected_upper_id", selected_upper_id),
        ("route_attempt_id", route_attempt_id),
        ("query_id", query_id),
    ):
        _cid(value, field_name)
    if type(recorder_id) is not str or not recorder_id:
        raise GroundFallbackV1Error("recorder_id must be a nonempty string")
    GroundFallbackCapProfileV1.from_dict(cap_profile.to_dict())
    trusted_registry = registry or official_counter_registry_v1()
    trusted_registry.validate_official_catalogue()
    validate_query(kernel, query)

    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    horizon = query_horizon(kernel, query)
    ledger = _FallbackLedger(cap_profile)
    Distribution = tuple[tuple[Hashable, Fraction], ...]
    memo: dict[tuple[int, Distribution], tuple[ParetoPoint, ...]] = {}
    transition_cache: dict[tuple[Hashable, Hashable], tuple[Any, ...]] = {}
    evaluated_state_actions: set[tuple[int, Hashable, Hashable]] = set()
    expanded_state_times: set[tuple[int, Hashable]] = set()
    zero = ParetoPoint(Fraction(0), Fraction(0), FiniteHorizonPolicy(()))

    def canonical_distribution(masses: Mapping[Hashable, Fraction]) -> Distribution:
        return tuple(
            sorted(
                ((state, mass) for state, mass in masses.items() if mass > 0),
                key=lambda item: repr(item[0]),
            )
        )

    def outcomes_for(
        state: Hashable, action: Hashable, remaining: int
    ) -> tuple[Any, ...]:
        action_key = (remaining, state, action)
        if action_key not in evaluated_state_actions:
            ledger.evaluate_action()
            evaluated_state_actions.add(action_key)
        transition_key = (state, action)
        cached = transition_cache.get(transition_key)
        if cached is not None:
            return cached
        ledger.reserve_transition()
        outcomes = iter_outcomes(kernel, state, action)
        ledger.record_outcomes(len(outcomes))
        transition_cache[transition_key] = outcomes
        return outcomes

    def occupancy_frontier(
        distribution: Distribution, remaining: int
    ) -> tuple[ParetoPoint, ...]:
        key = (remaining, distribution)
        if key in memo:
            return memo[key]
        if remaining <= 0 or not distribution:
            memo[key] = (zero,)
            return memo[key]

        decision_states: list[Hashable] = []
        action_sets: list[tuple[Hashable, ...]] = []
        state_mass = dict(distribution)
        for state, mass in distribution:
            if mass <= 0 or is_stopped(kernel, state, goal):
                continue
            state_time = (remaining, state)
            if state_time not in expanded_state_times:
                ledger.expand_state()
                expanded_state_times.add(state_time)
            actions = deterministic_order(kernel.actions(state))
            if actions:
                decision_states.append(state)
                action_sets.append(actions)
        if not decision_states:
            memo[key] = (zero,)
            return memo[key]

        if remaining == 1:
            partial_frontier: tuple[ParetoPoint, ...] = (zero,)
            for state, actions in zip(decision_states, action_sets):
                mass = state_mass[state]
                extended: list[ParetoPoint] = []
                for partial in partial_frontier:
                    for action in actions:
                        ledger.compose_candidate()
                        immediate_reward = Fraction(0)
                        immediate_failure = Fraction(0)
                        for branch in outcomes_for(state, action, remaining):
                            probability = mass * as_fraction(branch.probability)
                            immediate_reward += probability * outcome_reward(
                                branch, weights
                            )
                            if branch.failure:
                                immediate_failure += probability
                        mapping = partial.policy.as_dict()
                        mapping[(remaining, state)] = action
                        extended.append(
                            ParetoPoint(
                                partial.expected_reward + immediate_reward,
                                partial.failure_probability + immediate_failure,
                                FiniteHorizonPolicy.from_mapping(mapping),
                            )
                        )
                partial_frontier = pareto_prune(extended)
            memo[key] = partial_frontier
            return memo[key]

        candidates: list[ParetoPoint] = []
        for chosen_actions in product(*action_sets):
            ledger.compose_candidate()
            immediate_reward = Fraction(0)
            immediate_failure = Fraction(0)
            successor_mass: dict[Hashable, Fraction] = {}
            current_decisions: list[tuple[tuple[int, Hashable], Hashable]] = []
            for state, action in zip(decision_states, chosen_actions):
                mass = state_mass[state]
                current_decisions.append(((remaining, state), action))
                for branch in outcomes_for(state, action, remaining):
                    probability = mass * as_fraction(branch.probability)
                    immediate_reward += probability * outcome_reward(branch, weights)
                    if branch.failure:
                        immediate_failure += probability
                        continue
                    stopped = branch.terminal or is_stopped(
                        kernel, branch.next_state, goal
                    )
                    if not stopped:
                        successor_mass[branch.next_state] = (
                            successor_mass.get(branch.next_state, Fraction(0))
                            + probability
                        )
            continuation_frontier = occupancy_frontier(
                canonical_distribution(successor_mass), remaining - 1
            )
            for continuation in continuation_frontier:
                ledger.compose_candidate()
                mapping = continuation.policy.as_dict()
                conflict = False
                for decision_key, action in current_decisions:
                    incumbent = mapping.get(decision_key)
                    if incumbent is not None and incumbent != action:
                        conflict = True
                        break
                    mapping[decision_key] = action
                if conflict:
                    continue
                candidates.append(
                    ParetoPoint(
                        immediate_reward + continuation.expected_reward,
                        immediate_failure + continuation.failure_probability,
                        FiniteHorizonPolicy.from_mapping(mapping),
                    )
                )
        memo[key] = pareto_prune(candidates)
        return memo[key]

    cap_exhausted_name: str | None = None
    frontier: tuple[ParetoPoint, ...] = ()
    selected: ParetoPoint | None = None
    try:
        initial_mass: dict[Hashable, Fraction] = {}
        for probability, state in query_initial_distribution(kernel, query):
            initial_mass[state] = initial_mass.get(state, Fraction(0)) + probability
        frontier = occupancy_frontier(canonical_distribution(initial_mass), horizon)
        selected = select_constrained(frontier, as_fraction(getattr(query, "delta")))
        fallback_outcome = (
            GroundFallbackOutcome.FEASIBLE_CERTIFIED
            if selected is not None
            else GroundFallbackOutcome.INFEASIBLE_CERTIFIED
        )
    except _CapExhausted as exhausted:
        cap_exhausted_name = exhausted.cap_name
        fallback_outcome = GroundFallbackOutcome.CAP_EXHAUSTED
        # A partial search is not a frontier proof and cannot leak a candidate
        # into downstream terminal classification.
        frontier = ()
        selected = None
    except GroundFallbackProtocolError as error:
        error.partial_work_vector = _work_vector(
            ledger,
            route_attempt_id=route_attempt_id,
            # This value is used only to mark route/solver failure counters;
            # no GroundFallbackResultV1 is emitted on this exception path.
            outcome=GroundFallbackOutcome.CAP_EXHAUSTED,
            registry=trusted_registry,
            recorder_id=recorder_id,
        )
        raise

    work_vector = _work_vector(
        ledger,
        route_attempt_id=route_attempt_id,
        outcome=fallback_outcome,
        registry=trusted_registry,
        recorder_id=recorder_id,
    )
    result_frontier = tuple(
        GroundFallbackFrontierPointV1(
            point.expected_reward,
            point.failure_probability,
            _policy_content_signature(point.policy),
        )
        for point in frontier
    )
    result = GroundFallbackResultV1(
        route_decision_context_id,
        decision_point_id,
        route_decision_id,
        selected_upper_id,
        route_attempt_id,
        query_id,
        cap_profile.ground_fallback_cap_profile_id,
        work_vector.work_vector_id,
        fallback_outcome,
        fallback_outcome is not GroundFallbackOutcome.CAP_EXHAUSTED,
        result_frontier,
        _policy_content_signature(selected.policy) if selected is not None else (),
        selected.expected_reward if selected is not None else None,
        selected.failure_probability if selected is not None else None,
        cap_exhausted_name,
        ledger.composed_candidates,
    )
    return GroundFallbackExecutionV1(
        result,
        work_vector,
        selected.policy if selected is not None else None,
    )


def execute_authorized_ground_fallback_v1(
    kernel: Any,
    query: Any,
    *,
    context: Any,
    decision_point: Any,
    fallback_upper: Any,
    cardinality: Any,
    cardinality_bound: GroundFallbackCardinalityBoundV1,
    cap_profile: GroundFallbackCapProfileV1,
    route_decision_result: Any,
    fallback_upper_result: Any,
    cardinality_result: Any,
    registry: CounterRegistryV1 | None = None,
) -> GroundFallbackExecutionV1:
    """Execute only after the complete selected-fallback authority chain.

    Imports are local to avoid a module cycle.  In the partial verifier profile
    the required ROUTE_DECISION/ROUTE_UPPER/CARDINALITY roles are not yet all
    implemented, so fabricated objects and plausible attestations fail before
    any kernel access.
    """

    from acfqp.routing_v1 import (
        CardinalityEvidenceV1,
        DecisionPointV1,
        MarginalRouteDecisionV1,
        RouteDecisionContextV1,
        RouteKind,
        RouteSelection,
        RouteUpperBoundEnvelopeV1,
    )
    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        require_semantic_verification_result_v1,
    )

    verified_decision = require_semantic_verification_result_v1(
        route_decision_result, SemanticRole.ROUTE_DECISION
    )
    verified_upper = require_semantic_verification_result_v1(
        fallback_upper_result, SemanticRole.ROUTE_UPPER
    )
    verified_cardinality = require_semantic_verification_result_v1(
        cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    if verified_decision.outcome != RouteSelection.FALLBACK.value:
        raise GroundFallbackV1Error("semantic route decision did not select FALLBACK")
    if verified_upper.outcome != "VALID" or verified_cardinality.outcome != "VALID":
        raise GroundFallbackV1Error(
            "fallback upper and cardinality require VALID semantic outcomes"
        )
    if not isinstance(context, RouteDecisionContextV1):
        raise GroundFallbackV1Error("context must be RouteDecisionContextV1")
    if not isinstance(decision_point, DecisionPointV1):
        raise GroundFallbackV1Error("decision_point must be DecisionPointV1")
    if not isinstance(fallback_upper, RouteUpperBoundEnvelopeV1):
        raise GroundFallbackV1Error("fallback_upper must be RouteUpperBoundEnvelopeV1")
    if not isinstance(cardinality, CardinalityEvidenceV1):
        raise GroundFallbackV1Error("cardinality must be CardinalityEvidenceV1")
    decision = verified_decision.artifact
    if not isinstance(decision, MarginalRouteDecisionV1):
        raise GroundFallbackV1Error("route decision authority carries another artifact")
    if verified_upper.artifact != fallback_upper:
        raise GroundFallbackV1Error("route-upper authority carries another artifact")
    if verified_cardinality.artifact != cardinality:
        raise GroundFallbackV1Error("cardinality authority carries another artifact")
    if decision.selected_route is not RouteSelection.FALLBACK:
        raise GroundFallbackV1Error("route decision artifact did not select fallback")
    if decision.decision_point_id != decision_point.decision_point_id:
        raise GroundFallbackV1Error("route decision uses another decision point")
    if decision.selected_upper_id != fallback_upper.route_upper_bound_envelope_id:
        raise GroundFallbackV1Error("route decision selected another upper")
    if fallback_upper.route_kind is not RouteKind.DIRECT_FALLBACK:
        raise GroundFallbackV1Error("selected upper is not direct fallback")
    if fallback_upper.route_cap_profile_id != cap_profile.route_cap_profile_id:
        raise GroundFallbackV1Error("selected upper uses another fallback cap profile")
    fallback_upper.validate_bindings(context, decision_point, cardinality)
    cardinality_bound.validate_against_cap(cap_profile)
    if (
        cardinality_bound.route_decision_context_id
        != context.route_decision_context_id
        or cardinality_bound.decision_point_id != decision_point.decision_point_id
    ):
        raise GroundFallbackV1Error("fallback cardinality source is stale")
    if (
        cardinality_bound.ground_fallback_cardinality_bound_id
        not in cardinality.source_artifact_ids
    ):
        raise GroundFallbackV1Error(
            "CardinalityEvidenceV1 does not bind the fallback bound source"
        )
    exact_counts = dict(cardinality_bound.operational_count_values(registry))
    exact_counts["control.cap_rejections"] = (
        cardinality_bound.cap_rejection_upper(cap_profile)
    )
    if cardinality.counts != tuple(sorted(exact_counts.items())):
        raise GroundFallbackV1Error(
            "CardinalityEvidenceV1 counts differ from the bound-source projection"
        )

    execution = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=context.route_decision_context_id,
        decision_point_id=decision_point.decision_point_id,
        route_decision_id=decision.route_decision_id,
        selected_upper_id=fallback_upper.route_upper_bound_envelope_id,
        route_attempt_id=context.route_attempt_id,
        query_id=context.query_id,
        cap_profile=cap_profile,
        registry=registry,
    )
    actual = execution.work_vector.values
    # FQ4 compares actual work against the exact preregistered cardinality
    # formula clipped by this route's finite hard caps.  The source evidence
    # itself deliberately remains the unclipped complete-search cardinality.
    upper = dict(cardinality_bound.operational_upper_values(cap_profile, registry))
    exceeded = tuple(
        path
        for path in (
            "fallback.states_expanded",
            "fallback.actions_evaluated",
            "fallback.ground_steps",
            "fallback.outcome_rows",
            "fallback.bellman_backups",
            "control.cap_checks",
            "control.cap_rejections",
        )
        if actual[path] > upper[path]
    )
    if (
        execution.result.composed_candidate_count
        > min(
            dict(cardinality_bound.bounds)["fallback.composed_candidates"],
            cap_profile.max_composed_candidates,
        )
    ):
        exceeded += ("fallback.composed_candidates",)
    if exceeded:
        error = GroundFallbackProtocolError(
            "actual fallback work exceeded its pre-execution cardinality bound: "
            + ", ".join(exceeded)
        )
        error.partial_work_vector = execution.work_vector
        raise error
    # This is the only production minting point for the V0 in-process runtime
    # authority.  It is intentionally after route/cardinality/upper authority,
    # execution, and actual-bound checks.  The raw search primitive above
    # remains unsealed and cannot feed semantic terminal classification.
    return _seal_trusted_ground_fallback_execution_v1(
        execution,
        constraint_delta=as_fraction(getattr(query, "delta")),
    )


__all__ = [
    "CAP_PROFILE_KEY",
    "FALLBACK_FROZEN_BUNDLE_BYTES_CAP",
    "FALLBACK_ISOLATION_PROFILE_ID",
    "FALLBACK_MOUNTED_BYTES_UPPER",
    "FALLBACK_OUTPUT_BYTES_CAP",
    "FALLBACK_READ_BYTES_UPPER",
    "FALLBACK_REQUEST_BYTES_CAP",
    "FALLBACK_RUNTIME_SOURCE_BYTES_CAP",
    "FALLBACK_STAGED_BYTES_UPPER",
    "FALLBACK_WORKING_BYTES_CAP",
    "GroundFallbackCapProfileV1",
    "GroundFallbackCardinalityBoundV1",
    "GroundFallbackExecutionV1",
    "GroundFallbackFrontierPointV1",
    "GroundFallbackOutcome",
    "GroundFallbackProtocolError",
    "GroundFallbackRouteUpperNotIntegratedError",
    "GroundFallbackResultV1",
    "GroundFallbackTrustedExecutionProvenanceV1",
    "GroundFallbackV1Error",
    "SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_ID",
    "SAFE_CHAIN_CARDINALITY_EXTRACTION_PROFILE_KEY",
    "SEALED_ROUTE_CAP_PROFILE_KEY",
    "SafeChainFallbackCardinalitySourceV1",
    "build_ground_fallback_cardinality_evidence_v1",
    "derive_safe_chain_fallback_cardinality_bound_v1",
    "derive_safe_chain_fallback_cardinality_source_v1",
    "execute_authorized_ground_fallback_v1",
    "require_fallback_formula_binding_v1",
    "require_trusted_ground_fallback_execution_authority_v1",
    "run_ground_fallback_search_v1",
    "reconstruct_safe_chain_policy_from_signature_v1",
    "safe_chain_fallback_context_identity_v1",
    "verify_trusted_ground_fallback_execution_provenance_v1",
]
