"""Independent bytes replay of basis-authorized held-out model synthesis."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_overlay_abstract_reuse_independent_verifier_v1 as reuse_verifier
from acfqp import construction_k7_observation_derived_primitive_independent_verifier_v1 as basis_verifier
from acfqp import construction_k7_observed_program_heldout_independent_verifier_v1 as program_verifier
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_BASIS_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_MODEL_TRANSPORT_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_QUERY_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_SYNTHESIS_CAMPAIGN_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT = "2.0.153"
PROFILE = "construction_k7_basis_heldout_world_model_synthesis_v1"
GRAPH_TOPOLOGY_DOMAIN = "acfqp:relational-graph-topology:v1"
VERIFICATION_DOMAIN = CONSTRUCTION_K7_BASIS_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN
if VERIFICATION_DOMAIN not in PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("basis-heldout synthesis domain is not central")

W5_EDGES = (
    (0, 1), (0, 3), (0, 4), (1, 2),
    (1, 4), (2, 3), (2, 4), (3, 4),
)


class ConstructionK7BasisHeldoutWorldModelIndependentVerifierV1Error(ValueError):
    """Canonical held-out synthesis bytes do not independently replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7BasisHeldoutWorldModelIndependentVerifierV1Error(message)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7BasisHeldoutWorldModelIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _domain_id(document: dict[str, Any], domain: str, identity: str, nested: set[str]) -> str:
    identifier = _cid(document.get(identity), identity)
    payload = {key: value for key, value in document.items() if key != identity and key not in nested}
    if content_id(domain, payload) != identifier:
        _fail(f"{identity} content ID changed")
    return identifier


def _topology(document: Any, label: str) -> tuple[str, int, tuple[tuple[int, int], ...]]:
    row = _exact(
        document,
        {"schema", "schema_version", "vertex_count", "edges", "topology_id"},
        label,
    )
    edges = tuple(tuple(edge) for edge in row["edges"])
    if (
        row["schema"] != "acfqp.graph_topology.v1"
        or row["schema_version"] != "1.0.0"
        or type(row["vertex_count"]) is not int
        or edges != tuple(sorted(set(edges)))
        or any(
            len(edge) != 2
            or any(type(vertex) is not int for vertex in edge)
            or not 0 <= edge[0] < edge[1] < row["vertex_count"]
            for edge in edges
        )
    ):
        _fail(f"{label} topology changed")
    payload = {key: value for key, value in row.items() if key != "topology_id"}
    identifier = hashlib.sha256(
        GRAPH_TOPOLOGY_DOMAIN.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    if row["topology_id"] != identifier:
        _fail(f"{label} topology ID changed")
    return identifier, row["vertex_count"], edges


@dataclass(frozen=True, slots=True)
class BasisHeldoutWorldModelIndependentVerificationV1:
    campaign_id: str
    query_id: str
    transport_id: str
    plan_id: str
    primitive_verification_id: str
    program_verification_id: str
    reuse_verification_id: str

    def __post_init__(self) -> None:
        for value in (
            self.campaign_id, self.query_id, self.transport_id, self.plan_id,
            self.primitive_verification_id, self.program_verification_id,
            self.reuse_verification_id,
        ):
            _cid(value, "basis-heldout independent verification input")

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "role": "INDEPENDENT_VERIFICATION_V1",
                "campaign_id": self.campaign_id,
                "query_id": self.query_id,
                "transport_id": self.transport_id,
                "plan_id": self.plan_id,
                "primitive_verification_id": self.primitive_verification_id,
                "program_verification_id": self.program_verification_id,
                "reuse_verification_id": self.reuse_verification_id,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_basis_heldout_world_model_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "basis_heldout_synthesis_campaign_id": self.campaign_id,
            "basis_heldout_query_id": self.query_id,
            "basis_heldout_model_transport_id": self.transport_id,
            "basis_heldout_abstract_plan_id": self.plan_id,
            "primitive_independent_verification_id": self.primitive_verification_id,
            "program_independent_verification_id": self.program_verification_id,
            "source_reuse_independent_verification_id": self.reuse_verification_id,
            "query_isomorphism_replayed": True,
            "primitive_basis_replayed": True,
            "source_failure_recovery_and_model_replayed": True,
            "heldout_h2_abstract_audit_replayed": True,
            "no_transfer_controls_replayed": True,
            "process_execution_or_timing_independently_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


def verify_basis_heldout_world_model_synthesis_bytes_independently_v1(
    raw: bytes,
) -> BasisHeldoutWorldModelIndependentVerificationV1:
    if type(raw) is not bytes:
        _fail("basis-heldout independent verifier requires exact bytes")
    root = loads_canonical_json(raw)
    if type(root) is not dict or canonical_json_bytes(root) != raw:
        _fail("basis-heldout campaign is not canonical JSON")
    root = _exact(
        root,
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "observation_derived_primitive_campaign_id", "basis_heldout_query_id",
            "basis_heldout_model_transport_id", "basis_heldout_abstract_plan_id",
            "source_reuse_result_id", "source_reuse_bytes_sha256",
            "ordered_no_transfer_evaluation_ids", "world_model_construction_count",
            "abstract_h2_plan_count", "local_ground_recovery_count",
            "incremental_local_ground_draw_count",
            "local_ground_triggered_only_after_certificate_failure",
            "fresh_reuse_ground_draw_count", "unseen_structure_constructor_invocation_count",
            "cross_domain_constructor_invocation_count", "reusable_abstract_world_model_synthesized",
            "multi_step_planning_mainly_completed_in_abstract_model", "heldout_positive_scope",
            "broad_graph_or_cross_domain_generalization_claimed",
            "human_registered_relational_meta_grammar", "open_ended_operator_invention_claimed",
            "formal_exact_iid_plan_certificate", "official_execution_allowed",
            "official_scalar_cost", "official_N_break_even", "counter_completeness_gate_status",
            "workload_economics_gate_status", "primitive_campaign", "heldout_query",
            "model_transport", "heldout_plan", "source_reuse_result",
            "heldout_program_campaign", "basis_heldout_synthesis_campaign_id",
        },
        "basis-heldout campaign",
    )
    if (
        root["schema"] != "acfqp.construction_k7_basis_heldout_synthesis_campaign.v1"
        or root["schema_version"] != SCHEMA_VERSION
        or root["proposed_contract_version"] != CONTRACT
        or root["profile_key"] != PROFILE
        or root["world_model_construction_count"] != 1
        or root["abstract_h2_plan_count"] != 2
        or root["local_ground_recovery_count"] != 1
        or root["incremental_local_ground_draw_count"] != 4096
        or root["local_ground_triggered_only_after_certificate_failure"] is not True
        or root["fresh_reuse_ground_draw_count"] != 0
        or root["unseen_structure_constructor_invocation_count"] != 0
        or root["cross_domain_constructor_invocation_count"] != 0
        or root["reusable_abstract_world_model_synthesized"] is not True
        or root["multi_step_planning_mainly_completed_in_abstract_model"] is not True
        or root["heldout_positive_scope"] != "FRESH_PREREGISTERED_W5_VERTEX_RELABEL_ISOMORPHISM_ONLY"
        or root["broad_graph_or_cross_domain_generalization_claimed"] is not False
        or root["human_registered_relational_meta_grammar"] is not True
        or root["open_ended_operator_invention_claimed"] is not False
        or root["formal_exact_iid_plan_certificate"] is not False
        or root["official_execution_allowed"] is not False
        or root["official_scalar_cost"] is not None
        or root["official_N_break_even"] is not None
        or root["counter_completeness_gate_status"] != "NOT_RUN"
        or root["workload_economics_gate_status"] != "NOT_RUN"
    ):
        _fail("basis-heldout campaign claims changed")

    primitive_bytes = canonical_json_bytes(root["primitive_campaign"])
    primitive_verification = basis_verifier.verify_observation_derived_primitive_campaign_bytes_independently_v1(primitive_bytes)
    program_bytes = canonical_json_bytes(root["heldout_program_campaign"])
    program_verification = program_verifier.verify_observed_program_heldout_campaign_bytes_independently_v1(program_bytes)
    if (
        root["observation_derived_primitive_campaign_id"] != primitive_verification.campaign_id
        or root["primitive_campaign"]["source_heldout_program_campaign_id"]
        != program_verification.campaign_id
    ):
        _fail("primitive/program campaign join changed")

    query = _exact(
        root["heldout_query"],
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "basis_validation_observation_id", "basis_validation_program_evaluation_id", "source_context_id",
            "source_topology", "heldout_topology", "vertex_permutation_source_to_heldout",
            "source_root_ranks", "heldout_root_ranks", "horizon", "environment_semantics",
            "query_frozen_before_basis_derivation_and_authorized_constructor",
            "construction_topology_absent_from_basis_validation_rows",
            "query_value_policy_or_ground_input_present", "basis_heldout_query_id",
        },
        "basis-heldout query",
    )
    source_topology_id, count, source_edges = _topology(query["source_topology"], "source")
    heldout_topology_id, heldout_count, heldout_edges = _topology(query["heldout_topology"], "heldout")
    permutation = tuple(query["vertex_permutation_source_to_heldout"])
    source_ranks = tuple(query["source_root_ranks"])
    relabelled_ranks = [0] * len(source_ranks)
    for source_vertex, heldout_vertex in enumerate(permutation):
        relabelled_ranks[heldout_vertex] = source_ranks[source_vertex]
    expected_edges = tuple(
        sorted(tuple(sorted((permutation[left], permutation[right]))) for left, right in source_edges)
    )
    program_document = root["heldout_program_campaign"]
    positive_case = program_document["preregistration"]["ordered_cases"][0]
    positive_evaluation = program_document["heldout_evaluations"][0]
    validation_topology_id = positive_case["observation"]["structure"]["topology_id"]
    if (
        source_edges != W5_EDGES
        or count != heldout_count or count != 5
        or tuple(sorted(permutation)) != tuple(range(count))
        or heldout_edges != expected_edges
        or source_topology_id == heldout_topology_id
        or validation_topology_id == heldout_topology_id
        or source_ranks != (1, 1, 2, 0, 0)
        or query["heldout_root_ranks"] != relabelled_ranks
        or query["basis_validation_observation_id"] != positive_case["observation"]["heldout_observation_id"]
        or query["basis_validation_program_evaluation_id"] != positive_evaluation["heldout_evaluation_id"]
        or query["horizon"] != 2
        or query["environment_semantics"] != "VERTEX_RELABEL_TRANSPORT_OF_SOURCE_W5_V1"
        or query["query_frozen_before_basis_derivation_and_authorized_constructor"] is not True
        or query["construction_topology_absent_from_basis_validation_rows"] is not True
        or query["query_value_policy_or_ground_input_present"] is not False
    ):
        _fail("held-out query isomorphism replay changed")
    query_id = _domain_id(
        query,
        CONSTRUCTION_K7_BASIS_HELDOUT_QUERY_PREREGISTRATION_V1_DOMAIN,
        "basis_heldout_query_id",
        set(),
    )
    if root["basis_heldout_query_id"] != query_id:
        _fail("root/query identity join changed")

    reuse_bytes = canonical_json_bytes(root["source_reuse_result"])
    reuse_verification = reuse_verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(reuse_bytes)
    reuse = root["source_reuse_result"]
    reuse_digest = hashlib.sha256(reuse_bytes).hexdigest()
    if (
        root["source_reuse_result_id"] != reuse_verification.result_id
        or root["source_reuse_bytes_sha256"] != reuse_digest
    ):
        _fail("source reuse root binding changed")

    transport = _exact(
        root["model_transport"],
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "basis_heldout_query_id", "observation_derived_primitive_campaign_id",
            "observation_derived_primitive_basis_id", "source_world_model_synthesis_v3_result_id",
            "source_reuse_result_id", "source_reuse_bytes_sha256", "source_overlay_id",
            "quotient_model_id", "certified_audit_id", "selected_constructor_key",
            "constructor_selection_authority", "legacy_v3_executor_compatibility_cross_check_only",
            "base_abstract_certificate_status", "local_ground_recovery_triggered_after_failure",
            "changed_ground_distinction_count", "incremental_local_ground_draw_count",
            "final_abstract_certificate_status", "transport_kind", "state_action_bijection_rule",
            "canonical_quotient_model_reused_without_row_rewrite",
            "heldout_specific_model_bytes_materialized", "unseen_structure_transfer_allowed",
            "basis_heldout_model_transport_id",
        },
        "model transport",
    )
    if (
        transport["basis_heldout_query_id"] != query_id
        or transport["observation_derived_primitive_campaign_id"] != primitive_verification.campaign_id
        or transport["observation_derived_primitive_basis_id"] != primitive_verification.basis_id
        or transport["source_reuse_result_id"] != reuse_verification.result_id
        or transport["source_reuse_bytes_sha256"] != reuse_digest
        or transport["source_overlay_id"] != reuse["source_overlay_id"]
        or transport["quotient_model_id"] != reuse_verification.model_id
        or transport["certified_audit_id"] != reuse_verification.audit_id
        or transport["selected_constructor_key"] != "W5_CHECKPOINT_OVERLAY_V1"
        or transport["constructor_selection_authority"] != "OBSERVATION_DERIVED_PRIMITIVE_BASIS_AND_PROGRAM_V1"
        or transport["legacy_v3_executor_compatibility_cross_check_only"] is not True
        or transport["base_abstract_certificate_status"] != "FAILED_PROOF_FRONTIER"
        or transport["local_ground_recovery_triggered_after_failure"] is not True
        or transport["changed_ground_distinction_count"] != 2
        or transport["incremental_local_ground_draw_count"] != 4096
        or transport["final_abstract_certificate_status"] != "CERTIFIED"
        or transport["transport_kind"] != "VERTEX_PERMUTATION_EQUIVALENCE_CLASS"
        or transport["state_action_bijection_rule"] != "VERTEX_PERMUTATION_LIFT_V1"
        or transport["canonical_quotient_model_reused_without_row_rewrite"] is not True
        or transport["heldout_specific_model_bytes_materialized"] is not False
        or transport["unseen_structure_transfer_allowed"] is not False
    ):
        _fail("held-out model transport semantics changed")
    transport_id = _domain_id(
        transport,
        CONSTRUCTION_K7_BASIS_HELDOUT_MODEL_TRANSPORT_V1_DOMAIN,
        "basis_heldout_model_transport_id",
        set(),
    )
    if root["basis_heldout_model_transport_id"] != transport_id:
        _fail("root/transport identity join changed")

    plan = _exact(
        root["heldout_plan"],
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "basis_heldout_query_id", "basis_heldout_model_transport_id",
            "exact_reuse_world_model_synthesis_v3_result_id", "source_catalogue_query_result_id",
            "source_abstract_plan_id", "quotient_model_id", "certified_audit_id",
            "transported_policy_assignment_count", "horizon", "plan_certificate_kind",
            "multi_step_plan_completed_in_abstract_model",
            "fresh_occurrence_abstract_planner_invocations",
            "fresh_occurrence_model_construction_invocations",
            "fresh_occurrence_observer_call_count", "fresh_occurrence_ground_draw_count",
            "ground_solver_invocations", "formal_exact_iid_plan_certificate",
            "official_execution_allowed", "source_replayed_audit",
            "basis_heldout_abstract_plan_id",
        },
        "held-out abstract plan",
    )
    source_audit = reuse["plan"]["audit"]
    if (
        plan["basis_heldout_query_id"] != query_id
        or plan["basis_heldout_model_transport_id"] != transport_id
        or plan["quotient_model_id"] != reuse_verification.model_id
        or plan["certified_audit_id"] != reuse_verification.audit_id
        or plan["source_replayed_audit"] != source_audit
        or plan["transported_policy_assignment_count"] != len(source_audit["assignments"])
        or plan["horizon"] != 2
        or plan["plan_certificate_kind"] != "ISOMORPHISM_TRANSPORTED_CONDITIONAL_STATISTICAL"
        or plan["multi_step_plan_completed_in_abstract_model"] is not True
        or plan["fresh_occurrence_abstract_planner_invocations"] != 1
        or plan["fresh_occurrence_model_construction_invocations"] != 0
        or plan["fresh_occurrence_observer_call_count"] != 0
        or plan["fresh_occurrence_ground_draw_count"] != 0
        or plan["ground_solver_invocations"] != 0
        or plan["formal_exact_iid_plan_certificate"] is not False
        or plan["official_execution_allowed"] is not False
    ):
        _fail("held-out abstract plan replay changed")
    plan_id = _domain_id(
        plan,
        CONSTRUCTION_K7_BASIS_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN,
        "basis_heldout_abstract_plan_id",
        {"source_replayed_audit"},
    )
    if root["basis_heldout_abstract_plan_id"] != plan_id:
        _fail("root/plan identity join changed")

    no_transfer_ids = tuple(
        row["heldout_evaluation_id"] for row in program_document["heldout_evaluations"][1:]
    )
    if tuple(root["ordered_no_transfer_evaluation_ids"]) != no_transfer_ids:
        _fail("no-transfer controls differ from independent program replay")
    root_payload = {
        key: value
        for key, value in root.items()
        if key not in {
            "primitive_campaign", "heldout_query", "model_transport", "heldout_plan",
            "source_reuse_result", "heldout_program_campaign",
            "basis_heldout_synthesis_campaign_id",
        }
    }
    campaign_id = content_id(
        CONSTRUCTION_K7_BASIS_HELDOUT_SYNTHESIS_CAMPAIGN_V1_DOMAIN,
        root_payload,
    )
    if root["basis_heldout_synthesis_campaign_id"] != campaign_id:
        _fail("basis-heldout campaign content ID changed")
    return BasisHeldoutWorldModelIndependentVerificationV1(
        campaign_id,
        query_id,
        transport_id,
        plan_id,
        primitive_verification.verification_id,
        program_verification.verification_id,
        reuse_verification.verification_id,
    )


__all__ = (
    "BasisHeldoutWorldModelIndependentVerificationV1",
    "ConstructionK7BasisHeldoutWorldModelIndependentVerifierV1Error",
    "verify_basis_heldout_world_model_synthesis_bytes_independently_v1",
)
