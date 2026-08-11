"""Independent replay of the source-bound persistent proof-cache bundle.

This verifier does not import the cache or proof-DAG producers.  It replays the
registered source-bundle authority, both exact planning proofs, every proof-DAG
node and dependency edge, the persistent cache, and one fresh-query
consumption result.  Planner work performed here is evaluation-only; the
verified online result must still report zero planner calls and zero ground
access.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_reusable_rapm_source_bundle_binding_independent_verifier_v1 as binding_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_CONSUMPTION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_GRAPH_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_NODE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_TRANSITION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_PARTITION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_SEARCH_RESULT_V1_DOMAIN,
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
CONSUMPTION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_CONSUMPTION_V1_DOMAIN
NODE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_NODE_V1_DOMAIN
GRAPH_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_GRAPH_V1_DOMAIN
TRANSITION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_TRANSITION_V1_DOMAIN
)
PARTITION_RESULT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_PARTITION_RESULT_V1_DOMAIN
)
SEARCH_RESULT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_SEARCH_RESULT_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("persistent proof-cache verification domain is not central")


class ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
    ValueError
):
    """The source authority, DAG, cache, or fresh-query result diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _load(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} has missing or unknown fields")
    return value


def _without(document: dict[str, Any], *fields: str) -> dict[str, Any]:
    value = dict(document)
    for field in fields:
        try:
            value.pop(field)
        except KeyError as error:
            raise ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
                f"required expansion {field} is absent"
            ) from error
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


_GRAPH_FIELDS = {
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
}
_NODE_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "node_kind",
    "role_key",
    "result_id",
    "dependencies",
    "proof_dependency_node_id",
}
_DEPENDENCY_FIELDS = {"role_key", "node_id"}


def _expected_node_specs(
    proof: planning_v2.V075NumericalPlanningProofV2,
) -> list[tuple[str, str, str, tuple[str, ...]]]:
    model = proof.model
    quotient = proof.quotient
    frontier = proof.failed_frontier
    if quotient is None or frontier is None:
        _fail("proof dependency graph is not one failed adaptive proof")
    rows_by_binding = {row.row_binding_id: row for row in model.rows}
    binding_by_row = {row.row_id: row.row_binding_id for row in model.rows}
    behavior_by_row = {item.row_id: item for item in quotient.row_behaviors}
    if (
        len(rows_by_binding) != len(model.rows)
        or len(binding_by_row) != len(model.rows)
        or set(behavior_by_row) != set(binding_by_row)
    ):
        _fail("proof dependency semantic-row inventory changed")
    specs: list[tuple[str, str, str, tuple[str, ...]]] = []
    for binding in sorted(rows_by_binding):
        row = rows_by_binding[binding]
        specs.append(("SEMANTIC_ROW", f"ROW:{binding}", row.row_id, ()))
    h1_bindings = tuple(
        sorted(
            binding
            for binding, row in rows_by_binding.items()
            if row.remaining_horizon == 1
        )
    )
    h2_bindings = tuple(
        sorted(
            binding
            for binding, row in rows_by_binding.items()
            if row.remaining_horizon == 2
        )
    )
    for binding in h1_bindings:
        row = rows_by_binding[binding]
        specs.append(
            (
                "ROW_BEHAVIOR",
                f"BEHAVIOR:{binding}",
                behavior_by_row[row.row_id].behavior_key,
                (f"ROW:{binding}",),
            )
        )
    child_cells = sorted(
        (
            item.to_document()
            for item in quotient.cells
            if item.remaining_horizon == 1
        ),
        key=lambda item: item["cell_id"],
    )
    child_result = content_id(
        PARTITION_RESULT_DOMAIN,
        {
            "schema": "acfqp.construction_k7_query_bound_rapm_child_partition_result.v1",
            "schema_version": SCHEMA_VERSION,
            "cell_documents": child_cells,
        },
    )
    specs.append(
        (
            "CHILD_PARTITION",
            "CHILD_PARTITION",
            child_result,
            tuple(f"BEHAVIOR:{binding}" for binding in h1_bindings),
        )
    )
    for binding in h2_bindings:
        row = rows_by_binding[binding]
        specs.append(
            (
                "ROW_BEHAVIOR",
                f"BEHAVIOR:{binding}",
                behavior_by_row[row.row_id].behavior_key,
                ("CHILD_PARTITION", f"ROW:{binding}"),
            )
        )
    specs.append(
        (
            "ROOT_PARTITION",
            "ROOT_PARTITION",
            quotient.quotient_id,
            tuple(
                sorted(
                    ("CHILD_PARTITION",)
                    + tuple(f"BEHAVIOR:{binding}" for binding in h2_bindings)
                )
            ),
        )
    )
    search_result = content_id(
        SEARCH_RESULT_DOMAIN,
        {
            "schema": "acfqp.construction_k7_query_bound_rapm_policy_search_result.v1",
            "schema_version": SCHEMA_VERSION,
            "numerical_model_id": model.model_id,
            "behavioral_quotient_id": quotient.quotient_id,
            "numerical_outcome": proof.outcome.value,
            "policy_assignments_evaluated": proof.policy_assignments_evaluated,
        },
    )
    all_behaviors = tuple(
        sorted(f"BEHAVIOR:{binding}" for binding in rows_by_binding)
    )
    specs.append(
        (
            "POLICY_SEARCH",
            "POLICY_SEARCH",
            search_result,
            tuple(sorted(("ROOT_PARTITION",) + all_behaviors)),
        )
    )
    frontier_behaviors = []
    for obligation in frontier.obligations:
        binding = binding_by_row.get(obligation.row_id)
        if binding is None:
            _fail("failed frontier obligation is not one numerical row")
        frontier_behaviors.append(f"BEHAVIOR:{binding}")
    specs.append(
        (
            "FAILED_FRONTIER",
            "FAILED_FRONTIER",
            frontier.frontier_id,
            tuple(sorted(("POLICY_SEARCH", *frontier_behaviors))),
        )
    )
    specs.append(
        (
            "PROOF_ROOT",
            "PROOF_ROOT",
            proof.proof_id,
            ("FAILED_FRONTIER", "POLICY_SEARCH", "ROOT_PARTITION"),
        )
    )
    return specs


def _verify_graph(
    graph: Any,
) -> tuple[
    planning_v2.V075NumericalPlanningProofV2,
    str,
    dict[str, dict[str, Any]],
]:
    graph = _exact(graph, _GRAPH_FIELDS, "proof dependency graph")
    try:
        proof_bytes = canonical_json_bytes(graph["numerical_proof"])
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(proof_bytes)
    except Exception as error:
        raise ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
            "proof dependency graph failed exact planner replay"
        ) from error
    if (
        canonical_json_bytes(graph["numerical_model"])
        != canonical_json_bytes(proof.model.to_document())
        or graph["numerical_model_id"] != proof.model.model_id
        or graph["numerical_proof_id"] != proof.proof_id
        or proof.quotient is None
        or proof.failed_frontier is None
        or graph["behavioral_quotient_id"] != proof.quotient.quotient_id
        or graph["failed_frontier_id"] != proof.failed_frontier.frontier_id
        or graph["query_identity_is_dependency"] is not False
        or graph["threshold_profile_is_dependency"] is not True
        or graph["exact_h2_dependency_structure"] is not True
    ):
        _fail("proof dependency graph crossed its exact proof")
    expected_specs = _expected_node_specs(proof)
    nodes = graph["nodes"]
    if (
        type(nodes) is not list
        or not expected_specs
        or len(nodes) != len(expected_specs)
    ):
        _fail("proof dependency node cardinality changed")
    by_role: dict[str, dict[str, Any]] = {}
    expected_node_ids: list[str] = []
    expected_roles: list[str] = []
    for node, (kind, role, result_id, dependency_roles) in zip(
        nodes, expected_specs, strict=True
    ):
        node = _exact(node, _NODE_FIELDS, "proof dependency node")
        dependencies = node["dependencies"]
        if type(dependencies) is not list:
            _fail("proof dependency edge inventory changed")
        actual_dependency_roles = []
        for dependency in dependencies:
            dependency = _exact(
                dependency,
                _DEPENDENCY_FIELDS,
                "proof dependency edge",
            )
            _cid(dependency["node_id"], "proof dependency edge")
            actual_dependency_roles.append(dependency["role_key"])
        if (
            node["schema"]
            != "acfqp.construction_k7_query_bound_rapm_proof_dependency_node.v1"
            or node["schema_version"] != SCHEMA_VERSION
            or node["profile_key"]
            != "construction_k7_query_bound_rapm_proof_dependency_dag_v1"
            or node["node_kind"] != kind
            or node["role_key"] != role
            or node["result_id"] != result_id
            or tuple(actual_dependency_roles) != dependency_roles
            or role in by_role
        ):
            _fail("proof dependency node semantics changed")
        for dependency in dependencies:
            target = by_role.get(dependency["role_key"])
            if (
                target is None
                or dependency["node_id"]
                != target["proof_dependency_node_id"]
            ):
                _fail("proof dependency edge crossed its predecessor")
        node_id = content_id(
            NODE_DOMAIN,
            _without(node, "proof_dependency_node_id"),
        )
        if node["proof_dependency_node_id"] != node_id:
            _fail("proof dependency node ID changed")
        by_role[role] = node
        expected_node_ids.append(node_id)
        expected_roles.append(role)
    if (
        graph["node_count"] != len(expected_specs)
        or graph["node_ids"] != expected_node_ids
        or graph["node_role_keys"] != expected_roles
    ):
        _fail("proof dependency graph summary changed")
    graph_id = content_id(
        GRAPH_DOMAIN,
        _without(
            graph,
            "nodes",
            "numerical_model",
            "numerical_proof",
            "proof_dependency_graph_id",
        ),
    )
    if graph["proof_dependency_graph_id"] != graph_id:
        _fail("proof dependency graph ID changed")
    return proof, graph_id, by_role


_TRANSITION_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_final_local_replanning_id",
    "source_proof_dependency_graph_id",
    "target_proof_dependency_graph_id",
    "changed_semantic_row_binding_ids",
    "preserved_semantic_row_binding_ids",
    "changed_ancestor_role_keys",
    "resolutions",
    "proof_node_count",
    "reused_proof_node_count",
    "recomputed_proof_node_count",
    "proof_dependency_dag_materialized",
    "semantic_row_identity_is_stable_role_key",
    "preserved_row_nodes_reused_byte_exactly",
    "changed_row_nodes_recomputed",
    "changed_ancestor_invalidation_exact",
    "unaffected_nonancestor_recomputation_count",
    "source_and_target_exact_proofs_replayed",
    "source_final_local_bytes_replayed",
    "source_occurrence_bundle_binding_present",
    "persistent_cross_query_cache_materialized",
    "fresh_query_cache_consumer_present",
    "plan_certificate_issued",
    "official_execution_allowed",
    "next_required_action",
    "source_graph",
    "target_graph",
    "query_bound_rapm_proof_dependency_transition_id",
}
_RESOLUTION_FIELDS = {
    "role_key",
    "source_node_id",
    "target_node_id",
    "outcome",
    "reason",
}


def _verify_transition(
    transition: Any,
) -> tuple[
    planning_v2.V075NumericalPlanningProofV2,
    planning_v2.V075NumericalPlanningProofV2,
    str,
    tuple[tuple[str, str], ...],
]:
    transition = _exact(
        transition,
        _TRANSITION_FIELDS,
        "proof dependency transition",
    )
    source_proof, source_graph_id, source_nodes = _verify_graph(
        transition["source_graph"]
    )
    target_proof, target_graph_id, target_nodes = _verify_graph(
        transition["target_graph"]
    )
    source_rows = {row.row_binding_id: row for row in source_proof.model.rows}
    target_rows = {row.row_binding_id: row for row in target_proof.model.rows}
    if (
        len(source_rows) != len(source_proof.model.rows)
        or len(target_rows) != len(target_proof.model.rows)
        or set(source_rows) != set(target_rows)
        or set(source_nodes) != set(target_nodes)
        or source_proof.model.context != target_proof.model.context
        or source_proof.model.evidence_kind != target_proof.model.evidence_kind
    ):
        _fail("proof dependency transition changed its model closure")
    changed = tuple(
        sorted(
            binding
            for binding in source_rows
            if source_rows[binding].row_id != target_rows[binding].row_id
        )
    )
    preserved = tuple(sorted(set(source_rows) - set(changed)))
    if not changed:
        _fail("proof dependency transition contains no semantic delta")
    for binding in changed:
        source = source_rows[binding]
        target = target_rows[binding]
        if (
            source.context_id != target.context_id
            or source.source_state_id != target.source_state_id
            or source.action != target.action
            or source.remaining_horizon != target.remaining_horizon
            or source.immediate_reward != target.immediate_reward
            or canonical_json_bytes([item.to_document() for item in source.support])
            != canonical_json_bytes([item.to_document() for item in target.support])
            or target.validation_draw_count <= source.validation_draw_count
        ):
            _fail("proof dependency transition changed a row outside validation")
    resolutions = []
    reverse: dict[str, set[str]] = {}
    for nodes in (source_nodes, target_nodes):
        for node in nodes.values():
            for dependency in node["dependencies"]:
                reverse.setdefault(dependency["role_key"], set()).add(
                    node["role_key"]
                )
    closure = {f"ROW:{binding}" for binding in changed}
    pending = list(closure)
    while pending:
        role = pending.pop()
        for ancestor in reverse.get(role, ()):
            if ancestor not in closure:
                closure.add(ancestor)
                pending.append(ancestor)
    ancestors = tuple(sorted(closure))
    for role in sorted(source_nodes):
        source = source_nodes[role]
        target = target_nodes[role]
        reused = (
            source["proof_dependency_node_id"]
            == target["proof_dependency_node_id"]
        )
        resolutions.append(
            {
                "role_key": role,
                "source_node_id": source["proof_dependency_node_id"],
                "target_node_id": target["proof_dependency_node_id"],
                "outcome": "REUSED" if reused else "RECOMPUTED",
                "reason": (
                    "IDENTICAL_DEPENDENCY_CLOSURE"
                    if reused
                    else (
                        "SIGNED_SEMANTIC_ROW_DELTA"
                        if role.startswith("ROW:")
                        else "CHANGED_ANCESTOR"
                    )
                ),
            }
        )
    recomputed = tuple(
        item["role_key"] for item in resolutions if item["outcome"] == "RECOMPUTED"
    )
    reused_count = len(resolutions) - len(recomputed)
    expected_payload = {
        "schema": "acfqp.construction_k7_query_bound_rapm_proof_dependency_transition.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": "2.0.108",
        "profile_key": "construction_k7_query_bound_rapm_proof_dependency_dag_v1",
        "source_final_local_replanning_id": _cid(
            transition["source_final_local_replanning_id"],
            "source final-local replanning",
        ),
        "source_proof_dependency_graph_id": source_graph_id,
        "target_proof_dependency_graph_id": target_graph_id,
        "changed_semantic_row_binding_ids": list(changed),
        "preserved_semantic_row_binding_ids": list(preserved),
        "changed_ancestor_role_keys": list(ancestors),
        "resolutions": resolutions,
        "proof_node_count": len(resolutions),
        "reused_proof_node_count": reused_count,
        "recomputed_proof_node_count": len(recomputed),
        "proof_dependency_dag_materialized": True,
        "semantic_row_identity_is_stable_role_key": True,
        "preserved_row_nodes_reused_byte_exactly": True,
        "changed_row_nodes_recomputed": True,
        "changed_ancestor_invalidation_exact": True,
        "unaffected_nonancestor_recomputation_count": 0,
        "source_and_target_exact_proofs_replayed": True,
        "source_final_local_bytes_replayed": False,
        "source_occurrence_bundle_binding_present": False,
        "persistent_cross_query_cache_materialized": False,
        "fresh_query_cache_consumer_present": False,
        "plan_certificate_issued": False,
        "official_execution_allowed": False,
        "next_required_action": (
            "PERSIST_DAG_AND_CONSUME_UNAFFECTED_PROOF_NODES_ON_FRESH_QUERY"
        ),
    }
    transition_id = transition["query_bound_rapm_proof_dependency_transition_id"]
    _cid(transition_id, "proof dependency transition")
    if (
        recomputed != ancestors
        or transition
        != {
            **expected_payload,
            "source_graph": transition["source_graph"],
            "target_graph": transition["target_graph"],
            "query_bound_rapm_proof_dependency_transition_id": transition_id,
        }
        or transition_id != content_id(TRANSITION_DOMAIN, expected_payload)
    ):
        _fail("proof dependency transition differs from independent replay")
    inventory = tuple(
        (role, target_nodes[role]["proof_dependency_node_id"])
        for role in sorted(target_nodes)
    )
    return source_proof, target_proof, transition_id, inventory


_CACHE_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_bundle_binding_id",
    "source_logical_occurrence_id",
    "reusable_rapm_snapshot_id",
    "proof_dependency_transition_id",
    "reusable_numerical_model_id",
    "reusable_numerical_proof_id",
    "reusable_frontier_id",
    "source_bundle_binding_sha256",
    "source_bundle_binding_byte_count",
    "reusable_rapm_snapshot_sha256",
    "reusable_rapm_snapshot_byte_count",
    "proof_dependency_transition_sha256",
    "proof_dependency_transition_byte_count",
    "cached_node_inventory",
    "cached_proof_node_count",
    "offline_source_and_target_exact_proofs_present",
    "online_structural_replay_without_planner_supported",
    "query_identity_is_outside_proof_dependency_closure",
    "persistent_cross_query_cache_materialized",
    "fresh_query_cache_consumer_present",
    "fresh_query_ground_access_authority_present",
    "plan_certificate_issued",
    "official_execution_allowed",
    "next_required_action",
    "source_bundle_binding",
    "reusable_rapm_snapshot",
    "proof_dependency_transition",
    "query_bound_persistent_proof_cache_id",
}


def _verify_cache(
    *,
    preregistration_bytes: bytes,
    bundle_directory: str | Path,
    cache_bytes: bytes,
) -> tuple[
    dict[str, Any],
    planning_v2.V075NumericalPlanningProofV2,
    str,
    tuple[tuple[str, str], ...],
    str,
]:
    cache = _exact(_load(cache_bytes, "persistent proof cache"), _CACHE_FIELDS, "persistent proof cache")
    binding_bytes = canonical_json_bytes(cache["source_bundle_binding"])
    snapshot_bytes = canonical_json_bytes(cache["reusable_rapm_snapshot"])
    transition_bytes = canonical_json_bytes(cache["proof_dependency_transition"])
    try:
        binding_verification = (
            binding_v1.verify_query_bound_reusable_rapm_source_bundle_binding_bytes_v1(
                preregistration_bytes=preregistration_bytes,
                bundle_directory=bundle_directory,
                snapshot_bytes=snapshot_bytes,
                binding_bytes=binding_bytes,
            )
        )
    except Exception as error:
        raise ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error(
            "persistent cache source binding failed independent replay"
        ) from error
    source_proof, target_proof, transition_id, inventory = _verify_transition(
        cache["proof_dependency_transition"]
    )
    snapshot = cache["reusable_rapm_snapshot"]
    binding = cache["source_bundle_binding"]
    frontier = target_proof.failed_frontier
    if frontier is None:
        _fail("persistent cache target proof has no failed frontier")
    if (
        canonical_json_bytes(snapshot["reusable_model"])
        != canonical_json_bytes(target_proof.model.to_document())
        or canonical_json_bytes(snapshot["reusable_proof"])
        != target_proof.canonical_bytes
        or binding_verification["source_bundle_binding_id"]
        != binding["query_bound_reusable_rapm_source_bundle_binding_id"]
        or binding_verification["reusable_rapm_snapshot_id"]
        != snapshot["query_bound_reusable_rapm_snapshot_id"]
        or binding_verification["reusable_numerical_model_id"]
        != target_proof.model.model_id
        or binding_verification["reusable_numerical_proof_id"]
        != target_proof.proof_id
        or binding["source_final_local_replanning_id"]
        != cache["proof_dependency_transition"]["source_final_local_replanning_id"]
    ):
        _fail("persistent cache crossed source binding, snapshot, or transition")
    expected_payload = {
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
        "proof_dependency_transition_id": transition_id,
        "reusable_numerical_model_id": target_proof.model.model_id,
        "reusable_numerical_proof_id": target_proof.proof_id,
        "reusable_frontier_id": frontier.frontier_id,
        "source_bundle_binding_sha256": _sha(binding_bytes),
        "source_bundle_binding_byte_count": len(binding_bytes),
        "reusable_rapm_snapshot_sha256": _sha(snapshot_bytes),
        "reusable_rapm_snapshot_byte_count": len(snapshot_bytes),
        "proof_dependency_transition_sha256": _sha(transition_bytes),
        "proof_dependency_transition_byte_count": len(transition_bytes),
        "cached_node_inventory": [
            {"role_key": role, "node_id": node_id}
            for role, node_id in inventory
        ],
        "cached_proof_node_count": len(inventory),
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
    cache_id = cache["query_bound_persistent_proof_cache_id"]
    _cid(cache_id, "persistent proof cache")
    if (
        len(inventory) != 41
        or cache
        != {
            **expected_payload,
            "source_bundle_binding": binding,
            "reusable_rapm_snapshot": snapshot,
            "proof_dependency_transition": cache["proof_dependency_transition"],
            "query_bound_persistent_proof_cache_id": cache_id,
        }
        or cache_id != content_id(CACHE_DOMAIN, expected_payload)
    ):
        _fail("persistent proof cache differs from independent replay")
    return cache, target_proof, cache_id, inventory, binding_verification[
        "query_bound_reusable_rapm_source_bundle_binding_verification_id"
    ]


_QUERY_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "persistent_proof_cache_id",
    "reusable_numerical_model_id",
    "source_logical_occurrence_id",
    "logical_occurrence_id",
    "query_ordinal",
    "threshold_profile_id",
    "route",
    "query_identity_is_not_a_proof_dependency",
    "ground_access_authorized",
    "proof_cache_query_id",
}
_RESULT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "proof_cache_query_id",
    "persistent_proof_cache_id",
    "reusable_numerical_model_id",
    "cached_numerical_proof_id",
    "cached_failed_frontier_id",
    "reused_proof_node_ids",
    "proof_node_reuse_count",
    "proof_node_compute_count",
    "full_planner_call_count",
    "model_construction_repeated",
    "new_ground_access_count",
    "ground_input_parameter_present",
    "cached_frontier_row_count",
    "requestable_frontier_row_count",
    "cap_blocked_frontier_row_count",
    "exact_cached_certificate_failure_replayed",
    "query_local_ground_recovery_eligible",
    "query_local_ground_recovery_executed_here",
    "local_allowed_after_result",
    "local_forbidden_reason",
    "plan_certificate_issued",
    "official_execution_allowed",
    "next_required_action",
    "query",
    "query_bound_proof_cache_consumption_id",
}


def _verify_consumption(
    *,
    result_bytes: bytes,
    cache: dict[str, Any],
    target_proof: planning_v2.V075NumericalPlanningProofV2,
    cache_id: str,
    inventory: tuple[tuple[str, str], ...],
) -> tuple[dict[str, Any], str, str, bool]:
    result = _exact(
        _load(result_bytes, "proof-cache consumption"),
        _RESULT_FIELDS,
        "proof-cache consumption",
    )
    query = _exact(result["query"], _QUERY_FIELDS, "proof-cache query")
    query_payload = {
        "schema": "acfqp.construction_k7_query_bound_proof_cache_query.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "persistent_proof_cache_id": cache_id,
        "reusable_numerical_model_id": target_proof.model.model_id,
        "source_logical_occurrence_id": cache["source_logical_occurrence_id"],
        "logical_occurrence_id": _cid(
            query["logical_occurrence_id"],
            "fresh logical occurrence",
        ),
        "query_ordinal": query["query_ordinal"],
        "threshold_profile_id": worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
        "route": "ADAPTIVE_QUOTIENT",
        "query_identity_is_not_a_proof_dependency": True,
        "ground_access_authorized": False,
    }
    query_id = query["proof_cache_query_id"]
    _cid(query_id, "proof-cache query")
    if (
        query_payload["logical_occurrence_id"]
        == query_payload["source_logical_occurrence_id"]
        or type(query_payload["query_ordinal"]) is not int
        or query_payload["query_ordinal"] <= 1
        or query != {**query_payload, "proof_cache_query_id": query_id}
        or query_id != content_id(QUERY_DOMAIN, query_payload)
    ):
        _fail("proof-cache query differs from independent replay")
    frontier = target_proof.failed_frontier
    if frontier is None:
        _fail("proof-cache consumption target has no failed frontier")
    requestable = sum(
        item.next_registered_checkpoint is not None
        for item in frontier.obligations
    )
    blocked = len(frontier.obligations) - requestable
    local_allowed = requestable > 0
    result_payload = {
        "schema": "acfqp.construction_k7_query_bound_proof_cache_consumption.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "proof_cache_query_id": query_id,
        "persistent_proof_cache_id": cache_id,
        "reusable_numerical_model_id": target_proof.model.model_id,
        "cached_numerical_proof_id": target_proof.proof_id,
        "cached_failed_frontier_id": frontier.frontier_id,
        "reused_proof_node_ids": [node_id for _role, node_id in inventory],
        "proof_node_reuse_count": len(inventory),
        "proof_node_compute_count": 0,
        "full_planner_call_count": 0,
        "model_construction_repeated": False,
        "new_ground_access_count": 0,
        "ground_input_parameter_present": False,
        "cached_frontier_row_count": len(frontier.obligations),
        "requestable_frontier_row_count": requestable,
        "cap_blocked_frontier_row_count": blocked,
        "exact_cached_certificate_failure_replayed": True,
        "query_local_ground_recovery_eligible": local_allowed,
        "query_local_ground_recovery_executed_here": False,
        "local_allowed_after_result": local_allowed,
        "local_forbidden_reason": (
            None if local_allowed else "NO_REGISTERED_CHECKPOINT"
        ),
        "plan_certificate_issued": False,
        "official_execution_allowed": False,
        "next_required_action": (
            "FREEZE_QUERY_LOCAL_RECOVERY_REQUEST_FROM_CACHED_FRONTIER"
            if local_allowed
            else "DIRECT_GROUND_FALLBACK"
        ),
    }
    result_id = result["query_bound_proof_cache_consumption_id"]
    _cid(result_id, "proof-cache consumption")
    if (
        result
        != {
            **result_payload,
            "query": query,
            "query_bound_proof_cache_consumption_id": result_id,
        }
        or result_id != content_id(CONSUMPTION_DOMAIN, result_payload)
    ):
        _fail("proof-cache consumption differs from independent replay")
    return result, query_id, result_id, local_allowed


def verify_query_bound_persistent_proof_cache_bundle_bytes_v1(
    *,
    preregistration_bytes: bytes,
    bundle_directory: str | Path,
    cache_bytes: bytes,
    result_bytes: bytes,
) -> dict[str, Any]:
    """Independently replay one cache and one fresh-query consumption."""

    cache, target_proof, cache_id, inventory, binding_verification_id = (
        _verify_cache(
            preregistration_bytes=preregistration_bytes,
            bundle_directory=bundle_directory,
            cache_bytes=cache_bytes,
        )
    )
    _result, query_id, result_id, local_allowed = _verify_consumption(
        result_bytes=result_bytes,
        cache=cache,
        target_proof=target_proof,
        cache_id=cache_id,
        inventory=inventory,
    )
    payload = {
        "schema": "acfqp.construction_k7_query_bound_persistent_proof_cache_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_bundle_binding_verification_id": binding_verification_id,
        "persistent_proof_cache_id": cache_id,
        "proof_cache_query_id": query_id,
        "proof_cache_consumption_id": result_id,
        "reusable_numerical_model_id": target_proof.model.model_id,
        "reusable_numerical_proof_id": target_proof.proof_id,
        "reusable_frontier_id": target_proof.failed_frontier.frontier_id,
        "proof_dependency_node_count": len(inventory),
        "source_and_target_exact_planner_replay_count": 2,
        "snapshot_exact_planner_replay_count": 1,
        "evaluation_full_planner_replay_count": 3,
        "source_occurrence_complete_bundle_binding_verified": True,
        "proof_dependency_dag_verified": True,
        "persistent_cache_verified": True,
        "fresh_query_consumption_verified": True,
        "operational_full_planner_call_count": 0,
        "operational_new_ground_access_count": 0,
        "evaluation_replay_excluded_from_operational_work": True,
        "source_ground_transaction_bytes_replayed": False,
        "local_allowed_after_result": local_allowed,
        "plan_certificate_verified": False,
        "official_execution_allowed": False,
        "verification_result": "PERSISTENT_PROOF_CACHE_AND_FRESH_QUERY_VERIFIED",
        "next_required_action": (
            "FREEZE_QUERY_LOCAL_RECOVERY_REQUEST_FROM_CACHED_FRONTIER"
            if local_allowed
            else "DIRECT_GROUND_FALLBACK"
        ),
    }
    return {
        **payload,
        "query_bound_persistent_proof_cache_verification_id": content_id(
            VERIFICATION_DOMAIN,
            payload,
        ),
    }


__all__ = [
    "ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error",
    "LOCAL_DOMAINS",
    "verify_query_bound_persistent_proof_cache_bundle_bytes_v1",
]
