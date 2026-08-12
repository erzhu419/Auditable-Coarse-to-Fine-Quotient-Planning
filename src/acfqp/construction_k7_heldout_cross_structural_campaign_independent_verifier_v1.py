"""Producer-free replay of the W5+K6 structural campaign.

Only the two existing producer-free child verifiers are trusted as semantic
subroutines.  This module does not import the cross-structural producer or any
checkpoint, reuse, accounting, or child-campaign producer.  It reconstructs
the aggregate preregistration, both structural rows, their identity separation,
the cumulative comparison vector, and all three two-row denominators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import SHARED_AXES
from acfqp import (
    construction_k7_heldout_abstract_campaign_independent_verifier_v1
    as w5_verifier_v1,
)
from acfqp import (
    construction_k7_heldout_k6_abstract_campaign_independent_verifier_v1
    as k6_verifier_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PRODUCER_CONTRACT_VERSION = "2.0.134"
PROPOSED_CONTRACT_VERSION = "2.0.135"
PROFILE_KEY = (
    "construction_k7_heldout_cross_structural_campaign_independent_verifier_v1"
)
PRODUCER_PROFILE_KEY = "construction_k7_heldout_cross_structural_campaign_v1"
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("cross-structural verification domain is not central")

EXPECTED_FILENAMES = (
    "0001_PREREGISTRATION.json",
    "0002_W5_CHILD_ROW.json",
    "0003_K6_CHILD_ROW.json",
    "0004_CAMPAIGN_CLOSURE.json",
)
_FAMILY_SPECS: Mapping[str, tuple[str, int, str, str]] = {
    "W5": (
        "opaque_graph_w5_v0",
        5,
        "acfqp.construction_k7_heldout_abstract_reuse_result.v1",
        "acfqp.construction_k7_heldout_checkpoint_recertification_result.v1",
    ),
    "K6": (
        "opaque_graph_k6_v0",
        6,
        "acfqp.construction_k7_heldout_k6_abstract_reuse_result.v1",
        "acfqp.construction_k7_heldout_k6_recertification_result.v1",
    ),
}


class ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error(
    ValueError
):
    """The portable aggregate directory or either child replay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} must be canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _read_directory(root: Path) -> tuple[dict[str, Any], ...]:
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) & 0o077
        or tuple(sorted(path.name for path in root.iterdir()))
        != tuple(sorted(EXPECTED_FILENAMES))
    ):
        _fail("cross-structural campaign directory inventory changed")
    documents = []
    for filename in EXPECTED_FILENAMES:
        path = root / filename
        if path.is_symlink() or not path.is_file():
            _fail("cross-structural campaign artifact is not regular")
        documents.append(_canonical(path.read_bytes(), filename))
    return tuple(documents)


def _child_spec(
    family_key: str,
    reuse_bytes: bytes,
    preregistration_id: Any,
    closure_id: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context_key, vertex_count, reuse_schema, _source_schema = _FAMILY_SPECS[family_key]
    reuse = _canonical(reuse_bytes, f"{family_key} reuse result")
    if reuse.get("schema") != reuse_schema:
        _fail(f"{family_key} reuse schema changed")
    result_id = _cid(reuse.get("result_id"), f"{family_key} reuse result")
    spec = {
        "family_key": family_key,
        "source_vertex_counts": [4],
        "target_context_key": context_key,
        "target_vertex_count": vertex_count,
        "reuse_result_id": result_id,
        "reuse_bytes_sha256": hashlib.sha256(reuse_bytes).hexdigest(),
        "reuse_byte_count": len(reuse_bytes),
        "child_campaign_preregistration_id": _cid(
            preregistration_id, f"{family_key} child preregistration"
        ),
        "child_campaign_closure_id": _cid(
            closure_id, f"{family_key} child closure"
        ),
        "expected_route_kind": "ABSTRACT_ONLY_CERTIFICATE",
        "expected_terminal_class": "PLAN_CERTIFICATE",
        "expected_terminal_code": "ABSTRACT_CERTIFIED",
    }
    return spec, reuse


def _preregistration_payload(specs: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "ordered_child_specs": list(specs),
        "registered_structural_context_count": 2,
        "registered_logical_occurrence_count": 2,
        "preregistration_committed_before_child_independent_replay": True,
        "child_operational_execution_preexists_this_aggregate": True,
        "denominator_row_deletion_allowed": False,
        "cross_structural_model_transfer_allowed": False,
        "official_execution_allowed": False,
    }


def _cheap_gate(
    preregistration: Mapping[str, Any],
    rows: tuple[Mapping[str, Any], ...],
    closure: Mapping[str, Any],
) -> None:
    specs = preregistration.get("ordered_child_specs")
    if (
        type(specs) is not list
        or len(specs) != 2
        or [row.get("family_key") for row in specs] != ["W5", "K6"]
        or preregistration.get("registered_structural_context_count") != 2
        or preregistration.get("registered_logical_occurrence_count") != 2
        or preregistration.get("denominator_row_deletion_allowed") is not False
        or preregistration.get("cross_structural_model_transfer_allowed") is not False
        or preregistration.get("official_execution_allowed") is not False
        or [row.get("child_spec", {}).get("family_key") for row in rows]
        != ["W5", "K6"]
        or any(row.get("route_kind") != "ABSTRACT_ONLY_CERTIFICATE" for row in rows)
        or any(row.get("terminal_class") != "PLAN_CERTIFICATE" for row in rows)
        or any(row.get("terminal_code") != "ABSTRACT_CERTIFIED" for row in rows)
        or any(row.get("fresh_ground_or_observer_event_count") != 0 for row in rows)
        or any(row.get("cross_structural_model_transfer_attempted") is not False for row in rows)
        or closure.get("registered_structural_context_count") != 2
        or closure.get("registered_logical_occurrence_count") != 2
        or closure.get("closed_logical_occurrence_count") != 2
        or closure.get("closure_denominator") != 2
        or closure.get("certificate_coverage_denominator") != 2
        or closure.get("future_economics_cost_denominator") != 2
        or closure.get("plan_certificate_count") != 2
        or closure.get("infeasibility_certificate_count") != 0
        or closure.get("noncertificate_count") != 0
        or closure.get("cross_structural_model_transfer_attempted") is not False
        or closure.get("official_execution_allowed") is not False
    ):
        _fail("cross-structural cheap claim or denominator gate changed")


def _structural_facts(
    family_key: str,
    reuse: Mapping[str, Any],
) -> dict[str, Any]:
    context_key, vertex_count, reuse_schema, source_schema = _FAMILY_SPECS[family_key]
    source = reuse.get("source_result")
    query = reuse.get("query")
    plan = reuse.get("plan")
    model = reuse.get("final_quotient_model")
    if (
        reuse.get("schema") != reuse_schema
        or not all(type(item) is dict for item in (source, query, plan, model))
    ):
        _fail(f"{family_key} structural evidence is incomplete")
    preregistration = source.get("preregistration")
    if type(preregistration) is not dict:
        _fail(f"{family_key} source preregistration is absent")
    source_result_id = _cid(reuse.get("source_result_id"), f"{family_key} source")
    source_overlay_id = _cid(reuse.get("source_overlay_id"), f"{family_key} overlay")
    context_id = _cid(source.get("target_context_id"), f"{family_key} context")
    model_id = _cid(query.get("quotient_model_id"), f"{family_key} model")
    query_id = _cid(reuse.get("query_id"), f"{family_key} query")
    plan_id = _cid(reuse.get("plan_id"), f"{family_key} plan")
    audit_id = _cid(reuse.get("replanned_audit_id"), f"{family_key} audit")
    zero_fields = (
        "fresh_occurrence_new_ground_draw_count",
        "fresh_occurrence_observer_call_count",
        "fresh_occurrence_ground_solver_invocations",
        "fresh_occurrence_evaluation_exact_kernel_calls",
    )
    if (
        source.get("schema") != source_schema
        or source.get("result_id") != source_result_id
        or source.get("source_vertex_counts") != [4]
        or source.get("target_vertex_count") != vertex_count
        or preregistration.get("target_context_key") != context_key
        or query.get("context_id") != context_id
        or source.get("final_overlay_id") != source_overlay_id
        or query.get("source_overlay_id") != source_overlay_id
        or query.get("source_result_id") != source_result_id
        or source.get("final_quotient_model_id") != model_id
        or model.get("model_id") != model_id
        or query.get("query_id") != query_id
        or plan.get("query_id") != query_id
        or plan.get("plan_id") != plan_id
        or plan.get("replanned_audit_id") != audit_id
        or plan.get("audit_status") != "CERTIFIED"
        or source.get("multi_step_plan_formed_in_abstract_model") is not True
        or source.get("local_ground_restoration_only_after_certificate_failure")
        is not True
        or source.get("query_neutral_overlay_reusable") is not True
        or reuse.get("fresh_occurrence_directly_abstract_certified") is not True
        or reuse.get("certificate_failure_triggered_local_recovery") is not False
        or reuse.get("source_local_recovery_reused_as_query_neutral_overlay")
        is not True
        or reuse.get("fresh_occurrence_abstract_planner_invocations") != 1
        or any(reuse.get(field) != 0 for field in zero_fields)
        or (
            family_key == "K6"
            and reuse.get("fresh_occurrence_model_build_invocations") != 0
        )
    ):
        _fail(f"{family_key} structural identity or abstract-first claim changed")
    changed = source.get("changed_row_count")
    draws = source.get("incremental_local_ground_draw_count")
    if (
        type(changed) is not int
        or type(draws) is not int
        or (family_key == "W5" and (changed, draws) != (2, 4096))
        or (family_key == "K6" and (changed, draws) != (1, 8192))
    ):
        _fail(f"{family_key} recovery cardinality changed")
    return {
        "source_result_id": source_result_id,
        "source_overlay_id": source_overlay_id,
        "target_context_id": context_id,
        "quotient_model_id": model_id,
        "query_id": query_id,
        "plan_id": plan_id,
        "audit_id": audit_id,
        "changed_row_count": changed,
        "draw_count": draws,
    }


def _verification_document(family_key: str, verification: Any) -> dict[str, Any]:
    document = verification.to_document()
    if (
        document.get("valid") is not True
        or document.get("registered_logical_occurrence_count") != 1
        or document.get("closed_logical_occurrence_count") != 1
        or document.get("plan_certificate_count") != 1
        or document.get("noncertificate_count") != 0
        or document.get("official_execution_allowed") is not False
    ):
        _fail(f"{family_key} child verification contract changed")
    return document


def _row_payload(
    *,
    preregistration_id: str,
    spec: dict[str, Any],
    verification: Any,
    facts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_child_row.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "campaign_preregistration_id": preregistration_id,
        "child_spec": spec,
        "child_independent_verification": _verification_document(
            spec["family_key"], verification
        ),
        "source_result_id": facts["source_result_id"],
        "source_overlay_id": facts["source_overlay_id"],
        "target_context_id": facts["target_context_id"],
        "quotient_model_id": facts["quotient_model_id"],
        "query_id": facts["query_id"],
        "plan_id": facts["plan_id"],
        "audit_id": facts["audit_id"],
        "work_vector_id": verification.work_vector_id,
        "comparison_vector_id": verification.comparison_vector_id,
        "comparison_values": [
            {"axis": axis, "value": value}
            for axis, value in verification.comparison_values
        ],
        "io.output_bytes": verification.output_bytes,
        "historical_source_changed_row_count": facts["changed_row_count"],
        "historical_source_incremental_local_ground_draw_count": facts["draw_count"],
        "fresh_ground_or_observer_event_count": 0,
        "route_kind": "ABSTRACT_ONLY_CERTIFICATE",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "ABSTRACT_CERTIFIED",
        "closure_denominator_contribution": 1,
        "certificate_coverage_denominator_contribution": 1,
        "future_economics_denominator_contribution": 1,
        "model_scope": "PER_REGISTERED_STRUCTURAL_CONTEXT_ONLY",
        "cross_structural_model_transfer_attempted": False,
        "official_execution_allowed": False,
    }


def _comparison_values(verification: Any) -> tuple[tuple[str, int], ...]:
    values = tuple(verification.comparison_values)
    if (
        tuple(axis for axis, _value in values) != SHARED_AXES
        or any(type(value) is not int or value < 0 for _axis, value in values)
    ):
        _fail("child comparison vector changed")
    return values


def _closure_payload(
    preregistration_id: str,
    row_ids: tuple[str, str],
    verifications: tuple[Any, Any],
    facts: tuple[dict[str, Any], dict[str, Any]],
) -> tuple[dict[str, Any], tuple[tuple[str, int], ...]]:
    values = tuple(_comparison_values(item) for item in verifications)
    cumulative = tuple(
        (axis, dict(values[0])[axis] + dict(values[1])[axis])
        for axis in SHARED_AXES
    )
    payload = {
        "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "campaign_preregistration_id": preregistration_id,
        "ordered_child_row_ids": list(row_ids),
        "registered_structural_context_count": 2,
        "registered_target_vertex_counts": [5, 6],
        "registered_logical_occurrence_count": 2,
        "closed_logical_occurrence_count": 2,
        "closure_denominator": 2,
        "certificate_coverage_denominator": 2,
        "future_economics_cost_denominator": 2,
        "plan_certificate_count": 2,
        "infeasibility_certificate_count": 0,
        "noncertificate_count": 0,
        "cumulative_comparison_values": [
            {"axis": axis, "value": value} for axis, value in cumulative
        ],
        "distinct_source_result_count": len(
            {item["source_result_id"] for item in facts}
        ),
        "distinct_source_overlay_count": len(
            {item["source_overlay_id"] for item in facts}
        ),
        "distinct_quotient_model_count": len(
            {item["quotient_model_id"] for item in facts}
        ),
        "distinct_fresh_query_count": len({item["query_id"] for item in facts}),
        "distinct_fresh_plan_count": len({item["plan_id"] for item in facts}),
        "historical_source_changed_row_count": sum(
            item["changed_row_count"] for item in facts
        ),
        "historical_source_incremental_local_ground_draw_count": sum(
            item["draw_count"] for item in facts
        ),
        "fresh_ground_or_observer_event_count": 0,
        "certificate_failure_gated_local_ground_recovery_in_each_structure": True,
        "recovered_models_reused_by_fresh_multi_step_plans": True,
        "cross_structural_model_transfer_attempted": False,
        "automatic_coordinate_primitive_invention_claimed": False,
        "broad_cross_domain_generalization_claimed": False,
        "all_registered_occurrences_retained": True,
        "campaign_construction_closed": True,
        "campaign_orchestration_work_vector_issued": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return payload, cumulative


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralCampaignIndependentVerificationV1:
    preregistration_id: str
    child_row_ids: tuple[str, str]
    closure_id: str
    child_verification_ids: tuple[str, str]
    source_result_ids: tuple[str, str]
    source_overlay_ids: tuple[str, str]
    quotient_model_ids: tuple[str, str]
    query_ids: tuple[str, str]
    plan_ids: tuple[str, str]
    cumulative_comparison_values: tuple[tuple[str, int], ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "aggregate preregistration")
        _cid(self.closure_id, "aggregate closure")
        for values, label in (
            (self.child_row_ids, "child row"),
            (self.child_verification_ids, "child verification"),
            (self.source_result_ids, "source result"),
            (self.source_overlay_ids, "source overlay"),
            (self.quotient_model_ids, "quotient model"),
            (self.query_ids, "fresh query"),
            (self.plan_ids, "fresh plan"),
        ):
            if len(values) != 2 or len(set(values)) != 2:
                _fail(f"aggregate {label} identities changed or collapsed")
            for value in values:
                _cid(value, f"aggregate {label}")
        if tuple(axis for axis, _value in self.cumulative_comparison_values) != SHARED_AXES:
            _fail("aggregate cumulative comparison axes changed")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "ordered_child_row_ids": list(self.child_row_ids),
            "campaign_closure_id": self.closure_id,
            "ordered_child_independent_verification_ids": list(
                self.child_verification_ids
            ),
            "ordered_source_result_ids": list(self.source_result_ids),
            "ordered_source_overlay_ids": list(self.source_overlay_ids),
            "ordered_quotient_model_ids": list(self.quotient_model_ids),
            "ordered_fresh_query_ids": list(self.query_ids),
            "ordered_fresh_plan_ids": list(self.plan_ids),
            "registered_structural_context_count": 2,
            "registered_target_vertex_counts": [5, 6],
            "registered_logical_occurrence_count": 2,
            "closed_logical_occurrence_count": 2,
            "closure_denominator": 2,
            "certificate_coverage_denominator": 2,
            "future_economics_cost_denominator": 2,
            "plan_certificate_count": 2,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 0,
            "historical_source_changed_row_count": 3,
            "historical_source_incremental_local_ground_draw_count": 12288,
            "fresh_ground_or_observer_event_count": 0,
            "cumulative_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.cumulative_comparison_values
            ],
            "child_producer_modules_imported": False,
            "aggregate_producer_module_imported": False,
            "cross_structural_model_transfer_attempted": False,
            "automatic_coordinate_primitive_invention_claimed": False,
            "broad_cross_domain_generalization_claimed": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        current = content_id(VERIFICATION_DOMAIN, self._payload())
        if current != self._verification_id:
            _fail("cross-structural independent verification changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cross_structural_campaign_independent_verification_id": (
                self.verification_id
            ),
        }


def verify_heldout_cross_structural_campaign_directory_bytes_v1(
    *,
    campaign_directory: str | Path,
    w5_reuse_result_bytes: bytes,
    w5_campaign_directory: str | Path,
    k6_reuse_result_bytes: bytes,
    k6_campaign_directory: str | Path,
    expected_preregistration_id: str,
    expected_closure_id: str,
) -> HeldoutCrossStructuralCampaignIndependentVerificationV1:
    """Replay both children and the aggregate from canonical bytes."""

    preregistration, w5_row, k6_row, closure = _read_directory(
        Path(campaign_directory)
    )
    rows = (w5_row, k6_row)
    _cheap_gate(preregistration, rows, closure)
    stored_specs = preregistration.get("ordered_child_specs")
    w5_spec, w5_reuse = _child_spec(
        "W5",
        w5_reuse_result_bytes,
        stored_specs[0].get("child_campaign_preregistration_id"),
        stored_specs[0].get("child_campaign_closure_id"),
    )
    k6_spec, k6_reuse = _child_spec(
        "K6",
        k6_reuse_result_bytes,
        stored_specs[1].get("child_campaign_preregistration_id"),
        stored_specs[1].get("child_campaign_closure_id"),
    )
    specs = (w5_spec, k6_spec)
    preregistration_payload = _preregistration_payload(specs)
    preregistration_id = content_id(
        CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
        preregistration_payload,
    )
    if (
        preregistration
        != {**preregistration_payload, "campaign_preregistration_id": preregistration_id}
        or preregistration_id != _cid(expected_preregistration_id, "expected preregistration")
    ):
        _fail("cross-structural preregistration differs from independent replay")
    w5_verification = w5_verifier_v1.verify_heldout_abstract_campaign_directory_bytes_v1(
        reuse_result_bytes=w5_reuse_result_bytes,
        campaign_directory=w5_campaign_directory,
        expected_preregistration_id=w5_spec["child_campaign_preregistration_id"],
        expected_closure_id=w5_spec["child_campaign_closure_id"],
    )
    k6_verification = k6_verifier_v1.verify_heldout_k6_abstract_campaign_directory_bytes_v1(
        reuse_result_bytes=k6_reuse_result_bytes,
        campaign_directory=k6_campaign_directory,
        expected_preregistration_id=k6_spec["child_campaign_preregistration_id"],
        expected_closure_id=k6_spec["child_campaign_closure_id"],
    )
    verifications = (w5_verification, k6_verification)
    facts = (
        _structural_facts("W5", w5_reuse),
        _structural_facts("K6", k6_reuse),
    )
    for key in (
        "source_result_id",
        "source_overlay_id",
        "target_context_id",
        "quotient_model_id",
        "query_id",
        "plan_id",
    ):
        if len({item[key] for item in facts}) != 2:
            _fail(f"cross-structural {key} identities collapsed")
    row_payloads = tuple(
        _row_payload(
            preregistration_id=preregistration_id,
            spec=spec,
            verification=verification,
            facts=fact,
        )
        for spec, verification, fact in zip(specs, verifications, facts)
    )
    row_ids = tuple(
        content_id(
            CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN,
            payload,
        )
        for payload in row_payloads
    )
    expected_rows = tuple(
        {**payload, "cross_structural_child_row_id": row_id}
        for payload, row_id in zip(row_payloads, row_ids)
    )
    if rows != expected_rows:
        _fail("cross-structural child row differs from independent replay")
    closure_payload, cumulative = _closure_payload(
        preregistration_id,
        row_ids,
        verifications,
        facts,
    )
    closure_id = content_id(
        CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN,
        closure_payload,
    )
    if (
        closure != {**closure_payload, "campaign_closure_id": closure_id}
        or closure_id != _cid(expected_closure_id, "expected closure")
    ):
        _fail("cross-structural closure differs from independent replay")
    child_verification_ids = (
        w5_verification.verification_id,
        k6_verification.verification_id,
    )
    return HeldoutCrossStructuralCampaignIndependentVerificationV1(
        preregistration_id,
        row_ids,
        closure_id,
        child_verification_ids,
        tuple(item["source_result_id"] for item in facts),
        tuple(item["source_overlay_id"] for item in facts),
        tuple(item["quotient_model_id"] for item in facts),
        tuple(item["query_id"] for item in facts),
        tuple(item["plan_id"] for item in facts),
        cumulative,
    )


__all__ = (
    "ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error",
    "HeldoutCrossStructuralCampaignIndependentVerificationV1",
    "LOCAL_DOMAINS",
    "verify_heldout_cross_structural_campaign_directory_bytes_v1",
)
