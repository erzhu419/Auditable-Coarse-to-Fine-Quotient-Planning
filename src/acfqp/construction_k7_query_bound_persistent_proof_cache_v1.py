"""Persist and consume one source-bound H=2 RAPM proof cache.

The build path binds the exact proof-dependency transition to the reusable
RAPM snapshot and its registered source-bundle binding.  The online path
performs structural, content-addressed replay of both graphs and typed replay
of the numerical models, but deliberately does not invoke the exact planner.
All forty-one target proof nodes are therefore reusable on a fresh occurrence
whose query identity is outside the frozen dependency closure.

An evaluation-only no-reuse control reruns the exact planner and requires its
proof bytes to equal the cached proof.  The operational cache result remains a
failed-certificate result: it authorizes only the next query-local recovery
request and performs no ground access itself.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_rapm_proof_dependency_dag_v1 as dag_v1
from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_v1 as snapshot_v1
from acfqp import construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 as binding_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_CONSUMPTION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_NO_REUSE_CONTROL_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_QUERY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.109"
PROFILE_KEY = "construction_k7_query_bound_persistent_proof_cache_v1"

CACHE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_V1_DOMAIN
QUERY_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_QUERY_V1_DOMAIN
CONSUMPTION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_CONSUMPTION_V1_DOMAIN
)
NO_REUSE_CONTROL_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_NO_REUSE_CONTROL_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {CACHE_DOMAIN, QUERY_DOMAIN, CONSUMPTION_DOMAIN, NO_REUSE_CONTROL_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound persistent proof-cache domains are not central")

_CACHE_ISSUER = object()
_QUERY_ISSUER = object()
_CONSUMPTION_ISSUER = object()
_CONTROL_ISSUER = object()

_PLANNING_DOMAINS = {
    "behavior": "acfqp:v075-batch-planning-row-behavior:v2",
    "cell": "acfqp:v075-batch-planning-quotient-cell:v2",
    "quotient": "acfqp:v075-batch-planning-behavioral-quotient:v2",
    "frontier": "acfqp:v075-batch-planning-failed-frontier:v2",
    "proof": "acfqp:v075-batch-planning-numerical-proof:v2",
}


class ConstructionK7QueryBoundPersistentProofCacheV1Error(ValueError):
    """The cache identity, proof structure, or query isolation changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundPersistentProofCacheV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundPersistentProofCacheV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7QueryBoundPersistentProofCacheV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"{label} has missing or unknown fields")
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _same_document(left: Any, right: Any) -> bool:
    """Compare JSON documents by their canonical encoding, not container shape."""

    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _planning_id(role: str, payload: dict[str, Any]) -> str:
    try:
        domain = _PLANNING_DOMAINS[role]
    except KeyError as error:  # pragma: no cover
        raise ConstructionK7QueryBoundPersistentProofCacheV1Error(
            "unknown planning identity role"
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _without(document: dict[str, Any], *fields: str) -> dict[str, Any]:
    result = dict(document)
    for field_name in fields:
        try:
            result.pop(field_name)
        except KeyError as error:
            raise ConstructionK7QueryBoundPersistentProofCacheV1Error(
                f"required expansion {field_name} is absent"
            ) from error
    return result


def _verify_quotient_structure(
    quotient: Any,
    *,
    model: planning_v2.V075NumericalModelV2,
) -> str:
    quotient = _exact_keys(
        quotient,
        {
            "schema",
            "schema_version",
            "numerical_model_id",
            "row_behavior_bindings",
            "cell_ids",
            "compiler",
            "fixed_uniform_distinct_action_concretizer",
            "known_automorphism_used",
            "human_partition_used",
            "prior_or_proposal_access",
            "row_behaviors",
            "cells",
            "quotient_id",
        },
        "cached behavioral quotient",
    )
    if quotient["numerical_model_id"] != model.model_id:
        _fail("cached quotient crossed its numerical model")
    row_ids = {item.row_id for item in model.rows}
    bindings = []
    behavior_ids = set()
    behaviors = quotient["row_behaviors"]
    if type(behaviors) is not list or len(behaviors) != len(row_ids):
        _fail("cached quotient behavior inventory changed")
    for behavior in behaviors:
        behavior = _exact_keys(
            behavior,
            {
                "schema",
                "schema_version",
                "remaining_horizon",
                "terms",
                "selected_policy_other_rule",
                "interval_simplex_retained",
                "row_id",
                "behavior_key",
            },
            "cached row behavior",
        )
        payload = _without(behavior, "row_id", "behavior_key")
        behavior_key = _planning_id("behavior", payload)
        if (
            behavior["behavior_key"] != behavior_key
            or behavior["row_id"] not in row_ids
            or behavior["row_id"] in behavior_ids
        ):
            _fail("cached row behavior identity changed")
        behavior_ids.add(behavior["row_id"])
        bindings.append(
            {"row_id": behavior["row_id"], "behavior_key": behavior_key}
        )
    if quotient["row_behavior_bindings"] != bindings:
        _fail("cached quotient behavior bindings changed")
    cell_ids = []
    cells = quotient["cells"]
    if type(cells) is not list or not cells:
        _fail("cached quotient cell inventory changed")
    for cell in cells:
        cell = _exact_keys(
            cell,
            {
                "schema",
                "schema_version",
                "remaining_horizon",
                "state_ids",
                "behavior_keys",
                "partition_basis",
                "cell_id",
            },
            "cached quotient cell",
        )
        cell_id = _planning_id("cell", _without(cell, "cell_id"))
        if cell["cell_id"] != cell_id:
            _fail("cached quotient cell identity changed")
        cell_ids.append(cell_id)
    if quotient["cell_ids"] != cell_ids:
        _fail("cached quotient cell bindings changed")
    quotient_id = _planning_id(
        "quotient",
        _without(quotient, "row_behaviors", "cells", "quotient_id"),
    )
    if quotient["quotient_id"] != quotient_id:
        _fail("cached behavioral quotient identity changed")
    return quotient_id


def _verify_frontier_structure(
    frontier: Any,
    *,
    model_id: str,
) -> str:
    frontier = _exact_keys(
        frontier,
        {
            "schema",
            "schema_version",
            "numerical_model_id",
            "reason",
            "obligations",
            "prior_rank_present",
            "infeasibility_certificate",
            "plan_certificate",
            "frontier_id",
        },
        "cached failed frontier",
    )
    if (
        frontier["numerical_model_id"] != model_id
        or frontier["reason"] != "RISK_BOUND_FAILED"
        or frontier["prior_rank_present"] is not False
        or frontier["infeasibility_certificate"] is not False
        or frontier["plan_certificate"] is not False
        or type(frontier["obligations"]) is not list
        or not frontier["obligations"]
    ):
        _fail("cached failed frontier semantics changed")
    for obligation in frontier["obligations"]:
        _exact_keys(
            obligation,
            {
                "row_id",
                "interval_width_sum",
                "other_upper",
                "unmaterialized_successor_ids",
                "current_validation_draw_count",
                "next_registered_checkpoint",
            },
            "cached frontier obligation",
        )
        _cid(obligation["row_id"], "cached frontier row")
    frontier_id = _planning_id(
        "frontier",
        _without(frontier, "frontier_id"),
    )
    if frontier["frontier_id"] != frontier_id:
        _fail("cached failed frontier identity changed")
    return frontier_id


def _verify_proof_structure(
    proof: Any,
    *,
    model_document: dict[str, Any],
) -> tuple[planning_v2.V075NumericalModelV2, str, str, str]:
    proof = _exact_keys(
        proof,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "numerical_model_id",
            "route",
            "quotient_id",
            "outcome",
            "policy_id",
            "envelope_id",
            "failed_frontier_id",
            "policy_assignments_evaluated",
            "search_cap",
            "arm_field_present",
            "proposal_field_present",
            "source_provenance_field_present",
            "occurrence_field_present",
            "private_law_access",
            "plan_certificate",
            "infeasibility_certificate",
            "model",
            "quotient",
            "policy",
            "envelope",
            "failed_frontier",
            "proof_id",
        },
        "cached numerical proof",
    )
    model_bytes = canonical_json_bytes(model_document)
    model = planning_v2.replay_v075_numerical_model_bytes_v2(model_bytes)
    if proof["model"] != model_document or proof["numerical_model_id"] != model.model_id:
        _fail("cached proof crossed its numerical model")
    if (
        proof["route"] != "ADAPTIVE_QUOTIENT"
        or proof["outcome"] != "FAILED_PROOF_FRONTIER"
        or proof["policy"] is not None
        or proof["policy_id"] is not None
        or proof["envelope"] is not None
        or proof["envelope_id"] is not None
        or proof["arm_field_present"] is not False
        or proof["proposal_field_present"] is not False
        or proof["source_provenance_field_present"] is not False
        or proof["occurrence_field_present"] is not False
        or proof["private_law_access"] is not False
        or proof["plan_certificate"] is not False
        or proof["infeasibility_certificate"] is not False
    ):
        _fail("cached numerical proof claim boundary changed")
    quotient_id = _verify_quotient_structure(proof["quotient"], model=model)
    frontier_id = _verify_frontier_structure(
        proof["failed_frontier"],
        model_id=model.model_id,
    )
    if (
        proof["quotient_id"] != quotient_id
        or proof["failed_frontier_id"] != frontier_id
    ):
        _fail("cached proof expansion crossed its identity payload")
    proof_id = _planning_id(
        "proof",
        _without(
            proof,
            "model",
            "quotient",
            "policy",
            "envelope",
            "failed_frontier",
            "proof_id",
        ),
    )
    if proof["proof_id"] != proof_id:
        _fail("cached numerical proof identity changed")
    return model, proof_id, quotient_id, frontier_id


def _verify_graph_structure(
    graph: Any,
) -> tuple[
    planning_v2.V075NumericalModelV2,
    dict[str, Any],
    str,
    str,
    str,
    dict[str, dict[str, Any]],
]:
    graph = _exact_keys(
        graph,
        {
            "schema",
            "schema_version",
            "profile_key",
            "numerical_model_id",
            "numerical_proof_id",
            "behavioral_quotient_id",
            "failed_frontier_id",
            "node_ids",
            "node_role_keys",
            "node_count",
            "query_identity_is_dependency",
            "threshold_profile_is_dependency",
            "exact_h2_dependency_structure",
            "nodes",
            "numerical_model",
            "numerical_proof",
            "proof_dependency_graph_id",
        },
        "cached proof graph",
    )
    model, proof_id, quotient_id, frontier_id = _verify_proof_structure(
        graph["numerical_proof"],
        model_document=graph["numerical_model"],
    )
    if (
        graph["numerical_model_id"] != model.model_id
        or graph["numerical_proof_id"] != proof_id
        or graph["behavioral_quotient_id"] != quotient_id
        or graph["failed_frontier_id"] != frontier_id
        or graph["query_identity_is_dependency"] is not False
        or graph["threshold_profile_is_dependency"] is not True
        or graph["exact_h2_dependency_structure"] is not True
    ):
        _fail("cached proof graph identity closure changed")
    nodes = graph["nodes"]
    if type(nodes) is not list or len(nodes) != graph["node_count"]:
        _fail("cached proof graph node inventory changed")
    by_role: dict[str, dict[str, Any]] = {}
    node_ids = []
    role_keys = []
    for node in nodes:
        node = _exact_keys(
            node,
            {
                "schema",
                "schema_version",
                "profile_key",
                "node_kind",
                "role_key",
                "result_id",
                "dependencies",
                "proof_dependency_node_id",
            },
            "cached proof node",
        )
        role = node["role_key"]
        if type(role) is not str or not role or role in by_role:
            _fail("cached proof node role inventory changed")
        dependencies = node["dependencies"]
        if type(dependencies) is not list:
            _fail("cached proof node dependencies changed")
        for dependency in dependencies:
            _exact_keys(
                dependency,
                {"role_key", "node_id"},
                "cached proof dependency",
            )
            _cid(dependency["node_id"], "cached proof dependency")
        node_id = content_id(
            dag_v1.NODE_DOMAIN,
            _without(node, "proof_dependency_node_id"),
        )
        if node["proof_dependency_node_id"] != node_id:
            _fail("cached proof node identity changed")
        by_role[role] = node
        node_ids.append(node_id)
        role_keys.append(role)
    for node in nodes:
        for dependency in node["dependencies"]:
            target = by_role.get(dependency["role_key"])
            if (
                target is None
                or target["proof_dependency_node_id"] != dependency["node_id"]
            ):
                _fail("cached proof graph contains a crossed edge")
    if graph["node_ids"] != node_ids or graph["node_role_keys"] != role_keys:
        _fail("cached proof graph node summary changed")
    graph_id = content_id(
        dag_v1.GRAPH_DOMAIN,
        _without(
            graph,
            "nodes",
            "numerical_model",
            "numerical_proof",
            "proof_dependency_graph_id",
        ),
    )
    if graph["proof_dependency_graph_id"] != graph_id:
        _fail("cached proof graph identity changed")
    return model, graph["numerical_proof"], proof_id, frontier_id, graph_id, by_role


def _verify_transition_structure(
    transition: dict[str, Any],
) -> tuple[
    planning_v2.V075NumericalModelV2,
    dict[str, Any],
    str,
    str,
    str,
    tuple[tuple[str, str], ...],
]:
    source_graph = transition.get("source_graph")
    target_graph = transition.get("target_graph")
    (
        _source_model,
        _source_proof,
        _source_proof_id,
        _source_frontier_id,
        source_graph_id,
        source_nodes,
    ) = _verify_graph_structure(source_graph)
    (
        target_model,
        target_proof,
        target_proof_id,
        target_frontier_id,
        target_graph_id,
        target_nodes,
    ) = _verify_graph_structure(target_graph)
    transition_id = content_id(
        dag_v1.TRANSITION_DOMAIN,
        _without(
            transition,
            "source_graph",
            "target_graph",
            "query_bound_rapm_proof_dependency_transition_id",
        ),
    )
    if (
        transition.get("query_bound_rapm_proof_dependency_transition_id")
        != transition_id
        or transition.get("source_proof_dependency_graph_id") != source_graph_id
        or transition.get("target_proof_dependency_graph_id") != target_graph_id
        or set(source_nodes) != set(target_nodes)
        or transition.get("proof_dependency_dag_materialized") is not True
        or transition.get("changed_ancestor_invalidation_exact") is not True
        or transition.get("unaffected_nonancestor_recomputation_count") != 0
        or transition.get("persistent_cross_query_cache_materialized") is not False
    ):
        _fail("cached proof transition identity or claim boundary changed")
    resolutions = transition.get("resolutions")
    if type(resolutions) is not list or len(resolutions) != len(target_nodes):
        _fail("cached proof transition resolution inventory changed")
    resolution_by_role = {}
    for resolution in resolutions:
        resolution = _exact_keys(
            resolution,
            {"role_key", "source_node_id", "target_node_id", "outcome", "reason"},
            "cached proof resolution",
        )
        role = resolution["role_key"]
        source = source_nodes.get(role)
        target = target_nodes.get(role)
        if source is None or target is None or role in resolution_by_role:
            _fail("cached proof resolution role changed")
        reused = source["proof_dependency_node_id"] == target["proof_dependency_node_id"]
        expected_outcome = "REUSED" if reused else "RECOMPUTED"
        expected_reason = (
            "IDENTICAL_DEPENDENCY_CLOSURE"
            if reused
            else ("SIGNED_SEMANTIC_ROW_DELTA" if role.startswith("ROW:") else "CHANGED_ANCESTOR")
        )
        if (
            resolution["source_node_id"] != source["proof_dependency_node_id"]
            or resolution["target_node_id"] != target["proof_dependency_node_id"]
            or resolution["outcome"] != expected_outcome
            or resolution["reason"] != expected_reason
        ):
            _fail("cached proof resolution changed")
        resolution_by_role[role] = resolution
    changed = transition.get("changed_semantic_row_binding_ids")
    preserved = transition.get("preserved_semantic_row_binding_ids")
    if type(changed) is not list or type(preserved) is not list or len(changed) != 6 or len(preserved) != 12:
        _fail("cached proof semantic-row partition changed")
    reverse: dict[str, set[str]] = {}
    for nodes_by_role in (source_nodes, target_nodes):
        for node in nodes_by_role.values():
            for dependency in node["dependencies"]:
                reverse.setdefault(dependency["role_key"], set()).add(node["role_key"])
    closure = {f"ROW:{binding}" for binding in changed}
    pending = list(closure)
    while pending:
        role = pending.pop()
        for ancestor in reverse.get(role, ()):
            if ancestor not in closure:
                closure.add(ancestor)
                pending.append(ancestor)
    changed_ancestors = tuple(sorted(closure))
    recomputed = tuple(
        sorted(
            role
            for role, resolution in resolution_by_role.items()
            if resolution["outcome"] == "RECOMPUTED"
        )
    )
    if (
        transition.get("changed_ancestor_role_keys") != list(changed_ancestors)
        or recomputed != changed_ancestors
        or transition.get("recomputed_proof_node_count") != len(recomputed)
        or transition.get("reused_proof_node_count") != len(target_nodes) - len(recomputed)
    ):
        _fail("cached proof transition changed-ancestor cone changed")
    inventory = tuple(
        (role, target_nodes[role]["proof_dependency_node_id"])
        for role in sorted(target_nodes)
    )
    return (
        target_model,
        target_proof,
        target_proof_id,
        target_frontier_id,
        transition_id,
        inventory,
    )


def _verify_source_join(
    *,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    planning_v2.V075NumericalModelV2,
    dict[str, Any],
    tuple[tuple[str, str], ...],
]:
    binding = _canonical(binding_bytes, "source-bundle binding")
    snapshot = _canonical(snapshot_bytes, "reusable RAPM snapshot")
    transition = _canonical(transition_bytes, "proof dependency transition")
    binding_id = content_id(
        binding_v1.BINDING_DOMAIN,
        _without(binding, "query_bound_reusable_rapm_source_bundle_binding_id"),
    )
    snapshot_id = content_id(
        snapshot_v1.SNAPSHOT_DOMAIN,
        _without(
            snapshot,
            "reusable_model",
            "reusable_proof",
            "query_bound_reusable_rapm_snapshot_id",
        ),
    )
    if (
        binding.get("query_bound_reusable_rapm_source_bundle_binding_id") != binding_id
        or snapshot.get("query_bound_reusable_rapm_snapshot_id") != snapshot_id
        or binding.get("source_occurrence_complete_bundle_binding_present") is not True
        or binding.get("reusable_rapm_snapshot_id") != snapshot_id
    ):
        _fail("persistent proof cache crossed its source binding or snapshot")
    (
        target_model,
        target_proof,
        target_proof_id,
        target_frontier_id,
        transition_id,
        inventory,
    ) = _verify_transition_structure(transition)
    joins = {
        "snapshot_model_bytes": (
            _same_document(snapshot.get("reusable_model"), target_model.to_document())
        ),
        "snapshot_proof_bytes": _same_document(
            snapshot.get("reusable_proof"), target_proof
        ),
        "snapshot_model_id": (
            snapshot.get("reusable_numerical_model_id") == target_model.model_id
        ),
        "snapshot_proof_id": (
            snapshot.get("reusable_numerical_proof_id") == target_proof_id
        ),
        "snapshot_frontier_id": (
            snapshot.get("reusable_frontier_id") == target_frontier_id
        ),
        "binding_model_id": (
            binding.get("reusable_numerical_model_id") == target_model.model_id
        ),
        "binding_proof_id": (
            binding.get("reusable_numerical_proof_id") == target_proof_id
        ),
        "binding_final_local": (
            binding.get("source_final_local_replanning_id")
            == transition.get("source_final_local_replanning_id")
        ),
        "snapshot_final_local": (
            snapshot.get("source_final_local_replanning_id")
            == transition.get("source_final_local_replanning_id")
        ),
    }
    failed_joins = tuple(label for label, passed in joins.items() if not passed)
    if failed_joins:
        _fail(
            "persistent proof cache source/model/proof join changed: "
            + ",".join(failed_joins)
        )
    return binding, snapshot, transition, target_model, target_proof, inventory


@dataclass(frozen=True, slots=True)
class QueryBoundPersistentProofCacheV1:
    _issuer: InitVar[object]
    source_bundle_binding_bytes: bytes = field(repr=False)
    reusable_rapm_snapshot_bytes: bytes = field(repr=False)
    proof_dependency_transition_bytes: bytes = field(repr=False)
    target_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    target_proof_bytes: bytes = field(repr=False)
    node_inventory: tuple[tuple[str, str], ...]
    _cache_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CACHE_ISSUER
            or type(self.source_bundle_binding_bytes) is not bytes
            or type(self.reusable_rapm_snapshot_bytes) is not bytes
            or type(self.proof_dependency_transition_bytes) is not bytes
            or type(self.target_model) is not planning_v2.V075NumericalModelV2
            or type(self.target_proof_bytes) is not bytes
            or type(self.node_inventory) is not tuple
        ):
            _fail("persistent proof cache is caller-minted")
        (
            _binding,
            _snapshot,
            _transition,
            expected_model,
            expected_proof,
            expected_inventory,
        ) = _verify_source_join(
            binding_bytes=self.source_bundle_binding_bytes,
            snapshot_bytes=self.reusable_rapm_snapshot_bytes,
            transition_bytes=self.proof_dependency_transition_bytes,
        )
        if (
            not _same_document(
                self.target_model.to_document(), expected_model.to_document()
            )
            or self.target_proof_bytes != canonical_json_bytes(expected_proof)
            or self.node_inventory != expected_inventory
            or len(self.node_inventory) != 41
        ):
            _fail("persistent proof cache differs from source-bound replay")
        object.__setattr__(self, "_cache_id", content_id(CACHE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        binding = loads_canonical_json(self.source_bundle_binding_bytes)
        snapshot = loads_canonical_json(self.reusable_rapm_snapshot_bytes)
        transition = loads_canonical_json(self.proof_dependency_transition_bytes)
        target_proof = loads_canonical_json(self.target_proof_bytes)
        return {
            "schema": "acfqp.construction_k7_query_bound_persistent_proof_cache.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_bundle_binding_id": binding[
                "query_bound_reusable_rapm_source_bundle_binding_id"
            ],
            "source_logical_occurrence_id": binding["logical_occurrence_id"],
            "reusable_rapm_snapshot_id": snapshot[
                "query_bound_reusable_rapm_snapshot_id"
            ],
            "proof_dependency_transition_id": transition[
                "query_bound_rapm_proof_dependency_transition_id"
            ],
            "reusable_numerical_model_id": self.target_model.model_id,
            "reusable_numerical_proof_id": target_proof["proof_id"],
            "reusable_frontier_id": target_proof["failed_frontier_id"],
            "source_bundle_binding_sha256": _sha(self.source_bundle_binding_bytes),
            "source_bundle_binding_byte_count": len(self.source_bundle_binding_bytes),
            "reusable_rapm_snapshot_sha256": _sha(self.reusable_rapm_snapshot_bytes),
            "reusable_rapm_snapshot_byte_count": len(self.reusable_rapm_snapshot_bytes),
            "proof_dependency_transition_sha256": _sha(
                self.proof_dependency_transition_bytes
            ),
            "proof_dependency_transition_byte_count": len(
                self.proof_dependency_transition_bytes
            ),
            "cached_node_inventory": [
                {"role_key": role, "node_id": node_id}
                for role, node_id in self.node_inventory
            ],
            "cached_proof_node_count": len(self.node_inventory),
            "offline_source_and_target_exact_proofs_present": True,
            "online_structural_replay_without_planner_supported": True,
            "query_identity_is_outside_proof_dependency_closure": True,
            "persistent_cross_query_cache_materialized": True,
            "fresh_query_cache_consumer_present": True,
            "fresh_query_ground_access_authority_present": False,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
            "next_required_action": "CONSUME_CACHE_ON_FRESH_OCCURRENCE",
        }

    @property
    def cache_id(self) -> str:
        current = content_id(CACHE_DOMAIN, self._payload())
        if current != self._cache_id:
            _fail("persistent proof cache changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_bundle_binding": loads_canonical_json(
                self.source_bundle_binding_bytes
            ),
            "reusable_rapm_snapshot": loads_canonical_json(
                self.reusable_rapm_snapshot_bytes
            ),
            "proof_dependency_transition": loads_canonical_json(
                self.proof_dependency_transition_bytes
            ),
            "query_bound_persistent_proof_cache_id": self.cache_id,
        }


def materialize_query_bound_persistent_proof_cache_v1(
    *,
    binding: binding_v1.QueryBoundReusableRAPMSourceBundleBindingV1,
    snapshot: snapshot_v1.QueryBoundReusableRAPMSnapshotV1,
    transition: dag_v1.QueryBoundRAPMProofDependencyTransitionV1,
) -> QueryBoundPersistentProofCacheV1:
    if type(binding) is not binding_v1.QueryBoundReusableRAPMSourceBundleBindingV1:
        _fail("persistent proof cache binding has a foreign type")
    snapshot = snapshot_v1.require_query_bound_reusable_rapm_snapshot_v1(snapshot)
    if type(transition) is not dag_v1.QueryBoundRAPMProofDependencyTransitionV1:
        _fail("persistent proof cache transition has a foreign type")
    binding_bytes = canonical_json_bytes(binding.to_document())
    snapshot_bytes = canonical_json_bytes(snapshot.to_document())
    transition_bytes = canonical_json_bytes(transition.to_document())
    return materialize_query_bound_persistent_proof_cache_bytes_v1(
        binding_bytes=binding_bytes,
        snapshot_bytes=snapshot_bytes,
        transition_bytes=transition_bytes,
    )


def materialize_query_bound_persistent_proof_cache_bytes_v1(
    *,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
) -> QueryBoundPersistentProofCacheV1:
    """Materialize the cache from independently persisted canonical inputs."""

    (
        _binding,
        _snapshot,
        _transition,
        target_model,
        target_proof,
        inventory,
    ) = _verify_source_join(
        binding_bytes=binding_bytes,
        snapshot_bytes=snapshot_bytes,
        transition_bytes=transition_bytes,
    )
    return QueryBoundPersistentProofCacheV1(
        _CACHE_ISSUER,
        binding_bytes,
        snapshot_bytes,
        transition_bytes,
        target_model,
        canonical_json_bytes(target_proof),
        inventory,
    )


def load_query_bound_persistent_proof_cache_bytes_v1(
    cache_bytes: bytes,
) -> QueryBoundPersistentProofCacheV1:
    document = _canonical(cache_bytes, "persistent proof cache")
    try:
        binding_bytes = canonical_json_bytes(document["source_bundle_binding"])
        snapshot_bytes = canonical_json_bytes(document["reusable_rapm_snapshot"])
        transition_bytes = canonical_json_bytes(document["proof_dependency_transition"])
        (
            _binding,
            _snapshot,
            _transition,
            target_model,
            target_proof,
            inventory,
        ) = _verify_source_join(
            binding_bytes=binding_bytes,
            snapshot_bytes=snapshot_bytes,
            transition_bytes=transition_bytes,
        )
        expected = QueryBoundPersistentProofCacheV1(
            _CACHE_ISSUER,
            binding_bytes,
            snapshot_bytes,
            transition_bytes,
            target_model,
            canonical_json_bytes(target_proof),
            inventory,
        )
    except ConstructionK7QueryBoundPersistentProofCacheV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundPersistentProofCacheV1Error(
            "persistent proof cache failed typed structural replay"
        ) from error
    if canonical_json_bytes(expected.to_document()) != cache_bytes:
        _fail("persistent proof cache differs from structural replay")
    return expected


@dataclass(frozen=True, slots=True)
class QueryBoundProofCacheQueryV1:
    _issuer: InitVar[object]
    persistent_proof_cache_id: str
    reusable_numerical_model_id: str
    source_logical_occurrence_id: str
    logical_occurrence_id: str
    query_ordinal: int
    threshold_profile_id: str
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("proof-cache query is caller-minted")
        for value, label in (
            (self.persistent_proof_cache_id, "persistent proof cache"),
            (self.reusable_numerical_model_id, "reusable numerical model"),
            (self.source_logical_occurrence_id, "source logical occurrence"),
            (self.logical_occurrence_id, "fresh logical occurrence"),
            (self.threshold_profile_id, "threshold profile"),
        ):
            _cid(value, label)
        if (
            self.logical_occurrence_id == self.source_logical_occurrence_id
            or type(self.query_ordinal) is not int
            or self.query_ordinal <= 1
            or self.threshold_profile_id
            != worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        ):
            _fail("proof-cache query identity or threshold changed")
        object.__setattr__(self, "_query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_proof_cache_query.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "persistent_proof_cache_id": self.persistent_proof_cache_id,
            "reusable_numerical_model_id": self.reusable_numerical_model_id,
            "source_logical_occurrence_id": self.source_logical_occurrence_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "route": "ADAPTIVE_QUOTIENT",
            "query_identity_is_not_a_proof_dependency": True,
            "ground_access_authorized": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("proof-cache query changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_cache_query_id": self.query_id}


def freeze_query_bound_proof_cache_query_v1(
    *,
    cache_bytes: bytes,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> QueryBoundProofCacheQueryV1:
    cache = load_query_bound_persistent_proof_cache_bytes_v1(cache_bytes)
    binding = loads_canonical_json(cache.source_bundle_binding_bytes)
    return QueryBoundProofCacheQueryV1(
        _QUERY_ISSUER,
        cache.cache_id,
        cache.target_model.model_id,
        binding["logical_occurrence_id"],
        _cid(logical_occurrence_id, "fresh logical occurrence"),
        query_ordinal,
        worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
    )


@dataclass(frozen=True, slots=True)
class QueryBoundProofCacheConsumptionV1:
    _issuer: InitVar[object]
    query: QueryBoundProofCacheQueryV1
    proof_id: str
    frontier_id: str
    reused_node_ids: tuple[str, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CONSUMPTION_ISSUER
            or type(self.query) is not QueryBoundProofCacheQueryV1
            or type(self.reused_node_ids) is not tuple
            or len(self.reused_node_ids) != 41
            or len(set(self.reused_node_ids)) != 41
        ):
            _fail("proof-cache consumption is caller-minted")
        self.query.__post_init__(_QUERY_ISSUER)
        _cid(self.proof_id, "cached numerical proof")
        _cid(self.frontier_id, "cached failed frontier")
        for value in self.reused_node_ids:
            _cid(value, "reused proof node")
        object.__setattr__(
            self,
            "_result_id",
            content_id(CONSUMPTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_proof_cache_consumption.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "proof_cache_query_id": self.query.query_id,
            "persistent_proof_cache_id": self.query.persistent_proof_cache_id,
            "reusable_numerical_model_id": self.query.reusable_numerical_model_id,
            "cached_numerical_proof_id": self.proof_id,
            "cached_failed_frontier_id": self.frontier_id,
            "reused_proof_node_ids": list(self.reused_node_ids),
            "proof_node_reuse_count": len(self.reused_node_ids),
            "proof_node_compute_count": 0,
            "full_planner_call_count": 0,
            "model_construction_repeated": False,
            "new_ground_access_count": 0,
            "ground_input_parameter_present": False,
            "exact_cached_certificate_failure_replayed": True,
            "query_local_ground_recovery_eligible": True,
            "query_local_ground_recovery_executed_here": False,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
            "next_required_action": "FREEZE_QUERY_LOCAL_RECOVERY_REQUEST_FROM_CACHED_FRONTIER",
        }

    @property
    def result_id(self) -> str:
        current = content_id(CONSUMPTION_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("proof-cache consumption changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query": self.query.to_document(),
            "query_bound_proof_cache_consumption_id": self.result_id,
        }


def run_query_bound_proof_cache_consumer_v1(
    *,
    cache_bytes: bytes,
    query: QueryBoundProofCacheQueryV1,
) -> QueryBoundProofCacheConsumptionV1:
    cache = load_query_bound_persistent_proof_cache_bytes_v1(cache_bytes)
    if type(query) is not QueryBoundProofCacheQueryV1:
        _fail("proof-cache consumer query has a foreign type")
    query.__post_init__(_QUERY_ISSUER)
    binding = loads_canonical_json(cache.source_bundle_binding_bytes)
    if (
        query.persistent_proof_cache_id != cache.cache_id
        or query.reusable_numerical_model_id != cache.target_model.model_id
        or query.source_logical_occurrence_id != binding["logical_occurrence_id"]
    ):
        _fail("proof-cache consumer query crossed its cache")
    return QueryBoundProofCacheConsumptionV1(
        _CONSUMPTION_ISSUER,
        query,
        loads_canonical_json(cache.target_proof_bytes)["proof_id"],
        loads_canonical_json(cache.target_proof_bytes)["failed_frontier_id"],
        tuple(node_id for _role, node_id in cache.node_inventory),
    )


def verify_query_bound_proof_cache_consumption_bytes_v1(
    *,
    cache_bytes: bytes,
    result_bytes: bytes,
) -> QueryBoundProofCacheConsumptionV1:
    document = _canonical(result_bytes, "proof-cache consumption")
    try:
        query_document = document["query"]
        query = QueryBoundProofCacheQueryV1(
            _QUERY_ISSUER,
            query_document["persistent_proof_cache_id"],
            query_document["reusable_numerical_model_id"],
            query_document["source_logical_occurrence_id"],
            query_document["logical_occurrence_id"],
            query_document["query_ordinal"],
            query_document["threshold_profile_id"],
        )
        expected = run_query_bound_proof_cache_consumer_v1(
            cache_bytes=cache_bytes,
            query=query,
        )
    except ConstructionK7QueryBoundPersistentProofCacheV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundPersistentProofCacheV1Error(
            "proof-cache consumption failed typed replay"
        ) from error
    if canonical_json_bytes(expected.to_document()) != result_bytes:
        _fail("proof-cache consumption differs from exact cache replay")
    return expected


@dataclass(frozen=True, slots=True)
class QueryBoundProofCacheNoReuseControlV1:
    _issuer: InitVar[object]
    query_id: str
    cache_id: str
    model_id: str
    cached_proof_id: str
    recomputed_proof_id: str
    _control_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CONTROL_ISSUER:
            _fail("proof-cache no-reuse control is caller-minted")
        for value, label in (
            (self.query_id, "proof-cache query"),
            (self.cache_id, "persistent proof cache"),
            (self.model_id, "reusable numerical model"),
            (self.cached_proof_id, "cached numerical proof"),
            (self.recomputed_proof_id, "recomputed numerical proof"),
        ):
            _cid(value, label)
        if self.cached_proof_id != self.recomputed_proof_id:
            _fail("proof-cache no-reuse control differs from cached proof")
        object.__setattr__(
            self,
            "_control_id",
            content_id(NO_REUSE_CONTROL_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_proof_cache_no_reuse_control.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "proof_cache_query_id": self.query_id,
            "persistent_proof_cache_id": self.cache_id,
            "reusable_numerical_model_id": self.model_id,
            "cached_numerical_proof_id": self.cached_proof_id,
            "recomputed_numerical_proof_id": self.recomputed_proof_id,
            "full_planner_call_count": 1,
            "proof_node_compute_count": 41,
            "proof_node_reuse_count": 0,
            "proof_bytes_match_cache": True,
            "evaluation_only": True,
            "operational_route_work": False,
            "new_ground_access_count": 0,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def control_id(self) -> str:
        current = content_id(NO_REUSE_CONTROL_DOMAIN, self._payload())
        if current != self._control_id:
            _fail("proof-cache no-reuse control changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_cache_no_reuse_control_id": self.control_id}


def run_query_bound_proof_cache_no_reuse_control_v1(
    *,
    cache_bytes: bytes,
    query: QueryBoundProofCacheQueryV1,
) -> QueryBoundProofCacheNoReuseControlV1:
    cache = load_query_bound_persistent_proof_cache_bytes_v1(cache_bytes)
    if type(query) is not QueryBoundProofCacheQueryV1:
        _fail("proof-cache control query has a foreign type")
    query.__post_init__(_QUERY_ISSUER)
    if (
        query.persistent_proof_cache_id != cache.cache_id
        or query.reusable_numerical_model_id != cache.target_model.model_id
    ):
        _fail("proof-cache no-reuse control crossed its cache")
    proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=cache.target_model,
        route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    if proof.canonical_bytes != cache.target_proof_bytes:
        _fail("proof-cache no-reuse control proof bytes changed")
    return QueryBoundProofCacheNoReuseControlV1(
        _CONTROL_ISSUER,
        query.query_id,
        cache.cache_id,
        cache.target_model.model_id,
        loads_canonical_json(cache.target_proof_bytes)["proof_id"],
        proof.proof_id,
    )


__all__ = [
    "ConstructionK7QueryBoundPersistentProofCacheV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundPersistentProofCacheV1",
    "QueryBoundProofCacheConsumptionV1",
    "QueryBoundProofCacheNoReuseControlV1",
    "QueryBoundProofCacheQueryV1",
    "freeze_query_bound_proof_cache_query_v1",
    "load_query_bound_persistent_proof_cache_bytes_v1",
    "materialize_query_bound_persistent_proof_cache_bytes_v1",
    "materialize_query_bound_persistent_proof_cache_v1",
    "run_query_bound_proof_cache_consumer_v1",
    "run_query_bound_proof_cache_no_reuse_control_v1",
    "verify_query_bound_proof_cache_consumption_bytes_v1",
]
