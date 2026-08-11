"""Materialize exact H=2 proof dependencies across one local RAPM update.

The DAG factors each numerical row, its compiled behavior, the H=1 child
partition, H=2 quotient partition, exact policy search, failed frontier, and
proof root.  Stable semantic-row roles permit byte-exact reuse checks across
the second query-local validation overlay.  Only a changed row and nodes in
its transitive ancestor cone may be recomputed.

This is an immutable dependency certificate, not yet a persistent runtime
cache.  A later consumer must use it to avoid monolithic replanning for fresh
queries and must still request ground distinctions only after proof failure.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_query_bound_final_local_replanning_v1 as final_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import (
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
PROPOSED_CONTRACT_VERSION = "2.0.108"
PROFILE_KEY = "construction_k7_query_bound_rapm_proof_dependency_dag_v1"

NODE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_NODE_V1_DOMAIN
PARTITION_RESULT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_PARTITION_RESULT_V1_DOMAIN
)
SEARCH_RESULT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_SEARCH_RESULT_V1_DOMAIN
)
GRAPH_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_GRAPH_V1_DOMAIN
TRANSITION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_TRANSITION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {
        NODE_DOMAIN,
        PARTITION_RESULT_DOMAIN,
        SEARCH_RESULT_DOMAIN,
        GRAPH_DOMAIN,
        TRANSITION_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 5 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound proof-dependency domains are not central")

_TRANSITION_ISSUER = object()


class ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error(ValueError):
    """The proof graph or changed-ancestor resolution diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error(
            f"{label} must be one exact content ID"
        ) from error


class ProofDependencyNodeKindV1(str, Enum):
    SEMANTIC_ROW = "SEMANTIC_ROW"
    ROW_BEHAVIOR = "ROW_BEHAVIOR"
    CHILD_PARTITION = "CHILD_PARTITION"
    ROOT_PARTITION = "ROOT_PARTITION"
    POLICY_SEARCH = "POLICY_SEARCH"
    FAILED_FRONTIER = "FAILED_FRONTIER"
    PROOF_ROOT = "PROOF_ROOT"


class ProofDependencyResolutionV1(str, Enum):
    REUSED = "REUSED"
    RECOMPUTED = "RECOMPUTED"


@dataclass(frozen=True, slots=True)
class _DependencyRefV1:
    role_key: str
    node_id: str

    def __post_init__(self) -> None:
        if type(self.role_key) is not str or not self.role_key:
            _fail("proof dependency role is empty")
        _cid(self.node_id, "proof dependency node")

    def to_document(self) -> dict[str, str]:
        return {"role_key": self.role_key, "node_id": self.node_id}


@dataclass(frozen=True, slots=True)
class _ProofNodeV1:
    kind: ProofDependencyNodeKindV1
    role_key: str
    result_id: str
    dependencies: tuple[_DependencyRefV1, ...]
    _node_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not ProofDependencyNodeKindV1
            or type(self.role_key) is not str
            or not self.role_key
            or type(self.dependencies) is not tuple
            or tuple(item.role_key for item in self.dependencies)
            != tuple(sorted({item.role_key for item in self.dependencies}))
        ):
            _fail("proof dependency node is malformed")
        _cid(self.result_id, "proof dependency result")
        object.__setattr__(
            self,
            "_node_id",
            content_id(NODE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_rapm_proof_dependency_node.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "node_kind": self.kind.value,
            "role_key": self.role_key,
            "result_id": self.result_id,
            "dependencies": [item.to_document() for item in self.dependencies],
        }

    @property
    def node_id(self) -> str:
        return self._node_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_dependency_node_id": self.node_id}


@dataclass(frozen=True, slots=True)
class _ProofGraphV1:
    model: planning_v2.V075NumericalModelV2 = field(repr=False)
    proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    nodes: tuple[_ProofNodeV1, ...]
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.model) is not planning_v2.V075NumericalModelV2
            or type(self.proof) is not planning_v2.V075NumericalPlanningProofV2
            or self.proof.model != self.model
            or self.proof.route
            is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or self.proof.outcome
            is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
            or self.proof.quotient is None
            or self.proof.failed_frontier is None
            or type(self.nodes) is not tuple
            or tuple(item.role_key for item in self.nodes)
            != tuple(dict.fromkeys(item.role_key for item in self.nodes))
        ):
            _fail("proof dependency graph is malformed")
        role_to_node = {item.role_key: item for item in self.nodes}
        for node in self.nodes:
            for dependency in node.dependencies:
                expected = role_to_node.get(dependency.role_key)
                if expected is None or expected.node_id != dependency.node_id:
                    _fail("proof dependency graph contains a crossed edge")
        object.__setattr__(
            self,
            "_graph_id",
            content_id(GRAPH_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.proof.failed_frontier
        quotient = self.proof.quotient
        return {
            "schema": "acfqp.construction_k7_query_bound_rapm_proof_dependency_graph.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "numerical_model_id": self.model.model_id,
            "numerical_proof_id": self.proof.proof_id,
            "behavioral_quotient_id": quotient.quotient_id,
            "failed_frontier_id": frontier.frontier_id,
            "node_ids": [item.node_id for item in self.nodes],
            "node_role_keys": [item.role_key for item in self.nodes],
            "node_count": len(self.nodes),
            "query_identity_is_dependency": False,
            "threshold_profile_is_dependency": True,
            "exact_h2_dependency_structure": True,
        }

    @property
    def graph_id(self) -> str:
        return self._graph_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "nodes": [item.to_document() for item in self.nodes],
            "numerical_model": self.model.to_document(),
            "numerical_proof": self.proof.to_document(),
            "proof_dependency_graph_id": self.graph_id,
        }


@dataclass(frozen=True, slots=True)
class _ResolutionRowV1:
    role_key: str
    source_node_id: str
    target_node_id: str
    outcome: ProofDependencyResolutionV1
    reason: str

    def __post_init__(self) -> None:
        if type(self.role_key) is not str or not self.role_key:
            _fail("proof resolution role is empty")
        _cid(self.source_node_id, "source proof node")
        _cid(self.target_node_id, "target proof node")
        if (
            type(self.outcome) is not ProofDependencyResolutionV1
            or self.reason
            not in {
                "IDENTICAL_DEPENDENCY_CLOSURE",
                "SIGNED_SEMANTIC_ROW_DELTA",
                "CHANGED_ANCESTOR",
            }
            or (self.outcome is ProofDependencyResolutionV1.REUSED)
            != (self.source_node_id == self.target_node_id)
        ):
            _fail("proof dependency resolution is malformed")

    def to_document(self) -> dict[str, str]:
        return {
            "role_key": self.role_key,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "outcome": self.outcome.value,
            "reason": self.reason,
        }


def _ref(node: _ProofNodeV1) -> _DependencyRefV1:
    return _DependencyRefV1(node.role_key, node.node_id)


def _node(
    kind: ProofDependencyNodeKindV1,
    role_key: str,
    result_id: str,
    dependencies: Iterable[_ProofNodeV1] = (),
) -> _ProofNodeV1:
    return _ProofNodeV1(
        kind,
        role_key,
        result_id,
        tuple(sorted((_ref(item) for item in dependencies), key=lambda item: item.role_key)),
    )


def _binding_maps(
    model: planning_v2.V075NumericalModelV2,
) -> tuple[dict[str, planning_v2.V075NumericalRowV2], dict[str, str]]:
    by_binding = {item.row_binding_id: item for item in model.rows}
    if len(by_binding) != len(model.rows):
        _fail("numerical model repeats a semantic row binding")
    return by_binding, {item.row_id: item.row_binding_id for item in model.rows}


def _build_graph(
    model: planning_v2.V075NumericalModelV2,
    proof: planning_v2.V075NumericalPlanningProofV2,
) -> _ProofGraphV1:
    if proof.model != model or proof.quotient is None or proof.failed_frontier is None:
        _fail("proof dependency graph requires one exact failed adaptive proof")
    _by_binding, binding_by_row = _binding_maps(model)
    behavior_by_row = {item.row_id: item for item in proof.quotient.row_behaviors}
    if set(behavior_by_row) != set(binding_by_row):
        _fail("proof quotient behavior inventory crossed the model")
    row_nodes: dict[str, _ProofNodeV1] = {}
    ordered_nodes: list[_ProofNodeV1] = []
    for row in sorted(model.rows, key=lambda item: item.row_binding_id):
        role = f"ROW:{row.row_binding_id}"
        value = _node(
            ProofDependencyNodeKindV1.SEMANTIC_ROW,
            role,
            row.row_id,
        )
        row_nodes[row.row_binding_id] = value
        ordered_nodes.append(value)
    behavior_nodes: dict[str, _ProofNodeV1] = {}
    for row in sorted(
        (item for item in model.rows if item.remaining_horizon == 1),
        key=lambda item: item.row_binding_id,
    ):
        behavior = behavior_by_row[row.row_id]
        value = _node(
            ProofDependencyNodeKindV1.ROW_BEHAVIOR,
            f"BEHAVIOR:{row.row_binding_id}",
            behavior.behavior_key,
            (row_nodes[row.row_binding_id],),
        )
        behavior_nodes[row.row_binding_id] = value
        ordered_nodes.append(value)
    child_cells = tuple(
        sorted(
            (
                item.to_document()
                for item in proof.quotient.cells
                if item.remaining_horizon == 1
            ),
            key=lambda item: item["cell_id"],
        )
    )
    child_result = content_id(
        PARTITION_RESULT_DOMAIN,
        {
            "schema": "acfqp.construction_k7_query_bound_rapm_child_partition_result.v1",
            "schema_version": SCHEMA_VERSION,
            "cell_documents": list(child_cells),
        },
    )
    child_partition = _node(
        ProofDependencyNodeKindV1.CHILD_PARTITION,
        "CHILD_PARTITION",
        child_result,
        behavior_nodes.values(),
    )
    ordered_nodes.append(child_partition)
    for row in sorted(
        (item for item in model.rows if item.remaining_horizon == 2),
        key=lambda item: item.row_binding_id,
    ):
        behavior = behavior_by_row[row.row_id]
        value = _node(
            ProofDependencyNodeKindV1.ROW_BEHAVIOR,
            f"BEHAVIOR:{row.row_binding_id}",
            behavior.behavior_key,
            (row_nodes[row.row_binding_id], child_partition),
        )
        behavior_nodes[row.row_binding_id] = value
        ordered_nodes.append(value)
    root_partition = _node(
        ProofDependencyNodeKindV1.ROOT_PARTITION,
        "ROOT_PARTITION",
        proof.quotient.quotient_id,
        (
            child_partition,
            *(
                behavior_nodes[item.row_binding_id]
                for item in model.rows
                if item.remaining_horizon == 2
            ),
        ),
    )
    ordered_nodes.append(root_partition)
    search_result = content_id(
        SEARCH_RESULT_DOMAIN,
        {
            "schema": "acfqp.construction_k7_query_bound_rapm_policy_search_result.v1",
            "schema_version": SCHEMA_VERSION,
            "numerical_model_id": model.model_id,
            "behavioral_quotient_id": proof.quotient.quotient_id,
            "numerical_outcome": proof.outcome.value,
            "policy_assignments_evaluated": proof.policy_assignments_evaluated,
        },
    )
    search = _node(
        ProofDependencyNodeKindV1.POLICY_SEARCH,
        "POLICY_SEARCH",
        search_result,
        (root_partition, *behavior_nodes.values()),
    )
    ordered_nodes.append(search)
    obligation_dependencies = []
    for obligation in proof.failed_frontier.obligations:
        binding = binding_by_row.get(obligation.row_id)
        if binding is None:
            _fail("failed frontier obligation is not a model row")
        obligation_dependencies.append(behavior_nodes[binding])
    frontier = _node(
        ProofDependencyNodeKindV1.FAILED_FRONTIER,
        "FAILED_FRONTIER",
        proof.failed_frontier.frontier_id,
        (search, *obligation_dependencies),
    )
    ordered_nodes.append(frontier)
    proof_root = _node(
        ProofDependencyNodeKindV1.PROOF_ROOT,
        "PROOF_ROOT",
        proof.proof_id,
        (root_partition, search, frontier),
    )
    ordered_nodes.append(proof_root)
    return _ProofGraphV1(model, proof, tuple(ordered_nodes))


def _changed_ancestor_roles(
    source: _ProofGraphV1,
    target: _ProofGraphV1,
    changed_bindings: tuple[str, ...],
) -> tuple[str, ...]:
    reverse: dict[str, set[str]] = {}
    for graph in (source, target):
        for node in graph.nodes:
            for dependency in node.dependencies:
                reverse.setdefault(dependency.role_key, set()).add(node.role_key)
    closure = {f"ROW:{binding}" for binding in changed_bindings}
    pending = list(closure)
    while pending:
        role = pending.pop()
        for parent in reverse.get(role, ()):
            if parent not in closure:
                closure.add(parent)
                pending.append(parent)
    return tuple(sorted(closure))


@dataclass(frozen=True, slots=True)
class QueryBoundRAPMProofDependencyTransitionV1:
    _issuer: InitVar[object]
    source_final_local_replanning_id: str
    source_graph: _ProofGraphV1 = field(repr=False)
    target_graph: _ProofGraphV1 = field(repr=False)
    changed_row_binding_ids: tuple[str, ...]
    preserved_row_binding_ids: tuple[str, ...]
    resolutions: tuple[_ResolutionRowV1, ...]
    changed_ancestor_role_keys: tuple[str, ...]
    _transition_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TRANSITION_ISSUER
            or type(self.source_graph) is not _ProofGraphV1
            or type(self.target_graph) is not _ProofGraphV1
        ):
            _fail("proof dependency transition is caller-minted")
        _cid(self.source_final_local_replanning_id, "source final replanning")
        source_rows, _source_binding_by_row = _binding_maps(
            self.source_graph.model
        )
        target_rows, _target_binding_by_row = _binding_maps(
            self.target_graph.model
        )
        if (
            set(source_rows) != set(target_rows)
            or self.source_graph.model.context != self.target_graph.model.context
            or self.source_graph.model.evidence_kind
            != self.target_graph.model.evidence_kind
        ):
            _fail("proof dependency transition changed reusable model closure")
        expected_changed = tuple(
            sorted(
                binding
                for binding in source_rows
                if source_rows[binding].row_id != target_rows[binding].row_id
            )
        )
        expected_preserved = tuple(sorted(set(source_rows) - set(expected_changed)))
        if (
            self.changed_row_binding_ids != expected_changed
            or self.preserved_row_binding_ids != expected_preserved
            or not expected_changed
        ):
            _fail("proof dependency row partition changed")
        for binding in expected_changed:
            source_row = source_rows[binding]
            target_row = target_rows[binding]
            if (
                source_row.context_id != target_row.context_id
                or source_row.source_state_id != target_row.source_state_id
                or source_row.action != target_row.action
                or source_row.remaining_horizon != target_row.remaining_horizon
                or source_row.immediate_reward != target_row.immediate_reward
                or tuple(item.to_document() for item in source_row.support)
                != tuple(item.to_document() for item in target_row.support)
                or target_row.validation_draw_count
                <= source_row.validation_draw_count
            ):
                _fail("proof dependency changed a row outside validation bounds")
        source_nodes = {item.role_key: item for item in self.source_graph.nodes}
        target_nodes = {item.role_key: item for item in self.target_graph.nodes}
        if set(source_nodes) != set(target_nodes):
            _fail("proof dependency node roles changed")
        expected_resolutions = []
        for role_key in sorted(source_nodes):
            source_node = source_nodes[role_key]
            target_node = target_nodes[role_key]
            reused = source_node.node_id == target_node.node_id
            reason = (
                "IDENTICAL_DEPENDENCY_CLOSURE"
                if reused
                else (
                    "SIGNED_SEMANTIC_ROW_DELTA"
                    if role_key.startswith("ROW:")
                    else "CHANGED_ANCESTOR"
                )
            )
            expected_resolutions.append(
                _ResolutionRowV1(
                    role_key,
                    source_node.node_id,
                    target_node.node_id,
                    (
                        ProofDependencyResolutionV1.REUSED
                        if reused
                        else ProofDependencyResolutionV1.RECOMPUTED
                    ),
                    reason,
                )
            )
        if self.resolutions != tuple(expected_resolutions):
            _fail("proof dependency resolution differs from exact node replay")
        expected_ancestors = _changed_ancestor_roles(
            self.source_graph,
            self.target_graph,
            expected_changed,
        )
        recomputed = tuple(
            item.role_key
            for item in self.resolutions
            if item.outcome is ProofDependencyResolutionV1.RECOMPUTED
        )
        if (
            self.changed_ancestor_role_keys != expected_ancestors
            or recomputed != expected_ancestors
        ):
            _fail("proof dependency invalidation is not the exact ancestor cone")
        object.__setattr__(
            self,
            "_transition_id",
            content_id(TRANSITION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        reused = sum(
            item.outcome is ProofDependencyResolutionV1.REUSED
            for item in self.resolutions
        )
        recomputed = len(self.resolutions) - reused
        return {
            "schema": "acfqp.construction_k7_query_bound_rapm_proof_dependency_transition.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_final_local_replanning_id": (
                self.source_final_local_replanning_id
            ),
            "source_proof_dependency_graph_id": self.source_graph.graph_id,
            "target_proof_dependency_graph_id": self.target_graph.graph_id,
            "changed_semantic_row_binding_ids": list(
                self.changed_row_binding_ids
            ),
            "preserved_semantic_row_binding_ids": list(
                self.preserved_row_binding_ids
            ),
            "changed_ancestor_role_keys": list(self.changed_ancestor_role_keys),
            "resolutions": [item.to_document() for item in self.resolutions],
            "proof_node_count": len(self.resolutions),
            "reused_proof_node_count": reused,
            "recomputed_proof_node_count": recomputed,
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

    @property
    def transition_id(self) -> str:
        current = content_id(TRANSITION_DOMAIN, self._payload())
        if current != self._transition_id:
            _fail("proof dependency transition changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_graph": self.source_graph.to_document(),
            "target_graph": self.target_graph.to_document(),
            "query_bound_rapm_proof_dependency_transition_id": (
                self.transition_id
            ),
        }


def _transition(
    *,
    source_final_local_replanning_id: str,
    source_model: planning_v2.V075NumericalModelV2,
    source_proof: planning_v2.V075NumericalPlanningProofV2,
    target_model: planning_v2.V075NumericalModelV2,
    target_proof: planning_v2.V075NumericalPlanningProofV2,
) -> QueryBoundRAPMProofDependencyTransitionV1:
    source_graph = _build_graph(source_model, source_proof)
    target_graph = _build_graph(target_model, target_proof)
    source_rows, _ = _binding_maps(source_model)
    target_rows, _ = _binding_maps(target_model)
    if set(source_rows) != set(target_rows):
        _fail("proof dependency transition changed semantic row inventory")
    changed = tuple(
        sorted(
            binding
            for binding in source_rows
            if source_rows[binding].row_id != target_rows[binding].row_id
        )
    )
    preserved = tuple(sorted(set(source_rows) - set(changed)))
    source_nodes = {item.role_key: item for item in source_graph.nodes}
    target_nodes = {item.role_key: item for item in target_graph.nodes}
    resolutions = tuple(
        _ResolutionRowV1(
            role,
            source_nodes[role].node_id,
            target_nodes[role].node_id,
            (
                ProofDependencyResolutionV1.REUSED
                if source_nodes[role].node_id == target_nodes[role].node_id
                else ProofDependencyResolutionV1.RECOMPUTED
            ),
            (
                "IDENTICAL_DEPENDENCY_CLOSURE"
                if source_nodes[role].node_id == target_nodes[role].node_id
                else (
                    "SIGNED_SEMANTIC_ROW_DELTA"
                    if role.startswith("ROW:")
                    else "CHANGED_ANCESTOR"
                )
            ),
        )
        for role in sorted(source_nodes)
    )
    return QueryBoundRAPMProofDependencyTransitionV1(
        _TRANSITION_ISSUER,
        _cid(source_final_local_replanning_id, "source final replanning"),
        source_graph,
        target_graph,
        changed,
        preserved,
        resolutions,
        _changed_ancestor_roles(source_graph, target_graph, changed),
    )


def freeze_query_bound_rapm_proof_dependency_transition_v1(
    final_local: final_v1.QueryBoundFinalLocalReplanningV1,
) -> QueryBoundRAPMProofDependencyTransitionV1:
    final_local = final_v1.verify_query_bound_final_local_replanning_v1(
        final_local
    )
    return _transition(
        source_final_local_replanning_id=final_local.result_id,
        source_model=final_local.source_model,
        source_proof=final_local.source_proof,
        target_model=final_local.successor_model,
        target_proof=final_local.successor_proof,
    )


def replay_query_bound_rapm_proof_dependency_transition_bytes_v1(
    transition_bytes: bytes,
) -> QueryBoundRAPMProofDependencyTransitionV1:
    if type(transition_bytes) is not bytes or not transition_bytes:
        _fail("proof dependency transition must be nonempty bytes")
    try:
        document = loads_canonical_json(transition_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != transition_bytes:
            _fail("proof dependency transition is not canonical")
        source_graph = document["source_graph"]
        target_graph = document["target_graph"]
        source_model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(source_graph["numerical_model"])
        )
        source_proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(source_graph["numerical_proof"])
        )
        target_model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(target_graph["numerical_model"])
        )
        target_proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(target_graph["numerical_proof"])
        )
        expected = _transition(
            source_final_local_replanning_id=document[
                "source_final_local_replanning_id"
            ],
            source_model=source_model,
            source_proof=source_proof,
            target_model=target_model,
            target_proof=target_proof,
        )
    except ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error(
            "proof dependency transition failed typed replay"
        ) from error
    if canonical_json_bytes(expected.to_document()) != transition_bytes:
        _fail("proof dependency transition differs from exact replay")
    return expected


__all__ = [
    "ConstructionK7QueryBoundRAPMProofDependencyDAGV1Error",
    "LOCAL_DOMAINS",
    "ProofDependencyNodeKindV1",
    "ProofDependencyResolutionV1",
    "QueryBoundRAPMProofDependencyTransitionV1",
    "freeze_query_bound_rapm_proof_dependency_transition_v1",
    "replay_query_bound_rapm_proof_dependency_transition_bytes_v1",
]
