"""Safe-chain Phase-3E causal and local-cardinality source authorities.

This module closes only the *preselection* part of the Phase-3D safe-chain
vertical slice.  It projects a verified frozen Phase-3C RAPM plus the
``SafeChainPreparedEstimateContext`` into content-addressed causal/frontier and
local-route cardinality claims.  No function in this module calls
``kernel.step``, materializes a ground slice, compiles a capability, launches a
worker, stitches a patch, or performs a post-audit.

The source and bound objects below are transport claims, not semantic
authority.  Authority is minted only by the replay handlers in
``semantic_verification_v1`` after reloading the frozen parent and recomputing
this complete registered projection.  The profile is intentionally restricted
to ``g2048_select_safe_chain_2x2_v0`` at horizon two.  Other fixtures fail
closed and the official Phase-3E execution/economics locks remain unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from acfqp.accounting_v1 import (
    CounterRegistryV1,
    official_counter_registry_v1,
)
from acfqp.artifacts import object_id
from acfqp.phase3e_ids import (
    LOCAL_CARDINALITY_BOUND_DOMAIN,
    LOCAL_PRESELECTION_EXTRACTION_PROFILE_DOMAIN,
    LOCAL_PRESELECTION_PARENT_BINDING_DOMAIN,
    LOCAL_PRESELECTION_SOURCE_DOMAIN,
    LOCAL_PROOF_OBLIGATION_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_sealed_executor_v1 import (
    RuntimeFactoryCardinalityV1,
)
from acfqp.route_upper_formula_v1 import OFFICIAL_STRUCTURAL_GUARDS
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    LOCAL_WORK_CAP_BINDINGS,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    TransactionV1,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "phase3e_safe_chain_local_preselection_v1"
TRUST_SCOPE = "PHASE3D_SAFE_CHAIN_PRESELECTION_ONLY"

LOCAL_READ_BYTES_UPPER = 1_048_576
LOCAL_STAGED_BYTES_UPPER = 1_048_576
LOCAL_OUTPUT_BYTES_UPPER = 1_048_576
LOCAL_MOUNTED_BYTES_UPPER = 2_097_152
# The producer adapter enforces this with RLIMIT_AS before worker launch and
# records ru_maxrss-derived actual usage.  It is intentionally realistic for
# the Python runtime rather than the earlier unenforceable 4 MiB placeholder.
LOCAL_WORKING_BYTES_UPPER = 268_435_456


class Phase3ELocalPreselectionV1Error(ValueError):
    """A safe-chain preselection source or projection is inadmissible."""


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3ELocalPreselectionV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _token(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise Phase3ELocalPreselectionV1Error(
            f"{field} must be a nonempty string"
        )
    return value


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise Phase3ELocalPreselectionV1Error(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise Phase3ELocalPreselectionV1Error(str(error)) from error


def _parent_id(role: str, payload: Any) -> str:
    _token(role, "parent role")
    return content_id(
        LOCAL_PRESELECTION_PARENT_BINDING_DOMAIN,
        {"role": role, "payload": payload},
    )


LOCAL_PRESELECTION_EXTRACTION_PROFILE_ID = content_id(
    LOCAL_PRESELECTION_EXTRACTION_PROFILE_DOMAIN,
    {
        "schema": "acfqp.local_preselection_extraction_profile.v1",
        "profile_key": PROFILE_KEY,
        "trust_scope": TRUST_SCOPE,
        "horizon": 2,
        "causal_evaluation_cap": 32,
        "postfreeze_protocol_checks": 6,
        "isolated_worker_process_launch_upper": 1,
        "read_bytes_upper": LOCAL_READ_BYTES_UPPER,
        "staged_bytes_upper": LOCAL_STAGED_BYTES_UPPER,
        "output_bytes_upper": LOCAL_OUTPUT_BYTES_UPPER,
        "mounted_bytes_upper": LOCAL_MOUNTED_BYTES_UPPER,
        "working_bytes_upper": LOCAL_WORKING_BYTES_UPPER,
        # These byte/peak values are preregistered execution-envelope uppers,
        # not observed actuals.  A later production adapter must install the
        # corresponding sandbox/supervisor caps before it may execute this
        # route or report the peak as enforced actual work.
        "resource_upper_enforcement_required": True,
    },
)


_SOURCE_COUNT_NAMES = tuple(
    sorted(
        (
            "ancestor_state_action_pairs",
            "authorized_state_action_pairs",
            "causal_candidate_nodes",
            "causal_evaluations",
            "cell_policy_assignments",
            "compiler_domain_assignments",
            "compiler_expanded_forms",
            "compiler_input_records",
            "form_subset_evaluations",
            "frontier_nodes",
            "frontier_positive_outcomes",
            "frontier_state_action_pairs",
            "frontier_states",
            "postaudit_positive_outcomes",
            "postaudit_state_action_pairs",
            "proof_nodes",
            "rational_bits_upper",
            "slice_actions",
            "slice_cells",
            "slice_members",
            "slice_successor_rows",
            "solver_affine_term_evaluations",
            "solver_dominance_comparisons",
            "solver_frontier_points_peak",
            "solver_policy_assignments",
            "solver_subset_evaluations",
            "source_abstract_realization_rows",
        )
    )
)


@dataclass(frozen=True, slots=True)
class SafeChainLocalPreselectionSourceV1:
    """Complete frozen source for the registered local estimate profile."""

    route_decision_context_id: str
    decision_point_id: str
    transaction_id: str
    transaction_index: int
    route_cap_profile_id: str
    frontier_snapshot_id: str
    causal_evidence_id: str
    structural_id: str
    query_id: str
    build_epoch_id: str
    parent_artifact_ids: tuple[tuple[str, str], ...]
    legacy_proof_graph_id: str
    legacy_frontier_id: str
    proof_node_ids: tuple[str, ...]
    selected_causal_node_ids: tuple[str, ...]
    causal_candidate_node_ids: tuple[str, ...]
    frontier_action_member_ids: tuple[str, ...]
    ancestor_action_member_ids: tuple[str, ...]
    source_counts: tuple[tuple[str, int], ...]
    frozen_at_protocol_step: int
    extraction_profile_id: str = LOCAL_PRESELECTION_EXTRACTION_PROFILE_ID
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id",
            "decision_point_id",
            "transaction_id",
            "route_cap_profile_id",
            "frontier_snapshot_id",
            "causal_evidence_id",
            "structural_id",
            "query_id",
            "build_epoch_id",
            "extraction_profile_id",
        ):
            _cid(getattr(self, field), field)
        if self.transaction_index not in {1, 2}:
            raise Phase3ELocalPreselectionV1Error(
                "safe-chain local transaction index must be 1 or 2"
            )
        if self.extraction_profile_id != LOCAL_PRESELECTION_EXTRACTION_PROFILE_ID:
            raise Phase3ELocalPreselectionV1Error(
                "local preselection extraction profile mismatch"
            )
        if (
            not self.parent_artifact_ids
            or tuple(sorted(self.parent_artifact_ids)) != self.parent_artifact_ids
            or len({role for role, _ in self.parent_artifact_ids})
            != len(self.parent_artifact_ids)
        ):
            raise Phase3ELocalPreselectionV1Error(
                "parent artifact bindings must be nonempty, role-unique, and sorted"
            )
        for role, artifact_id in self.parent_artifact_ids:
            _token(role, "parent role")
            _cid(artifact_id, f"parent {role}")
        for field in ("legacy_proof_graph_id", "legacy_frontier_id"):
            _token(getattr(self, field), field)
        for field in (
            "proof_node_ids",
            "selected_causal_node_ids",
            "causal_candidate_node_ids",
        ):
            values = getattr(self, field)
            if (
                not values
                or tuple(sorted(values)) != values
                or len(set(values)) != len(values)
            ):
                raise Phase3ELocalPreselectionV1Error(
                    f"{field} must be nonempty, unique, and sorted"
                )
            for value in values:
                _token(value, field)
        for field in (
            "frontier_action_member_ids",
            "ancestor_action_member_ids",
        ):
            values = getattr(self, field)
            if tuple(sorted(values)) != values or len(set(values)) != len(values):
                raise Phase3ELocalPreselectionV1Error(
                    f"{field} must be unique and sorted"
                )
            for value in values:
                _cid(value, field)
        if set(self.frontier_action_member_ids).intersection(
            self.ancestor_action_member_ids
        ):
            raise Phase3ELocalPreselectionV1Error(
                "frontier and ancestor action members overlap"
            )
        if tuple(name for name, _ in self.source_counts) != _SOURCE_COUNT_NAMES:
            raise Phase3ELocalPreselectionV1Error(
                "source counts do not contain the exact registered names"
            )
        for name, value in self.source_counts:
            _nonnegative(value, name)
        _nonnegative(self.frozen_at_protocol_step, "frozen_at_protocol_step")
        if self.measured_before_execution is not True:
            raise Phase3ELocalPreselectionV1Error(
                "local source must be frozen before route execution"
            )
        if self.depends_on_actual_route_work is not False:
            raise Phase3ELocalPreselectionV1Error(
                "local source cannot depend on post-run actuals"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3ELocalPreselectionV1Error(
                "local preselection source version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.safe_chain_local_preselection_source.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "transaction_index": self.transaction_index,
            "route_cap_profile_id": self.route_cap_profile_id,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "causal_evidence_id": self.causal_evidence_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "parent_artifact_ids": [
                {"role": role, "artifact_id": artifact_id}
                for role, artifact_id in self.parent_artifact_ids
            ],
            "legacy_proof_graph_id": self.legacy_proof_graph_id,
            "legacy_frontier_id": self.legacy_frontier_id,
            "proof_node_ids": list(self.proof_node_ids),
            "selected_causal_node_ids": list(self.selected_causal_node_ids),
            "causal_candidate_node_ids": list(self.causal_candidate_node_ids),
            "frontier_action_member_ids": list(self.frontier_action_member_ids),
            "ancestor_action_member_ids": list(self.ancestor_action_member_ids),
            "source_counts": [
                {"name": name, "value": value}
                for name, value in self.source_counts
            ],
            "frozen_at_protocol_step": self.frozen_at_protocol_step,
            "extraction_profile_id": self.extraction_profile_id,
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
        }

    @property
    def source_artifact_id(self) -> str:
        return content_id(LOCAL_PRESELECTION_SOURCE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "source_artifact_id": self.source_artifact_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SafeChainLocalPreselectionSourceV1":
        expected = {
            "schema", "schema_version", "RouteDecisionContext_id",
            "decision_point_id", "transaction_id", "transaction_index",
            "route_cap_profile_id", "frontier_snapshot_id",
            "causal_evidence_id", "structural_id", "query_id", "BuildEpoch_id",
            "parent_artifact_ids", "legacy_proof_graph_id", "legacy_frontier_id",
            "proof_node_ids", "selected_causal_node_ids",
            "causal_candidate_node_ids", "frontier_action_member_ids",
            "ancestor_action_member_ids", "source_counts",
            "frozen_at_protocol_step", "extraction_profile_id",
            "measured_before_execution", "depends_on_actual_route_work",
            "source_artifact_id",
        }
        _fields(document, expected, "safe-chain local preselection source")
        list_fields = (
            "parent_artifact_ids", "proof_node_ids", "selected_causal_node_ids",
            "causal_candidate_node_ids", "frontier_action_member_ids",
            "ancestor_action_member_ids", "source_counts",
        )
        if (
            document["schema"] != "acfqp.safe_chain_local_preselection_source.v1"
            or any(type(document[field]) is not list for field in list_fields)
        ):
            raise Phase3ELocalPreselectionV1Error(
                "safe-chain local source schema mismatch"
            )
        parents: list[tuple[str, str]] = []
        for row in document["parent_artifact_ids"]:
            _fields(row, {"role", "artifact_id"}, "local parent binding")
            parents.append((row["role"], row["artifact_id"]))
        counts: list[tuple[str, int]] = []
        for row in document["source_counts"]:
            _fields(row, {"name", "value"}, "local source count")
            counts.append((row["name"], row["value"]))
        result = cls(
            document["RouteDecisionContext_id"], document["decision_point_id"],
            document["transaction_id"], document["transaction_index"],
            document["route_cap_profile_id"], document["frontier_snapshot_id"],
            document["causal_evidence_id"], document["structural_id"],
            document["query_id"], document["BuildEpoch_id"], tuple(parents),
            document["legacy_proof_graph_id"], document["legacy_frontier_id"],
            tuple(document["proof_node_ids"]),
            tuple(document["selected_causal_node_ids"]),
            tuple(document["causal_candidate_node_ids"]),
            tuple(document["frontier_action_member_ids"]),
            tuple(document["ancestor_action_member_ids"]), tuple(counts),
            document["frozen_at_protocol_step"], document["extraction_profile_id"],
            document["measured_before_execution"],
            document["depends_on_actual_route_work"], document["schema_version"],
        )
        if document["source_artifact_id"] != result.source_artifact_id:
            raise Phase3ELocalPreselectionV1Error(
                "safe-chain local source content ID mismatch"
            )
        return result


def _required_bound_names(registry: CounterRegistryV1) -> tuple[str, ...]:
    return tuple(
        sorted(
            [leaf.path for leaf in registry.operational_leaves]
            + [name for name, _ in OFFICIAL_STRUCTURAL_GUARDS]
        )
    )


@dataclass(frozen=True, slots=True)
class SafeChainLocalCardinalityBoundV1:
    """Registered exact integer upper projection for one local transaction.

    The byte and peak entries are preregistered execution-envelope limits.  No
    producer exists in this module, and semantic cardinality replay does not
    imply that a future worker supervisor enforced those limits.  Such an
    adapter must enforce them (and record observed actuals separately) before
    selected-route execution can be admitted.
    """

    route_decision_context_id: str
    decision_point_id: str
    transaction_id: str
    transaction_index: int
    route_cap_profile_id: str
    frontier_snapshot_id: str
    causal_evidence_id: str
    bounds: tuple[tuple[str, int], ...]
    source_artifact_ids: tuple[str, ...]
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False
    authorizes_route_selection: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "route_decision_context_id", "decision_point_id", "transaction_id",
            "route_cap_profile_id", "frontier_snapshot_id", "causal_evidence_id",
        ):
            _cid(getattr(self, field), field)
        if self.transaction_index not in {1, 2}:
            raise Phase3ELocalPreselectionV1Error(
                "local cardinality transaction index must be 1 or 2"
            )
        expected = _required_bound_names(official_counter_registry_v1())
        if tuple(name for name, _ in self.bounds) != expected:
            raise Phase3ELocalPreselectionV1Error(
                "local cardinality bound omits or repeats an operational/guard leaf"
            )
        for name, value in self.bounds:
            _nonnegative(value, name)
        if (
            not self.source_artifact_ids
            or tuple(sorted(self.source_artifact_ids)) != self.source_artifact_ids
            or len(set(self.source_artifact_ids)) != len(self.source_artifact_ids)
        ):
            raise Phase3ELocalPreselectionV1Error(
                "local bound source IDs must be nonempty, unique, and sorted"
            )
        for source_id in self.source_artifact_ids:
            _cid(source_id, "local bound source")
        if (
            self.measured_before_execution is not True
            or self.depends_on_actual_route_work is not False
            or self.authorizes_route_selection is not False
        ):
            raise Phase3ELocalPreselectionV1Error(
                "raw local bound cannot depend on execution or self-authorize"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3ELocalPreselectionV1Error(
                "local cardinality bound version mismatch"
            )

    def validate_against_cap(self, cap: RouteCapProfileV1) -> None:
        parsed = RouteCapProfileV1.from_dict(cap.to_dict())
        if self.route_cap_profile_id != parsed.route_cap_profile_id:
            raise Phase3ELocalPreselectionV1Error(
                "local cardinality/cap identity mismatch"
            )
        values = dict(self.bounds)
        limits = dict(parsed.limits)
        for count_name, cap_name in OFFICIAL_STRUCTURAL_GUARDS:
            if values[count_name] > limits[cap_name]:
                raise Phase3ELocalPreselectionV1Error(
                    f"{count_name} exceeds registered {cap_name}"
                )

    def cardinality_count_values(self) -> tuple[tuple[str, int], ...]:
        """Return the canonical formula inputs, including structural guards."""

        return self.bounds

    def operational_count_values(
        self, registry: CounterRegistryV1 | None = None
    ) -> tuple[tuple[str, int], ...]:
        """Return every operational leaf before formula hard-cap minima."""

        trusted = registry or official_counter_registry_v1()
        trusted.validate_official_catalogue()
        values = dict(self.bounds)
        return tuple(
            (leaf.path, values[leaf.path]) for leaf in trusted.operational_leaves
        )

    def operational_upper_values(
        self,
        cap: RouteCapProfileV1,
        registry: CounterRegistryV1 | None = None,
    ) -> tuple[tuple[str, int], ...]:
        """Return route-formula leaf uppers after frozen hard-cap minima."""

        self.validate_against_cap(cap)
        values = dict(self.operational_count_values(registry))
        limits = dict(cap.limits)
        for path, cap_name in LOCAL_WORK_CAP_BINDINGS:
            values[path] = min(values[path], limits[cap_name])
        return tuple(sorted(values.items()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.safe_chain_local_cardinality_bound.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "transaction_index": self.transaction_index,
            "route_cap_profile_id": self.route_cap_profile_id,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "causal_evidence_id": self.causal_evidence_id,
            "bounds": [
                {"name": name, "value": value} for name, value in self.bounds
            ],
            "source_artifact_ids": list(self.source_artifact_ids),
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
            "authorizes_route_selection": False,
        }

    @property
    def local_cardinality_bound_id(self) -> str:
        return content_id(LOCAL_CARDINALITY_BOUND_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "local_cardinality_bound_id": self.local_cardinality_bound_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "SafeChainLocalCardinalityBoundV1":
        expected = {
            "schema", "schema_version", "RouteDecisionContext_id",
            "decision_point_id", "transaction_id", "transaction_index",
            "route_cap_profile_id", "frontier_snapshot_id", "causal_evidence_id",
            "bounds", "source_artifact_ids", "measured_before_execution",
            "depends_on_actual_route_work", "authorizes_route_selection",
            "local_cardinality_bound_id",
        }
        _fields(document, expected, "safe-chain local cardinality bound")
        if (
            document["schema"] != "acfqp.safe_chain_local_cardinality_bound.v1"
            or type(document["bounds"]) is not list
            or type(document["source_artifact_ids"]) is not list
        ):
            raise Phase3ELocalPreselectionV1Error(
                "safe-chain local cardinality-bound schema mismatch"
            )
        bounds: list[tuple[str, int]] = []
        for row in document["bounds"]:
            _fields(row, {"name", "value"}, "local cardinality-bound row")
            bounds.append((row["name"], row["value"]))
        result = cls(
            document["RouteDecisionContext_id"], document["decision_point_id"],
            document["transaction_id"], document["transaction_index"],
            document["route_cap_profile_id"], document["frontier_snapshot_id"],
            document["causal_evidence_id"], tuple(bounds),
            tuple(document["source_artifact_ids"]),
            document["measured_before_execution"],
            document["depends_on_actual_route_work"],
            document["authorizes_route_selection"], document["schema_version"],
        )
        if document["local_cardinality_bound_id"] != result.local_cardinality_bound_id:
            raise Phase3ELocalPreselectionV1Error(
                "safe-chain local cardinality-bound content ID mismatch"
            )
        return result


def _require_prepared(prepared: Any) -> Any:
    from acfqp.frozen_phase3c import FrozenPhase3CWorld
    from acfqp.general_local_recovery import CausalSearchStatus
    from acfqp.phase3d import SafeChainPreparedEstimateContext

    if not isinstance(prepared, SafeChainPreparedEstimateContext):
        raise Phase3ELocalPreselectionV1Error(
            "local source requires SafeChainPreparedEstimateContext"
        )
    if not isinstance(prepared.world, FrozenPhase3CWorld):
        raise Phase3ELocalPreselectionV1Error(
            "local source requires a frozen Phase-3C parent"
        )
    if (
        prepared.world.binding_counters.get("kernel_step_calls") != 0
        or prepared.world.binding_counters.get("transition_closure_calls") != 0
    ):
        raise Phase3ELocalPreselectionV1Error(
            "frozen parent preparation used ground transitions"
        )
    causal = prepared.causal_search
    if (
        causal.status is not CausalSearchStatus.CAUSAL_FAMILY_FOUND
        or causal.search_complete is not True
        or causal.evaluation_cap != 32
        or causal.evaluation_count != 4
        or causal.selected_node_ids is None
        or len(causal.selected_node_ids) != 1
    ):
        raise Phase3ELocalPreselectionV1Error(
            "prepared source is outside the registered safe-chain FOUND profile"
        )
    if (
        prepared.world.queries[1].query_key
        != "g2048.safe_chain.h2.delta05.local_recovery"
        or int(prepared.query.horizon) != 2
    ):
        raise Phase3ELocalPreselectionV1Error(
            "local preselection profile is registered only for safe-chain H=2"
        )
    return prepared


def safe_chain_local_context_identity_v1(world: Any) -> dict[str, str]:
    """Use the same frozen structural/query/BuildEpoch identity as fallback."""

    from acfqp.phase3e_fallback_v1 import safe_chain_fallback_context_identity_v1

    return safe_chain_fallback_context_identity_v1(world)


def safe_chain_local_selected_plan_id_v1(prepared: Any) -> str:
    """Bind the RouteDecisionContext to the exact failed portable plan."""

    prepared = _require_prepared(prepared)
    return _parent_id(
        "selected_failed_portable_plan",
        {
            "proposal_source": prepared.proposal_source,
            "proposal": prepared.proposal.to_dict(),
        },
    )


def safe_chain_local_threshold_profile_id_v1(prepared: Any) -> str:
    """Replay the portable-threshold identity consumed by local post-audit."""

    prepared = _require_prepared(prepared)
    from acfqp.phase3e_local_semantics_v1 import FrozenThresholdProfileV1

    audit = prepared.pre_audit
    identities = safe_chain_local_context_identity_v1(prepared.world)
    return FrozenThresholdProfileV1(
        identities["query_id"],
        audit.regret_tolerance,
        audit.risk_tolerance,
    ).threshold_profile_id


def _failed_risk_obligation_id(context: RouteDecisionContextV1, prepared: Any) -> str:
    audit = prepared.pre_audit
    return content_id(
        LOCAL_PROOF_OBLIGATION_DOMAIN,
        {
            "schema": "acfqp.local_proof_obligation.v1",
            "RouteDecisionContext_id": context.route_decision_context_id,
            "selected_plan_id": context.selected_plan_id,
            "threshold_profile_id": context.threshold_profile_id,
            "channel": "failure_upper",
            "observed_upper": audit.lifted_failure_upper,
            "required_ceiling": audit.risk_tolerance,
            "failed": True,
        },
    )


def derive_safe_chain_local_frontier_and_causal_v1(
    *,
    prepared: Any,
    context: RouteDecisionContextV1,
    cap_profile: RouteCapProfileV1,
    frontier_stage: int,
) -> tuple[FrontierSnapshotV1, CausalEvidenceV1]:
    """Derive the safe-chain FOUND causal claim without route execution."""

    prepared = _require_prepared(prepared)
    RouteDecisionContextV1.from_dict(context.to_dict())
    RouteCapProfileV1.from_dict(cap_profile.to_dict())
    identities = safe_chain_local_context_identity_v1(prepared.world)
    for field in ("structural_id", "query_id", "build_epoch_id"):
        if getattr(context, field) != identities[field]:
            raise Phase3ELocalPreselectionV1Error(
                f"local context/{field} does not bind the frozen parent"
            )
    if context.selected_plan_id != safe_chain_local_selected_plan_id_v1(prepared):
        raise Phase3ELocalPreselectionV1Error(
            "local context selected_plan_id does not bind the failed portable plan"
        )
    if (
        context.threshold_profile_id
        != safe_chain_local_threshold_profile_id_v1(prepared)
    ):
        raise Phase3ELocalPreselectionV1Error(
            "local context threshold_profile_id does not bind the audit tolerances"
        )
    if frontier_stage not in {1, 2}:
        raise Phase3ELocalPreselectionV1Error(
            "frontier_stage must equal the local transaction index"
        )
    obligation_ids = (_failed_risk_obligation_id(context, prepared),)
    frontier = FrontierSnapshotV1(
        context.route_decision_context_id, frontier_stage, obligation_ids
    )
    causal = CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        prepared.causal_search.evaluation_count,
        cap_profile.route_cap_profile_id,
        obligation_ids,
    )
    return frontier, causal


def _action_member_ids(pairs: tuple[tuple[Any, Any], ...], scope: str) -> tuple[str, ...]:
    values = tuple(
        sorted(
            _parent_id(
                f"{scope}_state_action_member",
                {
                    "state_source_id": object_id(state, "state"),
                    "action_source_id": object_id(action, "ground-action"),
                },
            )
            for state, action in pairs
        )
    )
    if len(set(values)) != len(values):
        raise Phase3ELocalPreselectionV1Error(
            f"{scope} action catalogue contains duplicate members"
        )
    return values


def _source_counts(prepared: Any) -> tuple[tuple[str, int], ...]:
    authorization = prepared.authorization
    causal = prepared.causal_search
    frontier_states = {state for state, _ in authorization.frontier_state_actions}
    values = {
        "ancestor_state_action_pairs": len(
            authorization.reverse_dependency_state_actions
        ),
        "authorized_state_action_pairs": len(authorization.allowed_state_actions),
        "causal_candidate_nodes": len(causal.candidate_node_ids),
        "causal_evaluations": causal.evaluation_count,
        "cell_policy_assignments": 2 ** len(frontier_states),
        "compiler_domain_assignments": 3,
        "compiler_expanded_forms": 7,
        "compiler_input_records": 49,
        "form_subset_evaluations": 4,
        "frontier_nodes": len(prepared.frontier.nodes),
        "frontier_positive_outcomes": 4
        * len(authorization.frontier_state_actions),
        "frontier_state_action_pairs": len(
            authorization.frontier_state_actions
        ),
        "frontier_states": len(frontier_states),
        "postaudit_positive_outcomes": 4
        * len(authorization.reverse_dependency_state_actions),
        "postaudit_state_action_pairs": len(
            authorization.reverse_dependency_state_actions
        ),
        "proof_nodes": len(prepared.proof_graph.nodes),
        "rational_bits_upper": 32,
        "slice_actions": len(authorization.frontier_state_actions),
        "slice_cells": len(prepared.frontier.nodes),
        "slice_members": len(frontier_states),
        "slice_successor_rows": 0,
        "solver_affine_term_evaluations": 257,
        "solver_dominance_comparisons": 255,
        "solver_frontier_points_peak": 1,
        "solver_policy_assignments": 257,
        "solver_subset_evaluations": 2,
        "source_abstract_realization_rows": 20,
    }
    expected = {
        "ancestor_state_action_pairs": 8,
        "authorized_state_action_pairs": 24,
        "causal_candidate_nodes": 2,
        "causal_evaluations": 4,
        "cell_policy_assignments": 256,
        "compiler_domain_assignments": 3,
        "compiler_expanded_forms": 7,
        "compiler_input_records": 49,
        "form_subset_evaluations": 4,
        "frontier_nodes": 1,
        "frontier_positive_outcomes": 64,
        "frontier_state_action_pairs": 16,
        "frontier_states": 8,
        "postaudit_positive_outcomes": 32,
        "postaudit_state_action_pairs": 8,
        "proof_nodes": 4,
        "rational_bits_upper": 32,
        "slice_actions": 16,
        "slice_cells": 1,
        "slice_members": 8,
        "slice_successor_rows": 0,
        "solver_affine_term_evaluations": 257,
        "solver_dominance_comparisons": 255,
        "solver_frontier_points_peak": 1,
        "solver_policy_assignments": 257,
        "solver_subset_evaluations": 2,
        "source_abstract_realization_rows": 20,
    }
    if values != expected:
        raise Phase3ELocalPreselectionV1Error(
            f"safe-chain preselection cardinality golden changed: {values!r}"
        )
    return tuple((name, values[name]) for name in _SOURCE_COUNT_NAMES)


def derive_safe_chain_local_preselection_source_v1(
    *,
    prepared: Any,
    context: RouteDecisionContextV1,
    frontier: FrontierSnapshotV1,
    causal: CausalEvidenceV1,
    decision_point: DecisionPointV1,
    transaction: TransactionV1,
    cap_profile: RouteCapProfileV1,
    frozen_at_protocol_step: int,
) -> SafeChainLocalPreselectionSourceV1:
    """Freeze all registered local cardinality parents before route choice."""

    prepared = _require_prepared(prepared)
    expected_frontier, expected_causal = derive_safe_chain_local_frontier_and_causal_v1(
        prepared=prepared,
        context=context,
        cap_profile=cap_profile,
        frontier_stage=transaction.transaction_index,
    )
    if frontier != expected_frontier or causal != expected_causal:
        raise Phase3ELocalPreselectionV1Error(
            "frontier/causal claim differs from registered safe-chain replay"
        )
    if (
        decision_point.route_decision_context_id
        != context.route_decision_context_id
        or decision_point.transaction_index != transaction.transaction_index
        or decision_point.frontier_snapshot_id != frontier.frontier_snapshot_id
        or decision_point.causal_evidence_id != causal.causal_evidence_id
        or transaction.logical_occurrence_id != context.logical_occurrence_id
        or transaction.route_attempt_id != context.route_attempt_id
        or transaction.decision_point_id != decision_point.decision_point_id
        or transaction.frontier_snapshot_id != frontier.frontier_snapshot_id
        or transaction.route_cap_profile_id != cap_profile.route_cap_profile_id
    ):
        raise Phase3ELocalPreselectionV1Error(
            "local source context/decision/transaction identity chain is stale"
        )
    identities = safe_chain_local_context_identity_v1(prepared.world)
    parents = tuple(
        sorted(
            (
                ("bound_ground_action_catalogue", identities["bound_ground_action_catalogue_id"]),
                ("build_epoch", identities["build_epoch_id"]),
                ("local_pre_recovery", _parent_id("local_pre_recovery", prepared.world.local_pre_recovery_document)),
                ("manifest", identities["manifest_id"]),
                ("portable_rapm", identities["portable_rapm_id"]),
                ("source_authorization", _parent_id("source_authorization", prepared.source_phase3c_authorization)),
                ("source_locality", _parent_id("source_locality", prepared.source_phase3c_locality)),
            )
        )
    )
    authorization = prepared.authorization
    return SafeChainLocalPreselectionSourceV1(
        context.route_decision_context_id,
        decision_point.decision_point_id,
        transaction.transaction_id,
        transaction.transaction_index,
        cap_profile.route_cap_profile_id,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        context.structural_id,
        context.query_id,
        context.build_epoch_id,
        parents,
        prepared.proof_graph.graph_id,
        prepared.frontier.frontier_id,
        tuple(sorted(node.node_id for node in prepared.proof_graph.nodes)),
        tuple(sorted(prepared.causal_search.selected_node_ids or ())),
        tuple(sorted(prepared.causal_search.candidate_node_ids)),
        _action_member_ids(authorization.frontier_state_actions, "frontier"),
        _action_member_ids(
            authorization.reverse_dependency_state_actions, "ancestor"
        ),
        _source_counts(prepared),
        frozen_at_protocol_step,
    )


def derive_safe_chain_local_cardinality_bound_v1(
    *,
    source: SafeChainLocalPreselectionSourceV1,
    cap_profile: RouteCapProfileV1,
    registry: CounterRegistryV1 | None = None,
    runtime_factory_cardinality: RuntimeFactoryCardinalityV1 | None = None,
) -> SafeChainLocalCardinalityBoundV1:
    """Apply the registered safe-chain integer upper formula."""

    parsed = SafeChainLocalPreselectionSourceV1.from_dict(source.to_dict())
    cap = RouteCapProfileV1.from_dict(cap_profile.to_dict())
    if parsed.route_cap_profile_id != cap.route_cap_profile_id:
        raise Phase3ELocalPreselectionV1Error(
            "local source/cap identity mismatch"
        )
    trusted = registry or official_counter_registry_v1()
    trusted.validate_official_catalogue()
    source_counts = dict(parsed.source_counts)
    values = {leaf.path: 0 for leaf in trusted.operational_leaves}
    values.update(
        {
            # These six checks are the post-freeze verification suffix: four
            # runner integrity/projection/aggregation/upper checks plus the
            # independent local-result and post-audit semantic authorities. The
            # causal/cardinality/upper/decision work already incurred while
            # preparing the decision remains in common_prefix_work.
            "common.protocol_checks": 6,
            # Every registered safe-chain cardinality is strictly below its
            # official hard cap, so this successful route upper has no cap
            # rejection.  A smaller/new cap profile needs a separately
            # registered source formula rather than reserving a false event.
            "control.cap_rejections": 0,
            "io.read_bytes": LOCAL_READ_BYTES_UPPER,
            "io.staged_bytes": LOCAL_STAGED_BYTES_UPPER,
            "io.output_bytes": LOCAL_OUTPUT_BYTES_UPPER,
            "io.mounted_bytes_peak": LOCAL_MOUNTED_BYTES_UPPER,
            "memory.working_bytes_peak": LOCAL_WORKING_BYTES_UPPER,
            "process.launches": 1,
            "local.causal_candidate_evaluations": 0,
            "local.materialization_ground_steps": source_counts[
                "frontier_state_action_pairs"
            ],
            "local.materialization_outcome_rows": source_counts[
                "frontier_positive_outcomes"
            ],
            "local.compiler_input_records": source_counts[
                "compiler_input_records"
            ],
            "local.compiler_expanded_forms": source_counts[
                "compiler_expanded_forms"
            ],
            "local.compiler_domain_assignments": source_counts[
                "compiler_domain_assignments"
            ],
            "local.solver_subset_evaluations": source_counts[
                "solver_subset_evaluations"
            ],
            "local.solver_policy_assignments": source_counts[
                "solver_policy_assignments"
            ],
            "local.solver_frontier_points": source_counts[
                "solver_frontier_points_peak"
            ],
            "local.solver_dominance_comparisons": source_counts[
                "solver_dominance_comparisons"
            ],
            "local.solver_affine_term_evaluations": source_counts[
                "solver_affine_term_evaluations"
            ],
            "local.postaudit_ground_steps": source_counts[
                "postaudit_state_action_pairs"
            ],
            "local.postaudit_outcome_rows": source_counts[
                "postaudit_positive_outcomes"
            ],
        }
    )
    runtime_source_id: str | None = None
    runtime_values: dict[str, int] = {}
    if runtime_factory_cardinality is not None:
        parsed_runtime = RuntimeFactoryCardinalityV1.from_dict(
            runtime_factory_cardinality.to_dict()
        )
        runtime_source_id = parsed_runtime.runtime_factory_cardinality_id
        runtime_values = dict(parsed_runtime.upper_values())
        # Sealed/two-stage execution additionally verifies the merged route
        # WorkVector.  Historical unsealed bounds retain their exact V0 value.
        values["common.integrity_checks"] += 1
        # The CAS lease is a separate physical copy.  Add its exact manifest-
        # bound traffic once; peaks follow their registered SUM/MAX semantics.
        for path in (
            "common.hash_invocations",
            "common.integrity_checks",
            "common.protocol_checks",
            "io.read_bytes",
            "io.staged_bytes",
            "io.output_bytes",
        ):
            values[path] += runtime_values[path]
        values["io.mounted_bytes_peak"] += runtime_values[
            "io.mounted_bytes_peak"
        ]
        values["memory.working_bytes_peak"] += runtime_values[
            "memory.working_bytes_peak"
        ]
    structural = {
        "structural.cell_policy_assignments": source_counts[
            "cell_policy_assignments"
        ],
        "structural.form_subset_evaluations": source_counts[
            "form_subset_evaluations"
        ],
        "structural.rational_bits": source_counts["rational_bits_upper"],
        "structural.slice_actions": source_counts["slice_actions"],
        "structural.slice_cells": source_counts["slice_cells"],
        "structural.slice_members": source_counts["slice_members"],
    }
    cap_checked_paths = (
        "local.materialization_ground_steps",
        "local.materialization_outcome_rows",
        "local.compiler_input_records",
        "local.compiler_expanded_forms",
        "local.compiler_domain_assignments",
        "local.solver_subset_evaluations",
        "local.solver_policy_assignments",
        "local.solver_frontier_points",
        "local.solver_dominance_comparisons",
        "local.solver_affine_term_evaluations",
        "local.postaudit_ground_steps",
        "local.postaudit_outcome_rows",
    )
    values["control.cap_checks"] = (
        sum(values[path] for path in cap_checked_paths)
        + len(structural)
        + runtime_values.get("control.cap_checks", 0)
    )
    all_bounds = tuple(sorted({**values, **structural}.items()))
    result = SafeChainLocalCardinalityBoundV1(
        parsed.route_decision_context_id,
        parsed.decision_point_id,
        parsed.transaction_id,
        parsed.transaction_index,
        parsed.route_cap_profile_id,
        parsed.frontier_snapshot_id,
        parsed.causal_evidence_id,
        all_bounds,
        tuple(
            sorted(
                (parsed.source_artifact_id,)
                + ((runtime_source_id,) if runtime_source_id is not None else ())
            )
        ),
    )
    result.validate_against_cap(cap)
    return result


def build_safe_chain_local_cardinality_evidence_v1(
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    transaction: TransactionV1,
    cap_profile: RouteCapProfileV1,
    bound: SafeChainLocalCardinalityBoundV1,
) -> CardinalityEvidenceV1:
    """Adapt the registered bound to generic route-upper input transport."""

    bound.validate_against_cap(cap_profile)
    if (
        bound.route_decision_context_id != context.route_decision_context_id
        or bound.decision_point_id != decision_point.decision_point_id
        or bound.transaction_id != transaction.transaction_id
        or bound.transaction_index != transaction.transaction_index
        or bound.frontier_snapshot_id != transaction.frontier_snapshot_id
        or bound.causal_evidence_id != decision_point.causal_evidence_id
    ):
        raise Phase3ELocalPreselectionV1Error(
            "local cardinality bound is stale for this transaction"
        )
    sources = tuple(
        sorted(
            set(bound.source_artifact_ids) | {bound.local_cardinality_bound_id}
        )
    )
    return CardinalityEvidenceV1(
        context.route_decision_context_id,
        RouteKind.LOCAL_ATTEMPT,
        cap_profile.route_cap_profile_id,
        transaction.frontier_snapshot_id,
        bound.bounds,
        sources,
    )


__all__ = [
    "LOCAL_PRESELECTION_EXTRACTION_PROFILE_ID",
    "LOCAL_MOUNTED_BYTES_UPPER",
    "LOCAL_OUTPUT_BYTES_UPPER",
    "LOCAL_READ_BYTES_UPPER",
    "LOCAL_STAGED_BYTES_UPPER",
    "LOCAL_WORKING_BYTES_UPPER",
    "PROFILE_KEY",
    "Phase3ELocalPreselectionV1Error",
    "SafeChainLocalCardinalityBoundV1",
    "SafeChainLocalPreselectionSourceV1",
    "build_safe_chain_local_cardinality_evidence_v1",
    "derive_safe_chain_local_cardinality_bound_v1",
    "derive_safe_chain_local_frontier_and_causal_v1",
    "derive_safe_chain_local_preselection_source_v1",
    "safe_chain_local_context_identity_v1",
    "safe_chain_local_selected_plan_id_v1",
    "safe_chain_local_threshold_profile_id_v1",
]
