"""Complete construction cleanup plans for the anchored H1 lifecycle.

The module closes a structural gap left by the first-failure dispatcher.  It
rebuilds every declared candidate first-failure branch from the caller-pinned
transition table, including two candidates unreachable through the construction
dispatcher, adds the ten emitted mount-open overruns that the old table omitted,
and derives an ordered best-effort registered-resource cleanup continuation for
each row in that analysis universe.  It does not cover admitted work lost before
a dispatch event is appended or arbitrary runtime interleavings.

The artifacts are deliberately construction-only.  A cleanup plan is not a
cleanup execution, the current attempt gate has no cleanup-only capability,
and the production output context has not yet selected one of the registered
serializer leaves.  Consequently this module issues neither terminal status
nor accounting or route authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import copy
import hmac
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as output_join_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_LIFECYCLE_CLEANUP_PASS_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_COMPLETE_BRANCH_ANALYSIS_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-D"
PROFILE_KEY = "construction_k7_h1_lifecycle_complete_cleanup_v1"

COMPLETE_DECLARED_BRANCH_CLEANUP_PLANS_PRESENT = True
COMPLETE_REGISTERED_BRANCH_RESOURCE_CLEANUP_PLANS_PRESENT = True
CLEANUP_EXECUTION_AUTHORITY_PRESENT = False
OUTPUT_TERMINAL_CONTEXT_JOIN_COMPLETE = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
FORMAL_COUNTER_RECORD_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

COMPLETE_BRANCH_ANALYSIS_DOMAIN = (
    CONSTRUCTION_K7_H1_LIFECYCLE_COMPLETE_BRANCH_ANALYSIS_V1_DOMAIN
)
CLEANUP_PASS_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_CLEANUP_PASS_V1_DOMAIN
_DOMAINS = (COMPLETE_BRANCH_ANALYSIS_DOMAIN, CLEANUP_PASS_DOMAIN)
if len(set(_DOMAINS)) != len(_DOMAINS) or not set(_DOMAINS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("H1 complete-cleanup domains are not registered")

_TYPED_FULL_SUCCESS = {"kind": "NOT_APPLICABLE", "reason": "FULL_SUCCESS"}
_TYPED_NO_FAILURE = {"kind": "NOT_APPLICABLE", "reason": "NO_FAILURE"}
_OUTPUT_ROLES = (
    "BUSINESS_RESULT",
    "OPERATIONAL_TRACE",
    "TERMINAL_ARTIFACT",
    "COUNTER_RECORD_SET",
    "WORK_VECTOR",
    "COMPARISON_VECTOR",
    "ACTUAL_PROJECTION_PROOF",
    "OUTPUT_MANIFEST",
)
_SUPPLEMENTAL_OUTCOME = dispatch_v1.ANCHOR_GRAMMAR_VIOLATION_AFTER_ADMISSION
_ANALYSIS_ISSUER = object()
_PASS_ISSUER = object()


class ConstructionK7H1LifecycleCompleteCleanupV1Error(ValueError):
    """Complete branch or cleanup-plan verification failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1LifecycleCompleteCleanupV1Error(message)


def _cid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _resource_path(row: Mapping[str, Any]) -> str | None:
    path = row["resource_path"]
    if type(path) is dict:
        return None
    if type(path) is not str or path not in dispatch_v1.SHARED_RESOURCE_PATHS:
        _fail("anchored transition contains an invalid shared-resource path")
    return path


def _resource_prefix_documents(
    transitions: tuple[dict[str, Any], ...],
    index: int,
    current: Mapping[str, Any] | None,
    edge: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    completed = transitions[:index]
    completed_keys = {row["site_key"] for row in completed}
    attempted_keys = set(completed_keys)
    if current is not None:
        attempted_keys.add(current["site_key"])
    admitted_keys = {
        row["site_key"] for row in completed if row["reservation_edge"] is True
    }
    if current is not None and edge is not None and edge["current_site_admitted"]:
        admitted_keys.add(current["site_key"])
    result: list[dict[str, Any]] = []
    for path in dispatch_v1.SHARED_RESOURCE_PATHS:
        universe = [
            row["site_key"] for row in transitions if _resource_path(row) == path
        ]
        result.append(
            {
                "path": path,
                "attempted_site_prefix": [
                    key for key in universe if key in attempted_keys
                ],
                "admitted_site_prefix": [key for key in universe if key in admitted_keys],
                "completed_site_prefix": [
                    key for key in universe if key in completed_keys
                ],
                "unreached_site_keys": [
                    key for key in universe if key not in attempted_keys
                ],
                "partition_scope": "DECLARATIVE_CANDIDATE_TABLE_ONLY",
                "production_source_multiplicity_bound": False,
                "missing_as_zero_allowed": False,
                "wildcard_allowed": False,
            }
        )
    return result


def _declared_branch_documents(
    transitions: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = []
    for index, transition in enumerate(transitions):
        successful = [row["site_key"] for row in transitions[:index]]
        for edge in transition["failure_edges"]:
            branches.append(
                {
                    "branch_key": (
                        f"FAIL:{transition['site_key']}:{edge['outcome']}"
                    ),
                    "branch_kind": "FIRST_FAILURE_PREFIX",
                    "first_failure_outcome": edge["outcome"],
                    "failed_site_key": transition["site_key"],
                    "failed_edge": edge,
                    "successful_site_prefix": successful,
                    "attempted_site_prefix": [
                        *successful,
                        transition["site_key"],
                    ],
                    "resource_prefixes": _resource_prefix_documents(
                        transitions, index, transition, edge
                    ),
                    "prefix_derived_from_transition_table": True,
                    "attempt_closure_issued": False,
                    "terminal_classification_issued": False,
                }
            )
    all_keys = [row["site_key"] for row in transitions]
    branches.append(
        {
            "branch_key": "SUCCESS:COMPLETE_LIFECYCLE",
            "branch_kind": "FULL_SUCCESS",
            "first_failure_outcome": dict(_TYPED_FULL_SUCCESS),
            "failed_site_key": dict(_TYPED_FULL_SUCCESS),
            "failed_edge": dict(_TYPED_FULL_SUCCESS),
            "successful_site_prefix": all_keys,
            "attempted_site_prefix": all_keys,
            "resource_prefixes": _resource_prefix_documents(
                transitions, len(transitions), None, None
            ),
            "prefix_derived_from_transition_table": True,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
        }
    )
    return branches


def _replay_declared_analysis_id(
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
) -> str:
    branches = _declared_branch_documents(bundle.program.transitions)
    payload = {
        "schema": "acfqp.h1_production_lifecycle_branch_analysis.v1",
        "schema_version": "1.0.0",
        "h1_production_lifecycle_program_id": bundle.program.program_id,
        "branch_count": len(branches),
        "branch_count_formula": "ONE_PLUS_SUM_FAILURE_EDGES_OVER_TRANSITIONS",
        "branches": branches,
        "first_failure_prefixes_complete_for_declared_candidate_edges": True,
        "production_failure_edge_completeness_claimed": False,
        "shared_path_partitions_relative_to_candidate_table_only": True,
        "post_failure_cleanup_continuation_program_bound": False,
        "complete_attempt_branches_issued": False,
        "live_runtime_branch_completeness_claimed": False,
    }
    replayed = content_id(
        CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN,
        payload,
    )
    if not hmac.compare_digest(replayed, bundle.program.branch_analysis_id):
        _fail("declared branch analysis did not replay the pinned identity")
    return replayed


def _initial_frontier() -> dict[str, Any]:
    return {
        "memory_reservation_state": "NONE",
        "memory_native_state": "NOT_STARTED_BY_CONSTRUCTION_DISPATCH",
        "output_reservation_state": "NONE",
        "output_native_state": "NOT_STARTED_BY_CONSTRUCTION_DISPATCH",
        "output_owner_state": "NOT_STARTED_BY_CONSTRUCTION_DISPATCH",
        "known_descendant_roles": [],
        "ambiguous_descendant_roles": [],
        "active_mount_open_sites": [],
        "ambiguous_mount_sites": [],
        "completed_output_readback_callback_roles": [],
        "ambiguous_output_readback_callback_roles": [],
        "ambiguous_native_or_callback_sites": [],
    }


def _output_role(row: Mapping[str, Any]) -> str:
    site = row["site_key"]
    prefix = "readback:output-role:"
    if type(site) is not str or not site.startswith(prefix):
        _fail("output readback site has an invalid role encoding")
    role = site[len(prefix) :]
    if role not in _OUTPUT_ROLES:
        _fail("output readback site used an unregistered role")
    return role


def _apply_success(frontier: dict[str, Any], row: Mapping[str, Any]) -> None:
    operation = row["operation"]
    site = row["site_key"]
    if operation == "MEMORY_BIND":
        frontier["memory_reservation_state"] = "ACTIVE"
    elif operation == "OUTPUT_RESERVE":
        frontier["output_reservation_state"] = "ACTIVE"
    elif operation == "MOUNT_OPEN":
        frontier["active_mount_open_sites"].append(site)
    elif operation == "LAUNCH_CHILD":
        frontier["known_descendant_roles"].append(site.split(":", 1)[1])
    elif operation == "DESCENDANT_REAP":
        frontier["known_descendant_roles"] = []
        frontier["ambiguous_descendant_roles"] = []
    elif operation == "SAME_OFD_PEAK_READ":
        frontier["memory_reservation_state"] = "SETTLED"
    elif operation == "MOUNT_CLOSE":
        open_site = site.replace("mount-close:", "mount-open:", 1)
        if not frontier["active_mount_open_sites"] or (
            frontier["active_mount_open_sites"][-1] != open_site
        ):
            _fail("anchored mount-close success is not strict LIFO")
        frontier["active_mount_open_sites"].pop()
    elif operation == "OUTPUT_ROLE_READBACK":
        frontier["completed_output_readback_callback_roles"].append(
            _output_role(row)
        )
    elif operation == "OUTPUT_FINALIZE":
        frontier["output_reservation_state"] = "SETTLED"
    elif operation == "OUTPUT_CLOSE":
        frontier["output_owner_state"] = "CONTROL_CALLBACK_COMPLETED"


def _failure_frontier(
    transitions: tuple[dict[str, Any], ...],
    index: int,
    edge: Mapping[str, Any],
    *,
    supplemental: bool,
) -> dict[str, Any]:
    frontier = _initial_frontier()
    for completed in transitions[:index]:
        _apply_success(frontier, completed)
    row = transitions[index]
    operation = row["operation"]
    outcome = _SUPPLEMENTAL_OUTCOME if supplemental else edge["outcome"]
    native = edge["native_existence"]
    if supplemental:
        frontier["active_mount_open_sites"].append(row["site_key"])
    elif operation == "MEMORY_BIND" and edge["current_site_admitted"]:
        frontier["memory_reservation_state"] = "AMBIGUOUS"
        frontier["memory_native_state"] = "UNREACHABLE_DECLARED_AMBIGUITY"
        frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
    elif operation == "MOUNT_OPEN" and native == "AMBIGUOUS":
        frontier["ambiguous_mount_sites"].append(row["site_key"])
        frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
    elif operation == "LAUNCH_CHILD" and native == "AMBIGUOUS":
        role = row["site_key"].split(":", 1)[1]
        frontier["ambiguous_descendant_roles"].append(role)
        frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
    elif operation == "DESCENDANT_REAP":
        for role in frontier["known_descendant_roles"]:
            site = f"reap-state:{role}"
            if site not in frontier["ambiguous_native_or_callback_sites"]:
                frontier["ambiguous_native_or_callback_sites"].append(site)
    elif operation == "SAME_OFD_PEAK_READ":
        # The 59C deferred-completion handler always settles the retained
        # reservation, including callback failure and observed overrun.
        frontier["memory_reservation_state"] = "SETTLED"
    elif operation == "MOUNT_CLOSE":
        open_site = row["site_key"].replace("mount-close:", "mount-open:", 1)
        if open_site in frontier["active_mount_open_sites"]:
            frontier["active_mount_open_sites"].remove(open_site)
        frontier["ambiguous_mount_sites"].append(open_site)
        frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
    elif operation == "OUTPUT_ROLE_READBACK":
        role = _output_role(row)
        if outcome == "CALLBACK_FAILED_AFTER_ADMISSION":
            frontier["ambiguous_output_readback_callback_roles"].append(role)
            frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
        elif outcome == "OBSERVED_UPPER_BOUND_VIOLATION":
            frontier["completed_output_readback_callback_roles"].append(role)
    elif operation == "OUTPUT_FINALIZE":
        if outcome in {
            "CALLBACK_FAILED_AFTER_ADMISSION",
            "OBSERVED_UPPER_BOUND_VIOLATION",
        }:
            frontier["output_reservation_state"] = "SETTLED"
        else:
            frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
    elif operation == "OUTPUT_CLOSE":
        frontier["ambiguous_native_or_callback_sites"].append(row["site_key"])
    return frontier


def _action(
    ordinal: int,
    kind: str,
    target: str,
    *,
    condition: str = "REQUIRED",
) -> dict[str, Any]:
    return {
        "cleanup_ordinal": ordinal,
        "action_kind": kind,
        "target": target,
        "condition": condition,
        "primary_failure_preserved": True,
        "secondary_failure_is_append_only": True,
        "continue_with_later_safe_cleanup_after_secondary_failure": True,
        "new_business_work_allowed": False,
        "normal_route_reservation_allowed": False,
        "execution_authority_present": False,
    }


def _cleanup_actions(frontier: Mapping[str, Any], *, full_success: bool) -> list[dict[str, Any]]:
    if full_success:
        return []
    actions: list[dict[str, Any]] = []

    def add(kind: str, target: str, condition: str = "REQUIRED") -> None:
        actions.append(_action(len(actions) + 1, kind, target, condition=condition))

    for site in frontier["ambiguous_native_or_callback_sites"]:
        add("RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION", site)
    active_descendants = set(frontier["known_descendant_roles"]) | set(
        frontier["ambiguous_descendant_roles"]
    )
    for role in ("BUSINESS", "WORKER"):
        if role in active_descendants:
            add(
                "REAP_DESCENDANT",
                role,
                "KNOWN_PRESENT_OR_RESOLVED_PRESENT",
            )
    if frontier["memory_reservation_state"] in {"ACTIVE", "AMBIGUOUS"}:
        if frontier["memory_native_state"] == "KNOWN_PRESENT":
            add(
                "READ_SAME_OFD_PEAK_AND_SETTLE_MEMORY_RESERVATION",
                "memory:bind-working-hierarchy",
                "NATIVE_MEMORY_PRESENT",
            )
        else:
            add(
                "SETTLE_MEMORY_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_READ",
                "memory:bind-working-hierarchy",
                "ACCOUNTING_RESERVATION_PRESENT",
            )
    mount_universe = list(frontier["active_mount_open_sites"])
    for site in frontier["ambiguous_mount_sites"]:
        if site not in mount_universe:
            mount_universe.append(site)
    for site in reversed(mount_universe):
        add("CLOSE_MOUNT", site, "OPEN_OR_RESOLVED_OPEN")
    if frontier["output_native_state"] in {"OPEN", "AMBIGUOUS"}:
        completed = set(frontier["completed_output_readback_callback_roles"])
        ambiguous = set(frontier["ambiguous_output_readback_callback_roles"])
        for role in _OUTPUT_ROLES:
            if role not in completed:
                add(
                    "READBACK_OUTPUT_ROLE",
                    role,
                    (
                        "RESOLVE_COMMIT_THEN_READ_IF_SELECTED_PRESENT"
                        if role in ambiguous
                        else "READ_IF_SELECTED_OUTPUT_LEAF_PRESENT"
                    ),
                )
        if frontier["output_reservation_state"] in {"ACTIVE", "AMBIGUOUS"}:
            add(
                "FINALIZE_AND_SETTLE_OUTPUT_RESERVATION",
                "output:reserve-route-wide",
                "RESERVATION_PRESENT_OR_RESOLVED_PRESENT",
            )
        add("CLOSE_OUTPUT_OWNER", "output:close-owner", "OPEN_OR_RESOLVED_OPEN")
    elif frontier["output_reservation_state"] in {"ACTIVE", "AMBIGUOUS"}:
        add(
            "SETTLE_OUTPUT_RESERVATION_CONSERVATIVELY_WITHOUT_NATIVE_FINALIZE",
            "output:reserve-route-wide",
            "ACCOUNTING_RESERVATION_PRESENT",
        )
    return actions


def _dispatcher_outcome_reachable(row: Mapping[str, Any], outcome: str) -> bool:
    if row["site_key"] == "memory:bind-working-hierarchy" and outcome == (
        "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
    ):
        return False
    if row["site_key"] == "output:finalize-route-wide" and outcome == "PROTOCOL_FAILED":
        return False
    return True


def _complete_branch_documents(
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
) -> list[dict[str, Any]]:
    transitions = bundle.program.transitions
    branches: list[dict[str, Any]] = []
    supplemental_sites: list[str] = []
    for index, row in enumerate(transitions):
        successful = [item["site_key"] for item in transitions[:index]]
        for edge in row["failure_edges"]:
            frontier = _failure_frontier(
                transitions, index, edge, supplemental=False
            )
            outcome = edge["outcome"]
            branches.append(
                {
                    "branch_key": f"FAIL:{row['site_key']}:{outcome}",
                    "branch_kind": "DECLARED_FIRST_FAILURE",
                    "failed_ordinal": row["ordinal"],
                    "failed_site_key": row["site_key"],
                    "first_failure_outcome": outcome,
                    "failed_edge": edge,
                    "successful_site_prefix": successful,
                    "attempted_site_prefix": [*successful, row["site_key"]],
                    "dispatcher_outcome_reachable": _dispatcher_outcome_reachable(
                        row, outcome
                    ),
                    "cleanup_frontier": frontier,
                    "cleanup_actions": _cleanup_actions(frontier, full_success=False),
                    "registered_resource_cleanup_plan_complete": True,
                    "cleanup_execution_authority_present": False,
                    "attempt_closure_issued": False,
                    "terminal_classification_issued": False,
                }
            )
        declared = {edge["outcome"] for edge in row["failure_edges"]}
        if row["operation"] == "MOUNT_OPEN" and (
            "OBSERVED_UPPER_BOUND_VIOLATION" not in declared
        ):
            supplemental_sites.append(row["site_key"])
            synthetic = {
                "outcome": _SUPPLEMENTAL_OUTCOME,
                "current_site_admitted": True,
                "side_effect_may_have_started": True,
                "native_existence": "KNOWN_PRESENT_AFTER_CALLBACK",
                "provisional_primary_cause_class": "PROTOCOL_FAILURE",
                "provisional_primary_cause_code": (
                    "ANCHORED_FAILURE_GRAMMAR_MISSING_OBSERVED_OVERRUN"
                ),
                "attempt_closure_issued": False,
                "terminal_classification_issued": False,
                "certificate_issued": False,
                "infeasibility_certified": False,
            }
            frontier = _failure_frontier(
                transitions, index, synthetic, supplemental=True
            )
            branches.append(
                {
                    "branch_key": (
                        f"SUPPLEMENTAL:{row['site_key']}:{_SUPPLEMENTAL_OUTCOME}"
                    ),
                    "branch_kind": "SUPPLEMENTAL_DISPATCH_PROTOCOL_ABORT",
                    "failed_ordinal": row["ordinal"],
                    "failed_site_key": row["site_key"],
                    "first_failure_outcome": _SUPPLEMENTAL_OUTCOME,
                    "failed_edge": synthetic,
                    "successful_site_prefix": successful,
                    "attempted_site_prefix": [*successful, row["site_key"]],
                    "dispatcher_outcome_reachable": True,
                    "cleanup_frontier": frontier,
                    "cleanup_actions": _cleanup_actions(frontier, full_success=False),
                    "registered_resource_cleanup_plan_complete": True,
                    "cleanup_execution_authority_present": False,
                    "attempt_closure_issued": False,
                    "terminal_classification_issued": False,
                }
            )
    all_sites = [row["site_key"] for row in transitions]
    branches.append(
        {
            "branch_key": "SUCCESS:COMPLETE_LIFECYCLE",
            "branch_kind": "FULL_SUCCESS",
            "failed_ordinal": dict(_TYPED_FULL_SUCCESS),
            "failed_site_key": dict(_TYPED_FULL_SUCCESS),
            "first_failure_outcome": dict(_TYPED_FULL_SUCCESS),
            "failed_edge": dict(_TYPED_FULL_SUCCESS),
            "successful_site_prefix": all_sites,
            "attempted_site_prefix": all_sites,
            "dispatcher_outcome_reachable": True,
            "cleanup_frontier": _initial_frontier()
            | {
                "memory_reservation_state": "SETTLED",
                "output_reservation_state": "SETTLED",
                "output_owner_state": "CONTROL_CALLBACK_COMPLETED",
                "completed_output_readback_callback_roles": list(_OUTPUT_ROLES),
            },
            "cleanup_actions": [],
            "registered_resource_cleanup_plan_complete": True,
            "cleanup_execution_authority_present": False,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
        }
    )
    if (
        len(supplemental_sites) != 10
        or len(branches) != 154
        or len({row["branch_key"] for row in branches}) != 154
    ):
        _fail("registered cleanup analysis branch cardinality changed")
    return branches


@dataclass(frozen=True, slots=True)
class H1LifecycleCompleteBranchAnalysisV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _analysis_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ANALYSIS_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("complete branch analysis is caller-minted")
        try:
            payload = loads_canonical_json(self.payload_bytes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1LifecycleCompleteCleanupV1Error(
                "complete branch analysis is not canonical JSON"
            ) from error
        if type(payload) is not dict:
            _fail("complete branch analysis must be one object")
        object.__setattr__(
            self,
            "_analysis_id",
            content_id(COMPLETE_BRANCH_ANALYSIS_DOMAIN, payload),
        )

    @property
    def analysis_id(self) -> str:
        return self._analysis_id

    @property
    def payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self.payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("complete branch analysis changed type")
        return value

    @property
    def branches(self) -> tuple[dict[str, Any], ...]:
        return tuple(copy.deepcopy(row) for row in self.payload["branches"])

    @property
    def by_key(self) -> dict[str, dict[str, Any]]:
        return {row["branch_key"]: row for row in self.branches}

    def to_document(self) -> dict[str, Any]:
        return {
            **self.payload,
            "h1_lifecycle_complete_branch_analysis_id": self.analysis_id,
        }


def derive_h1_lifecycle_complete_branch_analysis_v1(
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    output_join: output_join_v1.H1LifecycleOutputLeafJoinV1,
) -> H1LifecycleCompleteBranchAnalysisV1:
    if (
        type(bundle) is not dispatch_v1.H1AnchoredLifecycleDispatchBundleV1
        or type(output_join) is not output_join_v1.H1LifecycleOutputLeafJoinV1
        or output_join.anchored_program_id != bundle.program.anchored_program_id
        or output_join.handler_registry_id != bundle.registry.registry_id
        or output_join.output_branch_dag_id != bundle.program.output_branch_dag_id
    ):
        _fail("complete branch analysis requires one exact anchored output join")
    replayed_declared = _replay_declared_analysis_id(bundle)
    branches = _complete_branch_documents(bundle)
    outcome_counts: dict[str, int] = {}
    for branch in branches:
        outcome = branch["first_failure_outcome"]
        if type(outcome) is str:
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    unreachable = [
        row["branch_key"]
        for row in branches
        if row["dispatcher_outcome_reachable"] is False
    ]
    payload = {
        "schema": "acfqp.k7_h1_lifecycle_complete_branch_analysis.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_lifecycle_local_main_anchor_id": bundle.program.anchor_id,
        "h1_caller_pinned_lifecycle_provenance_id": bundle.program.provenance_id,
        "lifecycle_program_snapshot_id": bundle.program.snapshot_id,
        "lifecycle_program_id": bundle.program.program_id,
        "replayed_declared_lifecycle_branch_analysis_id": replayed_declared,
        "h1_anchored_lifecycle_program_id": bundle.program.anchored_program_id,
        "h1_anchored_lifecycle_handler_registry_id": bundle.registry.registry_id,
        "h1_production_output_branch_dag_id": bundle.program.output_branch_dag_id,
        "h1_lifecycle_output_leaf_join_id": output_join.join_id,
        "declared_transition_count": 62,
        "declared_failure_edge_count": 143,
        "declared_branch_count_including_success": 144,
        "supplemental_dispatch_protocol_abort_count": 10,
        "registered_analysis_branch_count_including_success": len(branches),
        "first_failure_outcome_counts": outcome_counts,
        "dispatcher_unreachable_declared_branch_keys": unreachable,
        "dispatcher_unreachable_declared_branch_count": len(unreachable),
        "branches": branches,
        "cleanup_order": [
            "RESOLVE_NATIVE_EXISTENCE_OR_CALLBACK_COMPLETION",
            "REAP_DESCENDANTS_BUSINESS_THEN_WORKER",
            "SETTLE_RETAINED_MEMORY_ACCOUNTING_RESERVATION",
            "CLOSE_MOUNTS_LIFO",
            "SETTLE_RETAINED_OUTPUT_ACCOUNTING_RESERVATION",
        ],
        "future_live_native_output_cleanup_order_bound": False,
        "all_declared_candidate_edges_replayed": True,
        "all_registered_supplemental_overrun_events_included": True,
        "complete_registered_branch_resource_cleanup_plans_present": True,
        "primary_failure_is_immutable": True,
        "cleanup_failures_are_ordered_secondary_causes": True,
        "safe_cleanup_continues_after_secondary_failure": True,
        "cleanup_plan_is_cleanup_execution": False,
        "cleanup_execution_authority_present": False,
        "cleanup_only_attempt_gate_capability_present": False,
        "owner_journal_prefix_extension_verifier_required": True,
        "prefix_verification_attestation_issued": False,
        "output_role_presence_join_bound": True,
        "output_terminal_context_join_complete": False,
        "production_output_leaf_authority_present": False,
        "production_source_branch_completeness_claimed": False,
        "live_runtime_branch_completeness_claimed": False,
        "all_interleaving_branch_completeness_claimed": False,
        "post_admission_no_event_recovery_complete": False,
        "conditional_absent_output_role_skip_dispatch_semantics_present": False,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "formal_counter_record_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "production_execution_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
    }
    return H1LifecycleCompleteBranchAnalysisV1(
        _ANALYSIS_ISSUER, canonical_json_bytes(payload)
    )


def verify_h1_lifecycle_complete_branch_analysis_bytes_v1(
    raw: bytes,
    *,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    output_join: output_join_v1.H1LifecycleOutputLeafJoinV1,
) -> H1LifecycleCompleteBranchAnalysisV1:
    expected = derive_h1_lifecycle_complete_branch_analysis_v1(bundle, output_join)
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleCompleteCleanupV1Error(
            "complete branch analysis bytes are not canonical"
        ) from error
    if type(document) is not dict:
        _fail("complete branch analysis document must be one object")
    claimed = _cid(
        document.pop("h1_lifecycle_complete_branch_analysis_id", None),
        "complete branch analysis",
    )
    if (
        content_id(COMPLETE_BRANCH_ANALYSIS_DOMAIN, document) != claimed
        or not hmac.compare_digest(claimed, expected.analysis_id)
        or not hmac.compare_digest(
            canonical_json_bytes(document), expected.payload_bytes
        )
    ):
        _fail("complete branch analysis differs from exact reconstruction")
    return expected


@dataclass(frozen=True, slots=True)
class H1LifecycleCleanupPassV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _pass_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PASS_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("cleanup pass is caller-minted")
        payload = loads_canonical_json(self.payload_bytes)
        if type(payload) is not dict:
            _fail("cleanup pass payload must be one object")
        object.__setattr__(self, "_pass_id", content_id(CLEANUP_PASS_DOMAIN, payload))

    @property
    def pass_id(self) -> str:
        return self._pass_id

    @property
    def payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self.payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("cleanup pass changed type")
        return value

    def to_document(self) -> dict[str, Any]:
        return {**self.payload, "h1_lifecycle_cleanup_pass_id": self.pass_id}


def bind_h1_lifecycle_cleanup_pass_v1(
    analysis: H1LifecycleCompleteBranchAnalysisV1,
    *,
    branch_key: str,
) -> H1LifecycleCleanupPassV1:
    if type(analysis) is not H1LifecycleCompleteBranchAnalysisV1:
        _fail("cleanup pass requires one issuer-owned complete analysis")
    if type(branch_key) is not str or branch_key not in analysis.by_key:
        _fail("cleanup pass branch key is absent from complete analysis")
    branch = analysis.by_key[branch_key]
    payload = {
        "schema": "acfqp.k7_h1_lifecycle_cleanup_pass.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_lifecycle_complete_branch_analysis_id": analysis.analysis_id,
        "h1_lifecycle_dispatch_trace_id": _typed_null(
            "STATIC_BRANCH_PLAN_WITHOUT_RUNTIME_TRACE_BINDING"
        ),
        "branch_key": branch_key,
        "primary_failure_outcome": branch["first_failure_outcome"],
        "cleanup_frontier": branch["cleanup_frontier"],
        "planned_cleanup_actions": branch["cleanup_actions"],
        "planned_cleanup_action_count": len(branch["cleanup_actions"]),
        "cleanup_plan_complete": False,
        "registered_resource_cleanup_plan_complete": branch[
            "registered_resource_cleanup_plan_complete"
        ],
        "execution_status": "NOT_RUN",
        "executed_cleanup_events": [],
        "secondary_failures": [],
        "unresolved_obligations": [],
        "cleanup_pass_complete": False,
        "cleanup_execution_authority_present": False,
        "runtime_trace_bound": False,
        "prefix_verification_attestation_issued": False,
        "cleanup_only_attempt_gate_capability_present": False,
        "output_terminal_context_join_complete": False,
        "production_output_leaf_authority_present": False,
        "primary_failure_preserved": True,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "formal_counter_record_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_v7_route_authority_present": False,
        "production_execution_authority_present": False,
        "official_execution_allowed": False,
    }
    return H1LifecycleCleanupPassV1(_PASS_ISSUER, canonical_json_bytes(payload))


def verify_h1_lifecycle_cleanup_pass_bytes_v1(
    raw: bytes,
    *,
    analysis: H1LifecycleCompleteBranchAnalysisV1,
) -> H1LifecycleCleanupPassV1:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleCompleteCleanupV1Error(
            "cleanup pass bytes are not canonical"
        ) from error
    if type(document) is not dict:
        _fail("cleanup pass document must be one object")
    claimed = _cid(
        document.pop("h1_lifecycle_cleanup_pass_id", None), "cleanup pass"
    )
    expected = bind_h1_lifecycle_cleanup_pass_v1(
        analysis,
        branch_key=document.get("branch_key"),
    )
    if (
        content_id(CLEANUP_PASS_DOMAIN, document) != claimed
        or not hmac.compare_digest(claimed, expected.pass_id)
        or not hmac.compare_digest(canonical_json_bytes(document), expected.payload_bytes)
    ):
        _fail("cleanup pass differs from exact reconstruction")
    return expected


def _cleanup_branch_key_for_verified_dispatch_trace_v1(
    trace: dispatch_v1.H1LifecycleDispatchTraceV1,
) -> str:
    if type(trace) is not dispatch_v1.H1LifecycleDispatchTraceV1:
        _fail("cleanup selection requires one verified dispatch trace")
    document = trace.to_document()
    events = document["consumed_events"]
    if not events or all(row["outcome"] == "SUCCESS" for row in events):
        if len(events) == 62:
            return "SUCCESS:COMPLETE_LIFECYCLE"
        _fail("a successful partial prefix has no cleanup-triggering failure")
    failure = events[-1]
    if failure["outcome"] == _SUPPLEMENTAL_OUTCOME:
        return (
            f"SUPPLEMENTAL:{failure['site_key']}:{_SUPPLEMENTAL_OUTCOME}"
        )
    return f"FAIL:{failure['site_key']}:{failure['outcome']}"


def select_h1_lifecycle_cleanup_pass_for_dispatch_trace_bytes_v1(
    analysis: H1LifecycleCompleteBranchAnalysisV1,
    trace_bytes: bytes,
    *,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
    profile: dispatch_v1.H1LifecycleDispatchProfileV1,
    owner: Any,
) -> H1LifecycleCleanupPassV1:
    """Synchronously verify one prefix and select a nonauthorizing static plan."""

    if type(analysis) is not H1LifecycleCompleteBranchAnalysisV1:
        _fail("trace selection requires one issuer-owned complete analysis")
    analysis_document = analysis.payload
    if (
        analysis_document["h1_anchored_lifecycle_program_id"]
        != bundle.program.anchored_program_id
        or analysis_document["h1_anchored_lifecycle_handler_registry_id"]
        != bundle.registry.registry_id
    ):
        _fail("cleanup analysis crossed the verified trace program")
    trace = dispatch_v1.verify_h1_lifecycle_dispatch_trace_prefix_bytes_v1(
        trace_bytes,
        bundle=bundle,
        profile=profile,
        owner=owner,
    )
    branch_key = _cleanup_branch_key_for_verified_dispatch_trace_v1(trace)
    if branch_key not in analysis.by_key:
        _fail("verified dispatch outcome is absent from the cleanup analysis")
    return bind_h1_lifecycle_cleanup_pass_v1(analysis, branch_key=branch_key)


__all__ = (
    "CLEANUP_EXECUTION_AUTHORITY_PRESENT",
    "CLEANUP_PASS_DOMAIN",
    "COMPLETE_BRANCH_ANALYSIS_DOMAIN",
    "COMPLETE_DECLARED_BRANCH_CLEANUP_PLANS_PRESENT",
    "COMPLETE_REGISTERED_BRANCH_RESOURCE_CLEANUP_PLANS_PRESENT",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1LifecycleCompleteCleanupV1Error",
    "FORMAL_COMPARISON_VECTOR_ISSUED",
    "FORMAL_COUNTER_RECORD_ISSUED",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORMAL_WORK_VECTOR_ISSUED",
    "H1LifecycleCleanupPassV1",
    "H1LifecycleCompleteBranchAnalysisV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OUTPUT_TERMINAL_CONTEXT_JOIN_COMPLETE",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "bind_h1_lifecycle_cleanup_pass_v1",
    "derive_h1_lifecycle_complete_branch_analysis_v1",
    "select_h1_lifecycle_cleanup_pass_for_dispatch_trace_bytes_v1",
    "verify_h1_lifecycle_cleanup_pass_bytes_v1",
    "verify_h1_lifecycle_complete_branch_analysis_bytes_v1",
)
